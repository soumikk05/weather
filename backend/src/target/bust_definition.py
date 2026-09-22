"""
Bust Definition Engine & Threshold Formulations
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Implements rigorous target formulations for forecast bust detection:
1. Primary: Location × Season × Lead 90th percentile threshold,
   strictly fitted on training data with zero lookahead.
2. IMD Category Miss: Forecast misses observation by >= 2 IMD rainfall categories.
3. Magnitude-Relative: Absolute error exceeds large-event threshold and relative fraction.
4. Extreme Convective Bust: False alarm or missed heavy/extreme precipitation (> 115.5 mm).
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.data.schema import (
    SUBDIVISIONS,
    SUBDIVISION_MAP,
    IMD_RAINFALL_CATEGORIES,
    get_imd_category,
    imd_category_index,
    is_category_miss,
)


def get_season_for_date_and_subdivision(dt: pd.Timestamp, subdivision_name: str) -> str:
    """
    Map timestamp and subdivision to IMD meteorological season.
    Respects regional nuances (e.g. Tamil Nadu Northeast Monsoon primary season).
    """
    month = dt.month
    sub = SUBDIVISION_MAP.get(subdivision_name)
    if sub and sub.season_calendar:
        for s_name, (start_m, end_m) in sub.season_calendar.items():
            if start_m <= end_m:
                if start_m <= month <= end_m:
                    return s_name
            else:
                # Wrap around year-end (e.g. winter 12 to 2)
                if month >= start_m or month <= end_m:
                    return s_name

    # Standard all-India IMD seasonal calendar fallback
    if month in [6, 7, 8, 9]:
        return "sw_monsoon"
    elif month in [10, 11]:
        return "post_monsoon"
    elif month in [12, 1, 2]:
        return "winter"
    else:
        return "pre_monsoon"


class BustThresholdEngine:
    """
    Computes and applies forecast bust thresholds strictly on training blocks.
    
    Zero-Leakage Invariant:
    - `fit()` must ONLY be called on training split data.
    - `transform()` applies previously computed thresholds to validation/test sets.
    """

    def __init__(
        self,
        percentile: float = 90.0,
        min_threshold_mm: float = 5.0,
    ):
        self.percentile = percentile
        self.min_threshold_mm = min_threshold_mm
        self.thresholds_df_: Optional[pd.DataFrame] = None
        self.fallback_threshold_: float = min_threshold_mm

    def _derive_season_column(self, df: pd.DataFrame) -> pd.Series:
        """Derive season using initialization_time and location_id."""
        init_dt = pd.to_datetime(df["initialization_time"])
        locs = df["location_id"].values
        seasons = [
            get_season_for_date_and_subdivision(d, loc)
            for d, loc in zip(init_dt, locs)
        ]
        return pd.Series(seasons, index=df.index)

    def fit(self, train_df: pd.DataFrame) -> "BustThresholdEngine":
        """
        Fit bust thresholds on training data only.

        Parameters
        ----------
        train_df : pd.DataFrame
            Training dataframe containing 'initialization_time', 'location_id',
            'lead_day', and either 'abs_error_mm' or ('fcst_rainfall_mm', 'obs_rainfall_mm').
        """
        df = train_df.copy()
        if "abs_error_mm" not in df.columns:
            if "fcst_rainfall_mm" in df.columns and "obs_rainfall_mm" in df.columns:
                df["forecast_error_mm"] = df["fcst_rainfall_mm"] - df["obs_rainfall_mm"]
                df["abs_error_mm"] = df["forecast_error_mm"].abs()
            else:
                raise ValueError("train_df must contain 'abs_error_mm' or forecast and obs rainfall columns.")

        df["_season"] = self._derive_season_column(df)

        thresholds = (
            df.groupby(["location_id", "_season", "lead_day"])["abs_error_mm"]
            .quantile(self.percentile / 100.0)
            .reset_index()
            .rename(columns={"abs_error_mm": "bust_threshold_mm", "_season": "season"})
        )

        # Enforce minimum threshold to prevent noise flagging
        thresholds["bust_threshold_mm"] = thresholds["bust_threshold_mm"].clip(
            lower=self.min_threshold_mm
        )

        self.thresholds_df_ = thresholds
        self.fallback_threshold_ = float(
            thresholds["bust_threshold_mm"].median()
            if len(thresholds) > 0
            else self.min_threshold_mm
        )
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply fitted bust thresholds to any dataset (train, val, or test).
        Computes `is_bust`, `bust_threshold_mm`, and `bust_severity_ratio`.
        """
        if self.thresholds_df_ is None:
            raise RuntimeError("BustThresholdEngine must be fit() before calling transform().")

        out = df.copy()
        if "forecast_error_mm" not in out.columns and "fcst_rainfall_mm" in out.columns and "obs_rainfall_mm" in out.columns:
            out["forecast_error_mm"] = out["fcst_rainfall_mm"] - out["obs_rainfall_mm"]
        if "abs_error_mm" not in out.columns and "forecast_error_mm" in out.columns:
            out["abs_error_mm"] = out["forecast_error_mm"].abs()

        out["_season"] = self._derive_season_column(out)

        merged = out.merge(
            self.thresholds_df_,
            left_on=["location_id", "_season", "lead_day"],
            right_on=["location_id", "season", "lead_day"],
            how="left",
        )

        # Fill any unseen location-season-lead combinations with the fallback threshold
        merged["bust_threshold_mm"] = merged["bust_threshold_mm"].fillna(self.fallback_threshold_)
        merged["is_bust"] = (merged["abs_error_mm"] > merged["bust_threshold_mm"]).astype(int)
        merged["bust_severity_ratio"] = (merged["abs_error_mm"] / merged["bust_threshold_mm"]).round(3)

        # Drop temporary columns
        merged.drop(columns=["_season", "season"], errors="ignore", inplace=True)
        return merged

    def fit_transform(self, train_df: pd.DataFrame) -> pd.DataFrame:
        """Fit on train_df and transform train_df in one step."""
        return self.fit(train_df).transform(train_df)


# ---------------------------------------------------------------------------
# Alternative Bust Formulations
# ---------------------------------------------------------------------------

def compute_imd_category_miss(
    fcst_rainfall_mm: float,
    obs_rainfall_mm: float,
    min_miss_categories: int = 2,
) -> int:
    """Returns 1 if forecast and observation differ by >= min_miss_categories."""
    return 1 if is_category_miss(fcst_rainfall_mm, obs_rainfall_mm, n_categories=min_miss_categories) else 0


def add_alternative_bust_targets(
    df: pd.DataFrame,
    extreme_thresh_mm: float = 115.5,
) -> pd.DataFrame:
    """
    Enrich DataFrame with alternative meteorological bust labels:
    - is_category_miss: IMD category miss >= 2 categories
    - is_magnitude_bust: error > max(25mm, 100% of forecast)
    - is_extreme_miss: observed >= 115.5 mm (Very Heavy/Extremely Heavy) but forecast < 35.5 mm
    - is_extreme_false_alarm: forecast >= 115.5 mm but observed < 15.6 mm
    """
    out = df.copy()
    fcst = out["fcst_rainfall_mm"].to_numpy()
    obs = out["obs_rainfall_mm"].to_numpy()
    err = np.abs(fcst - obs)

    # 1. IMD Category Miss
    cat_misses = [
        compute_imd_category_miss(f, o, min_miss_categories=2)
        for f, o in zip(fcst, obs)
    ]
    out["is_category_miss"] = cat_misses

    # 2. Magnitude-Relative Bust (Significant hydrological error)
    rel_scale = np.maximum(fcst, obs)
    out["is_magnitude_bust"] = ((err > 25.0) & (err > 0.8 * rel_scale)).astype(int)

    # 3. High-Impact Convective / Extreme Miss & False Alarm
    out["is_extreme_miss"] = ((obs >= extreme_thresh_mm) & (fcst < 35.5)).astype(int)
    out["is_extreme_false_alarm"] = ((fcst >= extreme_thresh_mm) & (obs < 15.6)).astype(int)

    return out
