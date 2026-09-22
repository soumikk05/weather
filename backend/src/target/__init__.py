"""
Target Formulation & Bust Definition Package
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Provides:
  - BustThresholdEngine: Primary location x season x lead 90th percentile threshold
  - Alternative bust definitions: IMD category miss, magnitude relative, extreme convective
  - Spatial displacement tolerance: Resolves the double-penalty problem for shifted rainbands
  - Stratification & sample size adequacy diagnostics (< 30 samples flagged)
"""

from src.target.bust_definition import (
    BustThresholdEngine,
    get_season_for_date_and_subdivision,
    compute_imd_category_miss,
    add_alternative_bust_targets,
)
from src.target.spatial_tolerance import (
    SUBDIVISION_ADJACENCY,
    get_subdivision_neighbors,
    compute_neighbourhood_displacement_metrics,
)
from src.target.stratification import (
    MIN_BUST_SAMPLE_SIZE,
    compute_stratified_bust_statistics,
    generate_comprehensive_stratification_report,
    format_markdown_stratification_table,
)

__all__ = [
    # Primary Bust Engine
    "BustThresholdEngine",
    "get_season_for_date_and_subdivision",
    "compute_imd_category_miss",
    "add_alternative_bust_targets",
    # Spatial Tolerance
    "SUBDIVISION_ADJACENCY",
    "get_subdivision_neighbors",
    "compute_neighbourhood_displacement_metrics",
    # Stratification & Diagnostics
    "MIN_BUST_SAMPLE_SIZE",
    "compute_stratified_bust_statistics",
    "generate_comprehensive_stratification_report",
    "format_markdown_stratification_table",
]
