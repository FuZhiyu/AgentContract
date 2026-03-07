#!/usr/bin/env python3
"""
Install Codex-compatible skills from this repository and optionally update config.

This script discovers skill folders from plugins, installs them into a Codex
skill directory, and updates a target config.toml with:
- [[skills.config]] entries
- [agents.<role>] entries (optional)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class SkillSource:
    plugin_name: str
    skill_name: str
    skill_md: Path
    source_dir: Path


@dataclass(frozen=True)
class AgentSource:
    plugin_name: str
    agent_name: str
    agent_md: Path
    description: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install Codex skills from AgentContract."
    )
    parser.add_argument(
        "--source-repo",
        type=Path,
        default=None,
        help="AgentContract repo containing plugins/ directory (default: current directory).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        dest="repo_root_deprecated",
        help="Deprecated alias for --source-repo.",
    )
    parser.add_argument(
        "--target-root",
        type=Path,
        default=Path.cwd(),
        help="Target project root for project-scoped installs (default: current directory).",
    )
    parser.add_argument(
        "--plugins",
        type=str,
        default="all",
        help="Comma-separated plugin names to install, or 'all' (default).",
    )
    parser.add_argument(
        "--scope",
        choices=("project", "user"),
        default="project",
        help="Install scope. project => ./.agents + ./.codex, user => ~/.agents + ~/.codex.",
    )
    parser.add_argument(
        "--skills-dir",
        type=Path,
        help="Override install directory for skills.",
    )
    parser.add_argument(
        "--config-file",
        type=Path,
        help="Override config.toml to update.",
    )
    parser.add_argument(
        "--mode",
        choices=("copy", "symlink"),
        default="copy",
        help="Install mode for skill directories (default: copy). Use symlink for local development.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing installed skills with the same destination name.",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing installation (alias of --force): remove existing and reinstall.",
    )
    parser.add_argument(
        "--no-config-update",
        action="store_true",
        help="Install skills but do not edit config.toml.",
    )
    parser.add_argument(
        "--absolute-config-paths",
        action="store_true",
        help="Write absolute skill paths into config.toml (default is relative for project scope).",
    )
    parser.add_argument(
        "--agents-dir",
        type=Path,
        help="Override directory to write generated agent role TOML files.",
    )
    parser.add_argument(
        "--install-agents",
        action="store_true",
        dest="install_agents",
        help="Install plugin agents into [agents.*] roles (default: enabled).",
    )
    parser.add_argument(
        "--no-install-agents",
        action="store_false",
        dest="install_agents",
        help="Skip installing plugin agents.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without changing files.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List discovered plugins/skills/agents and exit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="With --list, print machine-readable JSON.",
    )
    parser.set_defaults(install_agents=True)
    return parser.parse_args()


def iter_plugins(repo_root: Path) -> list[tuple[Path, str]]:
    plugins_root = repo_root / "plugins"
    if not plugins_root.is_dir():
        raise FileNotFoundError(f"plugins directory not found: {plugins_root}")

    discovered: list[tuple[Path, str]] = []
    for plugin_dir in sorted(p for p in plugins_root.iterdir() if p.is_dir()):
        plugin_name = read_plugin_name(plugin_dir) or plugin_dir.name
        discovered.append((plugin_dir, plugin_name))
    return discovered


def find_skill_sources(repo_root: Path) -> list[SkillSource]:
    sources: list[SkillSource] = []
    for plugin_dir, plugin_name in iter_plugins(repo_root):
        candidates = []
        direct = plugin_dir / "SKILL.md"
        if direct.is_file():
            candidates.append(direct)
        nested_root = plugin_dir / "skills"
        if nested_root.is_dir():
            for skill_md in sorted(nested_root.glob("*/SKILL.md")):
                if skill_md.is_file():
                    candidates.append(skill_md)

        for skill_md in candidates:
            skill_name = read_skill_name(skill_md)
            if not skill_name:
                raise ValueError(f"Could not parse skill name from: {skill_md}")
            sources.append(
                SkillSource(
                    plugin_name=plugin_name,
                    skill_name=skill_name,
                    skill_md=skill_md,
                    source_dir=skill_md.parent,
                )
            )
    return sources


def find_agent_sources(repo_root: Path) -> list[AgentSource]:
    sources: list[AgentSource] = []
    for plugin_dir, plugin_name in iter_plugins(repo_root):
        agents_dir = plugin_dir / "agents"
        if not agents_dir.is_dir():
            continue
        for agent_md in sorted(agents_dir.glob("*.md")):
            if not agent_md.is_file():
                continue
            agent_name = read_frontmatter_field(agent_md, "name") or agent_md.stem
            description = read_frontmatter_field(agent_md, "description")
            sources.append(
                AgentSource(
                    plugin_name=plugin_name,
                    agent_name=agent_name,
                    agent_md=agent_md,
                    description=description,
                )
            )
    return sources


def read_plugin_name(plugin_dir: Path) -> str | None:
    plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
    if not plugin_json.is_file():
        return None
    try:
        data = json.loads(plugin_json.read_text(encoding="utf-8"))
    except Exception:
        return None
    name = data.get("name")
    return name if isinstance(name, str) and name.strip() else None


def read_skill_name(skill_md: Path) -> str | None:
    raw = read_frontmatter_field(skill_md, "name")
    if raw is None:
        return None
    return raw


def read_frontmatter_field(path: Path, key: str) -> str | None:
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
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", frontmatter)
    if not match:
        return None
    raw = match.group(1).strip()
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        raw = raw[1:-1]
    return raw


def parse_plugin_selection(arg: str, available_plugins: Iterable[str]) -> set[str]:
    available = set(available_plugins)
    if arg.strip().lower() == "all":
        return available
    requested = {item.strip() for item in arg.split(",") if item.strip()}
    unknown = requested - available
    if unknown:
        unknown_list = ", ".join(sorted(unknown))
        raise ValueError(f"Unknown plugin(s): {unknown_list}")
    return requested


def ensure_parent(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)


def install_skill(
    source: SkillSource,
    dest_root: Path,
    mode: str,
    force: bool,
    dry_run: bool,
) -> Path:
    dest = dest_root / source.skill_name

    if dest.exists() or dest.is_symlink():
        if is_same_install(dest, source.source_dir):
            print(f"[skip] {source.skill_name}: already installed at {dest}")
            return dest
        if not force:
            raise FileExistsError(
                f"Destination exists for {source.skill_name}: {dest}. Use --force to replace."
            )
        print(f"[replace] Removing existing destination: {dest}")
        if not dry_run:
            if dest.is_symlink() or dest.is_file():
                dest.unlink()
            else:
                shutil.rmtree(dest)

    print(f"[install] {source.skill_name} ({source.plugin_name}) -> {dest} [{mode}]")
    if dry_run:
        return dest

    if mode == "symlink":
        dest.symlink_to(source.source_dir.resolve(), target_is_directory=True)
    else:
        shutil.copytree(source.source_dir, dest)
    return dest


def is_same_install(dest: Path, source_dir: Path) -> bool:
    try:
        return dest.resolve() == source_dir.resolve()
    except FileNotFoundError:
        return False


def config_path_for_skill(
    skill_install_dir: Path, config_file: Path, relative: bool
) -> str:
    # Keep the configured path anchored to the installed location
    # (e.g., .agents/skills/...), not the symlink target.
    skill_md_path = (skill_install_dir / "SKILL.md").absolute()
    if relative:
        path = Path(
            os_path_relpath(skill_md_path, start=config_file.parent.resolve())
        ).as_posix()
    else:
        path = skill_md_path.as_posix()
    return path


def os_path_relpath(path: Path, start: Path) -> str:
    return (
        str(Path(path).relative_to(start))
        if path.is_relative_to(start)
        else os.path.relpath(path, start)
    )


def update_config_with_skills(
    config_file: Path,
    skill_paths: list[tuple[str, str]],
    dry_run: bool,
) -> int:
    if config_file.exists():
        text = config_file.read_text(encoding="utf-8")
    else:
        text = ""

    existing = extract_existing_skill_paths(text, config_file.parent)
    to_add = [(raw, resolved) for raw, resolved in skill_paths if resolved not in existing]

    if not to_add:
        print(f"[config] No new [[skills.config]] entries needed in {config_file}")
        return 0

    append_chunks = []
    for raw_path, _ in to_add:
        escaped = raw_path.replace("\\", "\\\\").replace('"', '\\"')
        append_chunks.append(
            "\n".join(
                [
                    "[[skills.config]]",
                    f'path = "{escaped}"',
                    "enabled = true",
                    "",
                ]
            )
        )

    new_text = text
    if new_text and not new_text.endswith("\n"):
        new_text += "\n"
    if new_text and not new_text.endswith("\n\n"):
        new_text += "\n"
    new_text += "".join(append_chunks)

    print(f"[config] Adding {len(to_add)} [[skills.config]] entries to {config_file}")
    if not dry_run:
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(new_text, encoding="utf-8")
    return len(to_add)


def extract_existing_skill_paths(text: str, config_dir: Path) -> set[str]:
    blocks = re.findall(
        r"(?ms)^\[\[skills\.config\]\]\s*(.*?)(?=^\[\[skills\.config\]\]|\Z)", text
    )
    existing: set[str] = set()
    for block in blocks:
        match = re.search(r'(?m)^\s*path\s*=\s*"([^"]+)"\s*$', block)
        if not match:
            continue
        raw = match.group(1)
        resolved = resolve_path_for_compare(raw, config_dir)
        if resolved:
            existing.add(resolved)
    return existing


def resolve_path_for_compare(path_str: str, config_dir: Path) -> str | None:
    if "$" in path_str or "{" in path_str:
        return path_str
    path = Path(path_str)
    if not path.is_absolute():
        path = (config_dir / path).resolve()
    else:
        path = path.resolve()
    return path.as_posix()


def sanitize_role_name(value: str) -> str:
    cleaned = value.strip().lower()
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    if not cleaned:
        cleaned = "agent"
    if cleaned[0].isdigit():
        cleaned = f"agent-{cleaned}"
    return cleaned


def make_role_name(plugin_name: str, agent_name: str) -> str:
    return sanitize_role_name(f"{plugin_name}__{agent_name}")


def ensure_features_multi_agent(config_file: Path, dry_run: bool) -> bool:
    text = config_file.read_text(encoding="utf-8") if config_file.exists() else ""

    section_match = re.search(
        r"(?ms)^\[features\]\s*(.*?)(?=^\[[^\[]|\Z)", text
    )
    if section_match:
        section = section_match.group(1)
        if re.search(r"(?m)^\s*multi_agent\s*=\s*true\s*$", section):
            return False
        if re.search(r"(?m)^\s*multi_agent\s*=", section):
            new_section = re.sub(
                r"(?m)^(\s*multi_agent\s*=\s*).*$",
                r"\1true",
                section,
            )
        else:
            new_section = section
            if new_section and not new_section.endswith("\n"):
                new_section += "\n"
            new_section += "multi_agent = true\n"
        new_text = text[: section_match.start(1)] + new_section + text[section_match.end(1) :]
    else:
        new_text = text
        if new_text and not new_text.endswith("\n"):
            new_text += "\n"
        if new_text and not new_text.endswith("\n\n"):
            new_text += "\n"
        new_text += "[features]\nmulti_agent = true\n"

    print(f"[config] Enabling features.multi_agent in {config_file}")
    if not dry_run:
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(new_text, encoding="utf-8")
    return True


def write_agent_role_file(
    source: AgentSource,
    role_name: str,
    agents_dir: Path,
    force: bool,
    dry_run: bool,
) -> Path:
    dest = agents_dir / f"{role_name}.toml"
    content = source.agent_md.read_text(encoding="utf-8")
    payload = [
        f"# Generated by scripts/install_codex_skills.py",
        f"# source_plugin = {source.plugin_name}",
        f"# source_agent = {source.agent_name}",
        f"# source_path = {source.agent_md}",
        f"developer_instructions = {json.dumps(content)}",
        "",
    ]
    new_text = "\n".join(payload)

    if dest.exists() and not force:
        old_text = dest.read_text(encoding="utf-8")
        if old_text == new_text:
            print(f"[skip] agent role file already up to date: {dest}")
            return dest
        raise FileExistsError(f"Agent role file exists: {dest}. Use --force to replace.")

    action = "write" if not dest.exists() else "replace"
    print(f"[{action}] agent role file: {dest}")
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(new_text, encoding="utf-8")
    return dest


def extract_existing_agent_roles(text: str) -> set[str]:
    roles = set(re.findall(r"(?m)^\[agents\.([^\]]+)\]\s*$", text))
    return roles


def update_config_with_agents(
    config_file: Path,
    role_entries: list[tuple[str, str, str]],
    dry_run: bool,
) -> int:
    text = config_file.read_text(encoding="utf-8") if config_file.exists() else ""
    existing = extract_existing_agent_roles(text)
    to_add = [entry for entry in role_entries if entry[0] not in existing]

    if not to_add:
        print(f"[config] No new [agents.*] entries needed in {config_file}")
        return 0

    append_chunks: list[str] = []
    for role_name, description, config_path in to_add:
        escaped_desc = description.replace("\\", "\\\\").replace('"', '\\"')
        escaped_path = config_path.replace("\\", "\\\\").replace('"', '\\"')
        append_chunks.append(
            "\n".join(
                [
                    f"[agents.{role_name}]",
                    f'description = "{escaped_desc}"',
                    f'config_file = "{escaped_path}"',
                    "",
                ]
            )
        )

    new_text = text
    if new_text and not new_text.endswith("\n"):
        new_text += "\n"
    if new_text and not new_text.endswith("\n\n"):
        new_text += "\n"
    new_text += "".join(append_chunks)

    print(f"[config] Adding {len(to_add)} [agents.*] entries to {config_file}")
    if not dry_run:
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(new_text, encoding="utf-8")
    return len(to_add)


def main() -> int:
    args = parse_args()
    if args.update:
        args.force = True

    # Resolve --repo-root (deprecated) → --source-repo
    if args.repo_root_deprecated is not None:
        print(
            "[warn] --repo-root is deprecated; use --source-repo instead.",
            file=sys.stderr,
        )
        if args.source_repo is not None:
            print(
                "[warn] Both --source-repo and --repo-root provided; ignoring --repo-root.",
                file=sys.stderr,
            )
        else:
            args.source_repo = args.repo_root_deprecated
    if args.source_repo is None:
        args.source_repo = Path.cwd()
    source_repo = args.source_repo.resolve()
    target_root = args.target_root.resolve()

    try:
        all_sources = find_skill_sources(source_repo)
        all_agent_sources = find_agent_sources(source_repo)
    except Exception as exc:
        print(
            f"Error discovering skills: {exc}\n"
            "--source-repo must point to the AgentContract repo containing plugins/. "
            "If installing into another project, set --target-root to the target project directory.",
            file=sys.stderr,
        )
        return 1

    if args.list:
        if args.json:
            payload = {
                "source_repo": str(source_repo),
                "plugins": sorted({src.plugin_name for src in all_sources} | {a.plugin_name for a in all_agent_sources}),
                "skills": [
                    {
                        "plugin": src.plugin_name,
                        "skill_name": src.skill_name,
                        "skill_md": str(src.skill_md),
                        "source_dir": str(src.source_dir),
                    }
                    for src in all_sources
                ],
                "agents": [
                    {
                        "plugin": src.plugin_name,
                        "agent_name": src.agent_name,
                        "agent_md": str(src.agent_md),
                        "description": src.description,
                        "role_name": make_role_name(src.plugin_name, src.agent_name),
                    }
                    for src in all_agent_sources
                ],
            }
            print(json.dumps(payload, indent=2))
        else:
            plugins = sorted({src.plugin_name for src in all_sources} | {a.plugin_name for a in all_agent_sources})
            print("Discovered plugins:")
            for name in plugins:
                print(f"- {name}")
            print("\nDiscovered skills:")
            for src in sorted(all_sources, key=lambda x: (x.plugin_name, x.skill_name)):
                print(f"- {src.plugin_name}: {src.skill_name} ({src.skill_md})")
            print("\nDiscovered agents:")
            if not all_agent_sources:
                print("- (none)")
            else:
                for src in sorted(all_agent_sources, key=lambda x: (x.plugin_name, x.agent_name)):
                    role_name = make_role_name(src.plugin_name, src.agent_name)
                    print(
                        f"- {src.plugin_name}: {src.agent_name} "
                        f"(role={role_name}, {src.agent_md})"
                    )
        return 0

    available_plugins = sorted(
        {src.plugin_name for src in all_sources} | {src.plugin_name for src in all_agent_sources}
    )
    try:
        selected_plugins = parse_plugin_selection(args.plugins, available_plugins)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    selected_sources = [src for src in all_sources if src.plugin_name in selected_plugins]
    selected_agent_sources = [
        src for src in all_agent_sources if src.plugin_name in selected_plugins
    ]
    if not selected_sources and not selected_agent_sources:
        print("No matching skills/agents found for selected plugins.", file=sys.stderr)
        return 1

    if args.skills_dir:
        skills_dir = args.skills_dir.expanduser().resolve()
    elif args.scope == "project":
        skills_dir = (target_root / ".agents" / "skills").resolve()
    else:
        skills_dir = (Path.home() / ".agents" / "skills").resolve()

    if args.config_file:
        config_file = args.config_file.expanduser().resolve()
    elif args.scope == "project":
        config_file = (target_root / ".codex" / "config.toml").resolve()
    else:
        config_file = (Path.home() / ".codex" / "config.toml").resolve()

    if args.agents_dir:
        agents_dir = args.agents_dir.expanduser().resolve()
    else:
        agents_dir = (config_file.parent / "agents").resolve()

    print(f"[info] Source repo:  {source_repo}")
    if args.scope == "project":
        print(f"[info] Target root:  {target_root}")
    print(f"[info] Scope:        {args.scope}")
    print(f"[info] Skills dir:   {skills_dir}")
    print(f"[info] Agents dir:   {agents_dir}")
    print(f"[info] Config file:  {config_file}")
    print(f"[info] Plugins:      {', '.join(sorted(selected_plugins))}")

    ensure_parent(skills_dir, args.dry_run)

    installed_paths: list[Path] = []
    for source in selected_sources:
        try:
            installed = install_skill(
                source=source,
                dest_root=skills_dir,
                mode=args.mode,
                force=args.force,
                dry_run=args.dry_run,
            )
            installed_paths.append(installed)
        except Exception as exc:
            print(f"Error installing {source.skill_name}: {exc}", file=sys.stderr)
            return 1

    skill_config_updates = 0
    if not args.no_config_update:
        relative_paths = args.scope == "project" and not args.absolute_config_paths
        skill_paths_for_config: list[tuple[str, str]] = []
        for p in installed_paths:
            configured = config_path_for_skill(
                skill_install_dir=p, config_file=config_file, relative=relative_paths
            )
            resolved_for_compare = resolve_path_for_compare(configured, config_file.parent)
            if resolved_for_compare is None:
                continue
            skill_paths_for_config.append((configured, resolved_for_compare))
        skill_config_updates = update_config_with_skills(
            config_file=config_file,
            skill_paths=skill_paths_for_config,
            dry_run=args.dry_run,
        )

    agent_role_files_written = 0
    agent_config_updates = 0
    multi_agent_updates = 0
    if args.install_agents and selected_agent_sources:
        ensure_parent(agents_dir, args.dry_run)
        role_entries: list[tuple[str, str, str]] = []
        for source in selected_agent_sources:
            role_name = make_role_name(source.plugin_name, source.agent_name)
            description = (
                source.description
                or f"Agent role from plugin {source.plugin_name}: {source.agent_name}"
            )
            try:
                write_agent_role_file(
                    source=source,
                    role_name=role_name,
                    agents_dir=agents_dir,
                    force=args.force,
                    dry_run=args.dry_run,
                )
                agent_role_files_written += 1
            except Exception as exc:
                print(f"Error installing agent {source.agent_name}: {exc}", file=sys.stderr)
                return 1

            config_path = f"agents/{role_name}.toml"
            role_entries.append((role_name, description, config_path))

        if not args.no_config_update:
            if ensure_features_multi_agent(config_file=config_file, dry_run=args.dry_run):
                multi_agent_updates += 1
            agent_config_updates = update_config_with_agents(
                config_file=config_file,
                role_entries=role_entries,
                dry_run=args.dry_run,
            )

    print(
        f"[done] Installed {len(installed_paths)} skill(s), "
        f"{agent_role_files_written} agent role file(s). "
        f"Config updates: skills={skill_config_updates}, "
        f"agents={agent_config_updates}, multi_agent={multi_agent_updates}. "
        f"{'Dry run only.' if args.dry_run else ''}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
