"""
Uncertainty & Ensemble Spread Feature Family
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Family Name: 'uncertainty'
Extracts:
- Multi-member ensemble standard deviations (Rainfall, 2m Temp, MSLP)
- Compounding lead-time spread interaction
- Rate of ensemble dispersion (spread to lead ratio)
- Ensemble agreement probabilities for moderate and extreme precipitation (>10mm, >50mm)
- Relative coefficient of variation (spread normalized by forecast rainfall)
"""

from typing import List
import numpy as np
import pandas as pd

from src.feature_families.base import BaseFeatureFamily


class UncertaintyFamily(BaseFeatureFamily):
    """Features capturing ensemble dispersion, multi-member consensus, and growth rates."""

    @property
    def family_name(self) -> str:
        return "uncertainty"

    @property
    def feature_names(self) -> List[str]:
        return [
            "ens_spread_rainfall",
            "ens_spread_temp",
            "ens_spread_mslp",
            "spread_lead_interaction",
            "spread_to_lead_ratio",
            "ens_prob_rain_gt10",
            "ens_prob_rain_gt50",
            "relative_spread_ratio",
        ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)

        # Baseline ensemble columns with fallback to single-model / legacy columns
        spread_rain = df.get("ens_spread_rainfall", df.get("ensemble_spread", 0.0)).fillna(0.0).clip(lower=0.0)
        spread_temp = (df["ens_spread_temp"].fillna(1.0) if "ens_spread_temp" in df.columns else pd.Series([1.0]*len(df), index=df.index)).clip(lower=0.0)
        spread_mslp = (df["ens_spread_mslp"].fillna(1.5) if "ens_spread_mslp" in df.columns else pd.Series([1.5]*len(df), index=df.index)).clip(lower=0.0)
        lead = (df["lead_day"].fillna(1.0) if "lead_day" in df.columns else pd.Series([1.0]*len(df), index=df.index)).clip(lower=1.0)
        fcst_rain = (df["fcst_rainfall_mm"].fillna(0.0) if "fcst_rainfall_mm" in df.columns else pd.Series([0.0]*len(df), index=df.index)).clip(lower=0.0)

        out["ens_spread_rainfall"] = spread_rain
        out["ens_spread_temp"] = spread_temp
        out["ens_spread_mslp"] = spread_mslp

        # Lead time interaction terms
        out["spread_lead_interaction"] = (spread_rain * lead).round(3)
        out["spread_to_lead_ratio"] = (spread_rain / (lead + 0.5)).round(3)

        # Member agreement probabilities
        total_members = (df["ens_members_total"].fillna(50) if "ens_members_total" in df.columns else pd.Series([50]*len(df), index=df.index)).clip(lower=1)
        gt10 = df.get("ens_members_rain_gt10", (fcst_rain > 10.0).astype(int) * total_members).fillna(0)
        gt50 = df.get("ens_members_rain_gt50", (fcst_rain > 50.0).astype(int) * total_members).fillna(0)

        out["ens_prob_rain_gt10"] = (gt10 / total_members).clip(0.0, 1.0).round(3)
        out["ens_prob_rain_gt50"] = (gt50 / total_members).clip(0.0, 1.0).round(3)

        # Relative spread (noise to signal ratio)
        out["relative_spread_ratio"] = (spread_rain / (fcst_rain + 5.0)).clip(0.0, 10.0).round(3)

        return out[self.feature_names]
