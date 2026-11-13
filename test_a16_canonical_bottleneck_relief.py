"""A16 regressions for bounded pullback gate alignment and non-starving cooldowns."""
from __future__ import annotations

import asyncio
import os
import tempfile
from types import SimpleNamespace

os.environ.setdefault("SCALPER_DB", os.path.join(tempfile.gettempdir(), f"v702-a16-tests-{os.getpid()}.db"))
import pandas as pd
import main as bot


def test_a16_terminal_selftest_passes_and_hard_invariants_stay_enabled():
    report = bot._v702_a16_bottleneck_relief_self_test()
    assert report["pass"], report
    assert report["hard_gate_bypass"] is False
    assert report["global_score_floor"] >= 70.0
    assert bot.CONFIG["LONG_ONLY"] is True
    assert bot.CONFIG["MARKET_TYPE"] == "SPOT"
    assert {"AERO", "BNB", "CAKE", "ETHFI", "PUMP"}.issubset(set(bot.V702_HARD_FORBIDDEN_BASES))
    assert bot.CONFIG["LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME"] >= 3_000_000.0
    assert bot.CONFIG["V45_TIER_MICRO_MIN_DEPTH_RATIO"] >= 1.90


def test_pullback_elite_gate_aligns_with_canonical_contract_not_old_82_70_55_stack():
    profile = bot._v702_elite_profile({"family": "PULLBACK", "strategy_mode": "PULLBACK",
                                      "features_snapshot": {"setup_quality": 72.0}})
    assert profile["score"] == 70.0
    assert profile["htf"] == 50.0
    assert profile["volume"] == 0.85
    assert profile["rs_points"] == 2.0
    assert profile["structure"] == 55.0
    assert profile["retest"] == 45.0
    assert profile["setup"] == 72.0
    assert profile["chase"] == 0.90


def test_elite_pullback_gate_passes_at_aligned_floor_but_keeps_hard_controls():
    opp = {"family": "PULLBACK", "strategy_mode": "PULLBACK",
           "features_snapshot": {"setup_quality": 72.0}}
    common = dict(opp=opp, score=70.0, htf_strength=50.0, volume_ratio=0.85,
                  rs_score_val=2.0, structure_confidence=55.0,
                  retest_quality_score=45.0, chase_atr=0.90, tier="MID")
    ok, reason, _ = bot._v702_elite_live_context_gate(**common)
    assert ok and reason == "pass"

    checks = [
        ({"score": 69.99}, "score_below_floor"),
        ({"htf_strength": 49.99}, "htf_below_floor"),
        ({"volume_ratio": 0.849}, "volume_below_floor"),
        ({"structure_confidence": 54.99}, "structure_below_floor"),
        ({"retest_quality_score": 44.99}, "retest_below_floor"),
        ({"chase_atr": 0.901}, "chase_above_ceiling"),
    ]
    for overrides, expected in checks:
        result = bot._v702_elite_live_context_gate(**{**common, **overrides})
        assert not result[0] and result[1] == expected, (overrides, result)


def test_scan_cooldown_disposition_only_keeps_same_strategy_same_closed_candle():
    stored = {"candle_key": "C1", "strategy_mode": "PULLBACK"}
    assert bot._v702_a16_scan_cooldown_disposition(stored, "C1", "PULLBACK") == "KEEP_SAME_STRATEGY_CANDLE"
    assert bot._v702_a16_scan_cooldown_disposition(stored, "C2", "PULLBACK") == "RESET_NEW_CLOSED_CANDLE"
    assert bot._v702_a16_scan_cooldown_disposition(stored, "C1", "LIQUIDITY_SWEEP_REVERSAL") == "RESET_ALTERNATE_STRATEGY"
    assert bot._v702_a16_scan_cooldown_disposition(stored, None, "PULLBACK") == "KEEP_UNVERIFIABLE_CANDLE"


def test_builder_wrapper_releases_old_symbol_cooldown_for_new_closed_candle(monkeypatch):
    symbol = "A16COOLDOWN/USDT"
    df = pd.DataFrame({"close": [1.0, 1.01, 1.02]}, index=pd.date_range("2026-10-12", periods=3, freq="5min"))
    key = bot._v702_a16_closed_5m_candle_key({"df_5m": df})
    candidate = SimpleNamespace(symbol=symbol, family="PULLBACK", strategy_mode="PULLBACK")
    cooldowns = {"symbol_scan": {symbol: 123.0}}
    monkeypatch.setattr(bot, "COOLDOWNS", cooldowns, raising=True)
    monkeypatch.setattr(bot, "_V702_A16_SCAN_COOLDOWN_CONTEXT",
                        {symbol: {"candle_key": "OLD-CANDLE", "strategy_mode": "PULLBACK", "ts": 123.0}},
                        raising=True)
    called = {"value": False}

    async def fake_builder(exchange, sym, market_data, preferred_candidate=None):
        called["value"] = True
        assert sym == symbol
        assert symbol not in bot.COOLDOWNS["symbol_scan"]
        return None

    monkeypatch.setattr(bot, "_V702_A16_PREV_BUILD_AND_ROUTE", fake_builder, raising=True)
    out = asyncio.run(bot.SignalBuilder.build_and_route(
        object(), symbol, {"df_5m": df}, preferred_candidate=candidate
    ))
    assert out is None
    assert called["value"] is True
    assert bot._v702_a16_closed_5m_candle_key({"df_5m": df}) == key


def test_alternate_strategy_retries_without_disabling_reentry_cooldown():
    # The scan-cooldown policy only permits alternate strategies/new candles;
    # the independent post-exit reentry timer remains owned by the canonical builder.
    stored = {"candle_key": "C1", "strategy_mode": "PULLBACK"}
    assert bot._v702_a16_scan_cooldown_disposition(stored, "C1", "LIQUIDITY_SWEEP_REVERSAL") == "RESET_ALTERNATE_STRATEGY"
    assert "reentry" in bot.COOLDOWNS


def test_candle_key_rejects_numeric_duplicate_and_unsorted_indices():
    numeric = pd.DataFrame({"close": [1.0, 2.0, 3.0]})
    assert bot._v702_a16_closed_5m_candle_key({"df_5m": numeric}) is None
    unsorted = pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=pd.to_datetime(["2026-10-12 00:10", "2026-10-12 00:05", "2026-10-12 00:15"], utc=True))
    assert bot._v702_a16_closed_5m_candle_key({"df_5m": unsorted}) is None
    duplicate = pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=pd.to_datetime(["2026-10-12 00:00", "2026-10-12 00:05", "2026-10-12 00:05"], utc=True))
    assert bot._v702_a16_closed_5m_candle_key({"df_5m": duplicate}) is None


def test_candle_key_is_normalized_utc_and_uses_only_closed_candle():
    df = pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=pd.date_range("2026-10-12", periods=3, freq="5min"))
    key = bot._v702_a16_closed_5m_candle_key({"df_5m": df})
    assert key == "2026-10-12T00:05:00+00:00"
