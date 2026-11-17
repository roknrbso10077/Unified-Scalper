from __future__ import annotations

from contextlib import closing

import asyncio
import os
import sqlite3
import tempfile
import time
import unittest
import numpy as np
import pandas as pd
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ["SCALPER_DB"] = os.path.join(tempfile.gettempdir(), f"v702-offline-tests-{os.getpid()}.db")
import main as bot


class ProductionGuardrailTests(unittest.TestCase):
    def test_peak_drawdown_guard_latches_and_survives_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            db = str(Path(td) / "guard.db")
            with patch.dict(bot.CONFIG, {"DB_PATH": db, "V702_PORTFOLIO_DRAWDOWN_LIMIT_PCT": 5.0}):
                first = bot.V702PortfolioDrawdownGuard.evaluate_equity(bot.__dict__, 1000.0)
                small_dd = bot.V702PortfolioDrawdownGuard.evaluate_equity(bot.__dict__, 970.0)
                breach = bot.V702PortfolioDrawdownGuard.evaluate_equity(bot.__dict__, 949.0)
                recovery = bot.V702PortfolioDrawdownGuard.evaluate_equity(bot.__dict__, 1000.0)
            self.assertTrue(first["allowed"])
            self.assertTrue(small_dd["allowed"])
            self.assertAlmostEqual(breach["drawdown_pct"], 5.1, places=6)
            self.assertFalse(breach["allowed"])
            self.assertEqual(breach["halt_reason"], "peak_drawdown_5.1000_pct_ge_5.0000_pct")
            self.assertFalse(recovery["allowed"], "breach must remain latched after equity recovers")
            with closing(sqlite3.connect(db)) as conn:
                self.assertEqual(conn.execute("SELECT halted FROM v702_portfolio_drawdown_state").fetchone()[0], 1)

    def test_pipeline_digest_exposes_monitor_only_entry_policy(self):
        snapshot = {
            "enabled": True, "cycle_counts": {}, "last_block": {}, "cycle_id": 1,
            "cycle_reject_count": 0, "epoch_reject_count": 0,
            "top_rejections_cycle": [], "top_rejections_epoch": [],
        }
        with patch.object(bot.V702PipelineMetrics, "snapshot", return_value=snapshot), \
             patch.dict(bot.STATS, {"v702_runtime_entry_policy": "MONITOR_ONLY_NO_NEW_BUYS"}):
            line = bot.V702PipelineMetrics.digest_line()
        self.assertIn("entry_policy=MONITOR_ONLY_NO_NEW_BUYS", line)

    def test_forced_monitor_only_blocks_live_entry_before_exchange_order_path(self):
        async def run():
            with patch.dict(os.environ, {"UNIFIED_ALLOW_LIVE_TRADING": "", "UNIFIED_LIVE_PILOT_ENABLE": "0", "UNIFIED_A19_DIAGNOSTIC_ONLY": "0"}):
                fake = SimpleNamespace()
                result = await bot._V702_R39_SUBMIT_ENTRY_GUARD(fake, "BTC/USDT", 1.0, 100.0, is_paper=False)
                return result
        result = asyncio.run(run())
        self.assertEqual(result, (False, None, 0.0))
        self.assertGreaterEqual(int(bot.STATS.get("v702_monitor_only_entry_blocks", 0)), 1)

    def test_user_requested_live_pilot_activates_only_with_credentials_and_hard_invariants(self):
        with patch.dict(os.environ, {"UNIFIED_ALLOW_LIVE_TRADING": "", "UNIFIED_LIVE_PILOT_ENABLE": "1", "UNIFIED_A55_LIVE_ARM": "1", "UNIFIED_A19_DIAGNOSTIC_ONLY": "0"}), \
             patch.dict(bot.ENV, {"MEXC_API_KEY": "OFFLINE_TEST_KEY", "MEXC_API_SECRET": "OFFLINE_TEST_SECRET"}), \
             patch.dict(bot.CONFIG, {"V702_LIVE_PILOT_ENABLE": True}), \
             patch.object(bot.LiveStateMachine, "is_live_runnable", return_value=True), \
             patch.object(bot, "_v702_position_manager_health_ok", return_value=True), \
             patch.object(bot.KillSwitch, "is_active", return_value=False), \
             patch.dict(bot.LIVE_ENTRIES_BLOCKED, {"active": False, "reason": None, "where": None, "since": None}):
            monitor_only = bot._V702_R39_REFRESH_ENTRY_MODE()
            self.assertFalse(monitor_only)
            self.assertEqual(bot.STATS.get("v702_runtime_entry_policy"), "USER_REQUESTED_LIVE_PILOT")
            self.assertTrue(bot.STATS.get("v702_spot_long_only_invariants_ok"))

    def test_user_requested_live_pilot_reaches_canonical_order_executor_with_mock_exchange(self):
        async def run():
            exchange = bot._V516MockExchange("")
            with patch.dict(os.environ, {"UNIFIED_ALLOW_LIVE_TRADING": "", "UNIFIED_LIVE_PILOT_ENABLE": "1", "UNIFIED_A55_LIVE_ARM": "1"}), \
                 patch.dict(bot.ENV, {"MEXC_API_KEY": "OFFLINE_TEST_KEY", "MEXC_API_SECRET": "OFFLINE_TEST_SECRET"}), \
                 patch.dict(bot.CONFIG, {"V702_LIVE_PILOT_ENABLE": True, "ENABLE_LIVE_TRADING": True,
                                         "PAPER_TRADING_MODE": False, "MAKER_FIRST_ENTRY_ENABLE": False}), \
                 patch.object(bot, "_v702_live_buy_possible", return_value=True), \
                 patch.object(bot, "_v702_position_manager_health_ok", return_value=True), \
                 patch.object(bot.LiveStateMachine, "is_live_runnable", return_value=True), \
                 patch.object(bot.KillSwitch, "is_active", return_value=False), \
                 patch.dict(bot.LIVE_ENTRIES_BLOCKED, {"active": False, "reason": None, "where": None, "since": None}), \
                 patch.object(bot.V702PortfolioDrawdownGuard, "authorize_entry", new=AsyncMock(
                     return_value=(True, "portfolio_drawdown_ok", {"equity_valuation_ok": True}))) as authorization:
                # Prove an absent diagnostic variable does not silently block the user-requested pilot.
                os.environ.pop("UNIFIED_A19_DIAGNOSTIC_ONLY", None)
                result = await bot._V702_R39_SUBMIT_ENTRY_GUARD(
                    exchange, "TEST/USDT", 0.1, 100.0, is_paper=False, trace_id="A21-DEFAULT-LIVE-PILOT-MOCK")
                return result, exchange, authorization
        result, exchange, authorization = asyncio.run(run())
        self.assertTrue(result[0], result)
        self.assertEqual(result[1], "MOCK-E-1")
        self.assertEqual(len(exchange.orders), 1)
        self.assertEqual(next(iter(exchange.orders.values())).get("side"), "buy")
        authorization.assert_awaited_once()
        self.assertIs(bot.STATS.get("v702_a19_diagnostic_only_effective"), False)

    def test_live_pilot_authorization_uses_canonical_policy_without_legacy_token(self):
        class FakeExchange:
            async def fetch_balance(self):
                return {"total": {"USDT": 100.0}}
            async def fetch_tickers(self):
                return {}

        async def run(db_path):
            with patch.dict(os.environ, {"UNIFIED_ALLOW_LIVE_TRADING": "", "UNIFIED_LIVE_PILOT_ENABLE": "1", "UNIFIED_A55_LIVE_ARM": "1", "UNIFIED_A19_DIAGNOSTIC_ONLY": "0"}), \
                 patch.dict(bot.ENV, {"MEXC_API_KEY": "OFFLINE_TEST_KEY", "MEXC_API_SECRET": "OFFLINE_TEST_SECRET"}), \
                 patch.dict(bot.CONFIG, {"DB_PATH": db_path, "V702_LIVE_PILOT_ENABLE": True,
                                         "ENABLE_LIVE_TRADING": True, "PAPER_TRADING_MODE": False}), \
                 patch.object(bot.LiveStateMachine, "is_live_runnable", return_value=True), \
                 patch.object(bot, "_v702_position_manager_health_ok", return_value=True), \
                 patch.object(bot.KillSwitch, "is_active", return_value=False), \
                 patch.dict(bot.LIVE_ENTRIES_BLOCKED, {"active": False, "reason": None, "where": None, "since": None}):
                return await bot.V702PortfolioDrawdownGuard.authorize_entry(
                    bot.__dict__, FakeExchange(), "BTC/USDT")

        with tempfile.TemporaryDirectory() as td:
            allowed, reason, details = asyncio.run(run(str(Path(td) / "pilot.db")))
        self.assertTrue(allowed, (reason, details))
        self.assertEqual(reason, "portfolio_drawdown_ok")
        self.assertTrue(details.get("equity_valuation_ok"))

    def test_emergency_off_blocks_authorize_entry_even_with_pilot_and_legacy_token(self):
        class NeverCalledExchange:
            async def fetch_balance(self):
                raise AssertionError("forced-off must block before account valuation")
            async def fetch_tickers(self):
                raise AssertionError("forced-off must block before ticker calls")

        async def run():
            with patch.dict(os.environ, {"UNIFIED_ALLOW_LIVE_TRADING": "I_ACCEPT_LIVE_RISK", "UNIFIED_LIVE_PILOT_ENABLE": "0", "UNIFIED_A19_DIAGNOSTIC_ONLY": "0"}), \
                 patch.dict(bot.ENV, {"MEXC_API_KEY": "OFFLINE_TEST_KEY", "MEXC_API_SECRET": "OFFLINE_TEST_SECRET"}), \
                 patch.dict(bot.CONFIG, {"V702_LIVE_PILOT_ENABLE": True, "ENABLE_LIVE_TRADING": True,
                                         "PAPER_TRADING_MODE": False}):
                return await bot.V702PortfolioDrawdownGuard.authorize_entry(
                    bot.__dict__, NeverCalledExchange(), "BTC/USDT")
        allowed, reason, details = asyncio.run(run())
        self.assertFalse(allowed)
        self.assertEqual(reason, "monitor_only_entry_policy_or_invariants")
        self.assertTrue(details.get("monitor_only"))
        self.assertTrue(details.get("forced_off"))

    def test_forced_off_wins_even_when_legacy_live_token_is_present(self):
        with patch.dict(os.environ, {"UNIFIED_ALLOW_LIVE_TRADING": "I_ACCEPT_LIVE_RISK", "UNIFIED_LIVE_PILOT_ENABLE": "0", "UNIFIED_A19_DIAGNOSTIC_ONLY": "0"}), \
             patch.dict(bot.ENV, {"MEXC_API_KEY": "OFFLINE_TEST_KEY", "MEXC_API_SECRET": "OFFLINE_TEST_SECRET"}), \
             patch.dict(bot.CONFIG, {"V702_LIVE_PILOT_ENABLE": True}):
            monitor_only = bot._V702_R39_REFRESH_ENTRY_MODE()
            self.assertTrue(monitor_only)
            self.assertEqual(bot.STATS.get("v702_runtime_entry_policy"), "MONITOR_ONLY_NO_NEW_BUYS")

    def test_peak_drawdown_authorization_blocks_entry_even_after_explicit_opt_in(self):
        async def run():
            with patch.dict(os.environ, {"UNIFIED_ALLOW_LIVE_TRADING": "I_ACCEPT_LIVE_RISK", "UNIFIED_LIVE_PILOT_ENABLE": "1", "UNIFIED_A55_LIVE_ARM": "1", "UNIFIED_A19_DIAGNOSTIC_ONLY": "0"}), \
                 patch.dict(bot.ENV, {"MEXC_API_KEY": "OFFLINE_TEST_KEY", "MEXC_API_SECRET": "OFFLINE_TEST_SECRET"}), \
                 patch.dict(bot.CONFIG, {"V702_LIVE_PILOT_ENABLE": True}), \
                 patch.object(bot, "_v702_live_buy_possible", return_value=True), \
                 patch.object(bot, "_v702_position_manager_health_ok", return_value=True), \
                 patch.object(bot.LiveStateMachine, "is_live_runnable", return_value=True), \
                 patch.object(bot.KillSwitch, "is_active", return_value=False), \
                 patch.dict(bot.LIVE_ENTRIES_BLOCKED, {"active": False, "reason": None, "where": None, "since": None}), \
                 patch.object(bot.V702PortfolioDrawdownGuard, "authorize_entry", new=AsyncMock(
                     return_value=(False, "portfolio_peak_drawdown_latched", {"drawdown_pct": 5.1}))) as authorization:
                result = await bot._V702_R39_SUBMIT_ENTRY_GUARD(object(), "BTC/USDT", 1.0, 100.0, is_paper=False)
                return result, authorization
        result, authorization = asyncio.run(run())
        self.assertEqual(result, (False, None, 0.0))
        authorization.assert_awaited_once()
        self.assertGreaterEqual(int(bot.STATS.get("v702_portfolio_drawdown_entry_blocks", 0)), 1)

    def test_account_valuation_unknown_asset_fails_closed(self):
        class FakeExchange:
            async def fetch_balance(self):
                return {"total": {"USDT": 100.0, "UNPRICED": 1.0}}
            async def fetch_tickers(self, symbols=None):
                return {"BTC/USDT": {"last": 100000.0}}
        async def run():
            return await bot.V702PortfolioDrawdownGuard.equity_usdt(FakeExchange())
        equity, reason = asyncio.run(run())
        self.assertIsNone(equity)
        self.assertEqual(reason, "unpriced_asset:UNPRICED")

    def test_non_usdt_stablecoin_equity_uses_market_price_not_assumed_par(self):
        class FakeExchange:
            async def fetch_balance(self):
                return {"total": {"USDT": 100.0, "USDC": 10.0}}
            async def fetch_tickers(self, symbols=None):
                return {"USDC/USDT": {"last": 0.98}}
        equity, reason = asyncio.run(bot.V702PortfolioDrawdownGuard.equity_usdt(FakeExchange()))
        self.assertEqual(reason, "ok")
        self.assertAlmostEqual(equity, 109.8, places=6)

    def test_drawdown_latch_reset_persists_operator_reason(self):
        class FakeExchange:
            async def fetch_balance(self):
                return {"total": {"USDT": 949.0}}
            async def fetch_tickers(self):
                return {}
        with tempfile.TemporaryDirectory() as td:
            db = str(Path(td) / "reset.db")
            with patch.dict(bot.CONFIG, {"DB_PATH": db, "V702_PORTFOLIO_DRAWDOWN_LIMIT_PCT": 5.0}):
                bot.V702PortfolioDrawdownGuard.evaluate_equity(bot.__dict__, 1000.0)
                bot.V702PortfolioDrawdownGuard.evaluate_equity(bot.__dict__, 949.0)
                refused = asyncio.run(bot.V702PortfolioDrawdownGuard.reset_latch(bot.__dict__, FakeExchange(), "short"))
                reset = asyncio.run(bot.V702PortfolioDrawdownGuard.reset_latch(
                    bot.__dict__, FakeExchange(), "operator checked account equity"))
            self.assertFalse(refused["ok"])
            self.assertTrue(reset["ok"])
            with closing(sqlite3.connect(db)) as conn:
                row = conn.execute("SELECT halted,last_reset_reason FROM v702_portfolio_drawdown_state").fetchone()
            self.assertEqual(row, (0, "operator checked account equity"))

    def test_shadow_stores_baseline_and_only_relevant_counterfactual_rejects(self):
        with tempfile.TemporaryDirectory() as td:
            db = str(Path(td) / "shadow.db")
            shadow = bot.V702ExpansionShadow(bot.__dict__)
            candidate = lambda symbol, ts, tier="MID": SimpleNamespace(
                symbol=symbol, family="BREAKOUT", strategy_mode="BREAKOUT", engine_id="breakout",
                generated_at_ms=ts, entry_ref=100.0, sl_price=98.0, tp1_rr=1.0, tp2_rr=2.0, tp3_rr=3.0,
                engine_score=0.8, features_snapshot={"liquidity_tier": tier, "htf_score": 76.0, "quote_volume_usdt": 500000.0}
            )
            with patch.dict(bot.CONFIG, {"DB_PATH": db}):
                baseline = candidate("BTC/USDT", 10001, "LARGE")
                mid_rejected = candidate("AAA/USDT", 10002, "MID")
                unrelated_reject = candidate("BBB/USDT", 10003, "MICRO")
                shadow.record_prequal(SimpleNamespace(candidate=baseline, score=85.0), {}, (True, "ok"))
                shadow.record_prequal(SimpleNamespace(candidate=mid_rejected, score=80.0), {}, (False, "liquidity.tier_not_accepted"))
                shadow.record_prequal(SimpleNamespace(candidate=unrelated_reject, score=80.0), {}, (False, "structure_missing"))
                inserted = shadow._flush_sync()
                report = shadow.report()
            self.assertEqual(inserted, 2)
            self.assertEqual(report["total_samples"], 2)
            self.assertEqual(report["scope"], "PREQUAL_ONLY_COUNTERFACTUAL_NOT_FULL_BUILDER_ACCEPTANCE")
            self.assertIn("BASELINE_PASS", report["lanes"])
            self.assertIn("MID_TIER_COUNTERFACTUAL", report["lanes"])
            self.assertNotIn("structure_missing", report["lanes"])
            self.assertFalse(report["live_policy_changed"])

    def test_shadow_dedupe_index_stays_bounded_and_consistent(self):
        from collections import deque
        shadow = bot.V702ExpansionShadow(bot.__dict__)
        shadow._dedupe_order = deque(f"old-{i}" for i in range(20000))
        shadow._dedupe = set(shadow._dedupe_order)
        candidate = SimpleNamespace(
            symbol="AAA/USDT", family="BREAKOUT", strategy_mode="BREAKOUT", engine_id="breakout",
            generated_at_ms=int(time.time() * 1000), entry_ref=100.0, sl_price=98.0,
            tp1_rr=1.0, tp2_rr=2.0, tp3_rr=3.0, engine_score=.8,
            features_snapshot={"liquidity_tier": "LARGE", "htf_score": 80.0, "quote_volume_usdt": 5_000_000.0},
        )
        shadow.record_prequal(SimpleNamespace(candidate=candidate, score=80.0), {}, (True, "ok"))
        self.assertEqual(len(shadow._dedupe), 20000)
        self.assertEqual(len(shadow._dedupe_order), 20000)
        self.assertEqual(set(shadow._dedupe_order), shadow._dedupe)
        self.assertNotIn("old-0", shadow._dedupe)
        self.assertEqual(len(shadow._pending), 1)

    def test_shadow_ohlcv_tracker_marks_same_bar_sl_target_ambiguous(self):
        with tempfile.TemporaryDirectory() as td:
            db = str(Path(td) / "shadow.db")
            shadow = bot.V702ExpansionShadow(bot.__dict__)
            now = time.time()
            created = now - 180
            last_bar = int(created // 60) * 60000
            sample_id = "ambiguous-test"
            with patch.dict(bot.CONFIG, {"DB_PATH": db, "V702_CF_SHADOW_SLIPPAGE_PCT": 0.1}):
                conn = shadow._connect()
                conn.execute(f"""INSERT INTO {shadow.TABLE}
                    (sample_id,created_ts,symbol,family,lane,source_reason,entry,sl,tp1,tp2,tp3,risk,status,last_bar_ts,updated_ts)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (sample_id, created, "BTC/USDT", "BREAKOUT", "BASELINE_PASS", "ok", 100.0, 98.0, 102.0, 104.0, 106.0, 2.0, "OPEN", last_bar, now))
                conn.commit()
                row = conn.execute(f"SELECT * FROM {shadow.TABLE} WHERE sample_id=?", (sample_id,)).fetchone()
                conn.close()
                bar_ts = last_bar + 60000
                # Both SL and TP1 are touched inside the same closed candle.
                bar = [bar_ts, 100.0, 103.0, 97.0, 101.0, 1000.0]
                shadow._track_sync_rows([(row, [bar])])
                with closing(sqlite3.connect(db)) as conn:
                    final = conn.execute(f"SELECT status,final_outcome,net_r FROM {shadow.TABLE} WHERE sample_id=?", (sample_id,)).fetchone()
            self.assertEqual(final[0], "CLOSED")
            self.assertEqual(final[1], "SL")
            self.assertIsNotNone(final[2])
            self.assertLess(final[2], 0.0)

    def test_expansion_shadow_rejects_forbidden_assets_and_preserves_unknown_spread(self):
        shadow = bot.V702ExpansionShadow(bot.__dict__)
        forbidden = SimpleNamespace(
            symbol="BNB/USDT", family="BREAKOUT", strategy_mode="BREAKOUT",
            generated_at_ms=1700000000001, entry_ref=100.0, sl_price=98.0,
            tp1_rr=1.0, tp2_rr=2.0, tp3_rr=3.0, engine_score=.8,
            features_snapshot={"liquidity_tier": "LARGE"},
        )
        missing_spread = SimpleNamespace(
            symbol="SAFE/USDT", family="BREAKOUT", strategy_mode="BREAKOUT",
            generated_at_ms=1700000000002, entry_ref=100.0, sl_price=98.0,
            tp1_rr=1.0, tp2_rr=2.0, tp3_rr=3.0, engine_score=.8,
            features_snapshot={"liquidity_tier": "LARGE"},
        )
        measured_spread = SimpleNamespace(
            symbol="MEASURED/USDT", family="BREAKOUT", strategy_mode="BREAKOUT",
            generated_at_ms=1700000000003, entry_ref=100.0, sl_price=98.0,
            tp1_rr=1.0, tp2_rr=2.0, tp3_rr=3.0, engine_score=.8,
            features_snapshot={"liquidity_tier": "LARGE", "spread_pct": 0.12},
        )
        shadow.record_prequal(forbidden, {}, (True, "ok"))
        shadow.record_prequal(missing_spread, {}, (True, "ok"))
        shadow.record_prequal(measured_spread, {}, (True, "ok"))
        queued = list(shadow._pending)
        self.assertEqual(len(queued), 2)
        self.assertEqual(queued[0][2], "SAFE/USDT")
        self.assertIsNone(queued[0][11], "unmeasured spread must remain NULL, not zero")
        self.assertEqual(queued[1][2], "MEASURED/USDT")
        self.assertAlmostEqual(queued[1][11], 0.12)

    def test_expansion_shadow_gap_is_ambiguous_and_has_no_net_r(self):
        with tempfile.TemporaryDirectory() as td:
            db = str(Path(td) / "shadow-gap.db")
            shadow = bot.V702ExpansionShadow(bot.__dict__)
            now = time.time()
            created = now - 240
            last_bar = int(created // 60) * 60000
            with patch.dict(bot.CONFIG, {"DB_PATH": db}):
                conn = shadow._connect()
                conn.execute(f"""INSERT INTO {shadow.TABLE}
                    (sample_id,created_ts,symbol,family,lane,source_reason,entry,sl,tp1,tp2,tp3,risk,status,last_bar_ts,updated_ts)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    ("gap-test", created, "SAFE/USDT", "BREAKOUT", "BASELINE_PASS", "ok",
                     100.0, 98.0, 102.0, 104.0, 106.0, 2.0, "OPEN", last_bar, now))
                conn.commit()
                row = conn.execute(f"SELECT * FROM {shadow.TABLE} WHERE sample_id=?", ("gap-test",)).fetchone()
                conn.close()
                # A two-minute jump skips at least one closed 1m candle.
                gap_bar = [last_bar + 120000, 100.0, 101.0, 99.0, 100.5, 1000.0]
                shadow._track_sync_rows([(row, [gap_bar])])
                with closing(sqlite3.connect(db)) as conn:
                    result = conn.execute(
                        f"SELECT final_outcome,net_r FROM {shadow.TABLE} WHERE sample_id=?", ("gap-test",)
                    ).fetchone()
            self.assertEqual(result[0], "AMBIGUOUS_DATA_GAP")
            self.assertIsNone(result[1])

    def test_expansion_shadow_be_and_cost_model_match_live_fee_policy(self):
        with tempfile.TemporaryDirectory() as td:
            db = str(Path(td) / "shadow-be.db")
            shadow = bot.V702ExpansionShadow(bot.__dict__)
            now = time.time()
            created = now - 180
            last_bar = int(created // 60) * 60000
            config_patch = {"DB_PATH": db, "TAKER_FEE_PCT": 0.10, "ROUNDTRIP_FEE_MULT": 2.0,
                            "V702_SMALL_NET_SPREAD_FALLBACK_PCT": 0.15,
                            "V702_SMALL_NET_SLIPPAGE_PER_SIDE_PCT": 0.05,
                            "TP1_EXIT_PCT": 0.5, "ENABLE_RUNNER_MODE": True}
            with patch.dict(bot.CONFIG, config_patch):
                conn = shadow._connect()
                conn.execute(f"""INSERT INTO {shadow.TABLE}
                    (sample_id,created_ts,symbol,family,lane,source_reason,entry,sl,tp1,tp2,tp3,risk,status,tp1_hit,last_bar_ts,updated_ts)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    ("be-test", created, "SAFE/USDT", "BREAKOUT", "BASELINE_PASS", "ok",
                     100.0, 98.0, 102.0, 104.0, 106.0, 2.0, "OPEN", 1, last_bar, now))
                conn.commit()
                row = conn.execute(f"SELECT * FROM {shadow.TABLE} WHERE sample_id=?", ("be-test",)).fetchone()
                conn.close()
                # Existing TP1 is already booked; this closed candle then tags SL.
                sl_bar = [last_bar + 60000, 100.0, 101.0, 97.0, 99.0, 1000.0]
                shadow._track_sync_rows([(row, [sl_bar])])
                with closing(sqlite3.connect(db)) as conn:
                    outcome = conn.execute(
                        f"SELECT final_outcome,net_r FROM {shadow.TABLE} WHERE sample_id=?", ("be-test",)
                    ).fetchone()
            self.assertEqual(outcome[0], "SL_AFTER_TARGET")
            self.assertIsNotNone(outcome[1])
            # 0.45% all-in friction is charged once against entry notional:
            # gross 0.55R - (0.45% * 100 / 2) = 0.325R.
            self.assertGreater(outcome[1], 0.32)
            self.assertLess(outcome[1], 0.33)

    def test_expansion_shadow_ohlcv_uses_safe_research_api_wrapper(self):
        async def run():
            with tempfile.TemporaryDirectory() as td:
                db = str(Path(td) / "shadow-safe-api.db")
                shadow = bot.V702ExpansionShadow(bot.__dict__)
                now = time.time()
                created = now - 120
                last_bar = int(now // 60) * 60000 - 60000
                with patch.dict(bot.CONFIG, {"DB_PATH": db}):
                    conn = shadow._connect()
                    conn.execute(f"""INSERT INTO {shadow.TABLE}
                        (sample_id,created_ts,symbol,family,lane,source_reason,entry,sl,tp1,tp2,tp3,risk,status,last_bar_ts,updated_ts)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        ("safe-api-test", created, "SAFE/USDT", "BREAKOUT", "BASELINE_PASS", "ok",
                         100.0, 98.0, 102.0, 104.0, 106.0, 2.0, "OPEN", last_bar, now))
                    conn.commit(); conn.close()
                    row = shadow._fetch_open_rows_sync(1)[0]
                    calls = []
                    class FakeExchange:
                        async def fetch_ohlcv(self, symbol, timeframe="1m", since=None, limit=120):
                            calls.append(("fetch", symbol, timeframe, since, limit))
                            return []
                    async def safe_api_call(label, factory, *, retry_safe=False):
                        calls.append(("safe", label, retry_safe))
                        return await factory()
                    shadow.ns["safe_api_call"] = safe_api_call
                    shadow._fetch_open_rows_sync = lambda limit: [row]
                    await shadow._poll_once(FakeExchange())
                    return calls
        calls = asyncio.run(run())
        self.assertEqual(calls[0][0], "safe")
        self.assertTrue(calls[0][1].startswith("knowledge_ohlcv_expansion_"))
        self.assertTrue(calls[0][2])
        self.assertEqual(calls[1][0], "fetch")

    def test_expansion_shadow_is_disabled_by_default_but_code_is_available(self):
        self.assertFalse(bool(bot.CONFIG.get("V702_EXPANSION_SHADOW_ENABLE", False)))
        self.assertTrue(callable(bot.__dict__.get("V702ExpansionShadow")))
        self.assertTrue(bool(bot.__dict__.get("_V702_R39_GUARDRAILS_INSTALLED")))

    def test_hunter_alert_limit_is_hard_capped_at_three_per_minute(self):
        hunter = bot.OpportunityHunter
        old_window_start, old_count, old_pending = hunter._alert_window_start, hunter._alert_window_count, set(hunter._alert_pending)
        async def no_delivery(cls, row, state, alert_token=""):
            return None
        try:
            hunter._alert_window_start = bot.WALL_NOW()
            hunter._alert_window_count = 0
            hunter._alert_pending.clear()
            with patch.dict(bot.CONFIG, {
                "V702_OPPORTUNITY_HUNTER_ENABLE": True,
                "V702_OPPORTUNITY_HUNTER_TELEGRAM_ENABLE": True,
                "TELEGRAM_ENABLED": True,
                "V702_OPPORTUNITY_HUNTER_MAX_ALERTS_PER_MINUTE": 999,
            }), patch.object(hunter, "_deliver_alert", new=classmethod(no_delivery)):
                async def submit():
                    accepted = [hunter._queue_alert({"opportunity_id": f"cap-{i}", "status": "CONFIRMED",
                                                     "confirmation_type": "CLOSED_BAR_BREAKOUT"}, "CONFIRMED") for i in range(4)]
                    await asyncio.sleep(0)
                    return accepted
                accepted = asyncio.run(submit())
            self.assertEqual(accepted, [True, True, True, False])
        finally:
            hunter._alert_window_start = old_window_start
            hunter._alert_window_count = old_count
            hunter._alert_pending.clear()
            hunter._alert_pending.update(old_pending)

    def test_complete_async_builder_reaches_monitor_only_submit_barrier_without_order_wire(self):
        """Exercise Builder→score→target lock→queue→entry guard with synthetic inputs.

        Market-dependent signals and the pre-send authorization result are test stubs;
        no external API credentials or live endpoints are used. The production R39
        submit guard remains real and must block before any create/cancel order call.
        """
        class SyntheticExchange:
            def price_to_precision(self, symbol, value):
                return f"{float(value):.6f}"

            def amount_to_precision(self, symbol, value):
                return f"{float(value):.6f}"

            async def fetch_order_book(self, symbol, limit=20):
                return {"bids": [[101.9, 10000], [101.8, 10000]],
                        "asks": [[102.1, 1000], [102.2, 1000]]}

            async def fetch_balance(self):
                return {"total": {"USDT": 1000}}

            async def fetch_tickers(self):
                return {"BTC/USDT": {"last": 100000}, "TEST/USDT": {"last": 102}}

            async def fetch_ticker(self, symbol):
                return {"last": 102, "bid": 101.9, "ask": 102.1, "quoteVolume": 5_000_000}

            async def fetch_ohlcv(self, *args, **kwargs):
                raise AssertionError("synthetic fixture must not fetch live OHLCV")

            def __getattr__(self, name):
                if name.startswith(("create_", "cancel_", "edit_")):
                    async def forbidden_order_wire(*args, **kwargs):
                        raise AssertionError(f"no exchange order wire allowed: {name}")
                    return forbidden_order_wire
                raise AttributeError(name)

        n = 150
        index = pd.date_range(end=pd.Timestamp.now(tz="UTC"), periods=n, freq="5min")
        values = np.linspace(99.0, 102.0, n)
        frame = pd.DataFrame({
            "open": values - .05, "high": values + .10, "low": values - .10,
            "close": values, "volume": np.full(n, 10000.0),
        }, index=index)
        frame.loc[frame.index[-3:], "volume"] = 15000
        candidate = bot.StrategyCandidate(
            engine_id="pullback", symbol="TEST/USDT", side="long",
            generated_at_ms=int(time.time() * 1000), entry_ref=102.0, sl_price=100.0,
            tp1_rr=1.5, tp2_rr=2.5, tp3_rr=4.0, engine_score=.95, rr_ratio=1.5,
            liquidity_score=.95, regime_fit=.95, family="PULLBACK", zone_ref=102.0,
            features_snapshot={"liquidity_tier": "LARGE", "tier": "LARGE", "htf_score": 90,
                               "htf_strength": 90, "quote_volume_usdt": 5_000_000,
                               "score": 95, "strategy_mode": "PULLBACK", "family": "PULLBACK",
                               "zone_ref": 102.0, "entry_ref": 102.0, "sl_price": 100.0},
            strategy_mode="PULLBACK", strategy_style="SCALP", market_phase="TRENDING",
            macro_regime="BULLISH", local_regime="BULLISH", bearish_severity="NORMAL")
        market_data = {
            "df_1d": frame, "df_4h": frame, "df_1h": frame, "df_15m": frame,
            "df_5m": frame, "df_btc_5m": frame, "df_btc_15m": frame,
            "df_btc_1h": frame, "df_btc_4h": frame,
            "quote_vol_24h": 5_000_000, "market_phase": "TRENDING",
        }
        geometry = lambda **kw: {
            "ok": True, "reason": "synthetic_test_geometry", "entry": float(kw["entry"]),
            "sl": float(kw["sl"]), "tp1": float(kw["tp1"]),
            "tp2": float(kw["tp2"]), "tp3": float(kw["tp3"]),
            "fee_detail": {"ok": True, "reason": "test_only"},
        }

        async def run_builder():
            patches = [
                patch.dict(os.environ, {"UNIFIED_ALLOW_LIVE_TRADING": "", "UNIFIED_LIVE_PILOT_ENABLE": "0", "UNIFIED_A19_DIAGNOSTIC_ONLY": "0"}),
                patch.object(bot.MarketRegime, "classify_from_btc_4h", return_value="BULLISH"),
                patch.object(bot.V425BearishSeverity, "classify", return_value="NORMAL"),
                patch.object(bot.V425LocalRegime, "classify", return_value="BULLISH"),
                patch.object(bot.BTCContext, "evaluate", return_value="BULLISH"),
                patch.object(bot.BTCContext, "blocks_new_entries", return_value=False),
                patch.object(bot.HTFGrader, "grade", return_value=(True, "BULLISH", 90.0, "ok")),
                patch.object(bot.MarketPhaseDetector, "detect", return_value={"phase": "TRENDING"}),
                patch.object(bot, "validate_mse_snapshot", return_value=(True, "ok")),
                patch.object(bot.CompositeRankingEngine, "_validate_fail_closed", return_value=None),
                patch.object(bot, "_v455_candidate_freshness_ok", return_value=(True, "ok", 0.0)),
                patch.object(bot, "_v689_prequal_snapshot_reusable", return_value=True),
                patch.object(bot.OpportunityDetectors, "detect_mtf_pullback", return_value=(False, {})),
                patch.object(bot.FamilyPolicyLayer, "regime_policy_detail", return_value=(True, "ok", {})),
                patch.object(bot.MicroStructure, "micro_bos_confirm", return_value=(True, .02)),
                patch.object(bot, "_v520_fake_break_gate", return_value=(True, {})),
                patch.object(bot, "_v565_structural_recovery_candidate", return_value=False),
                patch.object(bot, "_v631_verified_reclaim_structural_recovery", return_value=False),
                patch.object(bot, "_v642_adaptive_structural_recovery", return_value=(False, {})),
                patch.object(bot, "_v646_sr_structural_recovery_allowed", return_value=False),
                patch.object(bot, "_v455_record_prequal_reason", return_value=None),
                patch.object(bot, "_v648_mtf_promotion_allowed", return_value=False),
                patch.object(bot, "_v587_pullback_quality", return_value={
                    "ok": True, "quality": 95.0, "reason": "synthetic_offline_validated",
                    "confirmations": ["BOS", "RECLAIM", "VOLUME"], "canonical_confirmed": True,
                    "volume_ratio": 1.5, "rs_5m": .10, "htf_strength": 90.0,
                    "structure": 90.0, "retest": 90.0, "chase": 0.0}),
                patch.object(bot.CompositeScorer, "build", return_value=(92.0, "A_STRONG", {
                    "total": 92.0, "structure_quality": 90.0, "momentum": 90.0})),
                patch.object(bot, "_v702_elite_live_context_gate", return_value=(True, "ok", {"synthetic": True})),
                patch.object(bot.PreSendGate, "evaluate", new=AsyncMock(return_value=(True, "test-only pre-send pass",
                    SimpleNamespace(quantity_asset=.01, notional_usdt=10.0, notional_after_caps=100.0,
                                    fees_usdt=0.0, risk_usdt=.20)))),
                patch.object(bot.SizingEngine, "fee_viability_detail", return_value={"ok": True, "reason": "test_only"}),
                patch.object(bot, "_v702_normalize_final_geometry", side_effect=geometry),
            ]
            active = []
            try:
                for candidate_patch in patches:
                    active.append(candidate_patch.start())
                before_blocks = int(bot.STATS.get("v702_monitor_only_entry_blocks", 0) or 0)
                before_queued = int(bot.STATS.get("v702_queued", 0) or 0)
                result = await bot.SignalBuilder.build_and_route(
                    SyntheticExchange(), "TEST/USDT", market_data, preferred_candidate=candidate)
                after_blocks = int(bot.STATS.get("v702_monitor_only_entry_blocks", 0) or 0)
                return result, before_blocks, after_blocks, before_queued
            finally:
                for candidate_patch in reversed(patches):
                    candidate_patch.stop()

        result, before_blocks, after_blocks, _ = asyncio.run(run_builder())
        self.assertIsNone(result, "monitor-only guard must prevent an accepted live entry")
        self.assertGreater(after_blocks, before_blocks, "route did not reach central new-entry guard")
        self.assertEqual(bot.STATS.get("last_send_fail_reason"), "monitor_only_new_live_buys")
        self.assertTrue(bot.CONFIG.get("V702_MONITOR_ONLY_MODE", True))

    def test_canonical_builder_invocation_fails_closed_without_exchange_wires(self):
        class NoWireExchange:
            def __getattr__(self, name):
                if name.startswith("fetch_") or name.startswith("create_") or name.startswith("cancel_"):
                    async def no_wire(*args, **kwargs):
                        raise AssertionError(f"network method must not be used in this fixture: {name}")
                    return no_wire
                raise AttributeError(name)
        candidate = SimpleNamespace(
            symbol="BTC/USDT", family="BREAKOUT", strategy_mode="BREAKOUT", engine_id="breakout",
            generated_at_ms=int(time.time() * 1000) - 3_600_000,
            entry_ref=100.0, sl_price=98.0, tp1_rr=1.0, tp2_rr=2.0, tp3_rr=3.0,
            engine_score=0.8, rr_ratio=1.0, liquidity_score=0.7, regime_fit=0.7,
            features_snapshot={"snapshot_id": "SYNTHETIC-E2E-FAIL-CLOSED", "liquidity_tier": "LARGE"},
        )
        async def run():
            # The real installed Builder wrapper and downstream wrappers are called.
            # This intentionally incomplete market snapshot must fail closed; no
            # exchange network methods are implemented by this fixture.
            with patch.dict(os.environ, {"UNIFIED_ALLOW_LIVE_TRADING": "", "UNIFIED_A19_DIAGNOSTIC_ONLY": "0"}):
                return await bot.SignalBuilder.build_and_route(
                    NoWireExchange(), candidate.symbol, {"snapshot_id": "SYNTHETIC-E2E-FAIL-CLOSED"},
                    preferred_candidate=candidate)
        before = int(bot.STATS.get("v702_r26_builder_terminal_none", 0) or 0)
        result = asyncio.run(run())
        self.assertIsNone(result)
        self.assertGreaterEqual(int(bot.STATS.get("v702_r26_builder_terminal_none", 0) or 0), before + 1)
        self.assertEqual(bot.STATS.get("v702_r26_builder_terminal_last", {}).get("symbol"), "BTC/USDT")
        self.assertTrue(bot.CONFIG.get("V702_MONITOR_ONLY_MODE", True))


if __name__ == "__main__":
    unittest.main()


    def test_legacy_live_token_never_authorizes_without_canonical_resolver(self):
        async def run():
            isolated_ns = {
                "CONFIG": {"V702_LIVE_PILOT_ENABLE": True, "LONG_ONLY": True, "MARKET_TYPE": "SPOT"},
                "ENV": {"MEXC_API_KEY": "OFFLINE_TEST_KEY", "MEXC_API_SECRET": "OFFLINE_TEST_SECRET"},
                "STATS": {},
            }
            with patch.dict(os.environ, {"UNIFIED_ALLOW_LIVE_TRADING": "I_ACCEPT_LIVE_RISK"}, clear=False):
                return await bot.V702PortfolioDrawdownGuard.authorize_entry(
                    isolated_ns, object(), "BTC/USDT")
        allowed, reason, details = asyncio.run(run())
        self.assertFalse(allowed)
        self.assertEqual(reason, "entry_policy_authority_missing")
        self.assertTrue(details.get("legacy_token_ignored"))

    def test_portfolio_ignore_list_is_explicit_and_does_not_hide_other_unpriced_assets(self):
        class DustExchange:
            async def fetch_balance(self):
                return {"total": {"USDT": 50.0, "DELISTED": 1.0}}
            async def fetch_tickers(self, symbols=None):
                raise AssertionError("explicitly ignored dust must not require price lookup")

        cfg = dict(bot.CONFIG)
        cfg.update({"V702_EQUITY_IGNORE_ASSETS": ["DELISTED"], "V702_EQUITY_TICKER_CACHE_TTL_SEC": 0})
        ns = {"CONFIG": cfg, "STATS": {}}
        equity, reason = asyncio.run(bot.V702PortfolioDrawdownGuard.equity_usdt(DustExchange(), ns=ns))
        self.assertEqual(equity, 50.0)
        self.assertEqual(reason, "ok")

    def test_a58_cost_model_uses_conservative_max_for_paper_and_live_inputs(self):
        with patch.dict(bot.CONFIG, {
            "V702_SHADOW_MIN_ROUND_TRIP_COST_PCT": 0.30,
            "V702_SMALL_NET_SPREAD_FALLBACK_PCT": 0.15,
            "V702_SMALL_NET_SLIPPAGE_PER_SIDE_PCT": 0.05,
            "TAKER_FEE_PCT": 0.10,
            "ROUNDTRIP_FEE_MULT": 2.0,
        }):
            floor = bot._v702_unified_round_trip_cost_pct()
            measured = bot._v702_unified_round_trip_cost_pct(measured_cost_pct=0.72, spread_pct=0.04, fee_cost_pct=0.08)
        self.assertGreaterEqual(floor["round_trip_cost_pct"], 0.30)
        self.assertEqual(measured["round_trip_cost_pct"], 0.77)
        self.assertEqual(measured["measured_cost_pct"], 0.72)
        self.assertEqual(measured["measured_cost_buffer_pct"], 0.05)
        self.assertEqual(measured["used_measured_cost"], 1.0)

    def test_a58_paper_fill_requires_a_buffered_breakout(self):
        trigger, margin = bot.KnowledgeOutcomeLedger._paper_fill_trigger(100.0, 0.10)
        self.assertGreater(trigger, 100.0)
        self.assertGreaterEqual(margin, 0.05)
        self.assertEqual(bot.KnowledgeOutcomeLedger.max_active(), 20)
        with patch.dict(bot.CONFIG, {"V702_KNOWLEDGE_OUTCOME_MAX_ACTIVE": 999}):
            self.assertEqual(bot.KnowledgeOutcomeLedger.max_active(), 120)
        with patch.dict(bot.CONFIG, {"V702_KNOWLEDGE_OUTCOME_MAX_ACTIVE": 0}):
            self.assertEqual(bot.KnowledgeOutcomeLedger.max_active(), 1)

    def test_a58_platform_rate_limiter_classifies_safety_priority(self):
        priority = bot.V702PlatformRateLimiter.priority
        self.assertEqual(priority("position_manager_tick")[0], 0)
        self.assertEqual(priority("create_market_buy")[0], 1)
        self.assertEqual(priority("fetch_ohlcv_scan")[0], 2)
        self.assertEqual(priority("knowledge_ohlcv_BTC")[0], 3)
