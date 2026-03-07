---
name: report-in-markdown
description: Report back to the user in a well-formatted markdown file for readability. Use this skill PROACTIVELY when the output is lengthy or refers to figures/tables/or latex math, or when users request a markdown report.
user-invocable: true
---

# Report in Markdown

## Proactive Use

Agents should use this skill proactively when output would be lengthy, especially if it involves figures or LaTeX math. Long responses with math/figures render poorly in the terminal. Saving to markdown and providing a clickable link is a better UX.

## Instructions

### Step 0: Resolve Output Path

Check project guidance (`AGENTS.md`, `CLAUDE.md`, project README, `.claude/` docs) for a documentation path.

1. If project guidance specifies a location, use it.
2. Otherwise, fall back to `./scratch/` (create if needed). Use `scratch/` for transient agent output.

Define:
- `REPORT_DIR` = resolved directory
- `REPORT_ATTACHMENTS_DIR` = `${REPORT_DIR}/attachments`

### Step 1: Gather Metadata

Collect the following:

```bash
# Git state
git log -1 --pretty=format:"%H"   # HEAD commit
git diff --quiet; echo $?          # 0 = clean, 1 = dirty

# Timestamp
date -u +"%Y-%m-%dT%H:%M:%S"
```

Session ID: use context if available, otherwise generate `session-YYYYMMDD-HHMMSS`.

### Step 2: Write File

**Filename:** `YYYY-MM-DD-report-[description].md`

**Frontmatter:**
```yaml
---
author: "[[UserName]]"
date: YYYY-MM-DD
timestamp: "YYYY-MM-DDTHH:MM:SS"
session_id: "[from context or session-YYYYMMDD-HHMMSS]"
git_commit: "[current HEAD]"
git_dirty: true/false
tags: ["report"]
project: "[[ProjectName]]"
permalink: working-journal/YYYY-MM-DD-report-description
---
```

- `tags`: caller can add more (e.g., `"30-minute"`, `"exploration"`)
- `project`: optional, include if known from context

Write the content provided by the calling agent after the frontmatter. No content modifications -- write exactly what was provided.

### Step 3: Link in Response

After writing, print the file path as a clickable link:

```
Report saved: [REPORT_DIR/YYYY-MM-DD-report-description.md](REPORT_DIR/YYYY-MM-DD-report-description.md)
```

## Figure Handling

When the caller's content includes figures:

1. Create attachments directory relative to the report file's directory:
   ```bash
   mkdir -p "${REPORT_ATTACHMENTS_DIR}"
   ```

2. **PDF figures:** Convert to PNG first, then copy:
   ```bash
   uv run --with pdf2image python -c "
   from pdf2image import convert_from_path
   images = convert_from_path('path/to/figure.pdf')
   images[0].save('${REPORT_ATTACHMENTS_DIR}/description.png')
   "
   ```

3. **PNG/other images:** Copy directly:
   ```bash
   cp path/to/figure.png "${REPORT_ATTACHMENTS_DIR}/description.png"
   ```

4. Embed in markdown with relative paths:
   ```markdown
   ![Descriptive caption](./attachments/description.png)

   Source: [Original](relative/path/to/original/figure.pdf)
   ```

## Math and Figures Rendering

- **Inline math:** `$...$`
- **Display math:** `$$...$$`
- **Figures:** Copy to `attachments/` subfolder relative to the markdown file's directory. Embed with `![caption](./attachments/filename.png)`. Cite the original source path.

## File References

When mentioning files (scripts, outputs, figures, tables), always create markdown links with paths resolved relative to the report file's location. Do not use bare paths.

**Example:** If the report is at `notes/2026-03-07-report-analysis.md` and the referenced file is at `code/BOP/clean_data.py`:

- **Wrong:** `code/BOP/clean_data.py`
- **Correct:** [`code/BOP/clean_data.py`](../code/BOP/clean_data.py)

Compute the relative path from the markdown file's directory to the target file using `../` as needed.
