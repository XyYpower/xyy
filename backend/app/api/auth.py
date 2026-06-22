from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateLLMSettingsRequest,
    UpdateProfileRequest,
    UserOut,
)
from app.services import auth_service
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register(db, data.username, data.password, data.email)
    access_token = auth_service.create_access_token(str(user.id))
    refresh_token = auth_service.create_refresh_token(str(user.id))
    return success(TokenResponse(access_token=access_token, refresh_token=refresh_token, user=UserOut.model_validate(user)))


@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user, access_token, refresh_token = await auth_service.login(db, data.username, data.password)
    return success(TokenResponse(access_token=access_token, refresh_token=refresh_token, user=UserOut.model_validate(user)))


@router.post("/refresh")
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    access_token = auth_service.refresh_access_token(data.refresh_token)
    # 刷新后补充 user，便于前端同步状态。
    payload = auth_service.decode_token(access_token)
    user = await db.get(User, payload["sub"])
    return success(TokenResponse(access_token=access_token, refresh_token=data.refresh_token, user=UserOut.model_validate(user)))


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return success(UserOut.model_validate(current_user))


@router.put("/profile")
async def update_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.email is not None:
        current_user.email = data.email
    if data.reminder_enabled is not None:
        current_user.reminder_enabled = data.reminder_enabled
    if data.reminder_time is not None:
        try:
            current_user.reminder_time = datetime.strptime(data.reminder_time, "%H:%M").time()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="reminder_time must be HH:MM",
            ) from exc

    await db.flush()
    await db.commit()
    await db.refresh(current_user)
    return success(UserOut.model_validate(current_user))


@router.put("/password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not auth_service.verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码错误")

    current_user.password_hash = auth_service.hash_password(data.new_password)
    await db.flush()
    await db.commit()
    return success(message="密码已修改")


@router.put("/llm-settings")
async def update_llm_settings(
    data: UpdateLLMSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.llm_provider is not None:
        current_user.llm_provider = data.llm_provider
    if data.llm_api_key is not None:
        current_user.llm_api_key = data.llm_api_key.strip() or None
    if data.llm_model is not None:
        current_user.llm_model = data.llm_model.strip() or None
    await db.flush()
    await db.commit()
    await db.refresh(current_user)
    return success(UserOut.model_validate(current_user))
