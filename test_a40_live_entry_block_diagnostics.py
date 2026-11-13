from __future__ import annotations

import os
import tempfile

os.environ.setdefault(
    "SCALPER_DB",
    os.path.join(tempfile.gettempdir(), f"v702-a40-tests-{os.getpid()}.db"),
)
import main as bot


def _save_state():
    block = dict(bot.LIVE_ENTRIES_BLOCKED)
    keys = (
        "v702_a39_balance_snapshot",
        "v702_a39_balance_recovery_successes",
        "v702_a39_balance_recovery_blocks",
        "v702_a39_balance_recovery_errors",
        "v702_a39_balance_recovery_skipped_nonbalance",
        "v702_a39_balance_recovery_task_errors",
        "v702_a39_balance_recovery_last",
        "v702_a39_balance_recovery_last_skip",
        "v702_a39_balance_recovery_last_error",
        "v702_a40_unresolved_intents_latest",
        "v702_a40_open_orders_last",
    )
    stats = {key: (key in bot.STATS, bot.STATS.get(key)) for key in keys}
    return block, stats


def _restore_state(saved):
    block, stats = saved
    bot.LIVE_ENTRIES_BLOCKED.clear()
    bot.LIVE_ENTRIES_BLOCKED.update(block)
    for key, (present, value) in stats.items():
        if present:
            bot.STATS[key] = value
        else:
            bot.STATS.pop(key, None)


def test_a40_root_reason_balance_age_recovery_counters_and_order_reconciliation_are_visible():
    saved = _save_state()
    try:
        now = float(bot.WALL_NOW())
        bot.LIVE_ENTRIES_BLOCKED.update({
            "active": True,
            "reason": "startup_unresolved_execution_intents:2",
            "where": "run_bot.execution_intent_recovery",
            "since": now - 17.0,
        })
        bot.STATS["v702_a39_balance_snapshot"] = {
            "free_usdt": 75.0, "used_usdt": 75.0, "total_usdt": 150.0,
            "source": "fetch_balance", "ts": now - 5.0,
        }
        bot.STATS["v702_a39_balance_recovery_successes"] = 2
        bot.STATS["v702_a39_balance_recovery_blocks"] = 3
        bot.STATS["v702_a39_balance_recovery_errors"] = 4
        bot.STATS["v702_a39_balance_recovery_skipped_nonbalance"] = 5
        bot.STATS["v702_a39_balance_recovery_task_errors"] = 6
        bot.STATS["v702_a39_balance_recovery_last"] = {
            "ts": now, "block_before": "balance_cache_untrusted", "state": "REAL",
        }
        bot.STATS["v702_a40_unresolved_intents_latest"] = {
            "state": "REAL", "count": 2, "symbols": ["AAA/USDT"], "ts": now,
        }
        bot.STATS["v702_a40_open_orders_last"] = {
            "state": "REAL", "count": 1, "symbols": ["BBB/USDT"], "ts": now,
        }

        diag = bot._v702_a40_entry_block_telemetry()
        assert diag["block_active"] is True
        assert diag["block_reason"] == "startup_unresolved_execution_intents:2"
        assert diag["block_where"] == "run_bot.execution_intent_recovery"
        assert diag["block_age_sec"] >= 16.0
        assert (diag["balance_free_usdt"], diag["balance_used_usdt"], diag["balance_total_usdt"]) == (75.0, 75.0, 150.0)
        assert diag["balance_age_sec"] is not None
        assert (diag["recovery_successes"], diag["recovery_blocks"], diag["recovery_errors"],
                diag["recovery_skipped_nonbalance"], diag["recovery_task_errors"]) == (2, 3, 4, 5, 6)
        assert diag["unresolved_intents_count"] == 2
        assert diag["open_orders_count"] == 1
        assert diag["diagnostic_is_read_only"] is True
        assert diag["hard_gate_bypass"] is False
        assert bot.LIVE_ENTRIES_BLOCKED["active"] is True
    finally:
        _restore_state(saved)


def test_a40_heartbeat_exposes_block_root_and_live_diagnostic_fields():
    saved = _save_state()
    try:
        bot.LIVE_ENTRIES_BLOCKED.update({
            "active": True, "reason": "balance_cache_untrusted", "where": "test.balance", "since": float(bot.WALL_NOW()) - 3,
        })
        line = bot._V702R28TelegramDigest._heartbeat_line("ENTRY_STATUS=BLOCKED:SYSTEM")
        assert "A40_LIVE_BLOCK=active:1" in line
        assert "reason:balance_cache_untrusted" in line
        assert "A40_BALANCE=free:" in line
        assert "A40_RECOVERY=success/block/error/skip_nonbalance/taskerr:" in line
        assert "A40_RECON=intents:" in line
        assert "hard_gate_bypass:false" in line
        assert bot.LIVE_ENTRIES_BLOCKED["active"] is True
    finally:
        _restore_state(saved)


def test_a40_terminal_self_test_passes_without_relaxing_live_gates():
    report = bot.STATS["v702_a40_diagnostics_self_test"]
    assert report["pass"] is True, report
    assert report["diagnostic_is_read_only"] is True
    assert report["hard_gate_bypass"] is False
    assert bot.FINAL_CANONICAL_RUNTIME["a40_live_entry_block_diagnostics_self_test"]["pass"] is True
    assert bot.CONFIG["LONG_ONLY"] is True
    assert bot.CONFIG["MARKET_TYPE"] == "SPOT"
    assert bot.CONFIG["ENABLE_FUTURES"] is False


def test_a40_active_block_task_reads_database_and_open_orders_without_clearing_block():
    import asyncio
    from unittest.mock import AsyncMock, patch

    saved = _save_state()
    extra_keys = ("v702_a40_unresolved_intents_latest", "v702_a40_open_orders_last")
    now = float(bot.WALL_NOW())
    bot.LIVE_ENTRIES_BLOCKED.update({
        "active": True,
        "reason": "startup_unresolved_execution_intents:1",
        "where": "test.active_block",
        "since": now - 4.0,
    })
    fake_exchange = type("FakeExchange", (), {
        "has": {"fetchOpenOrders": True},
        "fetch_open_orders": AsyncMock(return_value=[
            {"symbol": "AAA/USDT", "status": "open", "id": "test-1"},
            {"symbol": "BBB/USDT", "status": "open", "id": "test-2"},
        ]),
    })()

    async def fake_safe_api_call(name, fn, **kwargs):
        assert name == "v702_a44_blockdiag_open_orders"
        value = fn()
        if hasattr(value, "__await__"):
            value = await value
        return value

    async def stop_after_one_cycle(_seconds):
        raise asyncio.CancelledError()

    async def runner():
        with patch.object(bot.DBManager, "aunresolved_execution_intents", new=AsyncMock(return_value=[
            {"symbol": "AAA/USDT", "intent_id": "pending-1"},
        ])), patch.object(bot, "safe_api_call", new=AsyncMock(side_effect=fake_safe_api_call)), \
             patch.object(bot.asyncio, "sleep", new=stop_after_one_cycle):
            try:
                await bot._v702_a40_entry_block_diagnostic_task(fake_exchange)
            except asyncio.CancelledError:
                return
        raise AssertionError("diagnostic task should run one active-block sample before cancellation")

    try:
        asyncio.run(runner())
        intents = bot.STATS["v702_a40_unresolved_intents_latest"]
        orders = bot.STATS["v702_a40_open_orders_last"]
        assert intents["state"] == "REAL" and intents["count"] == 1
        assert orders["state"] == "REAL" and orders["count"] == 2
        assert set(orders["symbols"]) == {"AAA/USDT", "BBB/USDT"}
        assert bot.LIVE_ENTRIES_BLOCKED["active"] is True
        assert bot.LIVE_ENTRIES_BLOCKED["reason"] == "startup_unresolved_execution_intents:1"
        assert fake_exchange.fetch_open_orders.await_count == 1
    finally:
        _restore_state(saved)
