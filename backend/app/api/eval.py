"""RAG 质量与评估 API。"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.common import PageResult
from app.services import eval_service
from app.utils.deps import get_current_user
from app.utils.response import success

from pydantic import BaseModel, Field

router = APIRouter(prefix="/eval", tags=["eval"])


# ── 请求模型 ──────────────────────


class FeedbackRequest(BaseModel):
    message_id: uuid.UUID
    rating: str = Field(..., pattern="^(helpful|not_helpful)$")
    issue_type: str | None = None
    comment: str | None = None


class EvalCaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    case_type: str = Field(..., min_length=1, max_length=40)
    input_data: dict
    expected_output: dict | None = None
    tags: list[str] | None = None


class EvalRunRequest(BaseModel):
    name: str = Field(default="RAG 评估", max_length=200)


# ── 反馈端点 ──────────────────────


@router.post("/feedback")
async def submit_feedback(
    data: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    feedback = await eval_service.submit_feedback(
        db, current_user.id, data.message_id, data.rating, data.issue_type, data.comment
    )
    return success({"id": str(feedback.id), "rating": feedback.rating})


@router.get("/feedback/stats")
async def get_feedback_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stats = await eval_service.get_feedback_stats(db, current_user.id)
    return success(stats)


# ── 评估用例端点 ──────────────────────


@router.post("/cases")
async def create_eval_case(
    data: EvalCaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    case = await eval_service.create_eval_case(
        db, current_user.id, data.name, data.case_type, data.input_data, data.expected_output, data.tags
    )
    return success({
        "id": str(case.id),
        "name": case.name,
        "case_type": case.case_type,
    })


@router.get("/cases")
async def list_eval_cases(
    case_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cases = await eval_service.get_eval_cases(db, current_user.id, case_type)
    return success([
        {
            "id": str(c.id),
            "name": c.name,
            "case_type": c.case_type,
            "input_data": c.input_data,
            "expected_output": c.expected_output,
            "tags": c.tags,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in cases
    ])


# ── 评估运行端点 ──────────────────────


@router.post("/runs")
async def start_eval_run(
    data: EvalRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        run = await eval_service.run_rag_evaluation(db, current_user.id, data.name)
        await db.commit()
        return success({
            "id": str(run.id),
            "name": run.name,
            "status": run.status,
            "total_cases": run.total_cases,
            "passed_cases": run.passed_cases,
            "avg_score": run.avg_score,
        })
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/runs")
async def list_eval_runs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    runs = await eval_service.get_eval_runs(db, current_user.id)
    return success([
        {
            "id": str(r.id),
            "name": r.name,
            "target_type": r.target_type,
            "status": r.status,
            "total_cases": r.total_cases,
            "passed_cases": r.passed_cases,
            "avg_score": r.avg_score,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        }
        for r in runs
    ])


@router.get("/runs/{run_id}")
async def get_eval_run_detail(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = await eval_service.get_eval_run_detail(db, current_user.id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")
    return success({
        "id": str(run.id),
        "name": run.name,
        "target_type": run.target_type,
        "status": run.status,
        "total_cases": run.total_cases,
        "passed_cases": run.passed_cases,
        "avg_score": run.avg_score,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "results": [
            {
                "id": str(r.id),
                "eval_case_id": str(r.eval_case_id),
                "score": r.score,
                "passed": r.passed,
                "metrics": r.metrics,
                "actual_output": r.actual_output,
                "error_message": r.error_message,
            }
            for r in run.results
        ] if hasattr(run, "results") else [],
    })
