"""
Feature Families Package
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Provides:
  - BaseFeatureFamily: Abstract contract
  - 8 Parallel Feature Families:
      1. NWPStateEvolutionFamily ('nwp_state_evolution')
      2. UncertaintyFamily ('uncertainty')
      3. RecentErrorFamily ('recent_error')
      4. RunConsistencyFamily ('run_consistency')
      5. SeasonalContextFamily ('seasonal_context')
      6. AnalogRegimeFamily ('analog_regime')
      7. SpatialOceanLargeScaleFamily ('spatial_ocean_large_scale')
      8. StaticGeographyFamily ('static_geography')
  - FeaturePipeline: Orchestrator supporting systematic family ablation
"""

from src.feature_families.base import BaseFeatureFamily
from src.feature_families.nwp_state_evolution import NWPStateEvolutionFamily
from src.feature_families.uncertainty import UncertaintyFamily
from src.feature_families.recent_error import RecentErrorFamily
from src.feature_families.run_consistency import RunConsistencyFamily
from src.feature_families.seasonal_context import SeasonalContextFamily
from src.feature_families.analog_regime import AnalogRegimeFamily
from src.feature_families.spatial_ocean_large_scale import SpatialOceanLargeScaleFamily
from src.feature_families.static_geography import StaticGeographyFamily
from src.feature_families.pipeline import (
    FeaturePipeline,
    ALL_FEATURE_FAMILIES,
)

__all__ = [
    "BaseFeatureFamily",
    "NWPStateEvolutionFamily",
    "UncertaintyFamily",
    "RecentErrorFamily",
    "RunConsistencyFamily",
    "SeasonalContextFamily",
    "AnalogRegimeFamily",
    "SpatialOceanLargeScaleFamily",
    "StaticGeographyFamily",
    "FeaturePipeline",
    "ALL_FEATURE_FAMILIES",
]
