import uuid
from contextvars import ContextVar

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth_service import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# 用户级 LLM 配置上下文，供 get_llm() 读取
_user_llm_provider: ContextVar[str | None] = ContextVar("_user_llm_provider", default=None)
_user_llm_api_key: ContextVar[str | None] = ContextVar("_user_llm_api_key", default=None)
_user_llm_model: ContextVar[str | None] = ContextVar("_user_llm_model", default=None)


def get_user_llm_config() -> tuple[str | None, str | None, str | None]:
    """获取当前请求用户的 LLM 配置。"""
    return _user_llm_provider.get(), _user_llm_api_key.get(), _user_llm_model.get()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    subject = payload.get("sub")
    try:
        user_id = uuid.UUID(str(subject))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject") from exc

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # 设置用户级 LLM 配置到上下文
    _user_llm_provider.set(user.llm_provider)
    _user_llm_api_key.set(user.llm_api_key)
    _user_llm_model.set(user.llm_model)
    return user
