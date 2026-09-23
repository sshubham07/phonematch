"""Test doubles. Unit tests never talk to real Ollama."""

import asyncio
from typing import Literal

from app.errors import LLMUnavailable
from app.llm.client import LLMClient

FakeMode = Literal["ok", "unavailable", "hang"]


class FakeLLMClient(LLMClient):
    def __init__(self, mode: FakeMode = "ok") -> None:
        super().__init__(base_url="http://fake-ollama.invalid", timeout_s=1)
        self.mode = mode

    async def ping(self) -> None:
        if self.mode == "unavailable":
            raise LLMUnavailable("fake: connection refused")
        if self.mode == "hang":
            await asyncio.sleep(60)
