"""DiagnosisAgent：根据知识点、复习和面试历史诊断用户薄弱点。"""

import json
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.rag.llm import get_llm
from app.services import interview_service, note_service, review_service

logger = logging.getLogger(__name__)

DIAGNOSIS_PROMPT = (
    "你是学习诊断专家。根据用户的知识库数据诊断学习薄弱点。\n"
    "输入包含：知识点列表（标题+掌握度）、复习统计、面试薄弱点。\n"
    "输出 JSON：{\"weak_areas\":[{\"area\":\"领域\",\"reason\":\"原因\",\"priority\":1,\"suggested_topics\":[\"topic1\"]}],"
    "\"summary\":\"总结\",\"next_steps\":[\"步骤1\"]}"
)


async def diagnose(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """诊断用户学习状态，返回薄弱领域和建议。"""

    # 收集数据
    notes_data = await _collect_notes_data(db, user_id)
    review_data = await _collect_review_data(db, user_id)
    weak_points = await interview_service.get_weak_points(db, user_id)

    context = {
        "notes_count": len(notes_data),
        "notes": notes_data[:30],
        "review_stats": review_data,
        "interview_weak_points": weak_points[:10],
    }

    llm = get_llm()
    if not llm.api_key:
        return _fallback_diagnosis(context)

    try:
        raw = await llm.chat_json([
            {"role": "system", "content": DIAGNOSIS_PROMPT},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False, default=str)},
        ])
        result = json.loads(raw)
        return _normalize_diagnosis(result, context)
    except Exception:
        logger.warning("LLM diagnosis failed; using fallback", exc_info=True)
        return _fallback_diagnosis(context)


async def _collect_notes_data(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    notes, _ = await note_service.get_notes(db, user_id, page=1, page_size=50)
    return [
        {"title": n.title, "mastery_level": n.mastery_level, "source_type": n.source_type}
        for n in notes
    ]


async def _collect_review_data(db: AsyncSession, user_id: uuid.UUID) -> dict:
    try:
        return await review_service.get_review_stats(db, user_id)
    except Exception:
        return {"total_cards": 0, "due_today": 0}


def _normalize_diagnosis(result: dict, context: dict) -> dict:
    weak_areas = result.get("weak_areas", [])
    if not isinstance(weak_areas, list):
        weak_areas = []

    normalized = []
    for i, area in enumerate(weak_areas[:8]):
        if not isinstance(area, dict):
            continue
        normalized.append({
            "area": str(area.get("area", ""))[:100],
            "reason": str(area.get("reason", ""))[:300],
            "priority": int(area.get("priority", i + 1)),
            "suggested_topics": [str(t)[:100] for t in area.get("suggested_topics", [])[:5]],
        })

    return {
        "weak_areas": normalized,
        "summary": str(result.get("summary", ""))[:500],
        "next_steps": [str(s)[:200] for s in result.get("next_steps", [])[:5]],
        "raw_context": context,
    }


def _fallback_diagnosis(context: dict) -> dict:
    notes = context.get("notes", [])
    weak_points = context.get("interview_weak_points", [])
    review = context.get("review_stats", {})

    weak_areas = []
    for wp in weak_points[:3]:
        weak_areas.append({
            "area": wp["title"],
            "reason": f"面试平均分 {wp['avg_score']}/10，测试 {wp['times_tested']} 次",
            "priority": 1,
            "suggested_topics": [wp["title"]],
        })

    not_started = [n for n in notes if n.get("mastery_level") == 0]
    if not_started:
        weak_areas.append({
            "area": "未学习的知识点",
            "reason": f"有 {len(not_started)} 个知识点尚未开始学习",
            "priority": 2,
            "suggested_topics": [n["title"] for n in not_started[:5]],
        })

    if review.get("due_today", 0) > 0:
        weak_areas.append({
            "area": "待复习内容",
            "reason": f"今日有 {review['due_today']} 张卡片待复习",
            "priority": 1,
            "suggested_topics": ["完成今日复习任务"],
        })

    return {
        "weak_areas": weak_areas,
        "summary": f"共 {len(notes)} 个知识点，{len(weak_points)} 个薄弱领域，{review.get('due_today', 0)} 张卡片待复习。",
        "next_steps": ["优先复习薄弱知识点", "完成待复习卡片", "补充未学习的知识点"],
        "raw_context": context,
    }
