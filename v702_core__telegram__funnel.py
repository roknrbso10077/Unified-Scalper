"""Opportunity-message taxonomy for Telegram funnel attribution."""
from __future__ import annotations

OPPORTUNITY_HEADLINES = (
    "🟢 <b>BUY OPPORTUNITY — READY FOR SUBMISSION</b>",
    "🟢 <b>BUY OPPORTUNITY — PENDING FINAL GATES</b>",
    "🟠 <b>HIGH-QUALITY OPPORTUNITY — EXECUTION BLOCKED</b>",
)


def is_canonical_opportunity_message(message: object) -> bool:
    text = str(message or "").lstrip()
    return any(text.startswith(headline) for headline in OPPORTUNITY_HEADLINES)
