# git-tools

Git worktree management for parallel development with sandbox isolation.

## Skills

### worktree-manager
Create sandboxed git worktrees with full isolation for experimental work.

Features:
- Create worktrees from branches (new or existing)
- Explicit existing-branch checkout mode (`--existing`) with local/remote resolution
- COW (copy-on-write) clone non-git-tracked content (Data/, Output/, Notes/)
- Automatic sandbox permission configuration
- Detect and sync changes between worktrees using stateless discovery
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

## `.gitignore` behavior control

By default, ignored paths are copied into each worktree (independent state).  
Important: `.gitignore` does not support trailing comments on pattern lines.
So `Data/  # worktree:symlink` is not a valid single-line ignore rule for Git.

With the current parser, use this two-line form:

```gitignore
Data/
Data/  # worktree:symlink
```

Quick examples:

- `Output/` -> independent COW clone (default)
- `Data/` + `Data/  # worktree:symlink` -> shared symlink
- `cache/**` + `cache/**  # worktree:symlink` -> treated as `cache` (shared symlink)

## Scripts

| Script | Purpose |
|--------|---------|
| `create_worktree.py` | Create new worktree with COW cloning |
| `remove_worktree.sh` | Clean up worktree and COW copies |
| `sync_worktree.py` | Sync non-git files between worktrees |
| `diff_worktree.py` | Compare files between worktrees |
| `configure_sandbox.py` | Set up sandbox permissions |

## Stateless Change Detection

`diff_worktree.py` and `sync_worktree.py` do not rely on manifest files.
They infer managed paths from current git/filesystem state each run:

- Gitignored paths from `git ls-files --others --ignored --exclude-standard --directory`
- Git-tracked symlinks that resolve outside the repo
- Top-level symlinks in the main worktree (safety net)
- `.gitignore` annotations `# worktree:symlink` (treated as shared-only)

### Cloud-only file rule

- If a worktree path is still a symlink, it is treated as unchanged/shared.
- If that path becomes a regular file, it is treated as a local override (`modified`).
- Sync skips symlinks and only copies regular files.

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
