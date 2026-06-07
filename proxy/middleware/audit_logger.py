"""
TokenSaver Enterprise – Structured Audit Logger Middleware
Logs every request as a single JSON line to stdout for ingestion by
log aggregation systems (Datadog, CloudWatch, Loki, etc.).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("tokensaver.audit")


class AuditLoggerMiddleware(BaseHTTPMiddleware):
    """
    Wraps every HTTP request and emits one structured JSON log line
    after the response is produced.

    Fields emitted
    --------------
    timestamp        – ISO-8601 UTC timestamp
    request_id       – UUID4 (also injected as X-Request-Id response header)
    team_id          – from request.state.team
    path             – request path
    method           – HTTP method
    model_requested  – from X-TokenSaver-Model-Requested header (if set)
    model_used       – from X-TokenSaver-Model-Used response header (if set)
    cache_hit        – from X-TokenSaver-Cache-Hit response header
    cache_level      – from X-TokenSaver-Cache-Level response header
    input_tokens     – approximate (from response header or 0)
    output_tokens    – approximate (from response header or 0)
    cost_usd         – from X-TokenSaver-Cost-USD response header
    savings_usd      – from X-TokenSaver-Savings-USD response header
    latency_ms       – wall-clock time for the full request
    status_code      – HTTP status code
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.monotonic()

        # Inject request_id so downstream handlers can reference it
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        except Exception as exc:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            _emit_log(
                request=request,
                request_id=request_id,
                response=None,
                latency_ms=latency_ms,
                status_code=500,
                error=str(exc),
            )
            raise

        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Tag the response with the request ID
        response.headers["X-Request-Id"] = request_id

        _emit_log(
            request=request,
            request_id=request_id,
            response=response,
            latency_ms=latency_ms,
            status_code=response.status_code,
        )
        return response


# ── Log emission ──────────────────────────────────────────────────────────

def _emit_log(
    request: Request,
    request_id: str,
    response: Optional[Response],
    latency_ms: int,
    status_code: int,
    error: Optional[str] = None,
) -> None:
    """Build and emit the JSON audit log entry."""
    from datetime import datetime, timezone

    team = getattr(request.state, "team", None)
    team_id = team.team_id if team else "unknown"

    headers_out = dict(response.headers) if response else {}

    record: dict[str, Any] = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "request_id": request_id,
        "team_id": team_id,
        "path": request.url.path,
        "method": request.method,
        "model_requested": headers_out.get(
            "x-tokensaver-model-requested",
            request.headers.get("x-tokensaver-model-override", ""),
        ),
        "model_used":      headers_out.get("x-tokensaver-model-used", ""),
        "cache_hit":       headers_out.get("x-tokensaver-cache-hit", "false").lower() == "true",
        "cache_level":     headers_out.get("x-tokensaver-cache-level", "MISS"),
        "input_tokens":    _safe_int(headers_out.get("x-tokensaver-input-tokens", "0")),
        "output_tokens":   _safe_int(headers_out.get("x-tokensaver-output-tokens", "0")),
        "cost_usd":        _safe_float(headers_out.get("x-tokensaver-cost-usd", "0")),
        "savings_usd":     _safe_float(headers_out.get("x-tokensaver-savings-usd", "0")),
        "latency_ms":      latency_ms,
        "status_code":     status_code,
    }
    if error:
        record["error"] = error

    # Single JSON line to stdout (logger handles buffering / transport)
    logger.info(json.dumps(record, ensure_ascii=False))


# ── Helpers ───────────────────────────────────────────────────────────────

def _safe_int(value: str) -> int:
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0


def _safe_float(value: str) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0
