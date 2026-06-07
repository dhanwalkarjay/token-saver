"""
TokenSaver Enterprise – Token Bucket Rate Limiter
Per-team sliding-window rate limiting backed by Redis.
Returns 429 with standard rate-limit headers when exceeded.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import redis.asyncio as aioredis

from proxy.config import settings

logger = logging.getLogger(__name__)

# Paths that skip rate limiting
_EXEMPT_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window counter rate limiter backed by Redis.

    Algorithm
    ---------
    Uses a Redis key ``ts:rl:{team_id}`` as an integer counter that
    expires every 60 seconds.  When the counter exceeds the team's
    configured rpm limit, requests are rejected with HTTP 429.

    Adds rate-limit headers to EVERY response:
      X-RateLimit-Limit    – requests allowed per minute
      X-RateLimit-Remaining – requests remaining this window
      X-RateLimit-Reset    – seconds until the window resets
    """

    def __init__(self, app, redis_client: aioredis.Redis) -> None:
        super().__init__(app)
        self._redis = redis_client

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        team = getattr(request.state, "team", None)
        team_id = team.team_id if team else "anonymous"
        limit = (
            team.rate_limit_rpm
            if team and team.rate_limit_rpm > 0
            else settings.rate_limit_requests_per_minute
        )

        allowed, remaining, reset_in = await self._check_rate_limit(team_id, limit)

        if not allowed:
            logger.warning("Rate limit exceeded for team=%s", team_id)
            return _rate_limited_response(limit, 0, reset_in)

        response = await call_next(request)

        # Inject headers into every response
        response.headers["X-RateLimit-Limit"]     = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"]      = str(reset_in)
        return response

    # ── Redis counter ──────────────────────────────────────────────────────

    async def _check_rate_limit(
        self,
        team_id: str,
        limit: int,
    ) -> tuple[bool, int, int]:
        """
        Increment the sliding-window counter and check against the limit.

        Returns (allowed, remaining, seconds_until_reset).
        """
        key = f"ts:rl:{team_id}"
        window = 60  # seconds

        try:
            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            results = await pipe.execute()

            count: int = results[0]
            ttl: int   = results[1]

            # If this is the first request in the window, set TTL
            if ttl == -1:
                await self._redis.expire(key, window)
                ttl = window

            reset_in = max(1, ttl)
            remaining = max(0, limit - count)
            allowed = count <= limit
            return allowed, remaining, reset_in

        except Exception as exc:
            # Redis unavailable → fail open (allow request, log warning)
            logger.warning(
                "Rate limiter Redis error for team=%s: %s – failing open", team_id, exc
            )
            return True, limit, window


# ── Response helpers ──────────────────────────────────────────────────────

def _rate_limited_response(limit: int, remaining: int, reset_in: int) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "message": (
                    f"Rate limit exceeded. Allowed {limit} requests/minute. "
                    f"Retry after {reset_in} seconds."
                ),
                "type": "rate_limit_error",
            }
        },
        headers={
            "X-RateLimit-Limit":     str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset":     str(reset_in),
            "Retry-After":           str(reset_in),
        },
    )
