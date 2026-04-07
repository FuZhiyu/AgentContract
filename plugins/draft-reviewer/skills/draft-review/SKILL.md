---
name: draft-review
description: "Comprehensive academic paper review covering mathematical correctness, writing clarity, consistency, argumentation, proofreading, and citations. Use when user asks to 'review draft', 'check paper', 'proofread manuscript', or requests feedback on academic writing. Can also verify code-paper consistency when source code is available. Defaults to comprehensive + standard review, with optional deep parallel review when Codex multi-agent support is available."
user-invocable: true
---

# Draft Review Skill

Review an academic draft rigorously and report issues by severity.

## Inputs

- Primary document path: PDF, TeX, Markdown, or plain text
- Optional code path when the user wants code-paper consistency checks
- Optional scope override: `comprehensive`, `mathematical`, `writing`, `quick-proof`
- Optional thoroughness override: `quick`, `standard`, `deep`

If the user does not specify scope or thoroughness, use:
- Scope: `comprehensive`
- Thoroughness: `standard`

If the paper path or review target is ambiguous, ask the user a direct plain-language question before proceeding.

## Review Workflow

### Phase 1: Document Ingestion

1. **PDF input**
   - Prefer converting the PDF to Markdown with the `mistral-pdf-to-markdown` skill if it is available.
   - If that skill is not installed, extract text locally or ask the user for a TeX/Markdown source when equation fidelity matters.
2. **TeX/Markdown input**
   - Read the source directly. Prefer TeX when mathematical precision matters.
3. **Code input (optional)**
   - If the user supplied a code path, identify only the files needed to verify claims, definitions, tables, figures, and empirical procedures.

After ingestion, create a compact document summary:
- Paper title and abstract
- Section structure with approximate lengths
- List of figures and tables with captions
- Key notation/variable definitions index

### Phase 2: Review Configuration

Use explicit user instructions when present. Otherwise:
- `comprehensive`: math, writing, consistency, argumentation, proofreading, citations, and optional code-paper consistency
- `mathematical`: derivations, equations, proofs, notation
- `writing`: clarity, structure, terminology
- `quick-proof`: typos, grammar, formatting

Thoroughness levels:
- `quick`: surface pass focused on highest-probability issues
- `standard`: one careful pass per relevant category
- `deep`: parallel or repeated review for maximum coverage

### Phase 3: Optional Agent Delegation

Deep review is optional. Only use multi-agent delegation when all of the following are true:
- the user explicitly asked for deep, parallel, or multi-agent review, or approved delegation after you proposed it
- the current Codex session supports multi-agent work
- the extra review cost is justified by the document complexity

When available, prefer the standalone reviewer roles installed by `scripts/install_codex_skills.py`. Their `agent_type` values are:

| `agent_type` | Purpose |
|--------------|---------|
| `draft-reviewer__mathematical-reviewer` | Verify derivations, proofs, equations, notation |
| `draft-reviewer__writing-clarity-reviewer` | Writing quality and clarity |
| `draft-reviewer__consistency-checker` | Internal consistency of claims, numbers, terminology |
| `draft-reviewer__argument-logic-reviewer` | Logical flow and argumentation |
| `draft-reviewer__proofreader` | Typos, grammar, formatting |
| `draft-reviewer__citation-checker` | Citation completeness and accuracy |
| `draft-reviewer__code-paper-consistency` | Verify code matches paper claims (if code provided) |

If those installed roles are not present, either:
- perform the review inline in the main thread, or
- if the user explicitly requested deep parallel review, spawn generic worker agents with category-specific prompts

Never rely on the old `plugin:agent` role syntax.

### Phase 4: Deep Mode Strategy

When thoroughness is `deep`, use one of these approaches:

1. **Installed-role parallel review**
   - Spawn one reviewer per relevant category.
   - For especially important categories, use two complementary perspectives.
2. **Generic-worker parallel review**
   - Only if installed roles are unavailable and the user still wants parallel review.
   - Give each worker a narrowly scoped prompt and a clear output contract.
3. **Inline fallback**
   - If multi-agent delegation is unavailable, do the same review categories yourself in sequence.

Useful perspective variations:
- Reviewer A: skeptical referee looking for flaws
- Reviewer B: constructive mentor suggesting improvements
- Reviewer C: domain specialist focusing on the method that matters most

Useful traversal variations:
- Start from beginning and work forward
- Start from conclusions and trace claims backward
- Start from the most technical section first

After any delegated runs, merge findings:
- Deduplicate overlapping issues
- Mark issues found by multiple reviewers as higher confidence
- Keep unique findings that may catch edge cases

### Phase 5: Result Aggregation

Collect all findings and organize by severity:

**Critical (Priority 1):**
- Mathematical errors in proofs or derivations
- Contradictory claims
- Missing critical references
- Data inconsistencies affecting results

**Major (Priority 2):**
- Logical gaps in argumentation
- Unclear methodology descriptions
- Significant notation inconsistencies
- Writing clarity issues affecting comprehension

**Minor (Priority 3):**
- Typos and grammatical errors
- Minor formatting issues
- Small notation inconsistencies
- Reference format issues

### Phase 6: Actionable Follow-up

If the user wants a follow-up plan, provide a plain Markdown checklist grouped by severity instead of assuming a task-management tool exists.

Example:

```markdown
## Action Items
- [ ] Fix Equation (14) sign error in Appendix A
- [ ] Define `kappa_t` on first use in Section 2
- [ ] Rephrase paragraph 3 on page 9 for clarity
```

## Scope to Reviewer Mapping

| Review focus | Comprehensive | Mathematical | Writing | Quick |
|--------------|:-------------:|:------------:|:-------:|:-----:|
| Mathematical reviewer | ✓ | ✓ | | |
| Writing clarity reviewer | ✓ | | ✓ | |
| Consistency checker | ✓ | | | |
| Argument/logic reviewer | ✓ | | | |
| Proofreader | ✓ | | | ✓ |
| Citation checker | ✓ | | | |
| Code-paper consistency | ✓* | | | |

*Only if a code path was provided

## Optional `spawn_agent` Template

If you use installed reviewer roles, pass focused context instead of the entire document:

```text
agent_type: draft-reviewer__mathematical-reviewer
message:
  Review the attached paper sections for mathematical correctness.

  Document summary:
  [title, abstract, section map]

  Sections to review:
  [only the relevant sections]

  Cross-reference index:
  [notation, tables, figures]

  Output format:
  ### [SEVERITY] [Category]: [Brief Title]
  **Location:** [Section/equation/page]
  **Issue:** [Description]
  **Recommendation:** [Suggested fix]
  **Auto-fixable:** [Yes/No]
```

## Output Format

Final report structure:

```markdown
# Draft Review Report: [Paper Title]

## Summary
- Total issues found: X
- Critical: X | Major: X | Minor: X
- Review scope: [scope]
- Thoroughness: [level]

## Critical Issues
[List with full details and recommendations]

## Major Issues
[List with details and suggestions]

## Minor Issues
[List with specific corrections]

## Auto-Fixable Items
[List of items that can be addressed quickly]
```

## Dependencies

- Optional: `mistral-pdf-to-markdown` skill for higher-quality PDF ingestion
- Optional: advanced installer roles created by `scripts/install_codex_skills.py`
