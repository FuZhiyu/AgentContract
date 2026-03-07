# zotero-connector

Read and analyze academic papers from your Zotero library. Searches by title/author/topic, retrieves PDFs (local storage first, then Zotero API), and integrates with pdf2markdown-converter.

## Prerequisites

- **Zotero API key** — get one at https://www.zotero.org/settings/keys
- **Zotero library ID** — your numeric user/group ID

Provide via `.claude/econ-research.yaml` or `~/.config/econ-research/config.yaml`:

```yaml
paper-reader:
  zotero_api_key: "your-key"
  zotero_library_type: "user"
  zotero_library_id: "12345"
```

Or via `Notes/.env`:

```
ZOTERO_API_KEY=your-key
ZOTERO_LIBRARY_TYPE=user
ZOTERO_LIBRARY_ID=12345
```

## Install

```bash
claude /plugin install zotero-connector@agent-contract
```

## Usage

Invoke the `zotero-paper-reader` skill in Claude Code. It will search your library, download the PDF, convert to markdown, and provide analysis.
