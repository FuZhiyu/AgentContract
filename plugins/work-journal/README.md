# research-docs

Documentation quality review, summarization, and working journal creation for academic research.

## Skills

### work-summary
Create factual working journal entries with proper citations to code and output files.

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

**Create working journal:**
- "Create a work summary for today's analysis"
- "Document what we did in this session"

**Review code:**
- Claude automatically spawns code-reviewer agent when reviewing research code

**Check reports:**
- "Check this report for accuracy"
- Claude spawns report-checker agent

**Summarize results:**
- "Summarize the results from Output/regression_results.csv"
- Claude spawns results-summarizer agent

## Philosophy

All documentation must be:
- **Factual** - No speculation or interpretation unless requested
- **Cited** - Every claim links to supporting code or output
- **Objective** - Present findings without subjective assessments
