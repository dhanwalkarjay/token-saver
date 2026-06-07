"""
TokenSaver Enterprise – Complexity Classifier
Rule-based (zero-ML) task complexity classifier.
Target latency: < 5 ms per call.

Algorithm
---------
1. Approximate token count from raw text length.
2. Scan for keyword signals (HIGH / LOW complexity word lists).
3. Detect structural features: code blocks, math symbols, multi-step cues.
4. Combine signals into a 0-100 score and map to tier 1/2/3.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# ── Signal word lists ─────────────────────────────────────────────────────

_HIGH_COMPLEXITY_KEYWORDS: list[str] = [
    "architect",
    "design system",
    "explain in detail",
    "compare and contrast",
    "analyze",
    "analyse",
    "algorithm",
    "implement from scratch",
    "mathematical proof",
    "step by step explanation",
    "comprehensive",
    "thesis",
    "research",
    "in depth",
    "elaborate",
    "derive",
    "optimize",
    "optimise",
    "scalable",
    "trade-off",
    "tradeoff",
    "evaluation",
    "systematic",
    "literature review",
    "critical analysis",
]

_LOW_COMPLEXITY_KEYWORDS: list[str] = [
    "fix this typo",
    "summarize briefly",
    "translate",
    "what is",
    "list",
    "rename",
    "format this",
    "correct grammar",
    "spell check",
    "bullet point",
    "one sentence",
    "briefly",
    "simple",
    "quick",
    "just ",          # "just tell me", "just list", etc.
    "tldr",
    "in one word",
]

# Regex patterns for structural signals
_CODE_BLOCK_RE = re.compile(r"```|~~~|<code>|`[^`]+`", re.IGNORECASE)
_MATH_SYMBOLS_RE = re.compile(
    r"[∑∏∫√∂∇∈∉⊂⊃∪∩≤≥≠±×÷α-ωΑ-Ω]|"
    r"\b(sin|cos|tan|log|exp|lim|sum|integral)\b",
    re.IGNORECASE,
)
_MULTI_STEP_RE = re.compile(
    r"\b(step \d|first[,:]|second[,:]|third[,:]|finally[,:]|"
    r"then,|also,|moreover|furthermore|in addition)\b",
    re.IGNORECASE,
)


# ── Result dataclass ──────────────────────────────────────────────────────

@dataclass
class ComplexityResult:
    tier: int           # 1, 2, or 3
    score: int          # 0-100
    reason: str         # Human-readable explanation


# ── Classifier ────────────────────────────────────────────────────────────

def classify_complexity(messages: list[dict[str, Any]]) -> ComplexityResult:
    """
    Classify the complexity of an LLM request and return the appropriate tier.

    Parameters
    ----------
    messages:
        OpenAI-style chat message list.

    Returns
    -------
    ComplexityResult with tier (1-3), score (0-100), and a short reason string.
    """
    full_text = _extract_text(messages)
    lower_text = full_text.lower()
    approx_tokens = _count_tokens_approx(full_text)

    score = 50   # Neutral baseline
    reasons: list[str] = []

    # ── 1. Token-count adjustment ─────────────────────────────────────────
    if approx_tokens < 200:
        score -= 20
        reasons.append(f"short input ({approx_tokens} tokens)")
    elif approx_tokens > 1000:
        score += 30
        reasons.append(f"long input ({approx_tokens} tokens)")

    # ── 2. High-complexity keyword signals ───────────────────────────────
    high_hits = [kw for kw in _HIGH_COMPLEXITY_KEYWORDS if kw in lower_text]
    if high_hits:
        increment = min(25, len(high_hits) * 10)
        score += increment
        reasons.append(f"high-complexity keywords: {', '.join(high_hits[:3])}")

    # ── 3. Low-complexity keyword signals ────────────────────────────────
    low_hits = [kw for kw in _LOW_COMPLEXITY_KEYWORDS if kw in lower_text]
    if low_hits:
        decrement = min(25, len(low_hits) * 8)
        score -= decrement
        reasons.append(f"low-complexity keywords: {', '.join(low_hits[:3])}")

    # ── 4. Structural feature signals ────────────────────────────────────
    if _CODE_BLOCK_RE.search(full_text):
        score += 15
        reasons.append("code blocks detected")

    if _MATH_SYMBOLS_RE.search(full_text):
        score += 20
        reasons.append("mathematical symbols detected")

    if _MULTI_STEP_RE.search(lower_text):
        score += 15
        reasons.append("multi-step reasoning cues")

    # ── Clamp to [0, 100] ────────────────────────────────────────────────
    score = max(0, min(100, score))

    # ── Map score to tier ────────────────────────────────────────────────
    if score <= 33:
        tier = 1
    elif score <= 66:
        tier = 2
    else:
        tier = 3

    reason = "; ".join(reasons) if reasons else "baseline estimate"
    return ComplexityResult(tier=tier, score=score, reason=reason)


# ── Helpers ───────────────────────────────────────────────────────────────

def _extract_text(messages: list[dict[str, Any]]) -> str:
    """Concatenate all message content into a single string."""
    parts: list[str] = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            # Multi-modal content (list of content blocks)
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
    return "\n".join(parts)


def _count_tokens_approx(text: str) -> int:
    """Approximate token count: characters / 4 (GPT tokeniser heuristic)."""
    return max(1, len(text) // 4)
