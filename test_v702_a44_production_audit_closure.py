from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import main as bot

ROOT = Path(__file__).resolve().parent


def test_a44_root_taxonomy_is_ordered_and_window_buckets_match():
    cases = [
        ("kill_switch balance.entries_blocked", "KILL_SWITCH", "system"),
        ("native_sl_unverified balance.entries_blocked", "PROTECTION", "execution"),
        ("startup_unresolved_execution_intents:3", "EXECUTION_INTENT", "execution"),
        ("balance.entries_blocked", "BALANCE", "balance"),
        ("family_regime_disallowed.macro", "POLICY", "policy"),
        ("liquidity.v45_micro", "LIQUIDITY", "liquidity"),
    ]
    for reason, root, bucket in cases:
        assert bot._v702_a44_reason_root(reason) == root, (reason, bot._v702_a44_reason_root(reason))
        assert bot._v453_reject_bucket(reason) == bucket, (reason, bot._v453_reject_bucket(reason))


def test_a44_all_live_score_relief_paths_keep_global_floor_at_70(monkeypatch):
    assert float(bot.CONFIG["MIN_LIVE_SCORE"]) >= 70.0
    assert float(bot.CONFIG["V453_SCORE_FLOOR_MIN"]) >= 70.0
    assert float(bot.CONFIG["V420_ADAPTIVE_FLOOR_MIN"]) >= 70.0
    assert bot._v704_hard_global_score_floor() >= 70.0

    ctl = bot.V699StarvationController()
    ctl.total_relief = 500.0
    assert ctl.effective_floor() >= 70.0

    original = float(getattr(bot._V420State, "adaptive_floor", 70.0) or 70.0)
    old_obs = list(getattr(bot.V453CanonicalScoreFloor, "_obs", []))
    monkeypatch.setattr(bot, "_v453_safety_hazard", lambda: "balance.entries_blocked")
    try:
        result = bot.V453CanonicalScoreFloor.tick()
        assert result >= 70.0
        assert float(getattr(bot._V420State, "adaptive_floor", 0.0) or 0.0) >= 70.0
    finally:
        bot._V420State.adaptive_floor = max(70.0, original)
        try:
            bot.V453CanonicalScoreFloor._obs.clear()
            bot.V453CanonicalScoreFloor._obs.extend(old_obs)
        except Exception:
            pass


def test_a44_v612_invariant_checks_effective_live_floor_not_soft_intermediate():
    assert bot._v612_combined_score_floor_invariant(68.0, 70.0) is True
    assert bot._v612_combined_score_floor_invariant(71.0, 69.9) is False
    assert bot._v612_combined_score_floor_invariant(float("nan"), 70.0) is False


def test_a44_v420_legacy_adaptive_floor_cannot_store_below_70(monkeypatch):
    old_floor = float(getattr(bot._V420State, "adaptive_floor", 70.0) or 70.0)
    old_min_live = bot.CONFIG.get("MIN_LIVE_SCORE", 70.0)
    old_min_adaptive = bot.CONFIG.get("V420_ADAPTIVE_FLOOR_MIN", 64.0)
    old_enable = bot.CONFIG.get("V420_ADAPTIVE_SCORE_FLOOR_ENABLE", True)
    old_recall = bot._V420State.recall_rate
    try:
        bot.CONFIG["MIN_LIVE_SCORE"] = 70.0
        bot.CONFIG["V420_ADAPTIVE_FLOOR_MIN"] = 64.0
        bot.CONFIG["V420_ADAPTIVE_SCORE_FLOOR_ENABLE"] = True
        bot._V420State.adaptive_floor = 64.0
        monkeypatch.setattr(bot._V420State, "recall_rate", staticmethod(lambda: (0.0, 200, 200, 0)))
        result = bot.V420AdaptiveFloor.compute()
        assert result >= 70.0
        assert float(bot._V420State.adaptive_floor) >= 70.0
    finally:
        bot._V420State.adaptive_floor = max(70.0, old_floor)
        bot.CONFIG["MIN_LIVE_SCORE"] = old_min_live
        bot.CONFIG["V420_ADAPTIVE_FLOOR_MIN"] = old_min_adaptive
        bot.CONFIG["V420_ADAPTIVE_SCORE_FLOOR_ENABLE"] = old_enable
        monkeypatch.setattr(bot._V420State, "recall_rate", old_recall)


def test_a44_balance_hysteresis_holds_for_low_and_stale_snapshot():
    old_block = dict(bot.LIVE_ENTRIES_BLOCKED) if isinstance(bot.LIVE_ENTRIES_BLOCKED, dict) else bot.LIVE_ENTRIES_BLOCKED
    old_value = getattr(bot.BalanceReconciler, "_last_real_value", None)
    old_ts = getattr(bot.BalanceReconciler, "_last_real_ts", None)
    old_min = bot.CONFIG.get("BALANCE_MIN_ACCEPT_USDT", 5.0)
    old_mult = bot.CONFIG.get("V702_A44_BALANCE_UNLATCH_MULTIPLIER", 1.10)
    try:
        bot.CONFIG["BALANCE_MIN_ACCEPT_USDT"] = 5.0
        bot.CONFIG["V702_A44_BALANCE_UNLATCH_MULTIPLIER"] = 1.10
        bot.LIVE_ENTRIES_BLOCKED = {"active": True, "reason": "balance_below_minimum", "where": "test"}
        bot.BalanceReconciler._last_real_value = 5.49
        bot.BalanceReconciler._last_real_ts = bot.MONO_NOW()
        assert bot.live_entries_unblock(reason="real_balance_recovered", where="test") is False
        bot.BalanceReconciler._last_real_value = 6.0
        bot.BalanceReconciler._last_real_ts = bot.MONO_NOW() - 10_000.0
        assert bot.live_entries_unblock(reason="real_balance_recovered", where="test") is False
        assert bool(bot.LIVE_ENTRIES_BLOCKED.get("active"))
    finally:
        bot.LIVE_ENTRIES_BLOCKED = old_block
        if old_value is None:
            if hasattr(bot.BalanceReconciler, "_last_real_value"):
                delattr(bot.BalanceReconciler, "_last_real_value")
        else:
            bot.BalanceReconciler._last_real_value = old_value
        if old_ts is None:
            if hasattr(bot.BalanceReconciler, "_last_real_ts"):
                delattr(bot.BalanceReconciler, "_last_real_ts")
        else:
            bot.BalanceReconciler._last_real_ts = old_ts
        bot.CONFIG["BALANCE_MIN_ACCEPT_USDT"] = old_min
        bot.CONFIG["V702_A44_BALANCE_UNLATCH_MULTIPLIER"] = old_mult


def test_a44_active_balance_latch_is_funding_not_opportunity_starvation():
    old_block = dict(bot.LIVE_ENTRIES_BLOCKED) if isinstance(bot.LIVE_ENTRIES_BLOCKED, dict) else bot.LIVE_ENTRIES_BLOCKED
    try:
        bot.LIVE_ENTRIES_BLOCKED = {"active": True, "reason": "balance_below_minimum", "where": "test"}
        snap = bot._v699_truthful_starvation_snapshot()
        assert snap["mode"] == "FUNDING_LATCH", snap
        assert snap["root"] == "FUNDING_LATCH", snap
        assert snap.get("hard_gate_bypass") is False
        assert bot._V702R28TelegramDigest._starvation_line("starvation mode=SYSTEM_STARVATION").startswith("starvation mode=FUNDING_LATCH")
    finally:
        bot.LIVE_ENTRIES_BLOCKED = old_block


def test_a44_policy_shadow_reason_is_telemetry_only():
    ranked = SimpleNamespace(candidate=SimpleNamespace(
        symbol="SAMPLE/USDT", family="PULLBACK", strategy_mode="PULLBACK",
        features_snapshot={"macro_regime": "BEARISH", "tier": "MID"},
    ))
    result = bot._v702_a44_shadow_policy_reason(ranked, {"SAMPLE/USDT": {"macro_regime": "BEARISH", "tier": "MID"}})
    assert result["reason"] in {"family_regime_disallowed.macro", "shadow_no_policy_reject_proven", "family_regime_disallowed.local", "family_regime_disallowed.severity"}
    assert result["telemetry_only"] is True
    assert result["source"] == "EXISTING_CANDIDATE_SNAPSHOT_ONLY"
    assert bot.FINAL_CANONICAL_RUNTIME.get("hard_gate_bypass") is False


def test_a44_digest_chunks_respect_limit_and_keep_action_first():
    source = [
        "FUNDING_LATCH ACTION_REQUIRED: fund account — free=3.00 USDT, min=5.00, blocked_since=90s",
        "PIPELINE " + ("x" * 5000),
        "OTHER_DIAGNOSTICS " + ("y" * 2000),
    ]
    chunks = bot._v702_a44_partition_digest_lines(source, limit=1700, max_parts=4)
    assert chunks
    assert "FUNDING_LATCH ACTION_REQUIRED" in chunks[0]
    assert all(len(f"DIGEST {i}/{len(chunks)}\n{chunk}") <= 1700 for i, chunk in enumerate(chunks, 1))


def test_a44_build_digest_does_not_cut_before_partitioning(monkeypatch):
    old_block = dict(bot.LIVE_ENTRIES_BLOCKED) if isinstance(bot.LIVE_ENTRIES_BLOCKED, dict) else bot.LIVE_ENTRIES_BLOCKED
    original_build = bot._V702_A44_OLD_BUILD
    original_diag = bot._v702_a40_entry_block_telemetry
    try:
        bot.LIVE_ENTRIES_BLOCKED = {"active": True, "reason": "balance_below_minimum", "where": "test"}
        monkeypatch.setattr(bot, "_V702_A44_OLD_BUILD", lambda cls: "HEADER\n" + "x" * 1000 + "\n" + "y" * 1000 + "\n" + "z" * 1000 + "\nTAIL_SENTINEL_A44")
        monkeypatch.setattr(bot, "_v702_a40_entry_block_telemetry", lambda: {"block_reason":"balance_below_minimum", "block_where":"test", "block_age_sec":1, "balance_free_usdt":4.0, "balance_age_sec":1})
        built = bot._V702R28TelegramDigest.build()
        assert "TAIL_SENTINEL_A44" in built
        chunks = bot._v702_a44_partition_digest_lines(built.splitlines(), limit=1700, max_parts=4)
        assert "FUNDING_LATCH" in chunks[0] and len(chunks) >= 2
    finally:
        bot.LIVE_ENTRIES_BLOCKED = old_block
        bot._V702_A44_OLD_BUILD = original_build
        bot._v702_a40_entry_block_telemetry = original_diag


def test_a44_config_guard_rejects_risk_drift_after_arm():
    config = bot.CONFIG
    key = "MIN_LIVE_SCORE"
    old_value = dict.__getitem__(config, key)
    old_armed = getattr(bot, "_V699_LIVE_EPOCH_ARMED", False)
    old_locked = dict(getattr(config, "_a44_locked_values", {}) or {})
    old_blocked_count = bot.STATS.get("v702_a44_config_mutation_blocked")
    try:
        config._a44_locked_values = {**old_locked, key: old_value}
        bot._V699_LIVE_EPOCH_ARMED = True
        config[key] = float(old_value) - 1.0
        assert dict.__getitem__(config, key) == old_value
        assert int(bot.STATS.get("v702_a44_config_mutation_blocked", 0) or 0) >= int(old_blocked_count or 0) + 1
    finally:
        dict.__setitem__(config, key, old_value)
        config._a44_locked_values = old_locked
        bot._V699_LIVE_EPOCH_ARMED = old_armed
        if old_blocked_count is None:
            bot.STATS.pop("v702_a44_config_mutation_blocked", None)
        else:
            bot.STATS["v702_a44_config_mutation_blocked"] = old_blocked_count


def test_a44_release_manifest_marks_offline_only_no_go_and_policy_bucket():
    manifest = json.loads((ROOT / "FINAL_MANIFEST.json").read_text(encoding="utf-8"))
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A44_CANONICAL_REVISION + "-A45-")
    assert bot.FINAL_CANONICAL_RUNTIME.get("hard_gate_bypass") is False
    assert bot.CONFIG["LONG_ONLY"] and str(bot.CONFIG["MARKET_TYPE"]).upper() == "SPOT"
    assert not bot.CONFIG.get("ENABLE_FUTURES", False)
    assert bot._v453_reject_bucket("family_regime_disallowed.macro") == "policy"
    assert manifest["dependency_lock_status"]["transitive_dependencies_hash_locked"] is False
    assert str(manifest.get("production_decision", manifest.get("status", "NO_GO"))).startswith(("NO_GO", "V702_A43_APPLIED", "V702_A44_APPLIED"))
    # Historical A49/A52/A53 lineage remains in the provenance chain;
    # A54/A55 append the current canonical distribution and its audit closure.
    assert manifest.get("active_release_tag") == "UNIFIED-SCALPER-V702-A61-CANONICAL-FINAL"
    revision = manifest.get("active_package_revision", "")
    assert "A53-EXECUTION-TELEGRAM-SWING-CLOSURE-2026-10-21" in revision
    assert revision.endswith("A54-CANONICAL-MONITOR-PAPER-EDGE-SAFETY-2026-11-04-A55-FINAL-SHADOW-PRESEND-EDGE-GATE-2026-11-04-A56-LIVE-AUTH-SHADOW-TIME-PM-HEALTH-2026-11-06-A57-CAPABILITY-PM-FIRST-HEALTH-CLOSURE-2026-11-06-A58-PRODUCTION-AUDIT-CANONICAL-FINAL-2026-11-11-A59-BEARISH-POLICY-REJECT-SHADOW-OBSERVABILITY-CLOSURE-2026-11-13-A60-PAPER-LEDGER-MODEL-AND-EDGE-REPORT-COHERENCE-2026-11-14-A61-BUILDER-EDGE-ELIGIBILITY-TRUTH-2026-11-14")
    assert manifest["canonical_source_sha256"] == hashlib.sha256((ROOT / "main.py").read_bytes()).hexdigest()
