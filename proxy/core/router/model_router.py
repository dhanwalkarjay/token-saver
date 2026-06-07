"""
TokenSaver Enterprise – Model Router
Selects the most cost-effective model for each request based on:
  - Routing mode (auto / cheap / balanced / premium / disabled)
  - Complexity classification
  - Team tier restrictions
  - Explicit model override headers
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal, Optional

from proxy.core.router.complexity_classifier import classify_complexity
from proxy.core.router.model_catalog import (
    DEFAULT_TIER_MODELS,
    MODEL_CATALOG,
    estimate_cost_per_1k_tokens,
    get_cheapest_model_in_tier,
    get_model_info,
)

logger = logging.getLogger(__name__)

RoutingMode = Literal["auto", "cheap", "balanced", "premium", "disabled"]


# ── Team configuration (injected by auth middleware) ──────────────────────

@dataclass
class TeamConfig:
    """Per-team routing and access configuration."""

    team_id: str
    name: str = ""
    routing_mode: RoutingMode = "auto"
    allowed_tiers: list[int] = None          # type: ignore[assignment]
    monthly_budget_usd: float = 0.0          # 0 = unlimited
    rate_limit_rpm: int = 60

    def __post_init__(self) -> None:
        if self.allowed_tiers is None:
            self.allowed_tiers = [1, 2, 3]   # All tiers allowed by default


# ── Result dataclass ──────────────────────────────────────────────────────

@dataclass
class RoutingResult:
    selected_model: str
    original_model: str
    tier: int
    complexity_score: int
    complexity_reason: str
    estimated_cost_per_1k_tokens: float
    estimated_savings_percent: float


# ── Router ────────────────────────────────────────────────────────────────

async def route(
    messages: list[dict[str, Any]],
    requested_model: str,
    team_config: TeamConfig,
    routing_mode: Optional[RoutingMode] = None,
    model_override: Optional[str] = None,
) -> RoutingResult:
    """
    Select the best model for the request.

    Parameters
    ----------
    messages:
        The chat message list (used for complexity classification).
    requested_model:
        Model explicitly requested by the client.
    team_config:
        Per-team settings injected by the auth middleware.
    routing_mode:
        Override for the routing strategy; falls back to team_config if None.
    model_override:
        Explicit model from X-TokenSaver-Model-Override header (highest priority).

    Returns
    -------
    RoutingResult with the selected model and cost/savings estimates.
    """
    # ── Honour explicit model override ────────────────────────────────────
    if model_override and model_override in MODEL_CATALOG:
        info = get_model_info(model_override)
        selected = model_override
        tier = info["tier"] if info else 2
        c_score, c_reason = 50, "model override by header"
        logger.debug("Using model override: %s", selected)
        return _build_result(
            selected_model=selected,
            original_model=requested_model,
            tier=tier,
            score=c_score,
            reason=c_reason,
        )

    # ── Determine effective routing mode ─────────────────────────────────
    effective_mode: RoutingMode = routing_mode or team_config.routing_mode

    # ── "disabled" – use the requested model as-is ────────────────────────
    if effective_mode == "disabled":
        info = get_model_info(requested_model)
        tier = info["tier"] if info else 2
        return _build_result(
            selected_model=requested_model,
            original_model=requested_model,
            tier=tier,
            score=50,
            reason="routing disabled",
        )

    # ── Classify prompt complexity ────────────────────────────────────────
    complexity = classify_complexity(messages)

    # ── Map routing mode to a tier ────────────────────────────────────────
    target_tier: int
    if effective_mode == "cheap":
        target_tier = 1
    elif effective_mode == "balanced":
        target_tier = 2
    elif effective_mode == "premium":
        target_tier = 3
    else:
        # "auto" – use the classifier's tier
        target_tier = complexity.tier

    # ── Respect team tier restrictions ───────────────────────────────────
    allowed = team_config.allowed_tiers or [1, 2, 3]
    if target_tier not in allowed:
        # Clamp to the highest allowed tier
        target_tier = max(t for t in allowed if t <= target_tier) if any(
            t <= target_tier for t in allowed
        ) else min(allowed)
        logger.debug(
            "Clamped to tier %d due to team restriction (allowed=%s)",
            target_tier,
            allowed,
        )

    # ── Select the best model for the chosen tier ─────────────────────────
    # Prefer the requested model if it already matches the target tier
    req_info = get_model_info(requested_model)
    if req_info and req_info["tier"] == target_tier:
        selected = requested_model
    else:
        selected = get_cheapest_model_in_tier(target_tier)

    logger.info(
        "Routing: %s → %s (tier=%d score=%d reason=%s)",
        requested_model,
        selected,
        target_tier,
        complexity.score,
        complexity.reason,
    )

    return _build_result(
        selected_model=selected,
        original_model=requested_model,
        tier=target_tier,
        score=complexity.score,
        reason=complexity.reason,
    )


# ── Helpers ───────────────────────────────────────────────────────────────

def _build_result(
    selected_model: str,
    original_model: str,
    tier: int,
    score: int,
    reason: str,
) -> RoutingResult:
    selected_cost = estimate_cost_per_1k_tokens(selected_model)
    original_cost = estimate_cost_per_1k_tokens(original_model)

    if original_cost > 0 and selected_cost < original_cost:
        savings_pct = round((1 - selected_cost / original_cost) * 100, 2)
    else:
        savings_pct = 0.0

    return RoutingResult(
        selected_model=selected_model,
        original_model=original_model,
        tier=tier,
        complexity_score=score,
        complexity_reason=reason,
        estimated_cost_per_1k_tokens=selected_cost,
        estimated_savings_percent=savings_pct,
    )
