# AgentContract

Skills and agents designed for academic research workflows, econ-flavored. Made by Claude, for Claude. For Codex, see below for installation instructions. 

## Available Skills

| Skills | Description |
|--------|-------------|
| `worktree-data-sync` | multi-agent work in parallel in different worktrees with isolated data |
| `work-journal` | Teach agents how to document and report the results |
| `draft-reviewer` | Comprehensive review of a paper draft. Even better, it can fixes things |
| `review-doc-commit` | Make sure we commit the right stuff |
| `zotero-connector` | Read papers from Zotero library |
| `pdf2markdown-converter` | Convert PDFs to markdown via Mistral OCR |

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [`uv`](https://docs.astral.sh/uv/) — Python scripts use PEP 723 inline metadata for auto-installing dependencies
- API keys per plugin (see individual plugin docs)

## Installation

### From GitHub

```bash
# Add marketplace
/plugin marketplace add FuZhiyu/AgentContract

# Install individual plugins
/plugin install zotero-connector@FuZhiyu-AgentContract
/plugin install pdf2markdown-converter@FuZhiyu-AgentContract
/plugin install work-journal@FuZhiyu-AgentContract
```

### Direct Installation (local development)

```bash
/plugin install ./plugins/zotero-connector
```

## Updating Plugins

```bash
# Update marketplace listing
/plugin marketplace update FuZhiyu-AgentContract
```

## Configuration

Create `.claude/agent-contract.yaml` (per-project) or `~/.config/agent-contract/config.yaml` (global):

```yaml
paper-reader:
  mistral_api_key: "sk-..."
  zotero_api_key: "..."
  zotero_library_type: "user"
  zotero_library_id: "12345"
```

## Plugin Details

### zotero-connector
- Search Zotero by title/author/topic
- Download PDFs from local storage or web API
- Integrates with pdf2markdown-converter
- **Requires:** Zotero API key, library ID

### pdf2markdown-converter
- Convert PDFs to markdown using Mistral OCR
- Extract images to separate folder
- Great for scanned documents
- **Requires:** Mistral API key

### work-journal
- `work-journal` skill: formal, fact-checked journal entries with citations and report-checker verification
- `report-in-markdown` skill: pure IO tool for saving markdown reports (no content rules)
- Agents: code-reviewer, report-checker, results-summarizer

### worktree-data-sync
- Sync non-git files between existing worktrees
- Seed missing managed files from one worktree to another
- Diff and apply overwrite/rename actions for managed data

### draft-reviewer
- Multi-agent paper review system
- Specialized agents: mathematical, writing, consistency, proofreading, citations
- Supports quick, standard, and deep (parallel) thoroughness levels
- Integrates with pdf2markdown-converter for PDF input

### review-doc-commit
- Two-agent code review: implementation correctness + integration/consistency
- Ensure CLAUDE.md coverage for all directories with AGENTS.md symlinks
- Hard gate: no commit until review is clean
- Group changes into topical commits

## Codex

Tell Codex:

> Fetch and follow instructions from https://raw.githubusercontent.com/FuZhiyu/AgentContract/main/CODEX_INSTALL.md

Detailed docs: [CODEX_INSTALL.md](CODEX_INSTALL.md)

## License

[MIT](LICENSE)
