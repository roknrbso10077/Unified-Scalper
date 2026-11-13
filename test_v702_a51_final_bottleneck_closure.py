"""A51 regression tests for safe bearish-policy throughput and telemetry boundaries."""
from __future__ import annotations

from collections import deque
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import main as bot


def test_a51_integer_second_window_edges_do_not_create_false_retention_mismatch():
    cls = bot.V702PipelineMetrics
    attrs = (
        "_events", "_event_counts_by_second", "_event_bucket_order",
        "_drop_counts_by_second", "_drop_bucket_order", "_events_dropped_total",
        "_cycle_events_dropped_total", "_cycle_id", "_enabled",
    )
    old = {name: getattr(cls, name) for name in attrs}
    try:
        # cutoff=200.4, while the counters store the event under second bucket 200.
        # Both views must include the retained event at 200.7 consistently.
        cls._events = deque([
            {"ts": 199.0, "stage": "DISCOVERY", "candidate_key": "old", "details": {}},
            {"ts": 200.7, "stage": "RANKED", "candidate_key": "edge", "details": {}},
            {"ts": 1999.9, "stage": "DISCOVERY", "candidate_key": "new", "details": {}},
        ], maxlen=20_000)
        cls._event_counts_by_second = {199: 1, 200: 1, 1999: 1}
        cls._event_bucket_order = deque([199, 200, 1999])
        cls._drop_counts_by_second = {}
        cls._drop_bucket_order = deque()
        cls._events_dropped_total = 0
        cls._cycle_events_dropped_total = 0
        cls._cycle_id = 5
        cls._enabled = True

        line = cls.window_line(interval_sec=1_800.0, now=2_000.4)
        assert "events=2 " in line
        assert "window_events=2" in line
        assert "retention_counter_mismatch=no" in line
        assert "event_retention_complete=yes" in line
        assert "window_covered=yes" in line

        health = cls.drop_health_snapshot(interval_sec=1_800.0, now=2_000.4)
        assert health["events_last_window"] == 2
        assert health["retained_events_last_window"] == 2
        assert health["event_retention_complete"] is True
        assert health["window_covered"] is True
    finally:
        for name, value in old.items():
            setattr(cls, name, value)


def test_a51_bearish_family_rejection_short_circuits_expensive_downstream_checks(monkeypatch):
    candidate = SimpleNamespace(
        symbol="ABC/USDT",
        side="long",
        family="PULLBACK",
        strategy_mode="PULLBACK",
        strategy_style="SCALP",
        market_phase="PULLBACK",
        local_regime="LOCAL_RECOVERY",
        generated_at_ms=bot.WALL_NOW() * 1000.0,
        engine_score=0.90,
        features_snapshot={"hard_valid": True, "market_phase": "PULLBACK"},
    )
    ranked = SimpleNamespace(candidate=candidate)
    snap = {
        "quote_vol_24h": 5_000_000.0,
        "tier": "LARGE",
        "spread_pct": 0.01,
        "macro_regime": "BEARISH",
        "macro_severity": "BEARISH_NORMAL",
        "local_regime": "LOCAL_RECOVERY",
        "market_phase": "PULLBACK",
        "htf_strength": 70.0,
    }
    monkeypatch.setattr(bot, "_v453_safety_hazard", lambda: None)
    monkeypatch.setattr(bot, "_v455_candidate_freshness_ok", lambda *_: (True, "ok", 0.0))
    monkeypatch.setattr(bot.CompositeRankingEngine, "_validate_fail_closed", staticmethod(lambda _c: None))
    monkeypatch.setattr(bot, "_v669_validate_market_snapshot", lambda *_a, **_k: (True, "ok", {}), raising=False)
    monkeypatch.setattr(bot, "_v455_record_prequal_reason", lambda *_a, **_k: None)
    monkeypatch.setattr(bot, "_v689_resolve_htf_strength", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("HTF resolver should be skipped")))
    monkeypatch.setattr(bot, "_v702_a43_derive_depth_ratio_from_exact_book", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("depth derivation should be skipped")))
    monkeypatch.setattr(bot, "_v45_orderbook_confirmation", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("orderbook confirmation should be skipped")))
    monkeypatch.setattr(bot.V410Telemetry, "reject", lambda *_a, **_k: None)
    old_count = int(bot.STATS.get("v702_a51_regime_policy_prefilter_blocks", 0) or 0)

    result = bot._orig_v453_prequalify(ranked, {"ABC/USDT": snap})
    assert result == (False, "family_regime_disallowed.macro")
    assert int(bot.STATS.get("v702_a51_regime_policy_prefilter_blocks", 0) or 0) == old_count + 1
    assert int(bot.STATS.get("v702_a51_regime_policy_prefilter_saved_checks", 0) or 0) >= 2


def test_a51_crash_guard_and_live_regime_policy_contracts_remain_unchanged():
    pullback_meta = bot.CanonicalStrategyPolicyRegistry.get("PULLBACK") or {}
    assert "BEARISH" not in {str(x).upper() for x in pullback_meta.get("allowed_regimes", ())}
    assert bot.CONFIG["V702_A48_BEARISH_V518_LIVE_ENABLE"] is False
    assert bot.CONFIG["V702_A48_BEARISH_NORMAL_SHADOW_ONLY"] is True
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False
    assert bot.FINAL_CANONICAL_RUNTIME["live_gates_relaxed"] is False
    assert bot.FINAL_CANONICAL_RUNTIME["active_post_audit_patch_revision"].startswith("V702-A51-")
    assert "OPERATOR-DIGEST-TELEMETRY-CLOSURE" in bot.FINAL_CANONICAL_RUNTIME["active_post_audit_patch_revision"]
    source = Path(bot.__file__).read_text(encoding="utf-8")
    assert "Post-audit patch:" in source and "post_audit_patch_revision={_post_audit_patch_revision}" in source

    # The throughput optimization must be visible to the operator, but remains
    # a diagnostic only: this line must not alter any policy/entry gates.
    keys = (
        "v702_a51_regime_policy_prefilter_blocks",
        "v702_a51_regime_policy_prefilter_saved_checks",
        "v702_a51_regime_policy_prefilter_errors",
        "v702_a51_regime_policy_prefilter_last_error",
    )
    old = {key: bot.STATS.get(key) for key in keys}
    try:
        bot.STATS[keys[0]] = 7
        bot.STATS[keys[1]] = 14
        bot.STATS[keys[2]] = 1
        bot.STATS[keys[3]] = "TypeError"
        digest = bot._V702R28TelegramDigest.build()
        assert "A51_POLICY_PREFILTER process_total blocks=7 saved_checks=14 errors=1 last_error=TypeError" in digest
    finally:
        for key, value in old.items():
            if value is None:
                bot.STATS.pop(key, None)
            else:
                bot.STATS[key] = value
