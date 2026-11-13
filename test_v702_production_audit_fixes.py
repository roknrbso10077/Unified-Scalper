from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
import os
import subprocess
import sys
from collections import defaultdict, deque
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock

import pandas as pd
import pytest
import main as bot


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
