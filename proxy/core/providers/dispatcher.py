"""
TokenSaver Enterprise – Provider Dispatcher
Routes LLM requests to the appropriate provider via litellm.
Handles streaming, retries, error mapping and token usage normalisation.

Supported providers (via litellm):
  OpenAI, Anthropic, Google Gemini, Mistral, AWS Bedrock, Azure OpenAI
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, AsyncIterator, Optional

import litellm  # type: ignore[import]
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from proxy.config import settings
from proxy.core.router.model_catalog import MODEL_CATALOG

logger = logging.getLogger(__name__)

# ── litellm global config ─────────────────────────────────────────────────
litellm.set_verbose = settings.debug

# Inject API keys into litellm from our settings (so callers don't have to
# set environment variables manually — we do it once here at import time).
_KEY_MAP: dict[str, Optional[str]] = {
    "OPENAI_API_KEY": settings.openai_api_key,
    "ANTHROPIC_API_KEY": settings.anthropic_api_key,
    "GOOGLE_API_KEY": settings.google_api_key,
    "MISTRAL_API_KEY": settings.mistral_api_key,
    "COHERE_API_KEY": settings.cohere_api_key,
    "AWS_ACCESS_KEY_ID": settings.aws_access_key_id,
    "AWS_SECRET_ACCESS_KEY": settings.aws_secret_access_key,
    "AWS_REGION_NAME": settings.aws_region,
    "AZURE_API_KEY": settings.azure_openai_api_key,
    "AZURE_API_BASE": settings.azure_openai_endpoint,
}
for env_var, value in _KEY_MAP.items():
    if value:
        os.environ.setdefault(env_var, value)

# ── Model name mapping (our catalog → litellm prefix format) ─────────────
_LITELLM_PREFIX: dict[str, str] = {
    "openai": "",           # litellm uses bare names for OpenAI
    "anthropic": "anthropic/",
    "google": "gemini/",
    "mistral": "mistral/",
    "aws_bedrock": "bedrock/",
    "azure_openai": "azure/",
    "cohere": "cohere/",
}


def _to_litellm_model(model: str) -> str:
    """
    Convert our internal model name to litellm's expected format.

    Examples:
      "gpt-4o"                    → "gpt-4o"
      "claude-3-5-sonnet-20241022" → "anthropic/claude-3-5-sonnet-20241022"
      "gemini-1.5-flash"          → "gemini/gemini-1.5-flash"
    """
    info = MODEL_CATALOG.get(model)
    if info is None:
        # Unknown model – pass through as-is and let litellm handle it
        return model

    provider = info["provider"]
    prefix = _LITELLM_PREFIX.get(provider, "")
    return f"{prefix}{model}"


# ── Retry policy for transient errors ────────────────────────────────────
_RETRYABLE = (
    litellm.exceptions.RateLimitError,
    litellm.exceptions.ServiceUnavailableError,
    litellm.exceptions.Timeout,
    litellm.exceptions.APIConnectionError,
)


def _make_retry_decorator():  # type: ignore[return]
    return retry(
        retry=retry_if_exception_type(_RETRYABLE),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        reraise=True,
    )


# ── Main dispatch function ─────────────────────────────────────────────────

async def dispatch(
    messages: list[dict[str, Any]],
    model: str,
    stream: bool = False,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    presence_penalty: Optional[float] = None,
    **kwargs: Any,
) -> dict[str, Any] | AsyncIterator[dict[str, Any]]:
    """
    Route a request to the appropriate LLM provider via litellm.

    Parameters
    ----------
    messages:
        OpenAI-format message list.
    model:
        Internal model name (key from MODEL_CATALOG or raw litellm model).
    stream:
        If True, return an async generator of SSE-compatible chunks.
    temperature, max_tokens, top_p, frequency_penalty, presence_penalty:
        Standard generation parameters passed through to the provider.

    Returns
    -------
    For non-streaming: OpenAI-compatible response dict with usage block.
    For streaming:     Async generator yielding response chunk dicts.
    """
    litellm_model = _to_litellm_model(model)
    call_kwargs: dict[str, Any] = {
        "model": litellm_model,
        "messages": messages,
        "temperature": temperature,
        "stream": stream,
        **kwargs,
    }
    if max_tokens is not None:
        call_kwargs["max_tokens"] = max_tokens
    if top_p is not None:
        call_kwargs["top_p"] = top_p
    if frequency_penalty is not None:
        call_kwargs["frequency_penalty"] = frequency_penalty
    if presence_penalty is not None:
        call_kwargs["presence_penalty"] = presence_penalty

    logger.debug("Dispatching to litellm model=%s stream=%s", litellm_model, stream)

    if stream:
        return _stream_with_retry(call_kwargs)
    return await _complete_with_retry(call_kwargs)


@_make_retry_decorator()
async def _complete_with_retry(call_kwargs: dict[str, Any]) -> dict[str, Any]:
    """Non-streaming completion with automatic retries."""
    try:
        response = await litellm.acompletion(**call_kwargs)
        return _normalise_response(response)
    except _RETRYABLE:
        raise
    except litellm.exceptions.AuthenticationError as exc:
        raise _provider_error(401, f"Authentication failed: {exc}") from exc
    except litellm.exceptions.NotFoundError as exc:
        raise _provider_error(404, f"Model not found: {exc}") from exc
    except litellm.exceptions.BadRequestError as exc:
        raise _provider_error(400, f"Bad request: {exc}") from exc
    except Exception as exc:
        logger.exception("Unexpected LLM error: %s", exc)
        raise _provider_error(502, f"LLM provider error: {exc}") from exc


async def _stream_with_retry(
    call_kwargs: dict[str, Any],
) -> AsyncIterator[dict[str, Any]]:
    """
    Streaming completion – yields OpenAI-compatible SSE chunk dicts.
    Wraps the litellm async generator with proper error handling.
    """
    try:
        response_gen = await litellm.acompletion(**call_kwargs)
        async for chunk in response_gen:
            yield _normalise_chunk(chunk)
    except _RETRYABLE as exc:
        logger.warning("Stream rate-limited, retry not supported mid-stream: %s", exc)
        raise _provider_error(429, "Rate limited by upstream provider") from exc
    except Exception as exc:
        logger.exception("Stream error: %s", exc)
        raise _provider_error(502, f"LLM stream error: {exc}") from exc


# ── Normalisation helpers ─────────────────────────────────────────────────

def _normalise_response(response: Any) -> dict[str, Any]:
    """
    Convert litellm ModelResponse to a plain dict in OpenAI response format.
    Ensures the usage block is always present.
    """
    if hasattr(response, "model_dump"):
        data: dict[str, Any] = response.model_dump()
    elif hasattr(response, "dict"):
        data = response.dict()
    else:
        data = dict(response)

    # Guarantee usage block
    if "usage" not in data or data["usage"] is None:
        data["usage"] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
    return data


def _normalise_chunk(chunk: Any) -> dict[str, Any]:
    """Convert a streaming chunk to a plain dict."""
    if hasattr(chunk, "model_dump"):
        return chunk.model_dump()
    if hasattr(chunk, "dict"):
        return chunk.dict()
    return dict(chunk)


# ── Error helper ──────────────────────────────────────────────────────────

class ProviderError(Exception):
    """Raised when the LLM provider returns a non-retryable error."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _provider_error(status_code: int, message: str) -> ProviderError:
    return ProviderError(status_code=status_code, message=message)
