# pdf2markdown-converter

Convert PDFs to Markdown using the Mistral OCR API with automatic image extraction.

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) (dependencies auto-install via PEP 723 inline metadata)
- **Mistral API key** — provide via one of:
  1. Environment variable: `export MISTRAL_API_KEY=your-key`
  2. Config file: `.claude/econ-research.yaml` → `paper-reader.mistral_api_key`
  3. `Notes/.env` file: `MISTRAL_API_KEY=your-key`

## Install

```bash
/plugin install pdf2markdown-converter@FuZhiyu-AgentContract
```

## Usage

Invoke the `mistral-pdf-to-markdown` skill in Claude Code, or run the script directly:

```bash
uv run plugins/pdf2markdown-converter/scripts/convert_pdf_to_markdown.py input.pdf output.md
uv run plugins/pdf2markdown-converter/scripts/convert_pdf_to_markdown.py input.pdf output.md --pages "1-5"
```
