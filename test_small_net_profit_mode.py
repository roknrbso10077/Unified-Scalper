from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("SCALPER_DB", os.path.join(tempfile.gettempdir(), f"v702-r40-small-net-{os.getpid()}.db"))
import main as bot


class SmallNetProfitModeTests(unittest.TestCase):
    def test_cost_model_uses_spread_floor_and_roundtrip_slippage(self):
        cfg = bot.CONFIG
        self.assertTrue(cfg.get("V702_SMALL_NET_PROFIT_MODE_ENABLE"))
        c = bot.SizingEngine.small_net_nonfee_cost_usdt(75.0, None)
        self.assertAlmostEqual(c["spread_pct_used"], 0.15, places=8)
        self.assertAlmostEqual(c["extra_cost_pct"], 0.25, places=8)  # 0.15 spread + 0.05 each side
        self.assertAlmostEqual(c["extra_cost_usdt"], 0.1875, places=8)
        higher = bot.SizingEngine.small_net_nonfee_cost_usdt(75.0, 0.30)
        self.assertAlmostEqual(higher["spread_pct_used"], 0.30, places=8)
        self.assertGreater(higher["extra_cost_usdt"], c["extra_cost_usdt"])

    def test_small_net_tp1_requires_positive_minimum_net_profit_after_costs(self):
        # 0.558% gross TP1, 0.20% commission + 0.15% spread + 0.10% slippage,
        # yields about 0.108% net. The TP2 geometry also clears blended net-R floor.
        good = bot.SizingEngine.fee_viability_detail(
            100.0, 99.6, 100.558, 100.8, 75.0,
            spread_pct=0.15, small_net_mode=True,
        )
        self.assertTrue(good.get("ok"), good)
        self.assertGreaterEqual(good.get("net_profit_pct_tp1", -99), 0.10)
        self.assertGreaterEqual(good.get("gross_tp1", 0), 2.5 * good.get("fees", 0))
        self.assertGreaterEqual(good.get("net_rr_overall", -99), 0.50)
        self.assertAlmostEqual(good.get("total_costs_usdt", 0), 0.3375, places=6)

    def test_small_net_never_accepts_target_below_net_profit_floor(self):
        result = bot.SizingEngine.fee_viability_detail(
            100.0, 99.95, 100.50, 100.8, 75.0,
            spread_pct=0.15, small_net_mode=True,
        )
        self.assertFalse(result.get("ok"), result)
        self.assertEqual(result.get("reason"), "tp1_net_profit_pct")
        self.assertLess(result.get("net_profit_pct_tp1", 999), 0.10)

    def test_wider_spread_increases_required_tp1_rr_and_can_reject_same_target(self):
        rr_base = bot.SizingEngine.small_net_required_tp1_rr(100.0, 99.6, 75.0, 0.15)
        rr_wide = bot.SizingEngine.small_net_required_tp1_rr(100.0, 99.6, 75.0, 0.30)
        self.assertGreater(rr_wide, rr_base)
        result = bot.SizingEngine.fee_viability_detail(
            100.0, 99.6, 100.558, 100.8, 75.0,
            spread_pct=0.30, small_net_mode=True,
        )
        self.assertFalse(result.get("ok"), result)

    def test_legacy_mode_keeps_original_net_rr_floors(self):
        result = bot.SizingEngine.fee_viability_detail(
            100.0, 99.0, 101.0, 103.0, 75.0, small_net_mode=False,
        )
        self.assertTrue(result.get("ok"), result)
        self.assertEqual(result.get("required_min_tp1_rr"), 0.8)
        self.assertEqual(result.get("required_min_net_rr_overall"), 1.2)
        self.assertEqual(bot.CONFIG.get("MIN_NET_RR_TP1"), 0.8)
        self.assertEqual(bot.CONFIG.get("MIN_NET_RR_OVERALL"), 1.2)

    def test_bounded_fee_rescue_uses_cost_aware_target_and_preserves_stop(self):
        ok, tp1, tp2, tp3, reason = bot.V420FeeRescue.try_expand_targets(
            100.0, 99.6, 100.4, 100.8, 102.0, 75.0, 80.0, "PULLBACK",
            spread_pct=0.15, small_net_mode=True,
        )
        self.assertTrue(ok, reason)
        self.assertGreater(tp1, 100.4)
        self.assertLessEqual((tp1 - 100.0) / 0.4, 2.0 + 1e-9)
        self.assertLessEqual((tp2 - 100.0) / 0.4, 3.2 + 1e-9)
        self.assertGreater(tp2, tp1)
        # Caller owns SL; rescue API returns only target levels and never changes SL.
        self.assertGreater(tp3, tp2)

    def test_small_net_compression_lowers_scalp_targets_only_when_economics_still_pass(self):
        result = bot.SizingEngine.small_net_compress_targets(
            100.0, 99.6, 100.8, 101.3, 101.6, 75.0,
            spread_pct=0.15, strategy_style="SCALP",
        )
        self.assertTrue(result.get("applied"), result)
        self.assertLess(result["tp1"], 100.8)
        self.assertLess(result["tp2"], 101.3)
        self.assertGreater(result["tp1"], 100.0)
        self.assertGreater(result["tp2"], result["tp1"])
        self.assertGreater(result["tp3"], result["tp2"])
        self.assertGreaterEqual(result["detail"].get("net_profit_pct_tp1", -99), 0.10)
        self.assertGreaterEqual(result["detail"].get("net_rr_overall", -99), 0.50)
        self.assertFalse(result.get("stop_loss_changed"))
        self.assertFalse(result.get("hard_gate_bypass"))

    def test_small_net_compression_skips_swing_profiles_and_unviable_plans(self):
        swing = bot.SizingEngine.small_net_compress_targets(
            100.0, 99.6, 100.8, 101.3, 101.6, 75.0,
            spread_pct=0.15, strategy_style="SWING",
        )
        self.assertFalse(swing.get("applied"), swing)
        self.assertIn("style_not_compressible", swing.get("reason", ""))
        unviable = bot.SizingEngine.small_net_compress_targets(
            100.0, 99.6, 100.2, 100.4, 100.6, 75.0,
            spread_pct=0.15, strategy_style="SCALP",
        )
        self.assertFalse(unviable.get("applied"), unviable)

    def test_small_net_compression_skips_if_target_saving_is_too_small(self):
        result = bot.SizingEngine.small_net_compress_targets(
            100.0, 99.6, 100.6, 101.2, 101.6, 75.0,
            spread_pct=0.15, strategy_style="SCALP",
        )
        # TP1 is only 1.5R, which is less than the 0.15R saving beyond
        # the computed cost-aware target in some cost configurations; in any
        # event a no-op is safer than changing a nearly-minimal target.
        self.assertFalse(result.get("applied"), result)

    def test_exit_split_sums_to_one_with_runner_enabled(self):
        total = (bot.CONFIG["TP1_EXIT_PCT"] + bot.CONFIG["TP2_EXIT_PCT"] +
                 bot.CONFIG["RUNNER_KEEP_PCT_AT_TP3"])
        self.assertAlmostEqual(total, 1.0, places=9)
        self.assertAlmostEqual(bot.CONFIG["TP1_EXIT_PCT"], 0.60, places=9)
        self.assertAlmostEqual(bot.CONFIG["TP2_EXIT_PCT"], 0.30, places=9)
        self.assertAlmostEqual(bot.CONFIG["RUNNER_KEEP_PCT_AT_TP3"], 0.10, places=9)


if __name__ == "__main__":
    unittest.main()
