"""Shared fixtures. Integration tests run against TEST_DATABASE_URL only, never the main DB."""

import asyncio
from argparse import Namespace
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from config.settings import get_settings

ROOT = Path(__file__).resolve().parent.parent


def get_test_db_url() -> str:
    return str(get_settings().test_database_url)


def alembic_config() -> Config:
    cfg = Config(str(ROOT / "alembic.ini"), cmd_opts=Namespace(x=[f"db_url={get_test_db_url()}"]))
    cfg.attributes["configure_logger"] = False
    return cfg


async def run_alembic(fn_name: str, *args: str) -> None:
    """Run an alembic command in a worker thread (env.py calls asyncio.run itself)."""
    await asyncio.to_thread(getattr(command, fn_name), alembic_config(), *args)


@pytest.fixture(scope="session")
async def test_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(get_test_db_url(), poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except OSError as exc:
        pytest.fail(f"Test database unreachable ({exc}). Start it with `make up`.", pytrace=False)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def migrated_db(test_engine: AsyncEngine) -> AsyncEngine:
    await run_alembic("upgrade", "head")
    return test_engine


@pytest.fixture
async def db_session(migrated_db: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Session inside an outer transaction that is rolled back after the test."""
    async with migrated_db.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
