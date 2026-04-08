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

This repo already includes a Codex marketplace at [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json). That is the object Codex discovers. The individual installable packages are the plugin folders under [`plugins/`](plugins/), each with its own [`.codex-plugin/plugin.json`](plugins/project-setup/.codex-plugin/plugin.json).

Per the official Codex docs, local plugins are discovered through either:

- a repo marketplace at `$REPO_ROOT/.agents/plugins/marketplace.json`
- a personal marketplace at `~/.agents/plugins/marketplace.json`

Codex installs local plugins into `~/.codex/plugins/cache/<marketplace>/<plugin>/local/`, and stores enable/disable state in `~/.codex/config.toml`.

Official references:

- https://developers.openai.com/codex/plugins/build#how-codex-uses-marketplaces
- https://developers.openai.com/codex/plugins/build#marketplace-metadata
- https://developers.openai.com/codex/plugins/build#install-a-local-plugin-manually

### Repo-scoped Codex install

This is the simplest path if you want to use the current checkout as the marketplace.

1. Clone this repository locally.
2. Open the repo root in Codex.
3. Restart Codex so it reloads [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json).
4. Open the plugin directory in Codex with `/plugins` or the Plugins panel.
5. Choose the marketplace `AgentContract Local Plugins`.
6. Install the plugin you want.

Notes:

- The marketplace name is `agent-contract-local`; the user-facing title is `AgentContract Local Plugins`.
- The `source.path` entries in the marketplace are resolved relative to the repo root, not relative to `.agents/plugins/`.
- If you change a plugin manifest or skill and the update does not appear, restart Codex. If the install still looks stale, disable and reinstall the plugin from the plugin directory.

Bundled skills are available after plugin install. Workflows that depend on standalone reviewer or worker roles still require the advanced installer in [CODEX_INSTALL.md](CODEX_INSTALL.md).

### Personal Codex marketplace

Use this when you want the current repo to appear as a marketplace across repositories instead of only when Codex is opened inside this checkout.

1. Keep a stable local checkout of this repo somewhere under your home directory.
2. Create `~/.agents/plugins/marketplace.json`.
3. Point each plugin entry's `source.path` at that checkout using a `./`-prefixed path relative to your home directory.
4. Restart Codex and install from that personal marketplace.

Example for a single plugin:

```json
{
  "name": "agent-contract-personal",
  "interface": {
    "displayName": "AgentContract Personal"
  },
  "plugins": [
    {
      "name": "project-setup",
      "source": {
        "source": "local",
        "path": "./path/to/AgentContract/plugins/project-setup"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Research"
    }
  ]
}
```

Important:

- Replace `./path/to/AgentContract/...` with a path relative to your home directory if you store the marketplace at `~/.agents/plugins/marketplace.json`.
- Do not copy this repo's existing marketplace file directly into `~/.agents/plugins/marketplace.json` without rewriting the `source.path` values. The shipped repo marketplace assumes the marketplace root is the repo root.
- Once the single-plugin version works, expand `plugins[]` to mirror the full list from [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json).

### How another user should install this marketplace

If you want another user to add this marketplace on their own machine, the reliable flow is:

1. Have them clone this repository somewhere under their home directory, for example `~/code/AgentContract` or `~/Dropbox/package_dev/EconResearchPlugins`.
2. Have them create or update `~/.agents/plugins/marketplace.json` on their machine.
3. In that personal marketplace file, point each plugin entry at their own local checkout using a `./`-prefixed path relative to their home directory.
4. Restart Codex.
5. Open `/plugins`, choose the personal marketplace, and install the desired plugin.

Two common examples:

- If they cloned to `~/code/AgentContract`, use paths like `./code/AgentContract/plugins/project-setup`.
- If they cloned to `~/Dropbox/package_dev/EconResearchPlugins`, use paths like `./Dropbox/package_dev/EconResearchPlugins/plugins/project-setup`.

What to send another user:

- The repository URL or checkout instructions.
- A note telling them where to clone it on their machine.
- A personal marketplace JSON snippet whose `source.path` values match that clone location.

What not to send another user unchanged:

- Your own `~/.agents/plugins/marketplace.json`.
- This repo's [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json).

Those files are only correct for the machine and marketplace root they were written for.

### Validate manifests before release

```bash
python3 scripts/validate_plugin_manifests.py
```

### Advanced Codex fallback

Use [CODEX_INSTALL.md](CODEX_INSTALL.md) only when you need standalone agent roles installed into `.codex/agents` or you want the older copy/symlink skill installer flow.

### Codex troubleshooting

- If the marketplace does not appear at all, verify that Codex was restarted after adding or editing the marketplace JSON.
- If the marketplace appears but a plugin does not, validate the repo with `python3 scripts/validate_plugin_manifests.py`.
- If a personal marketplace cannot find the plugin, the `source.path` is probably being interpreted relative to the wrong root.
- If a plugin installs but behaves like an older version, reinstall after restarting so Codex refreshes the local cached copy.

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
