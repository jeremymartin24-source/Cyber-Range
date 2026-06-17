import uuid
from fastapi import Depends, HTTPException, Cookie, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import auth_service
from app.crud import user as user_crud
from app.models.user import User, UserRole

security = HTTPBearer(auto_error=False)


async def _extract_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    access_token: str | None = Cookie(default=None),
) -> str:
    token = None
    if credentials:
        token = credentials.credentials
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


async def get_current_user(
    token: str = Depends(_extract_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        if await auth_service.is_token_denylisted(token):
            raise credentials_exception
        payload = auth_service.decode_token(token)
        if payload.get("type") != auth_service.TOKEN_TYPE_ACCESS:
            raise credentials_exception
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise credentials_exception

    db_user = await user_crud.get(db, id=user_id)
    if not db_user or not db_user.is_active:
        raise credentials_exception

    return db_user


def require_roles(*roles: UserRole):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return role_checker


require_admin = require_roles(UserRole.admin)
require_instructor = require_roles(UserRole.admin, UserRole.instructor)
