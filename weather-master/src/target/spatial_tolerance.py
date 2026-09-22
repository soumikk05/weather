"""
Spatial Displacement & Neighbourhood-Tolerant Bust Analysis
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Addresses the classical NWP "Double Penalty Problem":
Convective rainfall bands or monsoon depressions often have correct intensity
and morphology but are displaced by 50-150 km into an adjacent subdivision.
A point-wise verification penalizes this twice (a false alarm in region A
and a miss in region B).

This module computes:
1. Spatial adjacency topology across the 32 IMD subdivisions.
2. Neighbourhood-relaxed forecast error:
   Checks if the predicted rainfall was observed in any contiguous neighbor.
3. `is_displacement_candidate`: Flags busts that were actually spatial shifts.
4. `is_neighbourhood_bust`: Relaxed bust label accounting for spatial tolerance.
"""

from typing import Dict, List, Optional, Set
import numpy as np
import pandas as pd

from src.data.schema import SUBDIVISIONS, SUBDIVISION_MAP


# Contiguity adjacency graph for the 32 IMD meteorological subdivisions
# Each entry lists the physically adjacent neighbouring subdivisions.
SUBDIVISION_ADJACENCY: Dict[str, List[str]] = {
    "Jammu & Kashmir and Ladakh": ["Himachal Pradesh", "Punjab"],
    "Himachal Pradesh": ["Jammu & Kashmir and Ladakh", "Punjab", "Haryana, Chandigarh & Delhi", "Uttarakhand"],
    "Uttarakhand": ["Himachal Pradesh", "Haryana, Chandigarh & Delhi", "West Uttar Pradesh"],
    "Punjab": ["Jammu & Kashmir and Ladakh", "Himachal Pradesh", "Haryana, Chandigarh & Delhi", "West Rajasthan"],
    "Haryana, Chandigarh & Delhi": ["Punjab", "Himachal Pradesh", "Uttarakhand", "West Uttar Pradesh", "East Rajasthan"],
    "West Uttar Pradesh": ["Uttarakhand", "Haryana, Chandigarh & Delhi", "East Uttar Pradesh", "East Rajasthan", "West Madhya Pradesh"],
    "East Uttar Pradesh": ["West Uttar Pradesh", "Bihar", "East Madhya Pradesh", "Jharkhand"],
    "Bihar": ["East Uttar Pradesh", "Jharkhand", "Sub-Himalayan West Bengal & Sikkim", "Gangetic West Bengal"],
    "Sub-Himalayan West Bengal & Sikkim": ["Bihar", "Gangetic West Bengal", "Assam & Meghalaya"],
    "Gangetic West Bengal": ["Bihar", "Jharkhand", "Odisha", "Sub-Himalayan West Bengal & Sikkim"],
    "Odisha": ["Gangetic West Bengal", "Jharkhand", "Chhattisgarh", "Coastal Andhra Pradesh"],
    "Jharkhand": ["Bihar", "East Uttar Pradesh", "Chhattisgarh", "Odisha", "Gangetic West Bengal"],
    "East Madhya Pradesh": ["West Madhya Pradesh", "East Uttar Pradesh", "Chhattisgarh", "Vidarbha"],
    "West Madhya Pradesh": ["East Rajasthan", "West Uttar Pradesh", "East Madhya Pradesh", "Gujarat Region", "Madhya Maharashtra"],
    "Gujarat Region": ["Saurashtra & Kutch", "East Rajasthan", "West Madhya Pradesh", "Konkan & Goa", "Madhya Maharashtra"],
    "Saurashtra & Kutch": ["Gujarat Region", "West Rajasthan"],
    "West Rajasthan": ["Punjab", "Haryana, Chandigarh & Delhi", "East Rajasthan", "Saurashtra & Kutch"],
    "East Rajasthan": ["West Rajasthan", "Haryana, Chandigarh & Delhi", "West Uttar Pradesh", "West Madhya Pradesh", "Gujarat Region"],
    "Konkan & Goa": ["Gujarat Region", "Madhya Maharashtra", "Coastal Karnataka"],
    "Madhya Maharashtra": ["Konkan & Goa", "West Madhya Pradesh", "Marathwada", "South Interior Karnataka", "Coastal Karnataka"],
    "Marathwada": ["Madhya Maharashtra", "Vidarbha", "Telangana", "South Interior Karnataka"],
    "Vidarbha": ["East Madhya Pradesh", "Chhattisgarh", "Telangana", "Marathwada"],
    "Chhattisgarh": ["East Madhya Pradesh", "Jharkhand", "Odisha", "Telangana", "Vidarbha"],
    "Coastal Andhra Pradesh": ["Odisha", "Telangana", "Rayalaseema", "Tamil Nadu, Puducherry & Karaikal"],
    "Telangana": ["Maharashtra", "Vidarbha", "Marathwada", "Chhattisgarh", "Coastal Andhra Pradesh", "Rayalaseema", "South Interior Karnataka"],
    "Rayalaseema": ["Telangana", "Coastal Andhra Pradesh", "South Interior Karnataka", "Tamil Nadu, Puducherry & Karaikal"],
    "Tamil Nadu, Puducherry & Karaikal": ["Coastal Andhra Pradesh", "Rayalaseema", "South Interior Karnataka", "Kerala & Mahe"],
    "Coastal Karnataka": ["Konkan & Goa", "Madhya Maharashtra", "South Interior Karnataka", "Kerala & Mahe"],
    "South Interior Karnataka": ["Coastal Karnataka", "Madhya Maharashtra", "Marathwada", "Telangana", "Rayalaseema", "Tamil Nadu, Puducherry & Karaikal", "Kerala & Mahe"],
    "Kerala & Mahe": ["Coastal Karnataka", "South Interior Karnataka", "Tamil Nadu, Puducherry & Karaikal"],
    "Assam & Meghalaya": ["Sub-Himalayan West Bengal & Sikkim", "Arunachal Pradesh"],
    "Arunachal Pradesh": ["Assam & Meghalaya"],
}


def get_subdivision_neighbors(name: str) -> List[str]:
    """Return list of adjacent subdivisions for a given subdivision."""
    return SUBDIVISION_ADJACENCY.get(name, [])


def compute_neighbourhood_displacement_metrics(
    df: pd.DataFrame,
    lead_day_col: str = "lead_day",
    valid_time_col: str = "valid_time",
    location_col: str = "location_id",
    fcst_col: str = "fcst_rainfall_mm",
    obs_col: str = "obs_rainfall_mm",
    bust_col: str = "is_bust",
    relative_match_tol: float = 0.35,
) -> pd.DataFrame:
    """
    Computes neighbourhood displacement metrics for each record.

    Parameters
    ----------
    df : pd.DataFrame
        Verification dataframe containing valid_time, location_id, lead_day,
        fcst_rainfall_mm, obs_rainfall_mm, and is_bust.
    relative_match_tol : float
        Fractional tolerance to consider an adjacent observation matching the forecast.

    Returns
    -------
    pd.DataFrame with added columns:
      - `neighbourhood_obs_max_mm`: Maximum observed rainfall among location + contiguous neighbors.
      - `neighbourhood_min_error_mm`: Minimum absolute difference between forecast and any neighbor observation.
      - `is_displacement_candidate`: 1 if local point was a bust, but adjacent neighbor observed the rainfall.
      - `is_neighbourhood_bust`: Relaxed bust label (1 only if neither local nor neighbor matched).
    """
    out = df.copy()

    # Pre-index observations by (valid_time, location_id) for rapid lookup
    time_loc_obs: Dict[Tuple[str, str], float] = {}
    for _, row in out.iterrows():
        vt = str(row[valid_time_col])[:10]
        loc = str(row[location_col])
        time_loc_obs[(vt, loc)] = float(row[obs_col])

    neigh_max_obs = []
    neigh_min_errs = []
    is_displaced = []
    neigh_busts = []

    for _, row in out.iterrows():
        vt = str(row[valid_time_col])[:10]
        loc = str(row[location_col])
        fcst_val = float(row[fcst_col])
        obs_val = float(row[obs_col])
        is_local_bust = int(row.get(bust_col, 0))

        neighbors = get_subdivision_neighbors(loc)
        neighbor_obs_list = [obs_val]

        for n_name in neighbors:
            if (vt, n_name) in time_loc_obs:
                neighbor_obs_list.append(time_loc_obs[(vt, n_name)])

        max_n_obs = max(neighbor_obs_list)
        errors_against_neighbors = [abs(fcst_val - n_obs) for n_obs in neighbor_obs_list]
        min_n_err = min(errors_against_neighbors)

        # Check displacement condition:
        # If forecast called for rain (>15mm), local was a bust, but a neighbor received
        # approximately that amount (within tolerance)
        displaced = 0
        if is_local_bust and fcst_val >= 15.0:
            for n_obs in neighbor_obs_list[1:]:  # Check actual neighbors
                if abs(n_obs - fcst_val) <= max(15.0, relative_match_tol * fcst_val):
                    displaced = 1
                    break

        # A neighbourhood bust requires that both the local point and its neighbors failed
        # If displaced, neighbourhood bust is cleared to 0
        neigh_bust = 0 if displaced else is_local_bust

        neigh_max_obs.append(round(max_n_obs, 2))
        neigh_min_errs.append(round(min_n_err, 2))
        is_displaced.append(displaced)
        neigh_busts.append(neigh_bust)

    out["neighbourhood_obs_max_mm"] = neigh_max_obs
    out["neighbourhood_min_error_mm"] = neigh_min_errs
    out["is_displacement_candidate"] = is_displaced
    out["is_neighbourhood_bust"] = neigh_busts
    return out
