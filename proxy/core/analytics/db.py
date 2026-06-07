"""
TokenSaver Enterprise – Database Layer
Async SQLAlchemy + asyncpg connection pool, ORM models, and schema management.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    Index,
    BigInteger,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from proxy.config import settings

logger = logging.getLogger(__name__)

# ── SQLAlchemy engine & session factory ───────────────────────────────────

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,          # validate connections before use
    pool_recycle=3600,           # recycle after 1 hour to avoid stale connections
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── ORM base ──────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── ORM models ────────────────────────────────────────────────────────────

class ApiRequest(Base):
    """
    Stores analytics for every proxied LLM request.

    Indexed on team_id + timestamp for efficient per-team reporting.
    """

    __tablename__ = "api_requests"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    team_id         = Column(String(128), nullable=False, index=True)
    timestamp       = Column(DateTime(timezone=True), nullable=False, index=True)
    model_requested = Column(String(256), nullable=False)
    model_used      = Column(String(256), nullable=False)
    input_tokens    = Column(Integer, default=0, nullable=False)
    output_tokens   = Column(Integer, default=0, nullable=False)
    cost_usd        = Column(Float, default=0.0, nullable=False)
    savings_usd     = Column(Float, default=0.0, nullable=False)
    cache_hit       = Column(Boolean, default=False, nullable=False)
    cache_level     = Column(String(8), default="MISS", nullable=False)  # L1|L2|MISS
    routing_tier    = Column(Integer, default=1, nullable=False)
    latency_ms      = Column(Integer, default=0, nullable=False)
    request_hash    = Column(String(64), nullable=True)   # SHA-256 for dedup analysis

    __table_args__ = (
        Index("ix_api_requests_team_timestamp", "team_id", "timestamp"),
        Index("ix_api_requests_model_used", "model_used"),
    )


class Team(Base):
    """
    Stores team (tenant) configuration and authentication data.
    API keys are stored as bcrypt hashes — never plaintext.
    """

    __tablename__ = "teams"

    id               = Column(String(128), primary_key=True)   # UUID string
    name             = Column(String(256), nullable=False)
    api_key_hash     = Column(String(256), nullable=False, unique=True)
    api_key_prefix   = Column(String(32), nullable=False)      # "ts-{team_id}-" prefix for fast lookup
    tier_limit       = Column(Integer, default=3, nullable=False)   # max allowed tier
    monthly_budget_usd = Column(Float, default=0.0, nullable=False)  # 0 = unlimited
    rate_limit_rpm   = Column(Integer, default=60, nullable=False)
    routing_mode     = Column(String(32), default="auto", nullable=False)
    created_at       = Column(DateTime(timezone=True), nullable=False)
    is_active        = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("ix_teams_api_key_prefix", "api_key_prefix"),
    )


# ── Schema management ─────────────────────────────────────────────────────

async def init_db() -> None:
    """
    Create all tables if they don't exist.
    Safe to call on every startup (uses CREATE TABLE IF NOT EXISTS semantics).
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialised successfully.")
    except Exception as exc:
        logger.error("Failed to initialise database schema: %s", exc)
        raise


async def close_db() -> None:
    """Dispose of the connection pool on application shutdown."""
    await engine.dispose()
    logger.info("Database connection pool closed.")


# ── Dependency injection helper ───────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async DB session.

    Usage:
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
