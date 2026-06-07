"""
TokenSaver Enterprise – Cost Tracker
Real-time cost calculation, savings tracking, and PostgreSQL persistence.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from proxy.core.analytics.db import ApiRequest
from proxy.core.router.model_catalog import MODEL_CATALOG

logger = logging.getLogger(__name__)


# ── Result dataclasses ────────────────────────────────────────────────────

@dataclass
class SavingsResult:
    original_cost: float
    actual_cost: float
    saved_amount: float
    saved_percent: float
    cache_hit: bool
    routing_savings: bool   # True when a cheaper model was substituted


@dataclass
class TeamStats:
    team_id: str
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    total_savings_usd: float
    cache_hit_rate: float
    avg_latency_ms: float
    top_models: list[dict[str, Any]]


@dataclass
class GlobalStats:
    total_requests: int
    total_teams: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    total_savings_usd: float
    cache_hit_rate: float
    avg_latency_ms: float
    top_models: list[dict[str, Any]]


# ── Cost calculation ──────────────────────────────────────────────────────

def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """
    Calculate the USD cost for a completed request.

    Returns 0.0 for unknown models (so unknown models don't block requests).
    """
    info = MODEL_CATALOG.get(model)
    if info is None:
        logger.debug("Unknown model for cost calculation: %s", model)
        return 0.0

    input_cost  = (input_tokens  / 1_000_000) * info["input_per_mtok"]
    output_cost = (output_tokens / 1_000_000) * info["output_per_mtok"]
    return round(input_cost + output_cost, 8)


def calculate_savings(
    original_model: str,
    used_model: str,
    input_tokens: int,
    output_tokens: int,
    cache_hit: bool = False,
) -> SavingsResult:
    """
    Compare costs of the originally-requested model vs the model actually used.

    When *cache_hit* is True the actual cost is 0 (we served from cache).
    """
    original_cost = calculate_cost(original_model, input_tokens, output_tokens)

    if cache_hit:
        actual_cost = 0.0
    else:
        actual_cost = calculate_cost(used_model, input_tokens, output_tokens)

    saved_amount = max(0.0, original_cost - actual_cost)
    saved_percent = (
        round(saved_amount / original_cost * 100, 2) if original_cost > 0 else 0.0
    )
    routing_savings = (not cache_hit) and (used_model != original_model) and saved_amount > 0

    return SavingsResult(
        original_cost=round(original_cost, 8),
        actual_cost=round(actual_cost, 8),
        saved_amount=round(saved_amount, 8),
        saved_percent=saved_percent,
        cache_hit=cache_hit,
        routing_savings=routing_savings,
    )


# ── Persistence ───────────────────────────────────────────────────────────

async def track_request(
    team_id: str,
    model_requested: str,
    model_used: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    savings_usd: float,
    cache_hit: bool,
    cache_level: str,
    routing_tier: int,
    latency_ms: int,
    request_hash: str,
    db: AsyncSession,
) -> None:
    """
    Persist request analytics to PostgreSQL.
    This function is called fire-and-forget; errors are logged, not raised.
    """
    try:
        record = ApiRequest(
            team_id=team_id,
            timestamp=datetime.now(tz=timezone.utc),
            model_requested=model_requested,
            model_used=model_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            savings_usd=savings_usd,
            cache_hit=cache_hit,
            cache_level=cache_level,
            routing_tier=routing_tier,
            latency_ms=latency_ms,
            request_hash=request_hash,
        )
        db.add(record)
        await db.commit()
        logger.debug(
            "Tracked request team=%s model=%s cost=$%.6f saved=$%.6f",
            team_id,
            model_used,
            cost_usd,
            savings_usd,
        )
    except Exception as exc:
        logger.error("Failed to track request analytics: %s", exc)
        await db.rollback()


# ── Aggregate statistics ──────────────────────────────────────────────────

async def get_team_stats(
    team_id: str,
    days: int = 30,
    db: AsyncSession = None,  # type: ignore[assignment]
) -> TeamStats:
    """
    Return aggregated statistics for a single team over the last *days* days.
    """
    try:
        from datetime import timedelta
        from sqlalchemy import and_

        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)

        base_filter = and_(
            ApiRequest.team_id == team_id,
            ApiRequest.timestamp >= cutoff,
        )

        # Scalar aggregates
        agg_result = await db.execute(
            select(
                func.count(ApiRequest.id).label("total_requests"),
                func.sum(ApiRequest.input_tokens).label("total_input_tokens"),
                func.sum(ApiRequest.output_tokens).label("total_output_tokens"),
                func.sum(ApiRequest.cost_usd).label("total_cost_usd"),
                func.sum(ApiRequest.savings_usd).label("total_savings_usd"),
                func.avg(ApiRequest.latency_ms).label("avg_latency_ms"),
                func.sum(
                    func.cast(ApiRequest.cache_hit, type_=None)
                ).label("cache_hits"),
            ).where(base_filter)
        )
        row = agg_result.one()

        total_requests = row.total_requests or 0
        cache_hits = row.cache_hits or 0
        cache_hit_rate = (cache_hits / total_requests) if total_requests > 0 else 0.0

        # Top models by request count
        model_result = await db.execute(
            select(
                ApiRequest.model_used,
                func.count(ApiRequest.id).label("request_count"),
                func.sum(ApiRequest.cost_usd).label("cost_usd"),
            )
            .where(base_filter)
            .group_by(ApiRequest.model_used)
            .order_by(func.count(ApiRequest.id).desc())
            .limit(5)
        )
        top_models = [
            {
                "model": r.model_used,
                "requests": r.request_count,
                "cost_usd": round(float(r.cost_usd or 0), 4),
            }
            for r in model_result.all()
        ]

        return TeamStats(
            team_id=team_id,
            total_requests=total_requests,
            total_input_tokens=int(row.total_input_tokens or 0),
            total_output_tokens=int(row.total_output_tokens or 0),
            total_cost_usd=round(float(row.total_cost_usd or 0), 6),
            total_savings_usd=round(float(row.total_savings_usd or 0), 6),
            cache_hit_rate=round(cache_hit_rate, 4),
            avg_latency_ms=round(float(row.avg_latency_ms or 0), 1),
            top_models=top_models,
        )
    except Exception as exc:
        logger.error("Failed to get team stats for %s: %s", team_id, exc)
        return TeamStats(
            team_id=team_id,
            total_requests=0,
            total_input_tokens=0,
            total_output_tokens=0,
            total_cost_usd=0.0,
            total_savings_usd=0.0,
            cache_hit_rate=0.0,
            avg_latency_ms=0.0,
            top_models=[],
        )


async def get_global_stats(
    days: int = 30,
    db: AsyncSession = None,  # type: ignore[assignment]
) -> GlobalStats:
    """
    Return aggregated statistics across all teams for the last *days* days.
    """
    try:
        from datetime import timedelta

        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        base_filter = ApiRequest.timestamp >= cutoff

        agg_result = await db.execute(
            select(
                func.count(ApiRequest.id).label("total_requests"),
                func.count(func.distinct(ApiRequest.team_id)).label("total_teams"),
                func.sum(ApiRequest.input_tokens).label("total_input_tokens"),
                func.sum(ApiRequest.output_tokens).label("total_output_tokens"),
                func.sum(ApiRequest.cost_usd).label("total_cost_usd"),
                func.sum(ApiRequest.savings_usd).label("total_savings_usd"),
                func.avg(ApiRequest.latency_ms).label("avg_latency_ms"),
                func.sum(
                    func.cast(ApiRequest.cache_hit, type_=None)
                ).label("cache_hits"),
            ).where(base_filter)
        )
        row = agg_result.one()

        total_requests = row.total_requests or 0
        cache_hits = row.cache_hits or 0
        cache_hit_rate = (cache_hits / total_requests) if total_requests > 0 else 0.0

        model_result = await db.execute(
            select(
                ApiRequest.model_used,
                func.count(ApiRequest.id).label("request_count"),
                func.sum(ApiRequest.cost_usd).label("cost_usd"),
            )
            .where(base_filter)
            .group_by(ApiRequest.model_used)
            .order_by(func.count(ApiRequest.id).desc())
            .limit(10)
        )
        top_models = [
            {
                "model": r.model_used,
                "requests": r.request_count,
                "cost_usd": round(float(r.cost_usd or 0), 4),
            }
            for r in model_result.all()
        ]

        return GlobalStats(
            total_requests=total_requests,
            total_teams=int(row.total_teams or 0),
            total_input_tokens=int(row.total_input_tokens or 0),
            total_output_tokens=int(row.total_output_tokens or 0),
            total_cost_usd=round(float(row.total_cost_usd or 0), 6),
            total_savings_usd=round(float(row.total_savings_usd or 0), 6),
            cache_hit_rate=round(cache_hit_rate, 4),
            avg_latency_ms=round(float(row.avg_latency_ms or 0), 1),
            top_models=top_models,
        )
    except Exception as exc:
        logger.error("Failed to get global stats: %s", exc)
        return GlobalStats(
            total_requests=0,
            total_teams=0,
            total_input_tokens=0,
            total_output_tokens=0,
            total_cost_usd=0.0,
            total_savings_usd=0.0,
            cache_hit_rate=0.0,
            avg_latency_ms=0.0,
            top_models=[],
        )
