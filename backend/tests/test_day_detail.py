"""
Unit and Integration Tests for Day Detail & Sub-Daily Honesty Endpoint
Forecast Bust Detection System — NCMRWF / Ministry of Earth Sciences

Covers:
- GET /region/{region}/day_detail
- Daily-only granularity verification ("granularity": "daily")
- Explicit caveat note regarding absence of sub-daily observations
- Illustrative diurnal hourly curve with mandatory "is_illustrative": True flags
- Evidence agreement and contradiction flags
- Diagnostic ERA5 and NWP forecast fields
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app

client = TestClient(app)


def test_day_detail_endpoint_daily_honesty():
    """
    STRICT SUB-DAILY HONESTY TEST:
    Verifies that the day detail endpoint does NOT claim to provide real hourly forecasts,
    explicitly sets granularity='daily', carries the mandatory caveat note, and flags
    any intraday curve with is_illustrative=True.
    """
    response = client.get("/region/Odisha/day_detail?lead_day=1")
    assert response.status_code == 200
    data = response.json()

    # 1. Mandatory Daily Granularity declaration
    assert data["granularity"] == "daily"
    assert "sub-daily detail is not available" in data["note"].lower()
    assert "full daily verification record" in data["note"].lower()

    # 2. Illustrative curve flags
    assert data["is_illustrative"] is True
    assert "illustrative_note" in data
    assert "synthetic diurnal interpolation" in data["illustrative_note"].lower()

    hourly_curve = data["illustrative_hourly_curve"]
    assert isinstance(hourly_curve, list)
    assert len(hourly_curve) == 24

    for pt in hourly_curve:
        assert pt["is_illustrative"] is True
        assert 0 <= pt["hour"] <= 23
        assert "time_utc" in pt
        assert "temp_c" in pt
        assert "rainfall_mm" in pt


def test_day_detail_full_verification_fields():
    """Verify all forecast, ground truth, and diagnostic fields are populated."""
    response = client.get("/region/Haryana,%20Chandigarh%20&%20Delhi/day_detail?lead_day=1")
    assert response.status_code == 200
    data = response.json()

    # Model confidence & calibration
    assert 0.0 <= data["bust_probability"] <= 1.0
    assert 0.0 <= data["confidence_score"] <= 1.0
    assert "risk_tier" in data
    assert 0.0 <= data["evidence_agreement"] <= 1.0
    assert isinstance(data["contradiction_flag"], bool)

    # Forecast and observation fields
    assert "forecast_rainfall_mm" in data
    assert "forecast_temp_2m_c" in data
    assert "conformal_interval_mm" in data
    assert "top_drivers" in data
    assert "operational_bulletin" in data
    assert "plain_language_summary" in data

    # ERA5 diagnostic fields dictionary
    assert "era5_diagnostics" in data
    assert isinstance(data["era5_diagnostics"], dict)


def test_day_detail_validation_limits():
    """Verify input validation for day_detail endpoint."""
    # Invalid lead_day
    res_high_lead = client.get("/region/Odisha/day_detail?lead_day=12")
    assert res_high_lead.status_code == 422

    res_zero_lead = client.get("/region/Odisha/day_detail?lead_day=0")
    assert res_zero_lead.status_code == 422

    # Nonexistent region
    res_404 = client.get("/region/NonExistentProvince/day_detail")
    assert res_404.status_code == 404
