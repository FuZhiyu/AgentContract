# review-doc-commit

Plugin for reviewing code, updating documentation, and creating topical git commits. Enforces a hard gate: no commit until review is clean.

## Workflow Phases

1. **Scope** -- determine changed files (no subagent)
2. **Document** -- documentation review and updates (Documentation Subagent)
3. **Review** -- two parallel subagents: Implementation Review + Integration & Consistency Review
4. **Commit** -- topical commits only after phases 2 and 3 pass

Phases 2 and 3 run in parallel. Phase 4 is gated on both.

## Conventions

- AGENTS.md is always a symlink to CLAUDE.md (see SKILL.md for the convention)
- Nested CLAUDE.md files provide progressive context; each level adds only module-specific guidance
- No `.skill` binary bundle is distributed; install the plugin directory directly
