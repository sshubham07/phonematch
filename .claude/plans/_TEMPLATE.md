# Plan: <Mx> — <short name>

- **Spec:** ../specs/<same-file-name>.md (must be `approved` before this plan is written)
- **Status:** draft | approved | in-progress | done
- **Date:** YYYY-MM-DD

> A plan says *how* the approved spec gets built. If coding shows the spec is wrong, stop,
> update the spec, and ask. Don't drift silently.

## 1. Files
| Action | Path | Purpose |
|---|---|---|
| create | `app/...` | … |
| modify | `...` | … |

## 2. Steps
Order: schemas / SQL / interfaces → tests → implementation → docs. Keep each step small.
Tick the boxes while coding.

- [ ] 1. Schemas / models / migration — …
- [ ] 2. Tests for core logic (fakes, no real Ollama/YouTube/Flipkart) — …
- [ ] 3. Implementation — …
- [ ] 4. Wire-up (router / CLI / Makefile) — …
- [ ] 5. Docs — HLD / CLAUDE.md updates if a decision changed

## 3. Test plan
- **Unit:** … (which fakes/fixtures, e.g. `FakeLLMClient` with valid / invalid / timeout)
- **Integration:** … (test DB, transaction rolled back per test)
- **Real-LLM (`@pytest.mark.llm`, skipped by default):** …

## 4. Verification
```
make lint
make test
<the milestone's "done when" check, e.g. python -m jobs.<name> --limit 50>
```
Expected result: …

## 5. Risks and rollback
- …

## 6. Deviations
Filled in while coding: anything that differed from this plan, and why.

- …
