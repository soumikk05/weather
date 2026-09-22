"""
Unit and Verification Tests for Meteorological Metrics & Reliability
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences
"""

import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.evaluation.metrics import (
    compute_contingency_table,
    compute_brier_skill_score,
    compute_reliability_diagram_data,
    compute_meteorological_categorical_scores,
    compute_continuous_error_metrics,
    compute_comprehensive_evaluation,
)


def test_contingency_table():
    """Verify 2x2 contingency table elements."""
    y_true = np.array([1, 1, 0, 0, 1, 0])
    y_pred = np.array([1, 0, 0, 1, 1, 0])
    # H: (1,1) -> 2
    # F: (0,1) -> 1
    # M: (1,0) -> 1
    # C: (0,0) -> 2
    ct = compute_contingency_table(y_true, y_pred)
    assert ct["hits"] == 2
    assert ct["false_alarms"] == 1
    assert ct["misses"] == 1
    assert ct["correct_negatives"] == 2
    assert ct["total"] == 6


def test_brier_skill_score():
    """Verify Brier Score and BSS relative to climatology."""
    # Perfect forecast
    y_true = np.array([1, 0, 1, 0, 0, 1, 0, 0])
    y_prob_perfect = np.array([1.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
    res_perfect = compute_brier_skill_score(y_true, y_prob_perfect)
    assert res_perfect["brier_score"] == 0.0
    assert res_perfect["brier_skill_score"] == 1.0

    # Climatology forecast (predict base rate everywhere)
    base_rate = np.mean(y_true)
    y_prob_clim = np.full_like(y_true, fill_value=base_rate, dtype=float)
    res_clim = compute_brier_skill_score(y_true, y_prob_clim)
    # BSS vs climatology should be 0.0
    assert abs(res_clim["brier_skill_score"]) < 1e-4


def test_reliability_diagram_and_ece():
    """Verify reliability diagram binning and Expected Calibration Error (ECE)."""
    # Perfectly calibrated forecast probabilities
    # 100 samples with prob 0.2 where exactly 20 are true
    # 100 samples with prob 0.8 where exactly 80 are true
    y_prob = np.array([0.2] * 100 + [0.8] * 100)
    y_true = np.array([1] * 20 + [0] * 80 + [1] * 80 + [0] * 20)

    res = compute_reliability_diagram_data(y_true, y_prob, n_bins=10)
    assert res["ece"] < 0.05
    assert len(res["bin_edges"]) == 11
    assert len(res["sample_counts"]) == 10


def test_meteorological_categorical_scores():
    """Verify CSI, ETS, POD, and FAR."""
    # Contingency: H=40, F=10, M=10, C=40, N=100
    y_true = np.array([1] * 40 + [0] * 10 + [1] * 10 + [0] * 40)
    y_pred = np.array([1] * 40 + [1] * 10 + [0] * 10 + [0] * 40)

    scores = compute_meteorological_categorical_scores(y_true, y_pred)
    # CSI = 40 / (40 + 10 + 10) = 40/60 = 0.6667
    assert abs(scores["csi"] - 0.6667) < 1e-3
    # POD = 40 / (40 + 10) = 0.80
    assert abs(scores["pod"] - 0.80) < 1e-3
    # FAR = 10 / (40 + 10) = 0.20
    assert abs(scores["far"] - 0.20) < 1e-3
    # Precision = 40 / (40 + 10) = 0.80
    assert abs(scores["precision"] - 0.80) < 1e-3
    # ETS should be strictly positive and <= CSI
    assert 0.0 < scores["ets"] <= scores["csi"]


def test_continuous_error_metrics():
    """Verify MAE, RMSE, MBE, and Pearson correlation."""
    y_obs = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    y_fcst = np.array([12.0, 22.0, 32.0, 42.0, 52.0])  # constant +2.0 mm bias

    metrics = compute_continuous_error_metrics(y_obs, y_fcst)
    assert metrics["mae"] == 2.0
    assert metrics["rmse"] == 2.0
    assert metrics["mbe_bias"] == 2.0
    assert metrics["pearson_r"] == 1.0


def test_comprehensive_evaluation_pipeline():
    """Verify unified evaluation pipeline produces all required fields."""
    y_true = np.array([0, 1, 0, 1, 0, 0, 1, 0, 1, 0])
    y_prob = np.array([0.1, 0.8, 0.2, 0.7, 0.3, 0.1, 0.9, 0.4, 0.85, 0.15])

    eval_results = compute_comprehensive_evaluation(y_true, y_prob, decision_threshold=0.5)

    required_keys = [
        "sample_size", "base_rate", "brier_score", "brier_skill_score",
        "expected_calibration_error", "roc_auc", "pr_auc", "csi", "ets",
        "pod", "far", "precision", "recall", "f1", "contingency", "reliability_diagram"
    ]
    for k in required_keys:
        assert k in eval_results, f"Missing key '{k}' in comprehensive evaluation"
    assert eval_results["sample_size"] == 10
    assert eval_results["roc_auc"] > 0.80
