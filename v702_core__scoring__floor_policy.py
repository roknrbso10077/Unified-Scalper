"""Canonical live-score floor rules; paper/shadow scores remain separate."""
from __future__ import annotations

HARD_LIVE_SCORE_FLOOR = 70.0
MAX_CONFIGURABLE_LIVE_SCORE_FLOOR = 80.0


def effective_live_floor(configured_floor: float = 70.0, base_floor: float = 70.0,
                         bounded_relief: float = 0.0) -> float:
    """Return the canonical live floor. Relief can never take it below 70."""
    return max(HARD_LIVE_SCORE_FLOOR, float(configured_floor), float(base_floor) - max(0.0, float(bounded_relief)))


def valid_configured_floor(value: float) -> bool:
    try:
        x = float(value)
        return x == x and HARD_LIVE_SCORE_FLOOR <= x <= MAX_CONFIGURABLE_LIVE_SCORE_FLOOR
    except (TypeError, ValueError):
        return False
