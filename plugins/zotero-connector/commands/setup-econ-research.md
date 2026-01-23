---
description: Configure API keys for econ-research plugins
allowed-tools: [Read, Write, Bash, AskUserQuestion]
---

# Setup Econ Research Configuration

Create or update the configuration file for econ-research plugins.

## Workflow

### Step 1: Check existing config

Check if config already exists:
- `.claude/econ-research.yaml` (project-specific)
- `~/.config/econ-research/config.yaml` (global)

### Step 2: Ask for configuration location

Ask user where to store config:
1. Project-specific (`.claude/econ-research.yaml`) - Recommended for project-specific settings
2. Global (`~/.config/econ-research/config.yaml`) - For shared settings across all projects

### Step 3: Collect API keys

Ask user for:
1. Mistral API key (for PDF-to-markdown conversion)
2. Zotero API key (for paper reading)
3. Zotero library type (user or group)
4. Zotero library ID

### Step 4: Write config file

Create the YAML config file:

```yaml
paper-reader:
  mistral_api_key: "USER_PROVIDED_KEY"
  zotero_api_key: "USER_PROVIDED_KEY"
  zotero_library_type: "user"
  zotero_library_id: "USER_PROVIDED_ID"

project-setup:
  template_path: "/path/to/ResearchProjectTemplate"
  default_share_location: "~/Dropbox/package_dev"
```

### Step 5: Verify

Confirm the config was written and remind user:
- Config location
- How to edit later
- That changes take effect immediately for scripts

## Example Config

```yaml
# .claude/econ-research.yaml

paper-reader:
  mistral_api_key: "sk-..."
  zotero_api_key: "..."
  zotero_library_type: "user"
  zotero_library_id: "12345678"

project-setup:
  template_path: "/Users/you/Dropbox/package_dev/ResearchProjectTemplate"
  default_share_location: "~/Dropbox/package_dev"
```
