#!/usr/bin/env python3
"""Validate and optionally sync Claude and Codex plugin manifests."""

from __future__ import annotations

import argparse
import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
SHARED_FIELDS = ("name", "version", "description", "repository", "license")
OPTIONAL_SYNC_FIELDS = ("author", "keywords")
REQUIRED_INTERFACE_FIELDS = (
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
    "websiteURL",
    "privacyPolicyURL",
    "termsOfServiceURL",
    "defaultPrompt",
)
CODEX_BANNED_RUNTIME_PATTERNS = (
    (r"\$\{CLAUDE_SKILL_DIR\}", "uses unsupported ${CLAUDE_SKILL_DIR} path syntax"),
    (r"\bAskUserQuestion\b", "references AskUserQuestion instead of Codex-safe prompting"),
    (r"\bTask tool\b", "references the Claude Task tool"),
    (r"\bsubagent_type\b", "references legacy subagent_type syntax"),
    (r"\bTodoWrite\b", "references TodoWrite instead of a portable checklist"),
    (r"Skill\(skill=", "references the Claude Skill(...) helper"),
    (r"Read\(file_path=", "references the Claude Read(...) helper"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Codex plugin manifests and the repo marketplace against the "
            "existing Claude plugin manifests."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="AgentContract repository root (default: script parent repo).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Sync shared fields from .claude-plugin/plugin.json into .codex-plugin/plugin.json.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def strip_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[index + 1 :]).lstrip("\n")
    return text


def iter_plugin_dirs(repo_root: Path) -> list[Path]:
    plugins_root = repo_root / "plugins"
    return sorted(path for path in plugins_root.iterdir() if path.is_dir())


def sync_shared_fields(claude_manifest: dict[str, Any], codex_manifest: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    for field in SHARED_FIELDS + OPTIONAL_SYNC_FIELDS:
        if field not in claude_manifest:
            continue
        if codex_manifest.get(field) != claude_manifest[field]:
            codex_manifest[field] = deepcopy(claude_manifest[field])
            changed.append(field)
    return changed


def validate_interface(
    plugin_name: str,
    codex_manifest: dict[str, Any],
    issues: list[str],
) -> None:
    interface = codex_manifest.get("interface")
    if not isinstance(interface, dict):
        issues.append(f"{plugin_name}: missing interface object in .codex-plugin/plugin.json")
        return

    for field in REQUIRED_INTERFACE_FIELDS:
        value = interface.get(field)
        if value in (None, "", []):
            issues.append(f"{plugin_name}: interface.{field} is missing or empty")

    default_prompt = interface.get("defaultPrompt")
    if default_prompt is not None:
        if not isinstance(default_prompt, list) or not all(
            isinstance(item, str) and item.strip() for item in default_prompt
        ):
            issues.append(f"{plugin_name}: interface.defaultPrompt must be a non-empty string list")


def validate_marketplace(
    repo_root: Path,
    plugin_dirs: list[Path],
    issues: list[str],
) -> dict[str, dict[str, Any]]:
    marketplace_path = repo_root / ".agents" / "plugins" / "marketplace.json"
    if not marketplace_path.is_file():
        issues.append(f"Missing repo marketplace: {marketplace_path}")
        return {}

    marketplace = load_json(marketplace_path)
    if not isinstance(marketplace, dict):
        issues.append(f"{marketplace_path}: marketplace root must be a JSON object")
        return {}

    if not marketplace.get("name"):
        issues.append(f"{marketplace_path}: top-level name is missing")
    interface = marketplace.get("interface")
    if not isinstance(interface, dict) or not interface.get("displayName"):
        issues.append(f"{marketplace_path}: interface.displayName is missing")

    raw_plugins = marketplace.get("plugins")
    if not isinstance(raw_plugins, list):
        issues.append(f"{marketplace_path}: plugins must be an array")
        return {}

    entries: dict[str, dict[str, Any]] = {}
    for entry in raw_plugins:
        if not isinstance(entry, dict):
            issues.append(f"{marketplace_path}: plugin entry must be an object")
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            issues.append(f"{marketplace_path}: plugin entry is missing name")
            continue
        if name in entries:
            issues.append(f"{marketplace_path}: duplicate plugin entry for {name}")
            continue
        entries[name] = entry

    expected_names = {path.name for path in plugin_dirs}
    actual_names = set(entries)
    missing = sorted(expected_names - actual_names)
    extra = sorted(actual_names - expected_names)
    for name in missing:
        issues.append(f"{marketplace_path}: missing plugin entry for {name}")
    for name in extra:
        issues.append(f"{marketplace_path}: unexpected plugin entry for {name}")

    return entries


def validate_plugin(
    plugin_dir: Path,
    marketplace_entries: dict[str, dict[str, Any]],
    write_changes: bool,
    issues: list[str],
) -> list[str]:
    plugin_name = plugin_dir.name
    claude_path = plugin_dir / ".claude-plugin" / "plugin.json"
    codex_path = plugin_dir / ".codex-plugin" / "plugin.json"

    if not claude_path.is_file():
        issues.append(f"{plugin_name}: missing {claude_path}")
        return []
    if not codex_path.is_file():
        issues.append(f"{plugin_name}: missing {codex_path}")
        return []

    claude_manifest = load_json(claude_path)
    codex_manifest = load_json(codex_path)

    changed_fields: list[str] = []
    if write_changes:
        changed_fields = sync_shared_fields(claude_manifest, codex_manifest)
        if changed_fields:
            write_json(codex_path, codex_manifest)

    for field in SHARED_FIELDS:
        if codex_manifest.get(field) != claude_manifest.get(field):
            issues.append(
                f"{plugin_name}: shared field '{field}' differs between Claude and Codex manifests"
            )

    for field in OPTIONAL_SYNC_FIELDS:
        if field in claude_manifest and codex_manifest.get(field) != claude_manifest.get(field):
            issues.append(
                f"{plugin_name}: shared field '{field}' differs between Claude and Codex manifests"
            )

    if codex_manifest.get("skills") != "./skills/":
        issues.append(f"{plugin_name}: Codex manifest must declare skills as ./skills/")

    validate_interface(plugin_name, codex_manifest, issues)
    validate_runtime_docs(plugin_dir, plugin_name, issues)

    entry = marketplace_entries.get(claude_manifest.get("name", plugin_name))
    if entry is None:
        issues.append(f"{plugin_name}: missing repo marketplace entry")
        return changed_fields

    source = entry.get("source")
    if not isinstance(source, dict):
        issues.append(f"{plugin_name}: marketplace source must be an object")
    else:
        if source.get("source") != "local":
            issues.append(f"{plugin_name}: marketplace source.source must be 'local'")
        expected_path = f"./plugins/{plugin_name}"
        if source.get("path") != expected_path:
            issues.append(
                f"{plugin_name}: marketplace source.path must be {expected_path}"
            )

    policy = entry.get("policy")
    if not isinstance(policy, dict):
        issues.append(f"{plugin_name}: marketplace policy must be an object")
    else:
        if not policy.get("installation"):
            issues.append(f"{plugin_name}: marketplace policy.installation is missing")
        if not policy.get("authentication"):
            issues.append(f"{plugin_name}: marketplace policy.authentication is missing")

    category = entry.get("category")
    if not category:
        issues.append(f"{plugin_name}: marketplace category is missing")
    else:
        interface = codex_manifest.get("interface")
        if isinstance(interface, dict) and interface.get("category") != category:
            issues.append(
                f"{plugin_name}: interface.category does not match marketplace category"
            )

    return changed_fields


def read_frontmatter_name(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    frontmatter_lines: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        frontmatter_lines.append(line)
    frontmatter = "\n".join(frontmatter_lines)
    match = re.search(r"(?m)^\s*name\s*:\s*(.+?)\s*$", frontmatter)
    if not match:
        return None
    raw = match.group(1).strip()
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        raw = raw[1:-1]
    return raw


def validate_runtime_docs(plugin_dir: Path, plugin_name: str, issues: list[str]) -> None:
    skill_paths = sorted(plugin_dir.glob("skills/*/SKILL.md"))
    direct_skill = plugin_dir / "SKILL.md"
    if direct_skill.is_file():
        skill_paths.insert(0, direct_skill)

    agent_paths = sorted(plugin_dir.glob("agents/*.md"))
    agent_names = [read_frontmatter_name(path) or path.stem for path in agent_paths]

    for skill_path in skill_paths:
        text = strip_frontmatter(skill_path.read_text(encoding="utf-8"))
        rel = skill_path.relative_to(plugin_dir.parent.parent)
        for pattern, message in CODEX_BANNED_RUNTIME_PATTERNS:
            if re.search(pattern, text):
                issues.append(f"{plugin_name}: {rel} {message}")
        for agent_name in agent_names:
            legacy_role = f"{plugin_name}:{agent_name}"
            if legacy_role in text:
                issues.append(
                    f"{plugin_name}: {rel} references legacy role name '{legacy_role}'; "
                    f"use '{plugin_name}__{agent_name}' when referring to installed Codex roles"
                )

    for agent_path in agent_paths:
        text = strip_frontmatter(agent_path.read_text(encoding="utf-8"))
        rel = agent_path.relative_to(plugin_dir.parent.parent)
        for pattern, message in CODEX_BANNED_RUNTIME_PATTERNS:
            if re.search(pattern, text):
                issues.append(f"{plugin_name}: {rel} {message}")


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    issues: list[str] = []

    plugin_dirs = iter_plugin_dirs(repo_root)
    marketplace_entries = validate_marketplace(repo_root, plugin_dirs, issues)

    changed_by_plugin: dict[str, list[str]] = {}
    for plugin_dir in plugin_dirs:
        changed_fields = validate_plugin(
            plugin_dir=plugin_dir,
            marketplace_entries=marketplace_entries,
            write_changes=args.write,
            issues=issues,
        )
        if changed_fields:
            changed_by_plugin[plugin_dir.name] = changed_fields

    if args.write and changed_by_plugin:
        for plugin_name, fields in changed_by_plugin.items():
            field_list = ", ".join(fields)
            print(f"[sync] {plugin_name}: updated {field_list}")

    if issues:
        for issue in issues:
            print(f"[error] {issue}", file=sys.stderr)
        return 1

    print(f"Validated {len(plugin_dirs)} plugins and repo marketplace.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
