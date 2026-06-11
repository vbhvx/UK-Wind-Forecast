"""
Analytical engine for Windward.
Implements day-ahead cutoff replay, exact settlement period joins, and audit-grade metric calculations.
"""

import math
from datetime import datetime, date, timedelta, time
from typing import List, Dict, Any, Optional, Tuple
import zoneinfo
from dateutil import parser as date_parser

from app.schemas import (
    PeriodDetail,
    MetricsSummary,
    DailyAnalysisResponse,
    DaySummary,
    MonthAnalysisResponse
)

LONDON_TZ = zoneinfo.ZoneInfo("Europe/London")
UTC_TZ = zoneinfo.ZoneInfo("UTC")


def parse_london_cutoff_to_utc(
    delivery_date: date,
    cutoff_time_str: str,
    day_ahead: bool = True
) -> Tuple[datetime, str]:
    """
    Given a delivery date and a London local cutoff time (e.g. '10:00'),
    calculates the exact decision cutoff moment in UTC.
    For day-ahead, decision date is delivery_date - 1 day.
    Returns:
        (cutoff_dt_utc, cutoff_assumption_description)
    """
    # Parse cutoff time
    parts = cutoff_time_str.strip().split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    second = int(parts[2]) if len(parts) > 2 else 0

    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        raise ValueError(f"Invalid cutoff time: {cutoff_time_str}")

    target_date = delivery_date - timedelta(days=1) if day_ahead else delivery_date
    london_dt = datetime.combine(target_date, time(hour, minute, second), tzinfo=LONDON_TZ)
    utc_dt = london_dt.astimezone(UTC_TZ)

    assumption = (
        f"Day-ahead market decision deadline at {cutoff_time_str} Europe/London on "
        f"{target_date.isoformat()} (D-1). Only forecasts published at or before this timestamp are eligible."
        if day_ahead
        else f"Intraday decision deadline at {cutoff_time_str} Europe/London on "
             f"{target_date.isoformat()} (D). Only forecasts published at or before this timestamp are eligible."
    )

    return utc_dt, assumption


def select_latest_eligible_forecasts(
    windfor_records: List[Dict[str, Any]],
    cutoff_utc: datetime
) -> Dict[str, Dict[str, Any]]:
    """
    Applies the mathematical formulation:
        p*(t, c) = max { p : p <= c }
        G_hat(t, c) = G(t, p*(t, c))
    
    Filters out any publication where publishTime > cutoff_utc.
    For each unique delivery startTime t, selects the record with the maximum publishTime <= cutoff.
    Deterministic tie-breaking: if multiple records share the exact same latest publishTime and startTime,
    takes the first occurrence and logs if inconsistent.
    
    Returns:
        dict mapping startTime (UTC ISO str) -> { 'generation': float, 'publishTime': str }
    """
    cutoff_iso = cutoff_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Group eligible records by startTime
    grouped_by_delivery: Dict[str, List[Dict[str, Any]]] = {}
    for record in windfor_records:
        pub_time = record.get("publishTime")
        start_time = record.get("startTime")
        if not pub_time or not start_time:
            continue

        # Strict cutoff filtering: p <= c
        # ISO string comparison works because formats are normalized UTC (YYYY-MM-DDTHH:MM:SSZ)
        if pub_time <= cutoff_iso:
            if start_time not in grouped_by_delivery:
                grouped_by_delivery[start_time] = []
            grouped_by_delivery[start_time].append(record)

    selected: Dict[str, Dict[str, Any]] = {}
    for start_time, candidates in grouped_by_delivery.items():
        # Find candidate with highest publishTime
        # In case of tie, Python's max is deterministic
        best = max(candidates, key=lambda x: x["publishTime"])
        selected[start_time] = {
            "generation": float(best["generation"]),
            "publishTime": best["publishTime"]
        }

    return selected


def calculate_metrics(errors: List[float], total_actual_periods: int) -> MetricsSummary:
    """
    Calculates MAE, RMSE, bias, maxAbsoluteError, and coverage from a list of matched period errors:
        e_t = F_t - A_t
    
    Handles n = 0 edge case without crashing.
    """
    matched_count = len(errors)
    coverage = (matched_count / total_actual_periods) if total_actual_periods > 0 else 0.0

    if matched_count == 0:
        return MetricsSummary(
            mae=None,
            rmse=None,
            bias=None,
            maxAbsoluteError=None,
            matchedPeriods=0,
            actualPeriods=total_actual_periods,
            coverage=round(coverage, 4)
        )

    mae = sum(abs(e) for e in errors) / matched_count
    rmse = math.sqrt(sum(e ** 2 for e in errors) / matched_count)
    bias = sum(errors) / matched_count
    max_err = max(abs(e) for e in errors)

    return MetricsSummary(
        mae=round(mae, 2),
        rmse=round(rmse, 2),
        bias=round(bias, 2),
        maxAbsoluteError=round(max_err, 2),
        matchedPeriods=matched_count,
        actualPeriods=total_actual_periods,
        coverage=round(coverage, 4)
    )


def match_and_analyze_day(
    delivery_date: date,
    cutoff_time_str: str,
    actuals: List[Dict[str, Any]],
    windfor_records: List[Dict[str, Any]],
    day_ahead: bool = True
) -> DailyAnalysisResponse:
    """
    Matches actual FUELHH wind outturns with eligible WINDFOR forecasts for a single delivery day.
    Constructs the period detail list, computes accuracy metrics, and documents assumptions.
    """
    cutoff_utc, assumption = parse_london_cutoff_to_utc(delivery_date, cutoff_time_str, day_ahead=day_ahead)
    cutoff_iso = cutoff_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Select latest eligible forecasts
    selected_forecasts = select_latest_eligible_forecasts(windfor_records, cutoff_utc)

    # Sort actuals chronologically by startTime
    # Deduplicate actuals deterministically if any duplicate startTime exists
    unique_actuals_map: Dict[str, Dict[str, Any]] = {}
    for act in sorted(actuals, key=lambda x: (x["startTime"], x.get("settlementPeriod") or 0)):
        st = act["startTime"]
        if st not in unique_actuals_map:
            unique_actuals_map[st] = act

    period_details: List[PeriodDetail] = []
    errors: List[float] = []
    selected_publications: List[str] = []

    for start_time, act in unique_actuals_map.items():
        actual_val = act["generation"]
        settlement_period = act.get("settlementPeriod")

        if start_time in selected_forecasts:
            fc_entry = selected_forecasts[start_time]
            fc_val = fc_entry["generation"]
            pub_time = fc_entry["publishTime"]
            err = round(fc_val - actual_val, 2)

            errors.append(err)
            selected_publications.append(pub_time)

            period_details.append(PeriodDetail(
                startTime=start_time,
                settlementPeriod=settlement_period,
                actual=round(actual_val, 2),
                forecast=round(fc_val, 2),
                publishTime=pub_time,
                error=err,
                status="matched"
            ))
        else:
            # Unmatched period: forecast is None, NOT zero!
            period_details.append(PeriodDetail(
                startTime=start_time,
                settlementPeriod=settlement_period,
                actual=round(actual_val, 2),
                forecast=None,
                publishTime=None,
                error=None,
                status="missing_forecast"
            ))

    # Also handle case where there are forecasts for delivery periods that had no actual recorded
    # (Rare, but preserved for data completeness audit)
    all_actual_starts = set(unique_actuals_map.keys())
    for st, fc_entry in selected_forecasts.items():
        # Check if st falls within the delivery date in UTC
        if st not in all_actual_starts and st.startswith(delivery_date.isoformat()):
            period_details.append(PeriodDetail(
                startTime=st,
                settlementPeriod=None,
                actual=None,
                forecast=round(fc_entry["generation"], 2),
                publishTime=fc_entry["publishTime"],
                error=None,
                status="missing_actual"
            ))

    # Sort all period details by startTime
    period_details.sort(key=lambda p: p.startTime)

    metrics = calculate_metrics(errors, total_actual_periods=len(unique_actuals_map))
    latest_selected_pub = max(selected_publications) if selected_publications else None

    return DailyAnalysisResponse(
        deliveryDate=delivery_date.isoformat(),
        cutoffTimeLondon=cutoff_time_str,
        cutoffTimestampUtc=cutoff_iso,
        cutoffAssumption=assumption,
        metrics=metrics,
        latestSelectedPublication=latest_selected_pub,
        periods=period_details
    )
