"""
Stratified Bust Diagnostics & Sample Adequacy Reporting
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Computes granular bust rate breakdowns across:
1. Forecast lead day (Day 1 through Day 10)
2. Meteorological season (SW Monsoon, Post-Monsoon, Winter, Pre-Monsoon)
3. Geographic subdivision / terrain type
4. Synoptic weather regimes

Enforces scientific sample adequacy:
Subsets with < 30 positive bust events are flagged as 'INSUFFICIENT_SAMPLE_SIZE'
to prevent drawing statistically invalid conclusions on tiny tail-risk strata.
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd


MIN_BUST_SAMPLE_SIZE = 30  # Standard scientific threshold for tail-risk evaluation


def compute_stratified_bust_statistics(
    df: pd.DataFrame,
    group_cols: List[str],
    bust_col: str = "is_bust",
    error_col: str = "forecast_error_mm",
    abs_error_col: str = "abs_error_mm",
    threshold_col: str = "bust_threshold_mm",
) -> pd.DataFrame:
    """
    Compute aggregate sample counts, bust rates, and error statistics for arbitrary groups.

    Parameters
    ----------
    df : pd.DataFrame
        Verification dataframe with targets.
    group_cols : list of str
        Columns to group by (e.g. ['lead_day', 'season']).
    """
    # Ensure columns exist
    for c in group_cols:
        if c not in df.columns:
            raise KeyError(f"Group column '{c}' not found in DataFrame.")

    grouped = df.groupby(group_cols)

    agg_dict = {
        bust_col: ["count", "sum", "mean"],
    }
    if abs_error_col in df.columns:
        agg_dict[abs_error_col] = ["mean", "median"]
    if error_col in df.columns:
        agg_dict[error_col] = ["mean"]  # Mean bias
    if threshold_col in df.columns:
        agg_dict[threshold_col] = ["median"]

    res = grouped.agg(agg_dict)

    # Flatten multi-level column index
    res.columns = [
        f"{col}_{stat}" if stat != "count" else "total_records"
        for col, stat in res.columns
    ]
    res = res.reset_index()

    # Standardize column naming
    rename_map = {
        f"{bust_col}_sum": "bust_count",
        f"{bust_col}_mean": "bust_rate",
        f"{abs_error_col}_mean": "mean_abs_error_mm",
        f"{abs_error_col}_median": "median_abs_error_mm",
        f"{error_col}_mean": "mean_bias_mm",
        f"{threshold_col}_median": "median_bust_threshold_mm",
    }
    res = res.rename(columns={k: v for k, v in rename_map.items() if k in res.columns})

    # Add sample adequacy flags
    res["is_sufficient"] = res["bust_count"] >= MIN_BUST_SAMPLE_SIZE
    res["sample_status"] = res["is_sufficient"].apply(
        lambda x: "SUFFICIENT" if x else "INSUFFICIENT_SAMPLE_SIZE (<30 busts)"
    )

    # Round numeric fields
    if "bust_rate" in res.columns:
        res["bust_rate_pct"] = (res["bust_rate"] * 100).round(2)
    for col in ["mean_abs_error_mm", "median_abs_error_mm", "mean_bias_mm", "median_bust_threshold_mm"]:
        if col in res.columns:
            res[col] = res[col].round(2)

    return res


def generate_comprehensive_stratification_report(
    df: pd.DataFrame,
    bust_col: str = "is_bust",
) -> Dict[str, pd.DataFrame]:
    """
    Generate all standard operational stratification slices:
    - By lead day (1 to 10)
    - By season
    - By subdivision
    - By lead day × season
    - By synoptic regime (if present)
    """
    report = {}

    # 1. By lead day
    if "lead_day" in df.columns:
        report["by_lead_day"] = compute_stratified_bust_statistics(
            df, group_cols=["lead_day"], bust_col=bust_col
        )

    # 2. By season
    if "season" in df.columns:
        report["by_season"] = compute_stratified_bust_statistics(
            df, group_cols=["season"], bust_col=bust_col
        )

    # 3. By subdivision
    if "location_id" in df.columns:
        report["by_location"] = compute_stratified_bust_statistics(
            df, group_cols=["location_id"], bust_col=bust_col
        )

    # 4. By lead day x season
    if "lead_day" in df.columns and "season" in df.columns:
        report["by_lead_and_season"] = compute_stratified_bust_statistics(
            df, group_cols=["lead_day", "season"], bust_col=bust_col
        )

    # 5. By synoptic regime
    if "synoptic_regime" in df.columns:
        report["by_regime"] = compute_stratified_bust_statistics(
            df, group_cols=["synoptic_regime"], bust_col=bust_col
        )

    return report


def format_markdown_stratification_table(stats_df: pd.DataFrame, title: str) -> str:
    """Format a stratification DataFrame as a readable Markdown table with status badges."""
    lines = [f"### {title}\n"]
    lines.append(
        "| Group | Total Records | Bust Count | Bust Rate (%) | MAE (mm) | Bias (mm) | Sample Status |"
    )
    lines.append(
        "|:---|---:|---:|---:|---:|---:|:---|"
    )

    group_cols = [
        c for c in stats_df.columns
        if c not in [
            "total_records", "bust_count", "bust_rate", "bust_rate_pct",
            "mean_abs_error_mm", "median_abs_error_mm", "mean_bias_mm",
            "median_bust_threshold_mm", "is_sufficient", "sample_status"
        ]
    ]

    for _, row in stats_df.iterrows():
        group_label = " - ".join(str(row[c]) for c in group_cols)
        tot = f"{int(row['total_records']):,}"
        busts = f"{int(row['bust_count']):,}"
        rate = f"{row.get('bust_rate_pct', 0.0):.1f}%"
        mae = f"{row.get('mean_abs_error_mm', 0.0):.1f}"
        bias = f"{row.get('mean_bias_mm', 0.0):+.1f}"
        status = "✅ OK" if row["is_sufficient"] else "⚠️ < 30 busts"

        lines.append(
            f"| {group_label} | {tot} | {busts} | {rate} | {mae} | {bias} | {status} |"
        )

    return "\n".join(lines)
