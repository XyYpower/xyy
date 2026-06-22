import time
import json
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

import httpx

from app.config import get_settings


@dataclass(frozen=True)
class LLMClient:
    provider: str
    api_key: str
    base_url: str
    model: str
    endpoint_type: str = "openai"  # openai | anthropic

    async def chat_json(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise RuntimeError(f"{self.provider} API key is not configured")

        started = time.perf_counter()
        if self.endpoint_type == "anthropic":
            result = await self._anthropic_call(messages, temperature=0.2, max_tokens=2000)
        else:
            result = await self._openai_call(messages, temperature=0.2, json_mode=True)
        _ = round((time.perf_counter() - started) * 1000)
        return result

    async def chat(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise RuntimeError(f"{self.provider} API key is not configured")

        if self.endpoint_type == "anthropic":
            return await self._anthropic_call(messages, temperature=0.3, max_tokens=2000)
        return await self._openai_call(messages, temperature=0.3)

    async def chat_stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[str, None]:
        if not self.api_key:
            raise RuntimeError(f"{self.provider} API key is not configured")

        if self.endpoint_type == "anthropic":
            async for chunk in self._anthropic_stream(messages):
                yield chunk
        else:
            async for chunk in self._openai_stream(messages):
                yield chunk

    # ── OpenAI 兼容 ──────────────────────

    async def _openai_call(self, messages: list[dict[str, str]], temperature: float = 0.3, json_mode: bool = False) -> str:
        body: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": temperature}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
            )
            response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    async def _openai_stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": messages, "temperature": 0.3, "stream": True},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content

    # ── Anthropic 兼容（智谱 GLM 用这个端点） ──────────────────────

    def _anthropic_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _convert_messages_for_anthropic(self, messages: list[dict[str, str]]) -> tuple[str, list[dict]]:
        """将 OpenAI 格式 messages 转为 Anthropic 格式。"""
        system = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                anthropic_messages.append({"role": msg["role"], "content": msg["content"]})
        # Anthropic 要求第一条必须是 user
        if anthropic_messages and anthropic_messages[0]["role"] != "user":
            anthropic_messages.insert(0, {"role": "user", "content": "..."})
        return system, anthropic_messages

    async def _anthropic_call(self, messages: list[dict[str, str]], temperature: float = 0.3, max_tokens: int = 2000) -> str:
        system, anthropic_msgs = self._convert_messages_for_anthropic(messages)
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": anthropic_msgs,
            "temperature": temperature,
        }
        if system:
            body["system"] = system
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url.rstrip('/')}/v1/messages",
                headers=self._anthropic_headers(),
                json=body,
            )
            response.raise_for_status()
        data = response.json()
        content_blocks = data.get("content", [])
        return "".join(b.get("text", "") for b in content_blocks)

    async def _anthropic_stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[str, None]:
        system, anthropic_msgs = self._convert_messages_for_anthropic(messages)
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 2000,
            "messages": anthropic_msgs,
            "temperature": 0.3,
            "stream": True,
        }
        if system:
            body["system"] = system
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{self.base_url.rstrip('/')}/v1/messages",
                headers=self._anthropic_headers(),
                json=body,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = json.loads(line[6:])
                    event_type = data.get("type", "")
                    if event_type == "content_block_delta":
                        text = data.get("delta", {}).get("text", "")
                        if text:
                            yield text
                    elif event_type == "message_stop":
                        break


def get_llm(
    provider: str | None = None,
    user_provider: str | None = None,
    user_api_key: str | None = None,
    user_model: str | None = None,
) -> LLMClient:
    """获取 LLM 客户端。用户级 key 优先于环境变量配置。"""
    from app.utils.deps import get_user_llm_config
    ctx_provider, ctx_key, ctx_model = get_user_llm_config()

    settings = get_settings()
    selected = (user_provider or ctx_provider or provider or settings.LLM_PROVIDER).lower()
    key = user_api_key or ctx_key or ""
    model = user_model or ctx_model or ""

    if selected == "openai":
        return LLMClient("openai", key or settings.OPENAI_API_KEY, settings.OPENAI_BASE_URL, model or "gpt-4o-mini")
    if selected == "glm":
        # GLM 使用 Anthropic 兼容端点（资源配额独立，付费模型可用）
        return LLMClient("glm", key or settings.GLM_API_KEY, "https://open.bigmodel.cn/api/anthropic", model or "glm-4-flash", endpoint_type="anthropic")
    return LLMClient("deepseek", key or settings.DEEPSEEK_API_KEY, settings.DEEPSEEK_BASE_URL, model or "deepseek-chat")
