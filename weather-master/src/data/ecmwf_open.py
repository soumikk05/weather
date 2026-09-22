"""
ECMWF Open Data Loader
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Loads ECMWF open data (free tier) for deterministic + ensemble forecasts.
This is the FIRST-PRIORITY real forecast data source.

Data source: ECMWF Open Data (data.ecmwf.int)
Format: GRIB2 via ecmwf-opendata package or local files
Resolution: 0.4° (HRES) / 0.5° (ENS)
Lead times: Up to Day 10 (240h)

Prerequisites:
  pip install ecmwf-opendata
  No API key required for open data.

Usage:
  loader = ECMWFOpenDataLoader()
  df = loader.load_forecasts("2024-06-01", "2024-06-30")
"""

import os
from typing import Optional, List
import numpy as np
import pandas as pd

from src.data.loaders import BaseDataLoader
from src.data.schema import SUBDIVISIONS, SubdivisionInfo, DATA_SOURCE_REAL


class ECMWFOpenDataLoader(BaseDataLoader):
    """
    Loads ECMWF open forecast data.

    ECMWF provides free access to:
    - HRES (deterministic) forecasts
    - ENS (ensemble) spread and probabilities
    - Surface and pressure-level fields

    Parameters
    ----------
    cache_dir : str
        Directory to cache downloaded GRIB files.
    local_grib_dir : str, optional
        If provided, reads from local GRIB files instead of downloading.
    """

    # Fields to download for bust detection
    SURFACE_PARAMS = ["tp", "2t", "msl", "cape"]   # total precip, 2m temp, MSLP, CAPE
    PRESSURE_PARAMS = ["u", "v", "r", "gh"]         # wind, RH, geopotential height
    PRESSURE_LEVELS = [850, 700, 500, 200]

    def __init__(
        self,
        cache_dir: str = "data/ecmwf_open",
        local_grib_dir: Optional[str] = None,
    ):
        self.cache_dir = cache_dir
        self.local_grib_dir = local_grib_dir
        os.makedirs(cache_dir, exist_ok=True)

    def get_data_source(self) -> str:
        return DATA_SOURCE_REAL

    def load(
        self,
        start_date: str,
        end_date: str,
        locations: Optional[list] = None,
    ) -> pd.DataFrame:
        subs = None
        if locations:
            subs = [s for s in SUBDIVISIONS if s.name in locations]
        return self.load_forecasts(start_date=start_date, end_date=end_date, subdivisions=subs)

    def load_forecasts(
        self,
        start_date: str,
        end_date: str,
        subdivisions: Optional[List[SubdivisionInfo]] = None,
        lead_days: range = range(1, 11),
    ) -> pd.DataFrame:
        """
        Load ECMWF forecast data aggregated to subdivision level.

        Returns DataFrame with NWP forecast columns per schema.py.

        Parameters
        ----------
        start_date, end_date : str (YYYY-MM-DD)
        subdivisions : list, optional
        lead_days : range, default 1-10
        """
        if self.local_grib_dir:
            return self._load_from_local_grib(
                start_date, end_date, subdivisions, lead_days
            )
        else:
            return self._download_and_load(
                start_date, end_date, subdivisions, lead_days
            )

    def _download_and_load(
        self, start_date, end_date, subdivisions, lead_days
    ) -> pd.DataFrame:
        """Download from ECMWF open data API and process."""
        try:
            from ecmwf.opendata import Client
        except ImportError:
            raise ImportError(
                "ecmwf-opendata package is required. "
                "Install with: pip install ecmwf-opendata\n"
                "No API key needed — this uses free open data."
            )

        if subdivisions is None:
            subdivisions = SUBDIVISIONS

        client = Client()
        records = []
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")

        for date in date_range:
            init_date = date.strftime("%Y-%m-%d")

            for lead_day in lead_days:
                step_hours = lead_day * 24

                try:
                    # Download HRES surface fields
                    target_path = os.path.join(
                        self.cache_dir,
                        f"ecmwf_hres_{init_date}_t{step_hours:03d}.grib2"
                    )

                    if not os.path.exists(target_path):
                        client.retrieve(
                            date=init_date,
                            time=0,  # 00Z run
                            step=step_hours,
                            type="fc",
                            param=self.SURFACE_PARAMS,
                            target=target_path,
                        )

                    # Extract subdivision means from GRIB
                    sub_data = self._extract_from_grib(
                        target_path, subdivisions, init_date, lead_day
                    )
                    records.extend(sub_data)

                except Exception as e:
                    print(f"Warning: ECMWF download failed for {init_date} +{step_hours}h: {e}")
                    continue

        return pd.DataFrame(records) if records else pd.DataFrame()

    def _load_from_local_grib(
        self, start_date, end_date, subdivisions, lead_days
    ) -> pd.DataFrame:
        """Load from pre-downloaded local GRIB files."""
        try:
            import xarray as xr
            import cfgrib
        except ImportError:
            raise ImportError(
                "xarray and cfgrib are required for reading GRIB files. "
                "Install with: pip install xarray cfgrib eccodes"
            )

        if subdivisions is None:
            subdivisions = SUBDIVISIONS

        grib_files = sorted([
            os.path.join(self.local_grib_dir, f)
            for f in os.listdir(self.local_grib_dir)
            if f.endswith((".grib", ".grib2", ".grb", ".grb2"))
        ]) if os.path.isdir(self.local_grib_dir) else []

        if not grib_files:
            raise FileNotFoundError(
                f"No GRIB files found in {self.local_grib_dir}. "
                f"Expected ECMWF forecast GRIB2 files."
            )

        records = []
        for grib_path in grib_files:
            try:
                ds = xr.open_dataset(grib_path, engine="cfgrib")
                # Extract per subdivision
                for sub in subdivisions:
                    sub_data = self._extract_point_from_dataset(ds, sub)
                    if sub_data:
                        records.extend(sub_data)
            except Exception as e:
                print(f"Warning: Could not read {grib_path}: {e}")

        return pd.DataFrame(records) if records else pd.DataFrame()

    def _extract_from_grib(self, grib_path, subdivisions, init_date, lead_day):
        """Extract subdivision-mean values from a GRIB file."""
        try:
            import xarray as xr
            ds = xr.open_dataset(grib_path, engine="cfgrib")
            return self._extract_point_from_dataset(
                ds, subdivisions, init_date, lead_day
            )
        except Exception:
            return []

    def _extract_point_from_dataset(self, ds, subdivisions, init_date=None, lead_day=None):
        """Extract nearest-point values for each subdivision from xarray dataset."""
        records = []
        for sub in (subdivisions if isinstance(subdivisions, list) else [subdivisions]):
            try:
                point = ds.sel(latitude=sub.lat, longitude=sub.lon, method="nearest")
                rec = {
                    "initialization_time": init_date,
                    "lead_day": lead_day,
                    "location_id": sub.name,
                    "lat": sub.lat,
                    "lon": sub.lon,
                }
                # Map ECMWF parameter names to schema names
                param_map = {
                    "tp": "fcst_rainfall_mm",
                    "2t": "fcst_temp_2m_c",
                    "msl": "fcst_mslp_hpa",
                    "cape": "fcst_cape_jkg",
                }
                for ecmwf_name, schema_name in param_map.items():
                    if ecmwf_name in point.data_vars:
                        val = float(point[ecmwf_name].values)
                        if ecmwf_name == "tp":
                            val *= 1000.0  # m to mm
                        elif ecmwf_name == "2t":
                            val -= 273.15  # K to °C
                        elif ecmwf_name == "msl":
                            val /= 100.0  # Pa to hPa
                        rec[schema_name] = round(val, 2)
                records.append(rec)
            except Exception:
                continue
        return records
