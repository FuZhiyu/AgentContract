---
name: worktree-manager
description: Create sandboxed git worktrees with full isolation. Automatically COW-clones non-git-tracked content and configures Claude sandbox permissions for safe, autonomous agent execution. Also handles git branch operations (checkout, merge, switch) when worktrees are involved.
---

# Worktree Manager Skill

Create sandboxed git worktrees with full isolation for safe, autonomous Claude sessions.

## When to Use

**Activate this skill when:**

### Worktree Operations
- "Create a new worktree"
- "Add worktree for branch X"
- "Remove worktree"
- "Clean up worktree"

### Git Branch Operations (when worktrees exist)
- "Checkout branch X" - check if branch is in another worktree
- "Switch to branch X" - check if branch is in another worktree
- "Merge branch X" - **IMPORTANT**: check if branch is in another worktree first
- "Delete branch X" - check if branch has an associated worktree

**IMPORTANT FOR AGENTS**: Before performing any git branch operation (checkout, switch, merge, delete), first run `git worktree list` to check if the target branch is checked out in another worktree. If it is, follow the merge workflow below.

## How It Works

1. **Git worktree** creates the new directory with git-tracked content
2. **COW cloning** copies non-git-trackable content
3. **Sandbox configuration** restricts Claude operations to the worktree folder

**What gets COW cloned:**
- **Tracked symlink targets**: Git tracks symlinks as symlinks, not their content. We COW clone the targets so each worktree gets an independent copy of Data/, Output/, Notes/.
- **Gitignored files/dirs**: These aren't trackable by git, so we COW clone them.

**What does NOT get cloned:**
- **Untracked files that git could track**: If a file is untracked but not ignored, git could manage it. We leave it to the user to decide.

COW (copy-on-write) clones share disk space until modified. Only changed files use additional space.

## `.gitignore` Annotations for Folder Behavior

You can control whether ignored paths are **independent per worktree** or **shared across worktrees** by annotating `.gitignore` patterns.

### Default behavior (no annotation)

- Ignored paths are copied into the new worktree (COW clone for local files).
- This gives each worktree an independent copy.

### Shared behavior via annotation

Important: `.gitignore` does not support trailing comments on pattern lines.
So `Data/  # worktree:symlink` is not a valid single-line ignore rule for Git.

With the current parser, use this two-line form to get both Git ignore behavior and worktree annotation:

```gitignore
# Independent per worktree (default)
Output/
Notes/

# Shared across worktrees
Data/
Data/  # worktree:symlink
cache/**
cache/**  # worktree:symlink
```

### Pattern normalization rules

The annotation parser normalizes patterns before applying them:

- `path/` -> `path`
- `path/**` -> `path`
- `path/*` -> `path`

So this line:

```gitignore
models/*.bin  # worktree:symlink
```

is treated as `models` and symlinks the whole `models` path.

### Priority and scope

- Annotated paths are handled first.
- Any ignored file under an annotated directory is skipped from COW cloning.
- If an annotated path does not exist when creating the worktree, it is ignored.

### Practical guideline

- Use default (no annotation) for outputs/notes you want isolated per experiment.
- For shared datasets/caches, pair an ignore rule with an annotated duplicate line (for example `Data/` plus `Data/  # worktree:symlink`).

## Creating a Worktree

`create_worktree.py` is the single supported creation entrypoint (no shell wrapper).

```bash
python3 .claude/skills/worktree-manager/scripts/create_worktree.py [OPTIONS] <branch-name> [worktree-path]
```

**Options:**
- `-b`: Create new branch from current HEAD
- `--existing`: Checkout an existing branch into a new worktree
- `--remote <name>`: Remote to check when `--existing` branch is not local (default: `origin`)
- `--deny-sandbox-bypass`: Deny agents from using `dangerouslyDisableSandbox` (default: allowed)

**Arguments:**
- `branch-name` (required): Branch to checkout (existing or new)
- `worktree-path` (optional): Where to create worktree. Default: `../RepoName-branch`

**Examples:**
```bash
# Create worktree for existing branch
python3 .claude/skills/worktree-manager/scripts/create_worktree.py feature/new-analysis

# Create with custom path
python3 .claude/skills/worktree-manager/scripts/create_worktree.py feature/experiment ../my-experiment

# Create new branch from current HEAD
python3 .claude/skills/worktree-manager/scripts/create_worktree.py -b feature/new-feature

# Checkout existing branch (local or remote-tracking)
python3 .claude/skills/worktree-manager/scripts/create_worktree.py --existing feature/existing-work

# Checkout existing branch from non-default remote
python3 .claude/skills/worktree-manager/scripts/create_worktree.py --existing --remote upstream feature/existing-work

# Deny sandbox bypass (for untrusted agents)
python3 .claude/skills/worktree-manager/scripts/create_worktree.py --deny-sandbox-bypass feature/untrusted-work
```

### What Gets Created

After creation, the worktree is fully isolated:
```
worktree-path/
├── Codes/         (git-tracked)
├── Figures/       (git-tracked)
├── Tables/        (git-tracked)
├── Data/          (COW clone - independent copy)
├── Output/        (COW clone - independent copy)
├── Notes/         (COW clone - independent copy)
└── .claude/settings.local.json  (sandbox enabled)
```

## Sandbox Behavior

The worktree is sandboxed with these settings:

| Operation | Behavior |
|-----------|----------|
| `julia --project=. script.jl` | Auto-executes |
| `ENV_VAR=X julia script.jl` | Auto-executes |
| Read/write within worktree | Auto-allowed |
| Read sibling worktrees (same project) | Auto-allowed |
| Julia compilation (~/.julia/) | Auto-allowed |
| Cache directories (~/.cache/) | Auto-allowed |
| Write to other worktrees | Prompts for permission |
| Access ~/Documents, etc. | Prompts for permission |
| Bypass sandbox (dangerouslyDisableSandbox) | Allowed (use `--deny-sandbox-bypass` to restrict) |

Sibling worktrees are detected using the main worktree name (e.g., `MyProject*` matches `MyProject`, `MyProject-feature-xyz`, etc.).

### Sandbox Bypass Protection

By default, agents are allowed to use `dangerouslyDisableSandbox` to escape sandbox restrictions when needed. This provides flexibility for legitimate use cases.

To restrict untrusted agents, use `--deny-sandbox-bypass` when creating the worktree. This adds deny rules that require user approval before any sandbox bypass attempt.

## Using with Claude Code

**Important:** For the sandbox to take effect, you must start Claude Code from within the new worktree folder:

```bash
# After creating a sandboxed worktree
cd /path/to/worktree
claude

# Or run a specific task
cd /path/to/worktree
claude "Run the analysis script"
```

This is especially important for:
- **Automated agents** that should be isolated from other projects
- **Experimental work** where you want to prevent accidental modifications to the main worktree
- **Parallel development** with independent Claude sessions per worktree

The sandbox settings in `.claude/settings.local.json` are only applied when Claude starts in that directory.

## Removing a Worktree

```bash
bash .claude/skills/worktree-manager/scripts/remove_worktree.sh <worktree-path>
```

## Stateless Diff/Sync Behavior

`diff_worktree.py` and `sync_worktree.py` do not depend on manifest files.
`diff_worktree.py` discovers managed paths from current repository state on every run using:

- Gitignored paths (`git ls-files --others --ignored --exclude-standard --directory`)
- Git-tracked symlinks that resolve outside the repository
- Top-level symlinks in the main worktree (safety net)
- `.gitignore` annotations `# worktree:symlink` as shared-only exclusions

`diff_worktree.py` uses a union of:
- Entries discovered from the main worktree
- Ignored roots discovered in the target worktree

This catches new ignored roots/files created only in the target worktree.

`sync_worktree.py --from-json` is plan-driven:
- It executes `target_path` emitted by `diff_worktree.py --json`
- It does not re-discover destination paths in JSON mode
- `target_path` is required in each change record

### Cloud-only files (important)

- If a path in the worktree is still a symlink, it is treated as unchanged/shared.
- If that path is now a regular file, it is treated as a local override (`modified`).
- `sync_worktree.py` skips symlinks and only syncs regular files.

**Options:**
- `--force, -f`: Skip change detection and remove immediately
- `--check-only`: Only check for changes, don't remove

### Workflow

When removing a worktree:
1. **Change detection**: Scans COW-cloned directories for new/modified files
2. **If changes found**: Shows summary and saves details to `changes.json`
3. **Prompts for action**: Sync changes to share or discard them

### Handling Changed Files

If changes are detected, use the sync tool to handle them before removal:

```bash
# Interactive mode - choose action for each file
python3 .claude/skills/worktree-manager/scripts/sync_worktree.py \
    --from-json /path/to/worktree/changes.json --interactive

# Overwrite - copy to original location, replacing existing files
python3 .claude/skills/worktree-manager/scripts/sync_worktree.py \
    --from-json /path/to/worktree/changes.json --action overwrite

# Rename - copy with suffix to avoid conflicts (default: _worktree)
python3 .claude/skills/worktree-manager/scripts/sync_worktree.py \
    --from-json /path/to/worktree/changes.json --action rename

# Delete - discard all changes
python3 .claude/skills/worktree-manager/scripts/sync_worktree.py \
    --from-json /path/to/worktree/changes.json --action delete
```

### Sync Options

| Option | Description |
|--------|-------------|
| `--action overwrite` | Copy to original location, replacing existing files |
| `--action rename` | Copy with suffix to avoid conflicts (default: `_worktree`) |
| `--action delete` | Remove files from worktree (discard changes) |
| `--suffix TEXT` | Custom suffix for rename action |
| `--status new modified` | Only process files with these statuses |
| `--dry-run, -n` | Show actions without executing |
| `--interactive, -i` | Choose action for each file |

### Checking Changes Without Removing

To see what files have changed without removing:

```bash
# Human-readable output
python3 .claude/skills/worktree-manager/scripts/diff_worktree.py /path/to/worktree

# JSON output for scripting
python3 .claude/skills/worktree-manager/scripts/diff_worktree.py /path/to/worktree --json
```

Use fresh JSON generated by the current `diff_worktree.py` before running `sync_worktree.py --from-json`.

### Force Remove

To skip change detection and remove immediately (discards all changes):

```bash
bash .claude/skills/worktree-manager/scripts/remove_worktree.sh --force <worktree-path>
```

**Warning:** COW cloned directories contain independent copies. Changes not synced to share will be lost.

## Listing Worktrees

```bash
git worktree list
```

## Merging Branches from Other Worktrees

**CRITICAL**: When merging a branch that is checked out in another worktree, the worktrees have independent COW-cloned directories (Data, Output, Notes). Git merge only handles version-controlled files. You MUST check for changes in non-version-controlled files and ask the user how to proceed.

### Pre-Merge Workflow

Before merging branch X into the current branch:

```bash
# 1. Check if branch X is in another worktree
git worktree list

# Example output:
# /path/to/main-worktree        abc1234 [main]
# /path/to/feature-worktree     def5678 [feature/X]  <-- target branch is here!
```

If the target branch IS in another worktree:

```bash
# 2. Check for changes in non-version-controlled files
python3 .claude/skills/worktree-manager/scripts/diff_worktree.py /path/to/feature-worktree
```

### Asking User How to Proceed

If there are new or modified files in the other worktree's COW-cloned directories, **ASK THE USER** before proceeding:

> "Branch `feature/X` is checked out in worktree `/path/to/feature-worktree`.
>
> I found changes in non-version-controlled files:
> - NEW: Output/Analysis/new_results.csv (15KB)
> - MODIFIED: Notes/experiment_log.md (2KB -> 5KB)
>
> How would you like to handle these before merging?
> 1. **Overwrite** - copy to original location, replacing existing files
> 2. **Rename** - copy with suffix to avoid conflicts
> 3. **Ignore** - proceed with merge, leave worktree files as-is
> 4. **Abort** - cancel merge to review manually"

### Handling Options

Based on user's choice:

```bash
# Option 1: Overwrite
python3 .claude/skills/worktree-manager/scripts/sync_worktree.py \
    --from-json /path/to/feature-worktree/changes.json --action overwrite

# Option 2: Rename
python3 .claude/skills/worktree-manager/scripts/sync_worktree.py \
    --from-json /path/to/feature-worktree/changes.json --action rename --suffix "_from_feature"

# Option 3: Ignore - proceed directly with git merge

# Option 4: Abort - do not perform merge
```

### Complete Merge Example

```bash
# 1. List worktrees
git worktree list
# Output shows feature/experiment is in ../MyProject-feature-experiment

# 2. Check for non-git changes
python3 .claude/skills/worktree-manager/scripts/diff_worktree.py \
    ../MyProject-feature-experiment --json > /tmp/worktree_changes.json

# 3. [Ask user and handle based on response]

# 4. Perform git merge (only after user confirms)
git merge feature/experiment

# 5. Optionally clean up the worktree after merge
bash .claude/skills/worktree-manager/scripts/remove_worktree.sh \
    ../MyProject-feature-experiment
```

### Why This Matters

In this project structure:
- **Git-tracked files** (Code/, Figures/, Tables/) are merged normally by git
- **COW-cloned files** (Data/, Output/, Notes/) are INDEPENDENT copies in each worktree
- Without this check, work in Output/ or Notes/ could be silently lost when the worktree is removed

## Prerequisites

- macOS with APFS filesystem (for COW clones)
- Python 3 (for sandbox configuration)

## Troubleshooting

### "fatal: is already checked out"
The branch is checked out in another worktree. Use a different branch or remove the existing worktree first.

### COW clones not working
Verify you're on APFS: `diskutil info / | grep "Type"`. COW requires source and destination on the same APFS volume.

### Sandbox too restrictive
Edit `.claude/settings.local.json` in the worktree to add paths to `sandbox.filesystem.allowed`.
