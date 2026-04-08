# Jupytext Percent Format Guide

How to write, render, and manage analysis scripts in jupytext percent format.

## Why percent format

- **Git-friendly**: `.py`/`.jl` files diff cleanly; notebooks do not
- **Human-readable**: code + narrative in one file, no JSON wrapping
- **Executable**: runs as a normal script or converts to a notebook
- **Same syntax** for Python and Julia

## Writing Scripts

### Cell markers

```
# %%                        ← code cell
# %% [markdown]             ← narrative cell
# %% Optional title         ← named code cell
```

### Markdown cells

Line-comment style:
```python
# %% [markdown]
# ## Section Heading
#
# Narrative text.
```

Triple-quote style (more readable for longer blocks):
```python
# %% [markdown]
"""
## Section Heading

Longer narrative with multiple paragraphs. Preferred when the explanation
is more than a few lines.
"""
```

### Python example

```python
# %% [markdown]
"""
# Portfolio Analysis
Load holdings data and verify dimensions before any transformation.
"""

# %%
import pandas as pd
df = pd.read_parquet("Data/holdings.parquet")
print(f"Shape: {df.shape}")
df.describe(percentiles=[.01, .05, .25, .5, .75, .95, .99])

# %% [markdown]
"""
## Merge with Fund Characteristics
Left join on fund_id × date. Fund characteristics are at fund-date level (m:1).
Expect same row count after merge.
"""

# %%
n_before = len(df)
df = df.merge(chars, on=["fund_id", "date"], how="left")
print(f"Rows: {n_before} → {len(df)} (delta: {len(df) - n_before})")
df[["market_value", "weight"]].describe()
```

### Julia example

```julia
# %% [markdown]
# # Portfolio Analysis
# Load holdings data and verify dimensions.

# %%
using DataFrames, CSV
df = CSV.read("Data/holdings.csv", DataFrame)
println("Shape: ", size(df))
describe(df)

# %% [markdown]
# ## Filter to Active Funds
# Drop funds with zero AUM. Log how many rows are removed.

# %%
n_before = nrow(df)
df = filter(:aum => >(0), df)
println("Rows: $n_before → $(nrow(df)) (dropped: $(n_before - nrow(df)))")
```

### Best practices

1. **One cell per logical operation** — load, merge, filter, construct, describe
2. **Markdown cell before each operation** explaining what and why
3. **Last expression displays as output** — use this for diagnostics
   (e.g., end a cell with `df.describe()` or `describe(df)`)
4. **`print()`/`println()` for explicit output** — row counts, shape, messages
5. **After sample-changing operations**, display the new row count
6. **Major decisions** get a markdown cell with reasoning

## Rendering and Execution

**Important**: Execution requires a Jupyter kernel, which binds local sockets.
In Claude Code, the sandbox blocks socket binding. Two options:
1. Suggest the user type `! uv run jupytext ...` in the Claude Code prompt
   (the `!` prefix runs the command in the user's shell, bypassing the sandbox)
2. Run with sandbox disabled (Claude Code will prompt the user for permission)

### Single command (recommended)

Convert and execute in one step. The `--set-kernel` flag is required to match
the installed Jupyter kernel spec (list specs with `jupyter kernelspec list`):

```bash
# Python
jupytext --set-kernel python3 --to notebook --execute script.py

# Julia (automatically uses nearest Project.toml)
jupytext --set-kernel julia-1.x --to notebook --execute script.jl  # match your installed kernel
```

If `uv` is available, prefer `uv run` — it activates the project's `.venv`
so the kernel uses the correct environment automatically:

```bash
uv run jupytext --set-kernel python3 --to notebook --execute script.py
```

This requires `jupytext`, `nbconvert`, and `ipykernel` as dev dependencies
in the project's `pyproject.toml`.

### Convert only (no execution)

Does NOT require a kernel. Works inside the sandbox:

```bash
jupytext --to notebook script.py
```

### Pairing (auto-sync script ↔ notebook)

```bash
jupytext --set-formats ipynb,py:percent script.py   # Python
jupytext --set-formats ipynb,jl:percent script.jl   # Julia
jupytext --sync script.py                           # sync after editing
```

### Export to HTML

```bash
jupyter nbconvert --to html script.ipynb
```

## Working Directory and Project Environments

### Relative paths

Jupytext sets the working directory to the **script's parent directory** by
default (`--run-path` defaults to this). Relative paths like `Data/file.csv`
resolve relative to where the script lives.

### Julia

The IJulia kernel spec includes `--project=@.`, which activates the nearest
`Project.toml` upward from the working directory. No extra configuration needed.
If no `Project.toml` is found, Julia falls back to the global environment.

### Python

The default `python3` kernel uses whichever environment it was installed from.
To use a project-specific environment, use `uv run` (see above) — it puts the
project's `.venv/bin` on `PATH` so the kernel resolves `python` to the
project's Python automatically.

### Version control strategy

- **Commit the `.py`/`.jl` script** — it diffs cleanly
- **Optionally commit `.ipynb`** if you want rendered outputs in the repo
- Or `.gitignore` the `.ipynb` and re-render on demand

## Installation

```bash
# Global (for scripts not in a uv project)
uv pip install jupytext jupyter nbconvert ipykernel
python -m ipykernel install --user --name python3

# Per-project (add to pyproject.toml dev-dependencies)
# jupytext, nbconvert, ipykernel

# Julia kernel (run in Julia REPL)
# using Pkg; Pkg.add("IJulia")
```

Verify with: `jupyter kernelspec list`

## Troubleshooting

- **"No kernel found matching executable"**: use `--set-kernel <name>` with a
  kernel name from `jupyter kernelspec list`
- **Sandbox blocks execution**: Jupyter kernels need local sockets. Run the
  execute command outside the sandbox (e.g., `! jupytext ...` in Claude Code)
- **Wrong Python environment**: use `uv run jupytext ...` to activate the
  project's `.venv`
- **Percent format not recognized**: ensure file starts with `# %%` and
  jupytext is installed
- **Pairing not working**: check `jupytext.toml` or notebook metadata for
  correct `formats` string
