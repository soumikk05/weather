"""
Unit and Integration Tests for Stage 1 Data Layer
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

# Ensure root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.schema import (
    IDENTIFIER_COLS,
    DATA_SOURCE_SYNTHETIC,
    DATA_SOURCE_REAL,
    SUBDIVISIONS,
    get_imd_category,
    is_category_miss,
)
from src.data.synthetic import NonCircularSyntheticGenerator
from src.data.validation import validate_dataframe, ValidationReport
from src.data.static_geography import StaticGeographyLoader
from src.data.aggregation import aggregate_grid_to_subdivision, find_nearest_subdivision
from src.data.cyclone_tracks import CycloneTrackLoader
from src.data.gefs_reforecast import GEFSReforecastLoader
from src.data.ecmwf_open import ECMWFOpenDataLoader


def test_schema_and_subdivisions():
    """Verify subdivision metadata definitions."""
    assert len(SUBDIVISIONS) == 32
    for sub in SUBDIVISIONS:
        assert 6.0 <= sub.lat <= 38.0
        assert 68.0 <= sub.lon <= 98.0
        assert 0.0 <= sub.terrain_complexity <= 1.0


def test_imd_category_mappings():
    """Test IMD rainfall category thresholds."""
    assert get_imd_category(0.0) == "no_rain"
    assert get_imd_category(2.0) == "no_rain"
    assert get_imd_category(5.0) == "light"
    assert get_imd_category(35.0) == "moderate"
    assert get_imd_category(80.0) == "heavy"
    assert get_imd_category(150.0) == "very_heavy"
    assert get_imd_category(250.0) == "extremely_heavy"
    # Category miss test
    assert not is_category_miss(2.0, 10.0, n_categories=2)  # no_rain to light = 1 cat diff
    assert is_category_miss(2.0, 40.0, n_categories=2)   # no_rain to moderate = 2 cat diff


def test_non_circular_synthetic_generator():
    """Test non-circular synthetic generator for schema, realistic bust rate, and data_source tag."""
    gen = NonCircularSyntheticGenerator(random_seed=42)
    # Generate sample over 2 months for robust quantile estimation
    sub_names = ["Konkan & Goa", "East Rajasthan"]
    df = gen.load(start_date="2024-06-01", end_date="2024-07-31", locations=sub_names)

    # Check required identifier columns
    for col in IDENTIFIER_COLS:
        assert col in df.columns, f"Missing {col} in synthetic data"

    assert (df["data_source"] == DATA_SOURCE_SYNTHETIC).all()
    assert set(df["lead_day"].unique()) == set(range(1, 11))
    assert set(df["location_id"].unique()) == set(sub_names)

    # Target columns must be populated
    assert "is_bust" in df.columns
    assert "forecast_error_mm" in df.columns
    assert "abs_error_mm" in df.columns

    # Bust rate should be around ~8-15% with adequate sample size
    bust_rate = df["is_bust"].mean()
    assert 0.05 <= bust_rate <= 0.20, f"Bust rate {bust_rate:.3f} outside expected bounds [0.05, 0.20]"


def test_non_circularity_absence_of_exact_formula():
    """
    Verify non-circularity: error cannot be perfectly predicted by a simple
    deterministic linear combination of features (unlike the legacy generator).
    """
    gen = NonCircularSyntheticGenerator(random_seed=42)
    df = gen.load(start_date="2024-06-01", end_date="2024-07-15", locations=["Konkan & Goa"])

    feature_cols = [
        "fcst_rainfall_mm", "ens_spread_rainfall", "fcst_mslp_hpa",
        "fcst_wind_850_mps", "fcst_cape_jkg", "lead_day"
    ]
    X = df[feature_cols].values
    y = df["forecast_error_mm"].values

    # Fit least squares
    theta, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)
    preds = X @ theta
    corr = np.corrcoef(preds, y)[0, 1]

    # In legacy circular generator, R^2 was > 0.999. In non-circular,
    # feature correlation with error must be non-trivial but not near 1.0.
    assert corr < 0.95, f"Correlation {corr:.4f} is too high! Suggests circular formula leakage."


def test_data_validation():
    """Verify validation module correctly detects compliant and malformed data."""
    gen = NonCircularSyntheticGenerator(random_seed=123)
    df = gen.load(start_date="2024-06-01", end_date="2024-06-02", locations=["Punjab"])

    # Valid data should pass
    report = validate_dataframe(df)
    assert report.is_valid, f"Validation failed unexpectedly: {report.issues}"

    # Missing identifier column test
    corrupted_df = df.drop(columns=["lead_day"])
    report_bad = validate_dataframe(corrupted_df)
    assert not report_bad.is_valid
    assert any("lead_day" in issue for issue in report_bad.issues)

    # Unit anomaly test: temperature in Kelvin instead of Celsius
    kelvin_df = df.copy()
    kelvin_df["fcst_temp_2m_c"] = 305.0  # Kelvin
    report_kelvin = validate_dataframe(kelvin_df)
    assert any("fcst_temp_2m_c" in w or "temp" in w.lower() for w in report_kelvin.warnings)



def test_static_geography_loader():
    """Test topography and coastline distance calculations."""
    geo = StaticGeographyLoader()
    konkan = geo.get_subdivision_geography("Konkan & Goa")
    himalaya = geo.get_subdivision_geography("Jammu & Kashmir and Ladakh")

    # Konkan is coastal (small dist_coast, low elevation)
    assert konkan["dist_coast_km"] < 100.0
    assert konkan["elevation_m"] < 500.0

    # Himalayas are inland and high elevation
    assert himalaya["elevation_m"] > 2000.0
    assert himalaya["dist_coast_km"] > 500.0


def test_spatial_aggregation():
    """Test aggregation of grid cells to subdivision summary."""
    # Synthetic grid points within Konkan bounding box
    grid_data = pd.DataFrame({
        "lat": [16.0, 16.2, 16.5, 17.0],
        "lon": [73.5, 73.6, 73.8, 73.9],
        "rainfall_mm": [10.0, 20.0, 50.0, 80.0],
    })
    stats = aggregate_grid_to_subdivision(
        grid_data,
        lat_col="lat",
        lon_col="lon",
        value_col="rainfall_mm",
        subdivision_name="Konkan & Goa",
    )
    assert stats["cell_count"] == 4
    assert stats["max_peak"] == 80.0
    assert stats["mean"] > 10.0
    assert stats["spatial_std"] > 0.0
    assert stats["wet_fraction"] == 1.0  # All > 2.5 mm


def test_cyclone_track_loader_graceful_defaults():
    """Test IBTrACS loader provides default schema columns even when offline."""
    loader = CycloneTrackLoader(cache_dir="data/cyclone_tracks")
    features = loader.get_cyclone_features_for_point("2024-06-01", 16.0, 73.8)
    assert "cyclone_present" in features
    assert "cyclone_dist_km" in features
    assert "cyclone_category" in features


def test_gefs_and_ecmwf_loader_sources():
    """Verify real data loader source attributes and interfaces."""
    gefs = GEFSReforecastLoader()
    assert gefs.get_data_source() == DATA_SOURCE_REAL

    ecmwf = ECMWFOpenDataLoader()
    assert ecmwf.get_data_source() == DATA_SOURCE_REAL
