import hashlib
import math
from dataclasses import dataclass

import httpx

from app.config import get_settings

EMBEDDING_DIMENSIONS = 1536


@dataclass(frozen=True)
class EmbeddingClient:
    provider: str
    api_key: str
    base_url: str
    model: str

    async def embed(self, text: str) -> list[float]:
        return (await self.embed_many([text]))[0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.api_key:
            return [fallback_embedding(text) for text in texts]

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url.rstrip('/')}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": [text[:8000] for text in texts]},
            )
            response.raise_for_status()
        data = sorted(response.json()["data"], key=lambda item: item.get("index", 0))
        return [item["embedding"][:EMBEDDING_DIMENSIONS] for item in data]


async def embed_text(text: str) -> list[float]:
    return await get_embedding_client().embed(text)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    return await get_embedding_client().embed_many(texts)


def get_embedding_client(provider: str | None = None) -> EmbeddingClient:
    settings = get_settings()
    selected = (provider or settings.LLM_PROVIDER).lower()
    if selected == "openai":
        return EmbeddingClient("openai", settings.OPENAI_API_KEY, settings.OPENAI_BASE_URL, "text-embedding-3-small")
    if selected == "glm":
        return EmbeddingClient("glm", settings.GLM_API_KEY, settings.GLM_BASE_URL, "embedding-3")
    return EmbeddingClient("deepseek", settings.DEEPSEEK_API_KEY, settings.DEEPSEEK_BASE_URL, "text-embedding-3-small")


def fallback_embedding(text: str) -> list[float]:
    """无 API key 时生成确定性的伪向量，便于本地开发和测试。"""
    values: list[float] = []
    counter = 0
    while len(values) < EMBEDDING_DIMENSIONS:
        digest = hashlib.sha256(f"{text}:{counter}".encode("utf-8")).digest()
        for index in range(0, len(digest), 4):
            integer = int.from_bytes(digest[index:index + 4], byteorder="big", signed=False)
            values.append((integer / 0xFFFFFFFF) * 2 - 1)
            if len(values) >= EMBEDDING_DIMENSIONS:
                break
        counter += 1

    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


def vector_to_sql(vector: list[float]) -> str:
    normalized = vector[:EMBEDDING_DIMENSIONS]
    if len(normalized) < EMBEDDING_DIMENSIONS:
        normalized = normalized + [0.0] * (EMBEDDING_DIMENSIONS - len(normalized))
    return "[" + ",".join(f"{value:.8f}" for value in normalized) + "]"
