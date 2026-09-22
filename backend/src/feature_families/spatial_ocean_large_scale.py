"""
Large-Scale Climate Modes & Ocean Teleconnections Feature Family
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Family Name: 'spatial_ocean_large_scale'
Extracts:
- El Niño-Southern Oscillation (ENSO ONI)
- Madden-Julian Oscillation (MJO Amplitude & Phase)
- Indian Ocean Dipole (IOD DMI)
- Sea Surface Temperature (SST anomaly)
- Tropical cyclone proximity and wind intensity
- Large-scale active monsoon teleconnection composite
"""

from typing import List
import numpy as np
import pandas as pd

from src.feature_families.base import BaseFeatureFamily


class SpatialOceanLargeScaleFamily(BaseFeatureFamily):
    """Features capturing planetary wave oscillations, oceanic heat content, and cyclonic proximity."""

    @property
    def family_name(self) -> str:
        return "spatial_ocean_large_scale"

    @property
    def feature_names(self) -> List[str]:
        return [
            "enso_oni",
            "mjo_amplitude",
            "mjo_phase",
            "iod_dmi",
            "era5_sst_c",
            "cyclone_active_flag",
            "cyclone_proximity_index",
            "cyclone_intensity_kt",
            "active_monsoon_teleconnection_index",
        ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)

        # 1. Teleconnection indices with safe defaults
        enso_val = df["enso_oni"] if "enso_oni" in df.columns else (df["enso_oni_index"] if "enso_oni_index" in df.columns else pd.Series([0.0]*len(df), index=df.index))
        out["enso_oni"] = enso_val.fillna(0.0)
        out["mjo_amplitude"] = (df["mjo_amplitude"].fillna(1.0) if "mjo_amplitude" in df.columns else pd.Series([1.0]*len(df), index=df.index)).clip(lower=0.0)
        out["mjo_phase"] = (df["mjo_phase"].fillna(4) if "mjo_phase" in df.columns else pd.Series([4]*len(df), index=df.index)).clip(1, 8).astype(int)
        out["iod_dmi"] = (df["iod_dmi"].fillna(0.0) if "iod_dmi" in df.columns else pd.Series([0.0]*len(df), index=df.index))
        out["era5_sst_c"] = (df["era5_sst_c"].fillna(28.5) if "era5_sst_c" in df.columns else pd.Series([28.5]*len(df), index=df.index))

        # 2. Cyclone proximity features
        is_cyc = (df["cyclone_present"].fillna(0) if "cyclone_present" in df.columns else pd.Series([0]*len(df), index=df.index)).astype(int)
        dist_km = df["cyclone_dist_km"] if "cyclone_dist_km" in df.columns else pd.Series([np.nan]*len(df), index=df.index)
        intensity = (df["cyclone_intensity_kt"].fillna(0.0) if "cyclone_intensity_kt" in df.columns else pd.Series([0.0]*len(df), index=df.index))

        out["cyclone_active_flag"] = is_cyc.astype(float)
        # Normalized proximity: 1.0 at 0km, decaying to ~0.06 at 1500km
        clean_dist = dist_km.fillna(5000.0).clip(lower=0.0)
        out["cyclone_proximity_index"] = (100.0 / (clean_dist + 100.0)).round(4)
        out["cyclone_intensity_kt"] = intensity.fillna(0.0).clip(lower=0.0)

        # 3. Active monsoon composite:
        # MJO in Phase 3, 4, or 5 over the Indian Ocean / Maritime Continent
        # amplifies monsoon depressions and precipitation predictability breakdown
        mjo_favorable = out["mjo_phase"].isin([3, 4, 5]).astype(float)
        mjo_strength = out["mjo_amplitude"].clip(0.0, 3.0)
        out["active_monsoon_teleconnection_index"] = (
            mjo_favorable * mjo_strength + (out["iod_dmi"] > 0.4).astype(float) * 0.5
        ).round(3)

        return out[self.feature_names]
