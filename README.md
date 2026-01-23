# Econ Research Plugins

A Claude Code plugin marketplace for academic research workflows.

## Available Plugins

| Plugin | Description |
|--------|-------------|
| `project-setup` | Create research projects with two-folder architecture |
| `zotero-connector` | Read papers from Zotero library |
| `pdf2markdown-converter` | Convert PDFs to markdown via Mistral OCR |
| `pdf-tools` | PDF manipulation: merge, split, extract, forms |
| `work-journal` | Working journal and documentation quality |
| `worktree-manager` | Git worktree for parallel development |

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

### pdf-tools
- Merge, split PDFs
- Extract text and tables
- Fill PDF forms

### work-journal
- Create factual working journal entries
- Review code for research correctness
- Validate documentation accuracy
- Summarize analysis results

### worktree-manager
- Create isolated git worktrees
- COW-clone non-git-tracked content (Data/, Output/)
- Sandbox isolation for experiments
