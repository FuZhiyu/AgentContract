#!/usr/bin/env python3
"""
Compare worktree files against the original share folder.

Identifies files that are new or modified in the worktree's COW-cloned directories
compared to the original share folder (resolved from symlinks in main worktree).

Usage:
    python diff_worktree.py <worktree-path> [--json] [--include-unmodified]

Output:
    Lists files with their status (new, modified, unchanged) and paths.
    With --json: outputs machine-readable JSON for scripting.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal


@dataclass
class FileChange:
    """Represents a file change between worktree and share."""
    status: Literal["new", "modified", "unchanged"]
    worktree_path: str  # Absolute path in worktree
    share_path: str | None  # Absolute path in share (None if new)
    relative_path: str  # Path relative to the COW-cloned directory
    directory: str  # Which directory (e.g., "Output", "Data", "Notes")
    size_worktree: int
    size_share: int | None
    mtime_worktree: float
    mtime_share: float | None


def get_main_worktree(worktree_path: Path) -> Path:
    """Get the main worktree path using git."""
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.split("\n"):
        if line.startswith("worktree "):
            return Path(line.split(" ", 1)[1])
    raise RuntimeError("Could not find main worktree")


def get_symlinked_dirs(main_worktree: Path) -> dict[str, Path]:
    """
    Find directories in main worktree that are symlinks.
    Returns mapping of directory name -> resolved target path.
    Used as legacy fallback when no manifest exists.
    """
    symlinked = {}
    for item in main_worktree.iterdir():
        if item.is_symlink() and item.is_dir():
            target = item.resolve()
            if target.exists():
                symlinked[item.name] = target
    return symlinked


def get_manifest_entries(worktree_path: Path) -> list[dict]:
    """Read worktree manifest. Falls back to legacy symlink detection."""
    manifest_path = worktree_path / ".worktree-manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            return json.load(f).get("entries", [])
    # Legacy fallback: detect symlinked dirs in main worktree
    main_worktree = get_main_worktree(worktree_path)
    return [
        {"path": name, "type": "directory", "source": str(target)}
        for name, target in get_symlinked_dirs(main_worktree).items()
    ]


def diff_file(
    worktree_file: Path,
    source_file: Path,
    rel_path: str,
    dir_name: str,
    include_unmodified: bool = False,
    use_hash: bool = False,
) -> FileChange | None:
    """Compare a single COW-cloned file against its source."""
    # Skip symlinks (cloud files that weren't modified)
    if worktree_file.is_symlink():
        return None
    if not worktree_file.exists():
        return None

    wt_stat = worktree_file.stat()

    if not source_file.exists():
        return FileChange(
            status="new",
            worktree_path=str(worktree_file),
            share_path=None,
            relative_path=rel_path,
            directory=dir_name,
            size_worktree=wt_stat.st_size,
            size_share=None,
            mtime_worktree=wt_stat.st_mtime,
            mtime_share=None,
        )

    is_same = compare_files(worktree_file, source_file, use_hash)
    if not is_same:
        sh_stat = source_file.stat()
        return FileChange(
            status="modified",
            worktree_path=str(worktree_file),
            share_path=str(source_file),
            relative_path=rel_path,
            directory=dir_name,
            size_worktree=wt_stat.st_size,
            size_share=sh_stat.st_size,
            mtime_worktree=wt_stat.st_mtime,
            mtime_share=sh_stat.st_mtime,
        )
    elif include_unmodified:
        sh_stat = source_file.stat()
        return FileChange(
            status="unchanged",
            worktree_path=str(worktree_file),
            share_path=str(source_file),
            relative_path=rel_path,
            directory=dir_name,
            size_worktree=wt_stat.st_size,
            size_share=sh_stat.st_size,
            mtime_worktree=wt_stat.st_mtime,
            mtime_share=sh_stat.st_mtime,
        )
    return None


def file_hash(path: Path, chunk_size: int = 65536) -> str:
    """Compute MD5 hash of file for content comparison."""
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compare_files(worktree_file: Path, share_file: Path, use_hash: bool = False) -> bool:
    """
    Compare two files. Returns True if they are identical.
    Uses size + mtime for quick comparison, optionally hash for accuracy.
    """
    wt_stat = worktree_file.stat()
    sh_stat = share_file.stat()

    # Quick check: different size means definitely different
    if wt_stat.st_size != sh_stat.st_size:
        return False

    # If sizes match and we're not using hash, check mtime
    if not use_hash:
        # Files are "same" if size matches and mtimes are within tolerance.
        # COW clone preserves mtime, so if either file's mtime differs
        # significantly, one of them was modified.
        mtime_diff = abs(wt_stat.st_mtime - sh_stat.st_mtime)
        return mtime_diff <= 1  # 1 second tolerance

    # Hash comparison for accuracy
    return file_hash(worktree_file) == file_hash(share_file)


def diff_directory(
    worktree_dir: Path,
    share_dir: Path,
    dir_name: str,
    include_unmodified: bool = False,
    use_hash: bool = False,
) -> list[FileChange]:
    """
    Compare a worktree directory against its share counterpart.
    Skips symlinks that point to the share (cloud files we didn't COW clone).
    """
    changes = []

    # Walk the worktree directory, but don't follow symlinks
    for root, dirs, files in os.walk(worktree_dir, followlinks=False):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        # Skip directories that are symlinks (they point to share)
        dirs[:] = [d for d in dirs if not (Path(root) / d).is_symlink()]

        root_path = Path(root)
        rel_root = root_path.relative_to(worktree_dir)
        share_root = share_dir / rel_root

        for filename in files:
            # Skip hidden files
            if filename.startswith("."):
                continue

            worktree_file = root_path / filename
            share_file = share_root / filename
            rel_path = str(rel_root / filename)

            # Skip if either side is a symlink - symlinks are shared by design,
            # there's nothing to diff (they point to the same file or are
            # intentionally linked elsewhere)
            if worktree_file.is_symlink() or (share_file.exists() and share_file.is_symlink()):
                continue

            wt_stat = worktree_file.stat()

            if not share_file.exists():
                # New file
                changes.append(FileChange(
                    status="new",
                    worktree_path=str(worktree_file),
                    share_path=None,
                    relative_path=rel_path,
                    directory=dir_name,
                    size_worktree=wt_stat.st_size,
                    size_share=None,
                    mtime_worktree=wt_stat.st_mtime,
                    mtime_share=None,
                ))
            else:
                sh_stat = share_file.stat()
                is_same = compare_files(worktree_file, share_file, use_hash)

                if not is_same:
                    changes.append(FileChange(
                        status="modified",
                        worktree_path=str(worktree_file),
                        share_path=str(share_file),
                        relative_path=rel_path,
                        directory=dir_name,
                        size_worktree=wt_stat.st_size,
                        size_share=sh_stat.st_size,
                        mtime_worktree=wt_stat.st_mtime,
                        mtime_share=sh_stat.st_mtime,
                    ))
                elif include_unmodified:
                    changes.append(FileChange(
                        status="unchanged",
                        worktree_path=str(worktree_file),
                        share_path=str(share_file),
                        relative_path=rel_path,
                        directory=dir_name,
                        size_worktree=wt_stat.st_size,
                        size_share=sh_stat.st_size,
                        mtime_worktree=wt_stat.st_mtime,
                        mtime_share=sh_stat.st_mtime,
                    ))

    return changes


def format_size(size: int) -> str:
    """Format file size for human readability."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def main():
    parser = argparse.ArgumentParser(description="Compare worktree files against share folder")
    parser.add_argument("worktree_path", help="Path to the worktree")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--include-unmodified", action="store_true",
                        help="Include unchanged files in output")
    parser.add_argument("--use-hash", action="store_true",
                        help="Use content hash for accurate comparison (slower)")
    parser.add_argument("--dirs", nargs="+",
                        help="Specific directories to check (default: auto-detect symlinked dirs)")
    args = parser.parse_args()

    worktree_path = Path(args.worktree_path).resolve()
    if not worktree_path.exists():
        print(f"Error: Worktree path does not exist: {worktree_path}", file=sys.stderr)
        sys.exit(1)

    # Get main worktree
    main_worktree = get_main_worktree(worktree_path)

    # Get manifest entries (falls back to legacy symlink detection)
    entries = get_manifest_entries(worktree_path)

    if not entries:
        print("No manifest entries or symlinked directories found", file=sys.stderr)
        sys.exit(0)

    # Filter to specific dirs if requested
    if args.dirs:
        entries = [e for e in entries if e["path"].split("/")[0] in args.dirs]

    all_changes: list[FileChange] = []

    for entry in entries:
        entry_path = entry["path"]
        source = Path(entry["source"])
        worktree_item = worktree_path / entry_path
        entry_type = entry.get("type", "directory")

        if entry_type == "directory":
            if worktree_item.exists():
                changes = diff_directory(
                    worktree_item,
                    source,
                    entry_path,
                    include_unmodified=args.include_unmodified,
                    use_hash=args.use_hash,
                )
                all_changes.extend(changes)

        elif entry_type == "cow_clone":
            change = diff_file(
                worktree_item,
                source,
                entry_path,
                entry_path,
                include_unmodified=args.include_unmodified,
                use_hash=args.use_hash,
            )
            if change:
                all_changes.append(change)

        elif entry_type == "cloud_symlink":
            # If still a symlink, unmodified. If real file, was modified.
            if not worktree_item.is_symlink() and worktree_item.exists():
                change = diff_file(
                    worktree_item,
                    source,
                    entry_path,
                    entry_path,
                    include_unmodified=args.include_unmodified,
                    use_hash=args.use_hash,
                )
                if change:
                    all_changes.append(change)

        elif entry_type == "user_symlink":
            continue  # Shared state, no diff needed

    # Build source map for JSON output
    source_map = {e["path"]: e["source"] for e in entries}

    if args.json:
        output = {
            "worktree_path": str(worktree_path),
            "main_worktree": str(main_worktree),
            "manifest_entries": entries,
            "changes": [asdict(c) for c in all_changes],
            "summary": {
                "new": len([c for c in all_changes if c.status == "new"]),
                "modified": len([c for c in all_changes if c.status == "modified"]),
                "unchanged": len([c for c in all_changes if c.status == "unchanged"]),
            }
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        print(f"Worktree: {worktree_path}")
        print(f"Main worktree: {main_worktree}")
        entry_names = [e["path"] for e in entries if e.get("type") != "user_symlink"]
        print(f"Comparing: {', '.join(entry_names)}")
        print()

        new_files = [c for c in all_changes if c.status == "new"]
        modified_files = [c for c in all_changes if c.status == "modified"]

        if new_files:
            print(f"NEW FILES ({len(new_files)}):")
            for c in sorted(new_files, key=lambda x: x.relative_path):
                print(f"  + {c.directory}/{c.relative_path} ({format_size(c.size_worktree)})")
            print()

        if modified_files:
            print(f"MODIFIED FILES ({len(modified_files)}):")
            for c in sorted(modified_files, key=lambda x: x.relative_path):
                size_info = f"{format_size(c.size_share)} -> {format_size(c.size_worktree)}"
                print(f"  M {c.directory}/{c.relative_path} ({size_info})")
            print()

        if not new_files and not modified_files:
            print("No new or modified files found.")
        else:
            print(f"Summary: {len(new_files)} new, {len(modified_files)} modified")


if __name__ == "__main__":
    main()
