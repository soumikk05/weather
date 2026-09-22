"""
Meteorological Verification & Reliability Metrics Engine
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Implements official World Meteorological Organization (WMO) and operational
NWP verification standards for probabilistic and categorical forecast evaluation:
- Brier Score (BS) & Brier Skill Score (BSS vs Climatology)
- Expected Calibration Error (ECE) & Reliability Diagrams
- Critical Success Index (CSI / Threat Score) & Equitable Threat Score (ETS)
- Probability of Detection (POD / Recall), False Alarm Ratio (FAR), Precision, F1
- PR-AUC and ROC-AUC
- Continuous error metrics: MAE, RMSE, Mean Bias Error (MBE)
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, precision_recall_curve, auc, brier_score_loss


def compute_contingency_table(y_true: np.ndarray, y_pred_binary: np.ndarray) -> Dict[str, int]:
    """
    Compute 2x2 contingency table elements:
      - hits (H): true=1, pred=1
      - false_alarms (F): true=0, pred=1
      - misses (M): true=1, pred=0
      - correct_negatives (C): true=0, pred=0
    """
    y_t = np.asarray(y_true).astype(int)
    y_p = np.asarray(y_pred_binary).astype(int)

    h = int(np.sum((y_t == 1) & (y_p == 1)))
    f = int(np.sum((y_t == 0) & (y_p == 1)))
    m = int(np.sum((y_t == 1) & (y_p == 0)))
    c = int(np.sum((y_t == 0) & (y_p == 0)))

    return {"hits": h, "false_alarms": f, "misses": m, "correct_negatives": c, "total": len(y_t)}


def compute_brier_skill_score(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    climatological_prob: Optional[float] = None,
) -> Dict[str, float]:
    """
    Compute Brier Score and Brier Skill Score (BSS) relative to climatology.

    BSS = 1 - (BS / BS_reference)
    BSS > 0 indicates forecast possesses skill beyond simple historical frequency.
    """
    y_t = np.asarray(y_true).astype(float)
    y_p = np.clip(np.asarray(y_prob).astype(float), 0.0, 1.0)

    bs = float(np.mean((y_p - y_t) ** 2))

    # Reference climatology
    base_rate = float(np.mean(y_t)) if climatological_prob is None else climatological_prob
    # Reference Brier Score using static climatological probability
    bs_ref = float(np.mean((base_rate - y_t) ** 2))

    if bs_ref <= 1e-7:
        bss = 0.0  # degenerate case: no variance in true labels
    else:
        bss = 1.0 - (bs / bs_ref)

    return {
        "brier_score": round(bs, 5),
        "brier_reference": round(bs_ref, 5),
        "brier_skill_score": round(bss, 4),
        "climatological_rate": round(base_rate, 4),
    }


def compute_reliability_diagram_data(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> Dict[str, object]:
    """
    Compute bin statistics for reliability diagrams and Expected Calibration Error (ECE).

    Returns
    -------
    dict containing:
      bin_edges, bin_centers, mean_predicted_prob, empirical_observed_freq,
      sample_counts, expected_calibration_error (ECE), maximum_calibration_error (MCE)
    """
    y_t = np.asarray(y_true).astype(float)
    y_p = np.clip(np.asarray(y_prob).astype(float), 0.0, 1.0)
    total_n = len(y_t)

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_centers = 0.5 * (bins[:-1] + bins[1:])

    bin_pred_means = []
    bin_obs_freqs = []
    bin_counts = []
    ece = 0.0
    mce = 0.0

    for i in range(n_bins):
        low, high = bins[i], bins[i + 1]
        if i == n_bins - 1:
            mask = (y_p >= low) & (y_p <= high)
        else:
            mask = (y_p >= low) & (y_p < high)

        count = int(np.sum(mask))
        bin_counts.append(count)

        if count > 0:
            pred_mean = float(np.mean(y_p[mask]))
            obs_freq = float(np.mean(y_t[mask]))
            gap = abs(pred_mean - obs_freq)
            ece += (count / total_n) * gap
            mce = max(mce, gap)
        else:
            pred_mean = float(bin_centers[i])
            obs_freq = 0.0

        bin_pred_means.append(round(pred_mean, 4))
        bin_obs_freqs.append(round(obs_freq, 4))

    return {
        "bin_edges": [round(float(b), 3) for b in bins],
        "bin_centers": [round(float(b), 3) for b in bin_centers],
        "mean_pred_prob": bin_pred_means,
        "observed_freq": bin_obs_freqs,
        "sample_counts": bin_counts,
        "ece": round(float(ece), 4),
        "mce": round(float(mce), 4),
    }


def compute_meteorological_categorical_scores(
    y_true: np.ndarray,
    y_pred_binary: np.ndarray,
) -> Dict[str, float]:
    """
    Compute standard meteorological verification scores from contingency table:
    - Critical Success Index (CSI) / Threat Score
    - Equitable Threat Score (ETS) / Gilbert Skill Score
    - Probability of Detection (POD) / Hit Rate
    - False Alarm Ratio (FAR)
    - Precision, Recall, F1
    """
    ct = compute_contingency_table(y_true, y_pred_binary)
    h = ct["hits"]
    f = ct["false_alarms"]
    m = ct["misses"]
    c = ct["correct_negatives"]
    n = ct["total"]

    # Critical Success Index (Threat Score)
    denom_csi = h + f + m
    csi = (h / denom_csi) if denom_csi > 0 else 0.0

    # Equitable Threat Score (ETS)
    h_random = ((h + f) * (h + m)) / n if n > 0 else 0.0
    denom_ets = h + f + m - h_random
    ets = ((h - h_random) / denom_ets) if denom_ets > 0 else 0.0

    # Probability of Detection (Hit Rate / Recall)
    pod = (h / (h + m)) if (h + m) > 0 else 0.0

    # False Alarm Ratio (FAR)
    far = (f / (h + f)) if (h + f) > 0 else 0.0

    # Precision
    precision = (h / (h + f)) if (h + f) > 0 else 0.0

    # F1 score
    denom_f1 = precision + pod
    f1 = (2 * precision * pod / denom_f1) if denom_f1 > 0 else 0.0

    return {
        "hits": h,
        "false_alarms": f,
        "misses": m,
        "correct_negatives": c,
        "csi": round(csi, 4),
        "ets": round(ets, 4),
        "pod": round(pod, 4),
        "far": round(far, 4),
        "precision": round(precision, 4),
        "recall": round(pod, 4),
        "f1": round(f1, 4),
    }


def compute_continuous_error_metrics(
    y_true_continuous: np.ndarray,
    y_pred_continuous: np.ndarray,
) -> Dict[str, float]:
    """
    Compute continuous NWP forecast verification error metrics:
    - Mean Absolute Error (MAE)
    - Root Mean Square Error (RMSE)
    - Mean Bias Error (MBE): Positive = over-forecast, Negative = under-forecast
    - Pearson Correlation
    """
    yt = np.asarray(y_true_continuous).astype(float)
    yp = np.asarray(y_pred_continuous).astype(float)

    diff = yp - yt
    mae = float(np.mean(np.abs(diff)))
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    mbe = float(np.mean(diff))

    # Pearson correlation
    if np.std(yt) > 1e-6 and np.std(yp) > 1e-6:
        r = float(np.corrcoef(yt, yp)[0, 1])
    else:
        r = 0.0

    return {
        "mae": round(mae, 3),
        "rmse": round(rmse, 3),
        "mbe_bias": round(mbe, 3),
        "pearson_r": round(r, 4),
    }


def compute_comprehensive_evaluation(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    decision_threshold: float = 0.50,
) -> Dict[str, object]:
    """
    Run complete evaluation pipeline returning all probabilistic, calibration,
    and categorical verification metrics.
    """
    y_t = np.asarray(y_true).astype(int)
    y_p = np.asarray(y_prob).astype(float)
    y_pred_bin = (y_p >= decision_threshold).astype(int)

    # Probabilistic & Calibration
    bss_stats = compute_brier_skill_score(y_t, y_p)
    calib_stats = compute_reliability_diagram_data(y_t, y_p, n_bins=10)

    # Categorical Scores
    cat_scores = compute_meteorological_categorical_scores(y_t, y_pred_bin)

    # ROC & PR Curves
    try:
        roc_auc = float(roc_auc_score(y_t, y_p))
    except Exception:
        roc_auc = 0.5

    try:
        precs, recs, _ = precision_recall_curve(y_t, y_p)
        pr_auc = float(auc(recs, precs))
    except Exception:
        pr_auc = float(np.mean(y_t))

    return {
        "sample_size": len(y_t),
        "base_rate": bss_stats["climatological_rate"],
        "decision_threshold": decision_threshold,
        "brier_score": bss_stats["brier_score"],
        "brier_skill_score": bss_stats["brier_skill_score"],
        "expected_calibration_error": calib_stats["ece"],
        "max_calibration_error": calib_stats["mce"],
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "csi": cat_scores["csi"],
        "ets": cat_scores["ets"],
        "pod": cat_scores["pod"],
        "far": cat_scores["far"],
        "precision": cat_scores["precision"],
        "recall": cat_scores["recall"],
        "f1": cat_scores["f1"],
        "contingency": {
            "hits": cat_scores["hits"],
            "false_alarms": cat_scores["false_alarms"],
            "misses": cat_scores["misses"],
            "correct_negatives": cat_scores["correct_negatives"],
        },
        "reliability_diagram": calib_stats,
    }
