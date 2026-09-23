# PhoneMatch

Recommends the top 5 phones for a user's budget and needs. Specs and prices come from Postgres,
opinions come from YouTube review transcripts (digests + pgvector evidence), and a local LLM
(Ollama) only parses the user's intent and explains the final picks.

- Full design: `docs/HLD.md` — read the relevant section before starting any milestone.
- Coding standards: `docs/coding-standards.md` — follow it for every change.
- Folder rules: `app/CLAUDE.md` (API) and `jobs/CLAUDE.md` (cron jobs).

## Stack

Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2.0 async + Alembic · PostgreSQL 16 + pgvector ·
Ollama (local, Qwen family) · sentence-transformers `BAAI/bge-small-en-v1.5` · yt-dlp ·
youtube-transcript-api · rapidfuzz · httpx + selectolax · Typer (job CLIs) · Streamlit (UI) ·
pytest · ruff · mypy · uv (package manager) · Docker Compose (Postgres).

## Architecture style

Modular monolith. One codebase, separate processes: API (`app/`), cron jobs (`jobs/`), UI (`ui/`),
Postgres, Ollama. `app/` and `jobs/` share models, schemas and `LLMClient`. Do not introduce
microservices, message queues, Redis or new infra unless asked.

## Non-negotiable rules

1. All LLM calls go through `app/llm/client.py` (`LLMClient`). Never call Ollama/HTTP directly.
2. Every LLM output is validated by a Pydantic model. Every LLM step has a non-LLM fallback.
3. Prices and specs shown to users come only from the DB, never from LLM text.
4. The LLM never ranks from scratch: SQL filters + scores, the LLM picks and explains from candidates.
5. Jobs are idempotent (upsert on natural keys) and resumable (per-row `status`); log to `job_runs`.
6. Schema changes only through Alembic migrations. Never edit an applied migration.
7. Prompts live in `app/prompts/*.md`, never inline strings. Bump `PROMPT_VERSION` when changed.
8. Config via `config/settings.py` (pydantic-settings, `.env`). No hard-coded URLs, keys or model tags.
9. No new dependencies without asking first.
10. Every change comes with tests; `make test` and `make lint` must pass before you say "done".

## Commands

```
make up          # start Postgres (docker compose), waits until healthy
make down        # stop containers (data volume is kept)
make db-shell    # psql into the main DB
make migrate     # alembic upgrade head
make api         # uvicorn app.main:app --reload
make ui          # streamlit run ui/streamlit_app.py
make test        # pytest
make lint        # ruff check + ruff format --check + mypy
make nightly     # scripts/run_nightly.sh (jobs 2-6)
python -m jobs.<name> --help
```

## How to work in this repo

- One milestone per session (`docs/HLD.md` §13). State which milestone you are doing.
- Order of work: **spec → plan → code**, with an approval gate after each document:
  1. Write `.claude/specs/<Mx-name>.md` from `.claude/specs/_TEMPLATE.md` (what/why, contracts:
     Pydantic schemas, SQL, signatures). **Stop for approval.**
  2. Write `.claude/plans/<Mx-name>.md` (same file name) from `.claude/plans/_TEMPLATE.md`
     (files, ordered steps, tests, verification). **Stop for approval.**
  3. Code: schemas/SQL → tests → implementation. Tick the plan's checkboxes, log deviations,
     and set the plan's status to `done` at the end. If the spec turns out wrong, update it and ask first.
- Keep changes scoped to the milestone. If you spot something else, list it at the end instead of fixing it.
- If the HLD and the code disagree, ask; don't silently pick one. If you change a design decision,
  update `docs/HLD.md` in the same change.
- End every session with: what was done, how to run it, what's left, any open questions.

## Gotchas

- Ollama: always set `num_ctx` explicitly (default silently truncates) and pass a JSON schema via `format`.
- Title matching: "Pro" must never match "Pro+" / "Pro Max". Variant tokens: pro, plus, max, ultra, lite, fe, neo, mini.
- YouTube: sleep 3–5 s between transcript fetches; stop the run on HTTP 429.
- Embeddings are 384-dim (bge-small). Changing the model means a migration + full re-embed.
- Docker runs infra only (Postgres). API, jobs, UI and Ollama run natively. Tests use the
  `phonematch_test` DB (created by `docker/postgres/init/` on an empty volume only) and need `make up`.
- The MacBook Air is fanless: long LLM jobs throttle; run them overnight.
