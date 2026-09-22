"""
Non-Circular Synthetic Data Generator (Smoke-Test Fixture)
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

┌──────────────────────────────────────────────────────────────────┐
│  ⚠️  WARNING: SYNTHETIC SMOKE-TEST DATA                        │
│  This generator produces SYNTHETIC data for pipeline testing    │
│  ONLY. Results must NOT be presented as evidence of real-world  │
│  forecasting skill. Every output is labelled data_source=       │
│  "synthetic".                                                   │
└──────────────────────────────────────────────────────────────────┘

Architecture (non-circular by design):
--------------------------------------
1. HIDDEN LATENT STATE: For each (date, location, lead_day), we sample
   hidden variables that are NEVER exposed as features:
   - `latent_predictability` ∈ [0, 1]: how inherently predictable the
     atmosphere is on this day at this location
   - `latent_disturbance_intensity` ∈ [0, 1]: severity of weather system

2. TRUTH (target): The forecast error is driven by these hidden latents
   plus irreducible stochastic noise.

3. FEATURES (inputs): Observable features (ensemble spread, pressure
   gradients, etc.) are NOISY, PARTIAL proxies of the hidden state.
   The noise is large enough that the relationship is NOT trivially
   invertible. A perfect model on these features should achieve
   realistic skill (PR-AUC ~0.3-0.7), not 0.999.

4. BUST LABEL: is_bust = error exceeds location × season × lead 90th
   percentile, computed on training data only.
"""

import os
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.data.loaders import BaseDataLoader
from src.data.schema import (
    SUBDIVISIONS,
    SubdivisionInfo,
    SYNOPTIC_REGIMES,
    DATA_SOURCE_SYNTHETIC,
)


# ---------------------------------------------------------------------------
# Regime assignment (same meteorological logic as before, but regimes
# influence the hidden latent state rather than being directly informative)
# ---------------------------------------------------------------------------
def _assign_regime(month: int, day_noise: float, lat: float, terrain: str) -> str:
    """Assign synoptic regime based on season, region, and stochastic noise."""
    # Winter / Pre-monsoon Western Disturbances in North
    if month in [12, 1, 2, 3] and lat > 27.0:
        if day_noise > 0.75:
            return "western_disturbance"

    # Pre-monsoon Heat Waves (April-May) in Central & Plains
    if month in [4, 5] and terrain in ["Northern_Plains", "Central_Plateau", "Arid_Desert"]:
        if day_noise > 0.72:
            return "heat_wave"

    # Monsoon Season (June-September)
    if month in [6, 7, 8, 9]:
        if day_noise > 0.90:
            return "cyclonic_disturbance"
        elif day_noise > 0.78:
            return "monsoon_depression"
        elif day_noise > 0.50:
            return "active_monsoon"
        elif day_noise > 0.35:
            return "break_monsoon"

    # Post-monsoon cyclone season (October-November)
    if month in [10, 11]:
        if terrain == "Coastal_Plains" and day_noise > 0.80:
            return "cyclonic_disturbance"
        elif day_noise > 0.65:
            return "post_monsoon_transition"

    return "quiescent_clear"


class SyntheticDataGenerator(BaseDataLoader):
    """
    Generates non-circular synthetic forecast verification data.

    The key invariant is: forecast_error is driven by HIDDEN latent
    variables, while model features are noisy proxies of those latents.
    The model cannot perfectly recover the error from the features.
    """

    SYNTHETIC_BANNER = (
        "[WARNING] SYNTHETIC SMOKE-TEST DATA - not real forecast verification. "
        "Do not cite these metrics as evidence of operational skill."
    )

    def __init__(self, random_seed: int = 42):
        self.seed = random_seed

    def get_data_source(self) -> str:
        return DATA_SOURCE_SYNTHETIC

    def load(
        self,
        start_date: str = "2019-01-01",
        end_date: str = "2024-12-31",
        locations: Optional[list] = None,
        compute_bust: bool = True,
    ) -> pd.DataFrame:
        """
        Generate non-circular synthetic forecast verification records.

        Parameters
        ----------
        start_date, end_date : str
            Date range for synthetic initialization times.
        locations : list, optional
            Subset of subdivision names. None = all 32.
        compute_bust : bool
            If True, compute 90th percentile bust thresholds and assign is_bust labels.

        Returns
        -------
        pd.DataFrame
            Columns follow schema.py canonical names.
        """
        rng = np.random.RandomState(self.seed)
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")

        # Sample every 2nd day to keep dataset manageable
        sampled_dates = date_range[::2]

        subs = SUBDIVISIONS
        if locations:
            subs = [s for s in SUBDIVISIONS if s.name in locations]

        # Pre-generate slow-varying climate indices
        n_days = len(sampled_dates)
        enso_cycle = 1.1 * np.sin(np.linspace(0, 3 * np.pi, n_days)) + rng.normal(0, 0.15, n_days)
        mjo_amp = 1.2 + 0.7 * np.cos(np.linspace(0, 12 * np.pi, n_days)) + rng.normal(0, 0.2, n_days)
        mjo_amp = np.clip(mjo_amp, 0.3, 2.9)
        mjo_phases = ((np.linspace(1, 24 * 8, n_days).astype(int) % 8) + 1)
        iod_cycle = 0.6 * np.sin(np.linspace(0, 2.5 * np.pi, n_days)) + rng.normal(0, 0.1, n_days)

        records = []

        for day_idx, date in enumerate(sampled_dates):
            month = date.month
            day_of_year = date.day_of_year

            d_enso = float(enso_cycle[day_idx])
            d_mjo_amp = float(mjo_amp[day_idx])
            d_mjo_phase = int(mjo_phases[day_idx])
            d_iod = float(iod_cycle[day_idx])

            # Daily synoptic noise (shared across regions, with per-region perturbation)
            synoptic_base = rng.uniform(0, 1)

            for sub in subs:
                reg_noise = (synoptic_base + rng.uniform(-0.15, 0.15)) % 1.0
                regime = _assign_regime(month, reg_noise, sub.lat, sub.terrain_type)

                for lead_day in range(1, 11):
                    rec = self._generate_one_record(
                        rng, date, lead_day, sub, regime,
                        d_enso, d_mjo_amp, d_mjo_phase, d_iod,
                        month, day_of_year,
                    )
                    records.append(rec)

        df = pd.DataFrame(records)

        # Validate schema
        self.validate_schema(df)

        print(self.SYNTHETIC_BANNER)
        print(f"Generated {len(df):,} synthetic records "
              f"({len(subs)} locations × {len(sampled_dates)} dates × 10 leads)")

        if compute_bust and len(df) > 0:
            thresholds = compute_bust_thresholds(df)
            df = apply_bust_labels(df, thresholds)
            bust_rate = df["is_bust"].mean()
            print(f"Overall bust rate: {bust_rate*100:.1f}%")
        else:
            print(f"Overall bust rate (pre-threshold): n/a (thresholds computed in Stage 2)")

        return df

    def _generate_one_record(
        self,
        rng: np.random.RandomState,
        date: pd.Timestamp,
        lead_day: int,
        sub: SubdivisionInfo,
        regime: str,
        enso: float,
        mjo_amp: float,
        mjo_phase: int,
        iod: float,
        month: int,
        day_of_year: int,
    ) -> Dict:
        """
        Generate a single forecast verification record.

        The architecture ensures non-circularity:
        1. Sample hidden latent_predictability and latent_disturbance
        2. Generate TRUTH (forecast error) from hidden state
        3. Generate FEATURES as noisy proxies of hidden state
        """
        # ==================================================================
        # STEP 1: HIDDEN LATENT STATE (never exposed as features)
        # ==================================================================

        # Regime influence on hidden predictability (not directly informative)
        regime_predictability = {
            "quiescent_clear": 0.85,
            "heat_wave": 0.60,
            "active_monsoon": 0.40,
            "break_monsoon": 0.55,
            "western_disturbance": 0.35,
            "monsoon_depression": 0.25,
            "cyclonic_disturbance": 0.15,
            "post_monsoon_transition": 0.50,
        }

        # Base predictability from regime + lead decay + terrain
        base_pred = regime_predictability.get(regime, 0.5)
        # Lead-time decay: predictability drops with lead
        lead_decay = 0.06 * (lead_day - 1)
        # Terrain penalty: complex terrain reduces predictability
        terrain_penalty = 0.12 * sub.terrain_complexity

        # Hidden predictability: the TRUE atmospheric predictability on this day
        # Includes large stochastic variation that features cannot fully capture
        latent_predictability = np.clip(
            base_pred - lead_decay - terrain_penalty + rng.normal(0, 0.18),
            0.02, 0.98
        )

        # Hidden disturbance intensity
        base_intensity = 1.0 - regime_predictability.get(regime, 0.5)
        latent_disturbance = np.clip(
            base_intensity + rng.normal(0, 0.20),
            0.02, 0.98
        )

        # ==================================================================
        # STEP 2: TRUTH (forecast error & observed rainfall)
        # ==================================================================

        # Climatological rainfall for this location and season
        clim_rainfall = self._climatological_rainfall(month, sub)

        # Observed rainfall (truth)
        obs_rainfall = max(0.0, clim_rainfall * (1.0 + rng.normal(0, 0.6)) +
                          rng.exponential(3.0) * latent_disturbance)
        if regime in ["active_monsoon", "monsoon_depression", "cyclonic_disturbance"]:
            obs_rainfall += rng.exponential(15.0) * latent_disturbance

        # NWP forecast of rainfall (what the model predicted)
        # The forecast has errors driven by the HIDDEN latent state
        forecast_noise_scale = (1.0 - latent_predictability) * (10.0 + 3.0 * lead_day)
        forecast_bias = rng.normal(0, forecast_noise_scale * 0.5)
        forecast_scatter = rng.normal(0, forecast_noise_scale)
        fcst_rainfall = max(0.0, obs_rainfall + forecast_bias + forecast_scatter)

        # Actual forecast error (the target we're trying to predict)
        forecast_error = fcst_rainfall - obs_rainfall

        # ==================================================================
        # STEP 3: FEATURES (noisy proxies of hidden state)
        # ==================================================================
        # Each feature is influenced by the hidden state but with SUBSTANTIAL
        # independent noise, so the features do not fully determine the error.

        # --- Ensemble spread: correlated with low predictability but noisy ---
        base_spread = 2.0 * (lead_day ** 0.7)
        spread_signal = (1.0 - latent_predictability) * 8.0
        ens_spread_rainfall = max(
            0.5,
            base_spread + spread_signal + rng.normal(0, 3.5)
        )

        # --- Pressure gradient: correlated with disturbance but noisy ---
        base_pg = 2.0 + 1.5 * (sub.lat / 30.0)
        pg_signal = latent_disturbance * 10.0
        pressure_gradient = max(
            0.5,
            base_pg + pg_signal + rng.normal(0, 3.0)
        )

        # --- Wind shear: partially informative ---
        base_shear = 8.0 + 5.0 * np.sin(month * np.pi / 6.0)
        shear_signal = latent_disturbance * 8.0
        wind_shear = max(
            2.0,
            base_shear + shear_signal + rng.normal(0, 4.0)
        )

        # --- Moisture convergence: partially informative ---
        base_moist = 2.0
        if month in [6, 7, 8, 9]:
            base_moist = 5.0
        moist_signal = latent_disturbance * 6.0
        moisture_conv = max(
            0.1,
            base_moist + moist_signal + rng.normal(0, 3.0)
        )

        # --- CAPE: noisy indicator ---
        base_cape = 500.0 + 700.0 * np.sin(month * np.pi / 6.0)
        cape_signal = latent_disturbance * 1200.0
        cape = max(
            50.0,
            base_cape + cape_signal + rng.normal(0, 500.0)
        )

        # --- Forecast MSLP: partially correlated ---
        base_mslp = 1013.0 - 2.0 * latent_disturbance * 5.0
        fcst_mslp = base_mslp + rng.normal(0, 2.5)

        # --- Temperature: weakly informative ---
        seasonal_temp = 27.0 + 8.0 * np.sin((month - 4) * np.pi / 6.0) - (sub.lat - 15.0) * 0.45
        fcst_temp = seasonal_temp + rng.normal(0, 2.5)
        if regime == "heat_wave":
            fcst_temp += rng.uniform(3.0, 7.0)

        # --- Ensemble agreement features ---
        ens_spread_temp = max(0.1, 1.0 + (1.0 - latent_predictability) * 2.0 + rng.normal(0, 0.8))
        ens_spread_mslp = max(0.1, 0.5 + (1.0 - latent_predictability) * 1.5 + rng.normal(0, 0.5))

        ens_total = 50
        # Members predicting >10mm: more in disturbed situations
        ens_rain_gt10 = int(np.clip(
            ens_total * (0.1 + 0.6 * latent_disturbance + rng.normal(0, 0.15)),
            0, ens_total
        ))
        ens_rain_gt50 = int(np.clip(
            ens_total * (0.02 + 0.3 * latent_disturbance + rng.normal(0, 0.10)),
            0, ens_rain_gt10
        ))

        # --- ERA5-like atmospheric state features (noisy proxies) ---
        era5_vorticity = rng.normal(0, 1e-5) + latent_disturbance * 5e-5
        era5_rh = np.clip(50.0 + 30.0 * latent_disturbance + rng.normal(0, 12.0), 10, 100)
        era5_sst = 27.0 + 2.0 * np.sin((month - 3) * np.pi / 6.0) + rng.normal(0, 0.8)
        if sub.terrain_type in ["Arid_Desert", "Central_Plateau", "Northern_Plains"]:
            era5_sst = np.nan  # No nearby ocean

        # Valid time
        valid_time = date + pd.Timedelta(days=lead_day)

        return {
            # Identifiers
            "initialization_time": date.strftime("%Y-%m-%d"),
            "valid_time": valid_time.strftime("%Y-%m-%d"),
            "lead_day": lead_day,
            "location_id": sub.name,
            "lat": sub.lat,
            "lon": sub.lon,
            "model_version": "synthetic_v2",
            "data_source": DATA_SOURCE_SYNTHETIC,

            # NWP forecast fields
            "fcst_rainfall_mm": round(float(fcst_rainfall), 2),
            "fcst_temp_2m_c": round(float(fcst_temp), 1),
            "fcst_mslp_hpa": round(float(fcst_mslp), 1),
            "fcst_wind_850_mps": round(float(max(1, 5 + latent_disturbance * 12 + rng.normal(0, 4))), 1),
            "fcst_wind_200_mps": round(float(max(2, 15 + rng.normal(0, 6))), 1),
            "fcst_rh_700_pct": round(float(era5_rh + rng.normal(0, 5)), 1),
            "fcst_geopot_500_m": round(float(5600 - 50 * latent_disturbance + rng.normal(0, 20)), 0),
            "fcst_cape_jkg": round(float(cape), 0),
            "fcst_moisture_flux_conv": round(float(moisture_conv), 2),

            # Ensemble
            "ens_spread_rainfall": round(float(ens_spread_rainfall), 2),
            "ens_spread_temp": round(float(ens_spread_temp), 2),
            "ens_spread_mslp": round(float(ens_spread_mslp), 2),
            "ens_members_total": ens_total,
            "ens_members_rain_gt10": ens_rain_gt10,
            "ens_members_rain_gt50": ens_rain_gt50,

            # Observation truth
            "obs_rainfall_mm": round(float(obs_rainfall), 2),
            "obs_temp_2m_c": round(float(seasonal_temp + rng.normal(0, 1.5)), 1),

            # Atmospheric state (ERA5-like)
            "era5_mslp_hpa": round(float(fcst_mslp + rng.normal(0, 1.0)), 1),
            "era5_wind_shear_mps": round(float(wind_shear), 1),
            "era5_moisture_conv": round(float(moisture_conv + rng.normal(0, 1.0)), 2),
            "era5_vorticity_850": float(f"{era5_vorticity:.6f}"),
            "era5_cape_jkg": round(float(cape + rng.normal(0, 200)), 0),
            "era5_sst_c": round(float(era5_sst), 1) if not np.isnan(era5_sst) else np.nan,
            "era5_rh_700_pct": round(float(era5_rh), 1),

            # Climate indices
            "enso_oni": round(float(enso), 2),
            "mjo_rmm1": round(float(mjo_amp * np.cos(mjo_phase * np.pi / 4)), 2),
            "mjo_rmm2": round(float(mjo_amp * np.sin(mjo_phase * np.pi / 4)), 2),
            "mjo_amplitude": round(float(mjo_amp), 2),
            "mjo_phase": mjo_phase,
            "iod_dmi": round(float(iod), 2),

            # Cyclone proximity (simple simulation)
            "cyclone_present": 1 if regime in ["cyclonic_disturbance", "monsoon_depression"] else 0,
            "cyclone_dist_km": (
                round(float(rng.uniform(50, 800)), 0)
                if regime in ["cyclonic_disturbance", "monsoon_depression"]
                else np.nan
            ),
            "cyclone_intensity_kt": (
                round(float(rng.uniform(25, 130)), 0)
                if regime == "cyclonic_disturbance"
                else (round(float(rng.uniform(15, 35)), 0) if regime == "monsoon_depression" else np.nan)
            ),
            "cyclone_category": (
                "CS" if regime == "cyclonic_disturbance"
                else ("DD" if regime == "monsoon_depression" else "none")
            ),

            # Static geography
            "elevation_m": round(float(self._approx_elevation(sub)), 0),
            "dist_coast_km": round(float(self._approx_coast_dist(sub)), 0),
            "land_fraction": 1.0,
            "terrain_type": sub.terrain_type,
            "terrain_complexity": sub.terrain_complexity,

            # Regime (metadata, not a direct model feature in the new design)
            "synoptic_regime": regime,

            # Raw forecast error (for downstream target computation)
            "forecast_error_mm": round(float(forecast_error), 2),
            "abs_error_mm": round(float(abs(forecast_error)), 2),
        }

    def _climatological_rainfall(self, month: int, sub: SubdivisionInfo) -> float:
        """Return approximate climatological daily rainfall (mm) for location and month."""
        # Simple seasonal model based on terrain and month
        base = 2.0  # dry default
        if month in [6, 7, 8, 9]:  # SW monsoon
            if sub.terrain_type in ["Western_Ghats", "Northeastern_Hills"]:
                base = 25.0
            elif sub.terrain_type in ["Coastal_Plains", "Northern_Plains"]:
                base = 12.0
            elif sub.terrain_type == "Central_Plateau":
                base = 8.0
            elif sub.terrain_type == "Himalayan":
                base = 10.0
            elif sub.terrain_type == "Arid_Desert":
                base = 3.0
            else:
                base = 6.0
        elif month in [10, 11, 12]:  # Post-monsoon / NE monsoon
            if "Tamil Nadu" in sub.name or "Coastal Andhra" in sub.name:
                base = 10.0
            elif sub.terrain_type == "Coastal_Plains":
                base = 5.0
            else:
                base = 2.0
        elif month in [3, 4, 5]:  # Pre-monsoon
            if sub.terrain_type == "Northeastern_Hills":
                base = 8.0
            else:
                base = 3.0
        return base

    def _approx_elevation(self, sub: SubdivisionInfo) -> float:
        """Approximate mean elevation for subdivision."""
        elev_map = {
            "Himalayan": 2500, "Northeastern_Hills": 800, "Western_Ghats": 600,
            "Northern_Plains": 200, "Central_Plateau": 450, "Coastal_Plains": 50,
            "Arid_Desert": 300, "Peninsular_Interior": 500,
        }
        return elev_map.get(sub.terrain_type, 300)

    def _approx_coast_dist(self, sub: SubdivisionInfo) -> float:
        """Approximate distance to coast for subdivision."""
        coast_map = {
            "Coastal_Plains": 30, "Western_Ghats": 50, "Peninsular_Interior": 200,
            "Northern_Plains": 800, "Himalayan": 1200, "Northeastern_Hills": 400,
            "Central_Plateau": 500, "Arid_Desert": 600,
        }
        return coast_map.get(sub.terrain_type, 400)


# Forward/backward alias for NonCircularSyntheticGenerator
NonCircularSyntheticGenerator = SyntheticDataGenerator


def compute_bust_thresholds(
    df: pd.DataFrame,
    percentile: float = 90.0,
) -> pd.DataFrame:
    """
    Compute location × season × lead bust thresholds from TRAINING data.

    Parameters
    ----------
    df : pd.DataFrame
        Training-only data with 'abs_error_mm', 'location_id', 'lead_day',
        and 'initialization_time' (or 'valid_time').
    percentile : float
        Percentile of abs_error to use as bust threshold (default 90th).

    Returns
    -------
    pd.DataFrame
        Columns: location_id, season, lead_day, bust_threshold_mm
    """
    df = df.copy()

    # Derive season from initialization_time
    init_dt = pd.to_datetime(df["initialization_time"])
    df["_month"] = init_dt.dt.month

    def _month_to_season(m):
        if m in [6, 7, 8, 9]:
            return "sw_monsoon"
        elif m in [10, 11]:
            return "post_monsoon"
        elif m in [12, 1, 2]:
            return "winter"
        else:
            return "pre_monsoon"

    df["_season"] = df["_month"].apply(_month_to_season)

    thresholds = (
        df.groupby(["location_id", "_season", "lead_day"])["abs_error_mm"]
        .quantile(percentile / 100.0)
        .reset_index()
        .rename(columns={"abs_error_mm": "bust_threshold_mm", "_season": "season"})
    )

    # Ensure minimum threshold to avoid labelling trivial errors as busts
    thresholds["bust_threshold_mm"] = thresholds["bust_threshold_mm"].clip(lower=5.0)

    return thresholds


def apply_bust_labels(
    df: pd.DataFrame,
    thresholds: pd.DataFrame,
) -> pd.DataFrame:
    """
    Apply bust labels to data using pre-computed thresholds.

    Parameters
    ----------
    df : pd.DataFrame
        Data with 'abs_error_mm', 'location_id', 'lead_day', 'initialization_time'.
    thresholds : pd.DataFrame
        Output of compute_bust_thresholds().

    Returns
    -------
    pd.DataFrame
        Input with added 'is_bust', 'bust_threshold_mm' columns.
    """
    df = df.copy()
    init_dt = pd.to_datetime(df["initialization_time"])
    df["_month"] = init_dt.dt.month

    def _month_to_season(m):
        if m in [6, 7, 8, 9]:
            return "sw_monsoon"
        elif m in [10, 11]:
            return "post_monsoon"
        elif m in [12, 1, 2]:
            return "winter"
        else:
            return "pre_monsoon"

    df["_season"] = df["_month"].apply(_month_to_season)

    merged = df.merge(
        thresholds,
        left_on=["location_id", "_season", "lead_day"],
        right_on=["location_id", "season", "lead_day"],
        how="left",
    )

    # Fallback threshold for missing combinations
    fallback_threshold = thresholds["bust_threshold_mm"].median()
    merged["bust_threshold_mm"] = merged["bust_threshold_mm"].fillna(fallback_threshold)

    merged["is_bust"] = (merged["abs_error_mm"] > merged["bust_threshold_mm"]).astype(int)

    # Clean up temp columns
    merged.drop(columns=["_month", "_season", "season"], errors="ignore", inplace=True)

    return merged


# Alias for backward/forward naming
assign_bust_labels = apply_bust_labels


def generate_and_save_synthetic(
    output_path: str = "data/synthetic_smoke_test.csv",
    start_date: str = "2019-01-01",
    end_date: str = "2024-12-31",
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic data, compute bust labels, and save to disk."""
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    print("=" * 70)
    print("  ⚠️  SYNTHETIC SMOKE-TEST DATA GENERATOR")
    print("  Results are for pipeline testing ONLY.")
    print("=" * 70)

    generator = SyntheticDataGenerator(random_seed=seed)
    df = generator.load(start_date=start_date, end_date=end_date)

    # Chronological split for threshold computation
    unique_dates = sorted(df["initialization_time"].unique())
    train_cutoff = unique_dates[int(len(unique_dates) * 0.70)]

    train_mask = df["initialization_time"] <= train_cutoff
    train_df = df[train_mask]

    print(f"\nComputing bust thresholds on training data ({train_mask.sum():,} rows)...")
    thresholds = compute_bust_thresholds(train_df, percentile=90.0)

    # Apply to full dataset (thresholds from training only — no leakage)
    df = apply_bust_labels(df, thresholds)

    bust_rate = df["is_bust"].mean()
    print(f"\nOverall bust rate: {bust_rate*100:.1f}%")
    print(f"Bust rate by lead day:")
    for ld in range(1, 11):
        ld_rate = df[df["lead_day"] == ld]["is_bust"].mean()
        print(f"  Day {ld:2d}: {ld_rate*100:.1f}%")

    # Save
    df.to_csv(output_path, index=False)
    print(f"\nSaved to {output_path} ({len(df):,} rows)")

    # Save thresholds
    thresh_path = output_path.replace(".csv", "_thresholds.csv")
    thresholds.to_csv(thresh_path, index=False)
    print(f"Saved thresholds to {thresh_path}")

    return df


if __name__ == "__main__":
    generate_and_save_synthetic()
