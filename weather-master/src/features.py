"""
Feature Engineering & Dataset Splitting
Smart India Hackathon - NCMRWF / Ministry of Earth Sciences

Processes raw forecast verification tabular data, constructs physically-meaningful
interaction features, handles categorical encodings, and produces time-ordered
splits (no lookahead leakage).
"""

import json
import os
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd


SYNOPTIC_REGIMES = [
    "quiescent_clear",
    "heat_wave",
    "active_monsoon",
    "break_monsoon",
    "western_disturbance",
    "monsoon_depression",
    "cyclonic_disturbance",
    "post_monsoon_transition",
]

TERRAIN_TYPES = [
    "Himalayan",
    "Northern_Plains",
    "Northeastern_Hills",
    "Coastal_Plains",
    "Central_Plateau",
    "Arid_Desert",
    "Western_Ghats",
    "Peninsular_Interior",
]

BASE_NUMERICAL_COLS = [
    "lead_day",
    "terrain_difficulty",
    "ensemble_spread",
    "pressure_gradient_hpa",
    "wind_shear_mps",
    "moisture_convergence",
    "enso_oni_index",
    "mjo_amplitude",
    "mjo_phase",
    "surface_temp_c",
    "cape_jkg",
    "prior_day_error",
]

ENGINEERED_COLS = [
    "spread_lead_interaction",
    "shear_moisture_interaction",
    "baroclinic_instability",
    "convective_vulnerability",
    "spread_to_lead_ratio",
    "dynamic_instability_index",
    "month_sin",
    "month_cos",
]


class FeatureEngineer:
    """
    Transforms raw forecast tabular inputs into model-ready features.
    Maintains deterministic feature names and handles encoding.
    """

    def __init__(self):
        self.regimes = SYNOPTIC_REGIMES
        self.terrains = TERRAIN_TYPES
        self.feature_names = self._build_feature_names()

    def _build_feature_names(self) -> List[str]:
        names = list(BASE_NUMERICAL_COLS) + list(ENGINEERED_COLS)
        for r in self.regimes:
            names.append(f"regime_{r}")
        for t in self.terrains:
            names.append(f"terrain_{t}")
        return names

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Creates physical interaction terms, cyclical seasonal variables,
        and one-hot encoded categories.
        """
        out = df.copy()

        # Date-derived seasonal cycle
        dates = pd.to_datetime(out["date"])
        months = dates.dt.month
        out["month_sin"] = np.sin(2 * np.pi * months / 12.0)
        out["month_cos"] = np.cos(2 * np.pi * months / 12.0)

        # 1. Spread-Lead interaction (compounding ensemble divergence at extended leads)
        out["spread_lead_interaction"] = out["ensemble_spread"] * out["lead_day"]

        # 2. Shear-Moisture interaction (baroclinic frontal dynamics)
        out["shear_moisture_interaction"] = out["wind_shear_mps"] * out["moisture_convergence"]

        # 3. Baroclinic instability proxy (pressure gradient combined with vertical shear)
        out["baroclinic_instability"] = out["pressure_gradient_hpa"] * out["wind_shear_mps"]

        # 4. Convective vulnerability (thermodynamic CAPE + moisture convergence)
        out["convective_vulnerability"] = (out["cape_jkg"] / 1000.0) * out["moisture_convergence"]

        # 5. Spread to lead ratio (normalized rate of ensemble dispersion)
        out["spread_to_lead_ratio"] = out["ensemble_spread"] / (out["lead_day"] + 0.5)

        # 6. Dynamic instability composite index
        out["dynamic_instability_index"] = (
            (out["pressure_gradient_hpa"] / 10.0)
            * (out["wind_shear_mps"] / 10.0)
            * (out["moisture_convergence"] / 5.0)
        )

        # One-hot encode synoptic regime
        for r in self.regimes:
            out[f"regime_{r}"] = (out["synoptic_regime"] == r).astype(float)

        # One-hot encode terrain
        for t in self.terrains:
            out[f"terrain_{t}"] = (out["terrain"] == t).astype(float)

        return out

    def get_feature_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        """Returns only the model input features with exact ordering."""
        engineered = self.engineer_features(df)
        return engineered[self.feature_names]

    def transform_single_record(self, raw_dict: Dict) -> pd.DataFrame:
        """Processes a single dictionary into a 1-row feature matrix."""
        df_single = pd.DataFrame([raw_dict])
        if "date" not in df_single.columns:
            df_single["date"] = pd.Timestamp.now().strftime("%Y-%m-%d")
        return self.get_feature_matrix(df_single)


def get_chronological_splits(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Performs chronological splitting based on unique dates to prevent
    temporal lookahead leakage.
    """
    unique_dates = sorted(df["date"].unique())
    n_dates = len(unique_dates)

    train_end_idx = int(n_dates * train_ratio)
    val_end_idx = int(n_dates * (train_ratio + val_ratio))

    train_dates = set(unique_dates[:train_end_idx])
    val_dates = set(unique_dates[train_end_idx:val_end_idx])
    test_dates = set(unique_dates[val_end_idx:])

    train_df = df[df["date"].isin(train_dates)].copy()
    val_df = df[df["date"].isin(val_dates)].copy()
    test_df = df[df["date"].isin(test_dates)].copy()

    print("Chronological split summary:")
    print(f"  Train: {len(train_dates)} dates ({len(train_df):,} rows), range {min(train_dates)} to {max(train_dates)}")
    print(f"  Val:   {len(val_dates)} dates ({len(val_df):,} rows), range {min(val_dates)} to {max(val_dates)}")
    print(f"  Test:  {len(test_dates)} dates ({len(test_df):,} rows), range {min(test_dates)} to {max(test_dates)}")

    return train_df, val_df, test_df


if __name__ == "__main__":
    data_path = "data/nwp_forecast_bust_dataset.csv"
    if os.path.exists(data_path):
        df_raw = pd.read_csv(data_path)
        fe = FeatureEngineer()
        X = fe.get_feature_matrix(df_raw)
        print(f"Engineered feature matrix shape: {X.shape}")
        print(f"Features: {X.columns.tolist()[:10]} ... ({len(X.columns)} total features)")
        train_df, val_df, test_df = get_chronological_splits(df_raw)
    else:
        print(f"Dataset not found at {data_path}. Run generate_synthetic_data.py first.")
