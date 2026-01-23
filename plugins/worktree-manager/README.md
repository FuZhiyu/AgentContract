# git-tools

Git worktree management for parallel development with sandbox isolation.

## Skills

### worktree-manager
Create sandboxed git worktrees with full isolation for experimental work.

Features:
- Create worktrees from branches (new or existing)
- COW (copy-on-write) clone non-git-tracked content (Data/, Output/, Notes/)
- Automatic sandbox permission configuration
- Detect and sync changes between worktrees
- Pre-merge workflow checks

## Usage

**Create isolated worktree:**
- "Create a worktree for experimenting with new feature"
- "Set up an isolated branch for testing"

**Sync changes:**
- "Sync changes from worktree back to main"
- "Check what changed in the worktree"

**Remove worktree:**
- "Remove the experiment worktree"
- "Clean up the feature-x worktree"

## Scripts

| Script | Purpose |
|--------|---------|
| `create_worktree.py` | Create new worktree with COW cloning |
| `create_worktree.sh` | Shell wrapper for creation |
| `remove_worktree.sh` | Clean up worktree and COW copies |
| `sync_worktree.py` | Sync non-git files between worktrees |
| `diff_worktree.py` | Compare files between worktrees |
| `configure_sandbox.py` | Set up sandbox permissions |

## Architecture

```
main-repo/
├── Code/
├── Data/ -> ../main-repo-Share/Data
├── Output/ -> ../main-repo-Share/Output
└── Notes/ -> ../main-repo-Share/Notes

worktrees/
└── feature-branch/
    ├── Code/               # Git-tracked (from worktree)
    ├── Data/               # COW copy of main Data
    ├── Output/             # COW copy of main Output
    └── Notes/              # COW copy of main Notes
```

## Sandbox Mode

Worktrees run in sandbox mode by default:
- Agents can execute freely in worktree
- Prompts required for access to parent repo
- Uses `--deny-sandbox-bypass` for untrusted agents
