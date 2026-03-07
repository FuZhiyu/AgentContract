# Econ Research Plugins

A Claude Code plugin marketplace for academic research workflows.

## Available Plugins

| Plugin | Description |
|--------|-------------|
| `project-setup` | Create research projects with two-folder architecture |
| `zotero-connector` | Read papers from Zotero library |
| `pdf2markdown-converter` | Convert PDFs to markdown via Mistral OCR |
| `work-journal` | Formal work journal entries and markdown report IO |
| `worktree-data-sync` | Sync non-git data across existing worktrees |
| `draft-reviewer` | Multi-agent academic paper review |
| `review-doc-commit` | Review code, update docs, and create topical commits |

## Installation

### Register Marketplace

```bash
claude /plugin marketplace add /path/to/EconResearchPlugins

# Install plugins by name
claude /plugin install zotero-connector@econ-research-plugins
claude /plugin install work-journal@econ-research-plugins
```

### Direct Installation

```bash
claude /plugin install /path/to/EconResearchPlugins/plugins/zotero-connector
```

## Configuration

Create `.claude/econ-research.yaml` (per-project) or `~/.config/econ-research/config.yaml` (global):

```yaml
paper-reader:
  mistral_api_key: "sk-..."
  zotero_api_key: "..."
  zotero_library_type: "user"
  zotero_library_id: "12345"

project-setup:
  template_path: "/path/to/ResearchProjectTemplate"
  default_share_location: "~/Dropbox/package_dev"
```

## Plugin Details

### project-setup
Creates new research projects with:
- Git repo for code, figures, tables, papers
- Dropbox folder for notes, data, outputs
- Python environment, Claude agents

### zotero-connector
- Search Zotero by title/author/topic
- Download PDFs from local storage or web API
- Integrates with pdf2markdown-converter

### pdf2markdown-converter
- Convert PDFs to markdown using Mistral OCR
- Extract images to separate folder
- Great for scanned documents

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

