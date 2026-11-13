import hashlib
import sqlite3
import tempfile
import time
from contextlib import contextmanager
import unittest
from pathlib import Path

import pandas as pd

from v702_intraday_shadow import V702IntradayShadow


class IntradayShadowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "study.db")
        self.cfg = {
            "V702_INTRADAY_SHADOW_ENABLE": True,
            "V702_INTRADAY_SHADOW_LIVE_ENABLE": False,
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
        return pd.DataFrame(rows, index=idx)

    def snapshot(self, symbol="DOT/USDT"):
        return {"symbol":symbol,"quote_vol_24h":2_000_000,"tier":"MICRO","spread_pct":None,
                "df_5m":None,"df_15m":None,"df_btc_5m":None,"df_btc_15m":None,
                "macro_regime":"NEUTRAL"}

    def test_schema_selftest_and_shadow_only(self):
        result = self.study.self_test()
        self.assertTrue(result["pass"], result)
        self.assertFalse(self.cfg["V702_INTRADAY_SHADOW_LIVE_ENABLE"])

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
        result = self.study.process_symbol("DOT/USDT", frame, self.snapshot())
        with self.connect() as conn:
            status, net_r = conn.execute("SELECT status,net_r FROM v702_intraday_shadow_samples WHERE strategy_mode='MICRO_MOMENTUM_1M'").fetchone()
        self.assertEqual(status, "TP1")
        self.assertIsNotNone(net_r)
        self.assertGreater(net_r, -5.0)

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

    def test_report_includes_strategy_metrics_and_sample_quality(self):
        report = self.study.report()
        self.assertEqual(report["mode"], "SHADOW_ONLY_NO_ORDERS")
        self.assertEqual(len(report["strategies"]), 4)
        self.assertEqual(report["strategies"]["VWAP_RECLAIM_RS_5M"]["sample_quality"], "TOO_SMALL")


if __name__ == "__main__":
    unittest.main()
