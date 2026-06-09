"""Portfolio Builder 服务：生成项目技术报告和学习报告。"""

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.models.agent import AgentRun
from app.models.eval import MessageFeedback
from app.models.interview import InterviewSession
from app.models.path import LearningPath
from app.rag.llm import get_llm
from app.services import interview_service, note_service, review_service

logger = logging.getLogger(__name__)


async def generate_project_report(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """生成项目技术报告：汇总 KnowBase 的架构、能力和技术栈。"""

    # 收集项目数据
    notes_count = (await db.execute(
        select(func.count(Note.id)).where(Note.user_id == user_id)
    )).scalar() or 0

    review_stats = await _safe_get_review_stats(db, user_id)
    interview_count = (await db.execute(
        select(func.count(InterviewSession.id)).where(InterviewSession.user_id == user_id)
    )).scalar() or 0

    paths_count = (await db.execute(
        select(func.count(LearningPath.id)).where(LearningPath.user_id == user_id)
    )).scalar() or 0

    agent_runs = (await db.execute(
        select(func.count(AgentRun.id)).where(AgentRun.user_id == user_id)
    )).scalar() or 0

    llm = get_llm()
    context = {
        "notes_count": notes_count,
        "review_stats": review_stats,
        "interview_sessions": interview_count,
        "learning_paths": paths_count,
        "agent_runs": agent_runs,
    }

    if not llm.api_key:
        return _fallback_project_report(context)

    try:
        raw = await llm.chat_json([
            {"role": "system", "content": PROJECT_REPORT_PROMPT},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ])
        result = json.loads(raw)
        return _normalize_report(result, context)
    except Exception:
        logger.warning("LLM project report generation failed; using fallback", exc_info=True)
        return _fallback_project_report(context)


async def generate_learning_report(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """生成 AI Agent 应用开发学习报告。"""

    notes_data = await _collect_notes_summary(db, user_id)
    weak_points = await interview_service.get_weak_points(db, user_id)
    review_stats = await _safe_get_review_stats(db, user_id)

    # 最近的 Agent 运行
    recent_runs = (await db.execute(
        select(AgentRun).where(AgentRun.user_id == user_id).order_by(AgentRun.created_at.desc()).limit(5)
    )).scalars().all()

    context = {
        "notes": notes_data,
        "weak_points": weak_points[:5],
        "review_stats": review_stats,
        "recent_agent_runs": [
            {"type": r.run_type, "goal": r.goal, "status": r.status}
            for r in recent_runs
        ],
    }

    llm = get_llm()
    if not llm.api_key:
        return _fallback_learning_report(context)

    try:
        raw = await llm.chat_json([
            {"role": "system", "content": LEARNING_REPORT_PROMPT},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False, default=str)},
        ])
        result = json.loads(raw)
        return _normalize_learning_report(result, context)
    except Exception:
        logger.warning("LLM learning report generation failed; using fallback", exc_info=True)
        return _fallback_learning_report(context)


async def get_portfolio_summary(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """获取 Portfolio 总览数据。"""

    notes_count = (await db.execute(
        select(func.count(Note.id)).where(Note.user_id == user_id)
    )).scalar() or 0

    mastered = (await db.execute(
        select(func.count(Note.id)).where(Note.user_id == user_id, Note.mastery_level == 2)
    )).scalar() or 0

    review_stats = await _safe_get_review_stats(db, user_id)
    interview_count = (await db.execute(
        select(func.count(InterviewSession.id)).where(InterviewSession.user_id == user_id)
    )).scalar() or 0

    agent_runs = (await db.execute(
        select(func.count(AgentRun.id)).where(AgentRun.user_id == user_id)
    )).scalar() or 0

    paths_count = (await db.execute(
        select(func.count(LearningPath.id)).where(LearningPath.user_id == user_id)
    )).scalar() or 0

    # 反馈统计
    feedback_total = (await db.execute(
        select(func.count(MessageFeedback.id)).where(MessageFeedback.user_id == user_id)
    )).scalar() or 0
    feedback_helpful = (await db.execute(
        select(func.count(MessageFeedback.id)).where(
            MessageFeedback.user_id == user_id, MessageFeedback.rating == "helpful"
        )
    )).scalar() or 0

    return {
        "notes_count": notes_count,
        "mastered_count": mastered,
        "review_stats": review_stats,
        "interview_sessions": interview_count,
        "agent_runs": agent_runs,
        "learning_paths": paths_count,
        "feedback_total": feedback_total,
        "feedback_helpful_rate": round(feedback_helpful / feedback_total * 100, 1) if feedback_total > 0 else 0,
    }


def format_report_as_markdown(report: dict, report_type: str = "project") -> str:
    """将报告格式化为 Markdown，适合放进 README 或简历。"""
    lines = []
    title = report.get("title", "KnowBase 报告")
    lines.append(f"# {title}\n")

    if report.get("summary"):
        lines.append(f"> {report['summary']}\n")

    for section in report.get("sections", []):
        heading = section.get("heading", "")
        content = section.get("content", "")
        lines.append(f"## {heading}\n")
        lines.append(f"{content}\n")

    if report.get("highlights"):
        lines.append("## 亮点\n")
        for h in report["highlights"]:
            lines.append(f"- {h}")
        lines.append("")

    if report.get("metrics"):
        lines.append("## 数据指标\n")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        for key, value in report["metrics"].items():
            lines.append(f"| {key} | {value} |")
        lines.append("")

    lines.append(f"\n---\n*Generated by KnowBase Portfolio Builder*")
    return "\n".join(lines)


# ── 提示词 ──────────────────────

PROJECT_REPORT_PROMPT = (
    "你是技术项目报告撰写专家。根据 KnowBase 项目的使用数据，生成一份技术报告。\n"
    "KnowBase 是一个 AI Agent 学习工作台，技术栈：FastAPI + React + PostgreSQL + pgvector + RAG。\n"
    "输出 JSON：{\"title\":\"标题\",\"summary\":\"摘要\",\"sections\":[{\"heading\":\"标题\",\"content\":\"内容\"}],"
    "\"highlights\":[\"亮点1\"],\"metrics\":{\"指标\":\"数值\"}}"
)

LEARNING_REPORT_PROMPT = (
    "你是学习报告撰写专家。根据用户的学习数据生成 AI Agent 应用开发学习报告。\n"
    "输出 JSON：{\"title\":\"标题\",\"summary\":\"摘要\",\"sections\":[{\"heading\":\"标题\",\"content\":\"内容\"}],"
    "\"highlights\":[\"亮点1\"],\"next_steps\":[\"下一步1\"]}"
)


# ── 内部工具函数 ──────────────────────


async def _safe_get_review_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    try:
        return await review_service.get_review_stats(db, user_id)
    except Exception:
        return {}


async def _collect_notes_summary(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    notes, _ = await note_service.get_notes(db, user_id, page=1, page_size=30)
    return [{"title": n.title, "mastery": n.mastery_level, "source": n.source_type} for n in notes]


def _normalize_report(result: dict, context: dict) -> dict:
    return {
        "title": str(result.get("title", "KnowBase 项目技术报告"))[:200],
        "summary": str(result.get("summary", ""))[:500],
        "sections": [
            {"heading": str(s.get("heading", ""))[:100], "content": str(s.get("content", ""))[:1000]}
            for s in result.get("sections", [])[:8]
        ],
        "highlights": [str(h)[:200] for h in result.get("highlights", [])[:10]],
        "metrics": {str(k): str(v) for k, v in result.get("metrics", {}).items()},
        "raw_context": context,
    }


def _normalize_learning_report(result: dict, context: dict) -> dict:
    return {
        "title": str(result.get("title", "AI Agent 应用开发学习报告"))[:200],
        "summary": str(result.get("summary", ""))[:500],
        "sections": [
            {"heading": str(s.get("heading", ""))[:100], "content": str(s.get("content", ""))[:1000]}
            for s in result.get("sections", [])[:8]
        ],
        "highlights": [str(h)[:200] for h in result.get("highlights", [])[:10]],
        "next_steps": [str(s)[:200] for s in result.get("next_steps", [])[:5]],
        "raw_context": context,
    }


def _fallback_project_report(context: dict) -> dict:
    notes = context.get("notes_count", 0)
    review = context.get("review_stats", {})
    return {
        "title": "KnowBase — AI Agent 学习工作台技术报告",
        "summary": "KnowBase 是面向开发者的 AI Agent 学习工作台，集成 RAG 对话、间隔复习、模拟面试、Agent 运行追踪和评估系统。",
        "sections": [
            {
                "heading": "项目架构",
                "content": "后端：FastAPI + SQLAlchemy + PostgreSQL + pgvector\n前端：React 19 + TypeScript + Ant Design + Tailwind CSS\nAI：RAG 管线 + 多 Agent 运行时 + Tool Registry",
            },
            {
                "heading": "核心能力",
                "content": "1. RAG 对话：基于知识点的语义检索和 AI 回答\n2. 间隔复习：SM-2 算法驱动的复习调度\n3. 模拟面试：AI 出题、评分和反馈\n4. Agent Workspace：诊断薄弱点 + 自动生成学习计划\n5. Trace Lab：Agent 运行追踪和 AI 调用监控\n6. 评估系统：RAG 质量回归评估和用户反馈",
            },
            {
                "heading": "技术亮点",
                "content": f"管理 {notes} 个知识点，{review.get('total_cards', 0)} 张复习卡片，{context.get('agent_runs', 0)} 次 Agent 运行。",
            },
        ],
        "highlights": [
            "轻量 Agent Runtime：Tool Registry + Trace + 人工确认",
            "Hybrid Retrieval：向量相似度 + 全文搜索混合检索",
            "RAG 评估闭环：自动评分 + 用户反馈 + 回归测试",
            "完整数据隔离：JWT 认证 + user_id 级别隔离",
        ],
        "metrics": {
            "知识点数": notes,
            "复习卡片": review.get("total_cards", 0),
            "面试场次": context.get("interview_sessions", 0),
            "Agent 运行": context.get("agent_runs", 0),
            "学习路径": context.get("learning_paths", 0),
        },
        "raw_context": context,
    }


def _fallback_learning_report(context: dict) -> dict:
    notes = context.get("notes", [])
    mastered = sum(1 for n in notes if n.get("mastery") == 2)
    weak = context.get("weak_points", [])
    return {
        "title": "AI Agent 应用开发学习报告",
        "summary": f"共学习 {len(notes)} 个知识点，掌握 {mastered} 个，{len(weak)} 个薄弱领域待加强。",
        "sections": [
            {
                "heading": "学习进度",
                "content": f"已学习 {len(notes)} 个知识点，其中 {mastered} 个已掌握。\n"
                f"复习统计：总卡片 {context.get('review_stats', {}).get('total_cards', 0)} 张，"
                f"今日待复习 {context.get('review_stats', {}).get('due_today', 0)} 张。",
            },
            {
                "heading": "薄弱领域",
                "content": "\n".join(f"- {w['title']}（平均分 {w['avg_score']}/10）" for w in weak[:5]) or "暂无薄弱领域数据。",
            },
            {
                "heading": "Agent 使用情况",
                "content": "\n".join(
                    f"- {r['type']}: {r['goal'] or '无目标'} ({r['status']})"
                    for r in context.get("recent_agent_runs", [])[:5]
                ) or "暂无 Agent 运行记录。",
            },
        ],
        "highlights": [
            f"掌握 {mastered}/{len(notes)} 个知识点",
            f"完成 {context.get('review_stats', {}).get('total_cards', 0)} 张复习卡片",
        ],
        "next_steps": [
            "优先复习薄弱知识点",
            "通过模拟面试检验学习效果",
            "使用 Agent Workspace 制定新学习计划",
        ],
        "raw_context": context,
    }
