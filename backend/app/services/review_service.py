import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.note import Note
from app.models.review import ReviewCard, ReviewRecord
from app.rag.card_generator import generate_cards
from app.database import async_session


@dataclass(frozen=True)
class ReviewSchedule:
    next_review_at: datetime
    ease_factor: float
    interval_days: int
    review_count: int


def _utc_now() -> datetime:
    """返回 UTC 时间，保持数据库当前 naive timestamp 存储格式。"""
    return datetime.now(UTC).replace(tzinfo=None)


def calculate_next_review(
    quality: int,
    ease_factor: float,
    interval_days: int,
    review_count: int,
) -> ReviewSchedule:
    """计算 SM-2 下一次复习时间。"""

    if quality < 0 or quality > 5:
        raise ValueError("quality must be between 0 and 5")

    if quality < 3:
        new_interval = 1
        new_review_count = 0
    else:
        if review_count == 0:
            new_interval = 1
        elif review_count == 1:
            new_interval = 6
        else:
            new_interval = max(1, round(interval_days * ease_factor))
        new_review_count = review_count + 1

    new_ease = max(1.3, ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return ReviewSchedule(
        next_review_at=_utc_now() + timedelta(days=new_interval),
        ease_factor=new_ease,
        interval_days=new_interval,
        review_count=new_review_count,
    )


async def get_today_cards(db: AsyncSession, user_id: uuid.UUID) -> list[ReviewCard]:
    now = _utc_now()
    result = await db.execute(
        select(ReviewCard)
        .join(ReviewCard.note)
        .options(selectinload(ReviewCard.note))
        .where(Note.user_id == user_id)
        .where((ReviewCard.next_review_at.is_(None)) | (ReviewCard.next_review_at <= now))
        .order_by(ReviewCard.next_review_at.asc().nullsfirst(), ReviewCard.created_at.asc())
    )
    return result.unique().scalars().all()


async def get_cards_for_note(db: AsyncSession, user_id: uuid.UUID, note_id: uuid.UUID) -> list[ReviewCard]:
    result = await db.execute(
        select(ReviewCard)
        .join(ReviewCard.note)
        .where(Note.id == note_id, Note.user_id == user_id)
        .order_by(ReviewCard.created_at.asc())
    )
    return result.scalars().all()


async def submit_review(db: AsyncSession, user_id: uuid.UUID, card_id: uuid.UUID, quality: int) -> ReviewCard:
    result = await db.execute(
        select(ReviewCard)
        .join(ReviewCard.note)
        .where(ReviewCard.id == card_id, Note.user_id == user_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review card not found")

    schedule = calculate_next_review(quality, card.ease_factor, card.interval_days, card.review_count)
    card.next_review_at = schedule.next_review_at
    card.ease_factor = schedule.ease_factor
    card.interval_days = schedule.interval_days
    card.review_count = schedule.review_count
    card.last_reviewed_at = _utc_now()

    db.add(ReviewRecord(card_id=card.id, quality=quality))
    await db.flush()
    await db.refresh(card)
    await update_note_mastery(db, card.note_id)
    return card


async def update_note_mastery(db: AsyncSession, note_id: uuid.UUID) -> None:
    result = await db.execute(select(ReviewCard).where(ReviewCard.note_id == note_id))
    cards = result.scalars().all()
    note = await db.get(Note, note_id)
    if not note:
        return
    if cards and all(card.review_count >= 3 and card.ease_factor >= 2.3 for card in cards):
        note.mastery_level = 2
    elif any(card.review_count > 0 for card in cards):
        note.mastery_level = 1
    else:
        note.mastery_level = 0


async def get_review_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    now = _utc_now()
    total_cards = (
        await db.execute(select(func.count()).select_from(ReviewCard).join(ReviewCard.note).where(Note.user_id == user_id))
    ).scalar() or 0
    due_today = (
        await db.execute(
            select(func.count())
            .select_from(ReviewCard)
            .join(ReviewCard.note)
            .where(Note.user_id == user_id)
            .where((ReviewCard.next_review_at.is_(None)) | (ReviewCard.next_review_at <= now))
        )
    ).scalar() or 0
    mastered_count = (
        await db.execute(select(func.count()).select_from(Note).where(Note.user_id == user_id, Note.mastery_level == 2))
    ).scalar() or 0
    learning_count = (
        await db.execute(select(func.count()).select_from(Note).where(Note.user_id == user_id, Note.mastery_level == 1))
    ).scalar() or 0
    new_count = (
        await db.execute(select(func.count()).select_from(Note).where(Note.user_id == user_id, Note.mastery_level == 0))
    ).scalar() or 0
    return {
        "total_cards": total_cards,
        "due_today": due_today,
        "mastered_count": mastered_count,
        "learning_count": learning_count,
        "new_count": new_count,
    }


async def generate_cards_for_note(db: AsyncSession, user_id: uuid.UUID, note_id: uuid.UUID) -> list[ReviewCard]:
    note = (
        await db.execute(select(Note).where(Note.id == note_id, Note.user_id == user_id))
    ).scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    existing = await get_cards_for_note(db, user_id, note_id)
    if existing:
        return existing

    card_payloads = await generate_cards(note.title, note.content)
    cards = [
        ReviewCard(
            note_id=note.id,
            card_type=payload["card_type"],
            question=payload["question"],
            answer=payload["answer"],
        )
        for payload in card_payloads
    ]
    db.add_all(cards)
    await db.flush()
    for card in cards:
        await db.refresh(card)
    return cards


async def generate_cards_for_note_task(user_id: uuid.UUID, note_id: uuid.UUID) -> None:
    """后台生成复习卡片，避免创建知识点接口被 LLM 调用阻塞。"""
    async with async_session() as db:
        try:
            await generate_cards_for_note(db, user_id, note_id)
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def edit_card(
    db: AsyncSession,
    user_id: uuid.UUID,
    card_id: uuid.UUID,
    question: str,
    answer: str,
) -> ReviewCard:
    card = await _get_owned_card(db, user_id, card_id)
    card.question = question
    card.answer = answer
    card.is_user_edited = True
    await db.flush()
    await db.refresh(card)
    return card


async def flag_card(db: AsyncSession, user_id: uuid.UUID, card_id: uuid.UUID) -> ReviewCard:
    card = await _get_owned_card(db, user_id, card_id)
    card.is_flagged = True
    await db.flush()
    await db.refresh(card)
    return card


async def _get_owned_card(db: AsyncSession, user_id: uuid.UUID, card_id: uuid.UUID) -> ReviewCard:
    result = await db.execute(
        select(ReviewCard)
        .join(ReviewCard.note)
        .where(ReviewCard.id == card_id, Note.user_id == user_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review card not found")
    return card
