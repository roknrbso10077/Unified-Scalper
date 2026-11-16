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
    runtime.write_text(json.dumps({"timestamp": now, "boot_id": boot, "open_positions": 1,
                                   "open_position_ids": ["ABC/USDT|trade-a"]}), encoding="utf-8")
    manager.write_text(json.dumps({"timestamp": now, "boot_id": boot, "open_positions": 1,
                                   "open_position_ids": ["ABC/USDT|trade-a"],
                                   "managed_position_ids": ["ABC/USDT|trade-a"],
                                   "state": "RUNNING", "healthy_ticks": 1}), encoding="utf-8")
    for key, value in {
        "V702_HEARTBEAT_FILE": str(heartbeat),
        "V702_RUNTIME_HEARTBEAT_FILE": str(runtime),
        "V702_PM_HEARTBEAT_FILE": str(manager),
        "V702_RUNTIME_HEARTBEAT_STALE_SEC": "60",
        "V702_PM_HEARTBEAT_STALE_SEC": "30",
    }.items():
        monkeypatch.setenv(key, value)
    assert healthcheck.main() == 0
    # Matching counts are not sufficient: every runtime position must be
    # identified and explicitly covered by the manager's successful cycle.
    runtime.write_text(json.dumps({"timestamp": now, "boot_id": boot, "open_positions": 2,
                                   "open_position_ids": ["ABC/USDT|trade-a", "XYZ/USDT|trade-b"]}), encoding="utf-8")
    manager.write_text(json.dumps({"timestamp": now, "boot_id": boot, "open_positions": 1,
                                   "open_position_ids": ["ABC/USDT|trade-a"],
                                   "managed_position_ids": ["ABC/USDT|trade-a"],
                                   "state": "RUNNING", "healthy_ticks": 1}), encoding="utf-8")
    assert healthcheck.main() == 1
    manager.write_text(json.dumps({"timestamp": now, "boot_id": boot, "open_positions": 2,
                                   "open_position_ids": ["ABC/USDT|trade-a", "XYZ/USDT|trade-b"],
                                   "managed_position_ids": ["ABC/USDT|trade-a"],
                                   "state": "RUNNING", "healthy_ticks": 1}), encoding="utf-8")
    assert healthcheck.main() == 1
    runtime.write_text(json.dumps({"timestamp": now, "boot_id": boot, "open_positions": 1,
                                   "open_position_ids": ["ABC/USDT|trade-a"]}), encoding="utf-8")
    manager.write_text(json.dumps({"timestamp": now, "boot_id": boot, "open_positions": 1,
                                   "open_position_ids": ["ABC/USDT|trade-a"],
                                   "managed_position_ids": ["ABC/USDT|trade-a"],
                                   "state": "RUNNING", "healthy_ticks": 1}), encoding="utf-8")
    manager.write_text(json.dumps({"timestamp": now, "boot_id": boot, "open_positions": 1, "state": "ERROR", "healthy_ticks": 1}), encoding="utf-8")
    assert healthcheck.main() == 1
    manager.write_text(json.dumps({"timestamp": now, "boot_id": boot, "open_positions": 1, "state": "RUNNING", "healthy_ticks": 0}), encoding="utf-8")
    assert healthcheck.main() == 1
    manager.write_text(json.dumps({"timestamp": now - 60, "boot_id": boot, "open_positions": 1, "state": "RUNNING", "healthy_ticks": 1}), encoding="utf-8")
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


def test_a69_canonical_release_identity_and_current_audit_revision_are_coherent():
    runtime = main.FINAL_CANONICAL_RUNTIME
    identity = main.V702_A66_RELEASE_TAG
    compatibility_identity = main.V702_A64_RELEASE_TAG
    active_patch = main.V702_A66_POST_AUDIT_PATCH_REVISION
    active_audit_merge = "A69-MERGED-PRODUCTION-AUDIT-CLOSURES-2026-11-15"

    assert main.V702_FINAL_CANONICAL_RELEASE == compatibility_identity
    assert main.CONFIG["V702_FINAL_CANONICAL_RUNTIME_IDENTITY"] == compatibility_identity
    assert main.CONFIG["V702_FINAL_DISTRIBUTION_RELEASE_TAG"] == identity
    assert runtime["active_release_tag"] == identity
    assert runtime["active_distribution_release_tag"] == identity
    assert runtime["active_post_audit_patch_revision_current"] == active_patch
    assert runtime["active_audit_merge_revision_current"] == active_audit_merge
    assert runtime["package_revision"] == main.V702_PACKAGE_AUDIT_REVISION
    assert runtime["active_package_revision_current"] == main.V702_PACKAGE_AUDIT_REVISION
    assert main.STATS["v702_a69_canonical_identity_closure"]["pass"] is True
    assert runtime["effective_entry_policy"] == "MONITOR_ONLY_NO_NEW_BUYS"
    assert runtime["production_decision"] == "NO_GO_UNATTENDED_LIVE"
    assert runtime["hard_gate_bypass"] is False
    assert runtime["live_gates_relaxed"] is False

    # Historical A51 remains available for backwards-compatible readers, but
    # live startup and the operator Telegram view must prefer the *_current key.
    assert runtime["active_post_audit_patch_revision"].startswith("V702-A51-")
    source = Path(main.__file__).read_text(encoding="utf-8")
    assert source.count('get("active_post_audit_patch_revision_current")') >= 1
    assert 'get("active_post_audit_patch_revision_current")' in source
    assert "post_audit_patch_revision={_post_audit_patch_revision}" in source
    assert "[V702-STARTUP-PHASE] phase=validate_config_begin" in source
    assert "[V702-STARTUP-PHASE] phase=validate_config_end" in source
    assert "[V702-STARTUP-PHASE] phase=run_bot_enter" in source


def test_a70_audit_identity_is_applied_before_validate_only_and_persistent_entrypoint():
    source = Path(main.__file__).read_text(encoding="utf-8")
    revision_pos = source.index('V702_A70_ENTRYPOINT_IDENTITY_REVISION = "A70-ENTRYPOINT-AUDIT-IDENTITY-CLOSURE-2026-11-16"')
    merge_identity_pos = source.index('V702_A69_MERGED_AUDIT_REVISION = "A69-MERGED-PRODUCTION-AUDIT-CLOSURES-2026-11-15"')
    validate_cli_pos = source.index("\nif _V699_VALIDATE_ONLY_REQUEST:")
    main_guard_pos = source.index('\nif __name__ == "__main__":')
    main_call_pos = source.index("    main()", main_guard_pos)

    assert revision_pos < merge_identity_pos < validate_cli_pos < main_guard_pos < main_call_pos
    assert main.V702_PACKAGE_AUDIT_REVISION.endswith(main.V702_A70_ENTRYPOINT_IDENTITY_REVISION)
    assert main.FINAL_CANONICAL_RUNTIME["active_audit_merge_revision_current"] == main.V702_A69_MERGED_AUDIT_REVISION
    assert main.FINAL_CANONICAL_RUNTIME["active_entrypoint_identity_revision_current"] == main.V702_A70_ENTRYPOINT_IDENTITY_REVISION
    assert main.FINAL_CANONICAL_RUNTIME["active_package_revision_current"] == main.V702_PACKAGE_AUDIT_REVISION
    assert main.STATS["v702_a69_canonical_identity_closure"]["pass"] is True
    assert main.STATS["v702_a70_entrypoint_identity_closure"]["pass"] is True
    assert main.STATS["v702_a70_entrypoint_identity_closure"]["live_authority_changed"] is False
    assert 'audit_merge_revision={_audit_merge_revision}' in source
    assert 'entrypoint_identity_revision={_entrypoint_identity_revision}' in source


def test_v702_public_mexc_client_has_no_private_credentials(monkeypatch):
    from types import SimpleNamespace

    captured = {}
    fake_client = object()

    def fake_mexc(config):
        captured.update(config)
        return fake_client

    monkeypatch.setattr(main, "_CCXT_OK", True)
    monkeypatch.setattr(main, "ccxt_async", SimpleNamespace(mexc=fake_mexc), raising=False)
    monkeypatch.setitem(main.ENV, "MEXC_API_KEY", None)
    monkeypatch.setitem(main.ENV, "MEXC_API_SECRET", None)

    client = main.ExchangeFactory.create_mexc_public_async()

    assert client is fake_client
    assert captured.get("enableRateLimit") is True
    assert captured.get("options", {}).get("defaultType") == "spot"
    assert "apiKey" not in captured
    assert "secret" not in captured
    assert main.STATS["v702_public_market_client_authenticated"] is False



def test_v702_public_mexc_client_ignores_invalid_private_credentials(monkeypatch):
    from types import SimpleNamespace

    captured = {}
    def fake_mexc(config):
        captured.update(config)
        return object()

    monkeypatch.setattr(main, "_CCXT_OK", True)
    monkeypatch.setattr(main, "ccxt_async", SimpleNamespace(mexc=fake_mexc), raising=False)
    monkeypatch.setitem(main.ENV, "MEXC_API_KEY", "deliberately-invalid-key")
    monkeypatch.setitem(main.ENV, "MEXC_API_SECRET", "deliberately-invalid-secret")

    client = main.ExchangeFactory.create_mexc_public_async()

    assert client is not None
    assert "apiKey" not in captured and "secret" not in captured
    assert captured == {"enableRateLimit": True, "options": {"defaultType": "spot"}}


def test_v702_btc_macro_is_descriptive_not_bullish_only(monkeypatch):
    import numpy as np
    import pandas as pd

    def make_frame(length, direction):
        if direction == "up":
            close = np.linspace(100.0, 220.0, length)
        elif direction == "down":
            close = np.linspace(220.0, 100.0, length)
        else:
            close = np.full(length, 150.0)
        return pd.DataFrame({"close": close})

    bullish = main._v702_classify_btc_macro_context(make_frame(70, "up"), make_frame(230, "up"))
    bearish = main._v702_classify_btc_macro_context(make_frame(70, "down"), make_frame(230, "down"))
    neutral = main._v702_classify_btc_macro_context(make_frame(70, "flat"), make_frame(230, "flat"))
    unknown = main._v702_classify_btc_macro_context(None, None)

    assert bullish["regime"] == "BULLISH"
    assert bearish["regime"] == "BEARISH"
    assert neutral["regime"] == "NEUTRAL"
    assert unknown["regime"] == "UNKNOWN"
    for context in (bullish, bearish, neutral, unknown):
        assert context["informational_only"] is True
        assert context["discovery_direction_gate"] is False


def test_v702_macro_telegram_notifier_sends_bearish_context_without_entry_authority(monkeypatch):
    import asyncio

    captured = []

    async def fake_enqueue(message):
        captured.append(str(message))
        return True

    monkeypatch.setitem(main.ENV, "TELEGRAM_TOKEN", "test-token")
    monkeypatch.setitem(main.ENV, "TELEGRAM_CHAT", "test-chat")
    monkeypatch.setattr(main.TelegramDispatcher, "enqueue", staticmethod(fake_enqueue))
    monkeypatch.setattr(main, "WALL_NOW", lambda: 1_800_000_000.0)
    monkeypatch.setitem(main.STATS, "v702_btc_macro_last_notified_regime", "")
    monkeypatch.setitem(main.STATS, "v702_btc_macro_last_notified_ts", 0.0)

    queued = asyncio.run(main._v702_notify_btc_macro_context({
        "regime": "BEARISH", "reason": "test_closed_context",
        "closed_1h": 60, "closed_4h": 220,
        "btc_1h_close": 100.0, "btc_1h_ema50": 101.0,
        "btc_4h_close": 90.0, "btc_4h_ema50": 95.0, "btc_4h_ema200": 110.0,
    }))

    assert queued is True
    assert len(captured) == 1
    assert "Regime: <b>BEARISH</b>" in captured[0]
    assert "does not switch off discovery" in captured[0]
    assert "MONITOR_ONLY_NO_NEW_BUYS" in captured[0]


def test_v702_read_only_macro_audits_pass_without_relaxing_live_policy():
    a66 = main._v702_a66_startup_recovery_source_check()
    a72 = main._v702_a72_read_only_runtime_source_check()

    assert a66["pass"], a66.get("failed")
    assert a66["checks"]["btc_context_and_macro_run_before_empty_universe_defer"]
    assert a66["checks"]["empty_universe_skips_scan_pipeline"]
    assert a72["pass"], a72.get("failed")
    assert main.FINAL_CANONICAL_RUNTIME["effective_entry_policy"] == "MONITOR_ONLY_NO_NEW_BUYS"
    assert main.FINAL_CANONICAL_RUNTIME["production_decision"] == "NO_GO_UNATTENDED_LIVE"
