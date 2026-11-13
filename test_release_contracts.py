from __future__ import annotations

import asyncio
import os
import tempfile
import contextlib
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ["SCALPER_DB"] = os.path.join(tempfile.gettempdir(), f"v702-offline-tests-{os.getpid()}.db")
import main as bot

ROOT = Path(__file__).resolve().parent


class CanonicalReleaseContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # This log is immutable historical A51 evidence; it is not presented as
        # validation of the active A52 patch. A52 has separate focused regression
        # evidence and keeps live integration / profitability explicitly unverified.
        historical_validation_log = ROOT / "RESULTS__V702_A51_VALIDATE_ONLY.log"
        # Clean release archives intentionally exclude runtime logs and generated
        # validation output. Historical evidence is parsed only when explicitly
        # present; its absence is not a release-test setup failure.
        cls.validation_text = historical_validation_log.read_text(encoding="utf-8") if historical_validation_log.is_file() else ""
        machine_lines = [line for line in cls.validation_text.splitlines() if line.startswith('{"pass"')]
        cls.validation_error = "SKIPPED: historical A51 log is not packaged in the clean source release"
        cls.validation_json = None
        if machine_lines:
            try:
                cls.validation_json = json.loads(machine_lines[-1])
                cls.validation_error = ""
            except Exception as exc:
                cls.validation_error = f"cannot parse final validation JSON: {type(exc).__name__}: {exc}"
        cls.validate_exit = (0 if cls.validation_json.get("pass") is True else 1) if cls.validation_json is not None else None

    def test_only_one_canonical_executable_is_packaged(self):
        self.assertTrue((ROOT / "main.py").is_file())
        self.assertFalse((ROOT / "main_combined_V702_FINAL.py").exists())
        self.assertFalse((ROOT / "main_combined_V699_FINAL.py").exists())
        source = (ROOT / "main.py").read_bytes()
        manifest = json.loads((ROOT / "FINAL_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest.get("canonical_executable"), "main.py")
        self.assertEqual(manifest.get("canonical_main_sha256"), hashlib.sha256(source).hexdigest())
        self.assertFalse(manifest.get("byte_identical_canonical_copy"), "duplicate runtime must not be packaged")
        self.assertTrue((ROOT / "HISTORICAL_A53_main.py.baseline").is_file())
        # The runtime-policy identity remains pinned to A10 for its historical
        # self-test contract; the distribution's active revision is separate.
        self.assertEqual(bot.FINAL_CANONICAL_RUNTIME.get("canonical_package_revision"), bot.V702_A10_CANONICAL_REVISION)
        self.assertEqual(bot.FINAL_CANONICAL_RUNTIME.get("active_package_revision"), bot.V702_PACKAGE_AUDIT_REVISION)
        self.assertEqual(bot.FINAL_CANONICAL_RUNTIME.get("package_audit_revision"), bot.V702_PACKAGE_AUDIT_REVISION)
        self.assertEqual(bot.FINAL_CANONICAL_RUNTIME.get("active_release_tag"), "UNIFIED-SCALPER-V702-A59-CANONICAL-FINAL")


    def test_a59_bearish_policy_reject_observer_is_shadow_only_and_release_current(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertEqual(bot.V702_FINAL_CANONICAL_RELEASE, "UNIFIED-SCALPER-V702-A59-CANONICAL-FINAL")
        self.assertIn("BEARISH_POLICY_REJECT_OBSERVATION", source)
        self.assertIn("CF_SHADOW_POLICY_REJECT enabled=", source)
        self.assertTrue(bot.CONFIG.get("V702_CF_SHADOW_POLICY_REJECT_OBSERVE_ENABLE"))
        self.assertFalse(bot.CONFIG.get("V702_A48_BEARISH_V518_LIVE_ENABLE", True))
        self.assertFalse(bot.FINAL_CANONICAL_RUNTIME.get("hard_gate_bypass", True))
        self.assertFalse(bot.FINAL_CANONICAL_RUNTIME.get("live_gates_relaxed", True))
        self.assertEqual(bot.FINAL_CANONICAL_RUNTIME.get("production_decision"), "NO_GO_UNATTENDED_LIVE")
        self.assertTrue(bot._v702_a59_self_test().get("pass"))

    def test_a59_bearish_recovery_has_explicit_fail_closed_canonical_policy(self):
        # The dedicated V425 route may pass only with its own Bearish local
        # confirmation and non-crash severity; ordinary PULLBACK stays blocked.
        ok, reason, _ = bot.FamilyPolicyLayer.regime_policy_detail(
            "PULLBACK", "BEARISH", strategy_mode="BEARISH_RECOVERY",
            local_regime="RECOVERY", market_phase="PULLBACK",
            severity="BEARISH_NORMAL", strategy_style="SCALP")
        self.assertTrue(ok, reason)

        no_local, local_reason, _ = bot.FamilyPolicyLayer.regime_policy_detail(
            "PULLBACK", "BEARISH", strategy_mode="BEARISH_RECOVERY",
            local_regime="", market_phase="PULLBACK",
            severity="BEARISH_NORMAL", strategy_style="SCALP")
        self.assertFalse(no_local)
        self.assertEqual(local_reason, "local")

        wrong_local, wrong_reason, _ = bot.FamilyPolicyLayer.regime_policy_detail(
            "PULLBACK", "BEARISH", strategy_mode="BEARISH_RECOVERY",
            local_regime="BEARISH", market_phase="PULLBACK",
            severity="BEARISH_NORMAL", strategy_style="SCALP")
        self.assertFalse(wrong_local)
        self.assertEqual(wrong_reason, "local")

        crash, crash_reason, _ = bot.FamilyPolicyLayer.regime_policy_detail(
            "PULLBACK", "BEARISH", strategy_mode="BEARISH_RECOVERY",
            local_regime="RECOVERY", market_phase="PULLBACK",
            severity="BEARISH_CRASH", strategy_style="SCALP")
        self.assertFalse(crash)
        self.assertEqual(crash_reason, "severity")

        ordinary, ordinary_reason, _ = bot.FamilyPolicyLayer.regime_policy_detail(
            "PULLBACK", "BEARISH", strategy_mode="PULLBACK",
            local_regime="RECOVERY", market_phase="PULLBACK",
            severity="BEARISH_NORMAL", strategy_style="SCALP")
        self.assertFalse(ordinary)
        self.assertEqual(ordinary_reason, "macro")

    def test_a59_prequal_hook_observes_bearish_pullback_reject_without_changing_verdict(self):
        from types import SimpleNamespace
        original_prequal = bot._V702_CF_ORIGINAL_PREQUAL
        original_submit = bot._v702_cf_shadow_submit
        original_forbidden = bot._v587_is_forbidden_coin
        original_context = bot._v455_prequal_context
        original_enable = bot.CONFIG.get("V702_CF_SHADOW_ENABLE", True)
        original_observe = bot.CONFIG.get("V702_CF_SHADOW_POLICY_REJECT_OBSERVE_ENABLE", True)
        captured = []
        candidate = SimpleNamespace(
            symbol="PULLBACK-A59/USDT", family="PULLBACK", strategy_mode="PULLBACK",
            strategy_style="SCALP", side="long", macro_regime="BEARISH",
            bearish_severity="NORMAL", generated_at_ms=1_700_000_100_000,
            entry_ref=100.0, sl_price=99.0, tp1_rr=1.0,
            engine_score=0.80,
            features_snapshot={"htf_strength": 39.0, "quote_vol_24h": 2_400_000.0, "volume_ratio": 0.9},
        )
        try:
            bot._V702_CF_ORIGINAL_PREQUAL = lambda _r, _s: (False, "family_regime_disallowed.macro")
            bot._v587_is_forbidden_coin = lambda _symbol: (False, "allowed")
            bot._v455_prequal_context = lambda _candidate, _snap: {
                "regime": "BEARISH", "severity": "NORMAL", "htf_strength": 39.0,
                "allowed_regimes": ["BULLISH", "NEUTRAL"],
            }
            bot.CONFIG["V702_CF_SHADOW_ENABLE"] = True
            bot.CONFIG["V702_CF_SHADOW_POLICY_REJECT_OBSERVE_ENABLE"] = True
            bot._v702_cf_shadow_submit = lambda fn, *args, **kwargs: captured.append((fn, args, kwargs))
            verdict = bot._V702_CF_SHADOW_PREQUAL_WRAPPER(SimpleNamespace(candidate=candidate), {
                candidate.symbol: {"macro_regime": "BEARISH", "bearish_severity": "NORMAL",
                                   "htf_strength": 39.0, "quote_vol_24h": 2_400_000.0,
                                   "volume_ratio": 0.9}
            })
            self.assertEqual(verdict, (False, "family_regime_disallowed.macro"))
            self.assertEqual(len(captured), 1)
            self.assertEqual(captured[0][1][1], "BEARISH_POLICY_REJECT_OBSERVATION")
            self.assertEqual(captured[0][1][2], "family_regime_disallowed.macro")
        finally:
            bot._V702_CF_ORIGINAL_PREQUAL = original_prequal
            bot._v702_cf_shadow_submit = original_submit
            bot._v587_is_forbidden_coin = original_forbidden
            bot._v455_prequal_context = original_context
            bot.CONFIG["V702_CF_SHADOW_ENABLE"] = original_enable
            bot.CONFIG["V702_CF_SHADOW_POLICY_REJECT_OBSERVE_ENABLE"] = original_observe


    def test_a59_prequal_hook_observes_htf_reject_without_changing_verdict(self):
        original_prequal = bot._V702_CF_ORIGINAL_PREQUAL
        original_submit = bot._v702_cf_shadow_submit
        original_forbidden = bot._v587_is_forbidden_coin
        original_context = bot._v455_prequal_context
        original_enable = bot.CONFIG.get("V702_CF_SHADOW_ENABLE", True)
        original_observe = bot.CONFIG.get("V702_CF_SHADOW_HTF_REJECT_OBSERVE_ENABLE", True)
        captured = []
        candidate = SimpleNamespace(
            symbol="HTF-A59/USDT", family="PULLBACK", strategy_mode="PULLBACK",
            strategy_style="SCALP", side="long", macro_regime="NEUTRAL",
            generated_at_ms=1_700_000_100_000, entry_ref=100.0, sl_price=99.0, tp1_rr=1.0,
            engine_score=0.80, features_snapshot={"htf_strength": 40.0, "quote_vol_24h": 3_500_000.0},
        )
        try:
            bot._V702_CF_ORIGINAL_PREQUAL = lambda _r, _s: (False, "htf.family_htf_strength_below_floor")
            bot._v587_is_forbidden_coin = lambda _symbol: (False, "allowed")
            bot._v455_prequal_context = lambda _candidate, _snap: {
                "regime": "NEUTRAL", "htf_strength": 40.0, "effective_htf_floor": 55.0,
            }
            bot.CONFIG["V702_CF_SHADOW_ENABLE"] = True
            bot.CONFIG["V702_CF_SHADOW_HTF_REJECT_OBSERVE_ENABLE"] = True
            bot._v702_cf_shadow_submit = lambda fn, *args, **kwargs: captured.append((fn, args, kwargs))
            verdict = bot._V702_CF_SHADOW_PREQUAL_WRAPPER(SimpleNamespace(candidate=candidate), {
                candidate.symbol: {"macro_regime": "NEUTRAL", "htf_strength": 40.0,
                                   "family_htf_floor": 55.0, "quote_vol_24h": 3_500_000.0}
            })
            self.assertEqual(verdict, (False, "htf.family_htf_strength_below_floor"))
            htf_rows = [item for item in captured if item[1][1] == "HTF_POLICY_REJECT_OBSERVATION"]
            self.assertEqual(len(htf_rows), 1)
            self.assertEqual(htf_rows[0][1][2], "htf.family_htf_strength_below_floor")
            # The 15-point shortfall is deliberately outside the narrow 3-point
            # HTF_RELIEF lane, proving broad observer coverage is independent.
            self.assertFalse(any(item[1][1] == "HTF_RELIEF" for item in captured))
        finally:
            bot._V702_CF_ORIGINAL_PREQUAL = original_prequal
            bot._v702_cf_shadow_submit = original_submit
            bot._v587_is_forbidden_coin = original_forbidden
            bot._v455_prequal_context = original_context
            bot.CONFIG["V702_CF_SHADOW_ENABLE"] = original_enable
            bot.CONFIG["V702_CF_SHADOW_HTF_REJECT_OBSERVE_ENABLE"] = original_observe

    def test_btc4h_history_fetch_diagnostics_are_visible_in_heartbeat(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('BTC4H_FETCH=raw:', source)
        self.assertIn('closed_rows_available', source)
        self.assertIn('page_recovery_ok', source)
        self.assertIn('since=_since, limit=_limit', source)

    def test_route_orderbook_error_reason_is_diagnostic_bounded_and_redacted(self):
        token = bot._v703_route_orderbook_error_token(
            TypeError("malformed orderbook api_key=SECRET https://example.invalid/book?token=SECRET")
        )
        self.assertTrue(token.startswith("TypeError:"), token)
        self.assertIn("malformed_orderbook", token)
        self.assertNotIn("SECRET", token)
        self.assertNotIn("example.invalid", token)
        self.assertNotRegex(token, r"\s")
        self.assertLessEqual(len(token.split(":", 1)[-1]), 96)
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('route_orderbook_unverifiable:{_r35_error_token}', source)
        self.assertIn('v703_last_route_orderbook_error_token', source)

    def test_a12_projection_changes_are_wired_and_gate_preserving(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("_v702_r5_projection_disposition", source)
        self.assertIn("INCOMPLETE_KEEP_CANONICAL_RANK", source)
        self.assertIn("EXACT_UNDERFLOOR", source)
        self.assertIn("V702_R30_MICRO_RECALL_FAILED_RETRY_SEC", source)
        self.assertIn("_v702_r30_note_scan_result(_symbol, False)", source)
        self.assertIn('"v702_a12_selection_projection_validation": _v702_a12_report', source)
        self.assertFalse(bot.FINAL_CANONICAL_RUNTIME.get("hard_gate_bypass", True))
        self.assertTrue(bot._v702_a12_selection_projection_self_test().get("pass"))

    def test_route_projection_defers_incomplete_score_to_builder(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("if _v702_exact_route_projection_hard_block_allowed(", source)
        self.assertIn("projection_incomplete_or_stale_deferred_to_builder", source)
        self.assertIn('STATS["v703_route_projection_incomplete_deferred"]', source)
        self.assertIn('"candidate_object_id": id(c)', source)
        self.assertIn('status.get("complete") is not True', source)

    def test_micro_route_orderbook_handoff_uses_three_argument_contract(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        start = source.index("V703-R35 FINAL ROUTE SCORE/LIQUIDITY HANDOFF CLOSURE")
        end = source.index("# Re-project the exact canonical score", start)
        route_block = source[start:end]
        self.assertIn("_v45_orderbook_confirmation(\n                                    _r35_ob, _r35_ob_context, _r35_tier", route_block)
        self.assertNotIn("_v45_orderbook_confirmation(_route.candidate, md)", route_block)
        self.assertIn('"spread_pct": float(_r35_spread_pct)', route_block)
        self.assertIn('"depth_ratio": 0.0', route_block)  # Derive depth from the exact fetched book.
        self.assertIn('"volume_ratio": float(_r35_fs.get("volume_ratio", md.get("volume_ratio", 0.0)) or 0.0)', route_block)
        # Exercise the helper contract with a synthetic but valid MICRO book. The
        # zero depth_ratio must trigger computation from these fresh bid levels.
        ok, reason = bot._v45_orderbook_confirmation(
            {"bids": [[99.95, 10.0], [99.90, 4.0]], "asks": [[100.05, 1.0], [100.10, 1.0]]},
            {"spread_pct": 0.10, "depth_ratio": 0.0, "volume_ratio": 1.20,
             "structure_confidence": 70.0, "structure_quality": 70.0, "chase_atr": 0.40},
            "MICRO",
        )
        self.assertTrue(ok, reason)

    def test_incomplete_exact_projection_is_deferred_but_complete_low_projection_blocks(self):
        candidate = SimpleNamespace(symbol="TEST/USDT", family="PULLBACK")
        now = bot.WALL_NOW()
        base = {
            "score": 42.0, "complete": False, "symbol": "TEST/USDT",
            "candidate_object_id": id(candidate), "cycle_id": "C1", "candidate_id": "X1",
            "candle_ts": "T1", "ts": now, "notes": ["d1_unavailable"],
        }
        with patch.dict(bot.__dict__, {"_V702_R34_PROJECTION_STATUS": {"TEST/USDT": dict(base)}}, clear=False):
            self.assertFalse(bot._v702_exact_route_projection_hard_block_allowed(candidate, {"cycle_id":"C1", "candidate_id":"X1", "candle_ts":"T1"}, 42.0, 70.0))
            complete = dict(base, complete=True)
            with patch.dict(bot.__dict__, {"_V702_R34_PROJECTION_STATUS": {"TEST/USDT": complete}}, clear=False):
                self.assertTrue(bot._v702_exact_route_projection_hard_block_allowed(candidate, {"cycle_id":"C1", "candidate_id":"X1", "candle_ts":"T1"}, 42.0, 70.0))
                stale = dict(complete, ts=now-120.0)
                with patch.dict(bot.__dict__, {"_V702_R34_PROJECTION_STATUS": {"TEST/USDT": stale}}, clear=False):
                    self.assertFalse(bot._v702_exact_route_projection_hard_block_allowed(candidate, {"cycle_id":"C1", "candidate_id":"X1", "candle_ts":"T1"}, 42.0, 70.0))
                wrong_cycle = dict(complete, cycle_id="C2")
                with patch.dict(bot.__dict__, {"_V702_R34_PROJECTION_STATUS": {"TEST/USDT": wrong_cycle}}, clear=False):
                    self.assertFalse(bot._v702_exact_route_projection_hard_block_allowed(candidate, {"cycle_id":"C1", "candidate_id":"X1", "candle_ts":"T1"}, 42.0, 70.0))

    def test_micro_recall_warm_pool_stratifies_bounded_sample(self):
        old_history = dict(bot._V702_R30_MICRO_SCAN_HISTORY)
        try:
            bot._V702_R30_MICRO_SCAN_HISTORY = {}
            tickers = {f"C{i:02d}/USDT": {"quoteVolume": 1_100_000 + i*90_000, "last": 1.0} for i in range(12)}
            markets = {sym: {"quote":"USDT", "spot":True, "active":True} for sym in tickers}
            with patch.object(bot, "_v587_is_forbidden_coin", return_value=(False, "test"), create=True):
                selected, meta = bot._v702_r30_select_micro_symbols(tickers, markets, set(), 4, now=10_000.0)
            self.assertEqual(meta["eligible_rows"], 12)
            self.assertEqual(meta["warm_pool"], 12)
            self.assertEqual(meta["selected"], 4)
            self.assertEqual(meta["selection_mode"], "STRATIFIED_WARM_POOL")
            eligible_order = [f"C{i:02d}/USDT" for i in range(11, -1, -1)]
            positions = [eligible_order.index(sym) for sym in selected]
            self.assertGreater(positions[-1]-positions[0], 4, selected)
        finally:
            bot._V702_R30_MICRO_SCAN_HISTORY = old_history

    def test_r40_small_net_live_pilot_and_truthful_entry_status_closure_present(self):
        guard = (ROOT / "production_guardrails.py").read_text(encoding="utf-8")
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "FINAL_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertIn('cfg.setdefault("V702_LIVE_PILOT_ENABLE", True)', guard)
        self.assertIn('UNIFIED_LIVE_PILOT_ENABLE', guard)
        self.assertIn('UNIFIED_A55_LIVE_ARM', source)
        self.assertIn('operator_armed = bool(callable(arm_check) and arm_check())', guard)
        self.assertIn('policy = "USER_REQUESTED_LIVE_PILOT"', guard)
        self.assertIn('"BLOCKED:MONITOR_ONLY"', source)
        self.assertIn('V702_PACKAGE_AUDIT_REVISION = "V702-R40-SMALL-NET-PROFIT-COST-AWARE-TARGETS', source)
        self.assertIn('Package: {V702_PACKAGE_AUDIT_REVISION}', source)
        self.assertIn('V702-R40-SMALL-NET-PROFIT-COST-AWARE-TARGETS', manifest.get("package_audit_revision", manifest.get("canonical_revision", "")))
        self.assertEqual(manifest.get("runtime", {}).get("entry_policy", {}).get("hard_environment_off_switch"),
                         "UNIFIED_LIVE_PILOT_ENABLE=0")

    def test_a15_live_pilot_and_final_authorizer_share_one_policy_authority(self):
        guard = (ROOT / "production_guardrails.py").read_text(encoding="utf-8")
        self.assertIn("refresh_mode = ns.get(\"_V702_R39_REFRESH_ENTRY_MODE\")", guard)
        self.assertIn("monitor_only = bool(refresh_mode())", guard)
        self.assertIn("_v702_a15_canonical_policy_parity = True", guard)
        self.assertIn("_V702_R39_AUTHORIZATION_POLICY_PARITY", guard)
        self.assertIn("UNIFIED_LIVE_PILOT_ENABLE", guard)
        self.assertIn("V702_A15_CANONICAL_REVISION", (ROOT / "main.py").read_text(encoding="utf-8"))

    def test_docker_copies_nested_requirements_constraints_before_install(self):
        docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY requirements.txt requirements-lock.txt /app/", docker)
        self.assertIn("--require-hashes -r /app/requirements-lock.txt", docker)
        self.assertIn("grep -q -- \"--hash=sha256:\" /app/requirements-lock.txt", docker)
        self.assertIn("ARG STRICT_HASH_LOCK=0", docker)
        self.assertIn("STRICT_HASH_LOCK=1", (ROOT / ".github/workflows/a58-production-audit.yml").read_text(encoding="utf-8"))
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("-r requirements.in", requirements)

    def test_counterfactual_shadow_module_is_packaged_and_runtime_wired(self):
        self.assertTrue((ROOT / "v702_counterfactual_shadow.py").is_file())
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("from v702_counterfactual_shadow import V702CounterfactualShadow", source)
        self.assertIn("CURRENT_HTF_RELIEF_PASS", source)
        self.assertIn("HTF_RELIEF", source)
        self.assertIn("MID_TIER_COUNTERFACTUAL", source)
        self.assertIn("v702_counterfactual_shadow.py", docker)
        self.assertTrue((ROOT / "v702_intraday_shadow.py").is_file())
        self.assertIn("from v702_intraday_shadow import V702IntradayShadow", source)
        self.assertIn("V702_INTRADAY_SHADOW_LIVE_ENABLE", source)
        self.assertIn("VWAP_RECLAIM_RS_5M", (ROOT / "v702_intraday_shadow.py").read_text(encoding="utf-8"))

    def test_a9_intraday_research_batch_is_nonblocking_and_shadow_only(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        module = (ROOT / "v702_intraday_shadow.py").read_text(encoding="utf-8")
        self.assertIn("asyncio.create_task(_v702_intraday_process_batch", source)
        self.assertIn("previous bounded batch still active; skipping cycle to prevent overlap", source)
        self.assertIn("V702_INTRADAY_SHADOW_LIVE_ENABLE", source)
        self.assertIn("asyncio.wait(_tasks, timeout=_budget)", source)
        self.assertIn('"higher_timeframe_bullish_required":False', module)
        self.assertIn("btc_15m_crash_guard", module)
        self.assertNotIn("exchange.create_order", module)
        self.assertIn('"live_execution":False', module)

    def test_historical_a51_validate_only_record_is_valid_and_not_mislabeled_as_a52(self):
        if self.validation_json is None:
            self.skipTest(self.validation_error)
        self.assertEqual(self.validate_exit, 0, self.validation_error or json.dumps(self.validation_json, ensure_ascii=False, default=str)[-8000:])
        self.assertIsNotNone(self.validation_json, "no machine-readable historical validation JSON found")
        result = self.validation_json
        self.assertTrue(result.get("pass"), result)
        r39 = result.get("v702_r39_guardrails", {})
        self.assertTrue(r39.get("installed"), r39)
        self.assertTrue(r39.get("base_release_contract_pass"), r39)
        self.assertEqual(r39.get("default_entry_policy"), "MONITOR_ONLY_NO_NEW_BUYS")
        self.assertTrue(r39.get("portfolio_drawdown_guard_enabled"), r39)
        self.assertTrue(r39.get("expansion_shadow_enabled"), r39)
        a6 = result.get("v702_a6_complete_projection_micro_rotation", {})
        self.assertTrue(a6.get("pass"), a6)
        a7 = result.get("v702_a7_final_validation", {})
        self.assertTrue(a7.get("pass"), a7)
        self.assertFalse(a7.get("hard_gate_bypass", True), a7)
        # The A51 log must match the pre-A52 compatibility chain, not the active
        # A52 release. Avoid treating a historical validate-only pass as A52 proof.
        historical_revision = bot.V702_PACKAGE_AUDIT_REVISION.rsplit(
            "-A52-SAFETY-HARDENING-AND-CANONICAL-OUTCOME-COHERENCE-2026-10-21-A53-EXECUTION-TELEGRAM-SWING-CLOSURE-2026-10-21", 1
        )[0]
        active_revision = historical_revision
        self.assertEqual(result.get("canonical_package_revision"), historical_revision)
        self.assertEqual(result.get("active_package_revision"), historical_revision)
        self.assertEqual(result.get("canonical_runtime_revision"), historical_revision)
        self.assertEqual(result.get("package_audit_revision"), historical_revision)
        self.assertTrue(historical_revision.startswith(bot.V702_A36_CANONICAL_REVISION + "-A37-"))
        self.assertTrue(bot.V702_PACKAGE_AUDIT_REVISION.endswith(
            "-A52-SAFETY-HARDENING-AND-CANONICAL-OUTCOME-COHERENCE-2026-10-21-A53-EXECUTION-TELEGRAM-SWING-CLOSURE-2026-10-21"))
        self.assertTrue(bot.FINAL_CANONICAL_RUNTIME.get("a52_safety_hardening", {}).get("non_finite_score_inputs_fail_closed"))
        self.assertFalse(bot.FINAL_CANONICAL_RUNTIME.get("a52_safety_hardening", {}).get("hard_gate_bypass", True))
        self.assertTrue(result.get("v702_a40_live_entry_block_diagnostics_self_test", {}).get("pass"), result.get("v702_a40_live_entry_block_diagnostics_self_test"))
        self.assertFalse(result.get("a40_production_audit_closure", {}).get("diagnostics_can_clear_entry_block", True))
        self.assertTrue(result.get("v702_a41_execution_intent_reconciliation_self_test", {}).get("pass"), result.get("v702_a41_execution_intent_reconciliation_self_test"))
        a41 = result.get("a41_production_audit_closure", {})
        self.assertTrue(a41.get("only_terminal_zero_fill_auto_resolved"), a41)
        self.assertTrue(a41.get("unresolved_fill_or_unknown_states_remain_blocked"), a41)
        self.assertFalse(a41.get("hard_gate_bypass", True), a41)
        a42_self = result.get("v702_a42_mock_intent_isolation_self_test", {})
        self.assertTrue(a42_self.get("pass"), a42_self)
        self.assertFalse(a42_self.get("hard_gate_bypass", True), a42_self)
        isolation = result.get("v702_a42_selftest_db_isolation", {})
        self.assertTrue(isolation.get("pass"), isolation)
        a43 = result.get("a43_production_audit_closure", {})
        self.assertEqual(a43.get("revision"), bot.V702_A43_CANONICAL_REVISION)
        self.assertTrue(a43.get("four_hour_breakdown_alone_classified_stressed"), a43)
        self.assertTrue(a43.get("missing_or_invalid_macro_data_fail_closed"), a43)
        self.assertTrue(a43.get("depth_zero_sentinel_derived_only_from_fresh_provenance_stamped_book"), a43)
        self.assertFalse(a43.get("hard_gate_bypass", True), a43)
        self.assertTrue(result.get("v702_a43_crash_depth_self_test", {}).get("pass"), result.get("v702_a43_crash_depth_self_test"))
        a44 = result.get("a44_production_audit_closure", {})
        self.assertEqual(a44.get("revision"), bot.V702_A44_CANONICAL_REVISION)
        self.assertEqual(a44.get("superseded_by"), active_revision)
        self.assertTrue(result.get("v702_a45_terminal_self_test", {}).get("pass"), result.get("v702_a45_terminal_self_test"))
        self.assertEqual(float(a44.get("live_score_floor", 0.0)), 70.0)
        self.assertFalse(a44.get("hard_gate_bypass", True), a44)
        self.assertFalse(a44.get("live_gates_relaxed", True), a44)
        self.assertEqual(a44.get("live_integration_gate"), "NO_GO_UNTIL_CONTROLLED_LIVE_INTEGRATION_EVIDENCE")
        self.assertFalse(isolation.get("production_db_write_possible", True), isolation)
        self.assertFalse(isolation.get("live_gates_relaxed", True), isolation)
        a42 = result.get("a42_production_audit_closure", {})
        self.assertTrue(a42.get("boot_execution_selftests_use_disposable_database"), a42)
        self.assertTrue(a42.get("known_mock_intents_quarantined_from_live_reconciliation_not_deleted"), a42)
        self.assertFalse(a42.get("production_db_write_possible_during_selftest", True), a42)
        self.assertTrue(result.get("v702_a35_projection_htf_terminal_self_test", {}).get("pass"), result.get("v702_a35_projection_htf_terminal_self_test"))
        self.assertIn("A21-LIVE-PILOT-RELEASE-TIA-SUBMIT-HOLD-CLOSURE", result.get("package_audit_revision", ""))
        a13 = result.get("v702_a13_bottleneck_validation", {})
        self.assertTrue(a13.get("pass"), a13)
        self.assertFalse(a13.get("failed"), a13)
        self.assertFalse(a13.get("hard_gate_bypass", True), a13)
        self.assertFalse(a13.get("live_gates_relaxed", True), a13)
        a14 = result.get("v702_a14_selective_quality_relief_validation", {})
        self.assertTrue(a14.get("pass"), a14)
        self.assertFalse(a14.get("failed"), a14)
        self.assertFalse(a14.get("hard_gate_bypass", True), a14)
        self.assertFalse(a14.get("execution_policy_changed", True), a14)
        self.assertEqual(a14.get("global_score_floor"), 70.0)
        a16 = result.get("v702_a16_bottleneck_relief_validation", {})
        self.assertTrue(a16.get("pass"), a16)
        self.assertFalse(a16.get("failed"), a16)
        self.assertFalse(a16.get("hard_gate_bypass", True), a16)
        self.assertEqual(a16.get("global_score_floor"), 70.0)
        self.assertTrue(result.get("v702_a16_final_validation", {}).get("pass"), result.get("v702_a16_final_validation"))
        a17 = result.get("v702_a17_production_self_test", {})
        self.assertTrue(a17.get("pass"), a17)
        self.assertFalse(a17.get("failed"), a17)
        self.assertFalse(a17.get("hard_gate_bypass", True), a17)
        self.assertFalse(a17.get("gates_relaxed", True), a17)
        self.assertTrue(result.get("v702_a17_final_validation", {}).get("pass"), result.get("v702_a17_final_validation"))
        a15 = result.get("v702_a15_entry_authority_parity_validation", {})
        self.assertTrue(a15.get("pass"), a15)
        self.assertFalse(a15.get("failed"), a15)
        self.assertFalse(a15.get("hard_gate_bypass", True), a15)
        self.assertTrue(a15.get("execution_policy_changed"), a15)
        self.assertEqual(a15.get("execution_policy_change_scope"), "ENTRY_AUTHORIZATION_PARITY_ONLY")
        a10 = result.get("v702_a10_strategy_aware_htf_validation", {})
        self.assertTrue(a10.get("pass"), a10)
        self.assertEqual(len(a10.get("checks", {})), 17)
        self.assertTrue(all(v is True for v in (a10.get("checks") or {}).values()), a10.get("failed"))
        self.assertFalse(a10.get("failed"))
        self.assertTrue(a10["checks"].get("macro_context_240_closed_bar_floor_fails_closed"), a10)
        self.assertTrue(a10["checks"].get("canonical_runtime_metadata_stays_on_a10"), a10)
        a8 = result.get("v702_a8_final_validation", {})
        self.assertTrue(a8.get("pass"), a8)
        self.assertFalse(a8.get("hard_gate_bypass", True), a8)
        self.assertEqual(len(a8.get("checks", {})), 11)
        self.assertTrue(all(v is True for v in a8.get("checks", {}).values()), a8.get("failed"))
        self.assertTrue(a6.get("incomplete_projection_defers_to_builder"), a6)
        self.assertTrue(a6.get("micro_warm_pool_selector_installed"), a6)
        self.assertTrue(a6.get("micro_zero_selection_diagnostics_installed"), a6)
        self.assertTrue(a6.get("hard_gate_bypass_false"), a6)
        cf = result.get("v702_counterfactual_shadow", {})
        self.assertTrue(cf.get("installed"), cf)
        self.assertTrue(cf.get("enabled"), cf)
        self.assertEqual(cf.get("mode"), "SHADOW_ONLY_NO_ORDERS")
        self.assertFalse(cf.get("live_gates_changed"), cf)
        self.assertTrue(cf.get("prequal_hook"), cf)
        self.assertTrue(cf.get("closed_candle_hook"), cf)
        symbol_fix = result.get("v702_r39_symbol_attribution_fix", {})
        self.assertTrue(symbol_fix.get("installed"), symbol_fix)
        self.assertEqual(symbol_fix.get("scope"), "TELEGRAM_DIGEST_SYMBOL_DISPLAY_ONLY")
        self.assertFalse(symbol_fix.get("execution_policy_changed"), symbol_fix)
        self.assertEqual(result.get("runtime_identity"), "4.5.99-V702-R40-SMALL-NET-PROFIT-CANONICAL")
        self.assertEqual(result.get("canonical_runtime_revision"), active_revision)
        a3 = result.get("v702_a3_pipeline_telegram_closure", {})
        self.assertTrue(a3.get("pass"), a3)
        self.assertEqual(a3.get("telegram_digest_interval_seconds"), 1800.0)
        self.assertFalse(a3.get("live_gates_changed", True))
        small_net = result.get("v702_small_net_profit_model", {})
        self.assertTrue(small_net.get("pass"), small_net)
        self.assertFalse(small_net.get("live_gates_relaxed", True), small_net)
        self.assertAlmostEqual(small_net.get("minimum_net_profit_tp1_pct", 0), 0.10, places=9)
        self.assertTrue(small_net.get("target_compression_enabled"), small_net)
        self.assertEqual(small_net.get("target_compression_style_scope"), ["SCALP", "SCALPING", "INTRADAY", "DAY", "DAY_TRADE", "DAYTRADE"])
        self.assertAlmostEqual(small_net.get("target_compression_min_saving_r", 0), 0.15, places=9)
        self.assertTrue(small_net.get("checks", {}).get("small_net_prequal_fee_gate_cost_aware"), small_net)
        self.assertTrue(small_net.get("checks", {}).get("small_net_final_geometry_fee_gate_cost_aware"), small_net)
        self.assertIn("if not _compression_family_ok or not _sr_compress_ok", (ROOT / "main.py").read_text(encoding="utf-8"))
        r36 = result.get("v702_r36_final_validation", {})
        r37 = result.get("v702_r37_final_validation", {})
        sr = result.get("v702_sr_target_final_validation", {})
        self.assertTrue(r36.get("pass"), r36.get("failed"))
        self.assertTrue(r37.get("pass"), r37.get("failed"))
        self.assertTrue(sr.get("pass"), sr.get("failed"))
        checks = sr.get("checks", {})
        self.assertEqual(len(checks), 60)
        self.assertTrue(all(v is True for v in checks.values()), {k: v for k, v in checks.items() if v is not True})
        self.assertFalse(sr.get("failed"))
        r38 = result.get("v702_r38_final_validation", {})
        self.assertTrue(r38.get("pass"), r38.get("failed"))
        self.assertEqual(r38.get("count"), 32)
        self.assertTrue(all(v is True for v in (r38.get("checks") or {}).values()), r38.get("failed"))
        # R33/R34 predecessor result stays as forensic metadata and cannot
        # veto the current R36/R37 contracts on stale release-chain state.
        self.assertIn("historical_previous_r34_pass", r36)
        active_source = (ROOT / "main.py").read_text(encoding="utf-8")
        # Historical marker strings remain available for source forensics, but
        # superseded validators are DEBUG-only and must not pollute the active log.
        self.assertIn('logger.debug("[V702-R33][HISTORICAL/SUPERSEDED]', active_source)
        self.assertIn('logger.debug("[V702-R34][HISTORICAL/SUPERSEDED]', active_source)
        self.assertNotIn("[V702-R33][HISTORICAL/SUPERSEDED] validation did not pass", self.validation_text)
        self.assertNotIn("[V702-R34][HISTORICAL/SUPERSEDED] validation did not pass", self.validation_text)
        r34 = result.get("v702_r34_final_validation", {})
        self.assertTrue(r34.get("historical", False))
        self.assertIn("previous_canonical_validation", r34.get("failed", []))

    def test_docker_image_copies_r39_guardrail_module_with_canonical_runtime(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY main.py production_guardrails.py v702_counterfactual_shadow.py v702_intraday_shadow.py healthcheck.py /app/", dockerfile)
        self.assertIn("COPY v702_core__policy__family_policy.py", dockerfile)
        self.assertIn("v702_core__telegram__funnel.py /app/", dockerfile)
        self.assertIn("HEALTHCHECK --interval=60s --timeout=5s", dockerfile)
        self.assertTrue((ROOT / "healthcheck.py").is_file())
        self.assertTrue((ROOT / ".dockerignore").is_file())
        self.assertTrue((ROOT / "production_guardrails.py").is_file())
        self.assertIn("CMD [\"python\", \"-u\", \"main.py\"]", dockerfile)

    def test_runtime_dependency_constraints_match_ccxt_async_support(self):
        required = {"ccxt", "numpy", "pandas", "aiohttp", "aiosqlite", "python-dotenv"}
        constraints = {}
        # requirements.txt is the single installer entrypoint; resolve explicit
        # local -r includes so Docker/Railway and validation inspect the same pins.
        pending = [ROOT / "requirements.txt"]
        visited = set()
        while pending:
            req_path = pending.pop()
            if req_path in visited:
                continue
            visited.add(req_path)
            for line in req_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("-r "):
                    include = (req_path.parent / line[3:].strip()).resolve()
                    self.assertTrue(include.is_file(), f"missing requirements include: {include}")
                    pending.append(include)
                    continue
                name = re.split(r"(?:==|>=|<=|~=|!=|>|<)", line, maxsplit=1)[0]
                constraints[name.lower().replace("_", "-")] = line
        self.assertEqual(set(constraints), required)
        self.assertEqual(constraints["ccxt"], "ccxt==4.5.81")
        self.assertEqual(constraints["numpy"], "numpy==2.3.5")
        self.assertEqual(constraints["pandas"], "pandas==2.2.3")
        self.assertEqual(constraints["aiosqlite"], "aiosqlite==0.22.1")
        self.assertEqual(constraints["aiohttp"], "aiohttp==3.14.3")
        self.assertEqual(constraints["python-dotenv"], "python-dotenv==1.2.4")
        lock_notes = (ROOT / "LOCKFILE_NOTES.md").read_text(encoding="utf-8").lower()
        self.assertIn("transitive", lock_notes)
        self.assertIn("aiohttp==3.14.3", (ROOT / "requirements-lock.txt").read_text(encoding="utf-8"))

    def test_monitor_scan_is_independent_and_presend_stays_live_blocked(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("def _v702_monitor_only_scan_authorized()", source)
        scan_fn = source.split("def _v702_monitor_only_scan_authorized()", 1)[1].split("def _v702_paper_sim_authorized()", 1)[0]
        self.assertIn("UNIFIED_MONITOR_ONLY_SCAN_ENABLE", scan_fn)
        self.assertNotIn("_v702_env_is_explicitly_off(\"UNIFIED_LIVE_PILOT_ENABLE\")", scan_fn)
        self.assertIn('"[V702-MONITOR-SCAN] read-only scanner active', source)
        self.assertIn('"monitor_only_forced_off"', source)
        self.assertIn('if not entries_allowed and not monitor_scan_only:', source)

    def test_final_order_executor_has_independent_operator_off_guard(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        submit = source.split("async def submit_entry(exchange, symbol: str, qty: float, price: float,", 1)[1].split("# v4.0.2 PATCH D", 1)[0]
        self.assertIn('_v702_live_buy_possible(intent_context)', submit)
        self.assertIn('"submit_entry_final_guard"', submit)
        # The final gate must run before any state-changing exchange method.
        gate_pos = submit.index('_v702_live_buy_possible(intent_context)')
        first_order_pos = min((submit.find(token) for token in ('create_market_buy_order', 'create_order') if submit.find(token) >= 0), default=-1)
        self.assertTrue(first_order_pos < 0 or gate_pos < first_order_pos)
        self.assertIn('return False, None, 0.0', submit)

    def test_selected_paper_sim_has_no_exchange_execution_authority(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('source="SELECTED_ROUTE_PAPER", assume_fill=False', source)
        self.assertIn('"entry_model":"WAIT_FOR_BUFFERED_BREAKOUT"', source)
        self.assertIn("REFERENCE_PLUS_BUFFERED_BREAKOUT_V1", source)
        self.assertIn('"exchange_order_submitted":False', source)
        self.assertIn('"exchange_orders_submitted":False', source)
        self.assertIn('SELECTED_ROUTE_PAPER', source)
        self.assertIn('paper_edge_eligible', source)
        self.assertIn('"V702_KNOWLEDGE_OUTCOME_MAX_ACTIVE": 20', source)
        self.assertNotIn("UNIFIED_PAPER_SIM_MAX_ACTIVE=", (ROOT / "LIVE_RELEASE_ENV.example").read_text(encoding="utf-8"))
        self.assertNotIn("UNIFIED_PAPER_SIM_ROUND_TRIP_COST_PCT=", (ROOT / "LIVE_RELEASE_ENV.example").read_text(encoding="utf-8"))

    def test_stateful_runtime_database_is_excluded_from_release(self):
        # Import-time schema validation may create a DB in the working tree;
        # verify release exclusion metadata rather than conflating runtime state
        # with the bytes that were actually packaged. The final ZIP is checked
        # independently after the archive is built.
        manifest = json.loads((ROOT / "FINAL_MANIFEST.json").read_text(encoding="utf-8"))
        excluded = " ".join(map(str, manifest.get("archive_files_excluded", []))).lower()
        self.assertIn("unified_scalper.db", excluded)
        self.assertIn("wal/shm", excluded)
        self.assertIsNone(manifest.get("packaged_database_sha256"))
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("*.db", gitignore)
        self.assertIn("*.sqlite3", gitignore)

    def test_forbidden_assets_still_fail_closed(self):
        symbols = ["AERO/USDT", "aero/usdt", "AERO/USDT:USDT", "AERO_USDT",
                   "AERO-USDT", "AERO:USDT", "AERO.USDT", "AEROUSDT",
                   "BNB/USDC", "cake/usdt", "PUMP/USDT", "ETHFI/USDT", "BTC/USDT"]
        result = {symbol: bot._v587_is_forbidden_coin(symbol) for symbol in symbols}
        for symbol in ["AERO/USDT", "aero/usdt", "AERO/USDT:USDT", "AERO_USDT",
                       "AERO-USDT", "AERO:USDT", "AERO.USDT", "AEROUSDT",
                       "BNB/USDC", "cake/usdt", "PUMP/USDT", "ETHFI/USDT"]:
            self.assertTrue(result[symbol][0], f"forbidden symbol accepted: {symbol}: {result[symbol]}")
        self.assertFalse(result["BTC/USDT"][0], result["BTC/USDT"])
        # Exercise the early-call defensive path without importing a second bot
        # process (which would duplicate expensive import-time validation).
        hard = bot.V702_HARD_FORBIDDEN_BASES
        try:
            del bot.V702_HARD_FORBIDDEN_BASES
            self.assertTrue(bot._v587_is_forbidden_coin("PUMP/USDC")[0])
        finally:
            bot.V702_HARD_FORBIDDEN_BASES = hard

    def test_hard_safety_contracts_and_pipeline_observability_remain(self):
        src = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('CONFIG["MIN_LIVE_SCORE"] = max(70.0', src)
        self.assertIn('CONFIG["LONG_ONLY"] = True', src)
        self.assertIn('CONFIG["ENABLE_FUTURES"] = False', src)
        self.assertIn('"V702_R36_HARD_GATE_BYPASS": False', src)
        for asset in ("AERO", "BNB", "CAKE", "ETHFI", "PUMP"):
            self.assertIn(asset, src)
        for stage in ("DISCOVERY", "PREQUAL_SEEN", "PREQUAL_PASS", "RANKED", "SELECTED", "PREEXEC_PASS", "PREEXEC_BLOCK", "ROUTE_DEFERRED", "BUILDER_ENTERED", "BUILDER_RETURNED_NONE", "BUILDER_EXCEPTION", "SCORE_PASS", "SCORE_BLOCK", "PRESEND_PASS", "QUEUED", "TELEGRAM_ENQUEUED", "EXECUTION_ATTEMPT", "ORDER_ACCEPTED", "TRADE_STATE_CREATED", "NATIVE_SL_UNVERIFIED", "PROTECTED", "PROTECTION_FAILED"):
            self.assertIn(f'"{stage}"', src)
        self.assertIn("LIVE_EPOCH_UNIQUE_CANDIDATE_STAGES", src)
        self.assertIn('"V528_SPREAD_QUALITY_RELAX_ENABLE": False', src)
        self.assertIn('"V540_ELITE_SPREAD_RELIEF_ENABLE": False', src)
        self.assertIn('"V549_ULTRA_ELITE_SPREAD_ENABLE": False', src)
        self.assertIn("V702_FINAL_TARGET_GEOMETRY_LOCKED", src)


    def test_pipeline_digest_labels_follow_actual_gate_order(self):
        metrics = bot.V702PipelineMetrics
        stage_counts = {stage: index for index, stage in enumerate(metrics.STAGES, 1)}
        snap = {
            "enabled": True,
            "scope": "LIVE_EPOCH_UNIQUE_CANDIDATE_STAGES",
            "epoch": 1,
            "cycle_id": 7,
            "counts": stage_counts,
            "cycle_counts": stage_counts,
            "top_rejections": [],
            "top_rejections_cycle": [],
            "top_rejections_epoch": [],
            "cycle_reject_count": 0,
            "epoch_reject_count": 0,
            "last_block": {},
            "hard_gate_bypass": False,
        }
        with patch.object(metrics, "snapshot", return_value=snap):
            line = metrics.digest_line()
        self.assertIn(
            "PIPELINE[CYCLE] DISC/RANK/PRE/PASS/PRE_REJ/SEL/PREEXEC_PASS/PREEXEC_BLOCK/DEFER/BUILDER/BUILDER_NONE/BUILDER_ERR/SCORE_PASS/SCORE_BLOCK/PRESEND/QUEUE/TG_ENQ/EXEC/ORDER/STATE/NATIVE_SL_UNVERIFIED/PROTECTED/PROT_FAIL=",
            line,
        )
        self.assertIn("=1/2/3/4/5/6/7/8/9/10/11/12/13/14/15/16/17/18/19/20/21/22/23 ", line)

    def test_pipeline_window_summary_uses_window_scope_and_unique_stage_counts(self):
        from collections import deque
        metrics = bot.V702PipelineMetrics
        original_events = metrics._events
        original_event_counts = dict(metrics._event_counts_by_second)
        original_event_order = deque(metrics._event_bucket_order)
        original_drop_counts = dict(metrics._drop_counts_by_second)
        original_drop_order = deque(metrics._drop_bucket_order)
        metrics._event_counts_by_second = {950:1, 951:1, 952:1, 953:1, 954:1, 955:1, 956:1}
        metrics._event_bucket_order = deque([950, 951, 952, 953, 954, 955, 956])
        metrics._drop_counts_by_second = {}
        metrics._drop_bucket_order = deque()
        metrics._events = deque([
            {"ts": 950.0, "stage": "DISCOVERY", "candidate_key": "C1", "symbol": "DOT/USDT", "details": {}},
            {"ts": 951.0, "stage": "DISCOVERY", "candidate_key": "C1", "symbol": "DOT/USDT", "details": {}},
            {"ts": 952.0, "stage": "RANKED", "candidate_key": "C1", "symbol": "DOT/USDT", "details": {}},
            {"ts": 953.0, "stage": "PREQUAL_REJECT", "candidate_key": "C1", "symbol": "DOT/USDT", "details": {"reason": "liquidity.below_tier"}},
            {"ts": 954.0, "stage": "REJECT", "candidate_key": "C1", "symbol": "DOT/USDT", "details": {"stage": "prequal", "reason": "liquidity.below_tier"}},
            {"ts": 955.0, "stage": "REJECT", "candidate_key": "C1", "symbol": "DOT/USDT", "details": {"stage": "prequal", "reason": "liquidity.below_tier"}},
            {"ts": 956.0, "stage": "PREEXEC_BLOCK", "candidate_key": "C2", "symbol": "BTC/USDT", "details": {"reason": "selected_preexec_policy:family_regime_disallowed.macro"}},
            {"ts": 99.0, "stage": "PREQUAL_PASS", "candidate_key": "OLD", "symbol": "BTC/USDT", "details": {}},
        ], maxlen=4096)
        try:
            line = metrics.window_line(interval_sec=900.0, now=1000.0)
            self.assertIn("PIPELINE[WINDOW_15M]", line)
            self.assertIn("events=7", line)
            self.assertIn("DISC=1", line)  # duplicate stage for the same candidate is deduplicated
            self.assertIn("RANK=1", line)
            self.assertIn("PASS=0", line)  # stale event falls outside the window
            self.assertIn("PRE_REJ=1", line)
            self.assertIn("record_rejects=1", line)  # low-level rejection events are separate from PREQUAL outcomes
            self.assertIn("record_top=liquidity.below_tierx1", line)
            self.assertIn("prequal_top=liquidity.below_tierx1", line)
            self.assertIn("PX_BLK=1", line)
            self.assertIn("preexec_top=family_regime_disallowed.macrox1", line)
            self.assertIn("buffer_truncated=no", line)
        finally:
            metrics._events = original_events
            metrics._event_counts_by_second = original_event_counts
            metrics._event_bucket_order = original_event_order
            metrics._drop_counts_by_second = original_drop_counts
            metrics._drop_bucket_order = original_drop_order

    def test_pipeline_window_reports_prequal_reason_without_record_rejection_event(self):
        from collections import deque
        metrics = bot.V702PipelineMetrics
        original_events = metrics._events
        metrics._events = deque([
            {"ts": 950.0, "stage": "PREQUAL_REJECT", "candidate_key": "CANDIDATE_A",
             "symbol": "DOS/USDT", "details": {"reason": "liquidity.below_tier"}},
            {"ts": 951.0, "stage": "PREQUAL_REJECT", "candidate_key": "CANDIDATE_B",
             "symbol": "CAP/USDT", "details": {"reason": "liquidity.below_tier"}},
            {"ts": 952.0, "stage": "PREQUAL_REJECT", "candidate_key": "CANDIDATE_C",
             "symbol": "XDP/USDT", "details": {"reason": "htf.unavailable"}},
            {"ts": 953.0, "stage": "PREEXEC_BLOCK", "candidate_key": "CANDIDATE_D",
             "symbol": "DOS/USDT", "details": {"reason": "selected_preexec_policy:family_regime_disallowed.macro"}},
        ], maxlen=4096)
        try:
            with patch.object(bot, "WALL_NOW", return_value=1000.0):
                line = metrics.window_line(interval_sec=900.0, now=1000.0)
            self.assertIn("PRE_REJ=3", line)
            self.assertIn("PX_BLK=1", line)
            self.assertIn("record_rejects=3[unified_candidate_stage_reason]", line)
            self.assertIn("record_top=liquidity.below_tierx2,htf.unavailablex1", line)
            self.assertIn("prequal_source=arbiter", line)
            self.assertIn("preflight_separate=yes", line)
            self.assertIn("prequal_top=liquidity.below_tierx2,htf.unavailablex1", line)
            self.assertIn("preexec_top=family_regime_disallowed.macrox1", line)
        finally:
            metrics._events = original_events

    def test_builder_block_diagnostic_uses_exact_candidate_not_global_same_symbol_hint(self):
        keys = ("v702_builder_inflight_by_candidate", "v702_builder_rejection_by_candidate", "v701_current_builder_block")
        sentinel = object()
        old = {key: bot.STATS.get(key, sentinel) for key in keys}
        ctx = bot._V702_PIPELINE_CONTEXT
        token = ctx.set({"candidate_key": "CANDIDATE_A", "symbol": "DOT/USDT", "family": "PULLBACK"})
        try:
            bot.STATS["v702_builder_inflight_by_candidate"] = {
                "CANDIDATE_A": {"candidate_key": "CANDIDATE_A", "symbol": "DOT/USDT", "started_ts": 900.0, "cycle_id": 7},
                "CANDIDATE_B": {"candidate_key": "CANDIDATE_B", "symbol": "DOT/USDT", "started_ts": 900.0, "cycle_id": 7},
            }
            bot.STATS["v702_builder_rejection_by_candidate"] = {
                "CANDIDATE_A": {"candidate_key": "CANDIDATE_A", "symbol": "DOT/USDT", "stage": "prequal", "reason": "htf.family_htf_strength_below_floor", "root": "HTF", "ts": 999.0},
            }
            bot.STATS["v701_current_builder_block"] = {"symbol": "DOT/USDT", "stage": "wrong_candidate_stage", "reason": "WRONG_GLOBAL_HINT", "root": "EXECUTION", "ts": 999.0}
            message = "<b>Selected → Builder BLOCK</b>\nDOT/USDT\nroot=EXECUTION\nstage=builder\nreason=builder_returned_none"
            with patch.object(bot, "WALL_NOW", return_value=1000.0):
                attributed = bot._v702_a3_normalize_builder_block(message)
            self.assertIn("reason=htf.family_htf_strength_below_floor", attributed)
            self.assertIn("stage=prequal", attributed)
            self.assertIn("root=HTF", attributed)

            # Same symbol and a fresh global hint are not enough without this candidate's own row.
            token_b = ctx.set({"candidate_key": "CANDIDATE_B", "symbol": "DOT/USDT", "family": "PULLBACK"})
            try:
                with patch.object(bot, "WALL_NOW", return_value=1000.0):
                    unattributed = bot._v702_a3_normalize_builder_block(message)
            finally:
                ctx.reset(token_b)
            self.assertIn("reason=builder_terminal_no_result_unattributed", unattributed)
            self.assertNotIn("WRONG_GLOBAL_HINT", unattributed)
        finally:
            ctx.reset(token)
            for key, value in old.items():
                if value is sentinel:
                    bot.STATS.pop(key, None)
                else:
                    bot.STATS[key] = value

    def test_telegram_digest_interval_is_30m_and_expanded_digest_stays_bounded(self):
        metrics = bot.V702PipelineMetrics
        self.assertEqual(float(bot.CONFIG.get("V702_R28_TELEGRAM_DIGEST_INTERVAL_SEC", 0)), 1800.0)
        self.assertEqual(bot.FINAL_CANONICAL_RUNTIME.get("telegram_operator_mode"), "DIGEST_30M_NONCRITICAL__CRITICAL_IMMEDIATE")
        self.assertEqual(float(bot.CONFIG.get("HEARTBEAT_INTERVAL_SEC", 0)), 1800.0)
        marker = "Execution orders/protection/control/errors remain immediate; no gate was relaxed."
        with patch.object(bot, "_V702_DIGEST_BUILD_ORIGINAL", return_value=("X" * 5000) + "\n" + marker), \
             patch.object(metrics, "digest_line", return_value="PIPELINE[CYCLE] TEST"), \
             patch.object(metrics, "window_line", return_value="PIPELINE[WINDOW_15M] TEST"):
            rendered = bot._v702_digest_build_observed(bot._V702R28TelegramDigest)
        self.assertLessEqual(len(rendered), int(bot.CONFIG.get("V702_R28_TELEGRAM_DIGEST_MAX_CHARS", 3700)))
        self.assertIn("PIPELINE[CYCLE] TEST", rendered)
        self.assertIn("PIPELINE[WINDOW_15M] TEST", rendered)
        self.assertIn(marker, rendered)
        self.assertFalse(bool(bot.CONFIG.get("V702_R36_HARD_GATE_BYPASS", True)))

    def test_a59_truncated_digest_preserves_rejection_and_does_not_duplicate_header(self):
        digest_cls = bot._V702R28TelegramDigest
        max_key = "V702_R28_TELEGRAM_DIGEST_MAX_CHARS"
        old_max = bot.CONFIG.get(max_key)
        bot.CONFIG[max_key] = 1800
        try:
            with patch.object(digest_cls, "_compact_counts", return_value="COMPACT_SENTINEL"), \
                 patch.object(digest_cls, "_heartbeat_line", return_value="HEARTBEAT_SENTINEL"), \
                 patch.object(digest_cls, "_starvation_line", return_value="STARVATION_SENTINEL"), \
                 patch.object(digest_cls, "_rejection_line", return_value="REJECTION_SENTINEL"), \
                 patch.object(digest_cls, "_discovery_lines", return_value=[f"DISCOVERY_{i}_" + ("x" * 180) for i in range(30)]), \
                 patch.object(digest_cls, "_scorer_block_lines", return_value=["SCORER_SENTINEL"]), \
                 patch.object(digest_cls, "_route_block_lines", return_value=["ROUTE_SENTINEL"]), \
                 patch.object(digest_cls, "_block_lines", return_value=["BUILDER_SENTINEL"]), \
                 patch.object(digest_cls, "_shadow_lines", return_value=["SHADOW_SENTINEL"]), \
                 patch.object(digest_cls, "_edge_line", return_value="EDGE_SENTINEL"), \
                 patch.object(digest_cls, "_selected_route_summary", return_value="ROUTE_SUMMARY_SENTINEL"):
                rendered = digest_cls.build()
            self.assertLessEqual(len(rendered), 1800)
            self.assertIn("REJECTION_SENTINEL", rendered)
            self.assertEqual(rendered.count("STARVATION_SENTINEL"), 1)
            self.assertEqual(rendered.count("REJECTION_SENTINEL"), 1)
        finally:
            if old_max is None:
                bot.CONFIG.pop(max_key, None)
            else:
                bot.CONFIG[max_key] = old_max

    def test_prequal_exception_is_counted_as_reject_and_reraised(self):
        candidate = SimpleNamespace(
            symbol="PREQUAL-EXCEPTION/USDT", family="PULLBACK", strategy_mode="PULLBACK",
            engine_id="pullback", generated_at_ms=123456, features_snapshot={},
        )
        ranked = SimpleNamespace(candidate=candidate)
        with patch.object(bot, "_V702_PREQUAL_ORIGINAL", side_effect=ValueError("synthetic prequal fault")), \
             patch.object(bot.V702PipelineMetrics, "record") as record:
            with self.assertRaisesRegex(ValueError, "synthetic prequal fault"):
                bot._v702_prequal_observed(ranked, {})
        recorded_stages = [call.args[0] for call in record.call_args_list]
        self.assertEqual(recorded_stages, ["PREQUAL_SEEN", "PREQUAL_REJECT"])
        self.assertIn("exception.ValueError", str(record.call_args_list[-1].kwargs["details"]))


    def test_record_current_does_not_invent_candidate_key(self):
        metrics = bot.V702PipelineMetrics
        ctx = bot._V702_PIPELINE_CONTEXT
        token = ctx.set({})
        before_total = int(bot.STATS.get("v702_pipeline_unattributed_events", 0) or 0)
        before_stage = int(bot.STATS.get("v702_pipeline_unattributed.telegram_enqueued", 0) or 0)
        try:
            with patch.object(metrics, "_enabled", True), patch.object(metrics, "record") as record:
                accepted = metrics.record_current("TELEGRAM_ENQUEUED", symbol="OPERATOR")
            self.assertFalse(accepted)
            record.assert_not_called()
            self.assertEqual(int(bot.STATS.get("v702_pipeline_unattributed_events", 0) or 0), before_total + 1)
            self.assertEqual(int(bot.STATS.get("v702_pipeline_unattributed.telegram_enqueued", 0) or 0), before_stage + 1)
        finally:
            ctx.reset(token)


    def test_builder_return_none_is_explicitly_observed_with_deltas(self):
        candidate = SimpleNamespace(
            symbol="BUILDER-NONE/USDT", family="PULLBACK", strategy_mode="PULLBACK",
            engine_id="pullback", generated_at_ms=123456, features_snapshot={},
        )
        with patch.object(bot, "_V702_BUILDER_ORIGINAL", new=AsyncMock(return_value=None)), \
             patch.object(bot.V702PipelineMetrics, "_enabled", True), \
             patch.object(bot.V702PipelineMetrics, "record") as record:
            result = asyncio.run(bot.SignalBuilder.build_and_route(object(), candidate.symbol, {"snapshot_id": "test-snapshot"}, preferred_candidate=candidate))
        self.assertIsNone(result)
        stages = [call.args[0] for call in record.call_args_list]
        self.assertIn("BUILDER_ENTERED", stages)
        self.assertIn("BUILDER_RETURNED_NONE", stages)
        none_call = next(call for call in record.call_args_list if call.args[0] == "BUILDER_RETURNED_NONE")
        details = none_call.kwargs.get("details", {})
        self.assertIn("signals_queued_delta", details)
        self.assertIn("live_ready_delta", details)
        # A generic None must not inherit an unrelated same-symbol/global reason.
        self.assertEqual(details.get("reason"), "builder_terminal_no_result_unattributed", details)
        self.assertEqual(details.get("reason_attribution"), "unattributed_no_fresh_candidate_rejection", details)

    def test_builder_exception_is_observed_and_reraised(self):
        candidate = SimpleNamespace(
            symbol="BUILDER-EXCEPTION/USDT", family="PULLBACK", strategy_mode="PULLBACK",
            engine_id="pullback", generated_at_ms=123457, features_snapshot={},
        )
        with patch.object(bot, "_V702_BUILDER_ORIGINAL", new=AsyncMock(side_effect=RuntimeError("synthetic builder fault"))), \
             patch.object(bot.V702PipelineMetrics, "_enabled", True), \
             patch.object(bot.V702PipelineMetrics, "record") as record:
            with self.assertRaisesRegex(RuntimeError, "synthetic builder fault"):
                asyncio.run(bot.SignalBuilder.build_and_route(object(), candidate.symbol, {"snapshot_id": "test-snapshot"}, preferred_candidate=candidate))
        stages = [call.args[0] for call in record.call_args_list]
        self.assertIn("BUILDER_ENTERED", stages)
        self.assertIn("BUILDER_EXCEPTION", stages)

    def test_operator_telegram_enqueue_is_not_candidate_funnel_progress(self):
        ctx = bot._V702_PIPELINE_CONTEXT
        token = ctx.set({})
        before = int(bot.STATS.get("v702_telegram_enqueue_unattributed", 0) or 0)
        try:
            with patch.object(bot, "_V702_TELEGRAM_ENQUEUE_ORIGINAL", new=AsyncMock(return_value=True)), \
                 patch.object(bot.V702PipelineMetrics, "record_current") as record_current, \
                 patch.object(bot.V702PipelineMetrics, "record") as record:
                result = asyncio.run(bot.TelegramDispatcher.enqueue("operator heartbeat"))
            self.assertTrue(result)
            record_current.assert_not_called()
            record.assert_not_called()
            self.assertEqual(int(bot.STATS.get("v702_telegram_enqueue_unattributed", 0) or 0), before + 1)
        finally:
            ctx.reset(token)

    def test_builder_reason_recovers_exact_candidate_score_block_from_pipeline_ledger(self):
        from collections import deque
        metrics = bot.V702PipelineMetrics
        key = "812|PAIR/USDT|PULLBACK|MSE|case-a28-exact"
        old_events = metrics._events
        old_cycle = bot.STATS.get("v681_runtime_cycle_id")
        old_store = bot.STATS.get("v702_builder_rejection_by_candidate")
        try:
            bot.STATS["v681_runtime_cycle_id"] = 812
            bot.STATS.pop("v702_builder_rejection_by_candidate", None)
            metrics._events = deque([
                {"cycle_id":812,"stage":"SCORE_BLOCK","candidate_key":key,"symbol":"PAIR/USDT",
                 "family":"PULLBACK","ts":110.0,"details":{"reason":"score_below_threshold:51.4<70.0","score":51.4,"threshold":70.0}},
                {"cycle_id":812,"stage":"SCORE_BLOCK","candidate_key":"812|PAIR/USDT|PULLBACK|MSE|another-candidate",
                 "symbol":"PAIR/USDT","family":"PULLBACK","ts":111.0,"details":{"reason":"wrong_candidate"}},
            ])
            with patch.object(metrics, "_cycle", return_value=812):
                row = bot._v702_builder_rejection_reason_for_candidate(key, 100.0)
                wrong = bot._v702_builder_rejection_reason_for_candidate("812|PAIR/USDT|PULLBACK|MSE|another-candidate", 112.0)
            self.assertEqual(row["stage"], "scorer")
            self.assertEqual(row["reason"], "score_below_threshold:51.4<70.0")
            self.assertEqual(row["source"], "exact_candidate_pipeline_event")
            self.assertIsNone(wrong)
        finally:
            metrics._events = old_events
            if old_cycle is None: bot.STATS.pop("v681_runtime_cycle_id", None)
            else: bot.STATS["v681_runtime_cycle_id"] = old_cycle
            if old_store is None: bot.STATS.pop("v702_builder_rejection_by_candidate", None)
            else: bot.STATS["v702_builder_rejection_by_candidate"] = old_store

    def test_candidate_context_builder_notice_does_not_count_as_opportunity_telegram(self):
        from collections import deque
        metrics = bot.V702PipelineMetrics
        ctx = bot._V702_PIPELINE_CONTEXT
        key = "813|PAIR/USDT|PULLBACK|MSE|diagnostic-only"
        token = ctx.set({"candidate_key":key,"symbol":"PAIR/USDT","family":"PULLBACK"})
        old_events = metrics._events
        before = int(bot.STATS.get("v702_telegram_enqueue_unattributed", 0) or 0)
        try:
            metrics._events = deque()
            with patch.object(bot, "_V702_TELEGRAM_ENQUEUE_ORIGINAL", new=AsyncMock(return_value=True)), \
                 patch.object(metrics, "record_current") as record_current:
                msg = "<b>Selected → Builder BLOCK</b>\n<b>PAIR/USDT</b>\nroot=<code>SCORE</code>"
                result = asyncio.run(bot.TelegramDispatcher.enqueue(msg))
            self.assertTrue(result)
            record_current.assert_not_called()
            self.assertEqual(int(bot.STATS.get("v702_telegram_enqueue_unattributed", 0) or 0), before + 1)
        finally:
            metrics._events = old_events
            ctx.reset(token)

    def test_candidate_telegram_requires_exact_queue_commit_and_canonical_headline(self):
        from collections import deque
        metrics = bot.V702PipelineMetrics
        ctx = bot._V702_PIPELINE_CONTEXT
        key = "814|PAIR/USDT|PULLBACK|MSE|queued-opportunity"
        token = ctx.set({"candidate_key":key,"symbol":"PAIR/USDT","family":"PULLBACK"})
        old_events = metrics._events
        old_cycle = bot.STATS.get("v681_runtime_cycle_id")
        try:
            bot.STATS["v681_runtime_cycle_id"] = 814
            metrics._events = deque([{"cycle_id":814,"stage":"QUEUED","candidate_key":key,"symbol":"PAIR/USDT","ts":100.0,"details":{}}])
            msg = "🟢 <b>BUY OPPORTUNITY — PENDING FINAL GATES</b>\n<b>PAIR/USDT</b>"
            with patch.object(bot, "_V702_TELEGRAM_ENQUEUE_ORIGINAL", new=AsyncMock(return_value=True)), \
                 patch.object(metrics, "record_current", return_value=True) as record_current:
                result = asyncio.run(bot.TelegramDispatcher.enqueue(msg))
            self.assertTrue(result)
            record_current.assert_called_once()
            self.assertEqual(record_current.call_args.args[0], "TELEGRAM_ENQUEUED")
            self.assertTrue(bot._v702_candidate_telegram_enqueue_allowed(key, msg))
            self.assertFalse(bot._v702_candidate_telegram_enqueue_allowed(key, "operator digest"))
        finally:
            metrics._events = old_events
            if old_cycle is None: bot.STATS.pop("v681_runtime_cycle_id", None)
            else: bot.STATS["v681_runtime_cycle_id"] = old_cycle
            ctx.reset(token)

    def test_selected_route_outcome_is_attached_to_current_candidate(self):
        metrics = bot.V702PipelineMetrics
        old_cycle = bot.STATS.get("v681_runtime_cycle_id", 0)
        old_map = bot.STATS.get("v702_selected_candidate_key_by_symbol")
        try:
            bot.STATS["v681_runtime_cycle_id"] = 77
            bot.STATS["v702_selected_candidate_key_by_symbol"] = {
                "FIL/USDT": {"candidate_key": "77|FIL/USDT|COMPRESSION_EXPANSION|MSE|123", "family": "COMPRESSION_EXPANSION", "cycle_id": 77}
            }
            with patch.object(metrics, "record") as record:
                self.assertTrue(bot._v702_pipeline_route_outcome("FIL/USDT", "PREEXEC_BLOCK", "structural.fake_break_detected"))
            record.assert_called_once()
            self.assertEqual(record.call_args.args[0], "PREEXEC_BLOCK")
            self.assertEqual(record.call_args.args[1], "77|FIL/USDT|COMPRESSION_EXPANSION|MSE|123")
            self.assertIn("structural.fake_break_detected", str(record.call_args.kwargs.get("details")))
        finally:
            bot.STATS["v681_runtime_cycle_id"] = old_cycle
            if old_map is None:
                bot.STATS.pop("v702_selected_candidate_key_by_symbol", None)
            else:
                bot.STATS["v702_selected_candidate_key_by_symbol"] = old_map

    def test_liquidity_tier_normalization_is_fail_closed(self):
        normalize = bot._v702_normalize_liquidity_tier
        self.assertEqual(normalize(" below ", 9_000_000), "BELOW")
        self.assertEqual(normalize("mId", 9_000_000), "MID")
        self.assertIsNone(normalize("UNRECOGNIZED", 9_000_000))
        self.assertIsNone(normalize("", None))
        # Missing tier metadata may only be inferred from an actual volume fact.
        self.assertEqual(normalize(None, 3_000_000), bot.LiquidityTier.classify(3_000_000))

    def test_native_sl_exception_is_counted_unverified_and_reraised(self):
        trade = SimpleNamespace(symbol="NATIVE-SL-EXCEPTION/USDT", sl_health_state="UNVERIFIED")
        with patch.object(bot, "_V702_PLACE_SL_ORIGINAL", new=AsyncMock(side_effect=RuntimeError("synthetic native SL fault"))), \
             patch.object(bot.V702PipelineMetrics, "record_current") as record_current:
            with self.assertRaisesRegex(RuntimeError, "synthetic native SL fault"):
                asyncio.run(bot._v702_place_sl_observed(object(), trade))
        record_current.assert_called_once()
        self.assertEqual(record_current.call_args.args[0], "NATIVE_SL_UNVERIFIED")
        self.assertIn("synthetic native SL fault", str(record_current.call_args.kwargs["details"]))


    def test_digest_symbol_attribution_preserves_parentheses_unicode_and_missing_symbols(self):
        from collections import deque
        digest = bot._V702R28TelegramDigest
        old_rows = digest._discovery_by_symbol
        old_blocks = digest._selected_blocks
        old_shadows = digest._shadow_events
        structured = getattr(bot, "_V702_A37_STRUCTURED_BLOCKS", {})
        old_structured = {key: list(value) for key, value in structured.items()}
        try:
            # Isolate legacy string-queue coverage from structured events captured
            # by other tests in the same imported module.
            for value in structured.values():
                value.clear()
            digest._discovery_by_symbol = {}
            digest._selected_blocks = deque([
                "SELECTED → BUILDER BLOCK GOLD(PAXG)/USDT root=STRUCTURE stage=prequal reason=structural.fake_break_detected"
            ], maxlen=bot.V702_R28_TELEGRAM_DIGEST_TOP_BLOCKS)
            digest._shadow_events = deque([
                "KNOWLEDGE SHADOW — STOP LOSS REACHED\n\n<b>龙虾/USDT | PULLBACK</b>\nEvent: SL\nMFE: +0.12R\nMAE: -1.24R"
            ], maxlen=bot.V702_R28_TELEGRAM_DIGEST_TOP_SHADOW)

            digest._capture_discovery(
                "DISCOVERY SIGNAL — KNOWLEDGE ONLY\n\nGOLD(PAXG)/USDT\nStrategy: PULLBACK\n"
                "Engine Score: 80\nReviewed Score: 91\nProjected Canonical Live Score: 60\n"
                "HTF: 85\nVol: x1.4\nRS: 1.2%\nChase: 0.4 ATR\nTier: LARGE\nContext: VERIFIED"
            )
            digest._capture_discovery(
                "DISCOVERY SIGNAL — KNOWLEDGE ONLY\n\n龙虾/USDT\nStrategy: PULLBACK\n"
                "Engine Score: 80\nReviewed Score: 91\nProjected Canonical Live Score: 59\n"
                "HTF: 85\nVol: x1.4\nRS: 1.2%\nChase: 0.4 ATR\nTier: LARGE\nContext: VERIFIED"
            )
            digest._capture_discovery(
                "DISCOVERY SIGNAL — KNOWLEDGE ONLY\n\nStrategy: PULLBACK\n"
                "Engine Score: 80\nReviewed Score: 91\nProjected Canonical Live Score: 58\nHTF: 85"
            )

            rows = list(digest._discovery_by_symbol.values())
            self.assertEqual({r["symbol"] for r in rows}, {"GOLD(PAXG)/USDT", "龙虾/USDT", "UNATTRIBUTED"})
            self.assertNotIn("UNKNOWN/USDT", digest._discovery_by_symbol)
            discovery_lines = "\n".join(digest._discovery_lines())
            self.assertIn("GOLD(PAXG)/USDT", discovery_lines)
            self.assertIn("龙虾/USDT", discovery_lines)
            self.assertIn("UNATTRIBUTED", discovery_lines)

            block_line = digest._block_lines()[0]
            self.assertIn("GOLD(PAXG)/USDT", block_line)
            shadow_line = digest._shadow_lines()[0]
            self.assertIn("龙虾/USDT", shadow_line)
            self.assertNotIn("? SL", shadow_line)

            with patch.dict(bot.STATS, {
                "v681_runtime_cycle_id": 88,
                "v702_selected_route_last": {
                    "symbol": "GOLD(PAXG)/USDT", "stage": "selected_route_projection",
                    "reason": "reject.score.exact_route_projection:39.2<70.0",
                    "cycle_id": 88, "ts": bot.WALL_NOW(),
                },
            }):
                route_line = digest._selected_route_summary()
            self.assertIn("GOLD(PAXG)/USDT", route_line)
            self.assertNotIn("GOLDPAXG/USDT", route_line)
        finally:
            digest._discovery_by_symbol = old_rows
            digest._selected_blocks = old_blocks
            digest._shadow_events = old_shadows
            for key, value in structured.items():
                value.clear()
                value.extend(old_structured.get(key, []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
