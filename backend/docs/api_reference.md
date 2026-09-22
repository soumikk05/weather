# REST API Reference & Frontend Integration Guide

**Forecast Bust Detection & Reliability System**  
Smart India Hackathon — NCMRWF / Ministry of Earth Sciences  
API Version: `1.1.0` | Base URL: `http://localhost:8000` | OpenAPI Docs: `http://localhost:8000/docs`

---

## Overview & Frontend Core Invariants

1. **Spatial Granularity**: The API operates at the **32 IMD meteorological subdivision level**. Free-text city queries are resolved to containing subdivisions via programmatic Haversine centroid distance. City-level resolution is a known MVP limitation.
2. **Temporal Granularity**: All forecast and observational ground-truth records are **daily-accumulated only**. There is no sub-daily or hourly ground truth. Any intraday curves returned by the API are synthetic diurnal approximations and carry `"is_illustrative": true`.
3. **Operational Clock**: For synthetic and historical hindcast datasets, the frontend must anchor its operational clock and time-slider controls to `GET /system/today` (`current_data_date`) rather than the client system clock.
4. **CORS Support**: Cross-Origin Resource Sharing is enabled for all origins (`*`), supporting local Vite, Next.js, and Streamlit frontend development.

---

## Endpoint Summary Table

| Method | Endpoint | Description | Primary Use Case |
|:---|:---|:---|:---|
| `GET` | `/health` | Service diagnostics, loaded models & dataset recency | Health check & startup probe |
| `GET` | `/system/today` | Operational reference date & provenance info | Front-end timeline anchoring |
| `GET` | `/locations/search` | Search subdivisions or resolve major Indian cities | Top navigation search bar |
| `GET` | `/regions` | List all 32 IMD subdivisions with coordinates & terrain | Map initialization & choropleth |
| `GET` | `/dates` | All available forecast dates | Date picker dropdowns |
| `GET` | `/confidence_map` | Nationwide confidence & bust probabilities | National map / overview dashboard |
| `GET` | `/region/{region}/forecast` | 10-day lead time profile for a single subdivision | 10-day trajectory / lead-time charts |
| `GET` | `/region/{region}/history` | Historical verification records over last $N$ days | Timeline verification view |
| `GET` | `/region/{region}/history/summary` | Aggregate verification metrics & plain-language summary | "Validate all days" summary badge |
| `GET` | `/region/{region}/day_detail` | Full daily record & diagnostic fields + diurnal curve | Day-detail drilldown modal |
| `GET` | `/explain/{region}` | SHAP feature attributions & plain-language bulletin | Forecaster explanation card |
| `POST` | `/predict` | What-If synoptic scenario evaluator | Interactive forecaster simulator lab |

---

## Detailed Endpoint Specifications

### 1. `GET /health`
Returns system operational status, model readiness, and dataset recency metadata.

- **Query Parameters**: None
- **Response**: `200 OK`
```json
{
  "status": "healthy",
  "service": "NCMRWF Forecast Bust Detection System",
  "version": "1.1.0",
  "subdivisions_count": 32,
  "available_dates_count": 548,
  "models_loaded": true,
  "current_data_date": "2025-01-09",
  "data_recency_note": "Fixed historical/synthetic archive; use current_data_date as reference operational date."
}
```

---

### 2. `GET /system/today`
Returns the simulated operational reference date (`today`) representing the latest verified calendar date in the archive.

- **Query Parameters**: None
- **Response**: `200 OK`
```json
{
  "today": "2025-01-09",
  "is_synthetic_or_replay": true,
  "data_source": "synthetic",
  "earliest_date": "2022-01-02",
  "latest_date": "2025-01-09",
  "note": "Use 'today' as the operational reference clock for frontend timelines rather than system real-time."
}
```

---

### 3. `GET /locations/search`
Resolves free-text search queries to one of the 32 IMD meteorological subdivisions. Directly matches subdivision names or maps 50+ major Indian cities via Great-Circle Haversine distance to the nearest subdivision centroid.

- **Query Parameters**:
  - `q` (string, required, `min_length=1`): City or subdivision name (e.g. `Chennai`, `Delhi`, `Odisha`, `Bengaluru`).
- **Response**: `200 OK`
```json
{
  "query": "Chennai",
  "resolved_subdivision": "Rayalaseema",
  "subdivision_lat": 14.5,
  "subdivision_lon": 78.5,
  "match_confidence": "resolved_from_city",
  "matched_name": "Chennai",
  "distance_km": 247.79,
  "note": "All results are reported at meteorological subdivision resolution. City-level resolution is a known MVP limitation with high-resolution numerical grids planned for future phases."
}
```
- **Error Codes**:
  - `404 Not Found`: Query does not match any known subdivision or cataloged Indian city.
  - `422 Unprocessable Entity`: Query is empty or missing.

---

### 4. `GET /regions`
Returns metadata for all 32 IMD subdivisions including centroid coordinates and terrain classification.

- **Query Parameters**: None
- **Response**: `200 OK` (Array of 32 items)
```json
[
  {
    "name": "Jammu & Kashmir and Ladakh",
    "lat": 34.0,
    "lon": 76.5,
    "terrain": "Himalayan",
    "terrain_difficulty": 0.88
  },
  {
    "name": "Haryana, Chandigarh & Delhi",
    "lat": 29.0,
    "lon": 76.8,
    "terrain": "Northern_Plains",
    "terrain_difficulty": 0.32
  }
]
```

---

### 5. `GET /confidence_map`
Returns nationwide calibrated bust probabilities, confidence scores, conformal prediction intervals, and top risk factors for all 32 subdivisions at a specified lead time.

- **Query Parameters**:
  - `date` (string, optional): Forecast date (`YYYY-MM-DD`). Defaults to latest available.
  - `lead_day` (integer, optional, `ge=1, le=10`, default `1`): Forecast horizon (Day 1 to Day 10).
- **Response**: `200 OK` (Array of 32 items)
```json
[
  {
    "date": "2024-12-30",
    "region": "Haryana, Chandigarh & Delhi",
    "lat": 29.0,
    "lon": 76.8,
    "terrain": "Northern_Plains",
    "terrain_difficulty": 0.32,
    "synoptic_regime": "quiescent_clear",
    "lead_day": 1,
    "bust_probability": 0.082,
    "predicted_error_mm": 3.14,
    "error_interval_90_lower": 0.0,
    "error_interval_90_upper": 8.2,
    "conformal_interval_mm": [0.0, 8.2],
    "confidence_score": 0.918,
    "risk_tier": "High Confidence",
    "evidence_agreement": 0.88,
    "contradiction_flag": false,
    "top_drivers": [
      "Weak vertical wind shear (stable air column)",
      "Low convective energy (stable thermodynamic profile)"
    ],
    "plain_language_summary": "Forecast confidence is high; synoptic dynamics and ensemble consistency remain stable."
  }
]
```

---

### 6. `GET /region/{region}/forecast`
Returns the complete 10-day forecast confidence trajectory, bust risk evolution, and conformal intervals for a specific subdivision.

- **Path Parameters**:
  - `region` (string, required): Subdivision name (case-insensitive).
- **Query Parameters**:
  - `date` (string, optional): Forecast date (`YYYY-MM-DD`). Defaults to latest available.
- **Response**: `200 OK` (Array of 10 items, sorted by `lead_day` 1 to 10)
```json
[
  {
    "lead_day": 1,
    "date": "2024-12-30",
    "region": "Haryana, Chandigarh & Delhi",
    "terrain": "Northern_Plains",
    "synoptic_regime": "quiescent_clear",
    "ens_spread_rainfall": 2.1,
    "bust_probability": 0.05,
    "predicted_error_mm": 1.85,
    "error_interval_90_lower": 0.0,
    "error_interval_90_upper": 5.2,
    "conformal_interval_mm": [0.0, 5.2],
    "confidence_score": 0.95,
    "risk_tier": "High Confidence",
    "evidence_agreement": 0.92,
    "contradiction_flag": false,
    "plain_language_summary": "Forecast confidence is high; synoptic dynamics remain stable.",
    "top_drivers": [...]
  }
]
```

---

### 7. `GET /region/{region}/history`
Retrieves verified historical forecast records for the specified subdivision over the last $N$ days up to `as_of`.

- **Path Parameters**:
  - `region` (string, required): Subdivision name.
- **Query Parameters**:
  - `days` (integer, optional, `ge=1, le=30`, default `10`): Number of verified days.
  - `as_of` (string, optional): Reference verification date (`YYYY-MM-DD`). Defaults to latest date.
  - `lead_day` (integer, optional, `ge=1, le=10`, default `1`): Forecast lead horizon originally evaluated.
- **Response**: `200 OK` (Array of up to $N$ items, sorted chronologically ascending)
```json
[
  {
    "date": "2024-12-31",
    "initialization_time": "2024-12-30",
    "lead_day": 1,
    "region": "Haryana, Chandigarh & Delhi",
    "forecast_rainfall_mm": 2.93,
    "forecast_temp_2m_c": 14.2,
    "observed_rainfall_mm": 4.33,
    "observed_temp_2m_c": 13.8,
    "forecast_error_mm": -1.40,
    "abs_error_mm": 1.40,
    "bust_threshold_mm": 6.01,
    "was_bust": false,
    "confidence_at_issue_time": 0.9944,
    "bust_probability": 0.0056,
    "predicted_error_mm": 1.85,
    "conformal_interval_mm": [0.0, 5.2],
    "risk_tier": "High Confidence",
    "calibration_verdict": "confident_correct",
    "evidence_agreement": 0.72,
    "contradiction_flag": false,
    "top_drivers": ["Weak vertical wind shear (stable air column)"]
  }
]
```
- **Calibration Verdict Field Definitions**:
  - `"confident_correct"`: Model expressed high/moderate confidence, verified with no bust (True Negative).
  - `"confident_but_busted"`: Model expressed confidence, but a bust occurred (False Negative / Missed Alert).
  - `"flagged_risky_and_busted"`: Model issued bust risk alert, bust occurred (True Positive Alert).
  - `"flagged_risky_no_bust"`: Model issued bust risk alert, but forecast verified safely (False Alarm).

---

### 8. `GET /region/{region}/history/summary`
Returns aggregate verification metrics across the historical window to power batch validation cards.

- **Path Parameters**:
  - `region` (string, required): Subdivision name.
- **Query Parameters**:
  - `days` (integer, optional, `ge=1, le=30`, default `10`).
  - `as_of` (string, optional): Reference verification date.
  - `lead_day` (integer, optional, `ge=1, le=10`, default `1`).
- **Response**: `200 OK`
```json
{
  "region": "Haryana, Chandigarh & Delhi",
  "days": 10,
  "as_of": "2024-12-31",
  "lead_day": 1,
  "counts_per_calibration_verdict": {
    "confident_correct": 9,
    "confident_but_busted": 0,
    "flagged_risky_and_busted": 1,
    "flagged_risky_no_bust": 0
  },
  "overall_bust_rate": 0.10,
  "mean_abs_error": 2.16,
  "summary_sentence": "Over the last 10 verified days in Haryana, Chandigarh & Delhi (Lead Day 1), the reliability engine demonstrated strong calibration: 9 of 10 forecasts verified correct with high confidence (mean MAE 2.16 mm), and all 1 bust events were successfully pre-flagged as risky."
}
```

---

### 9. `GET /region/{region}/day_detail`
Returns the full daily record for a single day, including forecast parameters, observations, ERA5 diagnostic fields, SHAP explanations, and an illustrative diurnal curve.

- **Path Parameters**:
  - `region` (string, required): Subdivision name.
- **Query Parameters**:
  - `date` (string, optional): Verification date (`YYYY-MM-DD`). Defaults to latest available.
  - `lead_day` (integer, optional, `ge=1, le=10`, default `1`).
- **Response**: `200 OK`
```json
{
  "date": "2024-12-31",
  "region": "Haryana, Chandigarh & Delhi",
  "lead_day": 1,
  "initialization_time": "2024-12-30",
  "granularity": "daily",
  "note": "Sub-daily detail is not available from current data sources; this view shows the full daily verification record.",
  "bust_probability": 0.0056,
  "confidence_score": 0.9944,
  "predicted_error_mm": 1.85,
  "error_interval_90_lower": 0.0,
  "error_interval_90_upper": 5.2,
  "conformal_interval_mm": [0.0, 5.2],
  "risk_tier": "High Confidence",
  "evidence_agreement": 0.82,
  "contradiction_flag": false,
  "forecast_rainfall_mm": 2.93,
  "forecast_temp_2m_c": 14.2,
  "observed_rainfall_mm": 4.33,
  "observed_temp_2m_c": 13.8,
  "forecast_error_mm": -1.40,
  "abs_error_mm": 1.40,
  "bust_threshold_mm": 6.01,
  "was_bust": false,
  "era5_diagnostics": {
    "era5_mslp_hpa": 1016.4,
    "era5_wind_shear_mps": 11.2,
    "era5_moisture_conv": 0.04
  },
  "top_drivers": ["Weak vertical wind shear (stable air column)"],
  "plain_language_summary": "Forecast confidence is high; synoptic dynamics and ensemble consistency remain stable.",
  "illustrative_hourly_curve": [
    {
      "hour": 0,
      "time_utc": "00:00",
      "temp_c": 9.94,
      "rainfall_mm": 0.0,
      "is_illustrative": true
    },
    ...
  ],
  "is_illustrative": true,
  "illustrative_note": "Hourly curve is a synthetic diurnal interpolation for visual rendering only. It is NOT observed or forecasted hourly data."
}
```

---

### 10. `GET /explain/{region}`
Returns granular SHAP feature attributions, dominant family breakdown, and the duty forecaster advisory bulletin.

- **Path Parameters**:
  - `region` (string, required): Subdivision name.
- **Query Parameters**:
  - `lead_day` (integer, optional, `ge=1, le=10`, default `1`).
  - `date` (string, optional): Forecast date (`YYYY-MM-DD`).
- **Response**: `200 OK`
```json
{
  "region": "Odisha",
  "lead_day": 3,
  "date": "2024-12-30",
  "confidence_score": 0.842,
  "bust_probability": 0.158,
  "risk_tier": "High Confidence",
  "evidence_agreement": 0.87,
  "contradiction_flag": false,
  "synoptic_regime": "quiescent_clear",
  "plain_language_summary": "Forecast confidence is high; synoptic dynamics remain stable.",
  "top_drivers": [...],
  "operational_bulletin": {
    "advisory_level": "GREEN (High Confidence)",
    "primary_escalator": "None",
    "primary_stabilizer": "Strong ensemble consensus on precipitation",
    "operational_recommendation": "NWP forecast demonstrates strong physical stability. Proceed with standard deterministic guidance."
  }
}
```

---

### 11. `POST /predict`
Interactive Forecaster "What-If" Lab. Accepts arbitrary continuous synoptic variables and returns real-time calibrated bust probabilities and SHAP decomposition.

- **Request Body**: `application/json`
```json
{
  "lead_day": 7,
  "region": "Konkan & Goa",
  "terrain": "Western_Ghats",
  "terrain_difficulty": 0.78,
  "synoptic_regime": "cyclonic_disturbance",
  "fcst_rainfall_mm": 65.0,
  "ens_spread_rainfall": 14.5,
  "ens_spread_mslp": 4.2,
  "fcst_mslp_hpa": 992.0,
  "vertical_wind_shear": 24.0,
  "fcst_rh_700_pct": 92.0,
  "fcst_cape_jkg": 2800.0,
  "recent_error_mae_30d": 18.0
}
```
- **Response**: `200 OK`
```json
{
  "bust_probability": 0.785,
  "predicted_error_mm": 28.4,
  "error_interval_90_lower": 8.0,
  "error_interval_90_upper": 48.8,
  "conformal_interval_mm": [8.0, 48.8],
  "confidence_score": 0.215,
  "risk_tier": "Low Confidence - Bust Risk",
  "evidence_agreement": 0.94,
  "contradiction_flag": false,
  "plain_language_summary": "Elevated bust risk driven primarily by Ensemble Uncertainty and Synoptic State Evolution.",
  "operational_bulletin": {
    "advisory_level": "RED (Severe Bust Vulnerability)",
    "recommendation": "High risk of sudden forecast degradation. Deploy multi-model ensemble consensus and issue localized precautionary watch."
  }
}
```

---

## Validation Error Responses (HTTP 422)

Whenever query bounds are violated (e.g. `days > 30` or `lead_day > 10`), FastAPI automatically returns a structured 422 validation response:
```json
{
  "detail": [
    {
      "type": "less_than_equal",
      "loc": ["query", "days"],
      "msg": "Input should be less than or equal to 30",
      "input": "45",
      "ctx": {"le": 30}
    }
  ]
}
```
