# Spec: <Mx> — <short name>

- **Milestone:** <Mx> (docs/HLD.md §13)
- **Status:** draft | approved
- **Date:** YYYY-MM-DD
- **HLD sections:** §<n>, §<n>
- **Plan:** ../plans/<same-file-name>.md (written after this spec is approved)

> A spec says *what* gets built and *why*. It has no implementation steps; those go in the plan.

## 1. Goal
<1–3 lines: what this milestone delivers and why it matters.>

**Done when (from HLD §13):** <copy the "done when" cell>

## 2. Scope
**In:**
- …

**Out (explicitly not in this milestone):**
- …

## 3. Requirements
Numbered and testable. Each one maps to at least one acceptance test in §6.

1. R1 — …
2. R2 — …

## 4. Contracts
The interfaces that must be reviewed before any code is written.

### Pydantic schemas
```python
class Example(BaseModel): ...
```

### SQL / Alembic changes
```sql
-- tables, columns, indexes, constraints
```

### Functions / CLI / API signatures
```python
async def example(session: AsyncSession, llm: LLMClient, ...) -> Example: ...
```

### Config / env keys
| Key | Default | Purpose |
|---|---|---|

## 5. Edge cases and failure modes
Include the fallbacks CLAUDE.md requires (LLM failure, Ollama down, rate limits, idempotent re-runs).

- …

## 6. Acceptance criteria
| # | Criterion | Proven by (test / command) |
|---|---|---|
| A1 | … | `tests/...::test_...` |

## 7. Dependencies
New packages need approval before they are added.

- None / `<package>` — why

## 8. Open questions
- …
