---
name: commit
description: Review code, update documentation, and create well-organized git commits. Use when the user invokes /commit, asks to commit changes, or wants to review and commit their work. Handles three phases automatically - code review against project guidelines (CLAUDE.md), documentation updates (ensuring CLAUDE.md exists for each subfolder), and topical commits (grouping related changes, never mixing unrelated ones). Supports scoped commits (e.g., "/commit changes in folder A") or full-repo commits.
---

# Commit

Review, document, and commit workflow. Three phases run in sequence:

1. **Scope** — determine what to commit
2. **Review** — check code against project guidelines
3. **Document** — ensure CLAUDE.md coverage
4. **Commit** — group by topic and commit

## Phase 1: Determine Scope

Parse the user's request:

- `/commit` or `/commit` with no path → all unstaged/staged changes
- `/commit <message or path>` → scope to the specified path or use as context

Run `git status` and `git diff` (staged + unstaged) to identify all changed files. If a path scope was given, filter to only changes under that path.

## Phase 2: Code Review

For each changed file, review against the project's CLAUDE.md guidelines:

1. Find the nearest CLAUDE.md by walking up from the file's directory to the repo root
2. Read the CLAUDE.md to understand project conventions (coding style, naming, architecture, etc.)
3. Review the diff for:
   - Violations of stated conventions
   - Security issues (injection, XSS, hardcoded secrets)
   - Obvious bugs or logic errors
   - Breaking changes to public interfaces without documentation

If issues are found:
- **Fixable issues** (formatting, naming): fix them silently
- **Judgment calls** (architecture, design): report to user and ask before changing
- **Critical issues** (security, data loss): warn user, suggest fix, do not auto-commit

Skip review for non-code files (images, lock files, generated files).

## Phase 3: Documentation

Ensure every directory containing source code has a CLAUDE.md. Walk the tree of changed files:

1. For each directory containing changed files, check if a CLAUDE.md exists in that directory or any ancestor (up to repo root)
2. If no CLAUDE.md covers a directory, create one. See `references/claude_md_template.md` for the template.
3. If a CLAUDE.md exists but the changes introduce new patterns, modules, or architectural decisions, update it.

Rules for CLAUDE.md content:
- Describe the purpose of the directory/module
- List key conventions (naming, patterns, dependencies)
- Note any non-obvious architectural decisions
- Keep it concise — a guide for the next developer (or AI), not exhaustive docs
- Do NOT duplicate information already in a parent CLAUDE.md

## Phase 4: Commit

Group changes into topical commits. Never combine unrelated changes.

### Grouping Strategy

1. Collect all files to commit (after review fixes and doc updates)
2. Group by logical topic:
   - Files in the same module/feature → one commit
   - Documentation updates for a feature → same commit as the feature
   - Unrelated bug fixes → separate commits
   - Pure refactoring → separate from feature work
   - CLAUDE.md additions → can be grouped together or with their module
3. If all changes are related (single feature/fix), use one commit

### Commit Message Format

```
<type>: <concise description>

<optional body explaining why, not what>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

### Execution

For each topic group:
1. Stage only the files in that group (`git add <specific files>`)
2. Commit with appropriate message
3. Verify with `git status` after each commit

## Edge Cases

- **No changes**: report "nothing to commit" and exit
- **Only CLAUDE.md updates**: commit as `docs: update project documentation`
- **Merge conflicts in progress**: warn user, do not commit
- **Untracked files mixed with modifications**: ask user if untracked files should be included
- **Binary files**: include in commit but skip review
- **Files in .gitignore**: never commit these
