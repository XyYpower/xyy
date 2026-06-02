import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.interview import (
    AnswerSubmitRequest,
    InterviewQuestionOut,
    InterviewSessionOut,
    InterviewStartRequest,
    WeakPointOut,
)
from app.services import interview_service
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/interview", tags=["interview"])


@router.post("/start")
async def start_interview(
    data: InterviewStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await interview_service.start_interview(db, current_user.id, data.scope, data.num_questions)
    return success(InterviewSessionOut.model_validate(session))


@router.post("/{session_id}/answer/{question_id}")
async def submit_answer(
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    data: AnswerSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    question = await interview_service.submit_answer(db, current_user.id, session_id, question_id, data.answer)
    return success(InterviewQuestionOut.model_validate(question))


@router.post("/{session_id}/finish")
async def finish_interview(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await interview_service.finish_interview(db, current_user.id, session_id)
    return success(InterviewSessionOut.model_validate(session))


@router.get("/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sessions = await interview_service.get_sessions(db, current_user.id)
    return success([InterviewSessionOut.model_validate(session) for session in sessions])


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await interview_service.get_session(db, current_user.id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return success(InterviewSessionOut.model_validate(session))


@router.get("/weak-points")
async def get_weak_points(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    weak_points = await interview_service.get_weak_points(db, current_user.id)
    return success([WeakPointOut.model_validate(item) for item in weak_points])
