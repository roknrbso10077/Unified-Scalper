"""A12 regressions for exact-score selection and failure-aware micro scanning."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("SCALPER_DB", os.path.join(tempfile.gettempdir(), f"v702-a12-tests-{os.getpid()}.db"))
import main as bot


def _candidate(symbol="A12TEST/USDT"):
    return SimpleNamespace(
        symbol=symbol,
        family="PULLBACK",
        strategy_mode="PULLBACK",
        strategy_style="SCALP",
        macro_regime="BULLISH",
        features_snapshot={},
    )


def _status(candidate, *, score=65.0, floor=76.0, complete=True, ts=None):
    return {
        "score": score,
        "effective_floor": floor,
        "canonical_floor": 70.0,
        "complete": complete,
        "symbol": candidate.symbol,
        "candidate_object_id": id(candidate),
        "candidate_id": "A12-CANDIDATE",
        "candle_ts": "A12-CANDLE",
        "cycle_id": "A12-CYCLE",
        "ts": float(bot.WALL_NOW() if ts is None else ts),
    }


def _snapshot(symbol="A12TEST/USDT"):
    return {
        "symbol": symbol,
        "candidate_id": "A12-CANDIDATE",
        "candle_ts": "A12-CANDLE",
        "cycle_id": "A12-CYCLE",
        "regime": "BULLISH",
    }


def test_complete_exact_underfloor_is_blocked_before_winner_slot(monkeypatch):
    candidate = _candidate()
    monkeypatch.setattr(bot, "_V702_R34_PROJECTION_STATUS", {candidate.symbol: _status(candidate)}, raising=False)
    out = bot._v702_r5_projection_disposition(candidate, _snapshot(), 65.0, 0.81, blend_weight=0.40)
    assert out["complete"] is True
    assert out["hard_block"] is True
    assert out["status"] == "EXACT_UNDERFLOOR"
    assert out["floor"] == 76.0


def test_incomplete_projection_preserves_original_canonical_rank(monkeypatch):
    candidate = _candidate()
    monkeypatch.setattr(bot, "_V702_R34_PROJECTION_STATUS", {candidate.symbol: _status(candidate, complete=False)}, raising=False)
    out = bot._v702_r5_projection_disposition(candidate, _snapshot(), 65.0, 0.81, blend_weight=0.40)
    assert out["complete"] is False
    assert out["hard_block"] is False
    assert out["status"] == "INCOMPLETE_KEEP_CANONICAL_RANK"
    assert out["ranking_score"] == 0.81


def test_stale_projection_does_not_reorder_candidate(monkeypatch):
    candidate = _candidate()
    monkeypatch.setattr(
        bot, "_V702_R34_PROJECTION_STATUS",
        {candidate.symbol: _status(candidate, complete=True, ts=float(bot.WALL_NOW()) - 120.0)},
        raising=False,
    )
    out = bot._v702_r5_projection_disposition(candidate, _snapshot(), 65.0, 0.81, blend_weight=0.40)
    assert out["complete"] is False
    assert out["hard_block"] is False
    assert out["ranking_score"] == 0.81


def test_complete_passing_projection_can_influence_ordering(monkeypatch):
    candidate = _candidate()
    monkeypatch.setattr(
        bot, "_V702_R34_PROJECTION_STATUS",
        {candidate.symbol: _status(candidate, score=80.0, floor=76.0)},
        raising=False,
    )
    out = bot._v702_r5_projection_disposition(candidate, _snapshot(), 80.0, 0.70, blend_weight=0.40)
    assert out["complete"] is True
    assert out["hard_block"] is False
    assert out["status"] == "EXACT_PASS_BLEND"
    assert abs(out["ranking_score"] - 0.74) < 1e-9


def test_projected_floor_respects_bounded_starvation_relief(monkeypatch):
    candidate = _candidate()
    monkeypatch.setitem(bot.CONFIG, "ENABLE_LIVE_TRADING", True)
    monkeypatch.setitem(bot.CONFIG, "PAPER_TRADING_MODE", False)
    monkeypatch.setitem(bot.CONFIG, "MIN_LIVE_SCORE", 70.0)
    monkeypatch.setitem(bot.CONFIG, "V702_ELITE_LIVE_QUALITY_GATE_ENABLE", True)
    monkeypatch.setitem(bot.CONFIG, "V704_STARVATION_SCORE_RELIEF_FLOOR", 70.0)
    monkeypatch.setattr(
        bot, "_v704_starvation_score_floor_override",
        lambda opp, score, elite: (True, {"applied": True, "effective_floor": 70.0}),
        raising=True,
    )
    floors = bot._v702_projected_builder_score_floors(candidate, _snapshot(), 74.7, {})
    assert floors["is_live"] is True
    assert floors["relief_applied"] is True
    assert floors["effective_floor"] == 70.0


def test_failed_micro_market_data_gets_short_retry_but_success_refreshes_ttl(monkeypatch):
    monkeypatch.setattr(bot, "_V702_R30_MICRO_SCAN_HISTORY", {"MICROTEST/USDT": 900.0}, raising=False)
    monkeypatch.setitem(bot.CONFIG, "V702_R30_MICRO_RECALL_RECENT_SCAN_TTL_SEC", 600.0)
    monkeypatch.setitem(bot.CONFIG, "V702_R30_MICRO_RECALL_FAILED_RETRY_SEC", 60.0)
    bot._v702_r30_note_scan_result("MICROTEST/USDT", False, now=1100.0)
    failed_ts = bot._V702_R30_MICRO_SCAN_HISTORY["MICROTEST/USDT"]
    assert abs((1100.0 - failed_ts) - 540.0) < 1e-9
    bot._v702_r30_note_scan_result("MICROTEST/USDT", True, now=1200.0)
    assert bot._V702_R30_MICRO_SCAN_HISTORY["MICROTEST/USDT"] == 1200.0


def test_validate_only_a12_self_test_passes():
    out = bot._v702_a12_selection_projection_self_test()
    assert out["pass"] is True, out
    assert out["live_gates_relaxed"] is False
    assert out["hard_gate_bypass"] is False
