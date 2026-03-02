# EconResearchPlugins

A Claude Code plugin marketplace providing tools for academic research workflows. Each plugin is self-contained and can be installed independently.

## Structure

```
plugins/           # Individual plugins, each with its own .claude-plugin/
  ├── project-setup/
  ├── zotero-connector/
  ├── pdf2markdown-converter/
  ├── work-journal/
  ├── worktree-data-sync/
  ├── draft-reviewer/
  └── review-doc-commit/
shared/            # Shared utilities used across plugins
  └── config.py    # Config loader for .claude/econ-research.yaml
```

## Conventions

### Plugin Structure

Each plugin follows this layout:
```
plugin-name/
├── .claude-plugin/
│   └── plugin.json      # Plugin metadata, hooks, permissions
├── skills/
│   ├── skill-name.skill # Skill bundle (ZIP) for distribution
│   └── skill-name/
│       ├── SKILL.md     # Skill instructions
│       └── references/  # Supporting files
├── agents/              # Subagent definitions (optional)
├── scripts/             # Executable scripts (bash, python)
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
- Skill names should describe the action (e.g., `work-summary`, `draft-review`)
- Agent names use kebab-case with descriptive suffixes (e.g., `mathematical-reviewer`)

### Subagent Types
- Register subagents as `plugin-name:agent-name` (e.g., `draft-reviewer:mathematical-reviewer`)
- Define agent instructions in `agents/agent-name.md`

### Scripts
- Prefer Python for complex logic, bash for simple file operations
- Scripts should be executable (`chmod +x`)
- Use `${CLAUDE_PLUGIN_ROOT}` to reference plugin directory

## Development

### Creating a New Plugin

1. Create directory under `plugins/`
2. Add `.claude-plugin/plugin.json` with name, description, author
3. Add skills in `skills/skill-name/SKILL.md`
4. Build skill bundle: zip the skill directory into `skill-name.skill`

### Testing

Install locally:
```bash
claude /plugin install /path/to/EconResearchPlugins/plugins/plugin-name
```

### Shared Config

Plugins read config from `.claude/econ-research.yaml` (project) or `~/.config/econ-research/config.yaml` (global):

```python
import sys
sys.path.insert(0, "${CLAUDE_PLUGIN_ROOT}/../../shared")
from config import load_config

config = load_config('plugin-name')
```

## Key Plugins

| Plugin | Type | Description |
|--------|------|-------------|
| `project-setup` | Skill | Creates two-folder research project structure |
| `work-journal` | Skill + Agent | Working journal entries with quality validation |
| `draft-reviewer` | Skill + Agents | Multi-agent paper review system |
| `review-doc-commit` | Skill | Code review, docs, and topical git commits |
| `worktree-data-sync` | Skill | Sync non-git data across existing worktrees |
