"""V705 production-audit closure regression tests."""
from pathlib import Path
import math
import main


def test_v705_epoch_normalizes_s_ms_us_ns_and_rejects_invalid():
    expected = 1760000000.0
    assert math.isclose(main._v705_epoch_to_seconds(expected), expected, abs_tol=1e-6)
    assert math.isclose(main._v705_epoch_to_seconds(expected * 1000), expected, abs_tol=1e-6)
    assert math.isclose(main._v705_epoch_to_seconds(expected * 1e6), expected, abs_tol=1e-6)
    assert math.isclose(main._v705_epoch_to_seconds(expected * 1e9), expected, abs_tol=1e-6)
    assert main._v705_epoch_to_seconds(float("nan")) == 0.0
    assert main._v705_epoch_to_seconds(0) == 0.0
    assert main._v705_epoch_to_seconds("2026-11-07T09:00:00Z") == 0.0


def test_v705_sl_seed_alignment_and_production_invariants():
    report = main.STATS.get("v705_software_sl_tick_alignment", {})
    assert report.get("decisive_seed_covers_runtime_threshold") is True
    self_test = main.STATS.get("v705_self_test", {})
    assert self_test.get("pass") is True, self_test.get("failed")
    assert main.CONFIG["V570_SOFTWARE_SL_BREACH_CONFIRM_TICKS"] >= main.CONFIG["V702_SOFTWARE_SL_BREACH_CONFIRM_TICKS"]
    assert main.CONFIG["LONG_ONLY"] is True
    assert str(main.CONFIG["MARKET_TYPE"]).upper() == "SPOT"
    assert main.CONFIG["ALLOW_SHORT"] is False
    assert main.CONFIG["ENABLE_FUTURES"] is False


def test_v705_scan_sleep_is_bounded_and_defaulted():
    assert main.CONFIG.get("V705_SCAN_LOOP_SLEEP_SEC") == 15.0
    assert main._v705_scan_loop_sleep_seconds() == 15.0
    old = main.CONFIG.get("V705_SCAN_LOOP_SLEEP_SEC")
    try:
        main.CONFIG["V705_SCAN_LOOP_SLEEP_SEC"] = 0.1
        assert main._v705_scan_loop_sleep_seconds() == 1.0
        main.CONFIG["V705_SCAN_LOOP_SLEEP_SEC"] = 9999
        assert main._v705_scan_loop_sleep_seconds() == 300.0
    finally:
        main.CONFIG["V705_SCAN_LOOP_SLEEP_SEC"] = old


def test_v705_persistence_failure_telemetry_is_bounded_and_non_authoritative():
    before = int(main.STATS.get("v705_intent_persist_failures", 0) or 0)
    main._v705_note_persist_failure("unit_test", "TEST/USDT", RuntimeError("synthetic"))
    assert int(main.STATS.get("v705_intent_persist_failures", 0) or 0) == before + 1
    last = main.STATS["v705_last_intent_persist_failure"]
    assert last["stage"] == "unit_test"
    assert last["symbol"] == "TEST/USDT"
    assert "RuntimeError" in last["error"]


def test_v705_sr_planner_accepts_all_epoch_units_and_datetime_strings():
    import pandas as pd

    fixed_now = 1760000000.0
    candle_open = fixed_now - 1500.0  # 25 minutes old; planner adds the 15m interval.
    old_clock = main.WALL_NOW
    parse_errors_before = int(main.STATS.get("v705_sr_freshness_parse_errors", 0) or 0)
    try:
        main.WALL_NOW = lambda: fixed_now
        for factor in (1, 1_000, 1_000_000, 1_000_000_000):
            stamp = int(candle_open * factor)
            frame = pd.DataFrame({
                "timestamp": [stamp] * 60,
                "open": [100.0] * 60,
                "high": [105.0] * 60,
                "low": [95.0] * 60,
                "close": [100.0] * 60,
                "volume": [1.0] * 60,
            })
            planned = main._v702_sr_aware_target_plan(
                entry=100.0, sl=98.0, tp1_rr=1.0, tp2_rr=2.0, tp3_rr=3.0,
                df_15m=frame, atr_hint=1.0,
            )
            assert planned.get("sr_timestamp_source") == "column:timestamp"
            assert abs(float(planned.get("sr_data_age_sec", -1.0)) - 600.0) < 1e-6

        iso_stamp = pd.Timestamp(candle_open, unit="s", tz="UTC").isoformat()
        iso_frame = pd.DataFrame({
            "timestamp": [iso_stamp] * 60,
            "open": [100.0] * 60,
            "high": [105.0] * 60,
            "low": [95.0] * 60,
            "close": [100.0] * 60,
            "volume": [1.0] * 60,
        })
        iso_planned = main._v702_sr_aware_target_plan(
            entry=100.0, sl=98.0, tp1_rr=1.0, tp2_rr=2.0, tp3_rr=3.0,
            df_15m=iso_frame, atr_hint=1.0,
        )
        assert iso_planned.get("sr_timestamp_source") == "column:timestamp"
        assert abs(float(iso_planned.get("sr_data_age_sec", -1.0)) - 600.0) < 1e-6

        bad_frame = iso_frame.copy()
        bad_frame["timestamp"] = ["not-a-timestamp"] * 60
        main._v702_sr_aware_target_plan(
            entry=100.0, sl=98.0, tp1_rr=1.0, tp2_rr=2.0, tp3_rr=3.0,
            df_15m=bad_frame, atr_hint=1.0,
        )
        assert int(main.STATS.get("v705_sr_freshness_parse_errors", 0) or 0) == parse_errors_before + 1
    finally:
        main.WALL_NOW = old_clock


def test_v705_a32_a33_history_validators_use_canonical_wall_clock():
    import inspect

    for fn in (
        main._v702_a32_4h_history_integrity,
        main._v702_a33_history_integrity,
        main._v702_a33_closed_index,
    ):
        source = inspect.getsource(fn)
        assert "WALL_NOW()" in source
        assert "time.time()" not in source


def test_v705_submit_entry_has_no_silent_persistence_pass_handlers():
    import ast
    import inspect
    import textwrap

    # Parse only the original OrderExecutor.submit_entry definition. Parsing
    # the entire 5.6 MB main.py on every full-suite run is needlessly expensive
    # and can amplify memory pressure in CI.
    package_lines = Path(main.__file__).read_text(encoding="utf-8").splitlines()
    starts = [i for i, line in enumerate(package_lines)
              if line.startswith("    async def submit_entry(")]
    assert len(starts) == 1, starts
    start = starts[0]
    end = next((i for i in range(start + 1, len(package_lines))
                if package_lines[i].startswith(("    async def ", "    def ", "    @", "class "))),
               len(package_lines))
    source = textwrap.dedent("\n".join(package_lines[start:end]))
    for stage in ("maker_submission_unknown", "market_fill_unknown", "post_fill_confirmed"):
        assert stage in source
    tree = ast.parse(source)
    silent_handlers = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler)
        and len(node.body) == 1
        and isinstance(node.body[0], ast.Pass)
    ]
    assert silent_handlers == []



def test_a58_canonical_identity_cost_paper_context_and_wrapper_registry():
    assert main.V702_A58_RELEASE_TAG == "UNIFIED-SCALPER-V702-A58-CANONICAL-FINAL"
    assert main.V702_WRAPPER_CHAIN_VALIDATION["pass"] is True
    assert main.V702_WRAPPER_CHAIN_VALIDATION["submit_entry_calls_without_context"] == []
    report = main.STATS.get("v702_a58_validation", {})
    if not report:
        assert main._v702_a58_validate_config() is True
        report = main.STATS["v702_a58_validation"]
    assert report["pass"] is True, report.get("failed")
    assert report["production_decision"] == "NO_GO_UNATTENDED_LIVE"
    assert main.CONFIG["V702_KNOWLEDGE_OUTCOME_MAX_ACTIVE"] == 20
    assert main.KnowledgeOutcomeLedger.max_active() <= 120


def test_a58_healthcheck_requires_fresh_position_manager_heartbeat(tmp_path, monkeypatch):
    import json
    import time
    import healthcheck

    now = time.time()
    boot = "test-boot-a58"
    heartbeat = tmp_path / "heartbeat.json"
    runtime = tmp_path / "runtime.json"
    manager = tmp_path / "pm.json"
    heartbeat.write_text(json.dumps({"timestamp": now, "state": "RUNNING"}), encoding="utf-8")
    runtime.write_text(json.dumps({"timestamp": now, "boot_id": boot, "open_positions": 1}), encoding="utf-8")
    manager.write_text(json.dumps({"timestamp": now, "boot_id": boot, "open_positions": 1, "state": "HEALTHY"}), encoding="utf-8")
    for key, value in {
        "V702_HEARTBEAT_FILE": str(heartbeat),
        "V702_RUNTIME_HEARTBEAT_FILE": str(runtime),
        "V702_PM_HEARTBEAT_FILE": str(manager),
        "V702_RUNTIME_HEARTBEAT_STALE_SEC": "60",
        "V702_PM_HEARTBEAT_STALE_SEC": "30",
    }.items():
        monkeypatch.setenv(key, value)
    assert healthcheck.main() == 0
    manager.write_text(json.dumps({"timestamp": now - 60, "boot_id": boot, "open_positions": 1, "state": "HEALTHY"}), encoding="utf-8")
    assert healthcheck.main() == 1


def test_a58_rate_limiter_and_sqlite_async_boundary_contracts():
    import inspect
    source = Path(main.__file__).read_text(encoding="utf-8")
    assert "await _V702_PLATFORM_RATE_LIMITER.acquire(op_label)" in source
    assert "asyncio.to_thread(cls._active" in source
    assert "asyncio.to_thread(cls._update" in source
    assert "V702_KNOWLEDGE_LEDGER_WRITER_LOCK" in source
    assert "V702_EQUITY_IGNORE_ASSETS" in source
    assert "V702_EQUITY_TICKER_CACHE_TTL_SEC" in source
    assert "entry_policy_authority_missing" in inspect.getsource(main.V702PortfolioDrawdownGuard.authorize_entry.__func__)
