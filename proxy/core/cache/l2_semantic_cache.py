"""
TokenSaver Enterprise – L2 Semantic Cache
Stores sentence embeddings in Redis (via JSON + RedisSearch) and performs
approximate-nearest-neighbour lookup using cosine similarity.

Requires the RedisSearch module (redis-stack or redis with redisearch plugin).
Falls back gracefully to a no-op when the module is unavailable.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

import numpy as np
import redis.asyncio as aioredis
from redis.commands.search.field import TextField, VectorField  # type: ignore[import]
from redis.commands.search.indexDefinition import IndexDefinition, IndexType  # type: ignore[import]
from redis.commands.search.query import Query  # type: ignore[import]

from proxy.config import settings

logger = logging.getLogger(__name__)

_INDEX_NAME = "ts:l2:idx"
_KEY_PREFIX  = "ts:l2:doc:"
_VECTOR_FIELD = "embedding"
_DIM = settings.redis_vector_dim


class L2SemanticCache:
    """
    Semantic cache backed by Redis vector search.

    Each stored document is a Redis Hash with fields:
      - embedding  : float32 binary blob (DIM × 4 bytes)
      - payload    : JSON string (response + metadata)
      - created_at : Unix timestamp string
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client
        self._model: Any = None          # sentence_transformers model
        self._available = False          # True once index is confirmed ready
        self._threshold = settings.cache_similarity_threshold
        self._ttl = settings.cache_ttl_seconds

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """
        Load the embedding model and create the Redis vector index if absent.
        Called once at application startup.
        """
        await self._load_embedding_model()
        await self._ensure_index()

    async def _load_embedding_model(self) -> None:
        """Import and load sentence-transformers lazily (heavy dependency)."""
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import]

            self._model = SentenceTransformer(settings.embedding_model)
            logger.info(
                "Embedding model loaded: %s (dim=%d)",
                settings.embedding_model,
                _DIM,
            )
        except Exception as exc:
            logger.error("Failed to load embedding model – L2 cache disabled: %s", exc)
            self._model = None

    async def _ensure_index(self) -> None:
        """Create the RedisSearch vector index if it doesn't exist yet."""
        if self._model is None:
            return
        try:
            try:
                await self._redis.ft(_INDEX_NAME).info()
                logger.info("RedisSearch index '%s' already exists.", _INDEX_NAME)
                self._available = True
                return
            except Exception:
                pass  # Index does not exist – create it

            schema = (
                TextField("$.payload", as_name="payload"),
                VectorField(
                    f"$.{_VECTOR_FIELD}",
                    "FLAT",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": _DIM,
                        "DISTANCE_METRIC": "COSINE",
                    },
                    as_name=_VECTOR_FIELD,
                ),
            )
            definition = IndexDefinition(
                prefix=[_KEY_PREFIX], index_type=IndexType.JSON
            )
            await self._redis.ft(_INDEX_NAME).create_index(
                schema, definition=definition
            )
            logger.info("Created RedisSearch vector index '%s'.", _INDEX_NAME)
            self._available = True
        except Exception as exc:
            logger.warning(
                "RedisSearch not available – L2 semantic cache disabled: %s", exc
            )
            self._available = False

    # ── Public API ────────────────────────────────────────────────────────

    async def embed_query(self, text: str) -> list[float]:
        """
        Generate a sentence embedding for *text*.
        Returns a list of *_DIM* float values.
        """
        if self._model is None:
            return []
        try:
            vec: np.ndarray = self._model.encode(
                text,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return vec.tolist()
        except Exception as exc:
            logger.warning("Embedding error: %s", exc)
            return []

    async def search(
        self,
        query_text: str,
        top_k: int = 1,
    ) -> Optional[dict[str, Any]]:
        """
        Perform a KNN cosine-similarity search.

        Returns the best-matching stored response if its similarity
        score is ≥ *settings.cache_similarity_threshold*, else *None*.
        """
        if not self._available or self._model is None:
            return None

        try:
            embedding = await self.embed_query(query_text)
            if not embedding:
                return None

            vec_bytes = (
                np.array(embedding, dtype=np.float32).tobytes()
            )

            q = (
                Query(f"(*)=>[KNN {top_k} @{_VECTOR_FIELD} $vec AS score]")
                .sort_by("score")
                .return_fields("payload", "score")
                .paging(0, top_k)
                .dialect(2)
            )
            results = await self._redis.ft(_INDEX_NAME).search(
                q, query_params={"vec": vec_bytes}
            )

            if not results.docs:
                return None

            best = results.docs[0]
            # Redis COSINE distance is 1 - cosine_similarity
            distance = float(getattr(best, "score", 1.0))
            similarity = 1.0 - distance

            if similarity < self._threshold:
                logger.debug(
                    "L2 cache NEAR-MISS  similarity=%.3f threshold=%.3f",
                    similarity,
                    self._threshold,
                )
                return None

            payload: dict[str, Any] = json.loads(best.payload)
            payload["_similarity_score"] = similarity
            logger.debug(
                "L2 cache HIT  similarity=%.4f key=%s",
                similarity,
                best.id,
            )
            return payload

        except Exception as exc:
            logger.warning("L2 cache SEARCH error: %s", exc)
            return None

    async def store(
        self,
        query_text: str,
        response: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        """
        Store an embedding + response in Redis JSON format.

        *metadata* can contain: model_used, team_id, tokens_saved, etc.
        """
        if not self._available or self._model is None:
            return

        try:
            embedding = await self.embed_query(query_text)
            if not embedding:
                return

            doc_id = f"{_KEY_PREFIX}{_make_doc_id(query_text)}"
            doc: dict[str, Any] = {
                _VECTOR_FIELD: embedding,
                "payload": json.dumps(
                    {
                        "response": response,
                        "metadata": metadata,
                        "cached_at": time.time(),
                    },
                    ensure_ascii=False,
                ),
                "created_at": str(time.time()),
            }

            pipe = self._redis.pipeline()
            pipe.json().set(doc_id, "$", doc)
            pipe.expire(doc_id, self._ttl)
            await pipe.execute()

            logger.debug("L2 cache STORE  key=%s", doc_id)
        except Exception as exc:
            logger.warning("L2 cache STORE error: %s", exc)

    async def flush_all(self) -> int:
        """Delete all L2 cache documents. Returns deleted count."""
        deleted = 0
        try:
            async for key in self._redis.scan_iter(f"{_KEY_PREFIX}*"):
                await self._redis.delete(key)
                deleted += 1
        except Exception as exc:
            logger.warning("L2 cache FLUSH error: %s", exc)
        return deleted


# ── Helpers ───────────────────────────────────────────────────────────────

def _make_doc_id(text: str) -> str:
    """Short deterministic ID from the first 64 chars (hex-safe)."""
    import hashlib

    return hashlib.md5(text.encode("utf-8")).hexdigest()
