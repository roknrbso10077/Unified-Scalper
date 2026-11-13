import main as bot


def test_a37_release_identity_and_risk_guards_are_preserved():
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A36_CANONICAL_REVISION + "-A37-")
    assert bot.FINAL_CANONICAL_RUNTIME["package_audit_revision"] == bot.V702_PACKAGE_AUDIT_REVISION
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70.0
    assert str(bot.CONFIG.get("MARKET_TYPE", "")).upper() == "SPOT"
    assert bool(bot.CONFIG.get("LONG_ONLY", False))
    assert not bot.CONFIG.get("ENABLE_FUTURES", False)
    assert not bot.CONFIG.get("ALLOW_SHORT", False)


def test_a37_block_parser_keeps_symbol_and_stops_at_next_section():
    rec = bot._v702_a37_parse_block_record(
        "• TIA/USDT root=SCORE stage=scorer reason=score_below_threshold:69.3<70.0SELECTED → ROUTE BLOCK"
    )
    assert rec["symbol"] == "TIA/USDT"
    assert rec["root"] == "SCORE"
    assert rec["stage"] == "scorer"
    assert "SELECTED" not in rec["reason"]
    assert rec["reason"] == "score_below_threshold:69.3<70.0"


def test_a37_same_bar_tp_sl_resolves_conservatively_to_stop():
    assert bot.KnowledgeOutcomeLedger._first_touch_event(True, False, False, True, "") == "SL"
    assert bot.KnowledgeOutcomeLedger._first_touch_event(True, True, False, False, "") == "TP1"


def test_a37_html_repair_closes_open_tags_and_respects_limit():
    repaired = bot._v702_a37_repair_telegram_html("<b>heading</b>\n<b>truncated", 1000)
    assert repaired.count("<b>") == repaired.count("</b>")
    large = bot._v702_a37_repair_telegram_html("<b>" + "X" * 5000, 1200)
    assert len(large) <= 1200
    assert large.count("<b>") == large.count("</b>")


def test_a37_spread_shadow_derives_atr_percent_from_raw_atr_and_price():
    bot._v702_a34_record_spread_shadow_observation(
        "MID", 0.30, 0.22, {"features": {"atr": 0.50, "close": 100.0}}
    )
    row = bot.STATS["v702_a34_spread_shadow_last"]
    assert abs(row["atr_pct"] - 0.50) < 1e-9
    assert abs(row["spread_to_atr_ratio"] - 0.60) < 1e-9
    assert row["mode"] == "SHADOW_ONLY_NO_LIVE_RELIEF"


def test_a37_digest_block_formatter_supports_structured_records():
    rows = [{"symbol":"MBG/USDT", "root":"SCORE", "stage":"scorer", "reason":"score_below_threshold:41.2<70.0"}]
    lines = bot._V702R28TelegramDigest._format_block_lines(rows)
    assert "MBG/USDT" in lines[0]
    assert "reason=score_below_threshold:41.2&lt;70.0" in lines[0]


def test_a37_healthcheck_accepts_fresh_heartbeat(tmp_path):
    import json
    import os
    import subprocess
    import sys
    import time
    from pathlib import Path

    heartbeat = tmp_path / "heartbeat.json"
    heartbeat.write_text(json.dumps({"timestamp": time.time(), "state": "FULL_LIVE_RUNNING"}), encoding="utf-8")
    runtime = tmp_path / "runtime.json"
    runtime.write_text(json.dumps({"timestamp": time.time(), "state": "RUNNING", "open_positions": 0, "boot_id": "test-boot"}), encoding="utf-8")
    env = dict(os.environ, V702_HEARTBEAT_FILE=str(heartbeat), V702_RUNTIME_HEARTBEAT_FILE=str(runtime))
    result = subprocess.run([sys.executable, str(Path(bot.__file__).with_name("healthcheck.py"))], env=env, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "healthy:" in result.stdout


def test_a37_healthcheck_rejects_stale_or_missing_heartbeat(tmp_path):
    import json
    import os
    import subprocess
    import sys
    import time
    from pathlib import Path

    healthcheck = Path(bot.__file__).with_name("healthcheck.py")
    stale = tmp_path / "stale.json"
    stale.write_text(json.dumps({"timestamp": time.time() - 1000, "state": "FULL_LIVE_RUNNING"}), encoding="utf-8")
    env = dict(os.environ, V702_HEARTBEAT_FILE=str(stale), V702_HEARTBEAT_STALE_SEC="420")
    result = subprocess.run([sys.executable, str(healthcheck)], env=env, capture_output=True, text=True, timeout=5)
    assert result.returncode == 1
    assert "unhealthy:" in result.stdout

    missing_env = dict(os.environ, V702_HEARTBEAT_FILE=str(tmp_path / "missing.json"))
    missing = subprocess.run([sys.executable, str(healthcheck)], env=missing_env, capture_output=True, text=True, timeout=5)
    assert missing.returncode == 1
    assert "unhealthy:" in missing.stdout


def test_a37_elite_score_floor_exception_fails_closed_at_highest_profile_floor():
    class BrokenProfile:
        def get(self, *args, **kwargs):
            raise ValueError("synthetic malformed candidate profile")

    expected = bot._v702_live_quality_score_floor_fail_closed()
    actual = bot._v702_live_quality_score_floor(BrokenProfile())
    assert expected >= 80.0
    assert actual == expected
    assert actual > float(bot.CONFIG.get("MIN_LIVE_SCORE", 70.0))
