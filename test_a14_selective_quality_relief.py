"""A14 regressions: align redundant secondary score/HTF gates without bypassing hard gates."""
from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace

os.environ.setdefault("SCALPER_DB", os.path.join(tempfile.gettempdir(), f"v702-a14-tests-{os.getpid()}.db"))
import main as bot


def test_secondary_elite_score_floor_matches_global_minimum_by_family():
    families = (
        "PULLBACK", "MTF_PULLBACK", "LIQUIDITY_SWEEP_REVERSAL",
        "BREAKOUT_RETEST", "BREAKOUT_CONTINUATION", "MEASURED_MOVE",
        "LOCAL_STRENGTH_BREAKOUT", "MOMENTUM_EXPANSION", "MEAN_REVERSION",
        "CONTINUATION_RECLAIM", "FAILED_BREAKOUT_RECLAIM", "COMPRESSION_EXPANSION",
    )
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70.0
    assert all(
        bot._v702_live_quality_score_floor({"family": f, "strategy_mode": f, "features_snapshot": {}}) == 70.0
        for f in families
    )


def test_strong_pullback_can_pass_at_70_but_weak_volume_cannot():
    opp = {"family": "PULLBACK", "strategy_mode": "PULLBACK", "features_snapshot": {"setup_quality": 82.0}}
    common = dict(opp=opp, score=70.0, htf_strength=72.0, rs_score_val=4.0,
                  structure_confidence=70.0, retest_quality_score=55.0,
                  chase_atr=0.60, tier="MID")
    ok, reason, _ = bot._v702_elite_live_context_gate(volume_ratio=0.95, **common)
    assert ok and reason == "pass"
    weak, weak_reason, _ = bot._v702_elite_live_context_gate(volume_ratio=0.50, **common)
    assert not weak and weak_reason == "volume_below_floor"


def test_scores_below_70_remain_blocked():
    opp = {"family": "PULLBACK", "strategy_mode": "PULLBACK", "features_snapshot": {"setup_quality": 90.0}}
    ok, reason, _ = bot._v702_elite_live_context_gate(
        opp=opp, score=69.99, htf_strength=90.0, volume_ratio=1.20,
        rs_score_val=6.0, structure_confidence=90.0,
        retest_quality_score=90.0, chase_atr=0.20, tier="MID")
    assert not ok and reason == "score_below_floor"


def test_local_strength_still_requires_htf_volume_rs_structure_and_chase():
    opp = {"family": "LOCAL_STRENGTH_BREAKOUT", "strategy_mode": "LOCAL_STRENGTH_BREAKOUT", "features_snapshot": {}}
    ok, reason, _ = bot._v702_elite_live_context_gate(
        opp=opp, score=70.0, htf_strength=75.0, volume_ratio=1.20,
        rs_score_val=6.0, structure_confidence=80.0,
        retest_quality_score=55.0, chase_atr=0.40, tier="MID")
    assert ok and reason == "pass"
    weak_htf, reason_htf, _ = bot._v702_elite_live_context_gate(
        opp=opp, score=70.0, htf_strength=74.9, volume_ratio=1.20,
        rs_score_val=6.0, structure_confidence=80.0,
        retest_quality_score=55.0, chase_atr=0.40, tier="MID")
    assert not weak_htf and reason_htf == "htf_below_floor"
    weak_structure, reason_structure, _ = bot._v702_elite_live_context_gate(
        opp=opp, score=70.0, htf_strength=75.0, volume_ratio=1.20,
        rs_score_val=6.0, structure_confidence=79.9,
        retest_quality_score=55.0, chase_atr=0.40, tier="MID")
    assert not weak_structure and reason_structure == "structure_below_floor"


def test_projected_builder_floor_tracks_new_policy_without_lowering_global_floor():
    candidate = SimpleNamespace(
        symbol="A14TEST/USDT", family="PULLBACK", strategy_mode="PULLBACK",
        strategy_style="SCALP", macro_regime="BULLISH", features_snapshot={"setup_quality": 82.0},
    )
    floors = bot._v702_projected_builder_score_floors(candidate, {"regime": "BULLISH"}, 72.0, {})
    assert floors["is_live"] is True
    assert floors["elite_floor"] == 70.0
    assert floors["effective_floor"] == 70.0
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70.0


def test_risk_and_execution_guardrails_are_unchanged():
    cfg = bot.CONFIG
    assert float(cfg.get("LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME", 3_000_000.0)) >= 3_000_000.0
    assert float(cfg.get("V45_TIER_MICRO_MIN_DEPTH_RATIO", 1.90)) >= 1.90
    assert cfg["LONG_ONLY"] is True
    assert str(cfg.get("MARKET_TYPE", "SPOT")).upper() == "SPOT"
    assert not cfg.get("ENABLE_FUTURES", False) and not cfg.get("FUTURES_ENABLED", False)
    assert not cfg.get("ALLOW_SHORT", False) and not cfg.get("ALLOW_SHORTS", False)
    assert {"AERO", "BNB", "CAKE", "ETHFI", "PUMP"}.issubset(set(bot.V702_HARD_FORBIDDEN_BASES))
    assert int(cfg.get("MAX_CONCURRENT_TRADES", 2)) <= 2
    assert float(cfg.get("MAX_ENTRY_NOTIONAL_USDT", 75.0)) <= 75.0
    assert bot.FINAL_CANONICAL_RUNTIME.get("hard_gate_bypass", False) is False


def test_a14_terminal_selftest_passes():
    report = bot._v702_a14_selective_relief_self_test()
    assert report["pass"], report
    assert report["hard_gate_bypass"] is False
    assert report["global_score_floor"] >= 70.0
    assert report["execution_policy_changed"] is False
