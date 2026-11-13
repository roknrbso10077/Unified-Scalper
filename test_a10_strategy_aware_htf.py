"""A10 strategy-aware HTF policy: bounded relief, local proof, unchanged safety."""
from __future__ import annotations
import os
import tempfile
from pathlib import Path
os.environ.setdefault("SCALPER_DB", str(Path(tempfile.gettempdir()) / f"v702-a10-htf-{os.getpid()}.db"))
import main


def _soft_ctx(**overrides):
    snap = {
        "macro_regime": "BULLISH",
        "local_regime": "LOCAL_RECOVERY",
        "htf_state": "NEUTRAL",
        "htf_strength": 40.0,
        "macro_severity": "NORMAL",
        "reclaim": True,
        "higher_low": True,
    }
    snap.update(overrides.pop("snapshot", {}))
    args = {
        "family": "MEAN_REVERSION",
        "strategy_mode": "MEAN_REVERSION",
        "regime": "BULLISH",
        "local_regime": "LOCAL_RECOVERY",
        "severity": "NORMAL",
        "htf_state": "NEUTRAL",
        "htf_strength": 40.0,
        "snapshot": snap,
    }
    args.update(overrides)
    return args


def test_pullback_uses_bounded_context_floor_not_global_relief():
    assert main._v702_htf_policy_name("PULLBACK", "PULLBACK", {}) == "CONTEXTUAL_FLOOR"
    assert main._v702_effective_htf_floor("PULLBACK", "PULLBACK", "BULLISH", "LOCAL_BULLISH", 48.0) == 45.0
    ok, ctx = main._v702_soft_htf_alignment_allowed(
        family="PULLBACK", strategy_mode="PULLBACK", regime="BULLISH",
        local_regime="LOCAL_BULLISH", severity="NORMAL", htf_state="NEUTRAL",
        htf_strength=45.0, snapshot={"macro_regime":"BULLISH", "local_regime":"LOCAL_BULLISH",
                                    "htf_state":"NEUTRAL", "htf_strength":45.0})
    assert ok and ctx["alignment_claimed"] is False


def test_pullback_below_context_floor_still_fails():
    ok, ctx = main._v702_soft_htf_alignment_allowed(
        family="PULLBACK", strategy_mode="PULLBACK", regime="BULLISH",
        local_regime="LOCAL_BULLISH", severity="NORMAL", htf_state="NEUTRAL",
        htf_strength=44.9, snapshot={"macro_regime":"BULLISH", "local_regime":"LOCAL_BULLISH",
                                    "htf_state":"NEUTRAL", "htf_strength":44.9})
    assert not ok and ctx["reason"] == "contextual_htf_floor_not_met"


def test_mtf_pullback_and_breakout_retain_strict_htf_floors():
    assert main._v702_effective_htf_floor("MTF_PULLBACK", "MTF_PULLBACK", "BULLISH", "LOCAL_BULLISH", 58.0) == 58.0
    assert main._v702_effective_htf_floor("BREAKOUT_CONTINUATION", "BREAKOUT_CONTINUATION", "BULLISH", "LOCAL_BULLISH", 62.0) == 62.0
    ok, ctx = main._v702_soft_htf_alignment_allowed(**_soft_ctx(family="BREAKOUT_CONTINUATION", strategy_mode="BREAKOUT_CONTINUATION"))
    assert not ok and ctx["reason"] == "family_requires_strict_alignment"


def test_mean_reversion_allowed_in_bullish_only_with_local_confirmation():
    ok, reason, _ = main.FamilyPolicyLayer.regime_policy_detail(
        "MEAN_REVERSION", "BULLISH", strategy_mode="MEAN_REVERSION",
        local_regime="LOCAL_BULLISH", market_phase="REVERSAL", severity="NORMAL", strategy_style="SCALP")
    assert ok and reason == "allow"
    ok, reason, _ = main.FamilyPolicyLayer.regime_policy_detail(
        "MEAN_REVERSION", "BULLISH", strategy_mode="MEAN_REVERSION",
        local_regime="", market_phase="REVERSAL", severity="NORMAL", strategy_style="SCALP")
    assert not ok and reason == "local"


def test_mean_reversion_bearish_macro_requires_local_recovery():
    ok, reason, _ = main.FamilyPolicyLayer.regime_policy_detail(
        "MEAN_REVERSION", "BEARISH", strategy_mode="MEAN_REVERSION",
        local_regime="LOCAL_BULLISH", market_phase="REVERSAL", severity="BEARISH_NORMAL", strategy_style="SCALP")
    assert not ok and reason == "local"
    ok, reason, _ = main.FamilyPolicyLayer.regime_policy_detail(
        "MEAN_REVERSION", "BEARISH", strategy_mode="MEAN_REVERSION",
        local_regime="LOCAL_RECOVERY", market_phase="REVERSAL", severity="BEARISH_NORMAL", strategy_style="SCALP")
    assert ok and reason == "allow"


def test_soft_htf_relief_requires_a_known_state_strength_and_local_confirmation():
    ok, ctx = main._v702_soft_htf_alignment_allowed(**_soft_ctx())
    assert ok and ctx["allowed"] and ctx["alignment_claimed"] is False
    ok, ctx = main._v702_soft_htf_alignment_allowed(**_soft_ctx(local_regime="", snapshot={"local_regime":"", "reclaim":False, "higher_low":False}))
    assert not ok and ctx["reason"] == "local_confirmation_missing"
    ok, ctx = main._v702_soft_htf_alignment_allowed(**_soft_ctx(htf_state="UNKNOWN", snapshot={"htf_state":"UNKNOWN"}))
    assert not ok and ctx["reason"] == "htf_state_unverifiable"
    ok, ctx = main._v702_soft_htf_alignment_allowed(**_soft_ctx(htf_strength=20.0, snapshot={"htf_strength":20.0}))
    assert not ok and ctx["reason"] == "htf_context_too_weak"
    ok, ctx = main._v702_soft_htf_alignment_allowed(**_soft_ctx(severity="CRASH", snapshot={"macro_severity":"CRASH"}))
    assert not ok and ctx["reason"] == "bearish_crash_guard"


def test_bearish_htf_allows_only_proven_local_recovery_for_reversal_families():
    ok, ctx = main._v702_soft_htf_alignment_allowed(**_soft_ctx(
        regime="BEARISH", local_regime="LOCAL_RECOVERY", severity="BEARISH_NORMAL",
        htf_state="BEARISH", snapshot={"macro_regime":"BEARISH", "local_regime":"LOCAL_RECOVERY",
                                       "macro_severity":"BEARISH_NORMAL", "htf_state":"BEARISH",
                                       "htf_strength":40.0, "reclaim":True, "higher_low":True}))
    assert ok and ctx["alignment_claimed"] is False
    ok, ctx = main._v702_soft_htf_alignment_allowed(**_soft_ctx(
        family="PULLBACK", strategy_mode="PULLBACK", regime="BULLISH", local_regime="LOCAL_BULLISH",
        htf_state="BEARISH", htf_strength=48.0,
        snapshot={"macro_regime":"BULLISH", "local_regime":"LOCAL_BULLISH", "htf_state":"BEARISH", "htf_strength":48.0}))
    assert not ok and ctx["reason"] == "bearish_htf_requires_reversal_confirmation"


def test_spot_long_only_size_slots_and_forbidden_assets_are_unchanged():
    cfg = main.CONFIG
    assert cfg.get("LONG_ONLY", True) is True
    assert cfg.get("ALLOW_SHORT", False) is False
    assert cfg.get("ALLOW_SHORTS", False) is False
    assert str(cfg.get("TRADING_SIDE", "LONG")).upper() == "LONG"
    assert str(cfg.get("MARKET_TYPE", "SPOT")).upper() == "SPOT"
    assert cfg.get("ENABLE_FUTURES", False) is False
    assert cfg.get("FUTURES_ENABLED", False) is False
    assert int(cfg.get("MAX_CONCURRENT_TRADES", 2)) == 2
    assert float(cfg.get("FIXED_POSITION_SIZE_USDT", 75.0)) == 75.0
    assert float(cfg.get("MAX_POSITION_SIZE_USDT", 75.0)) == 75.0
    assert not bool(cfg.get("V702_INTRADAY_SHADOW_LIVE_ENABLE", True))
    assert main.FINAL_CANONICAL_RUNTIME.get("hard_gate_bypass", False) is False
    for base in ("AERO", "BNB", "CAKE", "ETHFI", "PUMP"):
        blocked, _reason = main._v587_is_forbidden_coin(f"{base}/USDT")
        assert blocked, base


def test_macro_context_enforces_shared_240_row_operational_floor():
    values = [100.0 + i * 1.25 for i in range(260)]
    frame = main.pd.DataFrame({
        "close": values,
        "high": [x + 1.0 for x in values],
        "low": [x - 1.0 for x in values],
    })
    # 240 total rows only provide 239 candles before iloc[-2]; require 241 total rows.
    short_regime, short_pct, short_reason = main._v702_r36_macro_context(frame.iloc[:240].copy())
    assert short_regime == "UNKNOWN"
    assert short_pct is None
    assert short_reason == "macro_history_insufficient"

    valid_regime, valid_pct, valid_reason = main._v702_r36_macro_context(frame.iloc[:241].copy())
    assert valid_regime in {"BULLISH", "BEARISH", "NEUTRAL"}
    assert valid_pct is not None
    assert valid_reason == ""

    from types import SimpleNamespace
    candidate = SimpleNamespace(family="PULLBACK", strategy_mode="PULLBACK", features_snapshot={})
    context = main._v455_prequal_context(candidate, {
        "macro_regime": "UNKNOWN", "snapshot_id": "offline-test-snapshot",
        "v703_r36_snapshot_coherent": False, "v702_r36_context_blocked": True,
        "v702_r36_context_block_reason": "macro_history_insufficient",
    })
    assert context["snapshot_id"] == "offline-test-snapshot"
    assert context["snapshot_coherent"] is False
    assert context["macro_context_blocked"] is True
    assert context["macro_context_block_reason"] == "macro_history_insufficient"
