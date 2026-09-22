"""
Automated Integration Tests for Forecast Bust Detection API
Smart India Hackathon - NCMRWF / Ministry of Earth Sciences
"""

import os
import sys
# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["subdivisions_count"] == 32
    assert data["models_loaded"] is True


def test_regions():
    response = client.get("/regions")
    assert response.status_code == 200
    regions = response.json()
    assert len(regions) == 32
    assert any(r["name"] == "Konkan & Goa" for r in regions)


def test_dates():
    response = client.get("/dates")
    assert response.status_code == 200
    dates = response.json()
    assert len(dates) > 0


def test_confidence_map():
    response = client.get("/confidence_map?lead_day=5")
    assert response.status_code == 200
    cmap = response.json()
    assert len(cmap) == 32
    first = cmap[0]
    assert "bust_probability" in first
    assert "confidence_score" in first
    assert "risk_tier" in first
    assert "plain_language_summary" in first
    assert 0.0 <= first["bust_probability"] <= 1.0
    assert 0.0 <= first["confidence_score"] <= 1.0


def test_region_forecast():
    response = client.get("/region/Odisha/forecast")
    assert response.status_code == 200
    timeline = response.json()
    assert len(timeline) == 10
    lead_days = [t["lead_day"] for t in timeline]
    assert lead_days == list(range(1, 11))


def test_explain_region():
    response = client.get("/explain/Odisha?lead_day=3")
    assert response.status_code == 200
    explanation = response.json()
    assert explanation["region"] == "Odisha"
    assert explanation["lead_day"] == 3
    assert "top_drivers" in explanation
    assert "plain_language_summary" in explanation


def test_predict_custom_scenario():
    payload = {
        "lead_day": 7,
        "region": "Konkan & Goa",
        "synoptic_regime": "cyclonic_disturbance",
        "ensemble_spread": 12.5,
        "pressure_gradient_hpa": 14.0,
        "wind_shear_mps": 22.0,
        "moisture_convergence": 11.0,
        "terrain": "Western_Ghats",
        "terrain_difficulty": 0.78,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert "prediction" in result
    pred = result["prediction"]
    assert "bust_probability" in pred
    assert "confidence_score" in pred
    assert "risk_tier" in pred
    assert "plain_language_summary" in pred
    # Severe cyclonic disturbance with high spread at day 7 should yield high bust probability
    assert pred["bust_probability"] > 0.5
    assert pred["risk_tier"] == "Low Confidence - Bust Risk"
