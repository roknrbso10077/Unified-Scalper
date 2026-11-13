"""Bounded event-time buckets that accept out-of-order timestamps safely."""
from __future__ import annotations

from collections import deque
from typing import Deque, MutableMapping


def bump_event_time_bucket(values: MutableMapping[int, int], order: Deque[int], ts: float,
                           amount: int = 1, max_age_sec: int = 3600) -> None:
    """Increment an event-time bucket without treating old event timestamps as clock rollback.

    Eviction records naturally arrive late: the event timestamp belongs to the
    evicted record, not the insertion that caused eviction. Buckets therefore
    remain sorted and are trimmed against the greatest observed event second.
    """
    second = int(float(ts))
    if second not in values:
        if not order or second > int(order[-1]):
            order.append(second)
        else:
            # Rare out-of-order insertion. Preserve stable chronological order;
            # one hour has at most ~3600 distinct keys, so this bounded insert is cheap.
            ordered = sorted(set(int(x) for x in order) | {second})
            order.clear()
            order.extend(ordered)
    values[second] = int(values.get(second, 0) or 0) + int(amount)
    newest = int(order[-1]) if order else second
    cutoff = newest - max(60, int(max_age_sec))
    while order and int(order[0]) < cutoff:
        expired = int(order.popleft())
        values.pop(expired, None)
