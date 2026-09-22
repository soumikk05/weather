"""
ERA5 Atmospheric State Loader
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Loads ERA5 reanalysis for ATMOSPHERIC STATE PREDICTORS ONLY.
ERA5 rainfall/precipitation MUST NOT be used as verification truth
(use IMD gridded rainfall for that).

Data source: ECMWF Climate Data Store (CDS)
Format: NetCDF via CDS API or local files
Resolution: 0.25° × 0.25°

Prerequisites:
  pip install cdsapi xarray netCDF4
  CDS API key: Register at https://cds.climate.copernicus.eu
  Place key in ~/.cdsapirc:
    url: https://cds.climate.copernicus.eu/api/v2
    key: {uid}:{api_key}

Usage:
  loader = ERA5Loader(data_dir="/path/to/era5/files")
  df = loader.load_atmospheric_state("2020-06-01", "2020-06-30")
"""

import os
from typing import Optional, List
import numpy as np
import pandas as pd

from src.data.schema import SUBDIVISIONS, SubdivisionInfo


class ERA5Loader:
    """
    Loads ERA5 reanalysis data for atmospheric-state features.

    ⚠️ ERA5 provides atmospheric state predictors (MSLP, wind shear,
    moisture convergence, CAPE, SST, vorticity). It is NOT used for
    rainfall verification truth.

    Parameters
    ----------
    data_dir : str
        Path to directory with ERA5 NetCDF files.
    use_cds_api : bool
        If True, download from CDS API (requires ~/.cdsapirc key).
    """

    # Variables to request from ERA5
    SINGLE_LEVEL_VARS = [
        "mean_sea_level_pressure",
        "2m_temperature",
        "convective_available_potential_energy",
        "sea_surface_temperature",
    ]
    PRESSURE_LEVEL_VARS = [
        "u_component_of_wind",
        "v_component_of_wind",
        "relative_humidity",
        "specific_humidity",
        "geopotential",
    ]
    PRESSURE_LEVELS = ["200", "500", "700", "850"]

    def __init__(
        self,
        data_dir: str = "data/era5",
        use_cds_api: bool = False,
    ):
        self.data_dir = data_dir
        self.use_cds_api = use_cds_api
        os.makedirs(data_dir, exist_ok=True)

    def load_atmospheric_state(
        self,
        start_date: str,
        end_date: str,
        subdivisions: Optional[List[SubdivisionInfo]] = None,
    ) -> pd.DataFrame:
        """
        Load ERA5 atmospheric state features aggregated to subdivision level.

        Returns DataFrame with ERA5 state columns per schema.py:
            valid_time, location_id, era5_mslp_hpa, era5_wind_shear_mps,
            era5_moisture_conv, era5_vorticity_850, era5_cape_jkg,
            era5_sst_c, era5_rh_700_pct

        ⚠️ NOTE: These are VALID-TIME analyses, not forecasts.
        When used as features, they must be restricted to dates
        available at forecast initialization time (see Stage 3
        leakage rules).
        """
        if subdivisions is None:
            subdivisions = SUBDIVISIONS

        if self.use_cds_api:
            return self._download_and_process(start_date, end_date, subdivisions)
        else:
            return self._load_local(start_date, end_date, subdivisions)

    def _download_and_process(self, start_date, end_date, subdivisions):
        """Download from CDS API and process."""
        try:
            import cdsapi
        except ImportError:
            raise ImportError(
                "cdsapi is required for ERA5 downloads. "
                "Install with: pip install cdsapi\n"
                "You also need a CDS API key. Register at:\n"
                "  https://cds.climate.copernicus.eu\n"
                "Then create ~/.cdsapirc with your key."
            )

        c = cdsapi.Client()

        # Download single-level data
        sl_path = os.path.join(self.data_dir, f"era5_sl_{start_date}_{end_date}.nc")
        if not os.path.exists(sl_path):
            c.retrieve(
                "reanalysis-era5-single-levels",
                {
                    "product_type": "reanalysis",
                    "format": "netcdf",
                    "variable": self.SINGLE_LEVEL_VARS,
                    "date": f"{start_date}/{end_date}",
                    "time": "00:00",
                    "area": [38, 65, 6, 98],  # India bounding box [N, W, S, E]
                },
                sl_path,
            )

        # Download pressure-level data
        pl_path = os.path.join(self.data_dir, f"era5_pl_{start_date}_{end_date}.nc")
        if not os.path.exists(pl_path):
            c.retrieve(
                "reanalysis-era5-pressure-levels",
                {
                    "product_type": "reanalysis",
                    "format": "netcdf",
                    "variable": self.PRESSURE_LEVEL_VARS,
                    "pressure_level": self.PRESSURE_LEVELS,
                    "date": f"{start_date}/{end_date}",
                    "time": "00:00",
                    "area": [38, 65, 6, 98],
                },
                pl_path,
            )

        return self._process_netcdf(sl_path, pl_path, subdivisions)

    def _load_local(self, start_date, end_date, subdivisions):
        """Load from local NetCDF files."""
        try:
            import xarray as xr
        except ImportError:
            raise ImportError(
                "xarray is required for reading ERA5 NetCDF files. "
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
                f"Place ERA5 files here or set use_cds_api=True with a CDS key."
            )

        records = []
        for nc_path in nc_files:
            try:
                ds = xr.open_dataset(nc_path)
                ds_sel = ds.sel(time=slice(start_date, end_date))
                for sub in subdivisions:
                    sub_records = self._extract_subdivision_era5(ds_sel, sub)
                    records.extend(sub_records)
            except Exception as e:
                print(f"Warning: Could not process {nc_path}: {e}")

        return pd.DataFrame(records) if records else pd.DataFrame()

    def _process_netcdf(self, sl_path, pl_path, subdivisions):
        """Process downloaded ERA5 NetCDF files."""
        import xarray as xr

        ds_sl = xr.open_dataset(sl_path)
        ds_pl = xr.open_dataset(pl_path)

        records = []
        for sub in subdivisions:
            try:
                sl_point = ds_sl.sel(
                    latitude=sub.lat, longitude=sub.lon, method="nearest"
                )
                pl_point = ds_pl.sel(
                    latitude=sub.lat, longitude=sub.lon, method="nearest"
                )

                for t_idx in range(len(sl_point.time)):
                    time_val = pd.Timestamp(sl_point.time.values[t_idx])
                    rec = self._build_era5_record(
                        sl_point.isel(time=t_idx),
                        pl_point.isel(time=t_idx),
                        sub, time_val,
                    )
                    records.append(rec)
            except Exception as e:
                print(f"Warning: ERA5 extraction failed for {sub.name}: {e}")

        return pd.DataFrame(records)

    def _extract_subdivision_era5(self, ds, sub):
        """Extract ERA5 features for one subdivision from a generic dataset."""
        records = []
        try:
            point = ds.sel(latitude=sub.lat, longitude=sub.lon, method="nearest")
            for t_idx in range(len(point.time)):
                time_val = pd.Timestamp(point.time.values[t_idx])
                rec = {
                    "valid_time": time_val.strftime("%Y-%m-%d"),
                    "location_id": sub.name,
                    "lat": sub.lat,
                    "lon": sub.lon,
                }
                # Extract whatever variables are available
                for var in point.data_vars:
                    val = float(point[var].isel(time=t_idx).values)
                    rec[f"era5_{var}"] = round(val, 4) if not np.isnan(val) else np.nan
                records.append(rec)
        except Exception:
            pass
        return records

    def _build_era5_record(self, sl_point, pl_point, sub, time_val):
        """Build a single ERA5 feature record from single and pressure level data."""
        rec = {
            "valid_time": time_val.strftime("%Y-%m-%d"),
            "location_id": sub.name,
            "lat": sub.lat,
            "lon": sub.lon,
        }

        # MSLP (Pa -> hPa)
        if "msl" in sl_point.data_vars:
            rec["era5_mslp_hpa"] = round(float(sl_point["msl"].values) / 100.0, 1)

        # CAPE
        if "cape" in sl_point.data_vars:
            rec["era5_cape_jkg"] = round(float(sl_point["cape"].values), 0)

        # SST (K -> °C)
        if "sst" in sl_point.data_vars:
            sst_val = float(sl_point["sst"].values)
            rec["era5_sst_c"] = round(sst_val - 273.15, 1) if not np.isnan(sst_val) else np.nan

        # Wind shear |V_200 - V_850|
        try:
            u850 = float(pl_point["u"].sel(level=850).values)
            v850 = float(pl_point["v"].sel(level=850).values)
            u200 = float(pl_point["u"].sel(level=200).values)
            v200 = float(pl_point["v"].sel(level=200).values)
            shear = np.sqrt((u200 - u850)**2 + (v200 - v850)**2)
            rec["era5_wind_shear_mps"] = round(shear, 1)
        except Exception:
            rec["era5_wind_shear_mps"] = np.nan

        # RH at 700 hPa
        try:
            rec["era5_rh_700_pct"] = round(float(pl_point["r"].sel(level=700).values), 1)
        except Exception:
            rec["era5_rh_700_pct"] = np.nan

        return rec


# Backward/forward alias
ERA5AtmosphericStateLoader = ERA5Loader

