from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

import main as bot

ROOT = Path(__file__).resolve().parent


def _frames(*, severe_drop: bool = False, lower_lows: bool = True):
    n15 = 64
    if severe_drop:
        close = [100.0] * n15
        # Last CLOSED candles carry a drop beyond the unchanged -6% crash threshold.
        for i in range(n15 - 10, n15 - 1):
            close[i] = 100.0 - float(i - (n15 - 10))
        close[-1] = close[-2]  # forming candle is ignored by classifier
    else:
        close = [100.0 - 0.015 * i for i in range(n15)]
    df15 = pd.DataFrame({
        "close": close,
        "high": [v + 0.5 for v in close],
        "low": [v - 0.5 for v in close],
        "volume": [1000.0] * n15,
    })
    if lower_lows:
        lows4 = [400.0 - 0.10 * i for i in range(261)]
    else:
        lows4 = [200.0 + 0.01 * i for i in range(261)]
    df4 = pd.DataFrame({"low": lows4, "close": [x + 1.0 for x in lows4], "high": [x + 2.0 for x in lows4]})
    return df15, df4


def test_a43_lower_low_sequence_alone_is_stressed_not_a_global_crash():
    original_state = bot.BTCContext._state
    original_cache = bot.OrderedDict(bot._V702_A17_BEARISH_SEVERITY_CACHE)
    try:
        bot.BTCContext._state = "OK"
        bot._V702_A17_BEARISH_SEVERITY_CACHE.clear()
        df15, df4 = _frames(severe_drop=False, lower_lows=True)
        severity = bot.V425BearishSeverity.classify("BEARISH", df15, df4)
        facts = dict(bot.STATS.get("v702_a43_bearish_last", {}) or {})
        assert severity == bot.V425BearishSeverity.STRESSED, (severity, facts)
        assert facts.get("cause") == "BREAKDOWN_ONLY_CLASSIFIED_STRESSED", facts
        assert facts.get("breakdown") is True and facts.get("atr_expanding") is False, facts
        assert facts.get("decision_changed_from_a42") is True, facts
        assert bot.V425BearishSeverity.allows_new_long(severity) is True
        # This classification is not trade authorization. The downstream family policy remains the same callable.
        assert bot.FamilyPolicyLayer.strategy_allowed is bot._V702_A43_FAMILY_POLICY_AUTHORITY
        assert bot.FINAL_CANONICAL_RUNTIME.get("hard_gate_bypass") is False
    finally:
        bot.BTCContext._state = original_state
        bot._V702_A17_BEARISH_SEVERITY_CACHE.clear()
        bot._V702_A17_BEARISH_SEVERITY_CACHE.update(original_cache)


def test_a43_severe_drop_missing_data_and_explicit_btc_crash_remain_fail_closed():
    original_state = bot.BTCContext._state
    original_cache = bot.OrderedDict(bot._V702_A17_BEARISH_SEVERITY_CACHE)
    try:
        bot.BTCContext._state = "OK"
        bot._V702_A17_BEARISH_SEVERITY_CACHE.clear()
        df15, df4 = _frames(severe_drop=True, lower_lows=False)
        severity = bot.V425BearishSeverity.classify("BEARISH", df15, df4)
        assert severity == bot.V425BearishSeverity.CRASH
        assert bot.STATS["v702_a43_bearish_last"]["cause"] == "15M_DROP_AT_CRASH_THRESHOLD"
        assert bot.V425BearishSeverity.allows_new_long(severity) is False
        assert bot.V425BearishSeverity.classify("BEARISH", None, df4) == bot.V425BearishSeverity.CRASH
        assert bot.V425BearishSeverity.allows_new_long("UNKNOWN") is False
        bot.BTCContext._state = "CRASH"
        bot._V702_A17_BEARISH_SEVERITY_CACHE.clear()
        df15_mild, df4_mild = _frames(severe_drop=False, lower_lows=False)
        assert bot.V425BearishSeverity.classify("BEARISH", df15_mild, df4_mild) == bot.V425BearishSeverity.CRASH
        assert bot.STATS["v702_a43_bearish_last"]["cause"] == "BTC_CONTEXT_HARD_CRASH"
    finally:
        bot.BTCContext._state = original_state
        bot._V702_A17_BEARISH_SEVERITY_CACHE.clear()
        bot._V702_A17_BEARISH_SEVERITY_CACHE.update(original_cache)


def test_a43_exact_orderbook_zero_sentinel_uses_only_fresh_trusted_book():
    book = {"bids": [[100.0, 2.0], [99.9, 2.0]], "asks": [[100.1, 1.0], [100.2, 1.0]]}
    fresh = {
        "v703_route_orderbook_source": "V702_A9_PREFETCH_EXACT_BOOK",
        "v702_a9_orderbook_prefetch_status": "FETCHED_FRESH",
        "depth_ratio": 0.0,
        "book_ts": bot.WALL_NOW(),
    }
    evidence = bot._v702_a43_derive_depth_ratio_from_exact_book(fresh, None, book)
    assert evidence["valid"] and evidence["trusted_source"], evidence
    assert evidence["reason"] == "derived_from_fresh_exact_book", evidence
    assert evidence["depth_ratio"] > 1.0 and evidence["required_notional_usdt"] > 0.0, evidence

    stale = dict(fresh, book_ts=bot.WALL_NOW() - bot.CONFIG["V702_A43_DEPTH_EXACT_BOOK_MAX_AGE_SEC"] - 30.0)
    stale_result = bot._v702_a43_derive_depth_ratio_from_exact_book(stale, None, book)
    assert stale_result["trusted_source"] and not stale_result["valid"]
    assert stale_result["reason"] == "exact_book_stale_or_future"

    untrusted = dict(fresh, v703_route_orderbook_source="", book_ts=bot.WALL_NOW())
    untrusted_result = bot._v702_a43_derive_depth_ratio_from_exact_book(untrusted, None, book)
    assert not untrusted_result["trusted_source"] and not untrusted_result["valid"]


def test_a43_depth_diagnostic_is_numeric_and_never_claims_to_change_decision():
    keys = ("v702_a43_depth_observation_count", "v702_a43_depth_reject_count", "v702_a43_depth_last", "v702_a43_depth_history")
    saved = {k: bot.STATS.get(k) for k in keys}
    had = {k: k in bot.STATS for k in keys}
    try:
        row = bot._v702_a43_record_depth_observation(
            "DEPTH/USDT", "MID", 0.75,
            {"source": "TEST_BOOK", "bid_notional_usdt": 60.0, "required_notional_usdt": 80.0,
             "book_age_sec": 2.0, "reason": "derived_from_fresh_exact_book"},
            1.0, "liquidity.depth_ratio_below_floor", "prequal",
        )
        assert row["depth_ratio"] == 0.75 and row["floor"] == 1.0
        assert row["bid_notional_usdt"] == 60.0 and row["required_notional_usdt"] == 80.0
        assert row["decision_changed"] is False and row["recorder_changed_decision"] is False and row["telemetry_only"] is True
        assert row["admission_input_derived"] is True
        assert bot.STATS["v702_a43_depth_reject_count"] >= 1
    finally:
        for k in keys:
            if had[k]: bot.STATS[k] = saved[k]
            else: bot.STATS.pop(k, None)


def test_a43_heartbeat_surfaces_numeric_crash_and_depth_context():
    keys = ("v702_a43_bearish_last", "v702_a43_depth_last")
    saved = {k: bot.STATS.get(k) for k in keys}
    had = {k: k in bot.STATS for k in keys}
    try:
        bot.STATS[keys[0]] = {"severity": "BEARISH_STRESSED", "cause": "BREAKDOWN_ONLY_CLASSIFIED_STRESSED",
                               "drop_pct": -0.7, "atr_ratio": 1.1, "breakdown": True,
                               "btc_context_state": "OK", "decision_changed_from_a42": True, "ts": bot.WALL_NOW()}
        bot.STATS[keys[1]] = {"symbol": "DEPTH/USDT", "tier": "MID", "depth_ratio": 0.75,
                              "floor": 1.0, "source": "EXACT_BOOK", "book_age_sec": 2.0,
                              "bid_notional_usdt": 60.0, "required_notional_usdt": 80.0,
                              "derived": True, "admission_input_derived": True,
                              "reason": "liquidity.depth_ratio_below_floor"}
        line = bot._V702R28TelegramDigest._heartbeat_line("state=FULL_LIVE_RUNNING funnel=0/0/0/0")
        assert "A43_BEARISH=" in line and "drop:-0.7" in line and "BREAKDOWN_ONLY_CLASSIFIED_STRESSED" in line and "deltaA42:1" in line
        assert "A43_DEPTH=" in line and "ratio:0.75" in line and "floor:1.0" in line and "bid:60.0" in line and "req:80.0" in line and "derived:1" in line
        assert "bypass:false" in line
    finally:
        for k in keys:
            if had[k]: bot.STATS[k] = saved[k]
            else: bot.STATS.pop(k, None)


def test_a43_release_contract_and_manifest_hash_are_coherent():
    assert bot.V702_A43_CANONICAL_REVISION.startswith(bot.V702_A42_CANONICAL_REVISION + "-A43-")
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A43_CANONICAL_REVISION + "-A44-")
    assert bot.STATS["v702_a43_crash_depth_self_test"]["pass"] is True
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False
    assert bot.CONFIG["LONG_ONLY"] and str(bot.CONFIG["MARKET_TYPE"]).upper() == "SPOT"
    assert not bot.CONFIG.get("ENABLE_FUTURES", False)
    manifest = json.loads((ROOT / "FINAL_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["canonical_revision"] == bot.V702_PACKAGE_AUDIT_REVISION
    assert manifest["canonical_source_sha256"] == hashlib.sha256((ROOT / "main.py").read_bytes()).hexdigest()
    assert manifest["archive_contents"] == sorted(manifest["archive_contents"])
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "_v702_a43_derive_depth_ratio_from_exact_book(snap, c, _ob)" in source
    assert "if not math.isfinite(_dr_value) or _dr_value < 0.0:" in source
