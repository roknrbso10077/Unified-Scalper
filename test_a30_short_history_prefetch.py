"""A30 throughput regressions: cached short 4H history skips only redundant reads."""
from pathlib import Path
import time

import main as bot

ROOT = Path(__file__).resolve().parent


def _cache_short_history(symbol="A30-SHORT/USDT", rows=92, now_ms=None):
    interval = 4 * 60 * 60 * 1000
    now = int(now_ms if now_ms is not None else time.time() * 1000)
    current_open = now - (now % interval)
    stamps = [current_open - (rows - i) * interval for i in range(rows)]
    bot._V702_A29_SHORT_HISTORY_CACHE[symbol] = {
        "closed_rows": [[ts, 1.0, 1.1, 0.9, 1.0, 100.0] for ts in stamps],
        "required_rows": 210,
        "expected_last_closed_ts": current_open - interval,
        "valid_after_ms": current_open + interval,
        "stored_at_ms": now,
        "reason": "age_limited_short_history",
        "source_reason": "short_history",
    }
    return now


def test_a30_revision_is_append_only_and_preserves_hard_gates():
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A35_CANONICAL_REVISION + "-A36-")
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A29_CANONICAL_REVISION + "-A30-")
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70
    assert bot.CONFIG["LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME"] >= 3_000_000
    assert bot.CONFIG["V45_TIER_MICRO_MIN_DEPTH_RATIO"] >= 1.90
    assert bot.CONFIG["MIN_TP1_TO_FEE_RATIO"] >= 2.5
    assert bot.CONFIG["LONG_ONLY"] and str(bot.CONFIG["MARKET_TYPE"]).upper() == "SPOT"
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False
    assert {"AERO", "BNB", "CAKE", "ETHFI", "PUMP"}.issubset(set(bot.V702_HARD_FORBIDDEN_BASES))


def test_a32_cache_does_not_skip_usable_short_history_and_accepts_50_plus_rows():
    symbol = "A32-USABLE/USDT"
    previous = bot._V702_A29_SHORT_HISTORY_CACHE.get(symbol)
    existed = symbol in bot._V702_A29_SHORT_HISTORY_CACHE
    try:
        now = _cache_short_history(symbol, rows=52)
        decision = bot._v702_a30_cached_short_history_prefetch_skip(symbol, now)
        assert decision is None, decision
        frames = {
            "df_4h": bot.pd.DataFrame({k: [1.0] * 52 for k in ("open", "high", "low", "close", "volume")}),
            "df_1h": bot.pd.DataFrame({k: [1.0] * 240 for k in ("open", "high", "low", "close", "volume")}),
            "df_15m": bot.pd.DataFrame({k: [1.0] * 350 for k in ("open", "high", "low", "close", "volume")}),
            "df_5m": bot.pd.DataFrame({k: [1.0] * 30 for k in ("open", "high", "low", "close", "volume")}),
        }
        ok, reason = bot._mse_candidate_scan_precheck(frames)
        assert ok and reason == "ok", reason
    finally:
        if existed:
            bot._V702_A29_SHORT_HISTORY_CACHE[symbol] = previous
        else:
            bot._V702_A29_SHORT_HISTORY_CACHE.pop(symbol, None)


def test_a32_history_below_50_is_reject_only_and_saves_three_redundant_reads():
    symbol = "A32-TOO-SHORT/USDT"
    previous = bot._V702_A29_SHORT_HISTORY_CACHE.get(symbol)
    existed = symbol in bot._V702_A29_SHORT_HISTORY_CACHE
    try:
        now = _cache_short_history(symbol, rows=49)
        decision = bot._v702_a30_cached_short_history_prefetch_skip(symbol, now)
        assert decision is not None, decision
        assert decision["skip"] is True
        assert decision["got"] == 49
        assert decision["required"] == 50
        assert decision["saved_lower_tf_requests"] == 3
        assert decision["execution_authority_added"] is False
        frames = {
            "df_4h": bot.pd.DataFrame({k: [1.0] * 49 for k in ("open", "high", "low", "close", "volume")}),
            "df_1h": bot.pd.DataFrame({k: [1.0] * 240 for k in ("open", "high", "low", "close", "volume")}),
            "df_15m": bot.pd.DataFrame({k: [1.0] * 350 for k in ("open", "high", "low", "close", "volume")}),
            "df_5m": bot.pd.DataFrame({k: [1.0] * 30 for k in ("open", "high", "low", "close", "volume")}),
        }
        ok, reason = bot._mse_candidate_scan_precheck(frames)
        assert not ok and reason == "df_4h:short_rows:got=49,required=50", reason
    finally:
        if existed:
            bot._V702_A29_SHORT_HISTORY_CACHE[symbol] = previous
        else:
            bot._V702_A29_SHORT_HISTORY_CACHE.pop(symbol, None)


def test_a30_expired_or_missing_short_history_cache_never_skips_fetch():
    symbol = "A30-EXPIRED/USDT"
    previous = bot._V702_A29_SHORT_HISTORY_CACHE.get(symbol)
    existed = symbol in bot._V702_A29_SHORT_HISTORY_CACHE
    try:
        now = _cache_short_history(symbol, rows=80)
        interval = 4 * 60 * 60 * 1000
        next_boundary = (now - (now % interval)) + interval
        assert bot._v702_a30_cached_short_history_prefetch_skip(symbol, next_boundary) is None
        assert bot._v702_a30_cached_short_history_prefetch_skip("A30-MISSING/USDT", now) is None
    finally:
        if existed:
            bot._V702_A29_SHORT_HISTORY_CACHE[symbol] = previous
        else:
            bot._V702_A29_SHORT_HISTORY_CACHE.pop(symbol, None)


def test_a30_short_history_prefetch_runs_before_any_lower_timeframe_fetch():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    marker = 'globals().get("_v702_a30_cached_short_history_prefetch_skip")'
    assert marker in source
    preflight = source.index(marker)
    gather = source.index("return await asyncio.gather(", preflight)
    assert preflight < gather
    assert 'return symbol, None' in source[preflight:gather]
    assert "v702_a30_saved_lower_tf_ohlcv_requests" in source


def test_a30_digest_does_not_report_unknown_last_skip_when_cache_only_exists():
    cache = bot._V702_A29_SHORT_HISTORY_CACHE
    old_cache = dict(cache)
    keys = ("v702_a30_cached_short_history_prefetch_skips",
            "v702_a30_saved_lower_tf_ohlcv_requests",
            "v702_a30_last_cached_history_skip")
    old_stats = {key: bot.STATS.get(key) for key in keys}
    try:
        cache.clear()
        cache["A30-CACHE-ONLY/USDT"] = {"closed_rows": [], "stored_at_ms": 1}
        bot.STATS[keys[0]] = 0
        bot.STATS[keys[1]] = 0
        bot.STATS["v702_a31_history_cache_hits"] = 0
        bot.STATS.pop(keys[2], None)
        line = bot._V702R28TelegramDigest._heartbeat_line(
            "Heartbeat state=FULL_LIVE_RUNNING trades=0 funnel=0/0/0/0"
        )
        assert "A30_HISTORY_PREFETCH=skips:0,saved_reads:0,hits:0,cache:1,last:none_yet" in line, line
        assert "last:-:0/210@unknown" not in line
    finally:
        cache.clear()
        cache.update(old_cache)
        for key, value in old_stats.items():
            if value is None:
                bot.STATS.pop(key, None)
            else:
                bot.STATS[key] = value


def test_a30_verified_skip_accounting_increments_saved_reads_and_last_skip():
    keys = (
        "v702_a30_cached_short_history_prefetch_skips",
        "v702_a30_saved_lower_tf_ohlcv_requests",
        "v702_a30_last_cached_history_skip",
        "v702_a23_local_history_blocks",
        "v702_a23_local_history_block_counts",
        "v702_a23_last_local_history_block",
        "v45_market_data_rejects",
        "v702_a30_last_skip_recorded_ts",
    )
    old = {}
    for key in keys:
        value = bot.STATS.get(key)
        if isinstance(value, dict):
            value = dict(value)
        old[key] = (key in bot.STATS, value)
    try:
        before_skip = int(bot.STATS.get("v702_a30_cached_short_history_prefetch_skips", 0) or 0)
        before_reads = int(bot.STATS.get("v702_a30_saved_lower_tf_ohlcv_requests", 0) or 0)
        ok = bot._v702_a30_record_prefetch_skip("A30-VERIFIED/USDT", {
            "skip": True, "got": 49, "required": 50, "saved_lower_tf_requests": 3,
            "execution_authority_added": False,
        })
        assert ok is True
        assert int(bot.STATS.get("v702_a30_cached_short_history_prefetch_skips", 0) or 0) == before_skip + 1
        assert int(bot.STATS.get("v702_a30_saved_lower_tf_ohlcv_requests", 0) or 0) == before_reads + 3
        last = bot.STATS.get("v702_a30_last_cached_history_skip", {})
        assert last.get("symbol") == "A30-VERIFIED/USDT"
        assert last.get("saved_lower_tf_requests") == 3
        assert bot._v702_a30_record_prefetch_skip("A30-INVALID/USDT", {
            "skip": True, "got": 210, "required": 50, "saved_lower_tf_requests": 3,
            "execution_authority_added": False,
        }) is False
    finally:
        for key, (existed, value) in old.items():
            if existed:
                bot.STATS[key] = value
            else:
                bot.STATS.pop(key, None)


def test_a30_terminal_self_test_passes_without_network_or_trade_authority():
    report = bot._v702_a30_terminal_self_test()
    assert report["pass"], report
    assert report["checks"]["a30_revision_appends_a29"] is True
    assert report["checks"]["a30_no_execution_authority_or_gate_bypass"] is True
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False


def test_a30_runtime_revision_and_helper_are_initialized_before_cli_validation():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    a30 = source.index("# V702 A30 — REJECT-ONLY SHORT-HISTORY PREFETCH THROUGHPUT CLOSURE")
    validate_branch = source.index("if _V699_VALIDATE_ONLY_REQUEST:")
    main_entry = source.rindex('if __name__ == "__main__":')
    assert a30 < validate_branch < main_entry
