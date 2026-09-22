# Data Contract & Ingestion Architecture

**Forecast Reliability Engine** — NCMRWF / Ministry of Earth Sciences (MoES)  
**System Version**: 2.0 (Post-Refactor)  
**Document Classification**: Scientific & Technical Specification  

---

## 1. Executive Summary & Core Invariants

The **Forecast Reliability Engine** provides an objective AI confidence and bust-risk layer on top of Numerical Weather Prediction (NWP) models (NCUM, NEPS, ECMWF, GEFS). It **never replaces NWP** and **never predicts raw weather independently**.

### Non-Negotiable Scientific Invariants

1. **Truth vs. Predictor Separation**:
   - **Ground Truth**: Ground truth daily accumulated precipitation **must strictly come from observational networks** — specifically IMD 0.25° × 0.25° gridded daily rainfall analysis.
   - **Strict Prohibition**: Reanalysis precipitation (such as ERA5 total precipitation) **must never be used as ground truth verification**. Model-derived precipitation in reanalysis reflects NWP convective parameterization biases and would invalidate error attribution. ERA5 is restricted exclusively to large-scale atmospheric state predictors (MSLP, vertical wind shear, CAPE, SST).
2. **Explicit Provenance & Data Source Tagging**:
   - Every single record, dataset, and API output is permanently tagged with `data_source: "synthetic"` or `data_source: "real"`.
   - Synthetic data is reserved strictly for smoke testing, pipeline verification, and regression tests. It is never conflated with operational verification.
3. **Temporal Causality (No Future Information Leaks)**:
   - Features available at forecast initialization time $T_{\text{init}}$ can only reflect information observed or modeled up to $T_{\text{init}}$.
   - $T_{\text{valid}} = T_{\text{init}} + \text{lead\_day}$.
4. **Non-Circularity**:
   - In synthetic fixtures, target forecast errors are generated from hidden latent variables ($Z_{\text{predictability}}, Z_{\text{disturbance}}$) that are **never** directly exposed as input features. Observed features are noisy, partial measurements.

---

## 2. Canonical Column Schema

Verification records follow a strict schema across all loaders:

### 2.1 Identifiers (`IDENTIFIER_COLS`)

| Column Name | Type | Allowed Values / Range | Description |
|:---|:---|:---|:---|
| `initialization_time` | string/datetime | `YYYY-MM-DD HH:MM:SS` (UTC) | NWP forecast run start time |
| `valid_time` | string/datetime | `YYYY-MM-DD` | Target verification calendar date |
| `lead_day` | integer | `1` to `10` | Forecast horizon in days |
| `location_id` | string | 32 IMD Subdivisions or Grid ID | Meteorological subdivision name |
| `lat` | float | `6.0` to `38.0` (°N) | Latitude of centroid or grid cell |
| `lon` | float | `68.0` to `98.0` (°E) | Longitude of centroid or grid cell |
| `model_version` | string | e.g. `NCUM_v3.2`, `GEFS_v12`, `ECMWF_IFS` | Identifier for NWP operational cycle |
| `data_source` | string | `"synthetic"` or `"real"` | Data provenance indicator |

### 2.2 NWP Forecast Fields (`NWP_FORECAST_COLS`)

| Column Name | Units | Range | Description |
|:---|:---|:---|:---|
| `fcst_rainfall_mm` | mm/day | $[0, \infty)$ | Deterministic accumulated precipitation |
| `fcst_temp_2m_c` | °C | $[-30, 55]$ | 2-meter air temperature |
| `fcst_mslp_hpa` | hPa | $[900, 1050]$ | Mean sea level pressure |
| `fcst_wind_850_mps` | m/s | $[0, 100]$ | 850 hPa horizontal wind speed |
| `fcst_wind_200_mps` | m/s | $[0, 120]$ | 200 hPa horizontal wind speed (upper troposphere / jet) |
| `fcst_rh_700_pct` | % | $[0, 100]$ | 700 hPa relative humidity (mid-tropospheric moisture) |
| `fcst_geopot_500_m` | gpm | $[4800, 6000]$ | 500 hPa geopotential height |
| `fcst_cape_jkg` | J/kg | $[0, 7000]$ | Surface-based Convective Available Potential Energy |
| `fcst_moisture_flux_conv` | g/(kg·s) | $[-50, 50]$ | Integrated moisture flux convergence |
| `ens_spread_rainfall` | mm | $[0, \infty)$ | Standard deviation across ensemble members |
| `ens_spread_temp` | °C | $[0, 20]$ | Ensemble 2m temperature spread |
| `ens_spread_mslp` | hPa | $[0, 30]$ | Ensemble MSLP spread |
| `ens_members_total` | int | $\ge 1$ | Total ensemble members (e.g., 50 for ECMWF, 31 for GEFS) |
| `ens_members_rain_gt10` | int | $[0, \text{total}]$ | Members forecasting $> 10$ mm rain |
| `ens_members_rain_gt50` | int | $[0, \text{total}]$ | Members forecasting $> 50$ mm rain |

### 2.3 Observational Ground Truth (`OBSERVATION_TRUTH_COLS`)

| Column Name | Units | Source | Description |
|:---|:---|:---|:---|
| `obs_rainfall_mm` | mm/day | IMD Gridded (0.25°) | Observed 24-hr daily rainfall (08:30 IST to 08:30 IST) |
| `obs_temp_2m_c` | °C | IMD station/grid | Observed 24-hr mean temperature (optional) |

### 2.4 Environmental & Atmospheric State Predictors

| Group | Columns | Source | Purpose |
|:---|:---|:---|:---|
| **ERA5 State** | `era5_mslp_hpa`, `era5_wind_shear_mps`, `era5_moisture_conv`, `era5_vorticity_850`, `era5_cape_jkg`, `era5_sst_c` | Copernicus CDS API | Quantifies large-scale flow stability, baroclinic shear, and oceanic heat content. |
| **Climate Modes** | `enso_oni`, `mjo_rmm1`, `mjo_rmm2`, `mjo_amplitude`, `mjo_phase`, `iod_dmi` | NOAA CPC, BoM | Captures intra-seasonal and inter-annual planetary wave teleconnections. |
| **Cyclone Proximity** | `cyclone_present`, `cyclone_dist_km`, `cyclone_intensity_kt`, `cyclone_category` | NOAA IBTrACS NI | Flags tropical cyclones in Bay of Bengal or Arabian Sea within 1500 km. |
| **Static Geography** | `elevation_m`, `dist_coast_km`, `land_fraction`, `terrain_type`, `terrain_complexity` | SRTM / Topo | Invariant local orographic complexity and land-sea contrast. |

---

## 3. Data Sources & Ingestion Protocols

### 3.1 Real-World Data Ingestion Matrix

| Data Stream | Primary Provider | Access Method | Cost / Auth | Update Frequency |
|:---|:---|:---|:---|:---|
| **IMD Rainfall Truth** | India Meteorological Department | NetCDF / `imdlib` | Open research tier / local archive | Daily (08:30 IST) |
| **ECMWF Open Data** | ECMWF (IFS & AIFS) | `ecmwf-opendata` API | Free tier / No API key required | 00Z, 06Z, 12Z, 18Z cycles |
| **GEFS Reforecast** | NOAA NCEI | AWS S3 `s3://noaa-gefs-retrospective/` | Free public S3 access | Daily retrospective |
| **ERA5 Atmospheric State** | ECMWF / Copernicus | CDS API (`cdsapi`) | Free account & API key required | Hourly / daily reanalysis |
| **Climate Indices** | BoM (MJO) / NOAA (ENSO) | HTTP CSV tables | Free public direct HTTP | Real-time & rolling daily |
| **Cyclone Tracks** | NOAA NCEI IBTrACS | HTTP CSV `ibtracs.NI.list.v04r01.csv` | Free public direct HTTP | 3-hourly during storm events |

---

## 4. Operational Invariant Validation (`src/data/validation.py`)

All ingested and processed datasets are passed through `validate_dataframe()`:

1. **Identifier Completeness**: Asserts all 8 required identifier columns are present without NaN values.
2. **Lead Time Bounding**: Asserts $1 \le \text{lead\_day} \le 10$.
3. **Temporal Monotonicity**: Verifies valid dates occur after or on initialization dates.
4. **Unit Range Sanity**:
   - Rainfall: $[0, 1500]$ mm/day.
   - Temperature: $[-40, 60]$ °C (automatically detects accidental Kelvin units $> 200$).
   - Pressure: $[850, 1085]$ hPa (automatically detects raw Pascals $> 80000$).
   - RH: $[0, 100]$ %.
5. **NWP Model Version Drift**: Detects changes in operational model naming or sudden distributional shifts across cycles.

---

## 5. Non-Circular Synthetic Data Architecture (`src/data/synthetic.py`)

To prevent the catastrophic metric inflation identified in the audit:
- The generator instantiates a latent dynamical system per location and day:
  $$\text{error} = f\big(Z_{\text{predictability}}, Z_{\text{disturbance}}, \epsilon_{\text{stochastic}}\big)$$
- The model is only provided with observable features:
  $$X_i = g_i\big(Z_{\text{predictability}}, Z_{\text{disturbance}}\big) + \eta_i$$
- Because the mapping is non-invertible and contains stochastic atmospheric noise $\eta$, machine learning models achieve realistic baseline metrics (PR-AUC $\approx 0.35 - 0.65$) matching operational reality.

---

## 6. Operational API Layer Data Contract

The operational API layer exposes the trained reliability models, conformal error bounds, and historical verification records to frontend dashboards and downstream client applications.

### 6.1 Spatial Granularity & Location Resolution (Known MVP Limitation)

- **Subdivision-Level Resolution**: All observational records, NWP forecasts, and AI predictions are evaluated strictly at the **IMD meteorological subdivision level** (32 subdivisions defined in `src/data/schema.py: SUBDIVISIONS`). There is no city-, district-, or block-level ground truth in the current pipeline.
- **City-to-Subdivision Resolution Method**:
  - The endpoint `GET /locations/search?q=<text>` resolves free-text queries.
  - Queries are first matched against official subdivision names (exact case-insensitive and substring match).
  - If no direct subdivision match is found, queries are evaluated against a catalog of 50+ major Indian state capitals and metropolitan centers.
  - Resolution from city to subdivision is computed **programmatically via Great-Circle Haversine distance** to the nearest IMD subdivision centroid coordinate.
  - Every response carries `match_confidence: "exact_subdivision"` or `match_confidence: "resolved_from_city"`, the centroid coordinates, and an explicit caveat note:
    > *"All results are reported at meteorological subdivision resolution. City-level resolution is a known MVP limitation with high-resolution numerical grids planned for future phases."*
- **Future Roadmap**: High-resolution grid-level verification ($0.12^{\circ} \times 0.12^{\circ}$ NCUM grid or $0.25^{\circ} \times 0.25^{\circ}$ IMD analysis) is planned for Phase 2.

### 6.2 Temporal Granularity & Sub-Daily Honesty (Daily-Only Verification)

- **Strict Daily-Accumulated Truth**:
  - Observational ground truth (`obs_rainfall_mm`) represents 24-hour rainfall accumulations (08:30 IST to 08:30 IST), and `fcst_rainfall_mm` represents 24-hour forecast accumulations.
  - **No sub-daily or hourly ground truth or forecast records exist anywhere in the pipeline.**
- **Honest Day-Detail Presentation**:
  - `GET /region/{region}/day_detail?date=<date>&lead_day=<n>` provides full daily diagnostic verification records (`granularity: "daily"`).
  - It carries an explicit caveat note:
    > *"Sub-daily detail is not available from current data sources; this view shows the full daily verification record."*
  - **Illustrative Diurnal Curve**: For frontend visual rendering and diurnal temperature display, an optional 24-hour diurnal curve is generated via smooth physical interpolation (sinusoidal temperature diurnal cycle peaking at 14:00, Gaussian convective rainfall fraction peaking at 16:00).
  - **Mandatory Flag**: Both the curve container and every hourly point carry `"is_illustrative": true`. Frontend clients MUST display an illustrative badge or notice and never present this as real hourly forecast data.

### 6.3 Operational Reference Clock ("Today" Replay)

- In historical archive or demonstration replay modes, the system operational reference date is anchored to the latest valid verification date present in the dataset (`2025-01-09`), exposed via:
  - `GET /health` -> `current_data_date: str`, `data_recency_note: str`
  - `GET /system/today` -> `today: str`, `is_synthetic_or_replay: bool`, `data_source: str`
- Frontend dashboards must consume `today` from this endpoint to coordinate time slider controls and timeline bounds rather than using the local browser clock.

### 6.4 Verification History & Calibration Verdict Matrix

- `GET /region/{region}/history?days=10&lead_day=1` and `GET /region/{region}/history/summary?days=10` provide past forecast verification over the last $N$ valid days ($1 \le N \le 30$).
- **Strict Zero-Leakage Guarantee**: `confidence_at_issue_time` is computed strictly using the row's own feature values as they existed at forecast initialization time ($T_{\text{init}}$), evaluated through the trained calibration pipeline. No future data or observed ground truth is accessed during inference.
- **Calibration Verdict Derivation**:
  Forecast reliability is classified into one of four operational verification quadrants by comparing the model's issue-time risk tier against verified ground truth (`was_bust`):
  
  | Operational Risk Flag at Issue Time | Verified Ground Truth (`was_bust == True`) | Verified Ground Truth (`was_bust == False`) |
  |:---|:---|:---|
  | **Flagged Risky** (`bust_prob >= 0.50` or `confidence <= 0.40`) | `flagged_risky_and_busted` *(True Positive Alert)* | `flagged_risky_no_bust` *(False Alarm)* |
  | **Confident** (`bust_prob < 0.50` and `confidence > 0.40`) | `confident_but_busted` *(False Negative / Missed Bust)* | `confident_correct` *(True Negative)* |

- **Evidence Agreement & Contradiction**:
  - `evidence_agreement`: Float in $[0, 1]$ measuring the proportion of signed SHAP feature family contributions aligning in the dominant direction.
  - `contradiction_flag`: Boolean flag indicating substantial opposing dynamical forces (e.g. strong thermodynamic instability conflicting with favorable large-scale oceanic suppression).

