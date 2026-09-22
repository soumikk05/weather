"""
Static Geography & Topographic Complexity Feature Family
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Family Name: 'static_geography'
Extracts:
- Mean terrain elevation (m) & normalized elevation
- Distance to Indian coastline (km)
- Coastal region proximity flag (< 60 km)
- Orographic / mountain barrier flag (> 1500 m elevation)
- Land area fraction [0.0 - 1.0]
- Orographic complexity index [0.0 - 1.0]
- Terrain classification code
"""

from typing import List
import numpy as np
import pandas as pd

from src.feature_families.base import BaseFeatureFamily
from src.data.schema import TERRAIN_TYPES
from src.data.static_geography import StaticGeographyLoader


class StaticGeographyFamily(BaseFeatureFamily):
    """Features capturing invariant topography, coastline proximity, and surface complexity."""

    def __init__(self):
        self._loader = StaticGeographyLoader()

    @property
    def family_name(self) -> str:
        return "static_geography"

    @property
    def feature_names(self) -> List[str]:
        return [
            "elevation_m",
            "dist_coast_km",
            "land_fraction",
            "terrain_complexity",
            "elevation_norm",
            "is_coastal_zone",
            "is_high_mountain_barrier",
            "terrain_type_code",
        ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)

        # Check if static geography columns are already present, else enrich via StaticGeographyLoader
        needed_cols = ["elevation_m", "dist_coast_km", "land_fraction", "terrain_complexity", "terrain_type"]
        missing = [c for c in needed_cols if c not in df.columns]

        if missing:
            enriched = self._loader.enrich_dataframe(df)
        else:
            enriched = df

        out["elevation_m"] = (enriched["elevation_m"] if "elevation_m" in enriched.columns else pd.Series([300.0]*len(enriched), index=enriched.index)).fillna(300.0)
        out["dist_coast_km"] = (enriched["dist_coast_km"] if "dist_coast_km" in enriched.columns else pd.Series([300.0]*len(enriched), index=enriched.index)).fillna(300.0)
        out["land_fraction"] = (enriched["land_fraction"] if "land_fraction" in enriched.columns else pd.Series([1.0]*len(enriched), index=enriched.index)).fillna(1.0)
        out["terrain_complexity"] = (enriched["terrain_complexity"] if "terrain_complexity" in enriched.columns else pd.Series([0.40]*len(enriched), index=enriched.index)).fillna(0.40)

        # Derived physical terms
        out["elevation_norm"] = (out["elevation_m"] / 3000.0).clip(0.0, 3.0).round(3)
        out["is_coastal_zone"] = (out["dist_coast_km"] <= 60.0).astype(float)
        out["is_high_mountain_barrier"] = (out["elevation_m"] >= 1500.0).astype(float)

        # Terrain categorical code
        terrain_vals = enriched.get("terrain_type", enriched.get("terrain", "Central_Plateau")).astype(str).values
        type_codes = [
            TERRAIN_TYPES.index(t) if t in TERRAIN_TYPES else 0
            for t in terrain_vals
        ]
        out["terrain_type_code"] = type_codes

        return out[self.feature_names]
