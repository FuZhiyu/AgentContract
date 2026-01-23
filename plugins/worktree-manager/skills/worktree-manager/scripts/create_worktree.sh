#!/bin/bash
# Create a sandboxed git worktree with COW clones for symlink targets
# Usage: create_worktree.sh [-b] [--deny-sandbox-bypass] <branch-name> [worktree-path]

set -e
trap 'echo "ERROR at line $LINENO (exit code $?): $BASH_COMMAND" >&2' ERR

# Verify we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Parse flags
CREATE_BRANCH=""
DENY_SANDBOX_BYPASS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -b)
            CREATE_BRANCH="-b"
            shift
            ;;
        --deny-sandbox-bypass)
            DENY_SANDBOX_BYPASS="--deny-sandbox-bypass"
            shift
            ;;
        -*)
            echo "Unknown option: $1"
            echo "Usage: create_worktree.sh [-b] [--deny-sandbox-bypass] <branch-name> [worktree-path]"
            exit 1
            ;;
        *)
            break
            ;;
    esac
done

BRANCH=$1
if [[ -z "$BRANCH" ]]; then
    echo "Usage: create_worktree.sh [-b] [--deny-sandbox-bypass] <branch-name> [worktree-path]"
    echo "  -b: Create new branch"
    echo "  --deny-sandbox-bypass: Deny agents from using dangerouslyDisableSandbox (default: allowed)"
    exit 1
fi

# Validate branch name (allow alphanumeric, /, -, _, .)
if [[ ! "$BRANCH" =~ ^[a-zA-Z0-9/_.-]+$ ]]; then
    echo "Error: Invalid branch name. Use only alphanumeric, /, -, _, ."
    exit 1
fi

# Get repo name and main worktree path
REPO_NAME=$(basename "$PWD")
MAIN_WORKTREE="$PWD"

# Default worktree path: sibling directory named RepoName-branch
BRANCH_SAFE=$(echo "$BRANCH" | tr '/' '-')
shift  # Remove branch from args
WORKTREE_PATH=${1:-"../${REPO_NAME}-${BRANCH_SAFE}"}

# Resolve to absolute path
WORKTREE_PATH=$(cd "$(dirname "$WORKTREE_PATH")" 2>/dev/null && pwd)/$(basename "$WORKTREE_PATH")

echo "Creating worktree at: $WORKTREE_PATH"
echo "Branch: $BRANCH"
echo "Main worktree: $MAIN_WORKTREE"

# 1. Create git worktree
if [[ -n "$CREATE_BRANCH" ]]; then
    git worktree add "$WORKTREE_PATH" -b "$BRANCH"
else
    git worktree add "$WORKTREE_PATH" "$BRANCH"
fi

# 2. COW clone non-git-trackable content
# We clone two types of content:
#   a) Tracked symlink TARGETS - git tracks symlinks as symlinks, not their content
#   b) Gitignored files/dirs - git won't track these, so we need to copy them
# We do NOT clone untracked files that git COULD track (user should decide on those)
#
# For cloud-synced files (dataless flag), we create symlinks instead of COW clones
# to avoid triggering downloads. When overwritten, the symlink becomes a real file.
echo "Creating COW clones for non-git-trackable content..."

# Check if a file has the dataless flag (online-only cloud file)
# Returns 0 if dataless, 1 if local
is_dataless() {
    local file="$1"
    # Get file flags in hex, check for SF_DATALESS (0x40000000)
    # Use stat -f to get flags in hex format
    local flags=$(stat -f "%f" "$file" 2>/dev/null)
    [[ -n "$flags" ]] && [[ $((flags & 0x40000000)) -ne 0 ]]
}

# Smart copy directory: COW clone local files, symlink cloud files
# Recursively handles directory contents
smart_copy_dir() {
    local src="$1"
    local dst="$2"
    local rel_display="$3"  # for logging (top-level only)

    local cloud_count=0
    local local_count=0

    # Use find to get all files/dirs (handles empty globs and spaces in names)
    while IFS= read -r -d '' item; do
        local name=$(basename "$item")
        [[ "$name" == "." || "$name" == ".." ]] && continue

        local dst_item="$dst/$name"

        if [[ -L "$item" ]]; then
            # Symlink inside directory - recreate the symlink
            ln -sf "$(readlink "$item")" "$dst_item"
        elif [[ -f "$item" ]]; then
            # Regular file
            if is_dataless "$item"; then
                # Cloud file - create symlink to original
                ln -sf "$item" "$dst_item"
                ((cloud_count++)) || true
            else
                # Local file - COW clone
                cp -c "$item" "$dst_item" 2>/dev/null || cp "$item" "$dst_item"
                ((local_count++)) || true
            fi
        elif [[ -d "$item" ]]; then
            # Subdirectory - recurse
            mkdir -p "$dst_item"
            smart_copy_dir "$item" "$dst_item" ""
        fi
    done < <(find "$src" -maxdepth 1 -mindepth 1 -print0 2>/dev/null)
    # Reset exit status - 'while read' returns 1 on EOF which triggers set -e
    :

    [[ -n "$rel_display" ]] && echo "    ($local_count local COW, $cloud_count cloud symlinks)"
}

clone_non_trackable() {
    local src_dir="$1"
    local dst_dir="$2"
    local rel_path="${3:-.}"  # relative path from repo root

    for item in "$src_dir"/*; do
        [[ -e "$item" || -L "$item" ]] || continue  # handle broken symlinks too
        local name=$(basename "$item")
        local dst_item="$dst_dir/$name"
        local item_rel="$rel_path/$name"
        [[ "$rel_path" == "." ]] && item_rel="$name"

        # Skip hidden files/dirs (like .git)
        [[ "$name" == .* ]] && continue

        if [[ -L "$item" ]]; then
            # Symlink - handle based on target type
            if git ls-files --error-unmatch "$item_rel" &>/dev/null || \
               git check-ignore -q "$item_rel" 2>/dev/null; then
                local target=$(readlink -f "$item")
                if [[ -d "$target" ]]; then
                    # Directory symlink: create real dir and clone contents inside
                    echo "  Cloning $item_rel (symlink -> $target)"
                    rm -f "$dst_item"
                    mkdir -p "$dst_item"
                    smart_copy_dir "$target" "$dst_item" "$item_rel"
                elif [[ -f "$target" ]]; then
                    # File symlink: COW clone or symlink based on cloud status
                    rm -f "$dst_item"
                    if is_dataless "$target"; then
                        echo "  Symlinking $item_rel (cloud file)"
                        ln -s "$target" "$dst_item"
                    else
                        echo "  COW cloning $item_rel (local file)"
                        cp -c "$target" "$dst_item" 2>/dev/null || cp "$target" "$dst_item"
                    fi
                else
                    echo "  Skipping $item_rel (symlink target does not exist)"
                fi
            fi

        elif git check-ignore -q "$item_rel" 2>/dev/null; then
            # Gitignored file/dir - clone
            if [[ ! -e "$dst_item" ]]; then
                if [[ -d "$item" ]]; then
                    echo "  Cloning $item_rel (gitignored)"
                    mkdir -p "$dst_item"
                    smart_copy_dir "$item" "$dst_item" "$item_rel"
                elif [[ -f "$item" ]]; then
                    if is_dataless "$item"; then
                        echo "  Symlinking $item_rel (gitignored, cloud)"
                        ln -sf "$item" "$dst_item"
                    else
                        echo "  COW cloning $item_rel (gitignored, local)"
                        cp -c "$item" "$dst_item" 2>/dev/null || cp "$item" "$dst_item"
                    fi
                fi
            fi

        elif [[ -d "$item" ]]; then
            # Regular directory - recurse
            if [[ -d "$dst_item" ]]; then
                clone_non_trackable "$item" "$dst_item" "$item_rel"
            fi
        fi
    done
}

clone_non_trackable "$MAIN_WORKTREE" "$WORKTREE_PATH"

# 3. Configure sandbox settings
echo "Configuring sandbox..."
python3 "$(dirname "$0")/configure_sandbox.py" "$WORKTREE_PATH" $DENY_SANDBOX_BYPASS

echo ""
echo "Worktree created successfully at $WORKTREE_PATH"
echo "Sandbox enabled - auto-execute within worktree, permission required outside"
echo ""
echo "Directory structure:"
ls -la "$WORKTREE_PATH" | grep -E "^[dl]"
