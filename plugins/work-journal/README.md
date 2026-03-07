# work-journal

Working journal creation and markdown report generation for academic research.

## Skills

### work-journal
Create formal, fact-checked work journal entries with proper citations to code and output files. Blocks on uncommitted changes, requires user confirmation, and runs the report-checker agent for verification. Use for documenting completed analysis work that needs to be accurate and well-cited.

### report-in-markdown
Pure IO tool for saving markdown reports. Handles file format, metadata frontmatter, naming, and placement. Content and style are determined entirely by the calling agent. No fact-checking, no tone rules, no blocking on uncommitted changes. Use for quick reports, session output, exploration notes, or any time an agent needs to persist markdown.

| Aspect | `report-in-markdown` | `work-journal` |
|--------|---------------------|----------------|
| Role | IO tool | Formal workflow |
| Content rules | None (caller decides) | Strict: factual, objective, cited |
| Fact-checking | No (unless requested) | Mandatory (report-checker agent) |
| Git state | Records dirty state, doesn't block | Blocks on uncommitted changes |
| User confirmation | No | Yes |

## Agents

### code-reviewer
Reviews analysis code for correctness and data integrity. Focuses on:
- Merge correctness
- Missing data handling
- Aggregation logic
- Filter conditions

### report-checker
Validates documentation accuracy and citations. Ensures:
- All claims have supporting evidence
- No speculation or unsupported interpretation
- Proper front matter (author, date, project)

### results-summarizer
Creates comprehensive markdown summaries of analysis results with:
- Objective overview
- Data source details
- Procedures
- Results with embedded tables/figures
- Conclusions

## Usage

**Create formal work journal:**
- "Create a work journal entry"
- "Document the results"
- "Summarize the work"

**Save a quick report:**
- "Save this as a report"
- "Write up these findings"

**Review code:**
- Claude automatically spawns code-reviewer agent when reviewing research code

**Check reports:**
- "Check this report for accuracy"
- Claude spawns report-checker agent

**Summarize results:**
- "Summarize the results from Output/regression_results.csv"
- Claude spawns results-summarizer agent

## Philosophy

Work journal entries must be:
- **Factual** - No speculation or interpretation unless requested
- **Cited** - Every claim links to supporting code or output
- **Objective** - Present findings without subjective assessments

Reports (via `report-in-markdown`) have no such constraints -- content rules are set by the calling agent.
