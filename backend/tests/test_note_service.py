import uuid

import pytest

from app.schemas.note import NoteCreate
from app.services import note_service


pytestmark = pytest.mark.asyncio


class FakeSession:
    def __init__(self):
        self.added = []
        self.flushed = 0
        self.refreshed = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed += 1
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()

    async def refresh(self, obj):
        self.refreshed.append(obj)


async def test_create_note_persists_note_without_inline_card_generation(monkeypatch):
    async def no_tags(db, tag_names):
        return []

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("card generation should run in a background task")

    monkeypatch.setattr(note_service, "_get_or_create_tags", no_tags)
    monkeypatch.setattr(note_service.review_service, "generate_cards_for_note", fail_if_called)
    session = FakeSession()
    user_id = uuid.uuid4()

    note = await note_service.create_note(
        session,  # type: ignore[arg-type]
        NoteCreate(title="FastAPI BackgroundTasks", content="后台任务不应该阻塞创建知识点。"),
        user_id,
    )

    assert note.user_id == user_id
    assert note.title == "FastAPI BackgroundTasks"
    assert session.flushed == 1
    assert session.refreshed == [note]
