"""Agent Workspace API：运行 Agent、确认队列、每日任务。"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.path import LearningTask, LearningPathTopic, LearningPathModule
from app.models.agent import AgentRun
from app.agents import runtime, diagnosis, planner
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.post("/diagnose")
async def run_diagnosis(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """运行诊断 Agent。"""
    run = await runtime.start_run(db, current_user.id, "diagnosis", goal="诊断学习薄弱点")
    step = await runtime.create_step(db, run.id, 1, "DiagnosisAgent", "diagnose")

    try:
        result = await diagnosis.diagnose(db, current_user.id)
        await runtime.complete_step(db, step.id, output=result, latency_ms=0)
        await runtime.update_run_status(db, run.id, "completed", output=result)
        await db.commit()
        return success({"run_id": str(run.id), "diagnosis": result})
    except Exception as exc:
        await runtime.fail_step(db, step.id, str(exc))
        await runtime.update_run_status(db, run.id, "failed", error_message=str(exc))
        await db.commit()
        raise HTTPException(status_code=500, detail=f"诊断失败: {exc}")


@router.post("/plan")
async def run_planner(
    goal: str,
    run_diagnosis_first: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """运行规划 Agent，可选先诊断。"""
    diagnosis_result = None
    if run_diagnosis_first:
        diagnosis_result = await diagnosis.diagnose(db, current_user.id)

    run = await runtime.start_run(
        db, current_user.id, "plan",
        goal=goal,
        input_data={"goal": goal, "has_diagnosis": diagnosis_result is not None},
    )
    step = await runtime.create_step(db, run.id, 1, "PlannerAgent", "plan")

    try:
        result = await planner.plan(db, current_user.id, goal, diagnosis_result)
        await runtime.complete_step(db, step.id, output=result, latency_ms=0)
        await runtime.update_run_status(db, run.id, "completed", output=result)
        await db.commit()
        return success({
            "run_id": str(run.id),
            "plan": result,
            "diagnosis": diagnosis_result,
        })
    except Exception as exc:
        await runtime.fail_step(db, step.id, str(exc))
        await runtime.update_run_status(db, run.id, "failed", error_message=str(exc))
        await db.commit()
        raise HTTPException(status_code=500, detail=f"规划失败: {exc}")


@router.post("/diagnose-and-plan")
async def run_diagnose_and_plan(
    goal: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """一站式：诊断 + 规划。"""
    # 诊断
    run = await runtime.start_run(db, current_user.id, "diagnosis", goal=goal)
    step1 = await runtime.create_step(db, run.id, 1, "DiagnosisAgent", "diagnose")
    diagnosis_result = await diagnosis.diagnose(db, current_user.id)
    await runtime.complete_step(db, step1.id, output=diagnosis_result)

    # 规划
    step2 = await runtime.create_step(db, run.id, 2, "PlannerAgent", "plan")
    plan_result = await planner.plan(db, current_user.id, goal, diagnosis_result)
    await runtime.complete_step(db, step2.id, output=plan_result)

    await runtime.update_run_status(db, run.id, "completed", output={
        "diagnosis": diagnosis_result,
        "plan": plan_result,
    })
    await db.commit()

    return success({
        "run_id": str(run.id),
        "diagnosis": diagnosis_result,
        "plan": plan_result,
    })


@router.get("/tasks/today")
async def get_today_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取今日学习任务。"""
    now = datetime.now(UTC).replace(tzinfo=None)
    today_end = now.replace(hour=23, minute=59, second=59)

    result = await db.execute(
        select(LearningTask)
        .options(selectinload(LearningTask.topic))
        .where(
            LearningTask.user_id == current_user.id,
            LearningTask.status.in_(["pending", "in_progress"]),
            LearningTask.due_at <= today_end,
        )
        .order_by(LearningTask.due_at.asc())
    )
    tasks = result.scalars().all()

    return success({
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "task_type": t.task_type,
                "status": t.status,
                "due_at": t.due_at.isoformat() if t.due_at else None,
                "topic_title": t.topic.title if t.topic else None,
            }
            for t in tasks
        ],
        "total": len(tasks),
    })


@router.get("/tasks")
async def list_tasks(
    status_filter: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取任务列表（可按状态筛选）。"""
    base = select(LearningTask).where(LearningTask.user_id == current_user.id)
    if status_filter:
        base = base.where(LearningTask.status == status_filter)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    result = await db.execute(
        base.order_by(LearningTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    tasks = result.scalars().all()

    return success({
        "items": [
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "task_type": t.task_type,
                "status": t.status,
                "due_at": t.due_at.isoformat() if t.due_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "topic_id": str(t.topic_id) if t.topic_id else None,
            }
            for t in tasks
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.put("/tasks/{task_id}/complete")
async def complete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记任务完成。"""
    task = await db.get(LearningTask, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "completed"
    task.completed_at = datetime.now(UTC).replace(tzinfo=None)
    await db.flush()
    return success({"id": str(task.id), "status": "completed"})
