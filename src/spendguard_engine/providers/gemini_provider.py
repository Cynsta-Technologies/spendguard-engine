from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def _normalize_model(model: str) -> str:
    if model.startswith("models/"):
        return model
    return f"models/{model}"


def call_gemini_generate_content(
    api_key: str,
    model: str,
    prompt: str,
    temperature: float | None,
    max_tokens: int,
) -> dict[str, Any]:
    url = f"https://generativelanguage.googleapis.com/v1beta/{_normalize_model(model)}:generateContent"
    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    if temperature is not None:
        payload["generationConfig"]["temperature"] = temperature
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else str(exc)
        raise RuntimeError(f"Gemini request failed: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini request failed: {exc.reason}") from exc
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise RuntimeError("Gemini returned invalid JSON")
    return payload


def extract_gemini_completion(payload: dict[str, Any]) -> str | None:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        return None
    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict):
            text = part.get("text")
            if isinstance(text, str):
                texts.append(text)
    if not texts:
        return None
    return "\n".join(texts)


def extract_gemini_usage(payload: dict[str, Any]) -> tuple[int | None, int | None]:
    usage = payload.get("usageMetadata")
    if not isinstance(usage, dict):
        return None, None
    return usage.get("promptTokenCount"), usage.get("candidatesTokenCount")

