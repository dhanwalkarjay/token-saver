"""
TokenSaver Enterprise – Conversation History Manager
Compresses long message histories to stay within token budgets while
preserving the most recent context and any system prompt.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Token count heuristic: 1 token ≈ 4 characters (GPT-family average)
_CHARS_PER_TOKEN = 4

# Number of recent messages to always keep verbatim (oldest first)
_RECENT_KEEP = 4


def count_tokens(messages: list[dict[str, Any]]) -> int:
    """
    Approximate token count for a message list.

    Uses the 4-chars-per-token heuristic.  For production deployments
    with precise token-billing needs, swap in tiktoken.
    """
    total_chars = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total_chars += len(block.get("text", ""))
        # Add a small overhead per message (role label + formatting)
        total_chars += 20
    return max(1, total_chars // _CHARS_PER_TOKEN)


def extract_summary(messages: list[dict[str, Any]]) -> str:
    """
    Produce a concise summary of key information from a list of messages.

    Extracts:
    - Decisions / conclusions (sentences ending with definitive language)
    - Fact statements (simple declarative sentences)
    - Code snippets mentioned (file names, function names)
    - The overall task context (first user message)
    """
    lines: list[str] = []

    # Capture first user message as task context
    for msg in messages:
        if msg.get("role") == "user":
            content = _get_text(msg)
            if content:
                short = content[:300].strip()
                lines.append(f"[Task context] {short}")
            break

    # Scan for key decision / fact sentences in assistant messages
    decisions: list[str] = []
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        content = _get_text(msg)
        for sentence in _split_sentences(content):
            s_lower = sentence.lower()
            if any(
                kw in s_lower
                for kw in [
                    "the answer is",
                    "in conclusion",
                    "therefore",
                    "we decided",
                    "the solution",
                    "the result",
                    "confirmed",
                    "established",
                    "the function",
                    "the class",
                    "the file",
                    "use ",
                    "should ",
                ]
            ):
                decisions.append(sentence.strip())
                if len(decisions) >= 8:
                    break

    if decisions:
        lines.append("[Key decisions / facts]")
        lines.extend(f"  • {d[:200]}" for d in decisions)

    # Detect code artifact references
    code_refs: list[str] = []
    for msg in messages:
        content = _get_text(msg)
        import re
        refs = re.findall(r"`([^`]{1,60})`|```(\w+)", content)
        for r in refs:
            ref = (r[0] or r[1]).strip()
            if ref and ref not in code_refs:
                code_refs.append(ref)
            if len(code_refs) >= 5:
                break
    if code_refs:
        lines.append(f"[Code artifacts mentioned] {', '.join(code_refs)}")

    return "\n".join(lines) if lines else "Previous conversation context (summarised)."


def compress_history(
    messages: list[dict[str, Any]],
    max_tokens: int = 2000,
) -> list[dict[str, Any]]:
    """
    Return a token-compressed version of *messages*.

    Strategy
    --------
    1. If total tokens ≤ max_tokens → return as-is (no compression needed).
    2. Always keep the system message intact.
    3. Always keep the most recent _RECENT_KEEP messages verbatim.
    4. Summarise any older messages into a single assistant "[History Summary]" message.

    Parameters
    ----------
    messages:
        Full conversation history in OpenAI format.
    max_tokens:
        Target token budget.  Compression is applied until this is satisfied
        or until only the system message + recent messages remain.

    Returns
    -------
    Compressed message list in OpenAI format.
    """
    if not messages:
        return messages

    current_tokens = count_tokens(messages)
    if current_tokens <= max_tokens:
        logger.debug(
            "History compression skipped: %d tokens ≤ %d limit",
            current_tokens,
            max_tokens,
        )
        return messages

    logger.info(
        "Compressing history: %d tokens → target %d",
        current_tokens,
        max_tokens,
    )

    # ── Partition messages ────────────────────────────────────────────────
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    # Most recent messages to preserve
    recent = non_system[-_RECENT_KEEP:] if len(non_system) > _RECENT_KEEP else non_system
    to_summarise = non_system[: -_RECENT_KEEP] if len(non_system) > _RECENT_KEEP else []

    # Build compressed list
    compressed: list[dict[str, Any]] = []

    # 1. System message(s) first
    compressed.extend(system_msgs)

    # 2. History summary (if there are old messages to collapse)
    if to_summarise:
        summary_text = extract_summary(to_summarise)
        summary_msg: dict[str, Any] = {
            "role": "assistant",
            "content": (
                f"[History Summary — {len(to_summarise)} messages compressed]\n"
                f"{summary_text}"
            ),
        }
        compressed.append(summary_msg)

    # 3. Recent messages verbatim
    compressed.extend(recent)

    final_tokens = count_tokens(compressed)
    logger.info(
        "Compression complete: %d → %d tokens (%.1f%% reduction)",
        current_tokens,
        final_tokens,
        100 * (1 - final_tokens / current_tokens),
    )
    return compressed


# ── Helpers ───────────────────────────────────────────────────────────────

def _get_text(msg: dict[str, Any]) -> str:
    """Extract plain text from a message, handling multi-modal content."""
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


def _split_sentences(text: str) -> list[str]:
    """Naive sentence splitter for summary extraction."""
    import re
    return re.split(r"(?<=[.!?])\s+", text)
