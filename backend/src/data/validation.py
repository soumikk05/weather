"""
Data Validation Module
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Validates data quality: time alignment, missing values, unit consistency,
NWP model version drift detection, and schema compliance.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.data.schema import IDENTIFIER_COLS


@dataclass
class ValidationReport:
    """Results of a data validation pass."""
    total_rows: int = 0
    valid_rows: int = 0
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    column_stats: Dict[str, Dict] = field(default_factory=dict)
    model_version_changes: List[Dict] = field(default_factory=list)
    is_valid: bool = True

    def summary(self) -> str:
        lines = [
            f"Data Validation Report",
            f"  Total rows: {self.total_rows:,}",
            f"  Valid rows: {self.valid_rows:,}",
            f"  Issues: {len(self.issues)}",
            f"  Warnings: {len(self.warnings)}",
            f"  Status: {'PASS' if self.is_valid else 'FAIL'}",
        ]
        if self.issues:
            lines.append("  Critical Issues:")
            for issue in self.issues:
                lines.append(f"    ❌ {issue}")
        if self.warnings:
            lines.append("  Warnings:")
            for w in self.warnings[:10]:
                lines.append(f"    ⚠️ {w}")
            if len(self.warnings) > 10:
                lines.append(f"    ... and {len(self.warnings) - 10} more warnings")
        return "\n".join(lines)


def validate_dataframe(
    df: pd.DataFrame,
    expected_cols: Optional[List[str]] = None,
    check_time_alignment: bool = True,
    check_units: bool = True,
    check_model_drift: bool = True,
) -> ValidationReport:
    """
    Run comprehensive validation on a forecast verification DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Data to validate.
    expected_cols : list, optional
        Columns that must be present. Defaults to IDENTIFIER_COLS.
    check_time_alignment : bool
        Verify that valid_time = initialization_time + lead_day.
    check_units : bool
        Check that numerical columns are within physically plausible ranges.
    check_model_drift : bool
        Detect changes in model_version over time.

    Returns
    -------
    ValidationReport
    """
    report = ValidationReport(total_rows=len(df))

    if len(df) == 0:
        report.issues.append("DataFrame is empty")
        report.is_valid = False
        return report

    # --- 1. Schema check ---
    if expected_cols is None:
        expected_cols = IDENTIFIER_COLS
    missing_cols = [c for c in expected_cols if c not in df.columns]
    if missing_cols:
        report.issues.append(f"Missing required columns: {missing_cols}")
        report.is_valid = False

    # --- 2. Missing data ---
    for col in df.columns:
        n_null = int(df[col].isnull().sum())
        n_total = len(df)
        pct = n_null / n_total * 100
        report.column_stats[col] = {
            "null_count": n_null,
            "null_pct": round(pct, 2),
            "dtype": str(df[col].dtype),
        }
        if n_null > 0 and col in IDENTIFIER_COLS:
            report.issues.append(f"NULL values in required column '{col}': {n_null} ({pct:.1f}%)")
            report.is_valid = False
        elif pct > 50:
            report.warnings.append(f"Column '{col}' is >50% null ({pct:.1f}%)")

    # --- 3. Time alignment ---
    if check_time_alignment and "initialization_time" in df.columns and "valid_time" in df.columns and "lead_day" in df.columns:
        try:
            init_dt = pd.to_datetime(df["initialization_time"])
            valid_dt = pd.to_datetime(df["valid_time"])
            expected_valid = init_dt + pd.to_timedelta(df["lead_day"], unit="D")
            misaligned = (valid_dt.dt.date != expected_valid.dt.date).sum()
            if misaligned > 0:
                report.warnings.append(
                    f"Time alignment: {misaligned} rows where valid_time != initialization_time + lead_day"
                )
        except Exception as e:
            report.warnings.append(f"Could not check time alignment: {e}")

    # --- 4. Lead day range ---
    if "lead_day" in df.columns:
        invalid_leads = df[(df["lead_day"] < 1) | (df["lead_day"] > 10)]
        if len(invalid_leads) > 0:
            report.issues.append(f"lead_day outside [1,10]: {len(invalid_leads)} rows")
            report.is_valid = False

    # --- 5. Unit consistency / physical plausibility ---
    if check_units:
        unit_checks = {
            "fcst_rainfall_mm": (0, 500, "mm"),
            "obs_rainfall_mm": (0, 500, "mm"),
            "fcst_temp_2m_c": (-30, 55, "°C"),
            "fcst_mslp_hpa": (950, 1060, "hPa"),
            "ens_spread_rainfall": (0, 100, "mm"),
            "fcst_cape_jkg": (0, 8000, "J/kg"),
            "elevation_m": (-50, 9000, "m"),
            "terrain_complexity": (0, 1, "index"),
        }
        for col, (lo, hi, unit) in unit_checks.items():
            if col in df.columns:
                below = (df[col].dropna() < lo).sum()
                above = (df[col].dropna() > hi).sum()
                if below > 0:
                    report.warnings.append(
                        f"'{col}' has {below} values below {lo} {unit}"
                    )
                if above > 0:
                    report.warnings.append(
                        f"'{col}' has {above} values above {hi} {unit}"
                    )

    # --- 6. Model version drift ---
    if check_model_drift and "model_version" in df.columns and "initialization_time" in df.columns:
        try:
            version_dates = (
                df.groupby("model_version")["initialization_time"]
                .agg(["min", "max"])
                .reset_index()
            )
            if len(version_dates) > 1:
                report.model_version_changes = version_dates.to_dict("records")
                report.warnings.append(
                    f"Multiple model versions detected: {list(version_dates['model_version'])}. "
                    f"Check for systematic performance changes around version transitions."
                )
        except Exception:
            pass

    # --- 7. Duplicate check ---
    if all(c in df.columns for c in ["initialization_time", "valid_time", "location_id", "lead_day"]):
        dup_count = df.duplicated(
            subset=["initialization_time", "valid_time", "location_id", "lead_day"]
        ).sum()
        if dup_count > 0:
            report.warnings.append(f"Found {dup_count} duplicate (init_time, valid_time, location, lead) rows")

    report.valid_rows = report.total_rows - sum(
        1 for issue in report.issues if "NULL" in issue
    )

    return report


def check_bust_rate_sanity(
    df: pd.DataFrame,
    min_rate: float = 0.03,
    max_rate: float = 0.25,
    min_samples_per_group: int = 30,
) -> List[str]:
    """
    Check that bust rates are within plausible ranges.

    Returns list of warning strings.
    """
    warnings = []

    if "is_bust" not in df.columns:
        return ["'is_bust' column not found — cannot check bust rates"]

    overall_rate = df["is_bust"].mean()
    if overall_rate < min_rate:
        warnings.append(
            f"Overall bust rate ({overall_rate*100:.1f}%) is very low (<{min_rate*100}%). "
            f"Check if thresholds are too high."
        )
    if overall_rate > max_rate:
        warnings.append(
            f"Overall bust rate ({overall_rate*100:.1f}%) is very high (>{max_rate*100}%). "
            f"Check if thresholds are too low or data has circularity."
        )

    # Check per lead day
    if "lead_day" in df.columns:
        for ld in sorted(df["lead_day"].unique()):
            sub = df[df["lead_day"] == ld]
            rate = sub["is_bust"].mean()
            n_bust = sub["is_bust"].sum()
            if n_bust < min_samples_per_group:
                warnings.append(
                    f"Day {ld}: only {n_bust} busts (< {min_samples_per_group} minimum). "
                    f"Results may be unreliable."
                )

    # Check per location
    if "location_id" in df.columns:
        for loc, grp in df.groupby("location_id"):
            rate = grp["is_bust"].mean()
            if rate > 0.5:
                warnings.append(
                    f"Location '{loc}' has {rate*100:.0f}% bust rate — suspiciously high. "
                    f"Check for data issues or threshold problems."
                )

    return warnings
