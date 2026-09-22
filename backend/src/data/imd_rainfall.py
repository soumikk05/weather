"""
IMD Gridded Rainfall Truth Loader
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Loads IMD 0.25° × 0.25° gridded daily rainfall analysis as GROUND TRUTH
for forecast verification. This is the ONLY acceptable rainfall truth
source (ERA5 rainfall must NOT be used as truth).

Data source: India Meteorological Department (IMD)
Format: NetCDF or binary (.grd) via imdlib or local files
Resolution: 0.25° × 0.25° daily
Coverage: 1901-present (gridded), most reliable post-1951

Prerequisites:
  pip install imdlib
  OR: Place local NetCDF/binary files in the configured directory.

Usage:
  loader = IMDRainfallLoader(data_dir="/path/to/imd/rainfall")
  df = loader.load("2020-01-01", "2024-12-31")
"""

import os
from typing import Optional, List
import numpy as np
import pandas as pd

from src.data.loaders import BaseDataLoader
from src.data.schema import DATA_SOURCE_REAL, SUBDIVISIONS, SubdivisionInfo


class IMDRainfallLoader:
    """
    Loads IMD gridded rainfall data and aggregates to subdivision level.

    This is NOT a full BaseDataLoader — it provides truth (observations)
    only. It must be combined with forecast data to produce complete records.

    Parameters
    ----------
    data_dir : str
        Path to directory containing IMD rainfall files.
        Expected formats:
        - NetCDF: 'RF25_ind{year}.nc' or 'rainfall_{year}.nc'
        - Binary: '{year}.grd' (imdlib format)
    use_imdlib : bool
        If True, attempt to use imdlib for data download/reading.
        If False, read local NetCDF files directly.
    """

    def __init__(self, data_dir: str = "data/imd_rainfall", use_imdlib: bool = False):
        self.data_dir = data_dir
        self.use_imdlib = use_imdlib

    def load_daily_rainfall(
        self,
        start_date: str,
        end_date: str,
        subdivisions: Optional[List[SubdivisionInfo]] = None,
    ) -> pd.DataFrame:
        """
        Load daily observed rainfall aggregated to subdivision level.

        Returns DataFrame with columns:
            valid_time, location_id, lat, lon, obs_rainfall_mm

        Parameters
        ----------
        start_date, end_date : str (YYYY-MM-DD)
        subdivisions : list of SubdivisionInfo, optional
            Defaults to all 32 subdivisions.
        """
        if subdivisions is None:
            subdivisions = SUBDIVISIONS

        if self.use_imdlib:
            return self._load_via_imdlib(start_date, end_date, subdivisions)
        else:
            return self._load_local_netcdf(start_date, end_date, subdivisions)

    def _load_via_imdlib(
        self, start_date: str, end_date: str, subdivisions: List[SubdivisionInfo]
    ) -> pd.DataFrame:
        """Load using imdlib package (downloads if needed)."""
        try:
            import imdlib as imd
        except ImportError:
            raise ImportError(
                "imdlib is required for IMD rainfall loading. "
                "Install with: pip install imdlib\n"
                "Alternatively, place local NetCDF files in the data directory "
                "and set use_imdlib=False."
            )

        start_yr = int(start_date[:4])
        end_yr = int(end_date[:4])

        # Download or load from cache
        os.makedirs(self.data_dir, exist_ok=True)
        data = imd.open_data("rain", start_yr, end_yr, "yearwise", self.data_dir)

        # Convert to xarray for extraction
        ds = data.get_xarray()

        return self._extract_subdivision_means(
            ds, start_date, end_date, subdivisions, var_name="rain"
        )

    def _load_local_netcdf(
        self, start_date: str, end_date: str, subdivisions: List[SubdivisionInfo]
    ) -> pd.DataFrame:
        """Load from local NetCDF files."""
        try:
            import xarray as xr
        except ImportError:
            raise ImportError(
                "xarray is required for reading NetCDF files. "
                "Install with: pip install xarray netCDF4"
            )

        nc_files = sorted([
            os.path.join(self.data_dir, f)
            for f in os.listdir(self.data_dir)
            if f.endswith((".nc", ".nc4"))
        ]) if os.path.isdir(self.data_dir) else []

        if not nc_files:
            raise FileNotFoundError(
                f"No NetCDF files found in {self.data_dir}. "
                f"Please provide IMD gridded rainfall files or use imdlib."
            )

        ds = xr.open_mfdataset(nc_files, combine="by_coords")

        # Try common variable names
        var_name = None
        for candidate in ["rain", "rainfall", "rf", "RAIN", "RF"]:
            if candidate in ds.data_vars:
                var_name = candidate
                break
        if var_name is None:
            raise ValueError(
                f"Could not find rainfall variable in NetCDF. "
                f"Available variables: {list(ds.data_vars)}"
            )

        return self._extract_subdivision_means(
            ds, start_date, end_date, subdivisions, var_name
        )

    def _extract_subdivision_means(
        self, ds, start_date: str, end_date: str,
        subdivisions: List[SubdivisionInfo], var_name: str,
    ) -> pd.DataFrame:
        """
        Extract area-mean rainfall for each subdivision.

        Uses a simple box average around each subdivision centroid (±1°).
        A production system would use proper polygon boundaries.
        """
        import xarray as xr

        # Slice time
        ds_sel = ds.sel(time=slice(start_date, end_date))

        records = []
        for sub in subdivisions:
            # Extract ±1° box around centroid
            try:
                box = ds_sel[var_name].sel(
                    lat=slice(sub.lat - 1.0, sub.lat + 1.0),
                    lon=slice(sub.lon - 1.0, sub.lon + 1.0),
                )
                daily_mean = box.mean(dim=["lat", "lon"])

                for t_idx in range(len(daily_mean.time)):
                    val = float(daily_mean.isel(time=t_idx).values)
                    time_val = pd.Timestamp(daily_mean.time.values[t_idx])
                    records.append({
                        "valid_time": time_val.strftime("%Y-%m-%d"),
                        "location_id": sub.name,
                        "lat": sub.lat,
                        "lon": sub.lon,
                        "obs_rainfall_mm": max(0.0, val) if not np.isnan(val) else np.nan,
                    })
            except Exception as e:
                print(f"Warning: Could not extract data for {sub.name}: {e}")

        return pd.DataFrame(records)
