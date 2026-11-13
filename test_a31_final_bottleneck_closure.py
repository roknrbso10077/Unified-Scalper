"""A31 canonical regressions for bounded history revalidation and complete paging."""
from pathlib import Path
import pandas as pd
import main as bot

ROOT = Path(__file__).resolve().parent


def _closed_short_rows(now_ms: int, n: int = 90):
    interval = 4 * 60 * 60 * 1000
    current_open = now_ms - (now_ms % interval)
    first = current_open - n * interval
    return [
        [first + i * interval, 1.0, 1.1, 0.9, 1.02, 100.0]
        for i in range(n)
    ]


def test_a31_lineage_is_preserved_and_a32_is_canonical_with_hard_floors_unchanged():
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A35_CANONICAL_REVISION + "-A36-")
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A32_CANONICAL_REVISION + "-A33-")
    assert bot.FINAL_CANONICAL_RUNTIME["package_audit_revision"].startswith(bot.V702_A35_CANONICAL_REVISION + "-A36-")
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False
    assert bot.CONFIG["LONG_ONLY"] is True
    assert str(bot.CONFIG["MARKET_TYPE"]).upper() == "SPOT"
    assert not bool(bot.CONFIG.get("ENABLE_FUTURES", False))
    assert not bool(bot.CONFIG.get("ALLOW_SHORT", False))
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70
    assert bot.CONFIG["LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME"] >= 3_000_000
    assert bot.CONFIG["V45_TIER_MICRO_MIN_DEPTH_RATIO"] >= 1.90
    assert bot.CONFIG["MIN_TP1_TO_FEE_RATIO"] >= 2.5
    assert max(210, int(bot.CONFIG.get("HTF_MIN_CANDLES_4H", 200))) >= 210
    assert {"AERO", "BNB", "CAKE", "ETHFI", "PUMP"}.issubset(set(bot.V702_HARD_FORBIDDEN_BASES))


def test_a31_negative_cache_expires_after_bounded_ttl_not_four_hours():
    # Use a stable instant that is safely away from the 4H boundary.
    now_ms = int(pd.Timestamp("2026-10-15T05:30:00Z").timestamp() * 1000)
    symbol = "A31-REVALIDATE/USDT"
    previous = bot._V702_A29_SHORT_HISTORY_CACHE.get(symbol)
    existed = symbol in bot._V702_A29_SHORT_HISTORY_CACHE
    old_ttl = bot.CONFIG.get("V702_A31_SHORT_HISTORY_RECHECK_SEC")
    old_enabled = bot.CONFIG.get("V702_A31_SHORT_HISTORY_NEGATIVE_CACHE_ENABLE")
    try:
        bot.CONFIG["V702_A31_SHORT_HISTORY_RECHECK_SEC"] = 420.0
        bot.CONFIG["V702_A31_SHORT_HISTORY_NEGATIVE_CACHE_ENABLE"] = True
        rows = _closed_short_rows(now_ms, n=90)
        assert bot._v702_a29_history_cache_put(
            symbol,
            rows,
            {"complete": False, "reason": "short_history", "required_rows": 210},
            now_ms,
        ) is True
        item = bot._V702_A29_SHORT_HISTORY_CACHE[symbol]
        assert item["cache_policy"] == "BOUNDED_NEGATIVE_CACHE"
        assert item["reason"] == "short_history_negative_cache"
        assert item["valid_after_ms"] == now_ms + 420_000
        hit = bot._v702_a29_history_cache_get(symbol, now_ms + 60_000)
        assert hit is not None
        assert hit[1]["cache_policy"] == "BOUNDED_NEGATIVE_CACHE"
        assert hit[1]["reason"] == "admissible_partial_4h_history_reuse"
        assert hit[1]["required"] == 50 and hit[1]["target_rows"] == 210
        assert bot._v702_a29_history_cache_get(symbol, now_ms + 421_000) is None
        assert symbol not in bot._V702_A29_SHORT_HISTORY_CACHE
        assert int(bot.STATS.get("v702_a31_history_cache_expired_rechecks", 0) or 0) >= 1
    finally:
        if existed:
            bot._V702_A29_SHORT_HISTORY_CACHE[symbol] = previous
        else:
            bot._V702_A29_SHORT_HISTORY_CACHE.pop(symbol, None)
        if old_ttl is None:
            bot.CONFIG.pop("V702_A31_SHORT_HISTORY_RECHECK_SEC", None)
        else:
            bot.CONFIG["V702_A31_SHORT_HISTORY_RECHECK_SEC"] = old_ttl
        if old_enabled is None:
            bot.CONFIG.pop("V702_A31_SHORT_HISTORY_NEGATIVE_CACHE_ENABLE", None)
        else:
            bot.CONFIG["V702_A31_SHORT_HISTORY_NEGATIVE_CACHE_ENABLE"] = old_enabled


def test_a31_disabled_negative_cache_falls_back_to_normal_fetch_policy():
    now_ms = int(pd.Timestamp("2026-10-15T05:30:00Z").timestamp() * 1000)
    symbol = "A31-CACHE-DISABLED/USDT"
    previous = bot._V702_A29_SHORT_HISTORY_CACHE.get(symbol)
    existed = symbol in bot._V702_A29_SHORT_HISTORY_CACHE
    old_enabled = bot.CONFIG.get("V702_A31_SHORT_HISTORY_NEGATIVE_CACHE_ENABLE")
    try:
        bot.CONFIG["V702_A31_SHORT_HISTORY_NEGATIVE_CACHE_ENABLE"] = False
        assert bot._v702_a29_history_cache_put(
            symbol,
            _closed_short_rows(now_ms, n=90),
            {"complete": False, "reason": "short_history", "required_rows": 210},
            now_ms,
        ) is False
        assert symbol not in bot._V702_A29_SHORT_HISTORY_CACHE
    finally:
        if existed:
            bot._V702_A29_SHORT_HISTORY_CACHE[symbol] = previous
        else:
            bot._V702_A29_SHORT_HISTORY_CACHE.pop(symbol, None)
        if old_enabled is None:
            bot.CONFIG.pop("V702_A31_SHORT_HISTORY_NEGATIVE_CACHE_ENABLE", None)
        else:
            bot.CONFIG["V702_A31_SHORT_HISTORY_NEGATIVE_CACHE_ENABLE"] = old_enabled


def test_a31_terminal_self_test_passes_and_refuses_policy_relaxation():
    report = bot._v702_a31_terminal_self_test()
    assert report["pass"] is True, report
    assert report["failed"] == [], report
    assert report["checks"]["a31_revision_appends_a30"] is True
    assert report["checks"]["a31_short_history_recheck_is_bounded"] is True
    assert report["checks"]["a31_recovery_timeout_is_bounded"] is True
    assert report["checks"]["a31_recovery_page_budget_is_four"] is True
    assert report["checks"]["a31_hard_contracts_preserved"] is True
    assert report["hard_gate_bypass"] is False
    assert report["live_gates_relaxed"] is False
    assert report["live_network_tested"] is False
    assert report["profitability_verified"] is False


def test_a31_page_and_heartbeat_contracts_are_present_in_canonical_source():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "max_extra_pages=4" in source
    assert "_pages_cap = max(0, min(4, int(max_extra_pages)))" in source
    assert '"V702_R41_4H_RECOVERY_PAGE_TIMEOUT_SEC": 2.0' in source
    assert "A31_HISTORY_RECHECK=ttl:" in source
    assert "does not prove listing age" in source
    assert '"v702_a31_terminal_self_test": STATS.get("v702_a31_terminal_self_test", {})' in source
    assert '"canonical_runtime_revision": V702_PACKAGE_AUDIT_REVISION' in source
    assert '"canonical_package_revision": V702_PACKAGE_AUDIT_REVISION' in source
