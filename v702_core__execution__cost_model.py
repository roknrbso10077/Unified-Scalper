"""Canonical round-trip trading-cost estimator shared by production and shadow.

All percentages are percentage points (0.10 means 0.10%). A measured all-in
round-trip estimate already includes the observed buy/sell book friction and
venue fees; it must not be combined with fallback spread/fee estimates again.
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


def unified_round_trip_cost_model(
    config: Dict[str, Any],
    *,
    measured_cost_pct: Any = None,
    spread_pct: Any = None,
    fee_cost_pct: Any = None,
) -> Dict[str, float]:
    """Return a conservative all-in estimate without double-counting.

    Precedence:
      1. Measured all-in book/VWAP friction + measured fees + safety buffer.
      2. Otherwise, measured spread (when present) or configured fallback spread,
         plus two-sided slippage and the configured round-trip fee estimate.
      3. An optional operator floor can raise either estimate; by default it is 0.

    This intentionally does *not* assume a universal exchange fee rate. When a
    symbol-specific rate is known, callers should pass its actual round-trip fee
    in ``fee_cost_pct`` or include it in ``measured_cost_pct``.
    """
    cfg = config if isinstance(config, dict) else {}

    floor = _finite(cfg.get("V702_SHADOW_MIN_ROUND_TRIP_COST_PCT", 0.0), 0.0)
    floor = max(0.0, min(5.0, float(floor or 0.0)))

    fallback_spread = _finite(cfg.get("V702_SMALL_NET_SPREAD_FALLBACK_PCT", 0.15), 0.15)
    fallback_spread = max(0.0, min(5.0, float(fallback_spread or 0.0)))

    observed_spread = _finite(spread_pct, None)
    has_observed_spread = observed_spread is not None and observed_spread >= 0.0
    spread_used = max(0.0, min(5.0, observed_spread)) if has_observed_spread else fallback_spread

    slip_side = _finite(cfg.get("V702_SMALL_NET_SLIPPAGE_PER_SIDE_PCT", 0.05), 0.05)
    slip_side = max(0.0, min(2.0, float(slip_side or 0.0)))

    if fee_cost_pct is None:
        fee_side = _finite(cfg.get("TAKER_FEE_PCT", 0.10), 0.10)
        fee_mult = _finite(cfg.get("ROUNDTRIP_FEE_MULT", 2.0), 2.0)
        fee_cost = max(0.0, float(fee_side or 0.0) * float(fee_mult or 0.0))
    else:
        fee_cost = _finite(fee_cost_pct, 0.0)
        fee_cost = max(0.0, float(fee_cost or 0.0))

    buffer = _finite(cfg.get("V702_MEASURED_COST_BUFFER_PCT", 0.05), 0.05)
    buffer = max(0.0, min(1.0, float(buffer or 0.0)))

    measured = _finite(measured_cost_pct, None)
    if measured is not None and measured >= 0.0:
        # The upstream PreSend calculation uses buy VWAP, sell VWAP and the
        # symbol's actual taker fee. Do not add the fallback model a second time.
        measured = max(0.0, min(10.0, measured))
        raw_selected = measured + buffer
        method = 1.0  # 1 = measured all-in + buffer
        fallback_cost = spread_used + 2.0 * slip_side + fee_cost
    else:
        measured = 0.0
        fallback_cost = spread_used + 2.0 * slip_side + fee_cost
        raw_selected = fallback_cost
        method = 0.0  # 0 = spread/fee/slippage fallback

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
