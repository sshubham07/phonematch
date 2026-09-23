"""Health check: database, Ollama and the latest run of each job."""

import asyncio
import time
from collections.abc import Awaitable

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobRun
from app.llm.client import LLMClient
from app.schemas.health import DependencyCheck, HealthResponse, JobRunSummary

MAX_ERROR_CHARS = 200


def _describe(exc: BaseException) -> str:
    """Short, credential-free error text: exception type + first line of the message."""
    first_line = str(exc).splitlines()[0] if str(exc) else ""
    return f"{type(exc).__name__}: {first_line}"[:MAX_ERROR_CHARS]


async def _timed(check: Awaitable[object], timeout_s: float) -> DependencyCheck:
    started = time.perf_counter()
    try:
        await asyncio.wait_for(check, timeout_s)
    except Exception as exc:  # any failure means the dependency is down
        return DependencyCheck(status="down", error=_describe(exc))
    latency_ms = round((time.perf_counter() - started) * 1000)
    return DependencyCheck(status="ok", latency_ms=latency_ms)


async def _latest_job_runs(session: AsyncSession) -> list[JobRunSummary]:
    stmt = select(JobRun).distinct(JobRun.job).order_by(JobRun.job, JobRun.started_at.desc())
    runs = (await session.scalars(stmt)).all()
    return [
        JobRunSummary(
            job=r.job,
            status=r.status,
            started_at=r.started_at,
            finished_at=r.finished_at,
            processed=r.processed,
            failed=r.failed,
        )
        for r in runs
    ]


async def check_health(session: AsyncSession, llm: LLMClient, timeout_s: float) -> HealthResponse:
    database, ollama = await asyncio.gather(
        _timed(session.execute(text("SELECT 1")), timeout_s),
        _timed(llm.ping(), timeout_s),
    )
    if database.status == "down":
        return HealthResponse(status="down", database=database, ollama=ollama, jobs=[])

    jobs = await _latest_job_runs(session)
    status = "ok" if ollama.status == "ok" else "degraded"
    return HealthResponse(status=status, database=database, ollama=ollama, jobs=jobs)
