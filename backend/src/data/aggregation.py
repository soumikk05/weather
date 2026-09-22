"""
Spatial Aggregation & Grid-to-Subdivision Mapping
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Provides tools for:
  1. Aggregating high-resolution (0.25° × 0.25°) gridded forecasts & observations
     up to IMD meteorological subdivision level.
  2. Preserving sub-grid heterogeneity metrics:
     - Area-weighted mean rainfall
     - Spatial standard deviation (convective clumpiness / dispersion)
     - Maximum grid cell rainfall (extreme local convective peaks / cloudburst proxy)
     - 90th percentile rainfall
     - Wet area fraction (fraction of grid cells with rainfall > 2.5 mm)
  3. Mapping arbitrary (lat, lon) coordinates to nearest subdivision.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.data.schema import SUBDIVISIONS, SubdivisionInfo, SUBDIVISION_MAP


# Approximate bounding boxes (lat_min, lat_max, lon_min, lon_max) for the 32 IMD subdivisions
# Used for spatial filtering and aggregation.
SUBDIVISION_BOUNDS: Dict[str, Tuple[float, float, float, float]] = {
    "Jammu & Kashmir and Ladakh": (32.0, 37.5, 73.0, 80.5),
    "Himachal Pradesh": (30.3, 33.3, 75.5, 79.1),
    "Uttarakhand": (28.7, 31.5, 77.5, 81.1),
    "Punjab": (29.5, 32.5, 73.8, 77.0),
    "Haryana, Chandigarh & Delhi": (27.6, 31.0, 74.4, 77.6),
    "West Uttar Pradesh": (26.0, 30.5, 77.0, 81.0),
    "East Uttar Pradesh": (23.8, 28.5, 81.0, 84.8),
    "Bihar": (24.2, 27.6, 83.3, 88.3),
    "Sub-Himalayan West Bengal & Sikkim": (25.5, 28.2, 87.8, 89.9),
    "Gangetic West Bengal": (21.5, 24.5, 86.5, 89.2),
    "Odisha": (17.8, 22.6, 81.4, 87.5),
    "Jharkhand": (21.9, 25.4, 83.3, 87.9),
    "East Madhya Pradesh": (21.5, 25.3, 78.5, 82.8),
    "West Madhya Pradesh": (21.1, 26.9, 74.0, 79.5),
    "Gujarat Region": (20.1, 24.7, 71.5, 74.5),
    "Saurashtra & Kutch": (20.5, 24.5, 68.1, 72.3),
    "West Rajasthan": (24.5, 30.2, 69.5, 75.0),
    "East Rajasthan": (23.5, 28.5, 74.0, 78.3),
    "Konkan & Goa": (14.8, 20.2, 72.6, 74.5),
    "Madhya Maharashtra": (15.7, 21.5, 73.5, 76.5),
    "Marathwada": (17.6, 20.7, 74.8, 78.3),
    "Vidarbha": (19.4, 21.8, 77.2, 80.9),
    "Chhattisgarh": (17.8, 24.1, 80.2, 84.4),
    "Coastal Andhra Pradesh": (13.5, 19.2, 79.9, 84.8),
    "Telangana": (15.8, 19.9, 77.2, 81.8),
    "Rayalaseema": (12.6, 16.2, 76.8, 80.1),
    "Tamil Nadu, Puducherry & Karaikal": (8.0, 13.6, 76.2, 80.4),
    "Coastal Karnataka": (12.7, 15.1, 74.0, 75.5),
    "South Interior Karnataka": (11.5, 15.0, 75.0, 78.5),
    "Kerala & Mahe": (8.2, 12.8, 74.8, 77.6),
    "Assam & Meghalaya": (24.8, 28.0, 89.7, 96.0),
    "Arunachal Pradesh": (26.5, 29.5, 91.5, 97.4),
}


def find_nearest_subdivision(lat: float, lon: float) -> str:
    """Find the nearest IMD subdivision name by Great Circle distance."""
    min_dist = float("inf")
    best_name = SUBDIVISIONS[0].name

    for sub in SUBDIVISIONS:
        # Euclidean approximation for fast matching
        d = (lat - sub.lat) ** 2 + ((lon - sub.lon) * np.cos(np.radians(sub.lat))) ** 2
        if d < min_dist:
            min_dist = d
            best_name = sub.name

    return best_name


def aggregate_grid_to_subdivision(
    grid_df: pd.DataFrame,
    lat_col: str = "lat",
    lon_col: str = "lon",
    value_col: str = "rainfall_mm",
    subdivision_name: Optional[str] = None,
) -> Dict[str, float]:
    """
    Compute subdivision-level summary statistics from high-resolution grid cells.

    Returns
    -------
    dict with:
      mean: Area-weighted mean rainfall (mm)
      spatial_std: Standard deviation across grid cells (mm)
      max_peak: Maximum grid-cell rainfall (mm)
      p90: 90th percentile grid-cell rainfall (mm)
      wet_fraction: Fraction of grid cells with value > 2.5 mm
      cell_count: Number of grid cells contributing
    """
    if subdivision_name and subdivision_name in SUBDIVISION_BOUNDS:
        lat_min, lat_max, lon_min, lon_max = SUBDIVISION_BOUNDS[subdivision_name]
        mask = (
            (grid_df[lat_col] >= lat_min)
            & (grid_df[lat_col] <= lat_max)
            & (grid_df[lon_col] >= lon_min)
            & (grid_df[lon_col] <= lon_max)
        )
        subset = grid_df[mask]
    else:
        subset = grid_df

    if subset.empty:
        return {
            "mean": 0.0,
            "spatial_std": 0.0,
            "max_peak": 0.0,
            "p90": 0.0,
            "wet_fraction": 0.0,
            "cell_count": 0,
        }

    values = subset[value_col].to_numpy()
    # Cosine latitude weighting for spherical area correction
    weights = np.cos(np.radians(subset[lat_col].to_numpy()))
    weights = np.maximum(weights, 0.01)
    norm_weights = weights / np.sum(weights)

    mean_val = float(np.sum(values * norm_weights))
    variance = float(np.sum(norm_weights * (values - mean_val) ** 2))
    spatial_std = float(np.sqrt(max(0.0, variance)))
    max_peak = float(np.max(values))
    p90 = float(np.percentile(values, 90))
    wet_frac = float(np.mean(values > 2.5))

    return {
        "mean": round(mean_val, 2),
        "spatial_std": round(spatial_std, 2),
        "max_peak": round(max_peak, 2),
        "p90": round(p90, 2),
        "wet_fraction": round(wet_frac, 3),
        "cell_count": len(values),
    }
