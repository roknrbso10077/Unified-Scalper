from __future__ import annotations

from collections import defaultdict, deque
from types import SimpleNamespace

import main as bot


def test_ring_eviction_counts_the_lost_record_timestamp(monkeypatch):
    cls = bot.V702PipelineMetrics
    class_attrs = (
        "_events", "_events_dropped_total", "_cycle_events_dropped_total", "_enabled", "_cycle_id",
        "_cycle_keys", "_cycle_counts", "_epoch_counts", "_event_counts_by_second", "_event_bucket_order",
        "_drop_counts_by_second", "_drop_bucket_order", "_reasons", "_cycle_reasons",
        "_rejection_view_dirty", "_last_block",
    )
    old_attrs = {name: getattr(cls, name) for name in class_attrs}
    stat_keys = (
        "v681_runtime_cycle_id", "v702_pipeline_events_dropped_total", "v702_pipeline_epoch_dropped",
        "v702_pipeline_cycle_dropped", "v702_pipeline_epoch.DISCOVERY", "v702_pipeline_cycle_id",
        "v702_pipeline_cycle_counts", "v702_pipeline_epoch_counts", "v702_pipeline_top_rejections_epoch",
        "v702_pipeline_top_rejections_cycle", "v702_pipeline_top_rejections", "v702_pipeline_last_block",
    )
    missing = object()
    old_stats = {key: bot.STATS.get(key, missing) for key in stat_keys}
    try:
        monkeypatch.setattr(bot, "WALL_NOW", lambda: 1000.0)
        bot.STATS["v681_runtime_cycle_id"] = 3
        cls._events = deque([
            {"cycle_id": 3, "stage": "DISCOVERY", "candidate_key": "OLD", "ts": 50.0,
             "symbol": "OLD/USDT", "family": "PULLBACK", "details": {}},
        ], maxlen=1)
        cls._events_dropped_total = 0
        cls._cycle_events_dropped_total = 0
        cls._enabled = True
        cls._cycle_id = 3
        cls._cycle_keys = defaultdict(set)
        cls._cycle_counts = defaultdict(int)
        cls._epoch_counts = defaultdict(int)
        cls._event_counts_by_second = {50: 1}
        cls._event_bucket_order = deque([50])
        cls._drop_counts_by_second = {}
        cls._drop_bucket_order = deque()
        cls._reasons = defaultdict(int)
        cls._cycle_reasons = defaultdict(int)
        cls._rejection_view_dirty = True
        cls._last_block = {}

        cls.record("DISCOVERY", "NEW", symbol="NEW/USDT", family="PULLBACK")
        snap = cls.drop_health_snapshot(interval_sec=900, now=1000.0)
        line = cls.window_line(interval_sec=900, now=1000.0)

        # The new event evicted a record from ts=50, outside the window starting at ts=100.
        assert snap["epoch_dropped"] == 1
        assert snap["dropped_last_window"] == 0
        assert snap["events_last_window"] == 1
        assert snap["drop_pct_last_window"] == 0.0
        assert "window_dropped=0" in line
        assert "window_events=1" in line
        assert "evict_rate_pct=0.0" in line
        assert "buffer_truncated=no" in line
        assert "event_retention_complete=yes" in line
        assert "window_covered=no" in line  # one retained event is not proof of a full 15m interval
    finally:
        for name, value in old_attrs.items():
            setattr(cls, name, value)
        for key, value in old_stats.items():
            if value is missing:
                bot.STATS.pop(key, None)
            else:
                bot.STATS[key] = value


def test_macro_policy_evidence_exposes_regime_and_allow_list_without_policy_change():
    candidate = SimpleNamespace(
        symbol="A46/USDT", family="PULLBACK", strategy_mode="PULLBACK",
        features_snapshot={"macro_regime": "BEARISH", "local_regime": "LOCAL_BEARISH"},
    )
    evidence = bot._v702_prequal_policy_evidence(
        candidate,
        {"A46/USDT": {"macro_regime": "BEARISH", "local_regime": "LOCAL_BEARISH", "macro_severity": "BEARISH_NORMAL"}},
    )
    assert evidence["policy_macro_regime"] == "BEARISH"
    assert evidence["policy_mode"] == "PULLBACK"
    assert evidence["policy_allowed_macro_regimes"]
    assert "BEARISH" not in evidence["policy_allowed_macro_regimes"]
    assert bot.FINAL_CANONICAL_RUNTIME.get("hard_gate_bypass") is False
    assert bot.FINAL_CANONICAL_RUNTIME.get("live_gates_relaxed") is False


def test_window_digest_includes_policy_context_for_macro_rejections(monkeypatch):
    cls = bot.V702PipelineMetrics
    old = (cls._events, cls._event_counts_by_second, cls._event_bucket_order,
           cls._drop_counts_by_second, cls._drop_bucket_order, cls._events_dropped_total,
           cls._cycle_events_dropped_total, cls._cycle_id)
    try:
        monkeypatch.setattr(bot, "WALL_NOW", lambda: 1000.0)
        cls._events = deque([{
            "cycle_id": 1, "stage": "PREQUAL_REJECT", "candidate_key": "A46-C1",
            "symbol": "A46/USDT", "family": "PULLBACK", "ts": 950.0,
            "details": {
                "reason": "family_regime_disallowed.macro",
                "policy_mode": "PULLBACK", "policy_family": "PULLBACK",
                "policy_macro_regime": "BEARISH",
                "policy_allowed_macro_regimes": ["BULLISH", "NEUTRAL"],
            },
        }], maxlen=4096)
        cls._event_counts_by_second = {950: 1}
        cls._event_bucket_order = deque([950])
        cls._drop_counts_by_second = {}
        cls._drop_bucket_order = deque()
        cls._events_dropped_total = 0
        cls._cycle_events_dropped_total = 0
        cls._cycle_id = 1
        line = cls.window_line(interval_sec=900, now=1000.0)
        assert "policy_ctx_top=" in line
        assert "PULLBACK@BEARISH" in line
        assert "allow=BULLISH+NEUTRAL" in line
    finally:
        (cls._events, cls._event_counts_by_second, cls._event_bucket_order,
         cls._drop_counts_by_second, cls._drop_bucket_order, cls._events_dropped_total,
         cls._cycle_events_dropped_total, cls._cycle_id) = old
