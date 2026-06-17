"""
Brute-force lockout: tracks consecutive failed logins per email in Redis.
After MAX_ATTEMPTS failures within the window, subsequent attempts are blocked
for LOCKOUT_SECONDS regardless of password correctness.
"""

import redis.asyncio as aioredis

from app.config import settings

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 900  # 15-minute sliding window for failure count
LOCKOUT_SECONDS = 900  # same window: lock out for 15 minutes

_KEY = "lockout:failed:{}"


async def _redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def record_failed(email: str) -> int:
    """Increment failure counter; returns new count."""
    r = await _redis()
    key = _KEY.format(email.lower())
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, WINDOW_SECONDS)
    results = await pipe.execute()
    await r.aclose()
    return results[0]


async def is_locked(email: str) -> bool:
    r = await _redis()
    key = _KEY.format(email.lower())
    val = await r.get(key)
    await r.aclose()
    return int(val or 0) >= MAX_ATTEMPTS


async def clear(email: str) -> None:
    r = await _redis()
    await r.delete(_KEY.format(email.lower()))
    await r.aclose()
