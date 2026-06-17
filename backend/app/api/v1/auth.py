from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
import uuid

from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse, RefreshResponse
from app.schemas.user import UserResponse, PasswordChange
from app.crud import user as user_crud
from app.services import auth_service
from app.dependencies.auth import get_current_user, _extract_token
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_OPTS = {
    "httponly": True,
    "samesite": "strict",
    "secure": False,  # set True in production behind HTTPS
}


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    db_user = await user_crud.get_by_email(db, email=body.email)
    if not db_user or not user_crud.verify_password(body.password, db_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not db_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    access_token = auth_service.create_access_token(db_user.id, db_user.role.value)
    refresh_token = auth_service.create_refresh_token(db_user.id)

    await user_crud.record_login(db, obj=db_user)

    response.set_cookie("access_token", access_token, max_age=15 * 60, **COOKIE_OPTS)
    response.set_cookie(
        "refresh_token",
        refresh_token,
        max_age=7 * 24 * 60 * 60,
        **COOKIE_OPTS,
    )

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(db_user),
    )


@router.post("/logout")
async def logout(
    response: Response,
    token: str = Depends(_extract_token),
):
    await auth_service.denylist_token(token)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

    try:
        payload = auth_service.decode_token(refresh_token)
        if payload.get("type") != auth_service.TOKEN_TYPE_REFRESH:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    db_user = await user_crud.get(db, id=user_id)
    if not db_user or not db_user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = auth_service.create_access_token(db_user.id, db_user.role.value)
    response.set_cookie("access_token", access_token, max_age=15 * 60, **COOKIE_OPTS)

    return RefreshResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.put("/me/password")
async def change_password(
    body: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user_crud.verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    await user_crud.update_password(db, obj=current_user, new_password=body.new_password)
    return {"message": "Password updated successfully"}
