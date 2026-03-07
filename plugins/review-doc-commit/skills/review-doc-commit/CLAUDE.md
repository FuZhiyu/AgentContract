# review-doc-commit Skill

Contains the main SKILL.md defining the review-doc-commit workflow and reference materials.

## Structure

- `SKILL.md` -- full workflow specification (phases, subagent contracts, edge cases)
- `references/` -- templates and reference files used by the documentation subagent

## Key Design Decisions

- Phase ordering: Documentation (Phase 2) runs in parallel with Review (Phase 3), not sequentially
- Two review subagents split focus: implementation correctness vs. integration/consistency
- The commit message Co-Authored-By line uses the model name at time of execution
