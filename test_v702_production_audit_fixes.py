from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
import os
from datetime import datetime, timezone
import subprocess
import sys
from collections import defaultdict, deque
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock

import pandas as pd
import pytest
import main as bot
from v702_core__execution__cost_model import unified_round_trip_cost_model


def test_operator_off_blocks_direct_final_order_executor_before_exchange_calls():
    class ExchangeMustNotReceiveOrders:
        def __init__(self):
            self.order_calls = 0
        async def create_market_buy_order(self, *args, **kwargs):
            self.order_calls += 1
            raise AssertionError("market BUY must not be called while operator OFF")
        async def create_limit_buy_order(self, *args, **kwargs):
            self.order_calls += 1
            raise AssertionError("limit BUY must not be called while operator OFF")
        async def load_markets(self, *args, **kwargs):
            self.order_calls += 1
            raise AssertionError("exchange must not be touched before final OFF guard")

    exchange = ExchangeMustNotReceiveOrders()
    with patch.dict(os.environ, {"UNIFIED_LIVE_PILOT_ENABLE": "0"}, clear=False):
        result = asyncio.run(bot._orig_v702_terminal_submit(exchange, "BTC/USDT", 1.0, 100.0))
    assert result == (False, None, 0.0)
    assert exchange.order_calls == 0
    assert int(bot.STATS.get("v702_submit_entry_monitor_only_blocks", 0) or 0) >= 1


def test_future_timestamp_is_not_silently_fresh_in_any_common_unit():
    wall_future = time.time() + 60.0
    for raw in (wall_future, wall_future * 1_000, wall_future * 1_000_000, wall_future * 1_000_000_000):
        age = bot._wall_age_sec(raw)
        assert age is not None and age < 0
        ok, reason, _ = bot._v455_candidate_freshness_ok(raw)
        assert not ok
        assert reason == "freshness.future_timestamp"


def test_4h_integrity_rejects_rows_more_than_one_current_candle_into_future():
    now_ms = int(time.time() * 1000)
    interval = 4 * 60 * 60 * 1000
    current_open = now_ms - (now_ms % interval)
    closed = list(range(current_open - 51 * interval, current_open, interval))
    good = pd.DataFrame({"open": [1.0] * len(closed), "high": [2.0] * len(closed),
                         "low": [0.5] * len(closed), "close": [1.0] * len(closed),
                         "volume": [10.0] * len(closed)},
                        index=pd.to_datetime(closed, unit="ms", utc=True))
    ok, reason = bot._v702_a32_4h_history_integrity(good, minimum_closed=50)
    assert ok, reason
    future_idx = pd.to_datetime(closed + [current_open + interval], unit="ms", utc=True)
    bad = pd.DataFrame({"open": [1.0] * len(future_idx), "high": [2.0] * len(future_idx),
                        "low": [0.5] * len(future_idx), "close": [1.0] * len(future_idx),
                        "volume": [10.0] * len(future_idx)}, index=future_idx)
    ok, reason = bot._v702_a32_4h_history_integrity(bad, minimum_closed=50)
    assert not ok and reason == "4h_future_candle_open_detected"


def test_starvation_classifier_does_not_choose_htf_when_no_rejection_evidence_exists():
    assert bot._v565_starvation_mode_from_window(
        generated=12, prequal=0, ranked=10, selected=0, queued=0, sent=0,
        reject_htf=0, reject_liq=0, reject_structure=0, reject_score=0,
        reject_execution=0, reject_policy=0,
    ) == "UNATTRIBUTED"


def test_starvation_classifier_can_attribute_policy_when_policy_is_dominant():
    assert bot._v565_starvation_mode_from_window(
        generated=12, prequal=0, ranked=10, selected=0, queued=0, sent=0,
        reject_htf=1, reject_liq=0, reject_structure=0, reject_score=0,
        reject_execution=0, reject_policy=7,
    ) == "POLICY"


def test_rejection_dedup_key_changes_for_material_price_move_but_is_stable_for_same_price():
    payload = {"entry": 1.0, "zone_ref": 0.99}
    first = bot._v657_rejection_key("ABC/USDT", "PULLBACK", "SCALP", "prequal", "x", payload)
    same = bot._v657_rejection_key("ABC/USDT", "PULLBACK", "SCALP", "prequal", "x", payload)
    moved = bot._v657_rejection_key("ABC/USDT", "PULLBACK", "SCALP", "prequal", "x", {"entry": 1.02, "zone_ref": 1.0098})
    assert first == same
    assert first != moved


def test_durable_execution_intent_survives_and_blocks_until_terminal_resolution(tmp_path):
    db_path = tmp_path / "intents.sqlite3"
    with patch.dict(bot.CONFIG, {"DB_PATH": str(db_path)}):
        bot.DBManager.init_schema()
        iid = bot.DBManager.begin_execution_intent(
            "ABC/USDT", "trace-a", "BUY", "MARKET", 1.0, 10.0,
            details={"planned_sl": 9.5, "planned_tp1": 11.0},
        )
        bot.DBManager.update_execution_intent(iid, "SUBMISSION_UNKNOWN", venue_order_id="venue-1")
        rows = bot.DBManager.unresolved_execution_intents()
        assert len(rows) == 1
        assert rows[0]["intent_id"] == iid
        assert rows[0]["venue_order_id"] == "venue-1"
        assert rows[0]["details"]["planned_sl"] == 9.5
        bot.DBManager.update_execution_intent(iid, "NO_FILL_TERMINAL", details={"verified": True})
        assert bot.DBManager.unresolved_execution_intents() == []


def test_buy_fill_context_keeps_unknown_order_as_zero_quantity_not_planned_quantity():
    oid = "unit-unknown-order"
    ctx = {"symbol": "ABC/USDT", "requested_qty": 1.0, "filled_qty": 0.0,
           "net_filled_qty": 0.0, "entry_reconcile_required": True,
           "fill_quantity_unverified": True, "order_ids": [oid]}
    bot._v553_store_buy_fill_context(oid, ctx)
    saved = bot._v553_take_buy_fill_context(oid)
    assert saved is not None
    assert saved["net_filled_qty"] == 0.0
    assert saved["entry_reconcile_required"] is True
    assert bot._v553_take_buy_fill_context(oid) is None


def test_software_stop_can_be_armed_for_breakeven_or_profit_lock_stop():
    trade = bot.TradeState(symbol="ABC/USDT", trace_id="stop-test", entry=100.0,
                           original_sl=98.0, current_sl=100.2,
                           position_size_asset=1.0, remaining_position=1.0)
    assert asyncio.run(bot._v560_arm_software_sl(trade, "profit_lock_test")) is True
    assert trade.software_sl_active is True
    assert trade.sl_health_state == "SOFTWARE_SL_ACTIVE"


def test_live_stop_match_rejects_missing_or_oversized_coverage():
    base = {"symbol": "ABC/USDT", "side": "sell", "status": "open", "id": "sl-1",
            "triggerPrice": 99.0}
    assert bot._v553_live_stop_match([base], symbol="ABC/USDT", side="sell", qty=1.0,
                                     stop_price=99.0, expected_id="sl-1") is None
    missing_amount = {**base, "amount": 0.0}
    assert bot._v553_live_stop_match([missing_amount], symbol="ABC/USDT", side="sell", qty=1.0,
                                     stop_price=99.0, expected_id="sl-1") is None
    correct = {**base, "amount": 1.0}
    assert bot._v553_live_stop_match([correct], symbol="ABC/USDT", side="sell", qty=1.0,
                                      stop_price=99.0, expected_id="sl-1") is not None
    oversized = {**base, "amount": 1.2}
    assert bot._v553_live_stop_match([oversized], symbol="ABC/USDT", side="sell", qty=1.0,
                                      stop_price=99.0, expected_id="sl-1") is None


def test_engine_helpers_are_real_and_fail_closed_on_insufficient_data():
    closes = [100.0 + i for i in range(20)]
    frame = pd.DataFrame({"open": closes, "high": [x + 1 for x in closes],
                          "low": [x - 1 for x in closes], "close": closes,
                          "volume": [100.0] * len(closes)})
    assert bot._atr(frame, 14) is not None
    assert bot._rs_pct_move(frame, frame, 6) == pytest.approx(0.0, abs=1e-12)
    assert bot._rs_pct_move(frame.iloc[:3], frame.iloc[:3], 6) is None


def test_pipeline_reports_events_dropped_from_bounded_ring_buffer():
    cls = bot.V702PipelineMetrics
    snapshot = (cls._events, cls._events_dropped_total, cls._enabled, cls._cycle_id,
                getattr(cls, "_cycle_events_dropped_total", 0), getattr(cls, "_cycle_counts", None),
                getattr(cls, "_event_counts_by_second", None), getattr(cls, "_event_bucket_order", None),
                getattr(cls, "_drop_counts_by_second", None), getattr(cls, "_drop_bucket_order", None),
                getattr(cls, "_rejection_view_dirty", True))
    try:
        cls._events = deque(maxlen=1)
        cls._events_dropped_total = 0
        cls._cycle_events_dropped_total = 0
        cls._cycle_counts = bot.defaultdict(int) if hasattr(bot, "defaultdict") else __import__("collections").defaultdict(int)
        cls._event_counts_by_second = {}
        cls._event_bucket_order = deque()
        cls._drop_counts_by_second = {}
        cls._drop_bucket_order = deque()
        cls._enabled = True
        cls._cycle_id = int(bot.STATS.get("v681_runtime_cycle_id", 0) or 0)
        cls.record("DISCOVERY", "candidate-a", symbol="A/USDT")
        cls.record("RANKED", "candidate-b", symbol="B/USDT")
        assert len(cls._events) == 1
        assert cls._events_dropped_total == 1
        assert bot.STATS["v702_pipeline_events_dropped_total"] == 1
    finally:
        (cls._events, cls._events_dropped_total, cls._enabled, cls._cycle_id,
         cls._cycle_events_dropped_total, cls._cycle_counts, cls._event_counts_by_second,
         cls._event_bucket_order, cls._drop_counts_by_second, cls._drop_bucket_order,
         cls._rejection_view_dirty) = snapshot


def test_route_outcome_is_not_attributed_by_symbol_alone():
    before = int(bot.STATS.get("v702_route_telemetry_unattributed", 0) or 0)
    ok = bot._v702_pipeline_route_outcome("ABC/USDT", "PREEXEC_BLOCK", "reason", source="test", candidate=None)
    assert ok is False
    assert int(bot.STATS.get("v702_route_telemetry_unattributed", 0) or 0) == before + 1


def test_telegram_http_200_requires_valid_bot_api_payload():
    assert bot._v696_telegram_api_ack_valid('{"ok":true,"result":{"message_id":3}}') is True
    assert bot._v696_telegram_api_ack_valid('{"ok":false,"description":"denied"}') is False
    assert bot._v696_telegram_api_ack_valid("not-json") is False
    assert bot._v696_telegram_api_ack_valid('{"ok":true,"result":null}') is False


def test_pending_trade_state_never_claims_a_fill_before_reconciliation():
    trade = bot.TradeState(symbol="ABC/USDT", trace_id="pending", entry=10.0,
                           planned_entry=10.0, original_sl=9.5, current_sl=9.5,
                           target_plan_pending=True, status="entry_pending_reconcile",
                           entry_filled=False, entry_fill_amount=0.0,
                           entry_requested_amount=1.0, entry_reconcile_required=True,
                           position_size_asset=0.0, remaining_position=0.0,
                           entry_order_ids=["venue-unknown"])
    assert trade.status == "entry_pending_reconcile"
    assert trade.entry_filled is False
    assert trade.entry_fill_amount == trade.remaining_position == 0.0
    assert trade.entry_reconcile_required is True



def _a52_valid_score_kwargs():
    return {
        "htf_passed": True, "htf_strength": 75.0, "htf_state": "STRICT_BULLISH",
        "structure_confidence": 80.0, "reclaim_detected": False, "bos_detected": False,
        "retest_quality_score": 75.0, "volume_ratio": 1.5, "vol_delta_score": 1.0,
        "orderbook_imbalance": 0.65, "momentum_score_val": 6.0, "rs_score_val": 4.0,
        "spread_pct": 0.04, "liquidity_tier": "MAJORS", "sweep_detected": False,
        "equal_lows_sweep": False, "rejection_type": "none", "zone_quality_class": "NORMAL",
        "symbol": "TEST/USDT", "strategy_mode": "PULLBACK", "measured_rr": 2.5,
    }


def test_a52_composite_scorer_rejects_non_finite_values_across_numeric_contract():
    fields = ("htf_strength", "structure_confidence", "retest_quality_score", "volume_ratio",
              "vol_delta_score", "orderbook_imbalance", "momentum_score_val", "rs_score_val",
              "spread_pct", "measured_rr")
    for field in fields:
        for bad in (math.inf, -math.inf, math.nan):
            values = _a52_valid_score_kwargs()
            values[field] = bad
            score, grade, detail = bot.CompositeScorer.build(**values)
            assert score == 0.0, (field, bad, score, grade, detail)
            assert grade == "C_REJECT"
            assert detail.get("reason") == "invalid_score_input"


def test_sizing_engine_rejects_nonfinite_price_geometry_before_balance_lookup(monkeypatch):
    async def balance_must_not_be_read(_exchange):
        raise AssertionError("invalid price geometry must be rejected before balance/API reads")

    monkeypatch.setattr(bot.BalanceReconciler, "fetch", balance_must_not_be_read)
    valid = {"entry": 100.0, "sl": 99.5, "tp1": 101.2, "tp2": 102.0, "tp3": 103.0}
    cases = (
        {"entry": math.nan},
        {"entry": math.inf},
        {"sl": math.nan},
        {"sl": math.inf},
        {"tp1": math.nan},
        {"tp2": math.inf},
        {"tp3": math.nan},
        {"spread_pct": math.nan},
        {"spread_pct": -0.01},
    )
    for bad_fields in cases:
        values = {**valid, **bad_fields}
        spread = values.pop("spread_pct", None)
        decision = asyncio.run(
            bot.SizingEngine.decide(
                None, "TEST/USDT", values["entry"], values["sl"],
                values["tp1"], values["tp2"], tp3=values["tp3"],
                strategy_score=90.0, quality_grade="A+", spread_pct=spread,
            )
        )
        assert decision.status == "REJECT"
        assert decision.reject_reason == "invalid_price_geometry"
        assert math.isfinite(decision.quantity_asset) and decision.quantity_asset == 0.0
        assert math.isfinite(decision.raw_position_value) and decision.raw_position_value == 0.0


def test_sizing_engine_rejects_invalid_price_order_before_balance_lookup(monkeypatch):
    async def balance_must_not_be_read(_exchange):
        raise AssertionError("invalid price ordering must be rejected before balance/API reads")

    monkeypatch.setattr(bot.BalanceReconciler, "fetch", balance_must_not_be_read)
    decision = asyncio.run(
        bot.SizingEngine.decide(
            None, "TEST/USDT", 100.0, 100.0, 101.0, 102.0,
            strategy_score=90.0, quality_grade="A+",
        )
    )
    assert decision.status == "REJECT"
    assert decision.reject_reason == "invalid_price_geometry"


def test_sizing_engine_valid_geometry_produces_finite_risk_capped_paper_decision(monkeypatch):
    async def fake_balance(_exchange):
        return 100.0, "REAL"

    monkeypatch.setattr(bot.BalanceReconciler, "fetch", fake_balance)
    monkeypatch.setattr(bot, "ACTIVE_TRADES", {})
    settings = {
        "RISK_PER_TRADE_PCT": 1.0, "MIN_SL_PCT": 0.4, "MAX_SL_PCT": 5.0,
        "MAX_POSITION_SIZE_USDT": 75.0, "MIN_POSITION_SIZE_USDT": 15.0,
        "FIXED_POSITION_SIZE_USDT": 75.0, "POSITION_SIZING_MODE": "HYBRID_CAP",
        "ENABLE_LIVE_TRADING": False, "PAPER_TRADING_MODE": True,
        "V702_GRADE_TICKET_SIZING_ENABLE": False,
        "V702_QUALITY_SCALED_TICKET_ENABLE": False,
        "V702_SMALL_NET_PROFIT_MODE_ENABLE": False,
        "MAX_TOTAL_EXPOSURE_PCT": 99.0, "TRADING_BALANCE_RESERVE_USDT": 0.0,
        "TAKER_FEE_PCT": 0.1, "ROUNDTRIP_FEE_MULT": 2.0,
        "MIN_NET_RR_TP1": 0.1, "MIN_TP1_TO_FEE_RATIO": 2.5,
        "TP1_EXIT_PCT": 0.5, "TP2_EXIT_PCT": 0.3,
        "RUNNER_KEEP_PCT_AT_TP3": 0.2, "ENABLE_RUNNER_MODE": True,
    }
    for key, value in settings.items():
        monkeypatch.setitem(bot.CONFIG, key, value)

    decision = asyncio.run(
        bot.SizingEngine.decide(
            None, "TEST/USDT", 100.0, 99.5, 103.0, 105.0, tp3=107.0,
            strategy_score=90.0, quality_grade="A+",
        )
    )
    assert decision.status == "OK"
    assert decision.notional_after_caps <= settings["MAX_POSITION_SIZE_USDT"]
    assert math.isfinite(decision.quantity_asset) and decision.quantity_asset > 0.0
    assert math.isfinite(decision.effective_risk_usdt)
    assert decision.effective_risk_usdt <= decision.target_risk_usdt


def test_a52_composite_scorer_treats_htf_sentinel_as_missing_not_quality():
    values = _a52_valid_score_kwargs()
    values["htf_strength"] = bot.CompositeScorer._MISSING
    score, grade, detail = bot.CompositeScorer.build(**values)
    assert score == 0.0
    assert grade == "C_REJECT"
    assert detail.get("reason") == "insufficient_score_data"
    assert "htf_strength" in detail.get("missing_names", "")


def test_a52_client_order_id_is_only_enabled_for_mexc_spot_methods_with_params():
    class FakeMexc:
        id = "mexc"
        async def create_market_buy_order(self, symbol, amount, params=None):
            return {"id": "unused"}

    class FakeOther(FakeMexc):
        id = "binance"

    with patch.dict(bot.CONFIG, {"MARKET_TYPE": "SPOT", "LONG_ONLY": True,
                                 "V702_A52_CLIENT_ORDER_ID_ENABLE": True}):
        cid, params = bot._v702_a52_client_order_params(FakeMexc(), "create_market_buy_order")
        assert cid.startswith("us") and len(cid) == 30
        assert params == {"clientOrderId": cid}
        assert bot._v702_a52_client_order_params(FakeOther(), "create_market_buy_order") == ("", {})


def test_a52_telegram_queue_eviction_settles_failure_callback():
    cls = bot.TelegramDispatcher
    old_queue = cls._queue
    old_callbacks = cls._delivery_callbacks
    old_recent = cls._recent_enqueued_keys
    old_enabled = bot.CONFIG.get("TELEGRAM_ENABLED", True)
    old_token, old_chat = bot.ENV.get("TELEGRAM_TOKEN"), bot.ENV.get("TELEGRAM_CHAT")
    seen = []
    try:
        cls._queue = deque(maxlen=1)
        cls._delivery_callbacks = defaultdict(list)
        cls._recent_enqueued_keys = {}
        bot.CONFIG["TELEGRAM_ENABLED"] = True
        bot.ENV["TELEGRAM_TOKEN"], bot.ENV["TELEGRAM_CHAT"] = "test-token", "test-chat"
        async def scenario():
            assert await cls.enqueue("a52-callback-message-1", on_failure=lambda reason: seen.append(reason))
            assert await cls.enqueue("a52-callback-message-2")
        asyncio.run(scenario())
        assert seen == ["queue_evicted"]
        assert len(cls._queue) == 1
        assert "a52-callback-message-2" in cls._queue
    finally:
        cls._queue = old_queue
        cls._delivery_callbacks = old_callbacks
        cls._recent_enqueued_keys = old_recent
        bot.CONFIG["TELEGRAM_ENABLED"] = old_enabled
        if old_token is None:
            bot.ENV.pop("TELEGRAM_TOKEN", None)
        else:
            bot.ENV["TELEGRAM_TOKEN"] = old_token
        if old_chat is None:
            bot.ENV.pop("TELEGRAM_CHAT", None)
        else:
            bot.ENV["TELEGRAM_CHAT"] = old_chat


def test_a52_healthcheck_rejects_json_nan_heartbeat_timestamp(tmp_path):
    heartbeat = tmp_path / "heartbeat.json"
    heartbeat.write_text('{"timestamp":NaN,"state":"RUNNING"}', encoding="utf-8")
    env = dict(os.environ)
    env["V702_HEARTBEAT_FILE"] = str(heartbeat)
    result = subprocess.run(
        [sys.executable, str(Path(bot.__file__).with_name("healthcheck.py"))],
        cwd=str(Path(bot.__file__).parent), env=env, text=True, capture_output=True, timeout=10,
    )
    assert result.returncode == 1
    assert "unhealthy:" in result.stdout


def test_a52_target_only_reservations_prevent_cumulative_oversell(monkeypatch):
    class Exchange:   
        def __init__(self):
            self.created = []
        async def fetch_order(self, order_id, symbol):
            assert order_id == "existing-tp1"
            return {"id": order_id, "symbol": symbol, "side": "sell",
                    "status": "open", "amount": 0.6, "filled": 0.0}
        async def create_limit_sell_order(self, symbol, amount, price):
            self.created.append(float(amount))
            return {"id": f"new-{len(self.created)}", "symbol": symbol,
                    "side": "sell", "status": "open", "amount": amount, "filled": 0.0}

    trade = bot.TradeState(
        symbol="ABC/USDT", trace_id="a52-target-reserve", entry=10.0, planned_entry=10.0,
        original_sl=9.5, current_sl=9.5, position_size_asset=1.0, remaining_position=1.0,
        tp1=10.5, tp2=11.0, tp3=12.0, target_only_mode=True, target_orders_active=True,
        tp1_order_id="existing-tp1",
    )
    exchange = Exchange()
    async def _normalizer(_exchange, _symbol, qty, px):
        return float(qty), float(px), None
    monkeypatch.setattr(bot.OrderExecutor, "_normalize_qty_price_with_reload", staticmethod(_normalizer))
    with patch.dict(bot.CONFIG, {"SL_FAILURE_TARGET_ONLY_PLACE_LIMITS": True,
                                 "ENABLE_RUNNER_MODE": True, "SL_FAILURE_TARGET_ONLY_ALLOW_TP3": True,
                                 "V561_TARGET_RECREATE_ON_CANCEL": False}):
        placed = asyncio.run(bot._v557_place_target_only_orders(exchange, trade))
    assert placed == 2
    assert exchange.created == pytest.approx([0.3, 0.1])
    assert 0.6 + sum(exchange.created) <= 1.0 + 1e-9


def test_a52_target_only_ambiguous_create_stops_later_target_submissions(monkeypatch):
    class Exchange:
        def __init__(self):
            self.created = 0
        async def create_limit_sell_order(self, symbol, amount, price):
            self.created += 1
            raise TimeoutError("create outcome unknown")

    trade = bot.TradeState(
        symbol="ABC/USDT", trace_id="a52-target-unknown", entry=10.0, planned_entry=10.0,
        original_sl=9.5, current_sl=9.5, position_size_asset=1.0, remaining_position=1.0,
        tp1=10.5, tp2=11.0, tp3=12.0, target_only_mode=True, target_orders_active=True,
    )
    exchange = Exchange()
    async def _normalizer(_exchange, _symbol, qty, px):
        return float(qty), float(px), None
    monkeypatch.setattr(bot.OrderExecutor, "_normalize_qty_price_with_reload", staticmethod(_normalizer))
    with patch.dict(bot.CONFIG, {"SL_FAILURE_TARGET_ONLY_PLACE_LIMITS": True,
                                 "ENABLE_RUNNER_MODE": True, "SL_FAILURE_TARGET_ONLY_ALLOW_TP3": True,
                                 "V561_TARGET_RECREATE_ON_CANCEL": False}):
        placed = asyncio.run(bot._v557_place_target_only_orders(exchange, trade))
    assert placed == 0
    assert exchange.created == 1
    assert trade.target_order_ambiguous is True
    assert trade.target_order_ambiguous_reason == "target_creation_outcome_unknown"


def test_a52_rejection_reason_identity_dedupes_dynamic_values_but_keeps_detail():
    assert bot._v702_a52_reason_identity("score_below_threshold:52.7<70.0") == "score_below_threshold"
    assert bot._v702_a52_reason_identity("score_below_threshold:46.5<70.0") == "score_below_threshold"
    assert bot._v702_a52_reason_identity("liquidity.spread=0.04") == "liquidity.spread"
    assert bot._v702_a52_reason_identity("htf.family_htf_strength~b88f5f") == "htf.family_htf_strength"
    assert bot._v702_a52_reason_identity("family_policy:family_regime_disallowed.macro") == "family_policy:family_regime_disallowed.macro"


def test_a52_reconciliation_queries_mexc_by_persisted_client_id_and_requires_exact_match():
    class FakeMexc:
        id = "mexc"
        def __init__(self, client_id):
            self.client_id = client_id
            self.calls = []
        async def fetch_order(self, order_id, symbol, params=None):
            self.calls.append((order_id, symbol, dict(params or {})))
            if order_id == "" and params == {"clientOrderId": "a52-client-exact"}:
                return {"id": "venue-123", "symbol": symbol, "side": "buy",
                        "clientOrderId": self.client_id, "status": "open",
                        "amount": 1.0, "filled": 0.25}
            return {"id": order_id, "symbol": symbol, "side": "buy",
                    "clientOrderId": self.client_id, "status": "open",
                    "amount": 1.0, "filled": 0.25}

    async def _run(client_id):
        exchange = FakeMexc(client_id)
        row = {"intent_id": "a52-intent", "symbol": "BTC/USDT", "side": "buy",
               "status": "SUBMISSION_UNKNOWN", "venue_order_id": "",
               "details": {"clientOrderId": "a52-client-exact"}}
        with patch.object(bot.DBManager, "aupdate_execution_intent", new=AsyncMock()):
            with patch.dict(bot.CONFIG, {"MARKET_TYPE": "SPOT",
                                         "V702_A41_EXECUTION_INTENT_RECONCILIATION_TIMEOUT_SEC": 3.0}):
                result = await bot._v702_a41_reconcile_one_intent_order(exchange, row, open_orders=None)
        return result, exchange

    good, exchange = asyncio.run(_run("a52-client-exact"))
    assert exchange.calls[0] == ("", "BTC/USDT", {"clientOrderId": "a52-client-exact"})
    assert good["venue_order_id"] == "venue-123"
    assert good["outcome"] == "FILLED_REQUIRES_POSITION_PROTECTION"
    bad, _ = asyncio.run(_run("different-client-id"))
    assert bad["outcome"] == "UNRESOLVED"
    assert bad["reason"] == "client_order_id_lookup_mismatch_or_missing"


def test_a53_blocked_alert_uses_last_closed_5m_candle_key(monkeypatch):
    """Blocked-outcome alert must match the same closed candle as the opportunity."""
    now = bot.WALL_NOW()
    rejection_map = dict(bot.STATS.get("v523_last_rejection_by_symbol") or {})
    rejection_map["ABC/USDT"] = {"ts": now, "reason": "submit_failed:balance", "stage": "submit", "score": 72.0}
    monkeypatch.setitem(bot.STATS, "v523_last_rejection_by_symbol", rejection_map)
    captured = {}

    async def original(*args, **kwargs):
        return None

    def notify_blocked(symbol, **kwargs):
        captured["symbol"] = symbol
        captured.update(kwargs)
        return True

    monkeypatch.setattr(bot, "_orig_build_and_route_v523", original)
    monkeypatch.setattr(bot.OpportunityTelegramNotifier, "notify_blocked", staticmethod(notify_blocked))
    index = pd.date_range("2026-10-21T10:00:00Z", periods=4, freq="5min")
    df5 = pd.DataFrame({"close": [1.0, 1.1, 1.2, 1.3]}, index=index)
    result = asyncio.run(bot._v523_build_and_route(None, "ABC/USDT", {"df_5m": df5}))
    assert result is None
    assert captured["symbol"] == "ABC/USDT"
    assert captured["candle_ts"] == int(index[-2].timestamp())
    assert captured["candle_ts"] != int(index[-1].timestamp())


def test_a53_swing_contract_overrides_stale_scalp_timeframe_metadata():
    candidate = bot.StrategyCandidate(
        engine_id="mtf_pullback", symbol="ABC/USDT", side="long", generated_at_ms=1,
        entry_ref=100.0, sl_price=96.0, tp1_rr=1.0, tp2_rr=2.2, tp3_rr=5.0,
        engine_score=0.82, rr_ratio=1.0, liquidity_score=0.9, regime_fit=0.9,
        family="MTF_PULLBACK", zone_ref=99.0,
        features_snapshot={"strategy_mode": "MTF_PULLBACK", "strategy_style": "SWING",
                           "timeframe_profile": "5M_1M"},
        strategy_mode="MTF_PULLBACK", strategy_style="SWING", timeframe_profile="15M_5M",
    )
    normalized = bot._v701_3_normalize_candidate(candidate)
    assert normalized.strategy_style == "SWING"
    assert normalized.timeframe_profile == "1D_4H_15M_5M"
    assert normalized.features_snapshot["timeframe_profile"] == "1D_4H_15M_5M"
    assert normalized.features_snapshot["execution_profile"] == "SWING_EARLY"


def test_a53_exit_lifecycle_message_reports_mode_trace_and_telegram_ack(monkeypatch):
    captured = {}
    async def fake_enqueue(message, on_success=None, on_failure=None):
        captured["message"] = message
        captured["on_success"] = on_success
        captured["on_failure"] = on_failure
        if callable(on_success):
            on_success("fake_telegram_ack")
        return True

    monkeypatch.setattr(bot.TelegramDispatcher, "enqueue", staticmethod(fake_enqueue))
    bot.OpportunityTelegramNotifier._blocked_seen.clear()
    before = int(bot.STATS.get("telegram_lifecycle_delivered", 0) or 0)
    trade = bot.TradeState(
        symbol="ABC/USDT", trace_id="a53-trace-123", entry=100.0, original_sl=98.0,
        current_sl=98.0, is_paper=False, execution_mode="LIVE", status="sl_hit",
    )
    asyncio.run(bot.OpportunityTelegramNotifier.notify_exit_event(
        trade, "STOP LOSS HIT", fill_px=98.0, remaining=0.0, extra="Exit reason=sl_hit"
    ))
    message = captured["message"]
    assert "STOP LOSS HIT" in message
    assert "Mode: <b>LIVE</b>" in message
    assert "a53-trace-123" in message
    assert callable(captured["on_failure"])
    assert int(bot.STATS.get("telegram_lifecycle_delivered", 0) or 0) == before + 1

@pytest.mark.asyncio
async def test_a53_entry_fill_message_precedes_protection_and_tracks_delivery(monkeypatch):
    delivered = []
    async def fake_enqueue(message, *, on_success=None, on_failure=None):
        delivered.append(message)
        if on_success:
            on_success("test-telegram-ack")
        return True
    monkeypatch.setattr(bot.TelegramDispatcher, "enqueue", staticmethod(fake_enqueue))
    trade = SimpleNamespace(
        symbol="XMR/USDT", trace_id="trace-a53-entry", execution_mode="LIVE", is_paper=False,
        strategy_mode="MTF_PULLBACK", strategy_style="SWING", timeframe_profile="1D_4H_15M_5M",
        score=78.0, entry=596.2, entry_fill_price=596.2, entry_fill_amount=0.25,
        remaining_position=0.25, current_sl=592.0, tp1=602.0, tp2=608.0, tp3=615.0,
        entry_order_ids=["mexc-order-a53"],
    )
    await bot.OpportunityTelegramNotifier.notify_entry_event(
        trade, "ENTRY FILLED — PROTECTION PENDING", protection="PENDING",
        extra="Exchange stop has not yet been verified."
    )
    assert len(delivered) == 1
    message = delivered[0]
    assert "ENTRY FILLED" in message
    assert "Mode:" in message and "LIVE" in message
    assert "MTF_PULLBACK" in message and "SWING" in message
    assert "1D_4H_15M_5M" in message
    assert "Actual fill" in message and "Filled quantity" in message
    assert "trace-a53-entry" in message
    assert "mexc-order-a53" in message and "TP3" in message
    assert "telegram_lifecycle_delivered.ENTRY_FILLED_PROTECTION_PENDING" in bot.STATS


def test_a53_execution_boundary_uses_swing_contract_not_stale_scalp_metadata():
    mode, style, timeframe, found = bot._v701_3_resolve_strategy_identity(
        "MTF_PULLBACK", "PULLBACK", fallback_style="SCALP", fallback_timeframe="5M_1M"
    )
    assert found is True
    assert mode == "MTF_PULLBACK"
    assert style == "SWING"
    assert timeframe == "1D_4H_15M_5M"
    source = Path(bot.__file__).read_text(encoding="utf-8")
    assert source.count("_v701_3_resolve_strategy_identity(") >= 2  # definition + live Builder use
    assert "The position exists despite protection failure" in source
    assert "# A fill is not a no-execution outcome" in source


def test_a66_final_validator_cannot_override_failed_inherited_validator(monkeypatch):
    monkeypatch.setattr(bot, "_V702_A66_PREVIOUS_VALIDATE_CONFIG", lambda: False)
    monkeypatch.setattr(bot, "_v702_a66_startup_recovery_source_check",
                        lambda: {"pass": True, "checks": {"a66": True}, "failed": []})
    assert bot._v702_a66_validate_config() is False
    report = bot.STATS["v702_a66_final_validation"]
    assert report["pass"] is False
    assert report["base_previous"] is False
    assert "previous_validator_failed" in report["failed"]


def test_break_even_or_profit_lock_is_valid_active_protection():
    trade = SimpleNamespace(
        remaining_position=1.0, entry=100.0, current_sl=100.15, original_sl=98.0,
        sl_order_id=None, sl_health_state="SOFTWARE_SL_ACTIVE", software_sl_active=True,
    )
    assert bot._v563_trade_protection_healthy(trade) is True


def test_protection_ticker_has_priority_over_scanner_ticker():
    assert bot.V702PlatformRateLimiter.priority("protected_fetch_ticker_BTC/USDT")[1] == "PROTECTION"
    assert bot.V702PlatformRateLimiter.priority("fetch_ticker_BTC/USDT")[1] == "SCAN"


def test_telegram_outbox_is_durable_and_terminal_ack_removes_pending(tmp_path, monkeypatch):
    db_path = tmp_path / "telegram-outbox.sqlite3"
    with patch.dict(bot.CONFIG, {"DB_PATH": str(db_path)}):
        bot.DBManager.init_schema()
        outbox_id = bot.DBManager.enqueue_telegram_outbox("critical operator alert")
        pending = bot.DBManager.list_pending_telegram_outbox()
        assert any(row["outbox_id"] == outbox_id and row["status"] == "QUEUED" for row in pending)
        assert bot.DBManager.update_telegram_outbox(outbox_id, "DELIVERED", 1, None)
        pending_after_ack = bot.DBManager.list_pending_telegram_outbox()
        assert all(row["outbox_id"] != outbox_id for row in pending_after_ack)


@pytest.mark.asyncio
async def test_pm_task_does_not_renew_health_lease_after_incomplete_cycle(monkeypatch, tmp_path):
    shutdown = asyncio.Event()
    monkeypatch.setattr(bot, "_SHUTDOWN", shutdown)
    monkeypatch.setattr(bot, "ACTIVE_TRADES", {"ABC/USDT": object()})
    monkeypatch.setitem(bot.CONFIG, "POSITION_MANAGER_INTERVAL_SEC", 0.20)
    heartbeat_writes = []
    monkeypatch.setattr(bot, "_v702_atomic_heartbeat_write", lambda *args, **kwargs: heartbeat_writes.append(args))

    async def _failed_tick(cls, exchange):
        shutdown.set()
        return {"healthy": False, "failed_by_symbol": {"ABC/USDT": "ERROR:fetch_ticker"}}

    monkeypatch.setattr(bot.PositionManager, "tick", classmethod(_failed_tick))
    await asyncio.wait_for(bot._position_manager_task(object()), timeout=2.0)
    assert bot.STATS["v702_pm_last_healthy_ts"] == 0.0
    assert bot.STATS["v702_pm_healthy_ticks"] == 0
    assert not heartbeat_writes
    assert "position_protection_cycle_incomplete" in bot.STATS["v702_pm_last_error"]


def test_tp1_reports_full_close_and_partial_realized_net_separately(monkeypatch):
    monkeypatch.setitem(bot.CONFIG, "TP1_EXIT_PCT", 0.60)
    monkeypatch.setitem(bot.CONFIG, "TP2_EXIT_PCT", 0.30)
    monkeypatch.setitem(bot.CONFIG, "RUNNER_KEEP_PCT_AT_TP3", 0.10)
    monkeypatch.setitem(bot.CONFIG, "ENABLE_RUNNER_MODE", True)
    monkeypatch.setitem(bot.CONFIG, "TAKER_FEE_PCT", 0.10)
    monkeypatch.setitem(bot.CONFIG, "ROUNDTRIP_FEE_MULT", 2.0)
    monkeypatch.setitem(bot.CONFIG, "V702_SMALL_NET_MIN_NET_PROFIT_PCT", 0.10)
    monkeypatch.setitem(bot.CONFIG, "V702_SMALL_NET_MIN_NET_RR_TP1", 0.25)
    monkeypatch.setitem(bot.CONFIG, "V702_SMALL_NET_MIN_NET_RR_OVERALL", 0.50)
    result = bot.SizingEngine.fee_viability_detail(
        100.0, 99.0, 101.0, 102.0, 1000.0, small_net_mode=True,
    )
    assert result["ok"] is True, result
    assert result["TP1_PARTIAL_EXIT_FRACTION"] == pytest.approx(0.60)
    assert result["TP1_FULL_CLOSE_NET_USDT"] == pytest.approx(result["net_profit_tp1_usdt"])
    assert result["TP1_PARTIAL_REALIZED_NET_USDT"] == pytest.approx(
        result["TP1_FULL_CLOSE_NET_USDT"] * 0.60
    )
    assert result["TP1_PARTIAL_REALIZED_NET_PCT_OF_ORIGINAL"] == pytest.approx(
        result["TP1_FULL_CLOSE_NET_PCT"] * 0.60
    )


def test_cost_model_never_clips_high_measured_cost_and_rejects_nan_fee():
    model = unified_round_trip_cost_model(
        {"V702_MEASURED_COST_BUFFER_PCT": 0.05}, measured_cost_pct=25.0,
        spread_pct=12.0, fee_cost_pct=0.20,
    )
    assert model["round_trip_cost_pct"] == pytest.approx(25.05)
    assert model["measured_cost_pct"] == pytest.approx(25.0)
    with pytest.raises(ValueError):
        unified_round_trip_cost_model({}, spread_pct=0.2, fee_cost_pct=float("nan"))


def _make_hunter_frame(interval_sec: int, *, closed_count: int = 80, incomplete_spike: bool = False):
    """Deterministic rising OHLCV series with an unfinished last exchange bar."""
    now = time.time()
    current_open = int(now // interval_sec) * interval_sec
    stamps = [current_open - (closed_count - i) * interval_sec for i in range(closed_count)]
    stamps.append(current_open)  # current/incomplete bar; must never drive a trigger
    closes = [100.0 + i * 0.03 for i in range(closed_count)]
    last_incomplete = closes[-1] + (4.0 if incomplete_spike else 0.02)
    closes.append(last_incomplete)
    frame = pd.DataFrame({
        "open": [x - 0.02 for x in closes],
        "high": [x + 0.15 for x in closes],
        "low": [x - 0.15 for x in closes],
        "close": closes,
        "volume": [100.0] * closed_count + ([10000.0] if incomplete_spike else [100.0]),
    }, index=pd.to_datetime(stamps, unit="s", utc=True))
    return frame




def _outcome_test_frame(now, *, bars=None, period=300):
    current_open = int(float(now) // period) * period
    # Sixty completed bars plus the currently forming bar, which the canonical
    # closed-frame validator must discard.
    stamps = [current_open - (60 - i) * period for i in range(60)] + [current_open]
    values = []
    for _ in stamps:
        values.append({"open": 100.0, "high": 100.2, "low": 99.5,
                       "close": 100.0, "volume": 100.0})
    for offset, candle in (bars or {}).items():
        values[offset] = {**values[offset], **candle}
    return pd.DataFrame(values, index=pd.to_datetime(stamps, unit="s", utc=True))


def _outcome_test_row(created_at, *, expires_at=None):
    return {
        "opportunity_id": "outcome-test", "symbol": "AAA/USDT", "family": "TEST",
        "pattern": "TEST_PATTERN", "status": "WATCH", "created_at": float(created_at),
        "expires_at": float(expires_at if expires_at is not None else time.time() + 3600),
        "entry_ref": 100.0, "sl_price": 99.0, "tp1": 101.0, "tp2": 102.0,
        "tp3": 103.0, "outcome_status": "PENDING", "outcome_events": [],
        "outcome_last_candle_ts": 0, "outcome_final": 0, "outcome_reason": "",
    }


def test_shadow_outcome_tracks_sequential_tp_targets_and_completes_at_tp3():
    now = time.time()
    raw = _outcome_test_frame(now, bars={
        -4: {"high": 101.2, "close": 100.8},
        -3: {"high": 102.2, "close": 101.8},
        -2: {"high": 103.2, "close": 102.8},
    })
    closed, _ = bot.OpportunityHunter._closed_frame(raw, 300, now=now)
    assert closed is not None
    first_target_open = int(pd.Timestamp(closed.index[-3]).timestamp())
    row = _outcome_test_row(first_target_open - 1, expires_at=now + 600)
    updates, events = bot.OpportunityHunter._advance_shadow_outcome(row, closed, now=now)
    kinds = [e["kind"] for e in events]
    assert kinds == ["SHADOW_TP1_TOUCHED", "SHADOW_TP2_TOUCHED", "SHADOW_TP3_TOUCHED"]
    assert updates["outcome_status"] == "SHADOW_TP3_TOUCHED"
    assert updates["outcome_final"] == 1
    assert updates["outcome_last_candle_ts"] == int(pd.Timestamp(closed.index[-1]).timestamp())


def test_shadow_outcome_uses_stop_first_when_one_closed_candle_touches_target_and_stop():
    now = time.time()
    raw = _outcome_test_frame(now, bars={-2: {"high": 101.5, "low": 98.5, "close": 100.2}})
    closed, _ = bot.OpportunityHunter._closed_frame(raw, 300, now=now)
    first_target_open = int(pd.Timestamp(closed.index[-2]).timestamp())
    row = _outcome_test_row(first_target_open - 1, expires_at=now + 600)
    updates, events = bot.OpportunityHunter._advance_shadow_outcome(row, closed, now=now)
    assert len(events) == 1
    assert events[0]["kind"] == "SHADOW_STOP_AMBIGUOUS_STOP_FIRST"
    assert events[0]["targets_also_touched"] == [1]
    assert updates["outcome_status"] == "SHADOW_STOP_HIT"
    assert updates["outcome_final"] == 1


def test_shadow_outcome_skips_signal_candle_but_records_later_target_before_expiry():
    now = time.time()
    raw = _outcome_test_frame(now, bars={-3: {"high": 101.5, "close": 100.5}})
    closed, _ = bot.OpportunityHunter._closed_frame(raw, 300, now=now)
    signal_open = int(pd.Timestamp(closed.index[-2]).timestamp())
    # Candidate appeared during the signal candle: its own high is excluded.
    row = _outcome_test_row(signal_open + 60, expires_at=now + 600)
    updates, events = bot.OpportunityHunter._advance_shadow_outcome(row, closed, now=now)
    assert events == []
    assert updates["outcome_status"] == "SHADOW_OPEN"
    assert updates["outcome_last_candle_ts"] == int(pd.Timestamp(closed.index[-1]).timestamp())

    # A separate candidate whose first eligible closed candle touched TP1 is
    # expired in the same evaluation; both its partial target and expiry stay.
    target_open = int(pd.Timestamp(closed.index[-2]).timestamp())
    expiring = _outcome_test_row(target_open - 1, expires_at=now - 1)
    updates, events = bot.OpportunityHunter._advance_shadow_outcome(expiring, closed, now=now)
    assert [e["kind"] for e in events] == ["SHADOW_TP1_TOUCHED", "SHADOW_EXPIRED_AFTER_TP1"]
    assert updates["outcome_status"] == "SHADOW_EXPIRED_AFTER_TP1"
    assert updates["outcome_final"] == 1


def test_opportunity_upsert_keeps_candidate_geometry_immutable_and_separates_candidate_keys(tmp_path):
    db_path = tmp_path / "hunter_geometry.sqlite3"
    with patch.dict(bot.CONFIG, {"DB_PATH": str(db_path), "TELEGRAM_ENABLED": False}, clear=False):
        bot.OpportunityHunter._schema_ready_paths.discard(str(db_path))
        first = {"candidate_key": "A|AAA/USDT|PULLBACK|1", "symbol": "AAA/USDT",
                 "family": "PULLBACK", "pattern": "PULLBACK_RECLAIM", "status": "WATCH",
                 "entry_ref": 100.0, "sl_price": 99.0, "tp1": 101.0, "tp2": 102.0, "tp3": 103.0}
        row, created = bot.OpportunityHunter._upsert(first, notify=False)
        assert created
        changed = {**first, "entry_ref": 110.0, "sl_price": 108.0,
                   "tp1": 112.0, "tp2": 114.0, "tp3": 116.0, "last_price": 111.0}
        same, created_again = bot.OpportunityHunter._upsert(changed, notify=False)
        assert not created_again
        assert (same["entry_ref"], same["sl_price"], same["tp1"], same["tp2"], same["tp3"]) == (100.0, 99.0, 101.0, 102.0, 103.0)
        other, other_created = bot.OpportunityHunter._upsert({**first, "candidate_key": "A|AAA/USDT|PULLBACK|2"}, notify=False)
        assert other_created and other["opportunity_id"] != row["opportunity_id"]
        assert len(bot.OpportunityHunter._active_rows(20)) >= 2


def test_opportunity_scan_persists_tp3_completion_and_monitors_tracked_symbol_outside_discovery_cap(tmp_path, monkeypatch):
    db_path = tmp_path / "hunter_tp3_scan.sqlite3"
    now = time.time()
    raw = _outcome_test_frame(now, bars={
        -4: {"high": 101.2, "close": 100.8},
        -3: {"high": 102.2, "close": 101.8},
        -2: {"high": 103.2, "close": 102.8},
    })
    closed, _ = bot.OpportunityHunter._closed_frame(raw, 300, now=now)
    first_open = int(pd.Timestamp(closed.index[-3]).timestamp())
    monkeypatch.setattr(bot.OpportunityHunter, "_evaluate_snapshot", classmethod(lambda cls, *args, **kwargs: []))
    with patch.dict(bot.CONFIG, {
        "DB_PATH": str(db_path), "TELEGRAM_ENABLED": False,
        "V702_OPPORTUNITY_HUNTER_TELEGRAM_ENABLE": False,
        "V702_OPPORTUNITY_HUNTER_MAX_SYMBOLS_PER_CYCLE": 1,
    }, clear=False):
        bot.OpportunityHunter._schema_ready_paths.discard(str(db_path))
        row, created = bot.OpportunityHunter._upsert({
            "candidate_key": "scan-tp3|AAA/USDT|1", "symbol": "AAA/USDT",
            "family": "TEST", "pattern": "TEST_PATTERN", "status": "WATCH",
            "entry_ref": 100.0, "sl_price": 99.0, "tp1": 101.0, "tp2": 102.0,
            "tp3": 103.0, "invalidation_price": 99.0, "last_price": 100.0,
            "expires_at": now + 900,
        }, notify=False)
        assert created
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE opportunity_hunter SET created_at=? WHERE opportunity_id=?", (first_open - 1, row["opportunity_id"]))
        conn.commit(); conn.close()
        # AAA is after the one-symbol discovery slice, but is a persisted watch
        # and must still get its closed-candle outcome follow-up.
        summary = asyncio.run(bot.OpportunityHunter.scan_market_map({
            "OTHER/USDT": {}, "AAA/USDT": {"df_5m": raw},
        }))
        saved = bot.OpportunityHunter._get_by_id(row["opportunity_id"])
        assert summary["scanned"] == 1
        assert saved["status"] == "COMPLETED"
        assert saved["outcome_status"] == "SHADOW_TP3_TOUCHED"
        assert saved["outcome_final"] == 1
        assert bot.OpportunityHunter._active_rows(50) == []
        assert bot.OpportunityHunter.outcome_summary().get("SHADOW_TP3_TOUCHED") == 1


def test_opportunity_outcome_schema_migrates_existing_database_in_place(tmp_path):
    db_path = tmp_path / "hunter_legacy.sqlite3"
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE opportunity_hunter (opportunity_id TEXT PRIMARY KEY, candidate_key TEXT NOT NULL DEFAULT '', symbol TEXT NOT NULL, family TEXT NOT NULL, status TEXT NOT NULL, updated_at REAL NOT NULL)")
    conn.commit(); conn.close()
    with patch.dict(bot.CONFIG, {"DB_PATH": str(db_path)}, clear=False):
        bot.OpportunityHunter._schema_ready_paths.discard(str(db_path))
        bot.OpportunityHunter._ensure_schema()
        conn = sqlite3.connect(db_path)
        columns = {r[1] for r in conn.execute("PRAGMA table_info(opportunity_hunter)")}
        conn.close()
    assert {"outcome_status", "outcome_events_json", "outcome_last_candle_ts",
            "outcome_final", "outcome_updated_at", "outcome_reason"}.issubset(columns)


def test_opportunity_hunter_pipeline_states_are_monotonic_and_read_only(tmp_path):
    db_path = tmp_path / "hunter_states.sqlite3"
    with patch.dict(bot.CONFIG, {
        "DB_PATH": str(db_path), "TELEGRAM_ENABLED": False,
        "V702_OPPORTUNITY_HUNTER_TELEGRAM_ENABLE": False,
    }, clear=False):
        bot.OpportunityHunter._schema_ready_paths.discard(str(db_path))
        item = {
            "candidate_key": "hunter-test|AAA/USDT|BREAKOUT|1",
            "symbol": "AAA/USDT", "family": "BREAKOUT", "pattern": "BREAKOUT_CONTINUATION",
            "source": "TEST", "status": "WATCH", "score": 72.0, "candle_ts": int(time.time()),
            "entry_ref": 100.0, "sl_price": 99.0, "tp1": 101.0, "tp2": 102.0, "tp3": 103.0,
            "last_price": 100.0, "invalidation_price": 99.0, "reason": "test evidence",
            "missing_conditions": ["canonical prequal"], "evidence": {"closed_bar": True},
        }
        row, created = bot.OpportunityHunter._upsert(item, notify=False)
        assert created and row["status"] == "WATCH"
        bot.OpportunityHunter.on_pipeline_event("PREQUAL_PASS", item["candidate_key"], "AAA/USDT", "BREAKOUT")
        row = bot.OpportunityHunter._get_by_id(row["opportunity_id"])
        assert row["status"] == "CONFIRMED"
        assert row["confirmation_type"] == "CANONICAL_PREQUAL"
        bot.OpportunityHunter.on_pipeline_event("SCORE_BLOCK", item["candidate_key"], "AAA/USDT", "BREAKOUT", {"reason": "score_floor"})
        row = bot.OpportunityHunter._get_by_id(row["opportunity_id"])
        assert row["status"] == "CONFIRMED"
        assert any("SCORE_BLOCK" in x for x in row["blockers"])
        bot.OpportunityHunter.on_pipeline_event("PRESEND_PASS", item["candidate_key"], "AAA/USDT", "BREAKOUT")
        row = bot.OpportunityHunter._get_by_id(row["opportunity_id"])
        assert row["status"] == "TRADEABLE"
        bot.OpportunityHunter.on_pipeline_event("PREQUAL_REJECT", item["candidate_key"], "AAA/USDT", "BREAKOUT")
        row = bot.OpportunityHunter._get_by_id(row["opportunity_id"])
        assert row["status"] == "TRADEABLE"  # never regress from a later gate
        assert bot.OpportunityHunter.execution_authority is False
        assert bot.FINAL_CANONICAL_RUNTIME["effective_entry_policy"] == "MONITOR_ONLY_NO_NEW_BUYS"
        assert bot.FINAL_CANONICAL_RUNTIME["live_gates_relaxed"] is False


def test_opportunity_hunter_ignores_unclosed_breakout_spike_and_uses_closed_candles():
    now = time.time()
    df5 = _make_hunter_frame(300, incomplete_spike=True)
    closed, candle_ts = bot.OpportunityHunter._closed_frame(df5, 300, now=now)
    assert closed is not None and candle_ts > 0
    assert float(closed["close"].iloc[-1]) == pytest.approx(float(df5["close"].iloc[-2]))
    assert float(closed["close"].iloc[-1]) != float(df5["close"].iloc[-1])
    df15 = _make_hunter_frame(900, incomplete_spike=True)
    btc15 = _make_hunter_frame(900, incomplete_spike=False)
    results = bot.OpportunityHunter._evaluate_snapshot("AAA/USDT", {
        "df_5m": df5, "df_15m": df15, "df_btc_15m": btc15,
        "quote_vol_24h": 8_000_000.0, "spread_pct": 0.05,
    }, now=now)
    # The unfinished spike cannot be the reason for a CONFIRMED breakout.
    assert all(not (r["pattern"] == "BREAKOUT_CONTINUATION" and r["status"] == "CONFIRMED") for r in results)


def test_opportunity_hunter_rejects_invalid_ohlc_and_duplicate_timestamps():
    good = _make_hunter_frame(300)
    bad = good.copy()
    bad.iloc[-2, bad.columns.get_loc("high")] = bad.iloc[-2]["close"] - 1.0
    closed, _ = bot.OpportunityHunter._closed_frame(bad, 300)
    assert closed is None
    duplicated = pd.concat([good, good.iloc[[-2]]]).sort_index()
    closed, _ = bot.OpportunityHunter._closed_frame(duplicated, 300)
    assert closed is None


def test_opportunity_hunter_scan_persists_watch_and_expires_without_orders(tmp_path):
    db_path = tmp_path / "hunter_scan.sqlite3"
    with patch.dict(bot.CONFIG, {
        "DB_PATH": str(db_path), "TELEGRAM_ENABLED": False,
        "V702_OPPORTUNITY_HUNTER_TELEGRAM_ENABLE": False,
        "V702_OPPORTUNITY_HUNTER_MAX_SYMBOLS_PER_CYCLE": 10,
    }, clear=False):
        bot.OpportunityHunter._schema_ready_paths.discard(str(db_path))
        df5 = _make_hunter_frame(300, incomplete_spike=False)
        df15 = _make_hunter_frame(900, incomplete_spike=False)
        btc15 = _make_hunter_frame(900, incomplete_spike=False)
        summary = asyncio.run(bot.OpportunityHunter.scan_market_map({"AAA/USDT": {
            "df_5m": df5, "df_15m": df15, "df_btc_15m": btc15,
            "quote_vol_24h": 8_000_000.0, "spread_pct": 0.05,
        }}))
        assert summary["status"] == "OK" and summary["scanned"] == 1
        rows = bot.OpportunityHunter._active_rows(20)
        assert any(r["symbol"] == "AAA/USDT" and r["status"] in ("WATCH", "CONFIRMED") for r in rows)
        target = next(r for r in rows if r["symbol"] == "AAA/USDT")
        bot.OpportunityHunter._update_row(target["opportunity_id"], {"expires_at": time.time() - 1})
        # A non-empty but unusable snapshot still lets the lifecycle monitor
        # expire prior ideas; no exchange or order route is called.
        asyncio.run(bot.OpportunityHunter.scan_market_map({"OTHER/USDT": {}}))
        expired = bot.OpportunityHunter._get_by_id(target["opportunity_id"])
        assert expired["status"] == "EXPIRED"
        assert bot.OpportunityHunter.execution_authority is False


def test_opportunity_hunter_terminal_record_cannot_be_resurrected(tmp_path):
    db_path = tmp_path / "hunter_terminal.sqlite3"
    with patch.dict(bot.CONFIG, {
        "DB_PATH": str(db_path), "TELEGRAM_ENABLED": False,
        "V702_OPPORTUNITY_HUNTER_TELEGRAM_ENABLE": False,
    }, clear=False):
        bot.OpportunityHunter._schema_ready_paths.discard(str(db_path))
        item = {
            "candidate_key": "hunter-terminal|AAA/USDT|PULLBACK|1", "symbol": "AAA/USDT",
            "family": "PULLBACK", "pattern": "PULLBACK_RECLAIM", "status": "WATCH",
            "candle_ts": int(time.time()), "entry_ref": 100.0, "sl_price": 99.0,
            "invalidation_price": 99.0, "last_price": 100.0, "reason": "test",
        }
        row, _ = bot.OpportunityHunter._upsert(item, notify=False)
        bot.OpportunityHunter._update_row(row["opportunity_id"], {"status": "INVALIDATED"})
        replay, created = bot.OpportunityHunter._upsert(item, notify=False)
        assert created is False
        assert replay["status"] == "INVALIDATED"


def test_opportunity_hunter_upgrades_technical_confirmation_to_canonical_prequal(tmp_path, monkeypatch):
    db_path = tmp_path / "hunter_upgrade.sqlite3"
    queued = []
    monkeypatch.setattr(bot.OpportunityHunter, "_queue_alert",
                        lambda row, state, variant="": queued.append((state, variant)) or True)
    with patch.dict(bot.CONFIG, {"DB_PATH": str(db_path), "TELEGRAM_ENABLED": False}, clear=False):
        bot.OpportunityHunter._schema_ready_paths.discard(str(db_path))
        item = {
            "candidate_key": "hunter-upgrade|AAA/USDT|BREAKOUT|1", "symbol": "AAA/USDT",
            "family": "BREAKOUT", "pattern": "BREAKOUT_CONTINUATION", "status": "CONFIRMED",
            "confirmation_type": "CLOSED_BAR_BREAKOUT", "candle_ts": int(time.time()),
            "entry_ref": 100.0, "sl_price": 99.0, "invalidation_price": 99.0,
            "last_price": 100.0, "reason": "technical trigger",
        }
        row, _ = bot.OpportunityHunter._upsert(item, notify=False)
        bot.OpportunityHunter.on_pipeline_event("PREQUAL_PASS", item["candidate_key"], "AAA/USDT", "BREAKOUT")
        updated = bot.OpportunityHunter._get_by_id(row["opportunity_id"])
        assert updated["status"] == "CONFIRMED"
        assert updated["confirmation_type"] == "CANONICAL_PREQUAL"
        assert queued == []  # Prequal alone is not a finished opportunity.
        bot.OpportunityHunter.on_pipeline_event("SCORE_PASS", item["candidate_key"], "AAA/USDT", "BREAKOUT")
        updated = bot.OpportunityHunter._get_by_id(row["opportunity_id"])
        assert updated["status"] == "CONFIRMED"
        assert updated["confirmation_type"] == "CANONICAL_SCORE_PASS"
        assert ("CONFIRMED", "CANONICAL_SCORE_PASS") in queued


@pytest.mark.asyncio
async def test_opportunity_hunter_does_not_overwrite_synchronous_telegram_ack(tmp_path, monkeypatch):
    db_path = tmp_path / "hunter_ack_race.sqlite3"
    async def _immediate_ack(message, on_success=None, on_failure=None):
        if callable(on_success):
            on_success("test_ack")
        return True
    monkeypatch.setattr(bot.TelegramDispatcher, "enqueue", _immediate_ack)
    with patch.dict(bot.CONFIG, {
        "DB_PATH": str(db_path), "TELEGRAM_ENABLED": True,
        "V702_OPPORTUNITY_HUNTER_TELEGRAM_ENABLE": True,
    }, clear=False):
        bot.OpportunityHunter._schema_ready_paths.discard(str(db_path))
        item = {
            "candidate_key": "hunter-ack|AAA/USDT|BREAKOUT|1", "symbol": "AAA/USDT",
            "family": "BREAKOUT", "pattern": "BREAKOUT_CONTINUATION", "status": "CONFIRMED",
            "confirmation_type": "CLOSED_BAR_BREAKOUT",
            "score": 90.0, "candle_ts": int(time.time()), "entry_ref": 100.0,
            "sl_price": 99.0, "invalidation_price": 99.0, "last_price": 100.0,
            "reason": "closed candle breakout", "missing_conditions": ["canonical prequal"],
            "evidence": {"strong_alert_eligible": True, "technical_score": 90.0,
                         "execution_score": 85.0, "regime_fit_score": 80.0, "net_rr_tp1_estimate": 1.1},
        }
        row, _ = bot.OpportunityHunter._upsert(item, notify=False)
        await bot.OpportunityHunter._deliver_alert(row, "CONFIRMED", "CONFIRMED")
        updated = bot.OpportunityHunter._get_by_id(row["opportunity_id"])
        assert updated["last_alert_delivery"] == "DELIVERED"
        assert "CONFIRMED" in updated["alerted_states"]


def test_opportunity_hunter_telegram_includes_reference_levels_and_no_profit_guarantee():
    row = {
        "opportunity_id": "hunter-message", "symbol": "AAA/USDT", "family": "BREAKOUT",
        "status": "WATCH", "score": 67.0, "timeframe": "5m+15m", "last_price": 100.0,
        "entry_ref": 100.0, "invalidation_price": 99.0, "tp1": 101.0, "tp2": 101.5,
        "tp3": 102.0, "reason": "closed-candle resistance compression",
        "confirmation_type": "WATCH_SETUP", "missing_conditions": ["breakout close"],
        "blockers": [], "evidence": {"relative_volume": 1.2, "strategy_style": "SWING", "outcome_interval_sec": 3600},
    }
    message = bot.OpportunityHunter._message(row, "WATCH", "WATCH")
    assert "مرجع الدخول التحليلي" in message
    assert "مستويات السيناريو" in message and "TP1" in message and "TP3" in message
    assert "ليست أوامر أو ضمانًا للربح" in message
    assert "MONITOR ONLY" in message
    assert "TradingView" in message and "https://www.tradingview.com/chart/?symbol=MEXC%3AAAAUSDT" in message
    assert "SWING" in message and "1h candles" in message


def test_opportunity_hunter_suppresses_watch_alerts_by_default(tmp_path):
    db_path = tmp_path / "hunter_watch_suppression.sqlite3"
    with patch.dict(bot.CONFIG, {
        "DB_PATH": str(db_path), "TELEGRAM_ENABLED": True,
        "V702_OPPORTUNITY_HUNTER_TELEGRAM_ENABLE": True,
    }, clear=False):
        bot.OpportunityHunter._schema_ready_paths.discard(str(db_path))
        row, _ = bot.OpportunityHunter._upsert({
            "candidate_key": "watch-only|AAA/USDT|1", "symbol": "AAA/USDT",
            "family": "PULLBACK", "pattern": "PULLBACK_RECLAIM", "status": "WATCH",
            "confirmation_type": "WATCH_SETUP", "entry_ref": 100.0, "sl_price": 99.0,
            "tp1": 101.0, "tp2": 102.0, "tp3": 103.0,
        }, notify=False)
        assert bot.OpportunityHunter._queue_alert(row, "WATCH") is False
        assert bot.OpportunityHunter._alert_allowed(row, "CONFIRMED") is False


def test_swing_shadow_outcome_uses_closed_hourly_candles():
    now = time.time()
    raw = _outcome_test_frame(now, period=3600, bars={
        -4: {"high": 101.2, "close": 100.8},
        -3: {"high": 102.2, "close": 101.8},
        -2: {"high": 103.2, "close": 102.8},
    })
    closed, _ = bot.OpportunityHunter._closed_frame(raw, 3600, now=now)
    assert closed is not None
    first_target_open = int(pd.Timestamp(closed.index[-3]).timestamp())
    row = _outcome_test_row(first_target_open - 1, expires_at=now + 7200)
    row.update({"timeframe": "1D_4H_15M_5M",
                "evidence": {"strategy_style": "SWING", "outcome_interval_sec": 3600}})
    updates, events = bot.OpportunityHunter._advance_shadow_outcome(row, closed, now=now)
    assert [event["kind"] for event in events] == [
        "SHADOW_TP1_TOUCHED", "SHADOW_TP2_TOUCHED", "SHADOW_TP3_TOUCHED"]
    assert all(event["candle_close_ts"] - event["candle_open_ts"] == 3600 for event in events)
    assert "1h" in updates["outcome_reason"]


def test_boot_selftest_synthetic_events_do_not_emit_live_error_or_warning_logs(caplog, monkeypatch):
    import logging

    caplog.set_level(logging.DEBUG, logger="unified_scalper")
    old_context = bot._v702_selftest_log_context_active()
    # A synthetic self-test context must not leak into concurrent worker threads.
    context_token = bot.V702_SELFTEST_LOG_CONTEXT.set(True)
    worker_context = []
    worker = bot.threading.Thread(
        target=lambda: worker_context.append(bot._v702_selftest_log_context_active()),
        name="selftest-context-isolation-regression",
    )
    worker.start()
    worker.join(timeout=2.0)
    bot.V702_SELFTEST_LOG_CONTEXT.reset(context_token)
    assert not worker.is_alive()
    assert worker_context == [False]
    old_live_state = bot.LIVE_STATE.current

    def _no_running_loop():
        raise RuntimeError("no running event loop")

    monkeypatch.setattr(bot.asyncio, "get_running_loop", _no_running_loop)
    try:
        streak = bot._v702_r4_loss_streak_self_test()
        assert streak.get("pass") is True

        telegram = bot._v523_opportunity_telegram_self_test()
        assert telegram.get("pass") is True

        bot._v455_record_prequal_reason(
            "SELFTEST/USDT", "exception.selftest:ValueError", stage="selftest",
            exception_type="ValueError",
        )
    finally:
        assert bot._v702_selftest_log_context_active() == old_context
        assert bot.LIVE_STATE.current == old_live_state

    synthetic_markers = (
        "[DailyCB-R5]", "[TG-LIFECYCLE-UNSCHEDULED]", "[V455-PREQUAL-EXCEPTION]",
    )
    synthetic_records = [
        record for record in caplog.records
        if any(marker in record.getMessage() for marker in synthetic_markers)
    ]
    assert synthetic_records
    assert all(record.levelno < logging.WARNING for record in synthetic_records)
    assert bot._v702_selftest_log_context_active() is old_context

def test_dotenv_backed_runtime_config_is_applied_after_config_construction(monkeypatch):
    keys = (
        "DB_PATH", "TELEGRAM_OPPORTUNITY_PUBLIC_URL",
        "TELEGRAM_PUBLIC_CHAT_USERNAME", "TELEGRAM_BOT_USERNAME",
        "TELEGRAM_PUBLIC_URL", "TELEGRAM_CHANNEL_USERNAME",
    )
    previous = {key: bot.CONFIG.get(key) for key in keys}
    try:
        monkeypatch.setenv("SCALPER_DB", "/tmp/unified-scalper-dotenv.sqlite3")
        monkeypatch.setenv("TELEGRAM_OPPORTUNITY_PUBLIC_URL", "https://t.me/opportunity-feed")
        monkeypatch.setenv("TELEGRAM_PUBLIC_CHAT_USERNAME", "@public_feed")
        monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "@scalper_bot")
        monkeypatch.setenv("TELEGRAM_CHANNEL_URL", "https://t.me/channel_feed")
        monkeypatch.setenv("TELEGRAM_USERNAME", "@channel_feed")

        bot._apply_loaded_environment_config()

        assert bot.CONFIG["DB_PATH"] == "/tmp/unified-scalper-dotenv.sqlite3"
        assert bot.CONFIG["TELEGRAM_OPPORTUNITY_PUBLIC_URL"] == "https://t.me/opportunity-feed"
        assert bot.CONFIG["TELEGRAM_PUBLIC_CHAT_USERNAME"] == "public_feed"
        assert bot.CONFIG["TELEGRAM_BOT_USERNAME"] == "scalper_bot"
        assert bot.CONFIG["TELEGRAM_PUBLIC_URL"] == "https://t.me/channel_feed"
        assert bot.CONFIG["TELEGRAM_CHANNEL_USERNAME"] == "channel_feed"
    finally:
        bot.CONFIG.update(previous)

def test_exchange_client_missing_credentials_fails_fast_with_actionable_boot_marker(caplog):
    import logging

    caplog.set_level(logging.CRITICAL, logger="unified_scalper")
    with patch.dict(bot.ENV, {"MEXC_API_KEY": None, "MEXC_API_SECRET": None}, clear=False):
        with patch.object(bot, "_CCXT_OK", True):
            with pytest.raises(SystemExit) as exc:
                bot.ExchangeFactory.create_mexc_async()
    assert exc.value.code == "missing_exchange_secrets"
    assert any("[V702-BOOT-STOP]" in record.getMessage() for record in caplog.records)
    assert all("MEXC_API_KEY=" not in record.getMessage() for record in caplog.records)



# A71 corrective integration regression tests.
def _a71_candidate(symbol="A71/USDT", mode="PULLBACK", side="long", score=0.80):
    return bot.StrategyCandidate(
        "a71-test", symbol, side, int(time.time() * 1000),
        100.0, 99.0, 1.0, 2.0, 3.0, score, 2.0, 0.8, 0.8,
        "PULLBACK", 100.0, {}, (), mode, "SCALP", "TREND",
        "BULLISH", "LOCAL_BULLISH", "NORMAL", "5m", "B",
    )


def test_a71_fallback_ranked_candidate_preserves_canonical_absolute_targets():
    candidate = _a71_candidate()
    ranked = bot._v702_fallback_ranked_candidate(candidate)
    assert isinstance(ranked, bot.RankedCandidate)
    assert ranked.candidate is candidate
    assert ranked.composite == candidate.engine_score
    assert (ranked.tp1_abs, ranked.tp2_abs, ranked.tp3_abs) == (101.0, 102.0, 103.0)


def test_a71_diversity_bonus_replaces_frozen_ranked_candidate_without_mutation():
    first = bot.RankedCandidate(_a71_candidate(mode="PULLBACK"), 0.800, 101.0, 102.0, 103.0)
    second = bot.RankedCandidate(_a71_candidate(symbol="B71/USDT", mode="BREAKOUT"), 0.799, 101.0, 102.0, 103.0)
    adjusted = bot._v702_apply_mse_diversity_bonus([first, second], 0.005)
    assert first.composite == 0.800 and second.composite == 0.799
    assert adjusted[0].composite == 0.804
    assert adjusted[0] is not second
    assert adjusted[0].candidate is second.candidate


def test_a71_long_only_contract_is_behavioral_and_rejects_short_candidate():
    candidate = _a71_candidate(side="short")
    assert bot.CompositeRankingEngine._validate_fail_closed(candidate) == "side_not_long"


def test_a71_universe_fallback_uses_only_bounded_explicit_cache():
    empty = SimpleNamespace(_liq_universe=[])
    assert bot._v699_cached_universe_fallback(empty, 4) == []
    assert bot.STATS["v699_universe_last_fallback_state"] == "EMPTY"
    cached = SimpleNamespace(_liq_universe=["A/USDT", "B/USDT", "C/USDT"])
    assert bot._v699_cached_universe_fallback(cached, 2) == ["A/USDT", "B/USDT"]
    assert bot.STATS["v699_universe_last_fallback_state"] == "CACHED_FALLBACK"


def test_a71_observability_self_test_fails_closed_when_summary_raises(monkeypatch):
    def raise_offline():
        raise RuntimeError("offline_injected_summary_error")
    monkeypatch.setattr(bot, "_v699_daily_summary_text", raise_offline)
    report = bot._v699_observability_closure_test()
    assert report["pass"] is False
    assert "exception" in report["failed"]
    assert "offline_injected_summary_error" in report["error"]
    assert all(isinstance(value, bool) for value in report["checks"].values())


def test_a71_runtime_source_extractor_returns_only_function_span():
    source = bot._v702_runtime_function_source(bot._v699_observability_closure_test)
    assert "def _v699_observability_closure_test" in source
    assert "checks={}" in source
    assert len(source) < 20_000


def test_a71_telegram_outbox_retention_never_deletes_nonterminal_work(tmp_path, monkeypatch):
    import sqlite3
    db_path = tmp_path / "outbox.sqlite3"
    monkeypatch.setitem(bot.CONFIG, "DB_PATH", str(db_path))
    conn = sqlite3.connect(str(db_path))
    conn.execute("""CREATE TABLE telegram_outbox (
        outbox_id TEXT PRIMARY KEY, message_key TEXT NOT NULL, message TEXT NOT NULL,
        status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_error TEXT
    )""")
    old = "2020-01-01T00:00:00+00:00"
    fresh = datetime_now = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    rows = [
        ("old-delivered", "k1", "x", "DELIVERED", 1, old, old, None),
        ("old-dead", "k2", "x", "DEAD_LETTER", 3, old, old, None),
        ("fresh-delivered", "k3", "x", "DELIVERED", 1, fresh, fresh, None),
        ("queued", "k4", "x", "QUEUED", 0, old, old, None),
        ("sending", "k5", "x", "SENDING", 1, old, old, None),
        ("retry", "k6", "x", "RETRY_PENDING", 2, old, old, None),
    ]
    conn.executemany("INSERT INTO telegram_outbox VALUES(?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    report = bot.DBManager.prune_telegram_outbox(retention_days=30, max_terminal_rows=100)
    assert report["deleted_by_age"] == 2
    assert report["pending_preserved"] == 3
    conn = sqlite3.connect(str(db_path))
    statuses = dict(conn.execute("SELECT outbox_id,status FROM telegram_outbox").fetchall())
    conn.close()
    assert statuses == {"fresh-delivered": "DELIVERED", "queued": "QUEUED",
                        "sending": "SENDING", "retry": "RETRY_PENDING"}


def test_a71_counterfactual_retention_preserves_pending_rows_over_cap(tmp_path):
    from v702_counterfactual_shadow import V702CounterfactualShadow
    study = V702CounterfactualShadow(str(tmp_path / "cf.sqlite3"), str(tmp_path / "reports"))
    with study._db() as conn:
        for index, status in enumerate(("PENDING", "PENDING", "TP1", "SL")):
            conn.execute("""INSERT INTO v702_cf_shadow_samples
                (sample_id,sample_key,created_ts,anchor_bar_ts_ms,symbol,family,strategy_mode,lane,reject_reason,
                 last_candle_ts_ms,bars_seen,status,note,context_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f"cf-{index}", f"key-{index}", float(index), 1, "A71/USDT", "PULLBACK", "PULLBACK",
                 "BASELINE_PASS", "test", 1, 0, status, "", "{}"))
        retention = study._prune_sample_rows(conn, 2)
    with study._db() as conn:
        statuses = dict(conn.execute("SELECT sample_id,status FROM v702_cf_shadow_samples").fetchall())
    assert statuses == {"cf-0": "PENDING", "cf-1": "PENDING"}
    assert retention["pending"] == 2
    assert retention["deleted_terminal"] == 2
    assert retention["over_cap"] == 0


def test_a71_intraday_retention_preserves_pending_rows_over_cap(tmp_path):
    from v702_intraday_shadow import V702IntradayShadow
    study = V702IntradayShadow(str(tmp_path / "intraday.sqlite3"), str(tmp_path / "reports"))
    with study._db() as conn:
        for index, status in enumerate(("PENDING", "PENDING", "TP1", "SL")):
            conn.execute("""INSERT INTO v702_intraday_shadow_samples
                (sample_id,symbol,strategy_mode,timeframe,signal_ts_ms,created_ts,entry,stop,target,risk_unit,
                 risk_pct,last_candle_ts_ms,bars_seen,status,cost_pct,quote_volume_24h,tier,features_json,note)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f"intra-{index}", f"A71-{index}/USDT", "PULLBACK", "1m", 1, float(index),
                 100.0, 99.0, 101.0, 1.0, 1.0, 1, 0, status, 0.3, 2_000_000.0, "MICRO", "{}", "test"))
        retention = study._prune_sample_rows(conn, 2)
    with study._db() as conn:
        statuses = dict(conn.execute("SELECT sample_id,status FROM v702_intraday_shadow_samples").fetchall())
    assert statuses == {"intra-0": "PENDING", "intra-1": "PENDING"}
    assert retention["pending"] == 2
    assert retention["deleted_terminal"] == 2


def test_swing_strategy_observation_deduplicates_by_closed_daily_anchor_and_tracks_one_hour(tmp_path):
    now = time.time()
    db_path = tmp_path / "hunter_swing_dedup.sqlite3"
    snapshot = {
        "df_5m": _outcome_test_frame(now, period=300),
        "df_1h": _outcome_test_frame(now, period=3600),
        "df_1d": _outcome_test_frame(now, period=86400),
    }
    common = {
        "engine_id": "mtf_pullback", "symbol": "AAA/USDT", "side": "long",
        "entry_ref": 100.0, "sl_price": 98.0, "tp1_rr": 1.0, "tp2_rr": 1.5,
        "tp3_rr": 2.0, "engine_score": 0.82, "rr_ratio": 1.0,
        "liquidity_score": 0.8, "regime_fit": 0.8, "family": "MTF_PULLBACK",
        "zone_ref": 100.0, "features_snapshot": {}, "strategy_mode": "MTF_PULLBACK",
        "strategy_style": "SWING", "timeframe_profile": "1D_4H_15M_5M",
        "quality_grade": "A",
    }
    with patch.dict(bot.CONFIG, {
        "DB_PATH": str(db_path), "TELEGRAM_ENABLED": False,
        "V702_OPPORTUNITY_HUNTER_SWING_TTL_SEC": 604800.0,
    }, clear=False):
        bot.OpportunityHunter._schema_ready_paths.discard(str(db_path))
        first = bot.OpportunityHunter.observe_strategy_candidate(
            bot.StrategyCandidate(generated_at_ms=int(now * 1000), **common), snapshot)
        second = bot.OpportunityHunter.observe_strategy_candidate(
            bot.StrategyCandidate(generated_at_ms=int((now + 17) * 1000), **common), snapshot)
        active = [row for row in bot.OpportunityHunter._active_rows(50)
                  if row.get("symbol") == "AAA/USDT" and row.get("family") == "MTF_PULLBACK"]
    assert first and second
    assert first["opportunity_id"] == second["opportunity_id"]
    assert len(active) == 1
    assert active[0]["evidence"]["strategy_style"] == "SWING"
    assert active[0]["evidence"]["outcome_interval_sec"] == 3600
    assert 604799 <= active[0]["expires_at"] - active[0]["created_at"] <= 604801


def test_opportunity_scan_persists_watch_but_only_queues_formed_signal(tmp_path, monkeypatch):
    db_path = tmp_path / "hunter_scan_alert_policy.sqlite3"
    queued = []
    watch = {
        "candidate_key": "scan-watch|AAA/USDT|1", "symbol": "AAA/USDT",
        "family": "PULLBACK", "pattern": "PULLBACK_RECLAIM", "status": "WATCH",
        "confirmation_type": "WATCH_SETUP", "entry_ref": 100.0, "sl_price": 99.0,
        "tp1": 101.0, "tp2": 102.0, "tp3": 103.0,
    }
    formed = {
        "candidate_key": "scan-formed|AAA/USDT|2", "symbol": "AAA/USDT",
        "family": "BREAKOUT", "pattern": "BREAKOUT_CONTINUATION", "status": "CONFIRMED",
        "confirmation_type": "CLOSED_BAR_BREAKOUT", "entry_ref": 100.0, "sl_price": 99.0,
        "tp1": 101.0, "tp2": 102.0, "tp3": 103.0,
    }

    def fake_evaluate(cls, symbol, md, now=None):
        return [watch, formed]

    def fake_queue(cls, row, state, variant=""):
        queued.append((row.get("candidate_key"), state))
        return True

    monkeypatch.setattr(bot.OpportunityHunter, "_evaluate_snapshot", classmethod(fake_evaluate))
    monkeypatch.setattr(bot.OpportunityHunter, "_queue_alert", classmethod(fake_queue))
    with patch.dict(bot.CONFIG, {
        "DB_PATH": str(db_path), "TELEGRAM_ENABLED": True,
        "V702_OPPORTUNITY_HUNTER_TELEGRAM_ENABLE": True,
    }, clear=False):
        bot.OpportunityHunter._schema_ready_paths.discard(str(db_path))
        summary = asyncio.run(bot.OpportunityHunter.scan_market_map({"AAA/USDT": {}}))
        active = bot.OpportunityHunter._active_rows(20)
    assert summary["created"] == 2
    assert {row["status"] for row in active} == {"WATCH", "CONFIRMED"}
    assert queued == [("scan-formed|AAA/USDT|2", "CONFIRMED")]



def _a74_trending_frame(now, period, *, count=130, breakout=True, volume_last=250.0):
    current_open = int(float(now) // period) * period
    stamps = [current_open - (count - i) * period for i in range(count)] + [current_open]
    values = []
    for i, _stamp in enumerate(stamps):
        close = 100.0 + i * 0.20
        values.append({"open": close - 0.04, "high": close + 0.03,
                       "low": close - 0.60, "close": close, "volume": 100.0})
    # The last closed bar has a real breakout and confirming relative volume.
    if breakout:
        # Cross the prior 20-bar resistance with enough ATR headroom to avoid
        # testing the setup after an already-extended impulse.
        trigger_close = float(values[-3]["close"]) + 0.10
        values[-2].update({"open": trigger_close - 0.06,
                           "high": trigger_close + 0.04,
                           "low": trigger_close - 0.60,
                           "close": trigger_close,
                           "volume": float(volume_last)})
    return pd.DataFrame(values, index=pd.to_datetime(stamps, unit="s", utc=True))


def test_a74_hunter_excludes_stablecoins_from_all_discovery_paths():
    assert bot.OpportunityHunter._evaluate_snapshot("USDC/USDT", {}) == []
    assert bot.OpportunityHunter._evaluate_snapshot("DAI/USDT", {}) == []
    assert bot.OpportunityHunter.observe_strategy_candidate(
        SimpleNamespace(symbol="USDC/USDT", side="long"), {}) is None
    assert bot.OpportunityHunter._evaluate_snapshot("BTC/USDT", {}) == []  # no data, but not blocked as stable


def test_a74_swing_hunter_generates_independent_1h_4h_closed_bar_setup():
    now = time.time()
    md = {
        "df_1h": _a74_trending_frame(now, 3600, breakout=True),
        "df_4h": _a74_trending_frame(now, 14400, breakout=True),
        "quote_vol_24h": 35_000_000.0,
        "spread_pct": 0.02,
    }
    rows = bot.OpportunityHunter._evaluate_snapshot("AAA/USDT", md, now=now)
    swing = [r for r in rows if str(r.get("pattern", "")).startswith("SWING_")]
    assert swing
    assert any(r["timeframe"] == "1H+4H" and r["evidence"]["strategy_style"] == "SWING"
               and r["evidence"]["outcome_interval_sec"] == 3600 for r in swing)
    assert all(float(r["tp1"]) > float(r["entry_ref"]) > float(r["sl_price"]) for r in swing)


def test_a74_pullback_and_breakout_quality_gates_reject_weak_volume_and_chasing():
    cls = bot.OpportunityHunter
    base = {"source": "READ_ONLY_MARKET_PATTERN", "status": "CONFIRMED", "entry_ref": 100.0,
            "sl_price": 99.0, "tp1": 102.0, "score": 95.0, "missing_conditions": [],
            "evidence": {"volume_ratio_5m": 0.45, "spread_pct": 0.02, "quote_vol_24h": 20_000_000,
                         "trend_1h": True, "trend_4h": True}}
    md = {"spread_pct": 0.02, "quote_vol_24h": 20_000_000}
    pull = {**base, "pattern": "PULLBACK_RECLAIM", "confirmation_type": "CLOSED_BAR_PULLBACK_RECLAIM"}
    q = _v = cls._evaluate_snapshot  # keep class resolution explicit for the regression below
    evaluated_pull = bot._A74_BASE_EVALUATE_SNAPSHOT if hasattr(bot, "_A74_BASE_EVALUATE_SNAPSHOT") else None
    # The pure quality evaluator is exported in the runtime namespace for auditability.
    quality = bot._v702_a74_market_quality(cls, pull, md, h1=None, h4=None)
    assert quality["status"] == "WATCH"
    assert quality["evidence"]["strong_alert_eligible"] is False

    breakout = {**base, "pattern": "BREAKOUT_CONTINUATION", "confirmation_type": "CLOSED_BAR_BREAKOUT",
                "evidence": {**base["evidence"], "volume_ratio_5m": 2.0, "distance_to_resistance_atr": -1.40}}
    quality2 = bot._v702_a74_market_quality(cls, breakout, md, h1=None, h4=None)
    assert quality2["status"] == "WATCH"
    assert "WAIT_FOR_RESISTANCE_RETEST_NO_CHASE" in quality2["missing_conditions"]


def test_a74_shadow_outcome_reports_estimated_net_result_after_costs():
    now = time.time()
    raw = _outcome_test_frame(now, bars={
        -4: {"high": 101.2, "close": 100.8},
        -3: {"high": 102.2, "close": 101.8},
        -2: {"high": 103.2, "close": 102.8},
    })
    closed, _ = bot.OpportunityHunter._closed_frame(raw, 300, now=now)
    first_open = int(pd.Timestamp(closed.index[-3]).timestamp())
    row = _outcome_test_row(first_open - 1, expires_at=now + 600)
    row["evidence"] = {"spread_pct": 0.02}
    updates, events = bot.OpportunityHunter._advance_shadow_outcome(row, closed, now=now)
    assert [e["kind"] for e in events] == ["SHADOW_TP1_TOUCHED", "SHADOW_TP2_TOUCHED", "SHADOW_TP3_TOUCHED"]
    assert updates["outcome_net_return_pct"] > 0
    assert updates["outcome_net_r"] > 0
    assert updates["outcome_realized_fraction"] == pytest.approx(1.0)
    assert updates["outcome_cost_pct"] > 0


def test_a74_stop_shadow_outcome_reports_net_loss_after_costs():
    now = time.time()
    raw = _outcome_test_frame(now, bars={-2: {"low": 98.5, "close": 99.0}})
    closed, _ = bot.OpportunityHunter._closed_frame(raw, 300, now=now)
    stop_open = int(pd.Timestamp(closed.index[-2]).timestamp())
    row = _outcome_test_row(stop_open - 1, expires_at=now + 600)
    row["evidence"] = {"spread_pct": 0.02}
    updates, events = bot.OpportunityHunter._advance_shadow_outcome(row, closed, now=now)
    assert events and events[0]["kind"] == "SHADOW_STOP_HIT"
    assert updates["outcome_net_return_pct"] < 0
    assert updates["outcome_net_r"] < 0


def test_a74_schema_persists_new_net_outcome_fields(tmp_path):
    db = tmp_path / "a74_schema.sqlite3"
    with patch.dict(bot.CONFIG, {"DB_PATH": str(db), "TELEGRAM_ENABLED": False}, clear=False):
        bot.OpportunityHunter._schema_ready_paths.discard(str(db))
        bot.OpportunityHunter._ensure_schema()
        conn = bot.sqlite3.connect(db)
        try:
            columns = {r[1] for r in conn.execute("PRAGMA table_info(opportunity_hunter)")}
        finally:
            conn.close()
    assert {"outcome_net_return_pct", "outcome_net_r", "outcome_realized_fraction", "outcome_cost_pct"}.issubset(columns)


def test_a74_data_gap_expiry_is_unknown_not_reported_as_loss_or_no_target(tmp_path, monkeypatch):
    db = tmp_path / "a74_gap.sqlite3"
    monkeypatch.setattr(bot.OpportunityHunter, "_evaluate_snapshot", classmethod(lambda cls, *a, **k: []))
    monkeypatch.setattr(bot.OpportunityHunter, "_queue_alert", classmethod(lambda cls, *a, **k: False))
    with patch.dict(bot.CONFIG, {"DB_PATH": str(db), "TELEGRAM_ENABLED": False,
                                 "V702_OPPORTUNITY_HUNTER_ENABLE": True}, clear=False):
        bot.OpportunityHunter._schema_ready_paths.discard(str(db))
        row, _ = bot.OpportunityHunter._upsert({
            "candidate_key": "gap|AAA/USDT|1", "symbol": "AAA/USDT", "family": "PULLBACK",
            "pattern": "PULLBACK_RECLAIM", "status": "WATCH", "entry_ref": 100.0,
            "sl_price": 99.0, "tp1": 102.0, "tp2": 103.0, "tp3": 104.0,
            "expires_at": time.time() - 2,
        }, notify=False)
        asyncio.run(bot.OpportunityHunter.scan_market_map({"AAA/USDT": {}}))
        saved = bot.OpportunityHunter._get_by_id(row["opportunity_id"])
    assert saved["outcome_status"] == "SHADOW_DATA_GAP_EXPIRED"
    assert saved["outcome_net_return_pct"] is None


def test_a74_symbol_alert_cooldown_survives_process_restart(tmp_path, monkeypatch):
    db = tmp_path / "a74_symbol_cooldown.sqlite3"
    cls = bot.OpportunityHunter
    with patch.dict(bot.CONFIG, {"DB_PATH": str(db), "TELEGRAM_ENABLED": False,
                                 "V702_OPPORTUNITY_HUNTER_SYMBOL_ALERT_COOLDOWN_SEC": 900.0}, clear=False):
        cls._schema_ready_paths.discard(str(db))
        cls._a74_symbol_alert_last = {}  # simulate process restart: volatile memory is empty
        row, _ = cls._upsert({
            "candidate_key": "cooldown|AAA/USDT|one", "symbol": "AAA/USDT",
            "family": "BREAKOUT", "pattern": "BREAKOUT_CONTINUATION", "status": "CONFIRMED",
            "confirmation_type": "CLOSED_BAR_BREAKOUT", "entry_ref": 100.0, "sl_price": 99.0,
            "tp1": 102.0, "tp2": 103.0, "tp3": 104.0, "score": 95.0,
            "evidence": {"strong_alert_eligible": True},
        }, notify=False)
        cls._update_row(row["opportunity_id"], {"symbol_last_alert_at": time.time() - 30.0})
        queued_calls = []
        monkeypatch.setattr(bot, "_A74_BASE_QUEUE_ALERT",
                            lambda cls_, row_, state_, variant="": queued_calls.append(state_) or True)
        blocked = cls._queue_alert(cls._get_by_id(row["opportunity_id"]), "CONFIRMED")
    assert blocked is False
    assert queued_calls == []


def test_a74_telegram_ack_persists_symbol_cooldown_timestamp(tmp_path, monkeypatch):
    db = tmp_path / "a74_symbol_ack.sqlite3"
    cls = bot.OpportunityHunter
    async def fake_enqueue(message, on_success=None, on_failure=None):
        assert message
        if callable(on_success):
            on_success("test_ack")
        return True
    with patch.dict(bot.CONFIG, {"DB_PATH": str(db), "TELEGRAM_ENABLED": False}, clear=False):
        cls._schema_ready_paths.discard(str(db))
        row, _ = cls._upsert({
            "candidate_key": "ack|AAA/USDT|one", "symbol": "AAA/USDT",
            "family": "BREAKOUT", "pattern": "BREAKOUT_CONTINUATION", "status": "CONFIRMED",
            "confirmation_type": "CLOSED_BAR_BREAKOUT", "entry_ref": 100.0, "sl_price": 99.0,
            "tp1": 102.0, "tp2": 103.0, "tp3": 104.0, "score": 95.0,
            "evidence": {"strong_alert_eligible": True},
        }, notify=False)
        monkeypatch.setattr(bot.TelegramDispatcher, "enqueue", staticmethod(fake_enqueue))
        monkeypatch.setattr(cls, "_message", classmethod(lambda cls_, *args, **kwargs: "shadow alert"))
        asyncio.run(cls._deliver_alert(cls._get_by_id(row["opportunity_id"]), "CONFIRMED", "TEST_ACK"))
        saved = cls._get_by_id(row["opportunity_id"])
    assert saved["last_alert_delivery"] == "DELIVERED"
    assert saved["symbol_last_alert_at"] > 0
    assert "TEST_ACK" in saved["alerted_states"]
    assert "TEST_ACK" not in saved["pending_alert_states"]


def test_a74_strong_quality_requires_and_accepts_full_technical_execution_regime_edge():
    cls = bot.OpportunityHunter
    now = time.time()
    h1 = _a74_trending_frame(now, 3600, breakout=False)
    h4 = _a74_trending_frame(now, 14400, breakout=False)
    item = {
        "source": "READ_ONLY_MARKET_PATTERN", "status": "CONFIRMED",
        "confirmation_type": "CLOSED_BAR_BREAKOUT", "pattern": "BREAKOUT_CONTINUATION",
        "entry_ref": 100.0, "sl_price": 99.0, "tp1": 103.0, "score": 96.0,
        "missing_conditions": [],
        "evidence": {"volume_ratio_5m": 2.2, "distance_to_resistance_atr": 0.30,
                     "spread_pct": 0.02, "quote_vol_24h": 30_000_000.0},
    }
    quality = bot._v702_a74_market_quality(
        cls, item, {"spread_pct": 0.02, "quote_vol_24h": 30_000_000.0}, h1=h1, h4=h4
    )
    assert quality["status"] == "CONFIRMED"
    assert quality["evidence"]["strong_alert_eligible"] is True
    assert quality["evidence"]["technical_score"] >= 82
    assert quality["evidence"]["execution_score"] >= 65
    assert quality["evidence"]["regime_fit_score"] >= 50
    assert quality["evidence"]["net_rr_tp1_estimate"] >= 0.8


def test_a74_stablecoin_block_does_not_depend_on_optional_filter_toggle():
    with patch.dict(bot.CONFIG, {"V531_STABLECOIN_FILTER_ENABLE": False}, clear=False):
        assert bot._v531_is_stablecoin("USDC/USDT") is True
        assert bot._v531_is_stablecoin("FDUSD/USDT") is True
        assert bot._v531_is_stablecoin("TUSD/USDT") is True
        assert bot._v531_is_stablecoin("USDG/USDT") is True
        assert bot._v531_is_stablecoin("EURT/USDT") is True
        assert bot._v702_a74_is_stable_symbol("USDC/USDT") is True
        assert bot._v702_a74_is_stable_symbol("XAUT/USDT") is False


def test_a74_swing_relative_strength_nonqualification_does_not_duplicate_previous_pattern():
    now = time.time()
    symbol_1h = _a74_trending_frame(now, 3600, breakout=True)
    btc_1h = _a74_trending_frame(now, 3600, breakout=True)
    # Similar absolute performance means no qualifying BTC-relative advantage.
    md = {
        "df_1h": symbol_1h,
        "df_4h": _a74_trending_frame(now, 14400, breakout=True),
        "df_btc_1h": btc_1h,
        "quote_vol_24h": 35_000_000.0,
        "spread_pct": 0.02,
    }
    rows = bot._v702_a74_swing_items(bot.OpportunityHunter, "AAA/USDT", md, now=now)
    patterns = [str(row.get("pattern")) for row in rows]
    assert patterns
    assert "SWING_RELATIVE_STRENGTH" not in patterns
    assert patterns.count("SWING_BREAKOUT_CONTINUATION") == 1


def test_a74_unknown_strategy_family_requires_measured_volume_evidence():
    cls = bot.OpportunityHunter
    h1 = _a74_trending_frame(time.time(), 3600, breakout=False)
    h4 = _a74_trending_frame(time.time(), 14400, breakout=False)
    item = {
        "source": "STRATEGY_ENGINE", "status": "CONFIRMED",
        "confirmation_type": "CANONICAL_SCORE_PASS", "pattern": "ENGINE_UNCLASSIFIED",
        "entry_ref": 100.0, "sl_price": 99.0, "tp1": 102.0, "score": 98.0,
        "missing_conditions": [], "evidence": {},
    }
    quality = bot._v702_a74_market_quality(
        cls, item, {"spread_pct": 0.02, "quote_vol_24h": 30_000_000.0}, h1=h1, h4=h4
    )
    assert quality["status"] == "WATCH"
    assert quality["evidence"]["strong_alert_eligible"] is False
    assert "GENERIC_VOLUME_CONFIRMATION" in quality["missing_conditions"]


# A75 regression closures: these turn independently reproduced audit cases
# into permanent no-regression checks. They do not grant live execution authority.

def test_a75_hunter_rsi_handles_monotone_and_flat_series():
    base = pd.DataFrame({
        "open": [100.0] * 80, "high": [101.0] * 80, "low": [99.0] * 80,
        "close": [100.0 + i for i in range(80)], "volume": [100.0] * 80,
    })
    rising = bot.OpportunityHunter._indicators(base)["rsi14"]
    falling_frame = base.copy()
    falling_frame["close"] = [200.0 - i for i in range(80)]
    falling = bot.OpportunityHunter._indicators(falling_frame)["rsi14"]
    flat_frame = base.copy()
    flat_frame["close"] = [100.0] * 80
    flat = bot.OpportunityHunter._indicators(flat_frame)["rsi14"]
    assert rising == pytest.approx(100.0)
    assert falling == pytest.approx(0.0)
    assert flat == pytest.approx(50.0)


def test_a75_cost_inputs_keep_zero_and_reject_negative_or_nonfinite():
    with patch.dict(bot.CONFIG, {
        "V702_OPPORTUNITY_HUNTER_PAPER_FEE_PCT": 0.0,
        "V702_OPPORTUNITY_HUNTER_PAPER_SLIPPAGE_PER_SIDE_PCT": 0.0,
    }, clear=False):
        assert bot._v702_a75_cost_input("V702_OPPORTUNITY_HUNTER_PAPER_FEE_PCT", 0.10) == 0.0
        assert bot._v702_a75_cost_input("V702_OPPORTUNITY_HUNTER_PAPER_SLIPPAGE_PER_SIDE_PCT", 0.05) == 0.0
    with patch.dict(bot.CONFIG, {"V702_OPPORTUNITY_HUNTER_PAPER_FEE_PCT": -0.01}, clear=False):
        assert bot._v702_a75_cost_input("V702_OPPORTUNITY_HUNTER_PAPER_FEE_PCT", 0.10) is None
    with patch.dict(bot.CONFIG, {"V702_OPPORTUNITY_HUNTER_PAPER_FEE_PCT": float("nan")}, clear=False):
        assert bot._v702_a75_cost_input("V702_OPPORTUNITY_HUNTER_PAPER_FEE_PCT", 0.10) is None


def test_a75_completed_opportunity_is_terminal_and_setup_geometry_is_frozen(tmp_path):
    db_path = tmp_path / "a75_terminal_geometry.sqlite3"
    cls = bot.OpportunityHunter
    payload = {
        "candidate_key": "a75-terminal|AAA/USDT|BREAKOUT|1", "symbol": "AAA/USDT",
        "family": "BREAKOUT", "pattern": "BREAKOUT_CONTINUATION", "status": "WATCH",
        "timeframe": "1H+4H", "entry_ref": 100.0, "sl_price": 98.0,
        "invalidation_price": 97.5, "tp1": 103.0, "tp2": 105.0, "tp3": 108.0,
        "evidence": {"strategy_style": "SWING", "spread_pct": 0.02},
    }
    with patch.dict(bot.CONFIG, {"DB_PATH": str(db_path), "TELEGRAM_ENABLED": False}, clear=False):
        cls._schema_ready_paths.discard(str(db_path))
        first, created = cls._upsert(payload, notify=False)
        assert created is True
        cls._update_row(first["opportunity_id"], {"status": "COMPLETED"})
        second, recreated = cls._upsert({
            **payload, "status": "CONFIRMED", "entry_ref": 110.0, "sl_price": 109.0,
            "invalidation_price": 108.5, "tp1": 115.0, "tp2": 120.0, "tp3": 125.0,
        }, notify=False)
    assert recreated is False
    assert second["status"] == "COMPLETED"
    assert second["entry_ref"] == pytest.approx(100.0)
    assert second["sl_price"] == pytest.approx(98.0)
    assert second["invalidation_price"] == pytest.approx(97.5)
    assert second["tp1"] == pytest.approx(103.0)
    assert second["tp2"] == pytest.approx(105.0)
    assert second["tp3"] == pytest.approx(108.0)
    assert second["evidence"]["setup_snapshot"]["entry_ref"] == pytest.approx(100.0)


def test_a75_shadow_outcome_ignores_target_touch_after_expiry():
    now = time.time()
    raw = _outcome_test_frame(now, bars={-2: {"high": 104.0, "close": 103.5}})
    closed, _ = bot.OpportunityHunter._closed_frame(raw, 300, now=now)
    assert closed is not None
    last_target_open = int(pd.Timestamp(closed.index[-2]).timestamp())
    row = _outcome_test_row(last_target_open - 1200, expires_at=last_target_open + 299)
    updates, events = bot.OpportunityHunter._advance_shadow_outcome(row, closed, now=now)
    assert not any(str(e.get("kind", "")).startswith("SHADOW_TP") for e in events)
    assert updates.get("outcome_status") != "SHADOW_TP3_TOUCHED"


def test_a75_closed_frame_uses_last_actual_retained_timestamp_after_dropna():
    now = time.time()
    raw = _outcome_test_frame(now)
    expected = int(pd.Timestamp(raw.index[-2]).timestamp())
    raw.iloc[-1, raw.columns.get_loc("close")] = float("nan")
    closed, actual_ts = bot.OpportunityHunter._closed_frame(raw, 300, now=now)
    assert closed is not None
    assert int(pd.Timestamp(closed.index[-1]).timestamp()) == expected
    assert actual_ts == expected


def test_a75_regime_confirmation_advances_once_per_distinct_closed_candle(monkeypatch):
    cls = bot.MarketRegime
    old_state = (cls._last_regime, cls._pending_regime, cls._pending_bars, cls._last_shift_ts,
                 getattr(cls, "_a75_last_closed_bar_key", None))
    idx = pd.date_range(end=pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=6), periods=220, freq="4h")
    frame = pd.DataFrame({"close": [100.0] * len(idx)}, index=idx)
    monkeypatch.setattr(bot, "_v702_a33_closed_index", lambda df, interval: len(df) - 1)
    monkeypatch.setattr(bot, "_v702_a33_timestamp_ms", lambda df: [int(x.value // 1_000_000) for x in df.index])
    monkeypatch.setattr(bot.Indicators, "ema", staticmethod(lambda series, period: pd.Series([90.0] * len(series), index=series.index)))
    monkeypatch.setattr(cls, "_classify_hysteresis", classmethod(lambda klass, pct: "BULLISH"))
    monkeypatch.setattr(bot, "MONO_NOW", lambda: 1000.0)
    try:
        cls._last_regime = "BEARISH"
        cls._pending_regime = None
        cls._pending_bars = 0
        cls._last_shift_ts = 0.0
        cls._a75_last_closed_bar_key = None
        with patch.dict(bot.CONFIG, {"REGIME_HYSTERESIS_ENABLE": True, "REGIME_CONFIRM_BARS": 3, "REGIME_MIN_DWELL_SEC": 0}, clear=False):
            for _ in range(10):
                cls.classify_from_btc_4h(frame)
            assert cls._pending_bars == 1
            next_idx = idx.append(pd.DatetimeIndex([idx[-1] + pd.Timedelta(hours=4)]))
            next_frame = pd.DataFrame({"close": [100.0] * len(next_idx)}, index=next_idx)
            cls.classify_from_btc_4h(next_frame)
            assert cls._pending_bars == 2
    finally:
        cls._last_regime, cls._pending_regime, cls._pending_bars, cls._last_shift_ts, cls._a75_last_closed_bar_key = old_state


def test_a75_final_validator_fails_when_a72_fails(monkeypatch):
    monkeypatch.setattr(bot, "_V702_A66_PREVIOUS_VALIDATE_CONFIG", lambda: True)
    monkeypatch.setattr(bot, "_v702_a66_startup_recovery_source_check",
                        lambda: {"pass": True, "checks": {"base": True}, "failed": []})
    monkeypatch.setattr(bot, "_v702_a72_read_only_runtime_source_check",
                        lambda: {"pass": False, "checks": {"forced": False}, "failed": ["forced_failure"]})
    assert bot._v702_a66_validate_config() is False
    result = bot.STATS["v702_a66_final_validation"]
    assert result["pass"] is False
    assert "a72:forced_failure" in result["failed"]


def test_a75_monitor_only_telegram_listener_allows_reads_but_blocks_mutations(monkeypatch):
    calls = []
    replies = []
    async def prior(cls, exchange, message):
        calls.append((exchange, message.get("text")))
    async def reply(cls, chat_id, text):
        replies.append(text)
    monkeypatch.setattr(bot.TelegramCommandController, "_authorized", classmethod(lambda cls, msg: True))
    monkeypatch.setattr(bot, "_A75_PREV_TG_HANDLE", prior)
    monkeypatch.setattr(bot.TelegramCommandController, "_reply", classmethod(reply))
    with patch.dict(bot.FINAL_CANONICAL_RUNTIME, {
        "effective_entry_policy": "MONITOR_ONLY_NO_NEW_BUYS", "production_decision": "NO_GO_UNATTENDED_LIVE",
    }, clear=False):
        asyncio.run(bot.TelegramCommandController._handle(None, {"text": "/cancel", "chat": {"id": 1}}))
        asyncio.run(bot.TelegramCommandController._handle(None, {"text": "/ping", "chat": {"id": 1}}))
    assert calls == [(None, "/ping")]
    assert replies and "MONITOR_ONLY" in replies[0]


def test_a79_supplemental_pool_excludes_scanned_stable_and_forbidden_symbols():
    tickers = {
        "AAA/USDT": {"quoteVolume": 9_000_000, "last": 1.0, "percentage": 3.0},
        "BBB/USDT": {"quoteVolume": 8_000_000, "last": 2.0, "percentage": 1.0},
        "CCC/USDT": {"quoteVolume": 1_000_000, "last": 3.0, "percentage": 2.0},
        "USDC/USDT": {"quoteVolume": 90_000_000, "last": 1.0, "percentage": 0.0},
        "BAD/USDT": {"quoteVolume": 7_000_000, "last": 1.0, "percentage": 2.0},
    }
    rows = bot._v702_a79_supplement_pool(
        list(tickers), tickers, already_scanned={"AAA/USDT"},
        min_quote_volume=2_000_000, forbidden_fn=lambda symbol: symbol == "BAD/USDT",
    )
    assert [row["symbol"] for row in rows] == ["BBB/USDT"]


def test_a79_supplement_selection_rotates_fairly_and_prioritizes_active_swing_followup():
    tickers = {
        f"S{i}/USDT": {"quoteVolume": 10_000_000 - i * 100_000, "last": 1.0, "percentage": float(i)}
        for i in range(1, 8)
    }
    first = bot._v702_a79_select_supplemental_symbols(
        list(tickers), tickers, max_symbols=2, offset=0, forbidden_fn=lambda _: False,
    )
    second = bot._v702_a79_select_supplemental_symbols(
        list(tickers), tickers, max_symbols=2, offset=2, forbidden_fn=lambda _: False,
    )
    assert len(first) == len(second) == 2
    assert set(first).isdisjoint(second)
    priority = bot._v702_a79_select_supplemental_symbols(
        list(tickers), tickers, max_symbols=2, offset=4,
        priority_symbols=["S7/USDT"], forbidden_fn=lambda _: False,
    )
    assert priority[0] == "S7/USDT"
    assert len(priority) == 2


def test_a79_swing_geometry_and_hourly_metadata_are_explicit_and_bounded():
    item = bot._v702_a79_stamp_swing({"timeframe": "5m", "evidence": {}})
    assert item["timeframe"] == "1H+4H"
    assert item["evidence"]["strategy_style"] == "SWING"
    assert item["evidence"]["outcome_interval_sec"] == 3600
    stop = bot._v702_a79_structural_stop(100.0, 99.8, 99.0, 1.0)
    assert stop is not None and stop < 100.0
    risk_pct = (100.0 - stop) / 100.0 * 100.0
    assert 0.35 - 1e-8 <= risk_pct <= 4.0 + 1e-8
    assert bot._v702_a79_structural_stop(100.0, 90.0, 91.0, 1.0) is None


def test_a79_release_contract_is_read_only_and_self_test_passes():
    report = bot.STATS.get("v702_a79_self_test", {})
    assert report.get("pass") is True, report.get("failed")
    assert bot.OpportunityHunter.execution_authority is False
    assert bot.FINAL_CANONICAL_RUNTIME.get("effective_entry_policy") == "MONITOR_ONLY_NO_NEW_BUYS"
    assert bot.FINAL_CANONICAL_RUNTIME.get("hard_gate_bypass") is False
    assert bot.FINAL_CANONICAL_RUNTIME.get("live_gates_relaxed") is False
    assert bot.FINAL_CANONICAL_RUNTIME.get("all_five_a9_engines_share_supplemental_mtf_snapshots") is True


def test_a79_bearish_btc_demotes_base_swing_confirmation_to_watch_without_local_rs(monkeypatch):
    now = time.time()
    md = {
        "df_1h": _a74_trending_frame(now, 3600, breakout=True),
        "df_4h": _a74_trending_frame(now, 14400, breakout=True),
        "quote_vol_24h": 35_000_000.0,
        "spread_pct": 0.02,
        # No closed BTC-relative series: long confirmation must not be inferred.
    }
    monkeypatch.setitem(bot.STATS, "v702_btc_macro_context_last_regime", "BEARISH")
    rows = bot.OpportunityHunter._evaluate_snapshot("AAA/USDT", md, now=now)
    swing = [row for row in rows if str(row.get("pattern") or "").startswith("SWING_")]
    assert swing
    assert all(str(row.get("status") or "").upper() != "CONFIRMED" for row in swing)
    assert any(str(row.get("status") or "").upper() == "WATCH" for row in swing)
    assert all(row.get("timeframe") == "1H+4H" for row in swing)
    assert all(row.get("evidence", {}).get("outcome_interval_sec") == 3600 for row in swing)


def test_a82_pivot_delta_configuration_is_read_from_environment(monkeypatch):
    key = "V702_A82_SWING_HIGHER_LOW_MIN_PIVOT_DELTA_ATR"
    previous = bot.CONFIG.get(key, 0.05)
    monkeypatch.setitem(bot.CONFIG, key, previous)
    monkeypatch.setattr(bot, "_env_first", lambda *keys: "0.12" if key in keys else None)
    bot._apply_loaded_environment_config()
    assert bot.CONFIG[key] == 0.12


def test_a82_supplement_outer_failure_reconciles_failed_and_redacts_diagnostics():
    exc = RuntimeError("api_key=super-secret https://private.example/path rate limit")
    row = bot._v702_a79_supplement_failure_summary(
        {"attempted": 32, "ok": 0, "failed": 0, "timed_out": 0}, exc
    )
    assert row["attempted"] == 32
    assert row["ok"] == 0
    assert row["failed"] == 32
    assert row["failure_stage"] == "supplement_exception"
    assert "super-secret" not in row["error"]
    assert "private.example" not in row["error"]


def test_a82_higher_low_local_structure_is_independent_of_bearish_btc_label(monkeypatch):
    now = time.time()
    md = {
        "df_1h": _a74_trending_frame(now, 3600, breakout=False),
        "df_4h": _a74_trending_frame(now, 14400, breakout=False),
        "quote_vol_24h": 35_000_000.0,
        "spread_pct": 0.02,
    }
    def stable_indicators(cls, frame):
        close = float(frame["close"].iloc[-1])
        return {"atr": 0.60, "ema9": close - 0.05, "ema20": close - 0.10,
                "ema50": close - 0.50, "rsi14": 65.0, "volume_ratio": 1.20}
    monkeypatch.setattr(bot.OpportunityHunter, "_indicators", classmethod(stable_indicators))
    monkeypatch.setattr(bot, "_v702_r20_swing_points", lambda df, upto_pos=None: (
        [(70, 123.0), (100, 126.5)], [(74, 121.0), (104, 122.0)]
    ))
    monkeypatch.setitem(bot.STATS, "v702_btc_macro_context_last_regime", "BEARISH")
    rows = bot.OpportunityHunter._evaluate_snapshot("AAA/USDT", md, now=now)
    item = next(row for row in rows if row["pattern"] == "SWING_HIGHER_LOW_RECLAIM")
    assert item["status"] == "WATCH"
    assert item["evidence"]["higher_low"] is True
    assert item["evidence"]["higher_high"] is True
    assert item["evidence"]["bearish_local_confirm"] is True
    assert item["timeframe"] == "1H+4H"
    assert item["evidence"]["outcome_interval_sec"] == 3600
    assert item["tp1"] > item["entry_ref"] > item["sl_price"]
    assert bot.FINAL_CANONICAL_RUNTIME["active_a82_revision_current"].startswith("A82-")
    assert bot.FINAL_CANONICAL_RUNTIME["effective_entry_policy"] == "MONITOR_ONLY_NO_NEW_BUYS"
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False


def test_a82_higher_low_and_higher_high_reclaim_can_confirm_only_when_macro_contract_passes(monkeypatch):
    now = time.time()
    md = {
        "df_1h": _a74_trending_frame(now, 3600, breakout=False),
        "df_4h": _a74_trending_frame(now, 14400, breakout=False),
        "quote_vol_24h": 35_000_000.0,
        "spread_pct": 0.02,
    }
    def stable_indicators(cls, frame):
        close = float(frame["close"].iloc[-1])
        return {"atr": 0.60, "ema9": close - 0.05, "ema20": close - 0.10,
                "ema50": close - 0.50, "rsi14": 65.0, "volume_ratio": 1.20}
    monkeypatch.setattr(bot.OpportunityHunter, "_indicators", classmethod(stable_indicators))
    # The latest confirmed swing high is below the final closed 1H close, so
    # the detector has a genuine HH reclaim rather than an unconfirmed wick.
    monkeypatch.setattr(bot, "_v702_r20_swing_points", lambda df, upto_pos=None: (
        [(70, 123.0), (100, 125.0)], [(74, 121.0), (104, 122.0)]
    ))
    monkeypatch.setitem(bot.STATS, "v702_btc_macro_context_last_regime", "NEUTRAL")
    rows = bot.OpportunityHunter._evaluate_snapshot("AAA/USDT", md, now=now)
    item = next(row for row in rows if row["pattern"] == "SWING_HIGHER_LOW_RECLAIM")
    assert item["status"] == "CONFIRMED"
    assert item["evidence"]["higher_low"] is True
    assert item["evidence"]["higher_high"] is True
    assert item["evidence"]["structure_reclaim"] is True


def test_a80_read_only_status_command_returns_live_digest_in_monitor_only(monkeypatch):
    replies = []
    async def reply(cls, chat_id, text):
        replies.append((chat_id, text))
    class FakeDigest:
        @classmethod
        def build(cls):
            return "FAKE-LIVE-DIGEST"
    monkeypatch.setattr(bot.TelegramCommandController, "_authorized", classmethod(lambda cls, msg: True))
    monkeypatch.setattr(bot.TelegramCommandController, "_reply", classmethod(reply))
    monkeypatch.setattr(bot, "_V702R28TelegramDigest", FakeDigest)
    with patch.dict(bot.FINAL_CANONICAL_RUNTIME, {
        "effective_entry_policy": "MONITOR_ONLY_NO_NEW_BUYS",
        "production_decision": "NO_GO_UNATTENDED_LIVE",
    }, clear=False):
        asyncio.run(bot.TelegramCommandController._handle(None, {"text": "/status", "chat": {"id": 123}}))
    assert len(replies) == 1
    assert replies[0][0] == 123
    assert "A80 READ-ONLY STATUS" in replies[0][1]
    assert "FAKE-LIVE-DIGEST" in replies[0][1]
    assert "MONITOR_ONLY_NO_NEW_BUYS" in replies[0][1]


def test_a80_telegram_bootstrap_fails_closed_when_webhook_clear_fails(monkeypatch):
    calls = []
    async def fake_api(cls, method, payload):
        calls.append(method)
        if method == "getMe":
            return {"ok": True, "result": {"id": 7, "username": "test_bot"}}
        if method == "deleteWebhook":
            return None
        raise AssertionError(method)
    async def fake_send(cls, text):
        raise AssertionError("startup message must not send before webhook clear")
    monkeypatch.setattr(bot.TelegramCommandController, "_call_api", classmethod(fake_api))
    monkeypatch.setattr(bot.TelegramDispatcher, "_send_one", classmethod(fake_send))
    monkeypatch.setitem(bot.ENV, "TELEGRAM_TOKEN", "test-token")
    monkeypatch.setitem(bot.ENV, "TELEGRAM_CHAT", "123")
    monkeypatch.setattr(bot.TelegramCommandController, "_bootstrapped", False, raising=False)
    result = asyncio.run(bot.TelegramCommandController.bootstrap())
    assert result is False
    assert calls == ["getMe", "deleteWebhook"]
    assert bot.STATS.get("v649_telegram_bootstrap_state") == "WEBHOOK_CLEAR_FAILED_POLLING_BLOCKED"
    assert bot.TelegramCommandController._bootstrapped is False


def test_a80_telegram_bootstrap_keeps_inbound_polling_when_startup_send_fails(monkeypatch):
    calls = []
    async def fake_api(cls, method, payload):
        calls.append(method)
        return {"ok": True, "result": ({"id": 7, "username": "test_bot"} if method == "getMe" else True)}
    async def fake_send(cls, text):
        return False, False
    monkeypatch.setattr(bot.TelegramCommandController, "_call_api", classmethod(fake_api))
    monkeypatch.setattr(bot.TelegramDispatcher, "_send_one", classmethod(fake_send))
    monkeypatch.setitem(bot.ENV, "TELEGRAM_TOKEN", "test-token")
    monkeypatch.setitem(bot.ENV, "TELEGRAM_CHAT", "123")
    monkeypatch.setattr(bot.TelegramCommandController, "_bootstrapped", False, raising=False)
    result = asyncio.run(bot.TelegramCommandController.bootstrap())
    assert result is True
    assert calls == ["getMe", "deleteWebhook"]
    assert bot.STATS.get("v649_telegram_bootstrap_state") == "VERIFIED_READY_OUTBOUND_DEGRADED"
    assert bot.STATS.get("v649_telegram_startup_send_ok") is False
    assert bot.TelegramCommandController._bootstrapped is True


def test_a80_wide_research_universe_uses_quote_volume_fallback_and_keeps_core_floor():
    markets = {
        "CORE/USDT": {"quote": "USDT", "spot": True, "active": True},
        "MID/USDT": {"quote": "USDT", "spot": True, "active": True},
        "LOW/USDT": {"quote": "USDT", "spot": True, "active": True},
        "USDC/USDT": {"quote": "USDT", "spot": True, "active": True},
        "PERP/USDT": {"quote": "USDT", "spot": False, "active": True},
        "BAD/USDT": {"quote": "USDT", "spot": True, "active": True},
    }
    tickers = {
        "CORE/USDT": {"quoteVolume": 4_000_000, "last": 1.0},
        "MID/USDT": {"quoteVolume": 750_000, "last": 2.0},
        "LOW/USDT": {"baseVolume": 100_000, "last": 3.0},
        "USDC/USDT": {"quoteVolume": 80_000_000, "last": 1.0},
        "PERP/USDT": {"quoteVolume": 30_000_000, "last": 1.0},
        "BAD/USDT": {"quoteVolume": 900_000, "last": 1.0},
    }
    result = bot._v702_a80_build_research_universe(
        ["CORE/USDT"], tickers, markets, max_symbols=500,
        min_quote_volume=250_000, forbidden_fn=lambda symbol: symbol == "BAD/USDT",
    )
    assert "CORE/USDT" in result
    assert "MID/USDT" in result
    assert "LOW/USDT" in result  # baseVolume * last fallback = 300k
    assert "USDC/USDT" not in result
    assert "PERP/USDT" not in result
    assert "BAD/USDT" not in result
    assert float(bot.CONFIG["LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME"]) >= 3_000_000.0


def test_a80_monitor_only_canonical_opportunity_alerts_are_not_suppressed_by_full_live_default():
    with patch.dict(bot.CONFIG, {
        "TELEGRAM_ENABLED": True,
        "TELEGRAM_OPPORTUNITY_ALERTS_ENABLE": True,
        "TELEGRAM_OPPORTUNITY_REQUIRE_FULL_LIVE": False,
    }, clear=False):
        assert bot.OpportunityTelegramNotifier._runtime_allowed() is True


def test_a80_release_contract_passes_and_preserves_monitor_only():
    result = bot.STATS.get("v702_a80_self_test", {})
    assert result.get("pass") is True, result.get("failed")
    assert bot.FINAL_CANONICAL_RUNTIME.get("effective_entry_policy") == "MONITOR_ONLY_NO_NEW_BUYS"
    assert bot.OpportunityHunter.execution_authority is False
    assert bot.FINAL_CANONICAL_RUNTIME.get("hard_gate_bypass") is False
    assert bot.FINAL_CANONICAL_RUNTIME.get("live_gates_relaxed") is False


def test_a80_supplement_pool_uses_same_venue_quote_volume_fallback():
    tickers = {
        "VENUE/USDT": {"last": 2.0, "info": {"volValue": "650000"}},
        "BASE/USDT": {"last": 3.0, "baseVolume": 100_000},
    }
    pool = bot._v702_a79_supplement_pool(
        ["VENUE/USDT", "BASE/USDT"], tickers, already_scanned=(),
        min_quote_volume=250_000, forbidden_fn=lambda symbol: False,
    )
    assert {row["symbol"] for row in pool} == {"VENUE/USDT", "BASE/USDT"}
    assert {round(row["quote_volume"]) for row in pool} == {650_000, 300_000}


def test_a80_supplement_selector_scales_to_32_symbols_without_bypassing_liquidity():
    symbols = [f"C{i:03d}/USDT" for i in range(40)]
    tickers = {symbol: {"quoteVolume": 400_000 + i, "last": 1.0, "percentage": 1.0}
               for i, symbol in enumerate(symbols)}
    selected = bot._v702_a79_select_supplemental_symbols(
        symbols, tickers, already_scanned=(), max_symbols=32,
        min_quote_volume=250_000, offset=0, forbidden_fn=lambda symbol: False,
    )
    assert len(selected) == 32
    assert len(set(selected)) == 32
    assert set(selected).issubset(set(symbols))



def test_a81_research_environment_tunables_are_loaded_and_wired(monkeypatch):
    keys = (
        "V702_INTRADAY_SHADOW_MIN_QUOTE_VOLUME_USDT",
        "V702_INTRADAY_SHADOW_MAX_SYMBOLS_PER_CYCLE",
        "V702_A79_SUPPLEMENT_MIN_QUOTE_VOLUME_USDT",
        "V702_A79_SUPPLEMENT_CONCURRENCY",
        "V702_A79_SUPPLEMENT_CYCLE_BUDGET_SEC",
    )
    previous = {key: bot.CONFIG.get(key) for key in keys}
    try:
        values = {
            "V702_INTRADAY_SHADOW_MIN_QUOTE_VOLUME_USDT": "900000",
            "V702_INTRADAY_SHADOW_MAX_SYMBOLS_PER_CYCLE": "7",
            "V702_A79_SUPPLEMENT_MIN_QUOTE_VOLUME_USDT": "900000",
            "V702_A79_SUPPLEMENT_CONCURRENCY": "5",
            "V702_A79_SUPPLEMENT_CYCLE_BUDGET_SEC": "9",
        }
        for key, value in values.items():
            monkeypatch.setenv(key, value)
        bot._apply_loaded_environment_config()
        assert bot.CONFIG["V702_INTRADAY_SHADOW_MIN_QUOTE_VOLUME_USDT"] == 900000
        assert bot.CONFIG["V702_INTRADAY_SHADOW_MAX_SYMBOLS_PER_CYCLE"] == 7
        assert bot.CONFIG["V702_A79_SUPPLEMENT_MIN_QUOTE_VOLUME_USDT"] == 900000
        assert bot.CONFIG["V702_A79_SUPPLEMENT_CONCURRENCY"] == 5
        assert bot.CONFIG["V702_A79_SUPPLEMENT_CYCLE_BUDGET_SEC"] == 9.0
        source = bot._v702_read_source_text()
        assert 'min_quote_volume=max(250_000.0, float(CONFIG.get("V702_A79_SUPPLEMENT_MIN_QUOTE_VOLUME_USDT"' in source
        assert 'concurrency=max(1, min(16, int(CONFIG.get("V702_A79_SUPPLEMENT_CONCURRENCY"' in source
        assert 'cycle_budget_sec=max(3.0, min(30.0, float(CONFIG.get("V702_A79_SUPPLEMENT_CYCLE_BUDGET_SEC"' in source
        assert bot.CONFIG["LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME"] == 3_000_000.0
        assert bot.FINAL_CANONICAL_RUNTIME.get("active_a81_revision_current") == bot.V702_A81_REVISION
    finally:
        for key, value in previous.items():
            if value is None:
                bot.CONFIG.pop(key, None)
            else:
                bot.CONFIG[key] = value


def test_a80_status_keyboard_text_alias_is_read_only_in_monitor_only(monkeypatch):
    replies = []
    async def reply(cls, chat_id, text):
        replies.append((chat_id, text))
    class FakeDigest:
        @classmethod
        def build(cls):
            return "FAKE-STATUS-ALIAS-DIGEST"
    monkeypatch.setattr(bot.TelegramCommandController, "_authorized", classmethod(lambda cls, msg: True))
    monkeypatch.setattr(bot.TelegramCommandController, "_reply", classmethod(reply))
    monkeypatch.setattr(bot, "_V702R28TelegramDigest", FakeDigest)
    with patch.dict(bot.FINAL_CANONICAL_RUNTIME, {
        "effective_entry_policy": "MONITOR_ONLY_NO_NEW_BUYS",
        "production_decision": "NO_GO_UNATTENDED_LIVE",
    }, clear=False):
        asyncio.run(bot.TelegramCommandController._handle(None, {"text": "Status", "chat": {"id": 321}}))
    assert len(replies) == 1
    assert replies[0][0] == 321
    assert "A80 READ-ONLY STATUS" in replies[0][1]
    assert "FAKE-STATUS-ALIAS-DIGEST" in replies[0][1]


# A83 stablecoin analytical primitives; no exchange orders are exercised.
def test_a83_stablecoin_microprice_imbalance_and_spread():
    mm = bot.StablecoinMarketMaker
    assert mm.microprice(.9998, 10, 1.0002, 20) == pytest.approx(.9999333333333333)
    assert mm.imbalance(60, 40) == pytest.approx(.2)
    assert mm.spread_bps(.9998, 1.0002) == pytest.approx(4.0)


def test_a83_stablecoin_net_profit_and_fail_closed_buy_edge():
    mm = bot.StablecoinMarketMaker
    result = mm.net_profit(100, 100.05, .01, .01)
    assert result["net_pnl_estimate_usdt"] == pytest.approx(.03)
    assert mm.buy_edge(1, .9998, .5, 1, .2, 1, 0, 10)[0] is True
    assert mm.buy_edge(1, .9998, 3, 1, .2, 1, 12, 10)[0] is False
    assert mm.live_is_armed() is False


def test_a83_stablecoin_invalid_book_rejected():
    with pytest.raises(ValueError):
        bot.StablecoinMarketMaker.microprice(1, 0, 1.001, 1)


def test_a83_shadow_trade_prints_consume_queue_before_simulated_fill():
    mm = bot.StablecoinMarketMaker
    order = {"limit_price": 1.0, "remaining_qty": 5.0, "queue_ahead_qty": 10.0}
    # Same-price sell prints first consume the visible queue ahead.
    assert mm.consume_trade_fill(order, {"side": "sell", "price": 1.0, "amount": 8.0}, "buy") == 0.0
    assert order["queue_ahead_qty"] == pytest.approx(2.0)
    assert mm.consume_trade_fill(order, {"side": "sell", "price": 1.0, "amount": 5.0}, "buy") == pytest.approx(3.0)
    # A print through the limit is evidence of executable volume, but still capped by order remainder.
    assert mm.consume_trade_fill(order, {"side": "sell", "price": 0.9999, "amount": 4.0}, "buy") == pytest.approx(2.0)
    assert order["remaining_qty"] == pytest.approx(0.0)
    assert mm.consume_trade_fill(order, {"side": "buy", "price": 1.0, "amount": 10.0}, "buy") == 0.0


def test_a83_quote_assessment_requires_edge_depth_depeg_and_print_flow(monkeypatch):
    mm = bot.StablecoinMarketMaker
    now_ms = int(time.time() * 1000)
    book = {"bids": [[0.9998, 2000.0]], "asks": [[1.0002, 2000.0]], "timestamp": now_ms}
    trades = [
        {"id": "1", "timestamp": now_ms - 1000, "side": "buy", "price": 1.0002, "amount": 10.0},
        {"id": "2", "timestamp": now_ms - 500, "side": "sell", "price": 0.9998, "amount": 2.0},
    ]
    eligible, reason, metrics = mm.assess_quote(book, trades, maker_fee_rate=0.0, now_ms=now_ms)
    assert eligible and reason == "eligible_shadow_quote"
    assert metrics["estimated_net_bps"] > metrics["required_net_bps"]
    bad_book = {"bids": [[0.996, 2000.0]], "asks": [[0.9962, 2000.0]], "timestamp": now_ms}
    eligible, reason, _ = mm.assess_quote(bad_book, trades, maker_fee_rate=0.0, now_ms=now_ms)
    assert not eligible and reason == "depeg_guard"
    thin_book = {"bids": [[0.9998, 10.0]], "asks": [[1.0002, 10.0]], "timestamp": now_ms}
    eligible, reason, _ = mm.assess_quote(thin_book, trades, maker_fee_rate=0.0, now_ms=now_ms)
    assert not eligible and reason == "depth_below_floor"


def test_a83_cycle_journal_persists_active_state_and_daily_report_claim(tmp_path):
    old_db = bot.CONFIG.get("DB_PATH")
    bot.CONFIG["DB_PATH"] = str(tmp_path / "a83.db")
    try:
        bot.DBManager.init_schema()
        cycle = {
            "cycle_id": "a83-cycle-test", "symbol": "USDC/USDT", "state": "BUY_PENDING",
            "started_at": datetime.now(timezone.utc).isoformat(), "buy_filled_qty": 0.0,
            "buy_cost_usdt": 0.0,
        }
        bot.DBManager.save_stablecoin_mm_cycle(cycle, "BUY_QUOTE_CREATED", {"test": True})
        recovered = bot.DBManager.get_active_stablecoin_mm_cycle("USDC/USDT")
        assert recovered and recovered["cycle_id"] == cycle["cycle_id"]
        assert recovered["state"] == "BUY_PENDING"
        cycle.update({"state": "CLOSED", "closed_at": datetime.now(timezone.utc).isoformat(), "net_pnl_usdt": 0.025})
        bot.DBManager.save_stablecoin_mm_cycle(cycle, "CYCLE_CLOSED")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        summary = bot.DBManager.stablecoin_mm_daily_summary(today)
        assert summary["completed_cycles"] == 1
        assert summary["net_pnl_usdt"] == pytest.approx(0.025)
        assert bot.DBManager.has_stablecoin_mm_daily_report(today) is False
        assert bot.DBManager.claim_stablecoin_mm_daily_report(today) is True
        assert bot.DBManager.claim_stablecoin_mm_daily_report(today) is False
        assert bot.DBManager.has_stablecoin_mm_daily_report(today) is True
    finally:
        bot.CONFIG["DB_PATH"] = old_db


def test_a83_tick_creates_only_a_shadow_quote_and_never_calls_order_methods(tmp_path):
    cfg_keys = ("DB_PATH", "STABLECOIN_MM_MODE", "STABLECOIN_MM_KILL_SWITCH",
                "STABLECOIN_MM_MAKER_FEE_RATE_OVERRIDE", "STABLECOIN_MM_MIN_NET_BPS",
                "STABLECOIN_MM_ESTIMATED_SLIPPAGE_BPS", "STABLECOIN_MM_MAX_SPREAD_BPS",
                "STABLECOIN_MM_ORDERBOOK_DEPTH_USDT", "STABLECOIN_MM_TRADE_LOOKBACK_SEC")
    old_cfg = {key: bot.CONFIG.get(key) for key in cfg_keys}
    bot.CONFIG["DB_PATH"] = str(tmp_path / "a83_tick.db")
    bot.CONFIG["STABLECOIN_MM_MODE"] = "SHADOW"
    bot.CONFIG["STABLECOIN_MM_KILL_SWITCH"] = False
    bot.CONFIG["STABLECOIN_MM_MAKER_FEE_RATE_OVERRIDE"] = 0.0
    bot.CONFIG["STABLECOIN_MM_MIN_NET_BPS"] = 1.0
    bot.CONFIG["STABLECOIN_MM_ESTIMATED_SLIPPAGE_BPS"] = 0.1
    bot.CONFIG["STABLECOIN_MM_MAX_SPREAD_BPS"] = 12.0
    bot.CONFIG["STABLECOIN_MM_ORDERBOOK_DEPTH_USDT"] = 1000.0
    bot.CONFIG["STABLECOIN_MM_TRADE_LOOKBACK_SEC"] = 120.0
    bot.DBManager.init_schema()
    now_ms = int(time.time() * 1000)

    class PublicOnlyFake:
        markets = {"USDC/USDT": {"symbol": "USDC/USDT", "base": "USDC", "quote": "USDT", "spot": True, "active": True, "maker": 0.0}}
        async def load_markets(self): return self.markets
        async def fetch_order_book(self, symbol, limit=20):
            return {"bids": [[0.9998, 2000.0]], "asks": [[1.0002, 2000.0]], "timestamp": now_ms}
        async def fetch_trades(self, symbol, limit=100):
            return [{"id": "recent-buy", "timestamp": now_ms - 100, "side": "buy", "price": 1.0002, "amount": 20.0}]
        def price_to_precision(self, symbol, value): return f"{float(value):.4f}"
        def amount_to_precision(self, symbol, value): return f"{float(value):.4f}"
        async def create_order(self, *args, **kwargs): raise AssertionError("Shadow must not submit orders")
        async def create_limit_buy_order(self, *args, **kwargs): raise AssertionError("Shadow must not submit orders")
        async def create_limit_sell_order(self, *args, **kwargs): raise AssertionError("Shadow must not submit orders")

    try:
        result = asyncio.run(bot.StablecoinMarketMaker.tick(PublicOnlyFake(), now_ms=now_ms))
        assert result["ok"] is True
        assert result["reason"] == "shadow_quote_created"
        active = bot.DBManager.get_active_stablecoin_mm_cycle("USDC/USDT")
        assert active and active["state"] == "BUY_PENDING"
        assert active["buy_order"]["limit_price"] == pytest.approx(0.9998)
        assert bot.StablecoinMarketMaker.live_is_armed() is False
    finally:
        for key, value in old_cfg.items():
            bot.CONFIG[key] = value


def test_a83_shadow_cycle_closes_only_after_buy_and_sell_public_prints(tmp_path, monkeypatch):
    old_cfg = {key: bot.CONFIG.get(key) for key in (
        "DB_PATH", "STABLECOIN_MM_MODE", "STABLECOIN_MM_KILL_SWITCH",
        "STABLECOIN_MM_MAKER_FEE_RATE_OVERRIDE", "STABLECOIN_MM_MIN_NET_BPS",
        "STABLECOIN_MM_ESTIMATED_SLIPPAGE_BPS", "STABLECOIN_MM_MAX_SPREAD_BPS",
        "STABLECOIN_MM_ORDERBOOK_DEPTH_USDT", "STABLECOIN_MM_TRADE_LOOKBACK_SEC",
        "STABLECOIN_MM_QUEUE_SAFETY_MULTIPLIER", "STABLECOIN_MM_MIN_NET_PROFIT_USDT",
    )}
    bot.CONFIG.update({
        "DB_PATH": str(tmp_path / "a83_full_cycle.db"),
        "STABLECOIN_MM_MODE": "SHADOW",
        "STABLECOIN_MM_KILL_SWITCH": False,
        "STABLECOIN_MM_MAKER_FEE_RATE_OVERRIDE": 0.0,
        "STABLECOIN_MM_MIN_NET_BPS": 1.0,
        "STABLECOIN_MM_ESTIMATED_SLIPPAGE_BPS": 0.1,
        "STABLECOIN_MM_MAX_SPREAD_BPS": 12.0,
        "STABLECOIN_MM_ORDERBOOK_DEPTH_USDT": 1000.0,
        "STABLECOIN_MM_TRADE_LOOKBACK_SEC": 120.0,
        "STABLECOIN_MM_QUEUE_SAFETY_MULTIPLIER": 1.25,
        "STABLECOIN_MM_MIN_NET_PROFIT_USDT": 0.02,
    })
    bot.DBManager.init_schema()
    now_ms = int(time.time() * 1000)

    class PublicOnlyCycleExchange:
        markets = {"USDC/USDT": {"symbol": "USDC/USDT", "base": "USDC", "quote": "USDT",
                                 "spot": True, "active": True, "maker": 0.0,
                                 "limits": {"amount": {"min": 0.0}, "cost": {"min": 0.0}}}}
        trades = [{"id": "seed-flow", "timestamp": now_ms - 100, "side": "buy",
                   "price": 1.0002, "amount": 20.0}]
        order_methods_called = 0

        async def fetch_order_book(self, symbol, limit=20):
            return {"bids": [[0.9998, 1.0], [0.9997, 2000.0]],
                    "asks": [[1.0002, 1.0], [1.0003, 2000.0]], "timestamp": now_ms}

        async def fetch_trades(self, symbol, limit=100):
            return list(self.trades)

        def price_to_precision(self, symbol, value):
            return f"{float(value):.4f}"

        def amount_to_precision(self, symbol, value):
            return f"{float(value):.4f}"

        async def create_order(self, *args, **kwargs):
            self.order_methods_called += 1
            raise AssertionError("A83 Shadow must never submit orders")

        async def create_limit_buy_order(self, *args, **kwargs):
            self.order_methods_called += 1
            raise AssertionError("A83 Shadow must never submit orders")

        async def create_limit_sell_order(self, *args, **kwargs):
            self.order_methods_called += 1
            raise AssertionError("A83 Shadow must never submit orders")

    async def no_notify(cls, message):
        return True

    monkeypatch.setattr(bot.StablecoinMarketMaker, "_notify", classmethod(no_notify))
    exchange = PublicOnlyCycleExchange()
    try:
        created = asyncio.run(bot.StablecoinMarketMaker.tick(exchange, now_ms=now_ms))
        assert created["reason"] == "shadow_quote_created"

        exchange.trades.append({"id": "buy-side-fill", "timestamp": now_ms + 500,
                                "side": "sell", "price": 0.9998, "amount": 120.0})
        bought = asyncio.run(bot.StablecoinMarketMaker.tick(exchange, now_ms=now_ms + 1000))
        assert bought["state"] == "SELL_PENDING"
        active = bot.DBManager.get_active_stablecoin_mm_cycle("USDC/USDT")
        assert active and active["state"] == "SELL_PENDING"
        assert active["buy_filled_qty"] > 0

        exchange.trades.append({"id": "sell-side-fill", "timestamp": now_ms + 1500,
                                "side": "buy", "price": 1.0002, "amount": 120.0})
        sold = asyncio.run(bot.StablecoinMarketMaker.tick(exchange, now_ms=now_ms + 2000))
        assert sold["state"] == "CLOSED"
        assert bot.DBManager.get_active_stablecoin_mm_cycle("USDC/USDT") is None
        summary = bot.DBManager.stablecoin_mm_daily_summary(
            datetime.fromtimestamp(now_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d"))
        assert summary["completed_cycles"] == 1
        assert summary["net_pnl_usdt"] >= 0.02
        assert exchange.order_methods_called == 0
    finally:
        for key, value in old_cfg.items():
            if value is None:
                bot.CONFIG.pop(key, None)
            else:
                bot.CONFIG[key] = value


def test_a83_mexc_raw_is_buyer_maker_maps_to_taker_aggressor_side():
    mm = bot.StablecoinMarketMaker
    assert mm._aggressor_side({"info": {"isBuyerMaker": True}}) == "sell"
    assert mm._aggressor_side({"info": {"isBuyerMaker": False}}) == "buy"
    assert mm._aggressor_side({"info": {"isBuyerMaker": "true"}}) == "sell"
    assert mm._aggressor_side({"side": "buy", "info": {"isBuyerMaker": True}}) == "buy"
    order = {"limit_price": 1.0, "remaining_qty": 2.0, "queue_ahead_qty": 0.0}
    raw_mexc_sell = {"info": {"isBuyerMaker": True}, "price": 1.0, "amount": 1.0}
    assert mm.consume_trade_fill(order, raw_mexc_sell, "buy") == pytest.approx(1.0)


def test_a83_public_market_zero_maker_rate_is_not_treated_as_account_fee(monkeypatch):
    old_fallback = bot.CONFIG.get("STABLECOIN_MM_FALLBACK_MAKER_FEE_RATE")
    old_override = bot.CONFIG.get("STABLECOIN_MM_MAKER_FEE_RATE_OVERRIDE")
    try:
        bot.CONFIG["STABLECOIN_MM_FALLBACK_MAKER_FEE_RATE"] = 0.001
        bot.CONFIG["STABLECOIN_MM_MAKER_FEE_RATE_OVERRIDE"] = None
        rate, source = bot.StablecoinMarketMaker.resolve_maker_fee_rate({"maker": 0.0})
        assert rate == pytest.approx(0.001)
        assert "NOT_ACCOUNT_CONFIRMED" in source
        bot.CONFIG["STABLECOIN_MM_MAKER_FEE_RATE_OVERRIDE"] = 0.0
        rate, source = bot.StablecoinMarketMaker.resolve_maker_fee_rate({"maker": 0.001})
        assert rate == 0.0
        assert "OPERATOR_OVERRIDE" in source
    finally:
        if old_fallback is None:
            bot.CONFIG.pop("STABLECOIN_MM_FALLBACK_MAKER_FEE_RATE", None)
        else:
            bot.CONFIG["STABLECOIN_MM_FALLBACK_MAKER_FEE_RATE"] = old_fallback
        if old_override is None:
            bot.CONFIG.pop("STABLECOIN_MM_MAKER_FEE_RATE_OVERRIDE", None)
        else:
            bot.CONFIG["STABLECOIN_MM_MAKER_FEE_RATE_OVERRIDE"] = old_override


def test_a79_supplement_fetch_uses_canonical_monitor_scan_authority(monkeypatch):
    """A79 supplemental market-data reads must not depend on an undefined alias."""
    monkeypatch.setattr(bot, "_V699_VALIDATE_ONLY_REQUEST", False)
    monkeypatch.setattr(bot, "_v702_monitor_only_scan_authorized", lambda: False)

    class MustNotFetch:
        async def fetch_ohlcv(self, *args, **kwargs):
            raise AssertionError("scan-disabled research must not call the exchange")

    snapshots, diagnostics = asyncio.run(bot._v702_a79_fetch_supplemental_snapshots(
        MustNotFetch(), ["AAA/USDT"], {"AAA/USDT": {"quoteVolume": 1_000_000}},
    ))
    assert snapshots == {}
    assert diagnostics["disabled_reason"] == "monitor_scan_disabled"
    assert diagnostics["attempted"] == diagnostics["failed"] == 1


def test_a83_market_primitives_and_orderbook_reject_nonfinite_values():
    mm = bot.StablecoinMarketMaker
    with pytest.raises(ValueError):
        mm.microprice(float("nan"), 10.0, 1.0002, 10.0)
    with pytest.raises(ValueError):
        mm.imbalance(float("inf"), 10.0)
    with pytest.raises(ValueError):
        mm.spread_bps(0.9998, float("nan"))
    with pytest.raises(ValueError):
        mm._book_snapshot({"bids": [[float("nan"), 1000.0]],
                           "asks": [[1.0002, 1000.0]]})
    allowed, reason, _ = mm.buy_edge(
        float("nan"), 1.0, 1.0, 0.1, 0.5, 0.5, 0.0, 25.0,
    )
    assert not allowed and reason == "invalid_price_or_metrics"


def test_a83_trade_flow_ignores_nonfinite_public_prints():
    now_ms = int(time.time() * 1000)
    flow = bot.StablecoinMarketMaker._trade_flow([
        {"timestamp": now_ms, "side": "buy", "price": float("nan"), "amount": 10.0},
        {"timestamp": now_ms, "side": "sell", "price": 1.0, "amount": float("inf")},
        {"timestamp": now_ms, "side": "buy", "price": 1.0, "amount": 2.0},
    ], now_ms, 120.0)
    assert flow["trade_count"] == 1
    assert flow["buy_quote"] == pytest.approx(2.0)
    assert flow["signed_flow_ratio"] == pytest.approx(1.0)


def test_a79_supplement_fetch_populates_isolated_read_only_research_map(monkeypatch):
    monkeypatch.setattr(bot, "_V699_VALIDATE_ONLY_REQUEST", False)
    monkeypatch.setattr(bot, "_v702_monitor_only_scan_authorized", lambda: True)
    async def passthrough(_label, callback, **_kwargs):
        value = callback()
        return await value if hasattr(value, "__await__") else value
    monkeypatch.setattr(bot, "safe_api_call", passthrough)

    now_ms = int(time.time() * 1000)
    periods = {"4h": 14_400_000, "1h": 3_600_000, "15m": 900_000, "5m": 300_000}
    rows_by_tf = {}
    for tf, period in periods.items():
        last_closed_open = (now_ms // period) * period - period
        rows_by_tf[tf] = [
            [last_closed_open - offset * period, 100.0, 101.0, 99.0, 100.0, 10.0]
            for offset in range(79, -1, -1)
        ]

    class PublicOhlcvOnly:
        calls = []
        async def fetch_ohlcv(self, symbol, timeframe, limit=100):
            self.calls.append((symbol, timeframe, limit))
            return rows_by_tf[timeframe]

    exchange = PublicOhlcvOnly()
    snapshots, diagnostics = asyncio.run(bot._v702_a79_fetch_supplemental_snapshots(
        exchange, ["AAA/USDT"],
        {"AAA/USDT": {"quoteVolume": 1_000_000, "last": 1.0, "bid": 0.999, "ask": 1.001}},
        cycle_budget_sec=10.0, read_timeout_sec=2.0,
    ))
    assert diagnostics["attempted"] == diagnostics["ok"] == 1, diagnostics
    assert diagnostics["failed"] == 0
    assert set(tf for _sym, tf, _limit in exchange.calls) == set(periods)
    row = snapshots["AAA/USDT"]
    assert row["v702_a79_research_recall_lane"] is True
    assert row["v702_a79_canonical_mse_eligible"] is False
    assert all(key in row for key in ("df_4h", "df_1h", "df_15m", "df_5m"))
    assert diagnostics["canonical_map_mutated"] is False


def test_a83_shadow_rejects_orderbook_without_exchange_timestamp(monkeypatch):
    old_cfg = {key: bot.CONFIG.get(key) for key in (
        "STABLECOIN_MM_MODE", "STABLECOIN_MM_KILL_SWITCH", "STABLECOIN_MM_MAKER_FEE_RATE_OVERRIDE",
        "STABLECOIN_MM_FETCH_TIMEOUT_SEC", "STABLECOIN_MM_MAX_ORDER_AGE_SEC",
    )}
    bot.CONFIG.update({"STABLECOIN_MM_MODE": "SHADOW", "STABLECOIN_MM_KILL_SWITCH": False,
                      "STABLECOIN_MM_MAKER_FEE_RATE_OVERRIDE": 0.0,
                      "STABLECOIN_MM_FETCH_TIMEOUT_SEC": 2.0,
                      "STABLECOIN_MM_MAX_ORDER_AGE_SEC": 60.0})
    class MissingTimestampExchange:
        markets = {"USDC/USDT": {"base": "USDC", "quote": "USDT", "spot": True, "active": True}}
        async def fetch_order_book(self, *_args, **_kwargs):
            return {"bids": [[0.9998, 2000.0]], "asks": [[1.0002, 2000.0]]}
        async def fetch_trades(self, *_args, **_kwargs):
            return [{"id": "x", "timestamp": int(time.time() * 1000),
                     "side": "buy", "price": 1.0002, "amount": 10.0}]
    try:
        result = asyncio.run(bot.StablecoinMarketMaker.tick(MissingTimestampExchange()))
        assert result == {"ok": False, "reason": "orderbook_timestamp_missing"}
    finally:
        for key, value in old_cfg.items():
            if value is None:
                bot.CONFIG.pop(key, None)
            else:
                bot.CONFIG[key] = value


def test_a83_trade_processor_ignores_future_and_nonfinite_prints():
    now_ms = int(time.time() * 1000)
    cycle = {"state": "BUY_PENDING", "created_ms": now_ms - 1000,
             "last_trade_ts": now_ms - 1000, "last_trade_keys": [],
             "buy_order": {"limit_price": 1.0, "remaining_qty": 5.0, "queue_ahead_qty": 0.0},
             "buy_filled_qty": 0.0, "buy_cost_usdt": 0.0, "buy_fee_usdt": 0.0,
             "maker_fee_buy_rate": 0.0}
    changes = bot.StablecoinMarketMaker._process_trades(cycle, [
        {"id": "future", "timestamp": now_ms + 10_000, "side": "sell", "price": 0.9999, "amount": 5.0},
        {"id": "nonfinite", "timestamp": now_ms, "side": "sell", "price": 0.9999, "amount": float("inf")},
    ], now_ms=now_ms)
    assert changes == []
    assert cycle["buy_filled_qty"] == 0.0


def test_a85_btc_direction_is_observational_but_crash_and_missing_context_are_hard_blocks():
    assert bot.CONFIG["V410_FAMILY_MACRO_DIRECTION_GATE_ENABLE"] is False
    ok, reason, ctx = bot.FamilyPolicyLayer.regime_policy_detail(
        "PULLBACK", "BEARISH", strategy_mode="PULLBACK", local_regime="LOCAL_RECOVERY",
        market_phase="PULLBACK", severity="BEARISH_NORMAL", strategy_style="SCALP")
    assert ok and reason == "allow" and ctx["macro_context_role"] == "OBSERVATIONAL_ONLY"
    crash, crash_reason, _ = bot.FamilyPolicyLayer.regime_policy_detail(
        "PULLBACK", "BEARISH", strategy_mode="PULLBACK", local_regime="LOCAL_RECOVERY",
        market_phase="PULLBACK", severity="BEARISH_CRASH", strategy_style="SCALP")
    assert not crash and crash_reason == "severity"
    missing, missing_reason, _ = bot.FamilyPolicyLayer.regime_policy_detail(
        "PULLBACK", "UNKNOWN", strategy_mode="PULLBACK", local_regime="LOCAL_RECOVERY",
        market_phase="PULLBACK", severity="NORMAL", strategy_style="SCALP")
    assert not missing and missing_reason == "macro_context_unavailable"


def test_a85_router_confluence_bonus_is_independent_deduplicated_and_bounded(monkeypatch):
    bonus, meta = bot._v702_router_confluence_bonus({
        "router_confluence_groups": ["PULLBACK", "PULLBACK", "BREAKOUT", "SWEEP", "MOMENTUM"]})
    assert bonus == pytest.approx(1.5)
    assert meta["group_count"] == 4
    assert set(meta["groups"]) == {"PULLBACK", "BREAKOUT", "SWEEP", "MOMENTUM"}
    monkeypatch.setitem(bot.CONFIG, "ROUTER_MULTI_STRATEGY_CONFLUENCE_ENABLE", False)
    bonus_off, meta_off = bot._v702_router_confluence_bonus({"router_confluence_groups": ["PULLBACK", "BREAKOUT"]})
    assert bonus_off == 0.0 and meta_off["group_count"] == 2


def test_a85_router_runs_all_nine_detectors_and_returns_one_corroborated_candidate(monkeypatch):
    specs = (
        ("detect_mtf_pullback", "MTF_PULLBACK"), ("detect_pullback", "PULLBACK"),
        ("detect_measured_move_breakout", "MEASURED_MOVE_BREAKOUT"),
        ("detect_breakout_retest", "BREAKOUT_RETEST"),
        ("detect_breakout_continuation", "BREAKOUT_CONTINUATION"),
        ("detect_liquidity_sweep", "LIQUIDITY_SWEEP_REVERSAL"),
        ("detect_momentum_expansion", "MOMENTUM_EXPANSION"),
        ("detect_mean_reversion", "MEAN_REVERSION"),
        ("detect_trend_continuation_soft", "TREND_CONTINUATION"),
    )
    called = []
    for method, name in specs:
        def _detector(*args, _name=name, **kwargs):
            called.append(_name)
            return True, {"family": _name, "detector": _name, "dist_atr": 0.2}
        monkeypatch.setattr(bot.OpportunityDetectors, method, staticmethod(_detector))
    result = bot.OpportunityRouter.classify({"symbol": "ROUTER-A85/USDT", "df_1d": object(),
                                              "df_4h": object(), "df_15m": object(), "df_5m": object()})
    assert len(called) == 9 and len(set(called)) == 9
    assert result and result["family"] == "MTF_PULLBACK"
    assert len(result["router_detector_hits"]) == 9
    assert result["router_confluence_group_count"] == 6
    assert "BREAKOUT" in result["router_confluence_groups"]


def test_a85_stablecoin_lane_is_opt_in_shadow_only_and_reports_economic_block():
    assert bot.CONFIG["STABLECOIN_MM_ENABLE"] is False
    assert bot.CONFIG["STABLECOIN_MM_MODE"] == "SHADOW"
    assert bot.StablecoinMarketMaker.live_is_armed() is False
    fee = float(bot.CONFIG["STABLECOIN_MM_FALLBACK_MAKER_FEE_RATE"])
    now_ms = int(time.time() * 1000)
    book = {"bids": [[0.9998, 2000.0]], "asks": [[1.0002, 2000.0]], "timestamp": now_ms}
    trades = [{"id": "a85-buy", "timestamp": now_ms - 100, "side": "buy",
               "price": 1.0002, "amount": 10.0}]
    eligible, reason, metrics = bot.StablecoinMarketMaker.assess_quote(book, trades, fee, now_ms=now_ms)
    assert not eligible and reason == "net_edge_below_floor"
    assert metrics["fee_cost_bps"] == pytest.approx(20.0)
    assert metrics["estimated_net_bps"] < metrics["required_net_bps"]
