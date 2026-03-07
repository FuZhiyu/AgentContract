# AgentContract

A Claude Code plugin marketplace for academic research workflows.

## Available Plugins

| Plugin | Description |
|--------|-------------|
| `zotero-connector` | Read papers from Zotero library |
| `pdf2markdown-converter` | Convert PDFs to markdown via Mistral OCR |
| `work-journal` | Formal work journal entries and markdown report IO |
| `worktree-data-sync` | Sync non-git data across existing worktrees |
| `draft-reviewer` | Multi-agent academic paper review |
| `review-doc-commit` | Review code, update docs, and create topical commits |

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [`uv`](https://docs.astral.sh/uv/) — Python scripts use PEP 723 inline metadata for auto-installing dependencies
- API keys per plugin (see individual plugin docs)

## Installation

### From GitHub

```bash
# Add marketplace
claude /plugin marketplace add FuZhiyu/AgentContract

# Install individual plugins
claude /plugin install zotero-connector@agent-contract
claude /plugin install pdf2markdown-converter@agent-contract
claude /plugin install work-journal@agent-contract
```

### Direct Installation (local development)

```bash
claude /plugin install ./plugins/zotero-connector
```

## Updating Plugins

```bash
# Update a single plugin
claude plugin update zotero-connector@agent-contract

# Update all plugins from this marketplace
claude /plugin marketplace update agent-contract
```

## Configuration

Create `.claude/econ-research.yaml` (per-project) or `~/.config/econ-research/config.yaml` (global):

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

## For Codex CLI Users

See [CODEX_INSTALL.md](CODEX_INSTALL.md) for installation instructions with OpenAI Codex.

## License

[MIT](LICENSE)
