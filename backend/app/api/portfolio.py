"""Portfolio Builder API。"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.agents import runtime
from app.services import portfolio_service
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/summary")
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    summary = await portfolio_service.get_portfolio_summary(db, current_user.id)
    return success(summary)


@router.post("/report/project")
async def generate_project_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await portfolio_service.generate_project_report(db, current_user.id)
    return success(report)


@router.post("/report/learning")
async def generate_learning_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await portfolio_service.generate_learning_report(db, current_user.id)
    return success(report)


@router.get("/report/project/markdown")
async def export_project_report_markdown(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await portfolio_service.generate_project_report(db, current_user.id)
    md = portfolio_service.format_report_as_markdown(report, "project")
    return PlainTextResponse(md, media_type="text/markdown", headers={
        "Content-Disposition": "attachment; filename=knowbase-project-report.md"
    })


@router.get("/report/learning/markdown")
async def export_learning_report_markdown(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await portfolio_service.generate_learning_report(db, current_user.id)
    md = portfolio_service.format_report_as_markdown(report, "learning")
    return PlainTextResponse(md, media_type="text/markdown", headers={
        "Content-Disposition": "attachment; filename=knowbase-learning-report.md"
    })


@router.get("/runs/recent")
async def get_recent_runs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取最近的 Agent 运行用于回放展示。"""
    runs, _ = await runtime.get_runs(db, current_user.id, limit=5)
    return success([
        {
            "id": str(r.id),
            "run_type": r.run_type,
            "goal": r.goal,
            "status": r.status,
            "total_prompt_tokens": r.total_prompt_tokens,
            "total_completion_tokens": r.total_completion_tokens,
            "estimated_cost": r.estimated_cost,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        }
        for r in runs
    ])
