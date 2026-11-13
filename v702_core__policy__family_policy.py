"""Small policy helpers extracted from the canonical runtime without execution authority."""
from __future__ import annotations
from typing import Any, Mapping


def family_policy_from_config(config: Mapping[str, Any], family: str) -> dict:
    name = str(family or "PULLBACK").upper()
    raw = config.get("FAMILY_POLICY_" + name) or config.get("FAMILY_POLICY_PULLBACK")
    return dict(raw) if isinstance(raw, dict) else {}


def regime_allowed(policy: Mapping[str, Any], regime: str) -> bool:
    """Pure allow-list check for audits/shadow logic; never grants trading authority."""
    allowed = policy.get("allowed_regimes", ()) if isinstance(policy, Mapping) else ()
    normalized = str(regime or "UNKNOWN").strip().upper()
    return normalized in {str(x).strip().upper() for x in (allowed or ())}
