# worktree-data-sync Skill

Skill definition and scripts for worktree data synchronization.

## Structure

- `SKILL.md` -- skill instructions (when to use, CLI surface, modes, examples)
- `scripts/` -- Python implementation and tests

## Conventions

- Single CLI entrypoint: `sync_worktree_data.py`
- `--seed-sync-mode` is only valid with `--mode seed`; CLI validates this constraint
- `SeedSyncMode` type alias defines valid modes: `auto`, `force-symlink`, `force-cow`
