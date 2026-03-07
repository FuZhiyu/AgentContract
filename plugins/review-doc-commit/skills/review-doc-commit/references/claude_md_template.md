# CLAUDE.md Template

When creating a new CLAUDE.md for a directory, adapt this structure to the directory's content. Not all sections are required — include only what's relevant.

## Template

```markdown
# <Directory/Module Name>

<1-2 sentence description of what this directory contains and its role in the project.>

## Structure

<Brief description of key subdirectories or file organization patterns, if non-obvious.>

## Conventions

<List project-specific conventions that apply to code in this directory:>
- Language/framework version requirements
- Naming conventions (files, functions, classes, variables)
- Import ordering or module patterns
- Error handling approach
- Testing patterns

## Architecture

<Non-obvious design decisions or patterns used here:>
- Key abstractions and their relationships
- Data flow patterns
- Dependencies and why they were chosen
- Performance considerations

## Development

<How to work with code in this directory:>
- How to run/test
- Common tasks
- Gotchas or pitfalls
```

## Nested Structure

Context is progressively revealed through a hierarchy of `CLAUDE.md` files:

```
repo/
├── CLAUDE.md          # Project-wide: architecture, tech stack, conventions
├── AGENTS.md -> CLAUDE.md   # Symlink
├── src/
│   ├── CLAUDE.md      # src module purpose and conventions
│   ├── AGENTS.md -> CLAUDE.md
│   ├── core/
│   │   ├── CLAUDE.md  # Core module specifics
│   │   └── AGENTS.md -> CLAUDE.md
│   └── utils/
│       ├── CLAUDE.md  # Utils module specifics
│       └── AGENTS.md -> CLAUDE.md
```

Each level documents only what is specific to that module. Do not repeat guidance from parent `CLAUDE.md` files.

## AGENTS.md Symlink

`AGENTS.md` is a mirror of `CLAUDE.md`. Whenever one exists, create a symlink for the other:

```bash
# In the same directory as the CLAUDE.md
ln -s CLAUDE.md AGENTS.md
```

If only `AGENTS.md` exists, symlink in the other direction: `ln -s AGENTS.md CLAUDE.md`.

## Guidelines

- Keep it under 50 lines for leaf directories, under 100 for major modules
- Focus on what's non-obvious — do not restate what the code clearly shows
- Use imperative voice ("Use X for Y" not "X is used for Y")
- If a parent CLAUDE.md already covers a convention, do not repeat it
- Update when architecture changes, not for every small edit
- For the repo root CLAUDE.md, include: project overview, tech stack, build/test commands, overall architecture
