import pytest

from app.rag import extractor
from app.rag.extractor import extract_knowledge_points


pytestmark = pytest.mark.asyncio


async def test_extract_knowledge_points_falls_back_to_paragraphs_without_api_key(monkeypatch):
    class NoKeyLLM:
        api_key = ""
        provider = "deepseek"

    monkeypatch.setattr(extractor, "get_llm", lambda: NoKeyLLM())
    text = (
        "短句会被忽略。\n\n"
        "JWT 由 header、payload、signature 组成，常用于无状态登录认证。\n\n"
        "刷新 Token 用于在 access token 过期后换取新的访问令牌。"
    )

    items = await extract_knowledge_points(text)

    assert [item["title"] for item in items] == [
        "JWT 由 header、payload、signature 组成，常用于无状态登录认证。",
        "刷新 Token 用于在 access token 过期后换取新的访问令牌。",
    ]
    assert all(item["content"] for item in items)


async def test_extract_knowledge_points_parses_llm_json(monkeypatch):
    class WorkingLLM:
        api_key = "configured"
        provider = "deepseek"

        async def chat_json(self, messages):
            return '{"items":[{"title":"缓存穿透","content":"查询不存在的数据导致请求打到数据库。"}]}'

    monkeypatch.setattr(extractor, "get_llm", lambda: WorkingLLM())

    items = await extract_knowledge_points("缓存穿透可以用布隆过滤器缓解。")

    assert items == [{"title": "缓存穿透", "content": "查询不存在的数据导致请求打到数据库。"}]


async def test_extract_knowledge_points_logs_warning_and_falls_back_when_llm_fails(monkeypatch, caplog):
    class BrokenLLM:
        api_key = "configured"
        provider = "deepseek"

        async def chat_json(self, messages):
            raise RuntimeError("timeout")

    monkeypatch.setattr(extractor, "get_llm", lambda: BrokenLLM())

    items = await extract_knowledge_points("SQL 索引可以提升查询性能，但会增加写入成本。")

    assert items
    assert any("deepseek" in record.message for record in caplog.records)
