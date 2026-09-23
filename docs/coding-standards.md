# Coding standards

Applies to all Python code in this repo. Tooling enforces most of it (`make lint`); the rest is on review.

## General

- Python 3.12, full type hints on every function signature. `mypy --strict` on `app/` and `jobs/`.
- Formatting and linting: `ruff format` + `ruff check` (line length 100). Don't argue with the formatter.
- Small functions (aim < 40 lines), one responsibility each. Prefer pure functions for logic
  (matching, scoring, chunking) so they're trivial to test.
- No global mutable state. Pass dependencies in (session, settings, `LLMClient`).
- No `print` — use the logger. No bare `except:`; catch specific exceptions.
- No commented-out code, no TODOs without an owner/issue reference.

## Naming

- Modules and functions: `snake_case`. Classes: `PascalCase`. Constants: `UPPER_SNAKE`.
- Pydantic request/response models end with `Request` / `Response`; LLM output models end with `LLMOut`
  (e.g. `DigestLLMOut`, `RecommendationLLMOut`).
- DB tables: plural `snake_case` (`phones`, `review_chunks`). Columns: `snake_case`, units in the name
  where useful (`battery_mah`, `duration_s`, `price_from`).
- Booleans read as questions: `is_5g`, `has_ois`, `low_confidence`.

## Async and DB

- FastAPI handlers and services are `async`. Use SQLAlchemy 2.0 async sessions.
- CPU-heavy work (embeddings) runs in jobs, or via `run_in_threadpool` in the API.
- Complex queries (ranking, vector search) may be raw SQL via `text()` with bound parameters —
  never string-format SQL.
- One transaction per request; jobs commit per row or small batch.

## Pydantic and validation

- Pydantic v2 everywhere data crosses a boundary: HTTP, LLM output, YAML config, external APIs.
- Use `Literal` / `Enum` for closed sets (aspects, statuses, tiers).
- Validate LLM JSON with `Model.model_validate_json(...)`; on failure retry once with the error
  message appended, then use the fallback.

## Errors and logging

- Custom exceptions in `app/errors.py` (`LLMUnavailable`, `LLMInvalidOutput`, `ExternalRateLimited`, ...).
- Map exceptions to HTTP codes in one exception handler, not in every route.
- Structured JSON logs: `event`, `request_id` or `job_run_id`, `latency_ms`, plus context fields.
- Never log secrets, API tokens, or full transcripts (log `video_id` and length instead).

## LLM usage

- Only through `LLMClient`. Always: JSON schema in `format`, explicit `num_ctx`, `temperature` set.
- Prompts in `app/prompts/*.md` with `{placeholders}`; loaded by name; `PROMPT_VERSION` constant.
- Never put prices/specs from LLM output into a response; join them from the DB.

## Config and secrets

- All config in `config/settings.py` (pydantic-settings) reading `.env`. `.env` is git-ignored;
  `.env.example` lists every key with a dummy value.
- Model tags, DB URL, Flipkart keys, rate limits, `num_ctx` are settings, not literals.

## Testing

- pytest + pytest-asyncio. Tests mirror source paths: `app/services/ranker.py` → `tests/app/services/test_ranker.py`.
- Test names describe behaviour: `test_pro_does_not_match_pro_plus`.
- Unit tests never call Ollama, YouTube or Flipkart — use fakes and saved fixtures in `tests/fixtures/`.
- Integration tests use a real Postgres (docker) with per-test rollback.
- Mark slow/real-service tests: `@pytest.mark.llm`, `@pytest.mark.network` (skipped by default).
- Every bug fix adds a failing test first.

## Git

- Small commits, one milestone or one logical change each.
- Conventional commit messages: `feat(jobs): add match_videos`, `fix(ranker): normalise weights`.
- Never commit `.env`, `data/raw/`, model files or notebooks with outputs.
