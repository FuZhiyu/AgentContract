#!/usr/bin/env python3
"""Create a sandboxed git worktree with COW clones for symlink targets.

Usage: create_worktree.py [-b] [--deny-sandbox-bypass] <branch-name> [worktree-path]
"""

import argparse
import os
import re
import shutil
import subprocess
import stat
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


def is_gitignored(path: str) -> bool:
    """Check if path is gitignored."""
    result = subprocess.run(
        ["git", "check-ignore", "-q", path],
        capture_output=True
    )
    return result.returncode == 0


def clone_non_trackable(src_dir: Path, dst_dir: Path, rel_path: str = "."):
    """Clone non-git-trackable content: tracked symlink targets and gitignored items."""
    try:
        items = list(src_dir.iterdir())
    except PermissionError:
        return

    for item in items:
        name = item.name

        # Skip hidden files/dirs (like .git)
        if name.startswith("."):
            continue

        dst_item = dst_dir / name
        item_rel = name if rel_path == "." else f"{rel_path}/{name}"

        if item.is_symlink():
            # Handle symlink - clone if tracked or gitignored
            if is_git_tracked(item_rel) or is_gitignored(item_rel):
                try:
                    target = item.resolve()
                except (OSError, RuntimeError) as e:
                    # OSError: symlink target doesn't exist
                    # RuntimeError: circular symlink (infinite loop protection)
                    print(f"  Skipping {item_rel} (cannot resolve symlink: {e})")
                    continue

                if target.is_dir():
                    # Directory symlink: create real dir and clone contents
                    print(f"  Cloning {item_rel} (symlink -> {target})")
                    if dst_item.is_symlink() or dst_item.is_file():
                        dst_item.unlink()
                    dst_item.mkdir(parents=True, exist_ok=True)
                    smart_copy_dir(target, dst_item, item_rel)
                elif target.is_file():
                    # File symlink: COW clone or symlink based on cloud status
                    if dst_item.exists() or dst_item.is_symlink():
                        dst_item.unlink()
                    if is_dataless(target):
                        print(f"  Symlinking {item_rel} (cloud file)")
                        dst_item.symlink_to(target)
                    else:
                        print(f"  COW cloning {item_rel} (local file)")
                        cow_copy(target, dst_item)

        elif is_gitignored(item_rel):
            # Gitignored file/dir - clone if not already exists
            if not dst_item.exists():
                if item.is_dir():
                    print(f"  Cloning {item_rel} (gitignored)")
                    dst_item.mkdir(parents=True, exist_ok=True)
                    smart_copy_dir(item, dst_item, item_rel)
                elif item.is_file():
                    if is_dataless(item):
                        print(f"  Symlinking {item_rel} (gitignored, cloud)")
                        dst_item.symlink_to(item.resolve())
                    else:
                        print(f"  COW cloning {item_rel} (gitignored, local)")
                        cow_copy(item, dst_item)

        elif item.is_dir() and dst_item.is_dir():
            # Regular directory - recurse
            clone_non_trackable(item, dst_item, item_rel)


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

    # 2. COW clone non-git-trackable content
    print("Creating COW clones for non-git-trackable content...")
    clone_non_trackable(main_worktree, worktree_path)

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
