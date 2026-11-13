"""A11 regression: the BTC macro snapshot always uses the dedicated shared feed."""
from pathlib import Path
import main

ROOT = Path(__file__).resolve().parent
EXPECTED_REVISION = main.V702_A46_CANONICAL_REVISION + "-A47-COVERAGE-POLICY-REUSE-REJECT-ATTRIBUTION-EVIDENCE-CLOSURE-2026-10-18-A48-CANONICAL-REJECTION-TELEMETRY-CLOSURE-2026-10-19-A49-ELITE-HTF-RELIEF-CONSISTENCY-AND-REJECT-ATTRIBUTION-2026-10-19-A52-SAFETY-HARDENING-AND-CANONICAL-OUTCOME-COHERENCE-2026-10-21-A53-EXECUTION-TELEGRAM-SWING-CLOSURE-2026-10-21"


def test_btc_context_fields_always_use_shared_btc_frames_for_every_symbol():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    # The candidate-local frames remain available via **frames, but macro context
    # must never be shadowed by BTC/USDT's separate limit=220 scan frame.
    assert '"df_btc_5m": shared_btc_5m' in source
    assert '"df_btc_15m": shared_btc_15m' in source
    assert '"df_btc_1h": shared_btc_1h' in source
    assert '"df_btc_4h": shared_btc_4h' in source
    assert '"df_btc_4h": frames["df_4h"] if _is_btc else shared_btc_4h' not in source
    assert '"btc_context_age_sec": max(0.0, MONO_NOW() - shared_btc_context_ts)' in source


def test_runtime_package_identity_advances_monotonically_through_a49_production_closure():
    assert main.V702_A40_CANONICAL_REVISION.startswith(main.V702_A39_CANONICAL_REVISION + "-A40-")
    assert main.V702_A41_CANONICAL_REVISION.startswith(main.V702_A40_CANONICAL_REVISION + "-A41-")
    assert main.V702_A42_CANONICAL_REVISION.startswith(main.V702_A41_CANONICAL_REVISION + "-A42-")
    assert main.V702_A43_CANONICAL_REVISION.startswith(main.V702_A42_CANONICAL_REVISION + "-A43-")
    assert main.V702_A44_CANONICAL_REVISION.startswith(main.V702_A43_CANONICAL_REVISION + "-A44-")
    assert main.V702_PACKAGE_AUDIT_REVISION.startswith(EXPECTED_REVISION)
    assert "-A54-" in main.V702_PACKAGE_AUDIT_REVISION
    assert "-A55-" in main.V702_PACKAGE_AUDIT_REVISION
    assert "-A56-" in main.V702_PACKAGE_AUDIT_REVISION
    assert main.FINAL_CANONICAL_RUNTIME.get("package_audit_revision") == main.V702_PACKAGE_AUDIT_REVISION


def test_short_local_symbol_history_is_adaptive_but_btc_macro_stays_strict():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert '"V702_A32_LOCAL_4H_MIN_CLOSED_CANDLES": 50' in source
    assert 'def _v702_a32_4h_history_integrity' in source
    assert '"df_btc_4h": int(CONFIG.get("BTC_SHARED_CONTEXT_MIN_CANDLES_4H", 120)) + 1' in source
    assert '"V702_A32_LOCAL_4H_FULL_EMA200_WARMUP_CANDLES": 210' in source
