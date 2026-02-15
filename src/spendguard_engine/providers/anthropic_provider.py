from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def call_anthropic_messages(
    api_key: str,
    model: str,
    system: str | None,
    messages: list[dict[str, Any]],
    temperature: float | None,
    max_tokens: int,
) -> dict[str, Any]:
    url = "https://api.anthropic.com/v1/messages"
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        payload["system"] = system
    if temperature is not None:
        payload["temperature"] = temperature

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            # Keep overrideable since Anthropic versions drift.
            "anthropic-version": os.getenv("ANTHROPIC_VERSION", "2023-06-01"),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else str(exc)
        raise RuntimeError(f"Anthropic request failed: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Anthropic request failed: {exc.reason}") from exc

    out = json.loads(raw)
    if not isinstance(out, dict):
        raise RuntimeError("Anthropic returned invalid JSON")
    return out


def extract_anthropic_completion(payload: dict[str, Any]) -> str | None:
    content = payload.get("content")
    if not isinstance(content, list) or not content:
        return None
    texts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "text":
            continue
        text = block.get("text")
        if isinstance(text, str) and text:
            texts.append(text)
    if not texts:
        return None
    return "\n".join(texts)


def extract_anthropic_usage(payload: dict[str, Any]) -> tuple[int | None, int | None]:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None, None
    return usage.get("input_tokens"), usage.get("output_tokens")

