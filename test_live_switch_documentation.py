"""Prevent dangerous drift between two-key A55/A56 authorization and operator docs."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_live_pilot_emergency_switch_and_two_key_arm_documentation_match_runtime():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    guardrails = (ROOT / "production_guardrails.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    source = (ROOT / "main.py").read_text(encoding="utf-8")

    assert 'control in {"0", "false", "no", "off", "disabled"}' in guardrails
    assert "UNIFIED_LIVE_PILOT_ENABLE=0 to block NEW live BUYs" in example
    assert "UNIFIED_LIVE_PILOT_ENABLE=0" in example
    assert "UNIFIED_A55_LIVE_ARM=0" in example
    assert "A55/A56 have one authorization authority" in guardrails
    assert "operator_armed = bool(callable(arm_check) and arm_check())" in guardrails
    assert 'str(os.environ.get("UNIFIED_A55_LIVE_ARM", "")).strip() == "1"' in source
    assert "contextless_live_buy" in source or "if not isinstance(intent_context, dict) or not intent_context:" in source
    assert "لا يكفي المفتاح الأول وحده" in readme
    assert "UNIFIED_LIVE_PILOT_ENABLE=1" in readme
    assert "UNIFIED_A55_LIVE_ARM=1" in readme
