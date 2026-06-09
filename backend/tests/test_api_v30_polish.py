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
        pytest.skip(f"database is not available for V3.0 API test: {exc}")


async def _cleanup_users(usernames: list[str]) -> None:
    async with async_session() as session:
        result = await session.execute(select(User.id).where(User.username.in_(usernames)))
        user_ids = result.scalars().all()
        if user_ids:
            await session.execute(delete(User).where(User.id.in_(user_ids)))
            await session.commit()


async def _register(client: AsyncClient, username: str, password: str = "secret123") -> str:
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_category_crud_is_user_scoped_and_delete_clears_note_category():
    await _require_database()
    suffix = uuid.uuid4().hex[:10]
    owner_username = f"v30_cat_owner_{suffix}"
    other_username = f"v30_cat_other_{suffix}"

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            owner_token = await _register(client, owner_username)
            other_token = await _register(client, other_username)
            owner_headers = _auth_header(owner_token)

            create_category = await client.post(
                "/api/v1/categories",
                headers=owner_headers,
                json={"name": "后端开发", "description": "服务端知识"},
            )
            assert create_category.status_code == 200, create_category.text
            category = create_category.json()["data"]

            other_categories = await client.get("/api/v1/categories", headers=_auth_header(other_token))
            assert other_categories.status_code == 200, other_categories.text
            assert other_categories.json()["data"] == []

            create_note = await client.post(
                "/api/v1/notes",
                headers=owner_headers,
                json={
                    "title": "分类归属验证",
                    "content": "分类只能使用当前用户自己的分类。",
                    "category_id": category["id"],
                },
            )
            assert create_note.status_code == 200, create_note.text
            note_id = create_note.json()["data"]["id"]
            assert create_note.json()["data"]["category"]["id"] == category["id"]

            update_category = await client.put(
                f"/api/v1/categories/{category['id']}",
                headers=owner_headers,
                json={"name": "后端工程", "sort_order": 3},
            )
            assert update_category.status_code == 200, update_category.text
            assert update_category.json()["data"]["name"] == "后端工程"

            filtered_notes = await client.get(
                "/api/v1/notes",
                headers=owner_headers,
                params={"category_id": category["id"]},
            )
            assert filtered_notes.status_code == 200, filtered_notes.text
            assert filtered_notes.json()["data"]["total"] == 1

            cross_user_note = await client.post(
                "/api/v1/notes",
                headers=_auth_header(other_token),
                json={
                    "title": "非法分类",
                    "content": "不允许绑定其他用户的分类。",
                    "category_id": category["id"],
                },
            )
            assert cross_user_note.status_code == 404

            delete_category = await client.delete(f"/api/v1/categories/{category['id']}", headers=owner_headers)
            assert delete_category.status_code == 200, delete_category.text

            note_response = await client.get(f"/api/v1/notes/{note_id}", headers=owner_headers)
            assert note_response.status_code == 200, note_response.text
            assert note_response.json()["data"]["category"] is None
    finally:
        await _cleanup_users([owner_username, other_username])


async def test_profile_and_password_settings_update_current_user():
    await _require_database()
    suffix = uuid.uuid4().hex[:10]
    username = f"v30_settings_{suffix}"

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await _register(client, username, "oldpass123")
            headers = _auth_header(token)

            profile_response = await client.put(
                "/api/v1/auth/profile",
                headers=headers,
                json={
                    "email": f"{username}@example.com",
                    "reminder_enabled": True,
                    "reminder_time": "09:30",
                },
            )
            assert profile_response.status_code == 200, profile_response.text
            profile = profile_response.json()["data"]
            assert profile["email"] == f"{username}@example.com"
            assert profile["reminder_enabled"] is True
            assert profile["reminder_time"] == "09:30:00"

            wrong_password = await client.put(
                "/api/v1/auth/password",
                headers=headers,
                json={"old_password": "wrongpass", "new_password": "newpass123"},
            )
            assert wrong_password.status_code == 400

            password_response = await client.put(
                "/api/v1/auth/password",
                headers=headers,
                json={"old_password": "oldpass123", "new_password": "newpass123"},
            )
            assert password_response.status_code == 200, password_response.text

            old_login = await client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": "oldpass123"},
            )
            assert old_login.status_code == 401

            new_login = await client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": "newpass123"},
            )
            assert new_login.status_code == 200, new_login.text
    finally:
        await _cleanup_users([username])


async def test_notes_can_be_filtered_by_favorite_state():
    await _require_database()
    suffix = uuid.uuid4().hex[:10]
    username = f"v30_fav_{suffix}"

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await _register(client, username)
            headers = _auth_header(token)

            for title, is_favorite in [("收藏知识点", True), ("普通知识点", False)]:
                response = await client.post(
                    "/api/v1/notes",
                    headers=headers,
                    json={
                        "title": title,
                        "content": f"{title} 内容",
                        "is_favorite": is_favorite,
                    },
                )
                assert response.status_code == 200, response.text

            favorites = await client.get("/api/v1/notes", headers=headers, params={"is_favorite": True})
            assert favorites.status_code == 200, favorites.text
            payload = favorites.json()["data"]
            assert payload["total"] == 1
            assert payload["items"][0]["title"] == "收藏知识点"
            assert payload["items"][0]["is_favorite"] is True
    finally:
        await _cleanup_users([username])
