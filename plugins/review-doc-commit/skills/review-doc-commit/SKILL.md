---
name: review-doc-commit
user-invocable: true
description: "Review code thoroughly, update documentation coverage, and commit only when the review is clean. Use when the user invokes /review-doc-commit, asks to commit changes, or wants review + docs + commit. Enforces a hard gate: if any issue is found, stop and discuss with the user before committing. Supports scoped commits (e.g., '/review-doc-commit changes in folder A') or full-repo commits."
---

# Commit

Review, document, and commit workflow. Use dedicated subagents for review, documentation, and commit phases.

1. **Scope** — determine what to commit (no subagent)
2. **Document** — comprehensive documentation review + updates (Documentation Subagent)
3. **Review** — two parallel subagents: Implementation Review + Integration & Consistency Review
4. **Commit** — group by topic and commit only after clean review/doc gates (Commit Subagent)

Execution model:
- Phase 1 runs first.
- Phases 2 and 3 run in parallel on the same scoped file set.
- Phase 4 runs only after both Phase 2 and Phase 3 are complete and clean.

## Phase 1: Determine Scope

Parse the user's request:

- `/review-doc-commit` with no path → all unstaged/staged changes
- `/review-doc-commit <message or path>` → scope to the specified path or use as context

Run `git status` and `git diff` (staged + unstaged) to identify all changed files. If a path scope was given, filter to only changes under that path.

Output contract from Scope phase:
- Final scoped file list
- File classification (code, tests, docs, generated/binary)
- Any blocking state (merge conflicts, nothing to commit)


## Phase 2: Documentation (Documentation Subagent)

Review and update documentation thoroughly so it reflects the latest changes. This includes inline docs and top-level/project docs.

Coverage checklist:
1. Inline and code-adjacent docs:
   - Docstrings/comments for changed public APIs, complex logic, and non-obvious constraints
   - Type/interface documentation where applicable
2. Directory/project guidance docs:
   - `CLAUDE.md` / `AGENTS.md` (see nested structure below)
3. User/developer-facing docs:
   - `README.md` (root and impacted module-level READMEs)
   - Other impacted docs (`docs/`, architecture notes, runbooks, examples, changelogs)


### Nested CLAUDE.md Structure

Context is progressively revealed through a hierarchy of `CLAUDE.md` files. Each level adds module-specific guidance without repeating what parent docs already cover:

- **Repo root `CLAUDE.md`** — overall architecture, tech stack, build/test commands, project-wide conventions
- **Module/subfolder `CLAUDE.md`** — the module's purpose, its conventions, non-obvious design decisions, and how to work with it

When reviewing or documenting a file, walk up from the file's directory to the repo root and read every `CLAUDE.md` encountered along the way. The union of these files provides the full context for that file.

### AGENTS.md Symlink Convention

`AGENTS.md` is a mirror of `CLAUDE.md`. Both names should resolve to the same content. When creating or discovering guidance docs:

1. If only `CLAUDE.md` exists, create a symlink: `ln -s CLAUDE.md AGENTS.md`
2. If only `AGENTS.md` exists, create a symlink: `ln -s AGENTS.md CLAUDE.md`
3. If both exist as separate files, unify them: keep the richer file and replace the other with a symlink
4. Always use relative symlinks (just the filename, not absolute paths)

### Required Actions

1. For each directory containing changed files (and important source subfolders), check whether a `CLAUDE.md` exists.
2. If a module directory lacks a `CLAUDE.md`, create one describing the module's purpose and conventions.
3. Ensure the `AGENTS.md` symlink exists alongside every `CLAUDE.md` (and vice versa).
4. Update existing docs for new patterns, modules, architecture, commands, constraints, and behavior changes introduced by the diff.
5. Keep guidance docs and README/docs mutually consistent.
6. Ensure docs clearly describe any breaking changes, migration notes, or operational changes.

Rules for documentation content:
- Describe the purpose of the directory/module
- List key conventions (naming, patterns, dependencies)
- Note non-obvious architectural decisions
- Keep it concise and actionable
- Do NOT duplicate information already covered well in parent docs; link instead when helpful

Initial intention: Update documentation to reflect the latest changes, ensuring all relevant sections, terminology, and examples are revised accordingly.

Output contract from Documentation Subagent:
- Files reviewed and files updated
- Coverage checklist status
- Any unresolved documentation ambiguity needing user input

Note: The Integration & Consistency reviewer (Phase 3, Subagent B) will independently verify that documentation updates are consistent with the actual code changes and with each other. This cross-check catches docs that were updated in isolation without accounting for the full picture.


## Phase 3: Comprehensive Review (Two Review Subagents)

Spawn **two review subagents in parallel**, each with a distinct perspective. A common failure mode is reviewing changes in isolation — one agent focuses narrowly on the changed files while missing how those changes interact with the rest of the project. These two agents address that by splitting the review into complementary scopes.

### Subagent A: Implementation Review

Focus: the changed code itself.

1. Find the nearest `CLAUDE.md` by walking up from each changed file's directory to the repo root.
2. Read all relevant `CLAUDE.md`/`AGENTS.md` guidance.
3. Review the diff for:
   - Correctness and logic errors
   - Violations of stated conventions
   - Security issues (injection, XSS, hardcoded secrets)
   - Unnecessary complexity or performance regressions
   - Test coverage gaps for changed behavior

### Subagent B: Integration & Consistency Review

Focus: how the changes fit into the broader project.

1. Identify all components that interact with the changed code (callers, dependents, shared interfaces, configuration, documentation references).
2. Review for:
   - **Consistency**: Do the changes align with patterns, naming, and conventions used elsewhere in the project?
   - **Ripple effects**: Do other components need updating to stay compatible? (e.g., a renamed export, changed API contract, new config key)
   - **Compatibility**: Should the current changes be modified to better fit existing code rather than forcing the rest of the project to adapt?
   - **Documentation references**: Do other docs, READMEs, or examples reference the changed behavior and need updates?
3. Based on the intent of the changes, recommend whether:
   - Other components should be updated to match the new changes, or
   - The current changes should be adjusted to integrate more smoothly with existing code

### Merging Review Results

After both subagents complete:

1. Combine their findings into a single issue list, deduplicating overlaps.
2. Flag any contradictions between the two reviews for the user to resolve.

If **any** issues are found:
- **Do not commit**
- Summarize issues clearly with file-level references
- Return to the user to discuss tradeoffs and resolution plan before moving forward
- Only continue once issues are resolved (or user explicitly accepts risk)

Skip deep quality review for binary/generated files.

## Phase 4: Commit (Commit Subagent)

Commit only after Phase 2 documentation updates and Phase 3 review are both complete and clean. Group changes into topical commits. Never combine unrelated changes.

### Grouping Strategy

1. Collect all files to commit (after review fixes and doc updates)
2. Group by logical topic:
   - Files in the same module/feature → one commit
   - Documentation updates for a feature → same commit as the feature
   - Unrelated bug fixes → separate commits
   - Pure refactoring → separate from feature work
   - Standalone documentation-only maintenance → separate docs commit
3. If all changes are related (single feature/fix), use one commit

### Commit Message Format

```
<type>: <concise description>

<optional body explaining why, not what>

Co-Authored-By: Claude <model> <noreply@anthropic.com>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

### Execution

For each topic group:
1. Stage only the files in that group (`git add <specific files>`)
2. Commit with appropriate message
3. Verify with `git status` after each commit

## Edge Cases

- **No changes**: report "nothing to commit" and exit
- **Only documentation updates**: commit as `docs: update project documentation`
- **Merge conflicts in progress**: warn user, do not commit
- **Untracked files mixed with modifications**: ask user if untracked files should be included
- **Binary files**: include in commit but skip deep quality review
- **Files in .gitignore**: never commit these
- **Open review issues**: stop, discuss with user, and do not commit
