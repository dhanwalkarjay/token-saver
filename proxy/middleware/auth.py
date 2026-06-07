"""
TokenSaver Enterprise – Authentication Middleware
Validates API keys (master key + team keys), injects team context into
request.state, and caches team lookups in Redis for 5 minutes.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import redis.asyncio as aioredis

from proxy.config import settings
from proxy.core.router.model_router import TeamConfig

logger = logging.getLogger(__name__)

# Endpoints that do NOT require authentication
_PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}
# Redis TTL for cached team lookups (5 minutes)
_TEAM_CACHE_TTL = 300


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that:
    1. Extracts the API key from Authorization or X-API-Key headers.
    2. Validates against the master key or a team key stored in Redis/DB.
    3. Injects ``request.state.team`` (TeamConfig) and
       ``request.state.is_admin`` (bool) for downstream handlers.
    """

    def __init__(self, app, redis_client: aioredis.Redis) -> None:
        super().__init__(app)
        self._redis = redis_client

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip auth for public paths
        if request.url.path in _PUBLIC_PATHS:
            request.state.team = _anonymous_team()
            request.state.is_admin = False
            return await call_next(request)

        api_key = _extract_api_key(request)
        if not api_key:
            return _unauthorized("Missing API key. Provide via Authorization: Bearer <key> or X-API-Key header.")

        # ── Master admin key ─────────────────────────────────────────────
        if api_key == settings.master_api_key:
            request.state.team = _admin_team()
            request.state.is_admin = True
            logger.debug("Admin access granted")
            return await call_next(request)

        # ── Team key lookup ──────────────────────────────────────────────
        team_config = await self._resolve_team(api_key)
        if team_config is None:
            return _unauthorized("Invalid API key.")

        request.state.team = team_config
        request.state.is_admin = False
        logger.debug("Team '%s' authenticated", team_config.team_id)
        return await call_next(request)

    # ── Team resolution ───────────────────────────────────────────────────

    async def _resolve_team(self, api_key: str) -> Optional[TeamConfig]:
        """
        Resolve an API key to a TeamConfig.

        Priority:
        1. Redis cache (5-minute TTL)
        2. PostgreSQL lookup + populate cache
        """
        key_hash = _hash_key(api_key)
        cache_key = f"ts:auth:team:{key_hash}"

        try:
            cached = await self._redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return _dict_to_team_config(data)
        except Exception as exc:
            logger.warning("Redis team cache read error: %s", exc)

        # Fallback: look up in PostgreSQL
        team_config = await self._lookup_team_in_db(api_key, key_hash)
        if team_config:
            try:
                await self._redis.setex(
                    cache_key,
                    _TEAM_CACHE_TTL,
                    json.dumps(_team_config_to_dict(team_config)),
                )
            except Exception as exc:
                logger.warning("Redis team cache write error: %s", exc)

        return team_config

    async def _lookup_team_in_db(
        self, api_key: str, key_hash: str
    ) -> Optional[TeamConfig]:
        """Query PostgreSQL for a matching team record."""
        try:
            from proxy.core.analytics.db import AsyncSessionLocal
            from proxy.core.analytics.db import Team
            from sqlalchemy import select

            async with AsyncSessionLocal() as db:
                # Use prefix index for efficiency before comparing full hash
                prefix = _key_prefix(api_key)
                result = await db.execute(
                    select(Team).where(
                        Team.api_key_prefix == prefix,
                        Team.is_active == True,  # noqa: E712
                    )
                )
                teams = result.scalars().all()

                for team in teams:
                    if _verify_key(api_key, team.api_key_hash):
                        return TeamConfig(
                            team_id=team.id,
                            name=team.name,
                            routing_mode=team.routing_mode,
                            allowed_tiers=list(range(1, team.tier_limit + 1)),
                            monthly_budget_usd=team.monthly_budget_usd,
                            rate_limit_rpm=team.rate_limit_rpm,
                        )
        except Exception as exc:
            logger.error("DB team lookup error: %s", exc)
        return None


# ── FastAPI dependency (for route-level injection) ────────────────────────

async def get_team_from_request(request: Request) -> TeamConfig:
    """
    FastAPI dependency that returns the TeamConfig injected by AuthMiddleware.
    Falls back to an anonymous team if somehow the middleware was bypassed.
    """
    team: Optional[TeamConfig] = getattr(request.state, "team", None)
    if team is None:
        return _anonymous_team()
    return team


# ── Helpers ───────────────────────────────────────────────────────────────

def _extract_api_key(request: Request) -> Optional[str]:
    """
    Extract API key from:
      Authorization: Bearer ts-xxxx
      X-API-Key: ts-xxxx
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    x_api_key = request.headers.get("X-API-Key", "")
    if x_api_key:
        return x_api_key.strip()

    return None


def _hash_key(api_key: str) -> str:
    """SHA-256 hash of the API key for safe storage and lookup."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def _verify_key(api_key: str, stored_hash: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    import hmac
    computed = _hash_key(api_key)
    return hmac.compare_digest(computed, stored_hash)


def _key_prefix(api_key: str) -> str:
    """
    Extract the prefix used for fast DB index lookup.
    Format: "ts-{team_id}-" (first segment before last 32-char random hex).
    """
    parts = api_key.split("-")
    if len(parts) >= 3:
        return f"ts-{parts[1]}-"
    return api_key[:16]


def _unauthorized(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"error": {"message": message, "type": "authentication_error"}},
    )


def _anonymous_team() -> TeamConfig:
    return TeamConfig(team_id="anonymous", name="Anonymous")


def _admin_team() -> TeamConfig:
    return TeamConfig(
        team_id="admin",
        name="Admin",
        routing_mode="auto",
        allowed_tiers=[1, 2, 3],
        monthly_budget_usd=0.0,
        rate_limit_rpm=10_000,
    )


def _team_config_to_dict(tc: TeamConfig) -> dict:
    return {
        "team_id": tc.team_id,
        "name": tc.name,
        "routing_mode": tc.routing_mode,
        "allowed_tiers": tc.allowed_tiers,
        "monthly_budget_usd": tc.monthly_budget_usd,
        "rate_limit_rpm": tc.rate_limit_rpm,
    }


def _dict_to_team_config(data: dict) -> TeamConfig:
    return TeamConfig(
        team_id=data["team_id"],
        name=data.get("name", ""),
        routing_mode=data.get("routing_mode", "auto"),
        allowed_tiers=data.get("allowed_tiers", [1, 2, 3]),
        monthly_budget_usd=data.get("monthly_budget_usd", 0.0),
        rate_limit_rpm=data.get("rate_limit_rpm", 60),
    )
