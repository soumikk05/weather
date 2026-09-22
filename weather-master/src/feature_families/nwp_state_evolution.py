"""
NWP State Evolution Feature Family
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Family Name: 'nwp_state_evolution'
Extracts:
- Raw NWP predicted thermodynamic and dynamic variables
- Vertical tropospheric wind shear |V_200 - V_850|
- Baroclinic instability proxy
- Convective vulnerability index (CAPE x mid-troposphere RH)
- Dynamic instability composite
- Heavy precipitation indicator flags
"""

from typing import List
import numpy as np
import pandas as pd

from src.feature_families.base import BaseFeatureFamily


class NWPStateEvolutionFamily(BaseFeatureFamily):
    """Features capturing the NWP model's predicted thermodynamic & dynamic state."""

    @property
    def family_name(self) -> str:
        return "nwp_state_evolution"

    @property
    def feature_names(self) -> List[str]:
        return [
            "fcst_rainfall_mm",
            "fcst_temp_2m_c",
            "fcst_mslp_hpa",
            "fcst_wind_850_mps",
            "fcst_wind_200_mps",
            "fcst_rh_700_pct",
            "fcst_geopot_500_m",
            "fcst_cape_jkg",
            "vertical_wind_shear",
            "baroclinic_gradient_proxy",
            "convective_vulnerability",
            "dynamic_instability_composite",
            "heavy_rain_flag",
        ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)

        # Baseline forecast fields (with safe fallbacks)
        out["fcst_rainfall_mm"] = (df["fcst_rainfall_mm"].fillna(0.0) if "fcst_rainfall_mm" in df.columns else pd.Series([0.0]*len(df), index=df.index)).clip(lower=0.0)
        out["fcst_temp_2m_c"] = (df["fcst_temp_2m_c"].fillna(25.0) if "fcst_temp_2m_c" in df.columns else pd.Series([25.0]*len(df), index=df.index))
        out["fcst_mslp_hpa"] = (df["fcst_mslp_hpa"].fillna(1013.0) if "fcst_mslp_hpa" in df.columns else pd.Series([1013.0]*len(df), index=df.index))
        out["fcst_wind_850_mps"] = (df["fcst_wind_850_mps"].fillna(8.0) if "fcst_wind_850_mps" in df.columns else pd.Series([8.0]*len(df), index=df.index))
        out["fcst_wind_200_mps"] = (df["fcst_wind_200_mps"].fillna(20.0) if "fcst_wind_200_mps" in df.columns else pd.Series([20.0]*len(df), index=df.index))
        out["fcst_rh_700_pct"] = (df["fcst_rh_700_pct"].fillna(65.0) if "fcst_rh_700_pct" in df.columns else pd.Series([65.0]*len(df), index=df.index)).clip(0.0, 100.0)
        out["fcst_geopot_500_m"] = (df["fcst_geopot_500_m"].fillna(5840.0) if "fcst_geopot_500_m" in df.columns else pd.Series([5840.0]*len(df), index=df.index))
        out["fcst_cape_jkg"] = (df["fcst_cape_jkg"].fillna(500.0) if "fcst_cape_jkg" in df.columns else pd.Series([500.0]*len(df), index=df.index)).clip(lower=0.0)

        # Vertical shear |V_200 - V_850|
        out["vertical_wind_shear"] = np.abs(out["fcst_wind_200_mps"] - out["fcst_wind_850_mps"])

        # Baroclinic instability proxy: anomaly from standard sea level pressure (1013.25) * shear
        mslp_anomaly = np.maximum(0.0, 1013.25 - out["fcst_mslp_hpa"])
        out["baroclinic_gradient_proxy"] = (mslp_anomaly / 10.0) * (out["vertical_wind_shear"] / 10.0)

        # Convective vulnerability: CAPE normalized * mid-troposphere RH fraction
        out["convective_vulnerability"] = (out["fcst_cape_jkg"] / 1000.0) * (out["fcst_rh_700_pct"] / 100.0)

        # Dynamic instability composite index
        out["dynamic_instability_composite"] = (
            (mslp_anomaly / 5.0)
            * (out["vertical_wind_shear"] / 15.0)
            * (out["fcst_rh_700_pct"] / 50.0)
        ).round(3)

        # Heavy rain indicator (IMD Moderate/Heavy threshold >= 35.5 mm)
        out["heavy_rain_flag"] = (out["fcst_rainfall_mm"] >= 35.5).astype(float)

        return out[self.feature_names]
