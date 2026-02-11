#!/usr/bin/env python3
"""Create a sandboxed git worktree with COW clones for symlink targets.

Usage: create_worktree.py [-b] [--deny-sandbox-bypass] <branch-name> [worktree-path]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# SF_DATALESS flag indicating cloud-only file (Dropbox, iCloud, etc.)
SF_DATALESS = 0x40000000


def is_dataless(path: Path) -> bool:
    """Check if file has the dataless flag (online-only cloud file)."""
    try:
        flags = os.stat(path).st_flags
        return bool(flags & SF_DATALESS)
    except (OSError, AttributeError):
        return False


def cow_copy(src: Path, dst: Path) -> bool:
    """Copy file using COW (copy-on-write) if available, fallback to regular copy.

    Returns True on success, False on failure.
    """
    # Remove destination if it exists to avoid conflicts
    if dst.exists() or dst.is_symlink():
        dst.unlink()

    try:
        # macOS supports COW via clonefile
        subprocess.run(["cp", "-c", str(src), str(dst)], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        # cp -c failed - clean up any partial file and try regular copy
        if dst.exists():
            dst.unlink()
        try:
            shutil.copy2(src, dst)
            return True
        except (OSError, shutil.Error) as e:
            print(f"    Warning: Failed to copy {src}: {e}", file=sys.stderr)
            return False


def smart_copy_dir(src: Path, dst: Path, rel_display: str = "") -> tuple[int, int]:
    """Copy directory contents: COW clone local files, symlink cloud files.

    Returns (local_count, cloud_count).
    """
    local_count = 0
    cloud_count = 0

    for item in src.iterdir():
        name = item.name
        if name in (".", ".."):
            continue

        dst_item = dst / name

        if item.is_symlink():
            # Symlink inside directory - recreate the symlink
            target = os.readlink(item)
            dst_item.unlink(missing_ok=True)
            dst_item.symlink_to(target)
        elif item.is_file():
            if is_dataless(item):
                # Cloud file - create symlink to original
                dst_item.unlink(missing_ok=True)
                dst_item.symlink_to(item.resolve())
                cloud_count += 1
            else:
                # Local file - COW clone
                cow_copy(item, dst_item)
                local_count += 1
        elif item.is_dir():
            # Subdirectory - recurse
            dst_item.mkdir(parents=True, exist_ok=True)
            sub_local, sub_cloud = smart_copy_dir(item, dst_item)
            local_count += sub_local
            cloud_count += sub_cloud

    if rel_display:
        print(f"    ({local_count} local COW, {cloud_count} cloud symlinks)")

    return local_count, cloud_count


def is_git_tracked(path: str) -> bool:
    """Check if path is tracked by git (as a symlink)."""
    try:
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", path],
            check=True, capture_output=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def is_within_repo(target: Path, repo_root: Path) -> bool:
    """Return True if target is inside the repository root."""
    try:
        target.resolve().relative_to(repo_root.resolve())
        return True
    except ValueError:
        return False


def get_gitignored_paths(src_dir: Path) -> list[tuple[Path, bool]]:
    """Get all gitignored paths using git ls-files.

    Returns (relative_path, is_directory) tuples.
    Works correctly for all .gitignore patterns: output/, output/**, output, etc.
    """
    result = subprocess.run(
        ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "--directory"],
        capture_output=True, text=True, cwd=src_dir
    )
    if not result.stdout.strip():
        return []
    paths = []
    for line in result.stdout.strip().split('\n'):
        is_dir = line.endswith('/')
        paths.append((Path(line.rstrip('/')), is_dir))
    return paths


def parse_worktree_annotations(repo_root: Path) -> set[str]:
    """Parse .gitignore for paths annotated with '# worktree:symlink'.

    Returns set of normalized directory/file paths to symlink instead of COW clone.
    """
    symlink_paths = set()
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.exists():
        return symlink_paths

    for line in gitignore_path.read_text().splitlines():
        if "# worktree:symlink" not in line:
            continue
        # Extract pattern (everything before the comment)
        pattern = line.split("#")[0].strip()
        if not pattern:
            continue
        # Normalize: output/, output/**, output/* all -> "output"
        normalized = pattern.rstrip("/")
        # Strip trailing glob: output/** -> output, models/*.bin -> models
        if "/**" in normalized:
            normalized = normalized.split("/**")[0]
        elif "/*" in normalized:
            normalized = normalized.split("/*")[0]
        symlink_paths.add(normalized)

    return symlink_paths


def clone_gitignored(src_dir: Path, dst_dir: Path) -> list[dict]:
    """Clone all gitignored content. Returns manifest entries.

    Handles user-annotated symlink paths first, then COW clones the rest.
    """
    entries = []

    # 1. Parse annotations for paths that should be symlinked
    symlink_paths = parse_worktree_annotations(src_dir)

    # 2. Create symlinks for annotated paths
    for sym_path in sorted(symlink_paths):
        src_item = src_dir / sym_path
        dst_item = dst_dir / sym_path
        if not src_item.exists():
            continue
        if dst_item.exists() or dst_item.is_symlink():
            continue
        dst_item.parent.mkdir(parents=True, exist_ok=True)
        resolved = src_item.resolve()
        dst_item.symlink_to(resolved)
        entries.append({
            "path": sym_path,
            "type": "user_symlink",
            "source": str(resolved)
        })
        print(f"  Symlinking {sym_path} (user config)")

    # 3. Clone remaining ignored paths (skip those under symlinked dirs)
    ignored_paths = get_gitignored_paths(src_dir)
    for rel_path, is_dir_hint in ignored_paths:
        src_item = src_dir / rel_path
        dst_item = dst_dir / rel_path

        # Skip if this path is under a user-symlinked directory
        rel_str = str(rel_path)
        if any(rel_str == sp or rel_str.startswith(sp + "/") for sp in symlink_paths):
            continue

        if dst_item.exists() or dst_item.is_symlink():
            continue

        # Ensure parent directory exists
        dst_item.parent.mkdir(parents=True, exist_ok=True)

        # Resolve source (follows symlinks for gitignored symlinks)
        resolved_source = src_item.resolve()

        if src_item.is_dir():  # follows symlinks
            entry = {
                "path": str(rel_path),
                "type": "directory",
                "source": str(resolved_source)
            }
            print(f"  Cloning {rel_path} (gitignored directory)")
            dst_item.mkdir(parents=True, exist_ok=True)
            local_count, cloud_count = smart_copy_dir(src_item, dst_item, str(rel_path))
            entry["local_files"] = local_count
            entry["cloud_files"] = cloud_count
            entries.append(entry)

        elif src_item.is_file():  # follows symlinks
            if is_dataless(src_item):
                entry = {
                    "path": str(rel_path),
                    "type": "cloud_symlink",
                    "source": str(resolved_source)
                }
                print(f"  Symlinking {rel_path} (cloud file)")
                dst_item.symlink_to(resolved_source)
            else:
                entry = {
                    "path": str(rel_path),
                    "type": "cow_clone",
                    "source": str(resolved_source)
                }
                print(f"  COW cloning {rel_path} (gitignored file)")
                cow_copy(src_item, dst_item)
            entries.append(entry)

    return entries


def clone_symlink_targets(
    src_dir: Path,
    dst_dir: Path,
    rel_path: str = ".",
    repo_root: Path | None = None,
) -> list[dict]:
    """Clone tracked symlink targets (not gitignored items).

    Only handles git-tracked symlinks that point to directories or files
    outside the repo. Returns manifest entries.
    """
    if repo_root is None:
        repo_root = src_dir

    entries = []
    try:
        items = list(src_dir.iterdir())
    except PermissionError:
        return entries

    for item in items:
        name = item.name

        # Skip hidden files/dirs (like .git)
        if name.startswith("."):
            continue

        dst_item = dst_dir / name
        item_rel = name if rel_path == "." else f"{rel_path}/{name}"

        if item.is_symlink():
            # Handle tracked symlinks only
            if is_git_tracked(item_rel):
                try:
                    target = item.resolve()
                except (OSError, RuntimeError) as e:
                    print(f"  Skipping {item_rel} (cannot resolve symlink: {e})")
                    continue

                # Keep git-tracked symlinks that point within the same repo.
                # Git already materializes these correctly in each worktree.
                if is_within_repo(target, repo_root):
                    print(f"  Keeping {item_rel} as symlink (target in same repo)")
                    continue

                if target.is_dir():
                    # Directory symlink: create real dir and clone contents
                    print(f"  Cloning {item_rel} (tracked symlink -> {target})")
                    if dst_item.is_symlink() or dst_item.is_file():
                        dst_item.unlink()
                    dst_item.mkdir(parents=True, exist_ok=True)
                    local_count, cloud_count = smart_copy_dir(target, dst_item, item_rel)
                    entries.append({
                        "path": item_rel,
                        "type": "directory",
                        "source": str(target),
                        "local_files": local_count,
                        "cloud_files": cloud_count
                    })
                elif target.is_file():
                    # File symlink: COW clone or symlink based on cloud status
                    if dst_item.exists() or dst_item.is_symlink():
                        dst_item.unlink()
                    if is_dataless(target):
                        print(f"  Symlinking {item_rel} (cloud file)")
                        dst_item.symlink_to(target)
                        entries.append({
                            "path": item_rel,
                            "type": "cloud_symlink",
                            "source": str(target)
                        })
                    else:
                        print(f"  COW cloning {item_rel} (tracked symlink)")
                        cow_copy(target, dst_item)
                        entries.append({
                            "path": item_rel,
                            "type": "cow_clone",
                            "source": str(target)
                        })

        elif item.is_dir() and dst_item.is_dir():
            # Regular directory - recurse to find tracked symlinks inside
            entries.extend(clone_symlink_targets(item, dst_item, item_rel, repo_root))

    return entries


def main():
    parser = argparse.ArgumentParser(
        description="Create a sandboxed git worktree with COW clones"
    )
    parser.add_argument("-b", action="store_true", help="Create new branch")
    parser.add_argument(
        "--deny-sandbox-bypass", action="store_true",
        help="Deny agents from using dangerouslyDisableSandbox"
    )
    parser.add_argument("branch", help="Branch name")
    parser.add_argument("worktree_path", nargs="?", help="Worktree path (optional)")
    args = parser.parse_args()

    # Verify we're in a git repository
    try:
        subprocess.run(["git", "rev-parse", "--git-dir"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("Error: Not in a git repository", file=sys.stderr)
        sys.exit(1)

    # Validate branch name
    if not re.match(r"^[a-zA-Z0-9/_.-]+$", args.branch):
        print("Error: Invalid branch name. Use only alphanumeric, /, -, _, .", file=sys.stderr)
        sys.exit(1)

    # Get paths
    main_worktree = Path.cwd()
    repo_name = main_worktree.name
    branch_safe = args.branch.replace("/", "-")

    if args.worktree_path:
        worktree_path = Path(args.worktree_path).resolve()
    else:
        worktree_path = main_worktree.parent / f"{repo_name}-{branch_safe}"

    print(f"Creating worktree at: {worktree_path}")
    print(f"Branch: {args.branch}")
    print(f"Main worktree: {main_worktree}")

    # 1. Create git worktree
    cmd = ["git", "worktree", "add", str(worktree_path)]
    if args.b:
        cmd.extend(["-b", args.branch])
    else:
        cmd.append(args.branch)

    subprocess.run(cmd, check=True)

    # 2. Clone non-git-trackable content and build manifest
    manifest = {"version": 1, "entries": []}

    print("Cloning gitignored content...")
    manifest["entries"].extend(clone_gitignored(main_worktree, worktree_path))

    print("Cloning tracked symlink targets...")
    manifest["entries"].extend(clone_symlink_targets(main_worktree, worktree_path))

    # Write manifest
    manifest_path = worktree_path / ".worktree-manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  Wrote manifest ({len(manifest['entries'])} entries)")

    # 3. Configure sandbox settings
    print("Configuring sandbox...")
    script_dir = Path(__file__).parent
    sandbox_args = [sys.executable, str(script_dir / "configure_sandbox.py"), str(worktree_path)]
    if args.deny_sandbox_bypass:
        sandbox_args.append("--deny-sandbox-bypass")
    subprocess.run(sandbox_args, check=True)

    print()
    print(f"Worktree created successfully at {worktree_path}")
    print("Sandbox enabled - auto-execute within worktree, permission required outside")
    print()
    print("Directory structure:")
    subprocess.run(["ls", "-la", str(worktree_path)], check=False)


if __name__ == "__main__":
    main()
