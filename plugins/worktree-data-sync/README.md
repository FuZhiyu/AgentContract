# worktree-data-sync

Sync non-git data between existing git worktrees.

## Skill

### worktree-data-sync
Use this skill when you want to compare or transfer non-versioned data between worktrees that already exist.

Features:
- Cross-worktree source/destination sync (`--from`, `--to`)
- Source defaults to the main worktree when `--from` is omitted
- Seed mode to materialize missing managed data in destination
- Diff mode with human-readable and JSON output
- Apply mode with explicit `overwrite` or `rename` actions
- Stateless managed-path discovery (no manifest files)

## Scope

This plugin only handles non-git data sync. It does **not**:
- create worktrees
- remove worktrees
- configure sandbox permissions
- manage git branch operations

## Command

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/sync_worktree_data.py --to <worktree> --mode <seed|diff|apply> [...]
```

## `.gitignore` annotations

You can mark ignored roots as symlink-only using either tag:

```gitignore
Data/
Data/  # data-sync:symlink
```

Legacy tag is still supported:

```gitignore
Data/
Data/  # worktree:symlink
```

## Modes

- `seed`: materialize missing managed files from source to destination
  - default `--seed-sync-mode auto`: preserve current per-path behavior
  - `--seed-sync-mode force-symlink`: create top-level symlinks for managed roots when the destination path does not already exist
  - `--seed-sync-mode force-cow`: copy/COW all managed roots, including symlink-only annotated paths
- `diff`: report source-to-destination deltas (`new`, `modified`, `unchanged`)
- `apply`: execute `overwrite` or `rename` actions on selected changes

`force-symlink` is intended for initial seeding and never replaces an existing destination root; conflicting paths are skipped.

## Progress Output

By default, seed, diff, and apply modes print per-entry progress to stderr (e.g., `Seeding [1/5] Data/ ...`). Use `--quiet` / `-q` to suppress this output. Structured output (JSON, summary reports) is always printed to stdout and is unaffected by `--quiet`.

## Examples

```bash
# 1) Seed from main worktree into destination
python3 ${CLAUDE_SKILL_DIR}/scripts/sync_worktree_data.py \
  --to ../MyRepo-feature \
  --mode seed

# 2) Seed using top-level symlinks for all managed roots
python3 ${CLAUDE_SKILL_DIR}/scripts/sync_worktree_data.py \
  --to ../MyRepo-feature \
  --mode seed \
  --seed-sync-mode force-symlink

# 3) Seed using copy/COW for all managed roots, including symlink-only ones
python3 ${CLAUDE_SKILL_DIR}/scripts/sync_worktree_data.py \
  --to ../MyRepo-feature \
  --mode seed \
  --seed-sync-mode force-cow

# 4) Diff explicit source -> destination
python3 ${CLAUDE_SKILL_DIR}/scripts/sync_worktree_data.py \
  --from ../MyRepo-experimentA \
  --to ../MyRepo-experimentB \
  --mode diff --json

# 5) Apply overwrite from diff json
python3 ${CLAUDE_SKILL_DIR}/scripts/sync_worktree_data.py \
  --to ../MyRepo-feature \
  --mode apply \
  --from-json changes.json \
  --action overwrite
```
