"""
Base Feature Family Contract
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Abstract base class for the 8 modular feature engineering families.
Each family encapsulates a distinct physical or statistical domain.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd


class BaseFeatureFamily(ABC):
    """
    Abstract interface for a meteorological feature family.

    Key invariants:
    - `family_name` uniquely identifies the family.
    - `transform(df)` must ONLY use data available at `initialization_time`.
    - No future information (e.g. valid-time truth) may ever be used.
    """

    @property
    @abstractmethod
    def family_name(self) -> str:
        """Returns canonical name of feature family (e.g. 'uncertainty')."""
        pass

    @property
    @abstractmethod
    def feature_names(self) -> List[str]:
        """Returns list of column names produced by this family."""
        pass

    def fit(self, df: pd.DataFrame) -> "BaseFeatureFamily":
        """Fit any parameters on historical training data (default is no-op)."""
        return self

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract features and return DataFrame with engineered columns added.

        Parameters
        ----------
        df : pd.DataFrame
            Input verification dataframe.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the engineered feature columns.
        """
        pass
