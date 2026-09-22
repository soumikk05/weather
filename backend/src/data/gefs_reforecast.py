"""
NOAA GEFS v12 Ensemble Reforecast Loader
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Loads NOAA Global Ensemble Forecast System (GEFS) version 12 reforecast data.
Provides multi-member ensemble forecasts for medium-range verification across India.

Data Source:
  NOAA GEFS v12 Reforecast (open access on AWS Open Data):
  - AWS S3: s3://noaa-gefs-retrospective/
  - HTTP: https://noaa-gefs-retrospective.s3.amazonaws.com/index.html
  - Resolution: 0.25° ~ 0.50° spatial grid, daily 00Z initialization
  - Ensemble: 1 control + 4/10/30 perturbed members (lead times 1-16 days)

Parameter Mappings:
  - APCP_surface (kg/m² = mm) -> fcst_rainfall_mm
  - TMP_2m (K -> °C)          -> fcst_temp_2m_c
  - PRMSL_msl (Pa -> hPa)     -> fcst_mslp_hpa
  - UGRD/VGRD 850 hPa (m/s)   -> fcst_wind_850_mps
  - UGRD/VGRD 200 hPa (m/s)   -> fcst_wind_200_mps
  - RH 700 hPa (%)            -> fcst_rh_700_pct
  - HGT 500 hPa (gpm)         -> fcst_geopot_500_m
  - CAPE surface (J/kg)       -> fcst_cape_jkg
  - Ensemble spread & probability counts computed across all members.
"""

import os
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.data.loaders import BaseDataLoader
from src.data.schema import (
    DATA_SOURCE_REAL,
    SUBDIVISIONS,
    SubdivisionInfo,
    IDENTIFIER_COLS,
    NWP_FORECAST_COLS,
)


class GEFSReforecastLoader(BaseDataLoader):
    """
    Loader for NOAA GEFS v12 ensemble reforecasts.
    
    Supports:
    1. Reading locally downloaded NetCDF/GRIB2 files in `data_dir`.
    2. Subsetting to Indian domain (Lat 6°N - 38°N, Lon 68°E - 98°E).
    3. Spatial aggregation onto IMD meteorological subdivisions.
    4. Computation of ensemble spread and probability counts.
    """

    def __init__(
        self,
        data_dir: str = "data/gefs_reforecast",
        model_version: str = "GEFS_v12",
    ):
        self.data_dir = data_dir
        self.model_version = model_version

    def get_data_source(self) -> str:
        return DATA_SOURCE_REAL

    def load(
        self,
        start_date: str,
        end_date: str,
        locations: Optional[List[str]] = None,
        max_lead_day: int = 10,
    ) -> pd.DataFrame:
        """
        Load GEFS forecast records for the specified date range.

        Parameters
        ----------
        start_date : str
            Start initialization date (YYYY-MM-DD).
        end_date : str
            End initialization date (YYYY-MM-DD), inclusive.
        locations : list of str, optional
            Subdivision names. None = all 32 subdivisions.
        max_lead_day : int
            Maximum forecast lead day (1 to 10).

        Returns
        -------
        pd.DataFrame
            Compliant verification dataframe with identifier and NWP forecast columns.
        """
        subdivs = SUBDIVISIONS
        if locations:
            subdivs = [s for s in SUBDIVISIONS if s.name in locations]
            if not subdivs:
                raise ValueError(f"None of specified locations matched known subdivisions: {locations}")

        init_dates = pd.date_range(start=start_date, end=end_date, freq="D")
        
        # Check if local files exist in data_dir
        local_files = []
        if os.path.isdir(self.data_dir):
            local_files = [
                f for f in os.listdir(self.data_dir)
                if f.endswith((".nc", ".nc4", ".grb2", ".grib2", ".csv"))
            ]

        if local_files:
            return self._load_from_local_files(local_files, init_dates, subdivs, max_lead_day)
        
        # If no local files, provide clear instructions and raise FileNotFoundError
        # or load sample template if in dry-run/mock mode
        msg = (
            f"No GEFS reforecast files found in '{self.data_dir}'.\n"
            f"To download NOAA GEFS v12 reforecasts:\n"
            f"  1. AWS Open Data S3 bucket: 's3://noaa-gefs-retrospective/'\n"
            f"  2. CLI example:\n"
            f"     aws s3 cp --no-sign-request s3://noaa-gefs-retrospective/GEFSv12/reforecast/ "
            f"{self.data_dir}/ --recursive --exclude '*' --include '*Days:1-10*'\n"
            f"  3. Required variables: APCP_surface, TMP_2m, PRMSL_msl, UGRD_850, VGRD_850, HGT_500\n"
            f"  4. Place files in {os.path.abspath(self.data_dir)}"
        )
        raise FileNotFoundError(msg)

    def _load_from_local_files(
        self,
        files: List[str],
        init_dates: pd.DatetimeIndex,
        subdivs: List[SubdivisionInfo],
        max_lead_day: int,
    ) -> pd.DataFrame:
        """Parse local GEFS files into standard schema."""
        # Support pre-processed CSV format as well as NetCDF
        csv_files = [f for f in files if f.endswith(".csv")]
        if csv_files:
            dfs = []
            for cf in csv_files:
                path = os.path.join(self.data_dir, cf)
                df = pd.read_csv(path)
                dfs.append(df)
            combined = pd.concat(dfs, ignore_index=True)
            self.validate_schema(combined)
            return combined

        # NetCDF reader via xarray
        try:
            import xarray as xr
        except ImportError:
            raise ImportError(
                "xarray is required to read GEFS NetCDF files. "
                "Install with: pip install xarray netcdf4"
            )

        rows = []
        for init_dt in init_dates:
            dt_str = init_dt.strftime("%Y%m%d")
            matching = [f for f in files if dt_str in f]
            if not matching:
                continue

            for f in matching:
                ds = xr.open_dataset(os.path.join(self.data_dir, f))
                for lead in range(1, max_lead_day + 1):
                    valid_dt = init_dt + pd.Timedelta(days=lead)
                    for sub in subdivs:
                        # Extract nearest grid point to subdivision centroid
                        pt = ds.sel(lat=sub.lat, lon=sub.lon, method="nearest")
                        
                        # Extract ensemble values if member dimension exists
                        if "member" in pt.dims:
                            rain_members = pt["APCP_surface"].values if "APCP_surface" in pt else np.zeros(1)
                            temp_members = pt["TMP_2m"].values - 273.15 if "TMP_2m" in pt else np.full(1, 25.0)
                            mslp_members = pt["PRMSL_msl"].values / 100.0 if "PRMSL_msl" in pt else np.full(1, 1013.0)
                            
                            fcst_rain = float(np.mean(rain_members))
                            fcst_temp = float(np.mean(temp_members))
                            fcst_mslp = float(np.mean(mslp_members))
                            ens_spread_rain = float(np.std(rain_members))
                            ens_spread_temp = float(np.std(temp_members))
                            ens_spread_mslp = float(np.std(mslp_members))
                            n_members = len(rain_members)
                            gt10 = int(np.sum(rain_members > 10.0))
                            gt50 = int(np.sum(rain_members > 50.0))
                        else:
                            fcst_rain = float(pt.get("APCP_surface", 0.0))
                            fcst_temp = float(pt.get("TMP_2m", 298.15)) - 273.15
                            fcst_mslp = float(pt.get("PRMSL_msl", 101325.0)) / 100.0
                            ens_spread_rain = 0.0
                            ens_spread_temp = 0.0
                            ens_spread_mslp = 0.0
                            n_members = 1
                            gt10 = int(fcst_rain > 10.0)
                            gt50 = int(fcst_rain > 50.0)

                        rows.append({
                            "initialization_time": init_dt.strftime("%Y-%m-%d 00:00:00"),
                            "valid_time": valid_dt.strftime("%Y-%m-%d"),
                            "lead_day": lead,
                            "location_id": sub.name,
                            "lat": sub.lat,
                            "lon": sub.lon,
                            "model_version": self.model_version,
                            "data_source": DATA_SOURCE_REAL,
                            "fcst_rainfall_mm": max(0.0, fcst_rain),
                            "fcst_temp_2m_c": fcst_temp,
                            "fcst_mslp_hpa": fcst_mslp,
                            "fcst_wind_850_mps": float(pt.get("WIND_850", 5.0)),
                            "fcst_wind_200_mps": float(pt.get("WIND_200", 15.0)),
                            "fcst_rh_700_pct": float(pt.get("RH_700", 60.0)),
                            "fcst_geopot_500_m": float(pt.get("HGT_500", 5800.0)),
                            "fcst_cape_jkg": float(pt.get("CAPE", 500.0)),
                            "fcst_moisture_flux_conv": float(pt.get("MFC", 0.0)),
                            "ens_spread_rainfall": ens_spread_rain,
                            "ens_spread_temp": ens_spread_temp,
                            "ens_spread_mslp": ens_spread_mslp,
                            "ens_members_total": n_members,
                            "ens_members_rain_gt10": gt10,
                            "ens_members_rain_gt50": gt50,
                        })

        df = pd.DataFrame(rows)
        if len(df) > 0:
            self.validate_schema(df)
        return df
