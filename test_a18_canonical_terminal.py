"""A18 regression contracts for bounded universe freshness and safe validation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = (ROOT / "main.py").read_text(encoding="utf-8")


def test_a18_refresh_cadence_is_five_minutes_without_deep_scan_expansion():
    assert '"LIQUIDITY_UNIVERSE_REFRESH_SEC": 300' in SOURCE
    assert '"TOP_LIQUIDITY_SYMBOLS": 500' in SOURCE
    assert 'V699 is now the active universe arbiter' in SOURCE
    assert 'A18 5-minute scanner cadence' in SOURCE or '5-minute scanner cadence' in SOURCE
    assert '"a18_deep_scan_width_changed": False' in SOURCE


def test_a18_validate_only_uses_disposable_database_unless_operator_overrides():
    sandbox = SOURCE.index("_V702_VALIDATE_ONLY_DB_SANDBOX_WIRED = True")
    section_two = SOURCE.index("SECTION 2 — ENV LOADER")
    assert sandbox < section_two
    snippet = SOURCE[sandbox:section_two]
    assert '"--validate-only" in sys.argv' in snippet
    assert 'os.environ.get("SCALPER_DB", "")' in snippet
    assert 'tempfile.mkdtemp(prefix=_v702_a18_db_prefix)' in snippet
    assert 'unified_scalper_pytest_import_' in snippet
    assert '_V702_TEST_IMPORT_DB_SANDBOX_REQUESTED' in snippet
    assert 'CONFIG["DB_PATH"] = os.path.join(_V702_VALIDATE_ONLY_DB_TEMP_DIR' in snippet
    assert '_v702_a18_shutil.rmtree, _V702_VALIDATE_ONLY_DB_TEMP_DIR, ignore_errors=True' in snippet


def test_a18_self_test_is_in_the_terminal_validation_gate():
    assert "def _v702_a18_terminal_self_test():" in SOURCE
    assert 'globals()["validate_config"] = _v702_a18_validate_config' in SOURCE
    assert '"v702_a18_terminal_self_test": STATS.get("v702_a18_terminal_self_test", {})' in SOURCE
    assert '"active_package_revision": V702_PACKAGE_AUDIT_REVISION' in SOURCE
    assert '"active_package_revision": V702_PACKAGE_AUDIT_REVISION' in SOURCE


def test_a18_preserves_live_score_and_liquidity_floors():
    assert 'checks["live_score_floor_remains_70"] = float(CONFIG.get("MIN_LIVE_SCORE", 0.0)) >= 70.0' in SOURCE
    assert 'checks["core_volume_floor_remains_3m"]' in SOURCE
    assert 'float(CONFIG.get("LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME", 0.0)) >= 3_000_000.0' in SOURCE
    assert 'float(CONFIG.get("V650_LIQUIDITY500_MIN_QUOTE_VOLUME", 0.0)) >= 3_000_000.0' in SOURCE
    assert 'checks["micro_depth_floor_remains_1_90"]' in SOURCE


def test_a18_preserves_spot_long_only_blacklist_trade_cap_and_ticket_cap():
    for marker in (
        'checks["spot_long_only_and_no_futures"]',
        'checks["forbidden_bases_preserved"]',
        'checks["max_two_live_slots_preserved"]',
        'checks["max_75_usdt_entry_preserved"]',
        'checks["hard_gate_bypass_disabled"]',
    ):
        assert marker in SOURCE
    assert '{"AERO", "BNB", "CAKE", "ETHFI", "PUMP"}.issubset(set(V702_HARD_FORBIDDEN_BASES))' in SOURCE
    assert '"hard_gate_bypass": False' in SOURCE


def test_a18_does_not_claim_live_or_profitability_verification():
    block = SOURCE[SOURCE.index("V702_A18_CANONICAL_REVISION ="):SOURCE.index("if _V699_VALIDATE_ONLY_REQUEST:", SOURCE.index("V702_A18_CANONICAL_REVISION ="))]
    assert '"live_network_tested": False' in block
    assert '"execution_policy_changed": False' in block
    assert '"live_gates_relaxed": False' in block
    assert '"hard_gate_bypass": False' in block
