"""Canonical conservative all-in round-trip trading-cost estimator.

All percentages are percentage points (0.10 means 0.10%). Explicit measured
inputs are evidence, not suggestions: invalid values fail closed and large
observed costs are never clipped downward. A measured all-in round-trip value
already includes observed buy/sell book friction and venue fees; it is not
combined with fallback spread/fee estimates a second time.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional


def _finite(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        out = float(value)
        return out if math.isfinite(out) else default
    except (TypeError, ValueError, OverflowError):
        return default


def _nonnegative(value: Any, name: str, *, default: Optional[float] = None) -> float:
    if value is None and default is not None:
        value = default
    parsed = _finite(value, None)
    if parsed is None:
        raise ValueError(f"{name}_missing_or_non_finite")
    if parsed < 0.0:
        raise ValueError(f"{name}_negative")
    return float(parsed)


def unified_round_trip_cost_model(
    config: Dict[str, Any],
    *,
    measured_cost_pct: Any = None,
    spread_pct: Any = None,
    fee_cost_pct: Any = None,
) -> Dict[str, float]:
    """Return a conservative estimate without double counting or optimistic caps.

    Precedence:
      1. Measured all-in friction + measured fees + safety buffer.
      2. Otherwise, observed/configured spread + two-sided slippage + round-trip fee.
      3. An operator floor can raise either estimate.

    Invalid explicit measurement or fee data raises ``ValueError``. The caller
    must then reject/defer the economic decision; NaN must never become zero fees.
    """
    cfg = config if isinstance(config, dict) else {}

    floor = _nonnegative(cfg.get("V702_SHADOW_MIN_ROUND_TRIP_COST_PCT", 0.0),
                         "cost_floor", default=0.0)
    fallback_spread = _nonnegative(cfg.get("V702_SMALL_NET_SPREAD_FALLBACK_PCT", 0.15),
                                   "fallback_spread", default=0.15)
    slip_side = _nonnegative(cfg.get("V702_SMALL_NET_SLIPPAGE_PER_SIDE_PCT", 0.05),
                             "slippage_per_side", default=0.05)

    if spread_pct is None:
        spread_used = fallback_spread
    else:
        spread_used = _nonnegative(spread_pct, "observed_spread")

    if fee_cost_pct is None:
        fee_side = _nonnegative(cfg.get("TAKER_FEE_PCT", 0.10), "taker_fee_side", default=0.10)
        fee_mult = _nonnegative(cfg.get("ROUNDTRIP_FEE_MULT", 2.0), "roundtrip_fee_multiplier", default=2.0)
        fee_cost = fee_side * fee_mult
    else:
        fee_cost = _nonnegative(fee_cost_pct, "measured_fee_cost")

    buffer = _nonnegative(cfg.get("V702_MEASURED_COST_BUFFER_PCT", 0.05),
                          "measured_cost_buffer", default=0.05)

    if measured_cost_pct is not None:
        measured = _nonnegative(measured_cost_pct, "measured_all_in_cost")
        raw_selected = measured + buffer
        method = 1.0
        fallback_cost = spread_used + 2.0 * slip_side + fee_cost
    else:
        measured = 0.0
        fallback_cost = spread_used + 2.0 * slip_side + fee_cost
        raw_selected = fallback_cost
        method = 0.0

    selected = max(floor, raw_selected)
    return {
        "round_trip_cost_pct": float(selected),
        "minimum_cost_pct": float(floor),
        "measured_cost_pct": float(measured),
        "spread_pct_used": float(spread_used),
        "slippage_per_side_pct": float(slip_side),
        "round_trip_fee_pct": float(fee_cost),
        "r40_fallback_cost_pct": float(fallback_cost),
        "measured_cost_buffer_pct": float(buffer if method == 1.0 else 0.0),
        "used_measured_cost": float(method),
    }
