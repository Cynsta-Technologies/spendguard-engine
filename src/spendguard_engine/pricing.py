from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RateCard:
    # Required base rates (backwards compatible with the MVP schema).
    input_cents_per_1m: int
    output_cents_per_1m: int

    # Optional refinements (provider-specific).
    cached_input_cents_per_1m: int | None = None
    uncached_input_cents_per_1m: int | None = None
    reasoning_output_cents_per_1m: int | None = None

    cache_write_input_cents_per_1m: int | None = None
    cache_read_input_cents_per_1m: int | None = None

    grounding_cents_per_1k_queries: int | None = None

    web_search_cents_per_call: int | None = None
    file_search_cents_per_call: int | None = None

    # Context cliff knobs (used for Anthropic-style tiering when configured).
    context_cliff_threshold_tokens: int | None = None
    context_cliff_input_multiplier: float | None = None
    context_cliff_output_multiplier: float | None = None


DEFAULT_RATES: dict[str, dict[str, RateCard]] = {
    # Conservative defaults. Wrapper services should override these in production.
    "openai": {
        "gpt-4o-mini": RateCard(input_cents_per_1m=30, output_cents_per_1m=120),
        "gpt-4o": RateCard(input_cents_per_1m=250, output_cents_per_1m=1000),
        # GPT-5.2 family (flagship; supports reasoning.effort).
        # Cached input rates for GPT-5.2 are fractional cents/1M (e.g. $0.175 => 17.5 cents/1M).
        # This MVP schema uses integer cents/1M, so we round up to stay conservative.
        "gpt-5.2": RateCard(input_cents_per_1m=175, output_cents_per_1m=1400, cached_input_cents_per_1m=18),
        "gpt-5.2-chat-latest": RateCard(input_cents_per_1m=175, output_cents_per_1m=1400, cached_input_cents_per_1m=18),
        "gpt-5.2-codex": RateCard(input_cents_per_1m=175, output_cents_per_1m=1400, cached_input_cents_per_1m=18),
        # GPT-5.2 pro is Responses-only and intentionally expensive; used for SOTA reasoning checks.
        "gpt-5.2-pro": RateCard(input_cents_per_1m=2100, output_cents_per_1m=16800),
        # Reasoning models (rates from OpenAI pricing as of 2026-02-10; keep overrideable).
        # Note: many OpenAI cached input rates are fractional cents/1M; we only include models whose
        # token rates are representable as integer cents/1M with this MVP schema.
        "o3-mini": RateCard(input_cents_per_1m=110, output_cents_per_1m=440, cached_input_cents_per_1m=55),
        "o3": RateCard(input_cents_per_1m=200, output_cents_per_1m=800, cached_input_cents_per_1m=50),
        "o3-pro": RateCard(input_cents_per_1m=2000, output_cents_per_1m=8000),
        "o3-deep-research": RateCard(input_cents_per_1m=1000, output_cents_per_1m=4000, cached_input_cents_per_1m=250),
        "o1-mini": RateCard(input_cents_per_1m=110, output_cents_per_1m=440, cached_input_cents_per_1m=55),
        "o1": RateCard(input_cents_per_1m=1500, output_cents_per_1m=6000, cached_input_cents_per_1m=750),
    },
    "gemini": {
        "gemini-3-flash-preview": RateCard(input_cents_per_1m=50, output_cents_per_1m=200),
        "gemini-3-pro-preview": RateCard(input_cents_per_1m=200, output_cents_per_1m=1200, cached_input_cents_per_1m=20),
        "gemini-1.5-flash": RateCard(input_cents_per_1m=35, output_cents_per_1m=150),
    },
    "anthropic": {
        # Conservative placeholders; override in production.
        "claude-opus-4-6": RateCard(input_cents_per_1m=500, output_cents_per_1m=2500),
        "claude-3-5-sonnet-latest": RateCard(input_cents_per_1m=400, output_cents_per_1m=2000),
        "claude-3-5-haiku-latest": RateCard(input_cents_per_1m=100, output_cents_per_1m=500),
    },
    "grok": {
        # xAI Grok model card defaults (OpenAI-compatible API), overrideable via cloud pricing.
        "grok-3": RateCard(input_cents_per_1m=300, output_cents_per_1m=1500, cached_input_cents_per_1m=75),
        "grok-3-latest": RateCard(input_cents_per_1m=300, output_cents_per_1m=1500, cached_input_cents_per_1m=75),
        "grok-3-fast-latest": RateCard(input_cents_per_1m=300, output_cents_per_1m=1500, cached_input_cents_per_1m=75),
    },
}


def copy_rates(rates: dict[str, dict[str, RateCard]]) -> dict[str, dict[str, RateCard]]:
    return {provider: dict(models) for provider, models in rates.items()}


def merge_rates(base: dict[str, dict[str, RateCard]], overlay: dict[str, dict[str, RateCard]]) -> None:
    for provider, models in overlay.items():
        base.setdefault(provider, {})
        base[provider].update(models)


def estimate_tokens_text(text: str) -> int:
    # Simple, conservative estimate; avoids adding tokenizer deps.
    # Typical English is ~4 chars/token; we overestimate a bit.
    if not text:
        return 0
    return max(1, (len(text) + 2) // 3)


def cost_cents(tokens: int, cents_per_1m: int) -> int:
    if tokens <= 0 or cents_per_1m <= 0:
        return 0
    # ceil(tokens * rate / 1_000_000) without floats
    return (tokens * cents_per_1m + 1_000_000 - 1) // 1_000_000
