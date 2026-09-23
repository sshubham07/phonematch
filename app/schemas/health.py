"""Response models for GET /api/v1/health."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

CheckStatus = Literal["ok", "down"]


class DependencyCheck(BaseModel):
    status: CheckStatus
    latency_ms: int | None = None
    error: str | None = None


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
    jobs: list[JobRunSummary]
