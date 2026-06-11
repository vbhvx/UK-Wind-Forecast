"""
Data schemas and Pydantic models for the Windward API.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class PeriodDetail(BaseModel):
    startTime: str = Field(description="ISO 8601 UTC delivery interval start timestamp")
    settlementPeriod: Optional[int] = Field(default=None, description="Settlement period (1-48 for a standard day)")
    actual: Optional[float] = Field(default=None, description="Actual metered wind generation (MW)")
    forecast: Optional[float] = Field(default=None, description="Selected forecast wind generation (MW)")
    publishTime: Optional[str] = Field(default=None, description="ISO 8601 UTC vintage publication timestamp")
    error: Optional[float] = Field(default=None, description="Forecast error: forecast - actual (MW)")
    status: str = Field(description="Period match status: matched, missing_forecast, or missing_actual")


class MetricsSummary(BaseModel):
    mae: Optional[float] = Field(default=None, description="Mean Absolute Error (MW)")
    rmse: Optional[float] = Field(default=None, description="Root Mean Squared Error (MW)")
    bias: Optional[float] = Field(default=None, description="Mean error/bias (MW) - positive indicates overforecasting")
    maxAbsoluteError: Optional[float] = Field(default=None, description="Maximum absolute error across matched periods (MW)")
    matchedPeriods: int = Field(description="Number of periods with both actual and forecast")
    actualPeriods: int = Field(description="Total actual periods in delivery date")
    coverage: float = Field(description="Proportion of periods matched: matchedPeriods / actualPeriods (0.0 to 1.0)")


class DailyAnalysisResponse(BaseModel):
    deliveryDate: str = Field(description="Delivery date in YYYY-MM-DD")
    cutoffTimeLondon: str = Field(description="Decision cutoff local time (Europe/London)")
    cutoffTimestampUtc: str = Field(description="Evaluated decision cutoff timestamp in ISO 8601 UTC")
    cutoffAssumption: str = Field(description="Auditable statement of the operational cutoff assumption")
    metrics: MetricsSummary = Field(description="Accuracy and coverage metrics for the delivery day")
    latestSelectedPublication: Optional[str] = Field(default=None, description="Latest publication timestamp among selected forecasts")
    periods: List[PeriodDetail] = Field(description="Half-hourly period records with actuals and matched forecasts")


class DaySummary(BaseModel):
    date: str = Field(description="Delivery date (YYYY-MM-DD)")
    mae: Optional[float] = Field(default=None, description="Day MAE (MW)")
    rmse: Optional[float] = Field(default=None, description="Day RMSE (MW)")
    bias: Optional[float] = Field(default=None, description="Day Mean Bias (MW)")
    maxAbsoluteError: Optional[float] = Field(default=None, description="Day Maximum Absolute Error (MW)")
    matchedPeriods: int = Field(description="Matched periods")
    actualPeriods: int = Field(description="Actual periods")
    coverage: float = Field(description="Coverage ratio (0.0 to 1.0)")
    status: str = Field(description="Data completeness status (e.g., complete, partial, no_data)")


class MonthAnalysisResponse(BaseModel):
    month: str = Field(description="Analyzed month (YYYY-MM)")
    cutoffTimeLondon: str = Field(description="Configured decision cutoff time (Europe/London)")
    cutoffAssumption: str = Field(description="Auditable statement of operational cutoff assumption")
    overallMetrics: MetricsSummary = Field(description="Aggregated month-to-date metrics")
    days: List[DaySummary] = Field(description="Daily summary series for trend analysis")


class HealthResponse(BaseModel):
    status: str = Field(description="Overall service health status ('ok')")
    timestamp: str = Field(description="Current server UTC timestamp")
    version: str = Field(default="1.0.0", description="Application version")
    cacheStatus: Dict[str, int] = Field(default_factory=dict, description="In-memory cache record counts")
