"""
Integration tests for FastAPI endpoints: request validation, error states, and response contracts.
"""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.elexon import ElexonAPIError

client = TestClient(app)


def test_health_endpoint():
    """Verify service readiness endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert "cacheStatus" in data


def test_invalid_date_in_february_returns_422():
    """
    Test: Invalid delivery date in February.
    Expected: HTTP 422 Unprocessable Entity with explicit reason.
    """
    response = client.get("/api/analysis?delivery_date=2026-02-01&cutoff_time=10:00")
    assert response.status_code == 422
    assert "out of scope" in response.json()["detail"].lower()


def test_malformed_date_returns_422():
    """
    Test: Malformed date string.
    Expected: HTTP 422.
    """
    response = client.get("/api/analysis?delivery_date=invalid-date&cutoff_time=10:00")
    assert response.status_code == 422
    assert "invalid date format" in response.json()["detail"].lower()


def test_invalid_cutoff_time_returns_422():
    """
    Test: Malformed cutoff time.
    Expected: HTTP 422.
    """
    response = client.get("/api/analysis?delivery_date=2026-01-10&cutoff_time=25:00")
    assert response.status_code == 422
    assert "invalid cutoff time" in response.json()["detail"].lower()


@patch("app.main.elexon_client.fetch_fuelhh_actuals")
def test_upstream_failure_returns_502(mock_fetch_fuelhh):
    """
    Test: Elexon responds with upstream error or is unreachable.
    Expected: HTTP 502 with visible diagnostic error, no fabricated metrics.
    """
    mock_fetch_fuelhh.side_effect = ElexonAPIError("Elexon upstream returned 500 Internal Server Error", status_code=502)

    response = client.get("/api/analysis?delivery_date=2026-01-05&cutoff_time=10:00")
    assert response.status_code == 502
    assert "upstream returned 500" in response.json()["detail"]


@patch("app.main.elexon_client.fetch_fuelhh_actuals")
@patch("app.main.elexon_client.fetch_windfor_vintages")
def test_valid_daily_analysis_mocked(mock_fetch_windfor, mock_fetch_fuelhh):
    """
    Verify complete daily analysis response contract with mocked Elexon records.
    """
    mock_fetch_fuelhh.return_value = [
        {"startTime": "2026-01-05T00:00:00Z", "settlementDate": "2026-01-05", "settlementPeriod": 1, "generation": 10000.0, "fuelType": "WIND"},
        {"startTime": "2026-01-05T01:00:00Z", "settlementDate": "2026-01-05", "settlementPeriod": 3, "generation": 12000.0, "fuelType": "WIND"}
    ]
    mock_fetch_windfor.return_value = [
        {"startTime": "2026-01-05T00:00:00Z", "publishTime": "2026-01-04T09:30:00Z", "generation": 10500.0},
        {"startTime": "2026-01-05T01:00:00Z", "publishTime": "2026-01-04T09:30:00Z", "generation": 11800.0}
    ]

    response = client.get("/api/analysis?delivery_date=2026-01-05&cutoff_time=10:00")
    assert response.status_code == 200
    data = response.json()

    assert data["deliveryDate"] == "2026-01-05"
    assert data["cutoffTimeLondon"] == "10:00"
    assert data["metrics"]["matchedPeriods"] == 2
    assert data["metrics"]["actualPeriods"] == 2
    assert data["metrics"]["coverage"] == 1.0
    assert data["metrics"]["mae"] == 350.0  # (|500| + |-200|) / 2 = 350.0
    assert data["metrics"]["bias"] == 150.0  # (500 + -200) / 2 = 150.0
    assert len(data["periods"]) == 2


@patch("app.main.elexon_client.fetch_fuelhh_actuals")
@patch("app.main.elexon_client.fetch_windfor_vintages")
def test_empty_dataset_returns_explicit_no_data_state(mock_fetch_windfor, mock_fetch_fuelhh):
    """
    Test 7 from Release Gate: Empty dataset produces explicit no-data/error state without crashing.
    """
    mock_fetch_fuelhh.return_value = []
    mock_fetch_windfor.return_value = []

    response = client.get("/api/analysis?delivery_date=2026-01-15&cutoff_time=10:00")
    assert response.status_code == 200
    data = response.json()

    assert data["deliveryDate"] == "2026-01-15"
    assert data["metrics"]["matchedPeriods"] == 0
    assert data["metrics"]["actualPeriods"] == 0
    assert data["metrics"]["coverage"] == 0.0
    assert data["metrics"]["mae"] is None
    assert data["metrics"]["rmse"] is None
    assert data["metrics"]["bias"] is None
    assert len(data["periods"]) == 0


@patch("app.main.elexon_client.fetch_fuelhh_actuals")
@patch("app.main.elexon_client.fetch_windfor_vintages")
def test_month_analysis_mocked(mock_fetch_windfor, mock_fetch_fuelhh):
    """
    Verify /api/month contract with mocked month data.
    """
    mock_fetch_fuelhh.return_value = [
        {"startTime": f"2026-01-{d:02d}T00:00:00Z", "settlementDate": f"2026-01-{d:02d}", "settlementPeriod": 1, "generation": 10000.0, "fuelType": "WIND"}
        for d in range(1, 32)
    ]
    mock_fetch_windfor.return_value = [
        {"startTime": f"2026-01-{d:02d}T00:00:00Z", "publishTime": "2025-12-31T09:30:00Z", "generation": 10200.0}
        for d in range(1, 32)
    ]

    response = client.get("/api/month?cutoff_time=10:00")
    assert response.status_code == 200
    data = response.json()

    assert data["month"] == "2026-01"
    assert len(data["days"]) == 31
    assert data["overallMetrics"]["matchedPeriods"] == 31
    assert data["overallMetrics"]["mae"] == 200.0
    assert data["overallMetrics"]["bias"] == 200.0

