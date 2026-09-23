"""FastAPI entrypoint: `uvicorn app.main:app`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import router as v1_router
from app.db.session import get_engine
from app.llm.client import get_llm_client


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await get_llm_client().aclose()
    await get_engine().dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="PhoneMatch", version="0.1.0", lifespan=lifespan)
    app.include_router(v1_router)
    return app


app = create_app()
