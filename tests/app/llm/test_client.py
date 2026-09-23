import httpx
import pytest

from app.errors import LLMUnavailable
from app.llm.client import LLMClient


def _client(handler: httpx.MockTransport) -> LLMClient:
    http = httpx.AsyncClient(base_url="http://ollama.test", transport=handler)
    return LLMClient(base_url="http://ollama.test", timeout_s=1, http=http)


async def test_ping_ok_on_200() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json={"models": []})

    await _client(httpx.MockTransport(handler)).ping()
    assert seen == ["/api/tags"]


async def test_ping_raises_on_server_error() -> None:
    client = _client(httpx.MockTransport(lambda _: httpx.Response(500)))
    with pytest.raises(LLMUnavailable):
        await client.ping()


async def test_ping_raises_on_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(LLMUnavailable):
        await _client(httpx.MockTransport(handler)).ping()


@pytest.mark.llm
async def test_ping_real_local_ollama() -> None:
    from config.settings import get_settings

    settings = get_settings()
    client = LLMClient(base_url=str(settings.ollama_base_url), timeout_s=2)
    try:
        await client.ping()
    finally:
        await client.aclose()
