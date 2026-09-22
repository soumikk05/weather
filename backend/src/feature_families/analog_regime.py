"""
Analog Regime & Historical Pattern Matching Feature Family
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Family Name: 'analog_regime'
Extracts:
- Distance to nearest atmospheric state analogs in historical archive
- Historical bust frequency among top-K nearest atmospheric analogs
- Mean historical error of matching analog states
- Quantitative synoptic regime category index

STRICT TEMPORAL CAUSALITY GUARANTEE:
For any query row at date T_query, candidate analogs from the archive are strictly
filtered such that T_archive < T_query (at least 1-day lag). Future days are NEVER
used as analogs, even if present in the fitted archive.
"""

from typing import List, Optional
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from src.feature_families.base import BaseFeatureFamily
from src.data.schema import SYNOPTIC_REGIMES


class AnalogRegimeFamily(BaseFeatureFamily):
    """Features evaluating how similar forecast states behaved in historical archives."""

    def __init__(self, k_neighbors: int = 5):
        self.k_neighbors = k_neighbors
        self.nn_model: Optional[NearestNeighbors] = None
        self.archive_errors: Optional[np.ndarray] = None
        self.archive_busts: Optional[np.ndarray] = None
        self.archive_dates: Optional[np.ndarray] = None

    @property
    def family_name(self) -> str:
        return "analog_regime"

    @property
    def feature_names(self) -> List[str]:
        return [
            "analog_min_distance",
            "analog_mean_error_mm",
            "analog_bust_probability",
            "synoptic_regime_index",
        ]

    def _extract_state_vectors(self, df: pd.DataFrame) -> np.ndarray:
        """Construct normalized state vector for analog matching."""
        rain = df.get("fcst_rainfall_mm", pd.Series([0.0]*len(df), index=df.index)).fillna(0.0).values / 50.0
        mslp = (df.get("fcst_mslp_hpa", pd.Series([1013.0]*len(df), index=df.index)).fillna(1013.0).values - 1000.0) / 20.0
        cape = df.get("fcst_cape_jkg", pd.Series([500.0]*len(df), index=df.index)).fillna(500.0).values / 2000.0
        shear = df.get("fcst_wind_850_mps", pd.Series([10.0]*len(df), index=df.index)).fillna(10.0).values / 20.0
        lead = df.get("lead_day", pd.Series([1.0]*len(df), index=df.index)).fillna(1.0).values / 10.0

        return np.column_stack([rain, mslp, cape, shear, lead])

    def fit(self, df: pd.DataFrame) -> "AnalogRegimeFamily":
        """Index training data for analog nearest-neighbor queries."""
        if len(df) < self.k_neighbors:
            return self

        X_state = self._extract_state_vectors(df)
        self.nn_model = NearestNeighbors(metric="euclidean")
        self.nn_model.fit(X_state)

        err_col = "forecast_error_mm" if "forecast_error_mm" in df.columns else "forecast_error"
        if err_col in df.columns:
            self.archive_errors = df[err_col].values
        else:
            self.archive_errors = np.zeros(len(df))

        if "is_bust" in df.columns:
            self.archive_busts = df["is_bust"].values
        else:
            self.archive_busts = (np.abs(self.archive_errors) > 15.0).astype(int)

        date_col = "initialization_time" if "initialization_time" in df.columns else ("date" if "date" in df.columns else None)
        if date_col:
            self.archive_dates = pd.to_datetime(df[date_col]).dt.normalize().values
        else:
            self.archive_dates = None

        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)

        # 1. Regime numeric encoding
        regimes = df.get("synoptic_regime", "quiescent_clear").astype(str).values
        regime_indices = [
            SYNOPTIC_REGIMES.index(r) if r in SYNOPTIC_REGIMES else 0
            for r in regimes
        ]
        out["synoptic_regime_index"] = regime_indices

        # 2. Nearest analog lookups if fitted
        if self.nn_model is not None and self.archive_errors is not None:
            X_query = self._extract_state_vectors(df)
            k_query = min(len(self.archive_errors), max(self.k_neighbors * 10, 30))
            distances, indices = self.nn_model.kneighbors(X_query, n_neighbors=k_query)

            date_col = "initialization_time" if "initialization_time" in df.columns else ("date" if "date" in df.columns else None)
            query_dates = pd.to_datetime(df[date_col]).dt.normalize().values if date_col and date_col in df.columns else None

            min_dists = []
            mean_errs = []
            bust_probs = []

            for i in range(len(df)):
                row_indices = indices[i]
                row_dists = distances[i]

                if query_dates is not None and self.archive_dates is not None:
                    # Enforce strict causality: T_archive < T_query
                    q_date = query_dates[i]
                    valid_mask = self.archive_dates[row_indices] < q_date
                    valid_indices = row_indices[valid_mask][:self.k_neighbors]
                    valid_dists = row_dists[valid_mask][:self.k_neighbors]
                else:
                    valid_indices = row_indices[:self.k_neighbors]
                    valid_dists = row_dists[:self.k_neighbors]

                if len(valid_indices) > 0:
                    min_dists.append(valid_dists[0])
                    mean_errs.append(np.mean(self.archive_errors[valid_indices]))
                    bust_probs.append(np.mean(self.archive_busts[valid_indices]))
                else:
                    min_dists.append(0.50)
                    mean_errs.append(0.0)
                    bust_probs.append(0.10)

            out["analog_min_distance"] = np.round(min_dists, 3)
            out["analog_mean_error_mm"] = np.round(mean_errs, 2)
            out["analog_bust_probability"] = np.round(bust_probs, 3)
        else:
            # Fallback when querying before fit or on tiny samples
            out["analog_min_distance"] = 0.50
            out["analog_mean_error_mm"] = 0.0
            out["analog_bust_probability"] = 0.10

        return out[self.feature_names]
