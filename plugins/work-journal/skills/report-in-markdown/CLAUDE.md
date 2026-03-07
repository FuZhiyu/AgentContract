# report-in-markdown Skill

Pure IO skill for saving markdown reports. Defines file format contract (frontmatter, naming, placement) but imposes no content or style rules.

## Key Design Decisions

- No fact-checking, no tone rules, no citation requirements -- caller decides content
- Records git dirty state but does not block on uncommitted changes
- Default output to `./scratch/` (not `notes/`) when no project guidance exists
- Agents should use this proactively for lengthy output with figures or LaTeX math
