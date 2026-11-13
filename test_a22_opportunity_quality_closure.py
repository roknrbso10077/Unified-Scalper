"""A22 regression tests: remove provisional TP1 starvation without weakening final gates."""
from pathlib import Path
from unittest.mock import patch
import main as bot

ROOT = Path(__file__).resolve().parent


def test_provisional_tp1_floor_is_observational_but_final_floor_stays_hard():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    pre = source.split("A22 FIX: this TP1 geometry is provisional.", 1)[-1].split(
        "# ---- Daily circuit breaker (hard pre-gate) ----", 1
    )[0]
    assert "A22_PRE_REPRICE_TP1_FLOOR_WARNING" in pre
    assert "return None" not in pre
    assert '"sr_aware_targets", _a22_tp1_diag' in source
    assert 'record_stage_reject("stage_e_to_q_rejected_by_score")' in source
    assert "shortfall_atr" in source and "required_tp1_distance_atr" in source


def test_shadow_htf_capture_band_does_not_change_live_policy_floors():
    assert bot.CONFIG["V702_CF_SHADOW_HTF_RELIEF_POINTS"] == 5.0
    pb_floor = bot._v702_effective_htf_floor(
        "PULLBACK", "PULLBACK", "BULLISH", "LOCAL_BULLISH", 60.0, {}
    )
    strict_floor = bot._v702_effective_htf_floor(
        "BREAKOUT_RETEST", "BREAKOUT_RETEST", "BULLISH", "LOCAL_BULLISH", 55.0, {}
    )
    assert pb_floor == 45.0
    assert strict_floor == 55.0
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70
    assert bot.CONFIG["LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME"] >= 3_000_000


def test_prequal_observer_returns_original_verdict_unchanged():
    candidate = type("Candidate", (), {
        "symbol": "A22-TEST/USDT", "family": "PULLBACK", "strategy_mode": "PULLBACK",
        "engine_score": 0.82, "reviewed_score": 82,
        "features_snapshot": {"htf_strength": 61, "volume_ratio": 1.2, "rs_5m": .02, "chase_atr": .2},
    })()
    verdict = (False, "structural.fake_break_detected")
    old_count = bot.STATS.get("v702_a22_prequal_reject_counts", {}).get(verdict[1], 0)
    with patch.dict(bot.__dict__, {"_V699_VALIDATE_ONLY_REQUEST": False}, clear=False):
        got = bot._v702_a22_capture_prequal_result(candidate, {}, verdict)
    assert got is verdict
    assert bot.STATS["v702_a22_prequal_reject_counts"][verdict[1]] == old_count + 1
    assert bot.STATS["v702_a22_last_prequal_block"]["symbol"] == "A22-TEST/USDT"
    assert bot.STATS["v702_a22_last_prequal_block"]["observation_scope"] == "PREQUAL_REJECTION_ONLY_NO_POLICY_CHANGE"


def test_a22_terminal_contract_passes_and_keeps_live_hard_gates():
    report = bot._v702_a22_terminal_self_test()
    assert report["pass"], report
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A22_CANONICAL_REVISION)
    assert bot.V702_A21_CANONICAL_REVISION == bot.V702_A22_CANONICAL_REVISION
    assert bot.CONFIG["LONG_ONLY"] is True
    assert str(bot.CONFIG["MARKET_TYPE"]).upper() == "SPOT"
    assert bot.CONFIG.get("ENABLE_FUTURES", False) is False
    assert bot.CONFIG.get("V520_PREQUAL_FAKE_BREAK_ENABLE") is True
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False


def test_stateful_runtime_db_is_excluded_by_release_policy_and_gitignore():
    # Import-time schema validation may create the disposable DB in this working
    # tree; that is not evidence it was packaged. The release metadata must
    # explicitly exclude stateful DB files, and ignore rules must protect them.
    manifest = __import__("json").loads((ROOT / "FINAL_MANIFEST.json").read_text(encoding="utf-8"))
    exclusions = str(manifest.get("archive_files_excluded", "")).lower()
    assert "unified_scalper.db" in exclusions and "wal/shm" in exclusions
    assert manifest.get("packaged_database_sha256") is None
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "*.db" in gi and ".env" in gi and "*.sqlite3" in gi
