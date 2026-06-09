import uuid
import hashlib
from fastapi import HTTPException, status
from sqlalchemy import delete, select, func, or_, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import NoteChunk
from app.models.note import Note, Category, Tag, note_tags
from app.schemas.note import CategoryCreate, CategoryUpdate, NoteCreate, NoteUpdate
from app.services import review_service
from app.rag import embedding


async def create_note(db: AsyncSession, data: NoteCreate, user_id: uuid.UUID) -> Note:
    await _ensure_category_owned(db, user_id, data.category_id)
    tags = await _get_or_create_tags(db, data.tag_names)
    note = Note(
        user_id=user_id,
        title=data.title,
        content=data.content,
        summary=data.summary,
        category_id=data.category_id,
        is_favorite=data.is_favorite,
        mastery_level=data.mastery_level,
        source_type=data.source_type,
        source_url=data.source_url,
        tags=tags,
    )
    db.add(note)
    await db.flush()
    await db.refresh(note)
    await embed_note(db, note)
    return note


async def get_notes(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    category_id: uuid.UUID | None = None,
    tag_id: uuid.UUID | None = None,
    mastery_level: int | None = None,
    source_type: str | None = None,
    is_favorite: bool | None = None,
) -> tuple[list[Note], int]:
    query = select(Note).options(selectinload(Note.category), selectinload(Note.tags)).where(Note.user_id == user_id)

    if keyword:
        query = query.where(or_(
            Note.title.ilike(f"%{keyword}%"),
            Note.content.ilike(f"%{keyword}%"),
        ))
    if category_id:
        query = query.where(Note.category_id == category_id)
    if tag_id:
        query = query.join(note_tags).where(note_tags.c.tag_id == tag_id)
    if mastery_level is not None:
        query = query.where(Note.mastery_level == mastery_level)
    if source_type:
        query = query.where(Note.source_type == source_type)
    if is_favorite is not None:
        query = query.where(Note.is_favorite == is_favorite)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Note.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.unique().scalars().all(), total


async def get_note(db: AsyncSession, note_id: uuid.UUID, user_id: uuid.UUID) -> Note | None:
    result = await db.execute(
        select(Note)
        .options(selectinload(Note.category), selectinload(Note.tags))
        .where(Note.id == note_id, Note.user_id == user_id)
    )
    return result.unique().scalar_one_or_none()


async def update_note(db: AsyncSession, note: Note, data: NoteUpdate) -> Note:
    update_data = data.model_dump(exclude_unset=True, exclude={"tag_names"})
    if "category_id" in update_data:
        await _ensure_category_owned(db, note.user_id, update_data["category_id"])

    for field, value in update_data.items():
        setattr(note, field, value)

    if data.tag_names is not None:
        note.tags = await _get_or_create_tags(db, data.tag_names)

    await db.flush()
    await db.refresh(note)
    if any(field in update_data for field in ("title", "content")):
        await embed_note(db, note)
    return note


async def delete_note(db: AsyncSession, note: Note) -> None:
    await db.delete(note)
    await db.flush()


async def get_categories_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[Category]:
    result = await db.execute(
        select(Category)
        .where(Category.user_id == user_id)
        .order_by(Category.sort_order.asc(), Category.name.asc())
    )
    return result.scalars().all()


async def get_category_for_user(db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID) -> Category | None:
    result = await db.execute(select(Category).where(Category.id == category_id, Category.user_id == user_id))
    return result.scalar_one_or_none()


async def create_category(db: AsyncSession, user_id: uuid.UUID, data: CategoryCreate) -> Category:
    category = Category(user_id=user_id, **data.model_dump())
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def update_category(
    db: AsyncSession,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    data: CategoryUpdate,
) -> Category:
    category = await get_category_for_user(db, user_id, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    await db.flush()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID) -> None:
    category = await get_category_for_user(db, user_id, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")

    await db.execute(
        update(Note)
        .where(Note.user_id == user_id, Note.category_id == category_id)
        .values(category_id=None)
    )
    await db.delete(category)
    await db.flush()


def split_note_text(text: str, max_chunk_size: int = 500) -> list[str]:
    clean = text.strip()
    if not clean:
        return []
    if len(clean) <= max_chunk_size:
        return [clean]

    chunks: list[str] = []
    current = ""
    for paragraph in [part.strip() for part in clean.split("\n\n") if part.strip()]:
        if len(current) + len(paragraph) + 2 > max_chunk_size and current:
            chunks.append(current.strip())
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph
    if current.strip():
        chunks.append(current.strip())
    return chunks


async def embed_note(db: AsyncSession, note: Note) -> None:
    source_text = f"{note.title}\n\n{note.content}".strip()
    chunks = split_note_text(source_text)

    vectors = await embedding.embed_texts(chunks)

    async with db.begin_nested():
        await db.execute(delete(NoteChunk).where(NoteChunk.note_id == note.id))
        await db.flush()

        for index, (chunk_text, vector) in enumerate(zip(chunks, vectors, strict=True)):
            await db.execute(
                text(
                    """
                    INSERT INTO note_chunks (id, note_id, chunk_index, chunk_text, content_hash, embedding)
                    VALUES (:id, :note_id, :chunk_index, :chunk_text, :content_hash, CAST(:embedding AS vector))
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "note_id": note.id,
                    "chunk_index": index,
                    "chunk_text": chunk_text,
                    "content_hash": hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
                    "embedding": embedding.vector_to_sql(vector),
                },
            )
    await db.flush()


async def get_tags_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[Tag]:
    result = await db.execute(
        select(Tag)
        .join(note_tags, note_tags.c.tag_id == Tag.id)
        .join(Note, Note.id == note_tags.c.note_id)
        .where(Note.user_id == user_id)
        .distinct()
        .order_by(Tag.name)
    )
    return result.scalars().all()


async def _ensure_category_owned(
    db: AsyncSession,
    user_id: uuid.UUID,
    category_id: uuid.UUID | None,
) -> None:
    if category_id is None:
        return
    category = await get_category_for_user(db, user_id, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")


async def _get_or_create_tags(db: AsyncSession, tag_names: list[str]) -> list[Tag]:
    if not tag_names:
        return []
    result = await db.execute(select(Tag).where(Tag.name.in_(tag_names)))
    existing = {t.name: t for t in result.scalars().all()}

    tags = []
    for name in tag_names:
        if name in existing:
            tags.append(existing[name])
        else:
            tag = Tag(name=name)
            db.add(tag)
            tags.append(tag)
    await db.flush()
    return tags
