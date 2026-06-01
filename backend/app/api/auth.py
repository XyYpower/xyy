from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserOut
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

