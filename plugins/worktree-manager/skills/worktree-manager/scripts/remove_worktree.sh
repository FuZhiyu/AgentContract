#!/bin/bash
# Remove a git worktree with file change detection and sync options
# Usage: remove_worktree.sh [OPTIONS] <worktree-path>
#
# Options:
#   --force, -f     Skip change detection and remove immediately
#   --check-only    Only check for changes, don't remove
#   --help, -h      Show this help message

set -e

SCRIPT_DIR="$(dirname "$0")"

show_help() {
    cat << 'EOF'
Usage: remove_worktree.sh [OPTIONS] <worktree-path>

Remove a git worktree with file change detection and sync options.

Options:
  --force, -f     Skip change detection and remove immediately
  --check-only    Only check for changes, don't remove
  --help, -h      Show this help message

Workflow:
  1. Detects new/modified files in COW-cloned directories (Data, Output, Notes)
  2. If changes found, shows summary and saves details to changes.json
  3. Prompts to handle changes before removal (unless --force)

Handling Changes:
  Before removing, use sync_worktree.py to handle changed files:

  # Interactive mode - choose action for each file
  python .claude/skills/worktree-manager/scripts/sync_worktree.py \
      --from-json /path/to/worktree/changes.json --interactive

  # Overwrite - copy to original location, replacing existing files
  python .claude/skills/worktree-manager/scripts/sync_worktree.py \
      --from-json /path/to/worktree/changes.json --action overwrite

  # Rename - copy with suffix to avoid conflicts
  python .claude/skills/worktree-manager/scripts/sync_worktree.py \
      --from-json /path/to/worktree/changes.json --action rename --suffix "_worktree"

  # Delete - discard all changes
  python .claude/skills/worktree-manager/scripts/sync_worktree.py \
      --from-json /path/to/worktree/changes.json --action delete
EOF
}

# Parse arguments
FORCE=false
CHECK_ONLY=false
WORKTREE_PATH=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE=true
            shift
            ;;
        --check-only)
            CHECK_ONLY=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        -*)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
        *)
            WORKTREE_PATH="$1"
            shift
            ;;
    esac
done

if [[ -z "$WORKTREE_PATH" ]]; then
    echo "Error: worktree-path is required"
    show_help
    exit 1
fi

# Resolve to absolute path if relative
if [[ ! "$WORKTREE_PATH" = /* ]]; then
    WORKTREE_PATH="$PWD/$WORKTREE_PATH"
fi

if [[ ! -d "$WORKTREE_PATH" ]]; then
    echo "Error: Directory not found: $WORKTREE_PATH"
    exit 1
fi

echo "Worktree: $WORKTREE_PATH"
echo ""

# Check for changes in COW-cloned directories
CHANGES_JSON="$WORKTREE_PATH/changes.json"

check_changes() {
    echo "Checking for changes in COW-cloned directories..."

    # Run diff and capture exit code
    if ! python3 "$SCRIPT_DIR/diff_worktree.py" "$WORKTREE_PATH" --json > "$CHANGES_JSON" 2>/dev/null; then
        echo "  Warning: Could not check for changes (diff_worktree.py failed)"
        rm -f "$CHANGES_JSON"
        return 0  # Treat as no changes
    fi

    # Parse summary from JSON with error handling
    if ! NEW_COUNT=$(python3 -c "import json, sys; d=json.load(open('$CHANGES_JSON')); print(d['summary']['new'])" 2>/dev/null); then
        echo "  Warning: Could not parse changes.json"
        rm -f "$CHANGES_JSON"
        return 0  # Treat as no changes
    fi
    MOD_COUNT=$(python3 -c "import json; d=json.load(open('$CHANGES_JSON')); print(d['summary']['modified'])" 2>/dev/null || echo "0")
    TOTAL=$((NEW_COUNT + MOD_COUNT))

    echo "  New files: $NEW_COUNT"
    echo "  Modified files: $MOD_COUNT"
    echo ""

    # Return 1 if any changes found, 0 otherwise
    # (Bash return codes must be 0-255, so we can't return TOTAL directly)
    if [[ $TOTAL -gt 0 ]]; then
        return 1
    else
        return 0
    fi
}

# Run change detection
if check_changes; then
    HAS_CHANGES=false
else
    HAS_CHANGES=true
fi

if $CHECK_ONLY; then
    if $HAS_CHANGES; then
        echo "Changes detected. Details saved to: $CHANGES_JSON"
        echo ""
        echo "To view changes:"
        echo "  python3 $SCRIPT_DIR/diff_worktree.py $WORKTREE_PATH"
    else
        rm -f "$CHANGES_JSON"
        echo "No changes detected."
    fi
    exit 0
fi

# Handle changes
if $HAS_CHANGES && ! $FORCE; then
    echo "WARNING: Changes detected in worktree!"
    echo "These files will be LOST if you proceed without syncing."
    echo ""
    echo "Changes saved to: $CHANGES_JSON"
    echo ""
    echo "Options:"
    echo "  1. Sync changes to share folder first:"
    echo "     python3 $SCRIPT_DIR/sync_worktree.py --from-json $CHANGES_JSON --interactive"
    echo ""
    echo "  2. Proceed anyway (discard changes):"
    echo "     Re-run with --force flag"
    echo ""
    exit 1
fi

# Cleanup changes.json if exists
rm -f "$CHANGES_JSON"

echo "Removing worktree at: $WORKTREE_PATH"

# 1. Remove non-git-tracked content (COW cloned items)
echo "Removing COW cloned content..."
cd "$WORKTREE_PATH"
# List untracked files/dirs and remove them (using -z for null-delimited output)
git ls-files --others --directory -z | while IFS= read -r -d '' item; do
    # Remove trailing slash if present
    item="${item%/}"
    if [[ -e "$item" ]]; then
        echo "  Removing $item"
        rm -rf "$item"
    fi
done
cd - > /dev/null

# 2. Remove git worktree (--force handles any remaining untracked files)
echo "Removing git worktree..."
git worktree remove --force "$WORKTREE_PATH"

echo ""
echo "Worktree removed successfully"
