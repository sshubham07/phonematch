---
name: implement-milestone
description: Implement one PhoneMatch build milestone (M0-M8 from docs/HLD.md §13) end to end - read the design, write spec.md then plan.md (each approved), build, test, and report. Use when asked to "do M2", "start milestone 3", "implement the next milestone".
---

# Implement a milestone

1. **Identify the milestone.** Find it in `docs/HLD.md` §13 (table: milestone, "done when", estimate).
   If the user didn't say which, check git log / existing code and propose the next unfinished one.
2. **Read only what it needs.** The HLD sections referenced by that milestone, plus `app/CLAUDE.md`
   or `jobs/CLAUDE.md` for the folder you'll work in, plus `docs/coding-standards.md`.
3. **Write the spec, then stop for approval.** Copy `.claude/specs/_TEMPLATE.md` to
   `.claude/specs/<Mx-name>.md` (e.g. `M0-repo-skeleton.md`) and fill in the goal, scope,
   requirements and contracts:
   - Pydantic schemas and function signatures you'll add
   - SQL / Alembic changes
   - Config keys, edge cases/fallbacks, acceptance criteria
   - Any dependency you want to add (ask; never add silently)
   Once the user approves, set `Status: approved`.
3b. **Write the plan, then stop for approval.** Copy `.claude/plans/_TEMPLATE.md` to
   `.claude/plans/<Mx-name>.md` (same file name) and fill in the files, ordered steps, test plan
   and verification. Once the user approves, set `Status: approved`. Tick its checkboxes while
   coding, and log any deviation. If the spec turns out wrong, update it and ask before continuing.
4. **Write tests first** for the core logic (matching, scoring, validation, parsing), using fakes and
   fixtures — no real Ollama/YouTube/Flipkart calls in unit tests.
5. **Implement** in small steps. Keep routers/job modules thin; logic in importable functions.
6. **Verify:** run `make lint` and `make test`. Then run the milestone's "done when" check for real
   (e.g. `python -m jobs.match_videos --limit 50`) and report the numbers.
7. **Update docs** if you changed any design decision (`docs/HLD.md`) or learned a rule worth keeping
   (one line in the relevant `CLAUDE.md`).
8. **Report:** set the plan's status to `done`. Then report what was built, how to run it, results of the "done when" check, what's left, open questions.
   Suggest a conventional commit message.
