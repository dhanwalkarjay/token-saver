"""
TokenSaver Enterprise – Admin & Management Router
All endpoints here require the master API key (enforced by AuthMiddleware).

Endpoints:
  GET  /health                     – health check (public)
  GET  /v1/stats                   – global aggregate stats
  GET  /v1/stats/teams/{team_id}   – per-team stats
  POST /v1/teams                   – create a new team
  GET  /v1/teams                   – list all teams
  DELETE /v1/cache                 – flush L1 + L2 cache
  GET  /v1/models                  – list all models with pricing
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from proxy.core.analytics.cost_tracker import get_global_stats, get_team_stats
from proxy.core.analytics.db import Team, get_db
from proxy.core.cache.cache_manager import CacheManager
from proxy.core.router.model_catalog import list_all_models
from proxy.middleware.auth import get_team_from_request
from proxy.core.router.model_router import TeamConfig

logger = logging.getLogger(__name__)
router = APIRouter()

# Application startup time (for uptime calculation)
_START_TIME = time.monotonic()


# ── Request/Response schemas ──────────────────────────────────────────────

class CreateTeamRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    tier_limit: int = Field(3, ge=1, le=3)
    monthly_budget_usd: float = Field(0.0, ge=0.0)
    rate_limit_rpm: int = Field(60, ge=1, le=10_000)
    routing_mode: str = Field("auto", pattern="^(auto|cheap|balanced|premium|disabled)$")


# ── Dependency: require admin ─────────────────────────────────────────────

async def require_admin(
    raw_request: Request,
    team: TeamConfig = Depends(get_team_from_request),
) -> TeamConfig:
    """FastAPI dependency that enforces admin access."""
    is_admin = getattr(raw_request.state, "is_admin", False)
    if not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required. Use the master API key.",
        )
    return team


# ── Health check (public) ─────────────────────────────────────────────────

@router.get("/health", response_model=None)
async def health_check(raw_request: Request) -> JSONResponse:
    """
    Public health check endpoint.
    Returns cache and DB connectivity status.
    """
    from proxy.config import settings

    uptime = int(time.monotonic() - _START_TIME)
    cache_mgr: Optional[CacheManager] = getattr(raw_request.app.state, "cache_manager", None)

    # Check Redis connectivity
    cache_status = "unavailable"
    if cache_mgr:
        try:
            await cache_mgr._redis.ping()
            cache_status = "ok"
        except Exception:
            cache_status = "error"

    # Check DB connectivity
    db_status = "unavailable"
    try:
        from proxy.core.analytics.db import engine
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return JSONResponse(
        content={
            "status": "ok",
            "version": settings.version,
            "uptime_seconds": uptime,
            "cache_status": cache_status,
            "database_status": db_status,
            "cache_stats": cache_mgr.get_stats() if cache_mgr else {},
        }
    )


# ── Global stats ──────────────────────────────────────────────────────────

@router.get("/v1/stats", response_model=None)
async def global_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _admin: TeamConfig = Depends(require_admin),
) -> JSONResponse:
    """
    Return aggregated analytics across all teams.
    Query param: ?days=30 (default 30 days lookback).
    """
    stats = await get_global_stats(days=days, db=db)
    cache_mgr_stats: dict[str, Any] = {}

    return JSONResponse(
        content={
            "period_days": days,
            "total_requests": stats.total_requests,
            "total_teams": stats.total_teams,
            "total_input_tokens": stats.total_input_tokens,
            "total_output_tokens": stats.total_output_tokens,
            "total_cost_usd": stats.total_cost_usd,
            "total_savings_usd": stats.total_savings_usd,
            "cache_hit_rate": stats.cache_hit_rate,
            "avg_latency_ms": stats.avg_latency_ms,
            "top_models": stats.top_models,
        }
    )


# ── Per-team stats ────────────────────────────────────────────────────────

@router.get("/v1/stats/teams/{team_id}", response_model=None)
async def team_stats(
    team_id: str,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _admin: TeamConfig = Depends(require_admin),
) -> JSONResponse:
    """Return analytics for a specific team."""
    stats = await get_team_stats(team_id=team_id, days=days, db=db)
    return JSONResponse(
        content={
            "team_id": stats.team_id,
            "period_days": days,
            "total_requests": stats.total_requests,
            "total_input_tokens": stats.total_input_tokens,
            "total_output_tokens": stats.total_output_tokens,
            "total_cost_usd": stats.total_cost_usd,
            "total_savings_usd": stats.total_savings_usd,
            "cache_hit_rate": stats.cache_hit_rate,
            "avg_latency_ms": stats.avg_latency_ms,
            "top_models": stats.top_models,
        }
    )


# ── Team management ───────────────────────────────────────────────────────

@router.post("/v1/teams", status_code=201, response_model=None)
async def create_team(
    body: CreateTeamRequest,
    db: AsyncSession = Depends(get_db),
    _admin: TeamConfig = Depends(require_admin),
) -> JSONResponse:
    """
    Create a new team and return its API key.

    The API key is only returned ONCE at creation time.
    It is stored as a SHA-256 hash in the database.
    """
    team_id = str(uuid.uuid4())
    # API key format: ts-{team_id_short}-{random_hex_32}
    random_hex = secrets.token_hex(16)    # 32 chars
    short_id = team_id.replace("-", "")[:8]
    api_key = f"ts-{short_id}-{random_hex}"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    api_key_prefix = f"ts-{short_id}-"

    new_team = Team(
        id=team_id,
        name=body.name,
        api_key_hash=api_key_hash,
        api_key_prefix=api_key_prefix,
        tier_limit=body.tier_limit,
        monthly_budget_usd=body.monthly_budget_usd,
        rate_limit_rpm=body.rate_limit_rpm,
        routing_mode=body.routing_mode,
        created_at=datetime.now(tz=timezone.utc),
        is_active=True,
    )
    db.add(new_team)
    await db.commit()
    await db.refresh(new_team)

    logger.info("Created team id=%s name='%s'", team_id, body.name)

    return JSONResponse(
        status_code=201,
        content={
            "team_id": team_id,
            "name": body.name,
            "api_key": api_key,  # Only returned once!
            "tier_limit": body.tier_limit,
            "monthly_budget_usd": body.monthly_budget_usd,
            "rate_limit_rpm": body.rate_limit_rpm,
            "routing_mode": body.routing_mode,
            "created_at": new_team.created_at.isoformat(),
            "warning": "Save this API key — it will not be shown again.",
        },
    )


@router.get("/v1/teams", response_model=None)
async def list_teams(
    db: AsyncSession = Depends(get_db),
    _admin: TeamConfig = Depends(require_admin),
) -> JSONResponse:
    """List all teams (without API keys)."""
    result = await db.execute(select(Team).order_by(Team.created_at.desc()))
    teams = result.scalars().all()
    return JSONResponse(
        content={
            "teams": [
                {
                    "team_id": t.id,
                    "name": t.name,
                    "tier_limit": t.tier_limit,
                    "monthly_budget_usd": t.monthly_budget_usd,
                    "rate_limit_rpm": t.rate_limit_rpm,
                    "routing_mode": t.routing_mode,
                    "is_active": t.is_active,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in teams
            ],
            "total": len(teams),
        }
    )


@router.delete("/v1/teams/{team_id}", response_model=None)
async def deactivate_team(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: TeamConfig = Depends(require_admin),
) -> JSONResponse:
    """Deactivate a team (soft delete — sets is_active=False)."""
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if team is None:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found.")
    team.is_active = False
    await db.commit()
    logger.info("Deactivated team id=%s", team_id)
    return JSONResponse(content={"message": f"Team '{team_id}' deactivated."})


# ── Cache management ──────────────────────────────────────────────────────

@router.delete("/v1/cache", response_model=None)
async def flush_cache(
    raw_request: Request,
    _admin: TeamConfig = Depends(require_admin),
) -> JSONResponse:
    """Flush both L1 (exact) and L2 (semantic) caches."""
    cache_mgr: Optional[CacheManager] = getattr(raw_request.app.state, "cache_manager", None)
    if cache_mgr is None:
        raise HTTPException(status_code=503, detail="Cache manager not available.")

    counts = await cache_mgr.flush()
    logger.info("Cache flushed by admin: %s", counts)
    return JSONResponse(
        content={
            "message": "Cache flushed successfully.",
            "deleted": counts,
        }
    )


# ── Model catalog ─────────────────────────────────────────────────────────

@router.get("/v1/models", response_model=None)
async def get_models() -> JSONResponse:
    """List all supported models with their pricing and tier information."""
    models = list_all_models()
    return JSONResponse(
        content={
            "object": "list",
            "data": models,
            "total": len(models),
        }
    )
