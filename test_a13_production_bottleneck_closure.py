"""A13 regressions for fresh liquidity universe, bounded 4H recovery, and MICRO handoff."""
from __future__ import annotations

import asyncio
import os
import tempfile
import time

os.environ.setdefault("SCALPER_DB", os.path.join(tempfile.gettempdir(), f"v702-a13-tests-{os.getpid()}.db"))
import main as bot


def test_fresh_core_filter_excludes_stale_micro_missing_and_derivative_symbols():
    symbols = ["CORE/USDT", "STALE/USDT", "MICRO/USDT", "SWAP/USDT", "MISSING/USDT", "CORE/USDT"]
    markets = {
        "CORE/USDT": {"quote": "USDT", "spot": True, "swap": False, "active": True},
        "STALE/USDT": {"quote": "USDT", "spot": True, "swap": False, "active": True},
        "MICRO/USDT": {"quote": "USDT", "spot": True, "swap": False, "active": True},
        "SWAP/USDT": {"quote": "USDT", "spot": False, "swap": True, "active": True},
        "MISSING/USDT": {"quote": "USDT", "spot": True, "swap": False, "active": True},
    }
    tickers = {
        "CORE/USDT": {"quoteVolume": 4_000_000.0, "last": 1.0},
        "STALE/USDT": {"quoteVolume": 800_000.0, "last": 1.0},
        "MICRO/USDT": {"quoteVolume": 2_000_000.0, "last": 1.0},
        "SWAP/USDT": {"quoteVolume": 8_000_000.0, "last": 1.0},
    }
    eligible, diag = bot._v702_r41_filter_fresh_core_symbols(
        symbols, tickers, markets, min_quote_volume=3_000_000.0
    )
    assert eligible == ["CORE/USDT"]
    assert diag["filtered"] == 4
    assert diag["unique_input"] == 5
    assert diag["reasons"]["below_fresh_core_volume"] == 2
    assert diag["reasons"]["market_inactive_or_not_spot"] == 1
    assert diag["reasons"]["current_ticker_missing"] == 1


def test_micro_depth_deferral_is_bounded_and_does_not_relax_terminal_confirmation():
    book = {"bids": [[1.0, 150.0]], "asks": [[1.001, 130.0]]}
    assert bot._v702_r41_micro_depth_recheck_eligible("MICRO", 1.65, book)
    assert not bot._v702_r41_micro_depth_recheck_eligible("MICRO", 1.49, book)
    assert not bot._v702_r41_micro_depth_recheck_eligible("MICRO", 1.90, book)
    assert not bot._v702_r41_micro_depth_recheck_eligible("MID", 1.65, book)
    assert not bot._v702_r41_micro_depth_recheck_eligible("MICRO", 1.65, {})

    ok, reason = bot._v45_orderbook_confirmation(
        book,
        {
            "spread_pct": 0.1,
            "depth_ratio": 1.65,
            "volume_ratio": 1.2,
            "chase_atr": 0.1,
            "structure_confidence": 80.0,
        },
        "MICRO",
    )
    assert not ok
    assert reason == "micro_depth"
    assert float(bot.CONFIG["V45_TIER_MICRO_MIN_DEPTH_RATIO"]) >= 1.90


def test_4h_fetch_recovers_a_truncated_initial_page_with_bounded_backfill():
    interval = 4 * 60 * 60 * 1000
    now = int(time.time() * 1000)
    current_open = now - now % interval
    all_rows = []
    for idx in range(301):
        ts = current_open - (300 - idx) * interval
        all_rows.append([ts, 1.0, 1.1, 0.9, 1.02, 100.0])

    async def fetch_page(since_ms, limit, suffix):
        # Simulate an exchange that caps every response at 64 rows even when a
        # larger limit was requested. `since` returns the oldest matching page.
        pool = all_rows if since_ms is None else [r for r in all_rows if r[0] >= int(since_ms)]
        if since_ms is None:
            pool = pool[-min(64, int(limit)):]
        else:
            pool = pool[:min(64, int(limit))]
        return pool

    rows, diag = asyncio.run(
        bot._v702_r41_fetch_4h_history(
            fetch_page, now_ms=now, target_rows=220, required_rows=210, max_extra_pages=3
        )
    )
    assert diag["initial_rows"] == 64
    assert diag["complete"] is True
    assert diag["recovered"] is True
    assert diag["pages"] <= 4
    assert len(rows) >= 220
    timestamps = [int(row[0]) for row in rows]
    assert len(timestamps) == len(set(timestamps))
    assert all(b - a == interval for a, b in zip(timestamps[-220:], timestamps[-219:]))
    assert diag["synthetic_rows"] == 0


def test_4h_fetch_handles_a_50_row_exchange_cap_with_four_recovery_pages():
    interval = 4 * 60 * 60 * 1000
    now = int(time.time() * 1000)
    current_open = now - now % interval
    all_rows = [
        [current_open - (300 - idx) * interval, 1.0, 1.1, 0.9, 1.02, 100.0]
        for idx in range(301)
    ]

    async def fetch_page(since_ms, limit, suffix):
        pool = all_rows if since_ms is None else [r for r in all_rows if r[0] >= int(since_ms)]
        if since_ms is None:
            return pool[-min(50, int(limit)):]
        return pool[:min(50, int(limit))]

    rows, diag = asyncio.run(
        bot._v702_r41_fetch_4h_history(
            fetch_page, now_ms=now, target_rows=220, required_rows=210, max_extra_pages=4
        )
    )
    assert diag["initial_rows"] == 50
    assert diag["complete"] is True, diag
    assert diag["recovered"] is True
    assert diag["pages"] <= 5
    assert len(rows) >= 220
    stamps = [int(row[0]) for row in rows]
    assert all(b - a == interval for a, b in zip(stamps[-220:], stamps[-219:]))
    assert diag["synthetic_rows"] == 0


def test_4h_fetch_keeps_short_history_fail_closed_without_fabricating_candles():
    interval = 4 * 60 * 60 * 1000
    now = int(time.time() * 1000)
    current_open = now - now % interval
    short = [
        [current_open - (63 - idx) * interval, 1.0, 1.1, 0.9, 1.02, 100.0]
        for idx in range(64)
    ]

    async def fetch_page(since_ms, limit, suffix):
        if since_ms is None:
            return list(short)
        return [r for r in short if r[0] >= int(since_ms)][:min(64, int(limit))]

    rows, diag = asyncio.run(
        bot._v702_r41_fetch_4h_history(
            fetch_page, now_ms=now, target_rows=220, required_rows=210, max_extra_pages=3
        )
    )
    assert len(rows) == 64
    assert diag["complete"] is False
    assert diag["synthetic_rows"] == 0
    assert diag["reason"] in {"short_history", "recovery_page_added_no_rows", "coverage_gap_or_stale_tail"}


def test_a13_policies_keep_strict_floors_and_five_minute_micro_rotation():
    report = bot._v702_r41_bottleneck_self_test()
    assert report["pass"], report
    assert float(bot.CONFIG["V702_R30_MICRO_RECALL_RECENT_SCAN_TTL_SEC"]) == 300.0
    assert float(bot.CONFIG["V45_TIER_MICRO_MIN_DEPTH_RATIO"]) >= 1.90
    assert max(210, int(bot.CONFIG.get("HTF_MIN_CANDLES_4H", 200))) >= 210
    assert bot.CONFIG["LONG_ONLY"] is True
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False
