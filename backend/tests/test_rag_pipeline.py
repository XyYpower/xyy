import uuid

import pytest

from app.rag import pipeline, prompts


def test_build_rag_messages_includes_context_and_query():
    contexts = [
        {
            "note_id": uuid.uuid4(),
            "note_title": "JWT 认证",
            "chunk_text": "JWT 包含 header、payload、signature。",
            "similarity": 0.9,
        }
    ]

    messages = prompts.build_rag_messages("JWT 怎么校验？", contexts)

    assert messages[0]["role"] == "system"
    assert "KnowBase AI 助手" in messages[0]["content"]
    assert "JWT 认证" in messages[0]["content"]
    assert messages[-1] == {"role": "user", "content": "JWT 怎么校验？"}


@pytest.mark.asyncio
async def test_rag_query_uses_retrieval_and_llm(monkeypatch):
    user_id = uuid.uuid4()
    contexts = [
        {
            "note_id": uuid.uuid4(),
            "note_title": "Redis 缓存",
            "chunk_text": "缓存穿透可以使用布隆过滤器缓解。",
            "similarity": 0.8,
        }
    ]

    async def fake_search(db, received_user_id, query, top_k):
        assert received_user_id == user_id
        assert query == "怎么处理缓存穿透？"
        assert top_k == 5
        return contexts

    class FakeLLM:
        provider = "deepseek"
        api_key = "configured"

        async def chat(self, messages):
            assert "Redis 缓存" in messages[0]["content"]
            return "可以用布隆过滤器。"

    monkeypatch.setattr(pipeline.retrieval, "search_similar", fake_search)
    monkeypatch.setattr(pipeline, "get_llm", lambda: FakeLLM())

    answer, sources = await pipeline.rag_query(None, user_id, "怎么处理缓存穿透？")  # type: ignore[arg-type]

    assert answer == "可以用布隆过滤器。"
    assert sources == contexts


@pytest.mark.asyncio
async def test_rag_query_falls_back_without_api_key(monkeypatch):
    class NoKeyLLM:
        provider = "deepseek"
        api_key = ""

    async def fake_search(*args, **kwargs):
        return []

    monkeypatch.setattr(pipeline.retrieval, "search_similar", fake_search)
    monkeypatch.setattr(pipeline, "get_llm", lambda: NoKeyLLM())

    answer, sources = await pipeline.rag_query(None, uuid.uuid4(), "没有资料的问题")  # type: ignore[arg-type]

    assert "没有找到" in answer
    assert sources == []
