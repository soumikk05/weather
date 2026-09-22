"""
Recent Error & NWP Memory Feature Family
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Family Name: 'recent_error'
Extracts:
- Rolling 30-day verified NWP bias (mean signed error)
- Rolling 30-day verified NWP MAE
- Rolling 30-day verified bust frequency
- Rolling 7-day short-term MAE
- Prior verified 1-day error

STRICT TEMPORAL CAUSALITY INVARIANT:
For a forecast initialized on date T_init, only verified observations from
dates <= T_init - 1 are included in rolling aggregates.
Target valid-time errors are strictly inaccessible.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.feature_families.base import BaseFeatureFamily


class RecentErrorFamily(BaseFeatureFamily):
    """Features tracking historical systematic NWP bias and rolling verification errors."""

    def __init__(self, default_lag_days: int = 1):
        self.default_lag_days = default_lag_days

    @property
    def family_name(self) -> str:
        return "recent_error"

    @property
    def feature_names(self) -> List[str]:
        return [
            "recent_error_bias_30d",
            "recent_error_mae_30d",
            "recent_error_bust_freq_30d",
            "recent_error_mae_7d",
            "prior_day_verified_error",
        ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)

        # Check if pre-computed rolling columns or prior_day_error exist
        if "prior_day_error" in df.columns:
            prior_err = df["prior_day_error"].fillna(0.0)
        else:
            prior_err = pd.Series(0.0, index=df.index)

        # If full time-series is present with verified errors, calculate causal rolling metrics
        date_col = "initialization_time" if "initialization_time" in df.columns else ("date" if "date" in df.columns else None)
        loc_col = "location_id" if "location_id" in df.columns else ("region" if "region" in df.columns else None)
        has_error = "forecast_error_mm" in df.columns or "forecast_error" in df.columns

        if date_col and loc_col and has_error and len(df) > 30:
            err_col = "forecast_error_mm" if "forecast_error_mm" in df.columns else "forecast_error"
            # Extract Day-1 verification errors as representative NWP systemic bias proxy
            lead_col = "lead_day" if "lead_day" in df.columns else None
            hist_df = df.copy()
            if lead_col:
                hist_df = hist_df[hist_df[lead_col] == 1]

            hist_df["_dt"] = pd.to_datetime(hist_df[date_col]).dt.normalize()
            hist_df["_abs_err"] = hist_df[err_col].abs()
            hist_df["_is_bust"] = hist_df.get("is_bust", (hist_df["_abs_err"] > 15.0).astype(int))

            # Group by location and date
            daily = (
                hist_df.groupby([loc_col, "_dt"])
                .agg({err_col: "mean", "_abs_err": "mean", "_is_bust": "mean"})
                .reset_index()
                .sort_values(["_dt"])
            )

            # Pre-compute rolling statistics per location with a 1-day lag to enforce causality
            daily["lag_err"] = daily.groupby(loc_col)[err_col].shift(self.default_lag_days)
            daily["lag_abs"] = daily.groupby(loc_col)["_abs_err"].shift(self.default_lag_days)
            daily["lag_bust"] = daily.groupby(loc_col)["_is_bust"].shift(self.default_lag_days)

            # Rolling 30-day and 7-day
            daily["bias_30d"] = daily.groupby(loc_col)["lag_err"].transform(
                lambda s: s.rolling(30, min_periods=3).mean()
            )
            daily["mae_30d"] = daily.groupby(loc_col)["lag_abs"].transform(
                lambda s: s.rolling(30, min_periods=3).mean()
            )
            daily["bust_freq_30d"] = daily.groupby(loc_col)["lag_bust"].transform(
                lambda s: s.rolling(30, min_periods=3).mean()
            )
            daily["mae_7d"] = daily.groupby(loc_col)["lag_abs"].transform(
                lambda s: s.rolling(7, min_periods=2).mean()
            )

            # Merge back onto df
            df_temp = df.copy()
            df_temp["_dt"] = pd.to_datetime(df_temp[date_col]).dt.normalize()
            merged = df_temp.merge(
                daily[[loc_col, "_dt", "bias_30d", "mae_30d", "bust_freq_30d", "mae_7d", "lag_err"]],
                on=[loc_col, "_dt"],
                how="left",
            )

            out["recent_error_bias_30d"] = merged["bias_30d"].fillna(0.0).round(2).values
            out["recent_error_mae_30d"] = merged["mae_30d"].fillna(5.0).round(2).values
            out["recent_error_bust_freq_30d"] = merged["bust_freq_30d"].fillna(0.10).round(3).values
            out["recent_error_mae_7d"] = merged["mae_7d"].fillna(5.0).round(2).values
            out["prior_day_verified_error"] = merged["lag_err"].fillna(prior_err).round(2).values
        else:
            # Fallback when single record or historical archive not fully provided
            out["recent_error_bias_30d"] = (prior_err * 0.5).round(2)
            out["recent_error_mae_30d"] = prior_err.abs().clip(lower=4.0).round(2)
            out["recent_error_bust_freq_30d"] = pd.Series([0.10] * len(df), index=df.index)
            out["recent_error_mae_7d"] = prior_err.abs().clip(lower=3.0).round(2)
            out["prior_day_verified_error"] = prior_err.round(2)

        return out[self.feature_names]
