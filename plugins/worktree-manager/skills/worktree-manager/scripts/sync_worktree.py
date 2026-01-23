#!/usr/bin/env python3
"""
Sync files from worktree back to original location or delete them.

Actions:
  - delete: Remove files from worktree (discard changes)
  - overwrite: Copy to original location, replacing existing files
  - rename: Copy with suffix to avoid conflicts

Usage:
    # From diff JSON output
    python diff_worktree.py /path/to/worktree --json > changes.json
    python sync_worktree.py --from-json changes.json --action overwrite

    # Specific files
    python sync_worktree.py --worktree /path/to/worktree \
        --files Output/Analysis/result.csv Notes/summary.md \
        --action rename --suffix "_worktree"

    # Interactive mode (with diff JSON)
    python sync_worktree.py --from-json changes.json --interactive
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal


Action = Literal["delete", "overwrite", "rename"]


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
    """Find symlinked directories in main worktree."""
    symlinked = {}
    for item in main_worktree.iterdir():
        if item.is_symlink() and item.is_dir():
            target = item.resolve()
            if target.exists():
                symlinked[item.name] = target
    return symlinked


def resolve_share_path(
    worktree_path: Path,
    relative_path: str,
    directory: str,
    symlinked_dirs: dict[str, Path],
) -> Path:
    """Convert worktree file path to corresponding share path."""
    share_dir = symlinked_dirs.get(directory)
    if not share_dir:
        raise ValueError(f"Directory '{directory}' is not a symlinked directory")
    return share_dir / relative_path


def generate_rename_suffix(suffix: str | None, timestamp: bool = False) -> str:
    """Generate suffix for renamed files."""
    if suffix:
        return suffix
    if timestamp:
        return f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return "_worktree"


def rename_path(path: Path, suffix: str) -> Path:
    """Add suffix to filename before extension."""
    stem = path.stem
    ext = path.suffix
    return path.with_name(f"{stem}{suffix}{ext}")


def process_file(
    worktree_file: Path,
    share_file: Path | None,
    action: Action,
    suffix: str,
    dry_run: bool = False,
    verbose: bool = True,
) -> bool:
    """
    Process a single file according to action.
    Returns True if successful.

    Actions:
    - delete: Remove the file from worktree
    - overwrite: Copy worktree file to share, replacing existing
    - rename: Copy worktree file to share with suffix
    """
    # Skip symlinks - they're shared by design, nothing to sync
    if worktree_file.is_symlink():
        if verbose:
            print(f"  SKIP (symlink): {worktree_file}")
        return True

    try:
        if action == "delete":
            if verbose:
                print(f"  DELETE: {worktree_file}")
            if not dry_run:
                worktree_file.unlink()
            return True

        elif action == "overwrite":
            if share_file is None:
                raise ValueError("share_file required for overwrite action")
            if verbose:
                print(f"  OVERWRITE: {worktree_file} -> {share_file}")
            if not dry_run:
                share_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(worktree_file, share_file)
            return True

        elif action == "rename":
            if share_file is None:
                raise ValueError("share_file required for rename action")
            renamed = rename_path(share_file, suffix)
            if verbose:
                print(f"  RENAME: {worktree_file} -> {renamed}")
            if not dry_run:
                renamed.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(worktree_file, renamed)
            return True

        return False

    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return False


def process_from_json(
    json_path: Path,
    action: Action,
    suffix: str,
    status_filter: list[str] | None = None,
    dry_run: bool = False,
    verbose: bool = True,
) -> tuple[int, int]:
    """
    Process files from diff_worktree.py JSON output.
    Returns (success_count, failure_count).
    """
    with open(json_path) as f:
        data = json.load(f)

    worktree_path = Path(data["worktree_path"])
    main_worktree = get_main_worktree(worktree_path)
    symlinked_dirs = get_symlinked_dirs(main_worktree)

    changes = data.get("changes", [])

    # Filter by status if specified
    if status_filter:
        changes = [c for c in changes if c["status"] in status_filter]

    if not changes:
        print("No files to process.")
        return 0, 0

    success = 0
    failure = 0

    for change in changes:
        worktree_file = Path(change["worktree_path"])

        # Determine share path
        if change["share_path"]:
            share_file = Path(change["share_path"])
        else:
            # New file - compute share path
            share_file = resolve_share_path(
                worktree_path,
                change["relative_path"],
                change["directory"],
                symlinked_dirs,
            )

        if process_file(worktree_file, share_file, action, suffix, dry_run, verbose):
            success += 1
        else:
            failure += 1

    return success, failure


def process_files(
    worktree_path: Path,
    files: list[str],
    action: Action,
    suffix: str,
    dry_run: bool = False,
    verbose: bool = True,
) -> tuple[int, int]:
    """
    Process specific files by relative path.
    Files should be relative to worktree root (e.g., "Output/Analysis/result.csv").
    """
    main_worktree = get_main_worktree(worktree_path)
    symlinked_dirs = get_symlinked_dirs(main_worktree)

    success = 0
    failure = 0

    for file_path in files:
        parts = Path(file_path).parts
        if not parts:
            continue

        directory = parts[0]
        relative_path = str(Path(*parts[1:])) if len(parts) > 1 else ""

        worktree_file = worktree_path / file_path

        if not worktree_file.exists():
            print(f"  SKIP (not found): {file_path}", file=sys.stderr)
            failure += 1
            continue

        # Determine share path
        if directory in symlinked_dirs:
            share_file = symlinked_dirs[directory] / relative_path
        else:
            print(f"  SKIP (not in symlinked dir): {file_path}", file=sys.stderr)
            failure += 1
            continue

        if process_file(worktree_file, share_file, action, suffix, dry_run, verbose):
            success += 1
        else:
            failure += 1

    return success, failure


def interactive_mode(json_path: Path, suffix: str, dry_run: bool = False):
    """
    Interactive mode: show files and let user choose action for each.
    """
    with open(json_path) as f:
        data = json.load(f)

    changes = [c for c in data.get("changes", []) if c["status"] in ("new", "modified")]

    if not changes:
        print("No new or modified files to process.")
        return

    worktree_path = Path(data["worktree_path"])
    main_worktree = get_main_worktree(worktree_path)
    symlinked_dirs = get_symlinked_dirs(main_worktree)

    print(f"Found {len(changes)} changed files.\n")
    print("Actions: [d]elete, [o]verwrite, [r]ename, [s]kip, [q]uit")
    print("         [D]elete all, [O]verwrite all, [R]ename all, [S]kip all\n")

    batch_action = None

    for i, change in enumerate(changes, 1):
        status = change["status"].upper()
        rel_path = f"{change['directory']}/{change['relative_path']}"

        print(f"[{i}/{len(changes)}] {status}: {rel_path}")

        if batch_action:
            action = batch_action
            print(f"  -> {action} (batch)")
        else:
            while True:
                choice = input("  Action [d/o/r/s/q/D/O/R/S]: ").strip()
                choice_lower = choice.lower()
                # Check uppercase (batch) commands first
                if choice == "D":
                    action = "delete"
                    batch_action = "delete"
                    break
                elif choice == "O":
                    action = "overwrite"
                    batch_action = "overwrite"
                    break
                elif choice == "R":
                    action = "rename"
                    batch_action = "rename"
                    break
                elif choice == "S":
                    action = "skip"
                    batch_action = "skip"
                    break
                # Then check lowercase (single) commands
                elif choice_lower in ("d", "delete"):
                    action = "delete"
                    break
                elif choice_lower in ("o", "overwrite"):
                    action = "overwrite"
                    break
                elif choice_lower in ("r", "rename"):
                    action = "rename"
                    break
                elif choice_lower in ("s", "skip", ""):
                    action = "skip"
                    break
                elif choice_lower == "q":
                    print("Quit.")
                    return
                else:
                    print("  Invalid choice. Try again.")

        if action == "skip":
            continue

        worktree_file = Path(change["worktree_path"])
        if change["share_path"]:
            share_file = Path(change["share_path"])
        else:
            share_file = resolve_share_path(
                worktree_path,
                change["relative_path"],
                change["directory"],
                symlinked_dirs,
            )

        process_file(worktree_file, share_file, action, suffix, dry_run, verbose=True)

    print("\nDone.")


def main():
    parser = argparse.ArgumentParser(
        description="Sync files from worktree back to original location",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all changes from diff output
  python sync_worktree.py --from-json changes.json --action overwrite

  # Only process new files
  python sync_worktree.py --from-json changes.json --action overwrite --status new

  # Rename to avoid conflicts
  python sync_worktree.py --from-json changes.json --action rename --suffix "_backup"

  # Interactive mode
  python sync_worktree.py --from-json changes.json --interactive

  # Specific files
  python sync_worktree.py --worktree /path/to/worktree \\
      --files Output/result.csv Notes/log.txt \\
      --action delete
        """,
    )

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--from-json", type=Path,
                             help="JSON file from diff_worktree.py")
    input_group.add_argument("--worktree", type=Path,
                             help="Worktree path (use with --files)")

    parser.add_argument("--files", nargs="+",
                        help="Specific files to process (relative to worktree)")

    # Action
    parser.add_argument("--action", choices=["delete", "overwrite", "rename"],
                        help="Action to perform (required unless --interactive)")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Interactive mode: choose action for each file")

    # Options
    parser.add_argument("--status", nargs="+", choices=["new", "modified", "unchanged"],
                        help="Only process files with these statuses (for --from-json)")
    parser.add_argument("--suffix", default="_worktree",
                        help="Suffix for renamed files (default: _worktree)")
    parser.add_argument("--timestamp-suffix", action="store_true",
                        help="Use timestamp as suffix instead")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Show what would be done without actually doing it")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress verbose output")

    args = parser.parse_args()

    # Validate arguments
    if args.worktree and not args.files:
        parser.error("--worktree requires --files")

    if not args.interactive and not args.action:
        parser.error("Either --action or --interactive is required")

    # Generate suffix
    suffix = generate_rename_suffix(
        args.suffix if not args.timestamp_suffix else None,
        timestamp=args.timestamp_suffix,
    )

    verbose = not args.quiet

    if args.dry_run:
        print("DRY RUN - no changes will be made\n")

    if args.interactive:
        if not args.from_json:
            parser.error("--interactive requires --from-json")
        interactive_mode(args.from_json, suffix, args.dry_run)
    elif args.from_json:
        success, failure = process_from_json(
            args.from_json,
            args.action,
            suffix,
            args.status,
            args.dry_run,
            verbose,
        )
        print(f"\nProcessed: {success} success, {failure} failed")
    else:
        success, failure = process_files(
            args.worktree.resolve(),
            args.files,
            args.action,
            suffix,
            args.dry_run,
            verbose,
        )
        print(f"\nProcessed: {success} success, {failure} failed")


if __name__ == "__main__":
    main()
