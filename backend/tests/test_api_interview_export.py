import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text

from app.database import async_session
from app.main import app
from app.models.user import User
from app.services import interview_service


pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _require_database() -> None:
    try:
        async with async_session() as session:
            await session.execute(text("select 1"))
    except Exception as exc:
        pytest.skip(f"database is not available for interview/export API test: {exc}")


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


async def test_interview_api_lifecycle_and_exports(monkeypatch):
    await _require_database()
    username = f"api_interview_{uuid.uuid4().hex[:10]}"

    async def fake_generate(topics, num_questions=5):
        return [{"question": f"第 {index + 1} 题", "reference_answer": "参考答案"} for index in range(num_questions)]

    async def fake_evaluate(question, answer, reference=None):
        return {"score": 7, "feedback": "回答方向正确。"}

    async def fake_summary(questions):
        return "整体表现稳定，建议补充细节。"

    monkeypatch.setattr(interview_service.interviewer, "generate_interview_questions", fake_generate)
    monkeypatch.setattr(interview_service.interviewer, "evaluate_answer", fake_evaluate)
    monkeypatch.setattr(interview_service.interviewer, "generate_session_summary", fake_summary)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await _register(client, username)
            headers = _auth_header(token)

            note_response = await client.post(
                "/api/v1/notes",
                headers=headers,
                json={"title": "JWT 认证", "content": "JWT 包含 header、payload、signature。"},
            )
            assert note_response.status_code == 200, note_response.text

            start_response = await client.post(
                "/api/v1/interview/start",
                headers=headers,
                json={"scope": "all", "num_questions": 2},
            )
            assert start_response.status_code == 200, start_response.text
            interview = start_response.json()["data"]
            assert len(interview["questions"]) == 2
            assert interview["questions"][0]["reference_answer"] == "参考答案"

            first_question = interview["questions"][0]
            answer_response = await client.post(
                f"/api/v1/interview/{interview['id']}/answer/{first_question['id']}",
                headers=headers,
                json={"answer": "我会说明 token 结构、签名校验和刷新机制。"},
            )
            assert answer_response.status_code == 200, answer_response.text
            assert answer_response.json()["data"]["ai_score"] == 7

            finish_response = await client.post(f"/api/v1/interview/{interview['id']}/finish", headers=headers)
            assert finish_response.status_code == 200, finish_response.text
            finished = finish_response.json()["data"]
            assert finished["status"] == "completed"
            assert finished["summary"] == "整体表现稳定，建议补充细节。"
            assert finished["score_percent"] == 35

            sessions_response = await client.get("/api/v1/interview/sessions", headers=headers)
            assert sessions_response.status_code == 200, sessions_response.text
            assert len(sessions_response.json()["data"]) == 1

            json_export = await client.get("/api/v1/export/json", headers=headers)
            assert json_export.status_code == 200, json_export.text
            assert json_export.json()["notes"][0]["title"] == "JWT 认证"
            assert json_export.json()["interviews"][0]["status"] == "completed"

            markdown_export = await client.get("/api/v1/export/markdown", headers=headers)
            assert markdown_export.status_code == 200, markdown_export.text
            assert "## JWT 认证" in markdown_export.text
    finally:
        await _cleanup_users([username])
