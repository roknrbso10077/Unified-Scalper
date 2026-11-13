from __future__ import annotations

from collections import defaultdict, deque
from types import SimpleNamespace

import main as bot


def test_a47_policy_allowlists_are_explicit_and_pullback_stays_non_bearish():
    assert bot.V43_STRATEGY_POLICY_META
    for mode, meta in bot.V43_STRATEGY_POLICY_META.items():
        assert isinstance(meta, dict), mode
        assert meta.get("allowed_regimes"), mode
        assert all(str(v).upper() in {"BULLISH", "NEUTRAL", "BEARISH", "CRASH"}
                   for v in meta["allowed_regimes"]), mode
    pullback = {str(v).upper() for v in bot.V43_STRATEGY_POLICY_META["PULLBACK"]["allowed_regimes"]}
    assert "BEARISH" not in pullback
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False
    assert bot.CONFIG["V702_A47_BEARISH_V518_LIVE_ENABLE"] is False


def test_a47_stale_snapshot_reuse_fails_closed(monkeypatch):
    candidate = SimpleNamespace(
        generated_at_ms=1_000_000,
        features_snapshot={"v688_prequal_verdict": {"verdict": True, "timestamp": 1_999.0, "cycle_id": "7"}},
    )
    monkeypatch.setattr(bot, "WALL_NOW", lambda: 2_000.0)
    monkeypatch.setattr(bot, "_wall_age_sec", lambda _value: 46.0)
    assert bot._v690_prequal_snapshot_reusable(candidate, {"cycle_id": "7"}) is False


def test_a47_ring_capacity_and_window_coverage_are_distinct(monkeypatch):
    cls = bot.V702PipelineMetrics
    old = (cls._events, cls._event_counts_by_second, cls._event_bucket_order,
           cls._drop_counts_by_second, cls._drop_bucket_order, cls._events_dropped_total,
           cls._cycle_events_dropped_total, cls._cycle_id, cls._enabled)
    try:
        assert bot._v702_pipeline_event_buffer_maxlen() >= 20_000
        monkeypatch.setattr(bot, "WALL_NOW", lambda: 2_000.0)
        cls._enabled = True
        cls._cycle_id = 7
        cls._events = deque([
            {"ts": 199.0, "stage": "DISCOVERY", "candidate_key": "old", "details": {}},
            {"ts": 1_950.0, "stage": "RANKED", "candidate_key": "new", "details": {}},
        ], maxlen=20_000)
        cls._event_counts_by_second = {199: 1, 1950: 1}
        cls._event_bucket_order = deque([199, 1950])
        cls._drop_counts_by_second = {}
        cls._drop_bucket_order = deque()
        cls._events_dropped_total = 0
        cls._cycle_events_dropped_total = 0
        covered = cls.window_line(interval_sec=1_800.0, now=2_000.0)
        assert "window_covered=yes" in covered
        assert "event_retention_complete=yes" in covered
        assert "evict_rate_pct=0.0" in covered

        cls._events = deque([
            {"ts": 1_950.0, "stage": "RANKED", "candidate_key": "retained", "details": {}},
        ], maxlen=1)
        cls._event_counts_by_second = {1950: 2}
        cls._event_bucket_order = deque([1950])
        cls._drop_counts_by_second = {1950: 1}
        cls._drop_bucket_order = deque([1950])
        cls._events_dropped_total = 1
        cls._cycle_events_dropped_total = 1
        incomplete = cls.window_line(interval_sec=1_800.0, now=2_000.0)
        assert "window_covered=no" in incomplete
        assert "event_retention_complete=no" in incomplete
        assert "buffer_truncated=yes" in incomplete
        assert "retained_oldest_age_sec=50" in incomplete
        assert "evict_rate_pct=50.0" in incomplete
    finally:
        (cls._events, cls._event_counts_by_second, cls._event_bucket_order,
         cls._drop_counts_by_second, cls._drop_bucket_order, cls._events_dropped_total,
         cls._cycle_events_dropped_total, cls._cycle_id, cls._enabled) = old


def test_a47_duplicate_rejection_is_counted_once_per_candidate_cycle(monkeypatch):
    cls = bot.V702PipelineMetrics
    attrs = ("_events", "_event_counts_by_second", "_event_bucket_order", "_drop_counts_by_second",
             "_drop_bucket_order", "_events_dropped_total", "_cycle_events_dropped_total", "_cycle_id",
             "_enabled", "_reasons", "_cycle_reasons", "_cycle_reason_keys", "_cycle_keys",
             "_cycle_counts", "_epoch_counts", "_rejection_view_dirty", "_last_block")
    old = {name: getattr(cls, name) for name in attrs}
    old_cycle = bot.STATS.get("v681_runtime_cycle_id")
    token = None
    try:
        monkeypatch.setattr(bot, "WALL_NOW", lambda: 2_000.0)
        bot.STATS["v681_runtime_cycle_id"] = 7
        cls._events = deque(maxlen=20_000)
        cls._event_counts_by_second = {}
        cls._event_bucket_order = deque()
        cls._drop_counts_by_second = {}
        cls._drop_bucket_order = deque()
        cls._events_dropped_total = cls._cycle_events_dropped_total = 0
        cls._cycle_id = 7
        cls._enabled = True
        cls._reasons = defaultdict(int)
        cls._cycle_reasons = defaultdict(int)
        cls._cycle_reason_keys = set()
        cls._cycle_keys = defaultdict(set)
        cls._cycle_counts = defaultdict(int)
        cls._epoch_counts = defaultdict(int)
        cls._rejection_view_dirty = True
        cls._last_block = {}
        token = bot._V702_PIPELINE_CONTEXT.set({"candidate_key": "7|XRP/USDT|PULLBACK|TEST|123", "symbol": "XRP/USDT"})
        for _ in range(3):
            cls.reject("trace-123", "XRP/USDT", "family_policy", "family_regime_disallowed.macro", "family_policy", {})
        reason_key = "family_policy:family_regime_disallowed.macro"
        assert cls._cycle_reasons[reason_key] == 1
        assert cls._reasons[reason_key] == 1
        assert cls._cycle_reason_keys == {(7, "7|XRP/USDT|PULLBACK|TEST|123", reason_key)}
    finally:
        if token is not None:
            bot._V702_PIPELINE_CONTEXT.reset(token)
        for name, value in old.items():
            setattr(cls, name, value)
        if old_cycle is None:
            bot.STATS.pop("v681_runtime_cycle_id", None)
        else:
            bot.STATS["v681_runtime_cycle_id"] = old_cycle


def test_a47_preflight_rechecks_do_not_inflate_arbiter_prequal(monkeypatch):
    cls = bot.V702PipelineMetrics
    attrs = ("_events", "_event_counts_by_second", "_event_bucket_order", "_drop_counts_by_second",
             "_drop_bucket_order", "_events_dropped_total", "_cycle_events_dropped_total", "_cycle_id",
             "_enabled", "_cycle_keys", "_cycle_counts", "_epoch_counts", "_reasons", "_cycle_reasons",
             "_cycle_reason_keys", "_rejection_view_dirty", "_last_block")
    old = {name: getattr(cls, name) for name in attrs}
    old_cycle = bot.STATS.get("v681_runtime_cycle_id")
    token = None
    try:
        monkeypatch.setattr(bot, "WALL_NOW", lambda: 2_000.0)
        bot.STATS["v681_runtime_cycle_id"] = 7
        cls._events = deque(maxlen=20_000)
        cls._event_counts_by_second = {}
        cls._event_bucket_order = deque()
        cls._drop_counts_by_second = {}
        cls._drop_bucket_order = deque()
        cls._events_dropped_total = cls._cycle_events_dropped_total = 0
        cls._cycle_id = 7
        cls._enabled = True
        cls._cycle_keys = defaultdict(set)
        cls._cycle_counts = defaultdict(int)
        cls._epoch_counts = defaultdict(int)
        cls._reasons = defaultdict(int)
        cls._cycle_reasons = defaultdict(int)
        cls._cycle_reason_keys = set()
        cls._rejection_view_dirty = True
        cls._last_block = {}
        monkeypatch.setattr(bot, "_V702_PREQUAL_ORIGINAL", lambda _r, _snap: (False, "test_reject"))
        monkeypatch.setattr(bot, "_V702_R39_RECORD_PREQUAL", lambda *_args: None, raising=False)
        candidate = SimpleNamespace(symbol="XRP/USDT", family="PULLBACK", strategy_mode="PULLBACK", generated_at_ms="a47-123")
        token = bot._V702_PREQUAL_SOURCE.set("preflight")
        result = bot._v702_prequal_observed(candidate, {"XRP/USDT": {"snapshot_id": "a47-123"}})
        assert result == (False, "test_reject")
        assert cls._cycle_counts["PREQUAL_PREFLIGHT_SEEN"] == 1
        assert cls._cycle_counts["PREQUAL_PREFLIGHT_REJECT"] == 1
        assert cls._cycle_counts.get("PREQUAL_SEEN", 0) == 0
        assert cls._cycle_counts.get("PREQUAL_REJECT", 0) == 0
    finally:
        if token is not None:
            bot._V702_PREQUAL_SOURCE.reset(token)
        for name, value in old.items():
            setattr(cls, name, value)
        if old_cycle is None:
            bot.STATS.pop("v681_runtime_cycle_id", None)
        else:
            bot.STATS["v681_runtime_cycle_id"] = old_cycle


def test_a47_macro_policy_cannot_be_overridden_by_cached_prequal():
    source = bot._v702_read_source_text()
    # The old bypass assignment is removed; the current-policy rejection remains authoritative.
    block = source.split("if not _canonical_regime_ok and _v689_reuse_prequal:", 1)[-1].split("if not _canonical_regime_ok:", 1)[0]
    assert "BLOCKED_CURRENT_POLICY_AUTHORITATIVE" in block
    assert "_canonical_regime_ok = True" not in block
    assert bot._v518_neutral_local_htf_bridge(None, None, None, None, "BEARISH", "LOCAL_BULLISH", 0.9, "PULLBACK")[0] is False


def test_a47_active_digest_and_source_identity_are_canonical():
    assert bot.CONFIG["V702_R28_TELEGRAM_DIGEST_INTERVAL_SEC"] == 1800.0
    assert bot.CANONICAL_RUNTIME_IDENTITY == bot.FINAL_CANONICAL_RUNTIME["public_runtime_identity"]
    digest = bot.FINAL_CANONICAL_RUNTIME["canonical_source_sha256"]
    assert len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
    assert bot.STATS["v702_a47_terminal_self_test"]["pass"] is True
