import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.chat import ChatRequest, ConversationCreate, ConversationListItem, ConversationOut
from app.services import chat_service
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/chat", tags=["chat"])


class FeedbackRequest(BaseModel):
    message_id: uuid.UUID
    rating: str = Field(..., pattern="^(helpful|not_helpful)$")
    issue_type: str | None = None
    comment: str | None = None


@router.get("/conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversations = await chat_service.get_conversations(db, current_user.id)
    return success([ConversationListItem.model_validate(item) for item in conversations])


@router.post("/conversations")
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        conversation = await chat_service.create_conversation(db, current_user.id, data.note_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Note not found") from exc
    return success(ConversationOut.model_validate(conversation))


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await chat_service.get_conversation(db, current_user.id, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return success(ConversationOut.model_validate(conversation))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await chat_service.delete_conversation(db, current_user.id, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return success(message="Deleted")


@router.post("/conversations/{conversation_id}/chat")
async def chat(
    request: Request,
    conversation_id: uuid.UUID,
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await chat_service.get_conversation(db, current_user.id, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 捕获用户 LLM 配置（context variable 在 SSE generator 中不可用）
    user_llm = {
        "provider": current_user.llm_provider,
        "api_key": current_user.llm_api_key,
        "model": current_user.llm_model,
    }

    async def event_generator():
        async for chunk in chat_service.chat_stream(db, current_user.id, conversation_id, data.query, user_llm=user_llm):
            if await request.is_disconnected():
                break
            yield {"data": json.dumps({"content": chunk}, ensure_ascii=False)}

        sources = await chat_service.get_latest_assistant_sources(db, conversation_id)
        if not await request.is_disconnected():
            yield {"data": json.dumps({"done": True, "sources": sources}, ensure_ascii=False)}

    return EventSourceResponse(
        event_generator(),
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/messages/{message_id}/save-as-note")
async def save_as_note(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        note = await chat_service.save_message_as_note(db, current_user.id, message_id)
        await db.commit()
        return success({"id": str(note.id), "title": note.title})
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/feedback")
async def submit_feedback(
    data: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    feedback = await chat_service.submit_feedback(
        db, current_user.id, data.message_id, data.rating, data.issue_type, data.comment
    )
    return success({"id": str(feedback.id), "rating": feedback.rating})


@router.get("/feedback/stats")
async def get_feedback_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stats = await chat_service.get_feedback_stats(db, current_user.id)
    return success(stats)
