---
name: draft-review
description: Comprehensive academic paper review using specialized agents. Covers mathematical correctness (with numerical verification), writing clarity, terminology consistency, internal consistency, argumentation, proofreading, and citations. Use when user asks to "review draft", "check paper", "proofread manuscript", or requests feedback on academic writing. Can also verify code-paper consistency when source code is available. Supports thoroughness levels: quick, standard (default), deep (parallel agents).
user-invocable: true
---

# Draft Review Skill

A multi-agent academic paper review system that provides comprehensive feedback across multiple dimensions.

## Usage

```
/draft-review path/to/paper.pdf
/draft-review path/to/paper.tex --code path/to/code/
```

## Review Workflow

### Phase 1: Document Ingestion

1. **PDF Input**: Convert PDF to markdown using mistral-pdf-to-markdown skill
2. **TeX Input**: Read tex file directly for mathematical precision
3. **Code (Optional)**: Index relevant code files if path provided

After ingestion, create a document structure summary:
- Paper title and abstract
- Section structure with approximate lengths
- List of figures and tables with captions
- Key notation/variable definitions index

### Phase 2: Review Configuration

Use AskUserQuestion to configure the review:

**Question 1: Review Scope**
```
header: "Scope"
question: "Which aspects should I review?"
options:
  - label: "Comprehensive (Recommended)"
    description: "All review aspects: math, writing, consistency, arguments, proofreading, citations"
  - label: "Mathematical"
    description: "Focus on derivations, equations, proofs, and notation"
  - label: "Writing & Clarity"
    description: "Writing quality, terminology consistency, and structure"
  - label: "Quick Proof"
    description: "Typos, grammar, and formatting only"
multiSelect: false
```

**Question 2: Thoroughness Level**
```
header: "Thoroughness"
question: "How thorough should the review be?"
options:
  - label: "Standard (Recommended)"
    description: "Thorough single-agent review per category"
  - label: "Quick"
    description: "Fast surface-level review"
  - label: "Deep"
    description: "Multiple parallel agents per category with diverse perspectives for maximum coverage"
multiSelect: false
```

### Phase 3: Dispatch Subagents

Based on configuration, dispatch appropriate subagents using the Task tool:

| Scope | Agents to Dispatch |
|-------|-------------------|
| Comprehensive | All 6 (or 7 if code provided) |
| Mathematical | mathematical-reviewer only |
| Writing & Clarity | writing-clarity-reviewer only |
| Quick Proof | proofreader only |

For each subagent, provide:
1. **Document Summary** (~500 tokens): Title, abstract, section structure
2. **Relevant Sections** (~2000-5000 tokens): Only sections pertinent to that agent's focus
3. **Cross-Reference Index**: Tables, figures, key definitions

#### Example Context for Mathematical Reviewer
```
Document: [title], [abstract summary]
Sections to Review: Appendix A, Appendix B, Section 3 (Model)
Notation Index: {ζ: elasticity, σ²: variance, β: coefficient, ...}
Tables Referenced: Table 1 (main estimates), Table B.3 (robustness)
```

### Phase 4: Deep Mode - Parallel Agent Strategy

When thoroughness is "Deep", run 2-3 agents per category with diverse perspectives:

**Perspective Variations:**
- Agent A: "Review as a skeptical referee looking for flaws"
- Agent B: "Review as a constructive mentor suggesting improvements"
- Agent C: "Review as a domain expert in [specific methodology]"

**Focus Ordering Variations:**
- Agent A: Start from beginning, work forward
- Agent B: Start from conclusions, trace claims backward
- Agent C: Start from most complex/critical section

After parallel runs, merge findings:
- Deduplicate similar issues
- Flag issues found by multiple agents as higher confidence
- Include unique findings (may catch edge cases)

### Phase 5: Result Aggregation

Collect all subagent outputs and organize by severity:

**Critical (Priority 1):**
- Mathematical errors in proofs/derivations
- Contradictory claims
- Missing critical references
- Data inconsistencies affecting results

**Major (Priority 2):**
- Logical gaps in argumentation
- Unclear methodology descriptions
- Significant notation inconsistencies
- Writing clarity issues affecting comprehension

**Minor (Priority 3) - Potentially Auto-fixable:**
- Typos and grammatical errors
- Minor formatting issues
- Small notation inconsistencies
- Reference format issues

### Phase 6: Task Generation (User Permission Required)

Present summary to user:
```
Review complete. Found:
- X Critical issues
- Y Major issues
- Z Minor issues (N auto-fixable)
```

Use AskUserQuestion:
```
header: "Tasks"
question: "Would you like me to create tasks for auto-fixable minor issues?"
options:
  - label: "Yes, create tasks (Recommended)"
    description: "I'll create TodoWrite tasks for typos, formatting, and other quick fixes"
  - label: "No, show report only"
    description: "Just show the full review report without creating tasks"
multiSelect: false
```

If approved, use TodoWrite to create tasks for each auto-fixable issue.

## Subagent Dispatch Instructions

Use the Task tool with `subagent_type: "general-purpose"` for each review agent.

### Dispatch Template

```
Task tool parameters:
  subagent_type: "general-purpose"
  description: "[Agent type] review"
  prompt: |
    You are acting as a [agent-type]-reviewer for an academic paper.

    [Read the agent file at agents/[agent-name].md for detailed instructions]

    Document Summary:
    [Insert summary]

    Sections to Review:
    [Insert relevant sections]

    Cross-Reference Index:
    [Insert index]

    Output your findings using the issue template format from references/issue-templates.md
```

### Scope to Agent Mapping

| Agent File | Comprehensive | Mathematical | Writing | Quick |
|------------|:-------------:|:------------:|:-------:|:-----:|
| mathematical-reviewer.md | ✓ | ✓ | | |
| writing-clarity-reviewer.md | ✓ | | ✓ | |
| consistency-checker.md | ✓ | | | |
| argument-logic-reviewer.md | ✓ | | | |
| proofreader.md | ✓ | | | ✓ |
| citation-checker.md | ✓ | | | |
| code-paper-consistency.md | ✓* | | | |

*Only if code path provided

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
[List of items that can be addressed via tasks]
```

## Dependencies

- `mistral-pdf-to-markdown` skill (for PDF input)
- Task tool with general-purpose subagent
- TodoWrite tool (for task generation)
- AskUserQuestion tool (for configuration)
- Read, Glob, Grep tools (for document processing)

## Notes

- Each review session focuses on one paper for thorough analysis
- For papers >40 pages, the hierarchical context management is critical
- Always read the full tex source if available (more precise than PDF conversion)
- Code-paper consistency check requires explicit code path
