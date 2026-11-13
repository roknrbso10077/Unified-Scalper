"""A21: close the confirmed TIA submit blocker without relaxing hard gates."""
from pathlib import Path

import main as bot


def test_a21_default_release_removes_hidden_diagnostic_hold():
    source = Path(bot.__file__).read_text(encoding="utf-8")
    guard = (Path(bot.__file__).with_name("production_guardrails.py")).read_text(encoding="utf-8")
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A21_CANONICAL_REVISION)
    assert 'os.environ.get("UNIFIED_A19_DIAGNOSTIC_ONLY", "0")' in source
    assert 'os.environ.get("UNIFIED_A19_DIAGNOSTIC_ONLY", "0")' in guard
    assert bot._v702_a21_terminal_self_test()["pass"]


def test_a21_release_preserves_execution_and_risk_hard_gates():
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70
    assert bot.CONFIG["LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME"] >= 3_000_000
    assert bot.CONFIG["LONG_ONLY"] is True
    assert str(bot.CONFIG["MARKET_TYPE"]).upper() == "SPOT"
    assert bot.CONFIG.get("ENABLE_FUTURES", False) is False
    assert bot.CONFIG.get("FUTURES_ENABLED", False) is False
    assert {"AERO", "BNB", "CAKE", "ETHFI", "PUMP"}.issubset(set(bot.V702_HARD_FORBIDDEN_BASES))
    assert bot.CONFIG["MAX_CONCURRENT_TRADES"] <= 2
    assert bot.CONFIG["MAX_ENTRY_NOTIONAL_USDT"] <= 75
    assert bot.CONFIG["MAX_POSITION_SIZE_USDT"] <= 75
    assert bot.CONFIG.get("V702_PORTFOLIO_DRAWDOWN_GUARD_ENABLE") is True
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False
