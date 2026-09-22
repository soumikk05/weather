"""
Run-to-Run Consistency & Flip-Flop Feature Family
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Family Name: 'run_consistency'
Extracts:
- Consecutive model run forecast changes for the SAME valid date:
  f_T(valid_date) - f_{T-1}(valid_date)
- Absolute run-to-run shift (mm)
- Relative shift ratio
- Severe flip-flop flag (> 25 mm change between consecutive cycles)
- Run-to-run MSLP forecast shift (hPa)
"""

from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from src.feature_families.base import BaseFeatureFamily


class RunConsistencyFamily(BaseFeatureFamily):
    """Features evaluating NWP cycle-to-cycle stability for the same target date."""

    @property
    def family_name(self) -> str:
        return "run_consistency"

    @property
    def feature_names(self) -> List[str]:
        return [
            "run_to_run_rainfall_delta_mm",
            "run_to_run_abs_delta_mm",
            "run_to_run_relative_shift",
            "run_flip_flop_flag",
            "run_to_run_mslp_delta_hpa",
        ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)

        has_init = "initialization_time" in df.columns
        has_valid = "valid_time" in df.columns
        has_loc = "location_id" in df.columns
        has_fcst = "fcst_rainfall_mm" in df.columns

        if has_init and has_valid and has_loc and has_fcst and len(df) > 1:
            df_work = df.copy()
            df_work["_init_d"] = pd.to_datetime(df_work["initialization_time"]).dt.normalize()
            df_work["_valid_d"] = pd.to_datetime(df_work["valid_time"]).dt.normalize()

            # Build a lookup table: (init_day, valid_day, location_id) -> (fcst_rain, fcst_mslp)
            lookup_cols = ["_init_d", "_valid_d", "location_id", "fcst_rainfall_mm"]
            if "fcst_mslp_hpa" in df_work.columns:
                lookup_cols.append("fcst_mslp_hpa")

            lookup = df_work[lookup_cols].copy()
            lookup = lookup.rename(columns={
                "fcst_rainfall_mm": "_prev_rain",
                **({"fcst_mslp_hpa": "_prev_mslp"} if "fcst_mslp_hpa" in lookup.columns else {})
            })

            # For each row in df_work, look for prev_init = _init_d - 1 day
            df_work["_prev_init_d"] = df_work["_init_d"] - pd.Timedelta(days=1)

            merged = df_work.merge(
                lookup,
                left_on=["_prev_init_d", "_valid_d", "location_id"],
                right_on=["_init_d", "_valid_d", "location_id"],
                how="left",
                suffixes=("", "_prev")
            )

            cur_rain = merged["fcst_rainfall_mm"].fillna(0.0)
            prev_rain = merged["_prev_rain"].fillna(np.nan)

            delta = (cur_rain - prev_rain).fillna(0.0)
            abs_d = delta.abs()
            denom = (cur_rain.clip(lower=0).combine(prev_rain.fillna(0), max) + 5.0)
            rel = (abs_d / denom).fillna(0.0).clip(0.0, 1.0)
            ff = (abs_d >= 25.0).astype(float).where(prev_rain.notna(), 0.0)

            if "_prev_mslp" in merged.columns:
                cur_mslp = merged["fcst_mslp_hpa"].fillna(1013.0)
                prev_mslp = merged["_prev_mslp"].fillna(np.nan)
                mslp_d = (cur_mslp - prev_mslp).fillna(0.0)
            else:
                mslp_d = pd.Series(0.0, index=merged.index)

            out["run_to_run_rainfall_delta_mm"] = delta.round(2).values
            out["run_to_run_abs_delta_mm"] = abs_d.round(2).values
            out["run_to_run_relative_shift"] = rel.round(3).values
            out["run_flip_flop_flag"] = ff.values
            out["run_to_run_mslp_delta_hpa"] = mslp_d.round(2).values
        else:
            n = len(df)
            out["run_to_run_rainfall_delta_mm"] = pd.Series([0.0] * n, index=df.index)
            out["run_to_run_abs_delta_mm"] = pd.Series([0.0] * n, index=df.index)
            out["run_to_run_relative_shift"] = pd.Series([0.0] * n, index=df.index)
            out["run_flip_flop_flag"] = pd.Series([0.0] * n, index=df.index)
            out["run_to_run_mslp_delta_hpa"] = pd.Series([0.0] * n, index=df.index)

        return out[self.feature_names]
