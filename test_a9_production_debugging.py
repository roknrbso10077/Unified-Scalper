"""A9 regression coverage for book handoff diagnostics, macro compatibility and Shadow metrics."""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("SCALPER_DB", str(Path(tempfile.gettempdir()) / f"v702-a9-tests-{os.getpid()}.db"))
import main
from v702_intraday_shadow import STRATEGIES, V702IntradayShadow


def _book():
    return {
        "bids": [[1.000, 2200.0], [0.999, 1900.0], [0.998, 1800.0], [0.997, 1700.0], [0.996, 1600.0]],
        "asks": [[1.001, 700.0], [1.002, 650.0], [1.003, 600.0], [1.004, 550.0], [1.005, 500.0]],
    }


class _MockExchange:
    def __init__(self, error_symbols=()):
        self.calls = []
        self.error_symbols = set(error_symbols)

    async def fetch_order_book(self, symbol, limit=20):
        self.calls.append((symbol, limit))
        if symbol in self.error_symbols:
            raise RuntimeError("synthetic_api_error")
        return _book()


def test_a9_prefetch_attaches_exact_fresh_orderbook_and_never_fetches_blacklist():
    async def run():
        old_cap = main.CONFIG.get("V702_A9_ORDERBOOK_PREFETCH_MAX_SYMBOLS_PER_CYCLE")
        main.CONFIG["V702_A9_ORDERBOOK_PREFETCH_MAX_SYMBOLS_PER_CYCLE"] = 8
        try:
            market = {
                "DOT/USDT": {"symbol":"DOT/USDT", "quote_vol_24h":1_250_000.0, "tier":"MICRO", "spread_pct":0.22},
                "PUMP/USDT": {"symbol":"PUMP/USDT", "quote_vol_24h":1_350_000.0, "tier":"MICRO", "spread_pct":0.10},
            }
            ex = _MockExchange()
            result = await main._v702_a9_prefetch_micro_orderbooks(ex, market)
            assert result["eligible"] == 1
            assert result["attempted"] == result["fetched_fresh"] == 1
            assert result["forbidden_skips"] == 1
            assert [x[0] for x in ex.calls] == ["DOT/USDT"]
            snap = market["DOT/USDT"]
            assert snap["v702_a9_orderbook_prefetch_status"] == "FETCHED_FRESH"
            assert snap["orderbook"] == snap["depth"] == snap["_v703_route_score_orderbook"]
            assert snap["orderbook_ts"] == snap["spread_ts"] == snap["depth_ts"]
            assert snap["depth_ratio"] == 0.0  # validator must derive depth from the exact fetched book
            assert abs(snap["spread_pct"] - 0.09995) < 0.01
            assert main._v702_a9_orderbook_levels_valid(snap["orderbook"])[0] is True
            # Candidate snapshot construction must retain the very same book payload.
            candidate_snapshot = main.GlobalOpportunityBrain._snapshot("DOT/USDT", snap)
            assert candidate_snapshot["orderbook"] == snap["orderbook"]
            assert candidate_snapshot["_v703_route_score_orderbook"] == snap["orderbook"]
            assert candidate_snapshot["orderbook_ts"] == snap["orderbook_ts"]
        finally:
            if old_cap is not None:
                main.CONFIG["V702_A9_ORDERBOOK_PREFETCH_MAX_SYMBOLS_PER_CYCLE"] = old_cap
    asyncio.run(run())


def test_a9_orderbook_missing_cause_separates_api_timeout_deferred_stale_and_transfer():
    store = main._v702_a9_ob_status_store()
    store.clear()
    cases = [
        ("API/USDT", {"status":"API_ERROR", "source":"MEXC", "error":"429"}, "api_error"),
        ("TIMEOUT/USDT", {"status":"TIMEOUT", "source":"MEXC"}, "timeout"),
        ("DEFER/USDT", {"status":"DEFERRED_BUDGET", "source":"budget"}, "not_fetched_budget"),
        ("FRESH/USDT", {"status":"FETCHED_FRESH", "source":"prefetch"}, "snapshot_not_transferred"),
    ]
    for symbol, state, expected in cases:
        store[symbol] = {**state, "ts": main.WALL_NOW()}
        cause, _detail = main._v702_a9_orderbook_missing_cause(symbol, {}, {})
        assert cause == expected, (symbol, cause, expected)
    stale_ts = main.WALL_NOW() - float(main.CONFIG.get("V702_A9_ORDERBOOK_PREFETCH_MAX_AGE_SEC", 15.0)) - 10.0
    cause, detail = main._v702_a9_orderbook_missing_cause("STALE/USDT", {"orderbook_ts":stale_ts}, {})
    assert cause == "stale" and detail["age_sec"] > 15.0
    cause, _ = main._v702_a9_orderbook_missing_cause("NEVER/USDT", {}, {})
    assert cause == "not_fetched"


def test_a9_prefetch_api_error_is_not_misreported_as_missing_data():
    async def run():
        market = {"ADA/USDT": {"symbol":"ADA/USDT", "quote_vol_24h":1_400_000.0, "tier":"MICRO"}}
        result = await main._v702_a9_prefetch_micro_orderbooks(_MockExchange({"ADA/USDT"}), market)
        assert result["attempted"] == 1
        assert result["api_errors"] == 1
        assert result["fetched_fresh"] == 0
        cause, detail = main._v702_a9_orderbook_missing_cause("ADA/USDT", market["ADA/USDT"], {})
        assert cause == "api_error"
        assert "synthetic_api_error" in detail.get("error", "")
    asyncio.run(run())


def test_a9_micro_handoff_requires_a_timestamped_book_and_preserves_hard_fails():
    candidate = SimpleNamespace(
        symbol="DOT/USDT", family="PULLBACK", strategy_mode="PULLBACK", strategy_style="SCALP",
        side="long", generated_at_ms=int(main.WALL_NOW()*1000), engine_score=80.0,
        entry_ref=1.0, sl_price=0.99, tp1_rr=2.0, tp2_rr=3.0, tp3_rr=4.0, chase_atr=0.2,
        features_snapshot={"volume_ratio":1.2,"structure_confidence":80.0,"structure_quality":80.0,"chase_atr":0.2,"depth_ratio":0.0},
    )
    now = main.WALL_NOW()
    snap = {"symbol":"DOT/USDT", "tier":"MICRO", "quote_vol_24h":1_200_000.0,"spread_pct":0.10,"spread_ts":now,
            "depth_ratio":0.0,"volume_ratio":1.2,"structure_confidence":80.0,"structure_quality":80.0,"orderbook":_book()}
    ok, reason, _ = main._v702_a7_micro_handoff_evidence(candidate, snap, tier="MICRO", record=False)
    assert not ok and reason == "orderbook_timestamp_missing"
    snap.update({"orderbook_ts":now,"book_ts":now,"depth_ts":now})
    ok, reason, _ = main._v702_a7_micro_handoff_evidence(candidate, snap, tier="MICRO", record=False)
    assert ok, reason
    snap["orderbook_ts"] = now - 60.0
    ok, reason, _ = main._v702_a7_micro_handoff_evidence(candidate, snap, tier="MICRO", record=False)
    assert not ok and reason == "orderbook_stale"


def test_a9_regime_matrix_matches_canonical_policy_and_does_not_open_bearish_pullback():
    matrix = main.STATS["v702_a9_regime_compatibility_matrix"]
    assert matrix["checked_mode_regime_cells"] > 0
    assert matrix["mismatch_count"] == 0, matrix.get("mismatches")
    pullback = matrix["matrix"]["PULLBACK"]["actual"]
    assert pullback["NEUTRAL"] == "ALLOW"
    assert pullback["BEARISH"] == "MACRO"
    ok, reason, _ = main.FamilyPolicyLayer.regime_policy_detail(
        " PULLBACK ", " NEUTRAL ", strategy_mode=" PULLBACK ", local_regime="", market_phase="", severity="", strategy_style=""
    )
    assert ok, reason
    ok, reason, _ = main.FamilyPolicyLayer.regime_policy_detail(
        "PULLBACK", "BEARISH", strategy_mode="PULLBACK", local_regime="", market_phase="", severity="", strategy_style=""
    )
    assert not ok and reason == "macro"
    ok, reason, _ = main.FamilyPolicyLayer.regime_policy_detail(
        "PULLBACK", "NON_BEARISH", strategy_mode="PULLBACK", local_regime="", market_phase="", severity="", strategy_style=""
    )
    assert not ok and reason == "macro"  # noncanonical macro remains fail-closed


def test_a9_shadow_skip_and_report_keep_all_four_independent_engines():
    import pandas as pd
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as tmp:
        cfg = {"V702_INTRADAY_SHADOW_ENABLE":True,"V702_INTRADAY_SHADOW_LIVE_ENABLE":False,
               "V702_INTRADAY_SHADOW_MIN_QUOTE_VOLUME_USDT":1_000_000,"V702_INTRADAY_SHADOW_MIN_1M_CANDLES":40,
               "TAKER_FEE_PCT":0.1,"V702_INTRADAY_SPREAD_FALLBACK_PCT":0.15,"V702_INTRADAY_SLIPPAGE_PER_SIDE_PCT":0.05}
        study = V702IntradayShadow(str(Path(tmp)/"shadow.db"), tmp, config_getter=lambda:cfg)
        idx = pd.date_range("2026-10-11T10:00:00Z", periods=12, freq="min")
        frame = pd.DataFrame([{"open":100.0,"high":100.1,"low":99.9,"close":100.0,"volume":100.0} for _ in idx], index=idx)
        result = study.process_symbol("DOT/USDT", frame, {"symbol":"DOT/USDT","quote_vol_24h":1_500_000.0,"tier":"MICRO"})
        assert set(result["engine_cycle"]) == set(STRATEGIES)
        for mode in STRATEGIES:
            assert result["engine_cycle"][mode]["evaluated"] == 1
            assert result["engine_cycle"][mode]["skipped"] == 1
            assert "closed_1m_bars_insufficient" in result["engine_cycle"][mode]["reject_reasons"]
        report = study.report()
        assert set(report["strategies"]) == set(STRATEGIES)
        for mode in STRATEGIES:
            row = report["strategies"][mode]
            assert all(key in row for key in ("evaluations","signals","rejections","rejection_reasons","post_cost_target_viable_signals","post_cost_target_capped_signals","avg_signal_cost_pct"))


def test_a9_reusing_fresh_book_does_not_refresh_original_capture_timestamp():
    async def run():
        captured = main.WALL_NOW() - 5.0
        book = _book()
        md = {
            "symbol": "DOT/USDT", "quote_vol_24h": 1_500_000.0, "tier": "MICRO",
            "orderbook": book, "depth": book, "_v703_route_score_orderbook": book,
            "orderbook_ts": captured, "book_ts": captured, "depth_ts": captured,
            "spread_ts": captured, "spread_pct": 0.09995,
        }
        result = await main._v702_a9_prefetch_micro_orderbooks(_MockExchange(), {"DOT/USDT": md})
        assert result["reused_fresh"] == 1 and result["attempted"] == 0
        for key in ("orderbook_ts", "book_ts", "depth_ts", "spread_ts", "v703_route_orderbook_captured_ts"):
            assert abs(float(md[key]) - captured) < 0.25, (key, md[key], captured)
        assert float(md["v702_a9_orderbook_checked_ts"]) >= captured + 4.0
        assert float(md["v702_a9_orderbook_prefetch_ts"]) == float(md["orderbook_ts"])
    asyncio.run(run())


def test_a9_missing_cause_prefers_stale_capture_over_success_status_and_rejects_future_time():
    store = main._v702_a9_ob_status_store()
    store.clear()
    max_age = float(main.CONFIG.get("V702_A9_ORDERBOOK_PREFETCH_MAX_AGE_SEC", 15.0))
    stale_ts = main.WALL_NOW() - max_age - 25.0
    store["STALE/USDT"] = {"status": "FETCHED_FRESH", "ts": main.WALL_NOW(), "book_ts": stale_ts,
                           "source": "V702_A9_PREFETCH_EXACT_BOOK"}
    cause, detail = main._v702_a9_orderbook_missing_cause(
        "STALE/USDT", {"v702_a9_orderbook_prefetch_status": "FETCHED_FRESH", "orderbook_ts": stale_ts}, {}
    )
    assert cause == "stale" and detail["age_sec"] > max_age
    future_ts = main.WALL_NOW() + 60.0
    cause, detail = main._v702_a9_orderbook_missing_cause(
        "FUTURE/USDT", {"orderbook_ts": future_ts}, {}
    )
    assert cause == "future_timestamp" and detail["age_sec"] < 0


def test_a9_handoff_rejects_future_orderbook_timestamp_fail_closed():
    now = main.WALL_NOW()
    candidate = SimpleNamespace(
        symbol="DOT/USDT", family="PULLBACK", strategy_mode="PULLBACK", strategy_style="SCALP",
        side="long", generated_at_ms=int(now * 1000), engine_score=80.0,
        entry_ref=1.0, sl_price=0.99, tp1_rr=2.0, tp2_rr=3.0, tp3_rr=4.0, chase_atr=0.2,
        features_snapshot={"volume_ratio":1.2,"structure_confidence":80.0,"structure_quality":80.0,"chase_atr":0.2,"depth_ratio":0.0},
    )
    future = now + 60.0
    snap = {"symbol":"DOT/USDT", "tier":"MICRO", "quote_vol_24h":1_200_000.0,
            "spread_pct":0.10,"spread_ts":future,"depth_ratio":0.0,"volume_ratio":1.2,
            "structure_confidence":80.0,"structure_quality":80.0,"orderbook":_book(),
            "orderbook_ts":future,"book_ts":future,"depth_ts":future,
            "v703_route_orderbook_captured_ts":future}
    ok, reason, detail = main._v702_a7_micro_handoff_evidence(candidate, snap, tier="MICRO", record=False)
    assert not ok and reason == "market_fact_timestamp_future", (ok, reason, detail)
    # A fresh book may not conceal an impossible future spread timestamp.
    fresh = main.WALL_NOW()
    snap.update({"orderbook_ts":fresh,"book_ts":fresh,"depth_ts":fresh,
                 "v703_route_orderbook_captured_ts":fresh,"spread_ts":fresh + 60.0,
                 "spread_snapshot_ts":fresh + 60.0})
    ok, reason, detail = main._v702_a7_micro_handoff_evidence(candidate, snap, tier="MICRO", record=False)
    assert not ok and reason == "market_fact_timestamp_future", (ok, reason, detail)


def test_a10_mean_reversion_macro_policy_uses_local_confirmation_and_bearish_recovery():
    ok, reason, ctx = main.FamilyPolicyLayer.regime_policy_detail(
        "MEAN_REVERSION", "BULLISH", strategy_mode="MEAN_REVERSION", local_regime="LOCAL_BULLISH",
        market_phase="REVERSAL", severity="NORMAL", strategy_style="SCALP"
    )
    assert ok and reason == "allow"
    assert set(ctx.get("allowed_regimes", ())) == {"BULLISH", "NEUTRAL", "BEARISH"}
    no_local, no_local_reason, _ = main.FamilyPolicyLayer.regime_policy_detail(
        "MEAN_REVERSION", "BULLISH", strategy_mode="MEAN_REVERSION", local_regime="",
        market_phase="REVERSAL", severity="NORMAL", strategy_style="SCALP"
    )
    assert not no_local and no_local_reason == "local"
    bearish_without_recovery, bearish_reason, _ = main.FamilyPolicyLayer.regime_policy_detail(
        "MEAN_REVERSION", "BEARISH", strategy_mode="MEAN_REVERSION", local_regime="LOCAL_BULLISH",
        market_phase="REVERSAL", severity="BEARISH_NORMAL", strategy_style="SCALP"
    )
    assert not bearish_without_recovery and bearish_reason == "local"
    bearish_recovery, recovery_reason, _ = main.FamilyPolicyLayer.regime_policy_detail(
        "MEAN_REVERSION", "BEARISH", strategy_mode="MEAN_REVERSION", local_regime="LOCAL_RECOVERY",
        market_phase="REVERSAL", severity="BEARISH_NORMAL", strategy_style="SCALP"
    )
    assert bearish_recovery and recovery_reason == "allow"


def test_a9_prefetch_captures_unexpected_worker_errors_as_a_separate_reason(monkeypatch):
    original = main._v702_a9_orderbook_levels_valid

    def fail_after_fetch(book):
        if isinstance(book, dict):
            raise RuntimeError("synthetic_metrics_worker_failure")
        return original(book)

    monkeypatch.setattr(main, "_v702_a9_orderbook_levels_valid", fail_after_fetch)
    async def run():
        market = {"ADA/USDT": {"symbol":"ADA/USDT", "quote_vol_24h":1_400_000.0, "tier":"MICRO"}}
        result = await main._v702_a9_prefetch_micro_orderbooks(_MockExchange(), market)
        assert result["attempted"] == 1
        assert result["task_errors"] == 1
        assert result["api_errors"] == 0
        assert market["ADA/USDT"]["v702_a9_orderbook_prefetch_status"] == "FETCH_TASK_ERROR"
        cause, _detail = main._v702_a9_orderbook_missing_cause("ADA/USDT", market["ADA/USDT"], {})
        assert cause == "fetch_task_error"
    asyncio.run(run())
