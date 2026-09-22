"""
Cyclone Proximity and Track Loader (IBTrACS)
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Loads official tropical cyclone best track data from NOAA NCEI IBTrACS
specifically for the North Indian Ocean basin (NI: Bay of Bengal & Arabian Sea).
Computes spatial proximity, storm distance, intensity, and IMD cyclone stage.

Data Source:
  NOAA NCEI IBTrACS v04r01 (North Indian Ocean basin):
  https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.NI.list.v04r01.csv
"""

import os
import urllib.request
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.data.schema import CYCLONE_COLS


IBTRACS_NI_URL = (
    "https://www.ncei.noaa.gov/data/international-best-track-archive-for-"
    "climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.NI.list.v04r01.csv"
)

# IMD Tropical Cyclone Classification (wind speed in knots)
# Reference: India Meteorological Department Cyclone Manual
IMD_CATEGORIES = [
    (120.0, "SuCS"),  # Super Cyclonic Storm
    (90.0, "ESCS"),   # Extremely Severe Cyclonic Storm
    (64.0, "VSCS"),   # Very Severe Cyclonic Storm
    (48.0, "SCS"),    # Severe Cyclonic Storm
    (34.0, "CS"),     # Cyclonic Storm
    (28.0, "DD"),     # Deep Depression
    (17.0, "D"),      # Depression
    (0.0, "none"),    # Low pressure / sub-depression
]


def _haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great Circle distance in kilometers between two points."""
    r_earth = 6371.0
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)

    a = (
        np.sin(delta_phi / 2.0) ** 2
        + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return float(r_earth * c)


def _classify_imd_cyclone(wind_kt: float) -> str:
    """Classify storm into IMD category based on max sustained wind in knots."""
    if np.isnan(wind_kt) or wind_kt <= 0:
        return "none"
    for threshold, cat in IMD_CATEGORIES:
        if wind_kt >= threshold:
            return cat
    return "none"


class CycloneTrackLoader:
    """
    Loads and processes IBTrACS cyclone track data for North Indian Ocean.
    """

    def __init__(self, cache_dir: str = "data/cyclone_tracks", auto_download: bool = False):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "ibtracs_ni.csv")
        self.auto_download = auto_download
        self._tracks_df: Optional[pd.DataFrame] = None

    def fetch_data(self, force_download: bool = False) -> pd.DataFrame:
        """Download or load cached IBTrACS North Indian Ocean track data."""
        if self._tracks_df is not None and not force_download:
            return self._tracks_df

        if not os.path.exists(self.cache_file):
            if not self.auto_download and not force_download:
                self._tracks_df = pd.DataFrame()
                return self._tracks_df

            os.makedirs(self.cache_dir, exist_ok=True)
            try:
                req = urllib.request.Request(
                    IBTRACS_NI_URL,
                    headers={"User-Agent": "NCMRWF-Reliability-Engine/2.0"},
                )
                with urllib.request.urlopen(req, timeout=3.0) as resp, open(self.cache_file, "wb") as f:
                    f.write(resp.read())
            except Exception as e:
                self._tracks_df = pd.DataFrame()
                return self._tracks_df


        try:
            # IBTrACS CSV has row 1 with column names, row 2 with unit descriptions
            df = pd.read_csv(self.cache_file, skiprows=[1], low_memory=False)
            
            # Select and clean relevant columns
            # Standardize column names
            col_map = {
                "ISO_TIME": "iso_time",
                "USA_LAT": "lat",
                "USA_LON": "lon",
                "USA_WIND": "wind_kt",
                "NAME": "storm_name",
                "SID": "storm_id",
            }
            # Fallback to LAT/LON/WMO_WIND if USA_* missing
            if "USA_LAT" not in df.columns and "LAT" in df.columns:
                col_map["LAT"] = "lat"
            if "USA_LON" not in df.columns and "LON" in df.columns:
                col_map["LON"] = "lon"
            if "USA_WIND" not in df.columns and "WMO_WIND" in df.columns:
                col_map["WMO_WIND"] = "wind_kt"

            available = [c for c in col_map.keys() if c in df.columns]
            df = df[available].rename(columns=col_map)

            df["date"] = pd.to_datetime(df["iso_time"], errors="coerce").dt.strftime("%Y-%m-%d")
            df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
            df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
            df["wind_kt"] = pd.to_numeric(df["wind_kt"], errors="coerce").fillna(0.0)
            df = df.dropna(subset=["date", "lat", "lon"])
            self._tracks_df = df
            return df
        except Exception as e:
            print(f"Error parsing IBTrACS file: {e}")
            self._tracks_df = pd.DataFrame()
            return self._tracks_df

    def get_cyclone_features_for_point(
        self,
        target_date: str,
        target_lat: float,
        target_lon: float,
        max_dist_km: float = 1500.0,
    ) -> Dict[str, object]:
        """
        Compute cyclone proximity features for a single location and date.

        Parameters
        ----------
        target_date : str
            Date formatted as YYYY-MM-DD.
        target_lat : float
            Latitude in degrees N.
        target_lon : float
            Longitude in degrees E.
        max_dist_km : float
            Maximum distance radius in km to consider storm active for the region.

        Returns
        -------
        dict with keys matching CYCLONE_COLS:
          cyclone_present, cyclone_dist_km, cyclone_intensity_kt, cyclone_category
        """
        tracks = self.fetch_data()
        if tracks.empty:
            return {
                "cyclone_present": 0,
                "cyclone_dist_km": np.nan,
                "cyclone_intensity_kt": np.nan,
                "cyclone_category": "none",
            }

        daily_storms = tracks[tracks["date"] == target_date]
        if daily_storms.empty:
            return {
                "cyclone_present": 0,
                "cyclone_dist_km": np.nan,
                "cyclone_intensity_kt": np.nan,
                "cyclone_category": "none",
            }

        # Calculate distances to all track fixes on this date
        min_dist = float("inf")
        best_intensity = 0.0

        for _, row in daily_storms.iterrows():
            d = _haversine_distance_km(target_lat, target_lon, row["lat"], row["lon"])
            if d < min_dist:
                min_dist = d
                best_intensity = float(row["wind_kt"])

        is_present = 1 if min_dist <= max_dist_km else 0
        cat = _classify_imd_cyclone(best_intensity) if is_present else "none"

        return {
            "cyclone_present": is_present,
            "cyclone_dist_km": round(min_dist, 1) if is_present else np.nan,
            "cyclone_intensity_kt": best_intensity if is_present else np.nan,
            "cyclone_category": cat,
        }

    def enrich_dataframe(
        self,
        df: pd.DataFrame,
        date_col: str = "valid_time",
        lat_col: str = "lat",
        lon_col: str = "lon",
        max_dist_km: float = 1500.0,
    ) -> pd.DataFrame:
        """
        Enrich a forecast verification DataFrame with cyclone proximity predictors.
        """
        tracks = self.fetch_data()
        if tracks.empty or len(df) == 0:
            # Populate defaults compliant with schema
            out = df.copy()
            out["cyclone_present"] = 0
            out["cyclone_dist_km"] = np.nan
            out["cyclone_intensity_kt"] = np.nan
            out["cyclone_category"] = "none"
            return out

        # Extract unique (date, lat, lon) tuples for fast vectorized/cached computation
        # Normalize date to YYYY-MM-DD
        dates_norm = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")
        pts = pd.DataFrame({"d": dates_norm, "lat": df[lat_col], "lon": df[lon_col]}).drop_duplicates()

        results = []
        for _, row in pts.iterrows():
            feat = self.get_cyclone_features_for_point(
                target_date=row["d"],
                target_lat=row["lat"],
                target_lon=row["lon"],
                max_dist_km=max_dist_km,
            )
            feat["d"] = row["d"]
            feat["lat"] = row["lat"]
            feat["lon"] = row["lon"]
            results.append(feat)

        lookup = pd.DataFrame(results)
        df_out = df.copy()
        df_out["_d"] = dates_norm
        merged = df_out.merge(lookup, left_on=["_d", lat_col, lon_col], right_on=["d", "lat", "lon"], how="left")
        merged = merged.drop(columns=["_d", "d"], errors="ignore")
        return merged
