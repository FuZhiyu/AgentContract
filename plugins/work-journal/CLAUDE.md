# work-journal

Plugin for creating formal work journal entries and saving markdown reports for academic research.

## Skills

- `work-journal` -- formal, fact-checked journal entries with mandatory citations, git-clean gate, and report-checker verification
- `report-in-markdown` -- pure IO tool for persisting markdown reports; no content rules, no fact-checking, no git-clean gate

## Agents

- `code-reviewer` -- reviews analysis code for correctness and data integrity
- `report-checker` -- validates documentation accuracy, citations, and objectivity
- `results-summarizer` -- creates comprehensive markdown summaries of analysis results

## Conventions

- Journal entries go to the project's notes directory (resolved from project guidance)
- Quick reports default to `./scratch/` (not `notes/`)
- Frontmatter is required on all output files (author, date, timestamp, session_id, git state)
