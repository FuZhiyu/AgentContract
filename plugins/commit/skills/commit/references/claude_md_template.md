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

## Guidelines

- Keep it under 50 lines for leaf directories, under 100 for major modules
- Focus on what's non-obvious — do not restate what the code clearly shows
- Use imperative voice ("Use X for Y" not "X is used for Y")
- If a parent CLAUDE.md already covers a convention, do not repeat it
- Update when architecture changes, not for every small edit
- For the repo root CLAUDE.md, include: project overview, tech stack, build/test commands, overall architecture
