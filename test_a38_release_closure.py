from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import main as bot

ROOT = Path(__file__).resolve().parent

def test_a38_digest_is_30m_and_critical_guards_remain():
    assert bot.V702_A44_CANONICAL_REVISION.startswith(bot.V702_A43_CANONICAL_REVISION + "-A44-")
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A44_CANONICAL_REVISION + "-A45-TELEMETRY-RETENTION-SCORE-FLOOR-ROOT-CLARITY-2026-10-18")
    assert bot.V702_A41_CANONICAL_REVISION.startswith(bot.V702_A40_CANONICAL_REVISION + "-A41-")
    assert bot.V702_A42_CANONICAL_REVISION.startswith(bot.V702_A41_CANONICAL_REVISION + "-A42-")
    assert bot.V702_A43_CANONICAL_REVISION.startswith(bot.V702_A42_CANONICAL_REVISION + "-A43-")
    assert bot.V702_A39_CANONICAL_REVISION.startswith(bot.V702_A38_CANONICAL_REVISION + "-A39-")
    assert bot.V702_A40_CANONICAL_REVISION.startswith(bot.V702_A39_CANONICAL_REVISION + "-A40-")
    assert bot.CONFIG["V702_A40_ENTRY_BLOCK_DIAGNOSTICS_ENABLE"] is True
    assert bot.CONFIG["V702_A40_ENTRY_BLOCK_DIAG_INTERVAL_SEC"] == 90.0
    assert bot.CONFIG["V702_R28_TELEGRAM_DIGEST_INTERVAL_SEC"] == 1800.0
    assert bot.CONFIG["HEARTBEAT_INTERVAL_SEC"] == 1800.0
    assert bot.FINAL_CANONICAL_RUNTIME["pipeline_window_summary_seconds"] == 900
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70.0
    assert bot.CONFIG["LONG_ONLY"] and bot.CONFIG["MARKET_TYPE"] == "SPOT"
    assert not bot.CONFIG.get("ENABLE_FUTURES", False) and not bot.CONFIG.get("ALLOW_SHORT", False)
    assert bot.CONFIG.get("V560_SOFTWARE_SL_MAX_MISSED_HEARTBEAT_SEC", 12.0) <= 12.0

def test_a38_same_bar_stop_is_conservative_and_preserves_only_prior_targets():
    assert bot._v702_a38_same_bar_stop_result("") == {"status":"SL_FINAL", "first_event":"SL", "final_outcome":"SL", "prior_target_proven":False}
    assert bot._v702_a38_same_bar_stop_result("TP1")["final_outcome"] == "SL_AFTER_TP1"
    assert bot._v702_a38_same_bar_stop_result("TP2")["final_outcome"] == "SL_AFTER_TP2"

def test_a38_htf_guard_evidence_is_bounded_telemetry_only():
    keys = ("v702_a38_htf_crash_guard_count", "v702_a38_htf_crash_guard_last", "v702_a38_htf_crash_guard_history")
    old = {k: bot.STATS.get(k, None) for k in keys}
    had = {k: k in bot.STATS for k in keys}
    try:
        row = bot._v702_a38_record_htf_crash_guard(
            "TEST/USDT", {"symbol":"TEST/USDT", "macro_regime":"BEARISH", "macro_severity":"BEARISH_CRASH",
            "htf_state":"BEARISH", "htf_strength":12.0, "htf_source":"TEST_SOURCE", "htf_age_sec":4.0},
            SimpleNamespace(symbol="TEST/USDT", features_snapshot={}), reason="htf.bearish_crash_guard")
        assert row["telemetry_only"] is True and row["decision_changed"] is False
        assert row["symbol"] == "TEST/USDT" and row["severity"] == "BEARISH_CRASH"
        assert int(bot.STATS["v702_a38_htf_crash_guard_count"]) >= 1
        assert len(bot.STATS["v702_a38_htf_crash_guard_history"]) <= 64
    finally:
        for key in keys:
            if had[key]: bot.STATS[key] = old[key]
            else: bot.STATS.pop(key, None)

def test_a38_closed_ohlcv_atr_reaches_the_spread_shadow_record():
    old = bot.STATS.get("v702_a34_spread_shadow_last")
    existed = "v702_a34_spread_shadow_last" in bot.STATS
    try:
        # Final row represents a still-forming candle and must be excluded. The
        # frame path is telemetry-only and does not participate in live approval.
        closes = [100.0 + i * 0.1 for i in range(30)]
        frame = pd.DataFrame({"open":closes, "high":[v+0.8 for v in closes], "low":[v-0.8 for v in closes], "close":closes, "volume":[1000.0]*30})
        ctx = bot._v702_a34_spread_context_fields(SimpleNamespace(features_snapshot={}), {"df_5m":frame}, {"features":{"close":closes[-2]}})
        assert ctx.get("atr_pct", 0) > 0
        assert str(ctx.get("atr_pct_source", "")).startswith("CLOSED_OHLCV_5M")
        bot._v702_a34_record_spread_shadow_observation("MID", 0.40, 0.22, {"features":{"close":closes[-2]}, **ctx})
        rec = bot.STATS["v702_a34_spread_shadow_last"]
        assert rec["atr_pct"] > 0
        assert rec["spread_to_atr_ratio"] > 0
        assert rec["atr_pct_source"].startswith("CLOSED_OHLCV_5M")
        assert rec["mode"] == "SHADOW_ONLY_NO_LIVE_RELIEF"
    finally:
        if existed: bot.STATS["v702_a34_spread_shadow_last"] = old
        else: bot.STATS.pop("v702_a34_spread_shadow_last", None)

def test_a38_heartbeat_includes_htf_and_builder_attribution_without_changing_pipeline_window():
    old_h = bot.STATS.get("v702_a38_htf_crash_guard_last")
    old_b = bot.STATS.get("v702_builder_return_none_last")
    had_h = "v702_a38_htf_crash_guard_last" in bot.STATS
    had_b = "v702_builder_return_none_last" in bot.STATS
    try:
        now = bot.WALL_NOW()
        bot.STATS["v702_a38_htf_crash_guard_count"] = 3
        bot.STATS["v702_a38_htf_crash_guard_last"] = {"ts":now,"symbol":"HTF/USDT","reason":"htf.bearish_crash_guard","severity":"BEARISH_CRASH","regime":"BEARISH","local_regime":"BEARISH","htf_state":"BEARISH","htf_strength":10.0,"htf_source":"TEST","htf_age_sec":5.0,"rows_1h":214,"rows_4h":52,"missing_fields":[]}
        bot.STATS["v702_builder_return_none_last"] = {"ts":now,"symbol":"NONE/USDT","reason":"builder_terminal_no_result_unattributed","reason_attribution":"unattributed_no_fresh_candidate_rejection","candidate_key":"abc123","cycle_id":8}
        line = bot._V702R28TelegramDigest._heartbeat_line("state=FULL_LIVE_RUNNING funnel=0/0/0/0")
        assert "A38_HTF_GUARD=" in line and "HTF/USDT" in line
        assert "A38_BUILDER_NONE=" in line and "NONE/USDT" in line
        assert "funnel_window_15m[" in line
    finally:
        for key, value, present in (("v702_a38_htf_crash_guard_last",old_h,had_h),("v702_builder_return_none_last",old_b,had_b)):
            if present: bot.STATS[key] = value
            else: bot.STATS.pop(key, None)

def test_a38_source_and_manifest_hash_are_current_after_packaging():
    manifest=json.loads((ROOT/"FINAL_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["canonical_revision"] == bot.V702_PACKAGE_AUDIT_REVISION
    assert manifest["canonical_source_sha256"] == hashlib.sha256((ROOT/"main.py").read_bytes()).hexdigest()
    assert manifest["archive_contents"] == sorted(manifest["archive_contents"])

import asyncio
from unittest.mock import AsyncMock, patch

def test_a38_knowledge_ledger_process_uses_sl_first_for_same_closed_bar():
    async def run_case(previous_first, previous_tp1_at):
        sym = "A38-LEDGER/USDT"
        row = {
            "alert_id": "A38-ALERT", "symbol": sym, "status": "IN_POSITION", "alerted_at": 1000.0,
            "last_bar_ts": 1800000, "entry": 100.0, "sl": 95.0, "risk_unit": 5.0,
            "tp1": 105.0, "tp2": 110.0, "tp3": 115.0, "notes": json.dumps({"horizon_sec": 20000}),
            "entry_triggered_at": 1700.0, "first_event": previous_first,
            "tp1_hit_at": previous_tp1_at, "tp2_hit_at": None, "tp3_hit_at": None, "sl_hit_at": None,
            "max_mfe_r": 0.0, "max_mae_r": 0.0, "bars_observed": 0,
            "tp1_notice_sent": 0, "tp2_notice_sent": 0, "tp3_notice_sent": 0, "sl_notice_sent": 0,
        }
        updated = []
        async def safe_api(*args, **kwargs):
            # One confirmed closed bar touches TP1 and SL in the same OHLC row.
            return [[1900000, 100.0, 106.0, 94.0, 100.0, 1000.0]]
        old_last = bot.KnowledgeOutcomeLedger._last_fetch_by_symbol.get(sym)
        had_last = sym in bot.KnowledgeOutcomeLedger._last_fetch_by_symbol
        bot.KnowledgeOutcomeLedger._last_fetch_by_symbol[sym] = 1000.0
        try:
            with patch.object(bot.KnowledgeOutcomeLedger, "_active", return_value=[row]), \
                 patch.object(bot.KnowledgeOutcomeLedger, "_update", side_effect=lambda aid, **fields: updated.append((aid, fields))), \
                 patch.object(bot.KnowledgeOutcomeLedger, "_send_milestone", new=AsyncMock(return_value=True)), \
                 patch.object(bot, "WALL_NOW", return_value=2000.0), \
                 patch.object(bot, "safe_api_call", side_effect=safe_api):
                await bot.KnowledgeOutcomeLedger.process(SimpleNamespace(fetch_ohlcv=lambda *a, **k: []))
        finally:
            if had_last: bot.KnowledgeOutcomeLedger._last_fetch_by_symbol[sym] = old_last
            else: bot.KnowledgeOutcomeLedger._last_fetch_by_symbol.pop(sym, None)
        assert updated, "ledger did not process synthetic closed candle"
        final = updated[-1][1]
        assert final["status"] == "SL_FINAL"
        assert final["sl_hit_at"] == 1900.0
        return final
    fresh = asyncio.run(run_case("", None))
    assert fresh["first_event"] == "SL" and fresh["final_outcome"] == "SL"
    assert fresh["tp1_hit_at"] is None, "TP reached only in same ambiguous candle must not be recorded"
    prior = asyncio.run(run_case("TP1", 1750.0))
    assert prior["first_event"] == "TP1" and prior["final_outcome"] == "SL_AFTER_TP1"
    assert prior["tp1_hit_at"] == 1750.0, "target proven on prior bar must be preserved"


def _a60_run_ledger_bar(row, bar, monkeypatch, *, fee_pct=0.10, fee_mult=2.0):
    """Run one deterministic closed OHLC bar through the persistent outcome ledger."""
    import asyncio
    from unittest.mock import AsyncMock, patch

    symbol = row["symbol"]
    updates = []

    async def fake_safe_api(*args, **kwargs):
        return [bar]

    old_last = bot.KnowledgeOutcomeLedger._last_fetch_by_symbol.get(symbol)
    had_last = symbol in bot.KnowledgeOutcomeLedger._last_fetch_by_symbol
    bot.KnowledgeOutcomeLedger._last_fetch_by_symbol[symbol] = 1000.0
    monkeypatch.setitem(bot.CONFIG, "TAKER_FEE_PCT", fee_pct)
    monkeypatch.setitem(bot.CONFIG, "ROUNDTRIP_FEE_MULT", fee_mult)
    try:
        with patch.object(bot.KnowledgeOutcomeLedger, "_active", return_value=[row]), \
             patch.object(bot.KnowledgeOutcomeLedger, "_update", side_effect=lambda aid, **fields: updates.append((aid, fields))), \
             patch.object(bot.KnowledgeOutcomeLedger, "_send_milestone", new=AsyncMock(return_value=True)), \
             patch.object(bot, "WALL_NOW", return_value=2000.0), \
             patch.object(bot, "safe_api_call", side_effect=fake_safe_api):
            asyncio.run(bot.KnowledgeOutcomeLedger.process(SimpleNamespace(fetch_ohlcv=lambda *a, **k: [])))
    finally:
        if had_last:
            bot.KnowledgeOutcomeLedger._last_fetch_by_symbol[symbol] = old_last
        else:
            bot.KnowledgeOutcomeLedger._last_fetch_by_symbol.pop(symbol, None)
    assert updates, "ledger did not persist the synthetic closed bar"
    return updates


def test_a60_paper_fill_bar_cannot_skip_a_same_candle_stop(monkeypatch):
    row = {
        "alert_id": "A60-FILL-STOP", "symbol": "A60FILL/USDT", "status": "WAITING_ENTRY",
        "alerted_at": 1000.0, "last_bar_ts": 0, "entry": 100.0, "sl": 95.0,
        "risk_unit": 5.0, "tp1": 105.0, "tp2": 110.0, "tp3": 115.0,
        "tp1_rr": 1.0, "tp2_rr": 2.0, "tp3_rr": 3.0,
        "notes": json.dumps({
            "horizon_sec": 20000, "record_source": "SELECTED_ROUTE_PAPER",
            "fill_model": "REFERENCE_PLUS_BUFFERED_BREAKOUT_V1",
            "fill_trigger_price": 100.02, "fill_margin_pct": 0.02,
            "round_trip_cost_pct": 0.30,
        }),
        "entry_triggered_at": None, "first_event": None,
        "tp1_hit_at": None, "tp2_hit_at": None, "tp3_hit_at": None, "sl_hit_at": None,
        "max_mfe_r": 0.0, "max_mae_r": 0.0, "bars_observed": 0,
        "tp1_notice_sent": 0, "tp2_notice_sent": 0, "tp3_notice_sent": 0, "sl_notice_sent": 0,
    }
    updates = _a60_run_ledger_bar(row, [1900000, 100.0, 106.0, 94.0, 100.0, 1000.0], monkeypatch)
    final = updates[-1][1]
    assert final["status"] == "SL_FINAL"
    assert final["final_outcome"] == "SL"
    assert final["first_event"] == "SL"
    assert final.get("tp1_hit_at") is None
    assert final["entry"] == 100.02
    assert final["sl_hit_at"] == 1900.0
    assert final["max_mae_r"] >= 1.0


def test_a60_paper_tp1_installs_fee_covered_virtual_stop(monkeypatch):
    row = {
        "alert_id": "A60-BE-STOP", "symbol": "A60BE/USDT", "status": "IN_POSITION",
        "alerted_at": 1000.0, "last_bar_ts": 1800000, "entry": 100.0, "sl": 95.0,
        "risk_unit": 5.0, "tp1": 105.0, "tp2": 110.0, "tp3": 115.0,
        "tp1_rr": 1.0, "tp2_rr": 2.0, "tp3_rr": 3.0,
        "notes": json.dumps({"horizon_sec": 20000, "record_source": "SELECTED_ROUTE_PAPER"}),
        "entry_triggered_at": 1700.0, "first_event": "TP1", "tp1_hit_at": 1750.0,
        "tp2_hit_at": None, "tp3_hit_at": None, "sl_hit_at": None,
        "max_mfe_r": 1.0, "max_mae_r": 0.1, "bars_observed": 1,
        "tp1_notice_sent": 1, "tp2_notice_sent": 0, "tp3_notice_sent": 0, "sl_notice_sent": 0,
    }
    updates = _a60_run_ledger_bar(row, [1900000, 100.3, 104.0, 100.1, 100.4, 1000.0], monkeypatch)
    final = updates[-1][1]
    notes = json.loads(final["notes"])
    assert final["status"] == "SL_FINAL"
    assert final["first_event"] == "TP1"
    assert final["final_outcome"] == "SL_AFTER_TP1"
    assert final["sl_hit_at"] == 1900.0
    assert notes["paper_virtual_sl_price"] == 100.2
    assert notes["paper_virtual_sl_reason"] == "LIVE_TP1_FEE_COVERED_BREAKEVEN_CONTRACT"
    assert final.get("sl", row["sl"]) == 95.0, "original stop must remain available as the original risk anchor"


def test_a60_same_bar_tp1_and_new_be_stop_is_marked_ambiguous(monkeypatch):
    row = {
        "alert_id": "A60-BE-AMBIG", "symbol": "A60AMBIG/USDT", "status": "IN_POSITION",
        "alerted_at": 1000.0, "last_bar_ts": 1800000, "entry": 100.0, "sl": 95.0,
        "risk_unit": 5.0, "tp1": 105.0, "tp2": 110.0, "tp3": 115.0,
        "tp1_rr": 1.0, "tp2_rr": 2.0, "tp3_rr": 3.0,
        "notes": json.dumps({"horizon_sec": 20000, "record_source": "SELECTED_ROUTE_PAPER", "paper_virtual_sl_price": 95.0}),
        "entry_triggered_at": 1700.0, "first_event": None, "tp1_hit_at": None,
        "tp2_hit_at": None, "tp3_hit_at": None, "sl_hit_at": None,
        "max_mfe_r": 0.0, "max_mae_r": 0.0, "bars_observed": 0,
        "tp1_notice_sent": 0, "tp2_notice_sent": 0, "tp3_notice_sent": 0, "sl_notice_sent": 0,
    }
    updates = _a60_run_ledger_bar(row, [1900000, 100.0, 106.0, 100.1, 101.0, 1000.0], monkeypatch)
    final = updates[-1][1]
    assert final["status"] == "AMBIGUOUS_FINAL"
    assert final["first_event"] == "TP1"
    assert final["final_outcome"] == "AMBIGUOUS_TP1_BE_SAME_BAR"
    assert final["tp1_hit_at"] == 1900.0
    assert final["sl_hit_at"] is None


def test_a60_release_identity_and_shadow_only_contract():
    assert bot.V702_FINAL_CANONICAL_RELEASE == "UNIFIED-SCALPER-V702-A61-CANONICAL-FINAL"
    report = bot._v702_a61_self_test()
    assert report["pass"] is True, report.get("failed")
    assert report["live_authority"] is False
    assert report["hard_gate_bypass"] is False
    assert report["live_gates_relaxed"] is False
    assert report["production_decision"] == "NO_GO_UNATTENDED_LIVE"


def test_a60_shadow_missing_is_not_misreported_as_a_shadow_block():
    key = "A60-CANDIDATE-KEY"
    shadow, status, reason = bot._v702_a60_resolve_paper_shadow(
        {}, key,
        {
            "candidate_key": key,
            "candidate_rejection": {"stage": "scorer", "code": "score_below_threshold:60.9<70.0"},
        },
    )
    assert status == "builder_returned_none"
    assert shadow["eligible"] is False
    assert shadow["not_reached"] is True
    assert "not_reached:builder_returned_none:scorer:score_below_threshold" in reason

    actual_block, status, _ = bot._v702_a60_resolve_paper_shadow(
        {key: {"eligible": False, "reason": "liquidity.spread=0.36%"}}, key, {}
    )
    assert status == "shadow_evaluated"
    assert actual_block.get("not_reached") is not True
    assert actual_block["reason"] == "liquidity.spread=0.36%"
