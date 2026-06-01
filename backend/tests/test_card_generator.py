import pytest

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

