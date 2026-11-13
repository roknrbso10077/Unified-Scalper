"""A35 regressions: projected HTF must match Builder authority or remain advisory."""
from types import SimpleNamespace

import main as bot


def _candidate(htf_strength=40.0):
    return SimpleNamespace(
        symbol="A35TEST/USDT",
        family="PULLBACK",
        strategy_mode="PULLBACK",
        strategy_style="SCALP",
        entry_ref=100.0,
        rr_ratio=2.0,
        features_snapshot={
            "htf_strength": htf_strength,
            "htf_state": "UNKNOWN",
            "structure_confidence": 82.0,
            "retest_quality_score": 78.0,
            "volume_ratio": 1.2,
            "rs_score_val": 6.0,
            "spread_pct": 0.1,
            "orderbook_imbalance": 0.55,
            "zone_quality_class": "ACCEPTABLE",
            "tier": "MID",
        },
    )


def _projection_snapshot(candidate, *, htf_strength=40.0):
    return {
        "symbol": candidate.symbol,
        "htf_strength": htf_strength,
        "htf_state": "UNKNOWN",
        "structure_confidence": 82.0,
        "retest_quality_score": 78.0,
        "volume_ratio": 1.2,
        "rs_score_val": 6.0,
        "spread_pct": 0.1,
        "orderbook_imbalance": 0.55,
        "tier": "MID",
        "candidate_id": "A35-CANDIDATE",
        "closed_candle_ts": "A35-CANDLE",
        "cycle_id": "A35-CYCLE",
        # Data frame contents are deliberately unused by the monkeypatched grader.
        "df_1h": object(),
    }


def _neutralize_non_htf_modifiers(monkeypatch):
    for key in (
        "V410_MASTER_ENABLE", "V410_D1_BIAS_ENABLE", "V410_BREADTH_ENABLE",
        "V520_PREQUAL_FAKE_BREAK_ENABLE", "V423_FAMILY_ZONE_PENALTY_ENABLE",
        "V423_FAMILY_VOLUME_PENALTY_ENABLE",
    ):
        monkeypatch.setitem(bot.CONFIG, key, False)
    monkeypatch.setattr(
        bot, "_v702_projected_builder_score_floors",
        lambda *args, **kwargs: {"canonical_floor": 70.0, "effective_floor": 76.0},
    )


def test_failed_htf_grade_cannot_become_a_complete_projection_hard_block(monkeypatch):
    _neutralize_non_htf_modifiers(monkeypatch)
    candidate = _candidate(htf_strength=90.0)
    captured = {}

    def grade(_df, label=""):
        return False, "UNKNOWN", 0.0, "insufficient_data"

    def build(**kwargs):
        captured.update(kwargs)
        return 20.0, "C_REJECT", {"reason": "htf_not_passed"}

    monkeypatch.setattr(bot.HTFGrader, "grade", staticmethod(grade))
    monkeypatch.setattr(bot.CompositeScorer, "build", staticmethod(build))
    monkeypatch.setattr(bot, "_V702_R34_PROJECTION_STATUS", {}, raising=False)

    projected = bot._v702_projected_canonical_score(candidate, _projection_snapshot(candidate, htf_strength=90.0))
    status = bot._V702_R34_PROJECTION_STATUS[candidate.symbol]

    assert projected == 20.0
    assert captured["htf_passed"] is False
    assert captured["htf_strength"] == 0.0
    assert status["complete"] is False
    assert "htf_zero_requires_builder_resolver_revalidation" in status["notes"]
    assert bot._v702_exact_route_projection_hard_block_allowed(
        candidate,
        {"cycle_id": "A35-CYCLE", "candidate_id": "A35-CANDIDATE", "candle_ts": "A35-CANDLE"},
        projected,
        76.0,
    ) is False


def test_projected_htf_uses_closed_grader_not_stale_snapshot_number(monkeypatch):
    _neutralize_non_htf_modifiers(monkeypatch)
    candidate = _candidate(htf_strength=40.0)
    captured = {}

    def grade(_df, label=""):
        return True, "STRICT_BULLISH", 93.0, "strict_ok"

    def build(**kwargs):
        captured.update(kwargs)
        return 81.0, "A", {"reason": "ok"}

    monkeypatch.setattr(bot.HTFGrader, "grade", staticmethod(grade))
    monkeypatch.setattr(bot.CompositeScorer, "build", staticmethod(build))
    monkeypatch.setattr(bot, "_V702_R34_PROJECTION_STATUS", {}, raising=False)

    projected = bot._v702_projected_canonical_score(candidate, _projection_snapshot(candidate, htf_strength=40.0))

    assert projected == 81.0
    assert captured["htf_passed"] is True
    assert captured["htf_strength"] == 93.0
    assert captured["htf_state"] == "STRICT_BULLISH"
    # It still cannot be called exact while Builder-only orderbook evidence is absent.
    assert bot._V702_R34_PROJECTION_STATUS[candidate.symbol]["complete"] is False
    assert "orderbook_snapshot_unavailable" in bot._V702_R34_PROJECTION_STATUS[candidate.symbol]["notes"]


def test_htf_zero_without_closed_1h_frame_is_fail_closed_and_incomplete(monkeypatch):
    _neutralize_non_htf_modifiers(monkeypatch)
    candidate = _candidate(htf_strength=95.0)
    captured = {}

    def build(**kwargs):
        captured.update(kwargs)
        return 0.0, "C_REJECT", {"reason": "htf_not_passed"}

    monkeypatch.setattr(bot.CompositeScorer, "build", staticmethod(build))
    monkeypatch.setattr(bot, "_V702_R34_PROJECTION_STATUS", {}, raising=False)
    snapshot = _projection_snapshot(candidate, htf_strength=95.0)
    snapshot.pop("df_1h")

    bot._v702_projected_canonical_score(candidate, snapshot)
    status = bot._V702_R34_PROJECTION_STATUS[candidate.symbol]

    assert captured["htf_passed"] is False
    assert status["complete"] is False
    assert "htf_closed_frame_unavailable" in status["notes"]


def test_a35_terminal_contract_preserves_authority_and_hard_gates():
    report = bot._v702_a35_projection_htf_terminal_self_test()
    assert report["pass"] is True, report
    assert report["checks"]["a35_revision_appends_a34"] is True
    assert report["checks"]["a35_incomplete_projection_preserves_canonical_rank"] is True
    assert report["checks"]["a35_spot_long_only_and_hard_floors_preserved"] is True
    assert report["hard_gate_bypass"] is False
    assert report["live_gates_relaxed"] is False
    assert report["live_network_tested"] is False
    assert report["profitability_verified"] is False
