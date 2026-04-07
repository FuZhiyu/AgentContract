# AgentContract

Academic research plugins and skills for both Claude Code and Codex. Claude marketplace support stays intact. Codex support now includes repo-scoped plugin manifests and a local marketplace for private or team distribution.

## Available Plugins

| Plugin | Description |
|--------|-------------|
| `project-setup` | Create a new research project with the expected repo/share structure |
| `zotero-connector` | Read papers from Zotero and summarize them in Markdown |
| `pdf2markdown-converter` | Convert PDFs to Markdown with Mistral OCR and image extraction |
| `work-journal` | Write formal work journals or quick Markdown reports for completed analysis |
| `draft-reviewer` | Run structured academic draft review across writing, math, and citations |
| `worktree-data-sync` | Compare and sync non-git data between existing worktrees |
| `review-doc-commit` | Review changes, update docs, and prepare topical git commits |

## Codex

Codex plugin distribution in this repo is currently aimed at private or team use through a repo-scoped marketplace. Official public Codex directory publishing is not self-serve yet.

### Preferred Codex install path

1. Clone this repository locally.
2. Open the repo in Codex.
3. Restart Codex so it reloads the repo marketplace at `.agents/plugins/marketplace.json`.
4. Open the Plugins panel or run `/plugins`.
5. Select the `AgentContract Local Plugins` marketplace.
6. Install the plugin you want.

Bundled skills are available immediately after plugin install. Workflows that depend on standalone reviewer/worker roles still require the advanced installer in [CODEX_INSTALL.md](CODEX_INSTALL.md).

### Validate manifests before release

```bash
python3 scripts/validate_plugin_manifests.py
```

### Advanced Codex fallback

Use [CODEX_INSTALL.md](CODEX_INSTALL.md) only when you need standalone agent roles installed into `.codex/agents` or you want the older copy/symlink skill installer flow.

## Claude Code

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [`uv`](https://docs.astral.sh/uv/) for skill scripts with PEP 723 inline dependencies
- API keys per plugin where required

### Install from the Claude marketplace

```bash
# Add marketplace
/plugin marketplace add FuZhiyu/AgentContract

# Install individual plugins
/plugin install zotero-connector@FuZhiyu-AgentContract
/plugin install pdf2markdown-converter@FuZhiyu-AgentContract
/plugin install work-journal@FuZhiyu-AgentContract
```

`project-setup` is currently repo-local/direct install only on the Claude side.

### Direct installation for local development

```bash
/plugin install ./plugins/zotero-connector
/plugin install ./plugins/project-setup
```

### Update the Claude marketplace listing

```bash
/plugin marketplace update FuZhiyu-AgentContract
```

## Shared Configuration

Several plugins read shared config from `.claude/agent-contract.yaml` (project) or `~/.config/agent-contract/config.yaml` (global):

```yaml
paper-reader:
  mistral_api_key: "sk-..."
  zotero_api_key: "..."
  zotero_library_type: "user"
  zotero_library_id: "12345"
```

Some plugins also support environment-variable alternatives. Check the plugin-specific README where needed.

## Plugin Notes

- `zotero-connector`: requires Zotero credentials and integrates with `pdf2markdown-converter`.
- `zotero-connector`: Codex v1 assumes Zotero tools are already available in the session, or that the user can supply an attachment key/local PDF path.
- `pdf2markdown-converter`: requires a Mistral API key.
- `work-journal`: ships `work-journal` and `report-in-markdown`; standalone review roles remain on the advanced installer path for Codex.
- `draft-reviewer`: ships the review skill in the Codex plugin and keeps standalone reviewer agents on the advanced installer path.
- `review-doc-commit`: Codex plugin ships the main skill; standalone agents stay installer-managed.

## License

[MIT](LICENSE)
