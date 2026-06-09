import csv
import io
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.import_job import ImportJob
from app.models.interview import InterviewSession
from app.models.note import Note
from app.models.path import LearningPath
from app.models.review import ReviewCard


async def export_json(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """导出当前用户主要学习数据为 JSON。"""

    notes = await _get_notes(db, user_id)
    review_cards = await _get_review_cards(db, user_id)
    paths = (
        await db.execute(select(LearningPath).where(LearningPath.user_id == user_id).order_by(LearningPath.created_at.asc()))
    ).scalars().all()
    interviews = (
        await db.execute(
            select(InterviewSession)
            .options(selectinload(InterviewSession.questions))
            .where(InterviewSession.user_id == user_id)
            .order_by(InterviewSession.created_at.asc())
        )
    ).scalars().all()
    import_jobs = (
        await db.execute(select(ImportJob).where(ImportJob.user_id == user_id).order_by(ImportJob.created_at.asc()))
    ).scalars().all()

    return {
        "notes": [
            {
                "id": str(note.id),
                "title": note.title,
                "content": note.content,
                "summary": note.summary,
                "category": note.category.name if note.category else None,
                "tags": [tag.name for tag in note.tags],
                "mastery_level": note.mastery_level,
                "source_type": note.source_type,
                "source_url": note.source_url,
                "created_at": note.created_at.isoformat() if note.created_at else None,
                "updated_at": note.updated_at.isoformat() if note.updated_at else None,
            }
            for note in notes
        ],
        "review_cards": [
            {
                "id": str(card.id),
                "note_id": str(card.note_id),
                "card_type": card.card_type,
                "question": card.question,
                "answer": card.answer,
                "next_review_at": card.next_review_at.isoformat() if card.next_review_at else None,
                "ease_factor": card.ease_factor,
                "interval_days": card.interval_days,
                "review_count": card.review_count,
                "is_flagged": card.is_flagged,
            }
            for card in review_cards
        ],
        "learning_paths": [
            {
                "id": str(path.id),
                "name": path.name,
                "description": path.description,
                "modules": path.modules_json,
                "created_at": path.created_at.isoformat() if path.created_at else None,
            }
            for path in paths
        ],
        "interviews": [
            {
                "id": str(interview.id),
                "title": interview.title,
                "scope": interview.scope,
                "total_score": interview.total_score,
                "summary": interview.summary,
                "status": interview.status,
                "created_at": interview.created_at.isoformat() if interview.created_at else None,
                "finished_at": interview.finished_at.isoformat() if interview.finished_at else None,
                "questions": [
                    {
                        "id": str(question.id),
                        "note_id": str(question.note_id) if question.note_id else None,
                        "question": question.question,
                        "user_answer": question.user_answer,
                        "ai_score": question.ai_score,
                        "ai_feedback": question.ai_feedback,
                    }
                    for question in interview.questions
                ],
            }
            for interview in interviews
        ],
        "import_jobs": [
            {
                "id": str(job.id),
                "source_type": job.source_type,
                "source_url": job.source_url,
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            }
            for job in import_jobs
        ],
    }


async def export_markdown(db: AsyncSession, user_id: uuid.UUID) -> str:
    """导出知识点 Markdown。"""

    notes = await _get_notes(db, user_id)
    lines = ["# KnowBase 知识点导出", ""]
    for note in notes:
        lines.extend(
            [
                f"## {note.title}",
                "",
                f"- 来源：{note.source_type}",
                f"- 掌握度：{note.mastery_level}",
                f"- 标签：{', '.join(tag.name for tag in note.tags) or '无'}",
                "",
                note.content or "",
                "",
            ]
        )
    return "\n".join(lines)


async def export_anki_csv(db: AsyncSession, user_id: uuid.UUID) -> str:
    """导出复习卡片为 Anki 可导入 CSV。"""

    cards = await _get_review_cards(db, user_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["front", "back", "tags"])
    for card in cards:
        note_title = card.note.title if card.note else ""
        writer.writerow([card.question, card.answer, note_title.replace(" ", "_")])
    return buffer.getvalue()


async def _get_notes(db: AsyncSession, user_id: uuid.UUID) -> list[Note]:
    result = await db.execute(
        select(Note)
        .options(selectinload(Note.tags), selectinload(Note.category))
        .where(Note.user_id == user_id)
        .order_by(Note.created_at.asc())
    )
    return list(result.scalars().all())


async def _get_review_cards(db: AsyncSession, user_id: uuid.UUID) -> list[ReviewCard]:
    result = await db.execute(
        select(ReviewCard)
        .join(ReviewCard.note)
        .options(selectinload(ReviewCard.note))
        .where(Note.user_id == user_id)
        .order_by(ReviewCard.created_at.asc())
    )
    return list(result.scalars().all())
