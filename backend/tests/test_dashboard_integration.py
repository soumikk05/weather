"""
Tests for Stage 8: API and Dashboard Integration Integrity
Validates that inference engine outputs conform to the dashboard specifications:
- Conformal prediction intervals
- Operational advisory bulletins (GREEN, AMBER, RED)
- 8 Feature families attribution breakdown
- Metrics and baseline structure for verification tab
"""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.inference import get_engine
from src.data.schema import SUBDIVISIONS


@pytest.fixture(scope="module")
def engine():
    return get_engine()


def test_confidence_map_stage8_fields(engine):
    cmap = engine.get_confidence_map(lead_day=5)
    assert len(cmap) == len(SUBDIVISIONS)
    sample = cmap[0]
    
    assert "conformal_interval_mm" in sample
    assert isinstance(sample["conformal_interval_mm"], list)
    assert len(sample["conformal_interval_mm"]) == 2
    assert sample["conformal_interval_mm"][0] <= sample["conformal_interval_mm"][1]
    
    assert "operational_bulletin" in sample
    assert "advisory_level" in sample["operational_bulletin"]
    assert any(sample["operational_bulletin"]["advisory_level"].startswith(lvl) for lvl in ["GREEN", "AMBER", "RED"])
    
    assert "top_families" in sample
    assert len(sample["top_families"]) > 0


def test_region_forecast_conformal_bounds(engine):
    region_name = SUBDIVISIONS[0].name
    timeline = engine.get_region_forecast(region_name=region_name)
    assert len(timeline) == 10
    
    for row in timeline:
        assert "error_interval_90_lower" in row
        assert "error_interval_90_upper" in row
        assert row["error_interval_90_lower"] <= row["error_interval_90_upper"]
        assert "operational_bulletin" in row
        assert "top_families" in row


def test_predict_custom_stage8_contract(engine):
    payload = {
        "lead_day": 7,
        "region": "Konkan & Goa",
        "synoptic_regime": "cyclonic_disturbance",
        "ensemble_spread": 14.5,
        "wind_shear_mps": 24.0,
        "terrain": "Western_Ghats",
    }
    res = engine.predict_custom(payload)
    
    assert "conformal_interval_mm" in res
    assert "error_interval_90_lower" in res
    assert "error_interval_90_upper" in res
    assert res["error_interval_90_lower"] <= res["error_interval_90_upper"]
    
    assert "operational_bulletin" in res
    bulletin = res["operational_bulletin"]
    assert bulletin["advisory_level"].startswith("RED")
    assert "primary_escalator" in bulletin
    assert "primary_stabilizer" in bulletin
    assert "recommendation" in bulletin
    
    assert "top_families" in res
    assert len(res["top_families"]) == 8
    shares = [f["percentage_share"] for f in res["top_families"]]
    assert 99.0 <= sum(shares) <= 101.0


def test_metrics_json_baseline_structure():
    metrics_path = os.path.join(os.path.dirname(__file__), "..", "models", "metrics.json")
    assert os.path.exists(metrics_path)
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
    
    assert "overall" in metrics
    overall = metrics["overall"]
    assert "brier_skill_score" in overall
    assert overall["brier_skill_score"] > 0.50
    assert "conformal_90_coverage" in overall
    assert 0.80 <= overall["conformal_90_coverage"] <= 0.95
    assert "expected_calibration_error" in overall
    assert overall["expected_calibration_error"] < 0.02
    
    assert "baselines" in metrics
    baselines = metrics["baselines"]
    assert "Integrated_Model_Calibrated" in baselines
    assert "Baseline_1_Climatology" in baselines
    assert baselines["Integrated_Model_Calibrated"]["pr_auc"] > baselines["Baseline_1_Climatology"]["pr_auc"] * 5
