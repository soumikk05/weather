"""
FastAPI Operational Backend for Forecast Bust Detection
Smart India Hackathon - NCMRWF / Ministry of Earth Sciences

Exposes REST endpoints for:
- Regional Confidence Maps (Day 1 - 10)
- 10-Day Subdivision Forecast Profiles
- Verification History & Calibration Audits (Day 1 - 30)
- Subdivision and City Location Search Resolution
- Daily Detail Records & Illustrative Diurnal Curves
- SHAP-Based Plain-Language Explanations
- Interactive Synoptic 'What-If' Predictions
"""

import os
import sys
# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.data.schema import SUBDIVISIONS
from src.inference import get_engine


app = FastAPI(
    title="NCMRWF Forecast Bust Detection API",
    description="AI-Driven Medium-Range (Day 1–10) NWP Forecast Bust Detection, Calibration Verification, and Confidence Mapping System.",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for cross-origin frontend dashboard development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------------------
class HealthResponse(BaseModel):
    model_config = {"extra": "allow"}

    status: str = Field(..., examples=["healthy"])
    service: str = Field(..., examples=["NCMRWF Forecast Bust Detection System"])
    version: str = Field(..., examples=["1.1.0"])
    subdivisions_count: int = Field(..., examples=[32])
    available_dates_count: int = Field(..., examples=[548])
    models_loaded: bool = Field(..., examples=[True])
    current_data_date: str = Field(..., examples=["2025-01-09"], description="Latest valid date available in dataset ('today' for replay/demo).")
    data_recency_note: str = Field(..., examples=["Fixed historical/synthetic archive; use current_data_date as reference operational date."])


class SystemTodayResponse(BaseModel):
    model_config = {"extra": "allow"}

    today: str = Field(..., examples=["2025-01-09"], description="Current simulated operational date (latest valid_time).")
    is_synthetic_or_replay: bool = Field(..., examples=[True], description="True if dataset is synthetic or historical hindcast replay.")
    data_source: str = Field(..., examples=["synthetic"], description="Underlying dataset provenance tag.")
    earliest_date: str = Field(..., examples=["2022-01-02"])
    latest_date: str = Field(..., examples=["2025-01-09"])
    note: str = Field(
        default="Use 'today' as the operational reference clock for frontend timelines rather than system real-time.",
        examples=["Use 'today' as the operational reference clock for frontend timelines rather than system real-time."]
    )


class LocationSearchResponse(BaseModel):
    model_config = {"extra": "allow"}

    query: str = Field(..., examples=["Chennai"])
    resolved_subdivision: str = Field(..., examples=["Rayalaseema"], description="IMD meteorological subdivision name.")
    subdivision_lat: float = Field(..., examples=[14.5])
    subdivision_lon: float = Field(..., examples=[78.5])
    match_confidence: str = Field(..., examples=["resolved_from_city"], description="'exact_subdivision' or 'resolved_from_city'")
    matched_name: Optional[str] = Field(None, examples=["Chennai"])
    distance_km: Optional[float] = Field(None, examples=[247.79], description="Haversine distance from queried city to subdivision centroid.")
    note: str = Field(
        default="All results are reported at meteorological subdivision resolution. City-level resolution is a known MVP limitation with high-resolution numerical grids planned for future phases.",
        examples=["All results are reported at meteorological subdivision resolution. City-level resolution is a known MVP limitation with high-resolution numerical grids planned for future phases."]
    )


class RegionMetadata(BaseModel):
    name: str = Field(..., examples=["Haryana, Chandigarh & Delhi"])
    lat: float = Field(..., examples=[29.0])
    lon: float = Field(..., examples=[76.8])
    terrain: str = Field(..., examples=["Northern_Plains"])
    terrain_difficulty: float = Field(..., examples=[0.32])


class ConfidenceMapItem(BaseModel):
    model_config = {"extra": "allow"}

    date: str = Field(..., examples=["2024-12-30"])
    region: str = Field(..., examples=["Haryana, Chandigarh & Delhi"])
    lat: float = Field(..., examples=[29.0])
    lon: float = Field(..., examples=[76.8])
    terrain: str = Field(..., examples=["Northern_Plains"])
    terrain_difficulty: float = Field(..., examples=[0.32])
    synoptic_regime: str = Field(..., examples=["quiescent_clear"])
    lead_day: int = Field(..., examples=[1])
    bust_probability: float = Field(..., examples=[0.082])
    predicted_error_mm: float = Field(..., examples=[3.14])
    error_interval_90_lower: Optional[float] = Field(None, examples=[0.0])
    error_interval_90_upper: Optional[float] = Field(None, examples=[8.2])
    conformal_interval_mm: Optional[List[float]] = Field(None, examples=[[0.0, 8.2]])
    confidence_score: float = Field(..., examples=[0.918])
    risk_tier: str = Field(..., examples=["High Confidence"])
    evidence_agreement: float = Field(default=1.0, examples=[0.88], description="Directional agreement (0-1) across feature families.")
    contradiction_flag: bool = Field(default=False, examples=[False], description="True if major escalators and mitigators exert opposing forces.")
    top_drivers: List[str] = Field(..., examples=[["Weak vertical wind shear (stable air column)"]])
    top_families: Optional[List[Dict]] = None
    operational_bulletin: Optional[Dict] = None
    plain_language_summary: str = Field(..., examples=["Forecast confidence is high; synoptic dynamics and ensemble consistency remain stable."])


class ForecastProfileItem(BaseModel):
    model_config = {"extra": "allow"}

    lead_day: int = Field(..., examples=[3])
    date: str = Field(..., examples=["2024-12-30"])
    region: str = Field(..., examples=["Haryana, Chandigarh & Delhi"])
    terrain: str = Field(..., examples=["Northern_Plains"])
    synoptic_regime: str = Field(..., examples=["quiescent_clear"])
    ens_spread_rainfall: float = Field(..., examples=[4.5])
    bust_probability: float = Field(..., examples=[0.14])
    predicted_error_mm: float = Field(..., examples=[4.2])
    error_interval_90_lower: Optional[float] = Field(None, examples=[0.0])
    error_interval_90_upper: Optional[float] = Field(None, examples=[9.5])
    conformal_interval_mm: Optional[List[float]] = Field(None, examples=[[0.0, 9.5]])
    confidence_score: float = Field(..., examples=[0.86])
    risk_tier: str = Field(..., examples=["High Confidence"])
    evidence_agreement: float = Field(default=1.0, examples=[0.85])
    contradiction_flag: bool = Field(default=False, examples=[False])
    plain_language_summary: str = Field(..., examples=["Forecast confidence is high."])
    top_drivers: List[Dict]
    top_families: Optional[List[Dict]] = None
    operational_bulletin: Optional[Dict] = None


class HistoryItem(BaseModel):
    model_config = {"extra": "allow"}

    date: str = Field(..., examples=["2024-12-31"], description="Verification date (valid_time).")
    initialization_time: Optional[str] = Field(None, examples=["2024-12-30"])
    lead_day: int = Field(..., examples=[1])
    region: str = Field(..., examples=["Haryana, Chandigarh & Delhi"])
    forecast_rainfall_mm: float = Field(..., examples=[2.93])
    forecast_temp_2m_c: float = Field(..., examples=[14.2])
    observed_rainfall_mm: float = Field(..., examples=[4.33])
    observed_temp_2m_c: float = Field(..., examples=[13.8])
    forecast_error_mm: float = Field(..., examples=[-1.40])
    abs_error_mm: float = Field(..., examples=[1.40])
    bust_threshold_mm: float = Field(..., examples=[6.01])
    was_bust: bool = Field(..., examples=[False])
    confidence_at_issue_time: float = Field(..., examples=[0.9944], description="Calibrated confidence score produced at issue time.")
    bust_probability: float = Field(..., examples=[0.0056])
    predicted_error_mm: Optional[float] = Field(None, examples=[1.85])
    conformal_interval_mm: Optional[List[float]] = Field(None, examples=[[0.0, 5.2]])
    risk_tier: str = Field(..., examples=["High Confidence"])
    calibration_verdict: str = Field(
        ...,
        examples=["confident_correct"],
        description="One of: 'confident_correct', 'confident_but_busted', 'flagged_risky_and_busted', 'flagged_risky_no_bust'"
    )
    evidence_agreement: float = Field(..., examples=[0.72])
    contradiction_flag: bool = Field(..., examples=[False])
    top_drivers: Optional[List[str]] = None


class HistorySummaryResponse(BaseModel):
    model_config = {"extra": "allow"}

    region: str = Field(..., examples=["Haryana, Chandigarh & Delhi"])
    days: int = Field(..., examples=[10])
    as_of: str = Field(..., examples=["2024-12-31"])
    lead_day: int = Field(..., examples=[1])
    counts_per_calibration_verdict: Dict[str, int] = Field(
        ...,
        examples=[{
            "confident_correct": 9,
            "confident_but_busted": 0,
            "flagged_risky_and_busted": 1,
            "flagged_risky_no_bust": 0,
        }]
    )
    overall_bust_rate: float = Field(..., examples=[0.10])
    mean_abs_error: float = Field(..., examples=[2.16])
    summary_sentence: str = Field(
        ...,
        examples=["Over the last 10 verified days in Haryana, Chandigarh & Delhi (Lead Day 1), the reliability engine demonstrated strong calibration."]
    )


class HourlyCurvePoint(BaseModel):
    hour: int = Field(..., ge=0, le=23, examples=[14])
    time_utc: str = Field(..., examples=["14:00"])
    temp_c: float = Field(..., examples=[24.5])
    rainfall_mm: float = Field(..., examples=[1.2])
    is_illustrative: bool = Field(default=True, examples=[True])


class DayDetailResponse(BaseModel):
    model_config = {"extra": "allow"}

    date: str = Field(..., examples=["2024-12-31"])
    region: str = Field(..., examples=["Haryana, Chandigarh & Delhi"])
    lead_day: int = Field(..., examples=[1])
    initialization_time: str = Field(..., examples=["2024-12-30"])
    granularity: str = Field(default="daily", examples=["daily"])
    note: str = Field(
        default="Sub-daily detail is not available from current data sources; this view shows the full daily verification record.",
        examples=["Sub-daily detail is not available from current data sources; this view shows the full daily verification record."]
    )
    bust_probability: float = Field(..., examples=[0.0056])
    confidence_score: float = Field(..., examples=[0.9944])
    predicted_error_mm: float = Field(..., examples=[1.85])
    error_interval_90_lower: Optional[float] = Field(None, examples=[0.0])
    error_interval_90_upper: Optional[float] = Field(None, examples=[5.2])
    conformal_interval_mm: Optional[List[float]] = Field(None, examples=[[0.0, 5.2]])
    risk_tier: str = Field(..., examples=["High Confidence"])
    evidence_agreement: float = Field(..., examples=[0.82])
    contradiction_flag: bool = Field(..., examples=[False])
    forecast_rainfall_mm: float = Field(..., examples=[2.93])
    forecast_temp_2m_c: float = Field(..., examples=[14.2])
    observed_rainfall_mm: Optional[float] = Field(None, examples=[4.33])
    observed_temp_2m_c: Optional[float] = Field(None, examples=[13.8])
    forecast_error_mm: Optional[float] = Field(None, examples=[-1.40])
    abs_error_mm: Optional[float] = Field(None, examples=[1.40])
    bust_threshold_mm: Optional[float] = Field(None, examples=[6.01])
    was_bust: Optional[bool] = Field(None, examples=[False])
    era5_diagnostics: Optional[Dict[str, Optional[float]]] = None
    top_drivers: List[str]
    top_families: Optional[List[Dict]] = None
    operational_bulletin: Optional[Dict] = None
    plain_language_summary: str
    illustrative_hourly_curve: Optional[List[HourlyCurvePoint]] = None
    is_illustrative: bool = Field(default=True, examples=[True])
    illustrative_note: str = Field(
        default="Hourly curve is a synthetic diurnal interpolation for visual rendering only. It is NOT observed or forecasted hourly data.",
        examples=["Hourly curve is a synthetic diurnal interpolation for visual rendering only. It is NOT observed or forecasted hourly data."]
    )


class WhatIfRequest(BaseModel):
    model_config = {"extra": "allow"}

    lead_day: int = Field(default=5, ge=1, le=10, description="Lead day (1-10)")
    region: Optional[str] = Field(default="Custom Region", description="Region name")
    terrain: Optional[str] = Field(default="Northern_Plains", description="Terrain type")
    terrain_difficulty: Optional[float] = Field(default=0.45, ge=0.0, le=1.0)
    synoptic_regime: Optional[str] = Field(default="monsoon_depression", description="Synoptic regime")

    # NWP features
    fcst_rainfall_mm: Optional[float] = Field(default=15.0, ge=0.0, description="Forecast rainfall (mm)")
    ens_spread_rainfall: Optional[float] = Field(default=8.5, ge=0.0, description="Ensemble spread standard deviation")
    ens_spread_mslp: Optional[float] = Field(default=2.0, ge=0.0, description="Ensemble spread MSLP (hPa)")
    fcst_mslp_hpa: Optional[float] = Field(default=1005.0, ge=900.0, le=1050.0, description="Forecast MSLP (hPa)")
    vertical_wind_shear: Optional[float] = Field(default=15.0, ge=1.0, le=45.0, description="Vertical wind shear 850-200 hPa (m/s)")
    fcst_rh_700_pct: Optional[float] = Field(default=80.0, ge=0.0, le=100.0, description="Relative Humidity at 700 hPa (%)")
    fcst_cape_jkg: Optional[float] = Field(default=1800.0, ge=0.0, le=6000.0, description="CAPE (J/kg)")
    baroclinic_gradient_proxy: Optional[float] = Field(default=0.05, description="Baroclinic gradient proxy")
    convective_vulnerability: Optional[float] = Field(default=0.5, ge=0.0, le=1.0, description="Convective vulnerability index")

    # Subseasonal/Global features
    enso_oni_index: Optional[float] = Field(default=0.5, ge=-3.0, le=3.0, description="ENSO Oceanic Niño Index")
    mjo_amplitude: Optional[float] = Field(default=1.4, ge=0.1, le=3.5, description="MJO amplitude")
    mjo_phase: Optional[int] = Field(default=4, ge=1, le=8, description="MJO phase")
    iod_index: Optional[float] = Field(default=0.2, ge=-2.0, le=2.0, description="Indian Ocean Dipole index")
    nao_index: Optional[float] = Field(default=0.0, ge=-3.0, le=3.0, description="North Atlantic Oscillation index")

    # Recent error
    recent_error_bias_30d: Optional[float] = Field(default=2.0, description="30-day average error bias")
    recent_error_mae_30d: Optional[float] = Field(default=10.0, ge=0.0, description="30-day Mean Absolute Error")
    recent_error_bust_freq_30d: Optional[float] = Field(default=0.1, ge=0.0, le=1.0, description="30-day bust frequency")
    recent_error_mae_7d: Optional[float] = Field(default=8.0, ge=0.0, description="7-day Mean Absolute Error")
    prior_day_verified_error: Optional[float] = Field(default=14.0, ge=0.0, le=100.0, description="Prior day absolute error (mm)")


# -------------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["Diagnostics"])
def health_check():
    """System health check, dataset recency metadata, and loaded model diagnostics."""
    engine = get_engine()
    return {
        "status": "healthy",
        "service": "NCMRWF Forecast Bust Detection System",
        "version": "1.1.0",
        "subdivisions_count": len(SUBDIVISIONS),
        "available_dates_count": len(engine.get_available_dates()),
        "models_loaded": True,
        "current_data_date": engine.latest_valid_date,
        "data_recency_note": "Fixed historical/synthetic archive; use current_data_date as reference operational date.",
    }


@app.get("/system/today", response_model=SystemTodayResponse, tags=["Diagnostics"])
def get_system_today():
    """
    Returns simulated operational reference date ('today') derived from the dataset's latest valid date.
    Frontends should anchor their clock and queries to this date rather than system local time.
    """
    engine = get_engine()
    return {
        "today": engine.latest_valid_date,
        "is_synthetic_or_replay": engine.is_synthetic_or_replay,
        "data_source": engine.data_source,
        "earliest_date": engine.earliest_valid_date,
        "latest_date": engine.latest_valid_date,
        "note": "Use 'today' as the operational reference clock for frontend timelines rather than system real-time.",
    }


@app.get("/locations/search", response_model=LocationSearchResponse, tags=["Metadata"])
def search_locations(
    q: str = Query(..., min_length=1, description="Location search query (subdivision name or Indian city).")
):
    """
    Resolves free-text location queries to the 32 IMD meteorological subdivisions.
    Matches subdivision names directly, or resolves major Indian cities via
    programmatic nearest-centroid calculation.
    """
    engine = get_engine()
    match = engine.resolve_location(q)
    if not match:
        raise HTTPException(
            status_code=404,
            detail=f"No meteorological subdivision or known Indian city matching '{q}' found."
        )
    return match


@app.get("/regions", response_model=List[RegionMetadata], tags=["Metadata"])
def get_regions():
    """Returns all 32 Indian meteorological subdivisions with centroid coordinates and terrain."""
    return [
        RegionMetadata(
            name=s.name,
            lat=s.lat,
            lon=s.lon,
            terrain=s.terrain_type,
            terrain_difficulty=s.terrain_complexity,
        )
        for s in SUBDIVISIONS
    ]


@app.get("/dates", response_model=List[str], tags=["Metadata"])
def get_dates():
    """Returns list of all available historical forecast initialization dates."""
    engine = get_engine()
    return engine.get_available_dates()


@app.get("/confidence_map", response_model=List[ConfidenceMapItem], tags=["Operational Forecasts"])
def get_confidence_map(
    date: Optional[str] = Query(None, description="Forecast date (YYYY-MM-DD). Defaults to latest available."),
    lead_day: int = Query(1, ge=1, le=10, description="Forecast lead day (Day 1 to Day 10).")
):
    """
    Returns full region-wise confidence scores, calibrated bust probabilities,
    conformal error intervals, and top meteorological risk factors for all 32 subdivisions.
    """
    engine = get_engine()
    cmap = engine.get_confidence_map(date_str=date, lead_day=lead_day)
    if not cmap:
        raise HTTPException(status_code=404, detail="No forecast data found for requested date/lead_day.")
    return cmap


@app.get("/region/{region}/forecast", response_model=List[ForecastProfileItem], tags=["Operational Forecasts"])
def get_region_forecast(
    region: str,
    date: Optional[str] = Query(None, description="Forecast date (YYYY-MM-DD). Defaults to latest.")
):
    """
    Returns complete Day 1 to Day 10 forecast confidence trajectory,
    bust probabilities, and synoptic explanations for a specified subdivision.
    """
    engine = get_engine()
    timeline = engine.get_region_forecast(region_name=region, date_str=date)
    if not timeline:
        raise HTTPException(status_code=404, detail=f"Region '{region}' not found or no data available.")
    return timeline


@app.get("/region/{region}/history", response_model=List[HistoryItem], tags=["Verification & History"])
def get_region_history(
    region: str,
    days: int = Query(10, ge=1, le=30, description="Number of verification days to retrieve (1 to 30)."),
    as_of: Optional[str] = Query(None, description="Anchor valid date (YYYY-MM-DD). Defaults to latest available."),
    lead_day: int = Query(1, ge=1, le=10, description="Forecast lead day to verify (1 to 10). Defaults to 1.")
):
    """
    Returns verified historical forecast records for the specified subdivision over the last N days.
    Includes forecast vs observed values, forecast errors, bust outcomes, and point-in-time calibration verdicts.
    """
    engine = get_engine()
    history = engine.get_region_history(region_name=region, days=days, as_of=as_of, lead_day=lead_day)
    if not history:
        raise HTTPException(status_code=404, detail=f"No verification history found for region '{region}'.")
    return history


@app.get("/region/{region}/history/summary", response_model=HistorySummaryResponse, tags=["Verification & History"])
def get_region_history_summary(
    region: str,
    days: int = Query(10, ge=1, le=30, description="Number of verification days to aggregate (1 to 30)."),
    as_of: Optional[str] = Query(None, description="Anchor valid date (YYYY-MM-DD). Defaults to latest available."),
    lead_day: int = Query(1, ge=1, le=10, description="Forecast lead day to aggregate (1 to 10). Defaults to 1.")
):
    """
    Aggregates verification performance over the last N days for a subdivision:
    counts per calibration verdict, overall bust rate, mean absolute error (MAE),
    and a plain-language summary bulletin for batch validation.
    """
    engine = get_engine()
    summary = engine.get_region_history_summary(region_name=region, days=days, as_of=as_of, lead_day=lead_day)
    if summary["days"] == 0:
        raise HTTPException(status_code=404, detail=f"No verification records found for region '{region}'.")
    return summary


@app.get("/region/{region}/day_detail", response_model=DayDetailResponse, tags=["Operational Forecasts"])
def get_region_day_detail(
    region: str,
    date: Optional[str] = Query(None, description="Verification date (YYYY-MM-DD). Defaults to latest available."),
    lead_day: int = Query(1, ge=1, le=10, description="Forecast lead day (1 to 10). Defaults to 1.")
):
    """
    Returns complete daily diagnostic verification record for a specific day.
    Explicitly daily granularity. Sub-daily data is NOT fabricated; an optional
    illustrative diurnal curve is provided for visual rendering, clearly flagged as illustrative.
    """
    engine = get_engine()
    detail = engine.get_day_detail(region_name=region, date_str=date, lead_day=lead_day)
    if not detail:
        raise HTTPException(status_code=404, detail=f"No daily detail found for region '{region}' on date '{date}'.")
    return detail


@app.get("/explain/{region}", tags=["Explainability"])
def explain_region(
    region: str,
    lead_day: int = Query(1, ge=1, le=10, description="Forecast lead day (1-10)."),
    date: Optional[str] = Query(None, description="Forecast date (YYYY-MM-DD).")
):
    """
    Returns granular SHAP feature attributions and plain-language
    meteorological synopsis for a region and lead day.
    """
    engine = get_engine()
    timeline = engine.get_region_forecast(region_name=region, date_str=date)
    if not timeline:
        raise HTTPException(status_code=404, detail=f"Region '{region}' not found.")

    match = [item for item in timeline if item["lead_day"] == lead_day]
    if not match:
        raise HTTPException(status_code=404, detail=f"Lead day {lead_day} not found for region {region}.")

    return {
        "region": region,
        "lead_day": lead_day,
        "date": match[0]["date"],
        "confidence_score": match[0]["confidence_score"],
        "bust_probability": match[0]["bust_probability"],
        "risk_tier": match[0]["risk_tier"],
        "evidence_agreement": match[0].get("evidence_agreement", 1.0),
        "contradiction_flag": match[0].get("contradiction_flag", False),
        "synoptic_regime": match[0]["synoptic_regime"],
        "plain_language_summary": match[0]["plain_language_summary"],
        "top_drivers": match[0]["top_drivers"],
        "top_families": match[0].get("top_families", []),
        "operational_bulletin": match[0].get("operational_bulletin", {}),
    }


@app.post("/predict", tags=["Forecaster What-If Lab"])
def predict_custom_scenario(payload: WhatIfRequest):
    """
    Forecaster 'What-If' testing endpoint.
    Accepts arbitrary synoptic parameters (ensemble spread, pressure gradient, shear,
    moisture, regime, terrain, lead day) and returns real-time calibrated bust probability,
    confidence score, and SHAP explainability decomposition.
    """
    engine = get_engine()
    raw_dict = payload.model_dump()
    result = engine.predict_custom(raw_dict)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
