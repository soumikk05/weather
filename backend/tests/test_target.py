"""
Unit and Integration Tests for Stage 2 Target Formulations
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.synthetic import NonCircularSyntheticGenerator
from src.target.bust_definition import (
    BustThresholdEngine,
    add_alternative_bust_targets,
    compute_imd_category_miss,
    get_season_for_date_and_subdivision,
)
from src.target.spatial_tolerance import (
    SUBDIVISION_ADJACENCY,
    get_subdivision_neighbors,
    compute_neighbourhood_displacement_metrics,
)
from src.target.stratification import (
    compute_stratified_bust_statistics,
    generate_comprehensive_stratification_report,
    MIN_BUST_SAMPLE_SIZE,
)


def test_zero_leakage_threshold_engine():
    """
    Test zero-leakage invariant:
    Thresholds must be computed strictly on training data, and test errors
    must have ZERO impact on fitted thresholds.
    """
    gen = NonCircularSyntheticGenerator(random_seed=42)
    df = gen.load(start_date="2024-06-01", end_date="2024-07-31", locations=["Konkan & Goa"], compute_bust=False)

    train_size = int(len(df) * 0.70)
    train_df = df.iloc[:train_size].copy()
    test_df = df.iloc[train_size:].copy()

    engine = BustThresholdEngine(percentile=90.0, min_threshold_mm=5.0)
    engine.fit(train_df)

    stored_thresholds = engine.thresholds_df_.copy()

    # Corrupt test set with massive artificial errors
    test_df_corrupted = test_df.copy()
    test_df_corrupted["abs_error_mm"] = test_df_corrupted["abs_error_mm"] + 500.0

    # Transform both normal and corrupted test sets
    out_normal = engine.transform(test_df)
    out_corrupted = engine.transform(test_df_corrupted)

    # Thresholds applied must be identical despite extreme test corruption
    pd.testing.assert_series_equal(
        out_normal["bust_threshold_mm"],
        out_corrupted["bust_threshold_mm"],
        check_names=True,
    )
    # Stored training thresholds must remain unchanged
    pd.testing.assert_frame_equal(engine.thresholds_df_, stored_thresholds)


def test_alternative_bust_targets():
    """Verify IMD category misses, magnitude-relative, and extreme bust labels."""
    df = pd.DataFrame({
        "fcst_rainfall_mm": [2.0, 50.0, 150.0, 5.0],
        "obs_rainfall_mm": [80.0, 48.0, 5.0, 160.0],
    })
    enriched = add_alternative_bust_targets(df, extreme_thresh_mm=115.5)

    # Row 0: fcst=2 (no_rain), obs=80 (heavy) -> 3 category diff -> is_category_miss = 1
    assert enriched.loc[0, "is_category_miss"] == 1

    # Row 1: fcst=50 (mod), obs=48 (mod) -> 0 category diff -> is_category_miss = 0
    assert enriched.loc[1, "is_category_miss"] == 0

    # Row 2: fcst=150 (very heavy), obs=5 (light) -> extreme false alarm
    assert enriched.loc[2, "is_extreme_false_alarm"] == 1
    assert enriched.loc[2, "is_extreme_miss"] == 0

    # Row 3: fcst=5 (light), obs=160 (very heavy) -> extreme miss
    assert enriched.loc[3, "is_extreme_miss"] == 1
    assert enriched.loc[3, "is_extreme_false_alarm"] == 0


def test_spatial_neighbourhood_tolerance():
    """Test spatial displacement tolerance resolving the double-penalty problem."""
    # Verify adjacency graph
    neighbors_konkan = get_subdivision_neighbors("Konkan & Goa")
    assert "Madhya Maharashtra" in neighbors_konkan
    assert "Coastal Karnataka" in neighbors_konkan

    # Synthetic scenario: Rainband predicted in Konkan (60mm) but hits Madhya Maharashtra (65mm)
    # Konkan observed 2mm, Madhya Maharashtra forecast was 10mm
    events = pd.DataFrame([
        {
            "valid_time": "2024-07-15",
            "location_id": "Konkan & Goa",
            "lead_day": 3,
            "fcst_rainfall_mm": 60.0,
            "obs_rainfall_mm": 2.0,
            "is_bust": 1,
        },
        {
            "valid_time": "2024-07-15",
            "location_id": "Madhya Maharashtra",
            "lead_day": 3,
            "fcst_rainfall_mm": 10.0,
            "obs_rainfall_mm": 65.0,
            "is_bust": 1,
        },
    ])

    out = compute_neighbourhood_displacement_metrics(events)

    # Konkan forecast of 60mm was observed next door (65mm in Madhya Maharashtra)
    konkan_row = out[out["location_id"] == "Konkan & Goa"].iloc[0]
    assert konkan_row["is_displacement_candidate"] == 1
    # Neighbourhood bust should be relaxed to 0
    assert konkan_row["is_neighbourhood_bust"] == 0


def test_stratified_bust_diagnostics_and_sample_adequacy():
    """Test stratification and < 30 bust sample adequacy flagging."""
    # Create dataset where one strata has 40 busts (sufficient) and another has 5 busts (insufficient)
    df_sufficient = pd.DataFrame({
        "lead_day": [1] * 200,
        "season": ["sw_monsoon"] * 200,
        "location_id": ["Konkan & Goa"] * 200,
        "is_bust": [1] * 40 + [0] * 160,
        "forecast_error_mm": [25.0] * 40 + [2.0] * 160,
        "abs_error_mm": [25.0] * 40 + [2.0] * 160,
        "bust_threshold_mm": [15.0] * 200,
    })
    df_insufficient = pd.DataFrame({
        "lead_day": [10] * 100,
        "season": ["winter"] * 100,
        "location_id": ["West Rajasthan"] * 100,
        "is_bust": [1] * 5 + [0] * 95,
        "forecast_error_mm": [12.0] * 5 + [1.0] * 95,
        "abs_error_mm": [12.0] * 5 + [1.0] * 95,
        "bust_threshold_mm": [10.0] * 100,
    })
    combined = pd.concat([df_sufficient, df_insufficient], ignore_index=True)

    stats = compute_stratified_bust_statistics(combined, group_cols=["lead_day", "season"])

    row_suff = stats[(stats["lead_day"] == 1) & (stats["season"] == "sw_monsoon")].iloc[0]
    row_insuff = stats[(stats["lead_day"] == 10) & (stats["season"] == "winter")].iloc[0]

    assert row_suff["is_sufficient"] == True
    assert row_suff["sample_status"] == "SUFFICIENT"
    assert row_suff["bust_count"] == 40

    assert row_insuff["is_sufficient"] == False
    assert "INSUFFICIENT" in row_insuff["sample_status"]
    assert row_insuff["bust_count"] == 5
