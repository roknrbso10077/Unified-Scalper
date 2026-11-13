"""A17 regression tests: shared BTC context caching and safe early quarantine."""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("SCALPER_DB", os.path.join(tempfile.gettempdir(), f"v702-a17-tests-{os.getpid()}.db"))
import numpy as np
import pandas as pd
import main as bot


def macro_frame(n=260, *, start=50.0, end=110.0):
    idx = pd.date_range("2026-01-01", periods=n, freq="4h", tz="UTC")
    close = np.linspace(start, end, n)
    return pd.DataFrame({"close": close, "low": close - 0.8, "high": close + 0.8}, index=idx)


def severity_frame(n=64):
    idx = pd.date_range("2026-10-01", periods=n, freq="15min", tz="UTC")
    close = np.linspace(70.0, 71.0, n)
    return pd.DataFrame({"close": close, "high": close + 0.6, "low": close - 0.6}, index=idx)


def test_a17_terminal_selftest_passes_and_preserves_hard_invariants():
    report = bot._v702_a17_production_self_test()
    assert report["pass"], report
    assert report["hard_gate_bypass"] is False
    assert report["gates_relaxed"] is False
    assert report["execution_policy_changed"] is False


def test_a17_macro_cache_reuses_valid_frame_and_invalidates_on_content_change(monkeypatch):
    old = bot.OrderedDict(bot._V702_A17_MACRO_CONTEXT_CACHE)
    bot._V702_A17_MACRO_CONTEXT_CACHE.clear()
    calls = {"n": 0}
    original = bot._V702_A17_PREV_MACRO_CONTEXT

    def counted(frame):
        calls["n"] += 1
        return original(frame)

    monkeypatch.setattr(bot, "_V702_A17_PREV_MACRO_CONTEXT", counted)
    try:
        df = macro_frame()
        a = bot._v702_a17_macro_context_cached(df)
        b = bot._v702_a17_macro_context_cached(df)
        assert a == b and calls["n"] == 1
        df.iloc[-2, df.columns.get_loc("close")] += 1.0
        c = bot._v702_a17_macro_context_cached(df)
        assert c[0] in {"BULLISH", "BEARISH", "NEUTRAL"} and calls["n"] == 2
        assert len(bot._V702_A17_MACRO_CONTEXT_CACHE) <= bot._V702_A17_MACRO_CACHE_MAX
    finally:
        bot._V702_A17_MACRO_CONTEXT_CACHE.clear()
        bot._V702_A17_MACRO_CONTEXT_CACHE.update(old)


def test_a17_invalid_macro_inputs_are_not_cached(monkeypatch):
    bot._V702_A17_MACRO_CONTEXT_CACHE.clear()
    calls = {"n": 0}
    original = bot._V702_A17_PREV_MACRO_CONTEXT

    def counted(frame):
        calls["n"] += 1
        return original(frame)

    monkeypatch.setattr(bot, "_V702_A17_PREV_MACRO_CONTEXT", counted)
    try:
        assert bot._v702_a17_macro_context_cached(None)[0] == "UNKNOWN"
        assert bot._v702_a17_macro_context_cached(None)[0] == "UNKNOWN"
        assert calls["n"] == 2
        assert len(bot._V702_A17_MACRO_CONTEXT_CACHE) == 0
    finally:
        bot._V702_A17_MACRO_CONTEXT_CACHE.clear()


def test_a17_severity_cache_reuses_valid_pair_and_invalidates_changed_frame(monkeypatch):
    old = bot.OrderedDict(bot._V702_A17_BEARISH_SEVERITY_CACHE)
    bot._V702_A17_BEARISH_SEVERITY_CACHE.clear()
    calls = {"n": 0}
    original = bot._V702_A17_PREV_BEARISH_SEVERITY

    def counted(df15, df4):
        calls["n"] += 1
        return original(df15, df4)

    monkeypatch.setattr(bot, "_V702_A17_PREV_BEARISH_SEVERITY", counted)
    try:
        df15, df4 = severity_frame(), macro_frame()
        a = bot._v702_a17_bearish_severity_cached(df15, df4)
        b = bot._v702_a17_bearish_severity_cached(df15, df4)
        assert a == b and calls["n"] == 1, (a, b, calls)
        df15.iloc[-2, df15.columns.get_loc("close")] += 0.25
        c = bot._v702_a17_bearish_severity_cached(df15, df4)
        assert c[1] in {"bearish_crash_confirmed", "bearish_stressed", "bearish_normal"}
        assert calls["n"] == 2
        assert len(bot._V702_A17_BEARISH_SEVERITY_CACHE) <= bot._V702_A17_SEVERITY_CACHE_MAX
    finally:
        bot._V702_A17_BEARISH_SEVERITY_CACHE.clear()
        bot._V702_A17_BEARISH_SEVERITY_CACHE.update(old)


def test_a17_rank_filters_missing_and_short_shared_macro_before_engine_fanout(monkeypatch):
    good = macro_frame()
    short = good.iloc[:100].copy()
    received = {}

    def spy(mapping):
        received.update(mapping)
        return ["delegated"]

    monkeypatch.setattr(bot, "_V702_A17_PREV_RANK_AND_SELECT", spy)
    result = bot.GlobalOpportunityBrain.rank_and_select({
        "GOOD/USDT": {"df_btc_4h": good},
        "MISSING/USDT": {"df_btc_4h": None},
        "SHORT/USDT": {"df_btc_4h": short},
    })
    assert result == ["delegated"]
    assert list(received) == ["GOOD/USDT"]
    diag = bot.STATS.get("v702_a17_macro_prefilter_last", {})
    assert diag.get("seen") == 3 and diag.get("pass") == 1 and diag.get("blocked") == 2, diag
    assert diag.get("fail_closed") is True


def test_a17_all_invalid_macro_cycle_resets_mse_counts_and_runs_no_engines(monkeypatch):
    received = {}
    reset = {"count": 0}

    def spy_rank(mapping):
        received.update(mapping)
        return []

    original_reset = bot._MSEState.reset_run_counts

    def count_reset(cls):
        reset["count"] += 1
        return original_reset()

    monkeypatch.setattr(bot, "_V702_A17_PREV_RANK_AND_SELECT", spy_rank)
    monkeypatch.setattr(bot._MSEState, "reset_run_counts", classmethod(count_reset))
    before = int(bot.STATS.get("v702_a17_empty_macro_cycle_counts_reset", 0) or 0)
    result = bot.GlobalOpportunityBrain.rank_and_select({"BAD/USDT": {"df_btc_4h": None}})
    assert result == [] and received == {}
    assert reset["count"] == 1
    assert int(bot.STATS.get("v702_a17_empty_macro_cycle_counts_reset", 0) or 0) == before + 1


def test_a17_heartbeat_displays_macro_quarantine_and_cache_counters():
    saved = {k: bot.STATS.get(k) for k in ("v702_a17_macro_prefilter_last", "v702_a17_macro_cache_hits", "v702_a17_macro_cache_misses", "v702_a17_severity_cache_hits", "v702_a17_severity_cache_misses")}
    try:
        bot.STATS["v702_a17_macro_prefilter_last"] = {"seen": 10, "pass": 4, "blocked": 6, "reasons": {"macro_frame_missing": 6}, "fail_closed": True}
        bot.STATS["v702_a17_macro_cache_hits"] = 8
        bot.STATS["v702_a17_macro_cache_misses"] = 2
        bot.STATS["v702_a17_severity_cache_hits"] = 5
        bot.STATS["v702_a17_severity_cache_misses"] = 1
        line = bot._V702R28TelegramDigest._heartbeat_line("Heartbeat state=FULL_LIVE_RUNNING")
        assert "A17_MACRO_PREFILTER=seen:10,pass:4,block:6,top:macro_frame_missingx6" in line
        assert "A17_MACRO_CACHE=8/2" in line and "A17_SEVERITY_CACHE=5/1" in line
    finally:
        for k, value in saved.items():
            if value is None:
                bot.STATS.pop(k, None)
            else:
                bot.STATS[k] = value
