"""
Evaluation & Verification Framework
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Provides:
  - Meteorological verification metrics: Brier Skill Score, ECE, CSI, ETS, POD, FAR
  - Reliability diagrams & Expected Calibration Error calculation
  - Continuous NWP verification: MAE, RMSE, Mean Bias Error (MBE)
  - Full evaluation pipeline
"""

from src.evaluation.metrics import (
    compute_contingency_table,
    compute_brier_skill_score,
    compute_reliability_diagram_data,
    compute_meteorological_categorical_scores,
    compute_continuous_error_metrics,
    compute_comprehensive_evaluation,
)

__all__ = [
    "compute_contingency_table",
    "compute_brier_skill_score",
    "compute_reliability_diagram_data",
    "compute_meteorological_categorical_scores",
    "compute_continuous_error_metrics",
    "compute_comprehensive_evaluation",
]
