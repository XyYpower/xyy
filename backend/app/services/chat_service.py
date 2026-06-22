import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload, selectinload

from app.models.chat import Conversation, Message, MessageFeedback
from app.models.note import Note
from app.rag import prompts, retrieval
from app.rag.llm import get_llm

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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
        .options(lazyload(Conversation.messages))
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
    user_llm: dict | None = None,
) -> AsyncGenerator[str, None]:
    conversation = await get_conversation(db, user_id, conversation_id)
    if not conversation:
        raise ValueError("Conversation not found")

    if conversation.title == "新对话":
        conversation.title = query[:80]
    conversation.updated_at = _utc_now()

    user_message = Message(conversation_id=conversation_id, role="user", content=query)
    db.add(user_message)
    await db.flush()

    contexts = await retrieval.search_similar(db, user_id, query, top_k=5)
    rag_messages = prompts.build_rag_messages(query, contexts)
    sources = _build_sources(contexts)

    full_answer = ""
    llm = get_llm(
        user_provider=(user_llm or {}).get("provider"),
        user_api_key=(user_llm or {}).get("api_key"),
        user_model=(user_llm or {}).get("model"),
    )
    if not getattr(llm, "api_key", ""):
        full_answer = _fallback_answer_no_key(query, contexts)
        yield full_answer
    else:
        try:
            async for chunk in llm.chat_stream(rag_messages):
                full_answer += chunk
                yield chunk
        except Exception as exc:
            logger.warning("LLM chat stream failed after %s chars: %s", len(full_answer), exc)
            if not full_answer:
                error_msg = _format_api_error(exc)
                full_answer = error_msg
                yield full_answer

    if not full_answer:
        full_answer = _fallback_answer_no_key(query, contexts)
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


def _fallback_answer_no_key(query: str, contexts: list[dict]) -> str:
    if not contexts:
        return (
            "未配置 LLM API Key，无法调用 AI 模型回答问题。\n\n"
            "请前往 设置 → AI 配置，填入你的 API Key（推荐 DeepSeek 或智谱 GLM）。\n"
            "配置后即可使用 AI 对话、智能生成复习卡片、面试评分等功能。"
        )

    lines = [
        "未配置 LLM API Key，以下是从你的知识库中检索到的相关内容：\n",
    ]
    for ctx in contexts[:3]:
        lines.append("**{}**：{}".format(ctx['note_title'], ctx['chunk_text'][:200]))
    lines.append("\n请前往 设置 → AI 配置 填入 API Key，获取 AI 深度解答。")
    return "\n".join(lines)


def _format_api_error(exc: Exception) -> str:
    """将 API 错误转换为用户友好的提示。"""
    exc_str = str(exc)
    if "429" in exc_str or "Too Many Requests" in exc_str:
        return (
            "AI 请求被限流（429 Too Many Requests）。\n\n"
            "可能原因：免费额度用完了或请求太频繁。\n"
            "解决方案：\n"
            "1. 等几分钟后重试\n"
            "2. 去智谱平台检查余额：https://open.bigmodel.cn\n"
            "3. 换用 DeepSeek（更便宜）：https://platform.deepseek.com"
        )
    if "401" in exc_str or "Unauthorized" in exc_str:
        return "API Key 无效，请前往 设置 → AI 配置 检查并更新你的 API Key。"
    if "404" in exc_str or "Not Found" in exc_str:
        return (
            "API 返回 404，可能是模型名称不正确。\n\n"
            "请前往 设置 → AI 配置 检查模型名称是否是平台支持的模型 ID。\n"
            "智谱可用模型查看：https://open.bigmodel.cn/dev/api"
        )
    return f"AI 调用失败：{exc_str[:200]}\n\n请前往 设置 → AI 配置 检查配置是否正确。"


# -- Save as Note --


async def save_message_as_note(
    db: AsyncSession,
    user_id: uuid.UUID,
    message_id: uuid.UUID,
) -> "Note":
    from app.models.note import Note
    from app.services.note_service import embed_note

    # 找到消息及其所属对话
    msg = (await db.execute(
        select(Message)
        .where(Message.id == message_id, Message.role == "assistant")
    )).scalar_one_or_none()
    if not msg:
        raise ValueError("Message not found or not an assistant message")

    # 校验对话归属
    conv = (await db.execute(
        select(Conversation)
        .where(Conversation.id == msg.conversation_id, Conversation.user_id == user_id)
    )).scalar_one_or_none()
    if not conv:
        raise ValueError("Conversation not found")

    note = Note(
        user_id=user_id,
        title=conv.title[:200],
        content=msg.content,
        source_type="chat",
    )
    db.add(note)
    await db.flush()
    await db.refresh(note)
    await embed_note(db, note)
    return note


# -- Feedback --


async def submit_feedback(
    db: AsyncSession,
    user_id: uuid.UUID,
    message_id: uuid.UUID,
    rating: str,
    issue_type: str | None = None,
    comment: str | None = None,
) -> MessageFeedback:
    feedback = MessageFeedback(
        message_id=message_id,
        user_id=user_id,
        rating=rating,
        issue_type=issue_type,
        comment=comment,
    )
    db.add(feedback)
    await db.flush()
    await db.refresh(feedback)
    return feedback


async def get_feedback_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    total = (await db.execute(
        select(func.count(MessageFeedback.id)).where(MessageFeedback.user_id == user_id)
    )).scalar() or 0

    helpful = (await db.execute(
        select(func.count(MessageFeedback.id)).where(
            MessageFeedback.user_id == user_id, MessageFeedback.rating == "helpful"
        )
    )).scalar() or 0

    return {
        "total": total,
        "helpful": helpful,
        "not_helpful": total - helpful,
        "helpful_rate": round(helpful / total * 100, 1) if total > 0 else 0.0,
    }
