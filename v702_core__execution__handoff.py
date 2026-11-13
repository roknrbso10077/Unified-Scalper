"""Pure classification helper for a candidate that passed PreSend but has no queue evidence."""
from __future__ import annotations


def presend_queue_gap_reason(presend_seen: bool, queued_seen: bool, *, same_candidate: bool = True) -> str | None:
    if not presend_seen or queued_seen or not same_candidate:
        return None
    return "presend_pass_without_candidate_queue_evidence"
