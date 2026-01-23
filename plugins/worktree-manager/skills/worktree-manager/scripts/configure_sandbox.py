#!/usr/bin/env python3
"""
Configure sandbox settings for a worktree.

Usage:
    python configure_sandbox.py <worktree-path> [OPTIONS]

Options:
    --deny-sandbox-bypass  Deny agents from using dangerouslyDisableSandbox
                           (default: allowed)
"""
import argparse
import json
import sys
from pathlib import Path


def get_main_worktree_info(worktree_path: Path) -> tuple[str, Path]:
    """
    Get the main worktree's base name and path.
    E.g., for 'MyProject-feature-xyz' -> ('MyProject', Path('/path/to/MyProject'))

    Uses git to find the main worktree as the canonical project location.
    Returns (base_name, main_worktree_path).
    """
    import subprocess

    # Get main worktree path from git
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )

    # First worktree listed is the main one
    for line in result.stdout.split("\n"):
        if line.startswith("worktree "):
            main_worktree = Path(line.split(" ", 1)[1])
            return main_worktree.name, main_worktree

    # Fallback: strip common suffixes from current worktree name
    name = worktree_path.name
    parts = name.split("-")
    if len(parts) > 1:
        return parts[0], worktree_path
    return name, worktree_path


def filter_permissions(permissions: list[str], worktree_path: str, sibling_pattern: str, main_worktree_path: str) -> list[str]:
    """
    Filter permissions to remove overly broad Read/Edit/Write rules.
    Keep only:
    - Bash permissions (controlled by sandbox)
    - WebFetch/WebSearch permissions
    - MCP tool permissions
    - Skill permissions
    - Read/Edit/Write only for the worktree itself
    - Read for sibling worktrees (same project)
    - Edit for main repo's .git (needed for git operations)
    """
    filtered = []

    # Strip leading / from paths since // prefix is the absolute marker
    wt_path = worktree_path.lstrip("/")
    sib_path = sibling_pattern.lstrip("/")
    main_path = main_worktree_path.lstrip("/")

    for perm in permissions:
        # Skip broad Read/Edit/Write permissions outside worktree
        if perm.startswith(("Read(", "Edit(", "Write(")):
            # Keep only if it's specifically for the worktree path
            # Format: Read(//absolute/path/**) - double slash for absolute paths
            if f"(//{wt_path}" in perm:
                filtered.append(perm)
            # Skip broad permissions
            continue

        # Also skip any Bash permissions that use dangerouslyDisableSandbox
        # These should always require user approval
        if "dangerouslyDisableSandbox" in perm.lower():
            continue

        # Keep everything else (Bash, WebFetch, mcp__, Skill, etc.)
        filtered.append(perm)

    # Add worktree-specific Read/Edit/Write permissions
    # Format: Tool(//absolute/path/**) or Tool(~/home-relative/**)
    # Note: wt_path, sib_path, main_path have leading / stripped
    worktree_perms = [
        f"Read(//{wt_path}/**)",
        f"Edit(//{wt_path}/**)",
        f"Write(//{wt_path}/**)",
        f"Read(//{sib_path}/**)",  # Read access to all sibling worktrees
        # Allow Julia/Python package managers to work within sandbox
        # Use ~ for home-relative paths (Claude Code syntax)
        "Edit(~/.julia/**)",
        "Edit(~/.cache/**)",
        # Allow git operations - worktrees store state in main repo's .git/worktrees/
        f"Edit(//{main_path}/.git/**)",
    ]
    for p in worktree_perms:
        if p not in filtered:
            filtered.append(p)

    return filtered


def get_deny_rules() -> list[str]:
    """
    Return deny rules that should always require user approval.

    These rules ensure that agents cannot bypass the sandbox without
    explicit user consent. The dangerouslyDisableSandbox flag in Bash
    tool calls will always trigger a permission prompt.
    """
    return [
        # Block any attempt to disable sandbox - this pattern ensures
        # that if Claude tries to use dangerouslyDisableSandbox, the
        # user is prompted. The sandbox system should already do this,
        # but we add explicit deny rules as defense in depth.
        "Bash(dangerouslyDisableSandbox:*)",
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Configure sandbox settings for a worktree"
    )
    parser.add_argument("worktree_path", type=Path, help="Path to the worktree")
    parser.add_argument(
        "--deny-sandbox-bypass",
        action="store_true",
        help="Deny agents from using dangerouslyDisableSandbox (default: allowed)",
    )
    args = parser.parse_args()

    worktree_path = args.worktree_path.resolve()
    settings_file = worktree_path / ".claude" / "settings.local.json"

    # Get project base name and main worktree path
    project_base, main_worktree = get_main_worktree_info(worktree_path)
    sibling_pattern = str(worktree_path.parent / f"{project_base}*")

    # Load existing settings (from git checkout)
    settings = {}
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in {settings_file}, starting fresh: {e}")
            settings = {}

    # Add/update sandbox configuration
    # Note: filesystem access is controlled via permissions.allow (Read/Edit/Write rules),
    # NOT via sandbox settings. The sandbox only controls bash command execution.
    settings["sandbox"] = {
        "enabled": True,
        "autoAllowBashIfSandboxed": True,
    }

    # Get deny rules only if bypass is denied
    deny_rules = get_deny_rules() if args.deny_sandbox_bypass else []

    # Filter permissions to remove broad Read/Edit/Write rules
    if "permissions" in settings and "allow" in settings["permissions"]:
        settings["permissions"]["allow"] = filter_permissions(
            settings["permissions"]["allow"], str(worktree_path), sibling_pattern, str(main_worktree)
        )
        # Merge deny rules, avoiding duplicates
        existing_deny = settings["permissions"].get("deny", [])
        settings["permissions"]["deny"] = list(set(existing_deny + deny_rules))
    else:
        # Strip leading / since // is the absolute path marker
        wt = str(worktree_path).lstrip("/")
        sib = sibling_pattern.lstrip("/")
        main = str(main_worktree).lstrip("/")
        settings["permissions"] = {
            "allow": [
                f"Read(//{wt}/**)",
                f"Edit(//{wt}/**)",
                f"Write(//{wt}/**)",
                f"Read(//{sib}/**)",  # Read access to sibling worktrees
                "Edit(~/.julia/**)",  # Julia packages
                "Edit(~/.cache/**)",  # Cache dirs
                f"Edit(//{main}/.git/worktrees/**)",  # Git worktree state
            ],
            "deny": deny_rules,
        }

    # Write back
    settings_file.write_text(json.dumps(settings, indent=2) + "\n")
    print(f"Sandbox configured for {worktree_path}")
    print(f"  - Removed broad Read/Edit/Write permissions")
    print(f"  - Added worktree-specific permissions")
    print(f"  - Added read access for sibling worktrees: {sibling_pattern}")
    if args.deny_sandbox_bypass:
        print(f"  - Sandbox bypass DENIED (dangerouslyDisableSandbox requires approval)")
    else:
        print(f"  - Sandbox bypass ALLOWED (dangerouslyDisableSandbox permitted)")


if __name__ == "__main__":
    main()
