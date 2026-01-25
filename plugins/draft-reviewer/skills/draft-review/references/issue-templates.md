# Issue Reporting Templates

Standardized formats for reporting review findings.

## Issue Report Format

Each issue should be reported using this structure:

```markdown
### [SEVERITY] [Category]: [Brief Title]

**Location:** [Section/Page/Equation/Table reference]

**Issue:** [Clear description of the problem]

**Evidence:** [Quote or reference to specific text/equation]

**Suggestion:** [Recommended fix or improvement]

**Auto-fixable:** [Yes/No]
```

## Severity Levels

### Critical (Priority 1)
Issues that invalidate results or major claims.

Indicators:
- Mathematical errors that change conclusions
- Data inconsistencies affecting key results
- Contradictory claims about main findings
- Missing critical methodological details

Example:
```markdown
### CRITICAL Mathematical: Sign Error in Main Derivation

**Location:** Appendix A, Equation (A.3)

**Issue:** The derivative of the utility function has incorrect sign, which propagates to the main theoretical result.

**Evidence:**
- Eq (A.2): U = -exp(-γW)
- Eq (A.3) claims: dU/dW = exp(-γW)
- Correct: dU/dW = γ·exp(-γW)

**Suggestion:** Correct the derivative and verify all subsequent equations that depend on this result.

**Auto-fixable:** No
```

### Major (Priority 2)
Issues that affect comprehension or require significant revision.

Indicators:
- Logical gaps in argumentation
- Unclear methodology affecting reproducibility
- Significant notation inconsistencies
- Writing issues that impede understanding

Example:
```markdown
### MAJOR Clarity: Identification Strategy Unclear

**Location:** Section 3.2, paragraphs 2-4

**Issue:** The instrumental variable strategy is introduced but the exclusion restriction is never explicitly stated or justified.

**Evidence:** "We instrument X with Z" (p. 12) but no discussion of why Z affects Y only through X.

**Suggestion:** Add explicit statement of exclusion restriction and provide economic justification for why Z satisfies it.

**Auto-fixable:** No
```

### Minor (Priority 3)
Issues that are small and often auto-fixable.

Indicators:
- Typos and grammatical errors
- Minor formatting inconsistencies
- Small notation inconsistencies
- Reference format issues

Example:
```markdown
### MINOR Typo: Misspelling

**Location:** Section 4.1, paragraph 3, line 2

**Issue:** "heteroskedasticity" misspelled as "heteroskedastisity"

**Evidence:** "...robust to heteroskedastisity..."

**Suggestion:** Change to "heteroskedasticity"

**Auto-fixable:** Yes
```

## Category-Specific Templates

### Mathematical Issues

```markdown
### [SEVERITY] Mathematical: [Title]

**Location:** [Equation number or section]

**Issue:** [Description of mathematical error]

**Current:** [What the paper says]
**Correct:** [What it should be]

**Verification Method:** [How you verified - symbolic/numerical]

**Impact:** [What results/claims are affected]

**Auto-fixable:** [Yes only for trivial notation fixes]
```

### Writing/Clarity Issues

```markdown
### [SEVERITY] Clarity: [Title]

**Location:** [Section, paragraph, or page]

**Issue:** [Description of clarity problem]

**Current text:** "[Problematic sentence or passage]"

**Suggested revision:** "[Improved version]"

**Reason:** [Why the change improves clarity]

**Auto-fixable:** [Yes for minor rewording, No for substantial revision]
```

### Consistency Issues

```markdown
### [SEVERITY] Consistency: [Title]

**Location A:** [First location]
**Location B:** [Second location with conflict]

**Issue:** [Description of inconsistency]

**At Location A:** [What it says/shows]
**At Location B:** [What it says/shows]

**Resolution:** [Which is correct, or how to reconcile]

**Auto-fixable:** [Yes if simple number fix]
```

### Citation Issues

```markdown
### [SEVERITY] Citation: [Title]

**Location:** [Where citation appears or should appear]

**Issue:** [Description of citation problem]

**Current:** [Current state]
**Suggested:** [Correction]

**Auto-fixable:** [Yes for format fixes, No for missing citations]
```

### Code-Paper Consistency Issues

```markdown
### [SEVERITY] Code-Paper: [Title]

**Paper Location:** [Section/equation in paper]
**Code Location:** [File:line in code]

**Issue:** [Description of discrepancy]

**Paper says:** [Paper description]
**Code does:** [Code behavior]

**Resolution:** [Which is correct and what needs updating]

**Auto-fixable:** No (requires author decision)
```

## Aggregated Report Template

```markdown
# Draft Review Report

**Paper:** [Title]
**Date:** [Review date]
**Scope:** [Review scope selected]
**Thoroughness:** [Level selected]

## Executive Summary

| Severity | Count | Auto-fixable |
|----------|-------|--------------|
| Critical | X     | 0            |
| Major    | Y     | 0            |
| Minor    | Z     | N            |
| **Total**| **T** | **N**        |

### Top Priorities
1. [Most critical issue - one line summary]
2. [Second most critical]
3. [Third most critical]

---

## Critical Issues

[List all critical issues using templates above]

---

## Major Issues

[List all major issues using templates above]

---

## Minor Issues

[List all minor issues using templates above]

---

## Auto-Fixable Items Summary

For user approval before task creation:

| # | Location | Issue | Fix |
|---|----------|-------|-----|
| 1 | p.5, ¶2  | Typo  | "teh" → "the" |
| 2 | Eq (3)   | Notation | "α" → "β" (consistency) |
| ... | ... | ... | ... |

---

## Review Coverage

### Sections Reviewed
- [x] Abstract
- [x] Introduction
- [x] Section 2: [Title]
- ...

### Agents Used
- [x] Mathematical Reviewer
- [x] Writing Clarity Reviewer
- ...

### Limitations
- [Any sections not reviewed or limitations of the review]
```

## Task Creation Format

When creating tasks for auto-fixable issues (after user permission):

```markdown
Subject: Fix [issue type] in [location]

Description:
- Location: [precise location]
- Current: [current text/equation]
- Change to: [corrected version]
- Reason: [brief explanation]

Source: Draft Review - [timestamp]
```
