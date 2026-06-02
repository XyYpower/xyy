import pytest

from app.rag import card_generator
from app.rag.card_generator import generate_cards


@pytest.mark.asyncio
async def test_generate_cards_returns_three_review_card_types_without_api_key():
    cards = await generate_cards(
        "JWT 认证",
        "JWT 由 header、payload、signature 三部分组成，常用于无状态登录认证。",
    )

    assert [card["card_type"] for card in cards] == ["concept", "code", "scenario"]
    assert all(card["question"] for card in cards)
    assert all(card["answer"] for card in cards)


@pytest.mark.asyncio
async def test_generate_cards_logs_warning_when_configured_llm_fails(monkeypatch, caplog):
    class BrokenLLM:
        provider = "deepseek"
        api_key = "secret-key-should-not-be-logged"

        async def chat_json(self, messages):
            raise RuntimeError("remote API unavailable")

    monkeypatch.setattr(card_generator, "get_llm", lambda: BrokenLLM())

    cards = await generate_cards("FastAPI 依赖注入", "Depends 用于声明依赖。")

    assert [card["card_type"] for card in cards] == ["concept", "code", "scenario"]
    assert any("deepseek" in record.message for record in caplog.records)
    assert all("secret-key-should-not-be-logged" not in record.message for record in caplog.records)
