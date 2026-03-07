# project-setup

Create new research projects with two-folder architecture.

## Features

- Creates Git repository for code (`ProjectName/`)
- Creates shared folder for data (`ProjectName-Share/`)
- Sets up Python environment with uv
- Initializes git with first commit
- Copies Claude agents and skills

## Usage

Say something like:
- "Create a new research project called RiskPremia"
- "I want to start a new paper on market microstructure"
- "Set up a new analysis project"

## Configuration

Add to `.claude/agent-contract.yaml`:

```yaml
project-setup:
  template_path: "/path/to/ResearchProjectTemplate"
  default_share_location: "~/Dropbox/package_dev"
```

## Project Structure

```
ProjectName/                 # Git repository
├── Code/                   # Analysis scripts
├── Figures/                # Publication figures
├── Tables/                 # Publication tables
├── Paper/                  # LaTeX documents
├── Slides/                 # Presentations
├── Notes -> ../Share/Notes # Symlink
├── Data -> ../Share/Data   # Symlink
└── Output -> ../Share/Output

ProjectName-Share/          # Dropbox folder
├── Notes/                  # Research notes
├── Data/                   # Datasets
└── Output/                 # Results
```
