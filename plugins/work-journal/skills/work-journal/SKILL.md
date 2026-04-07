---
name: work-journal
description: Create formal, fact-checked work journal entries after completing analysis work. Use when user asks to "summarize work", "document results", or "create work journal entry". Ensures code is committed, copies figures to attachments, and creates objective summaries with mandatory citations plus a report-quality verification pass. For quick reports without fact-checking, use the `report-in-markdown` skill.
user-invocable: true
---

# Work Journal Skill

Create formal, fact-checked work journal entries that document completed analysis work without interpretation or recommendations. Every claim must be cited and must survive either a dedicated report-checker pass or the equivalent inline verification checklist.

## When to Use

Activate when the user requests:
- "Summarize the work"
- "Document the results"
- "Create a work journal entry"
- "Write up the analysis"

## Instructions

### Step 0: Resolve Work Journal Path from Project Guidance

Before writing anything, locate project-specific guidance for documentation paths, for example in `AGENTS.md`, `CLAUDE.md`, the project README, or `.claude/` docs.

1. If project guidance specifies a work journal location, use that path exactly.
2. If not specified, select a sensible default in this order:
   - `notes/` (if it exists, or create it)
   - `work journal/` (if user or project prefers this naming)
3. Define:
   - `WORK_JOURNAL_DIR` = resolved directory for journal files
   - `WORK_JOURNAL_ATTACHMENTS_DIR` = `${WORK_JOURNAL_DIR}/attachments`
4. Use these resolved paths consistently for all file creation, links, and copy commands.

### Step 1: Verify Git Commit

Check whether the relevant code has been committed:

```bash
git status
```

If uncommitted changes exist:
1. Tell the user exactly what you found.
2. Ask whether they want a review-and-commit pass before the journal entry is written.
3. If they confirm:
   - If the standalone Codex role `work-journal__code-reviewer` is installed and delegated review is appropriate, use that role.
   - Otherwise perform the same code-review checklist inline.
   - Do not create a commit without explicit user approval.
4. After the review/commit step, record the latest commit info:

```bash
git log -1 --pretty=format:"%H%n%s"
```

If the worktree is already clean, just capture the latest commit info:

```bash
git log -1 --pretty=format:"%H%n%s"
```

### Step 2: Confirm Understanding

If you already have enough context from the current thread:
- Summarize your understanding of the objective, code location, output location, and relevant files
- Ask the user a direct confirmation question only if something material is ambiguous

If you do not have enough context:
- Ask the user for the objective, code location, and output location

Then read the code files, output files, and documentation needed to support the report.

### Step 3: Handle Figures

If figures exist in the output folder:

```bash
mkdir -p "${WORK_JOURNAL_ATTACHMENTS_DIR}"
```

For PDF figures, convert to PNG first, then copy:

```bash
uv run --with pdf2image python -c "
from pdf2image import convert_from_path
images = convert_from_path('Output/[subfolder]/figure.pdf')
images[0].save('${WORK_JOURNAL_ATTACHMENTS_DIR}/YYYY-MM-DD-description.png')
"
```

For PNG or other image figures, copy directly:

```bash
cp Output/[subfolder]/figure.png "${WORK_JOURNAL_ATTACHMENTS_DIR}/YYYY-MM-DD-description.png"
```

In Markdown:

```markdown
![Descriptive caption](./attachments/YYYY-MM-DD-description.png)

Source: [Original](relative/path/from/report/to/original/figure.pdf)
```

### Step 4: Create the Work Journal Entry

Create one entry file at:
`[WORK_JOURNAL_DIR]/YYYY-MM-DD-[Author]-[Description].md`

**Filename:** `YYYY-MM-DD-[Author]-[Description].md`

**Front Matter:**

```yaml
---
author: "[[Author]]"
date: YYYY-MM-DD
timestamp: "YYYY-MM-DDTHH:MM:SS"
session_id: "[from context or session-YYYYMMDD-HHMMSS]"
project: "[[ProjectName]]"
git_commit: [full hash if available]
git_message: "[message if available]"
tags: ["work-journal"]
permalink: working-journal/YYYY-MM-DD-author-description
---
```

### Step 5: Write the Summary

The structure can be flexible, but usually includes:
- Objective
- Summary of what was done
- Data description
- Methodology description
- Results with tables or figures
- Technical implementation details

Rules:
- Keep the writing factual and objective.
- Do not speculate about causes, implications, or next steps unless the user explicitly asked for that.
- Every claim must link to supporting evidence.
- When mentioning files, always create Markdown links with paths resolved relative to the report file's location.

Example:
- Wrong: `code/BOP/clean_data.py`
- Correct: [`code/BOP/clean_data.py`](../code/BOP/clean_data.py)

### Step 6: Verify Report Quality

After creating the report, run a verification pass before finalizing.

Preferred path when available:
- Use the installed Codex role `work-journal__report-checker` if the advanced installer has registered it and delegated checking is appropriate.

Fallback path:
- Run the same checklist inline in the main thread.

The verification pass must check:
- All claims are cited and accurate
- No speculation or unsupported interpretation
- Numbers match source files
- No subjective language
- Figures are copied correctly and cite their sources

If issues are found, revise the report before finalizing it.

## Critical Rules

### 1. Be Factual and Objective

Do:
- State what was done and what was found
- Report numerical results precisely
- Describe methods used
- Link every claim to code, output, or documentation

Do not:
- Interpret economic meaning without user request
- Speculate on causes or implications
- Make recommendations or suggest next steps
- Use subjective assessments such as "excellent", "poor", or "successful"

### 2. Examples

Good:
- "Processed 4.7M holdings from 11,857 submissions"
- "Difference of -30% (-$243B)"
- "Front-end tenors within 7% of benchmark"
- "Classification success rate: 70% (3,988 of 5,699)"

Bad:
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

- PDF figures must be converted to PNG before embedding
- Copy them into the report attachments directory
- Cite the original source location
- Use descriptive captions

## Optional Installed Roles

If the advanced installer has been used, these role names are available to Codex as `agent_type` values:

- `work-journal__code-reviewer`
- `work-journal__report-checker`
- `work-journal__results-summarizer`

Use those exact names if you delegate work. Do not rely on bare role names such as `code-reviewer` or `report-checker`.

## After Creating the Entry

1. Tell the user the file path.
2. List what was documented.
3. Report any issues found by the verification pass.
4. Ask whether they want any specific information added.
5. Do not suggest interpretations or next steps unless the user asked for them.
