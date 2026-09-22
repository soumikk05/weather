"""
End-to-End Pipeline Unit & Verification Tests
Smart India Hackathon - NCMRWF / Ministry of Earth Sciences
"""

import os
import sys
# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import pytest

from src.explain import ForecastExplainer
from src.features import FeatureEngineer
from src.generate_synthetic_data import SUBDIVISIONS, SyntheticDataLoader
from src.inference import get_engine


def test_subdivisions_metadata():
    assert len(SUBDIVISIONS) >= 28
    for sub in SUBDIVISIONS:
        assert "name" in sub
        assert "lat" in sub and 6.0 <= sub["lat"] <= 38.0
        assert "lon" in sub and 65.0 <= sub["lon"] <= 98.0
        assert "terrain" in sub
        assert "terrain_difficulty" in sub and 0.0 <= sub["terrain_difficulty"] <= 1.0


def test_synthetic_data_loader_structure():
    loader = SyntheticDataLoader(random_seed=123)
    # Load 4 days of data to test generator logic quickly
    df = loader.load_data(start_date="2024-06-01", end_date="2024-06-04")
    
    required_cols = [
        "date", "region", "lat", "lon", "terrain", "terrain_difficulty",
        "synoptic_regime", "lead_day", "ensemble_spread", "pressure_gradient_hpa",
        "wind_shear_mps", "moisture_convergence", "enso_oni_index", "mjo_amplitude",
        "mjo_phase", "surface_temp_c", "cape_jkg", "prior_day_error",
        "forecast_error", "is_bust"
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing column {col} in synthetic data"
        
    assert set(df["lead_day"].unique()) == set(range(1, 11))
    assert df["is_bust"].isin([0, 1]).all()
    assert (df["forecast_error"] > 0).all()


def test_feature_engineering_pipeline():
    fe = FeatureEngineer()
    sample_record = {
        "date": "2024-07-15",
        "region": "Konkan & Goa",
        "lat": 16.0,
        "lon": 73.8,
        "terrain": "Western_Ghats",
        "terrain_difficulty": 0.78,
        "synoptic_regime": "monsoon_depression",
        "lead_day": 5,
        "ensemble_spread": 8.4,
        "pressure_gradient_hpa": 7.5,
        "wind_shear_mps": 14.0,
        "moisture_convergence": 9.0,
        "enso_oni_index": 0.4,
        "mjo_amplitude": 1.2,
        "mjo_phase": 4,
        "surface_temp_c": 29.5,
        "cape_jkg": 2100.0,
        "prior_day_error": 16.0,
    }
    X = fe.transform_single_record(sample_record)
    assert len(X) == 1
    assert len(X.columns) == len(fe.feature_names)
    assert "spread_lead_interaction" in X.columns
    assert "shear_moisture_interaction" in X.columns
    assert "baroclinic_instability" in X.columns
    assert X["spread_lead_interaction"].iloc[0] == pytest.approx(8.4 * 5, rel=1e-3)


def test_explainability_natural_language():
    explainer = ForecastExplainer(model_dir="models")
    fe = FeatureEngineer()
    sample_record = {
        "date": "2024-07-15",
        "region": "Odisha",
        "lat": 20.3,
        "lon": 85.8,
        "terrain": "Coastal_Plains",
        "terrain_difficulty": 0.62,
        "synoptic_regime": "monsoon_depression",
        "lead_day": 7,
        "ensemble_spread": 12.0,
        "pressure_gradient_hpa": 12.0,
        "wind_shear_mps": 20.0,
        "moisture_convergence": 11.0,
        "enso_oni_index": 0.8,
        "mjo_amplitude": 1.8,
        "mjo_phase": 4,
        "surface_temp_c": 31.0,
        "cape_jkg": 2600.0,
        "prior_day_error": 22.0,
    }
    X = fe.transform_single_record(sample_record)
    res = explainer.explain_instance(X, top_k=3)
    
    assert "plain_language_summary" in res
    assert "top_drivers" in res
    assert len(res["top_drivers"]) > 0
    # Ensure no raw snake_case feature name leaked to user
    summary = res["plain_language_summary"]
    assert "pressure_gradient_hpa" not in summary
    assert "spread_lead_interaction" not in summary
    assert "moisture_convergence" not in summary


def test_inference_engine_contract():
    engine = get_engine()
    dates = engine.get_available_dates()
    assert len(dates) > 0

    # 1. Test Confidence Map
    cmap = engine.get_confidence_map(lead_day=3)
    assert len(cmap) == 32
    for item in cmap:
        assert item["lead_day"] == 3
        assert 0.0 <= item["bust_probability"] <= 1.0
        assert 0.0 <= item["confidence_score"] <= 1.0
        assert item["risk_tier"] in ["High Confidence", "Moderate Confidence", "Low Confidence - Bust Risk"]

    # 2. Test Region Timeline
    timeline = engine.get_region_forecast(region_name="Kerala & Mahe")
    assert len(timeline) == 10
    for idx, point in enumerate(timeline, start=1):
        assert point["lead_day"] == idx

    # 3. Test Custom Prediction
    custom_pred = engine.predict_custom({
        "lead_day": 8,
        "synoptic_regime": "cyclonic_disturbance",
        "ensemble_spread": 15.0,
        "pressure_gradient_hpa": 18.0,
        "wind_shear_mps": 25.0,
        "moisture_convergence": 14.0,
    })
    assert custom_pred["bust_probability"] > 0.5
    assert custom_pred["risk_tier"] == "Low Confidence - Bust Risk"
