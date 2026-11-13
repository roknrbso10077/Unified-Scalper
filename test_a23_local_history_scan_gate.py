"""A23 closure: do not rank symbols which already fail mandatory local MSE history."""
from pathlib import Path
import main as bot

ROOT = Path(__file__).resolve().parent


def _frame(rows):
    return bot.pd.DataFrame({
        "open": [1.0] * rows,
        "high": [1.1] * rows,
        "low": [0.9] * rows,
        "close": [1.0] * rows,
        "volume": [10.0] * rows,
    })


def _complete_frames():
    return {
        "df_4h": _frame(210),
        "df_1h": _frame(240),
        "df_15m": _frame(350),
        "df_5m": _frame(30),
    }


def test_valid_local_history_passes_same_contract_as_builder_snapshot():
    ok, reason = bot._mse_candidate_scan_precheck(_complete_frames())
    assert ok is True
    assert reason == "ok"


def test_usable_short_4h_history_is_accepted_before_ranking():
    frames = _complete_frames()
    frames["df_4h"] = _frame(52)
    ok, reason = bot._mse_candidate_scan_precheck(frames)
    assert ok is True
    assert reason == "ok"


def test_below_minimum_4h_history_is_rejected_before_ranking_with_exact_reason():
    frames = _complete_frames()
    frames["df_4h"] = _frame(49)
    ok, reason = bot._mse_candidate_scan_precheck(frames)
    assert ok is False
    assert reason == "df_4h:short_rows:got=49,required=50"


def test_invalid_local_history_is_rejected_without_sanitizing_or_padding():
    frames = _complete_frames()
    frames["df_1h"].loc[7, "close"] = float("nan")
    rows_before = len(frames["df_1h"])
    ok, reason = bot._mse_candidate_scan_precheck(frames)
    assert ok is False
    assert reason.startswith("df_1h:nonfinite_values:close:")
    assert len(frames["df_1h"]) == rows_before
    assert frames["df_1h"]["close"].isna().sum() == 1


def test_scan_admission_commits_market_candidate_only_after_behavioral_precheck():
    short_frames = _complete_frames()
    short_frames["df_4h"] = _frame(49)
    rows_before = {name: len(frame) for name, frame in short_frames.items()}
    committed = {}

    blocked, reason = bot._mse_candidate_scan_admit(
        short_frames, lambda: committed.__setitem__("TEST/USDT", short_frames)
    )
    assert blocked is False
    assert reason == "df_4h:short_rows:got=49,required=50"
    assert committed == {}
    assert {name: len(frame) for name, frame in short_frames.items()} == rows_before

    good_frames = _complete_frames()
    admitted, reason = bot._mse_candidate_scan_admit(
        good_frames, lambda: committed.__setitem__("GOOD/USDT", good_frames)
    )
    assert admitted is True
    assert reason == "ok"
    assert committed == {"GOOD/USDT": good_frames}
    assert callable(bot.validate_mse_snapshot)  # Builder-side defense remains independent.


def test_scan_admission_fails_closed_if_commit_callback_missing_or_raises():
    frames = _complete_frames()
    allowed, reason = bot._mse_candidate_scan_admit(frames, None)
    assert allowed is False and reason == "commit_not_callable"
    allowed, reason = bot._mse_candidate_scan_admit(
        frames, lambda: (_ for _ in ()).throw(RuntimeError("test"))
    )
    assert allowed is False and reason == "commit_failed:RuntimeError"


def test_a23_terminal_contract_and_live_invariants_pass():
    report = bot._v702_a23_terminal_self_test()
    assert report["pass"], report
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A23_CANONICAL_REVISION)
    assert bot.CONFIG["LONG_ONLY"] is True
    assert str(bot.CONFIG["MARKET_TYPE"]).upper() == "SPOT"
    assert bot.CONFIG.get("ENABLE_FUTURES", False) is False
    assert bot.CONFIG["MIN_LIVE_SCORE"] >= 70
    assert bot.CONFIG["LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME"] >= 3_000_000
    assert bot.FINAL_CANONICAL_RUNTIME["hard_gate_bypass"] is False
