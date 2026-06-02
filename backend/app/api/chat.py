import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.chat import ChatRequest, ConversationCreate, ConversationOut
from app.services import chat_service
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversations = await chat_service.get_conversations(db, current_user.id)
    return success([ConversationOut.model_validate(item) for item in conversations])


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
    conversation_id: uuid.UUID,
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await chat_service.get_conversation(db, current_user.id, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    async def event_generator():
        async for chunk in chat_service.chat_stream(db, current_user.id, conversation_id, data.query):
            yield _sse({"content": chunk})

        sources = await chat_service.get_latest_assistant_sources(db, conversation_id)
        yield _sse({"done": True, "sources": sources})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
