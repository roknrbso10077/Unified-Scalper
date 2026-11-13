"""A49 regressions: complete elite rejection attribution and same-candidate HTF relief."""
from __future__ import annotations

from unittest.mock import patch

import main as bot


def _relief_candidate():
    htf = 38.0
    fs = {
        "symbol": "XRP/USDT",
        "candidate_id": "candidate-xrp-1",
        "family": "PULLBACK",
        "strategy_mode": "PULLBACK",
        "strategy_style": "SCALP",
        "macro_regime": "NEUTRAL",
        "local_regime": "LOCAL_BULLISH",
        "macro_severity": "NORMAL",
        "htf_strength": htf,
        "htf_state": "NEUTRAL",
        "setup_quality": 88.0,
        "v643_canonical_quality": 88.0,
        # Frames are only used by the patched fingerprint / evidence functions below.
        "df_5m": object(),
        "df_15m": object(),
    }
    marker = {
        "applied": True,
        "reason": "verified_closed_local_scalp_evidence",
        "family": "PULLBACK",
        "strategy_mode": "PULLBACK",
        "style": "SCALP",
        "regime": "NEUTRAL",
        "local_regime": "LOCAL_BULLISH",
        "severity": "NORMAL",
        "htf_strength": htf,
        "htf_state": "NEUTRAL",
        "minimum_htf": 35.0,
        "alignment_claimed": False,
        "score_floor_unchanged": True,
        "liquidity_fee_stop_gates_unchanged": True,
        "evidence": {"closed_frame_verified": True, "confirmations": 4, "closed_frame_key": "key-5m"},
        "local_15m": {"verified": True, "confirmations": 3},
        "pullback": {
            "applied": True,
            "reason": "strong_closed_local_evidence_compensates_htf_only_near_miss",
            "values": {
                "setup": 88.0, "quality": 88.0, "volume": 1.50,
                "rs": 0.08, "structure": 80.0, "retest": 76.0, "chase": 0.20,
            },
        },
        "a49_candidate_binding": {
            "valid": True,
            "candidate_ref": "candidate-xrp-1",
            "symbol": "XRP/USDT",
            "family": "PULLBACK",
            "strategy_mode": "PULLBACK",
            "style": "SCALP",
            "regime": "NEUTRAL",
            "local_regime": "LOCAL_BULLISH",
            "severity": "NORMAL",
            "htf_strength": htf,
            "htf_state": "NEUTRAL",
            "minimum_htf": 35.0,
            "closed_5m_frame_key": "key-5m",
            "closed_15m_frame_key": "key-15m",
            "local_15m_verified": True,
        },
    }
    fs["v702_a36_scalp_htf_relief"] = marker
    return {
        "symbol": "XRP/USDT",
        "candidate_id": "candidate-xrp-1",
        "family": "PULLBACK",
        "strategy_mode": "PULLBACK",
        "strategy_style": "SCALP",
        "macro_regime": "NEUTRAL",
        "macro_severity": "NORMAL",
        "features_snapshot": fs,
    }


def _patch_fresh_evidence():
    return (
        patch.object(bot, "_v702_a29_closed_evidence", return_value={
            "closed_frame_verified": True, "confirmations": 4, "closed_frame_key": "key-5m",
        }),
        patch.object(bot, "_v702_a36_local_15m_evidence", return_value={"verified": True, "confirmations": 3}),
        patch.object(bot, "_v702_a49_closed_frame_fingerprint", return_value="key-15m"),
    )


def test_same_candidate_verified_a36_pullback_grant_relaxes_only_htf_floor():
    opp = _relief_candidate()
    patches = _patch_fresh_evidence()
    with patches[0], patches[1], patches[2]:
        ok, reason, ctx = bot._v702_elite_live_context_gate(
            opp=opp, score=82.0, htf_strength=38.0, volume_ratio=1.50,
            rs_score_val=6.0, structure_confidence=80.0, retest_quality_score=76.0,
            chase_atr=0.20, tier="MID", regime="NEUTRAL", severity="NORMAL",
        )
    assert ok, reason
    assert ctx["htf_relief_applied"] is True
    assert ctx["htf_floor"] == 50.0  # Canonical strict floor before the verified A36 grant.
    assert ctx["htf_effective_floor"] == 35.0
    assert ctx["score_floor"] >= 70.0
    assert ctx["volume_floor"] == bot._v702_elite_profile(opp)["volume"]
    assert ctx["structure_floor"] == bot._v702_elite_profile(opp)["structure"]
    assert ctx["retest_floor"] == bot._v702_elite_profile(opp)["retest"]
    assert ctx["htf_relief"]["hard_gates_bypassed"] is False


def test_a49_relief_does_not_bypass_volume_or_score_floor():
    opp = _relief_candidate()
    patches = _patch_fresh_evidence()
    with patches[0], patches[1], patches[2]:
        ok, reason, ctx = bot._v702_elite_live_context_gate(
            opp=opp, score=82.0, htf_strength=38.0, volume_ratio=0.01,
            rs_score_val=6.0, structure_confidence=80.0, retest_quality_score=76.0,
            chase_atr=0.20, tier="MID", regime="NEUTRAL", severity="NORMAL",
        )
    assert not ok and reason == "volume_below_floor"
    assert ctx["htf_relief_applied"] is True
    with patches[0], patches[1], patches[2]:
        ok, reason, _ = bot._v702_elite_live_context_gate(
            opp=opp, score=69.0, htf_strength=38.0, volume_ratio=1.50,
            rs_score_val=6.0, structure_confidence=80.0, retest_quality_score=76.0,
            chase_atr=0.20, tier="MID", regime="NEUTRAL", severity="NORMAL",
        )
    assert not ok and reason == "score_below_floor"


def test_missing_or_stale_a36_grant_fails_closed_at_strict_htf_floor():
    opp = _relief_candidate()
    opp["features_snapshot"].pop("v702_a36_scalp_htf_relief")
    ok, reason, ctx = bot._v702_elite_live_context_gate(
        opp=opp, score=82.0, htf_strength=38.0, volume_ratio=1.50,
        rs_score_val=6.0, structure_confidence=80.0, retest_quality_score=76.0,
        chase_atr=0.20, tier="MID", regime="NEUTRAL", severity="NORMAL",
    )
    assert not ok and reason == "htf_below_floor"
    assert ctx["htf_relief_applied"] is False
    assert ctx["htf_effective_floor"] == ctx["htf_floor"] == 50.0

    opp = _relief_candidate()
    patches = _patch_fresh_evidence()
    with patches[0], patches[1], patch.object(bot, "_v702_a49_closed_frame_fingerprint", return_value="changed-key"):
        ok, reason, ctx = bot._v702_elite_live_context_gate(
            opp=opp, score=82.0, htf_strength=38.0, volume_ratio=1.50,
            rs_score_val=6.0, structure_confidence=80.0, retest_quality_score=76.0,
            chase_atr=0.20, tier="MID", regime="NEUTRAL", severity="NORMAL",
        )
    assert not ok and reason == "htf_below_floor"
    assert ctx["htf_relief_applied"] is False


def test_elite_quality_recorder_classifies_every_rejection_family_once():
    cases = {
        "htf_below_floor": "htf",
        "htf_unverifiable": "htf",
        "volume_below_floor": "liquidity",
        "tier_not_allowed": "liquidity",
        "spread_above_floor": "liquidity",
        "score_below_floor": "score",
        "rs_below_floor": "score",
        "structure_below_floor": "structure",
        "retest_below_floor": "structure",
    }
    for reason, expected_taxonomy in cases.items():
        with patch.object(bot, "record_rejection") as recorder:
            taxonomy = bot._v702_a49_record_elite_quality_rejection(
                trace_id="trace-a49", symbol="XRP/USDT", reason=reason,
                score=73.0, family="PULLBACK", mode="PULLBACK", context={"htf": 38.0},
            )
        assert taxonomy == expected_taxonomy
        recorder.assert_called_once()
        args, kwargs = recorder.call_args
        assert args[0:3] == ("trace-a49", "XRP/USDT", expected_taxonomy)
        assert args[3] == f"v702.elite_quality.{reason}"
        assert args[4] == "v702_elite_quality_gate"
        assert kwargs["ctx"]["family"] == "PULLBACK"
        assert kwargs["ctx"]["mode"] == "PULLBACK"
        assert kwargs["ctx"]["quality_reason"] == reason


def test_a49_terminal_contract_keeps_hard_guards_and_global_score_floor():
    report = bot._v702_a49_terminal_self_test()
    assert report["pass"], report
    assert report["hard_gate_bypass"] is False
    assert report["unbounded_live_gates_relaxed"] is False
    assert report["live_network_tested"] is False
    assert report["profitability_verified"] is False
    assert float(bot.CONFIG["MIN_LIVE_SCORE"]) >= 70.0
    assert float(bot.CONFIG["V453_SCORE_FLOOR_MIN"]) >= 70.0
