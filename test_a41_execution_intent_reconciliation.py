from __future__ import annotations

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, patch

os.environ.setdefault("SCALPER_DB", os.path.join(tempfile.gettempdir(), f"v702-a41-tests-{os.getpid()}.db"))
import main as bot


def _save_state():
    return {
        "block": dict(bot.LIVE_ENTRIES_BLOCKED),
        "active_trades": dict(bot.ACTIVE_TRADES),
        "stats": {k: (k in bot.STATS, bot.STATS.get(k)) for k in (
            "v702_a41_intents_resolved_no_fill", "v702_a41_filled_intent_requires_protection",
            "v702_a41_last_intent_results", "v702_a41_last_unblock_proof",
            "v702_a41_verified_startup_intent_blocks_cleared",
        )},
    }


def _restore_state(saved):
    bot.LIVE_ENTRIES_BLOCKED.clear()
    bot.LIVE_ENTRIES_BLOCKED.update(saved["block"])
    bot.ACTIVE_TRADES.clear()
    bot.ACTIVE_TRADES.update(saved["active_trades"])
    for key, (present, value) in saved["stats"].items():
        if present:
            bot.STATS[key] = value
        else:
            bot.STATS.pop(key, None)


async def _safe_call_inline(_name, fn, **_kwargs):
    value = fn()
    if hasattr(value, "__await__"):
        value = await value
    return value


def test_a41_exact_cancelled_zero_fill_intent_is_durably_resolved():
    saved = _save_state()
    exchange = type("FakeExchange", (), {})()
    exchange.fetch_order = AsyncMock(return_value={
        "id": "ord-1", "symbol": "AAA/USDT", "side": "buy", "status": "canceled",
        "amount": 1.0, "filled": 0.0,
    })
    row = {"intent_id": "intent-1", "symbol": "AAA/USDT", "side": "BUY", "status": "SUBMISSION_UNKNOWN",
           "venue_order_id": "ord-1", "details": {}}
    try:
        with patch.object(bot, "safe_api_call", new=_safe_call_inline), \
             patch.object(bot.DBManager, "aupdate_execution_intent", new=AsyncMock()) as update:
            result = asyncio.run(bot._v702_a41_reconcile_one_intent_order(exchange, row, []))
        assert result["outcome"] == "RESOLVED_NO_FILL", result
        assert result["reason"] == "exact_order_confirmed_terminal_zero_fill"
        # Persist the exact order link before the terminal no-fill state so a
        # crash between writes remains recoverable and cannot trigger a duplicate buy.
        assert [call.args[1] for call in update.await_args_list] == ["ORDER_KNOWN", "NO_FILL_TERMINAL"]
        assert all(call.args[0] == "intent-1" for call in update.await_args_list)
        assert update.await_args_list[0].kwargs["venue_order_id"] == "ord-1"
        args, kwargs = update.await_args_list[-1]
        assert args[0] == "intent-1" and args[1] == "NO_FILL_TERMINAL"
        assert kwargs["venue_order_id"] == "ord-1"
        assert kwargs["details"]["a41_resolution_basis"] == "EXACT_ORDER_ID_TERMINAL_NO_FILL"
    finally:
        _restore_state(saved)


def test_a41_partial_fill_cancelled_order_is_not_marked_no_fill():
    saved = _save_state()
    exchange = type("FakeExchange", (), {})()
    exchange.fetch_order = AsyncMock(return_value={
        "id": "ord-2", "symbol": "AAA/USDT", "side": "buy", "status": "canceled",
        "amount": 1.0, "filled": 0.25,
    })
    row = {"intent_id": "intent-2", "symbol": "AAA/USDT", "side": "BUY", "status": "SUBMISSION_UNKNOWN",
           "venue_order_id": "ord-2", "details": {}}
    try:
        with patch.object(bot, "safe_api_call", new=_safe_call_inline), \
             patch.object(bot.DBManager, "aupdate_execution_intent", new=AsyncMock()) as update:
            result = asyncio.run(bot._v702_a41_reconcile_one_intent_order(exchange, row, []))
        assert result["outcome"] == "FILLED_REQUIRES_POSITION_PROTECTION", result
        assert result["reason"] == "partial_fill_without_matching_active_trade_manual_adoption_required"
        assert all(call.args[1] != "NO_FILL_TERMINAL" for call in update.await_args_list)
    finally:
        _restore_state(saved)


def test_a41_filled_order_requires_position_adoption_and_protection():
    saved = _save_state()
    exchange = type("FakeExchange", (), {})()
    exchange.fetch_order = AsyncMock(return_value={
        "id": "ord-3", "symbol": "AAA/USDT", "side": "buy", "status": "closed",
        "amount": 1.0, "filled": 1.0,
    })
    row = {"intent_id": "intent-3", "symbol": "AAA/USDT", "side": "BUY", "status": "SUBMISSION_UNKNOWN",
           "venue_order_id": "ord-3", "details": {}}
    try:
        with patch.object(bot, "safe_api_call", new=_safe_call_inline), \
             patch.object(bot.DBManager, "aupdate_execution_intent", new=AsyncMock()) as update:
            result = asyncio.run(bot._v702_a41_reconcile_one_intent_order(exchange, row, []))
        assert result["outcome"] == "FILLED_REQUIRES_POSITION_PROTECTION", result
        assert "manual_adoption_required" in result["reason"]
        # It may persist observation metadata, but must not promote the intent to a terminal state.
        assert all(call.args[1] != "NO_FILL_TERMINAL" for call in update.await_args_list)
    finally:
        _restore_state(saved)


def test_a41_missing_order_id_stays_unresolved_even_if_symbol_and_amount_match():
    saved = _save_state()
    exchange = type("FakeExchange", (), {})()
    exchange.fetch_order = AsyncMock()
    row = {"intent_id": "intent-4", "symbol": "AAA/USDT", "side": "BUY", "status": "SUBMISSION_UNKNOWN",
           "venue_order_id": None, "requested_qty": 1.0, "planned_price": 100.0, "details": {}}
    orders = [{"id": "ord-4", "symbol": "AAA/USDT", "side": "buy", "amount": 1.0, "price": 100.0}]
    try:
        with patch.object(bot.DBManager, "aupdate_execution_intent", new=AsyncMock()) as update:
            result = asyncio.run(bot._v702_a41_reconcile_one_intent_order(exchange, row, orders))
        assert result["outcome"] == "UNRESOLVED", result
        assert result["reason"] == "venue_order_id_missing_no_exact_client_id_match"
        exchange.fetch_order.assert_not_awaited()
        update.assert_not_awaited()
    finally:
        _restore_state(saved)


def test_a41_exact_client_id_link_is_allowed_but_approximate_match_is_not():
    saved = _save_state()
    exchange = type("FakeExchange", (), {})()
    exchange.fetch_order = AsyncMock(return_value={
        "id": "ord-5", "symbol": "AAA/USDT", "side": "buy", "status": "canceled", "amount": 1.0, "filled": 0.0,
    })
    row = {"intent_id": "intent-5", "symbol": "AAA/USDT", "side": "BUY", "status": "SUBMISSION_UNKNOWN",
           "venue_order_id": None, "details": {"clientOrderId": "my-exact-client-id"}}
    orders = [{"id": "ord-5", "symbol": "AAA/USDT", "side": "buy", "clientOrderId": "my-exact-client-id"}]
    try:
        with patch.object(bot, "safe_api_call", new=_safe_call_inline), \
             patch.object(bot.DBManager, "aupdate_execution_intent", new=AsyncMock()) as update:
            result = asyncio.run(bot._v702_a41_reconcile_one_intent_order(exchange, row, orders))
        assert result["outcome"] == "RESOLVED_NO_FILL", result
        assert any(call.args[1] == "ORDER_KNOWN" for call in update.await_args_list)
        assert any(call.args[1] == "NO_FILL_TERMINAL" for call in update.await_args_list)
    finally:
        _restore_state(saved)


def test_a41_verified_unblock_clears_only_exact_startup_intent_latch():
    saved = _save_state()
    try:
        bot.LIVE_ENTRIES_BLOCKED.clear()
        bot.LIVE_ENTRIES_BLOCKED.update({
            "active": True, "reason": "startup_unresolved_execution_intents:3",
            "where": "run_bot.execution_intent_recovery", "since": float(bot.WALL_NOW()) - 100,
        })
        proof = bot._v702_a41_verified_startup_intent_block_clear(
            original_reason="startup_unresolved_execution_intents:3",
            current_reason="startup_unresolved_execution_intents:3",
            current_where="run_bot.execution_intent_recovery",
            unresolved_state="REAL", unresolved_count=0, open_orders_state="REAL", open_orders=[],
            balance_state="REAL", balance_free_usdt=100.0, balance_age_sec=1.0,
        )
        assert proof["eligible"] is True, proof
        assert bot._v702_a41_apply_verified_startup_intent_clear(proof) is True
        assert bot.LIVE_ENTRIES_BLOCKED["active"] is False
    finally:
        _restore_state(saved)


def test_a41_unknown_open_buy_or_changed_block_root_prevents_unblock():
    saved = _save_state()
    try:
        bot.LIVE_ENTRIES_BLOCKED.clear()
        bot.LIVE_ENTRIES_BLOCKED.update({
            "active": True, "reason": "startup_unresolved_execution_intents:3",
            "where": "run_bot.execution_intent_recovery", "since": float(bot.WALL_NOW()) - 100,
        })
        proof = bot._v702_a41_verified_startup_intent_block_clear(
            original_reason="startup_unresolved_execution_intents:3",
            current_reason="startup_unresolved_execution_intents:3",
            current_where="run_bot.execution_intent_recovery",
            unresolved_state="REAL", unresolved_count=0, open_orders_state="REAL",
            open_orders=[{"id": "entry-unknown", "symbol": "AAA/USDT", "side": "buy"}],
            balance_state="REAL", balance_free_usdt=100.0, balance_age_sec=1.0,
        )
        assert proof["eligible"] is False, proof
        assert proof["checks"]["all_open_orders_are_tracked_protection_only"] is False
        changed = bot._v702_a41_verified_startup_intent_block_clear(
            original_reason="startup_unresolved_execution_intents:3", current_reason="stopless_exposure_BTC/USDT",
            current_where="run_bot.execution_intent_recovery", unresolved_state="REAL", unresolved_count=0,
            open_orders_state="REAL", open_orders=[], balance_state="REAL", balance_free_usdt=100.0, balance_age_sec=1.0)
        assert changed["eligible"] is False, changed
        assert bot.LIVE_ENTRIES_BLOCKED["active"] is True
    finally:
        _restore_state(saved)


def test_a41_terminal_contract_and_spot_long_only_are_preserved():
    report = bot.STATS["v702_a41_reconciliation_self_test"]
    assert report["pass"] is True, report
    assert report["hard_gate_bypass"] is False
    assert report["live_gates_relaxed"] is False
    assert bot.CONFIG["LONG_ONLY"] is True
    assert bot.CONFIG["MARKET_TYPE"] == "SPOT"
    assert bot.CONFIG["ENABLE_FUTURES"] is False


def test_a41_worker_resolves_terminal_zero_fill_then_clears_only_verified_startup_latch():
    saved = _save_state()
    extra_stats = ("v702_a41_unresolved_intents_latest", "v702_a41_open_orders_snapshot",
                   "v702_a41_last_reconcile", "v702_a41_last_intent_results",
                   "v702_a41_last_unblock_proof", "v702_a39_balance_snapshot")
    stats_saved = {k: (k in bot.STATS, bot.STATS.get(k)) for k in extra_stats}
    bot.LIVE_ENTRIES_BLOCKED.clear()
    bot.LIVE_ENTRIES_BLOCKED.update({
        "active": True, "reason": "startup_unresolved_execution_intents:1",
        "where": "run_bot.execution_intent_recovery", "since": float(bot.WALL_NOW()) - 120,
    })
    row = {"intent_id": "intent-worker", "symbol": "AAA/USDT", "side": "BUY", "order_type": "LIMIT",
           "requested_qty": 1.0, "planned_price": 100.0, "status": "SUBMISSION_UNKNOWN",
           "venue_order_id": "ord-worker", "details": {}, "created_at": "2026-10-17T18:00:00+00:00",
           "updated_at": "2026-10-17T18:00:00+00:00"}
    exchange = type("FakeExchange", (), {})()
    exchange.fetch_open_orders = AsyncMock(return_value=[])
    exchange.fetch_order = AsyncMock(return_value={
        "id": "ord-worker", "symbol": "AAA/USDT", "side": "buy", "status": "canceled",
        "amount": 1.0, "filled": 0.0,
    })

    async def sleep_cancel(_seconds):
        raise asyncio.CancelledError()

    async def runner():
        # Initial DB read has one ambiguous intent; second read confirms durable zero unresolved.
        with patch.object(bot.DBManager, "aunresolved_execution_intents", new=AsyncMock(side_effect=[ [row], [] ])), \
             patch.object(bot.DBManager, "aupdate_execution_intent", new=AsyncMock()), \
             patch.object(bot, "safe_api_call", new=_safe_call_inline), \
             patch.object(bot.BalanceReconciler, "fetch", new=AsyncMock(return_value=(100.0, "REAL"))), \
             patch.object(bot.asyncio, "sleep", new=sleep_cancel):
            bot.STATS["v702_a39_balance_snapshot"] = {
                "free_usdt": 100.0, "used_usdt": 0.0, "total_usdt": 100.0,
                "state": "REAL", "source": "fetch_balance", "ts": float(bot.WALL_NOW()),
            }
            try:
                await bot._v702_a41_execution_intent_reconciliation_task(exchange)
            except asyncio.CancelledError:
                pass

    try:
        asyncio.run(runner())
        assert exchange.fetch_order.await_count == 1
        assert bot.STATS["v702_a41_last_intent_results"][0]["outcome"] == "RESOLVED_NO_FILL"
        assert bot.LIVE_ENTRIES_BLOCKED["active"] is False
        assert bot.STATS["v702_a41_verified_startup_intent_blocks_cleared"] >= 1
        proof = bot.STATS["v702_a41_last_unblock_proof"]
        assert proof["eligible"] is True and all(proof["checks"].values()), proof
    finally:
        _restore_state(saved)
        for key, (present, value) in stats_saved.items():
            if present:
                bot.STATS[key] = value
            else:
                bot.STATS.pop(key, None)


def test_a41_protection_order_must_match_exact_id_side_and_symbol():
    saved = _save_state()
    try:
        class Trade:
            entry_reconcile_required = False
            sl_order_id = "sl-1"
            tp1_order_id = "tp-1"
            tp2_order_id = None
            tp3_order_id = None
            software_sl_active = False
            sl_health_state = "NATIVE_SL_VERIFIED"
        bot.ACTIVE_TRADES.clear()
        bot.ACTIVE_TRADES["AAA/USDT"] = Trade()
        assert bot._v702_a41_untracked_open_order_ids([
            {"id":"sl-1", "symbol":"AAA/USDT", "side":"sell"}
        ]) == []
        assert bot._v702_a41_untracked_open_order_ids([
            {"id":"sl-1", "symbol":"BBB/USDT", "side":"sell"}
        ]) == ["sl-1"]
        assert bot._v702_a41_untracked_open_order_ids([
            {"id":"sl-1", "symbol":"AAA/USDT", "side":"buy"}
        ]) == ["sl-1"]
    finally:
        _restore_state(saved)


def test_a41_historical_positive_fill_evidence_prevents_false_zero_fill_resolution():
    saved = _save_state()
    exchange = type("FakeExchange", (), {})()
    exchange.fetch_order = AsyncMock(return_value={
        "id": "ord-conflict", "symbol": "AAA/USDT", "side": "buy", "status": "canceled",
        "amount": 1.0, "filled": 0.0,
    })
    row = {"intent_id": "intent-conflict", "symbol": "AAA/USDT", "side": "BUY", "status": "SUBMISSION_UNKNOWN",
           "venue_order_id": "ord-conflict", "details": {"fill_qty": 0.25}}
    try:
        with patch.object(bot, "safe_api_call", new=_safe_call_inline), \
             patch.object(bot.DBManager, "aupdate_execution_intent", new=AsyncMock()) as update:
            result = asyncio.run(bot._v702_a41_reconcile_one_intent_order(exchange, row, []))
        assert result["outcome"] == "CONFLICT", result
        assert result["reason"] == "database_or_details_fill_evidence_conflicts_with_exchange_zero_fill"
        assert all(call.args[1] != "NO_FILL_TERMINAL" for call in update.await_args_list)
    finally:
        _restore_state(saved)


def test_a41_exchange_order_identity_or_side_mismatch_stays_blocked():
    saved = _save_state()
    try:
        for payload, reason in [
            ({"id":"some-other-order", "symbol":"AAA/USDT", "side":"buy", "status":"canceled", "filled":0}, "fetched_order_id_mismatch"),
            ({"id":"ord-identity", "symbol":"BBB/USDT", "side":"buy", "status":"canceled", "filled":0}, "fetched_order_symbol_mismatch"),
            ({"id":"ord-identity", "symbol":"AAA/USDT", "side":"sell", "status":"canceled", "filled":0}, "fetched_order_side_mismatch"),
        ]:
            exchange = type("FakeExchange", (), {})()
            exchange.fetch_order = AsyncMock(return_value=payload)
            row = {"intent_id":"intent-identity", "symbol":"AAA/USDT", "side":"BUY", "status":"SUBMISSION_UNKNOWN",
                   "venue_order_id":"ord-identity", "details":{}}
            with patch.object(bot, "safe_api_call", new=_safe_call_inline):
                result = asyncio.run(bot._v702_a41_reconcile_one_intent_order(exchange, row, []))
            assert result["outcome"] == "UNRESOLVED", result
            assert result["reason"] == reason
    finally:
        _restore_state(saved)
