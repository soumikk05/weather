"""
Integration and Temporal Causality Tests for Verification History Endpoint
Forecast Bust Detection System — NCMRWF / Ministry of Earth Sciences

Covers:
- GET /region/{region}/history
- GET /region/{region}/history/summary
- Calibration verdict derivation logic (4 quadrants)
- Validation constraints (days <= 30, lead_day 1-10, 422 errors)
- Strict temporal causality and zero leakage verification
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app
from src.inference import get_engine

client = TestClient(app)


def test_history_endpoint_structure():
    """Verify history endpoint returns correct schema, fields, and types."""
    response = client.get("/region/Odisha/history?days=10&lead_day=1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 10

    required_fields = [
        "date",
        "lead_day",
        "forecast_rainfall_mm",
        "forecast_temp_2m_c",
        "observed_rainfall_mm",
        "observed_temp_2m_c",
        "forecast_error_mm",
        "abs_error_mm",
        "bust_threshold_mm",
        "was_bust",
        "confidence_at_issue_time",
        "bust_probability",
        "risk_tier",
        "calibration_verdict",
        "evidence_agreement",
        "contradiction_flag",
    ]

    for item in data:
        for f in required_fields:
            assert f in item, f"Missing required field '{f}' in history response item"
        assert item["lead_day"] == 1
        assert 0.0 <= item["confidence_at_issue_time"] <= 1.0
        assert 0.0 <= item["bust_probability"] <= 1.0
        assert 0.0 <= item["evidence_agreement"] <= 1.0
        assert isinstance(item["was_bust"], bool)
        assert isinstance(item["contradiction_flag"], bool)


def test_calibration_verdict_derivation():
    """
    Verify calibration_verdict derivation adheres strictly to the 4 operational quadrants:
    1. flagged_risky_and_busted: High risk flagged, bust occurred (True Positive Alert)
    2. flagged_risky_no_bust: High risk flagged, no bust occurred (False Alarm)
    3. confident_but_busted: Model confident, bust occurred (False Negative / Missed Bust)
    4. confident_correct: Model confident, no bust occurred (True Negative)
    """
    response = client.get("/region/Haryana,%20Chandigarh%20&%20Delhi/history?days=20&lead_day=1")
    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0

    valid_verdicts = {
        "confident_correct",
        "confident_but_busted",
        "flagged_risky_and_busted",
        "flagged_risky_no_bust",
    }

    for item in items:
        verdict = item["calibration_verdict"]
        assert verdict in valid_verdicts

        is_flagged_risky = (item["risk_tier"] == "Low Confidence - Bust Risk") or (item["bust_probability"] >= 0.50 or item["confidence_at_issue_time"] <= 0.40)
        was_bust = item["was_bust"]

        if is_flagged_risky:
            expected = "flagged_risky_and_busted" if was_bust else "flagged_risky_no_bust"
        else:
            expected = "confident_but_busted" if was_bust else "confident_correct"

        assert verdict == expected, f"Verdict mismatch: got {verdict}, expected {expected} (flagged={is_flagged_risky}, bust={was_bust})"


def test_history_summary_endpoint():
    """Verify GET /region/{region}/history/summary returns expected aggregates."""
    response = client.get("/region/Odisha/history/summary?days=10&lead_day=1")
    assert response.status_code == 200
    summary = response.json()

    assert summary["region"] == "Odisha"
    assert summary["days"] == 10
    assert summary["lead_day"] == 1
    assert "as_of" in summary
    assert "counts_per_calibration_verdict" in summary
    counts = summary["counts_per_calibration_verdict"]

    assert sum(counts.values()) == 10
    assert 0.0 <= summary["overall_bust_rate"] <= 1.0
    assert summary["mean_abs_error"] >= 0.0
    assert len(summary["summary_sentence"]) > 20


def test_history_input_validation_422():
    """Verify validation boundaries: days <= 30 and lead_day in [1, 10] return 422 on invalid input."""
    # Exceeding maximum days limit (days=31)
    res_high_days = client.get("/region/Odisha/history?days=31")
    assert res_high_days.status_code == 422

    # Zero or negative days
    res_zero_days = client.get("/region/Odisha/history?days=0")
    assert res_zero_days.status_code == 422

    # Invalid lead day
    res_high_lead = client.get("/region/Odisha/history?lead_day=15")
    assert res_high_lead.status_code == 422

    res_zero_lead = client.get("/region/Odisha/history?lead_day=0")
    assert res_zero_lead.status_code == 422

    # Summary endpoint validation
    res_summ_high = client.get("/region/Odisha/history/summary?days=35")
    assert res_summ_high.status_code == 422


def test_nonexistent_region_404():
    """Verify 404 is raised when querying a non-existent region."""
    res_hist = client.get("/region/NonExistentProvince123/history?days=5")
    assert res_hist.status_code == 404

    res_summ = client.get("/region/NonExistentProvince123/history/summary?days=5")
    assert res_summ.status_code == 404


def test_history_zero_temporal_leakage():
    """
    STRICT ZERO-LEAKAGE VERIFICATION:
    Verifies that confidence_at_issue_time for a historical record:
    1. Uses strictly the features available at initialization_time.
    2. Exactly matches a point-in-time isolated transformation of that single row.
    3. Does NOT change when subsequent future rows are removed from the dataset.
    """
    engine = get_engine()
    region = "Haryana, Chandigarh & Delhi"
    lead_day = 1

    # Fetch 10 history items
    history = engine.get_region_history(region_name=region, days=10, lead_day=lead_day)
    assert len(history) >= 2

    # Select an evaluation row in the middle of the history
    eval_item = history[3]
    eval_date = eval_item["date"]
    issue_conf = eval_item["confidence_at_issue_time"]
    issue_bust_prob = eval_item["bust_probability"]

    # Extract the raw row corresponding to eval_date from engine dataset
    df = engine.data_df
    time_col = "valid_time" if "valid_time" in df.columns else "date"
    raw_row = df[
        (df["region"] == region)
        & (df["lead_day"] == lead_day)
        & (df[time_col].astype(str) == eval_date)
    ]
    assert len(raw_row) == 1

    # 1. Transform single isolated row with zero knowledge of surrounding rows
    X_single = engine.fe.transform(raw_row)
    single_prob = float(engine.calibrator.predict_calibrated_proba(X_single)[0])
    single_conf = float(engine.calibrator.predict_confidence(X_single)[0])

    assert np.isclose(issue_bust_prob, round(single_prob, 4), atol=1e-4), (
        f"Leakage detected: bust_probability {issue_bust_prob} differs from isolated calculation {single_prob}"
    )
    assert np.isclose(issue_conf, round(single_conf, 4), atol=1e-4), (
        f"Leakage detected: confidence_at_issue_time {issue_conf} differs from isolated calculation {single_conf}"
    )

    # 2. Simulate temporal truncation: remove all future records after eval_date
    df_truncated = df[pd.to_datetime(df[time_col]) <= pd.to_datetime(eval_date)].copy()
    raw_row_trunc = df_truncated[
        (df_truncated["region"] == region)
        & (df_truncated["lead_day"] == lead_day)
        & (df_truncated[time_col].astype(str) == eval_date)
    ]
    X_trunc = engine.fe.transform(raw_row_trunc)
    trunc_prob = float(engine.calibrator.predict_calibrated_proba(X_trunc)[0])
    trunc_conf = float(engine.calibrator.predict_confidence(X_trunc)[0])

    assert np.isclose(issue_bust_prob, round(trunc_prob, 4), atol=1e-4), (
        "Temporal leakage detected: bust probability changed when future records were truncated!"
    )
    assert np.isclose(issue_conf, round(trunc_conf, 4), atol=1e-4), (
        "Temporal leakage detected: confidence score changed when future records were truncated!"
    )
