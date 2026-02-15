from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spendguard_engine.pricing import RateCard


MICROCENTS_PER_CENT = 1_000_000


def _ceil_div(n: int, d: int) -> int:
    if d <= 0:
        raise ValueError("divisor must be > 0")
    if n <= 0:
        return 0
    return (n + d - 1) // d


def cents_ceiled_from_microcents(microcents: int) -> int:
    return _ceil_div(int(microcents), MICROCENTS_PER_CENT)


def _token_cost_microcents(tokens: int, cents_per_1m: int) -> int:
    # Since cents_per_1m is cents per 1,000,000 tokens, the exact cost in microcents
    # is tokens * cents_per_1m.
    if tokens <= 0 or cents_per_1m <= 0:
        return 0
    return int(tokens) * int(cents_per_1m)


def _per_call_cost_microcents(calls: int, cents_per_call: int) -> int:
    if calls <= 0 or cents_per_call <= 0:
        return 0
    return int(calls) * int(cents_per_call) * MICROCENTS_PER_CENT


def _per_1k_cost_microcents(count: int, cents_per_1k: int) -> int:
    if count <= 0 or cents_per_1k <= 0:
        return 0
    # microcents = ceil(count * cents_per_1k * 1e6 / 1000)
    return _ceil_div(int(count) * int(cents_per_1k) * MICROCENTS_PER_CENT, 1000)


@dataclass(frozen=True)
class LineItem:
    name: str
    quantity: int
    unit: str
    rate: dict[str, Any]
    cost_microcents: int


def apply_context_cliff_to_rates(rate_card: RateCard, input_tokens: int) -> tuple[int, int, bool, dict[str, Any]]:
    """
    Return (input_rate_cents_per_1m, output_rate_cents_per_1m, applied, configured_dict).

    Keep this consistent with compute_cost_breakdown so preflight WCEC and settlement match.
    """
    input_tokens = max(0, int(input_tokens))
    inp_rate = int(rate_card.input_cents_per_1m)
    out_rate = int(rate_card.output_cents_per_1m)
    cliff_applied = False
    cliff = {
        "threshold_tokens": rate_card.context_cliff_threshold_tokens,
        "input_multiplier": rate_card.context_cliff_input_multiplier,
        "output_multiplier": rate_card.context_cliff_output_multiplier,
    }
    if (
        rate_card.context_cliff_threshold_tokens is not None
        and input_tokens > int(rate_card.context_cliff_threshold_tokens)
    ):
        if rate_card.context_cliff_input_multiplier is not None:
            inp_rate = int((inp_rate * float(rate_card.context_cliff_input_multiplier) + 0.9999999))
            cliff_applied = True
        if rate_card.context_cliff_output_multiplier is not None:
            out_rate = int((out_rate * float(rate_card.context_cliff_output_multiplier) + 0.9999999))
            cliff_applied = True
    return inp_rate, out_rate, cliff_applied, cliff


def compute_cost_breakdown(
    *,
    provider: str,
    model: str,
    rate_card: RateCard,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int | None = None,
    reasoning_tokens: int | None = None,
    cache_write_input_tokens: int | None = None,
    cache_read_input_tokens: int | None = None,
    grounding_queries: int | None = None,
    tool_calls: dict[str, int] | None = None,
) -> dict[str, Any]:
    cached_input_tokens = int(cached_input_tokens or 0)
    reasoning_tokens = int(reasoning_tokens or 0)
    cache_write_input_tokens = int(cache_write_input_tokens or 0)
    cache_read_input_tokens = int(cache_read_input_tokens or 0)
    grounding_queries = int(grounding_queries or 0)
    tool_calls = tool_calls or {}

    input_tokens = max(0, int(input_tokens))
    output_tokens = max(0, int(output_tokens))

    # Clamp provider category counts so odd payloads can't overcharge.
    cached_input_tokens = max(0, min(int(cached_input_tokens), int(input_tokens)))
    cache_write_input_tokens = max(0, int(cache_write_input_tokens))
    cache_read_input_tokens = max(0, int(cache_read_input_tokens))
    if cache_write_input_tokens > input_tokens:
        cache_write_input_tokens = input_tokens
    if cache_read_input_tokens > (input_tokens - cache_write_input_tokens):
        cache_read_input_tokens = max(0, input_tokens - cache_write_input_tokens)
    reasoning_tokens = max(0, min(int(reasoning_tokens), int(output_tokens)))
    grounding_queries = max(0, int(grounding_queries))

    # Apply optional context cliff by adjusting rates (conservatively: round up to whole cents/1m).
    inp_rate, out_rate, cliff_applied, cliff = apply_context_cliff_to_rates(rate_card, input_tokens)

    items: list[LineItem] = []

    # Provider-agnostic default: price total input and output, then optionally refine.
    # Input refinements:
    if cached_input_tokens > 0:
        cached_rate = rate_card.cached_input_cents_per_1m
        uncached_rate = rate_card.uncached_input_cents_per_1m
        if cached_rate is None:
            cached_rate = inp_rate
        if uncached_rate is None:
            uncached_rate = inp_rate
        uncached_tokens = max(0, input_tokens - cached_input_tokens)
        items.append(
            LineItem(
                name="input_tokens_uncached",
                quantity=uncached_tokens,
                unit="tokens",
                rate={"cents_per_1m": int(uncached_rate)},
                cost_microcents=_token_cost_microcents(uncached_tokens, int(uncached_rate)),
            )
        )
        items.append(
            LineItem(
                name="input_tokens_cached",
                quantity=cached_input_tokens,
                unit="tokens",
                rate={"cents_per_1m": int(cached_rate)},
                cost_microcents=_token_cost_microcents(cached_input_tokens, int(cached_rate)),
            )
        )
    elif cache_write_input_tokens > 0 or cache_read_input_tokens > 0:
        write_rate = rate_card.cache_write_input_cents_per_1m or inp_rate
        read_rate = rate_card.cache_read_input_cents_per_1m or inp_rate
        base_tokens = max(0, input_tokens - cache_write_input_tokens - cache_read_input_tokens)
        items.append(
            LineItem(
                name="input_tokens_base",
                quantity=base_tokens,
                unit="tokens",
                rate={"cents_per_1m": int(inp_rate)},
                cost_microcents=_token_cost_microcents(base_tokens, int(inp_rate)),
            )
        )
        items.append(
            LineItem(
                name="input_tokens_cache_write",
                quantity=cache_write_input_tokens,
                unit="tokens",
                rate={"cents_per_1m": int(write_rate)},
                cost_microcents=_token_cost_microcents(cache_write_input_tokens, int(write_rate)),
            )
        )
        items.append(
            LineItem(
                name="input_tokens_cache_read",
                quantity=cache_read_input_tokens,
                unit="tokens",
                rate={"cents_per_1m": int(read_rate)},
                cost_microcents=_token_cost_microcents(cache_read_input_tokens, int(read_rate)),
            )
        )
    else:
        items.append(
            LineItem(
                name="input_tokens",
                quantity=input_tokens,
                unit="tokens",
                rate={"cents_per_1m": int(inp_rate)},
                cost_microcents=_token_cost_microcents(input_tokens, int(inp_rate)),
            )
        )

    # Output refinements:
    if reasoning_tokens > 0 and rate_card.reasoning_output_cents_per_1m is not None:
        reasoning_rate = int(rate_card.reasoning_output_cents_per_1m)
        non_reasoning = max(0, output_tokens - reasoning_tokens)
        items.append(
            LineItem(
                name="output_tokens_non_reasoning",
                quantity=non_reasoning,
                unit="tokens",
                rate={"cents_per_1m": int(out_rate)},
                cost_microcents=_token_cost_microcents(non_reasoning, int(out_rate)),
            )
        )
        items.append(
            LineItem(
                name="output_tokens_reasoning",
                quantity=reasoning_tokens,
                unit="tokens",
                rate={"cents_per_1m": int(reasoning_rate)},
                cost_microcents=_token_cost_microcents(reasoning_tokens, int(reasoning_rate)),
            )
        )
    else:
        items.append(
            LineItem(
                name="output_tokens",
                quantity=output_tokens,
                unit="tokens",
                rate={"cents_per_1m": int(out_rate)},
                cost_microcents=_token_cost_microcents(output_tokens, int(out_rate)),
            )
        )

    # Grounding fees (Gemini-style).
    if grounding_queries > 0 and rate_card.grounding_cents_per_1k_queries is not None:
        items.append(
            LineItem(
                name="grounding_queries",
                quantity=grounding_queries,
                unit="queries",
                rate={"cents_per_1k": int(rate_card.grounding_cents_per_1k_queries)},
                cost_microcents=_per_1k_cost_microcents(grounding_queries, int(rate_card.grounding_cents_per_1k_queries)),
            )
        )

    # Tool fees (OpenAI Responses-style; only when we can observe counts).
    web_search_calls = int(tool_calls.get("web_search_call") or 0)
    if web_search_calls > 0 and rate_card.web_search_cents_per_call is not None:
        items.append(
            LineItem(
                name="tool_web_search_call",
                quantity=web_search_calls,
                unit="calls",
                rate={"cents_per_call": int(rate_card.web_search_cents_per_call)},
                cost_microcents=_per_call_cost_microcents(web_search_calls, int(rate_card.web_search_cents_per_call)),
            )
        )

    file_search_calls = int(tool_calls.get("file_search_call") or 0)
    if file_search_calls > 0 and rate_card.file_search_cents_per_call is not None:
        items.append(
            LineItem(
                name="tool_file_search_call",
                quantity=file_search_calls,
                unit="calls",
                rate={"cents_per_call": int(rate_card.file_search_cents_per_call)},
                cost_microcents=_per_call_cost_microcents(file_search_calls, int(rate_card.file_search_cents_per_call)),
            )
        )

    realized_microcents = sum(it.cost_microcents for it in items)
    return {
        "provider": provider,
        "model": model,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_input_tokens": cached_input_tokens or 0,
            "reasoning_tokens": reasoning_tokens or 0,
            "cache_write_input_tokens": cache_write_input_tokens or 0,
            "cache_read_input_tokens": cache_read_input_tokens or 0,
            "grounding_queries": grounding_queries or 0,
            "tool_calls": tool_calls,
        },
        "cliff": {"configured": cliff, "applied": bool(cliff_applied)},
        "charges": [
            {
                "name": it.name,
                "quantity": it.quantity,
                "unit": it.unit,
                "rate": it.rate,
                "cost_microcents": it.cost_microcents,
            }
            for it in items
        ],
        "totals": {
            "realized_microcents": int(realized_microcents),
            "realized_cents_ceiled": int(cents_ceiled_from_microcents(realized_microcents)),
        },
    }
