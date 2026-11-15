from v702_core__execution__cost_model import unified_round_trip_cost_model


def test_measured_all_in_cost_supersedes_fallback_and_adds_only_buffer():
    cfg = {
        "V702_SHADOW_MIN_ROUND_TRIP_COST_PCT": 0.0,
        "V702_MEASURED_COST_BUFFER_PCT": 0.05,
        "V702_SMALL_NET_SPREAD_FALLBACK_PCT": 0.15,
        "V702_SMALL_NET_SLIPPAGE_PER_SIDE_PCT": 0.05,
        "TAKER_FEE_PCT": 0.10,
        "ROUNDTRIP_FEE_MULT": 2.0,
    }
    result = unified_round_trip_cost_model(cfg, measured_cost_pct=0.24, spread_pct=0.04, fee_cost_pct=0.08)
    assert result["round_trip_cost_pct"] == 0.29
    assert result["measured_cost_pct"] == 0.24
    assert result["measured_cost_buffer_pct"] == 0.05
    assert result["used_measured_cost"] == 1.0
    assert abs(result["r40_fallback_cost_pct"] - 0.22) < 1e-12


def test_fallback_uses_observed_spread_and_two_sided_fee_and_slippage():
    cfg = {
        "V702_SHADOW_MIN_ROUND_TRIP_COST_PCT": 0.0,
        "V702_SMALL_NET_SPREAD_FALLBACK_PCT": 0.15,
        "V702_SMALL_NET_SLIPPAGE_PER_SIDE_PCT": 0.05,
        "TAKER_FEE_PCT": 0.10,
        "ROUNDTRIP_FEE_MULT": 2.0,
    }
    result = unified_round_trip_cost_model(cfg, spread_pct=0.08)
    assert result["round_trip_cost_pct"] == 0.38
    assert result["spread_pct_used"] == 0.08
    assert result["round_trip_fee_pct"] == 0.20
    assert result["used_measured_cost"] == 0.0


def test_operator_floor_remains_a_hard_floor():
    result = unified_round_trip_cost_model(
        {"V702_SHADOW_MIN_ROUND_TRIP_COST_PCT": 0.55, "V702_MEASURED_COST_BUFFER_PCT": 0.05},
        measured_cost_pct=0.20,
    )
    assert result["round_trip_cost_pct"] == 0.55


def test_invalid_measured_cost_fails_closed_instead_of_becoming_zero_cost():
    import pytest
    with pytest.raises(ValueError, match="measured_all_in_cost_missing_or_non_finite"):
        unified_round_trip_cost_model(
            {"V702_SHADOW_MIN_ROUND_TRIP_COST_PCT": 0.0, "V702_SMALL_NET_SPREAD_FALLBACK_PCT": 0.15,
             "V702_SMALL_NET_SLIPPAGE_PER_SIDE_PCT": 0.05, "TAKER_FEE_PCT": 0.10,
             "ROUNDTRIP_FEE_MULT": 2.0},
            measured_cost_pct=float("nan"),
        )

def test_large_measured_cost_and_spread_are_never_clipped_downward():
    result = unified_round_trip_cost_model(
        {"V702_SHADOW_MIN_ROUND_TRIP_COST_PCT": 0.0, "V702_MEASURED_COST_BUFFER_PCT": 0.05,
         "V702_SMALL_NET_SPREAD_FALLBACK_PCT": 0.15, "V702_SMALL_NET_SLIPPAGE_PER_SIDE_PCT": 0.05,
         "TAKER_FEE_PCT": 0.10, "ROUNDTRIP_FEE_MULT": 2.0},
        measured_cost_pct=25.0, spread_pct=12.0, fee_cost_pct=0.2,
    )
    assert result["measured_cost_pct"] == 25.0
    assert result["spread_pct_used"] == 12.0
    assert result["round_trip_cost_pct"] == 25.05

def test_non_finite_explicit_fee_fails_closed():
    import pytest
    with pytest.raises(ValueError, match="measured_fee_cost_missing_or_non_finite"):
        unified_round_trip_cost_model({}, fee_cost_pct=float("nan"))
