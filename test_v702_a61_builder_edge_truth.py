from __future__ import annotations

import json
import sqlite3

import main as bot


def _memory_ledger(monkeypatch, tmp_path):
    db_path = tmp_path / "a61_edge_truth.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE knowledge_outcomes (
            alert_id TEXT PRIMARY KEY, notes TEXT, entry REAL, sl REAL,
            tp1 REAL, tp2 REAL, tp3 REAL, tp1_rr REAL, tp2_rr REAL,
            tp3_rr REAL, risk_unit REAL, updated_at REAL
        )"""
    )
    conn.execute(
        """INSERT INTO knowledge_outcomes
           (alert_id, notes, entry, sl, tp1, tp2, tp3, tp1_rr, tp2_rr, tp3_rr, risk_unit, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "A61-LEDGER-ROW",
            json.dumps({
                "record_source": "SELECTED_ROUTE_PAPER",
                "paper_fill_price": None,
                "candidate_spread_pct": 0.10,
                "round_trip_cost_pct": 0.20,
            }),
            100.0, 95.0, 105.0, 110.0, 115.0, 1.0, 2.0, 3.0, 5.0, 1.0,
        ),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(
        bot.KnowledgeOutcomeLedger,
        "_connect",
        classmethod(lambda cls: sqlite3.connect(db_path)),
    )
    return db_path


def test_a61_exact_builder_none_overrides_even_an_eligible_stored_shadow():
    key = "A61-EXACT-CANDIDATE-KEY"
    stale_or_prior_shadow = {
        key: {
            "eligible": True,
            "reason": "prior_shadow_pass_must_not_override_builder_none",
            "entry": 100.0,
            "sl": 95.0,
            "tp1": 105.0,
            "tp2": 110.0,
            "tp3": 115.0,
            "spread_pct": 0.1,
            "fee_cost_pct": 0.1,
            "round_trip_cost_pct": 0.2,
        }
    }
    builder_none = {
        "candidate_key": key,
        "candidate_rejection": {"stage": "scorer", "code": "score_below_threshold:61.9<70.0"},
    }

    shadow, status, reason = bot._v702_a60_resolve_paper_shadow(
        stale_or_prior_shadow, key, builder_none
    )
    assert status == "builder_returned_none"
    assert shadow["eligible"] is False
    assert shadow["not_reached"] is True
    assert "score_below_threshold" in reason


def test_a61_builder_none_cannot_make_ledger_row_edge_eligible(monkeypatch, tmp_path):
    db_path = _memory_ledger(monkeypatch, tmp_path)
    shadow, status, _ = bot._v702_a60_resolve_paper_shadow(
        {"A61-EXACT-CANDIDATE-KEY": {"eligible": True}},
        "A61-EXACT-CANDIDATE-KEY",
        {"candidate_key": "A61-EXACT-CANDIDATE-KEY", "candidate_rejection": {"stage": "scorer", "code": "score_below_threshold"}},
    )
    assert status == "builder_returned_none"
    assert bot.KnowledgeOutcomeLedger.annotate_paper_edge(
        "A61-LEDGER-ROW",
        shadow,
        builder_completed=False,
        live_eligible=False,
        builder_reason="builder_returned_none:score_below_threshold",
    ) is True
    with sqlite3.connect(db_path) as conn:
        notes = json.loads(conn.execute(
            "SELECT notes FROM knowledge_outcomes WHERE alert_id=?", ("A61-LEDGER-ROW",)
        ).fetchone()[0])
    assert notes["builder_completed"] is False
    assert notes["shadow_presend_eligible"] is False
    assert notes["paper_edge_eligible"] is False
    assert notes["market_live_eligible"] is False
    assert notes["account_execution_eligible"] is False


def test_a61_same_attempt_shadow_pass_qualifies_market_without_trade_state(monkeypatch, tmp_path):
    db_path = _memory_ledger(monkeypatch, tmp_path)
    attempt_id = "A63-ATTEMPT-EXACT-001"
    candidate_key = "A61-EXACT-CANDIDATE-KEY"
    actual_shadow = {
        "eligible": True, "reached": True,
        "candidate_key": candidate_key,
        "evaluation_attempt_id": attempt_id,
        "reason": "shadow_presend_pass",
        "entry": 100.0, "sl": 95.0, "tp1": 105.0, "tp2": 110.0, "tp3": 115.0,
        "spread_pct": 0.1, "fee_cost_pct": 0.1, "round_trip_cost_pct": 0.2,
    }
    diag = {"candidate_key": candidate_key, "evaluation_attempt_id": attempt_id,
            "reason": "monitor_only_forced_off"}
    resolved, status, _ = bot._v702_a60_resolve_paper_shadow(
        {attempt_id: actual_shadow}, candidate_key, diag,
    )
    assert status == "shadow_evaluated_after_builder_none"
    assert resolved["eligible"] is True
    assert resolved["reached"] is True
    assert bot.KnowledgeOutcomeLedger.annotate_paper_edge(
        "A61-LEDGER-ROW", resolved, builder_completed=True, live_eligible=False,
        builder_reason="monitor_only_forced_off", market_qualification_completed=True,
        trade_state_created=False, evaluation_attempt_id=attempt_id,
    ) is True
    with sqlite3.connect(db_path) as conn:
        notes = json.loads(conn.execute(
            "SELECT notes FROM knowledge_outcomes WHERE alert_id=?", ("A61-LEDGER-ROW",)
        ).fetchone()[0])
    assert notes["builder_completed"] is True
    assert notes["trade_state_created"] is False
    assert notes["evaluation_attempt_id"] == attempt_id
    assert notes["shadow_presend_reached"] is True
    assert notes["shadow_presend_eligible"] is True
    assert notes["paper_edge_eligible"] is True
    assert notes["market_live_eligible"] is True
    assert notes["account_execution_eligible"] is False


def test_a63_shadow_store_rejects_candidate_or_attempt_mismatch():
    key = "CANDIDATE-A"
    aid = "ATTEMPT-A"
    shadow = {"eligible": True, "reached": True, "candidate_key": key,
              "evaluation_attempt_id": aid, "reason": "shadow_pass"}
    wrong_candidate, status1, _ = bot._v702_a60_resolve_paper_shadow(
        {aid: shadow}, "CANDIDATE-B", {"candidate_key": "CANDIDATE-B", "evaluation_attempt_id": aid}
    )
    wrong_attempt, status2, _ = bot._v702_a60_resolve_paper_shadow(
        {aid: shadow}, key, {"candidate_key": key, "evaluation_attempt_id": "ATTEMPT-B"}
    )
    assert status1 != "shadow_evaluated"
    assert wrong_candidate.get("eligible") is False
    assert status2 != "shadow_evaluated"
    assert wrong_attempt.get("eligible") is False


def test_a61_self_test_and_release_identity():
    assert bot.V702_FINAL_CANONICAL_RELEASE == "UNIFIED-SCALPER-V702-A63-CANONICAL-FINAL"
    report = bot._v702_a61_self_test()
    assert report["pass"] is True, report.get("failed")
    assert report["live_authority"] is False
    assert report["hard_gate_bypass"] is False
    assert report["live_gates_relaxed"] is False
    assert report["production_decision"] == "NO_GO_UNATTENDED_LIVE"
