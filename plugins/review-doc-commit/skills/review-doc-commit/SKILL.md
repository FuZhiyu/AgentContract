---
name: review-doc-commit
user-invocable: true
description: "Review code thoroughly, update documentation coverage, and commit only when the review is clean. Use when the user invokes /review-doc-commit, asks to commit changes, or wants review + docs + commit. Enforces a hard gate: if any issue is found, stop and discuss with the user before committing. Supports scoped commits (e.g., '/review-doc-commit changes in folder A') or full-repo commits."
---

# Commit

Review, document, and commit workflow. Use dedicated subagents for review, documentation, and commit phases.

1. **Scope** — determine what to commit (no subagent)
2. **Review** — comprehensive code quality and correctness review (Code Review Subagent)
3. **Document** — comprehensive documentation review + updates (Documentation Subagent)
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

## Phase 2: Comprehensive Review (Code Review Subagent)

For each changed **code/test/config** file, perform a serious review against project guidance and existing docs:

1. Find the nearest `CLAUDE.md` by walking up from the file's directory to the repo root.
2. Read `CLAUDE.md`/`AGENTS.md` guidance relevant to that file.
3. Review the diff for code quality and behavior:
   - Violations of stated conventions
   - Inconsistencies with existing behavior or interfaces
   - Security issues (injection, XSS, hardcoded secrets)
   - Obvious bugs or logic errors
   - Performance regressions or unnecessary complexity
   - Breaking changes to public interfaces without required migration notes
   - Test gaps for changed behavior
4. Where possible, run a second independent review perspective/subagent for cross-checking.

If issues are found:
- **Do not commit**
- Summarize issues clearly with file-level references
- Return to the user to discuss tradeoffs and resolution plan before moving forward
- Only continue once issues are resolved (or user explicitly accepts risk)

Skip deep quality review for binary/generated files.

## Phase 3: Documentation (Documentation Subagent)

Review and update documentation thoroughly so it reflects the latest changes. This includes inline docs and top-level/project docs.

Coverage checklist:
1. Inline and code-adjacent docs:
   - Docstrings/comments for changed public APIs, complex logic, and non-obvious constraints
   - Type/interface documentation where applicable
2. Directory/project guidance docs:
   - `CLAUDE.md` (or legacy `cloud.md` if present)
   - `AGENTS.md`
3. User/developer-facing docs:
   - `README.md` (root and impacted module-level READMEs)
   - Other impacted docs (`docs/`, architecture notes, runbooks, examples, changelogs)

Required actions:
1. For each directory containing changed files (and important source subfolders), check whether guidance docs exist and are current.
2. Create missing guidance docs when relevant.
3. Update existing docs for new patterns, modules, architecture, commands, constraints, and behavior changes introduced by the diff.
4. Keep `AGENTS.md`, `CLAUDE.md`, and README/docs mutually consistent.
5. Ensure docs clearly describe any breaking changes, migration notes, or operational changes.

Rules for documentation content:
- Describe the purpose of the directory/module
- List key conventions (naming, patterns, dependencies)
- Note non-obvious architectural decisions
- Keep it concise and actionable
- Do NOT duplicate information already covered well in parent docs; link instead when helpful

Output contract from Documentation Subagent:
- Files reviewed and files updated
- Coverage checklist status
- Any unresolved documentation ambiguity needing user input

## Phase 4: Commit (Commit Subagent)

Commit only after Phase 2 is clean and Phase 3 documentation updates are complete. Group changes into topical commits. Never combine unrelated changes.

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
- **Only documentation updates**: commit as `docs: update project documentation`
- **Merge conflicts in progress**: warn user, do not commit
- **Untracked files mixed with modifications**: ask user if untracked files should be included
- **Binary files**: include in commit but skip deep quality review
- **Files in .gitignore**: never commit these
- **Open review issues**: stop, discuss with user, and do not commit
