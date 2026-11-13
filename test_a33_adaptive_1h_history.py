"""A33 regressions: align local 1H admission with A32 short 4H policy."""
import pandas as pd
import main as bot


def _frame(rows, rising=True):
    close = [1.0 + i * 0.005 for i in range(rows)] if rising else [1.0] * rows
    return pd.DataFrame({
        "open": close, "high": [x * 1.01 for x in close],
        "low": [x * 0.99 for x in close], "close": close,
        "volume": [1000.0] * rows,
    })


def _frames(n1=214, n4=52):
    return {"df_4h": _frame(n4), "df_1h": _frame(n1),
            "df_15m": _frame(350), "df_5m": _frame(30)}


def test_a33_is_canonical_and_preserves_hard_execution_invariants():
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A35_CANONICAL_REVISION + "-A36-")
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A32_CANONICAL_REVISION + "-A33-")
    assert bot.FINAL_CANONICAL_RUNTIME["package_audit_revision"].startswith(bot.V702_A35_CANONICAL_REVISION + "-A36-")
    assert bot.CONFIG["LONG_ONLY"] is True
    assert str(bot.CONFIG["MARKET_TYPE"]).upper() == "SPOT"
    assert not bot.CONFIG.get("ENABLE_FUTURES", False)
    assert not bot.CONFIG.get("ALLOW_SHORT", False)
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70
    assert bot.CONFIG["LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME"] >= 3_000_000
    assert bot.CONFIG["V45_TIER_MICRO_MIN_DEPTH_RATIO"] >= 1.90
    assert bot.CONFIG["MIN_TP1_TO_FEE_RATIO"] >= 2.5
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False


def test_scan_admits_214_rows_when_4h_has_at_least_50_valid_rows():
    ok, reason = bot._mse_candidate_scan_precheck(_frames())
    assert ok and reason == "ok", reason
    assert bot._v702_a33_local_1h_min_closed_candles(_frames()) == 210
    assert bot.CONFIG["V702_A33_LOCAL_1H_FULL_HISTORY_TARGET"] >= 240


def test_scan_rejects_209_rows_without_synthetic_padding():
    frames = _frames(n1=209)
    before = len(frames["df_1h"])
    ok, reason = bot._mse_candidate_scan_precheck(frames)
    assert not ok
    assert reason == "df_1h:short_rows:got=209,required=210", reason
    assert len(frames["df_1h"]) == before


def test_timestamped_1h_gap_is_rejected_even_when_row_count_passes():
    # Fixed clock and closed-only bars make this independent of the hour at
    # which pytest happens to run. The final row is the last CLOSED candle;
    # the in-progress candle is deliberately not appended.
    current_open = pd.Timestamp("2026-10-15T15:00:00Z")
    now_ms = int((current_open + pd.Timedelta(minutes=5)).timestamp() * 1000)
    index = pd.date_range(end=current_open - pd.Timedelta(hours=1), periods=211, freq="h", tz="UTC")
    valid = _frame(len(index))
    valid.index = index
    assert index[-1] == current_open - pd.Timedelta(hours=1)
    assert index[-1] < current_open
    assert bot._v702_a33_local_1h_history_integrity(valid, 210, now_ms=now_ms) == (True, "ok")
    gap_idx = index.delete(10)
    gap = valid.drop(valid.index[10]).copy()
    gap.index = gap_idx
    ok, reason = bot._v702_a33_local_1h_history_integrity(gap, 210, now_ms=now_ms)
    assert not ok and "candle_gap_detected" in reason, reason


def test_a33_terminal_self_test_is_repeatable_with_frozen_history_clock():
    first = bot._v702_a33_terminal_self_test()
    first_checks = dict(first.get("checks", {}))
    second = bot._v702_a33_terminal_self_test()
    assert first.get("pass") is True, first.get("failed")
    assert second.get("pass") is True, second.get("failed")
    assert first_checks == second.get("checks")
    assert second["checks"]["timestamp_fixture_ends_at_last_closed_bar"] is True


def test_short_4h_and_1h_proxy_uses_closed_history_and_caps_confidence():
    snap = {"symbol": "A33/USDT", "htf_strength": 0.0, "htf_state": "UNKNOWN",
            "htf_reason": "insufficient_data", "df_1h": _frame(214), "df_4h": _frame(52)}
    score, source, _ = bot._v702_a33_resolve_htf_strength("A33/USDT", snap)
    assert source == "RECOMPUTED_H0", (score, source, snap.get("htf_recompute_reason"))
    assert score is not None and 0 <= score <= 50
    assert snap["htf_evidence_class"] == "HTF_LIMITED_HISTORY"
    assert snap["htf_1h_history_minimum"] == 210
    assert snap["htf_history_confidence_cap"] <= 50


def test_active_resolver_does_not_recompute_over_credible_crash_evidence():
    snap = {"symbol": "CRASH/USDT", "htf_strength": 0.0, "htf_state": "BEARISH_CRASH",
            "htf_reason": "bearish_crash_evidence", "df_1h": _frame(214), "df_4h": _frame(52)}
    score, source, _ = bot._v702_a33_resolve_htf_strength("CRASH/USDT", snap)
    # The legacy resolver has precedence for credible bearish evidence; no short-history
    # bullish proxy is allowed to replace the crash decision.
    assert source != "RECOMPUTED_H0", (score, source, snap)


def test_a33_terminal_self_test_passes_without_enabling_gate_bypass():
    report = bot._v702_a33_terminal_self_test()
    assert report["pass"] is True, report
    assert report["hard_gate_bypass"] is False
    assert report["live_gates_relaxed"] is False


def test_builder_snapshot_gate_uses_same_conditional_1h_minimum_as_scanner():
    snap = {
        "df_5m": _frame(30), "df_15m": _frame(350), "df_1h": _frame(214), "df_4h": _frame(52),
        "df_btc_5m": _frame(60), "df_btc_15m": _frame(80), "df_btc_1h": _frame(80), "df_btc_4h": _frame(241),
        "btc_context_age_sec": 0.0, "symbol": "SNAP/USDT", "regime": "NEUTRAL",
        "macro_regime": "NEUTRAL", "local_regime": "LOCAL_NEUTRAL", "macro_severity": 0,
        "bearish_severity": 0, "market_phase": "RANGE", "btc_context": {},
        "htf_strength": 50.0, "tier": "MID",
    }
    ok, reason = bot.validate_mse_snapshot(snap)
    assert ok and reason == "ok", (ok, reason, bot.STATS.get("mse_snapshot_invalid_diagnostic"))
    snap["df_1h"] = _frame(209)
    ok, reason = bot.validate_mse_snapshot(snap)
    assert not ok and reason == "mse_snapshot_invalid"
    assert str(bot.STATS.get("mse_snapshot_invalid_detail", "")).endswith(":df_1h")


def test_prequal_root_diagnostic_uses_recent_rejections_only_with_zero_selection(monkeypatch):
    recent = [
        (bot.WALL_NOW() - 10, "prequal_reject", {"reason": "htf.bearish_crash_guard"}),
        (bot.WALL_NOW() - 8, "prequal_reject", {"reason": "htf.bearish_crash_guard"}),
        (bot.WALL_NOW() - 6, "prequal_reject", {"reason": "liquidity.depth_ratio_below_floor"}),
    ]
    monkeypatch.setattr(bot._V456_EVENTS, "items", lambda window_sec, kind=None: recent if kind == "prequal_reject" else [])
    monkeypatch.setattr(bot.V702PipelineMetrics, "snapshot", classmethod(lambda cls: {"enabled": True, "cycle_counts": {"SELECTED": 0}}))
    heartbeat = "state=FULL_LIVE_RUNNING funnel=20/0/0/0 ENTRY_STATUS=BLOCKED:NO_LIVE_READY"
    root, age = bot._v702_a7_entry_block_summary(heartbeat)
    assert root == "HTF" and 0 <= age < 30, (root, age)

    monkeypatch.setattr(bot.V702PipelineMetrics, "snapshot", classmethod(lambda cls: {"enabled": True, "cycle_counts": {"SELECTED": 1}}))
    root, age = bot._v702_a7_entry_block_summary(heartbeat)
    assert root == "NONE" and age == -1, (root, age)
