"""
Unit and Integration Tests for Stage 7: Explainability Layer
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.explain import (
    ForecastExplainer,
    FEATURE_MET_TRANSLATION,
    FEATURE_MET_STABILIZING,
    FAMILY_FRIENDLY_NAMES,
)


@pytest.fixture(scope="module")
def explainer():
    """Initializes the ForecastExplainer singleton fixture."""
    return ForecastExplainer(model_dir="models")


@pytest.fixture
def sample_raw_record():
    """Returns a realistic single verification record in canonical schema."""
    return pd.DataFrame([{
        "initialization_time": "2024-07-15 00:00:00",
        "valid_time": "2024-07-22 00:00:00",
        "lead_day": 7,
        "location_id": "Konkan & Goa",
        "lat": 15.5,
        "lon": 73.8,
        "model_version": "NCUM_v3.2",
        "data_source": "synthetic",
        "fcst_rainfall_mm": 65.0,
        "fcst_temp_2m_c": 28.5,
        "fcst_mslp_hpa": 998.0,
        "fcst_wind_850_mps": 24.0,
        "fcst_wind_200_mps": 28.0,
        "fcst_rh_700_pct": 88.0,
        "fcst_geopot_500_m": 5820.0,
        "fcst_cape_jkg": 2400.0,
        "ens_spread_rainfall": 14.5,
        "ens_spread_temp": 1.5,
        "ens_spread_mslp": 3.0,
        "ens_members_total": 50,
        "ens_members_rain_gt10": 42,
        "ens_members_rain_gt50": 26,
        "prior_day_verified_error": 22.0,
        "recent_error_bias_30d": 4.5,
        "recent_error_mae_30d": 16.0,
        "recent_error_bust_freq_30d": 0.25,
        "recent_error_mae_7d": 18.0,
        "fcst_rainfall_yesterday_lead_plus_1": 45.0,
        "fcst_mslp_yesterday_lead_plus_1": 1002.0,
        "fcst_rainfall_lead_prev": 50.0,
        "analog_min_distance": 2.8,
        "analog_mean_error_mm": 18.5,
        "analog_bust_probability": 0.35,
        "synoptic_regime": "cyclonic_disturbance",
        "enso_oni": 0.8,
        "mjo_amplitude": 1.9,
        "mjo_phase": 4,
        "iod_dmi": 0.3,
        "era5_sst_c": 29.8,
        "cyclone_active_flag": 1,
        "cyclone_distance_km": 120.0,
        "cyclone_intensity_kt": 65.0,
        "elevation_m": 450.0,
        "dist_coast_km": 15.0,
        "land_fraction": 0.85,
        "terrain_type": "Western_Ghats",
        "terrain_complexity": 0.78,
    }])


def test_lexicon_coverage_against_feature_pipeline(explainer):
    """Verify that every feature produced by the FeaturePipeline has a human-readable translation."""
    feature_names = explainer.feature_names
    assert len(feature_names) >= 50

    missing_translations = [f for f in feature_names if f not in FEATURE_MET_TRANSLATION]
    assert len(missing_translations) == 0, f"Features missing from FEATURE_MET_TRANSLATION: {missing_translations}"


def test_explain_instance_structure(explainer, sample_raw_record):
    """Verify explain_instance outputs all expected contract keys with correct types."""
    res = explainer.explain_instance(sample_raw_record, top_k_families=3)

    assert "plain_language_summary" in res
    assert isinstance(res["plain_language_summary"], str)
    assert len(res["plain_language_summary"]) > 20

    assert "top_families" in res
    assert isinstance(res["top_families"], list)
    assert len(res["top_families"]) == 8

    assert "top_drivers" in res
    assert len(res["top_drivers"]) > 0

    assert "all_attributions" in res
    assert len(res["all_attributions"]) > 0

    assert "operational_bulletin" in res
    bulletin = res["operational_bulletin"]
    assert "advisory_level" in bulletin
    assert "operational_recommendation" in bulletin
    assert any(tier in bulletin["advisory_level"] for tier in ["GREEN", "AMBER", "RED"])


def test_no_raw_snake_case_leaks(explainer, sample_raw_record):
    """Ensure plain-language summary does not leak raw snake_case feature names to forecasters."""
    res = explainer.explain_instance(sample_raw_record)
    summary = res["plain_language_summary"]

    forbidden_patterns = [
        "fcst_rainfall_mm",
        "vertical_wind_shear",
        "ens_spread_rainfall",
        "spread_lead_interaction",
        "recent_error_mae_30d",
        "cyclone_intensity_kt",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in summary, f"Raw feature name '{pattern}' leaked into plain-language summary!"


def test_family_percentage_shares(explainer, sample_raw_record):
    """Verify that family percentage shares are non-negative and sum to ~100%."""
    res = explainer.explain_instance(sample_raw_record)
    top_families = res["top_families"]

    total_pct = sum(f["percentage_share"] for f in top_families)
    assert 98.0 <= total_pct <= 102.0, f"Percentage shares sum to {total_pct}%, expected ~100%"

    for fam in top_families:
        assert fam["percentage_share"] >= 0.0
        assert fam["family_name"] in FAMILY_FRIENDLY_NAMES.values()


def test_explain_dataset_batch(explainer, sample_raw_record):
    """Verify batch dataset explanation computes global family rankings."""
    # Create a small batch
    batch_df = pd.concat([sample_raw_record] * 5, ignore_index=True)
    batch_res = explainer.explain_dataset(batch_df, sample_size=5)

    assert "family_ranking" in batch_res
    ranking = batch_res["family_ranking"]
    assert len(ranking) == 8

    total_importance = sum(r["percentage_importance"] for r in ranking)
    assert 98.0 <= total_importance <= 102.0
