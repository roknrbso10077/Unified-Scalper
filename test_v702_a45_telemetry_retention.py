from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import defaultdict, deque
from pathlib import Path
from unittest.mock import patch

import main as bot

ROOT = Path(__file__).resolve().parent


def test_a45_event_drop_counts_are_scoped_by_cycle_and_live_epoch(monkeypatch):
    cls = bot.V702PipelineMetrics
    attr_names = (
        "_events", "_events_dropped_total", "_cycle_events_dropped_total", "_enabled", "_cycle_id",
        "_cycle_keys", "_cycle_counts", "_epoch_counts", "_event_counts_by_second", "_event_bucket_order",
        "_drop_counts_by_second", "_drop_bucket_order", "_reasons", "_cycle_reasons", "_rejection_view_dirty", "_last_block",
    )
    old_attrs = {name: getattr(cls, name) for name in attr_names}
    stat_keys = ("v681_runtime_cycle_id", "v702_pipeline_events_dropped_total", "v702_pipeline_epoch_dropped", "v702_pipeline_cycle_dropped")
    missing = object()
    old_stats = {key: bot.STATS.get(key, missing) for key in stat_keys}
    try:
        monkeypatch.setattr(bot, "WALL_NOW", lambda: 1000.0)
        bot.STATS["v681_runtime_cycle_id"] = 10
        cls._events = deque(maxlen=1)
        cls._events_dropped_total = 0
        cls._cycle_events_dropped_total = 0
        cls._enabled = True
        cls._cycle_id = 10
        cls._cycle_keys = defaultdict(set)
        cls._cycle_counts = defaultdict(int)
        cls._epoch_counts = defaultdict(int)
        cls._event_counts_by_second = {}
        cls._event_bucket_order = deque()
        cls._drop_counts_by_second = {}
        cls._drop_bucket_order = deque()
        cls._reasons = defaultdict(int)
        cls._cycle_reasons = defaultdict(int)
        cls._rejection_view_dirty = True
        cls._last_block = {}

        cls.record("DISCOVERY", "A")
        cls.record("RANKED", "B")
        cls.record("PREQUAL_REJECT", "C", details={"reason": "family_regime_disallowed.macro"})
        snap = cls.drop_health_snapshot(interval_sec=900, now=1000.0)
        assert snap["events_last_window"] == 3
        assert snap["dropped_last_window"] == 2
        assert snap["epoch_dropped"] == 2
        assert snap["cycle_dropped"] == 2
        assert snap["drop_pct_last_window"] == 66.667

        bot.STATS["v681_runtime_cycle_id"] = 11
        cls.record("DISCOVERY", "D")
        snap2 = cls.drop_health_snapshot(interval_sec=900, now=1000.0)
        assert snap2["epoch_dropped"] == 3
        assert snap2["cycle_dropped"] == 1
        assert bot.STATS["v702_pipeline_events_dropped_total"] == 3
        assert bot.STATS["v702_pipeline_epoch_dropped"] == 3
        assert bot.STATS["v702_pipeline_cycle_dropped"] == 1
    finally:
        for name, value in old_attrs.items():
            setattr(cls, name, value)
        for key, value in old_stats.items():
            if value is missing:
                bot.STATS.pop(key, None)
            else:
                bot.STATS[key] = value


def test_a45_pipeline_window_reports_real_duration_and_drop_scopes(monkeypatch):
    cls = bot.V702PipelineMetrics
    old = (cls._events, cls._enabled, cls._drop_counts_by_second, cls._event_counts_by_second,
           cls._events_dropped_total, cls._cycle_events_dropped_total)
    try:
        monkeypatch.setattr(bot, "WALL_NOW", lambda: 1000.0)
        cls._events = deque([
            {"ts": 990.0, "stage": "DISCOVERY", "candidate_key": "C1", "details": {}},
        ], maxlen=1)
        cls._enabled = True
        cls._drop_counts_by_second = {995: 2}
        cls._event_counts_by_second = {990: 2, 995: 3}
        cls._events_dropped_total = 8
        cls._cycle_events_dropped_total = 2
        line = cls.window_line(interval_sec=900.0, now=1000.0)
        assert "PIPELINE[WINDOW_15M]" in line
        assert "interval_sec=900" in line
        assert "window_dropped=2" in line
        assert "cycle_dropped=2" in line
        assert "epoch_dropped_cumulative=8" in line
        assert "buffer_truncated=yes" in line
    finally:
        (cls._events, cls._enabled, cls._drop_counts_by_second, cls._event_counts_by_second,
         cls._events_dropped_total, cls._cycle_events_dropped_total) = old


def test_a45_score_floor_and_bearish_bridge_remain_fail_closed():
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70.0
    assert bot.CONFIG["V453_SCORE_FLOOR_MIN"] >= 70.0
    assert bot.V647_CANONICAL_HARD_POLICY["V453_SCORE_FLOOR_MIN"] >= 70.0
    ok, strength, context = bot._v518_neutral_local_htf_bridge(
        None, None, None, None, "BEARISH", "LOCAL_RECOVERY", 50.0, "MEAN_REVERSION"
    )
    assert ok is False
    assert strength == 50.0
    assert context.get("reason") == "not_eligible"
    assert bot.FINAL_CANONICAL_RUNTIME.get("hard_gate_bypass") is False
    assert bot.FINAL_CANONICAL_RUNTIME.get("live_gates_relaxed") is False


def test_a45_starvation_digest_has_explicit_root():
    # Other tests may intentionally leave a simulated global safety latch active.
    # Isolate this diagnostic-unit test so it exercises the ordinary policy root.
    old_block = bot.LIVE_ENTRIES_BLOCKED
    try:
        bot.LIVE_ENTRIES_BLOCKED = {"active": False, "reason": "", "where": "a45_test"}
        line = bot._V702R28TelegramDigest._starvation_line(
            "mode=POLICY live_root=POLICY generated_delta=10 prequal_pass_delta=0 ranked_delta=10 selected_delta=0 queued_delta=0 sent_delta=0"
        )
        assert "starvation_root=POLICY" in line
        assert "root=POLICY" in line
    finally:
        bot.LIVE_ENTRIES_BLOCKED = old_block


def test_a45_healthcheck_warns_on_telemetry_drop_without_forcing_restart(tmp_path):
    heartbeat = tmp_path / "heartbeat.json"
    heartbeat.write_text(json.dumps({
        "timestamp": time.time(), "state": "FULL_LIVE_RUNNING",
        "telemetry": {"events_last_window": 100, "dropped_last_window": 15, "drop_pct_last_window": 15.0},
    }), encoding="utf-8")
    script = ROOT / "healthcheck.py"
    runtime = tmp_path / "runtime.json"
    runtime.write_text(json.dumps({"timestamp": time.time(), "state": "RUNNING", "open_positions": 0, "boot_id": "test-boot"}), encoding="utf-8")
    env = {**os.environ, "V702_HEARTBEAT_FILE": str(heartbeat), "V702_RUNTIME_HEARTBEAT_FILE": str(runtime), "V702_HEALTHCHECK_TELEMETRY_DROP_THRESHOLD_PCT": "10"}
    env.pop("V702_HEALTHCHECK_FAIL_ON_TELEMETRY_DEGRADE", None)
    warn = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True, timeout=5)
    assert warn.returncode == 0
    assert "telemetry=DEGRADED" in warn.stdout

    env["V702_HEALTHCHECK_FAIL_ON_TELEMETRY_DEGRADE"] = "1"
    strict = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True, timeout=5)
    assert strict.returncode == 1
    assert "telemetry=DEGRADED" in strict.stdout


def test_a45_healthcheck_preserves_liveness_when_telemetry_is_unavailable(tmp_path):
    heartbeat = tmp_path / "heartbeat.json"
    heartbeat.write_text(json.dumps({"timestamp": time.time(), "state": "FULL_LIVE_RUNNING"}), encoding="utf-8")
    runtime = tmp_path / "runtime.json"
    runtime.write_text(json.dumps({"timestamp": time.time(), "state": "RUNNING", "open_positions": 0, "boot_id": "test-boot"}), encoding="utf-8")
    env = {**os.environ, "V702_HEARTBEAT_FILE": str(heartbeat), "V702_RUNTIME_HEARTBEAT_FILE": str(runtime)}
    env.pop("V702_HEALTHCHECK_FAIL_ON_TELEMETRY_DEGRADE", None)
    result = subprocess.run([sys.executable, str(ROOT / "healthcheck.py")], env=env, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    assert "telemetry=unavailable" in result.stdout
