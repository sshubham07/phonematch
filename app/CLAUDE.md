# app/ — FastAPI service rules

Design reference: `docs/HLD.md` §10 (request flow), §11 (user input), §12 (API).

## Layout

- `api/v1/` — routers only: parse request, call a service, return a schema. No business logic, no SQL.
- `services/` — one module per request step: `intent.py`, `ranker.py`, `evidence.py`, `cards.py`,
  `recommender.py` (steps 5 + 6), `clarify.py`.
- `schemas/` — Pydantic models for requests, responses, `UserIntent`, `PhoneCard`, LLM outputs.
- `db/` — SQLAlchemy models, async session, Alembic.
- `llm/client.py` — the only place that talks to Ollama.
- `prompts/` — `intent.md`, `map.md`, `reduce.md`, `recommend.md`.

## Rules

- Routers are thin; services are plain async functions/classes that receive dependencies
  (session, `LLMClient`) as arguments so they are easy to test with fakes.
- Use FastAPI `Depends` for the DB session, settings and `LLMClient`.
- Ranking and filtering are SQL (`services/ranker.py`); keep the scoring formula in one function
  with unit tests. Weights must sum to 1.
- Step 6 validation is mandatory: every `phone_id` must be in the candidate set, every evidence id
  must exist and belong to that phone, and price/specs are re-read from the DB.
- Fallbacks: intent LLM fails → form values + default profile; recommender fails twice → SQL top 5
  with template reasons. Set `fallback_used=true` in the response.
- Clarification: max 1 question per session, chosen from the fixed bank in `clarify.py`.
  Budget is the only hard blocker.
- Response errors: 422 for bad input, 503 when Ollama is down (still return SQL-only results if possible).
- Log one structured line per request step with `request_id` and latency; write a `query_logs` row.

## Testing

- Unit-test services with a `FakeLLMClient` that returns canned JSON (valid, invalid, timeout).
- API tests with `httpx.AsyncClient` against a test database (transaction rolled back per test).
- Never hit real Ollama in unit tests; mark real-LLM tests `@pytest.mark.llm` (skipped by default).
