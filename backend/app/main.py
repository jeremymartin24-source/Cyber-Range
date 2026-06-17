import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import uuid
import time

from app.config import settings
from app.rate_limit import limiter
from app.api.v1.router import router

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer() if settings.is_production else structlog.dev.ConsoleRenderer(),
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", environment=settings.environment)
    yield
    logger.info("shutdown")


app = FastAPI(
    title="CyberOps Range API",
    version="0.1.0",
    # Disable interactive docs in production — reduces attack surface
    docs_url=None if settings.is_production else "/api/docs",
    redoc_url=None if settings.is_production else "/api/redoc",
    openapi_url=None if settings.is_production else "/api/openapi.json",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-XSS-Protection"] = "0"  # modern browsers use CSP instead
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    return response


@app.middleware("http")
async def request_id_and_logging(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration_ms,
        request_id=request_id,
    )
    return response


@app.get("/api/health", tags=["health"])
async def health():
    return {"status": "ok", "environment": settings.environment}


app.include_router(router)
