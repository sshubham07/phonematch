from collections.abc import AsyncIterator, Callable

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db.session import get_session
from app.llm.client import get_llm_client
from app.main import create_app
from tests.fakes import FakeLLMClient, FakeMode

ClientFactory = Callable[[AsyncSession, FakeMode], httpx.AsyncClient]


@pytest.fixture
def make_client() -> ClientFactory:
    def factory(session: AsyncSession, mode: FakeMode) -> httpx.AsyncClient:
        app = create_app()

        async def _session() -> AsyncIterator[AsyncSession]:
            yield session

        app.dependency_overrides[get_session] = _session
        app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient(mode)
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    return factory


async def test_health_ok(db_session: AsyncSession, make_client: ClientFactory) -> None:
    async with make_client(db_session, "ok") as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"]["status"] == "ok"
    assert body["ollama"]["status"] == "ok"
    assert body["jobs"] == []


async def test_health_degraded_when_ollama_down(
    db_session: AsyncSession, make_client: ClientFactory
) -> None:
    async with make_client(db_session, "unavailable") as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"


async def test_health_503_when_db_down(make_client: ClientFactory) -> None:
    engine = create_async_engine("postgresql+asyncpg://nobody:pw@127.0.0.1:1/nope")
    async with AsyncSession(engine) as session, make_client(session, "ok") as client:
        resp = await client.get("/api/v1/health")
    await engine.dispose()
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "down"
    assert body["jobs"] == []
