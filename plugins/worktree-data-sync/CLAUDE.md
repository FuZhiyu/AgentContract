# worktree-data-sync

Plugin for syncing non-git data between existing git worktrees. Does not create/remove worktrees or manage branches.

## Structure

- `README.md` -- user-facing documentation with modes, examples, and `.gitignore` annotation syntax
- `skills/worktree-data-sync/` -- SKILL.md and scripts

## Key Concepts

- **Managed paths**: discovered statelessly from `.gitignore`, tracked symlinks, and annotations
- **Shared-only roots**: annotated with `# data-sync:symlink` (or legacy `# worktree:symlink`); excluded from copy/apply by default
- **Seed sync modes**: `auto` (default), `force-symlink`, `force-cow` -- control how missing data is materialized
