"""A26 regression: historical A21/A22 checks must accept append-only releases."""
import inspect
import main as bot


def test_a21_a22_revision_checks_are_prefix_compatible():
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A35_CANONICAL_REVISION + "-A36-")
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A28_CANONICAL_REVISION + "-A29-")
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A27_CANONICAL_REVISION)
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A26_CANONICAL_REVISION)
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A25_CANONICAL_REVISION)
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A22_CANONICAL_REVISION)
    a21 = bot._v702_a21_terminal_self_test()
    a22 = a21.get("a22_terminal_self_test", {})
    assert a21["checks"].get("canonical_revision") is True, a21
    assert a21["pass"] is True, a21
    assert a22["checks"].get("canonical_a22_revision") is True, a22
    assert a22["pass"] is True, a22


def test_a26_terminal_contract_preserves_policy_and_revision_lineage():
    report = bot._v702_a26_terminal_self_test()
    assert report["pass"] is True, report
    assert report["checks"]["hard_score_and_liquidity_floors_unchanged"] is True
    assert report["checks"]["spot_long_only_no_futures_or_short"] is True
    assert report["checks"]["forbidden_assets_preserved"] is True
    assert report["checks"]["hard_gate_bypass_disabled"] is True


def test_final_validator_integrates_historical_a49_chain_through_additive_a57_and_a56_wrappers():
    # A63 is additive and must preserve the complete A62 -> A61 -> A60 ->
    # A59 -> A58 -> A57 -> A56 -> A55/A54 -> A49/A48 validator chain.
    assert callable(bot.validate_config)
    source = inspect.getsource(bot.validate_config)
    assert "_V702_A63_PREVIOUS_VALIDATE_CONFIG()" in source
    assert callable(bot._V702_A63_PREVIOUS_VALIDATE_CONFIG)
    a62_source = inspect.getsource(bot._V702_A63_PREVIOUS_VALIDATE_CONFIG)
    assert "_V702_A62_PREVIOUS_VALIDATE_CONFIG()" in a62_source
    assert callable(bot._V702_A62_PREVIOUS_VALIDATE_CONFIG)
    a61_source = inspect.getsource(bot._V702_A62_PREVIOUS_VALIDATE_CONFIG)
    assert "_V702_A61_PREVIOUS_VALIDATE_CONFIG()" in a61_source
    assert callable(bot._V702_A61_PREVIOUS_VALIDATE_CONFIG)
    a60_source = inspect.getsource(bot._V702_A61_PREVIOUS_VALIDATE_CONFIG)
    assert "_V702_A60_PREVIOUS_VALIDATE_CONFIG()" in a60_source
    assert callable(bot._V702_A60_PREVIOUS_VALIDATE_CONFIG)
    a59_source = inspect.getsource(bot._V702_A60_PREVIOUS_VALIDATE_CONFIG)
    assert "_V702_A59_PREVIOUS_VALIDATE_CONFIG()" in a59_source
    assert callable(bot._V702_A59_PREVIOUS_VALIDATE_CONFIG)
    a58_source = inspect.getsource(bot._V702_A59_PREVIOUS_VALIDATE_CONFIG)
    assert "_V702_A58_PREVIOUS_VALIDATE_CONFIG()" in a58_source
    assert callable(bot._V702_A58_PREVIOUS_VALIDATE_CONFIG)
    a57_source = inspect.getsource(bot._V702_A58_PREVIOUS_VALIDATE_CONFIG)
    assert "_V702_A57_PREVIOUS_VALIDATE_CONFIG()" in a57_source
    assert callable(bot._V702_A57_PREVIOUS_VALIDATE_CONFIG)
    a56_source = inspect.getsource(bot._V702_A57_PREVIOUS_VALIDATE_CONFIG)
    assert "_V702_A56_PREVIOUS_VALIDATE_CONFIG()" in a56_source
    assert callable(bot._V702_A56_PREVIOUS_VALIDATE_CONFIG)
    a55_source = inspect.getsource(bot._V702_A56_PREVIOUS_VALIDATE_CONFIG)
    assert "_V702_A55_PREVIOUS_VALIDATE_CONFIG()" in a55_source
    assert callable(bot._V702_A55_PREVIOUS_VALIDATE_CONFIG)
    previous_source = inspect.getsource(bot._V702_A55_PREVIOUS_VALIDATE_CONFIG)
    assert "_V702_A54_PREVIOUS_VALIDATE_CONFIG()" in previous_source
    assert callable(bot._V702_A54_PREVIOUS_VALIDATE_CONFIG)
    a49_chain_source = inspect.getsource(bot._V702_A54_PREVIOUS_VALIDATE_CONFIG)
    assert "_V702_A52_PREVIOUS_VALIDATE_CONFIG()" in a49_chain_source or "_V702_A52_PREVIOUS_VALIDATE_CONFIG" in a49_chain_source
    assert callable(bot._A48_PREVIOUS_VALIDATE_CONFIG)
    a48_source = inspect.getsource(bot._A48_PREVIOUS_VALIDATE_CONFIG)
    assert "_V702_A44_PREV_VALIDATE_CONFIG()" in a48_source
    assert bot._V702_A44_PREV_VALIDATE_CONFIG is bot._v702_a36_validate_config
    assert "_V702_A36_PREV_VALIDATE_CONFIG()" in inspect.getsource(bot._V702_A44_PREV_VALIDATE_CONFIG)
    assert bot._v702_a33_terminal_self_test()["pass"] is True
    assert "_v702_a32_terminal_self_test()" in inspect.getsource(bot._V702_A33_PREV_VALIDATE_CONFIG)
    assert bot.STATS["v702_a26_terminal_self_test"]["pass"] is True
    assert bot._v702_a49_terminal_self_test()["pass"] is True
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False


def test_a24_freshest_source_terminal_probe_is_repeatable_and_restores_clock_providers():
    wall_now, mono_now = bot.WALL_NOW, bot.MONO_NOW
    for _ in range(3):
        report = bot._v702_a24_terminal_self_test()
        assert report["checks"].get("no_send_age_uses_freshest_source") is True, report
        assert report["pass"] is True, report
    assert bot.WALL_NOW is wall_now
    assert bot.MONO_NOW is mono_now
