import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from v702_counterfactual_shadow import (V702CounterfactualShadow, LANES, bearish_policy_reject_observation_eligible, htf_policy_reject_observation_eligible)


class CounterfactualShadowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = {
            "V702_CF_SHADOW_ENABLE": True,
            "V702_CF_SHADOW_TIMEFRAME_SEC": 300,
            "V702_CF_SHADOW_MAX_HOLD_BARS": 12,
            "V702_CF_SHADOW_REPORT_INTERVAL_SEC": 900,
            "V702_CF_SHADOW_FEE_BPS_PER_SIDE": 10.0,
            "V702_CF_SHADOW_SLIPPAGE_BPS_PER_SIDE": 5.0,
            "V702_CF_SHADOW_MAX_ROWS": 1000,
        }
        self.study = V702CounterfactualShadow(str(self.root / "study.db"), str(self.root / "reports"), lambda: self.cfg)
        self.anchor = 1_700_000_100_000
        self.candidate = SimpleNamespace(
            symbol="TEST/USDT", family="PULLBACK", engine_id="pullback",
            strategy_mode="PULLBACK", generated_at_ms=self.anchor + 12_000,
            entry_ref=100.0, sl_price=99.0, tp1_rr=1.0,
            engine_score=0.80, features_snapshot={"quote_vol_24h": 2_000_000.0},
            macro_regime="BULLISH", local_regime="LOCAL_BULLISH", side="long",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def candles(self, rows):
        idx = pd.to_datetime([r[0] for r in rows], unit="ms", utc=True)
        return pd.DataFrame({"high": [r[1] for r in rows], "low": [r[2] for r in rows], "close": [r[3] for r in rows]}, index=idx)

    def test_schema_and_shadow_only_contract(self):
        result = self.study.self_test()
        self.assertTrue(result["pass"], result)
        self.assertEqual(set(LANES), {"BASELINE_PASS", "CURRENT_HTF_RELIEF_PASS", "HTF_RELIEF", "MID_TIER_COUNTERFACTUAL", "BEARISH_NORMAL_LSR", "BEARISH_POLICY_REJECT_OBSERVATION", "HTF_POLICY_REJECT_OBSERVATION"})
        self.assertEqual(self.study.report()["study_mode"], "SHADOW_ONLY_NO_ORDERS")

    def test_record_is_idempotent_and_forbidden_pairs_are_excluded(self):
        snap = {"quote_vol_24h": 2_000_000, "tier": "MICRO", "htf_strength": 48}
        self.assertTrue(self.study.record_candidate(self.candidate, "BASELINE_PASS", "prequal_pass", snap))
        self.assertFalse(self.study.record_candidate(self.candidate, "BASELINE_PASS", "prequal_pass", snap))
        forbidden = SimpleNamespace(**{**vars(self.candidate), "symbol": "AERO/USDT"})
        self.assertFalse(self.study.record_candidate(forbidden, "BASELINE_PASS", "prequal_pass", snap))
        with self.study._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM v702_cf_shadow_samples").fetchone()[0]
        self.assertEqual(count, 1)

    def test_tp1_outcome_uses_future_closed_bars_and_deducts_costs(self):
        self.assertTrue(self.study.record_candidate(self.candidate, "BASELINE_PASS", "prequal_pass", {"quote_vol_24h": 5_000_000}))
        future = self.anchor // 300_000 * 300_000
        frame = self.candles([
            (future, 100.2, 99.8, 100.0),
            (future + 300_000, 100.6, 99.5, 100.2),
            (future + 600_000, 101.2, 100.3, 101.0),
            (future + 900_000, 101.5, 100.5, 101.2),  # forming candle: excluded
        ])
        result = self.study.process_market_data({"TEST/USDT": {"df_5m": frame}})
        self.assertEqual(result["resolved"], 1)
        with self.study._connect() as conn:
            row = conn.execute("SELECT status,gross_r,net_r,bars_seen FROM v702_cf_shadow_samples").fetchone()
        self.assertEqual(row[0], "TP1")
        self.assertAlmostEqual(row[1], 1.0, places=6)
        self.assertLess(row[2], row[1])
        self.assertEqual(row[3], 2)

    def test_same_bar_sl_tp_is_conservatively_stop_first(self):
        self.study.record_candidate(self.candidate, "HTF_RELIEF", "htf.family_htf_strength_below_floor", {"quote_vol_24h": 5_000_000}, htf_strength=53, htf_floor=55)
        future = self.anchor // 300_000 * 300_000
        frame = self.candles([
            (future, 100.2, 99.8, 100.0),
            (future + 300_000, 101.2, 98.8, 100.0),
            (future + 600_000, 100.2, 99.8, 100.0),  # forming candle excluded
        ])
        self.study.process_market_data({"TEST/USDT": {"df_5m": frame}})
        with self.study._connect() as conn:
            row = conn.execute("SELECT status,gross_r FROM v702_cf_shadow_samples").fetchone()
        self.assertEqual(row[0], "AMBIGUOUS_SL_FIRST")
        self.assertAlmostEqual(row[1], -1.0, places=6)

    def test_report_has_lane_comparison_and_sample_size_warning(self):
        self.study.record_candidate(self.candidate, "BASELINE_PASS", "prequal_pass", {"quote_vol_24h": 5_000_000})
        self.study.record_candidate(self.candidate, "MID_TIER_COUNTERFACTUAL", "liquidity.below_tier", {"quote_vol_24h": 2_000_000})
        report = self.study.write_report()
        self.assertIn("CURRENT_HTF_RELIEF_PASS", report["comparison"])
        self.assertIn("HTF_RELIEF", report["comparison"])
        self.assertEqual(report["lanes"]["MID_TIER_COUNTERFACTUAL"]["samples"], 1)
        self.assertEqual(report["lanes"]["MID_TIER_COUNTERFACTUAL"]["sample_quality"], "EARLY_SMALL_SAMPLE")
        self.assertTrue(Path(report["report_files"]["json"]).exists())
        payload = json.loads(Path(report["report_files"]["json"]).read_text(encoding="utf-8"))
        self.assertEqual(payload["study_mode"], "SHADOW_ONLY_NO_ORDERS")

    def test_bearish_normal_lsr_lane_requires_all_strict_shadow_evidence(self):
        candidate = SimpleNamespace(
            symbol="LSRTEST/USDT", family="LIQUIDITY_SWEEP_REVERSAL", engine_id="liq_sweep",
            strategy_mode="LIQUIDITY_SWEEP_REVERSAL", generated_at_ms=self.anchor + 12_000,
            entry_ref=100.0, sl_price=99.0, tp1_rr=1.0, engine_score=0.80,
            features_snapshot={"quote_vol_24h": 5_000_000.0, "volume_ratio": 1.5, "htf_strength": 48.0, "bearish_severity": "NORMAL"},
            macro_regime="BEARISH", local_regime="LOCAL_RECOVERY", bearish_severity="NORMAL", side="long",
        )
        snap = {"quote_vol_24h": 5_000_000.0, "volume_ratio": 1.5, "htf_strength": 48.0,
                "macro_regime": "BEARISH", "bearish_severity": "NORMAL", "tier": "MICRO"}
        self.cfg.update({"V453_SCORE_FLOOR_MIN": 70.0, "LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME": 3_000_000.0,
                         "V702_A48_BEARISH_SHADOW_MIN_HTF_STRENGTH": 47.0,
                         "V702_A48_BEARISH_SHADOW_VOLUME_FLOOR_RATIO": 1.4,
                         "V702_A48_BEARISH_SHADOW_SIZE_MULTIPLIER": 0.5})
        self.assertTrue(self.study.record_candidate(candidate, "BEARISH_NORMAL_LSR",
                                                    "family_regime_disallowed.macro", snap,
                                                    htf_strength=48.0, htf_floor=47.0))
        with self.study._connect() as conn:
            row = conn.execute("SELECT lane,context_json FROM v702_cf_shadow_samples").fetchone()
        self.assertEqual(row[0], "BEARISH_NORMAL_LSR")
        ctx = json.loads(row[1])
        self.assertEqual(ctx["policy_override"], "SHADOW_ONLY_NOT_LIVE")
        self.assertEqual(ctx["hypothetical_size_multiplier"], 0.5)
        invalid = SimpleNamespace(**{**vars(candidate), "bearish_severity": "STRESSED"})
        self.assertFalse(self.study.record_candidate(invalid, "BEARISH_NORMAL_LSR",
                                                     "family_regime_disallowed.macro", snap,
                                                     htf_strength=48.0, htf_floor=47.0))
        low_volume_snap = {**snap, "volume_ratio": 1.39}
        self.assertFalse(self.study.record_candidate(candidate, "BEARISH_NORMAL_LSR",
                                                     "family_regime_disallowed.macro", low_volume_snap,
                                                     htf_strength=48.0, htf_floor=47.0))


    def test_bearish_policy_reject_observation_captures_raw_pullback_without_admission_claim(self):
        candidate = SimpleNamespace(
            **{**vars(self.candidate), "symbol": "PULLBACKTEST/USDT", "family": "PULLBACK",
               "strategy_mode": "PULLBACK", "macro_regime": "BEARISH", "bearish_severity": "STRESSED",
               "side": "long"}
        )
        snap = {
            "macro_regime": "BEARISH", "bearish_severity": "STRESSED",
            "quote_vol_24h": 2_400_000.0, "volume_ratio": 0.92,
            "htf_strength": 38.0, "allowed_regimes": ["BULLISH", "NEUTRAL"],
        }
        self.assertTrue(self.study.record_candidate(
            candidate, "BEARISH_POLICY_REJECT_OBSERVATION",
            "family_regime_disallowed.macro", snap, htf_strength=38.0,
        ))
        with self.study._connect() as conn:
            row = conn.execute("SELECT lane,reject_reason,context_json FROM v702_cf_shadow_samples").fetchone()
        self.assertEqual(row[0], "BEARISH_POLICY_REJECT_OBSERVATION")
        self.assertEqual(row[1], "family_regime_disallowed.macro")
        ctx = json.loads(row[2])
        self.assertEqual(ctx["policy_override"], "SHADOW_ONLY_NO_LIVE_AUTHORITY")
        self.assertEqual(ctx["policy_evaluation_scope"], "RAW_PREQUAL_POLICY_REJECT_OUTCOME_ONLY_NOT_FULL_PIPELINE_ADMISSION")
        self.assertTrue(ctx["counterfactual_policy_check_skipped"])
        self.assertEqual(ctx["candidate_side"], "long")
        self.assertEqual(ctx["bearish_severity"], "STRESSED")
        self.assertFalse(ctx.get("live_execution", True))

    def test_bearish_policy_reject_observation_predicate_fails_closed(self):
        eligible = {"reason": "family_regime_disallowed.macro", "side": "long", "macro_regime": "BEARISH"}
        self.assertTrue(bearish_policy_reject_observation_eligible(**eligible))
        self.assertFalse(bearish_policy_reject_observation_eligible(**{**eligible, "reason": "htf.family_htf_strength_below_floor"}))
        self.assertFalse(bearish_policy_reject_observation_eligible(**{**eligible, "side": "short"}))
        self.assertFalse(bearish_policy_reject_observation_eligible(**{**eligible, "macro_regime": "BULLISH"}))
        self.assertFalse(bearish_policy_reject_observation_eligible(**{**eligible, "side": ""}))

    def test_bearish_policy_reject_lane_not_compared_to_baseline(self):
        candidate = SimpleNamespace(
            **{**vars(self.candidate), "symbol": "BEARTEST/USDT", "family": "MTF_PULLBACK",
               "strategy_mode": "MTF_PULLBACK", "macro_regime": "BEARISH", "side": "buy"}
        )
        snap = {"macro_regime": "BEARISH", "bearish_severity": "UNKNOWN", "quote_vol_24h": 2_000_000.0}
        self.assertTrue(self.study.record_candidate(candidate, "BEARISH_POLICY_REJECT_OBSERVATION",
                                                    "family_regime_disallowed.macro", snap))
        report = self.study.report()
        self.assertNotIn("BEARISH_POLICY_REJECT_OBSERVATION", report["comparison"])
        self.assertIn("BEARISH_POLICY_REJECT_OBSERVATION", report["non_comparable_lanes"])
        self.assertFalse(report["lane_semantics"]["BEARISH_POLICY_REJECT_OBSERVATION"]["downstream_admission_claim"])
        self.assertEqual(report["lanes"]["BEARISH_POLICY_REJECT_OBSERVATION"]["bearish_severities"], {"UNKNOWN": 1})


    def test_htf_policy_reject_observation_captures_raw_floor_reject_without_admission_claim(self):
        candidate = SimpleNamespace(
            **{**vars(self.candidate), "symbol": "HTFREJECT/USDT", "family": "PULLBACK",
               "strategy_mode": "PULLBACK", "macro_regime": "NEUTRAL", "side": "long"}
        )
        snap = {"macro_regime": "NEUTRAL", "htf_strength": 40.0,
                "family_htf_floor": 55.0, "quote_vol_24h": 3_000_000.0}
        self.assertTrue(self.study.record_candidate(
            candidate, "HTF_POLICY_REJECT_OBSERVATION",
            "htf.family_htf_strength_below_floor", snap,
            htf_strength=40.0, htf_floor=55.0,
        ))
        with self.study._connect() as conn:
            row = conn.execute("SELECT lane,reject_reason,context_json FROM v702_cf_shadow_samples").fetchone()
        self.assertEqual(row[0], "HTF_POLICY_REJECT_OBSERVATION")
        self.assertEqual(row[1], "htf.family_htf_strength_below_floor")
        ctx = json.loads(row[2])
        self.assertEqual(ctx["policy_override"], "SHADOW_ONLY_NO_LIVE_AUTHORITY")
        self.assertEqual(ctx["policy_evaluation_scope"], "RAW_PREQUAL_HTF_FLOOR_REJECT_OUTCOME_ONLY_NOT_FULL_PIPELINE_ADMISSION")
        self.assertEqual(ctx["policy_reject_cohort"], "HTF_STRENGTH_FLOOR")
        self.assertTrue(ctx["counterfactual_policy_check_skipped"])
        self.assertFalse(ctx.get("live_execution", True))

    def test_htf_policy_reject_observation_predicate_fails_closed(self):
        eligible = {"reason": "htf.family_htf_strength_below_floor", "side": "buy", "macro_regime": "NEUTRAL"}
        self.assertTrue(htf_policy_reject_observation_eligible(**eligible))
        self.assertFalse(htf_policy_reject_observation_eligible(**{**eligible, "reason": "family_regime_disallowed.macro"}))
        self.assertFalse(htf_policy_reject_observation_eligible(**{**eligible, "side": "short"}))
        self.assertFalse(htf_policy_reject_observation_eligible(**{**eligible, "macro_regime": "UNKNOWN"}))

    def test_no_execution_api_in_shadow_module(self):
        source = Path(__import__("v702_counterfactual_shadow").__file__).read_text(encoding="utf-8")
        self.assertNotIn("create_market_buy_order", source)
        self.assertNotIn("create_order(", source)
        self.assertIn("AMBIGUOUS_SL_FIRST", source)
        self.assertIn("fees and configurable slippage", source.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
