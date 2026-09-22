"""
FastAPI Operational Backend for Forecast Bust Detection
Smart India Hackathon - NCMRWF / Ministry of Earth Sciences

Exposes REST endpoints for:
- Regional Confidence Maps (Day 1 - 10)
- 10-Day Subdivision Forecast Profiles
- SHAP-Based Plain-Language Explanations
- Interactive Synoptic 'What-If' Predictions
"""

import os
import sys
# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.generate_synthetic_data import SUBDIVISIONS
from src.inference import get_engine


app = FastAPI(
    title="NCMRWF Forecast Bust Detection API",
    description="AI-Driven Medium-Range (Day 1–10) NWP Forecast Bust Detection and Confidence Mapping System.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for cross-origin dashboard access
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
    status: str
    service: str
    version: str
    subdivisions_count: int
    available_dates_count: int
    models_loaded: bool


class RegionMetadata(BaseModel):
    name: str
    lat: float
    lon: float
    terrain: str
    terrain_difficulty: float


class ConfidenceMapItem(BaseModel):
    date: str
    region: str
    lat: float
    lon: float
    terrain: str
    terrain_difficulty: float
    synoptic_regime: str
    lead_day: int
    bust_probability: float
    predicted_error_mm: float
    confidence_score: float
    risk_tier: str
    top_drivers: List[str]
    plain_language_summary: str


class ForecastProfileItem(BaseModel):
    lead_day: int
    date: str
    region: str
    terrain: str
    synoptic_regime: str
    ens_spread_rainfall: float
    bust_probability: float
    predicted_error_mm: float
    confidence_score: float
    risk_tier: str
    plain_language_summary: str
    top_drivers: List[Dict]


class WhatIfRequest(BaseModel):
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
    """System health check and loaded model diagnostics."""
    engine = get_engine()
    return {
        "status": "healthy",
        "service": "NCMRWF Forecast Bust Detection System",
        "version": "1.0.0",
        "subdivisions_count": len(SUBDIVISIONS),
        "available_dates_count": len(engine.get_available_dates()),
        "models_loaded": True,
    }


@app.get("/regions", response_model=List[RegionMetadata], tags=["Metadata"])
def get_regions():
    """Returns all 32 Indian meteorological subdivisions with centroid coordinates and terrain."""
    return SUBDIVISIONS


@app.get("/dates", response_model=List[str], tags=["Metadata"])
def get_dates():
    """Returns list of all available historical forecast verification dates."""
    engine = get_engine()
    return engine.get_available_dates()


@app.get("/confidence_map", response_model=List[ConfidenceMapItem], tags=["Operational Forecasts"])
def get_confidence_map(
    date: Optional[str] = Query(None, description="Forecast date (YYYY-MM-DD). Defaults to latest available."),
    lead_day: int = Query(1, ge=1, le=10, description="Forecast lead day (Day 1 to Day 10).")
):
    """
    Returns full region-wise confidence scores, calibrated bust probabilities,
    and top meteorological risk factors for all 32 subdivisions at specified lead time.
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
    
    # Filter for requested lead day
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
        "synoptic_regime": match[0]["synoptic_regime"],
        "plain_language_summary": match[0]["plain_language_summary"],
        "top_drivers": match[0]["top_drivers"],
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
