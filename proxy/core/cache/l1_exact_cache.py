"""
TokenSaver Enterprise – L1 Exact Cache
Uses SHA-256 hash of a normalized prompt as Redis key.
Provides sub-millisecond lookup for identical repeated queries.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Optional

import redis.asyncio as aioredis

from proxy.config import settings

logger = logging.getLogger(__name__)

# Redis key prefix to avoid collisions with other namespaces
_PREFIX = "ts:l1:"


def normalize_prompt(messages: list[dict[str, Any]]) -> str:
    """
    Produce a stable string representation of a message list.

    Steps:
    1. For each message, sort dict keys alphabetically.
    2. Lowercase role and content strings so "Hello" == "hello".
    3. Strip leading/trailing whitespace from content.
    4. Serialise to compact JSON for consistent hashing.
    """
    normalised: list[dict[str, Any]] = []
    for msg in messages:
        norm_msg: dict[str, Any] = {}
        for k in sorted(msg.keys()):
            v = msg[k]
            if isinstance(v, str):
                v = v.strip().lower()
            norm_msg[k] = v
        normalised.append(norm_msg)
    return json.dumps(normalised, ensure_ascii=False, separators=(",", ":"))


def compute_hash(normalized: str, model: str) -> str:
    """
    SHA-256 over (normalized_prompt + model_name) so different
    model targets for the same prompt don't collide.
    """
    payload = f"{model}::{normalized}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class L1ExactCache:
    """
    Exact-match prompt cache backed by Redis strings.

    Cache entry schema (JSON-encoded value):
    {
        "response":     <OpenAI-compatible response dict>,
        "model_used":   "gpt-4o-mini",
        "tokens_saved": 312,
        "cached_at":    1718000000.0
    }
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client
        self._ttl = settings.cache_ttl_seconds

    # ── Public API ────────────────────────────────────────────────────────

    async def get(
        self,
        messages: list[dict[str, Any]],
        model: str,
    ) -> Optional[dict[str, Any]]:
        """
        Look up an exact cache hit.

        Returns the stored cache-entry dict, or *None* on a miss.
        """
        key = self._build_key(messages, model)
        try:
            raw = await self._redis.get(key)
            if raw is None:
                return None
            entry: dict[str, Any] = json.loads(raw)
            logger.debug("L1 cache HIT  key=%s", key[:16])
            return entry
        except Exception as exc:
            # Never let cache errors break the request path
            logger.warning("L1 cache GET error: %s", exc)
            return None

    async def set(
        self,
        messages: list[dict[str, Any]],
        model: str,
        response: dict[str, Any],
    ) -> None:
        """
        Store a response in the L1 cache.

        *tokens_saved* is derived from the response usage block so
        callers don't have to pre-compute it.
        """
        key = self._build_key(messages, model)
        usage = response.get("usage") or {}
        tokens_saved = usage.get("total_tokens", 0)

        entry: dict[str, Any] = {
            "response": response,
            "model_used": model,
            "tokens_saved": tokens_saved,
            "cached_at": time.time(),
        }
        try:
            await self._redis.setex(
                key,
                self._ttl,
                json.dumps(entry, ensure_ascii=False),
            )
            logger.debug("L1 cache SET   key=%s ttl=%ds", key[:16], self._ttl)
        except Exception as exc:
            logger.warning("L1 cache SET error: %s", exc)

    async def invalidate(
        self,
        messages: list[dict[str, Any]],
        model: str,
    ) -> bool:
        """Delete a cache entry. Returns True if the key existed."""
        key = self._build_key(messages, model)
        try:
            deleted = await self._redis.delete(key)
            return bool(deleted)
        except Exception as exc:
            logger.warning("L1 cache INVALIDATE error: %s", exc)
            return False

    async def flush_all(self) -> int:
        """
        Delete every L1 cache key (pattern scan).
        Returns the count of deleted keys.
        """
        deleted = 0
        try:
            async for key in self._redis.scan_iter(f"{_PREFIX}*"):
                await self._redis.delete(key)
                deleted += 1
        except Exception as exc:
            logger.warning("L1 cache FLUSH error: %s", exc)
        return deleted

    # ── Helpers ───────────────────────────────────────────────────────────

    def _build_key(
        self,
        messages: list[dict[str, Any]],
        model: str,
    ) -> str:
        normalised = normalize_prompt(messages)
        digest = compute_hash(normalised, model)
        return f"{_PREFIX}{digest}"
