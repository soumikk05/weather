"""
DEPRECATED: Legacy Synthetic Data Generator (Circular)
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

⚠️ WARNING: THIS MODULE IS DEPRECATED AND PRESERVED ONLY FOR LEGACY COMPATIBILITY.
The error formula in this generator is circular: forecast_error is a deterministic
function of the exact input features (ensemble_spread, pressure_gradient, etc.).
This artificially inflates machine learning metrics (e.g. PR-AUC ~0.999).

For scientifically honest evaluation and pipeline testing, use:
    src.data.synthetic.NonCircularSyntheticGenerator
"""

from abc import ABC, abstractmethod
import os
from typing import Dict, List, Optional
import warnings
import numpy as np
import pandas as pd

warnings.warn(
    "src/generate_synthetic_data.py is DEPRECATED due to circular dependency. "
    "Use src.data.synthetic.NonCircularSyntheticGenerator instead.",
    DeprecationWarning,
    stacklevel=2,
)

# -------------------------------------------------------------------------
# Meteorological Subdivisions Metadata (Centroids, Terrain, Difficulty)
# -------------------------------------------------------------------------
SUBDIVISIONS = [
    {"name": "Jammu & Kashmir and Ladakh", "lat": 34.0, "lon": 76.5, "terrain": "Himalayan", "terrain_difficulty": 0.88},
    {"name": "Himachal Pradesh", "lat": 31.8, "lon": 77.2, "terrain": "Himalayan", "terrain_difficulty": 0.82},
    {"name": "Uttarakhand", "lat": 30.1, "lon": 79.2, "terrain": "Himalayan", "terrain_difficulty": 0.80},
    {"name": "Punjab", "lat": 31.1, "lon": 75.3, "terrain": "Northern_Plains", "terrain_difficulty": 0.30},
    {"name": "Haryana, Chandigarh & Delhi", "lat": 29.0, "lon": 76.8, "terrain": "Northern_Plains", "terrain_difficulty": 0.32},
    {"name": "West Uttar Pradesh", "lat": 28.2, "lon": 78.5, "terrain": "Northern_Plains", "terrain_difficulty": 0.35},
    {"name": "East Uttar Pradesh", "lat": 26.5, "lon": 82.5, "terrain": "Northern_Plains", "terrain_difficulty": 0.40},
    {"name": "Bihar", "lat": 25.6, "lon": 85.8, "terrain": "Northern_Plains", "terrain_difficulty": 0.45},
    {"name": "Sub-Himalayan West Bengal & Sikkim", "lat": 26.8, "lon": 88.4, "terrain": "Northeastern_Hills", "terrain_difficulty": 0.84},
    {"name": "Gangetic West Bengal", "lat": 22.8, "lon": 87.9, "terrain": "Coastal_Plains", "terrain_difficulty": 0.58},
    {"name": "Odisha", "lat": 20.3, "lon": 85.8, "terrain": "Coastal_Plains", "terrain_difficulty": 0.62},
    {"name": "Jharkhand", "lat": 23.6, "lon": 85.3, "terrain": "Central_Plateau", "terrain_difficulty": 0.42},
    {"name": "East Madhya Pradesh", "lat": 23.2, "lon": 80.5, "terrain": "Central_Plateau", "terrain_difficulty": 0.38},
    {"name": "West Madhya Pradesh", "lat": 23.0, "lon": 76.5, "terrain": "Central_Plateau", "terrain_difficulty": 0.36},
    {"name": "Gujarat Region", "lat": 22.3, "lon": 72.5, "terrain": "Coastal_Plains", "terrain_difficulty": 0.52},
    {"name": "Saurashtra & Kutch", "lat": 22.2, "lon": 70.0, "terrain": "Arid_Desert", "terrain_difficulty": 0.48},
    {"name": "West Rajasthan", "lat": 26.9, "lon": 71.9, "terrain": "Arid_Desert", "terrain_difficulty": 0.34},
    {"name": "East Rajasthan", "lat": 26.5, "lon": 75.5, "terrain": "Central_Plateau", "terrain_difficulty": 0.38},
    {"name": "Konkan & Goa", "lat": 16.0, "lon": 73.8, "terrain": "Western_Ghats", "terrain_difficulty": 0.78},
    {"name": "Madhya Maharashtra", "lat": 18.5, "lon": 74.5, "terrain": "Peninsular_Interior", "terrain_difficulty": 0.42},
    {"name": "Marathwada", "lat": 19.3, "lon": 76.5, "terrain": "Peninsular_Interior", "terrain_difficulty": 0.40},
    {"name": "Vidarbha", "lat": 21.1, "lon": 79.1, "terrain": "Central_Plateau", "terrain_difficulty": 0.41},
    {"name": "Chhattisgarh", "lat": 21.3, "lon": 81.8, "terrain": "Central_Plateau", "terrain_difficulty": 0.45},
    {"name": "Coastal Andhra Pradesh", "lat": 16.5, "lon": 81.5, "terrain": "Coastal_Plains", "terrain_difficulty": 0.66},
    {"name": "Telangana", "lat": 17.8, "lon": 79.0, "terrain": "Peninsular_Interior", "terrain_difficulty": 0.43},
    {"name": "Rayalaseema", "lat": 14.5, "lon": 78.5, "terrain": "Peninsular_Interior", "terrain_difficulty": 0.44},
    {"name": "Tamil Nadu, Puducherry & Karaikal", "lat": 11.0, "lon": 79.0, "terrain": "Coastal_Plains", "terrain_difficulty": 0.56},
    {"name": "Coastal Karnataka", "lat": 13.5, "lon": 74.8, "terrain": "Western_Ghats", "terrain_difficulty": 0.75},
    {"name": "South Interior Karnataka", "lat": 13.0, "lon": 76.5, "terrain": "Peninsular_Interior", "terrain_difficulty": 0.46},
    {"name": "Kerala & Mahe", "lat": 10.5, "lon": 76.2, "terrain": "Western_Ghats", "terrain_difficulty": 0.80},
    {"name": "Assam & Meghalaya", "lat": 26.1, "lon": 92.9, "terrain": "Northeastern_Hills", "terrain_difficulty": 0.85},
    {"name": "Arunachal Pradesh", "lat": 28.2, "lon": 94.7, "terrain": "Northeastern_Hills", "terrain_difficulty": 0.88},
]

# Regime multiplier for forecast instability
REGIME_MULTIPLIERS = {
    "quiescent_clear": 0.65,
    "heat_wave": 1.25,
    "active_monsoon": 1.55,
    "break_monsoon": 1.45,
    "western_disturbance": 1.95,
    "monsoon_depression": 2.25,
    "cyclonic_disturbance": 2.75,
    "post_monsoon_transition": 1.35,
}

# -------------------------------------------------------------------------
# Abstract Base Data Loader (Contract for Real & Synthetic Data)
# -------------------------------------------------------------------------
class BaseDataLoader(ABC):
    """
    Abstract interface for forecast verification data ingestion.
    Allows zero-code-change transition from synthetic to real operational feeds.
    """

    @abstractmethod
    def load_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Loads forecast data with schema:
        [date, region, lat, lon, terrain, terrain_difficulty, synoptic_regime,
         lead_day, ensemble_spread, pressure_gradient_hpa, wind_shear_mps,
         moisture_convergence, enso_oni_index, mjo_amplitude, mjo_phase,
         surface_temp_c, cape_jkg, prior_day_error, forecast_error, is_bust]
        """
        pass


class RealNCMRWFDataLoader(BaseDataLoader):
    """
    Production-ready template for connecting real NCMRWF/IMD/ECMWF feeds.
    Matches the BaseDataLoader contract exactly.
    """

    def __init__(self, ncmrwf_gfs_dir: str = "", imd_obs_dir: str = ""):
        self.ncmrwf_gfs_dir = ncmrwf_gfs_dir
        self.imd_obs_dir = imd_obs_dir

    def load_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        raise NotImplementedError(
            "RealNCMRWFDataLoader requires access to NCMRWF FTP/OpenDAP archives. "
            "See Section 6 of README.md for the complete parameter mapping schema."
        )


class SyntheticDataLoader(BaseDataLoader):
    """
    Physically-motivated synthetic generator simulating medium-range NWP
    forecast verification dynamics across India.
    """

    def __init__(self, random_seed: int = 42):
        self.seed = random_seed

    def _determine_regime(self, month: int, day_noise: float, region: Dict) -> str:
        """Assigns meteorologically plausible synoptic regimes based on season and region."""
        # Winter / Pre-monsoon Western Disturbances in North / Himalayan
        if month in [12, 1, 2, 3] and region["lat"] > 27.0:
            if day_noise > 0.68:
                return "western_disturbance"

        # Pre-monsoon Heat Waves (April - May) in Central & Plains
        if month in [4, 5] and region["terrain"] in ["Northern_Plains", "Central_Plateau", "Arid_Desert"]:
            if day_noise > 0.65:
                return "heat_wave"

        # Monsoon Season (June - September)
        if month in [6, 7, 8, 9]:
            if day_noise > 0.84:
                return "cyclonic_disturbance"
            elif day_noise > 0.68:
                return "monsoon_depression"
            elif day_noise > 0.45:
                return "active_monsoon"
            elif day_noise > 0.30:
                return "break_monsoon"

        # Post-monsoon cyclone season (October - November) in coastal zones
        if month in [10, 11]:
            if region["terrain"] == "Coastal_Plains" and day_noise > 0.72:
                return "cyclonic_disturbance"
            elif day_noise > 0.60:
                return "post_monsoon_transition"

        return "quiescent_clear"

    def load_data(self, start_date: str = "2022-01-01", end_date: str = "2024-12-31") -> pd.DataFrame:
        np.random.seed(self.seed)
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")
        
        # Sample realistic dates to keep dataset efficient yet comprehensive (~45,000 - 65,000 rows)
        # e.g., sampling every 2nd day across 3 years provides high temporal density
        sampled_dates = date_range[::2]
        
        records = []
        
        # Simulated slow climate oscillation drivers
        total_days = len(sampled_dates)
        enso_cycle = 1.1 * np.sin(np.linspace(0, 3 * np.pi, total_days)) + np.random.normal(0, 0.15, total_days)
        mjo_amp_cycle = 1.2 + 0.7 * np.cos(np.linspace(0, 12 * np.pi, total_days)) + np.random.normal(0, 0.2, total_days)
        mjo_amp_cycle = np.clip(mjo_amp_cycle, 0.3, 2.9)
        mjo_phases = ((np.linspace(1, 24 * 8, total_days).astype(int) % 8) + 1)

        # Region-specific historical state memory for prior error
        prev_error_memory = {r["name"]: 8.0 for r in SUBDIVISIONS}

        for idx, date in enumerate(sampled_dates):
            month = date.month
            d_enso = float(enso_cycle[idx])
            d_mjo_amp = float(mjo_amp_cycle[idx])
            d_mjo_phase = int(mjo_phases[idx])
            
            # Daily synoptic noise
            synoptic_seed = np.random.uniform(0, 1)

            for reg in SUBDIVISIONS:
                reg_name = reg["name"]
                lat = reg["lat"]
                lon = reg["lon"]
                terrain = reg["terrain"]
                t_diff = reg["terrain_difficulty"]

                # Regional synoptic regime
                reg_noise = (synoptic_seed + np.random.uniform(-0.15, 0.15)) % 1.0
                regime = self._determine_regime(month, reg_noise, reg)
                regime_mult = REGIME_MULTIPLIERS[regime]

                # Base regional surface temperature (°C)
                seasonal_temp = 27.0 + 8.0 * np.sin((month - 4) * np.pi / 6.0) - (lat - 15.0) * 0.45
                surface_temp = seasonal_temp + np.random.normal(0, 1.8)
                if regime == "heat_wave":
                    surface_temp += np.random.uniform(4.0, 7.5)

                # Prior forecast cycle verification error
                prior_error = prev_error_memory[reg_name]

                # Simulate across Lead Day 1 to 10
                for lead_day in range(1, 11):
                    # 1. Non-linear ensemble spread growth with lead time
                    base_spread = 1.8 * (lead_day ** 0.85)
                    spread_noise = np.random.gamma(shape=2.5, scale=0.45)
                    ensemble_spread = (base_spread + spread_noise) * (1.0 + 0.35 * (regime_mult - 1.0))

                    # 2. Dynamic atmospheric predictors
                    # Pressure gradient (hPa across subdivision boundary)
                    base_pg = 2.0 + 1.8 * (lat / 30.0)
                    if regime in ["cyclonic_disturbance", "monsoon_depression"]:
                        pressure_gradient = base_pg + np.random.uniform(6.0, 14.0)
                    elif regime == "western_disturbance":
                        pressure_gradient = base_pg + np.random.uniform(3.5, 8.0)
                    else:
                        pressure_gradient = base_pg + np.random.exponential(1.2)

                    # Vertical Wind Shear (850 - 200 hPa in m/s)
                    wind_shear = 8.0 + 6.0 * np.sin(month * np.pi / 6.0) + np.random.normal(0, 2.5)
                    if regime in ["cyclonic_disturbance", "monsoon_depression"]:
                        wind_shear += np.random.uniform(5.0, 12.0)
                    wind_shear = max(2.0, wind_shear)

                    # Tropospheric Moisture Convergence (scaled g/kg/s proxy)
                    if month in [6, 7, 8, 9] or regime in ["cyclonic_disturbance", "monsoon_depression"]:
                        moisture_convergence = np.random.uniform(4.0, 12.0) + (1.5 if terrain in ["Western_Ghats", "Northeastern_Hills"] else 0.0)
                    elif regime == "western_disturbance":
                        moisture_convergence = np.random.uniform(2.5, 6.5)
                    else:
                        moisture_convergence = np.random.uniform(0.5, 3.5)

                    # Convective Available Potential Energy (CAPE, J/kg)
                    base_cape = 600.0 + 900.0 * np.sin(month * np.pi / 6.0)
                    if regime in ["monsoon_depression", "cyclonic_disturbance", "active_monsoon"]:
                        cape = base_cape + np.random.uniform(800.0, 2400.0)
                    else:
                        cape = max(50.0, base_cape + np.random.normal(0, 300.0))

                    # 3. Ground Truth Forecast Error Generation
                    # Atmospheric predictability decay curve:
                    predictability_decay = 2.4 * (lead_day ** 1.30)

                    # Dynamic disturbance factor
                    disturbance_component = (
                        0.40 * ensemble_spread
                        + 0.32 * pressure_gradient
                        + 0.25 * wind_shear
                        + 0.42 * moisture_convergence
                        + 0.0018 * cape
                    )

                    # Terrain and historical inertia penalty
                    terrain_penalty = 8.5 * t_diff * (lead_day / 5.0)
                    inertia_penalty = 0.20 * prior_error

                    # Climate oscillation modulation (ENSO/MJO)
                    climate_modulation = 1.0 + 0.10 * abs(d_enso) + 0.12 * (d_mjo_amp if d_mjo_phase in [3, 4, 5] else 0.0)

                    # Total continuous forecast error (mm or verification index)
                    total_error = (
                        (predictability_decay + disturbance_component + terrain_penalty + inertia_penalty)
                        * regime_mult
                        * climate_modulation
                        + np.random.normal(0, 3.5)
                    )
                    forecast_error = float(np.clip(total_error, 0.5, 180.0))

                    # 4. Forecast Bust Formulation
                    # Operational tolerance threshold scaling realistically with lead time
                    # Day 1 ~ 20 mm, Day 5 ~ 42 mm, Day 10 ~ 68 mm
                    tolerance_threshold = 16.5 + 4.6 * (lead_day ** 1.05)
                    
                    # Bust condition: continuous error > lead-adjusted tolerance
                    is_bust = 1 if forecast_error > tolerance_threshold else 0

                    records.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "region": reg_name,
                        "lat": lat,
                        "lon": lon,
                        "terrain": terrain,
                        "terrain_difficulty": round(t_diff, 2),
                        "synoptic_regime": regime,
                        "lead_day": lead_day,
                        "ensemble_spread": round(ensemble_spread, 3),
                        "pressure_gradient_hpa": round(pressure_gradient, 2),
                        "wind_shear_mps": round(wind_shear, 2),
                        "moisture_convergence": round(moisture_convergence, 2),
                        "enso_oni_index": round(d_enso, 2),
                        "mjo_amplitude": round(d_mjo_amp, 2),
                        "mjo_phase": d_mjo_phase,
                        "surface_temp_c": round(surface_temp, 1),
                        "cape_jkg": round(cape, 1),
                        "prior_day_error": round(prior_error, 2),
                        "forecast_error": round(forecast_error, 2),
                        "is_bust": is_bust,
                    })

                    # Update prior error memory using Day-1 error as proxy for subsequent cycle
                    if lead_day == 1:
                        prev_error_memory[reg_name] = round(0.7 * prior_error + 0.3 * forecast_error, 2)

        df = pd.DataFrame(records)
        return df


def generate_and_save_dataset(
    output_path: str = "data/nwp_forecast_bust_dataset.csv",
    start_date: str = "2022-01-01",
    end_date: str = "2024-12-31"
) -> pd.DataFrame:
    """Generates synthetic forecast dataset and persists to disk."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"Generating synthetic NWP forecast dataset from {start_date} to {end_date}...")
    loader = SyntheticDataLoader(random_seed=42)
    df = loader.load_data(start_date=start_date, end_date=end_date)
    df.to_csv(output_path, index=False)
    
    bust_pct = df["is_bust"].mean() * 100
    print(f"Dataset generated successfully at: {output_path}")
    print(f"Total records: {len(df):,}")
    print(f"Subdivisions: {df['region'].nunique()}")
    print(f"Bust class balance: {bust_pct:.2f}% busts ({df['is_bust'].sum():,} busts)")
    print(f"Lead day coverage: {sorted(df['lead_day'].unique())}")
    return df


if __name__ == "__main__":
    generate_and_save_dataset()
