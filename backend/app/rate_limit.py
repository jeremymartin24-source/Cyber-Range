from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    # Production: Redis-backed for distributed rate limiting across workers.
    # Dev/test: in-memory (no Redis required).
    storage_uri=settings.redis_url if settings.is_production else None,
)
