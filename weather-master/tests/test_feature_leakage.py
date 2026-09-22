"""
Unit and Temporal Causality Leakage Tests for the 8 Feature Families
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.synthetic import NonCircularSyntheticGenerator
from src.feature_families import (
    BaseFeatureFamily,
    NWPStateEvolutionFamily,
    UncertaintyFamily,
    RecentErrorFamily,
    RunConsistencyFamily,
    SeasonalContextFamily,
    AnalogRegimeFamily,
    SpatialOceanLargeScaleFamily,
    StaticGeographyFamily,
    FeaturePipeline,
    ALL_FEATURE_FAMILIES,
)


@pytest.fixture
def sample_forecast_dataset() -> pd.DataFrame:
    """Generate a realistic multi-month sample dataset for feature testing."""
    gen = NonCircularSyntheticGenerator(random_seed=42)
    # Generate 60 days across 2 subdivisions with full schema
    df = gen.load(
        start_date="2024-06-01",
        end_date="2024-07-31",
        locations=["Konkan & Goa", "East Rajasthan"],
        compute_bust=True,
    )
    return df


def test_individual_feature_families(sample_forecast_dataset):
    """Verify each of the 8 feature families adheres to the BaseFeatureFamily contract."""
    df = sample_forecast_dataset

    families = [
        NWPStateEvolutionFamily(),
        UncertaintyFamily(),
        RecentErrorFamily(),
        RunConsistencyFamily(),
        SeasonalContextFamily(),
        AnalogRegimeFamily(),
        SpatialOceanLargeScaleFamily(),
        StaticGeographyFamily(),
    ]

    for fam in families:
        # Check properties
        assert fam.family_name in ALL_FEATURE_FAMILIES
        assert len(fam.feature_names) > 0

        # Fit & transform
        fam.fit(df)
        res = fam.transform(df)

        assert isinstance(res, pd.DataFrame)
        assert len(res) == len(df)
        assert list(res.columns) == fam.feature_names
        # Check no completely NaN or infinite columns
        for col in fam.feature_names:
            assert not res[col].isna().all(), f"Family {fam.family_name} produced all-NaN for {col}"
            assert not np.isinf(res[col].to_numpy(dtype=float, na_value=0.0)).any(), f"Infinite values in {col}"


def test_feature_pipeline_ablation(sample_forecast_dataset):
    """Verify FeaturePipeline extraction and drop-one / single-family ablation functionality."""
    df = sample_forecast_dataset
    pipe = FeaturePipeline()
    pipe.fit(df)

    # 1. Full extraction
    full_X = pipe.transform(df)
    expected_total_features = sum(len(pipe.families[f].feature_names) for f in ALL_FEATURE_FAMILIES)
    assert full_X.shape[1] == expected_total_features
    assert len(full_X) == len(df)

    # 2. Ablation: Drop uncertainty family
    drop_uncert_X = pipe.transform(df, drop_families=["uncertainty"])
    uncert_features = pipe.families["uncertainty"].feature_names
    for f in uncert_features:
        assert f not in drop_uncert_X.columns
    assert drop_uncert_X.shape[1] == expected_total_features - len(uncert_features)

    # 3. Ablation: Isolated family only
    only_geo_X = pipe.transform(df, only_families=["static_geography"])
    geo_features = pipe.families["static_geography"].feature_names
    assert list(only_geo_X.columns) == geo_features


def test_strict_temporal_causality_zero_leakage(sample_forecast_dataset):
    """
    STRICT ZERO-LEAKAGE CAUSALITY TEST:
    Verifies that features for an evaluation date T_eval are 100% IDENTICAL
    whether calculated on the full future dataset or a dataset strictly truncated
    at T_eval (zero lookahead).
    """
    df = sample_forecast_dataset.copy()
    unique_dates = sorted(pd.to_datetime(df["initialization_time"]).unique())

    # Pick an evaluation initialization date in the middle of the range
    eval_date_idx = len(unique_dates) // 2
    eval_date = unique_dates[eval_date_idx]

    pipe = FeaturePipeline()
    # Fit and transform on full dataset
    pipe.fit(df)
    full_transformed = pipe.transform(df)

    # Truncate dataset to strictly include only dates <= eval_date
    df_truncated = df[pd.to_datetime(df["initialization_time"]) <= eval_date].copy()

    pipe_truncated = FeaturePipeline()
    pipe_truncated.fit(df_truncated)
    trunc_transformed = pipe_truncated.transform(df_truncated)

    # Locate rows corresponding to eval_date in both transformations
    eval_mask_full = pd.to_datetime(df["initialization_time"]) == eval_date
    eval_mask_trunc = pd.to_datetime(df_truncated["initialization_time"]) == eval_date

    features_from_full = full_transformed[eval_mask_full].reset_index(drop=True)
    features_from_trunc = trunc_transformed[eval_mask_trunc].reset_index(drop=True)

    # Assert exact equality across all features (no leakage from future records)
    for col in features_from_full.columns:
        diff = np.abs(features_from_full[col].values - features_from_trunc[col].values)
        max_diff = np.nanmax(diff) if len(diff) > 0 else 0.0
        assert max_diff < 1e-4, (
            f"LEAKAGE DETECTED in feature '{col}'! "
            f"Value changed by {max_diff} when future records were removed."
        )
