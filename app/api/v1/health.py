from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.llm.client import LLMClient, get_llm_client
from app.schemas.health import HealthResponse
from app.services.health import check_health
from config.settings import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(
    session: Annotated[AsyncSession, Depends(get_session)],
    llm: Annotated[LLMClient, Depends(get_llm_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    result = await check_health(session, llm, settings.health_check_timeout_s)
    status_code = 503 if result.status == "down" else 200
    return JSONResponse(content=result.model_dump(mode="json"), status_code=status_code)
