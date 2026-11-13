"""Focused regression tests for the A55 production-release fixes."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pandas as pd
from pathlib import Path
import main as bot


def test_a55_monitor_scan_does_not_depend_on_live_toggle_or_balance(monkeypatch):
    monkeypatch.setenv("UNIFIED_LIVE_PILOT_ENABLE", "1")
    monkeypatch.setenv("UNIFIED_MONITOR_ONLY_SCAN_ENABLE", "1")
    monkeypatch.setattr(bot.KillSwitch, "is_active", staticmethod(lambda: False))
    monkeypatch.setitem(bot.CONFIG, "V702_R38_HARD_GATE_BYPASS", False)
    monkeypatch.setitem(bot.CONFIG, "V702_R36_HARD_GATE_BYPASS", False)
    assert bot._v702_monitor_only_scan_authorized() is True


def test_a55_paper_sim_is_independent_of_available_balance(monkeypatch):
    monkeypatch.setenv("UNIFIED_LIVE_PILOT_ENABLE", "1")
    monkeypatch.setenv("UNIFIED_PAPER_SIM_ENABLE", "1")
    monkeypatch.setenv("UNIFIED_MONITOR_ONLY_SCAN_ENABLE", "1")
    monkeypatch.setattr(bot.KillSwitch, "is_active", staticmethod(lambda: False))
    monkeypatch.setitem(bot.CONFIG, "V702_R38_HARD_GATE_BYPASS", False)
    monkeypatch.setitem(bot.CONFIG, "V702_R36_HARD_GATE_BYPASS", False)
    assert bot._v702_paper_sim_authorized() is True


def test_a55_timestamp_conversion_supports_ns_us_and_ms_datetime_indexes():
    expected = [1704067200000, 1704070800000]
    for unit in ("ns", "us", "ms"):
        idx = pd.date_range("2024-01-01T00:00:00Z", periods=2, freq="h").as_unit(unit)
        frame = pd.DataFrame({"close": [1.0, 1.1]}, index=idx)
        assert bot._v702_a33_timestamp_ms(frame) == expected


def test_a55_real_buy_is_blocked_when_operator_did_not_explicitly_opt_in(monkeypatch):
    class ExchangeStub:
        def __init__(self):
            self.calls = 0

        def amount_to_precision(self, *_args):
            self.calls += 1
            return "1"

    # An inherited prior-release live toggle must not arm A55 without its second key.
    monkeypatch.setenv("UNIFIED_LIVE_PILOT_ENABLE", "1")
    monkeypatch.delenv("UNIFIED_A55_LIVE_ARM", raising=False)
    monkeypatch.setattr(bot.KillSwitch, "is_active", staticmethod(lambda: False))
    monkeypatch.setattr(bot.LiveStateMachine, "is_live_runnable", staticmethod(lambda: True))
    monkeypatch.setattr(bot, "LIVE_ENTRIES_BLOCKED", {"active": False})
    exchange = ExchangeStub()
    ok, order_id, fill_price = asyncio.run(
        bot.OrderExecutor.submit_entry(exchange, "TEST/USDT", 1.0, 10.0, is_paper=False)
    )
    assert (ok, order_id, fill_price) == (False, None, 0.0)
    assert exchange.calls == 0


def test_a55_live_authorization_requires_two_keys_and_nonempty_candidate_context(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(bot.KillSwitch, "is_active", staticmethod(lambda: False))
    monkeypatch.setattr(bot.LiveStateMachine, "is_live_runnable", staticmethod(lambda: True))
    monkeypatch.setattr(bot, "LIVE_ENTRIES_BLOCKED", {"active": False})
    monkeypatch.setattr(bot, "_v702_position_manager_health_ok", lambda: True)
    monkeypatch.delenv("UNIFIED_LIVE_PILOT_ENABLE", raising=False)
    assert bot._v702_live_buy_possible() is False
    monkeypatch.setenv("UNIFIED_LIVE_PILOT_ENABLE", "1")
    monkeypatch.delenv("UNIFIED_A55_LIVE_ARM", raising=False)
    assert bot._v702_live_buy_possible() is False
    monkeypatch.setenv("UNIFIED_A55_LIVE_ARM", "1")
    # Even two keys never authorize a context-free call.
    assert bot._v702_live_buy_possible() is False
    monkeypatch.setattr(bot, "EdgeGate", SimpleNamespace(live_permitted=lambda _ctx: (True, "test_allowed")), raising=False)
    context = {"family": "PULLBACK", "strategy_mode": "PULLBACK", "strategy_style": "SCALP", "timeframe_profile": "15M_5M", "htf_strength": 90.0}
    assert bot._v702_live_buy_possible(context) is True


def test_a55_release_defaults_are_monitor_first_and_recipe_sample_is_conservative():
    assert bot.CONFIG["V702_KNOWLEDGE_OUTCOME_MAX_ACTIVE"] == 20
    assert bot.CONFIG["V702_KNOWLEDGE_RECIPE_MIN_OBS"] == 100
    env_example = Path(__file__).with_name("LIVE_RELEASE_ENV.example").read_text(encoding="utf-8")
    assert "\nUNIFIED_LIVE_PILOT_ENABLE=0\n" in "\n" + env_example + "\n"
    assert "\nUNIFIED_A55_LIVE_ARM=0\n" in "\n" + env_example + "\n"


def test_a55_legacy_submit_wrapper_preserves_exact_intent_context(monkeypatch):
    captured = {}
    async def fake_submit(exchange, symbol, qty, price, is_paper=False, trace_id=None, intent_context=None):
        captured["context"] = intent_context
        return True, "MOCK", float(price)
    monkeypatch.setattr(bot, "_orig_v587_submit", fake_submit)
    monkeypatch.setitem(bot.CONFIG, "V587_PULLBACK_JIT_VALIDATION_ENABLE", False)
    context = {"family": "PULLBACK", "strategy_style": "SCALP",
               "timeframe_profile": "15M_5M", "htf_strength": 91.0}
    result = asyncio.run(bot._v587_submit_entry(
        object(), "BTC/USDT", 0.1, 100.0, False, "A55-CONTEXT", intent_context=context
    ))
    assert result == (True, "MOCK", 100.0)
    assert captured["context"] is context
