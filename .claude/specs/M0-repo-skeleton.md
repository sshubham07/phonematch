# Spec: M0 — Repo skeleton, Docker Postgres, initial schema

- **Milestone:** M0 (docs/HLD.md §13)
- **Status:** approved (decisions in §9; schema tightened by delegation — see §4)
- **Date:** 2026-09-23
- **HLD sections:** §3 (stack), §8 (database), §9 (pgvector), §12 (`/health`), §13 (structure)
- **Plan:** ../plans/M0-repo-skeleton.md

> A spec says *what* gets built and *why*. It has no implementation steps; those go in the plan.

## 1. Goal
Give every later milestone a runnable base: infrastructure dependencies run in Docker (Postgres 16 +
pgvector now; more services can be added later without restructuring), the full §8 schema created
through one Alembic migration, typed settings, and a `/api/v1/health` endpoint that reports DB,
Ollama and last job-run status.

**Done when (from HLD §13):** `docker compose up` + `/health` green.

## 2. Scope
**In:**
- `docker-compose.yml` with a `db` service (`pgvector/pgvector:pg16`), healthcheck, named volume,
  and an init script that also creates a `phonematch_test` database for integration tests.
  Written so extra infra services can be added later as new blocks, with no other changes.
- `pyproject.toml` (uv): runtime + dev dependencies (§7), ruff (line length 100), mypy strict,
  pytest config (asyncio mode, `llm` / `network` markers skipped by default).
- `Makefile` installed from `_setup/Makefile.txt`, plus `down`, `db-shell` targets; `make up` waits
  until the DB is healthy.
- `config/settings.py` (pydantic-settings, reads `.env`); `.env.example` updated with the new keys.
- SQLAlchemy 2.0 models for all 10 tables (§4) in `app/db/models.py`; async engine/session in
  `app/db/session.py`.
- Alembic under `app/db/alembic/` (async `env.py`), one migration `0001_initial_schema` that creates
  the `vector` extension, all 10 tables, constraints and indexes from §4, with a working `downgrade()`.
- Install `_setup/` into place, then delete `_setup/`: `Makefile.txt` → `Makefile`,
  `claude/settings.json` → `.claude/settings.json`, `claude/hooks/*` → `.claude/hooks/`,
  `claude/skills/*/SKILL.md` → `.claude/skills/*/` (target folders already exist, empty).
- Minimal `app/llm/client.py`: `LLMClient` with only `ping()` (so the health check obeys rule 1 —
  no direct Ollama HTTP outside `LLMClient`). Generation methods come in M4.
- FastAPI app (`app/main.py`) with `GET /api/v1/health`.
- Tests for settings, migration (up/down/up), models ↔ migration parity, and the health endpoint.
- Update HLD §8 to the tightened schema below (and "9 tables" → 10); §6 resumability note for
  `transcripts.embedded_at` / `map_prompt_version`.

**Out (explicitly not in this milestone):**
- Running the API, jobs or UI in Docker (decided: they run natively via `uv`).
- Running Ollama in Docker (Docker on macOS has no Metal GPU access → far slower; Ollama stays native).
- Any job, service, prompt, or endpoint other than `/health`.
- Seed data, `config/profiles.yaml`, `data/phones_seed.yaml` (M1).
- Structured-logging middleware / `request_id` (M6, when there are real requests to log).
- `git init` / commits (user will do it later).

## 3. Requirements
1. R1 — `make up` starts Postgres 16 with pgvector ≥ 0.8 and returns only once the container is healthy.
   Data survives `make down` / `make up` (named volume).
2. R2 — The Postgres container creates two databases on first start: `phonematch` and `phonematch_test`.
3. R3 — `make migrate` on an empty DB creates the `vector` extension and the 10 tables, constraints
   and indexes in §4 of this spec (the tightened version of HLD §8).
3b. R3b — Constraints reject bad data: e.g. an unknown `review_videos.status`, a digest score of 11,
   `feedback = 0`, or a duplicate `(phone_id, video_id, start_sec)` chunk all raise `IntegrityError`.
4. R4 — `alembic downgrade base` removes everything the migration created (tables and indexes;
   the extension is left in place), and `upgrade head` works again afterwards.
5. R5 — SQLAlchemy models match the migration: `alembic check` reports no differences.
6. R6 — All config comes from `Settings`; no URL, model tag or credential literal elsewhere in code.
   A missing required key fails fast at startup with a clear pydantic error.
7. R7 — `GET /api/v1/health` returns `HealthResponse` (§4):
   - DB reachable + Ollama reachable → HTTP 200, `status="ok"`.
   - DB reachable + Ollama down → HTTP 200, `status="degraded"` (API can still serve SQL-only results).
   - DB unreachable → HTTP 503, `status="down"`.
   - `jobs` lists the latest `job_runs` row per job name (empty list on a fresh DB).
8. R8 — Health checks are bounded: each dependency check times out (setting, default 2 s), so
   `/health` never hangs.
9. R9 — `make lint` and `make test` pass.

## 4. Contracts

### Pydantic schemas
```python
# app/schemas/health.py
CheckStatus = Literal["ok", "down"]


class DependencyCheck(BaseModel):
    status: CheckStatus
    latency_ms: int | None = None
    error: str | None = None  # short message, never secrets / URLs with credentials


class JobRunSummary(BaseModel):
    job: str
    status: str | None
    started_at: datetime | None
    finished_at: datetime | None
    processed: int | None
    failed: int | None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    database: DependencyCheck
    ollama: DependencyCheck
    jobs: list[JobRunSummary]  # latest run per job
```

### SQL / Alembic changes
Migration `0001_initial_schema`. Based on HLD §8 with these changes (why in the comments):

- **NOT NULL** on every FK, natural key and column a job always writes.
- **CHECK** instead of Postgres ENUMs for closed sets (easy to extend in a later migration):
  `price_band`, `os`, `tier`, `review_videos.status`, `job_runs.status`, 0–10 scores, `feedback`.
- **ON DELETE CASCADE** only for data derived from a phone/transcript (prices, matches, digests, chunks).
  Phones are never hard-deleted in normal operation (`is_active`), so this only matters for cleanup.
- **Natural key for chunks** `UNIQUE (phone_id, video_id, start_sec)` → `embed_chunks` can upsert (rule 5).
  It also covers the `phone_id` lookup, so the separate `phone_id` index from §8 is dropped.
- **Resumability columns:** `transcripts.map_prompt_version` (cached phase-A output is rebuilt when the
  map prompt changes), `transcripts.embedded_at` (NULL = not embedded yet → job 6 picks it up).
- **Bookkeeping:** `created_at`/`updated_at` on mutable tables, `channel_videos.first_seen_at`,
  `channels.is_active` (removed from YAML → deactivated, not deleted), `query_logs.session_id`
  (feedback and refine look up by session).
- **Indexes** for known access paths: `job_runs (job, started_at DESC)` (`/health`),
  `review_videos (status)` (job queues), `review_videos (video_id)`, `channel_videos (channel_id)`,
  `query_logs (session_id)`. All indexes/constraints get explicit names (naming convention) so
  `downgrade()` and `alembic check` are reliable.
- `updated_at` is maintained by the app (SQLAlchemy `onupdate`), no triggers.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE phones (
  id             SERIAL PRIMARY KEY,
  slug           TEXT NOT NULL UNIQUE,                 -- 'redmi-note-14-pro'
  brand          TEXT NOT NULL,
  model          TEXT NOT NULL,
  launch_date    DATE,
  price_from     INT  CHECK (price_from > 0),          -- INR, cheapest variant
  price_band     TEXT CHECK (price_band IN ('u15k','15-25k','25-40k','40-70k','70k+')),
  sales_rank     INT,
  os             TEXT CHECK (os IN ('android','ios')),
  chipset        TEXT,
  antutu         INT,
  ram_gb_max     INT,
  storage_gb_max INT,
  display_in     REAL,
  display_type   TEXT,                                 -- AMOLED / LCD
  refresh_hz     INT,
  battery_mah    INT,
  charging_w     INT,
  main_cam_mp    INT,
  has_ois        BOOLEAN,
  is_5g          BOOLEAN,
  weight_g       INT,
  ip_rating      TEXT,
  update_years   INT,
  flipkart_url   TEXT,
  gsmarena_url   TEXT,
  is_active      BOOLEAN     NOT NULL DEFAULT true,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_phones_is_active_price_from ON phones (is_active, price_from);

CREATE TABLE phone_prices (                            -- price history
  phone_id    INT  NOT NULL REFERENCES phones(id) ON DELETE CASCADE,
  variant     TEXT NOT NULL,                           -- '8/256'
  price       INT  NOT NULL CHECK (price > 0),
  mrp         INT  CHECK (mrp > 0),
  in_stock    BOOLEAN,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (phone_id, variant, captured_at)
);

CREATE TABLE channels (
  id             SERIAL PRIMARY KEY,
  handle         TEXT NOT NULL UNIQUE,
  name           TEXT NOT NULL,
  tier           TEXT NOT NULL CHECK (tier IN ('core','backup')),
  language       TEXT,
  is_active      BOOLEAN NOT NULL DEFAULT true,
  last_synced_at TIMESTAMPTZ
);

CREATE TABLE channel_videos (                          -- full catalog per channel
  video_id      TEXT PRIMARY KEY,
  channel_id    INT  NOT NULL REFERENCES channels(id),
  title         TEXT NOT NULL,
  duration_s    INT,
  published_at  DATE,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_channel_videos_channel_id ON channel_videos (channel_id);
CREATE INDEX ix_channel_videos_title_tsv  ON channel_videos USING gin (to_tsvector('simple', title));

CREATE TABLE review_videos (                           -- video matched to a phone
  id          SERIAL PRIMARY KEY,
  phone_id    INT  NOT NULL REFERENCES phones(id) ON DELETE CASCADE,
  video_id    TEXT NOT NULL REFERENCES channel_videos(video_id),
  match_score REAL CHECK (match_score BETWEEN 0 AND 100),
  status      TEXT NOT NULL DEFAULT 'pending'
              CHECK (status IN ('pending','needs_review','fetched','failed','rejected')),
  error       TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (phone_id, video_id)
);
CREATE INDEX ix_review_videos_status   ON review_videos (status);
CREATE INDEX ix_review_videos_video_id ON review_videos (video_id);

CREATE TABLE transcripts (
  video_id           TEXT PRIMARY KEY REFERENCES channel_videos(video_id),
  language           TEXT    NOT NULL,
  is_auto            BOOLEAN NOT NULL,
  raw_path           TEXT    NOT NULL,                 -- data/raw/transcripts/<id>.json
  word_count         INT,
  map_json           JSONB,                            -- phase A output (NULL = not mapped yet)
  map_prompt_version TEXT,                             -- prompt that produced map_json
  embedded_at        TIMESTAMPTZ,                      -- NULL = not embedded yet (job 6)
  fetched_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE phone_digests (
  phone_id       INT PRIMARY KEY REFERENCES phones(id) ON DELETE CASCADE,
  camera REAL, battery REAL, performance REAL, display REAL,
  thermals REAL, software REAL, build REAL,            -- 0-10, NULL = not discussed; each CHECK 0..10
  pros           TEXT[]  NOT NULL DEFAULT '{}',
  cons           TEXT[]  NOT NULL DEFAULT '{}',
  gaming_notes   TEXT,
  summary        TEXT,
  disagreements  JSONB,
  source_videos  TEXT[]  NOT NULL DEFAULT '{}',
  coverage       TEXT,                                 -- 'core:4,backup:1'
  low_confidence BOOLEAN NOT NULL DEFAULT false,
  source_hash    TEXT    NOT NULL,                     -- hash of video_ids used
  prompt_version TEXT    NOT NULL,
  model          TEXT    NOT NULL,
  built_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE review_chunks (
  id        BIGSERIAL PRIMARY KEY,
  phone_id  INT  NOT NULL REFERENCES phones(id) ON DELETE CASCADE,
  video_id  TEXT NOT NULL REFERENCES transcripts(video_id) ON DELETE CASCADE,
  start_sec INT  NOT NULL CHECK (start_sec >= 0),
  aspect    TEXT,
  text      TEXT NOT NULL,
  embedding VECTOR(384) NOT NULL,
  UNIQUE (phone_id, video_id, start_sec)               -- natural key; also serves phone_id lookups
);
CREATE INDEX ix_review_chunks_embedding ON review_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE job_runs (
  id          SERIAL PRIMARY KEY,
  job         TEXT NOT NULL,
  started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  processed   INT  NOT NULL DEFAULT 0,
  failed      INT  NOT NULL DEFAULT 0,
  status      TEXT NOT NULL DEFAULT 'running'
              CHECK (status IN ('running','success','partial','failed')),
  notes       TEXT
);
CREATE INDEX ix_job_runs_job_started_at ON job_runs (job, started_at DESC);

CREATE TABLE query_logs (
  id            BIGSERIAL PRIMARY KEY,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  session_id    TEXT,
  raw_input     JSONB NOT NULL,
  intent        JSONB,
  candidate_ids INT[],
  result        JSONB,
  latency_ms    INT,
  fallback_used BOOLEAN NOT NULL DEFAULT false,
  feedback      SMALLINT CHECK (feedback IN (-1, 1))   -- +1 / -1, NULL = none
);
CREATE INDEX ix_query_logs_session_id ON query_logs (session_id);
```

`downgrade()` drops tables in reverse FK order; it does **not** drop the `vector` extension.

### Functions / CLI / API signatures
```python
# config/settings.py
class Settings(BaseSettings):             # env_file=".env"
    database_url: PostgresDsn            # postgresql+asyncpg://...
    test_database_url: PostgresDsn
    ollama_base_url: HttpUrl
    llm_model_main: str
    llm_model_intent: str
    llm_num_ctx_main: int = 8192
    llm_num_ctx_intent: int = 4096
    embedding_model: str
    embedding_dim: int = 384
    flipkart_affiliate_id: SecretStr | None = None
    flipkart_affiliate_token: SecretStr | None = None
    youtube_sleep_seconds: float = 4
    youtube_max_transcripts_per_run: int = 300
    gsmarena_sleep_seconds: float = 5
    health_check_timeout_s: float = 2
    log_level: str = "INFO"
    result_cache_ttl_hours: int = 24

def get_settings() -> Settings: ...      # lru_cache'd; used via Depends

# app/db/session.py
def create_engine(url: str) -> AsyncEngine: ...
async def get_session() -> AsyncIterator[AsyncSession]: ...   # FastAPI dependency

# app/llm/client.py
class LLMClient:
    def __init__(self, base_url: str, timeout_s: float, http: httpx.AsyncClient | None = None): ...
    async def ping(self) -> None: ...     # GET /api/tags; raises LLMUnavailable on error/timeout
def get_llm_client() -> LLMClient: ...    # FastAPI dependency

# app/errors.py
class LLMUnavailable(Exception): ...

# app/services/health.py
async def check_health(session: AsyncSession, llm: LLMClient, timeout_s: float) -> HealthResponse: ...

# app/api/v1/health.py
@router.get("/health", response_model=HealthResponse)   # mounted at /api/v1
async def health(...) -> JSONResponse: ...              # 503 when status == "down"
```

**Makefile targets:** `up` (`docker compose up -d --wait`), `down`, `db-shell` (psql in container),
`migrate`, `api`, `ui`, `test`, `lint`, `fmt`, `nightly` (as in `_setup/Makefile.txt`).

### Config / env keys
New keys (existing `.env.example` keys unchanged):

| Key | Default | Purpose |
|---|---|---|
| `POSTGRES_USER` | `phonematch` | Used by docker compose to init the container |
| `POSTGRES_PASSWORD` | `phonematch` | Same |
| `POSTGRES_DB` | `phonematch` | Main DB name |
| `POSTGRES_PORT` | `5432` | Host port mapping (change if 5432 is taken) |
| `TEST_DATABASE_URL` | `postgresql+asyncpg://phonematch:phonematch@localhost:5432/phonematch_test` | Integration tests |
| `HEALTH_CHECK_TIMEOUT_S` | `2` | Per-dependency timeout in `/health` |

## 5. Edge cases and failure modes
- Port 5432 already used by a local Postgres → `POSTGRES_PORT` override; `make up` fails visibly, not silently.
- Init script only runs on an empty volume → documented; if the volume predates it, `make db-shell`
  + `CREATE DATABASE phonematch_test` (noted in README-style comment in the script).
- Ollama not installed / not running → `/health` is `degraded`, not an error; tests use a fake client.
- DB down → `/health` 503 with `database.status="down"`, `jobs=[]`; no stack trace in the body.
- Slow dependency → per-check timeout (R8).
- Re-running `make migrate` → no-op (Alembic head already applied).
- Tests must never touch the main DB → test fixtures use `TEST_DATABASE_URL` only.
- LLM fallback rule: not applicable in M0 (no LLM output yet); `ping()` only.

## 6. Acceptance criteria
| # | Criterion | Proven by (test / command) |
|---|---|---|
| A1 | Postgres + pgvector up and healthy | `make up` returns 0; `docker compose ps` shows `healthy` |
| A2 | Both DBs exist | `tests/app/db/test_migration.py::test_test_database_exists` (connects) + `make db-shell -c '\l'` |
| A3 | Migration creates all tables, indexes, extension | `tests/app/db/test_migration.py::test_upgrade_creates_schema` |
| A3b | Constraints reject bad rows | `tests/app/db/test_constraints.py` (one test per CHECK / UNIQUE) |
| A4 | Downgrade/upgrade round-trip | `tests/app/db/test_migration.py::test_downgrade_then_upgrade` |
| A5 | Models match migration | `tests/app/db/test_migration.py::test_models_match_migration` (`alembic check`) |
| A6 | Vector column is 384-dim, HNSW cosine index | `test_upgrade_creates_schema` inspects `pg_indexes` / `format_type` |
| A7 | Settings load from env; missing required key fails | `tests/config/test_settings.py` |
| A8 | Health ok / degraded / down | `tests/app/api/test_health.py` (fake LLM client; DB-down via bad URL) |
| A9 | Health reports latest job run per job | `tests/app/services/test_health.py::test_latest_run_per_job` |
| A10 | Done-when | `make up && make migrate && make api` → `curl localhost:8000/api/v1/health` gives `ok` (or `degraded` if Ollama is off) |
| A11 | Lint + tests | `make lint`, `make test` |

## 7. Dependencies
Needs approval (rule 9). All are already named in the CLAUDE.md stack; this is the M0 subset.

**Runtime:** `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `pydantic-settings`,
`sqlalchemy[asyncio]>=2`, `asyncpg` (async driver), `alembic`, `pgvector` (SQLAlchemy `Vector` type),
`httpx` (LLMClient transport).
**Dev:** `pytest`, `pytest-asyncio`, `ruff`, `mypy`.

Not added yet (later milestones): typer, pyyaml, rapidfuzz, selectolax, yt-dlp,
youtube-transcript-api, sentence-transformers, streamlit.

## 8. Open questions
- None blocking. Later: containerise the API when moving to a server (M8).

## 9. Decisions (2026-09-23)
- **API in Docker:** no. Docker runs infrastructure only (Postgres now); Python runs natively via `uv`.
  Ollama also stays native (Metal GPU).
- **`_setup/`:** Claude's call → install everything into place and delete `_setup/`.
- **Schema:** may deviate from HLD §8 → tightened as in §4; HLD §8 updated in the same change.
- **Git:** not in M0; the user will `git init` later. (The `protect_files` hook's committed-migration
  check is a no-op without git; that's fine.)
