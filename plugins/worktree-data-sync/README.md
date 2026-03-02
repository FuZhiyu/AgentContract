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
python3 .claude/skills/worktree-data-sync/scripts/sync_worktree_data.py --to <worktree> --mode <seed|diff|apply> [...]
```

## `.gitignore` annotations

You can mark ignored roots as shared-only using either tag:

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

- `seed`: copy only missing managed files from source to destination
- `diff`: report source-to-destination deltas (`new`, `modified`, `unchanged`)
- `apply`: execute `overwrite` or `rename` actions on selected changes

## Examples

```bash
# 1) Seed from main worktree into destination
python3 .claude/skills/worktree-data-sync/scripts/sync_worktree_data.py \
  --to ../MyRepo-feature \
  --mode seed

# 2) Diff explicit source -> destination
python3 .claude/skills/worktree-data-sync/scripts/sync_worktree_data.py \
  --from ../MyRepo-experimentA \
  --to ../MyRepo-experimentB \
  --mode diff --json

# 3) Apply overwrite from diff json
python3 .claude/skills/worktree-data-sync/scripts/sync_worktree_data.py \
  --to ../MyRepo-feature \
  --mode apply \
  --from-json changes.json \
  --action overwrite
```
