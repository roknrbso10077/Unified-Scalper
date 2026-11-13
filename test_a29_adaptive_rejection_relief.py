"""A29 focused regressions: safe soft-quality relief, diagnostics and history deferral."""
import math
from datetime import datetime, timezone

import pandas as pd
import main as bot


def _closed_5m_frame(rows=60):
    # Keep the final completed bar current so freshness tests exercise logic,
    # not a historical fixture that has naturally become stale.
    now = pd.Timestamp.now(tz="UTC").floor("5min")
    idx = pd.date_range(end=now, periods=rows, freq="5min", tz="UTC")
    values = []
    for i in range(rows):
        close = 100.0 + 0.08 * i
        values.append({"open": close - 0.03, "high": close + 0.12,
                       "low": 95.0 + 0.07 * i, "close": close,
                       "volume": 1000.0 + i * 3.0})
    # Force a clear higher-low, bullish close and zone reclaim at iloc[-2].
    values[-4]["low"] = 97.30
    values[-3]["low"] = 97.40
    values[-3]["close"] = 102.00
    values[-2]["low"] = 97.55
    values[-2]["open"] = 102.01
    values[-2]["close"] = 102.40
    values[-1]["open"] = values[-1]["close"] - 0.01  # potentially open candle is ignored
    df = pd.DataFrame(values, index=idx)
    return df


def _quality_candidate(df5=None, **overrides):
    fs = {
        "family": "PULLBACK", "strategy_mode": "PULLBACK", "macro_regime": "BULLISH",
        "local_regime": "LOCAL_BULLISH", "htf_state": "BULLISH", "htf_reason": "aligned",
        "htf_strength": 90.0, "volume_ratio": 0.80, "rs_5m": 0.07,
        "structure_confidence": 85.0, "retest_quality_score": 85.0,
        "chase_atr": 0.20, "v587_setup_quality": 90.0,
        "v587_pullback_confirmations": 4, "zone_ref": 102.20,
    }
    fs.update(overrides)
    if df5 is not None:
        fs["df_5m"] = df5
    return {"family": "PULLBACK", "strategy_mode": "PULLBACK", "features_snapshot": fs}


def _quality_record(**overrides):
    q = {"htf_strength": 90.0, "volume_ratio": 0.80, "rs_5m": 0.07,
         "structure": 85.0, "retest": 85.0, "chase": 0.20,
         "quality": 86.0, "confirmations": 4, "reason": "volume_below_floor", "ok": False}
    q.update(overrides)
    return q


def test_a29_revision_is_append_only_and_hard_policy_is_unchanged():
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A35_CANONICAL_REVISION + "-A36-")
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A28_CANONICAL_REVISION + "-A29-")
    assert float(bot.CONFIG["MIN_LIVE_SCORE"]) >= 70.0
    assert float(bot.CONFIG["LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME"]) >= 3_000_000.0
    assert float(bot.CONFIG["V45_TIER_MICRO_MIN_DEPTH_RATIO"]) >= 1.90
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False
    assert bot.CONFIG["LONG_ONLY"] and str(bot.CONFIG["MARKET_TYPE"]).upper() == "SPOT"
    assert {"AERO", "BNB", "CAKE", "ETHFI", "PUMP"}.issubset(set(bot.V702_HARD_FORBIDDEN_BASES))


def test_a29_single_volume_near_miss_can_pass_only_with_strong_independent_closed_bar_evidence():
    candidate = _quality_candidate(_closed_5m_frame())
    ok, ctx = bot._v702_a29_pb_quality_relief_decision(candidate, {"df_5m": candidate["features_snapshot"]["df_5m"]},
                                                        "volume", _quality_record())
    assert ok, ctx
    assert ctx["applied"] is True
    assert ctx["reason"] == "one_near_miss_compensated_by_independent_evidence"
    assert "volume" not in ctx.get("support", [])
    assert ctx["evidence"]["closed_frame_verified"] is True
    assert ctx["confirmations"] >= 3

    # Exercise the actual V587 quality wrapper with the runtime candidate type.
    runtime_candidate = bot.StrategyCandidate(
        engine_id="pullback", symbol="TEST/USDT", side="long", generated_at_ms=1791957600000,
        entry_ref=102.4, sl_price=100.0, tp1_rr=1.5, tp2_rr=2.5, tp3_rr=4.0,
        engine_score=0.9, rr_ratio=2.0, liquidity_score=0.95, regime_fit=0.95,
        family="PULLBACK", zone_ref=102.20,
        features_snapshot=dict(candidate["features_snapshot"]), strategy_mode="PULLBACK",
        macro_regime="BULLISH", local_regime="LOCAL_BULLISH",
    )
    df5 = candidate["features_snapshot"]["df_5m"]
    def frame(freq, periods=35):
        idx = pd.date_range(end=pd.Timestamp.now(tz="UTC").floor("5min"), periods=periods, freq=freq, tz="UTC")
        values = []
        for i in range(periods):
            close = 100.0 + i * 0.04
            values.append({"open": close - 0.02, "high": close + 0.12,
                           "low": close - 0.10, "close": close, "volume": 1500.0 + i})
        return pd.DataFrame(values, index=idx)
    market_data = {"df_5m": df5, "df_15m": frame("15min"),
                   "df_1h": frame("1h"), "df_4h": frame("4h"),
                   "quote_vol_24h": 5_000_000.0, "spread_pct": 0.05,
                   "htf_strength": 90.0, "depth_ratio": 3.0}
    q = bot._v702_a29_v587_pullback_quality(runtime_candidate, market_data)
    assert "a29_closed_evidence" in q, q
    assert q["a29_closed_evidence"]["closed_frame_verified"] is True


def test_a29_refuses_multiple_near_misses_or_unverified_closed_bars():
    df5 = _closed_5m_frame()
    candidate = _quality_candidate(df5, htf_strength=49.0)
    ok, ctx = bot._v702_a29_pb_quality_relief_decision(candidate, {"df_5m": df5}, "volume", _quality_record(htf_strength=49.0))
    assert not ok
    assert ctx["reason"] == "multiple_or_mismatched_soft_failures"

    no_df_candidate = _quality_candidate(None, htf_strength=90.0)
    ok, ctx = bot._v702_a29_pb_quality_relief_decision(no_df_candidate, {}, "volume", _quality_record())
    assert not ok
    assert ctx["reason"] == "closed_candle_confirmation_insufficient"

    # The one-soft-miss allowance is candidate-wide, not independently reusable
    # at each pipeline stage.
    already_htf_relieved = _quality_candidate(df5, htf_strength=90.0)
    already_htf_relieved["features_snapshot"]["v702_a29_contextual_htf_relief"] = {
        "applied": True, "quality_decision": {"failed_metric": "htf"}
    }
    ok, ctx = bot._v702_a29_pb_quality_relief_decision(already_htf_relieved, {"df_5m": df5}, "volume", _quality_record())
    assert not ok
    assert ctx["reason"] == "prior_soft_relief_already_used_for_another_metric"


def test_a29_feature_flags_cannot_fabricate_closed_bar_confirmations():
    # A valid timestamp/index alone is not proof that bullish closed-bar
    # confirmations occurred; contradictory/stale feature flags are diagnostic only.
    now = pd.Timestamp.now(tz="UTC").floor("5min")
    idx = pd.date_range(end=now, periods=60, freq="5min", tz="UTC")
    values = []
    for i in range(60):
        low = 99.9 - i * 0.005
        values.append({"open": 100.1, "high": 100.2, "low": low,
                       "close": 100.0, "volume": 1000.0})
    df = pd.DataFrame(values, index=idx)
    candidate = _quality_candidate(
        df,
        reclaim=True,
        higher_low=True,
        bos_confirmed=True,
        bullish_close=True,
        bullish_candle_confirmed=True,
        ema20_slope_up=True,
        local_recovery_confirmed=True,
        zone_ref=110.0,
    )
    evidence = bot._v702_a29_closed_evidence(candidate, {"df_5m": df})
    assert evidence["valid_closed_frame"] is True
    assert evidence["confirmations"] == 0, evidence
    assert evidence["closed_frame_verified"] is False, evidence


def test_a29_elite_gate_relieves_only_one_soft_metric_but_never_score_or_chase():
    df5 = _closed_5m_frame()
    candidate = _quality_candidate(df5)
    candidate["features_snapshot"]["v702_a29_closed_bar_evidence_verified"] = True
    candidate["features_snapshot"]["v587_pullback_confirmations"] = 4
    common = dict(opp=candidate, htf_strength=90.0, volume_ratio=0.80, rs_score_val=8.0,
                  structure_confidence=80.0, retest_quality_score=65.0, chase_atr=0.30, tier="MID")
    ok, reason, ctx = bot._v702_a29_elite_context_gate(score=82.0, **common)
    assert ok and reason == "pass_a29_selective_relief", (reason, ctx)
    assert ctx["a29_relief_metric"] == "volume"
    assert ctx["hard_score_floor_preserved"] is True

    ok, reason, _ = bot._v702_a29_elite_context_gate(score=74.0, **common)
    assert not ok  # below profile score + required safety margin
    common2 = dict(common)
    common2["htf_strength"] = 49.0
    ok, reason, _ = bot._v702_a29_elite_context_gate(score=82.0, **common2)
    assert not ok  # two soft misses are not compensated

    common3 = dict(common)
    common3["chase_atr"] = 0.95
    ok, reason, _ = bot._v702_a29_elite_context_gate(score=82.0, **common3)
    assert not ok  # chase stays hard

    prior_relief_candidate = _quality_candidate(df5)
    prior_relief_candidate["features_snapshot"]["v702_a29_contextual_htf_relief"] = {
        "applied": True, "quality_decision": {"failed_metric": "htf"}
    }
    common4 = dict(common)
    common4["opp"] = prior_relief_candidate
    ok, reason, ctx = bot._v702_a29_elite_context_gate(score=82.0, **common4)
    assert not ok
    assert ctx.get("a29_relief_denied") == "prior_soft_relief_already_used_for_another_metric"


def test_a29_score_band_65_to_70_is_shadow_only_and_selftest_does_not_pollute_it():
    before = int(bot.STATS.get("v702_a29_score_shadow_count", 0) or 0)
    result = bot._v702_a29_record_score_shadow(symbol="TEST/USDT", score=67.0, floor=70.0, family="PULLBACK")
    assert result["recorded"] and result["routes"] is False
    assert bot.STATS["v702_a29_score_shadow_count"] == before + 1
    assert bot._v702_a29_record_score_shadow(symbol="TEST/USDT", score=64.99, floor=70.0)["recorded"] is False
    after_call = int(bot.STATS["v702_a29_score_shadow_count"])
    report = bot._v702_a29_terminal_self_test()
    assert report["pass"], report
    assert int(bot.STATS["v702_a29_score_shadow_count"]) == after_call
    assert report["score_65_69_live_admission"] is False


def test_a29_short_history_cache_rechecks_ambiguous_short_history_after_bounded_ttl():
    bot._V702_A29_SHORT_HISTORY_CACHE.clear()
    interval = 4 * 60 * 60 * 1000
    now_dt = pd.Timestamp("2026-10-14T05:30:00Z")
    now_ms = int(now_dt.timestamp() * 1000)
    current_open = now_ms - (now_ms % interval)
    first_closed = current_open - interval - 119 * interval
    rows = []
    for i in range(120):
        stamp = first_closed + i * interval
        px = 1.0 + i * 0.001
        rows.append([stamp, px, px + 0.01, px - 0.01, px, 1000.0])
    assert rows[-1][0] == current_open - interval
    assert bot._v702_a29_history_cache_put(
        "YOUNG/USDT", rows, {"complete": False, "reason": "short_history", "required_rows": 210}, now_ms
    ) is True
    cached = bot._v702_a29_history_cache_get("YOUNG/USDT", now_ms + 60_000)
    assert cached is not None
    closed_rows, info = cached
    assert len(closed_rows) == 120 and info["required"] == 50
    assert info["target_rows"] == 210
    assert info["reason"] == "admissible_partial_4h_history_reuse"
    assert info["cache_policy"] == "BOUNDED_NEGATIVE_CACHE"
    assert all(int(row[0]) < current_open for row in closed_rows)
    assert info["no_stale_open_candle_reused"] is True
    # A short/empty response is not proof of a new listing. Revalidate after the
    # configured bounded TTL (or earlier at the next 4H boundary), not four hours later.
    assert bot._V702_A29_SHORT_HISTORY_CACHE["YOUNG/USDT"]["valid_after_ms"] == now_ms + 420_000
    assert bot._v702_a29_history_cache_get("YOUNG/USDT", now_ms + 421_000) is None
    assert "YOUNG/USDT" not in bot._V702_A29_SHORT_HISTORY_CACHE


def test_a29_htf_relief_is_pullback_only_and_requires_the_one_near_miss_contract():
    candidate = _quality_candidate(
        _closed_5m_frame(), htf_strength=42.0, volume_ratio=1.20,
        structure_confidence=100.0, retest_quality_score=100.0, chase_atr=0.20,
        v587_setup_quality=90.0,
    )
    ok, ctx = bot._v702_a29_pullback_htf_relief_allowed(
        candidate, {"df_5m": candidate["features_snapshot"]["df_5m"]},
        family="PULLBACK", strategy_mode="PULLBACK", regime="BULLISH",
        local_regime="LOCAL_BULLISH", severity="NORMAL", htf_state="BULLISH",
        htf_strength=42.0, htf_reason="contextual_floor",
    )
    assert ok, ctx
    assert ctx["alignment_claimed"] is False
    candidate["family"] = "MTF_PULLBACK"
    ok, ctx = bot._v702_a29_pullback_htf_relief_allowed(
        candidate, {"df_5m": candidate["features_snapshot"]["df_5m"]},
        family="MTF_PULLBACK", strategy_mode="MTF_PULLBACK", regime="BULLISH",
        local_regime="LOCAL_BULLISH", severity="NORMAL", htf_state="BULLISH",
        htf_strength=42.0, htf_reason="contextual_floor",
    )
    assert not ok


def test_a29_closed_bar_evidence_rejects_stale_or_snapshot_mismatched_confirmation_markers():
    fresh = _closed_5m_frame()
    candidate = _quality_candidate(fresh, v702_a29_closed_bar_evidence_verified=True,
                                   v587_pullback_confirmations=4)
    first = bot._v702_a29_closed_evidence(candidate, {"df_5m": fresh})
    assert first["frame_fresh"] is True, first
    assert first["closed_frame_verified"] is True, first
    assert first["closed_frame_key"]

    stale = fresh.copy()
    stale.index = stale.index - pd.Timedelta(hours=2)
    stale_candidate = _quality_candidate(stale, v702_a29_closed_bar_evidence_verified=True,
                                         v702_a29_closed_bar_evidence_key=first["closed_frame_key"],
                                         v587_pullback_confirmations=4)
    evidence = bot._v702_a29_closed_evidence(stale_candidate, {"df_5m": stale})
    assert evidence["frame_fresh"] is False, evidence
    assert evidence["closed_frame_verified"] is False, evidence
    assert evidence["prior_validated_closed_frame"] is False, evidence

    revised = fresh.copy()
    revised.iloc[-2, revised.columns.get_loc("close")] += 0.25
    revised_candidate = _quality_candidate(revised, v702_a29_closed_bar_evidence_verified=True,
                                           v702_a29_closed_bar_evidence_key=first["closed_frame_key"],
                                           v587_pullback_confirmations=4)
    revised_evidence = bot._v702_a29_closed_evidence(revised_candidate, {"df_5m": revised})
    assert revised_evidence["closed_frame_key"] != first["closed_frame_key"]
    assert revised_evidence["prior_validated_closed_frame"] is False

    future = fresh.copy()
    future.index = future.index + pd.Timedelta(hours=2)
    future_candidate = _quality_candidate(future, v702_a29_closed_bar_evidence_verified=True,
                                          v702_a29_closed_bar_evidence_key=first["closed_frame_key"],
                                          v587_pullback_confirmations=4)
    future_evidence = bot._v702_a29_closed_evidence(future_candidate, {"df_5m": future})
    assert future_evidence["frame_fresh"] is False, future_evidence
    assert future_evidence["closed_frame_verified"] is False, future_evidence


def test_a29_history_cache_temporarily_throttles_empty_older_page_and_is_bounded():
    bot._V702_A29_SHORT_HISTORY_CACHE.clear()
    interval = 4 * 60 * 60 * 1000
    now_ms = int(pd.Timestamp("2026-10-14T05:30:00Z").timestamp() * 1000)
    current_open = now_ms - (now_ms % interval)
    rows = []
    for i in range(120):
        stamp = current_open - interval * (120 - i)
        px = 1.0 + i * 0.001
        rows.append([stamp, px, px + 0.01, px - 0.01, px, 1000.0])
    assert bot._v702_a29_history_cache_put(
        "NO_OLDER/USDT", rows,
        {"complete": False, "reason": "recovery_page_added_no_rows", "pages": 2,
         "required_rows": 210, "synthetic_rows": 0}, now_ms,
    ) is True
    cached = bot._v702_a29_history_cache_get("NO_OLDER/USDT", now_ms + 60_000)
    assert cached is not None
    assert len(cached[0]) == 120
    assert cached[1]["reason"] == "admissible_partial_4h_history_reuse"
    assert cached[1]["cache_policy"] == "BOUNDED_NEGATIVE_CACHE"
    # A blank older-page result is ambiguous; it can only suppress repeated reads
    # for the bounded TTL and then must retry the full data path.
    assert bot._v702_a29_history_cache_get("NO_OLDER/USDT", now_ms + 421_000) is None

    # Transport/API failures are not evidence that the listing is genuinely
    # young; those cases must remain retryable and must never enter this cache.
    assert bot._v702_a29_history_cache_put(
        "API_TIMEOUT/USDT", rows,
        {"complete": False, "reason": "timeout", "pages": 3,
         "required_rows": 210, "synthetic_rows": 0}, now_ms,
    ) is False
    assert bot._v702_a29_history_cache_get("API_TIMEOUT/USDT", now_ms + 60_000) is None

    old_cap = bot.CONFIG.get("V702_A29_SHORT_HISTORY_CACHE_MAX", 512)
    try:
        bot.CONFIG["V702_A29_SHORT_HISTORY_CACHE_MAX"] = 64
        bot._V702_A29_SHORT_HISTORY_CACHE.clear()
        short_rows = rows[-3:]
        for i in range(65):
            assert bot._v702_a29_history_cache_put(
                f"CAP{i:02d}/USDT", short_rows,
                {"complete": False, "reason": "short_history", "required_rows": 210,
                 "synthetic_rows": 0}, now_ms,
            ) is True
        assert len(bot._V702_A29_SHORT_HISTORY_CACHE) == 64
        assert int(bot.STATS.get("v702_a29_local_history_cache_evictions", 0) or 0) >= 1
    finally:
        bot.CONFIG["V702_A29_SHORT_HISTORY_CACHE_MAX"] = old_cap
        bot._V702_A29_SHORT_HISTORY_CACHE.clear()
