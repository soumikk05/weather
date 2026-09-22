"""
Base Data Loader Contract
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Abstract base class that all data sources (synthetic, ECMWF, GEFS,
NCMRWF local files) must implement. Enforces schema compliance.
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd

from src.data.schema import IDENTIFIER_COLS, DATA_SOURCE_SYNTHETIC, DATA_SOURCE_REAL


class BaseDataLoader(ABC):
    """
    Abstract interface for forecast verification data ingestion.

    Every concrete loader must produce a DataFrame with at minimum the
    identifier columns defined in schema.py. Additional columns (NWP fields,
    observations, ensemble stats) are loader-specific but should follow
    the canonical naming from schema.py.

    Key invariants:
    - initialization_time and valid_time are datetime-parseable strings or Timestamps
    - lead_day ∈ {1, 2, ..., 10}
    - data_source is either "synthetic" or "real"
    - No future information leaks into features (features depend only on
      data available at initialization_time)
    """

    @abstractmethod
    def load(
        self,
        start_date: str,
        end_date: str,
        locations: Optional[list] = None,
    ) -> pd.DataFrame:
        """
        Load forecast verification data for the specified date range.

        Parameters
        ----------
        start_date : str
            Start of initialization date range (YYYY-MM-DD).
        end_date : str
            End of initialization date range (YYYY-MM-DD), inclusive.
        locations : list, optional
            Subset of location IDs to load. None = all.

        Returns
        -------
        pd.DataFrame
            DataFrame following the schema defined in schema.py.
            Must contain all IDENTIFIER_COLS at minimum.
        """
        pass

    @abstractmethod
    def get_data_source(self) -> str:
        """Returns 'synthetic' or 'real'."""
        pass

    def validate_schema(self, df: pd.DataFrame) -> None:
        """
        Validates that the DataFrame contains required identifier columns.
        Raises ValueError if schema is violated.
        """
        missing = [c for c in IDENTIFIER_COLS if c not in df.columns]
        if missing:
            raise ValueError(
                f"DataFrame missing required identifier columns: {missing}. "
                f"Expected: {IDENTIFIER_COLS}"
            )

        # Validate lead_day range
        if "lead_day" in df.columns:
            invalid = df[(df["lead_day"] < 1) | (df["lead_day"] > 10)]
            if len(invalid) > 0:
                raise ValueError(
                    f"Found {len(invalid)} rows with lead_day outside [1, 10]"
                )

        # Validate data_source
        if "data_source" in df.columns:
            valid_sources = {DATA_SOURCE_SYNTHETIC, DATA_SOURCE_REAL}
            invalid_sources = set(df["data_source"].unique()) - valid_sources
            if invalid_sources:
                raise ValueError(
                    f"Invalid data_source values: {invalid_sources}. "
                    f"Must be one of: {valid_sources}"
                )
