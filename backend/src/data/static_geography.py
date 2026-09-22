"""
Static Geography & Terrain Feature Loader
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Provides static geographical, topographic, and coastal proximity attributes
for IMD meteorological subdivisions and fine-scale grid cells.

Features:
  - elevation_m: Mean elevation (m above sea level)
  - dist_coast_km: Geodesic distance to nearest Indian coastline (km)
  - land_fraction: Land area fraction [0.0 - 1.0]
  - terrain_type: Canonical terrain category
  - terrain_complexity: Orographic complexity index [0.0 - 1.0]
"""

import os
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from src.data.schema import (
    STATIC_GEO_COLS,
    SUBDIVISIONS,
    SubdivisionInfo,
)


# Approximate representative Indian coastline reference points (lat, lon)
# for fast distance calculation from any subdivision centroid.
INDIAN_COASTLINE_POINTS = [
    # Gujarat / Kutch
    (23.0, 68.5), (21.7, 69.5), (20.8, 70.8), (21.0, 72.5),
    # Maharashtra / Goa
    (19.0, 72.8), (17.5, 73.2), (15.5, 73.8),
    # Karnataka / Kerala
    (14.0, 74.4), (12.0, 75.2), (10.0, 76.2), (8.1, 77.5),
    # Tamil Nadu / Andhra Pradesh
    (9.3, 79.1), (11.9, 79.8), (13.1, 80.3), (16.0, 80.8), (17.7, 83.3),
    # Odisha / West Bengal
    (19.8, 85.8), (21.5, 87.0), (21.8, 88.5),
]


def _distance_to_nearest_coast(lat: float, lon: float) -> float:
    """Calculate distance in km to nearest representative Indian coastline point."""
    r_earth = 6371.0
    min_dist = float("inf")
    phi1 = np.radians(lat)

    for c_lat, c_lon in INDIAN_COASTLINE_POINTS:
        phi2 = np.radians(c_lat)
        delta_phi = np.radians(c_lat - lat)
        delta_lambda = np.radians(c_lon - lon)
        a = (
            np.sin(delta_phi / 2.0) ** 2
            + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0) ** 2
        )
        c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
        d = r_earth * c
        if d < min_dist:
            min_dist = d
    return float(round(min_dist, 1))


# Curated geographic attributes for the 32 IMD meteorological subdivisions
# Elevation based on SRTM/ETOPO1 mean topography.
SUBDIVISION_GEO_METADATA: Dict[str, Dict[str, object]] = {
    "Jammu & Kashmir and Ladakh": {
        "elevation_m": 3150.0,
        "land_fraction": 1.0,
    },
    "Himachal Pradesh": {
        "elevation_m": 2450.0,
        "land_fraction": 1.0,
    },
    "Uttarakhand": {
        "elevation_m": 2100.0,
        "land_fraction": 1.0,
    },
    "Punjab": {
        "elevation_m": 250.0,
        "land_fraction": 1.0,
    },
    "Haryana, Chandigarh & Delhi": {
        "elevation_m": 220.0,
        "land_fraction": 1.0,
    },
    "West Uttar Pradesh": {
        "elevation_m": 180.0,
        "land_fraction": 1.0,
    },
    "East Uttar Pradesh": {
        "elevation_m": 110.0,
        "land_fraction": 1.0,
    },
    "Bihar": {
        "elevation_m": 75.0,
        "land_fraction": 1.0,
    },
    "Sub-Himalayan West Bengal & Sikkim": {
        "elevation_m": 1350.0,
        "land_fraction": 1.0,
    },
    "Gangetic West Bengal": {
        "elevation_m": 25.0,
        "land_fraction": 0.88,
    },
    "Odisha": {
        "elevation_m": 280.0,
        "land_fraction": 0.85,
    },
    "Jharkhand": {
        "elevation_m": 420.0,
        "land_fraction": 1.0,
    },
    "East Madhya Pradesh": {
        "elevation_m": 410.0,
        "land_fraction": 1.0,
    },
    "West Madhya Pradesh": {
        "elevation_m": 460.0,
        "land_fraction": 1.0,
    },
    "Gujarat Region": {
        "elevation_m": 85.0,
        "land_fraction": 0.82,
    },
    "Saurashtra & Kutch": {
        "elevation_m": 70.0,
        "land_fraction": 0.72,
    },
    "West Rajasthan": {
        "elevation_m": 210.0,
        "land_fraction": 1.0,
    },
    "East Rajasthan": {
        "elevation_m": 340.0,
        "land_fraction": 1.0,
    },
    "Konkan & Goa": {
        "elevation_m": 160.0,
        "land_fraction": 0.75,
    },
    "Madhya Maharashtra": {
        "elevation_m": 580.0,
        "land_fraction": 1.0,
    },
    "Marathwada": {
        "elevation_m": 490.0,
        "land_fraction": 1.0,
    },
    "Vidarbha": {
        "elevation_m": 290.0,
        "land_fraction": 1.0,
    },
    "Chhattisgarh": {
        "elevation_m": 360.0,
        "land_fraction": 1.0,
    },
    "Coastal Andhra Pradesh": {
        "elevation_m": 45.0,
        "land_fraction": 0.80,
    },
    "Telangana": {
        "elevation_m": 430.0,
        "land_fraction": 1.0,
    },
    "Rayalaseema": {
        "elevation_m": 410.0,
        "land_fraction": 1.0,
    },
    "Tamil Nadu, Puducherry & Karaikal": {
        "elevation_m": 180.0,
        "land_fraction": 0.82,
    },
    "Coastal Karnataka": {
        "elevation_m": 120.0,
        "land_fraction": 0.78,
    },
    "South Interior Karnataka": {
        "elevation_m": 780.0,
        "land_fraction": 1.0,
    },
    "Kerala & Mahe": {
        "elevation_m": 240.0,
        "land_fraction": 0.76,
    },
    "Assam & Meghalaya": {
        "elevation_m": 620.0,
        "land_fraction": 1.0,
    },
    "Arunachal Pradesh": {
        "elevation_m": 2150.0,
        "land_fraction": 1.0,
    },
}


class StaticGeographyLoader:
    """
    Provides static topography and coastline features for subdivisions or grid points.
    """

    def __init__(self):
        # Build reference cache for all 32 subdivisions
        self._cache = {}
        for sub in SUBDIVISIONS:
            meta = SUBDIVISION_GEO_METADATA.get(sub.name, {"elevation_m": 300.0, "land_fraction": 1.0})
            dist_c = _distance_to_nearest_coast(sub.lat, sub.lon)
            self._cache[sub.name] = {
                "elevation_m": float(meta["elevation_m"]),
                "dist_coast_km": float(dist_c),
                "land_fraction": float(meta["land_fraction"]),
                "terrain_type": sub.terrain_type,
                "terrain_complexity": float(sub.terrain_complexity),
            }

    def get_subdivision_geography(self, subdivision_name: str) -> Dict[str, object]:
        """Return static geography dictionary for a given subdivision."""
        if subdivision_name in self._cache:
            return dict(self._cache[subdivision_name])
        # Fallback default
        return {
            "elevation_m": 300.0,
            "dist_coast_km": 300.0,
            "land_fraction": 1.0,
            "terrain_type": "Central_Plateau",
            "terrain_complexity": 0.40,
        }

    def get_point_geography(self, lat: float, lon: float, terrain_type: str = "Central_Plateau") -> Dict[str, object]:
        """Estimate static geography for an arbitrary (lat, lon) point."""
        dist_c = _distance_to_nearest_coast(lat, lon)
        # Approximate elevation proxy based on latitude and proximity to Himalayas/Ghats
        elevation = 300.0
        complexity = 0.4
        if lat > 28.0:
            elevation = 1800.0
            complexity = 0.8
            terrain_type = "Himalayan"
        elif 8.0 <= lat <= 16.0 and lon < 76.5:
            elevation = 600.0
            complexity = 0.75
            terrain_type = "Western_Ghats"
        elif dist_c < 60.0:
            elevation = 30.0
            complexity = 0.3
            terrain_type = "Coastal_Plains"

        return {
            "elevation_m": elevation,
            "dist_coast_km": dist_c,
            "land_fraction": 0.85 if dist_c < 30.0 else 1.0,
            "terrain_type": terrain_type,
            "terrain_complexity": complexity,
        }

    def enrich_dataframe(
        self,
        df: pd.DataFrame,
        location_col: str = "location_id",
        lat_col: str = "lat",
        lon_col: str = "lon",
    ) -> pd.DataFrame:
        """
        Add static geography features to a DataFrame.
        """
        out = df.copy()

        # If location_id matches subdivisions, use curated lookup
        if location_col in out.columns:
            elevations = []
            dist_coasts = []
            land_fracs = []
            terrains = []
            complexities = []

            for _, row in out.iterrows():
                loc = row.get(location_col)
                if loc in self._cache:
                    geo = self._cache[loc]
                else:
                    lat = row.get(lat_col, 20.0)
                    lon = row.get(lon_col, 78.0)
                    geo = self.get_point_geography(lat, lon)

                elevations.append(geo["elevation_m"])
                dist_coasts.append(geo["dist_coast_km"])
                land_fracs.append(geo["land_fraction"])
                terrains.append(geo["terrain_type"])
                complexities.append(geo["terrain_complexity"])

            out["elevation_m"] = elevations
            out["dist_coast_km"] = dist_coasts
            out["land_fraction"] = land_fracs
            out["terrain_type"] = terrains
            out["terrain_complexity"] = complexities
        return out
