"""LLMClient: the only place in the codebase that talks to Ollama (CLAUDE.md rule 1).

M0 only needs a liveness check; JSON-schema generation arrives in M4.
"""

from functools import lru_cache

import httpx

from app.errors import LLMUnavailable
from config.settings import get_settings


class LLMClient:
    def __init__(
        self, base_url: str, timeout_s: float, http: httpx.AsyncClient | None = None
    ) -> None:
        self._http = http or httpx.AsyncClient(base_url=base_url, timeout=timeout_s)

    async def ping(self) -> None:
        """Raise LLMUnavailable unless Ollama answers GET /api/tags with a 2xx."""
        try:
            response = await self._http.get("/api/tags")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc

    async def aclose(self) -> None:
        await self._http.aclose()


@lru_cache
def get_llm_client() -> LLMClient:
    settings = get_settings()
    return LLMClient(
        base_url=str(settings.ollama_base_url), timeout_s=settings.health_check_timeout_s
    )
