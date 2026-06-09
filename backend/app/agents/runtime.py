"""Agent Runtime：管理 AgentRun 生命周期。"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import AgentRun, AgentStep

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def start_run(
    db: AsyncSession,
    user_id: uuid.UUID,
    run_type: str,
    goal: str | None = None,
    input_data: dict[str, Any] | None = None,
) -> AgentRun:
    """创建并启动一次 Agent 运行。"""
    run = AgentRun(
        user_id=user_id,
        run_type=run_type,
        goal=goal,
        status="running",
        input=input_data,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)
    logger.info("AgentRun %s started (type=%s)", run.id, run_type)
    return run


async def create_step(
    db: AsyncSession,
    run_id: uuid.UUID,
    step_order: int,
    agent_name: str,
    node_name: str,
    input_data: dict[str, Any] | None = None,
    requires_approval: bool = False,
) -> AgentStep:
    """为运行创建一个步骤。"""
    step = AgentStep(
        run_id=run_id,
        step_order=step_order,
        agent_name=agent_name,
        node_name=node_name,
        status="running",
        input=input_data,
        requires_approval=requires_approval,
    )
    db.add(step)
    await db.flush()
    await db.refresh(step)
    return step


async def complete_step(
    db: AsyncSession,
    step_id: uuid.UUID,
    output: dict[str, Any] | None = None,
    latency_ms: int | None = None,
    reasoning_summary: str | None = None,
) -> None:
    """标记步骤完成。"""
    step = await db.get(AgentStep, step_id)
    if step:
        step.status = "completed"
        step.output = output
        step.latency_ms = latency_ms
        step.reasoning_summary = reasoning_summary
        await db.flush()


async def fail_step(
    db: AsyncSession,
    step_id: uuid.UUID,
    error_message: str,
    latency_ms: int | None = None,
) -> None:
    """标记步骤失败。"""
    step = await db.get(AgentStep, step_id)
    if step:
        step.status = "failed"
        step.error_message = error_message
        step.latency_ms = latency_ms
        await db.flush()


async def update_run_status(
    db: AsyncSession,
    run_id: uuid.UUID,
    status: str,
    current_step: str | None = None,
    output: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    """更新运行状态。"""
    run = await db.get(AgentRun, run_id)
    if not run:
        return
    run.status = status
    if current_step is not None:
        run.current_step = current_step
    if output is not None:
        run.output = output
    if error_message is not None:
        run.error_message = error_message
    if status in ("completed", "failed", "cancelled"):
        run.finished_at = _utc_now()
    await db.flush()


async def accumulate_tokens(
    db: AsyncSession,
    run_id: uuid.UUID,
    prompt_tokens: int,
    completion_tokens: int,
    cost: float = 0.0,
) -> None:
    """累加 token 和成本。"""
    run = await db.get(AgentRun, run_id)
    if run:
        run.total_prompt_tokens += prompt_tokens
        run.total_completion_tokens += completion_tokens
        run.estimated_cost += cost
        await db.flush()


async def get_runs(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[AgentRun], int]:
    """获取用户的 Agent 运行列表。"""
    count_query = select(AgentRun).where(AgentRun.user_id == user_id)
    from sqlalchemy import func
    total = (await db.execute(select(func.count()).select_from(count_query.subquery()))).scalar() or 0

    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.user_id == user_id)
        .order_by(AgentRun.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def get_run_detail(
    db: AsyncSession,
    user_id: uuid.UUID,
    run_id: uuid.UUID,
) -> AgentRun | None:
    """获取运行详情（含 steps 和 tool_calls）。"""
    result = await db.execute(
        select(AgentRun)
        .options(selectinload(AgentRun.steps), selectinload(AgentRun.tool_calls))
        .where(AgentRun.id == run_id, AgentRun.user_id == user_id)
    )
    return result.scalar_one_or_none()
