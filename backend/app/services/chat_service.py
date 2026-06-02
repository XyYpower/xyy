import logging
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import Conversation, Message
from app.models.note import Note
from app.rag import prompts, retrieval
from app.rag.llm import get_llm

logger = logging.getLogger(__name__)


async def create_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    note_id: uuid.UUID | None = None,
) -> Conversation:
    title = "新对话"
    if note_id:
        note = (
            await db.execute(select(Note).where(Note.id == note_id, Note.user_id == user_id))
        ).scalar_one_or_none()
        if not note:
            raise ValueError("Note not found")
        title = note.title[:200]

    conversation = Conversation(user_id=user_id, note_id=note_id, title=title)
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)
    return conversation


async def get_conversations(db: AsyncSession, user_id: uuid.UUID) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> Conversation | None:
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def delete_conversation(db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID) -> bool:
    conversation = await get_conversation(db, user_id, conversation_id)
    if not conversation:
        return False
    await db.delete(conversation)
    await db.flush()
    return True


async def chat_stream(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    query: str,
) -> AsyncGenerator[str, None]:
    conversation = await get_conversation(db, user_id, conversation_id)
    if not conversation:
        raise ValueError("Conversation not found")

    if conversation.title == "新对话":
        conversation.title = query[:80]

    user_message = Message(conversation_id=conversation_id, role="user", content=query)
    db.add(user_message)
    await db.flush()

    contexts = await retrieval.search_similar(db, user_id, query, top_k=5)
    rag_messages = prompts.build_rag_messages(query, contexts)
    sources = _build_sources(contexts)

    full_answer = ""
    llm = get_llm()
    if not getattr(llm, "api_key", ""):
        full_answer = _fallback_answer(query, contexts)
        yield full_answer
    else:
        try:
            async for chunk in llm.chat_stream(rag_messages):
                full_answer += chunk
                yield chunk
        except Exception as exc:
            logger.warning("LLM chat stream failed, using fallback answer: %s", exc)
            full_answer = _fallback_answer(query, contexts)
            yield full_answer

    if not full_answer:
        full_answer = _fallback_answer(query, contexts)
        yield full_answer

    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=full_answer,
        sources=sources,
    )
    db.add(assistant_message)
    await db.flush()


async def get_latest_assistant_sources(
    db: AsyncSession,
    conversation_id: uuid.UUID,
) -> list[dict]:
    result = await db.execute(
        select(Message.sources)
        .where(Message.conversation_id == conversation_id, Message.role == "assistant")
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none() or []


def _build_sources(contexts: list[dict]) -> list[dict]:
    seen: set[str] = set()
    sources: list[dict] = []
    for context in contexts:
        note_id = str(context["note_id"])
        if note_id in seen:
            continue
        seen.add(note_id)
        sources.append({"note_id": note_id, "title": context["note_title"]})
    return sources


def _fallback_answer(query: str, contexts: list[dict]) -> str:
    if not contexts:
        return f"我没有找到和“{query}”相关的知识库内容。你可以先补充相关知识点，再来继续追问。"

    lines = ["我找到了这些相关知识点，可以先基于它们帮你梳理："]
    for context in contexts[:3]:
        lines.append(f"- {context['note_title']}：{context['chunk_text'][:160]}")
    lines.append("当前未配置可用的 LLM API key，所以这是本地兜底摘要。")
    return "\n".join(lines)
