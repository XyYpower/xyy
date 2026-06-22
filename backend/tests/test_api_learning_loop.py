import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text

from app.database import async_session
from app.main import app
from app.models.user import User


pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _require_database() -> None:
    try:
        async with async_session() as session:
            await session.execute(text("select 1"))
    except Exception as exc:
        pytest.skip(f"database is not available for API integration test: {exc}")


async def _cleanup_users(usernames: list[str]) -> None:
    async with async_session() as session:
        result = await session.execute(select(User.id).where(User.username.in_(usernames)))
        user_ids = result.scalars().all()
        if user_ids:
            await session.execute(delete(User).where(User.id.in_(user_ids)))
            await session.commit()


async def _register(client: AsyncClient, username: str) -> str:
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "secret123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_api_learning_loop_creates_owned_cards_and_submits_review():
    await _require_database()
    suffix = uuid.uuid4().hex[:10]
    owner_username = f"api_owner_{suffix}"
    other_username = f"api_other_{suffix}"

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            owner_token = await _register(client, owner_username)
            other_token = await _register(client, other_username)

            create_response = await client.post(
                "/api/v1/notes",
                headers=_auth_header(owner_token),
                json={
                    "title": "Python async await",
                    "content": "async def 用于定义协程，await 会让出事件循环控制权。",
                    "tag_names": ["python", "asyncio"],
                },
            )
            assert create_response.status_code == 200, create_response.text
            note_id = create_response.json()["data"]["id"]

            cards_response = await client.get(
                f"/api/v1/review/cards/{note_id}",
                headers=_auth_header(owner_token),
            )
            assert cards_response.status_code == 200, cards_response.text
            cards = cards_response.json()["data"]
            assert {card["card_type"] for card in cards} == {"concept", "code", "scenario"}

            other_cards_response = await client.get(
                f"/api/v1/review/cards/{note_id}",
                headers=_auth_header(other_token),
            )
            assert other_cards_response.status_code == 200, other_cards_response.text
            assert other_cards_response.json()["data"] == []

            submit_response = await client.post(
                "/api/v1/review/submit",
                headers=_auth_header(owner_token),
                json={"card_id": cards[0]["id"], "quality": 5},
            )
            assert submit_response.status_code == 200, submit_response.text
            reviewed_card = submit_response.json()["data"]
            assert reviewed_card["interval_days"] == 1
            assert reviewed_card["review_count"] == 1
            assert reviewed_card["next_review_at"] is not None

            stats_response = await client.get("/api/v1/review/stats", headers=_auth_header(owner_token))
            assert stats_response.status_code == 200, stats_response.text
            stats = stats_response.json()["data"]
            assert stats["total_cards"] == 3
            assert stats["due_today"] == 2
            assert stats["learning_count"] == 1

            other_notes_response = await client.get("/api/v1/notes", headers=_auth_header(other_token))
            assert other_notes_response.status_code == 200, other_notes_response.text
            assert other_notes_response.json()["data"]["total"] == 0
    finally:
        await _cleanup_users([owner_username, other_username])


async def test_tag_and_category_list_require_auth_and_tags_are_user_scoped():
    await _require_database()
    suffix = uuid.uuid4().hex[:10]
    owner_username = f"tag_owner_{suffix}"
    other_username = f"tag_other_{suffix}"

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            assert (await client.get("/api/v1/tags")).status_code == 401
            assert (await client.get("/api/v1/categories")).status_code == 401

            owner_token = await _register(client, owner_username)
            other_token = await _register(client, other_username)

            create_response = await client.post(
                "/api/v1/notes",
                headers=_auth_header(owner_token),
                json={
                    "title": "SQLAlchemy relationship",
                    "content": "relationship 用于描述 ORM 对象之间的关联。",
                    "tag_names": ["owner-only-tag"],
                },
            )
            assert create_response.status_code == 200, create_response.text

            owner_tags = (
                await client.get("/api/v1/tags", headers=_auth_header(owner_token))
            ).json()["data"]
            assert [tag["name"] for tag in owner_tags] == ["owner-only-tag"]

            other_tags = (
                await client.get("/api/v1/tags", headers=_auth_header(other_token))
            ).json()["data"]
            assert other_tags == []
    finally:
        await _cleanup_users([owner_username, other_username])


async def test_import_text_api_creates_drafts_and_confirms_selected_notes():
    await _require_database()
    suffix = uuid.uuid4().hex[:10]
    username = f"import_api_{suffix}"

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await _register(client, username)
            headers = _auth_header(token)

            response = await client.post(
                "/api/v1/import/text",
                headers=headers,
                json={
                    "text": (
                        "缓存穿透是查询不存在的数据导致请求打到数据库。\n\n"
                        "布隆过滤器可以提前判断 key 是否可能存在。"
                    )
                },
            )
            assert response.status_code == 200, response.text
            payload = response.json()["data"]
            job_id = payload["job"]["id"]
            drafts = payload["drafts"]
            assert payload["job"]["status"] == "draft"
            assert len(drafts) == 2

            update_response = await client.put(
                f"/api/v1/import/drafts/{drafts[1]['id']}",
                headers=headers,
                json={"title": "布隆过滤器方案", "is_selected": False},
            )
            assert update_response.status_code == 200, update_response.text
            assert update_response.json()["data"]["is_selected"] is False

            confirm_response = await client.post(f"/api/v1/import/jobs/{job_id}/confirm", headers=headers)
            assert confirm_response.status_code == 200, confirm_response.text
            notes = confirm_response.json()["data"]
            assert len(notes) == 1
            assert notes[0]["source_type"] == "imported"

            cards_response = await client.get(f"/api/v1/review/cards/{notes[0]['id']}", headers=headers)
            assert cards_response.status_code == 200, cards_response.text
            assert len(cards_response.json()["data"]) == 3
    finally:
        await _cleanup_users([username])
