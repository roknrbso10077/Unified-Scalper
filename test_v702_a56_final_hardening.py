"""A56 offline regression tests for final authorization, time integrity and stop-worker health."""
from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import main as bot


class _ExchangeWithFees:
    def __init__(self):
        self.markets = {"A56TEST/USDT": {"taker": 0.001}}
        self.fees = {"trading": {"taker": 0.001}}


def _valid_shadow_geometry():
    book = {"asks": [[100.10, 1000.0]], "bids": [[99.90, 1000.0]]}
    return book


def test_a56_contextless_live_buy_is_denied_even_when_both_keys_are_armed(monkeypatch):
    monkeypatch.setenv("UNIFIED_LIVE_PILOT_ENABLE", "1")
    monkeypatch.setenv("UNIFIED_A55_LIVE_ARM", "1")
    monkeypatch.setattr(bot.KillSwitch, "is_active", staticmethod(lambda: False))
    monkeypatch.setattr(bot.LiveStateMachine, "is_live_runnable", staticmethod(lambda: True))
    monkeypatch.setattr(bot, "LIVE_ENTRIES_BLOCKED", {"active": False})
    monkeypatch.setattr(bot, "_v702_position_manager_health_ok", lambda: True)
    monkeypatch.setattr(bot, "EdgeGate", SimpleNamespace(live_permitted=lambda _ctx: (True, "mock_ok")), raising=False)

    assert bot._v702_live_buy_possible(None) is False
    assert bot._v702_live_buy_possible({}) is False
    assert bot.STATS.get("v702_a56_contextless_live_buy_blocks", 0) >= 2
    context = {
        "family": "PULLBACK", "strategy_mode": "PULLBACK", "strategy_style": "SCALP",
        "timeframe_profile": "15M_5M", "htf_strength": 90.0,
    }
    assert bot._v702_live_buy_possible(context) is True


def test_a56_shadow_rejects_future_dated_orderbook(monkeypatch):
    monkeypatch.setitem(bot.CONFIG, "MARKET_TYPE", "SPOT")
    monkeypatch.setitem(bot.CONFIG, "LONG_ONLY", True)
    monkeypatch.setitem(bot.CONFIG, "ALLOW_SHORT", False)
    monkeypatch.setitem(bot.CONFIG, "MIN_LIVE_SCORE", 70.0)
    book = _valid_shadow_geometry()
    market_data = {"orderbook": book, "orderbook_ts": time.time() + 3600.0}
    result = asyncio.run(bot.ShadowPreSendGate.evaluate(
        _ExchangeWithFees(), "A56TEST/USDT", 100.0, 99.0, 103.0, 105.0, 110.0,
        market_data=market_data, cached_ob=book, strategy_score=90.0,
        strategy_mode="PULLBACK", strategy_family="PULLBACK",
        strategy_style="SCALP", timeframe_profile="15M_5M", htf_strength=90.0,
    ))
    assert result["eligible"] is False
    assert result["reason"] == "orderbook_timestamp_in_future"
    assert result["exchange_order_submitted"] is False


def test_a56_software_sl_mode_requires_recent_position_manager_health_lease(monkeypatch):
    monkeypatch.setattr(bot.ProductionCapabilityGate, "_checked", True)
    monkeypatch.setattr(bot.ProductionCapabilityGate, "_stop_mode", "software_sl_only")
    monkeypatch.setitem(bot.CONFIG, "POSITION_MANAGER_TASK_ENABLE", True)
    monkeypatch.setattr(bot, "ACTIVE_TRADES", {}, raising=False)
    monkeypatch.setitem(bot.STATS, "v702_pm_task_state", "STOPPED")
    monkeypatch.setitem(bot.STATS, "v702_pm_last_healthy_ts", time.time())
    assert bot._v702_position_manager_health_ok() is False

    monkeypatch.setitem(bot.STATS, "v702_pm_task_state", "RUNNING")
    monkeypatch.setitem(bot.STATS, "v702_pm_healthy_ticks", 1)
    monkeypatch.setitem(bot.STATS, "v702_pm_last_healthy_ts", time.time())
    assert bot._v702_position_manager_health_ok() is True

    monkeypatch.setitem(bot.STATS, "v702_pm_healthy_ticks", 0)
    assert bot._v702_position_manager_health_ok() is False
    monkeypatch.setitem(bot.STATS, "v702_pm_healthy_ticks", 1)

    monkeypatch.setitem(bot.STATS, "v702_pm_last_healthy_ts", time.time() - 120.0)
    assert bot._v702_position_manager_health_ok() is False


def test_a56_software_sl_mode_blocks_new_entries_if_any_open_trade_is_unprotected(monkeypatch):
    monkeypatch.setattr(bot.ProductionCapabilityGate, "_checked", True)
    monkeypatch.setattr(bot.ProductionCapabilityGate, "_stop_mode", "software_sl_only")
    monkeypatch.setitem(bot.CONFIG, "POSITION_MANAGER_TASK_ENABLE", True)
    monkeypatch.setitem(bot.STATS, "v702_pm_task_state", "RUNNING")
    monkeypatch.setitem(bot.STATS, "v702_pm_last_healthy_ts", time.time())
    bad_trade = SimpleNamespace(
        symbol="A56TEST/USDT", remaining_position=1.0, entry=100.0,
        current_sl=99.0, original_sl=99.0, sl_order_id=None,
        sl_health_state="UNVERIFIED", software_sl_active=False,
    )
    monkeypatch.setattr(bot, "ACTIVE_TRADES", {"A56TEST/USDT": bad_trade}, raising=False)
    assert bot._v702_position_manager_health_ok() is False


def test_a56_runtime_guardrails_require_both_operator_keys(monkeypatch):
    monkeypatch.setenv("UNIFIED_LIVE_PILOT_ENABLE", "1")
    monkeypatch.delenv("UNIFIED_A55_LIVE_ARM", raising=False)
    monkeypatch.setenv("UNIFIED_ALLOW_LIVE_TRADING", "I_ACCEPT_LIVE_RISK")
    monkeypatch.setattr(bot.KillSwitch, "is_active", staticmethod(lambda: False))
    monkeypatch.setattr(bot.LiveStateMachine, "is_live_runnable", staticmethod(lambda: True))
    monkeypatch.setattr(bot, "_v702_position_manager_health_ok", lambda: True)
    monkeypatch.setitem(bot.ENV, "MEXC_API_KEY", "OFFLINE_TEST_KEY")
    monkeypatch.setitem(bot.ENV, "MEXC_API_SECRET", "OFFLINE_TEST_SECRET")
    monkeypatch.setitem(bot.CONFIG, "V702_LIVE_PILOT_ENABLE", True)
    monkeypatch.setitem(bot.CONFIG, "ENABLE_LIVE_TRADING", True)
    monkeypatch.setitem(bot.CONFIG, "PAPER_TRADING_MODE", False)
    monkeypatch.setitem(bot.CONFIG, "LONG_ONLY", True)
    monkeypatch.setitem(bot.CONFIG, "MARKET_TYPE", "SPOT")
    monkeypatch.setitem(bot.CONFIG, "TRADING_SIDE", "LONG")
    monkeypatch.setitem(bot.CONFIG, "FUTURES_ENABLED", False)
    monkeypatch.setitem(bot.CONFIG, "ENABLE_FUTURES", False)
    monkeypatch.setitem(bot.CONFIG, "ALLOW_SHORT", False)
    monkeypatch.setitem(bot.CONFIG, "ALLOW_SHORTS", False)
    monkeypatch.setitem(bot.CONFIG, "POSITION_MANAGER_TASK_ENABLE", True)
    monkeypatch.setitem(bot.CONFIG, "V702_PORTFOLIO_DRAWDOWN_GUARD_ENABLE", True)
    monkeypatch.setitem(bot.CONFIG, "MAX_CONCURRENT_TRADES", 2)
    monkeypatch.setitem(bot.CONFIG, "MIN_LIVE_SCORE", 70.0)
    monkeypatch.setitem(bot.CONFIG, "LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME", 3_000_000.0)
    monkeypatch.setitem(bot.CONFIG, "V702_R38_HARD_GATE_BYPASS", False)
    monkeypatch.setitem(bot.CONFIG, "V702_R36_HARD_GATE_BYPASS", False)
    monkeypatch.setattr(bot, "LIVE_ENTRIES_BLOCKED", {"active": False})
    monkeypatch.setattr(bot, "V702_HARD_FORBIDDEN_BASES", {"AERO", "BNB", "CAKE", "ETHFI", "PUMP"})
    assert bot._V702_R39_REFRESH_ENTRY_MODE() is True

    monkeypatch.setenv("UNIFIED_A55_LIVE_ARM", "1")
    assert bot._V702_R39_REFRESH_ENTRY_MODE() is False
    assert bot.STATS.get("v702_runtime_entry_policy") == "USER_REQUESTED_LIVE_PILOT"
    assert bot.STATS.get("v702_live_operator_two_key_armed") is True


def test_a56_validator_contains_all_new_safety_closures():
    assert bot.validate_config() is True
    report = bot.STATS.get("v702_a56_validation") or {}
    assert report.get("pass") is True, report
    assert all((report.get("checks") or {}).values()), report
    assert report.get("live_network_tested") is False
    assert report.get("docker_build_tested") is False
    assert report.get("transitive_dependencies_hash_locked") is False


def test_a57_unknown_or_uncertified_stop_mode_fails_closed(monkeypatch):
    monkeypatch.setitem(bot.CONFIG, "POSITION_MANAGER_TASK_ENABLE", True)
    monkeypatch.setitem(bot.STATS, "v702_pm_task_state", "RUNNING")
    monkeypatch.setitem(bot.STATS, "v702_pm_healthy_ticks", 1)
    monkeypatch.setitem(bot.STATS, "v702_pm_last_healthy_ts", time.time())
    monkeypatch.setattr(bot.ProductionCapabilityGate, "_checked", False)
    monkeypatch.setattr(bot.ProductionCapabilityGate, "_stop_mode", "dedicated_stop_market")
    assert bot._v702_position_manager_health_ok() is False
    assert bot.STATS.get("v702_pm_health_last_reason") == "production_capability_not_certified"

    monkeypatch.setattr(bot.ProductionCapabilityGate, "_checked", True)
    monkeypatch.setattr(bot.ProductionCapabilityGate, "_stop_mode", None)
    assert bot._v702_position_manager_health_ok() is False
    assert bot.STATS.get("v702_pm_health_last_reason") == "production_stop_mode_unverified"


def test_a57_position_manager_start_does_not_claim_health_before_first_success(monkeypatch):
    class StopAfterOneCycle:
        def __init__(self): self.calls = 0
        def is_set(self):
            self.calls += 1
            return self.calls > 1

    async def broken_tick(_exchange):
        raise RuntimeError("injected_first_cycle_failure")

    monkeypatch.setattr(bot.ProductionCapabilityGate, "_checked", True)
    monkeypatch.setattr(bot.ProductionCapabilityGate, "_stop_mode", "software_sl_only")
    monkeypatch.setitem(bot.CONFIG, "POSITION_MANAGER_TASK_ENABLE", True)
    monkeypatch.setattr(bot, "_SHUTDOWN", StopAfterOneCycle())
    monkeypatch.setattr(bot, "ACTIVE_TRADES", {"A57TEST/USDT": object()}, raising=False)
    monkeypatch.setattr(bot.PositionManager, "tick", staticmethod(broken_tick))
    asyncio.run(bot._position_manager_task(object()))
    assert bot.STATS.get("v702_pm_task_state") == "STOPPED"
    assert bot.STATS.get("v702_pm_last_healthy_ts") == 0.0
    assert bot._v702_position_manager_health_ok() is False
