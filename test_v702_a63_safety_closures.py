from __future__ import annotations

import asyncio
import copy
import math
import time
from collections import defaultdict, deque
from types import SimpleNamespace

import pytest
import main as bot


def _valid_edge_context():
    return {
        "family": "PULLBACK", "strategy_mode": "PULLBACK",
        "strategy_style": "SCALP", "timeframe_profile": "15M_5M",
        "htf_strength": 90.0,
    }


def _valid_edge_report():
    ctx = _valid_edge_context()
    key = bot.EdgeGate.recipe_key(ctx)
    return {
        "version": bot.V702_KNOWLEDGE_EDGE_VERSION,
        "generated_at": bot.WALL_NOW(),
        "learned_recipes": {
            key: {
                "entries": 100, "status": "VALIDATED_POSITIVE",
                "expectancy_r": 0.20, "lower_bound_90_r": 0.03,
                "first_half_expectancy_r": 0.12, "second_half_expectancy_r": 0.18,
            }
        },
    }


def test_a63_order_match_requires_exact_client_identity_timestamp_and_venue_id():
    started = bot.WALL_NOW()
    exact = {
        "id": "venue-order-1", "symbol": "ABC/USDT", "side": "buy",
        "status": "open", "amount": 1.0, "filled": 0.0,
        "timestamp": int(started * 1000), "clientOrderId": "bot-intent-1",
    }
    manual_without_id = {**exact, "id": "manual-1", "clientOrderId": ""}
    manual_other_id = {**exact, "id": "manual-2", "clientOrderId": "other-client"}
    no_timestamp = {**exact, "id": "old-order", "timestamp": None}
    assert bot._v517_match_order(
        [manual_without_id, manual_other_id, no_timestamp], symbol="ABC/USDT", side="buy",
        qty=1.0, started_wall=started, client_order_id="bot-intent-1", require_identity=True,
    ) is None
    recovered = bot._v517_match_order(
        [manual_without_id, manual_other_id, exact], symbol="ABC/USDT", side="buy",
        qty=1.0, started_wall=started, client_order_id="bot-intent-1", require_identity=True,
    )
    assert recovered is not None and recovered["id"] == "venue-order-1"
    recovered_by_venue_id = bot._v517_match_order(
        [exact], symbol="ABC/USDT", side="buy", qty=1.0,
        started_wall=started, expected_order_id="venue-order-1", require_identity=True,
    )
    assert recovered_by_venue_id is not None and recovered_by_venue_id["id"] == "venue-order-1"
    wrong_venue_id = bot._v517_match_order(
        [exact], symbol="ABC/USDT", side="buy", qty=1.0,
        started_wall=started, expected_order_id="manual-unknown", require_identity=True,
    )
    assert wrong_venue_id is None
    missing_symbol = {**exact, "symbol": None}
    assert bot._v517_match_order(
        [missing_symbol], symbol="ABC/USDT", side="buy", qty=1.0,
        started_wall=started, client_order_id="bot-intent-1", require_identity=True,
    ) is None
    assert bot._v517_order_fill_qty(exact) == 0.0


def test_a63_market_proxy_forwards_client_id_and_recovers_timeout_by_same_id(monkeypatch):
    class FakeMexc:
        id = "mexc"

        def __init__(self):
            self.orders = []
            self.submitted_params = []

        async def create_market_buy_order(self, symbol, qty, params=None):
            params = dict(params or {})
            self.submitted_params.append(params)
            self.orders.append({
                "id": "mexc-accepted-1", "symbol": symbol, "side": "buy",
                "status": "open", "amount": float(qty), "filled": 0.0,
                "timestamp": int(bot.WALL_NOW() * 1000),
                "clientOrderId": params.get("clientOrderId"),
            })
            raise TimeoutError("request timed out after venue acceptance")

    async def fetch_recent(exchange, symbol):
        return [row for row in exchange.orders if row.get("symbol") == symbol]

    monkeypatch.setattr(bot, "_v517_fetch_recent_orders", fetch_recent)
    venue = FakeMexc()
    proxy = bot._V517ExchangeProxy(venue)
    result = asyncio.run(proxy.create_market_buy_order(
        "ABC/USDT", 1.0, {"clientOrderId": "bot-intent-1"}
    ))
    assert venue.submitted_params == [{"clientOrderId": "bot-intent-1"}]
    assert result["id"] == "mexc-accepted-1"
    assert result["clientOrderId"] == "bot-intent-1"
    assert proxy.unknown_entry is False


def test_a63_market_proxy_keeps_unknown_when_venue_has_no_matching_identity(monkeypatch):
    class FakeMexc:
        id = "mexc"

        async def create_market_buy_order(self, symbol, qty, params=None):
            raise TimeoutError("request timeout")

    async def no_rows(_exchange, _symbol):
        return [{
            "id": "manual-order", "symbol": "ABC/USDT", "side": "buy",
            "status": "open", "amount": 1.0, "filled": 0.0,
            "timestamp": int(bot.WALL_NOW() * 1000), "clientOrderId": "manual-client",
        }]

    monkeypatch.setattr(bot, "_v517_fetch_recent_orders", no_rows)
    proxy = bot._V517ExchangeProxy(FakeMexc())
    with pytest.raises(bot._V517UnknownExecution):
        asyncio.run(proxy.create_market_buy_order("ABC/USDT", 1.0, {"clientOrderId": "bot-intent-1"}))
    assert proxy.unknown_entry is True


def test_a63_precision_preflight_rejects_unknown_metadata_missing_price_precision_and_nan(monkeypatch):
    class GoodExchange:
        def market(self, symbol):
            return {"symbol": symbol, "limits": {"amount": {"min": 0.001, "max": 10.0},
                                                   "cost": {"min": 5.0, "max": 10000.0}}}

        def amount_to_precision(self, _symbol, qty):
            return f"{qty:.4f}"

        def price_to_precision(self, _symbol, price):
            return f"{price:.4f}"

    class MissingPrecision:
        def market(self, symbol):
            return {"symbol": symbol, "limits": {"amount": {}, "cost": {}}}

        def amount_to_precision(self, _symbol, qty):
            return str(qty)

    good = GoodExchange()
    qty, price, error = bot.OrderExecutor._normalize_qty_price(good, "ABC/USDT", 1.0, 10.0)
    assert (qty, price, error) == (1.0, 10.0, None)
    assert bot.OrderExecutor._normalize_qty_price(good, "ABC/USDT", math.nan, 10.0)[2]
    assert bot.OrderExecutor._normalize_qty_price(good, "ABC/USDT", 1.0, math.nan)[2]
    assert bot.OrderExecutor._normalize_qty_price(MissingPrecision(), "ABC/USDT", 1.0, 10.0)[2]


def test_a63_edge_gate_fails_closed_for_nan_inf_bool_future_and_stale(monkeypatch):
    monkeypatch.setitem(bot.CONFIG, "V702_KNOWLEDGE_RECIPE_MIN_OBS", 100)
    context = _valid_edge_context()
    valid = _valid_edge_report()
    monkeypatch.setitem(bot.STATS, "v702_knowledge_edge_report", valid)
    assert bot.EdgeGate.live_permitted(context) == (True, "validated_positive_edge")

    for metric in ("expectancy_r", "lower_bound_90_r", "first_half_expectancy_r", "second_half_expectancy_r"):
        for bad in (math.nan, math.inf, -math.inf, True):
            report = copy.deepcopy(valid)
            key = bot.EdgeGate.recipe_key(context)
            report["learned_recipes"][key][metric] = bad
            monkeypatch.setitem(bot.STATS, "v702_knowledge_edge_report", report)
            permitted, _ = bot.EdgeGate.live_permitted(context)
            assert permitted is False, (metric, bad)

    future = copy.deepcopy(valid)
    future["generated_at"] = bot.WALL_NOW() + 3600.0
    monkeypatch.setitem(bot.STATS, "v702_knowledge_edge_report", future)
    assert bot.EdgeGate.live_permitted(context)[0] is False

    stale = copy.deepcopy(valid)
    stale["generated_at"] = bot.WALL_NOW() - 86400.0
    monkeypatch.setitem(bot.STATS, "v702_knowledge_edge_report", stale)
    assert bot.EdgeGate.live_permitted(context)[0] is False

    for bad_stamp in (math.nan, math.inf, -math.inf, True, "not-a-timestamp"):
        malformed = copy.deepcopy(valid)
        malformed["generated_at"] = bad_stamp
        monkeypatch.setitem(bot.STATS, "v702_knowledge_edge_report", malformed)
        assert bot.EdgeGate.live_permitted(context)[0] is False


def test_a63_rate_limiter_rejects_non_progressing_burst_and_allows_minimum_progress(monkeypatch):
    limiter = bot.V702PlatformRateLimiter()
    monkeypatch.setitem(bot.CONFIG, "V702_PLATFORM_RATE_LIMIT_ENABLE", True)
    monkeypatch.setitem(bot.CONFIG, "V702_PLATFORM_RATE_LIMIT_RPS", 12.0)
    monkeypatch.setitem(bot.CONFIG, "V702_PLATFORM_RATE_LIMIT_BURST", 2.0)
    with pytest.raises(ValueError, match="progress_floor"):
        asyncio.run(limiter.acquire("research_knowledge"))

    monkeypatch.setitem(bot.CONFIG, "V702_PLATFORM_RATE_LIMIT_BURST", 8.0)
    asyncio.run(asyncio.wait_for(limiter.acquire("research_knowledge"), timeout=1.0))


def _seed_digest(monkeypatch, structured):
    digest = bot._V702R28TelegramDigest
    monkeypatch.setattr(bot, "_V702_A37_STRUCTURED_BLOCKS", structured)
    monkeypatch.setattr(digest, "_events", 3)
    monkeypatch.setattr(digest, "_category_counts", defaultdict(int, {"scorer_block": 1}))
    monkeypatch.setattr(digest, "_heartbeat", "heartbeat=old")
    monkeypatch.setattr(digest, "_starvation", "")
    monkeypatch.setattr(digest, "_edge", "")
    monkeypatch.setattr(digest, "_latest_rejection", "")
    monkeypatch.setattr(digest, "_rejection_captured", 0)
    monkeypatch.setattr(digest, "_selected_blocks", deque(["old-selected"]))
    monkeypatch.setattr(digest, "_scorer_blocks", deque(["old-scorer"]))
    monkeypatch.setattr(digest, "_route_blocks", deque())
    monkeypatch.setattr(digest, "_shadow_events", deque())
    monkeypatch.setattr(digest, "_discovery_by_symbol", {})
    monkeypatch.setattr(digest, "_periodic_summary", "")
    monkeypatch.setattr(digest, "_last_flush_ts", 0.0)
    monkeypatch.setattr(digest, "_started_ts", 0.0)
    monkeypatch.setattr(digest, "build", classmethod(lambda cls: "A63 test digest\n"))
    return digest


@pytest.mark.asyncio
async def test_a63_digest_snapshot_swap_keeps_events_arriving_during_await(monkeypatch):
    structured = {"scorer_block": deque([{"symbol": "OLD"}]),
                  "route_block": deque(), "builder_block": deque()}
    digest = _seed_digest(monkeypatch, structured)
    injected = False

    async def enqueue(_message):
        nonlocal injected
        if not injected:
            injected = True
            digest.capture("scorer_block", "SELECTED → BUILDER BLOCK\nNEW/USDT\nstage=scorer\nreason=score_below_threshold")
        return True

    monkeypatch.setattr(bot, "_V702_R28_RAW_ENQUEUE", enqueue)
    result = await digest.flush(force=True)
    assert result is True
    assert digest._events == 1
    assert list(digest._scorer_blocks)[0].find("NEW/USDT") >= 0
    assert [item.get("symbol") for item in structured["scorer_block"]] == ["NEW/USDT"]
    assert bot.STATS.get("v702_a63_digest_delivery_state") == "QUEUED_NOT_DELIVERED_ACK"


@pytest.mark.asyncio
async def test_a63_digest_failed_enqueue_merges_old_and_new_generations(monkeypatch):
    structured = {"scorer_block": deque([{"symbol": "OLD"}]),
                  "route_block": deque(), "builder_block": deque()}
    digest = _seed_digest(monkeypatch, structured)
    injected = False

    async def enqueue(_message):
        nonlocal injected
        if not injected:
            injected = True
            digest.capture("scorer_block", "SELECTED → BUILDER BLOCK\nNEW/USDT\nstage=scorer\nreason=score_below_threshold")
        return False

    monkeypatch.setattr(bot, "_V702_R28_RAW_ENQUEUE", enqueue)
    result = await digest.flush(force=True)
    assert result is False
    assert digest._events == 4
    assert len(digest._scorer_blocks) == 2
    assert "NEW/USDT" in "\n".join(digest._scorer_blocks)
    assert "old-scorer" in digest._scorer_blocks
    assert len(structured["scorer_block"]) == 2
    assert {row.get("symbol") for row in structured["scorer_block"]} == {"OLD", "NEW/USDT"}


def test_a63_release_self_test_is_current_and_remains_no_go():
    report = bot._v702_a63_self_test()
    assert report["pass"] is True, report.get("failed")
    assert bot.V702_FINAL_CANONICAL_RELEASE == "UNIFIED-SCALPER-V702-A63-CANONICAL-FINAL"
    assert report["hard_gate_bypass"] is False
    assert report["live_gates_relaxed"] is False
    assert report["production_decision"] == "NO_GO_UNATTENDED_LIVE"


def test_a63_reconciliation_reads_use_central_rate_limiter(monkeypatch):
    calls = []

    class ReadOnlyExchange:
        async def fetch_orders(self, symbol, since=None):
            return [{"id": "venue-1", "symbol": symbol, "side": "buy", "amount": 1.0}]

        async def fetch_open_orders(self, symbol):
            return []

    async def audited_safe_call(label, factory, *, retry_safe=False):
        calls.append(label)
        value = factory()
        return await value if asyncio.iscoroutine(value) else value

    monkeypatch.setattr(bot, "safe_api_call", audited_safe_call)
    result = asyncio.run(bot._v517_fetch_recent_orders(ReadOnlyExchange(), "ABC/USDT"))
    assert result and result[0]["id"] == "venue-1"
    assert "reconcile_fetch_orders" in calls
    assert all(label.startswith("reconcile_") for label in calls)


def test_a63_native_stop_capability_does_not_bypass_live_position_manager_health(monkeypatch):
    monkeypatch.setattr(bot.ProductionCapabilityGate, "_checked", True)
    monkeypatch.setattr(bot.ProductionCapabilityGate, "_stop_mode", "dedicated_stop_market")
    monkeypatch.setitem(bot.CONFIG, "POSITION_MANAGER_TASK_ENABLE", True)
    monkeypatch.setattr(bot, "ACTIVE_TRADES", {}, raising=False)
    monkeypatch.setitem(bot.STATS, "v702_pm_task_state", "STOPPED")
    monkeypatch.setitem(bot.STATS, "v702_pm_healthy_ticks", 0)
    monkeypatch.setitem(bot.STATS, "v702_pm_last_healthy_ts", bot.WALL_NOW())
    assert bot._v702_position_manager_health_ok() is False
    assert bot.STATS.get("v702_pm_health_last_reason") == "position_manager_not_running"

    monkeypatch.setitem(bot.STATS, "v702_pm_task_state", "RUNNING")
    monkeypatch.setitem(bot.STATS, "v702_pm_healthy_ticks", 1)
    monkeypatch.setitem(bot.STATS, "v702_pm_last_healthy_ts", bot.WALL_NOW())
    assert bot._v702_position_manager_health_ok() is True


def test_a63_setup_identity_collapses_repeated_scan_of_same_closed_bar(tmp_path, monkeypatch):
    monkeypatch.setitem(bot.CONFIG, "DB_PATH", str(tmp_path / "setup-identity.sqlite3"))
    monkeypatch.setenv("UNIFIED_PAPER_SIM_ENABLE", "1")
    monkeypatch.setenv("UNIFIED_MONITOR_ONLY_SCAN_ENABLE", "1")
    monkeypatch.setattr(bot.KillSwitch, "is_active", staticmethod(lambda: False))
    bot.KnowledgeOutcomeLedger.ensure_schema()
    bar_ts = int(bot.WALL_NOW() * 1000) // 300_000 * 300_000

    def candidate(generated_at_ms):
        return SimpleNamespace(
            symbol="ABC/USDT", side="long", family="PULLBACK", strategy_mode="PULLBACK",
            strategy_style="SCALP", timeframe_profile="15M_5M", engine_score=0.90,
            entry_ref=100.0, sl_price=98.0, tp1_rr=1.0, tp2_rr=2.0, tp3_rr=3.0,
            generated_at_ms=generated_at_ms, quality_grade="A", zone_ref=100.0,
            features_snapshot={"closed_candle_ts": bar_ts / 1000.0},
        )

    first_id = bot.KnowledgeOutcomeLedger.register_alert(
        candidate(bar_ts + 1_000), {}, source="SELECTED_ROUTE_PAPER", assume_fill=False,
    )
    duplicate_id = bot.KnowledgeOutcomeLedger.register_alert(
        candidate(bar_ts + 90_000), {}, source="SELECTED_ROUTE_PAPER", assume_fill=False,
    )
    assert first_id
    assert duplicate_id is None  # same closed-bar setup is not a second independent sample
    import json as _json
    import sqlite3 as _sqlite3
    conn = _sqlite3.connect(str(bot.CONFIG["DB_PATH"]))
    rows = conn.execute("SELECT alert_id,notes FROM knowledge_outcomes").fetchall()
    conn.close()
    assert len(rows) == 1 and rows[0][0] == first_id
    notes = _json.loads(rows[0][1])
    assert notes["setup_id"]
    assert notes["attempt_id"]
    assert notes["setup_bar_ts_ms"] == bar_ts
