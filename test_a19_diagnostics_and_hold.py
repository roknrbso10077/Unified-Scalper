"""A19 regressions: exact candidate attribution, root-cause MICRO diagnostics, and live-entry hold."""
from __future__ import annotations

import asyncio
import os
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import main as bot


def _candidate(**overrides):
    fields = dict(
        symbol="BTC/USDT", side="long", family="PULLBACK", strategy_mode="PULLBACK",
        generated_at_ms=1770000000123, engine_score=0.80, entry_ref=100.0,
        sl_price=98.0, tp1_rr=1.0, tp2_rr=2.0, tp3_rr=3.0,
        features_snapshot={},
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_a19_candidate_ref_matches_knowledge_outcome_payload():
    candidate = _candidate()
    ref = bot._v702_a19_candidate_ref(candidate)
    raw, _reviewed, _grade, _ctx = bot.KnowledgeOutcomeLedger._derive(candidate, {})
    import hashlib
    payload = "|".join([
        candidate.symbol, candidate.family, str(candidate.generated_at_ms),
        f"{candidate.entry_ref:.16g}", f"{candidate.sl_price:.16g}",
        f"{candidate.tp1_rr:.8f}", f"{candidate.tp2_rr:.8f}", f"{candidate.tp3_rr:.8f}", f"{raw:.6f}",
    ])
    assert ref == hashlib.sha256(payload.encode()).hexdigest()[:40]
    assert len(ref) == 40


def test_a19_micro_handoff_reports_specific_reason_without_weakening_gate():
    candidate = _candidate(features_snapshot={})
    # Has enough MICRO quote volume and score, but no verified spread/book proof.
    ok = bot._v702_a7_micro_handoff_allowed(candidate, {"symbol": "BTC/USDT", "quote_vol_24h": 2_000_000, "tier": "MICRO"}, "MICRO")
    diag = bot.STATS.get("v702_a19_micro_handoff_last", {})
    assert not ok
    assert diag.get("reason") == "spread_missing"
    assert diag.get("candidate_ref") == bot._v702_a19_candidate_ref(candidate)
    assert bot.CONFIG.get("MIN_LIVE_SCORE", 70.0) >= 70.0


def test_a19_non_allowlisted_family_is_rejected_without_per_candidate_handoff_record():
    candidate = _candidate(family="OPPORTUNITY_SCOUT", strategy_mode="OPPORTUNITY_SCOUT")
    old_last = bot.STATS.get("v702_a19_micro_handoff_last")
    old_skipped = int(bot.STATS.get("v702_a19_micro_handoff_skipped_non_allowlisted", 0) or 0)
    try:
        assert bot._v702_a7_micro_handoff_allowed(
            candidate, {"symbol": candidate.symbol, "tier": "MICRO"}, "MICRO"
        ) is False
        assert bot.STATS.get("v702_a19_micro_handoff_last") == old_last
        assert int(bot.STATS.get("v702_a19_micro_handoff_skipped_non_allowlisted", 0) or 0) == old_skipped + 1
        assert bot.STATS.get("v702_a7_micro_handoff_last_block_reason") == "family_not_allowlisted"
    finally:
        if old_last is None:
            bot.STATS.pop("v702_a19_micro_handoff_last", None)
        else:
            bot.STATS["v702_a19_micro_handoff_last"] = old_last
        bot.STATS["v702_a19_micro_handoff_skipped_non_allowlisted"] = old_skipped


def test_a19_shadow_attribution_requires_exact_ref_and_a_blocking_route():
    candidate = _candidate()
    ref = bot._v702_a19_candidate_ref(candidate)
    old = bot.STATS.get("v702_selected_route_last")
    old_gap = bot.STATS.get("v702_a7_shadow_live_gap_last")
    old_unmatched_gap = bot.STATS.get("v702_a7_shadow_live_gap_unmatched_last")
    old_progress = bot.STATS.get("v702_candidate_route_progress_history")
    old_route_history = bot.STATS.get("v702_selected_route_history")
    now = time.time()
    try:
        # A builder block alone is insufficient. Inject exact-ref historical evidence
        # that this same candidate had previously reached QUEUE/PRESEND.
        bot.STATS["v702_candidate_route_progress_history"] = [{
            "symbol": candidate.symbol, "family": candidate.family, "candidate_ref": ref,
            "stage": "queued", "cycle_id": int(bot.STATS.get("v681_runtime_cycle_id", 0) or 0), "ts": now,
        }]
        bot.STATS["v702_selected_route_history"] = []
        bot.STATS["v702_selected_route_last"] = {
            "symbol": candidate.symbol, "family": candidate.family,
            "candidate_ref": ref, "stage": "builder_block", "reason": "post_queue_execution_block",
            "cycle_id": int(bot.STATS.get("v681_runtime_cycle_id", 0) or 0), "ts": now,
        }
        bot._V702R28TelegramDigest.capture(
            "shadow",
            f"<b>KNOWLEDGE SHADOW OUTCOME</b>\n<b>{candidate.symbol}</b> | {candidate.family}\n"
            f"MFE: +1.42R | MAE: -1.70R\nCandidateRef: {ref}\nResearch telemetry only",
        )
        matched = bot.STATS.get("v702_a7_shadow_live_gap_last", {})
        assert matched.get("same_candidate_attribution") is True
        assert matched.get("reason") == "post_queue_execution_block"

        # Same symbol/ref and a builder blocker without prior PRESEND/QUEUE evidence
        # remains an unmatched diagnostic and must not refresh the live gap alert.
        bot.STATS["v702_candidate_route_progress_history"] = []
        bot.STATS["v702_selected_route_last"] = {
            "symbol": candidate.symbol, "family": candidate.family,
            "candidate_ref": ref, "stage": "builder_block", "reason": "builder_block_before_presend",
            "cycle_id": int(bot.STATS.get("v681_runtime_cycle_id", 0) or 0), "ts": time.time(),
        }
        bot._V702R28TelegramDigest.capture(
            "shadow",
            f"<b>KNOWLEDGE SHADOW OUTCOME</b>\n<b>{candidate.symbol}</b> | {candidate.family}\n"
            f"MFE: +1.42R | MAE: -1.70R\nCandidateRef: {ref}\nResearch telemetry only",
        )
        no_progress = bot.STATS.get("v702_a7_shadow_live_gap_unmatched_last", {})
        assert no_progress.get("reason") == "candidate_never_reached_presend_queue"
        assert bot.STATS.get("v702_a7_shadow_live_gap_last", {}).get("candidate_ref") == ref

        bot.STATS["v702_selected_route_last"] = {
            "symbol": candidate.symbol, "family": candidate.family,
            "candidate_ref": "0" * 40, "stage": "builder_block", "reason": "different_candidate",
            "cycle_id": int(bot.STATS.get("v681_runtime_cycle_id", 0) or 0), "ts": time.time(),
        }
        bot._V702R28TelegramDigest.capture(
            "shadow",
            f"<b>KNOWLEDGE SHADOW OUTCOME</b>\n<b>{candidate.symbol}</b> | {candidate.family}\n"
            f"MFE: +1.42R | MAE: -1.70R\nCandidateRef: {ref}\nResearch telemetry only",
        )
        unmatched = bot.STATS.get("v702_a7_shadow_live_gap_unmatched_last", {})
        assert unmatched.get("same_candidate_attribution") is False
        assert unmatched.get("reason") == "candidate_ref_mismatch"
        # An unmatched symbol/candidate must not overwrite a verified gap or
        # produce a live SHADOW_LIVE_GAP heartbeat alert.
        active_gap = bot.STATS.get("v702_a7_shadow_live_gap_last", {})
        assert active_gap.get("same_candidate_attribution") is True
        assert active_gap.get("candidate_ref") == ref
        heartbeat = bot._V702R28TelegramDigest._heartbeat_line("Heartbeat state=FULL_LIVE_RUNNING trades=0 funnel=0/0/0/0")
        assert "SHADOW_LIVE_GAP=" in heartbeat
    finally:
        if old is None:
            bot.STATS.pop("v702_selected_route_last", None)
        else:
            bot.STATS["v702_selected_route_last"] = old
        if old_gap is None:
            bot.STATS.pop("v702_a7_shadow_live_gap_last", None)
        else:
            bot.STATS["v702_a7_shadow_live_gap_last"] = old_gap
        if old_unmatched_gap is None:
            bot.STATS.pop("v702_a7_shadow_live_gap_unmatched_last", None)
        else:
            bot.STATS["v702_a7_shadow_live_gap_unmatched_last"] = old_unmatched_gap
        if old_progress is None:
            bot.STATS.pop("v702_candidate_route_progress_history", None)
        else:
            bot.STATS["v702_candidate_route_progress_history"] = old_progress
        if old_route_history is None:
            bot.STATS.pop("v702_selected_route_history", None)
        else:
            bot.STATS["v702_selected_route_history"] = old_route_history


def test_a19_explicit_hold_blocks_new_live_buy_before_authorization():
    async def run():
        with patch.dict(os.environ, {
            "UNIFIED_A19_DIAGNOSTIC_ONLY": "1",
            "UNIFIED_LIVE_PILOT_ENABLE": "1",
            "UNIFIED_ALLOW_LIVE_TRADING": "",
        }), patch.object(bot.V702PortfolioDrawdownGuard, "authorize_entry", new=AsyncMock(
            side_effect=AssertionError("authorization/exchange valuation must not run during diagnostic hold")
        )) as auth:
            result = await bot._V702_R39_SUBMIT_ENTRY_GUARD(object(), "BTC/USDT", 1.0, 100.0, is_paper=False)
            return result, auth
    result, auth = asyncio.run(run())
    assert result == (False, None, 0.0)
    auth.assert_not_awaited()
    assert bot.STATS.get("v702_a19_diagnostic_only_effective") is True
    assert bot.STATS.get("last_send_fail_reason") == "a19_diagnostic_only_new_live_entries"


def test_a19_paper_submit_is_not_blocked_by_live_diagnostic_hold():
    # The guard must pass paper orders to the prior submit implementation; only
    # real new BUY authorization is held. The invoked test exchange is local/mock.
    async def run():
        exchange = bot._V516MockExchange("")
        with patch.dict(os.environ, {"UNIFIED_A19_DIAGNOSTIC_ONLY": "1"}):
            return await bot._V702_R39_SUBMIT_ENTRY_GUARD(exchange, "TEST/USDT", 0.1, 100.0, is_paper=True)
    result = asyncio.run(run())
    assert result[0] is True


def test_a19_validator_and_revision_are_canonical():
    report = bot._v702_a19_terminal_self_test()
    assert report["pass"], report
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A21_CANONICAL_REVISION)
    assert report["hard_gate_bypass"] is False
