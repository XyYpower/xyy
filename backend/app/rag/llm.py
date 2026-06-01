import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_settings


@dataclass(frozen=True)
class LLMClient:
    provider: str
    api_key: str
    base_url: str
    model: str

    async def chat_json(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise RuntimeError(f"{self.provider} API key is not configured")

        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
        _ = round((time.perf_counter() - started) * 1000)
        data: dict[str, Any] = response.json()
        return data["choices"][0]["message"]["content"]


def get_llm(provider: str | None = None) -> LLMClient:
    settings = get_settings()
    selected = (provider or settings.LLM_PROVIDER).lower()
    if selected == "openai":
        return LLMClient("openai", settings.OPENAI_API_KEY, settings.OPENAI_BASE_URL, "gpt-4o-mini")
    if selected == "glm":
        return LLMClient("glm", settings.GLM_API_KEY, settings.GLM_BASE_URL, "glm-4-flash")
    return LLMClient("deepseek", settings.DEEPSEEK_API_KEY, settings.DEEPSEEK_BASE_URL, "deepseek-chat")

