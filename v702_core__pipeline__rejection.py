"""Canonical facade for candidate rejection telemetry.

The runtime passes its existing metrics recorder into this adapter so legacy
V410/V455 events and V702 pipeline events share one signature without creating
an independent counter or changing any admission decision.
"""
from __future__ import annotations
from typing import Any, Callable, Mapping


def record_reject(recorder: Callable[..., Any], *, trace_id: str = "", symbol: str = "",
                  taxonomy: str = "", reason: str = "", stage: str = "unknown",
                  source: str = "unknown", context: Mapping[str, Any] | None = None,
                  candidate_key: str = "") -> bool:
    if not callable(recorder):
        return False
    details = dict(context or {})
    details.update({"source": str(source or "unknown")[:80],
                    "taxonomy": str(taxonomy or "")[:80]})
    return bool(recorder(trace_id, symbol, taxonomy, reason, stage, details,
                         candidate_key=candidate_key, source=source))
