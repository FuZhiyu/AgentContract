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
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal

from worktree_discovery import (
    discover_managed_entries,
    get_gitignored_paths,
    get_main_worktree,
    promote_ignored_path_to_symlink_dir_root,
)


@dataclass
class FileChange:
    """Represents a file change between worktree and share."""
    status: Literal["new", "modified", "unchanged"]
    worktree_path: str  # Absolute path in worktree
    share_path: str | None  # Absolute path in share (None if new)
    target_path: str  # Absolute destination path for sync
    relative_path: str  # Path relative to the COW-cloned directory
    directory: str  # Managed entry path key
    size_worktree: int
    size_share: int | None
    mtime_worktree: float
    mtime_share: float | None


def diff_file(
    worktree_file: Path,
    source_file: Path,
    rel_path: str,
    dir_name: str,
    include_unmodified: bool = False,
    use_hash: bool = False,
) -> FileChange | None:
    """Compare a single managed file against its source."""
    # Symlink means this worktree still points to shared state.
    if worktree_file.is_symlink():
        return None
    if not worktree_file.exists():
        return None

    wt_stat = worktree_file.stat()

    # Source symlink + worktree real file => local override.
    if source_file.exists() and source_file.is_symlink():
        sh_stat = source_file.lstat()
        return FileChange(
            status="modified",
            worktree_path=str(worktree_file),
            share_path=str(source_file),
            target_path=str(source_file),
            relative_path=rel_path,
            directory=dir_name,
            size_worktree=wt_stat.st_size,
            size_share=sh_stat.st_size,
            mtime_worktree=wt_stat.st_mtime,
            mtime_share=sh_stat.st_mtime,
        )

    if not source_file.exists():
        return FileChange(
            status="new",
            worktree_path=str(worktree_file),
            share_path=None,
            target_path=str(source_file),
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
            target_path=str(source_file),
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
            target_path=str(source_file),
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
    if worktree_file.is_symlink() or share_file.is_symlink():
        return False

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
    Compare a worktree directory against its source counterpart.
    """
    changes = []

    # Walk the worktree directory, but don't follow symlinks
    for root, dirs, files in os.walk(worktree_dir, followlinks=False):
        # Skip internal VCS metadata directories only.
        # Hidden control files/dirs (e.g. ".env", ".config") are valid
        # non-git changes and must be detected.
        dirs[:] = [d for d in dirs if d != ".git"]
        # Skip directories that are symlinks (they point to share)
        dirs[:] = [d for d in dirs if not (Path(root) / d).is_symlink()]

        root_path = Path(root)
        rel_root = root_path.relative_to(worktree_dir)
        share_root = share_dir / rel_root

        for filename in files:
            # Skip internal VCS metadata files only.
            if filename == ".git":
                continue

            worktree_file = root_path / filename
            share_file = share_root / filename
            rel_path = str(rel_root / filename)

            # Symlink in worktree means shared state is still intact.
            if worktree_file.is_symlink():
                continue

            if not worktree_file.exists():
                continue

            wt_stat = worktree_file.stat()

            # Source symlink + worktree real file => local override.
            if share_file.exists() and share_file.is_symlink():
                sh_stat = share_file.lstat()
                changes.append(FileChange(
                    status="modified",
                    worktree_path=str(worktree_file),
                    share_path=str(share_file),
                    target_path=str(share_file),
                    relative_path=rel_path,
                    directory=dir_name,
                    size_worktree=wt_stat.st_size,
                    size_share=sh_stat.st_size,
                    mtime_worktree=wt_stat.st_mtime,
                    mtime_share=sh_stat.st_mtime,
                ))
                continue

            if not share_file.exists():
                # New file
                changes.append(FileChange(
                    status="new",
                    worktree_path=str(worktree_file),
                    share_path=None,
                    target_path=str(share_file),
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
                        target_path=str(share_file),
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
                        target_path=str(share_file),
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


def _is_under(base: str, maybe_child: str) -> bool:
    return maybe_child == base or maybe_child.startswith(base + "/")


def discover_union_entries(main_worktree: Path, worktree_path: Path) -> list[dict]:
    """Discover managed entries using union of main and target worktree ignored roots."""
    by_path = {entry["path"]: dict(entry) for entry in discover_managed_entries(main_worktree)}

    ignored_candidates = sorted(
        get_gitignored_paths(worktree_path),
        key=lambda x: (len(x[0].parts), 0 if x[1] else 1, str(x[0])),
    )
    ignored_dir_roots: list[str] = []

    for rel_path, is_dir_hint in ignored_candidates:
        promoted_path, promoted_dir_hint = promote_ignored_path_to_symlink_dir_root(worktree_path, rel_path)
        rel_str = str(promoted_path)
        is_dir_hint = is_dir_hint or promoted_dir_hint
        if rel_str in by_path:
            if is_dir_hint:
                ignored_dir_roots.append(rel_str)
            continue
        if any(_is_under(root, rel_str) for root in ignored_dir_roots):
            continue

        worktree_item = worktree_path / promoted_path
        if not (worktree_item.exists() or worktree_item.is_symlink()):
            continue

        if is_dir_hint or (worktree_item.is_dir() and not worktree_item.is_symlink()):
            entry_kind = "directory"
            ignored_dir_roots.append(rel_str)
        elif worktree_item.is_file():
            entry_kind = "file"
        else:
            continue

        by_path[rel_str] = {
            "path": rel_str,
            "source": str(main_worktree / promoted_path),
            "entry_kind": entry_kind,
            "shared_only": False,
            "origin": "worktree_ignored",
        }

    return [by_path[path] for path in sorted(by_path)]


def main():
    parser = argparse.ArgumentParser(description="Compare worktree files against share folder")
    parser.add_argument("worktree_path", help="Path to the worktree")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--include-unmodified", action="store_true",
                        help="Include unchanged files in output")
    parser.add_argument("--use-hash", action="store_true",
                        help="Use content hash for accurate comparison (slower)")
    parser.add_argument("--dirs", nargs="+",
                        help="Specific top-level directories to check (default: auto-detect)")
    args = parser.parse_args()

    worktree_path = Path(args.worktree_path).resolve()
    if not worktree_path.exists():
        print(f"Error: Worktree path does not exist: {worktree_path}", file=sys.stderr)
        sys.exit(1)

    # Get main worktree
    main_worktree = get_main_worktree(worktree_path)

    # Stateless entry discovery from current git/filesystem state.
    entries = discover_union_entries(main_worktree, worktree_path)

    if not entries:
        print("No managed entries found", file=sys.stderr)
        sys.exit(0)

    # Filter to specific dirs if requested
    if args.dirs:
        entries = [e for e in entries if e["path"].split("/")[0] in args.dirs]

    all_changes: list[FileChange] = []

    for entry in entries:
        entry_path = entry["path"]
        source = Path(entry["source"])
        worktree_item = worktree_path / entry_path
        entry_kind = entry.get("entry_kind", "directory")
        shared_only = bool(entry.get("shared_only", False))

        if shared_only:
            continue

        if entry_kind == "directory":
            if worktree_item.exists() and worktree_item.is_dir() and not worktree_item.is_symlink():
                changes = diff_directory(
                    worktree_item,
                    source,
                    entry_path,
                    include_unmodified=args.include_unmodified,
                    use_hash=args.use_hash,
                )
                all_changes.extend(changes)

        elif entry_kind == "file":
            change = diff_file(
                worktree_item,
                source,
                "",
                entry_path,
                include_unmodified=args.include_unmodified,
                use_hash=args.use_hash,
            )
            if change:
                all_changes.append(change)

    if args.json:
        output = {
            "worktree_path": str(worktree_path),
            "main_worktree": str(main_worktree),
            "discovered_entries": entries,
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
        entry_names = [e["path"] for e in entries if not e.get("shared_only", False)]
        print(f"Comparing: {', '.join(entry_names)}")
        print()

        new_files = [c for c in all_changes if c.status == "new"]
        modified_files = [c for c in all_changes if c.status == "modified"]

        if new_files:
            print(f"NEW FILES ({len(new_files)}):")
            for c in sorted(new_files, key=lambda x: x.relative_path):
                display_path = c.directory if not c.relative_path else f"{c.directory}/{c.relative_path}"
                print(f"  + {display_path} ({format_size(c.size_worktree)})")
            print()

        if modified_files:
            print(f"MODIFIED FILES ({len(modified_files)}):")
            for c in sorted(modified_files, key=lambda x: x.relative_path):
                size_info = f"{format_size(c.size_share)} -> {format_size(c.size_worktree)}"
                display_path = c.directory if not c.relative_path else f"{c.directory}/{c.relative_path}"
                print(f"  M {display_path} ({size_info})")
            print()

        if not new_files and not modified_files:
            print("No new or modified files found.")
        else:
            print(f"Summary: {len(new_files)} new, {len(modified_files)} modified")


if __name__ == "__main__":
    main()
