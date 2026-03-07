# Codex Install Guide

**This file is meant to be read by an agent (Codex).** Ask Codex to read this file for installation.

This repository is structured for Claude plugins. This guide shows how to install the same skills for Codex, with project-scoped config under `./.codex/`.

## What This Supports

- Install plugin skills into project-local `./.agents/skills/` (or user `~/.agents/skills/`)
- Update Codex config with `[[skills.config]]` entries
- Install plugin agents as Codex roles:
  - write role files to `./.codex/agents/*.toml` (or `~/.codex/agents/*.toml`)
  - add `[agents.<role>]` entries in `config.toml`
  - enable `[features].multi_agent = true`
- Keep setup project-specific by default (`./.codex/config.toml`)

## Dynamic Discovery

The installer discovers everything directly from the repo:

- Plugins: `plugins/*/.claude-plugin/plugin.json` (`name`)
- Skills: `plugins/*/SKILL.md` and `plugins/*/skills/*/SKILL.md`
- Agents: `plugins/*/agents/*.md` (frontmatter `name`, fallback to filename)

List discovered plugins/skills/agents:

```bash
python3 scripts/install_codex_skills.py --list
```

Machine-readable output:

```bash
python3 scripts/install_codex_skills.py --list --json
```

## Installer Script

Script path:

```bash
python3 scripts/install_codex_skills.py --help
```

## Agent-Assisted Install Protocol (Required)

When an agent is asked to install Codex skills for this repo, it must follow this flow:

1. Read this file first (`CODEX_INSTALL.md`).
2. Discover current inventory dynamically:
   ```bash
   python3 scripts/install_codex_skills.py --list --json
   ```
3. Show the discovered plugin names to the user.
4. Ask the user which plugins to install (`all` or a subset).
5. Restate the selection and ask for explicit confirmation before any install command.
6. Run installation only after user confirms.
7. Report exactly what was installed:
   - skills installed
   - agent roles installed
   - config file(s) updated

If the user asked to **update** an existing installation, run with `--update` so existing installed skills/roles are replaced.

Hard rule:
- Do not install anything until the user confirms the plugin selection.

Suggested question format:

```text
I discovered these plugins: <plugin-list>.
Which plugins should I install in Codex? (all or comma-separated list)
```

Confirmation format:

```text
I will install: <selected-plugins> with scope=<project|user>.
Proceed?
```

### If an Agent Needs to Fetch the Repo First

```bash
git clone <REPO_URL> AgentContract
cd AgentContract
python3 scripts/install_codex_skills.py --list --json > /tmp/codex_plugin_inventory.json
```

Then install using the discovered set (no static list):

```bash
python3 scripts/install_codex_skills.py --scope project
```

Suggested agent instruction:

```text
Clone the AgentContract repo, run:
python3 scripts/install_codex_skills.py --list --json
Use that discovered inventory (plugins/skills/agents) as the source of truth,
then run installation with --scope project.
Do not hardcode plugin or skill names.
```

### Default (project-scoped, recommended)

Run from repo root:

```bash
python3 scripts/install_codex_skills.py --scope project
```

This will:

1. Install skills to `./.agents/skills/` (copy mode by default)
2. Install agent role TOML files to `./.codex/agents/`
3. Create/update `./.codex/config.toml`
4. Append missing `[[skills.config]]` entries idempotently
5. Append missing `[agents.<role>]` entries idempotently
6. Ensure `features.multi_agent = true`

### Install only selected plugins

```bash
python3 scripts/install_codex_skills.py \
  --scope project \
  --plugins <plugin-1>,<plugin-2>
```

Use `--list` output as the source of truth for valid plugin names.

### Update existing installation (remove + reinstall)

For all plugins:

```bash
python3 scripts/install_codex_skills.py --scope project --update
```

For selected plugins:

```bash
python3 scripts/install_codex_skills.py \
  --scope project \
  --plugins <plugin-1>,<plugin-2> \
  --update
```

`--update` is an alias of `--force`.

### User-scoped install (shared across repos)

```bash
python3 scripts/install_codex_skills.py --scope user
```

Targets:

- Skills: `~/.agents/skills/`
- Config: `~/.codex/config.toml`

### Useful flags

- `--mode symlink` for local development (live updates from repo checkout)
- `--force` to replace existing installed skills
- `--update` same as `--force` (remove and reinstall existing skills/roles)
- `--dry-run` to preview actions
- `--no-config-update` to skip editing `config.toml`
- `--no-install-agents` to skip agent role installation
- `--agents-dir <path>` to override where generated agent role TOML files are written
- `--absolute-config-paths` to write absolute paths in config

## Project-Specific Agent Instructions

Codex supports project-specific instructions under `./.codex/` and `AGENTS.md`.

### 1) Project guidance via `AGENTS.md`

At repo root:

```bash
codex
# then run /init
```

Or create manually:

```md
# AGENTS.md
## Repo conventions
- Prefer relative paths
- Run tests before commit
```

### 2) Role-specific agent instructions via `./.codex/config.toml`

Example:

```toml
[features]
multi_agent = true

[agents.reviewer]
description = "Find correctness and test risks"
config_file = "agents/reviewer.toml"
```

And `./.codex/agents/reviewer.toml`:

```toml
model = "gpt-5.3-codex"
model_reasoning_effort = "high"
developer_instructions = "Focus on bugs, regressions, and missing tests."
```

`config_file` is resolved relative to the config file that declares it, so project-local `./.codex/agents/*.toml` works.

## Verification Checklist

1. Start Codex from repo root.
2. Ask Codex to list active instructions and available skills.
3. Confirm project is trusted if `.codex/config.toml` changes do not apply.

## Notes

- Codex discovers skills from `.agents/skills` automatically; `[[skills.config]]` entries are useful for explicit enable/disable control.
- If a skill has hard-coded Claude paths (for example `.claude/skills/...`), update those commands to your installed skill paths.
