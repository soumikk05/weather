"""
Climate Indices Loader (MJO, ENSO, IOD, BSISO)
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Loads large-scale climate oscillation indices from public sources.
These are available in near-real-time and do not require special credentials.

Sources:
  - ENSO ONI: NOAA CPC (https://origin.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php)
  - MJO RMM: BoM Australia (http://www.bom.gov.au/climate/mjo/)
  - IOD DMI: NOAA PSL or BoM
  - BSISO: Various research centers

No API keys required. Data is downloaded from public URLs.
"""

import os
from typing import Optional
import numpy as np
import pandas as pd


class ClimateIndicesLoader:
    """
    Loads climate oscillation indices and merges them by date.

    These indices are slowly varying (weekly/monthly for ENSO/IOD,
    daily for MJO/BSISO) and can be freely used as features without
    leakage concerns — they are public knowledge at forecast time.

    Parameters
    ----------
    cache_dir : str
        Directory to cache downloaded index files.
    """

    # Public data URLs
    ONI_URL = "https://origin.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/detrend.nino34.ascii.txt"
    RMM_URL = "http://www.bom.gov.au/climate/mjo/graphics/rmm.74toRealtime.txt"

    def __init__(self, cache_dir: str = "data/climate_indices"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def load_all_indices(
        self,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        Load all available climate indices for the date range.

        Returns DataFrame with columns:
            date, enso_oni, mjo_rmm1, mjo_rmm2, mjo_amplitude,
            mjo_phase, iod_dmi

        These are keyed by date (not location) and should be broadcast
        across all locations when merging.
        """
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")
        result = pd.DataFrame({"date": date_range.strftime("%Y-%m-%d")})

        # Try to load each index; fill with NaN if unavailable
        try:
            oni = self._load_enso_oni(start_date, end_date)
            result = result.merge(oni, on="date", how="left")
        except Exception as e:
            print(f"Warning: Could not load ENSO ONI: {e}")
            result["enso_oni"] = np.nan

        try:
            rmm = self._load_mjo_rmm(start_date, end_date)
            result = result.merge(rmm, on="date", how="left")
        except Exception as e:
            print(f"Warning: Could not load MJO RMM: {e}")
            result["mjo_rmm1"] = np.nan
            result["mjo_rmm2"] = np.nan
            result["mjo_amplitude"] = np.nan
            result["mjo_phase"] = np.nan

        # IOD is harder to get programmatically — fill from local file if available
        try:
            iod = self._load_iod(start_date, end_date)
            result = result.merge(iod, on="date", how="left")
        except Exception:
            result["iod_dmi"] = np.nan

        return result

    def _load_enso_oni(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Load ENSO ONI index from NOAA CPC.

        ONI is a 3-month running mean of SST anomalies in the Niño 3.4 region.
        Updated monthly. We interpolate to daily by forward-filling the monthly value.
        """
        cache_path = os.path.join(self.cache_dir, "enso_oni.csv")

        if os.path.exists(cache_path):
            oni_df = pd.read_csv(cache_path)
        else:
            # Try to download
            try:
                oni_df = pd.read_csv(
                    self.ONI_URL, delim_whitespace=True, skiprows=1,
                    names=["year", "month", "anom", "total"]
                )
                oni_df["date"] = pd.to_datetime(
                    oni_df["year"].astype(str) + "-" + oni_df["month"].astype(str).str.zfill(2) + "-15"
                )
                oni_df = oni_df[["date", "anom"]].rename(columns={"anom": "enso_oni"})
                oni_df["date"] = oni_df["date"].dt.strftime("%Y-%m-%d")
                oni_df.to_csv(cache_path, index=False)
            except Exception:
                # If download fails, provide instructions
                raise FileNotFoundError(
                    f"Could not download ENSO ONI data and no cache found at {cache_path}. "
                    f"Please download ONI data from NOAA CPC and place as CSV with columns "
                    f"[date, enso_oni] at {cache_path}."
                )

        # Resample to daily by forward-fill
        oni_df["date"] = pd.to_datetime(oni_df["date"])
        oni_df = oni_df.set_index("date").resample("D").ffill().reset_index()
        oni_df["date"] = oni_df["date"].dt.strftime("%Y-%m-%d")

        mask = (oni_df["date"] >= start_date) & (oni_df["date"] <= end_date)
        return oni_df[mask][["date", "enso_oni"]].reset_index(drop=True)

    def _load_mjo_rmm(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Load MJO RMM index from BoM Australia.

        RMM1 and RMM2 are the two principal components of the MJO.
        Phase = atan2(RMM2, RMM1) mapped to 1-8.
        Amplitude = sqrt(RMM1² + RMM2²).
        Updated daily.
        """
        cache_path = os.path.join(self.cache_dir, "mjo_rmm.csv")

        if os.path.exists(cache_path):
            rmm_df = pd.read_csv(cache_path)
        else:
            try:
                # BoM RMM file has a specific format
                rmm_raw = pd.read_csv(
                    self.RMM_URL, delim_whitespace=True, skiprows=2,
                    names=["year", "month", "day", "RMM1", "RMM2", "phase", "amplitude", "source"],
                    na_values=["1e+36", "1E+36", "999"],
                )
                rmm_raw["date"] = pd.to_datetime(
                    rmm_raw[["year", "month", "day"]].astype(int).astype(str).agg("-".join, axis=1),
                    format="%Y-%m-%d",
                    errors="coerce",
                )
                rmm_df = rmm_raw.dropna(subset=["date"])[
                    ["date", "RMM1", "RMM2", "phase", "amplitude"]
                ].rename(columns={
                    "RMM1": "mjo_rmm1",
                    "RMM2": "mjo_rmm2",
                    "phase": "mjo_phase",
                    "amplitude": "mjo_amplitude",
                })
                rmm_df["date"] = rmm_df["date"].dt.strftime("%Y-%m-%d")
                rmm_df.to_csv(cache_path, index=False)
            except Exception:
                raise FileNotFoundError(
                    f"Could not download MJO RMM data and no cache found at {cache_path}. "
                    f"Please download from BoM and place as CSV with columns "
                    f"[date, mjo_rmm1, mjo_rmm2, mjo_phase, mjo_amplitude] at {cache_path}."
                )

        mask = (rmm_df["date"] >= start_date) & (rmm_df["date"] <= end_date)
        return rmm_df[mask].reset_index(drop=True)

    def _load_iod(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Load Indian Ocean Dipole (IOD) DMI index.

        IOD is monthly; daily values are forward-filled.
        Must be provided as local CSV: data/climate_indices/iod_dmi.csv
        with columns [date, iod_dmi].
        """
        cache_path = os.path.join(self.cache_dir, "iod_dmi.csv")

        if not os.path.exists(cache_path):
            raise FileNotFoundError(
                f"IOD DMI data not found at {cache_path}. "
                f"Please download from NOAA PSL or BoM and provide as CSV "
                f"with columns [date, iod_dmi]."
            )

        iod_df = pd.read_csv(cache_path)
        iod_df["date"] = pd.to_datetime(iod_df["date"])
        iod_df = iod_df.set_index("date").resample("D").ffill().reset_index()
        iod_df["date"] = iod_df["date"].dt.strftime("%Y-%m-%d")

        mask = (iod_df["date"] >= start_date) & (iod_df["date"] <= end_date)
        return iod_df[mask][["date", "iod_dmi"]].reset_index(drop=True)
