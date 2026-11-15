from __future__ import annotations

from pathlib import Path

from collections import deque
from unittest.mock import patch

import main as bot
from v702_core__execution__handoff import presend_queue_gap_reason
from v702_core__pipeline__event_time_buckets import bump_event_time_bucket
from v702_core__policy__family_policy import regime_allowed
from v702_core__scoring__floor_policy import (
    HARD_LIVE_SCORE_FLOOR,
    MAX_CONFIGURABLE_LIVE_SCORE_FLOOR,
    effective_live_floor,
    valid_configured_floor,
)


def test_event_time_bucket_accepts_delayed_evictions_without_resetting_history():
    values: dict[int, int] = {}
    order: deque[int] = deque()
    bump_event_time_bucket(values, order, 1003, 2)
    bump_event_time_bucket(values, order, 1004, 1)
    bump_event_time_bucket(values, order, 990, 3)
    assert list(order) == sorted(order)
    assert values == {990: 3, 1003: 2, 1004: 1}
    bump_event_time_bucket(values, order, 1003, 4)
    assert values[1003] == 6


def test_score_floor_is_hard_70_with_explicit_70_to_80_config_range():
    assert HARD_LIVE_SCORE_FLOOR == 70.0
    assert MAX_CONFIGURABLE_LIVE_SCORE_FLOOR == 80.0
    assert effective_live_floor(70, 70, 20) == 70.0
    assert effective_live_floor(75, 70, 20) == 75.0
    assert all(valid_configured_floor(v) for v in (70, 72.5, 80))
    assert not any(valid_configured_floor(v) for v in (69.99, 80.01, float("nan")))


def test_a48_floor_parser_does_not_mask_explicit_invalid_configuration():
    parse_floor = bot._v702_a48_configured_score_floor_value
    assert parse_floor(70.0) == 70.0
    assert parse_floor(0.0) == 0.0
    assert not valid_configured_floor(parse_floor(0.0))
    assert not valid_configured_floor(parse_floor(False))
    assert not valid_configured_floor(parse_floor(None))
    assert not valid_configured_floor(parse_floor(""))


def test_canonical_reject_facade_keeps_candidate_stage_source_and_reason():
    with patch.object(bot.V702PipelineMetrics, "reject", return_value=True) as recorder:
        ok = bot.record_reject(
            trace_id="trace-a48", symbol="ABC/USDT", taxonomy="liquidity",
            reason="micro_spread_above_floor", stage="prequal", source="arbiter",
            ctx={"evidence": "fresh_orderbook"}, candidate_key="candidate-a48",
        )
    assert ok is True
    recorder.assert_called_once()
    args, kwargs = recorder.call_args
    assert args[:5] == ("trace-a48", "ABC/USDT", "liquidity", "micro_spread_above_floor", "prequal")
    assert kwargs["candidate_key"] == "candidate-a48"
    assert kwargs["source"] == "arbiter"
    assert args[5]["source"] == "arbiter"
    assert args[5]["taxonomy"] == "liquidity"
    assert args[5]["evidence"] == "fresh_orderbook"


def test_presend_queue_gap_is_candidate_scoped_and_observability_only():
    assert presend_queue_gap_reason(True, False, same_candidate=True) == "presend_pass_without_candidate_queue_evidence"
    assert presend_queue_gap_reason(True, True, same_candidate=True) is None
    assert presend_queue_gap_reason(True, False, same_candidate=False) is None
    assert presend_queue_gap_reason(False, False, same_candidate=True) is None
    source = Path(bot.__file__).read_text(encoding="utf-8")
    assert 'source": "V702_A48_QUEUE_RECONCILIATION' in source
    assert '"queued_seen"' not in source or "_v702_presend_queue_gap_reason" in source


def test_tp1_and_score_reasons_keep_searchable_diagnostics():
    token = bot._v702_reason_summary_token(
        "family_tp1_distance_below_floor:tp1_atr=0.612<0.700", 40
    )
    assert token == "tp1_floor:0.612<0.700"
    assert bot._v702_reason_summary_token("score_below_feasible_floor:62.2+2.0<70.0", 32) == "score_below_feasible_floor"


def test_bearish_bridge_remains_shadow_only_and_current_policy_is_fail_closed():
    policy = bot.FamilyPolicyLayer.get_family_policy("PULLBACK")
    assert not regime_allowed(policy, "BEARISH")
    assert bot.CONFIG["V702_A48_BEARISH_V518_LIVE_ENABLE"] is False
    assert bot.CONFIG["V702_A48_BEARISH_NORMAL_SHADOW_ONLY"] is True
    assert bot.CONFIG["V702_A48_BEARISH_SHADOW_FAMILY"] == "LIQUIDITY_SWEEP_REVERSAL"
    assert bot.CONFIG["V702_A48_BEARISH_SHADOW_MIN_HTF_STRENGTH"] == 47.0
    assert bot.CONFIG["V702_A48_BEARISH_SHADOW_VOLUME_FLOOR_RATIO"] == 1.4
    assert bot.CONFIG["V702_A48_BEARISH_SHADOW_SIZE_MULTIPLIER"] == 0.5
    import v702_counterfactual_shadow as shadow
    assert "BEARISH_NORMAL_LSR" in shadow.LANES


def test_a48_historical_authority_is_preserved_under_active_a49_release():
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A48_CANONICAL_REVISION + "-A49-ELITE-HTF-RELIEF-CONSISTENCY-AND-REJECT-ATTRIBUTION-2026-10-19")
    assert bot.FINAL_CANONICAL_RUNTIME["package_audit_revision"] == bot.V702_PACKAGE_AUDIT_REVISION
    assert bot.FINAL_CANONICAL_RUNTIME["canonical_revision"] == bot.V702_R38_FINAL_CANONICAL_REVISION
    assert bot.FINAL_CANONICAL_RUNTIME["terminal_authority"] == "V702-R38"
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False
    assert bot.FINAL_CANONICAL_RUNTIME["live_gates_relaxed"] is False
