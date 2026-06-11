"""
FastAPI application for Windward.
Provides endpoints for health check, daily forecast replay analysis, and January 2026 monthly metrics.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import FastAPI, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dateutil import parser as date_parser

from app.schemas import (
    DailyAnalysisResponse,
    MonthAnalysisResponse,
    DaySummary,
    MetricsSummary,
    HealthResponse
)
from app.elexon import ElexonClient, ElexonAPIError
from app.analysis import match_and_analyze_day, parse_london_cutoff_to_utc, calculate_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("wind_forecast_app")

app = FastAPI(
    title="Windward API",
    description="Analyzes national wind generation forecasts against actuals for day-ahead purchasing decisions.",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

elexon_client = ElexonClient()


def validate_january_2026_date(date_str: str) -> date:
    """Validates that the provided delivery date is within January 2026 scope."""
    try:
        parsed_date = date_parser.parse(date_str).date()
    except Exception:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid date format: '{date_str}'. Expected format YYYY-MM-DD."
        )

    if parsed_date.year != 2026 or parsed_date.month != 1:
        raise HTTPException(
            status_code=422,
            detail=f"Date '{date_str}' is out of scope. Evaluation is strictly confined to January 2026 (2026-01-01 to 2026-01-31)."
        )

    return parsed_date


def validate_cutoff_time(cutoff_str: str) -> str:
    """Validates that cutoff time is a valid HH:MM string."""
    try:
        parts = cutoff_str.strip().split(":")
        if len(parts) < 2:
            raise ValueError()
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError()
        return f"{h:02d}:{m:02d}"
    except Exception:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid cutoff time: '{cutoff_str}'. Expected format HH:MM in 24-hour time (e.g. 10:00)."
        )


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Service health and cache readiness check."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        version="1.0.0",
        cacheStatus=elexon_client.cache_stats
    )


@app.get("/api/analysis", response_model=DailyAnalysisResponse, tags=["Analysis"])
async def get_daily_analysis(
    delivery_date: str = Query(..., description="Target delivery date in January 2026 (YYYY-MM-DD)"),
    cutoff_time: str = Query("10:00", description="London local decision cutoff time (HH:MM)"),
    day_ahead: bool = Query(True, description="True for day-ahead cutoff (D-1), False for same-day intraday cutoff")
):
    """
    Returns matched forecasts vs actuals, accuracy metrics (MAE, RMSE, bias),
    and settlement period audit records for a single delivery day.
    """
    target_date = validate_january_2026_date(delivery_date)
    norm_cutoff_time = validate_cutoff_time(cutoff_time)

    # Calculate cutoff in UTC
    cutoff_utc, _ = parse_london_cutoff_to_utc(target_date, norm_cutoff_time, day_ahead=day_ahead)

    # To ensure all relevant vintages are captured across WINDFOR's 73-hour horizon,
    # look back 4 days prior to the cutoff
    fetch_window_start = cutoff_utc - timedelta(days=4)
    fetch_window_end = cutoff_utc

    try:
        # Fetch actuals for the delivery date
        actuals = await elexon_client.fetch_fuelhh_actuals(target_date, target_date)
        # Fetch WINDFOR publications up to cutoff
        windfor_records = await elexon_client.fetch_windfor_vintages(fetch_window_start, fetch_window_end)
    except ElexonAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in daily analysis: %s", exc)
        raise HTTPException(status_code=502, detail=f"Upstream data processing error: {str(exc)}")

    response = match_and_analyze_day(
        delivery_date=target_date,
        cutoff_time_str=norm_cutoff_time,
        actuals=actuals,
        windfor_records=windfor_records,
        day_ahead=day_ahead
    )
    return response


@app.get("/api/month", response_model=MonthAnalysisResponse, tags=["Analysis"])
async def get_monthly_analysis(
    cutoff_time: str = Query("10:00", description="London local decision cutoff time (HH:MM)")
):
    """
    Returns daily accuracy metrics and aggregated performance across the entire month of January 2026.
    """
    norm_cutoff_time = validate_cutoff_time(cutoff_time)

    month_start = date(2026, 1, 1)
    month_end = date(2026, 1, 31)

    # Query window for forecasts: from 2025-12-28 to 2026-01-31
    wind_fetch_start = datetime(2025, 12, 28, 0, 0, 0)
    wind_fetch_end = datetime(2026, 1, 31, 23, 59, 59)

    try:
        # Fetch month actuals and forecasts (served from cache after initial query)
        month_actuals = await elexon_client.fetch_fuelhh_actuals(month_start, month_end)
        all_windfor = await elexon_client.fetch_windfor_vintages(wind_fetch_start, wind_fetch_end)
    except ElexonAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in monthly analysis: %s", exc)
        raise HTTPException(status_code=502, detail=f"Upstream data processing error: {str(exc)}")

    # Group actuals by settlementDate or delivery date
    actuals_by_date: dict[str, list] = {}
    for act in month_actuals:
        d_str = act.get("settlementDate")
        if not d_str and act.get("startTime"):
            d_str = act["startTime"][:10]
        if d_str:
            if d_str not in actuals_by_date:
                actuals_by_date[d_str] = []
            actuals_by_date[d_str].append(act)

    daily_summaries: list[DaySummary] = []
    all_matched_errors: list[float] = []
    total_month_actual_periods = 0

    curr_date = month_start
    while curr_date <= month_end:
        d_str = curr_date.isoformat()
        day_acts = actuals_by_date.get(d_str, [])

        # Analyze day
        day_res = match_and_analyze_day(
            delivery_date=curr_date,
            cutoff_time_str=norm_cutoff_time,
            actuals=day_acts,
            windfor_records=all_windfor,
            day_ahead=True
        )

        day_metrics = day_res.metrics
        status_label = "complete" if day_metrics.coverage >= 0.95 else ("partial" if day_metrics.matchedPeriods > 0 else "no_data")

        daily_summaries.append(DaySummary(
            date=d_str,
            mae=day_metrics.mae,
            rmse=day_metrics.rmse,
            bias=day_metrics.bias,
            maxAbsoluteError=day_metrics.maxAbsoluteError,
            matchedPeriods=day_metrics.matchedPeriods,
            actualPeriods=day_metrics.actualPeriods,
            coverage=day_metrics.coverage,
            status=status_label
        ))

        # Accumulate errors for month-wide metrics
        for p in day_res.periods:
            if p.status == "matched" and p.error is not None:
                all_matched_errors.append(p.error)
        total_month_actual_periods += day_metrics.actualPeriods

        curr_date += timedelta(days=1)

    overall_metrics = calculate_metrics(all_matched_errors, total_actual_periods=total_month_actual_periods)

    assumption = (
        f"Month-wide day-ahead decision replay at {norm_cutoff_time} Europe/London on D-1. "
        "Strict vintage selection excluding any post-cutoff publication."
    )

    return MonthAnalysisResponse(
        month="2026-01",
        cutoffTimeLondon=norm_cutoff_time,
        cutoffAssumption=assumption,
        overallMetrics=overall_metrics,
        days=daily_summaries
    )
