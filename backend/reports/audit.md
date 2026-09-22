# Stage 0 — Full Repository Audit

**Auditor**: AI ML Engineer
**Date**: 2026-09-22
**Repo**: `Rainfall_bust_2` — "AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts"

---

## 1. Inventory of What Exists

| File | Purpose | Lines | Status |
|:-----|:--------|------:|:-------|
| `src/generate_synthetic_data.py` | Synthetic data generation for 32 subdivisions × 10 lead days | 325 | **CIRCULAR — see §2** |
| `src/features.py` | Feature engineering (36 features) + chronological split | 185 | Functional but incomplete |
| `src/train_model.py` | XGBoost classifier + isotonic calibration + error regressor | 297 | Works, but metrics are meaningless (§2) |
| `src/inference.py` | Unified inference engine (confidence map, region forecast, what-if) | 254 | Functional |
| `src/explain.py` | SHAP TreeExplainer + meteorological lexicon translation | 194 | Functional |
| `api/main.py` | FastAPI backend (6 endpoints) | 225 | Functional |
| `dashboard/app.py` | Streamlit dashboard (4 tabs, ~1000 lines) | 997 | Functional but displays misleading metrics |
| `tests/test_api.py` | API integration tests (7 tests) | 96 | Passes |
| `tests/test_pipeline.py` | Pipeline unit tests (6 tests) | 149 | Passes |
| `launch.py` | One-click launcher (API + Streamlit) | 66 | Functional |
| `requirements.txt` | Dependencies (unpinned) | 14 | Missing lightgbm, xarray, etc. |
| `README.md` | Project documentation | 194 | **Contains unsupported claims — see §3** |
| `models/*.joblib` | Persisted model artifacts (4 files) | — | **Git-tracked (should not be)** |
| `models/metrics.json` | Persisted evaluation metrics | 376 | Git-tracked; metrics are circular |
| `data/nwp_forecast_bust_dataset.csv` | Synthetic dataset (175,360 rows, 24 MB) | — | Should not be committed |
| `.gitignore` | Ignore rules | 5 | **Incomplete** — does not exclude models/, data/, or reports/ |

---

## 2. Critical Problem: Circular Data Generation (Fatal Flaw)

### 2.1 The Circularity

In `generate_synthetic_data.py`, `forecast_error` is computed as a **deterministic function** of the exact columns that become model features:

```python
disturbance_component = (
    0.40 * ensemble_spread
    + 0.32 * pressure_gradient
    + 0.25 * wind_shear
    + 0.42 * moisture_convergence
    + 0.0018 * cape
)
terrain_penalty = 8.5 * t_diff * (lead_day / 5.0)
inertia_penalty = 0.20 * prior_error
climate_modulation = 1.0 + 0.10 * abs(d_enso) + 0.12 * (d_mjo_amp ...)

total_error = (predictability_decay + disturbance_component + terrain_penalty + inertia_penalty)
              * regime_mult * climate_modulation + noise(0, 3.5)
```

Then `is_bust = 1 if forecast_error > threshold(lead_day)`.

**The model is given the exact formula inputs and asked to recover the formula output.** XGBoost can trivially approximate this polynomial with near-zero error.

### 2.2 Consequences Visible in the Metrics

| Symptom | Value | Expected in Reality |
|:--------|:------|:--------------------|
| Overall bust rate | 33.8% (42% in test) | ~8-15% for well-calibrated NWP |
| PR-AUC | 0.9992 | 0.3–0.7 would be excellent |
| Brier Score | 0.0056 | 0.05–0.15 realistic |
| R² (error regressor) | 0.9908 | 0.2–0.5 realistic |
| Active Monsoon bust rate | 100.0% | ~20–40% |
| Cyclonic Disturbance bust rate | 100.0% | ~30–50% |
| Western Disturbance bust rate | 99.97% | ~25–45% |
| `regime_quiescent_clear` feature importance | **0.711** (71%) | Should not dominate — it's a proxy for the formula |
| Day 8–9 PR-AUC | 1.0000 | Physically impossible for Day 8–9 predictions |

The regime one-hot is the #1 feature because `regime_mult` enters the error formula **multiplicatively** — knowing the regime is nearly sufficient to predict the error.

### 2.3 Bust Threshold Problem

The bust threshold is `16.5 + 4.6 * lead_day^1.05`, which:
- Depends only on `lead_day`, not on location or season
- Is fixed across all regions (flat 16.5 mm tolerance for J&K vs. Konkan is meteorologically absurd)
- Produces pathological bust rates: 100% for all "stormy" regimes, ~0.9% for "quiescent_clear"

---

## 3. Unsupported Claims in README

| Claim (README line) | Problem |
|:-----|:--------|
| "PR-AUC: **0.9992**" | Circular — model recovers its own formula |
| "Brier score: **0.0056** (near-perfect calibration)" | Calibration of a circular model is meaningless |
| "$R^2$: 0.9908" | Same circularity |
| "100% bust rate for Active Monsoon / Cyclonic / Depression" | Artifact of the formula, not a real finding |
| "Evaluated strictly on holdout chronological test data" | Chronological split is correct but irrelevant when the error formula is stationary |
| "zero changes to downstream ... modules" when switching to real data | False — the feature set is designed for the formula; real data will have entirely different features |
| Dashboard pitch tab: "Brier score: 0.0056" hard-coded | Hard-coded metric, not read from metrics.json |

---

## 4. Feature Engineering Gaps

### 4.1 What Exists (36 features in `features.py`)

- 12 base numerical: lead_day, terrain_difficulty, ensemble_spread, pressure_gradient, wind_shear, moisture_convergence, ENSO ONI, MJO amplitude, MJO phase, surface_temp, CAPE, prior_day_error
- 6 engineered interactions: spread×lead, shear×moisture, baroclinic (PG×shear), convective vulnerability, spread/lead ratio, dynamic instability index
- 2 seasonal: month_sin, month_cos
- 8 regime one-hots + 8 terrain one-hots

### 4.2 What Is Missing (Required by Spec)

| Feature Family | Status | Notes |
|:---------------|:-------|:------|
| **nwp_state_evolution** | ❌ Missing | No Day-to-Day change features, no persistence-consistency, no stability flags |
| **uncertainty** (ensemble) | ⚠️ Partial | Only `ensemble_spread`; no ensemble rainfall agreement, no multi-model spread |
| **recent_error** (30-day verified) | ❌ Missing | Only `prior_day_error` (single lag); no rolling 30-day bias/MAE/bust frequency with proper initialization-time lag |
| **run_consistency** | ❌ Missing | No run-to-run forecast change tracking |
| **seasonal_context** | ⚠️ Minimal | Only sin/cos month encoding; no location-specific season calendar, no monsoon onset/withdrawal anomaly, no days-to-transition, no regime-shift signal |
| **analog_regime** | ❌ Missing | No historical analog search, no K-means/GMM regimes |
| **spatial_ocean_large_scale** | ❌ Missing | No upstream moisture, no SST, no cyclone distance/intensity, no MJO phase interaction with Indian regions, no monsoon trough position |
| **static_geography** | ⚠️ Partial | terrain_difficulty and one-hots exist, but no elevation, distance-to-coast, or land-sea mask |
| Feature family tagging | ❌ Missing | No family labels for grouped SHAP or ablation |

---

## 5. Model & Evaluation Gaps

| Component | Status |
|:----------|:-------|
| LightGBM option | ❌ Missing (spec requires LightGBM as primary) |
| Baselines (climatology, location+season+lead, ensemble-spread-only, recent-error, etc.) | ❌ None implemented |
| Ablation study | ❌ None |
| Brier Skill Score vs. climatology | ❌ Missing |
| Precision / Recall / F1 at operational thresholds | ❌ Missing |
| False-alarm and miss rates | ❌ Missing |
| Conformal prediction intervals | ❌ Missing |
| Time-blocked evaluation (by year/season) | ❌ Missing |
| Grouped SHAP by feature family | ❌ Missing |
| Event-grouping in splits (same weather event) | ❌ Missing |
| Season/regime-stratified metrics with sample-count warnings | ⚠️ Regime breakdown exists but bust rates are artifacts |
| Confidence defined as `1 - calibrated_bust_probability` | ❌ Current confidence is `1 - (pred_error / p95)` — inconsistent |
| Case studies (Kerala 2018, Chennai 2015) | ❌ None |
| Location-specific bust threshold (90th percentile) | ❌ Current threshold is formula-based, lead-day-only |

---

## 6. Hygiene Issues

| Issue | Details |
|:------|:--------|
| **Model artifacts in git** | `models/*.joblib` (4 files, ~3 MB total) are tracked; should be in `.gitignore` |
| **Large CSV in repo** | `data/nwp_forecast_bust_dataset.csv` (24 MB) should not be committed |
| **Unpinned requirements** | All versions are `>=` with no upper bound; no lockfile |
| **No Makefile/pipeline script** | No reproducible build command beyond individual scripts |
| **No `--data-source` flag** | Code silently uses synthetic data; no real-data path operational |
| **`RealNCMRWFDataLoader`** | Raises `NotImplementedError` — purely a stub |
| **Hardcoded timestamp** | Timestamp is hard-coded in dashboard |
| **No data validation** | No alignment checks, unit checks, model-version-drift detection |
| **No leakage test** | No automated test to verify features use only initialization-time data |

---

## 7. What Works Well (Preserving)

Despite the circularity problem, the codebase has solid engineering structure that should be preserved:

1. **`BaseDataLoader` ABC pattern** — clean contract for data source swapping
2. **Chronological splitting** in `features.py` — correct methodology
3. **`FeatureEngineer` class** — good pattern for deterministic feature transformation; extensible
4. **`ForecastExplainer` with meteorological lexicon** — excellent UX for forecasters; needs grouping
5. **Unified inference engine** — single source of truth for API + dashboard; good architecture
6. **FastAPI with Pydantic schemas** — clean REST layer
7. **Streamlit dashboard** — polished UI with 4 tabs; the visual quality is high
8. **Test structure** — pytest integration and pipeline tests exist and pass

---

## 8. Implementation Plan (Stages 1–9)

*(Outlined per user's prompt - see full document above for details)*

---

## 9. Assumptions & Prerequisites

1. **Real data**: The system will be built and fully tested on the **redesigned synthetic fixture**. Real-data loaders will be created as pluggable modules.
2. **Compute**: LightGBM/XGBoost training on ~175K rows is feasible on a local machine.
3. **No breaking changes yet**: Existing modules will be preserved and the circular generator will be deprecated (not deleted).

---

## 10. Verdict

> **The current system is a well-engineered demonstration prototype with a fatally circular data pipeline.** The model metrics are artifacts of the model recovering its own formula and must not be presented as evidence of forecasting skill. The code architecture, API design, dashboard quality, and testing infrastructure are solid and will be preserved. The refactoring will replace the data/target/feature layers while extending the model evaluation framework to produce scientifically honest results.
