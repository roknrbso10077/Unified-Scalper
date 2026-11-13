from __future__ import annotations

import asyncio
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

os.environ.setdefault("SCALPER_DB", os.path.join(tempfile.gettempdir(), f"v702-a42-tests-{os.getpid()}.db"))
import main as bot


def _fresh_db(prefix="v702-a42-fixture-"):
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=".db")
    os.close(fd)
    return path


def _remove_db(path):
    for suffix in ("", "-wal", "-shm"):
        try:
            Path(path + suffix).unlink(missing_ok=True)
        except Exception:
            pass


def test_a42_explicit_v517_mock_rows_quarantined_from_live_read_but_not_deleted():
    old_db = bot.CONFIG.get("DB_PATH")
    old_flag = bool(globals().get("V644_SELFTEST_ACTIVE", False))
    stats_key = "v702_a42_synthetic_intent_quarantine"
    prior_stats = (stats_key in bot.STATS, bot.STATS.get(stats_key))
    path = _fresh_db()
    try:
        bot.CONFIG["DB_PATH"] = path
        bot.DBManager.init_schema()
        real_id = bot.DBManager.begin_execution_intent("AAA/USDT", "live-trace-1", "BUY", "LIMIT", 1, 1, {})
        mock_fill_id = bot.DBManager.begin_execution_intent("TEST/USDT", "V517-UE", "BUY", "MARKET", 0.1, 100, {})
        bot.DBManager.update_execution_intent(mock_fill_id, "FILL_CONFIRMED", venue_order_id="MOCK-UE-1")
        mock_unknown_id = bot.DBManager.begin_execution_intent("TEST/USDT", "V517-UE2", "BUY", "MARKET", 0.1, 100, {})

        bot.V644_SELFTEST_ACTIVE = False
        live = bot.DBManager.unresolved_execution_intents()
        assert [x["intent_id"] for x in live] == [real_id], live
        evidence = bot.STATS[stats_key]
        assert evidence["count"] == 2, evidence
        assert evidence["live_unresolved_count"] == 1, evidence
        assert evidence["rows_deleted"] == 0, evidence

        conn = sqlite3.connect(path)
        try:
            rows = conn.execute("SELECT intent_id,venue_order_id FROM execution_intents ORDER BY created_at").fetchall()
        finally:
            conn.close()
        assert len(rows) == 3, rows
        assert {row[0] for row in rows} == {real_id, mock_fill_id, mock_unknown_id}
    finally:
        bot.CONFIG["DB_PATH"] = old_db
        bot.V644_SELFTEST_ACTIVE = old_flag
        if prior_stats[0]:
            bot.STATS[stats_key] = prior_stats[1]
        else:
            bot.STATS.pop(stats_key, None)
        _remove_db(path)


def test_a42_test_symbol_alone_is_not_enough_to_quarantine_real_intent():
    row = {"intent_id": "live-test-symbol", "symbol": "TEST/USDT", "trace_id": "real-live-uuid",
           "side": "BUY", "status": "SUBMISSION_UNKNOWN", "venue_order_id": "123456789", "details": {}}
    assert bot._v702_a42_is_synthetic_execution_intent(row) is False


def test_a42_direct_mock_reconcile_never_calls_exchange():
    exchange = type("FakeExchange", (), {})()
    exchange.fetch_order = AsyncMock()
    row = {"intent_id": "old-mock", "symbol": "TEST/USDT", "trace_id": "V517-UE",
           "side": "BUY", "status": "FILL_CONFIRMED", "venue_order_id": "MOCK-UE-1", "details": {}}
    was_active = bool(getattr(bot, "V644_SELFTEST_ACTIVE", False))
    bot.V644_SELFTEST_ACTIVE = False
    try:
        result = asyncio.run(bot._v702_a41_reconcile_one_intent_order(exchange, row, []))
        assert result["outcome"] == "QUARANTINED_SYNTHETIC_TEST", result
        assert result["reason"] == "known_selftest_fixture_not_sent_to_exchange"
        exchange.fetch_order.assert_not_awaited()
    finally:
        bot.V644_SELFTEST_ACTIVE = was_active


def test_a42_selftest_writer_cannot_touch_configured_database():
    old_db = bot.CONFIG.get("DB_PATH")
    old_flag = bool(getattr(bot, "V644_SELFTEST_ACTIVE", False))
    old_state = getattr(bot.LIVE_STATE, "current", None)
    old_stat = bot.STATS.get("v702_a42_selftest_db_isolation")
    had_stat = "v702_a42_selftest_db_isolation" in bot.STATS
    prod_path = _fresh_db("v702-a42-prod-db-")
    try:
        bot.CONFIG["DB_PATH"] = prod_path
        bot.DBManager.init_schema()
        bot.LIVE_STATE.current = "STOPPED"
        bot.V644_SELFTEST_ACTIVE = True

        async def fake_test():
            assert bot.CONFIG["DB_PATH"] != prod_path
            iid = await bot.DBManager.abegin_execution_intent("TEST/USDT", "V517-UE", "BUY", "MARKET", 0.1, 100, {})
            return {"pass": bool(iid), "fixture_intent_id": iid}

        outcome = asyncio.run(bot._v702_a42_run_selftest_in_isolated_db(fake_test))
        assert outcome["pass"] is True, outcome
        assert outcome["production_db_path_restored"] is True, outcome
        assert outcome["disposable_db_removed"] is True, outcome
        assert outcome["temp_db_distinct_from_configured_db"] is True, outcome
        assert outcome["production_db_write_possible"] is False, outcome

        conn = sqlite3.connect(prod_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM execution_intents").fetchone()[0]
        finally:
            conn.close()
        assert count == 0, count
    finally:
        bot.CONFIG["DB_PATH"] = old_db
        bot.V644_SELFTEST_ACTIVE = old_flag
        bot.LIVE_STATE.current = old_state
        if had_stat:
            bot.STATS["v702_a42_selftest_db_isolation"] = old_stat
        else:
            bot.STATS.pop("v702_a42_selftest_db_isolation", None)
        _remove_db(prod_path)


def test_a42_isolation_helper_refuses_unmarked_call_without_swapping_database():
    old_db = bot.CONFIG.get("DB_PATH")
    old_flag = bool(getattr(bot, "V644_SELFTEST_ACTIVE", False))
    bot.V644_SELFTEST_ACTIVE = False
    ran = {"value": False}

    async def fake_test():
        ran["value"] = True
        return {"pass": True}

    try:
        result = asyncio.run(bot._v702_a42_run_selftest_in_isolated_db(fake_test))
        assert result["pass"] is False, result
        assert ran["value"] is False
        assert bot.CONFIG.get("DB_PATH") == old_db
        assert result.get("production_db_write_possible") is False
    finally:
        bot.V644_SELFTEST_ACTIVE = old_flag


def test_a42_release_metadata_keeps_trade_safety_contracts():
    report = bot.STATS["v702_a42_mock_intent_isolation_self_test"]
    assert report["pass"] is True, report
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False
    assert bot.CONFIG["LONG_ONLY"] is True
    assert str(bot.CONFIG["MARKET_TYPE"]).upper() == "SPOT"
    assert bot.CONFIG["ENABLE_FUTURES"] is False
