---
name: work-summary
description: Create factual work journal entries after completing analysis work. Use when user asks to "summarize work", "document results", or "create work journal entry". Ensures code is committed, copies figures to attachments, and creates objective summaries with citations.
---

# Work Summary Skill

Create factual work journal entries that document completed analysis work without interpretation or recommendations.

## When to Use

Activate when user requests:
- "Summarize the work"
- "Document the results"
- "Create a work journal entry"
- "Write up the analysis"

## Instructions

### Step 0: Resolve Work Journal Path from Project Guidance

Before writing anything, locate project-specific guidance for documentation paths (for example in `AGENTS.md`, `CLAUDE.md`, project README, or `.claude/` docs).

1. If project guidance specifies a work journal location, use that path exactly.
2. If not specified, select a sensible default in this order:
   - `notes/` (if it exists, or create it)
   - `work journal/` (if user/project prefers this naming)
3. Define:
   - `WORK_JOURNAL_DIR` = resolved directory for journal files
   - `WORK_JOURNAL_ATTACHMENTS_DIR` = `${WORK_JOURNAL_DIR}/attachments`
4. Use these resolved paths consistently for all file creation, links, and copy commands.

### Step 1: Verify Git Commit

Check if code has been committed:

```bash
git status
```

**If uncommitted changes exist:**
1. Inform user: "I see uncommitted changes. Should I run the code-quality-reviewer agent and commit the code first?"
2. Wait for user confirmation
3. If confirmed, use Task tool with `subagent_type="code-quality-reviewer"` then assist with git commit
4. Get commit info: `git log -1 --pretty=format:"%H%n%s"`

**If clean:** Get latest commit: `git log -1 --pretty=format:"%H%n%s"`

### Step 2: Confirm Understanding

**If you have context from recent work:**
- Summarize your understanding of objective, code location, output location
- Use AskUserQuestion tool to confirm with user

**If you don't have context:**
- Ask user for: objective, code location, output location

Then read code files, output files, and documentation to gather information.

### Step 3: Handle Figures

If figures exist in output folder:

```bash
mkdir -p "${WORK_JOURNAL_ATTACHMENTS_DIR}"
```

**For PDF figures:** Convert to PNG first using the pdf-tools script, then copy:

```bash
# Create a temp directory for conversion
mkdir -p /tmp/pdf_convert
python plugins/pdf-tools/scripts/convert_pdf_to_images.py Output/[subfolder]/figure.pdf /tmp/pdf_convert
# Copy converted PNG(s) to attachments with descriptive names
cp /tmp/pdf_convert/page_1.png "${WORK_JOURNAL_ATTACHMENTS_DIR}/YYYY-MM-DD-description.png"
```

**For PNG/other image figures:** Copy directly:

```bash
cp Output/[subfolder]/figure.png "${WORK_JOURNAL_ATTACHMENTS_DIR}/YYYY-MM-DD-description.png"
```

In markdown:
```markdown
![Descriptive caption](./attachments/YYYY-MM-DD-description.png)

Source: [Original](relative/path/from/report/to/original/figure.pdf)
```

### Step 4: Create work journal Entry

One entry file at:
`[WORK_JOURNAL_DIR]/YYYY-MM-DD-[Author]-[Description].md`

**Filename:** `YYYY-MM-DD-[Author]-[Description].md`

**Front Matter:**
```yaml
---
author: "[[Author]]"
date: YYYY-MM-DD
project: "[[IntermediaryDemand]]"
git_commit: [full hash if available]
git_message: "[message if available]"
permalink: working-journal/YYYY-MM-DD-author-description
---
```

### Step 5: Write Summary

**Structure can be flexible**, but typically include:
- Objective section
- Summary of what was done
- Data description
- Methodology description
- Results with tables/figures
- Technical implementation details (code and outputs)

**Use paths relative to the resolved `WORK_JOURNAL_DIR`:**
- Do not hardcode path depth.
- Build links relative to the report location and the actual project layout.
- Follow project guidelines if they specify citation/link style.

If no project guideline exists, use clear repo-relative links that resolve from the report location.

## Critical Rules - MUST FOLLOW

### 1. Be Factual and Objective

**✓ DO:**
- State what was done and what was found
- Report numerical results precisely
- Describe methods used
- Link every claim to source (code, output, documentation)

**✗ DO NOT:**
- Interpret economic meaning without user request
- Speculate on causes or implications
- Make recommendations or suggest next steps
- Use subjective assessments ("excellent", "poor", "successful")

### 2. Examples

**Good (Factual):**
- "Processed 4.7M holdings from 11,857 submissions"
- "Difference of -30% (-$243B)"
- "Front-end tenors within 7% of benchmark"
- "Classification success rate: 70% (3,988 of 5,699)"

**Bad (Speculative/Interpretive):**
- "This suggests the classification is insufficient"
- "The results indicate strong performance"
- "This likely means we should use BKMS data"
- "The excellent match validates our approach"

### 3. Cite Everything

Every claim must link to supporting evidence:
- `[descriptive text](relative/path/from/report/to/file)`
- Code files for methodology
- Output files for results
- Documentation for data sources

### 4. Figures

- **PDF figures must be converted to PNG** before embedding (use `plugins/pdf-tools/scripts/convert_pdf_to_images.py`)
- Copy to attachments/ with descriptive filename
- Cite original source location
- Use descriptive captions

### Step 6: Verify Report Quality

After creating the report, use the report-checker agent to verify quality:

```
Use Task tool with subagent_type="report-checker"
Pass: report path, code location, output location, objective
```

The agent will check:
- All claims are cited and accurate
- No speculation or unsupported interpretation
- Numbers match source files
- No subjective language

If issues found, revise the report before finalizing.

## After Creating

1. Tell user the file path
2. List what was documented
3. Report any issues found by report-checker
4. Ask: "Would you like me to add any specific information?"
5. Do NOT suggest interpretations or next steps unless asked
