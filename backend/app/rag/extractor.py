import json
import logging

from app.rag.llm import get_llm

logger = logging.getLogger(__name__)


async def extract_knowledge_points(text: str) -> list[dict[str, str]]:
    """从技术文本中提取候选知识点。"""
    llm = get_llm()
    if not llm.api_key:
        return _fallback_extract(text)

    prompt = (
        "你是编程知识点提取器。从用户给出的技术文章、面经或代码中，"
        "提取出独立可学习的知识点。每个知识点包含 title 和 content。"
        "只返回 JSON：{\"items\":[{\"title\":\"...\",\"content\":\"...\"}]}"
    )
    try:
        raw = await llm.chat_json(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text[:4000]},
            ]
        )
        payload = json.loads(raw)
        items = _normalize_items(payload.get("items", []))
        if items:
            return items
        logger.warning("LLM extraction returned no usable items for provider=%s; using fallback", llm.provider)
    except Exception:
        logger.warning("LLM extraction failed for provider=%s; using fallback", llm.provider, exc_info=True)

    return _fallback_extract(text)


def _normalize_items(items: list[dict]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in items:
        title = str(item.get("title", "")).strip()
        content = str(item.get("content", "")).strip()
        if title and content:
            result.append({"title": title[:200], "content": content})
    return result[:10]


def _fallback_extract(text: str) -> list[dict[str, str]]:
    """无 API key 或 LLM 失败时按段落拆分。"""
    paragraphs = [part.strip() for part in text.split("\n\n") if len(part.strip()) > 20]
    if not paragraphs and text.strip():
        paragraphs = [text.strip()]
    return [
        {
            "title": paragraph[:50] + ("..." if len(paragraph) > 50 else ""),
            "content": paragraph,
        }
        for paragraph in paragraphs[:10]
    ]
