#!/bin/bash
# Test the worktree manager: create, verify sandbox, test Claude session, cleanup
# Usage: bash test_worktree.sh [--no-cleanup]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_BRANCH="test/sandbox-verification"
NO_CLEANUP=false

if [[ "$1" == "--no-cleanup" ]]; then
    NO_CLEANUP=true
fi

echo "=== Testing Worktree Manager ==="

# 1. Create test worktree
echo -e "\n[1/5] Creating test worktree..."
python3 "$SCRIPT_DIR/create_worktree.py" -b "$TEST_BRANCH"

# Compute worktree path
REPO_NAME=$(basename "$PWD")
BRANCH_SAFE=$(echo "$TEST_BRANCH" | tr '/' '-')
WORKTREE_PATH="$(dirname "$PWD")/${REPO_NAME}-${BRANCH_SAFE}"

echo "  Worktree created at: $WORKTREE_PATH"

# 2. Verify COW clones (not symlinks)
echo -e "\n[2/5] Verifying COW clones..."
FOUND_CLONES=0
# Check common directories (some may not exist in all projects)
for dir in Data Output Notes Overleaf; do
    if [[ -L "$WORKTREE_PATH/$dir" ]]; then
        echo "  FAIL: $dir is a symlink, expected directory"
        exit 1
    elif [[ -d "$WORKTREE_PATH/$dir" ]]; then
        echo "  OK: $dir is a directory (COW clone)"
        ((FOUND_CLONES++)) || true
    else
        echo "  SKIP: $dir does not exist in main worktree"
    fi
done
echo "  Found $FOUND_CLONES COW cloned directories"

# 3. Verify sandbox settings
echo -e "\n[3/5] Verifying sandbox configuration..."
SETTINGS="$WORKTREE_PATH/.claude/settings.local.json"
if [[ ! -f "$SETTINGS" ]]; then
    echo "  FAIL: settings.local.json not found"
    exit 1
fi

python3 << EOF
import json
import sys
import os

with open("$SETTINGS") as f:
    s = json.load(f)

errors = []
warnings = []

# Check sandbox settings
if not s.get("sandbox", {}).get("enabled"):
    errors.append("sandbox.enabled is not True")
if not s.get("sandbox", {}).get("autoAllowBashIfSandboxed"):
    errors.append("sandbox.autoAllowBashIfSandboxed is not True")

# Check that filesystem key is NOT present (it's invalid)
if "filesystem" in s.get("sandbox", {}):
    warnings.append("sandbox.filesystem is set but not a valid setting (ignored)")

# Check permission rules for worktree and ~/.julia, ~/.cache
allow_rules = s.get("permissions", {}).get("allow", [])

has_worktree_edit = any("$WORKTREE_PATH" in r and r.startswith("Edit(") for r in allow_rules)
has_julia_edit = any("~/.julia" in r and r.startswith("Edit(") for r in allow_rules)
has_cache_edit = any("~/.cache" in r and r.startswith("Edit(") for r in allow_rules)
has_git_worktrees = any(".git/worktrees" in r and r.startswith("Edit(") for r in allow_rules)

if not has_worktree_edit:
    errors.append(f"Missing Edit permission for worktree path")
if not has_julia_edit:
    errors.append(f"Missing Edit(~/.julia/**) permission")
if not has_cache_edit:
    errors.append(f"Missing Edit(~/.cache/**) permission")
if not has_git_worktrees:
    errors.append(f"Missing Edit(<main>/.git/worktrees/**) permission")

if errors:
    for e in errors:
        print(f"  FAIL: {e}")
    sys.exit(1)
else:
    print("  OK: Sandbox enabled with autoAllowBashIfSandboxed")
    print("  OK: Edit permissions for worktree, ~/.julia, ~/.cache, .git/worktrees")
    for w in warnings:
        print(f"  WARN: {w}")
EOF

# 4. Test Claude session in sandbox
echo -e "\n[4/5] Testing Claude Code session in sandbox..."

# Check if claude command exists
if ! command -v claude &> /dev/null; then
    echo "  SKIP: 'claude' command not found, skipping sandbox test"
else
    echo "  Starting Claude in sandboxed worktree..."
    echo "  (Claude will attempt to create a file inside worktree and read a file outside)"
    cd "$WORKTREE_PATH"

    # Run Claude with a test prompt - use --print for non-interactive
    claude --print "Test sandbox: 1) Create scratch/sandbox_test.txt with 'hello from sandbox'. 2) Try to read the main worktree's CLAUDE.md at $PWD/../$REPO_NAME/CLAUDE.md and report if access was blocked or allowed."
    cd - > /dev/null
fi

# Check if the file was created (only if claude ran)
if command -v claude &> /dev/null; then
    if [[ -f "$WORKTREE_PATH/scratch/sandbox_test.txt" ]]; then
        echo "  OK: File created inside worktree (sandbox allowed write)"
    else
        echo "  INFO: Test file not created (Claude may have been blocked or chose not to)"
    fi
fi

# 5. Cleanup
if [[ "$NO_CLEANUP" == "false" ]]; then
    echo -e "\n[5/5] Cleaning up test worktree..."
    bash "$SCRIPT_DIR/remove_worktree.sh" "$WORKTREE_PATH"
    git branch -D "$TEST_BRANCH" 2>/dev/null || true
    echo "  Cleanup complete"
else
    echo -e "\n[5/5] Skipping cleanup (--no-cleanup flag set)"
    echo "  Worktree remains at: $WORKTREE_PATH"
    echo "  To manually clean up:"
    echo "    bash $SCRIPT_DIR/remove_worktree.sh $WORKTREE_PATH"
    echo "    git branch -D $TEST_BRANCH"
fi

echo -e "\n=== Test completed ==="
