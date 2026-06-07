"""
TokenSaver Enterprise – FastAPI Application Entrypoint
Configures middleware stack, routers, lifespan events, and global error handling.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from proxy.config import settings
from proxy.core.analytics.db import close_db, init_db
from proxy.core.cache.cache_manager import CacheManager
from proxy.routers import admin, chat

# ── Logging configuration ─────────────────────────────────────────────────
_LOG_LEVEL = logging.DEBUG if settings.debug else logging.INFO

logging.basicConfig(
    level=_LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
    stream=sys.stdout,
)

# Audit logger: outputs raw JSON lines (no timestamp prefix)
_audit_handler = logging.StreamHandler(sys.stdout)
_audit_handler.setFormatter(logging.Formatter("%(message)s"))
_audit_logger = logging.getLogger("tokensaver.audit")
_audit_logger.handlers = [_audit_handler]
_audit_logger.propagate = False

logger = logging.getLogger(__name__)


# ── Lazy Redis-aware middleware base ──────────────────────────────────────
# Starlette creates middleware instances at startup before the lifespan
# context runs.  We use app.state to share the live Redis client lazily.

class _LazyRedisMiddleware(BaseHTTPMiddleware):
    """Base class that reads the live Redis client from app.state at request time."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    def _get_redis(self, request: Request) -> aioredis.Redis:
        return request.app.state.redis  # type: ignore[return-value]


# ── Auth middleware ───────────────────────────────────────────────────────

class _AuthMiddleware(_LazyRedisMiddleware):
    """
    Validates API keys and injects team context into request.state.
    Thin wrapper around the logic in proxy.middleware.auth.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        from proxy.middleware.auth import (
            _PUBLIC_PATHS,
            _anonymous_team,
            _admin_team,
            _extract_api_key,
            _unauthorized,
        )
        from proxy.middleware.auth import AuthMiddleware as _AuthImpl

        if request.url.path in _PUBLIC_PATHS:
            request.state.team = _anonymous_team()
            request.state.is_admin = False
            return await call_next(request)

        api_key = _extract_api_key(request)
        if not api_key:
            return _unauthorized(
                "Missing API key. Provide via Authorization: Bearer <key> or X-API-Key header."
            )

        if api_key == settings.master_api_key:
            request.state.team = _admin_team()
            request.state.is_admin = True
            return await call_next(request)

        # Use a temporary AuthMiddleware instance for team resolution logic
        impl = _AuthImpl.__new__(_AuthImpl)
        impl._redis = self._get_redis(request)
        team_config = await impl._resolve_team(api_key)
        if team_config is None:
            return _unauthorized("Invalid API key.")

        request.state.team = team_config
        request.state.is_admin = False
        return await call_next(request)


# ── Rate limiter middleware ───────────────────────────────────────────────

class _RateLimiterMiddleware(_LazyRedisMiddleware):
    """Token-bucket rate limiter reading Redis from app.state."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        from proxy.middleware.rate_limiter import (
            _EXEMPT_PATHS,
            _rate_limited_response,
        )
        from proxy.middleware.rate_limiter import RateLimiterMiddleware as _RLImpl

        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        team = getattr(request.state, "team", None)
        team_id = team.team_id if team else "anonymous"
        limit = (
            team.rate_limit_rpm
            if team and team.rate_limit_rpm > 0
            else settings.rate_limit_requests_per_minute
        )

        impl = _RLImpl.__new__(_RLImpl)
        impl._redis = self._get_redis(request)
        allowed, remaining, reset_in = await impl._check_rate_limit(team_id, limit)

        if not allowed:
            logger.warning("Rate limit exceeded for team=%s", team_id)
            return _rate_limited_response(limit, 0, reset_in)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"]     = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"]      = str(reset_in)
        return response


# ── Audit logger middleware ───────────────────────────────────────────────

class _AuditLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        from proxy.middleware.audit_logger import AuditLoggerMiddleware as _ALImpl

        impl = _ALImpl.__new__(_ALImpl)
        return await _ALImpl.dispatch(impl, request, call_next)


# ── Application lifespan ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup and shutdown sequence.

    Startup:
      1. Connect to Redis
      2. Initialise PostgreSQL schema
      3. Initialise L2 semantic cache (loads the embedding model)

    Shutdown:
      1. Close Redis connection pool
      2. Dispose SQLAlchemy engine
    """
    logger.info("Starting %s v%s …", settings.app_name, settings.version)

    # ── Redis ──────────────────────────────────────────────────────────────
    redis_client: aioredis.Redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30,
    )
    try:
        await redis_client.ping()
        logger.info("Redis connected: %s", settings.redis_url)
    except Exception as exc:
        logger.warning("Redis not reachable at startup: %s – continuing anyway", exc)

    # Expose the live client via app.state (middleware reads it lazily)
    app.state.redis = redis_client

    # ── Cache manager ──────────────────────────────────────────────────────
    cache_manager = CacheManager(redis_client)
    await cache_manager.initialize()
    app.state.cache_manager = cache_manager

    # ── PostgreSQL ─────────────────────────────────────────────────────────
    try:
        await init_db()
    except Exception as exc:
        logger.warning("DB init failed: %s – analytics will be disabled", exc)

    logger.info("%s is ready ✓", settings.app_name)
    yield  # ← Application runs here

    # ── Shutdown ───────────────────────────────────────────────────────────
    logger.info("Shutting down %s …", settings.app_name)
    try:
        await redis_client.aclose()
        logger.info("Redis connection closed.")
    except Exception as exc:
        logger.warning("Error closing Redis: %s", exc)

    try:
        await close_db()
    except Exception as exc:
        logger.warning("Error closing DB: %s", exc)


# ── FastAPI application ───────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    description=(
        "Intelligent LLM Cost Optimization Middleware.\n\n"
        "TokenSaver Enterprise sits between your application and LLM providers, "
        "automatically applying caching, prompt compression, and intelligent model "
        "routing to minimise costs while maintaining response quality."
    ),
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-TokenSaver-Cache-Hit",
        "X-TokenSaver-Cache-Level",
        "X-TokenSaver-Model-Used",
        "X-TokenSaver-Model-Requested",
        "X-TokenSaver-Cost-USD",
        "X-TokenSaver-Savings-USD",
        "X-TokenSaver-Savings-Percent",
        "X-TokenSaver-Latency-Ms",
        "X-TokenSaver-Input-Tokens",
        "X-TokenSaver-Output-Tokens",
        "X-TokenSaver-Similarity-Score",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-Request-Id",
    ],
)

# Middleware registration (Starlette executes in LIFO order — last added = outermost)
# Desired execution order (outer → inner):
#   Audit Logger → Rate Limiter → Auth → Routes
# Registration order (innermost first → outermost last):
app.add_middleware(_AuthMiddleware)          # innermost custom MW
app.add_middleware(_RateLimiterMiddleware)
app.add_middleware(_AuditLoggerMiddleware)   # outermost custom MW

# ── Routers ───────────────────────────────────────────────────────────────
app.include_router(chat.router, tags=["Chat Completions"])
app.include_router(admin.router, tags=["Admin & Management"])


# ── Global exception handlers ─────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all that returns a consistent JSON error envelope."""
    logger.exception(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "An internal server error occurred.",
                "type": "internal_server_error",
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Any) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "message": (
                    f"Endpoint not found: {request.method} {request.url.path}"
                ),
                "type": "not_found",
            }
        },
    )


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "proxy.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
        access_log=False,   # We use our structured audit logger instead
    )
