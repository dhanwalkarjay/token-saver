"""
TokenSaver Enterprise - Configuration Module
Reads all settings from environment variables with .env file support.
"""

from __future__ import annotations

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator, AnyUrl
import json


class Settings(BaseSettings):
    # ── Server ──────────────────────────────────────────────────────────────
    app_name: str = "TokenSaver Enterprise"
    version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Security ─────────────────────────────────────────────────────────────
    master_api_key: str = "ts-master-changeme"  # Override in production
    allowed_origins: list[str] = ["*"]

    # ── Redis (L1 exact cache + L2 vector cache) ──────────────────────────
    redis_url: str = "redis://localhost:6379"
    redis_vector_dim: int = 384          # BGE-small-en-v1.5 output dimension
    cache_similarity_threshold: float = 0.85
    cache_ttl_seconds: int = 86400       # 24 hours

    # ── PostgreSQL (analytics / audit) ────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://tokensaver:password@localhost:5432/tokensaver"
    )

    # ── Embedding model (runs locally, zero external calls) ───────────────
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # ── LLM Provider API Keys ─────────────────────────────────────────────
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    cohere_api_key: Optional[str] = None

    # AWS Bedrock
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"

    # Azure OpenAI
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None

    # ── Model routing thresholds ──────────────────────────────────────────
    tier1_max_tokens: int = 200
    tier2_max_tokens: int = 1000

    # ── Compression ───────────────────────────────────────────────────────
    compression_enabled: bool = True
    compression_threshold_tokens: int = 2000
    compression_ratio: float = 0.4      # Keep 40 % of tokens

    # ── Rate limiting ─────────────────────────────────────────────────────
    rate_limit_requests_per_minute: int = 60

    # ── Validators ───────────────────────────────────────────────────────
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: object) -> list[str]:
        """Accept JSON string or list for allowed_origins env var."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            # Comma-separated fallback
            return [o.strip() for o in v.split(",") if o.strip()]
        return list(v)  # type: ignore[arg-type]

    @field_validator("cache_similarity_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("cache_similarity_threshold must be between 0 and 1")
        return v

    @field_validator("compression_ratio")
    @classmethod
    def validate_compression_ratio(cls, v: float) -> float:
        if not 0.0 < v <= 1.0:
            raise ValueError("compression_ratio must be between 0 (exclusive) and 1")
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


# ── Module-level singleton ─────────────────────────────────────────────────
settings = Settings()
