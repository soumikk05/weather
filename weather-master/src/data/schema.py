"""
Data Schema & Contract Definitions
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Defines the canonical column schema for forecast verification records,
subdivision metadata, and constants used across all data loaders.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np

# ---------------------------------------------------------------------------
# Data source labels — every record and API response MUST carry one
# ---------------------------------------------------------------------------
DATA_SOURCE_SYNTHETIC = "synthetic"
DATA_SOURCE_REAL = "real"

# ---------------------------------------------------------------------------
# Canonical Column Schema
# ---------------------------------------------------------------------------
# These are the columns that every data loader must produce.
# The schema separates:
#   - IDENTIFIERS:  who/when/where
#   - NWP FORECAST: what the model predicted
#   - TRUTH:        what was observed
#   - TARGET:       derived labels (computed downstream, not by loader)

IDENTIFIER_COLS = [
    "initialization_time",   # datetime: when the NWP model was initialised (e.g. 2024-06-15 00:00 UTC)
    "valid_time",            # datetime: the target time being forecast
    "lead_day",              # int 1-10
    "location_id",           # str: subdivision name or grid-cell ID
    "lat",                   # float: centroid latitude
    "lon",                   # float: centroid longitude
    "model_version",         # str: NWP model identifier (e.g. "NCUM_v3.2", "GFS_16", "synthetic_v2")
    "data_source",           # str: "synthetic" or "real"
]

NWP_FORECAST_COLS = [
    # Deterministic forecast fields
    "fcst_rainfall_mm",      # float: forecast daily accumulated rainfall (mm)
    "fcst_temp_2m_c",        # float: forecast 2m temperature (°C)
    "fcst_mslp_hpa",         # float: forecast mean sea level pressure (hPa)
    "fcst_wind_850_mps",     # float: forecast 850 hPa wind speed (m/s)
    "fcst_wind_200_mps",     # float: forecast 200 hPa wind speed (m/s)
    "fcst_rh_700_pct",       # float: forecast 700 hPa relative humidity (%)
    "fcst_geopot_500_m",     # float: forecast 500 hPa geopotential height (m)
    "fcst_cape_jkg",         # float: forecast CAPE (J/kg)
    "fcst_moisture_flux_conv",  # float: forecast integrated moisture flux convergence

    # Ensemble fields
    "ens_spread_rainfall",   # float: std dev of ensemble rainfall forecasts
    "ens_spread_temp",       # float: std dev of ensemble temperature forecasts
    "ens_spread_mslp",       # float: std dev of ensemble MSLP forecasts
    "ens_members_total",     # int: number of ensemble members
    "ens_members_rain_gt10", # int: members forecasting > 10mm rain
    "ens_members_rain_gt50", # int: members forecasting > 50mm rain
]

OBSERVATION_TRUTH_COLS = [
    "obs_rainfall_mm",       # float: observed daily accumulated rainfall (mm) — IMD gridded
    "obs_temp_2m_c",         # float: observed 2m temperature (°C) — optional
]

# Derived target columns (computed in Stage 2, not by data loaders)
TARGET_COLS = [
    "forecast_error_mm",     # float: fcst_rainfall_mm - obs_rainfall_mm
    "abs_error_mm",          # float: |forecast_error_mm|
    "is_bust",               # int 0/1: error exceeds location×season×lead 90th percentile
    "bust_threshold_mm",     # float: the threshold used
]

# Atmospheric-state predictors from ERA5 / analysis (NOT used as truth for rainfall)
ERA5_STATE_COLS = [
    "era5_mslp_hpa",
    "era5_wind_shear_mps",   # |V_200 - V_850|
    "era5_moisture_conv",
    "era5_vorticity_850",
    "era5_cape_jkg",
    "era5_sst_c",            # nearby ocean SST
    "era5_rh_700_pct",
]

# Large-scale oscillation indices
CLIMATE_INDEX_COLS = [
    "enso_oni",              # float: Oceanic Niño Index
    "mjo_rmm1",             # float: MJO RMM component 1
    "mjo_rmm2",             # float: MJO RMM component 2
    "mjo_amplitude",         # float: sqrt(rmm1² + rmm2²)
    "mjo_phase",             # int 1-8
    "iod_dmi",               # float: Indian Ocean Dipole Mode Index
    "bsiso_amp",             # float: BSISO amplitude (optional)
]

# Cyclone/depression proximity
CYCLONE_COLS = [
    "cyclone_present",       # int 0/1: active cyclone/depression within 1500 km
    "cyclone_dist_km",       # float: distance to nearest cyclone center (km), NaN if none
    "cyclone_intensity_kt",  # float: max sustained wind (kt), NaN if none
    "cyclone_category",      # str: DD/CS/SCS/VSCS/ESCS/SuCS or "none"
]

# Static geography
STATIC_GEO_COLS = [
    "elevation_m",           # float: mean elevation of location (m)
    "dist_coast_km",         # float: distance to nearest coastline (km)
    "land_fraction",         # float: land fraction 0-1 (1 = fully land)
    "terrain_type",          # str: Himalayan, Western_Ghats, etc.
    "terrain_complexity",    # float 0-1: orographic complexity index
]


# ---------------------------------------------------------------------------
# Subdivision Metadata (32 IMD meteorological subdivisions)
# ---------------------------------------------------------------------------
@dataclass
class SubdivisionInfo:
    """Metadata for one IMD meteorological subdivision."""
    name: str
    lat: float
    lon: float
    terrain_type: str
    terrain_complexity: float
    # IMD season calendar: dict mapping season name -> (start_month, end_month)
    season_calendar: Dict[str, tuple] = field(default_factory=dict)


SUBDIVISIONS: List[SubdivisionInfo] = [
    SubdivisionInfo("Jammu & Kashmir and Ladakh", 34.0, 76.5, "Himalayan", 0.88,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Himachal Pradesh", 31.8, 77.2, "Himalayan", 0.82,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Uttarakhand", 30.1, 79.2, "Himalayan", 0.80,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Punjab", 31.1, 75.3, "Northern_Plains", 0.30,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Haryana, Chandigarh & Delhi", 29.0, 76.8, "Northern_Plains", 0.32,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("West Uttar Pradesh", 28.2, 78.5, "Northern_Plains", 0.35,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("East Uttar Pradesh", 26.5, 82.5, "Northern_Plains", 0.40,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Bihar", 25.6, 85.8, "Northern_Plains", 0.45,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Sub-Himalayan West Bengal & Sikkim", 26.8, 88.4, "Northeastern_Hills", 0.84,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Gangetic West Bengal", 22.8, 87.9, "Coastal_Plains", 0.58,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Odisha", 20.3, 85.8, "Coastal_Plains", 0.62,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Jharkhand", 23.6, 85.3, "Central_Plateau", 0.42,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("East Madhya Pradesh", 23.2, 80.5, "Central_Plateau", 0.38,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("West Madhya Pradesh", 23.0, 76.5, "Central_Plateau", 0.36,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Gujarat Region", 22.3, 72.5, "Coastal_Plains", 0.52,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Saurashtra & Kutch", 22.2, 70.0, "Arid_Desert", 0.48,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("West Rajasthan", 26.9, 71.9, "Arid_Desert", 0.34,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("East Rajasthan", 26.5, 75.5, "Central_Plateau", 0.38,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Konkan & Goa", 16.0, 73.8, "Western_Ghats", 0.78,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Madhya Maharashtra", 18.5, 74.5, "Peninsular_Interior", 0.42,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Marathwada", 19.3, 76.5, "Peninsular_Interior", 0.40,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Vidarbha", 21.1, 79.1, "Central_Plateau", 0.41,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Chhattisgarh", 21.3, 81.8, "Central_Plateau", 0.45,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Coastal Andhra Pradesh", 16.5, 81.5, "Coastal_Plains", 0.66,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "ne_monsoon": (10, 12)}),
    SubdivisionInfo("Telangana", 17.8, 79.0, "Peninsular_Interior", 0.43,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Rayalaseema", 14.5, 78.5, "Peninsular_Interior", 0.44,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "ne_monsoon": (10, 12)}),
    # Tamil Nadu: NE monsoon is the PRIMARY rain season (Oct-Dec)
    SubdivisionInfo("Tamil Nadu, Puducherry & Karaikal", 11.0, 79.0, "Coastal_Plains", 0.56,
                    {"winter": (1, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "ne_monsoon": (10, 12)}),
    SubdivisionInfo("Coastal Karnataka", 13.5, 74.8, "Western_Ghats", 0.75,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("South Interior Karnataka", 13.0, 76.5, "Peninsular_Interior", 0.46,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Kerala & Mahe", 10.5, 76.2, "Western_Ghats", 0.80,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Assam & Meghalaya", 26.1, 92.9, "Northeastern_Hills", 0.85,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
    SubdivisionInfo("Arunachal Pradesh", 28.2, 94.7, "Northeastern_Hills", 0.88,
                    {"winter": (12, 2), "pre_monsoon": (3, 5), "sw_monsoon": (6, 9), "post_monsoon": (10, 11)}),
]

# Quick lookup by name
SUBDIVISION_MAP: Dict[str, SubdivisionInfo] = {s.name: s for s in SUBDIVISIONS}

# Terrain types
TERRAIN_TYPES = [
    "Himalayan", "Northern_Plains", "Northeastern_Hills",
    "Coastal_Plains", "Central_Plateau", "Arid_Desert",
    "Western_Ghats", "Peninsular_Interior",
]

# Synoptic regime labels
SYNOPTIC_REGIMES = [
    "quiescent_clear", "heat_wave", "active_monsoon", "break_monsoon",
    "western_disturbance", "monsoon_depression", "cyclonic_disturbance",
    "post_monsoon_transition",
]

# IMD rainfall categories (mm/day)
IMD_RAINFALL_CATEGORIES = {
    "no_rain": (0.0, 2.5),
    "light": (2.5, 15.6),
    "moderate": (15.6, 64.5),
    "heavy": (64.5, 115.5),
    "very_heavy": (115.5, 204.5),
    "extremely_heavy": (204.5, float("inf")),
}


def get_imd_category(rainfall_mm: float) -> str:
    """Returns the IMD rainfall category for a given daily rainfall amount."""
    for cat, (low, high) in IMD_RAINFALL_CATEGORIES.items():
        if low <= rainfall_mm < high:
            return cat
    return "extremely_heavy"


def imd_category_index(rainfall_mm: float) -> int:
    """Returns 0-5 index for IMD rainfall category."""
    cats = list(IMD_RAINFALL_CATEGORIES.keys())
    return cats.index(get_imd_category(rainfall_mm))


def is_category_miss(fcst_mm: float, obs_mm: float, n_categories: int = 2) -> bool:
    """Returns True if forecast misses observation by >= n IMD categories."""
    return abs(imd_category_index(fcst_mm) - imd_category_index(obs_mm)) >= n_categories


@dataclass
class ForecastRecord:
    """
    Canonical representation of a single forecast verification record.
    Used for type documentation; actual data flows through pandas DataFrames.
    """
    initialization_time: str
    valid_time: str
    lead_day: int
    location_id: str
    lat: float
    lon: float
    model_version: str
    data_source: str  # "synthetic" or "real"

    # NWP forecast
    fcst_rainfall_mm: float = 0.0
    fcst_temp_2m_c: float = 25.0
    fcst_mslp_hpa: float = 1013.0

    # Ensemble
    ens_spread_rainfall: float = 0.0
    ens_spread_temp: float = 0.0
    ens_members_total: int = 50

    # Observation truth
    obs_rainfall_mm: float = 0.0

    # Targets (computed downstream)
    forecast_error_mm: Optional[float] = None
    abs_error_mm: Optional[float] = None
    is_bust: Optional[int] = None
