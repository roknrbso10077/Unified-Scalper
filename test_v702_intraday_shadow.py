import hashlib
import sqlite3
import tempfile
import time
from contextlib import contextmanager
import unittest
from pathlib import Path

import pandas as pd

from v702_intraday_shadow import V702IntradayShadow, select_balanced_shadow_symbols


class IntradayShadowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "study.db")
        self.cfg = {
            "V702_INTRADAY_SHADOW_ENABLE": True,
            "V702_INTRADAY_SHADOW_LIVE_ENABLE": False,
            "V702_INTRADAY_SHADOW_TELEGRAM_ALERTS_ENABLE": True,
            "V702_INTRADAY_SHADOW_ALERT_COOLDOWN_SEC": 180,
            "V702_INTRADAY_LSA_MAX_AGE_SEC": 120,
            "V702_INTRADAY_SHADOW_MIN_QUOTE_VOLUME_USDT": 1_000_000,
            "V702_INTRADAY_SHADOW_MIN_1M_CANDLES": 40,
            "V702_INTRADAY_SHADOW_MAX_HOLD_BARS": 30,
            "TAKER_FEE_PCT": 0.10,
            "V702_INTRADAY_SPREAD_FALLBACK_PCT": 0.15,
            "V702_INTRADAY_SLIPPAGE_PER_SIDE_PCT": 0.05,
            "V702_INTRADAY_MIN_NET_PROFIT_PCT": 0.10,
            "V702_INTRADAY_MIN_NET_RR": 0.25,
            "V702_INTRADAY_TP1_FEE_COVERAGE": 2.5,
            "V702_INTRADAY_MAX_TARGET_RR": 3.0,
            "V702_INTRADAY_TARGET_BUFFER_R": 0.03,
            "V702_INTRADAY_MIN_VOLUME_RATIO": 1.10,
            "V702_INTRADAY_MAX_CHASE_ATR": 0.80,
        }
        self.study = V702IntradayShadow(self.db, self.tmp.name, config_getter=lambda: self.cfg)

    def tearDown(self):
        self.tmp.cleanup()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def make_1m(breakout=False):
        periods = 52
        idx = pd.date_range("2026-10-11T10:00:00Z", periods=periods, freq="min")
        rows = []
        for i in range(periods):
            rows.append({"open":99.95,"high":100.10,"low":99.80,"close":100.00,"volume":100.0})
        if breakout:
            # The penultimate candle is the latest closed signal bar; final row is open.
            rows[-2] = {"open":99.98,"high":100.23,"low":99.90,"close":100.20,"volume":180.0}
            rows[-1] = {"open":100.00,"high":100.08,"low":99.92,"close":100.00,"volume":90.0}
        frame = pd.DataFrame(rows, index=idx)
        # Deterministically mark the final candle as still forming.
        frame.attrs["as_of_ms"] = int(idx[-1].timestamp() * 1000) + 60_000 - 1
        return frame

    def snapshot(self, symbol="DOT/USDT"):
        asset5 = [100.0 + i * 0.035 for i in range(60)]
        asset15 = [100.0 + i * 0.060 for i in range(60)]
        btc5 = [100.0 + i * 0.020 for i in range(60)]
        btc15 = [100.0 + i * 0.030 for i in range(60)]
        df5 = self._ohlcv_frame("5min", asset5)
        btc5_frame = self._ohlcv_frame("5min", btc5)
        # Align the latest closed 5m bars to the latest closed 15m bars.
        for frame in (df5, btc5_frame):
            frame.index = frame.index + pd.Timedelta(hours=10)
            frame.attrs["as_of_ms"] = int(frame.index[-1].timestamp() * 1000) + 300_000 + 1001
        return {"symbol":symbol,"quote_vol_24h":2_000_000,"tier":"MICRO","spread_pct":0.05,
                "df_5m":df5,
                "df_15m":self._ohlcv_frame("15min", asset15),
                "df_btc_5m":btc5_frame,
                "df_btc_15m":self._ohlcv_frame("15min", btc15),
                "macro_regime":"NEUTRAL"}

    def enable_test_micro_alerts(self):
        # Relax only the synthetic fixture's net-R floor; production defaults remain 0.75R.
        self.cfg["V702_INTRADAY_MICRO_ALERT_MIN_NET_R"] = 0.25

    def test_scheduler_events_explain_empty_or_skipped_shadow_days(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        tz=ZoneInfo("Africa/Cairo")
        day_start=datetime(2026,10,11,0,0,tzinfo=tz)
        self.assertTrue(self.study.record_scheduler_event("SELECTION_EMPTY",reason="no_eligible_core_or_micro_symbols",
            event_ts=datetime(2026,10,11,10,0,tzinfo=tz).timestamp()))
        self.assertTrue(self.study.record_scheduler_event("BATCH_SELECTED",selected_count=4,
            event_ts=datetime(2026,10,11,10,4,tzinfo=tz).timestamp()))
        self.assertTrue(self.study.record_scheduler_event("BATCH_STARTED",selected_count=4,
            event_ts=datetime(2026,10,11,10,5,tzinfo=tz).timestamp()))
        self.assertTrue(self.study.record_scheduler_event("BATCH_COMPLETED",selected_count=4,fetched_count=3,
            processed_count=3,failed_count=1,reason="partial_fetch_or_processing_failure",
            event_ts=datetime(2026,10,11,10,6,tzinfo=tz).timestamp()))
        report=self.study.ensure_daily_telegram_report(datetime(2026,10,12,1,0,tzinfo=tz).timestamp())
        self.assertIsNotNone(report)
        scheduler=report["payload"].get("scheduler",{})
        self.assertEqual(scheduler.get("status"),"RECORDED")
        self.assertEqual(scheduler.get("selected_count"),4)
        self.assertEqual(scheduler.get("fetched_count"),3)
        self.assertEqual(scheduler.get("failed_count"),1)
        self.assertEqual(scheduler.get("by_event_type",{}).get("SELECTION_EMPTY",{}).get("events"),1)
        self.assertIn("no_eligible_core_or_micro_symbols",scheduler.get("top_reasons",{}))

    def test_schema_selftest_and_shadow_only(self):
        result = self.study.self_test()
        self.assertTrue(result["pass"], result)
        self.assertFalse(self.cfg["V702_INTRADAY_SHADOW_LIVE_ENABLE"])

    def test_micro_telegram_alert_and_result_use_shared_opportunity_links(self):
        source = Path(__file__).with_name("main.py").read_text(encoding="utf-8")
        self.assertIn("OpportunityTelegramNotifier._links_html(str(_alert.get(\"symbol\") or \"\"), int(_alert.get(\"signal_ts_ms\") or 0), str(_alert.get(\"strategy_mode\") or \"MICRO\"))", source)
        self.assertIn("OpportunityTelegramNotifier._links_html(_osym, int(_op.get(\"signal_ts_ms\") or 0), _omode)", source)
        self.assertIn("V702-A9-MICRO-OUTCOME-TG", source)

    def test_micro_momentum_is_recorded_without_higher_timeframe_bull_gate(self):
        result = self.study.process_symbol("DOT/USDT", self.make_1m(True), self.snapshot())
        self.assertGreaterEqual(result["signals"], 1)
        with self.connect() as conn:
            row = conn.execute("SELECT strategy_mode,status,target,entry,risk_pct,cost_pct,features_json FROM v702_intraday_shadow_samples WHERE strategy_mode='MICRO_MOMENTUM_1M'").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], "PENDING")
        self.assertGreater(row[2], row[3])
        self.assertGreater(row[4], 0)
        self.assertGreaterEqual(row[5], 0.35)  # fee + fallback spread + two-sided slippage
        self.assertIn('"higher_timeframe_bullish_required":false', row[6])

    def test_micro_shadow_alert_is_persisted_without_live_order_authority(self):
        self.enable_test_micro_alerts()
        result = self.study.process_symbol("DOT/USDT", self.make_1m(True), self.snapshot())
        self.assertGreaterEqual(result["signals"], 1)
        alerts = self.study.pending_micro_alerts(limit=5, max_age_sec=180)
        self.assertTrue(alerts, "new micro sample must create an independent Shadow alert outbox row")
        self.assertTrue(all(x["payload"].get("alert_mode") == "MONITOR_ONLY_NO_ORDERS" for x in alerts))
        self.assertTrue(all(x["payload"].get("liquidation_spot_absorption", {}).get("status") == "UNAVAILABLE" for x in alerts))
        first = alerts[0]["sample_id"]
        self.assertTrue(self.study.mark_micro_alert_queued(first))
        self.assertNotIn(first, {x["sample_id"] for x in self.study.pending_micro_alerts(limit=5, max_age_sec=180)})
        self.assertFalse(self.cfg["V702_INTRADAY_SHADOW_LIVE_ENABLE"])

    def test_micro_alert_outbox_expires_stale_rows_and_deduplicates_same_candle(self):
        self.enable_test_micro_alerts()
        self.study.process_symbol("DOT/USDT", self.make_1m(True), self.snapshot())
        first = self.study.pending_micro_alerts(limit=5, max_age_sec=180)
        self.assertTrue(first)
        # Replaying the same closed candle cannot create another sample/alert.
        replay = self.study.process_symbol("DOT/USDT", self.make_1m(True), self.snapshot())
        self.assertEqual(replay["signals"], 0)
        with self.connect() as conn:
            count_before = conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_alerts").fetchone()[0]
            conn.execute("UPDATE v702_intraday_shadow_alerts SET created_ts=? WHERE sample_id=?", (time.time()-600, first[0]["sample_id"]))
        self.assertEqual(count_before, 1)
        self.assertEqual(self.study.pending_micro_alerts(limit=5, max_age_sec=60), [])
        with self.connect() as conn:
            state = conn.execute("SELECT state FROM v702_intraday_shadow_alerts WHERE sample_id=?", (first[0]["sample_id"],)).fetchone()[0]
        self.assertEqual(state, "EXPIRED")

    def test_zero_spread_is_not_treated_as_zero_cost_evidence(self):
        snapshot = self.snapshot()
        snapshot["spread_pct"] = 0.0
        self.study.process_symbol("DOT/USDT", self.make_1m(True), snapshot)
        with self.connect() as conn:
            row = conn.execute(
                "SELECT cost_pct,features_json FROM v702_intraday_shadow_samples WHERE strategy_mode='MICRO_MOMENTUM_1M'"
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertGreaterEqual(row[0], 0.45)  # fallback spread + round-trip fees + two-sided slippage
        self.assertIn('"spread_source":"FALLBACK_MISSING_OR_NONPOSITIVE_BBO"', row[1])
        self.assertEqual(self.study.pending_micro_alerts(limit=5, max_age_sec=180), [])

    def test_technical_only_or_low_net_rr_sample_is_never_alerted(self):
        self.cfg["V702_INTRADAY_MICRO_ALERT_MIN_NET_R"] = 99.0
        self.study.process_symbol("DOT/USDT", self.make_1m(True), self.snapshot())
        with self.connect() as conn:
            row = conn.execute(
                "SELECT features_json FROM v702_intraday_shadow_samples WHERE strategy_mode='MICRO_MOMENTUM_1M'"
            ).fetchone()
        self.assertIsNotNone(row)  # research ledger still records the setup
        self.assertIn('"micro_alert_eligible":false', row[0])
        self.assertIn('"micro_alert_block_reason":"micro_net_rr_below_alert_floor"', row[0])
        self.assertEqual(self.study.pending_micro_alerts(limit=5, max_age_sec=180), [])

    def test_micro_alert_fails_closed_without_closed_5m_15m_confirmation(self):
        snapshot = self.snapshot()
        snapshot["df_15m"] = None
        self.enable_test_micro_alerts()
        self.study.process_symbol("DOT/USDT", self.make_1m(True), snapshot)
        with self.connect() as conn:
            row = conn.execute(
                "SELECT features_json FROM v702_intraday_shadow_samples WHERE strategy_mode='MICRO_MOMENTUM_1M'"
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertIn('"micro_alert_block_reason":"micro_mtf_history_insufficient"', row[0])
        self.assertEqual(self.study.pending_micro_alerts(limit=5, max_age_sec=180), [])

    def test_micro_alert_rejects_recent_mtf_candle_gaps(self):
        snapshot = self.snapshot()
        snapshot["df_15m"].attrs.pop("as_of_ms", None)
        # Introduce a real missing 15m timestamp; the recent-bar quality gate must fail closed.
        frame = snapshot["df_15m"].drop(snapshot["df_15m"].index[-3])
        frame.attrs["as_of_ms"] = int(frame.index[-1].timestamp() * 1000) + 900_000 + 1001
        snapshot["df_15m"] = frame
        details = self.study._micro_alert_confirmation(snapshot)
        self.assertFalse(details[0])
        self.assertEqual(details[1], "micro_mtf_recent_candle_gap")

    def test_micro_pullback_alerts_are_paused_while_research_samples_continue(self):
        snapshot = self.snapshot()
        cost = self.study._cost_model_details(snapshot)
        allowed, reason, _ = self.study._micro_alert_gate(
            "MICRO_PULLBACK_RECLAIM_1M", cost, 0.50, 1.0, True, snapshot
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "micro_pullback_alerts_paused_pending_validation")

    def test_report_exposes_micro_alert_quality_policy_and_suppression(self):
        self.cfg["V702_INTRADAY_MICRO_ALERT_MIN_NET_R"] = 99.0
        self.study.process_symbol("DOT/USDT", self.make_1m(True), self.snapshot())
        report = self.study.report()
        self.assertTrue(report["micro_alerts"]["quality_policy"]["require_closed_5m_15m_confirmation"])
        self.assertEqual(report["micro_alerts"]["quality_policy"]["minimum_net_r"], 99.0)
        strat = report["strategies"]["MICRO_MOMENTUM_1M"]
        self.assertEqual(strat["micro_alert_suppressed_samples"], 1)
        self.assertEqual(strat["micro_alert_suppression_reasons"]["micro_net_rr_below_alert_floor"], 1)

    def test_lsa_contract_qualifies_only_with_complete_fresh_cross_market_evidence(self):
        now_ms = int(time.time() * 1000)
        snapshot = self.snapshot("DOT/USDT")
        snapshot["liquidation_spot_absorption"] = {
            "source": "test-provider", "observed_at_ms": now_ms, "symbol": "DOT/USDT",
            "long_liquidations_usdt_15m": 300000.0, "baseline_long_liquidations_usdt_15m": 100000.0,
            "open_interest_change_pct_15m": -3.0, "funding_rate_current": 0.00005,
            "funding_rate_previous": 0.00010, "spot_buy_volume_usdt_5m": 700000.0,
            "spot_sell_volume_usdt_5m": 300000.0, "reclaimed_support": True,
        }
        assessment = self.study._assess_liquidation_spot_absorption(snapshot, symbol="DOT/USDT", now_ms=now_ms)
        self.assertEqual(assessment["status"], "QUALIFIED")
        self.assertEqual(assessment["conditions_passed"], 5)

    def test_lsa_stale_or_incomplete_data_is_unavailable(self):
        now_ms = int(time.time() * 1000)
        incomplete = self.study._assess_liquidation_spot_absorption({"liquidation_spot_absorption":{"source":"x"}}, "DOT/USDT", now_ms)
        self.assertEqual(incomplete["status"], "UNAVAILABLE")
        stale_context = {
            "source": "test-provider", "observed_at_ms": now_ms - 600000, "symbol": "DOT/USDT",
            "long_liquidations_usdt_15m": 300000.0, "baseline_long_liquidations_usdt_15m": 100000.0,
            "open_interest_change_pct_15m": -3.0, "funding_rate_current": 0.00005,
            "funding_rate_previous": 0.00010, "spot_buy_volume_usdt_5m": 700000.0,
            "spot_sell_volume_usdt_5m": 300000.0, "reclaimed_support": True,
        }
        stale = self.study._assess_liquidation_spot_absorption({"symbol":"DOT/USDT","liquidation_spot_absorption":stale_context}, "DOT/USDT", now_ms)
        self.assertEqual(stale["status"], "UNAVAILABLE")

    def test_balanced_selector_prevents_rs_leaders_crowding_out_micro_pool(self):
        core = [(f"CORE{i}/USDT", 5_000_000-i*1000) for i in range(40)]
        micro = [(f"MICRO{i}/USDT", 2_000_000-i*1000) for i in range(30)]
        leaders = [f"CORE{i}/USDT" for i in range(10)]
        result = select_balanced_shadow_symbols(core, micro, leaders, batch_size=24, core_offset=0, micro_offset=0)
        self.assertEqual(len(result["selected"]), 24)
        self.assertEqual(result["core_selected"], 12)
        self.assertEqual(result["micro_selected"], 12)
        self.assertEqual(len(set(result["selected"])), 24)
        self.assertLessEqual(result["rs_leaders_selected"], 3)
        rotated = select_balanced_shadow_symbols(core, micro, leaders, batch_size=24, core_offset=result["core_offset"], micro_offset=result["micro_offset"])
        self.assertEqual(rotated["micro_selected"], 12)
        self.assertNotEqual(result["selected"], rotated["selected"])

    def test_cost_aware_target_accounts_for_round_trip_costs(self):
        self.study.process_symbol("DOT/USDT", self.make_1m(True), self.snapshot())
        with self.connect() as conn:
            row = conn.execute("SELECT entry,target,risk_unit,risk_pct,cost_pct,features_json FROM v702_intraday_shadow_samples WHERE strategy_mode='MICRO_MOMENTUM_1M'").fetchone()
        entry, target, risk, risk_pct, cost_pct, features = row
        rr = (target-entry)/risk
        self.assertGreater(rr, 1.0)
        import json
        meta = json.loads(features)
        self.assertGreaterEqual(rr, min(meta["required_target_rr_before_cap"], 3.0))
        self.assertGreaterEqual(cost_pct, 0.35)

    def test_following_closed_bar_resolves_virtual_tp(self):
        self.enable_test_micro_alerts()
        self.study.process_symbol("DOT/USDT", self.make_1m(True), self.snapshot())
        with self.connect() as conn:
            row = conn.execute("SELECT target FROM v702_intraday_shadow_samples WHERE strategy_mode='MICRO_MOMENTUM_1M'").fetchone()
        self.assertIsNotNone(row)
        target = row[0]
        frame = self.make_1m(True)
        frame.iloc[-1, frame.columns.get_loc("open")] = target - 0.05
        frame.iloc[-1, frame.columns.get_loc("high")] = target + 0.05
        frame.iloc[-1, frame.columns.get_loc("low")] = target - 0.10
        frame.iloc[-1, frame.columns.get_loc("close")] = target
        # New final row represents the next still-open bar; the prior final row is now closed.
        next_row = frame.iloc[-1].copy()
        next_ts = frame.index[-1] + pd.Timedelta(minutes=1)
        frame = pd.concat([frame, pd.DataFrame([next_row], index=[next_ts])])
        frame.attrs["as_of_ms"] = int(next_ts.timestamp() * 1000) + 60_000 - 1
        result = self.study.process_symbol("DOT/USDT", frame, self.snapshot())
        with self.connect() as conn:
            status, net_r = conn.execute("SELECT status,net_r FROM v702_intraday_shadow_samples WHERE strategy_mode='MICRO_MOMENTUM_1M'").fetchone()
        self.assertEqual(status, "TP1")
        self.assertIsNotNone(net_r)
        self.assertGreater(net_r, -5.0)
        outcomes = self.study.pending_micro_outcomes(limit=5)
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0]["outcome"], "TP1")
        self.assertEqual(outcomes[0]["payload"]["mode"], "MONITOR_ONLY_NO_ORDERS")
        self.assertIsNotNone(outcomes[0]["payload"]["net_r"])
        self.assertTrue(self.study.mark_micro_outcome_queued(outcomes[0]["sample_id"]))
        self.assertEqual(self.study.pending_micro_outcomes(limit=5), [])

    def test_micro_sl_outcome_creates_single_retryable_telegram_event(self):
        self.enable_test_micro_alerts()
        self.study.process_symbol("DOT/USDT", self.make_1m(True), self.snapshot())
        with self.connect() as conn:
            sample = conn.execute("SELECT sample_id,entry,stop,target,signal_ts_ms FROM v702_intraday_shadow_samples WHERE strategy_mode='MICRO_MOMENTUM_1M'").fetchone()
        self.assertIsNotNone(sample)
        sid, entry, stop, target, signal_ts = sample
        frame = self.make_1m(True)
        frame.iloc[-1, frame.columns.get_loc("open")] = entry
        frame.iloc[-1, frame.columns.get_loc("high")] = min(target - 0.01, entry + 0.02)
        frame.iloc[-1, frame.columns.get_loc("low")] = stop - 0.02
        frame.iloc[-1, frame.columns.get_loc("close")] = stop
        next_row = frame.iloc[-1].copy()
        next_ts = frame.index[-1] + pd.Timedelta(minutes=1)
        frame = pd.concat([frame, pd.DataFrame([next_row], index=[next_ts])])
        frame.attrs["as_of_ms"] = int(next_ts.timestamp() * 1000) + 60_000 - 1
        self.study.process_symbol("DOT/USDT", frame, self.snapshot())
        with self.connect() as conn:
            status, net_r = conn.execute("SELECT status,net_r FROM v702_intraday_shadow_samples WHERE sample_id=?", (sid,)).fetchone()
            event_count = conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_outcomes WHERE sample_id=?", (sid,)).fetchone()[0]
        self.assertEqual(status, "SL")
        self.assertIsNotNone(net_r)
        self.assertEqual(event_count, 1)
        outcome = self.study.pending_micro_outcomes(limit=5)[0]
        self.assertEqual(outcome["outcome"], "SL")
        self.assertEqual(outcome["payload"]["gross_r"], -1.0)
        self.assertTrue(self.study.mark_micro_outcome_queued(sid))
        self.assertFalse(self.study.mark_micro_outcome_queued(sid))

    def test_ambiguous_data_gap_is_not_scored_as_win_or_loss_and_is_notified(self):
        self.enable_test_micro_alerts()
        self.study.process_symbol("DOT/USDT", self.make_1m(True), self.snapshot())
        with self.connect() as conn:
            sid = conn.execute("SELECT sample_id FROM v702_intraday_shadow_samples WHERE strategy_mode='MICRO_MOMENTUM_1M'").fetchone()[0]
        signal_ts = int(pd.Timestamp("2026-10-11T10:51:00Z").timestamp() * 1000)
        self.study._update_pending("DOT/USDT", [{"ts":float(signal_ts+120_000),"open":100.0,"high":101.0,"low":99.0,"close":100.0,"volume":100.0,"gap_before":True}])
        with self.connect() as conn:
            status, net_r = conn.execute("SELECT status,net_r FROM v702_intraday_shadow_samples WHERE sample_id=?", (sid,)).fetchone()
        self.assertEqual(status, "AMBIGUOUS_DATA_GAP")
        self.assertIsNone(net_r)
        outcome = self.study.pending_micro_outcomes(limit=5)[0]
        self.assertEqual(outcome["outcome"], "AMBIGUOUS_DATA_GAP")
        self.assertTrue(outcome["payload"]["ambiguous"])
        self.assertIsNone(outcome["payload"]["net_r"])

    def test_daily_report_is_previous_cairo_day_per_strategy_and_deduplicated(self):
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo
        cairo = ZoneInfo("Africa/Cairo")
        sample_time = datetime(2026, 11, 17, 12, 0, tzinfo=cairo).timestamp()
        with self.connect() as conn:
            conn.execute("""INSERT INTO v702_intraday_shadow_samples
                (sample_id,symbol,strategy_mode,timeframe,signal_ts_ms,created_ts,entry,stop,target,risk_unit,risk_pct,
                 last_candle_ts_ms,bars_seen,status,exit_price,gross_r,net_r,net_pct,cost_pct,resolved_ts,features_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("daily-test-sample","DOT/USDT","MICRO_MOMENTUM_1M","1m",int(sample_time*1000),sample_time,
                 100.0,99.0,102.0,1.0,1.0,int(sample_time*1000),3,"TP1",102.0,2.0,1.5,1.5,0.5,sample_time+60,"{}"))
        too_early = datetime(2026, 11, 18, 0, 3, tzinfo=cairo).timestamp()
        self.assertIsNone(self.study.ensure_daily_telegram_report(now_ts=too_early))
        due = datetime(2026, 11, 18, 0, 10, tzinfo=cairo).timestamp()
        report = self.study.ensure_daily_telegram_report(now_ts=due)
        self.assertIsNotNone(report)
        self.assertEqual(report["report_date"], "2026-11-17")
        self.assertEqual(len(report["payload"]["strategies"]), 5)
        micro = report["payload"]["strategies"]["MICRO_MOMENTUM_1M"]
        self.assertEqual(micro["signals_created"], 1)
        self.assertEqual(micro["outcomes"]["TP1"], 1)
        self.assertTrue(self.study.mark_daily_telegram_report_queued("2026-11-17"))
        self.assertIsNone(self.study.ensure_daily_telegram_report(now_ts=due))

    def test_daily_report_exposes_per_strategy_evaluation_and_rejection_diagnostics(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        cairo = ZoneInfo("Africa/Cairo")
        report_due = datetime(2026, 11, 18, 0, 10, tzinfo=cairo).timestamp()
        report_day_start = datetime(2026, 11, 17, 0, 0, tzinfo=cairo).timestamp()
        with self.connect() as conn:
            rows = [
                ("eval-micro-reject", "DOT/USDT", "MICRO_MOMENTUM_1M", "1m", 1_800_000_000_000,
                 report_day_start + 60, "REJECT", "liquidity.spread", 0.31, 0, 2_000_000.0, "{}"),
                ("eval-micro-skip", "ADA/USDT", "MICRO_MOMENTUM_1M", "1m", 1_800_000_060_000,
                 report_day_start + 120, "SKIP", "closed_candle_unavailable", None, 0, 2_500_000.0, "{}"),
                ("eval-sweep-block", "SOL/USDT", "MICRO_SWEEP_RECLAIM_1M", "1m", 1_800_000_120_000,
                 report_day_start + 180, "BLOCKED", "volume_ratio_below_floor", 0.22, 0, 4_000_000.0, "{}"),
            ]
            conn.executemany("""INSERT INTO v702_intraday_shadow_evaluations
                (evaluation_id,symbol,strategy_mode,timeframe,bar_ts_ms,evaluated_ts,outcome,reason,cost_pct,
                 post_cost_viable,quote_volume_24h,features_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
        report = self.study.ensure_daily_telegram_report(now_ts=report_due)
        self.assertIsNotNone(report)
        self.assertEqual(report["payload"].get("schema_version"), 4)
        micro = report["payload"]["strategies"]["MICRO_MOMENTUM_1M"]
        self.assertEqual(micro["evaluations"], 2)
        self.assertEqual(micro["evaluation_rejections"], 1)
        self.assertEqual(micro["skipped_evaluations"], 1)
        self.assertEqual(micro["evaluation_diagnosis"], "EVALUATED_ZERO_SIGNALS")
        self.assertEqual(micro["evaluation_rejection_reasons"].get("liquidity.spread"), 1)
        sweep = report["payload"]["strategies"]["MICRO_SWEEP_RECLAIM_1M"]
        self.assertEqual(sweep["evaluation_blocked"], 1)
        self.assertEqual(sweep["evaluation_rejection_reasons"].get("volume_ratio_below_floor"), 1)
        empty = report["payload"]["strategies"]["MICRO_PULLBACK_RECLAIM_1M"]
        self.assertEqual(empty["evaluation_diagnosis"], "NO_EVALUATION_ROWS_FOR_REPORT_DAY")
        totals = report["payload"]["totals"]
        self.assertEqual(totals["evaluations"], 3)
        self.assertEqual(totals["evaluation_rejections"], 1)
        self.assertEqual(totals["skipped_evaluations"], 1)

    def test_same_bar_sl_tp_resolves_sl_first(self):
        signal_ts = 1_800_000_000_000
        sample_id = hashlib.sha256(b"test-same-bar").hexdigest()[:32]
        with self.connect() as conn:
            conn.execute("""INSERT INTO v702_intraday_shadow_samples
              (sample_id,symbol,strategy_mode,timeframe,signal_ts_ms,created_ts,entry,stop,target,risk_unit,risk_pct,last_candle_ts_ms,bars_seen,status,cost_pct,features_json)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (sample_id,"DOT/USDT","MICRO_MOMENTUM_1M","1m",signal_ts,time.time(),100.0,99.0,101.0,1.0,1.0,signal_ts-60_000,0,"PENDING",0.45,"{}"))
        bars = [{"ts":float(signal_ts),"open":100.0,"high":102.0,"low":98.0,"close":100.5,"volume":100.0,"close_ts":signal_ts+60_000}]
        self.study._update_pending("DOT/USDT", bars)
        with self.connect() as conn:
            status, gross_r = conn.execute("SELECT status,gross_r FROM v702_intraday_shadow_samples WHERE sample_id=?", (sample_id,)).fetchone()
        self.assertEqual(status, "SL")
        self.assertEqual(gross_r, -1.0)

    def test_forbidden_coin_is_not_researched(self):
        result = self.study.process_symbol("PUMP/USDT", self.make_1m(True), self.snapshot("PUMP/USDT"))
        self.assertEqual(result["signals"], 0)
        with self.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_samples WHERE symbol='PUMP/USDT'").fetchone()[0]
        self.assertEqual(count, 0)

    def test_invalid_canonical_blacklist_fails_closed(self):
        blocked = V702IntradayShadow(self.db, self.tmp.name, config_getter=lambda:self.cfg,
                                    forbidden_fn=lambda _s: (_ for _ in ()).throw(RuntimeError("blacklist unavailable")))
        result = blocked.process_symbol("DOT/USDT", self.make_1m(True), self.snapshot())
        self.assertEqual(result["signals"], 0)

    def test_vwap_reclaim_relative_strength_signal_uses_closed_bars(self):
        # The 5m price first rises, then dips below session VWAP, and closes back above it.
        idx5 = pd.date_range("2026-10-11T10:00:00Z", periods=25, freq="5min")
        rows5 = []
        for i in range(25):
            close = 100.2
            if i == 17: close = 99.6
            elif i == 18: close = 99.68
            elif i == 19: close = 99.72
            elif i == 20: close = 99.76
            elif i in (21, 22): close = 99.8
            open_ = close - 0.03 if i == 23 else close
            high = max(open_, close) + 0.10
            low = min(open_, close) - 0.10
            vol = 120.0
            if i == 23:
                open_, high, low, close, vol = 99.8, 100.32, 99.75, 100.2, 260.0
            rows5.append({"open":open_,"high":high,"low":low,"close":close,"volume":vol})
        # The last row is intentionally in-progress and must not create/alter the signal.
        rows5[-1] = {"open":100.2,"high":100.25,"low":100.15,"close":100.2,"volume":40.0}
        df5 = pd.DataFrame(rows5, index=idx5)
        df5.attrs["as_of_ms"] = int(idx5[-1].timestamp() * 1000) + 300_000 - 1

        idx15 = pd.date_range("2026-10-11T08:00:00Z", periods=21, freq="15min")
        rows15 = []
        for i in range(21):
            close = 100.0
            if i == 16: close = 99.75
            elif i == 17: close = 99.85
            elif i == 18: close = 100.05
            rows15.append({"open":close-0.02,"high":close+0.08,"low":close-0.10,"close":close,"volume":100.0})
        df15 = pd.DataFrame(rows15, index=idx15)
        btc5 = pd.DataFrame([{"open":100.0,"high":100.1,"low":99.9,"close":100.0,"volume":100.0} for _ in range(25)], index=idx5)
        btc15 = pd.DataFrame([{"open":100.0,"high":100.1,"low":99.9,"close":100.0,"volume":100.0} for _ in range(21)], index=idx15)
        snapshot = self.snapshot()
        snapshot.update({"df_5m":df5,"df_15m":df15,"df_btc_5m":btc5,"df_btc_15m":btc15})
        signal = self.study._make_vwap_rs_signal(snapshot)
        self.assertIsNotNone(signal, "synthetic VWAP reclaim with positive relative strength should emit a shadow signal")
        self.assertEqual(signal["mode"], "VWAP_RECLAIM_RS_5M")
        self.assertGreater(signal["entry"], signal["features"]["vwap_current"])
        self.assertGreaterEqual(signal["features"]["rs_5m"], 0.0)
        self.assertGreaterEqual(signal["features"]["rs_15m"], 0.0)

    def test_vwap_reclaim_rejects_missing_or_unusable_btc_relative_strength(self):
        signal = self.study._make_vwap_rs_signal(self.snapshot())
        self.assertIsNone(signal)


    @staticmethod
    def _ohlcv_frame(freq, values, high_extra=0.12, low_extra=0.12, volumes=None):
        idx = pd.date_range("2026-10-01T00:00:00Z", periods=len(values), freq=freq)
        rows = []
        for i, close in enumerate(values):
            open_ = values[i - 1] if i else close - 0.05
            rows.append({
                "open": open_, "high": max(open_, close) + high_extra,
                "low": min(open_, close) - low_extra, "close": close,
                "volume": 100.0 if volumes is None else float(volumes[i]),
            })
        frame = pd.DataFrame(rows, index=idx)
        # All synthetic bars are fully closed, with deterministic grace handling.
        tf_ms = int(pd.Timedelta(freq).total_seconds() * 1000)
        frame.attrs["as_of_ms"] = int(idx[-1].timestamp() * 1000) + tf_ms + 1001
        return frame

    def test_adaptive_relative_strength_pullback_emits_only_after_mtf_confirmation(self):
        asset4 = [100.0 + i * 0.4 for i in range(60)]
        btc4 = [100.0 + i * 0.2 for i in range(60)]
        asset1 = [100.0 + i * 0.1 for i in range(65)]
        asset15 = [100.0 + i * 0.09 for i in range(60)]
        base = asset15[-6]
        asset15[-5:] = [base - 0.50, base - 0.55, base - 0.60, base - 0.45, base - 0.30]
        asset5 = [104.5 + i * 0.003 for i in range(60)]
        asset5[-5:] = [104.66, 104.68, 104.70, 104.71, 104.98]
        volumes = [100.0] * 60
        volumes[-1] = 180.0
        snapshot = self.snapshot("LEADER/USDT")
        snapshot.update({
            "df_4h": self._ohlcv_frame("4h", asset4, 0.25, 0.25),
            "df_1h": self._ohlcv_frame("1h", asset1, 0.10, 0.10),
            "df_15m": self._ohlcv_frame("15min", asset15, 0.12, 0.12),
            "df_5m": self._ohlcv_frame("5min", asset5, 0.15, 0.15, volumes),
            "df_btc_4h": self._ohlcv_frame("4h", btc4, 0.25, 0.25),
            "adaptive_rs_rank": {"rank": 1.0, "rs_4h": 0.006},
            "quote_vol_24h": 5_000_000,
            "spread_pct": 0.10,
        })
        signal, reason = self.study._make_adaptive_rs_pullback_signal_detailed(snapshot)
        self.assertEqual(reason, "signal")
        self.assertIsNotNone(signal)
        self.assertEqual(signal["mode"], "ADAPTIVE_RS_PULLBACK_15M")
        self.assertAlmostEqual((signal["target"] - signal["entry"]) / signal["risk"], 1.5, places=6)
        self.assertGreaterEqual(signal["features"]["rank_4h"], 1.0)
        self.assertLessEqual(signal["features"]["rank_4h"], 10.0)
        self.assertGreaterEqual(signal["features"]["volume_ratio_5m"], 1.1)
        self.assertEqual(signal["features"].get("experiment"), "SHADOW_ONLY_NO_ORDERS")

    def test_relative_strength_rank_uses_closed_4h_bars(self):
        btc4 = self._ohlcv_frame("4h", [100.0 + i * 0.2 for i in range(60)], 0.25, 0.25)
        leader4 = self._ohlcv_frame("4h", [100.0 + i * 0.4 for i in range(60)], 0.25, 0.25)
        laggard4 = self._ohlcv_frame("4h", [100.0 + i * 0.1 for i in range(60)], 0.25, 0.25)
        ranks = V702IntradayShadow.rank_relative_strength({
            "LEADER/USDT": {"df_4h": leader4, "df_btc_4h": btc4},
            "LAGGARD/USDT": {"df_4h": laggard4, "df_btc_4h": btc4},
        }, top_n=2)
        self.assertEqual(ranks["LEADER/USDT"]["rank"], 1.0)
        self.assertGreater(ranks["LEADER/USDT"]["rs_4h"], 0.0)
        self.assertEqual(ranks["LAGGARD/USDT"]["rank"], 2.0)

    def test_adaptive_partial_tp_uses_only_post_entry_confirmed_15m_pivots(self):
        signal_ts = 1_800_000_000_000
        sample_id = hashlib.sha256(b"adaptive-partial-trailing-test").hexdigest()[:32]
        with self.connect() as conn:
            conn.execute("""INSERT INTO v702_intraday_shadow_samples
              (sample_id,symbol,strategy_mode,timeframe,signal_ts_ms,created_ts,entry,stop,target,risk_unit,risk_pct,
               last_candle_ts_ms,bars_seen,status,cost_pct,features_json)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (sample_id,"LEADER/USDT","ADAPTIVE_RS_PULLBACK_15M","5m",signal_ts,time.time(),
               100.0,98.0,103.0,2.0,2.0,signal_ts-60_000,0,"PENDING",0.40,"{}"))
        # The old pivot is confirmed exactly at entry and must not be used.
        # The new pivot is confirmed 45 minutes after entry and can then trail.
        self.cfg["V702_INTRADAY_SHADOW_MAX_HOLD_BARS"] = 120
        rows15 = []
        for i in range(18):
            low = 99.5
            if i == 13: low = 97.0
            if i == 14: low = 98.0
            if i == 16: low = 98.5
            if i == 17: low = 98.8
            bar_ts = signal_ts - 15 * 900_000 + i * 900_000
            rows15.append({"ts":float(bar_ts), "open":100.0, "high":100.5,
                           "low":low, "close":100.1, "volume":100.0,
                           "close_ts":float(bar_ts + 900_000)})
        # Keep the 1m outcome series continuous through the new pivot's confirm time.
        bars = [{"ts":float(signal_ts),"open":100.0,"high":103.2,"low":99.8,"close":103.0,
                 "volume":100.0,"close_ts":signal_ts+60_000}]
        end_ts = signal_ts + 45 * 60_000
        for ts in range(signal_ts + 60_000, end_ts, 60_000):
            bars.append({"ts":float(ts),"open":103.0,"high":103.1,"low":102.9,"close":103.0,
                         "volume":100.0,"close_ts":ts+60_000})
        bars.append({"ts":float(end_ts),"open":103.0,"high":103.1,"low":98.2,"close":99.0,
                     "volume":100.0,"close_ts":end_ts+60_000})
        self.study._update_pending("LEADER/USDT", bars, rows15)
        with self.connect() as conn:
            status, gross_r, tp1_hit, trailing_stop, exit_price = conn.execute(
                "SELECT status,gross_r,tp1_hit,trailing_stop,exit_price FROM v702_intraday_shadow_samples WHERE sample_id=?",
                (sample_id,)).fetchone()
        self.assertEqual(status, "TRAILING_EXIT")
        self.assertEqual(tp1_hit, 1)
        self.assertGreater(trailing_stop, 98.0)
        self.assertAlmostEqual(exit_price, trailing_stop, places=6)
        self.assertGreater(gross_r, 0.0)

    def test_report_includes_strategy_metrics_and_sample_quality(self):
        report = self.study.report()
        self.assertEqual(report["mode"], "SHADOW_ONLY_NO_ORDERS")
        self.assertEqual(len(report["strategies"]), 5)
        self.assertIn("ADAPTIVE_RS_PULLBACK_15M", report["strategies"])
        self.assertEqual(report["strategies"]["VWAP_RECLAIM_RS_5M"]["sample_quality"], "TOO_SMALL")
        self.assertEqual(report["evaluation_coverage"]["scope"], "RETAINED_DB_ALL_DATES_NOT_DAILY_REPORT_WINDOW")
        self.assertEqual(report["evaluation_coverage"]["row_count"], 0)
        self.assertEqual(report["strategy_timeframe_contracts"]["ADAPTIVE_RS_PULLBACK_15M"],
                         {"signal_timeframe": "5m", "context_timeframe": "15m"})

    def test_a9_evaluation_report_exposes_retained_database_time_range(self):
        now_ms = int(time.time() * 1000)
        inserted = self.study._record_evaluations("DOT/USDT", [{
            "strategy_mode": "MICRO_MOMENTUM_1M", "timeframe": "1m",
            "bar_ts_ms": now_ms - 60_000, "outcome": "REJECT",
            "reason": "test_retained_history_scope", "cost_pct": 0.30,
            "post_cost_viable": False, "quote_volume_24h": 2_000_000,
        }])
        self.assertEqual(inserted, 1)
        report = self.study.report()
        coverage = report["evaluation_coverage"]
        self.assertEqual(coverage["scope"], "RETAINED_DB_ALL_DATES_NOT_DAILY_REPORT_WINDOW")
        self.assertEqual(coverage["row_count"], 1)
        self.assertIsNotNone(coverage["first_evaluated_utc"])
        self.assertIsNotNone(coverage["last_evaluated_utc"])
        self.assertEqual(report["strategies"]["MICRO_MOMENTUM_1M"]["evaluations"], 1)


if __name__ == "__main__":
    unittest.main()


def test_closed_rows_rejects_impossible_ohlc_and_duplicate_timestamps():
    from v702_intraday_shadow import _closed_rows
    idx = pd.to_datetime([1_800_000_000_000, 1_800_000_060_000], unit="ms", utc=True)
    good = pd.DataFrame({"open": [100.0, 100.0], "high": [101.0, 101.0],
                         "low": [99.0, 99.0], "close": [100.5, 100.5],
                         "volume": [10.0, 10.0]}, index=idx)
    good.attrs["as_of_ms"] = 1_800_000_300_000
    assert len(_closed_rows(good, 60_000)) == 2
    impossible = good.copy()
    impossible.iloc[0, impossible.columns.get_loc("high")] = 99.5
    impossible.attrs["as_of_ms"] = 1_800_000_300_000
    assert _closed_rows(impossible, 60_000) == []
    duplicated = good.copy()
    duplicated.index = pd.to_datetime([1_800_000_000_000, 1_800_000_000_000], unit="ms", utc=True)
    duplicated.attrs["as_of_ms"] = 1_800_000_300_000
    assert _closed_rows(duplicated, 60_000) == []


def test_closed_rows_marks_unobserved_interval_as_data_gap():
    from v702_intraday_shadow import _closed_rows
    idx = pd.to_datetime([1_800_000_000_000, 1_800_000_180_000], unit="ms", utc=True)
    frame = pd.DataFrame({"open": [100.0, 100.0], "high": [101.0, 101.0],
                          "low": [99.0, 99.0], "close": [100.5, 100.5],
                          "volume": [10.0, 10.0]}, index=idx)
    frame.attrs["as_of_ms"] = 1_800_000_300_000
    rows = _closed_rows(frame, 60_000)
    assert len(rows) == 2
    assert rows[0]["gap_before"] is False
    assert rows[1]["gap_before"] is True
