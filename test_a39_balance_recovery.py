from __future__ import annotations

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, patch

os.environ.setdefault("SCALPER_DB", os.path.join(tempfile.gettempdir(), f"v702-a39-tests-{os.getpid()}.db"))
import main as bot


def _snapshot_state():
    cls = bot.BalanceReconciler
    attrs = ("_last_real_value", "_last_real_ts", "_last_real_wall_ts", "_last_state", "_last_source", "_sealed")
    class_state = {k: getattr(cls, k) for k in attrs}
    entries = dict(bot.LIVE_ENTRIES_BLOCKED)
    # Keep this module independent from deliberate sticky-block scenarios in
    # other modules. Each test below constructs the exact block state it needs.
    bot.LIVE_ENTRIES_BLOCKED.clear()
    bot.LIVE_ENTRIES_BLOCKED.update({"active": False, "reason": None, "where": None, "since": None})
    keys = ("v702_a39_balance_snapshot", "v702_a39_balance_recovery_last", "v702_a39_block_reason_overwrite_prevented")
    stats = {k: (k in bot.STATS, bot.STATS.get(k)) for k in keys}
    return attrs, class_state, entries, stats


def _restore_state(saved):
    attrs, class_state, entries, stats = saved
    for k in attrs:
        setattr(bot.BalanceReconciler, k, class_state[k])
    bot.LIVE_ENTRIES_BLOCKED.clear()
    bot.LIVE_ENTRIES_BLOCKED.update(entries)
    for k, (present, value) in stats.items():
        if present:
            bot.STATS[k] = value
        else:
            bot.STATS.pop(k, None)


def test_a39_parser_uses_exchange_free_and_never_total_as_fallback():
    free, used, total = bot._v702_a39_extract_usdt_balance({
        "free": {"USDT": 75.0}, "used": {"USDT": 75.0}, "total": {"USDT": 150.0},
        "USDT": {"free": 75.0, "used": 75.0, "total": 150.0},
    })
    assert (free, used, total) == (75.0, 75.0, 150.0)
    # Alternate CCXT-adapter per-currency structure is also supported.
    assert bot._v702_a39_extract_usdt_balance({"USDT": {"free": 75, "used": 75, "total": 150}}) == (75.0, 75.0, 150.0)
    try:
        bot._v702_a39_extract_usdt_balance({"used": {"USDT": 75}, "total": {"USDT": 150}})
    except ValueError as exc:
        assert "free_usdt_field_missing" in str(exc)
    else:
        raise AssertionError("must never spend total/locked USDT when free is missing")


def test_a39_real_balance_recovers_soft_balance_latch_with_pending_order_lock_untouched():
    saved = _snapshot_state()
    balance = {"free": {"USDT": 75.0}, "used": {"USDT": 75.0}, "total": {"USDT": 150.0}}

    async def run():
        bot.live_entries_block("balance_below_minimum", where="test.before")
        with patch.object(bot, "safe_api_call", new=AsyncMock(return_value=balance)):
            recovered = await bot._v702_a39_attempt_balance_entry_recovery(object())
        assert recovered is True
        assert bot.LIVE_ENTRIES_BLOCKED["active"] is False
        snapshot = bot.STATS["v702_a39_balance_snapshot"]
        assert snapshot["free_usdt"] == 75.0
        assert snapshot["used_usdt"] == 75.0
        assert snapshot["total_usdt"] == 150.0
        assert snapshot["spendable_basis"] == "FREE_ONLY_NO_DOUBLE_DEDUCT"

    try:
        with patch.dict(bot.CONFIG, {"BALANCE_MIN_ACCEPT_USDT": 5.0, "ENABLE_LIVE_TRADING": True, "PAPER_TRADING_MODE": False}):
            asyncio.run(run())
    finally:
        _restore_state(saved)


def test_a39_balance_fetch_cannot_clear_unresolved_execution_intent_block():
    saved = _snapshot_state()
    balance = {"free": {"USDT": 75.0}, "used": {"USDT": 75.0}, "total": {"USDT": 150.0}}

    async def run():
        bot.live_entries_block("startup_unresolved_execution_intents:1", where="test.unresolved")
        with patch.object(bot, "safe_api_call", new=AsyncMock(return_value=balance)):
            free, state = await bot.BalanceReconciler.fetch(object())
        assert free == 75.0 and state == "REAL"
        assert bot.LIVE_ENTRIES_BLOCKED["active"] is True
        assert bot.LIVE_ENTRIES_BLOCKED["reason"] == "startup_unresolved_execution_intents:1"

    try:
        with patch.dict(bot.CONFIG, {"BALANCE_MIN_ACCEPT_USDT": 5.0, "ENABLE_LIVE_TRADING": True, "PAPER_TRADING_MODE": False}):
            asyncio.run(run())
    finally:
        _restore_state(saved)


def test_a39_preflight_accepts_sized_buy_from_75_free_with_75_locked_elsewhere():
    saved = _snapshot_state()
    balance = {"free": {"USDT": 75.0}, "used": {"USDT": 75.0}, "total": {"USDT": 150.0}}

    async def run():
        with patch.object(bot, "safe_api_call", new=AsyncMock(return_value=balance)):
            ok, reason = await bot._v626_execution_balance_preflight(
                object(), "TEST/USDT", qty=0.9, price=78.0, stage="test_pending_order_balance"
            )
        assert ok is True, reason
        assert reason.startswith("real_balance_ok:75.000000")

    try:
        with patch.dict(bot.CONFIG, {
            "ENABLE_LIVE_TRADING": True, "PAPER_TRADING_MODE": False,
            "V626_BALANCE_PREFLIGHT_TIMEOUT_SEC": 3.0,
            "V626_BALANCE_PREFLIGHT_BUFFER_PCT": 0.20,
            "TRADING_BALANCE_RESERVE_USDT": 3.0, "TAKER_FEE_PCT": 0.10,
            "BALANCE_MIN_ACCEPT_USDT": 5.0,
        }):
            asyncio.run(run())
    finally:
        _restore_state(saved)



def test_a39_balance_latch_cannot_overwrite_sticky_execution_intent_block():
    saved = _snapshot_state()
    try:
        bot.LIVE_ENTRIES_BLOCKED.clear()
        bot.LIVE_ENTRIES_BLOCKED.update({"active": False, "reason": None, "where": None, "since": None})
        bot.live_entries_block("startup_unresolved_execution_intents:1", where="startup_reconcile")
        bot.live_entries_block("balance_reconciler_block", where="BalanceReconciler.fetch")
        assert bot.LIVE_ENTRIES_BLOCKED["active"] is True
        assert bot.LIVE_ENTRIES_BLOCKED["reason"] == "startup_unresolved_execution_intents:1"
    finally:
        _restore_state(saved)

def test_a39_release_self_test_passes_and_hard_gates_remain():
    report = bot.STATS["v702_a39_balance_closure_self_test"]
    assert report["pass"] is True, report
    assert report["hard_gate_bypass"] is False
    assert bot.FINAL_CANONICAL_RUNTIME["a39_locked_open_orders_subtracted_twice"] is False
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70.0
    assert bot.CONFIG["LONG_ONLY"] is True
    assert bot.CONFIG["MARKET_TYPE"] == "SPOT"
    assert bot.CONFIG["ENABLE_FUTURES"] is False
