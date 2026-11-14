"""Focused A55 tests for isolated Shadow PreSend, post-Builder evidence and EdgeGate."""
from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from pathlib import Path
from types import SimpleNamespace

import main as bot


class _ExchangeWithFees:
    def __init__(self, rate=0.001):
        self.markets = {"A55TEST/USDT": {"taker": rate}} if rate is not None else {}
        self.fees = {"trading": {"taker": rate}} if rate is not None else {}


class _ExchangeWithoutFees:
    markets = {}
    fees = {}


def _shadow_input():
    book = {"asks": [[100.10, 1000.0]], "bids": [[99.90, 1000.0]]}
    market_data = {"orderbook": book, "orderbook_ts": time.time()}
    return book, market_data


def test_a55_score_bucket_edges_are_exact():
    cases = {
        74.99: "<75", 75: "75-79.9", 79.99: "75-79.9",
        80: "80-84.9", 85: "85-89.9", 90: "90-94.9", 95: "95+",
    }
    for score, expected in cases.items():
        assert bot.KnowledgeOutcomeLedger._bucket_score(score) == expected


def test_a55_shadow_presend_measures_spread_vwap_fees_and_cost_floor(monkeypatch):
    monkeypatch.setitem(bot.CONFIG, "MARKET_TYPE", "SPOT")
    monkeypatch.setitem(bot.CONFIG, "LONG_ONLY", True)
    monkeypatch.setitem(bot.CONFIG, "ALLOW_SHORT", False)
    monkeypatch.setitem(bot.CONFIG, "MIN_LIVE_SCORE", 70.0)
    monkeypatch.setitem(bot.CONFIG, "MIN_ORDER_BOOK_DEPTH_RATIO", 1.6)
    monkeypatch.setitem(bot.CONFIG, "MIN_TP1_TO_FEE_RATIO", 2.5)
    monkeypatch.setitem(bot.CONFIG, "MIN_NET_RR_TP1", 0.8)
    monkeypatch.setitem(bot.CONFIG, "MIN_NET_RR_OVERALL", 1.2)
    monkeypatch.setitem(bot.CONFIG, "V702_SMALL_NET_PROFIT_MODE_ENABLE", False)
    monkeypatch.setitem(bot.CONFIG, "ENABLE_RUNNER_MODE", True)
    monkeypatch.setitem(bot.CONFIG, "TP1_EXIT_PCT", 0.60)
    monkeypatch.setitem(bot.CONFIG, "TP2_EXIT_PCT", 0.30)
    monkeypatch.setitem(bot.CONFIG, "RUNNER_KEEP_PCT_AT_TP3", 0.10)
    book, market_data = _shadow_input()
    bot.STATS.setdefault("v702_a55_taker_fee_cache", {}).pop("A55TEST/USDT", None)

    result = asyncio.run(bot.ShadowPreSendGate.evaluate(
        _ExchangeWithFees(), "A55TEST/USDT", 100.0, 99.0, 103.0, 105.0, 110.0,
        market_data=market_data, cached_ob=book, strategy_score=90.0,
        strategy_mode="PULLBACK", strategy_family="PULLBACK",
        strategy_style="SCALP", timeframe_profile="15M_5M", htf_strength=90.0,
    ))
    assert result["eligible"] is True
    assert result["exchange_order_submitted"] is False
    assert result["round_trip_cost_pct"] >= 0.30
    model = result["round_trip_cost_model"]
    assert result["round_trip_cost_pct"] == max(
        model["minimum_cost_pct"], model["measured_cost_pct"], model["r40_fallback_cost_pct"]
    )
    assert result["taker_fee_source"] == "exchange_market_taker"
    assert result["family"] == "PULLBACK"
    assert result["vwap_buy"] > result["vwap_sell"]


def test_a55_shadow_presend_fails_closed_without_taker_fee_metadata(monkeypatch):
    monkeypatch.setitem(bot.CONFIG, "MARKET_TYPE", "SPOT")
    monkeypatch.setitem(bot.CONFIG, "LONG_ONLY", True)
    monkeypatch.setitem(bot.CONFIG, "ALLOW_SHORT", False)
    book, market_data = _shadow_input()
    bot.STATS.setdefault("v702_a55_taker_fee_cache", {}).pop("A55TEST/USDT", None)
    result = asyncio.run(bot.ShadowPreSendGate.evaluate(
        _ExchangeWithoutFees(), "A55TEST/USDT", 100.0, 99.0, 103.0, 105.0, 110.0,
        market_data=market_data, cached_ob=book, strategy_score=90.0,
        strategy_mode="PULLBACK", strategy_family="PULLBACK",
        strategy_style="SCALP", timeframe_profile="15M_5M", htf_strength=90.0,
    ))
    assert result["eligible"] is False
    assert result["reason"] == "taker_fee_unavailable_or_invalid"
    assert result["exchange_order_submitted"] is False


def test_a55_paper_annotation_persists_shadow_geometry_and_dynamic_cost(tmp_path, monkeypatch):
    db = tmp_path / "a55-paper.db"
    monkeypatch.setitem(bot.CONFIG, "DB_PATH", str(db))
    monkeypatch.setenv("UNIFIED_PAPER_SIM_ENABLE", "1")
    monkeypatch.setenv("UNIFIED_MONITOR_ONLY_SCAN_ENABLE", "1")
    monkeypatch.setattr(bot.KillSwitch, "is_active", staticmethod(lambda: False))
    bot.KnowledgeOutcomeLedger.ensure_schema()
    candidate = SimpleNamespace(
        symbol="A55TEST/USDT", side="long", family="PULLBACK", strategy_mode="PULLBACK",
        strategy_style="SCALP", timeframe_profile="15M_5M", engine_score=0.90,
        entry_ref=100.0, sl_price=98.0, tp1_rr=1.0, tp2_rr=2.0, tp3_rr=3.0,
        generated_at_ms=1793790000000, quality_grade="A", features_snapshot={"htf_strength": 90.0},
    )
    alert_id = bot.KnowledgeOutcomeLedger.register_alert(candidate, {}, source="SELECTED_ROUTE_PAPER", assume_fill=False)
    assert alert_id
    shadow = {
        "reached": True, "eligible": True, "reason": "shadow_presend_pass", "round_trip_cost_pct": 0.42,
        "entry": 101.0, "sl": 99.0, "tp1": 104.0, "tp2": 107.0, "tp3": 111.0,
    }
    assert bot.KnowledgeOutcomeLedger.annotate_paper_edge(
        alert_id, shadow, builder_completed=True, live_eligible=False, builder_reason="builder_completed",
        market_qualification_completed=True, trade_state_created=False, evaluation_attempt_id="attempt-a55-1",
    ) is True
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT entry,sl,risk_unit,tp1,tp2,tp3,tp1_rr,tp2_rr,tp3_rr,notes FROM knowledge_outcomes WHERE alert_id=?",
        (alert_id,),
    ).fetchone()
    conn.close()
    assert row[:9] == (101.0, 99.0, 2.0, 104.0, 107.0, 111.0, 1.5, 3.0, 5.0)
    notes = json.loads(row[9])
    assert notes["paper_edge_eligible"] is True
    assert notes["shadow_presend_eligible"] is True
    assert notes["live_eligible"] is False
    assert notes["trade_state_created"] is False
    assert notes["market_qualification_completed"] is True
    assert notes["evaluation_attempt_id"] == "attempt-a55-1"
    assert notes["round_trip_cost_pct"] == bot._v702_unified_round_trip_cost_pct(measured_cost_pct=0.42)["round_trip_cost_pct"]
    assert notes["paper_final_geometry_source"] == "BUILDER_SHADOW_PRESEND"


def test_a55_edge_gate_fails_closed_without_validated_matching_recipe(monkeypatch):
    monkeypatch.setenv("UNIFIED_LIVE_PILOT_ENABLE", "1")
    monkeypatch.setenv("UNIFIED_A55_LIVE_ARM", "1")
    monkeypatch.setattr(bot.KillSwitch, "is_active", staticmethod(lambda: False))
    monkeypatch.setattr(bot.LiveStateMachine, "is_live_runnable", staticmethod(lambda: True))
    monkeypatch.setattr(bot, "LIVE_ENTRIES_BLOCKED", {"active": False})
    monkeypatch.setattr(bot.KnowledgeOutcomeLedger, "_edge_report", classmethod(lambda cls: {
        "generated_at": time.time(), "learned_recipes": {}
    }))
    bot.STATS["v702_knowledge_edge_report"] = None
    ctx = {"family": "PULLBACK", "strategy_mode": "PULLBACK", "strategy_style": "SCALP",
           "timeframe_profile": "15M_5M", "htf_strength": 90.0}
    assert bot._v702_live_buy_possible(ctx) is False


def test_a55_edge_gate_requires_exact_recipe_and_fdr_validation(monkeypatch):
    monkeypatch.setitem(bot.CONFIG, "V702_KNOWLEDGE_RECIPE_MIN_OBS", 100)
    monkeypatch.setenv("UNIFIED_LIVE_PILOT_ENABLE", "1")
    monkeypatch.setenv("UNIFIED_A55_LIVE_ARM", "1")
    monkeypatch.setattr(bot.KillSwitch, "is_active", staticmethod(lambda: False))
    monkeypatch.setattr(bot.LiveStateMachine, "is_live_runnable", staticmethod(lambda: True))
    monkeypatch.setattr(bot.ProductionCapabilityGate, "_checked", True)
    monkeypatch.setattr(bot.ProductionCapabilityGate, "_stop_mode", "dedicated_stop_market")
    monkeypatch.setitem(bot.CONFIG, "POSITION_MANAGER_TASK_ENABLE", True)
    monkeypatch.setitem(bot.STATS, "v702_pm_task_state", "RUNNING")
    monkeypatch.setitem(bot.STATS, "v702_pm_healthy_ticks", 1)
    monkeypatch.setitem(bot.STATS, "v702_pm_last_healthy_ts", time.time())
    monkeypatch.setattr(bot, "ACTIVE_TRADES", {}, raising=False)
    monkeypatch.setattr(bot, "LIVE_ENTRIES_BLOCKED", {"active": False})
    ctx = {"family": "PULLBACK", "strategy_mode": "PULLBACK", "strategy_style": "SCALP",
           "timeframe_profile": "15M_5M", "htf_strength": 90.0}
    key = bot.EdgeGate.recipe_key(ctx)
    recipe = {"entries": 100, "status": "VALIDATED_POSITIVE", "expectancy_r": 0.15,
              "lower_bound_90_r": 0.02, "first_half_expectancy_r": 0.12,
              "second_half_expectancy_r": 0.18}
    monkeypatch.setattr(bot.KnowledgeOutcomeLedger, "_edge_report", classmethod(lambda cls: {
        "version": bot.V702_KNOWLEDGE_EDGE_VERSION,
        "generated_at": time.time(), "learned_recipes": {key: recipe}
    }))
    bot.STATS["v702_knowledge_edge_report"] = {
        "version": bot.V702_KNOWLEDGE_EDGE_VERSION,
        "generated_at": time.time(), "learned_recipes": {key: recipe}
    }
    assert bot._v702_live_buy_possible(ctx) is True
    recipe["status"] = "REQUIRES_FDR_VALIDATION"
    bot.STATS["v702_knowledge_edge_report"] = {
        "version": bot.V702_KNOWLEDGE_EDGE_VERSION,
        "generated_at": time.time(), "learned_recipes": {key: recipe}
    }
    assert bot._v702_live_buy_possible(ctx) is False


def test_a55_release_validator_is_the_active_canonical_validator():
    result = bot.validate_config()
    report = bot.STATS.get("v702_a55_validation") or {}
    assert result is True, report.get("failed")
    assert report.get("revision", "").startswith("V702-A55-")
    assert all(report.get("checks", {}).values())


def test_a55_shadow_cost_floor_respects_operator_minimum_not_below_030(monkeypatch):
    monkeypatch.setitem(bot.CONFIG, "MARKET_TYPE", "SPOT")
    monkeypatch.setitem(bot.CONFIG, "LONG_ONLY", True)
    monkeypatch.setitem(bot.CONFIG, "ALLOW_SHORT", False)
    monkeypatch.setitem(bot.CONFIG, "MIN_ORDER_BOOK_DEPTH_RATIO", 1.0)
    monkeypatch.setitem(bot.CONFIG, "MIN_TP1_TO_FEE_RATIO", 0.1)
    monkeypatch.setitem(bot.CONFIG, "V702_SMALL_NET_PROFIT_MODE_ENABLE", True)
    monkeypatch.setitem(bot.CONFIG, "V702_SMALL_NET_MIN_NET_RR_TP1", 0.01)
    monkeypatch.setitem(bot.CONFIG, "V702_SMALL_NET_MIN_NET_RR_OVERALL", 0.01)
    monkeypatch.setitem(bot.CONFIG, "V702_SMALL_NET_MIN_NET_PROFIT_PCT", -1.0)
    monkeypatch.setitem(bot.CONFIG, "V702_SHADOW_MIN_ROUND_TRIP_COST_PCT", 0.55)
    book, market_data = _shadow_input()
    bot.STATS.setdefault("v702_a55_taker_fee_cache", {}).pop("A55TEST/USDT", None)
    result = asyncio.run(bot.ShadowPreSendGate.evaluate(
        _ExchangeWithFees(0.0001), "A55TEST/USDT", 100.0, 99.0, 104.0, 108.0, 112.0,
        market_data=market_data, cached_ob=book, strategy_score=90.0,
        strategy_mode="PULLBACK", strategy_family="PULLBACK", strategy_style="SCALP",
        timeframe_profile="15M_5M", htf_strength=90.0,
    ))
    assert result["eligible"] is True, result
    assert result["round_trip_cost_pct"] >= 0.55


def test_a55_shadow_presend_excludes_forbidden_assets(monkeypatch):
    monkeypatch.setattr(bot, "_v587_is_forbidden_coin", lambda _symbol: (True, "test_blacklist"))
    book, market_data = _shadow_input()
    result = asyncio.run(bot.ShadowPreSendGate.evaluate(
        _ExchangeWithFees(), "A55TEST/USDT", 100.0, 99.0, 103.0, 105.0, 110.0,
        market_data=market_data, cached_ob=book, strategy_score=90.0,
        strategy_mode="PULLBACK", strategy_family="PULLBACK",
        strategy_style="SCALP", timeframe_profile="15M_5M", htf_strength=90.0,
    ))
    assert result["eligible"] is False
    assert result["reason"] == "forbidden_asset:test_blacklist"
    assert result["exchange_order_submitted"] is False


def test_a60_edge_report_separates_exploratory_paper_from_eligible_edge(tmp_path, monkeypatch):
    db = tmp_path / "a60-edge-separation.sqlite3"
    monkeypatch.setitem(bot.CONFIG, "DB_PATH", str(db))
    bot.KnowledgeOutcomeLedger.ensure_schema()
    conn = sqlite3.connect(str(db))
    for i in range(1, 7):
        is_selected = i <= 3
        eligible = i == 1
        notes = {
            "record_source": "SELECTED_ROUTE_PAPER" if is_selected else "DISCOVERY",
            "version": bot.V702_KNOWLEDGE_EDGE_VERSION,
            "paper_edge_eligible": eligible,
            "shadow_presend_eligible": eligible,
            "market_live_eligible": eligible,
            "round_trip_cost_r": 0.10,
            "paper_virtual_sl_price": 100.02,
            "coverage_contract": "CLOSED_CANDLE_SEQUENCE_V1",
            "coverage_complete": True,
        }
        conn.execute("""INSERT INTO knowledge_outcomes
            (alert_id,alerted_at,symbol,family,strategy_mode,strategy_style,timeframe_profile,
             entry,sl,risk_unit,tp1,tp2,tp3,tp1_rr,tp2_rr,tp3_rr,status,first_event,final_outcome,
             entry_triggered_at,created_at,updated_at,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f"a60-{i}", 1000.0+i, "A60TEST/USDT", "PULLBACK", "PULLBACK", "SCALP", "15M_5M",
             100.0, 99.0, 1.0, 101.0, 102.0, 103.0, 1.0, 2.0, 3.0, "SL_FINAL", "SL", "SL",
             1001.0+i, 1000.0+i, 1000.0+i, json.dumps(notes)))
    conn.commit()
    conn.close()

    report = bot.KnowledgeOutcomeLedger._edge_report()
    key = "PULLBACK|STYLE=SCALP|TF=15M_5M"
    assert report["by_family_timeframe"][key]["alerts"] == 6  # legacy diagnostic includes all sources
    assert report["paper_selected"]["alerts"] == 3
    assert report["paper_selected_by_family_timeframe"][key]["alerts"] == 3
    assert report["edge_eligible_paper_rows"] == 1
    assert report["edge_eligible_paper"]["alerts"] == 1
    assert report["edge_eligible_by_family_timeframe"][key]["alerts"] == 1
