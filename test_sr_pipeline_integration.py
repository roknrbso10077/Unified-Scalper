"""Offline, no-wire integration contract for final S/R targets.

This uses the production planner, geometry authority, PreSend gate, TradeState,
precision normalizer and lifecycle trace. All exchange-facing entry calls are
mocked/capture-only; the test cannot submit a real order or Telegram message.
"""
from __future__ import annotations

import asyncio
import contextlib
import io
import math
import os
import tempfile
import re
import unittest
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import numpy as np
import pandas as pd

os.environ["SCALPER_DB"] = os.path.join(tempfile.gettempdir(), f"v702-offline-tests-{os.getpid()}.db")
import main as bot


class CaptureExchange:
    """Deterministic tick/amount precision fake; contains no API credentials."""
    def __init__(self, tick: str = "0.1"):
        self.tick = Decimal(tick)
        self.buy_requests = []
        self.sell_requests = []

    def price_to_precision(self, symbol, price):
        x = Decimal(str(price))
        rounded = (x / self.tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * self.tick
        return format(rounded, "f")

    def amount_to_precision(self, symbol, qty):
        return f"{float(qty):.6f}"

    def market(self, symbol):
        return {"symbol": symbol, "limits": {"amount": {"min": 0.000001}, "cost": {"min": 1.0}}}

    async def create_market_buy_order(self, symbol, qty):
        # This method is a recording stub. It is never called by this test.
        self.buy_requests.append({"symbol": symbol, "qty": qty, "offline_capture_only": True})
        return {"id": "SIMULATED_ONLY"}


def _ohlcv(resistances=(106.0, 108.0), timestamps=None):
    n = 90
    close = np.full(n, 103.2, dtype=float)
    high = np.full(n, 103.8, dtype=float)
    low = np.full(n, 102.8, dtype=float)
    open_ = close - 0.05
    volume = np.full(n, 1000.0, dtype=float)
    # Separated confirmed swing highs; all are in the closed lookback window.
    ix_groups = ((36, 45, 54), (66, 75, 81))
    for level, indices in zip(resistances, ix_groups):
        for i in indices:
            high[i] = float(level)
    data = {"open": open_, "high": high, "low": low, "close": close, "volume": volume}
    if timestamps is not None:
        data["timestamp"] = np.asarray(timestamps, dtype=float)
    return pd.DataFrame(data)


class SRPipelineIntegration(unittest.TestCase):
    def setUp(self):
        self.exchange = CaptureExchange("0.1")
        self.symbol = "TEST/USDT"
        self.trace_id = "OFFLINE-SR-INTEGRATION"

    def _plan(self, df=None, resistance=(106.0, 108.0), entry=104.0, sl=103.0):
        if df is None:
            df = _ohlcv(resistance)
        return bot._v702_sr_aware_target_plan(
            entry=entry, sl=sl, tp1_rr=3.0, tp2_rr=5.0, tp3_rr=7.0,
            df_15m=df, family="PULLBACK", atr_hint=1.0,
        )

    def test_sr_target_geometry_survives_presend_queue_state_and_order_context(self):
        plan = self._plan()
        self.assertTrue(plan["ok"])
        self.assertEqual(plan["tp1_source"], "RESISTANCE")
        self.assertEqual(plan["tp2_source"], "RESISTANCE")
        self.assertLess(plan["tp1"], plan["resistance_levels"][0])
        self.assertLess(plan["tp2"], plan["resistance_levels"][1])

        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {"UNIFIED_LIVE_PILOT_ENABLE": "1", "UNIFIED_A55_LIVE_ARM": "1"}, clear=False))
            stack.enter_context(patch.object(bot, "_v702_position_manager_health_ok", return_value=True))
            stack.enter_context(patch.object(bot.EdgeGate, "live_permitted", return_value=(True, "offline_sr_test_recipe")))
            stack.enter_context(patch.object(bot.KillSwitch, "is_active", return_value=False))
            stack.enter_context(patch.object(bot.LiveStateMachine, "is_live_runnable", return_value=True))
            stack.enter_context(patch.object(bot, "_v563_entry_block_applies", return_value=False))
            stack.enter_context(patch.object(bot.ExchangeWatchdog, "is_tripped", return_value=False))
            stack.enter_context(patch.object(bot.FailedSendCircuitBreaker, "is_open", return_value=False))
            sizing = SimpleNamespace(
                status="OK", reject_reason="", notional_after_caps=75.0,
                balance_free_usdt=1000.0, fee_target_rescued=False,
                rescued_tp1=0.0, rescued_tp2=0.0, rescued_tp3=0.0,
                quantity_asset=0.721153,
            )
            stack.enter_context(patch.object(bot.SizingEngine, "decide", new=AsyncMock(return_value=sizing)))
            stack.enter_context(patch.object(bot.ExposureProtection, "check", return_value=(True, "ok")))
            stack.enter_context(patch.object(bot.SymbolExpectancyCooldown, "check", return_value=(True, "ok")))
            stack.enter_context(patch.object(bot.NewsBlackout, "check", return_value=(True, "ok")))
            stack.enter_context(patch.object(bot.LiquidityDepth, "check", new=AsyncMock(return_value=(True, "ok", 2.0))))

            gate_ok, gate_reason, sd = asyncio.run(bot.PreSendGate.evaluate(
                self.exchange, self.trace_id, self.symbol,
                plan["entry"], plan["sl"], plan["tp1"], plan["tp2"], plan["tp3"],
                strategy_mode="PULLBACK", strategy_score=92.0,
                strategy_style="SCALP", strategy_risk_factor=1.0,
                timeframe_profile="15M_5M", htf_strength=90.0, strategy_family="PULLBACK",
            ))
        self.assertTrue(gate_ok, gate_reason)
        self.assertIsNotNone(sd)

        final = bot._v702_normalize_final_geometry(
            exchange=self.exchange, symbol=self.symbol,
            entry=plan["entry"], sl=plan["sl"], tp1=plan["tp1"],
            tp2=plan["tp2"], tp3=plan["tp3"], sr_context=plan,
            notional=75.0, check_economics=True,
        )
        self.assertTrue(final["ok"], final)
        levels = {k: final[k] for k in ("entry", "sl", "tp1", "tp2", "tp3")}
        payload = {k: float(v) for k, v in levels.items()}

        # Actual post-fill re-anchor path, using a deterministic same-price fill.
        postfill = bot._v702_reanchor_targets_after_fill(
            exchange=self.exchange, symbol=self.symbol,
            planned_entry=levels["entry"], fill_entry=levels["entry"],
            planned_sl=levels["sl"], planned_tp1=levels["tp1"],
            planned_tp2=levels["tp2"], planned_tp3=levels["tp3"],
            sr_context=plan,
        )
        self.assertTrue(postfill["ok"], postfill)
        for k in levels:
            self.assertEqual(float(postfill[k]), float(levels[k]), k)

        trade = bot.TradeState(
            symbol=self.symbol, trace_id=self.trace_id,
            entry=levels["entry"], planned_entry=levels["entry"],
            effective_entry=levels["entry"], original_sl=levels["sl"],
            current_sl=levels["sl"], tp1=levels["tp1"], tp2=levels["tp2"],
            tp3=levels["tp3"], entry_filled=True, entry_fill_price=levels["entry"],
            entry_fill_amount=0.721153, position_size_asset=0.721153,
            remaining_position=0.721153, execution_mode="LIVE", is_paper=False,
        )
        state_levels = {k: float(getattr(trade, k if k != "sl" else "current_sl"))
                        for k in ("entry", "sl", "tp1", "tp2", "tp3")}
        self.assertEqual(payload, state_levels)

        # Spot market BUY endpoint accepts symbol + base quantity (not TP fields).
        # The immutable trace/request context carries the exact targets; the stop
        # order separately normalizes the same SL through the real precision path.
        qty_n, sl_request_px, err = bot.OrderExecutor._normalize_qty_price(
            self.exchange, self.symbol, trade.position_size_asset, trade.current_sl
        )
        self.assertIsNone(err)
        self.assertEqual(float(sl_request_px), levels["sl"])
        simulated_entry_request = {
            "method": "create_market_buy_order", "symbol": self.symbol,
            "quantity": float(qty_n), "trace_id": self.trace_id,
            "target_context": payload.copy(), "network_call": False,
        }
        self.assertEqual(simulated_entry_request["target_context"], payload)
        self.assertEqual(simulated_entry_request["target_context"], state_levels)
        self.assertEqual(self.exchange.buy_requests, [], "request context construction must not submit")

        # Exercise the production entry submitter against a local capture exchange.
        # Balance/fill reconciliation are replaced, but the production precision,
        # kill-switch and submit route still execute. The fake exchange has no network.
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(bot.KillSwitch, "is_active", return_value=False))
            stack.enter_context(patch.dict(bot.CONFIG, {"MAKER_FIRST_ENTRY_ENABLE": False}))
            stack.enter_context(patch.object(bot, "_v626_execution_balance_preflight", new=AsyncMock(return_value=(True, "offline_test_ok"))))
            stack.enter_context(patch.object(bot, "_v553_reconcile_buy_fill", new=AsyncMock(return_value=(None, levels["entry"], {"id":"SIMULATED_ONLY"}))))
            # Explicitly authorize the *offline capture test only*. Production defaults
            # remain monitor-only, and the capture exchange has no real network client.
            stack.enter_context(patch.dict(os.environ, {
                "UNIFIED_LIVE_PILOT_ENABLE": "1",
                "UNIFIED_A55_LIVE_ARM": "1",
                "UNIFIED_A19_DIAGNOSTIC_ONLY": "0",  # offline capture-only; no network exchange
            }))
            stack.enter_context(patch.dict(bot.ENV, {"MEXC_API_KEY": "OFFLINE_TEST_KEY", "MEXC_API_SECRET": "OFFLINE_TEST_SECRET"}))
            stack.enter_context(patch.object(bot.LiveStateMachine, "is_live_runnable", return_value=True))
            stack.enter_context(patch.object(bot, "_v702_position_manager_health_ok", return_value=True))
            stack.enter_context(patch.object(bot.EdgeGate, "live_permitted", return_value=(True, "offline_capture_recipe")))
            stack.enter_context(patch.object(bot.V702PortfolioDrawdownGuard, "authorize_entry", new=AsyncMock(return_value=(True, "offline_test_authorized", {"offline_capture_only": True}))))
            entry_ok, order_id, fill_px = asyncio.run(bot.OrderExecutor.submit_entry(
                self.exchange, self.symbol, trade.position_size_asset, levels["entry"],
                is_paper=False, trace_id=self.trace_id,
                intent_context={"family": "PULLBACK", "strategy_mode": "PULLBACK", "strategy_style": "SCALP", "timeframe_profile": "15M_5M", "htf_strength": 90.0},
            ))
        self.assertTrue(entry_ok)
        self.assertEqual(order_id, "SIMULATED_ONLY")
        self.assertEqual(float(fill_px), levels["entry"])
        self.assertEqual(len(self.exchange.buy_requests), 1)
        self.assertEqual(self.exchange.buy_requests[0]["symbol"], self.symbol)
        self.assertTrue(self.exchange.buy_requests[0].get("offline_capture_only", False))

        # Exercise the actual Telegram queue entrypoint with network delivery never
        # started. A unique JSON payload prevents digest compaction; the Telegram
        # network sender is a separate worker and is not called by enqueue().
        import json
        from collections import deque
        old_queue = list(bot.TelegramDispatcher._queue)
        old_queue_maxlen = bot.TelegramDispatcher._queue.maxlen
        old_recent = dict(bot.TelegramDispatcher._recent_enqueued_keys)
        old_callbacks = dict(bot.TelegramDispatcher._delivery_callbacks)
        msg = json.dumps({"trace_id":self.trace_id,"symbol":self.symbol,"targets":payload}, sort_keys=True)
        try:
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.dict(bot.CONFIG, {"TELEGRAM_ENABLED":True, "V702_R28_TELEGRAM_CONVERGENCE_ENABLE":False}))
                stack.enter_context(patch.dict(bot.ENV, {"TELEGRAM_TOKEN":"offline-test-token", "TELEGRAM_CHAT":"offline-test-chat"}))
                queued = asyncio.run(bot.TelegramDispatcher.enqueue(msg))
            self.assertTrue(queued)
            self.assertIn(msg, list(bot.TelegramDispatcher._queue))
            queued_payload = json.loads(next(x for x in reversed(bot.TelegramDispatcher._queue) if x == msg))
            self.assertEqual(queued_payload["targets"], payload)
            self.assertEqual(queued_payload["targets"], state_levels)
        finally:
            bot.TelegramDispatcher._queue = deque(old_queue, maxlen=old_queue_maxlen)
            bot.TelegramDispatcher._recent_enqueued_keys.clear()
            bot.TelegramDispatcher._recent_enqueued_keys.update(old_recent)
            bot.TelegramDispatcher._delivery_callbacks.clear()
            bot.TelegramDispatcher._delivery_callbacks.update(old_callbacks)

        # The exchange and Telegram workers were never started; only the mocked
        # OrderExecutor request and in-memory transport queue were exercised.

    def test_post_fill_buffer_consumption_uses_management_only_targets_below_physical_resistance(self):
        plan = self._plan()
        self.assertTrue(plan["ok"], plan)
        # The fill has moved close enough to the first resistance that the
        # standard buffered target can no longer remain above the actual fill.
        reanchored = bot._v702_reanchor_targets_after_fill(
            exchange=self.exchange, symbol=self.symbol,
            planned_entry=plan["entry"], fill_entry=105.9,
            planned_sl=plan["sl"], planned_tp1=plan["tp1"],
            planned_tp2=plan["tp2"], planned_tp3=plan["tp3"],
            sr_context=plan,
        )
        self.assertFalse(reanchored["ok"], reanchored)
        self.assertEqual(reanchored["reason"], "post_fill_tp1_no_room_before_resistance")

        emergency = bot._v702_post_fill_emergency_targets(
            exchange=self.exchange, symbol=self.symbol,
            planned_entry=plan["entry"], fill_entry=105.9,
            planned_sl=plan["sl"], planned_tp1=plan["tp1"],
            planned_tp2=plan["tp2"], planned_tp3=plan["tp3"],
            tp1_rr=3.0, tp2_rr=5.0, tp3_rr=7.0, sr_context=plan,
        )
        self.assertTrue(emergency["ok"], emergency)
        self.assertTrue(emergency["management_only"])
        self.assertFalse(emergency["hard_gate_bypass"])
        self.assertTrue(emergency["sr_buffer_exception"])
        self.assertLess(emergency["sl"], emergency["entry"])
        self.assertLess(emergency["entry"], emergency["tp1"])
        self.assertLess(emergency["tp1"], emergency["tp2"])
        self.assertLess(emergency["tp2"], emergency["tp3"])
        levels = plan["resistance_levels"]
        self.assertLessEqual(emergency["tp1"], levels[0] + 1e-9)
        self.assertLessEqual(emergency["tp2"], levels[1] + 1e-9)

    def test_close_resistance_can_fail_net_fee_floor_instead_of_bypassing_it(self):
        # Under R40 small-net accounting, 105.0 leaves enough gross distance to
        # pass the modeled 0.10% net floor; use truly close confirmed levels so
        # costs consume the edge and S/R cannot override the economic gate.
        plan = self._plan(resistance=(104.5, 105.0))
        self.assertTrue(plan["ok"])
        self.assertEqual(plan["tp1_source"], "RESISTANCE")
        final = bot._v702_normalize_final_geometry(
            exchange=self.exchange, symbol=self.symbol,
            entry=plan["entry"], sl=plan["sl"], tp1=plan["tp1"],
            tp2=plan["tp2"], tp3=plan["tp3"], sr_context=plan,
            notional=75.0, check_economics=True,
        )
        self.assertFalse(final["ok"])
        self.assertTrue(str(final["reason"]).startswith("fee_"), final)

    def test_missing_and_stale_sr_fall_back_without_fabricating_resistance(self):
        missing = self._plan(df=None)
        self.assertTrue(missing["ok"])
        missing_data = bot._v702_sr_aware_target_plan(
            entry=104.0, sl=103.0, tp1_rr=1.0, tp2_rr=2.0, tp3_rr=3.0,
            df_15m=None, family="PULLBACK", atr_hint=1.0,
        )
        self.assertEqual(missing_data["reason"], "sr_dataframe_unavailable")
        self.assertEqual(missing_data["tp1_source"], "EXIT_PROFILE_RR")

        stale = _ohlcv((106.0, 108.0), timestamps=np.full(90, 1_600_000_000.0))
        with patch.object(bot, "WALL_NOW", return_value=1_800_000_000.0):
            stale_plan = bot._v702_sr_aware_target_plan(
                entry=104.0, sl=103.0, tp1_rr=3.0, tp2_rr=5.0, tp3_rr=7.0,
                df_15m=stale, family="PULLBACK", atr_hint=1.0,
            )
        self.assertEqual(stale_plan["reason"], "sr_data_stale")
        self.assertEqual(stale_plan["tp1_source"], "EXIT_PROFILE_RR")

    def test_fee_rescue_cannot_cross_resistance_even_if_rr_improves(self):
        plan = self._plan()
        compatible, why = bot._v702_sr_target_rescue_compatible(
            entry=plan["entry"], tp1=106.0, tp2=108.5, context=plan,
        )
        self.assertFalse(compatible)
        self.assertIn("crosses_resistance", why)
        reject = bot._v702_normalize_final_geometry(
            exchange=self.exchange, symbol=self.symbol, entry=104.0, sl=103.0,
            tp1=106.0, tp2=108.5, tp3=111.0, sr_context=plan,
            notional=75.0, check_economics=False,
        )
        self.assertFalse(reject["ok"])
        self.assertTrue(str(reject["reason"]).startswith("sr_cap_after_precision"), reject)

    def test_precision_rounding_and_invalid_geometry_fail_closed(self):
        coarse = CaptureExchange("0.5")
        rounded_invalid = bot._v702_normalize_final_geometry(
            exchange=coarse, symbol=self.symbol, entry=104.0, sl=103.0,
            tp1=104.1, tp2=105.1, tp3=106.1, sr_context={},
            check_economics=False,
        )
        self.assertFalse(rounded_invalid["ok"])
        self.assertEqual(rounded_invalid["reason"], "rounded_risk_reward_order_invalid")

        invalid_sl = bot._v702_normalize_final_geometry(
            exchange=self.exchange, symbol=self.symbol, entry=104.0, sl=104.2,
            tp1=105.0, tp2=106.0, tp3=107.0, sr_context={}, check_economics=False,
        )
        self.assertFalse(invalid_sl["ok"])
        self.assertEqual(invalid_sl["reason"], "rounded_risk_reward_order_invalid")

        valid = bot._v702_normalize_final_geometry(
            exchange=self.exchange, symbol=self.symbol, entry=104.04, sl=103.04,
            tp1=105.94, tp2=107.94, tp3=111.04, sr_context={}, check_economics=False,
        )
        self.assertTrue(valid["ok"], valid)
        self.assertEqual(valid["entry"], 104.0)
        self.assertEqual(valid["sl"], 103.0)

    def test_pipeline_counters_are_unique_and_scope_labelled(self):
        metrics = bot.V702PipelineMetrics
        saved = {
            "_enabled": metrics._enabled, "_epoch_id": metrics._epoch_id,
            "_cycle_id": metrics._cycle_id, "_epoch_counts": metrics._epoch_counts,
            "_cycle_keys": metrics._cycle_keys, "_events": metrics._events,
            "_reasons": metrics._reasons, "_cycle_reasons": metrics._cycle_reasons,
            "_last_block": metrics._last_block,
        }
        stats_keys = [k for k in bot.STATS if k.startswith("v702_pipeline_")]
        stats_snapshot = {k: bot.STATS[k] for k in stats_keys}
        try:
            metrics.begin_live_epoch()
            cycle = metrics._cycle()
            key = f"{cycle}|TEST/USDT|PULLBACK|TEST_ENGINE|stable-candidate"
            metrics.record("DISCOVERY", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.record("DISCOVERY", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.record("RANKED", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.record("PREQUAL_SEEN", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.record("PREQUAL_PASS", key, symbol="TEST/USDT", family="PULLBACK")
            rejected_key = f"{cycle}|REJECTED/USDT|PULLBACK|TEST_ENGINE|stable-candidate"
            metrics.record("PREQUAL_SEEN", rejected_key, symbol="REJECTED/USDT", family="PULLBACK")
            metrics.record("PREQUAL_REJECT", rejected_key, symbol="REJECTED/USDT", family="PULLBACK")
            metrics.record("SELECTED", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.record("BUILDER_ENTERED", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.record("SCORE_PASS", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.record("PRESEND_PASS", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.record("QUEUED", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.record("TELEGRAM_ENQUEUED", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.record("EXECUTION_ATTEMPT", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.record("ORDER_ACCEPTED", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.record("TRADE_STATE_CREATED", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.record("NATIVE_SL_UNVERIFIED", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.record("PROTECTED", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.record("PROTECTION_FAILED", key, symbol="TEST/USDT", family="PULLBACK")
            metrics.reject("TRACE", "TEST/USDT", "liquidity", "below_tier", "prequal", {"root":"LIQUIDITY"})
            snap = metrics.snapshot()
            self.assertEqual(snap["scope"], "LIVE_EPOCH_UNIQUE_CANDIDATE_STAGES")
            self.assertEqual(snap["cycle_counts"]["DISCOVERY"], 1)
            self.assertEqual(snap["cycle_counts"]["PREQUAL_SEEN"], 2)
            self.assertEqual(snap["cycle_counts"]["PREQUAL_REJECT"], 1)
            self.assertEqual(snap["cycle_counts"]["PREQUAL_PASS"], 1)
            self.assertEqual(snap["cycle_counts"]["PROTECTED"], 1)
            self.assertEqual(snap["cycle_counts"]["NATIVE_SL_UNVERIFIED"], 1)
            self.assertEqual(snap["cycle_counts"]["PROTECTION_FAILED"], 1)
            self.assertEqual(snap["top_rejections"][0][0], "prequal:below_tier")
            self.assertIn("NATIVE_SL_UNVERIFIED", metrics.digest_line())
            self.assertIn("PRE_REJ", metrics.digest_line())
            self.assertIn("PROT_FAIL", metrics.digest_line())
            line = metrics.digest_line()
            self.assertIn("PIPELINE[CYCLE]", line)
            self.assertIn("bypass=0", line)
        finally:
            for key, value in saved.items():
                setattr(metrics, key, value)
            for key in [k for k in bot.STATS if k.startswith("v702_pipeline_")]:
                bot.STATS.pop(key, None)
            bot.STATS.update(stats_snapshot)

    def test_production_builder_keeps_the_same_final_geometry_authority(self):
        from pathlib import Path
        src = Path(bot.__file__).read_text(encoding="utf-8")
        class_start = src.find("class SignalBuilder")
        method_start = src.find("async def build_and_route", class_start)
        next_class = re.search(r"\nclass [A-Za-z_]", src[method_start:])
        method_end = method_start + next_class.start() if next_class else len(src)
        builder = src[method_start:method_end]
        self.assertIn("_v702_sr_aware_target_plan", builder)
        self.assertIn("_v702_normalize_final_geometry", builder)
        self.assertIn("V702_FINAL_TARGET_GEOMETRY_LOCKED", builder)
        self.assertIn("_v702_reanchor_targets_after_fill", src)
        self.assertIn("TelegramDispatcher.enqueue", src)
        self.assertIn("OrderExecutor.submit_entry", src)
        self.assertIn("ACTIVE_TRADES[symbol] = trade", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
