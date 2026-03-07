# draft-reviewer

Multi-agent academic paper review plugin with 7 specialized reviewer agents.

## Structure

- `skills/draft-review/SKILL.md` -- single skill that orchestrates all agents
- `agents/*.md` -- standalone agent definitions, each with YAML frontmatter

## Agents

All agents require YAML frontmatter (`name`, `description`, `tools`):

| Agent | Focus |
|-------|-------|
| `mathematical-reviewer` | Derivations, proofs, equations, notation |
| `writing-clarity-reviewer` | Structure, readability, terminology |
| `proofreader` | Typos, grammar, punctuation, formatting |
| `consistency-checker` | Internal consistency, cross-references |
| `citation-checker` | Citation completeness and format |
| `argument-logic-reviewer` | Logical structure and evidence |
| `code-paper-consistency` | Code-paper alignment |

## Thoroughness Levels

- **quick**: single-agent sequential review
- **standard** (default): key agents run sequentially
- **deep**: all agents run in parallel
