"""A7 regression tests for bounded MICRO handoff and operator control hardening."""
from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

# Isolate import-time schema/self-tests from the package's empty reference DB.
os.environ["SCALPER_DB"] = os.path.join(tempfile.gettempdir(), f"v702-a7-tests-{os.getpid()}.db")
import main


def _candidate(symbol="MCR/USDT", score=80.0, family="PULLBACK"):
    now = main.WALL_NOW()
    features = {
        "quote_vol_24h": 1_200_000.0,
        "spread_pct": 0.10,
        "volume_ratio": 1.20,
        "structure_confidence": 80.0,
        "structure_quality": 80.0,
        "chase_atr": 0.20,
        "depth_ratio": 0.0,
    }
    return SimpleNamespace(
        symbol=symbol,
        family=family,
        strategy_mode=family,
        strategy_style="SCALP",
        side="long",
        generated_at_ms=int(now * 1000),
        engine_score=float(score),
        entry_ref=1.0,
        sl_price=0.99,
        tp1_rr=2.0,
        tp2_rr=3.0,
        tp3_rr=4.0,
        chase_atr=0.20,
        features_snapshot=features,
    )


def _snapshot(candidate, quote_volume=1_200_000.0, spread=0.10, include_book=True):
    now = main.WALL_NOW()
    snap = {
        "symbol": candidate.symbol,
        "tier": "MICRO",
        "quote_vol_24h": float(quote_volume),
        "spread_pct": float(spread),
        "spread_ts": now,
        "orderbook_ts": now,
        "depth_ratio": 0.0,
        "volume_ratio": 1.20,
        "structure_confidence": 80.0,
        "structure_quality": 80.0,
    }
    if include_book:
        snap["orderbook"] = {
            "bids": [[1.00, 2000.0], [0.99, 1000.0]],
            "asks": [[1.01, 500.0], [1.02, 200.0]],
        }
    return snap


def _auth_message(chat_id, sender_id, chat_type="private", is_bot=False):
    return {
        "chat": {"id": chat_id, "type": chat_type},
        "from": {"id": sender_id, "is_bot": is_bot},
    }


def test_a7_telegram_private_owner_allowed_but_wrong_sender_denied(monkeypatch):
    monkeypatch.setitem(main.ENV, "TELEGRAM_CHAT", "12345")
    monkeypatch.delenv("TELEGRAM_ALLOWED_USER_IDS", raising=False)
    assert main.TelegramCommandController._authorized(_auth_message(12345, 12345)) is True
    assert main.TelegramCommandController._authorized(_auth_message(12345, 99999)) is False
    assert main.TelegramCommandController._authorized(_auth_message(12345, 12345, is_bot=True)) is False


def test_a7_telegram_group_requires_allowlisted_sender(monkeypatch):
    monkeypatch.setitem(main.ENV, "TELEGRAM_CHAT", "-100555")
    monkeypatch.delenv("TELEGRAM_ALLOWED_USER_IDS", raising=False)
    msg = _auth_message(-100555, 456, chat_type="supergroup")
    assert main.TelegramCommandController._authorized(msg) is False
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "123, 456;789")
    assert main.TelegramCommandController._authorized(msg) is True
    assert main.TelegramCommandController._authorized(_auth_message(-100555, 999, chat_type="supergroup")) is False


def test_a7_micro_handoff_passes_only_with_complete_book_spread_fee_and_score():
    c = _candidate()
    snap = _snapshot(c)
    ok, reason, proof = main._v702_a7_micro_handoff_evidence(c, snap, tier="MICRO", record=False)
    assert ok is True
    assert reason == "PASS:BOOK_SPREAD_FEE_SCORE"
    assert all(proof[k] for k in ("verified", "book_pass", "spread_pass", "fee_pass", "score_pass"))
    assert proof["quote_volume_24h"] == 1_200_000.0
    assert proof["score_floor"] >= 70.0


def test_a7_micro_handoff_fails_closed_on_missing_book():
    c = _candidate()
    ok, reason, _ = main._v702_a7_micro_handoff_evidence(c, _snapshot(c, include_book=False), tier="MICRO")
    assert ok is False
    assert reason == "orderbook_missing"


def test_a7_micro_handoff_rejects_score_below_70_even_in_pilot():
    c = _candidate(score=69.9)
    ok, reason, _ = main._v702_a7_micro_handoff_evidence(c, _snapshot(c), tier="MICRO")
    assert ok is False
    assert reason == "score_below_micro_handoff_floor"


def test_a7_micro_handoff_rejects_out_of_band_quote_volume_and_forbidden_assets():
    c = _candidate()
    ok, reason, _ = main._v702_a7_micro_handoff_evidence(c, _snapshot(c, quote_volume=3_000_000.0), tier="MICRO")
    assert ok is False
    assert reason == "outside_micro_quote_band"
    forbidden = _candidate(symbol="AERO/USDT")
    ok, reason, _ = main._v702_a7_micro_handoff_evidence(forbidden, _snapshot(forbidden), tier="MICRO")
    assert ok is False
    assert reason == "forbidden_asset"


def test_a7_micro_handoff_does_not_bypass_fee_economics():
    c = _candidate()
    with patch.object(main.CompositeRankingEngine, "_fee_viable", return_value=False):
        ok, reason, _ = main._v702_a7_micro_handoff_evidence(c, _snapshot(c), tier="MICRO")
    assert ok is False
    assert reason == "fee_unviable"


def test_a7_family_tier_allows_micro_only_with_live_verified_proof():
    c = _candidate()
    snap = _snapshot(c)
    ok, _, proof = main._v702_a7_micro_handoff_evidence(c, snap, tier="MICRO")
    assert ok
    features = dict(c.features_snapshot)
    features["v702_a7_micro_handoff"] = proof
    assert main._v689_tier_allowed("PULLBACK", "PULLBACK", "MICRO", 0.80, features) is True
    assert main._v689_tier_allowed("PULLBACK", "PULLBACK", "MICRO", 0.80, {}) is False


def test_a7_heartbeat_displays_entry_root_and_micro_funnel():
    original = dict(main.STATS)
    try:
        main.STATS["v702_a7_micro_eligible_after_quote_filter"] = 7
        main.STATS["v702_a7_micro_orderbook_pass"] = 3
        main.STATS["v702_a7_micro_fee_viable"] = 2
        main.STATS["v702_selected_route_last"] = {
            "ts": main.WALL_NOW(), "reason": "liquidity.below_tier", "stage": "prequal", "root": "LIQUIDITY"
        }
        line = main._V702R28TelegramDigest._heartbeat_line("Heartbeat state=FULL_LIVE_RUNNING")
        assert "ENTRY_BLOCK_ROOT=LIQUIDITY" in line
        assert "MICRO_ELIG/OB_PASS/FEE_OK=7/3/2" in line
    finally:
        main.STATS.clear()
        main.STATS.update(original)


def test_a7_heartbeat_prefers_current_entry_status_over_stale_blocker_cache():
    original = dict(main.STATS)
    try:
        stale_ts = float(main.WALL_NOW()) - 3600.0
        main.STATS["v702_selected_route_last"] = {
            "ts": stale_ts, "reason": "liquidity.below_tier", "stage": "prequal", "root": "LIQUIDITY"
        }
        main.STATS["v699_live_entry_status"] = "BLOCKED:LIQUIDITY"
        main.STATS["v699_live_entry_status_ts"] = stale_ts
        line = main._V702R28TelegramDigest._heartbeat_line(
            "Heartbeat state=FULL_LIVE_RUNNING ENTRY_STATUS=BLOCKED:STRUCTURE"
        )
        assert "ENTRY_BLOCK_ROOT=STRUCTURE age=unknown" in line

        # A generic readiness state must not inherit an old specific rejection.
        line = main._V702R28TelegramDigest._heartbeat_line(
            "Heartbeat state=FULL_LIVE_RUNNING ENTRY_STATUS=BLOCKED:NO_LIVE_READY"
        )
        assert "ENTRY_BLOCK_ROOT=NONE age=unknown" in line
    finally:
        main.STATS.clear()
        main.STATS.update(original)


def test_a7_digest_build_observer_identity_is_preserved_for_release_contract():
    current = getattr(main._V702R28TelegramDigest.build, "__func__", None)
    observer = getattr(main, "_v702_digest_build_observed", None)
    # A44 additively wraps the A7 observer to prioritize the active latch and
    # partition the digest without pre-truncation; the A7 observer remains the
    # directly delegated implementation rather than being bypassed.
    a44_wrapper = getattr(main, "_v702_a44_build_digest", None)
    a44_wrapper_func = getattr(a44_wrapper, "__func__", a44_wrapper)
    assert current is observer or (
        current is a44_wrapper_func
        and getattr(main, "_V702_A44_OLD_BUILD", None) is observer
    )
    assert getattr(main._V702R28TelegramDigest._heartbeat_line, "__func__", None).__name__ == "_v702_a7_heartbeat_line"


def test_a7_canonical_config_validator_confirms_safety_invariants():
    assert main.validate_config() is True
    result = main.STATS.get("v702_a7_final_validation") or {}
    assert result.get("pass") is True
    assert result.get("hard_gate_bypass") is False
    assert not result.get("failed")
