# AgentContract

A plugin workspace for academic research workflows across Claude Code and Codex. Each plugin is self-contained and can be installed independently.

## Structure

```
plugins/           # Individual plugins, each with its own plugin manifest directory
  ├── project-setup/
  ├── zotero-connector/
  ├── pdf2markdown-converter/
  ├── work-journal/
  ├── worktree-data-sync/
  ├── draft-reviewer/
  ├── review-doc-commit/
  └── wrds-data/
shared/            # Shared utilities (canonical reference; each plugin carries its own copy)
  └── config.py    # Config loader for .claude/agent-contract.yaml
```

## Conventions

### Plugin Structure

Each plugin follows this layout:
```
plugin-name/
├── .claude-plugin/
│   └── plugin.json      # Claude plugin metadata, hooks, permissions
├── .codex-plugin/
│   └── plugin.json      # Codex plugin metadata and interface fields
├── skills/
│   └── skill-name/
│       ├── SKILL.md     # Skill instructions
│       ├── scripts/     # Executable scripts co-located with the skill
│       │   └── _config_loader.py  # Self-contained config loader (copy of shared/config.py)
│       └── references/  # Supporting files
├── agents/              # Subagent definitions (optional)
└── hooks/               # Hook scripts (optional)
```

### SKILL.md Frontmatter

```yaml
---
name: skill-name
description: One-line description for skill matching
user-invocable: true  # Set false for internal-only skills
---
```

### Plugin Naming
- Use kebab-case for plugin and skill names
- Skill names should describe the action (e.g., `work-journal`, `draft-review`)
- Agent names use kebab-case with descriptive suffixes (e.g., `mathematical-reviewer`)

### Agent Frontmatter

Agent markdown files require YAML frontmatter:
```yaml
---
name: agent-name
description: What this agent does
tools: [Read, Grep, Glob, Bash]
---
```

### Subagent Types
- Register subagents as `plugin-name:agent-name` (e.g., `draft-reviewer:mathematical-reviewer`)
- Define agent instructions in `agents/agent-name.md` for standalone reusable agents
- Lightweight subagents (e.g., review checklists) may be defined inline in SKILL.md

### Scripts
- Prefer Python for complex logic, bash for simple file operations
- Scripts should be executable (`chmod +x`)
- Python scripts with external dependencies use PEP 723 inline metadata + `#!/usr/bin/env -S uv run --script` shebang for self-installing deps
- **Script location:** Place scripts inside the skill directory at `skills/skill-name/scripts/` so they are co-located with the SKILL.md that references them
- **SKILL.md invocations** — use `${CLAUDE_SKILL_DIR}` (resolves to the directory containing the SKILL.md):
  - Scripts with external deps: `uv run python ${CLAUDE_SKILL_DIR}/scripts/script.py`
  - Scripts without external deps: `python3 ${CLAUDE_SKILL_DIR}/scripts/script.py`
  - Inline one-liners needing external packages: `uv run --with <pkg> python -c "..."`
- `${CLAUDE_PLUGIN_ROOT}` is available in hooks and MCP configs but **not** in SKILL.md content
- Each plugin carries its own `_config_loader.py` (do NOT use `sys.path` hacks to reach `shared/`)

## Development

### Creating a New Plugin

1. Create directory under `plugins/`
2. Add `.claude-plugin/plugin.json` with name, description, author, license, repository, keywords
3. Add skills in `skills/skill-name/SKILL.md`
4. If the plugin has Python scripts with external deps, add PEP 723 metadata
5. Copy `shared/config.py` as `skills/skill-name/scripts/_config_loader.py` if config access is needed

### Releasing Changes

Always bump shipped plugin manifest versions before pushing. Claude Code caches by version, and Codex plugin manifests should stay in sync with the corresponding Claude manifest. Also bump the Claude marketplace version in `.claude-plugin/marketplace.json` when published marketplace entries change, and keep `.agents/plugins/marketplace.json` aligned with the repo-scoped Codex marketplace contents.

### Testing

Install locally:
```bash
claude /plugin install ./plugins/plugin-name
```

### Shared Config

Plugins read config from `.claude/agent-contract.yaml` (project) or `~/.config/agent-contract/config.yaml` (global). Each plugin uses its own `_config_loader.py` copy:

```python
from _config_loader import load_config
config = load_config('plugin-name')
```

The canonical reference is `shared/config.py`. When updating config logic, sync changes to each plugin's `skills/skill-name/scripts/_config_loader.py`.

## Key Plugins

| Plugin | Type | Description |
|--------|------|-------------|
| `zotero-connector` | Skill | Read papers from Zotero library |
| `pdf2markdown-converter` | Skill | Convert PDFs to markdown via Mistral OCR |
| `work-journal` | Skills + Agents | Formal work journal entries and markdown report IO |
| `draft-reviewer` | Skill + Agents | Multi-agent paper review system |
| `review-doc-commit` | Skill + Agents | Parallel review, documentation, and topical git commits |
| `worktree-data-sync` | Skill | Sync non-git data across existing worktrees |
| `wrds-data` | Skill | Search and download financial data from WRDS (CRSP, Compustat, IBES, etc.) |
| `project-setup` | Skill | Creates two-folder research project structure; repo-local on Claude and included in the repo-scoped Codex marketplace |
