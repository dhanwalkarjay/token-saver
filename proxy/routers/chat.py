"""
TokenSaver Enterprise – Chat Completions Router
Implements the /v1/chat/completions endpoint with full OpenAI API compatibility.

Request flow:
  1. Parse & validate ChatCompletionRequest
  2. Read control headers (cache / route / compress toggles)
  3. Check L1/L2 cache → return immediately on hit
  4. Compress history if needed
  5. Route to best model
  6. Dispatch to LLM provider
  7. Track analytics & populate cache (async, non-blocking)
  8. Return OpenAI-compatible response + X-TokenSaver-* headers
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, AsyncIterator, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from proxy.config import settings
from proxy.core.analytics.cost_tracker import calculate_cost, calculate_savings, track_request
from proxy.core.analytics.db import get_db
from proxy.core.cache.cache_manager import CacheManager
from proxy.core.compression.history_manager import compress_history, count_tokens
from proxy.core.providers.dispatcher import ProviderError, dispatch
from proxy.core.router.model_router import TeamConfig, route
from proxy.middleware.auth import get_team_from_request

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Pydantic models (OpenAI-compatible) ──────────────────────────────────


class ContentPart(BaseModel):
    """Multi-modal content block (text, image_url, etc.)."""
    type: str
    text: Optional[str] = None
    image_url: Optional[dict[str, Any]] = None


class Message(BaseModel):
    """A single chat message."""
    role: Literal["system", "user", "assistant", "tool", "function"]
    content: str | list[ContentPart] | None = None
    name: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None
    tool_call_id: Optional[str] = None

    def model_dump_api(self) -> dict[str, Any]:
        """Dump only fields that LLM APIs actually accept."""
        data: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            if isinstance(self.content, list):
                data["content"] = [p.model_dump(exclude_none=True) for p in self.content]
            else:
                data["content"] = self.content
        if self.name:
            data["name"] = self.name
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        return data


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request body."""

    model: str = Field(..., description="Model identifier")
    messages: list[Message] = Field(..., min_length=1)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1)
    stream: bool = False
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    stop: Optional[str | list[str]] = None
    n: Optional[int] = Field(None, ge=1, le=10)
    user: Optional[str] = None

    # Tool / function calling pass-through
    tools: Optional[list[dict[str, Any]]] = None
    tool_choice: Optional[str | dict[str, Any]] = None
    functions: Optional[list[dict[str, Any]]] = None
    function_call: Optional[str | dict[str, Any]] = None

    model_config = {"extra": "allow"}   # Forward unknown fields to litellm


# ── Main endpoint ─────────────────────────────────────────────────────────

@router.post("/v1/chat/completions")
async def chat_completions(
    request_body: ChatCompletionRequest,
    raw_request: Request,
    team: TeamConfig = Depends(get_team_from_request),
) -> JSONResponse | StreamingResponse:
    """
    OpenAI-compatible chat completions endpoint with TokenSaver optimisations.

    Control headers (all optional, defaults shown):
      X-TokenSaver-Cache:    true     – enable/disable cache lookup
      X-TokenSaver-Route:    auto     – routing mode (auto|cheap|balanced|premium|disabled)
      X-TokenSaver-Compress: true     – enable/disable history compression
      X-TokenSaver-Model-Override: <model> – force a specific model
    """
    start_time = time.monotonic()
    request_id = getattr(raw_request.state, "request_id", "unknown")

    # ── Read control headers ─────────────────────────────────────────────
    use_cache   = raw_request.headers.get("X-TokenSaver-Cache",    "true").lower() != "false"
    route_mode  = raw_request.headers.get("X-TokenSaver-Route",    "auto")
    compress    = raw_request.headers.get("X-TokenSaver-Compress", "true").lower() != "false"
    model_override = raw_request.headers.get("X-TokenSaver-Model-Override")

    # Retrieve the shared CacheManager from app state
    cache_mgr: CacheManager = raw_request.app.state.cache_manager

    # Convert Pydantic messages to raw dicts for internal processing
    raw_messages: list[dict[str, Any]] = [m.model_dump_api() for m in request_body.messages]

    # ── 1. Cache lookup ──────────────────────────────────────────────────
    if use_cache:
        cache_result = await cache_mgr.get(
            messages=raw_messages,
            model=request_body.model,
            team_id=team.team_id,
        )
        if cache_result is not None:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            usage = cache_result.response.get("usage") or {}
            savings = calculate_savings(
                original_model=request_body.model,
                used_model=cache_result.model_used or request_body.model,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                cache_hit=True,
            )
            return _build_response(
                body=cache_result.response,
                model_requested=request_body.model,
                model_used=cache_result.model_used or request_body.model,
                cache_hit=True,
                cache_level=cache_result.cache_level,
                cost_usd=0.0,
                savings_usd=savings.original_cost,
                savings_pct=savings.saved_percent,
                latency_ms=latency_ms,
                similarity_score=cache_result.similarity_score,
            )

    # ── 2. History compression ───────────────────────────────────────────
    messages_to_send = raw_messages
    if compress and settings.compression_enabled:
        token_count = count_tokens(raw_messages)
        if token_count > settings.compression_threshold_tokens:
            messages_to_send = compress_history(
                raw_messages,
                max_tokens=settings.compression_threshold_tokens,
            )
            logger.info(
                "Compressed history: %d → %d tokens for request_id=%s",
                token_count,
                count_tokens(messages_to_send),
                request_id,
            )

    # ── 3. Model routing ────────────────────────────────────────────────
    routing_result = await route(
        messages=messages_to_send,
        requested_model=request_body.model,
        team_config=team,
        routing_mode=route_mode if route_mode in ("auto", "cheap", "balanced", "premium", "disabled") else "auto",  # type: ignore[arg-type]
        model_override=model_override,
    )
    selected_model = routing_result.selected_model

    # ── 4. Dispatch to LLM provider ──────────────────────────────────────
    dispatch_kwargs: dict[str, Any] = {
        "messages":           messages_to_send,
        "model":              selected_model,
        "stream":             request_body.stream,
        "temperature":        request_body.temperature,
    }
    if request_body.max_tokens:
        dispatch_kwargs["max_tokens"] = request_body.max_tokens
    if request_body.top_p is not None:
        dispatch_kwargs["top_p"] = request_body.top_p
    if request_body.frequency_penalty is not None:
        dispatch_kwargs["frequency_penalty"] = request_body.frequency_penalty
    if request_body.presence_penalty is not None:
        dispatch_kwargs["presence_penalty"] = request_body.presence_penalty
    if request_body.stop:
        dispatch_kwargs["stop"] = request_body.stop
    if request_body.tools:
        dispatch_kwargs["tools"] = request_body.tools
    if request_body.tool_choice:
        dispatch_kwargs["tool_choice"] = request_body.tool_choice

    try:
        result = await dispatch(**dispatch_kwargs)
    except ProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    # ── 5. Streaming path ────────────────────────────────────────────────
    if request_body.stream:
        async def sse_generator() -> AsyncIterator[bytes]:
            async for chunk in result:  # type: ignore[union-attr]
                yield b"data: " + json.dumps(chunk, ensure_ascii=False).encode() + b"\n\n"
            yield b"data: [DONE]\n\n"

        latency_ms = int((time.monotonic() - start_time) * 1000)
        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={
                "X-TokenSaver-Model-Requested": request_body.model,
                "X-TokenSaver-Model-Used":      selected_model,
                "X-TokenSaver-Cache-Hit":        "false",
                "X-TokenSaver-Cache-Level":      "MISS",
            },
        )

    # ── 6. Non-streaming path ────────────────────────────────────────────
    response_body: dict[str, Any] = result  # type: ignore[assignment]
    usage = response_body.get("usage") or {}
    input_tokens  = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    cost_usd = calculate_cost(selected_model, input_tokens, output_tokens)
    savings  = calculate_savings(
        original_model=request_body.model,
        used_model=selected_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_hit=False,
    )

    latency_ms = int((time.monotonic() - start_time) * 1000)

    # ── 7. Async background tasks ────────────────────────────────────────
    request_hash = _compute_request_hash(raw_messages, request_body.model)
    asyncio.ensure_future(
        _store_cache_background(cache_mgr, raw_messages, selected_model, response_body, team.team_id)
    )
    asyncio.ensure_future(
        _track_analytics_background(
            team_id=team.team_id,
            model_requested=request_body.model,
            model_used=selected_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            savings_usd=savings.saved_amount,
            cache_hit=False,
            cache_level="MISS",
            routing_tier=routing_result.tier,
            latency_ms=latency_ms,
            request_hash=request_hash,
        )
    )

    # ── 8. Build & return response ───────────────────────────────────────
    return _build_response(
        body=response_body,
        model_requested=request_body.model,
        model_used=selected_model,
        cache_hit=False,
        cache_level="MISS",
        cost_usd=cost_usd,
        savings_usd=savings.saved_amount,
        savings_pct=savings.saved_percent,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


# ── Response builder ──────────────────────────────────────────────────────

def _build_response(
    body: dict[str, Any],
    model_requested: str,
    model_used: str,
    cache_hit: bool,
    cache_level: str,
    cost_usd: float,
    savings_usd: float,
    savings_pct: float,
    latency_ms: int,
    similarity_score: float = 1.0,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> JSONResponse:
    headers = {
        "X-TokenSaver-Cache-Hit":        str(cache_hit).lower(),
        "X-TokenSaver-Cache-Level":      cache_level,
        "X-TokenSaver-Model-Used":       model_used,
        "X-TokenSaver-Model-Requested":  model_requested,
        "X-TokenSaver-Cost-USD":         f"{cost_usd:.8f}",
        "X-TokenSaver-Savings-USD":      f"{savings_usd:.8f}",
        "X-TokenSaver-Savings-Percent":  f"{savings_pct:.2f}",
        "X-TokenSaver-Latency-Ms":       str(latency_ms),
        "X-TokenSaver-Input-Tokens":     str(input_tokens),
        "X-TokenSaver-Output-Tokens":    str(output_tokens),
    }
    if cache_level == "L2":
        headers["X-TokenSaver-Similarity-Score"] = f"{similarity_score:.4f}"

    return JSONResponse(content=body, headers=headers)


# ── Background helpers ────────────────────────────────────────────────────

async def _store_cache_background(
    cache_mgr: CacheManager,
    messages: list[dict[str, Any]],
    model: str,
    response: dict[str, Any],
    team_id: str,
) -> None:
    try:
        await cache_mgr.store(messages, model, response, team_id)
    except Exception as exc:
        logger.warning("Background cache store failed: %s", exc)


async def _track_analytics_background(
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
) -> None:
    try:
        from proxy.core.analytics.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await track_request(
                team_id=team_id,
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
                db=db,
            )
    except Exception as exc:
        logger.warning("Background analytics tracking failed: %s", exc)


def _compute_request_hash(messages: list[dict[str, Any]], model: str) -> str:
    payload = json.dumps({"model": model, "messages": messages}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()
