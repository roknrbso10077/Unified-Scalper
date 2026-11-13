from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd

import main as bot


def _frame(freq: str, periods: int, interval_minutes: int):
    now = pd.Timestamp.now(tz="UTC").floor(freq)
    idx = pd.date_range(end=now, periods=periods, freq=freq, tz="UTC")
    values = [100.0 + i * (0.16 if interval_minutes == 5 else 0.45) for i in range(periods)]
    data = []
    for i, close in enumerate(values):
        op = close - 0.025
        lo = close - 0.12
        hi = close + 0.12
        vol = 100.0 + i
        data.append([op, hi, lo, close, vol])
    return pd.DataFrame(data, index=idx, columns=["open", "high", "low", "close", "volume"])


def _candidate(family="COMPRESSION_EXPANSION", mode=None, style="SCALP", strength=48.0,
               state="NEUTRAL", regime="NEUTRAL"):
    df5 = _frame("5min", 48, 5)
    df15 = _frame("15min", 36, 15)
    fs = {
        "family": family,
        "strategy_mode": mode or family,
        "strategy_style": style,
        "htf_strength": strength,
        "htf_state": state,
        "htf_reason": "family_strength_below_floor",
        "macro_regime": regime,
        "local_regime": "LOCAL_BULLISH",
        "df_5m": df5,
        "df_15m": df15,
        "volume_ratio": 1.35,
        "bos_confirmed": True,
    }
    snap = {
        "df_5m": df5,
        "df_15m": df15,
        "htf_strength": strength,
        "htf_state": state,
        "htf_reason": "family_strength_below_floor",
        "macro_regime": regime,
        "regime": regime,
        "local_regime": "LOCAL_BULLISH",
        "macro_severity": "NORMAL",
        "volume_ratio": 1.35,
        "bos_confirmed": True,
    }
    return SimpleNamespace(family=family, strategy_mode=mode or family, strategy_style=style,
                           features_snapshot=fs, macro_regime=regime, local_regime="LOCAL_BULLISH"), snap


def test_a36_relief_allows_confirmed_neutral_scalp_context_only():
    candidate, snap = _candidate()
    ok, ctx = bot._v702_a36_scalp_htf_relief_allowed(
        candidate, snap, family=candidate.family, strategy_mode=candidate.strategy_mode,
        regime="NEUTRAL", local_regime="LOCAL_BULLISH", severity="NORMAL",
        htf_state="NEUTRAL", htf_strength=48.0, htf_reason="family_strength_below_floor",
    )
    assert ok is True
    assert ctx["applied"] is True
    assert ctx["alignment_claimed"] is False
    assert ctx["score_floor_unchanged"] is True
    assert candidate.features_snapshot["v702_a36_scalp_htf_relief"]["applied"] is True


def test_a36_relief_fails_closed_for_unknown_or_bearish_context():
    candidate, snap = _candidate(state="UNKNOWN")
    ok, ctx = bot._v702_a36_scalp_htf_relief_allowed(
        candidate, snap, family=candidate.family, strategy_mode=candidate.strategy_mode,
        regime="NEUTRAL", local_regime="LOCAL_BULLISH", severity="NORMAL",
        htf_state="UNKNOWN", htf_strength=48.0, htf_reason="",
    )
    assert not ok
    assert ctx["reason"] == "htf_state_not_context_safe"

    candidate, snap = _candidate(regime="BEARISH")
    ok, ctx = bot._v702_a36_scalp_htf_relief_allowed(
        candidate, snap, family=candidate.family, strategy_mode=candidate.strategy_mode,
        regime="BEARISH", local_regime="LOCAL_BULLISH", severity="BEARISH_NORMAL",
        htf_state="NEUTRAL", htf_strength=48.0, htf_reason="family_strength_below_floor",
    )
    assert not ok
    assert ctx["reason"] == "macro_or_severity_not_eligible"


def test_a36_relief_does_not_apply_to_strict_breakout_or_non_scalp():
    candidate, snap = _candidate(family="BREAKOUT_CONTINUATION")
    ok, ctx = bot._v702_a36_scalp_htf_relief_allowed(
        candidate, snap, family=candidate.family, strategy_mode=candidate.strategy_mode,
        regime="NEUTRAL", local_regime="LOCAL_BULLISH", severity="NORMAL",
        htf_state="NEUTRAL", htf_strength=48.0, htf_reason="family_strength_below_floor",
    )
    assert not ok
    assert ctx["reason"] == "family_or_style_not_eligible"

    candidate, snap = _candidate(style="SWING")
    ok, ctx = bot._v702_a36_scalp_htf_relief_allowed(
        candidate, snap, family=candidate.family, strategy_mode=candidate.strategy_mode,
        regime="NEUTRAL", local_regime="LOCAL_BULLISH", severity="NORMAL",
        htf_state="NEUTRAL", htf_strength=48.0, htf_reason="family_strength_below_floor",
    )
    assert not ok


def test_a36_missing_style_does_not_default_to_scalp_relief():
    candidate, snap = _candidate()
    candidate.strategy_style = None
    candidate.features_snapshot.pop("strategy_style", None)
    snap.pop("strategy_style", None)
    ok, ctx = bot._v702_a36_scalp_htf_relief_allowed(
        candidate, snap, family=candidate.family, strategy_mode=candidate.strategy_mode,
        regime="NEUTRAL", local_regime="LOCAL_BULLISH", severity="NORMAL",
        htf_state="NEUTRAL", htf_strength=48.0, htf_reason="family_strength_below_floor",
    )
    assert not ok
    assert ctx["reason"] == "family_or_style_not_eligible"
    assert ctx["style"] == "UNKNOWN"


def test_a36_15m_minimum_counts_closed_rows_not_the_forming_row():
    short = _frame("15min", 24, 15)
    result = bot._v702_a36_local_15m_evidence({"df_15m": short}, {})
    assert not result["verified"]
    assert result["reason"] == "insufficient_15m_history"

    enough = _frame("15min", 25, 15)
    result = bot._v702_a36_local_15m_evidence({"df_15m": enough}, {})
    assert result["verified"] is True, result


def test_a36_15m_duplicate_timestamps_are_rejected():
    frame = _frame("15min", 30, 15)
    idx = list(frame.index)
    idx[-3] = idx[-4]
    frame.index = idx
    result = bot._v702_a36_local_15m_evidence({"df_15m": frame}, {})
    assert not result["verified"]
    assert result["reason"] == "duplicate_15m_timestamps"


def test_a36_pullback_relief_requires_htf_only_failure_and_strong_independent_quality():
    candidate, snap = _candidate(family="PULLBACK", strength=38.0)
    # A reclaim between the previous and latest closed candle creates the fourth
    # independently derived closed-5m signal; stale feature flags alone are not used.
    prev_close = float(snap["df_5m"]["close"].iloc[-3])
    latest_close = float(snap["df_5m"]["close"].iloc[-2])
    candidate.features_snapshot["zone_ref"] = (prev_close + latest_close) / 2.0
    snap["zone_ref"] = candidate.features_snapshot["zone_ref"]
    q = {
        "ok": False, "reason": "htf_below_floor", "htf_strength": 38.0,
        "quality": 88.0, "setup_quality": 86.0, "volume_ratio": 1.45,
        "rs_5m": 0.08, "structure": 80.0, "retest": 76.0, "chase": 0.20,
        "confirmations": 4,
    }
    ok, ctx = bot._v702_a36_pullback_htf_quality_relief_allowed(
        candidate, snap, htf_strength=38.0, htf_state="NEUTRAL",
        htf_reason="family_strength_below_floor", quality_record=q,
    )
    assert ok is True
    assert ctx["score_floor_unchanged"] is True
    assert ctx["values"]["chase"] <= 0.75

    weak_q = dict(q, structure=48.0)
    ok, ctx = bot._v702_a36_pullback_htf_quality_relief_allowed(
        candidate, snap, htf_strength=38.0, htf_state="NEUTRAL",
        htf_reason="family_strength_below_floor", quality_record=weak_q,
    )
    assert not ok


def test_a36_validator_keeps_existing_hard_gates_and_live_score_floor():
    report = bot._v702_a36_terminal_self_test()
    assert report["pass"] is True, report["failed"]
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70.0
    assert bot.CONFIG["V45_TIER_MICRO_MIN_DEPTH_RATIO"] >= 1.90
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False


def test_a36_relief_is_wired_to_active_canonical_builder_and_prequal_without_legacy_replay():
    import inspect
    from pathlib import Path
    # The old exact-policy precheck name is intentionally aliased to the active
    # builder handoff. Verify the effective function, not the shadowed legacy
    # function object that is replaced during module initialization.
    active_builder = bot._v542_exact_policy_precheck
    assert active_builder is bot._v692_builder_precheck
    builder_source = inspect.getsource(active_builder)
    assert "reuse_canonical_prequal" in builder_source
    assert '_terminal_prequal = globals().get("_v702_public_prequal")' in builder_source
    assert "_v692_canonical_prequal" in builder_source

    public_source = inspect.getsource(bot._v702_public_prequal)
    assert "_v702_orig_public_prequal(ranked, _prequal_snap_map)" in public_source
    assert bot._v702_a29_pullback_htf_relief_allowed is bot._v702_a36_a29_htf_relief_wrapper
    assert bot._v587_pullback_quality is bot._v702_a36_v587_pullback_quality_wrapper
    assert bot._v702_soft_htf_alignment_allowed is bot._v702_a36_soft_htf_alignment_wrapper
    canonical_source = inspect.getsource(bot._v692_canonical_prequal)
    package_source = Path(bot.__file__).read_text(encoding="utf-8")
    assert "_v690_tier_allowed" in canonical_source
    # Tier/micro gates are owned by the established base prequalification and
    # order-book authorities, not by the thin recovery wrapper.
    assert callable(bot._v690_tier_allowed)
    assert callable(bot._v702_a7_micro_handoff_evidence)
    assert callable(bot._v702_a7_micro_handoff_allowed)
    assert "_v702_a7_micro_handoff_evidence" in package_source
    assert "liquidity.family_tier_below_floor" in package_source
    assert "liquidity.micro_handoff_unverified" in package_source
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70.0
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False
