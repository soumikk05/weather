"""
Seasonal Context & Intra-Annual Timing Feature Family
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Family Name: 'seasonal_context'
Extracts:
- Multi-scale cyclic intra-annual coordinates (Day of Year & Month harmonics)
- Regional meteorological season flags (respecting Tamil Nadu NE monsoon)
- Seasonal transition vulnerability flags (May onset transition & October withdrawal)
- Distance in days from nominal Indian monsoon onset (June 1)
- Climatological seasonal bust rate baseline
"""

from typing import List
import numpy as np
import pandas as pd

from src.feature_families.base import BaseFeatureFamily
from src.target.bust_definition import get_season_for_date_and_subdivision


# Historical baseline bust frequencies by season across India
CLIMATOLOGICAL_SEASON_BUST_RATES = {
    "sw_monsoon": 0.125,
    "post_monsoon": 0.095,
    "pre_monsoon": 0.080,
    "winter": 0.065,
}


class SeasonalContextFamily(BaseFeatureFamily):
    """Features encoding cyclic calendar timing, monsoon transitions, and seasonal climatology."""

    @property
    def family_name(self) -> str:
        return "seasonal_context"

    @property
    def feature_names(self) -> List[str]:
        return [
            "doy_sin",
            "doy_cos",
            "month_sin",
            "month_cos",
            "is_monsoon_season",
            "is_transition_window",
            "days_from_june_1",
            "climatological_season_bust_rate",
        ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)

        # Parse date
        date_col = "initialization_time" if "initialization_time" in df.columns else ("date" if "date" in df.columns else None)
        if date_col:
            dt = pd.to_datetime(df[date_col])
        else:
            dt = pd.Series([pd.Timestamp.now()] * len(df), index=df.index)

        doy = dt.dt.dayofyear.values
        months = dt.dt.month.values
        locs = df.get("location_id", df.get("region", "Konkan & Goa")).astype(str).values

        # 1. Cyclic harmonics
        out["doy_sin"] = np.sin(2.0 * np.pi * doy / 365.25).round(4)
        out["doy_cos"] = np.cos(2.0 * np.pi * doy / 365.25).round(4)
        out["month_sin"] = np.sin(2.0 * np.pi * months / 12.0).round(4)
        out["month_cos"] = np.cos(2.0 * np.pi * months / 12.0).round(4)

        # 2. Regional monsoon flag
        is_monsoon = []
        is_transition = []
        clim_rates = []

        for m, loc in zip(months, locs):
            # Check regional season
            temp_dt = pd.Timestamp(year=2024, month=int(m), day=15)
            s_name = get_season_for_date_and_subdivision(temp_dt, loc)

            monsoon_flag = 1.0 if s_name in ["sw_monsoon", "ne_monsoon"] else 0.0
            # May (pre-monsoon onset) and October (withdrawal) are highest transition volatility
            trans_flag = 1.0 if m in [5, 10] else 0.0
            c_rate = CLIMATOLOGICAL_SEASON_BUST_RATES.get(s_name, 0.10)

            is_monsoon.append(monsoon_flag)
            is_transition.append(trans_flag)
            clim_rates.append(c_rate)

        out["is_monsoon_season"] = is_monsoon
        out["is_transition_window"] = is_transition
        out["climatological_season_bust_rate"] = clim_rates

        # 3. Days from June 1 (Day 152 in standard year)
        out["days_from_june_1"] = (doy - 152).astype(float)

        return out[self.feature_names]
