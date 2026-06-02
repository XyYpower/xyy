import uuid

import pytest
from sqlalchemy import delete, select, text

from app.database import async_session
from app.models.interview import InterviewQuestion, InterviewSession
from app.models.note import Note
from app.models.user import User
from app.services import interview_service


pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _require_database() -> None:
    try:
        async with async_session() as session:
            await session.execute(text("select 1"))
    except Exception as exc:
        pytest.skip(f"database is not available for interview service test: {exc}")


async def _create_user_with_notes(username: str) -> User:
    async with async_session() as session:
        user = User(username=username, password_hash="hash")
        session.add(user)
        await session.flush()
        session.add_all(
            [
                Note(user_id=user.id, title="JWT 认证", content="JWT 包含 header、payload、signature。"),
                Note(user_id=user.id, title="Redis 缓存穿透", content="布隆过滤器可以拦截不存在的 key。"),
            ]
        )
        await session.commit()
        await session.refresh(user)
        return user


async def _cleanup_user(username: str) -> None:
    async with async_session() as session:
        result = await session.execute(select(User.id).where(User.username == username))
        user_id = result.scalar_one_or_none()
        if user_id:
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()


async def test_interview_lifecycle_generates_scores_and_summary(monkeypatch):
    await _require_database()
    username = f"interview_{uuid.uuid4().hex[:10]}"

    async def fake_generate(topics, num_questions=5):
        return [{"question": f"请解释 {index}", "reference_answer": "参考答案"} for index in range(num_questions)]

    async def fake_evaluate(question, answer, reference=None):
        return {"score": 8, "feedback": f"{question} 回答基本正确"}

    async def fake_summary(questions):
        return f"完成 {len(questions)} 道题，整体不错。"

    monkeypatch.setattr(interview_service.interviewer, "generate_interview_questions", fake_generate)
    monkeypatch.setattr(interview_service.interviewer, "evaluate_answer", fake_evaluate)
    monkeypatch.setattr(interview_service.interviewer, "generate_session_summary", fake_summary)

    try:
        user = await _create_user_with_notes(username)

        async with async_session() as session:
            interview = await interview_service.start_interview(session, user.id, scope="all", num_questions=2)
            await session.commit()
            session_id = interview.id

        async with async_session() as session:
            interview = await interview_service.get_session(session, user.id, session_id)
            assert interview is not None
            assert interview.status == "in_progress"
            assert len(interview.questions) == 2

            for question in interview.questions:
                scored = await interview_service.submit_answer(
                    session,
                    user.id,
                    session_id,
                    question.id,
                    "我会先说明概念，再结合项目场景展开。",
                )
                assert scored.ai_score == 8
                assert "基本正确" in (scored.ai_feedback or "")

            finished = await interview_service.finish_interview(session, user.id, session_id)
            await session.commit()

        assert finished.status == "completed"
        assert finished.total_score == 16
        assert finished.summary == "完成 2 道题，整体不错。"
        assert finished.finished_at is not None
    finally:
        await _cleanup_user(username)


async def test_weak_points_are_aggregated_by_note(monkeypatch):
    await _require_database()
    username = f"weak_point_{uuid.uuid4().hex[:10]}"

    try:
        user = await _create_user_with_notes(username)

        async with async_session() as session:
            note_ids = (await session.execute(select(Note.id).where(Note.user_id == user.id).order_by(Note.title))).scalars().all()
            interview = InterviewSession(user_id=user.id, title="薄弱点测试", scope="all", status="completed")
            session.add(interview)
            await session.flush()
            session.add_all(
                [
                    InterviewQuestion(
                        session_id=interview.id,
                        note_id=note_ids[0],
                        question="JWT 怎么校验？",
                        user_answer="不太清楚",
                        ai_score=4,
                        ai_feedback="需要补充签名校验。",
                        question_order=1,
                    ),
                    InterviewQuestion(
                        session_id=interview.id,
                        note_id=note_ids[1],
                        question="缓存穿透怎么处理？",
                        user_answer="布隆过滤器。",
                        ai_score=9,
                        ai_feedback="回答良好。",
                        question_order=2,
                    ),
                ]
            )
            await session.commit()

        async with async_session() as session:
            weak_points = await interview_service.get_weak_points(session, user.id)

        assert len(weak_points) == 1
        assert weak_points[0]["avg_score"] == 4.0
        assert weak_points[0]["times_tested"] == 1
    finally:
        await _cleanup_user(username)
