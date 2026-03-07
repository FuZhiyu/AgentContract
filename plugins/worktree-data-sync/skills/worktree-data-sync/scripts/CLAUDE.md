# scripts

Python implementation of the worktree-data-sync skill.

## Files

- `sync_worktree_data.py` -- main CLI entrypoint for seed/diff/apply operations
- `worktree_data_discovery.py` -- stateless managed-path discovery logic
- `test_worktree_data_sync.py` -- tests (run with `python3 -m pytest`)

## Key Types

- `SeedSyncMode = Literal["auto", "force-symlink", "force-cow"]`
- `symlink_missing_entry()` -- creates top-level symlinks for managed roots (used by `force-symlink` mode)

## Progress Logging

- `_progress()` -- writes progress messages to stderr (not stdout), keeping structured output clean
- `run_seed()` and `collect_changes()` accept a `verbose` parameter (default `True`); when enabled, per-entry progress is printed via `_progress()`
- CLI flag `--quiet` / `-q` suppresses progress output by setting `verbose=False`
