"""
Modular Feature Pipeline & Ablation Orchestrator
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Manages and coordinates the 8 modular feature engineering families:
1. nwp_state_evolution
2. uncertainty
3. recent_error
4. run_consistency
5. seasonal_context
6. analog_regime
7. spatial_ocean_large_scale
8. static_geography

Supports systematic ablation testing:
- Drop single family
- Evaluate isolated individual families
- Additive forward ablation
"""

from typing import Dict, List, Optional, Set
import pandas as pd

from src.feature_families.base import BaseFeatureFamily
from src.feature_families.nwp_state_evolution import NWPStateEvolutionFamily
from src.feature_families.uncertainty import UncertaintyFamily
from src.feature_families.recent_error import RecentErrorFamily
from src.feature_families.run_consistency import RunConsistencyFamily
from src.feature_families.seasonal_context import SeasonalContextFamily
from src.feature_families.analog_regime import AnalogRegimeFamily
from src.feature_families.spatial_ocean_large_scale import SpatialOceanLargeScaleFamily
from src.feature_families.static_geography import StaticGeographyFamily


ALL_FEATURE_FAMILIES = [
    "nwp_state_evolution",
    "uncertainty",
    "recent_error",
    "run_consistency",
    "seasonal_context",
    "analog_regime",
    "spatial_ocean_large_scale",
    "static_geography",
]


class FeaturePipeline:
    """
    Coordinates extraction and ablation across all 8 feature families.
    """

    def __init__(self, selected_families: Optional[List[str]] = None):
        self.families: Dict[str, BaseFeatureFamily] = {
            "nwp_state_evolution": NWPStateEvolutionFamily(),
            "uncertainty": UncertaintyFamily(),
            "recent_error": RecentErrorFamily(),
            "run_consistency": RunConsistencyFamily(),
            "seasonal_context": SeasonalContextFamily(),
            "analog_regime": AnalogRegimeFamily(),
            "spatial_ocean_large_scale": SpatialOceanLargeScaleFamily(),
            "static_geography": StaticGeographyFamily(),
        }

        if selected_families:
            invalid = set(selected_families) - set(ALL_FEATURE_FAMILIES)
            if invalid:
                raise ValueError(f"Unknown feature families requested: {invalid}")
            self.active_family_names = list(selected_families)
        else:
            self.active_family_names = list(ALL_FEATURE_FAMILIES)

    def get_family_features_map(self) -> Dict[str, List[str]]:
        """Return dictionary mapping family name to list of its feature columns."""
        return {
            name: self.families[name].feature_names
            for name in self.active_family_names
        }

    def get_feature_names(
        self,
        drop_families: Optional[List[str]] = None,
        only_families: Optional[List[str]] = None,
    ) -> List[str]:
        """Return flattened list of feature column names for active or ablated families."""
        target_families = self._resolve_families(drop_families, only_families)
        cols = []
        for name in target_families:
            cols.extend(self.families[name].feature_names)
        return cols

    def fit(self, train_df: pd.DataFrame) -> "FeaturePipeline":
        """Fit stateful feature extractors (e.g. analog search index) on training data."""
        for name in self.active_family_names:
            self.families[name].fit(train_df)
        return self

    def transform(
        self,
        df: pd.DataFrame,
        drop_families: Optional[List[str]] = None,
        only_families: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Extract features across all requested families and return single combined DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            Input verification dataframe.
        drop_families : list of str, optional
            Families to exclude (e.g. for ablation).
        only_families : list of str, optional
            Only include these specific families.
        """
        target_families = self._resolve_families(drop_families, only_families)
        extracted_dfs = []

        for name in target_families:
            family_df = self.families[name].transform(df)
            extracted_dfs.append(family_df)

        if not extracted_dfs:
            return pd.DataFrame(index=df.index)

        combined = pd.concat(extracted_dfs, axis=1)
        return combined

    def fit_transform(self, train_df: pd.DataFrame) -> pd.DataFrame:
        """Fit on train_df and transform in one step."""
        return self.fit(train_df).transform(train_df)

    def _resolve_families(
        self,
        drop_families: Optional[List[str]],
        only_families: Optional[List[str]],
    ) -> List[str]:
        """Resolve which families to execute based on drop/only filters."""
        if only_families is not None:
            return [f for f in self.active_family_names if f in only_families]
        if drop_families is not None:
            return [f for f in self.active_family_names if f not in drop_families]
        return self.active_family_names
