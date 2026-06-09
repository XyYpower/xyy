"""KnowBase MCP Server：让外部 IDE/Agent 调用 KnowBase 的资源和工具。

通过 SSE transport 挂载到 FastAPI，客户端可通过 HTTP 连接。
"""

import json
import logging
import uuid

from mcp.server.fastmcp import FastMCP

from app.database import async_session
from app.models.user import User
from app.models.note import Note
from app.services import note_service, review_service, interview_service, path_service
from app.rag import retrieval, hybrid_retrieval

logger = logging.getLogger(__name__)

# 创建 MCP Server 实例
mcp = FastMCP(
    name="KnowBase",
    instructions=(
        "KnowBase 是 AI 驱动的个人知识库。你可以搜索知识点、创建笔记草稿、"
        "获取复习卡片和生成面试题。所有操作基于当前用户的知识库数据。"
    ),
)


# ── Tools ──────────────────────


@mcp.tool()
async def search_notes(query: str, limit: int = 5) -> str:
    """搜索知识点。根据关键词在知识库中搜索相关笔记。

    Args:
        query: 搜索关键词
        limit: 返回结果数量（默认 5）
    """
    async with async_session() as db:
        user = await _get_default_user(db)
        if not user:
            return json.dumps({"error": "没有可用用户"}, ensure_ascii=False)

        # 使用混合检索
        try:
            results = await hybrid_retrieval.hybrid_search(db, user.id, query, top_k=limit)
        except Exception:
            # 降级到普通搜索
            notes, _ = await note_service.get_notes(db, user.id, 1, limit, query)
            results = [{"note_id": str(n.id), "note_title": n.title, "chunk_text": n.content[:300], "combined_score": 0} for n in notes]

        return json.dumps({
            "results": [
                {
                    "note_id": str(r.get("note_id", "")),
                    "title": r.get("note_title", ""),
                    "excerpt": r.get("chunk_text", "")[:300],
                    "score": round(r.get("combined_score", 0), 3),
                }
                for r in results
            ],
            "total": len(results),
        }, ensure_ascii=False)


@mcp.tool()
async def get_note(note_id: str) -> str:
    """获取知识点详情。返回标题、内容、分类和标签。

    Args:
        note_id: 知识点 UUID
    """
    async with async_session() as db:
        user = await _get_default_user(db)
        if not user:
            return json.dumps({"error": "没有可用用户"}, ensure_ascii=False)

        note = await note_service.get_note(db, uuid.UUID(note_id), user.id)
        if not note:
            return json.dumps({"error": "知识点不存在"}, ensure_ascii=False)

        return json.dumps({
            "id": str(note.id),
            "title": note.title,
            "content": note.content,
            "summary": note.summary,
            "category": note.category.name if note.category else None,
            "tags": [t.name for t in note.tags],
            "mastery_level": note.mastery_level,
            "source_type": note.source_type,
        }, ensure_ascii=False)


@mcp.tool()
async def create_note_draft(title: str, content: str = "", tag_names: list[str] | None = None) -> str:
    """创建知识点草稿。返回创建的知识点 ID 和标题。

    Args:
        title: 知识点标题
        content: 知识点内容（Markdown 格式）
        tag_names: 标签名称列表（可选）
    """
    async with async_session() as db:
        user = await _get_default_user(db)
        if not user:
            return json.dumps({"error": "没有可用用户"}, ensure_ascii=False)

        from app.schemas.note import NoteCreate
        data = NoteCreate(title=title, content=content, tag_names=tag_names or [])
        note = await note_service.create_note(db, data, user.id)
        await db.commit()

        return json.dumps({
            "id": str(note.id),
            "title": note.title,
            "message": f"知识点 '{note.title}' 已创建",
        }, ensure_ascii=False)


@mcp.tool()
async def get_review_cards(limit: int = 10) -> str:
    """获取今日待复习卡片。返回需要复习的问题列表。

    Args:
        limit: 返回卡片数量（默认 10）
    """
    async with async_session() as db:
        user = await _get_default_user(db)
        if not user:
            return json.dumps({"error": "没有可用用户"}, ensure_ascii=False)

        cards = await review_service.get_today_review_cards(db, user.id)
        return json.dumps({
            "cards": [
                {
                    "id": str(c.id),
                    "question": c.question,
                    "card_type": c.card_type,
                }
                for c in cards[:limit]
            ],
            "total": len(cards),
        }, ensure_ascii=False)


@mcp.tool()
async def generate_interview_questions(topic: str, num_questions: int = 3) -> str:
    """根据主题生成面试题。返回题目和参考答案。

    Args:
        topic: 面试主题（如 "JWT 认证"、"Redis 缓存"）
        num_questions: 题目数量（默认 3）
    """
    from app.rag.interviewer import generate_interview_questions as gen_questions

    questions = await gen_questions([topic], num_questions)
    return json.dumps({
        "questions": [
            {
                "question": q.get("question", ""),
                "reference_answer": q.get("reference_answer", ""),
            }
            for q in questions
        ],
        "topic": topic,
    }, ensure_ascii=False)


# ── Resources ──────────────────────


@mcp.resource("knowbase://notes/{note_id}")
async def read_note_resource(note_id: str) -> str:
    """读取知识点资源。"""
    async with async_session() as db:
        user = await _get_default_user(db)
        if not user:
            return "没有可用用户"

        note = await note_service.get_note(db, uuid.UUID(note_id), user.id)
        if not note:
            return "知识点不存在"

        return f"# {note.title}\n\n{note.content}"


@mcp.resource("knowbase://reviews/today")
async def read_today_reviews() -> str:
    """读取今日复习资源。"""
    async with async_session() as db:
        user = await _get_default_user(db)
        if not user:
            return "没有可用用户"

        cards = await review_service.get_today_review_cards(db, user.id)
        if not cards:
            return "今日无需复习的卡片"

        lines = [f"今日待复习：{len(cards)} 张卡片\n"]
        for i, card in enumerate(cards[:10], 1):
            lines.append(f"{i}. [{card.card_type}] {card.question}")
        return "\n".join(lines)


@mcp.resource("knowbase://paths")
async def read_learning_paths() -> str:
    """读取学习路径列表。"""
    async with async_session() as db:
        user = await _get_default_user(db)
        if not user:
            return "没有可用用户"

        paths = await path_service.get_paths(db, user.id)
        if not paths:
            return "暂无学习路径"

        lines = []
        for path in paths:
            lines.append(f"## {path.name}\n{path.description}")
            modules = path.modules_json or []
            for mod in modules:
                lines.append(f"  - {mod.get('name', '')}: {', '.join(mod.get('topics', []))}")
            lines.append("")
        return "\n".join(lines)


# ── 辅助函数 ──────────────────────


async def _get_default_user(db) -> User | None:
    """获取默认用户（MCP 本地使用场景，取第一个用户）。"""
    from sqlalchemy import select
    result = await db.execute(select(User).order_by(User.created_at).limit(1))
    return result.scalar_one_or_none()


def get_mcp_app():
    """获取 MCP SSE ASGI 应用，用于挂载到 FastAPI。"""
    return mcp.sse_app(mount_path="/mcp")
