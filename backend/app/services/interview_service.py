import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interview import InterviewQuestion, InterviewSession
from app.models.note import Note
from app.rag import interviewer


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def start_interview(
    db: AsyncSession,
    user_id: uuid.UUID,
    scope: str = "all",
    num_questions: int = 5,
) -> InterviewSession:
    notes = await _get_interview_notes(db, user_id, scope)
    topics = [f"{note.title}: {note.content[:180]}" for note in notes[:20]]
    question_payloads = await interviewer.generate_interview_questions(topics, num_questions)

    session = InterviewSession(
        user_id=user_id,
        title=f"模拟面试 {datetime.now().strftime('%m-%d %H:%M')}",
        scope=scope,
        status="in_progress",
    )
    db.add(session)
    await db.flush()

    for index, payload in enumerate(question_payloads[:num_questions], start=1):
        note = notes[(index - 1) % len(notes)] if notes else None
        db.add(
            InterviewQuestion(
                session_id=session.id,
                note_id=note.id if note else None,
                question=payload["question"],
                reference_answer=payload.get("reference_answer"),
                question_order=index,
            )
        )

    await db.flush()
    await db.refresh(session)
    return await get_session(db, user_id, session.id) or session


async def submit_answer(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    answer: str,
) -> InterviewQuestion:
    session = await get_session(db, user_id, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
    if session.status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview session is completed")

    question = next((item for item in session.questions if item.id == question_id), None)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview question not found")

    evaluation = await interviewer.evaluate_answer(question.question, answer, question.reference_answer)
    question.user_answer = answer
    question.ai_score = int(evaluation["score"])
    question.ai_feedback = str(evaluation["feedback"])
    await db.flush()
    await db.refresh(question)
    return question


async def finish_interview(db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID) -> InterviewSession:
    session = await get_session(db, user_id, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")

    question_payloads = [
        {
            "question": question.question,
            "user_answer": question.user_answer,
            "ai_score": question.ai_score,
            "ai_feedback": question.ai_feedback,
        }
        for question in session.questions
    ]
    scores = [question.ai_score for question in session.questions if question.ai_score is not None]
    session.total_score = sum(scores) if scores else None
    session.summary = await interviewer.generate_session_summary(question_payloads)
    session.status = "completed"
    session.finished_at = _utc_now()
    await db.flush()
    await db.refresh(session)
    return await get_session(db, user_id, session_id) or session


async def get_sessions(db: AsyncSession, user_id: uuid.UUID) -> list[InterviewSession]:
    result = await db.execute(
        select(InterviewSession)
        .options(selectinload(InterviewSession.questions))
        .where(InterviewSession.user_id == user_id)
        .order_by(InterviewSession.created_at.desc())
    )
    return list(result.scalars().all())


async def get_session(db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID) -> InterviewSession | None:
    result = await db.execute(
        select(InterviewSession)
        .options(selectinload(InterviewSession.questions))
        .where(InterviewSession.id == session_id, InterviewSession.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_weak_points(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(
            Note.id.label("note_id"),
            Note.title.label("title"),
            func.avg(InterviewQuestion.ai_score).label("avg_score"),
            func.count(InterviewQuestion.id).label("times_tested"),
        )
        .join(InterviewQuestion, InterviewQuestion.note_id == Note.id)
        .join(InterviewSession, InterviewSession.id == InterviewQuestion.session_id)
        .where(Note.user_id == user_id, InterviewQuestion.ai_score.is_not(None))
        .group_by(Note.id, Note.title)
        .having(func.avg(InterviewQuestion.ai_score) < 7)
        .order_by(func.avg(InterviewQuestion.ai_score).asc(), func.count(InterviewQuestion.id).desc())
    )
    return [
        {
            "note_id": row.note_id,
            "title": row.title,
            "avg_score": round(float(row.avg_score), 1),
            "times_tested": int(row.times_tested),
        }
        for row in result
    ]


async def _get_interview_notes(db: AsyncSession, user_id: uuid.UUID, scope: str) -> list[Note]:
    stmt = select(Note).where(Note.user_id == user_id).order_by(Note.updated_at.desc())
    if scope == "weak_points":
        stmt = stmt.where(Note.mastery_level < 2)
    result = await db.execute(stmt.limit(20))
    return list(result.scalars().all())
