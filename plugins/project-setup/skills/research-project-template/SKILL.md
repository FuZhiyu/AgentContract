---
name: research-project-template
description: Create new academic research projects with two-folder architecture. Use when user wants to create a new research project, start a new paper, set up a new analysis project, or mentions needing a project structure for research.
user-invocable: true
---

# Research Project Template

Automatically create new research projects with the standard two-folder architecture.

## When to Use

Use this skill when the user:
- Wants to create a new research project
- Asks to set up a new paper/analysis
- Mentions starting a new research project
- Needs a project structure for academic research

## Architecture

The template creates two folders:

1. **Git Repository** (`ProjectName/`):
   - `Code/` - Analysis scripts (Julia, Python, R)
   - `Figures/` - Final figures for publication
   - `Tables/` - Final tables for publication
   - `Paper/` - LaTeX documents
   - `Slides/` - Presentations
   - Symlinks to shared folders

2. **Shared Folder** (`ProjectName-Share/`):
   - `Notes/` - Research notes, working journals
   - `Data/` - Raw and processed datasets
   - `Output/` - Intermediate results

This separation allows Git to track code while Dropbox handles large data files.

## Workflow

### Step 1: Get Project Details

Ask the user for:
1. Project name (e.g., `IntermediaryDemand`)
2. Location for the project (defaults to config or current directory)

### Step 2: Check Configuration

Read config from shared config loader to get:
- `template_path`: Path to ResearchProjectTemplate
- `default_share_location`: Where to create projects

```python
from _config_loader import load_config

config = load_config('project-setup')
template_path = config.get('template_path')
share_location = config.get('default_share_location', '.')
```

### Step 3: Run Creation Script

Execute the project creation script:

```bash
cd /path/to/target/location
bash "${CLAUDE_PLUGIN_ROOT}/scripts/create_project.sh" "ProjectName"
```

The script will:
1. Create `ProjectName-Share/` with Notes, Data, Output directories
2. Create `ProjectName/` with Code, Figures, Tables, Paper, Slides
3. Set up Python environment with uv
4. Create symlinks between the two folders
5. Initialize git repository
6. Copy Claude configuration (.claude folder with agents/skills)

### Step 4: Post-Creation

Inform the user:
1. Project structure created successfully
2. How to share with collaborators (Dropbox for Share folder, Git for code)
3. Next steps: start coding in `Code/` directory

## Configuration

The plugin reads from `.claude/agent-contract.yaml` or `~/.config/agent-contract/config.yaml`:

```yaml
project-setup:
  template_path: "/path/to/ResearchProjectTemplate"
  default_share_location: "~/Dropbox/package_dev"
```

## Example

**User:** "I want to create a new research project called RiskPremia"

**Workflow:**
1. Check config for template_path and default_share_location
2. Run: `bash create_project.sh RiskPremia`
3. Report success with project structure

## Notes

- The script requires macOS (uses `sed -i ''` syntax)
- Requires `uv` for Python environment management (installed via Homebrew)
- Creates initial git commit automatically
- Copies Claude agents and skills to new project
