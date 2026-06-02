from sqlalchemy import LargeBinary
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base
from app.models import Conversation, InterviewQuestion, InterviewSession, Message, NoteChunk


def test_note_chunk_table_is_registered():
    note_chunks = Base.metadata.tables["note_chunks"]

    assert NoteChunk.__tablename__ == "note_chunks"
    assert note_chunks.c.note_id.foreign_keys
    assert note_chunks.c.note_id.index is True
    assert note_chunks.c.chunk_index.nullable is False
    assert note_chunks.c.content_hash.type.length == 64
    assert isinstance(note_chunks.c.embedding.type, LargeBinary)
    assert any(constraint.name == "uq_note_chunk_index" for constraint in note_chunks.constraints)


def test_conversation_and_message_tables_are_user_scoped():
    conversations = Base.metadata.tables["conversations"]
    messages = Base.metadata.tables["messages"]

    assert Conversation.__tablename__ == "conversations"
    assert Message.__tablename__ == "messages"
    assert conversations.c.user_id.foreign_keys
    assert conversations.c.user_id.index is True
    assert messages.c.conversation_id.foreign_keys
    assert isinstance(messages.c.sources.type, JSONB)


def test_interview_tables_are_registered_and_user_scoped():
    sessions = Base.metadata.tables["interview_sessions"]
    questions = Base.metadata.tables["interview_questions"]

    assert InterviewSession.__tablename__ == "interview_sessions"
    assert InterviewQuestion.__tablename__ == "interview_questions"
    assert sessions.c.user_id.foreign_keys
    assert sessions.c.user_id.index is True
    assert questions.c.session_id.foreign_keys
    assert questions.c.session_id.index is True
    assert questions.c.reference_answer.nullable is True
