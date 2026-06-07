"""
TokenSaver Enterprise – Cache Manager
Orchestrates the two-level cache: L1 (exact) → L2 (semantic).
Provides a unified interface for the rest of the application.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import redis.asyncio as aioredis

from proxy.config import settings
from proxy.core.cache.l1_exact_cache import L1ExactCache
from proxy.core.cache.l2_semantic_cache import L2SemanticCache

logger = logging.getLogger(__name__)

CacheLevel = str  # "L1" | "L2" | "MISS"


@dataclass
class CacheResult:
    """Result returned by CacheManager.get()."""

    response: dict[str, Any]
    cache_level: CacheLevel          # "L1" or "L2"
    similarity_score: float = 1.0    # 1.0 for exact hits, <1 for semantic
    model_used: str = ""
    tokens_saved: int = 0
    cached_at: float = field(default_factory=time.time)


@dataclass
class CacheStats:
    """Running counters (in-process; reset on restart)."""

    hits_l1: int = 0
    hits_l2: int = 0
    misses: int = 0

    @property
    def total_requests(self) -> int:
        return self.hits_l1 + self.hits_l2 + self.misses

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.hits_l1 + self.hits_l2) / self.total_requests


class CacheManager:
    """
    Two-level cache orchestrator.

    L1 → exact SHA-256 key match (sub-millisecond)
    L2 → semantic embedding similarity (milliseconds)

    Both layers share the same Redis connection.
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client
        self.l1 = L1ExactCache(redis_client)
        self.l2 = L2SemanticCache(redis_client)
        self.stats = CacheStats()

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Called once at application startup to warm up the L2 layer."""
        await self.l2.initialize()
        logger.info("CacheManager initialized (L1=Redis KV, L2=RedisSearch)")

    # ── Core API ──────────────────────────────────────────────────────────

    async def get(
        self,
        messages: list[dict[str, Any]],
        model: str,
        team_id: str = "",
    ) -> Optional[CacheResult]:
        """
        Check both cache levels in order.

        1. L1 (exact SHA-256 match)  → instant hit
        2. L2 (semantic similarity)   → hit if score ≥ threshold
        3. Return None on full miss
        """
        # ── L1 check ──────────────────────────────────────────────────────
        l1_entry = await self.l1.get(messages, model)
        if l1_entry is not None:
            self.stats.hits_l1 += 1
            return CacheResult(
                response=l1_entry["response"],
                cache_level="L1",
                similarity_score=1.0,
                model_used=l1_entry.get("model_used", model),
                tokens_saved=l1_entry.get("tokens_saved", 0),
                cached_at=l1_entry.get("cached_at", time.time()),
            )

        # ── L2 check ──────────────────────────────────────────────────────
        query_text = _extract_query_text(messages)
        if query_text:
            l2_entry = await self.l2.search(query_text)
            if l2_entry is not None:
                self.stats.hits_l2 += 1
                inner_response = l2_entry.get("response", {})
                meta = l2_entry.get("metadata", {})
                return CacheResult(
                    response=inner_response,
                    cache_level="L2",
                    similarity_score=l2_entry.get("_similarity_score", 0.0),
                    model_used=meta.get("model_used", model),
                    tokens_saved=meta.get("tokens_saved", 0),
                    cached_at=l2_entry.get("cached_at", time.time()),
                )

        # ── Full miss ─────────────────────────────────────────────────────
        self.stats.misses += 1
        return None

    async def store(
        self,
        messages: list[dict[str, Any]],
        model: str,
        response: dict[str, Any],
        team_id: str = "",
    ) -> None:
        """
        Write to both L1 and L2 concurrently.
        Errors in either layer are suppressed so the request path is unaffected.
        """
        query_text = _extract_query_text(messages)
        usage = response.get("usage") or {}
        tokens_saved = usage.get("total_tokens", 0)

        metadata: dict[str, Any] = {
            "model_used": model,
            "team_id": team_id,
            "tokens_saved": tokens_saved,
        }

        await asyncio.gather(
            self.l1.set(messages, model, response),
            self.l2.store(query_text, response, metadata) if query_text else _noop(),
            return_exceptions=True,
        )

    async def flush(self) -> dict[str, int]:
        """Flush both cache levels. Returns counts of deleted keys."""
        l1_deleted, l2_deleted = await asyncio.gather(
            self.l1.flush_all(),
            self.l2.flush_all(),
            return_exceptions=True,
        )
        return {
            "l1_deleted": l1_deleted if isinstance(l1_deleted, int) else 0,
            "l2_deleted": l2_deleted if isinstance(l2_deleted, int) else 0,
        }

    def get_stats(self) -> dict[str, Any]:
        """Return current in-process cache statistics."""
        return {
            "hits_l1": self.stats.hits_l1,
            "hits_l2": self.stats.hits_l2,
            "misses": self.stats.misses,
            "total_requests": self.stats.total_requests,
            "hit_rate": round(self.stats.hit_rate, 4),
        }


# ── Helpers ───────────────────────────────────────────────────────────────

def _extract_query_text(messages: list[dict[str, Any]]) -> str:
    """
    Produce a single flat string from a message list for embedding.

    Uses the last user message first (most relevant), then appends
    previous context up to 512 chars.
    """
    parts: list[str] = []
    # Walk in reverse; collect user / assistant messages
    for msg in reversed(messages):
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, str) and content.strip():
            parts.append(f"{role}: {content.strip()}")
        if sum(len(p) for p in parts) > 1024:
            break
    return "\n".join(reversed(parts))[:1024]


async def _noop() -> None:  # noqa: RUF029
    """Placeholder coroutine for asyncio.gather when L2 is skipped."""
    pass
