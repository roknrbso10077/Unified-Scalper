"""Canonical hard-deny asset policy shared by runtime and shadow telemetry.

This list is a safety restriction, not a strategy preference. Shadow lanes must
never study assets that the canonical execution guard rejects.
"""
from __future__ import annotations

HARD_FORBIDDEN_BASES = frozenset({"AERO", "BNB", "CAKE", "ETHFI", "PUMP"})


def base_asset(symbol: object) -> str:
    """Normalize a market symbol to its base asset without guessing unknowns."""
    value = str(symbol or "").strip().upper().replace("-", "/").replace("_", "/")
    if ":" in value:
        value = value.split(":", 1)[0]
    if "/" in value:
        return value.split("/", 1)[0].strip()
    for quote in ("USDT", "USDC", "BUSD", "USD"):
        if value.endswith(quote) and len(value) > len(quote):
            return value[:-len(quote)]
    return value


def is_hard_forbidden(symbol: object) -> bool:
    base = base_asset(symbol)
    return bool(base and base in HARD_FORBIDDEN_BASES)
