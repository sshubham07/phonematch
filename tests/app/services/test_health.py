import time
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.db.models import JobRun
from app.services.health import check_health
from tests.fakes import FakeLLMClient

T0 = datetime(2026, 9, 20, 3, 0, tzinfo=UTC)


async def test_ok_when_db_and_ollama_up(db_session: AsyncSession) -> None:
    result = await check_health(db_session, FakeLLMClient("ok"), timeout_s=1)
    assert result.status == "ok"
    assert result.database.status == "ok"
    assert result.ollama.status == "ok"
    assert result.database.latency_ms is not None


async def test_degraded_when_ollama_down(db_session: AsyncSession) -> None:
    result = await check_health(db_session, FakeLLMClient("unavailable"), timeout_s=1)
    assert result.status == "degraded"
    assert result.ollama.status == "down"
    assert result.ollama.error is not None
    assert "LLMUnavailable" in result.ollama.error


async def test_hanging_ollama_is_bounded_by_timeout(db_session: AsyncSession) -> None:
    started = time.perf_counter()
    result = await check_health(db_session, FakeLLMClient("hang"), timeout_s=0.2)
    assert time.perf_counter() - started < 2
    assert result.status == "degraded"
    assert result.ollama.error is not None
    assert "Timeout" in result.ollama.error


async def test_down_when_db_unreachable(test_engine: AsyncEngine) -> None:
    engine = create_async_engine("postgresql+asyncpg://nobody:secretpw@127.0.0.1:1/nope")
    async with AsyncSession(engine) as session:
        result = await check_health(session, FakeLLMClient("ok"), timeout_s=1)
    await engine.dispose()
    assert result.status == "down"
    assert result.database.status == "down"
    assert result.jobs == []
    assert result.database.error is not None
    assert "secretpw" not in result.database.error


async def test_empty_jobs_on_fresh_db(db_session: AsyncSession) -> None:
    result = await check_health(db_session, FakeLLMClient("ok"), timeout_s=1)
    assert result.jobs == []


async def test_latest_run_per_job(db_session: AsyncSession) -> None:
    db_session.add_all(
        [
            JobRun(job="sync_channels", started_at=T0, status="failed", processed=0, failed=1),
            JobRun(
                job="sync_channels",
                started_at=T0 + timedelta(days=1),
                finished_at=T0 + timedelta(days=1, minutes=5),
                status="success",
                processed=120,
            ),
            JobRun(job="match_videos", started_at=T0, status="partial", processed=40, failed=2),
        ]
    )
    await db_session.flush()

    result = await check_health(db_session, FakeLLMClient("ok"), timeout_s=1)

    by_job = {j.job: j for j in result.jobs}
    assert set(by_job) == {"sync_channels", "match_videos"}
    assert by_job["sync_channels"].status == "success"
    assert by_job["sync_channels"].processed == 120
    assert by_job["match_videos"].failed == 2
