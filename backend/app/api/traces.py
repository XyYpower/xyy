"""Trace Lab API：展示 Agent 运行追踪和 AI 调用日志。"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.agent import AgentRun, AICallLog
from app.models.user import User
from app.agents import runtime
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("/runs")
async def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    runs, total = await runtime.get_runs(db, current_user.id, limit=page_size, offset=(page - 1) * page_size)
    return success({
        "items": [
            {
                "id": str(r.id),
                "run_type": r.run_type,
                "goal": r.goal,
                "status": r.status,
                "current_step": r.current_step,
                "total_prompt_tokens": r.total_prompt_tokens,
                "total_completion_tokens": r.total_completion_tokens,
                "estimated_cost": r.estimated_cost,
                "error_message": r.error_message,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in runs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/runs/{run_id}")
async def get_run_detail(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = await runtime.get_run_detail(db, current_user.id, run_id)
    if not run:
        return success(None)
    return success({
        "id": str(run.id),
        "run_type": run.run_type,
        "goal": run.goal,
        "status": run.status,
        "input": run.input,
        "output": run.output,
        "current_step": run.current_step,
        "total_prompt_tokens": run.total_prompt_tokens,
        "total_completion_tokens": run.total_completion_tokens,
        "estimated_cost": run.estimated_cost,
        "error_message": run.error_message,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "steps": [
            {
                "id": str(s.id),
                "step_order": s.step_order,
                "agent_name": s.agent_name,
                "node_name": s.node_name,
                "status": s.status,
                "input": s.input,
                "output": s.output,
                "reasoning_summary": s.reasoning_summary,
                "requires_approval": s.requires_approval,
                "latency_ms": s.latency_ms,
                "error_message": s.error_message,
            }
            for s in run.steps
        ],
        "tool_calls": [
            {
                "id": str(tc.id),
                "step_id": str(tc.step_id) if tc.step_id else None,
                "tool_name": tc.tool_name,
                "arguments": tc.arguments,
                "result": tc.result,
                "status": tc.status,
                "latency_ms": tc.latency_ms,
                "error_message": tc.error_message,
            }
            for tc in run.tool_calls
        ],
    })


@router.get("/ai-logs")
async def list_ai_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base = select(AICallLog).where(AICallLog.user_id == current_user.id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0

    result = await db.execute(
        base.order_by(AICallLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    logs = result.scalars().all()

    return success({
        "items": [
            {
                "id": str(l.id),
                "provider": l.provider,
                "model": l.model,
                "purpose": l.purpose,
                "prompt_tokens": l.prompt_tokens,
                "completion_tokens": l.completion_tokens,
                "estimated_cost": l.estimated_cost,
                "latency_ms": l.latency_ms,
                "status": l.status,
                "error_message": l.error_message,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/stats")
async def get_trace_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Agent 运行统计
    total_runs = (await db.execute(
        select(func.count(AgentRun.id)).where(AgentRun.user_id == current_user.id)
    )).scalar() or 0

    completed_runs = (await db.execute(
        select(func.count(AgentRun.id)).where(
            AgentRun.user_id == current_user.id, AgentRun.status == "completed"
        )
    )).scalar() or 0

    token_cost = (await db.execute(
        select(
            func.sum(AgentRun.total_prompt_tokens),
            func.sum(AgentRun.total_completion_tokens),
            func.sum(AgentRun.estimated_cost),
        ).where(AgentRun.user_id == current_user.id)
    )).one()

    # AI 调用统计
    ai_stats = (await db.execute(
        select(
            func.count(AICallLog.id).label("total_calls"),
            func.sum(AICallLog.prompt_tokens).label("ai_prompt_tokens"),
            func.sum(AICallLog.completion_tokens).label("ai_completion_tokens"),
            func.sum(AICallLog.estimated_cost).label("ai_cost"),
        ).where(AICallLog.user_id == current_user.id)
    )).one()

    success_rate = round(completed_runs / total_runs * 100, 1) if total_runs > 0 else 0.0

    return success({
        "total_runs": total_runs,
        "completed_runs": completed_runs,
        "success_rate": success_rate,
        "total_prompt_tokens": token_cost[0] or 0,
        "total_completion_tokens": token_cost[1] or 0,
        "total_cost": round(token_cost[2] or 0, 4),
        "total_ai_calls": ai_stats.total_calls or 0,
        "ai_prompt_tokens": ai_stats.ai_prompt_tokens or 0,
        "ai_completion_tokens": ai_stats.ai_completion_tokens or 0,
        "ai_cost": round(ai_stats.ai_cost or 0, 4),
    })
