from __future__ import annotations

import os
from typing import Any

from openai import OpenAI


def clamp_openai_max_tokens(max_tokens: int) -> int:
    # Provider-side safety ceiling. SpendGuard's budget-based clamp can compute values
    # above a model's supported max completion tokens, which causes provider 400s.
    raw = os.getenv("CAP_OPENAI_MAX_COMPLETION_TOKENS", "16384").strip()
    cap = int(raw)
    if cap <= 0:
        return max_tokens
    return min(int(max_tokens), cap)


def clamp_openai_max_output_tokens(max_output_tokens: int) -> int:
    raw = os.getenv("CAP_OPENAI_MAX_OUTPUT_TOKENS", "16384").strip()
    cap = int(raw)
    if cap <= 0:
        return max_output_tokens
    return min(int(max_output_tokens), cap)


def call_openai_chat(
    client: OpenAI,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float | None,
    max_tokens: int,
    stream: bool,
) -> Any:
    return client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=clamp_openai_max_tokens(max_tokens),
        stream=stream,
    )


def call_openai_responses(
    client: OpenAI,
    payload: dict[str, Any],
    max_output_tokens: int,
) -> Any:
    body = dict(payload)
    body["max_output_tokens"] = clamp_openai_max_output_tokens(max_output_tokens)
    return client.responses.create(**body)


def extract_openai_usage(response: Any) -> tuple[int | None, int | None]:
    usage = getattr(response, "usage", None)
    if not usage:
        return None, None
    if isinstance(usage, dict):
        return usage.get("prompt_tokens"), usage.get("completion_tokens")
    return getattr(usage, "prompt_tokens", None), getattr(usage, "completion_tokens", None)
