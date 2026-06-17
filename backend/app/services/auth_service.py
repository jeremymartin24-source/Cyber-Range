import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
from jose import JWTError, jwt

from app.config import settings

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    expire = datetime.now(UTC) + expires_delta
    payload = {
        "sub": subject,
        "type": token_type,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    return _create_token(
        subject=str(user_id),
        token_type=TOKEN_TYPE_ACCESS,
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(
        subject=str(user_id),
        token_type=TOKEN_TYPE_REFRESH,
        expires_delta=timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


async def get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def denylist_token(token: str) -> None:
    """Add an access token to the Redis denylist until it expires."""
    try:
        payload = decode_token(token)
        exp = payload.get("exp")
        if exp:
            ttl = int(exp - datetime.now(UTC).timestamp())
            if ttl > 0:
                r = await get_redis()
                await r.setex(f"denylist:{token}", ttl, "1")
                await r.aclose()
    except JWTError:
        pass


async def is_token_denylisted(token: str) -> bool:
    r = await get_redis()
    result = await r.exists(f"denylist:{token}")
    await r.aclose()
    return bool(result)
