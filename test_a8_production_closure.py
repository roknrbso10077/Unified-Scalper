"""A8 regression checks for score-floor parity, fail-closed MSE diagnosis and live blocker telemetry."""
from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace

os.environ["SCALPER_DB"] = os.path.join(tempfile.gettempdir(), f"v702-a8-tests-{os.getpid()}.db")
import main


def test_a8_exact_complete_projection_uses_canonical_effective_floor(monkeypatch):
    now = main.WALL_NOW()
    candidate = SimpleNamespace(symbol="TEST/USDT")
    snapshot = {"symbol": "TEST/USDT", "cycle_id": "cycle-1", "closed_candle_ts": "candle-1", "candidate_id": "candidate-1"}
    monkeypatch.setattr(main, "_V702_R34_PROJECTION_STATUS", {
        "TEST/USDT": {
            "complete": True,
            "symbol": "TEST/USDT",
            "candidate_object_id": id(candidate),
            "score": 75.7,
            "effective_floor": 80.0,
            "ts": now,
            "cycle_id": "cycle-1",
            "candle_ts": "candle-1",
            "candidate_id": "candidate-1",
        }
    }, raising=False)
    floor = main._v702_exact_route_projection_effective_floor(candidate, snapshot, 75.7, 70.0)
    assert floor == 80.0
    assert main._v702_exact_route_projection_hard_block_allowed(candidate, snapshot, 75.7, floor) is True


def test_a8_incomplete_or_mismatched_projection_does_not_raise_route_floor(monkeypatch):
    now = main.WALL_NOW()
    candidate = SimpleNamespace(symbol="TEST/USDT")
    snapshot = {"symbol": "TEST/USDT", "cycle_id": "cycle-1"}
    monkeypatch.setattr(main, "_V702_R34_PROJECTION_STATUS", {
        "TEST/USDT": {
            "complete": False,
            "symbol": "TEST/USDT",
            "candidate_object_id": id(candidate),
            "score": 75.7,
            "effective_floor": 80.0,
            "ts": now,
            "cycle_id": "cycle-1",
        }
    }, raising=False)
    assert main._v702_exact_route_projection_effective_floor(candidate, snapshot, 75.7, 70.0) == 70.0
    assert main._v702_exact_route_projection_hard_block_allowed(candidate, snapshot, 75.7, 80.0) is False


def test_a8_mse_diagnostic_identifies_short_4h_context_without_repairing_it():
    if not getattr(main, "_PDNP_OK", False) or getattr(main, "pd", None) is None:
        return
    pd = main.pd
    def frame(rows):
        return pd.DataFrame({
            "open": [1.0] * rows,
            "high": [1.1] * rows,
            "low": [0.9] * rows,
            "close": [1.0] * rows,
            "volume": [100.0] * rows,
        })
    snap = {
        "df_5m": frame(30), "df_15m": frame(350), "df_1h": frame(240), "df_4h": frame(49),
        "df_btc_5m": frame(60), "df_btc_15m": frame(80), "df_btc_1h": frame(80), "df_btc_4h": frame(240),
        "btc_context_age_sec": 0.0,
        "symbol": "TEST/USDT", "regime": "NEUTRAL", "macro_regime": "NEUTRAL", "local_regime": "NEUTRAL",
        "macro_severity": "NORMAL", "bearish_severity": "NORMAL", "market_phase": "RANGE",
        "btc_context": "OK", "htf_strength": 80.0, "tier": "MID",
    }
    assert main._mse_context_failure_detail(snap["df_4h"], 50) == "short_rows:got=49,required=50"
    valid, reason = main.validate_mse_snapshot(snap)
    assert valid is False
    assert reason == "mse_snapshot_invalid"
    assert main.STATS["mse_snapshot_invalid_detail"] == "mse_snapshot_invalid:df_4h"
    assert "df_4h:short_rows:got=49,required=50" in main.STATS["mse_snapshot_invalid_diagnostic"]
    assert len(snap["df_4h"]) == 49  # diagnostic did not synthesize rows


def test_a8_orderbook_block_telemetry_is_reason_specific_and_live_epoch_scoped(monkeypatch):
    monkeypatch.setattr(main, "_V699_LIVE_EPOCH_ARMED", True, raising=False)
    monkeypatch.setitem(main.STATS, "v702_a8_orderbook_block_counts", {})
    main._v702_a8_note_orderbook_block("TEST/USDT", "prequal", "micro_depth", {"depth_ratio": 0.4, "spread_pct": 0.1})
    counts = main.STATS["v702_a8_orderbook_block_counts"]
    assert counts["prequal:micro_depth"] == 1
    last = main.STATS["v702_a8_orderbook_block_last"]
    assert last["symbol"] == "TEST/USDT"
    assert last["reason"] == "micro_depth"
    assert last["context"]["depth_ratio"] == 0.4


def test_a8_canonical_revision_preserves_safety_invariants():
    assert main.V702_A8_CANONICAL_REVISION == "V702-R40-A8-PROJECTION-FLOOR-MSE-DIAGNOSTICS-ORDERBOOK-ROOT-CLOSURE"
    assert main.CONFIG["MIN_LIVE_SCORE"] >= 70.0
    assert main.CONFIG["LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME"] == 3_000_000.0
    assert main.CONFIG["V45_TIER_MICRO_MIN_DEPTH_RATIO"] >= 1.90
    assert main.CONFIG["V45_TIER_MICRO_MAX_SPREAD_PCT"] <= 0.30
    assert main.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False


def test_a8_stale_entry_status_does_not_masquerade_as_current_root(monkeypatch):
    monkeypatch.setitem(main.CONFIG, "V702_A7_ENTRY_BLOCK_MAX_AGE_SEC", 300.0)
    monkeypatch.setitem(main.STATS, "v702_selected_route_last", {})
    monkeypatch.setattr(main, "_V698_LAST_BUILDER_BLOCK", {}, raising=False)
    monkeypatch.setitem(main.STATS, "v699_live_entry_status", "BLOCKED:SCORE")
    monkeypatch.setitem(main.STATS, "v699_live_entry_status_ts", main.WALL_NOW() - 1200.0)
    assert main._v702_a7_entry_block_summary() == ("NONE", -1)
    monkeypatch.setitem(main.STATS, "v699_live_entry_status_ts", main.WALL_NOW() - 12.0)
    root, age = main._v702_a7_entry_block_summary()
    assert root == "SCORE"
    assert 0 <= age <= 20
