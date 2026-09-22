"""
Data Layer for Forecast Bust Detection System.
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Provides:
  - Canonical schema definitions & validation
  - Real-data loaders (IMD, ECMWF, GEFS, ERA5, Climate indices, Cyclone tracks)
  - Non-circular synthetic test data generator
  - Topographic & coastal static geography
  - Spatial aggregation utilities (grid to subdivision)
"""

from src.data.schema import (
    ForecastRecord,
    SubdivisionInfo,
    SUBDIVISIONS,
    SUBDIVISION_MAP,
    DATA_SOURCE_SYNTHETIC,
    DATA_SOURCE_REAL,
    IDENTIFIER_COLS,
    NWP_FORECAST_COLS,
    OBSERVATION_TRUTH_COLS,
    TARGET_COLS,
    ERA5_STATE_COLS,
    CLIMATE_INDEX_COLS,
    CYCLONE_COLS,
    STATIC_GEO_COLS,
    IMD_RAINFALL_CATEGORIES,
    get_imd_category,
    is_category_miss,
)
from src.data.loaders import BaseDataLoader
from src.data.synthetic import NonCircularSyntheticGenerator
from src.data.imd_rainfall import IMDRainfallLoader
from src.data.ecmwf_open import ECMWFOpenDataLoader
from src.data.gefs_reforecast import GEFSReforecastLoader
from src.data.era5 import ERA5AtmosphericStateLoader
from src.data.climate_indices import ClimateIndicesLoader
from src.data.cyclone_tracks import CycloneTrackLoader
from src.data.static_geography import StaticGeographyLoader
from src.data.aggregation import (
    aggregate_grid_to_subdivision,
    find_nearest_subdivision,
    SUBDIVISION_BOUNDS,
)
from src.data.validation import validate_dataframe, ValidationReport

__all__ = [
    # Schema & Constants
    "ForecastRecord",
    "SubdivisionInfo",
    "SUBDIVISIONS",
    "SUBDIVISION_MAP",
    "DATA_SOURCE_SYNTHETIC",
    "DATA_SOURCE_REAL",
    "IDENTIFIER_COLS",
    "NWP_FORECAST_COLS",
    "OBSERVATION_TRUTH_COLS",
    "TARGET_COLS",
    "ERA5_STATE_COLS",
    "CLIMATE_INDEX_COLS",
    "CYCLONE_COLS",
    "STATIC_GEO_COLS",
    "IMD_RAINFALL_CATEGORIES",
    "get_imd_category",
    "is_category_miss",
    # Base Contract
    "BaseDataLoader",
    # Loaders
    "NonCircularSyntheticGenerator",
    "IMDRainfallLoader",
    "ECMWFOpenDataLoader",
    "GEFSReforecastLoader",
    "ERA5AtmosphericStateLoader",
    "ClimateIndicesLoader",
    "CycloneTrackLoader",
    "StaticGeographyLoader",
    # Aggregation & Validation
    "aggregate_grid_to_subdivision",
    "find_nearest_subdivision",
    "SUBDIVISION_BOUNDS",
    "validate_dataframe",
    "ValidationReport",
]
