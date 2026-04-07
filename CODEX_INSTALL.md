# Codex Advanced Install Guide

**This file is meant to be read by an agent (Codex).** Use it for the advanced fallback path when you need standalone agent roles or manual skill installation.

For most users, the preferred Codex path is now the repo marketplace:

1. Clone the repository.
2. Open it in Codex.
3. Restart Codex so it reloads `.agents/plugins/marketplace.json`.
4. Open the Plugins panel or run `/plugins`.
5. Choose `AgentContract Local Plugins`.
6. Install the plugin you want.

That marketplace path installs bundled skills only. If you want standalone reviewer/worker roles such as `draft-reviewer__mathematical-reviewer` or `work-journal__report-checker`, use this advanced installer.

This guide remains for the advanced fallback path: install skills into `.agents/skills` and install standalone reviewer/worker roles into `.codex/agents`.

## What This Supports

This guide covers the advanced fallback installer only. It can:

- Install plugin skills into project-local `./.agents/skills/` (or user `~/.agents/skills/`)
- Update Codex config with `[[skills.config]]` entries
- Install plugin agents as Codex roles:
  - write role files to `./.codex/agents/*.toml` (or `~/.codex/agents/*.toml`)
  - add `[agents.<role>]` entries in `config.toml`
  - enable `[features].multi_agent = true`
  - register role names in `plugin__agent` form; these are the `agent_type` values Codex uses when spawning
- Keep setup project-specific by default (`./.codex/config.toml`)

## Dynamic Discovery

The installer discovers everything directly from the repo:

- Plugins: `plugins/*/.codex-plugin/plugin.json` (`name`), falling back to `plugins/*/.claude-plugin/plugin.json`
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

When an agent is asked to use the advanced installer for this repo, it must follow this flow:

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

### Installing from Inside AgentContract

Run from repo root:

```bash
python3 scripts/install_codex_skills.py --scope project
```

The script auto-detects the current directory as both `--source-repo` (plugin discovery) and `--target-root` (install destination).

### Installing into Another Project

When the AgentContract repo and the target project are different directories, use `--source-repo` and `--target-root`:

```bash
python3 /path/to/AgentContract/scripts/install_codex_skills.py \
  --source-repo /path/to/AgentContract \
  --target-root . \
  --scope project \
  --plugins all
```

Preview what will happen first:

```bash
python3 /path/to/AgentContract/scripts/install_codex_skills.py \
  --source-repo /path/to/AgentContract \
  --target-root . \
  --scope project \
  --dry-run
```

### If an Agent Needs to Fetch the Repo First

```bash
git clone <REPO_URL> AgentContract
python3 AgentContract/scripts/install_codex_skills.py \
  --source-repo AgentContract \
  --target-root . \
  --list --json > /tmp/codex_plugin_inventory.json
```

Then install using the discovered set (no static list):

```bash
python3 AgentContract/scripts/install_codex_skills.py \
  --source-repo AgentContract \
  --target-root . \
  --scope project
```

Suggested agent instruction:

```text
Clone the AgentContract repo, run:
python3 AgentContract/scripts/install_codex_skills.py --source-repo AgentContract --list --json
Use that discovered inventory (plugins/skills/agents) as the source of truth,
then run installation with --source-repo AgentContract --target-root . --scope project.
Do not hardcode plugin or skill names.
```

### Default advanced install (project-scoped)

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
