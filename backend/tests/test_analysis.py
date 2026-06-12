"""
Unit tests for the analytical engine: cutoff logic, vintage selection, and metric calculations.
"""

import math
from datetime import date, datetime
import pytest
from app.analysis import (
    parse_london_cutoff_to_utc,
    select_latest_eligible_forecasts,
    calculate_metrics,
    match_and_analyze_day
)


def test_parse_london_cutoff_day_ahead():
    """Verify that a 10:00 cutoff for Jan 2 delivery evaluates to 10:00 UTC on Jan 1."""
    delivery_date = date(2026, 1, 2)
    cutoff_utc, assumption = parse_london_cutoff_to_utc(delivery_date, "10:00", day_ahead=True)

    assert cutoff_utc.strftime("%Y-%m-%dT%H:%M:%SZ") == "2026-01-01T10:00:00Z"
    assert "Day-ahead market decision deadline at 10:00 Europe/London on 2026-01-01 (D-1)" in assumption


def test_select_latest_eligible_forecast_among_multiple():
    """
    Test: Two eligible forecasts for one period.
    Expected: Newest publication before cutoff is selected.
    """
    cutoff = datetime(2026, 1, 1, 10, 0, 0)
    records = [
        # Earlier eligible vintage
        {"startTime": "2026-01-02T12:00:00Z", "publishTime": "2026-01-01T04:30:00Z", "generation": 12000.0},
        # Later eligible vintage
        {"startTime": "2026-01-02T12:00:00Z", "publishTime": "2026-01-01T09:30:00Z", "generation": 14500.0},
    ]

    selected = select_latest_eligible_forecasts(records, cutoff)
    assert "2026-01-02T12:00:00Z" in selected
    assert selected["2026-01-02T12:00:00Z"]["generation"] == 14500.0
    assert selected["2026-01-02T12:00:00Z"]["publishTime"] == "2026-01-01T09:30:00Z"


def test_exclude_post_cutoff_publications():
    """
    Test: One forecast published after cutoff.
    Expected: Excluded from historical decision (prevent lookahead bias).
    """
    cutoff = datetime(2026, 1, 1, 10, 0, 0)
    records = [
        # Eligible vintage before 10:00 cutoff
        {"startTime": "2026-01-02T14:00:00Z", "publishTime": "2026-01-01T09:30:00Z", "generation": 10000.0},
        # Post-cutoff publication (leakage if included!)
        {"startTime": "2026-01-02T14:00:00Z", "publishTime": "2026-01-01T11:30:00Z", "generation": 18000.0},
    ]

    selected = select_latest_eligible_forecasts(records, cutoff)
    assert selected["2026-01-02T14:00:00Z"]["generation"] == 10000.0
    assert selected["2026-01-02T14:00:00Z"]["publishTime"] == "2026-01-01T09:30:00Z"


def test_unmatched_period_is_none_not_zero():
    """
    Test: No forecast for an actual period.
    Expected: Period is unmatched, not assigned zero.
    """
    delivery_date = date(2026, 1, 2)
    actuals = [
        {"startTime": "2026-01-02T00:00:00Z", "settlementPeriod": 1, "generation": 5000.0},
        {"startTime": "2026-01-02T00:30:00Z", "settlementPeriod": 2, "generation": 5200.0},
    ]
    # Only period 1 has a forecast
    forecasts = [
        {"startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-01T09:30:00Z", "generation": 5100.0}
    ]

    res = match_and_analyze_day(delivery_date, "10:00", actuals, forecasts, day_ahead=True)

    # Period 1 should be matched
    p1 = next(p for p in res.periods if p.startTime == "2026-01-02T00:00:00Z")
    assert p1.status == "matched"
    assert p1.actual == 5000.0
    assert p1.forecast == 5100.0
    assert p1.error == 100.0

    # Period 2 should be missing_forecast, forecast must be None, NOT 0.0
    p2 = next(p for p in res.periods if p.startTime == "2026-01-02T00:30:00Z")
    assert p2.status == "missing_forecast"
    assert p2.actual == 5200.0
    assert p2.forecast is None
    assert p2.error is None


def test_known_errors_metric_calculation():
    """
    Test: Known errors of +10 and -10 MW.
    Expected: MAE = 10 MW; bias = 0 MW; RMSE = 10 MW.
    """
    errors = [10.0, -10.0]
    metrics = calculate_metrics(errors, total_actual_periods=2)

    assert metrics.mae == 10.0
    assert metrics.bias == 0.0
    assert metrics.rmse == 10.0
    assert metrics.maxAbsoluteError == 10.0
    assert metrics.matchedPeriods == 2
    assert metrics.actualPeriods == 2
    assert metrics.coverage == 1.0


def test_coverage_calculation():
    """
    Test: 24 matched out of 48 actual periods gives 50% coverage.
    """
    errors = [5.0] * 24
    metrics = calculate_metrics(errors, total_actual_periods=48)

    assert metrics.matchedPeriods == 24
    assert metrics.actualPeriods == 48
    assert metrics.coverage == 0.5


def test_empty_errors_metric_calculation():
    """
    Test: Empty dataset produces explicit None metrics without division by zero.
    """
    metrics = calculate_metrics([], total_actual_periods=48)
    assert metrics.mae is None
    assert metrics.rmse is None
    assert metrics.bias is None
    assert metrics.maxAbsoluteError is None
    assert metrics.matchedPeriods == 0
    assert metrics.coverage == 0.0


def test_duplicate_actuals_deterministic_handling():
    """
    Test: Duplicate actual records for same startTime are deduplicated deterministically.
    """
    delivery_date = date(2026, 1, 2)
    actuals = [
        {"startTime": "2026-01-02T00:00:00Z", "settlementPeriod": 1, "generation": 5000.0},
        {"startTime": "2026-01-02T00:00:00Z", "settlementPeriod": 1, "generation": 5000.0},
    ]
    forecasts = [
        {"startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-01T09:30:00Z", "generation": 5100.0}
    ]

    res = match_and_analyze_day(delivery_date, "10:00", actuals, forecasts, day_ahead=True)
    assert len(res.periods) == 1
    assert res.metrics.actualPeriods == 1
    assert res.metrics.matchedPeriods == 1
    assert res.metrics.coverage == 1.0


def test_all_actual_periods_matched_100_percent_coverage():
    """
    Test 8 from Release Gate: All actual periods matched -> Coverage = 100%.
    """
    delivery_date = date(2026, 1, 2)
    actuals = [
        {"startTime": f"2026-01-02T{h:02d}:00:00Z", "settlementPeriod": h * 2 + 1, "generation": 10000.0}
        for h in range(24)
    ]
    forecasts = [
        {"startTime": f"2026-01-02T{h:02d}:00:00Z", "publishTime": "2026-01-01T09:30:00Z", "generation": 10500.0}
        for h in range(24)
    ]

    res = match_and_analyze_day(delivery_date, "10:00", actuals, forecasts, day_ahead=True)
    assert res.metrics.actualPeriods == 24
    assert res.metrics.matchedPeriods == 24
    assert res.metrics.coverage == 1.0
    assert res.metrics.mae == 500.0
    assert res.metrics.bias == 500.0


def test_missing_or_malformed_source_fields_excluded():
    """
    Test 9 from Release Gate: Missing or malformed source fields are excluded
    under documented policy without corrupting valid data.
    """
    cutoff = datetime(2026, 1, 1, 10, 0, 0)
    malformed_records = [
        # Missing startTime
        {"publishTime": "2026-01-01T09:30:00Z", "generation": 10000.0},
        # Missing publishTime
        {"startTime": "2026-01-02T12:00:00Z", "generation": 10000.0},
        # None values
        {"startTime": None, "publishTime": "2026-01-01T09:30:00Z", "generation": 10000.0},
        {"startTime": "2026-01-02T14:00:00Z", "publishTime": None, "generation": 10000.0},
        # Valid record
        {"startTime": "2026-01-02T16:00:00Z", "publishTime": "2026-01-01T09:30:00Z", "generation": 15000.0},
    ]

    selected = select_latest_eligible_forecasts(malformed_records, cutoff)
    # Only the valid record should be selected
    assert len(selected) == 1
    assert "2026-01-02T16:00:00Z" in selected
    assert selected["2026-01-02T16:00:00Z"]["generation"] == 15000.0


def test_parse_london_cutoff_same_day_intraday():
    """
    Verify same-day intraday cutoff logic (day_ahead=False): evaluates to delivery_date (D).
    """
    delivery_date = date(2026, 1, 2)
    cutoff_utc, assumption = parse_london_cutoff_to_utc(delivery_date, "12:00", day_ahead=False)

    assert cutoff_utc.strftime("%Y-%m-%dT%H:%M:%SZ") == "2026-01-02T12:00:00Z"
    assert "Intraday decision deadline at 12:00 Europe/London on 2026-01-02 (D)" in assumption

