import json

from app.rag.llm import get_llm

CARD_TYPES = ("concept", "code", "scenario")


async def generate_cards(note_title: str, note_content: str) -> list[dict[str, str]]:
    """生成三类复习卡片；没有 API key 时返回本地兜底卡片。"""

    llm = get_llm()
    if not llm.api_key:
        return _fallback_cards(note_title, note_content)

    prompt = (
        "你是编程知识复习卡片生成器。请基于用户知识点生成恰好 3 张卡片，"
        "card_type 分别为 concept、code、scenario。只返回 JSON："
        "{\"cards\":[{\"card_type\":\"concept\",\"question\":\"...\",\"answer\":\"...\"}]}"
    )
    content = f"标题：{note_title}\n内容：{note_content}"
    try:
        raw = await llm.chat_json(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": content},
            ]
        )
        payload = json.loads(raw)
        cards = payload.get("cards", [])
        normalized = _normalize_cards(cards)
        if len(normalized) == 3:
            return normalized
    except Exception:
        return _fallback_cards(note_title, note_content)

    return _fallback_cards(note_title, note_content)


def _normalize_cards(cards: list[dict]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen = set()
    for card in cards:
        card_type = str(card.get("card_type", "")).strip()
        question = str(card.get("question", "")).strip()
        answer = str(card.get("answer", "")).strip()
        if card_type in CARD_TYPES and card_type not in seen and question and answer:
            result.append({"card_type": card_type, "question": question, "answer": answer})
            seen.add(card_type)
    return result


def _fallback_cards(note_title: str, note_content: str) -> list[dict[str, str]]:
    answer = note_content.strip() or "这条知识点还没有详细内容，请补充后再复习。"
    return [
        {
            "card_type": "concept",
            "question": f"{note_title} 的核心概念是什么？",
            "answer": answer,
        },
        {
            "card_type": "code",
            "question": f"请写出或解释一个与 {note_title} 相关的代码/配置片段。",
            "answer": answer,
        },
        {
            "card_type": "scenario",
            "question": f"在实际项目或面试中，什么时候会用到 {note_title}？",
            "answer": answer,
        },
    ]

