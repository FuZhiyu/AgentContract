#!/usr/bin/env python3
"""Stateless discovery of managed non-git worktree paths."""

from __future__ import annotations

import subprocess
from pathlib import Path


def get_main_worktree(worktree_path: Path) -> Path:
    """Get the main worktree path for a git repository."""
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            return Path(line.split(" ", 1)[1])
    raise RuntimeError("Could not find main worktree")


def normalize_annotation_pattern(pattern: str) -> str:
    """Normalize .gitignore annotation patterns to a concrete repo path."""
    normalized = pattern.strip().rstrip("/")
    if "/**" in normalized:
        normalized = normalized.split("/**")[0]
    elif "/*" in normalized:
        normalized = normalized.split("/*")[0]
    return normalized


def parse_worktree_annotations(repo_root: Path) -> set[str]:
    """Parse '# worktree:symlink' annotations from .gitignore."""
    symlink_paths: set[str] = set()
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.exists():
        return symlink_paths

    for line in gitignore_path.read_text().splitlines():
        if "# worktree:symlink" not in line:
            continue
        pattern = line.split("#", 1)[0].strip()
        if not pattern:
            continue
        normalized = normalize_annotation_pattern(pattern)
        if normalized:
            symlink_paths.add(normalized)
    return symlink_paths


def get_gitignored_paths(repo_root: Path) -> list[tuple[Path, bool]]:
    """Get ignored paths from git with directory hints."""
    result = subprocess.run(
        ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "--directory"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if not result.stdout.strip():
        return []
    paths: list[tuple[Path, bool]] = []
    for line in result.stdout.strip().splitlines():
        is_dir = line.endswith("/")
        paths.append((Path(line.rstrip("/")), is_dir))
    return paths


def is_within_repo(target: Path, repo_root: Path) -> bool:
    """Return True if target is inside repo_root."""
    try:
        target.resolve().relative_to(repo_root.resolve())
        return True
    except ValueError:
        return False


def _is_under(base: str, maybe_child: str) -> bool:
    return maybe_child == base or maybe_child.startswith(base + "/")


def _is_shared_only(path: str, shared_roots: set[str]) -> bool:
    return any(_is_under(root, path) for root in shared_roots)


def _entry_kind_for_source(source: Path) -> str | None:
    if source.is_dir():
        return "directory"
    if source.is_file():
        return "file"
    return None


def promote_ignored_path_to_symlink_dir_root(repo_root: Path, rel_path: Path) -> tuple[Path, bool]:
    """Promote ignored child paths under symlinked directories to directory root entries.

    Returns (promoted_path, promoted_is_directory_hint). If no symlink-dir ancestor
    exists, returns (rel_path, False).
    """
    current = rel_path
    seen: set[Path] = set()
    while True:
        if current in seen:
            break
        seen.add(current)

        item = repo_root / current
        if item.is_symlink():
            try:
                resolved = item.resolve()
            except (OSError, RuntimeError):
                break
            if resolved.exists() and resolved.is_dir():
                return current, True

        parent = current.parent
        if parent == current or str(parent) in ("", "."):
            break
        current = parent

    return rel_path, False


def _tracked_external_symlink_paths(repo_root: Path) -> list[str]:
    """Return repo-relative paths that are tracked symlinks."""
    result = subprocess.run(
        ["git", "ls-files", "-s"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    paths: list[str] = []
    for line in result.stdout.splitlines():
        # Format: "<mode> <hash> <stage>\t<path>"
        if "\t" not in line:
            continue
        meta, rel_path = line.split("\t", 1)
        mode = meta.split(" ", 1)[0]
        if mode == "120000":
            paths.append(rel_path)
    return paths


def discover_managed_entries(main_worktree: Path) -> list[dict]:
    """Discover managed paths without reading manifest state."""
    shared_roots = parse_worktree_annotations(main_worktree)
    by_path: dict[str, dict] = {}
    priority: dict[str, int] = {}

    def add_entry(path: str, source: Path, origin_priority: int) -> None:
        if not path:
            return
        kind = _entry_kind_for_source(source)
        if kind is None:
            return
        if path in priority and priority[path] > origin_priority:
            return
        by_path[path] = {
            "path": path,
            "source": str(source),
            "entry_kind": kind,
            "shared_only": _is_shared_only(path, shared_roots),
        }
        priority[path] = origin_priority

    # 1) Gitignored entries
    # Collapse child entries under ignored directories to avoid redundant
    # per-file discovery/scanning on large ignored trees.
    ignored_candidates = sorted(
        get_gitignored_paths(main_worktree),
        key=lambda x: (len(x[0].parts), 0 if x[1] else 1, str(x[0])),
    )
    ignored_dir_roots: list[str] = []

    for rel_path, is_dir_hint in ignored_candidates:
        promoted_path, promoted_dir_hint = promote_ignored_path_to_symlink_dir_root(main_worktree, rel_path)
        rel_str = str(promoted_path)
        is_dir_hint = is_dir_hint or promoted_dir_hint
        if any(_is_under(root, rel_str) for root in ignored_dir_roots):
            continue

        src_item = main_worktree / promoted_path
        if not (src_item.exists() or src_item.is_symlink()):
            continue
        try:
            resolved = src_item.resolve()
        except (OSError, RuntimeError):
            continue
        if not resolved.exists():
            continue
        add_entry(rel_str, resolved, origin_priority=30)

        if is_dir_hint:
            ignored_dir_roots.append(rel_str)

    # 2) Tracked external symlinks (including nested)
    for rel_path in _tracked_external_symlink_paths(main_worktree):
        src_item = main_worktree / rel_path
        if not src_item.is_symlink():
            continue
        try:
            resolved = src_item.resolve()
        except (OSError, RuntimeError):
            continue
        if not resolved.exists():
            continue
        if is_within_repo(resolved, main_worktree):
            continue
        add_entry(rel_path, resolved, origin_priority=20)

    # 3) Top-level symlink safety net
    for item in main_worktree.iterdir():
        if item.name == ".git":
            continue
        if not item.is_symlink():
            continue
        try:
            resolved = item.resolve()
        except (OSError, RuntimeError):
            continue
        if not resolved.exists():
            continue
        add_entry(item.name, resolved, origin_priority=10)

    # 4) Ensure annotation roots are explicitly represented and shared_only
    for root in sorted(shared_roots):
        src_item = main_worktree / root
        if not (src_item.exists() or src_item.is_symlink()):
            continue
        try:
            resolved = src_item.resolve()
        except (OSError, RuntimeError):
            continue
        if not resolved.exists():
            continue
        add_entry(root, resolved, origin_priority=40)
        by_path[root]["shared_only"] = True

    return [by_path[path] for path in sorted(by_path)]


def build_source_map(main_worktree: Path, include_shared: bool = False) -> dict[str, Path]:
    """Build path->source map from stateless discovery."""
    source_map: dict[str, Path] = {}
    for entry in discover_managed_entries(main_worktree):
        if entry["shared_only"] and not include_shared:
            continue
        source_map[entry["path"]] = Path(entry["source"])
    return source_map
