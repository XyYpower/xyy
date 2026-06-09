"""KnowBase MCP Server：让外部 IDE/Agent 调用 KnowBase 的资源和工具。

通过 SSE transport 挂载到 FastAPI，客户端可通过 HTTP 连接。
安全要求：必须配置 KNOWBASE_MCP_USER_ID 才能使用。
"""

import json
import logging
import uuid

from mcp.server.fastmcp import FastMCP

from app.database import async_session
from app.config import get_settings
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
        user = await _get_configured_user(db)
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
        user = await _get_configured_user(db)
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
        user = await _get_configured_user(db)
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
        user = await _get_configured_user(db)
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
        user = await _get_configured_user(db)
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
        user = await _get_configured_user(db)
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
        user = await _get_configured_user(db)
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


# ── Prompts ──────────────────────


@mcp.prompt()
async def prepare_agent_engineer_interview(focus_area: str = "") -> str:
    """准备 AI Agent 应用开发岗位面试。根据知识库内容生成面试准备材料。

    Args:
        focus_area: 重点准备方向（如 "RAG"、"工具调用"、"多Agent编排"，可选）
    """
    async with async_session() as db:
        user = await _get_configured_user(db)
        if not user:
            return "没有可用用户，请先注册并添加知识点。"

        # 收集用户知识库
        notes, total = await note_service.get_notes(db, user.id, 1, 20)
        weak_points = await interview_service.get_weak_points(db, user.id)

        note_titles = [n.title for n in notes]
        weak_titles = [w["title"] for w in weak_points[:5]]

        prompt_parts = [
            "你是一位资深 AI Agent 应用开发技术面试官。请根据候选人的知识库准备面试。",
            f"\n候选人知识库（{total} 个知识点）：",
            *[f"- {t}" for t in note_titles[:15]],
        ]

        if weak_titles:
            prompt_parts.append("\n候选人薄弱领域：")
            prompt_parts.extend(f"- {t}" for t in weak_titles)

        if focus_area:
            prompt_parts.append(f"\n重点准备方向：{focus_area}")

        prompt_parts.extend([
            "\n请：",
            "1. 评估候选人的知识覆盖度",
            "2. 列出 5 道针对性面试题（概念+实践+场景）",
            "3. 每道题给出参考答案和评分标准",
            "4. 给出面试准备建议",
        ])

        return "\n".join(prompt_parts)


@mcp.prompt()
async def explain_knowledge_gap(topic: str) -> str:
    """解释某个知识点的学习差距和改进方向。

    Args:
        topic: 要分析的知识点主题
    """
    async with async_session() as db:
        user = await _get_configured_user(db)
        if not user:
            return "没有可用用户。"

        # 搜索相关笔记
        notes, _ = await note_service.get_notes(db, user.id, 1, 5, topic)

        context = f"用户正在学习：{topic}\n"
        if notes:
            context += "已有相关知识点：\n"
            for n in notes:
                mastery = {0: "未学", 1: "学习中", 2: "已掌握"}[n.mastery_level]
                context += f"- {n.title}（{mastery}）\n"
        else:
            context += "知识库中没有相关知识点。\n"

        return (
            f"{context}\n"
            f"请分析用户在「{topic}」方面的知识差距：\n"
            "1. 该主题的核心概念和关键知识点\n"
            "2. 用户当前掌握情况评估\n"
            "3. 需要补充的学习内容\n"
            "4. 推荐的学习路径和资源\n"
            "5. 实践项目建议"
        )


@mcp.prompt()
async def generate_project_case_study(project_name: str = "KnowBase") -> str:
    """生成项目案例研究，适合放在简历或面试中展示。

    Args:
        project_name: 项目名称（默认 KnowBase）
    """
    async with async_session() as db:
        user = await _get_configured_user(db)
        stats = {}
        if user:
            from sqlalchemy import func, select
            notes_count = (await db.execute(
                select(func.count(Note.id)).where(Note.user_id == user.id)
            )).scalar() or 0
            stats["知识点数"] = notes_count

    return (
        f"请为项目「{project_name}」生成一份技术案例研究，包含：\n\n"
        "1. **项目概述**：一句话定位 + 核心价值\n"
        "2. **技术架构**：系统架构图描述、技术栈选型理由\n"
        "3. **核心挑战**：遇到的 3 个技术难题及解决方案\n"
        "4. **技术亮点**：可量化的性能指标、创新点\n"
        "5. **工程实践**：测试策略、CI/CD、可观测性\n"
        "6. **总结与反思**：学到了什么、可以改进什么\n\n"
        f"项目数据：{stats}\n"
        "输出格式：Markdown，适合放进 GitHub README 或技术博客。"
    )


# ── 辅助函数 ──────────────────────


async def _get_configured_user(db) -> User | None:
    """获取 MCP 配置的绑定用户。未配置时返回 None。"""
    settings = get_settings()
    if not settings.KNOWBASE_MCP_USER_ID:
        return None
    try:
        user_id = uuid.UUID(settings.KNOWBASE_MCP_USER_ID)
    except ValueError:
        logger.warning("KNOWBASE_MCP_USER_ID is not a valid UUID: %s", settings.KNOWBASE_MCP_USER_ID)
        return None
    return await db.get(User, user_id)


def get_mcp_app():
    """获取 MCP SSE ASGI 应用，用于挂载到 FastAPI。"""
    return mcp.sse_app(mount_path="/mcp")
