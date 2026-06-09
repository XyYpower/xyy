"""将现有服务函数注册为 Agent 可调用工具。"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.registry import ToolDef, registry, ToolResult

logger = logging.getLogger(__name__)


# ── 工具函数（薄包装，不修改原始服务） ──────────────────────


async def _notes_search(db: AsyncSession, user_id: uuid.UUID, keyword: str = "", page: int = 1, page_size: int = 5) -> dict:
    from app.services import note_service
    notes, total = await note_service.get_notes(db, user_id, page, page_size, keyword or None)
    return {"total": total, "items": [{"id": str(n.id), "title": n.title} for n in notes]}


async def _notes_get(db: AsyncSession, user_id: uuid.UUID, note_id: str) -> dict:
    from app.services import note_service
    note = await note_service.get_note(db, uuid.UUID(note_id), user_id)
    if not note:
        raise ValueError("Note not found")
    return {"id": str(note.id), "title": note.title, "content": note.content[:500]}


async def _retrieval_search(db: AsyncSession, user_id: uuid.UUID, query: str, top_k: int = 5) -> dict:
    from app.rag import retrieval
    contexts = await retrieval.search_similar(db, user_id, query, top_k=top_k)
    return {"contexts": contexts, "count": len(contexts)}


async def _review_today(db: AsyncSession, user_id: uuid.UUID) -> dict:
    from app.services import review_service
    cards = await review_service.get_today_review_cards(db, user_id)
    return {"count": len(cards), "cards": [{"id": str(c.id), "question": c.question[:80]} for c in cards[:10]]}


async def _review_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    from app.services import review_service
    stats = await review_service.get_review_stats(db, user_id)
    return stats


async def _interview_start(db: AsyncSession, user_id: uuid.UUID, scope: str = "all", num_questions: int = 5) -> dict:
    from app.services import interview_service
    session = await interview_service.start_interview(db, user_id, scope, num_questions)
    return {"session_id": str(session.id), "title": session.title, "question_count": len(session.questions)}


async def _interview_weak_points(db: AsyncSession, user_id: uuid.UUID) -> dict:
    from app.services import interview_service
    weak = await interview_service.get_weak_points(db, user_id)
    return {"weak_points": weak}


async def _import_create_text(db: AsyncSession, user_id: uuid.UUID, text: str) -> dict:
    from app.services import import_service
    job = await import_service.create_import_job(db, user_id, "text", text)
    return {"job_id": str(job.id), "status": job.status}


# ── 注册工具 ──────────────────────────────


def register_all_tools() -> None:
    """注册所有工具到全局 registry。"""
    tools = [
        ToolDef(
            name="notes.search",
            description="搜索知识点列表",
            requires_approval=False,
            fn=_notes_search,
        ),
        ToolDef(
            name="notes.get",
            description="获取单个知识点详情",
            requires_approval=False,
            fn=_notes_get,
        ),
        ToolDef(
            name="retrieval.search",
            description="RAG 语义检索相关知识点片段",
            requires_approval=False,
            fn=_retrieval_search,
        ),
        ToolDef(
            name="review.today",
            description="获取今日待复习卡片",
            requires_approval=False,
            fn=_review_today,
        ),
        ToolDef(
            name="review.stats",
            description="获取复习统计数据",
            requires_approval=False,
            fn=_review_stats,
        ),
        ToolDef(
            name="interview.start",
            description="开始模拟面试",
            requires_approval=False,
            fn=_interview_start,
        ),
        ToolDef(
            name="interview.weak_points",
            description="获取薄弱知识点分析",
            requires_approval=False,
            fn=_interview_weak_points,
        ),
        ToolDef(
            name="imports.create_text_job",
            description="导入文本并提取知识点草稿",
            requires_approval=False,
            fn=_import_create_text,
        ),
    ]
    for tool in tools:
        registry.register(tool)

    logger.info("Registered %d tools", len(tools))
