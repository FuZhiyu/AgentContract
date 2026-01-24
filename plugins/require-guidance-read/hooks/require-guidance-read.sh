#!/bin/bash
# Require reading CLAUDE.md/AGENTS.md before accessing code directories
# This hook blocks file operations in code directories until the project's
# guidance file has been read, ensuring Claude follows project-specific instructions.

# Read JSON input from stdin
input=$(cat)
session_id=$(echo "$input" | jq -r '.session_id')
tool_name=$(echo "$input" | jq -r '.tool_name')
# Handle different tool input field names
file_path=$(echo "$input" | jq -r '.tool_input.file_path // .tool_input.path // empty')

# Tracking file for this session (auto-cleaned on system restart)
TRACKING_FILE="/tmp/claude-guidance-read-${session_id}"

# Code directory patterns that trigger the check
CODE_DIRS="src/|code/|codes/|scripts/|tests/"

# Exit if no file path (nothing to check)
[[ -z "$file_path" ]] && exit 0

# Function: Check if a guidance file has been recorded as read
is_read() {
    local guidance_file="$1"
    [[ -f "$TRACKING_FILE" ]] && grep -qxF "$guidance_file" "$TRACKING_FILE"
}

# Function: Record a guidance file as read
record_read() {
    local guidance_file="$1"
    # Avoid duplicates
    if ! is_read "$guidance_file"; then
        echo "$guidance_file" >> "$TRACKING_FILE"
    fi
}

# Function: Find git root (stop boundary for search)
find_git_root() {
    local dir="$1"
    while [[ "$dir" != "/" && "$dir" != "." ]]; do
        if [[ -d "$dir/.git" ]]; then
            echo "$dir"
            return 0
        fi
        dir=$(dirname "$dir")
    done
    return 1
}

# Function: Find nearest CLAUDE.md or AGENTS.md walking up (stop at git root)
find_guidance_file() {
    local dir="$1"
    local git_root=$(find_git_root "$dir")

    while [[ "$dir" != "/" && "$dir" != "." ]]; do
        for name in CLAUDE.md AGENTS.md; do
            if [[ -f "$dir/$name" ]]; then
                echo "$dir/$name"
                return 0
            fi
        done
        # Stop at git root (don't cross repo boundaries)
        if [[ -n "$git_root" && "$dir" == "$git_root" ]]; then
            return 1
        fi
        dir=$(dirname "$dir")
    done
    return 1
}

# If reading/writing a guidance file itself, handle specially
basename_file=$(basename "$file_path")
if [[ "$basename_file" == "CLAUDE.md" || "$basename_file" == "AGENTS.md" ]]; then
    # Only record as read if actually READING (not writing/editing)
    if [[ "$tool_name" == "Read" ]]; then
        record_read "$file_path"
    fi
    exit 0  # Always allow access to guidance files themselves
fi

# Check if path is in a code directory
if ! echo "$file_path" | grep -qE "$CODE_DIRS"; then
    exit 0  # Not a code directory, allow
fi

# Find the nearest guidance file
target_dir=$(dirname "$file_path")
guidance_file=$(find_guidance_file "$target_dir")

# No guidance file found, allow
[[ -z "$guidance_file" ]] && exit 0

# Check if already read
if is_read "$guidance_file"; then
    exit 0  # Already read, allow
fi

# Block and request reading the guidance file
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Please read the project guidance file first: $guidance_file"
  }
}
EOF
