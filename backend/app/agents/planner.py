"""PlannerAgent：根据诊断结果和学习目标生成结构化学习路径。

V4.1 拆分为 preview_plan（只生成草稿）和 commit_plan（审批后落库）。
"""

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.path import LearningPath, LearningPathModule, LearningPathTopic, LearningTask
from app.rag.llm import get_llm
from app.services import path_service

logger = logging.getLogger(__name__)

PLANNER_PROMPT = (
    "你是编程学习路径规划师。根据用户目标和诊断结果，生成结构化学习计划。\n"
    "输出 JSON：\n"
    "{\"name\":\"路径名\",\"description\":\"描述\",\"modules\":[{\"title\":\"模块\",\"description\":\"描述\",\"topics\":[{\"title\":\"topic\",\"objective\":\"目标\"}]}]}\n"
    "模块按优先级排列，每模块 3-5 个 topic。"
)


async def preview_plan(
    goal: str,
    diagnosis: dict | None = None,
) -> dict:
    """生成学习计划预览（不落库）。返回结构化草稿。"""

    context = {"goal": goal}
    if diagnosis:
        context["weak_areas"] = diagnosis.get("weak_areas", [])
        context["next_steps"] = diagnosis.get("next_steps", [])

    llm = get_llm()
    if not llm.api_key:
        payload = _fallback_plan(goal, diagnosis)
    else:
        try:
            raw = await llm.chat_json([
                {"role": "system", "content": PLANNER_PROMPT},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False, default=str)},
            ])
            payload = _normalize_plan(json.loads(raw), goal)
        except Exception:
            logger.warning("LLM planning failed; using fallback", exc_info=True)
            payload = _fallback_plan(goal, diagnosis)

    # 计算任务总数
    tasks_count = sum(len(m.get("topics", [])) for m in payload["modules"])

    return {
        "name": payload["name"],
        "description": payload["description"],
        "modules": payload["modules"],
        "legacy_modules": payload.get("legacy_modules", []),
        "modules_count": len(payload["modules"]),
        "tasks_count": tasks_count,
    }


async def commit_plan(
    db: AsyncSession,
    user_id: uuid.UUID,
    plan_preview: dict,
    agent_run_id: uuid.UUID | None = None,
) -> dict:
    """审批通过后将计划落库。创建 LearningPath + modules + topics + tasks。"""

    path = LearningPath(
        user_id=user_id,
        name=plan_preview["name"],
        description=plan_preview["description"],
        modules_json=plan_preview.get("legacy_modules", []),
    )
    db.add(path)
    await db.flush()

    tasks = []
    for mod_index, module in enumerate(plan_preview.get("modules", [])):
        mod = LearningPathModule(
            path_id=path.id,
            title=module["title"],
            description=module.get("description", ""),
            order_index=mod_index + 1,
        )
        db.add(mod)
        await db.flush()

        for topic_index, topic in enumerate(module.get("topics", [])):
            tp = LearningPathTopic(
                module_id=mod.id,
                title=topic["title"],
                objective=topic.get("objective", ""),
                priority=topic_index + 1,
            )
            db.add(tp)
            await db.flush()

            task = LearningTask(
                user_id=user_id,
                topic_id=tp.id,
                task_type="learn",
                title=f"学习：{topic['title']}",
                description=topic.get("objective", ""),
                due_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=mod_index * 7 + topic_index),
                agent_run_id=agent_run_id,
            )
            db.add(task)
            tasks.append(task)

    await db.flush()
    await db.refresh(path)

    return {
        "path_id": str(path.id),
        "name": path.name,
        "description": path.description,
        "modules_count": len(plan_preview.get("modules", [])),
        "tasks_count": len(tasks),
        "tasks": [
            {"title": t.title, "task_type": t.task_type, "due_at": t.due_at.isoformat() if t.due_at else None}
            for t in tasks[:20]
        ],
    }


async def plan(
    db: AsyncSession,
    user_id: uuid.UUID,
    goal: str,
    diagnosis: dict | None = None,
) -> dict:
    """兼容旧接口：preview + commit 一步完成。"""
    preview = await preview_plan(goal, diagnosis)
    return await commit_plan(db, user_id, preview)


def _normalize_plan(result: dict, goal: str) -> dict:
    name = str(result.get("name") or f"{goal} 学习路径").strip()[:100]
    description = str(result.get("description") or "").strip()
    modules = []
    legacy_modules = []

    for module in result.get("modules", [])[:8]:
        if not isinstance(module, dict):
            continue
        title = str(module.get("title") or module.get("name", "")).strip()
        topics_raw = module.get("topics", [])
        topics = []
        topic_names = []
        for t in topics_raw[:5]:
            if isinstance(t, dict):
                topics.append({"title": str(t.get("title", ""))[:200], "objective": str(t.get("objective", ""))[:500]})
                topic_names.append(str(t.get("title", "")))
            elif isinstance(t, str):
                topics.append({"title": t[:200], "objective": ""})
                topic_names.append(t)
        if title and topics:
            modules.append({
                "title": title,
                "description": str(module.get("description", "")),
                "topics": topics,
            })
            legacy_modules.append({
                "name": title,
                "topics": topic_names,
                "priority": len(modules),
            })

    return {
        "name": name,
        "description": description or f"围绕 {goal} 的学习路径",
        "modules": modules,
        "legacy_modules": legacy_modules,
    }


def _fallback_plan(goal: str, diagnosis: dict | None = None) -> dict:
    weak = []
    if diagnosis:
        weak = [a["area"] for a in diagnosis.get("weak_areas", [])[:3]]

    modules = [
        {
            "title": "基础巩固",
            "description": "补齐核心概念和基础知识",
            "topics": [
                {"title": f"复习 {w}", "objective": f"深入理解 {w} 的核心概念"} for w in weak[:3]
            ] or [
                {"title": "核心概念梳理", "objective": "系统回顾已学知识"},
            ],
        },
        {
            "title": "实践练习",
            "description": "通过实际项目巩固知识",
            "topics": [
                {"title": "小项目实战", "objective": "动手实现一个完整项目"},
                {"title": "代码重构", "objective": "优化已有代码质量"},
            ],
        },
        {
            "title": "进阶提升",
            "description": "深入高级主题",
            "topics": [
                {"title": "性能优化", "objective": "学习性能分析和优化技巧"},
                {"title": "架构设计", "objective": "理解系统设计原则"},
            ],
        },
    ]

    return {
        "name": f"{goal} 学习路径",
        "description": f"围绕 {goal} 的结构化学习计划",
        "modules": modules,
        "legacy_modules": [
            {"name": m["title"], "topics": [t["title"] for t in m["topics"]], "priority": i + 1}
            for i, m in enumerate(modules)
        ],
    }
