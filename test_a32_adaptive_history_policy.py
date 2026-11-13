"""A32 regressions: admit safe short local 4H history without weakening hard gates."""
from datetime import timezone
import time
import main as bot


def _frame(rows, *, rising=False):
    if rising:
        close = [1.0 + i * 0.005 for i in range(rows)]
    else:
        close = [1.0] * rows
    return bot.pd.DataFrame({
        "open": close,
        "high": [x * 1.01 for x in close],
        "low": [x * 0.99 for x in close],
        "close": close,
        "volume": [1000.0] * rows,
    })


def _candidate_frames(n4=52):
    return {
        "df_4h": _frame(n4, rising=True),
        "df_1h": _frame(240, rising=True),
        "df_15m": _frame(350, rising=True),
        "df_5m": _frame(30, rising=True),
    }


def test_a32_is_canonical_and_keeps_risk_and_entry_contracts():
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A35_CANONICAL_REVISION + "-A36-")
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A31_CANONICAL_REVISION + "-A32-")
    assert bot._v702_a32_local_4h_min_closed_candles() == 50
    assert bot.CONFIG["LONG_ONLY"] is True
    assert str(bot.CONFIG["MARKET_TYPE"]).upper() == "SPOT"
    assert not bot.CONFIG.get("ENABLE_FUTURES", False)
    assert not bot.CONFIG.get("ALLOW_SHORT", False)
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70
    assert bot.CONFIG["LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME"] >= 3_000_000
    assert bot.CONFIG["V45_TIER_MICRO_MIN_DEPTH_RATIO"] >= 1.90
    assert bot.CONFIG["MIN_TP1_TO_FEE_RATIO"] >= 2.5
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False


def test_a32_admits_52_rows_and_rejects_49_without_padding():
    ok, reason = bot._mse_candidate_scan_precheck(_candidate_frames(52))
    assert ok and reason == "ok", reason
    short = _candidate_frames(49)
    before = len(short["df_4h"])
    ok, reason = bot._mse_candidate_scan_precheck(short)
    assert not ok and reason == "df_4h:short_rows:got=49,required=50"
    assert len(short["df_4h"]) == before


def test_a32_timestamped_history_requires_50_closed_contiguous_bars():
    pd = bot.pd
    now = pd.Timestamp.now(tz="UTC")
    interval = pd.Timedelta(hours=4)
    current_open = now.floor("4h")
    closed_index = pd.date_range(end=current_open - interval, periods=50, freq="4h", tz="UTC")
    frame = _frame(51, rising=True)
    # 50 genuine closed bars + the currently-forming 4H bar.
    frame.index = closed_index.append(pd.DatetimeIndex([current_open]))
    ok, reason = bot._v702_a32_4h_history_integrity(frame, 50)
    assert ok and reason == "ok", reason

    gap_index = frame.index.delete(10)
    gapped = frame.iloc[:-1].drop(frame.index[10])
    gapped.index = gap_index[:-1]
    ok, reason = bot._v702_a32_4h_history_integrity(gapped, 50)
    assert not ok
    assert reason in {"short_closed_rows:got=49,required=50", "4h_candle_gap_detected"}


def test_a32_short_history_proxy_uses_closed_data_and_caps_confidence():
    snap = {
        "symbol": "SHORT/USDT", "htf_strength": 0.0,
        "htf_state": "UNKNOWN", "htf_reason": "insufficient_data",
        "df_1h": _frame(240, rising=True), "df_4h": _frame(50, rising=True),
    }
    score, source, _ = bot._v702_a32_resolve_htf_strength("SHORT/USDT", snap)
    assert source == "RECOMPUTED_H0"
    assert score is not None and 0 < score <= 50.0, (score, snap)
    assert snap["htf_evidence_class"] == "HTF_LIMITED_HISTORY"
    assert snap["htf_history_minimum"] == 50
    assert snap["htf_history_confidence_cap"] == 50.0

    too_short = dict(snap)
    too_short["df_4h"] = _frame(49, rising=True)
    score, source, _ = bot._v702_a32_resolve_htf_strength("TOO-SHORT/USDT", too_short)
    assert score is None and source == "UNAVAILABLE"


def test_a32_full_history_keeps_existing_ema200_resolver_and_spread_diagnostics():
    snap = {
        "symbol": "FULL/USDT", "htf_strength": 0.0,
        "htf_state": "UNKNOWN", "htf_reason": "insufficient_data",
        "df_1h": _frame(240, rising=True), "df_4h": _frame(210, rising=True),
    }
    score, source, _ = bot._v702_a32_resolve_htf_strength("FULL/USDT", snap)
    assert source == "RECOMPUTED_H0" and score is not None
    assert "htf_history_confidence_cap" not in snap
    bad, bad_reason = bot.tier_spread_hard_ok_v410(0.99, "MICRO")
    good, good_reason = bot.tier_spread_hard_ok_v410(0.25, "MICRO")
    assert not bad and ">ceil=" in bad_reason, bad_reason
    assert good and "<=ceil=" in good_reason, good_reason
