"""
TokenSaver Enterprise – Model Catalog
Complete catalog of all supported LLM models with current (2024-Q4) pricing.
Prices are in USD per million tokens (input / output).
"""

from __future__ import annotations

from typing import TypedDict, Literal


ProviderName = Literal[
    "openai", "anthropic", "google", "mistral",
    "cohere", "aws_bedrock", "azure_openai",
]


class ModelInfo(TypedDict):
    """Metadata for a single model entry."""

    tier: int                   # 1 = cheap, 2 = balanced, 3 = premium
    input_per_mtok: float       # USD per 1M input tokens
    output_per_mtok: float      # USD per 1M output tokens
    provider: ProviderName
    max_tokens: int             # Context window (tokens)


# ── Master catalog ────────────────────────────────────────────────────────
# Prices as of 2024-Q4; update as providers change their rates.

MODEL_CATALOG: dict[str, ModelInfo] = {
    # ── Tier 1 – Cheap & Fast ─────────────────────────────────────────────
    "gpt-4o-mini": {
        "tier": 1,
        "input_per_mtok": 0.15,
        "output_per_mtok": 0.60,
        "provider": "openai",
        "max_tokens": 128_000,
    },
    "claude-3-haiku-20240307": {
        "tier": 1,
        "input_per_mtok": 0.25,
        "output_per_mtok": 1.25,
        "provider": "anthropic",
        "max_tokens": 200_000,
    },
    "gemini-1.5-flash": {
        "tier": 1,
        "input_per_mtok": 0.075,
        "output_per_mtok": 0.30,
        "provider": "google",
        "max_tokens": 1_000_000,
    },
    "mistral-small-latest": {
        "tier": 1,
        "input_per_mtok": 0.20,
        "output_per_mtok": 0.60,
        "provider": "mistral",
        "max_tokens": 32_000,
    },

    # ── Tier 2 – Balanced ─────────────────────────────────────────────────
    "gpt-4o": {
        "tier": 2,
        "input_per_mtok": 2.50,
        "output_per_mtok": 10.00,
        "provider": "openai",
        "max_tokens": 128_000,
    },
    "claude-3-5-sonnet-20241022": {
        "tier": 2,
        "input_per_mtok": 3.00,
        "output_per_mtok": 15.00,
        "provider": "anthropic",
        "max_tokens": 200_000,
    },
    "gemini-1.5-pro": {
        "tier": 2,
        "input_per_mtok": 1.25,
        "output_per_mtok": 5.00,
        "provider": "google",
        "max_tokens": 2_000_000,
    },
    "mistral-large-latest": {
        "tier": 2,
        "input_per_mtok": 2.00,
        "output_per_mtok": 6.00,
        "provider": "mistral",
        "max_tokens": 128_000,
    },

    # ── Tier 3 – Premium ──────────────────────────────────────────────────
    "o1": {
        "tier": 3,
        "input_per_mtok": 15.00,
        "output_per_mtok": 60.00,
        "provider": "openai",
        "max_tokens": 200_000,
    },
    "o1-mini": {
        "tier": 3,
        "input_per_mtok": 3.00,
        "output_per_mtok": 12.00,
        "provider": "openai",
        "max_tokens": 128_000,
    },
    "claude-3-5-opus-20240229": {
        "tier": 3,
        "input_per_mtok": 15.00,
        "output_per_mtok": 75.00,
        "provider": "anthropic",
        "max_tokens": 200_000,
    },
    "gemini-ultra": {
        "tier": 3,
        "input_per_mtok": 7.00,
        "output_per_mtok": 21.00,
        "provider": "google",
        "max_tokens": 1_000_000,
    },
}

# ── Defaults ─────────────────────────────────────────────────────────────

DEFAULT_TIER_MODELS: dict[int, str] = {
    1: "gpt-4o-mini",
    2: "gpt-4o",
    3: "o1",
}

# ── Convenience helpers ───────────────────────────────────────────────────

def get_model_info(model: str) -> ModelInfo | None:
    """Return catalog entry for *model*, or None if unknown."""
    return MODEL_CATALOG.get(model)


def get_models_by_tier(tier: int) -> dict[str, ModelInfo]:
    """Return all models belonging to a specific tier."""
    return {
        name: info
        for name, info in MODEL_CATALOG.items()
        if info["tier"] == tier
    }


def get_cheapest_model_in_tier(tier: int) -> str:
    """Return the model name with the lowest combined cost in a given tier."""
    tier_models = get_models_by_tier(tier)
    if not tier_models:
        return DEFAULT_TIER_MODELS.get(tier, "gpt-4o-mini")
    return min(
        tier_models,
        key=lambda m: tier_models[m]["input_per_mtok"] + tier_models[m]["output_per_mtok"],
    )


def estimate_cost_per_1k_tokens(model: str) -> float:
    """
    Approximate cost for 1 000 tokens (500 in / 500 out).
    Returns 0.0 for unknown models.
    """
    info = MODEL_CATALOG.get(model)
    if info is None:
        return 0.0
    return (
        info["input_per_mtok"] * 0.5 / 1000
        + info["output_per_mtok"] * 0.5 / 1000
    )


def list_all_models() -> list[dict]:
    """Return full catalog as a list of dicts (for the /v1/models endpoint)."""
    return [
        {
            "id": name,
            "provider": info["provider"],
            "tier": info["tier"],
            "max_tokens": info["max_tokens"],
            "pricing": {
                "input_per_million_tokens": info["input_per_mtok"],
                "output_per_million_tokens": info["output_per_mtok"],
            },
        }
        for name, info in MODEL_CATALOG.items()
    ]
