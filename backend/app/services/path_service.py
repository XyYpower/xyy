import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.path import LearningPath, LearningPathModule, LearningPathTopic, LearningTask
from app.rag.llm import get_llm

logger = logging.getLogger(__name__)

PATH_GENERATION_PROMPT = (
    "你是编程学习路径规划师。用户给出学习目标，你生成结构化的学习路径。"
    "包含 5-8 个模块，每模块 3-5 个具体知识点 topic，按优先级排序。"
    "只返回 JSON：{\"name\":\"路径名\",\"description\":\"描述\","
    "\"modules\":[{\"name\":\"模块名\",\"topics\":[\"topic1\",\"topic2\"],\"priority\":1}]}"
)


async def generate_path_payload(goal: str) -> dict:
    llm = get_llm()
    if not llm.api_key:
        return _fallback_path(goal)

    try:
        raw = await llm.chat_json(
            [
                {"role": "system", "content": PATH_GENERATION_PROMPT},
                {"role": "user", "content": goal},
            ]
        )
        payload = json.loads(raw)
        return _normalize_path(payload, goal)
    except Exception:
        logger.warning("LLM learning path generation failed for provider=%s; using fallback", llm.provider, exc_info=True)
        return _fallback_path(goal)


async def generate_learning_path(db: AsyncSession, user_id: uuid.UUID, goal: str) -> LearningPath:
    payload = await generate_path_payload(goal)
    path = LearningPath(
        user_id=user_id,
        name=payload["name"],
        description=payload["description"],
        modules_json=payload["modules"],
    )
    db.add(path)
    await db.flush()

    # 创建结构化模块、主题和任务
    for mod_index, module in enumerate(payload["modules"]):
        mod = LearningPathModule(
            path_id=path.id,
            title=module.get("name", ""),
            description="",
            order_index=module.get("priority", mod_index + 1),
        )
        db.add(mod)
        await db.flush()

        topics = module.get("topics", [])
        for topic_index, topic_name in enumerate(topics):
            if not isinstance(topic_name, str) or not topic_name.strip():
                continue
            tp = LearningPathTopic(
                module_id=mod.id,
                title=topic_name.strip(),
                objective="",
                priority=topic_index + 1,
            )
            db.add(tp)
            await db.flush()

            task = LearningTask(
                user_id=user_id,
                topic_id=tp.id,
                task_type="learn",
                title=f"学习：{topic_name.strip()}",
                description="",
                due_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=mod_index * 7 + topic_index),
            )
            db.add(task)

    await db.flush()
    # 重新加载以确保 structured_modules 可用
    result = await db.execute(
        select(LearningPath)
        .options(selectinload(LearningPath.structured_modules))
        .where(LearningPath.id == path.id)
    )
    return result.scalar_one()


async def get_paths(db: AsyncSession, user_id: uuid.UUID) -> list[LearningPath]:
    result = await db.execute(
        select(LearningPath)
        .options(selectinload(LearningPath.structured_modules))
        .where(LearningPath.user_id == user_id)
        .order_by(LearningPath.created_at.desc())
    )
    return list(result.scalars().all())


async def get_path(db: AsyncSession, user_id: uuid.UUID, path_id: uuid.UUID) -> LearningPath:
    result = await db.execute(
        select(LearningPath)
        .options(selectinload(LearningPath.structured_modules))
        .where(LearningPath.id == path_id, LearningPath.user_id == user_id)
    )
    path = result.scalar_one_or_none()
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    return path


def _normalize_path(payload: dict, goal: str) -> dict:
    name = str(payload.get("name") or f"{goal} 学习路径").strip()[:100]
    description = str(payload.get("description") or f"围绕 {goal} 生成的学习路径。").strip()
    modules = []
    raw_modules = payload.get("modules", [])
    if not isinstance(raw_modules, list):
        return _fallback_path(goal)

    for index, module in enumerate(raw_modules, start=1):
        if not isinstance(module, dict):
            continue
        module_name = str(module.get("name", "")).strip()
        raw_topics = module.get("topics", [])
        if not isinstance(raw_topics, list):
            continue
        topics = [str(topic).strip() for topic in raw_topics if str(topic).strip()]
        if module_name and topics:
            priority = _normalize_priority(module.get("priority"), index)
            modules.append(
                {
                    "name": module_name,
                    "topics": topics[:5],
                    "priority": priority,
                }
            )
    if not modules:
        return _fallback_path(goal)
    return {"name": name, "description": description, "modules": modules[:8]}


def _normalize_priority(value, fallback: int) -> int:
    if value is None:
        return fallback
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return fallback


def _fallback_path(goal: str) -> dict:
    return {
        "name": f"{goal} 学习路径",
        "description": f"围绕 {goal} 的基础学习路线，适合先搭建知识框架再逐步补充项目经验。",
        "modules": [
            {"name": "语言与基础", "topics": ["核心语法", "异常处理", "常用集合", "异步与并发"], "priority": 1},
            {"name": "数据库", "topics": ["索引原理", "事务隔离", "慢 SQL 优化", "ORM 使用"], "priority": 2},
            {"name": "缓存", "topics": ["Redis 数据结构", "缓存穿透", "缓存雪崩", "缓存一致性"], "priority": 3},
            {"name": "接口与认证", "topics": ["REST API", "JWT 认证", "权限校验", "接口错误处理"], "priority": 4},
            {"name": "工程实践", "topics": ["测试", "日志", "部署", "性能排查"], "priority": 5},
        ],
    }
