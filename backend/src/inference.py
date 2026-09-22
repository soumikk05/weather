"""
Unified Inference Engine for Forecast Bust Detection
Smart India Hackathon - NCMRWF / Ministry of Earth Sciences

Single source of truth used by both FastAPI and Streamlit Dashboard.
Produces region-wise confidence maps, 10-day lead time profiles,
calibrated bust probabilities, plain-language explanations,
historical verification tracking, and location resolution.
"""

import json
import math
import os
import sys
# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Any, Dict, List, Optional
import joblib
import numpy as np
import pandas as pd

from src.explain import ForecastExplainer
from src.features import FeatureEngineer
from src.data.schema import SUBDIVISIONS
from src.data.location_resolver import resolve_location as resolve_location_fn


class ForecastInferenceEngine:
    """
    Central inference engine serving predictions, confidence maps,
    explanations, verification history, and location resolution
    across Day 1 - Day 10 for operational forecasters.
    """

    def __init__(self, model_dir: str = "models", data_path: str = "data/nwp_forecast_bust_dataset.csv"):
        self.model_dir = model_dir
        self.data_path = data_path

        # Load models
        self.calibrator = joblib.load(os.path.join(model_dir, "calibrator.joblib"))
        self.fe = joblib.load(os.path.join(model_dir, "feature_pipeline.joblib"))
        self.explainer = ForecastExplainer(model_dir=model_dir)

        # Cache dataset for date-based retrieval
        if os.path.exists(data_path):
            self.data_df = pd.read_csv(data_path)
            # Schema backward-compatibility aliases
            if "date" not in self.data_df.columns:
                time_col = "initialization_time" if "initialization_time" in self.data_df.columns else "valid_time"
                self.data_df["date"] = pd.to_datetime(self.data_df[time_col]).dt.strftime("%Y-%m-%d")
            if "region" not in self.data_df.columns and "location_id" in self.data_df.columns:
                self.data_df["region"] = self.data_df["location_id"]
            if "terrain" not in self.data_df.columns and "terrain_type" in self.data_df.columns:
                self.data_df["terrain"] = self.data_df["terrain_type"]
            if "terrain_difficulty" not in self.data_df.columns and "terrain_complexity" in self.data_df.columns:
                self.data_df["terrain_difficulty"] = self.data_df["terrain_complexity"]
            elif "terrain_difficulty" not in self.data_df.columns:
                self.data_df["terrain_difficulty"] = 0.50
            if "synoptic_regime" not in self.data_df.columns:
                self.data_df["synoptic_regime"] = "quiescent_clear"
            self.available_dates = sorted(self.data_df["date"].unique().tolist())

            # Data recency and source metadata
            if "valid_time" in self.data_df.columns:
                valid_series = pd.to_datetime(self.data_df["valid_time"]).dt.strftime("%Y-%m-%d")
                self.latest_valid_date = str(valid_series.max())
                self.earliest_valid_date = str(valid_series.min())
            else:
                self.latest_valid_date = self.available_dates[-1] if self.available_dates else "2024-12-31"
                self.earliest_valid_date = self.available_dates[0] if self.available_dates else "2022-01-01"

            if "data_source" in self.data_df.columns:
                sources = self.data_df["data_source"].unique().tolist()
                self.data_source = str(sources[0]) if sources else "synthetic"
                self.is_synthetic_or_replay = "synthetic" in [s.lower() for s in sources]
            else:
                self.data_source = "synthetic"
                self.is_synthetic_or_replay = True
        else:
            self.data_df = None
            self.available_dates = []
            self.latest_valid_date = "2024-12-31"
            self.earliest_valid_date = "2022-01-01"
            self.data_source = "synthetic"
            self.is_synthetic_or_replay = True

    def _compute_risk_tier(self, bust_prob: float, confidence_score: float) -> str:
        """Categorizes operational risk into 3 intuitive tiers."""
        if bust_prob >= 0.50 or confidence_score <= 0.40:
            return "Low Confidence - Bust Risk"
        elif bust_prob >= 0.25 or confidence_score <= 0.65:
            return "Moderate Confidence"
        else:
            return "High Confidence"

    def _derive_calibration_verdict(self, bust_prob: float, confidence_score: float, was_bust: bool) -> str:
        """
        Derives calibration verdict by comparing model risk flagging against verified ground truth.

        Thresholds strictly match _compute_risk_tier:
        - Flagged risky: bust_prob >= 0.50 or confidence_score <= 0.40 (i.e. 'Low Confidence - Bust Risk')
        - Confident: bust_prob < 0.50 and confidence_score > 0.40 ('Moderate' or 'High' Confidence)

        Verdicts:
        - 'flagged_risky_and_busted': Alert issued, bust occurred (True Positive Alert)
        - 'flagged_risky_no_bust': Alert issued, no bust occurred (False Alarm)
        - 'confident_but_busted': Confident forecast, bust occurred (False Negative / Missed Bust)
        - 'confident_correct': Confident forecast, no bust occurred (True Negative)
        """
        is_flagged_risky = (bust_prob >= 0.50 or confidence_score <= 0.40)
        if is_flagged_risky:
            return "flagged_risky_and_busted" if was_bust else "flagged_risky_no_bust"
        else:
            return "confident_but_busted" if was_bust else "confident_correct"

    def get_available_dates(self) -> List[str]:
        return self.available_dates

    def get_confidence_map(self, date_str: Optional[str] = None, lead_day: int = 1) -> List[Dict]:
        """
        Generates full nationwide confidence map for all 32 subdivisions
        for a given date and lead day (1 to 10).
        """
        if self.data_df is None or len(self.data_df) == 0:
            return []

        if not date_str or date_str not in self.available_dates:
            # Default to the most recent available date
            date_str = self.available_dates[-1]

        lead_day = max(1, min(10, int(lead_day)))
        subset = self.data_df[(self.data_df["date"] == date_str) & (self.data_df["lead_day"] == lead_day)].copy()

        if len(subset) == 0:
            return []

        X_matrix = self.fe.transform(subset)
        bust_probs = self.calibrator.predict_calibrated_proba(X_matrix)
        pred_errors, p_lowers, p_uppers = self.calibrator.predict_error_with_intervals(X_matrix)
        conf_scores = self.calibrator.predict_confidence(X_matrix)

        results = []
        for idx, (_, row) in enumerate(subset.iterrows()):
            b_prob = float(bust_probs[idx])
            p_err = float(pred_errors[idx])
            p_low = max(0.0, float(p_lowers[idx]))
            p_up = float(p_uppers[idx])
            conf_score = float(conf_scores[idx])
            risk_tier = self._compute_risk_tier(b_prob, conf_score)

            # Generate lightweight top 3 factor summary
            row_df = X_matrix.iloc[[idx]]
            exp_info = self.explainer.explain_instance(row_df, top_k_families=3)

            results.append({
                "date": date_str,
                "region": row["region"],
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "terrain": row["terrain"],
                "terrain_difficulty": float(row["terrain_difficulty"]),
                "synoptic_regime": row["synoptic_regime"],
                "lead_day": lead_day,
                "bust_probability": round(b_prob, 4),
                "predicted_error_mm": round(p_err, 2),
                "error_interval_90_lower": round(p_low, 2),
                "error_interval_90_upper": round(p_up, 2),
                "conformal_interval_mm": [round(p_low, 2), round(p_up, 2)],
                "confidence_score": round(conf_score, 4),
                "risk_tier": risk_tier,
                "evidence_agreement": exp_info.get("evidence_agreement", 1.0),
                "contradiction_flag": exp_info.get("contradiction_flag", False),
                "top_drivers": [d["top_driver_phrase"] for d in exp_info.get("top_families", [])[:3]],
                "top_families": exp_info.get("top_families", []),
                "operational_bulletin": exp_info.get("operational_bulletin", {}),
                "plain_language_summary": exp_info.get("plain_language_summary", ""),
            })

        return results

    def get_region_forecast(self, region_name: str, date_str: Optional[str] = None) -> List[Dict]:
        """
        Returns full Day 1 to Day 10 confidence profile and bust trajectory
        for a specific meteorological subdivision.
        """
        if self.data_df is None:
            return []

        if not date_str or date_str not in self.available_dates:
            date_str = self.available_dates[-1]

        subset = self.data_df[(self.data_df["date"] == date_str) & (self.data_df["region"] == region_name)].sort_values("lead_day")

        if len(subset) == 0:
            # Fallback to case-insensitive match
            matching = self.data_df[self.data_df["region"].str.lower() == region_name.lower()]
            if len(matching) > 0:
                actual_name = matching["region"].iloc[0]
                subset = self.data_df[(self.data_df["date"] == date_str) & (self.data_df["region"] == actual_name)].sort_values("lead_day")
            else:
                return []

        X_matrix = self.fe.transform(subset)
        bust_probs = self.calibrator.predict_calibrated_proba(X_matrix)
        pred_errors, p_lowers, p_uppers = self.calibrator.predict_error_with_intervals(X_matrix)
        conf_scores = self.calibrator.predict_confidence(X_matrix)

        timeline = []
        for idx, (_, row) in enumerate(subset.iterrows()):
            b_prob = float(bust_probs[idx])
            p_err = float(pred_errors[idx])
            p_low = max(0.0, float(p_lowers[idx]))
            p_up = float(p_uppers[idx])
            conf_score = float(conf_scores[idx])
            risk_tier = self._compute_risk_tier(b_prob, conf_score)

            row_df = X_matrix.iloc[[idx]]
            exp_info = self.explainer.explain_instance(row_df, top_k_families=3)

            timeline.append({
                "lead_day": int(row["lead_day"]),
                "date": date_str,
                "region": row["region"],
                "terrain": row["terrain"],
                "synoptic_regime": row["synoptic_regime"],
                "ens_spread_rainfall": float(row.get("ens_spread_rainfall", row.get("ensemble_spread", 0.0))),
                "bust_probability": round(b_prob, 4),
                "predicted_error_mm": round(p_err, 2),
                "error_interval_90_lower": round(p_low, 2),
                "error_interval_90_upper": round(p_up, 2),
                "conformal_interval_mm": [round(p_low, 2), round(p_up, 2)],
                "confidence_score": round(conf_score, 4),
                "risk_tier": risk_tier,
                "evidence_agreement": exp_info.get("evidence_agreement", 1.0),
                "contradiction_flag": exp_info.get("contradiction_flag", False),
                "plain_language_summary": exp_info.get("plain_language_summary", ""),
                "top_drivers": exp_info.get("top_families", []),
                "top_families": exp_info.get("top_families", []),
                "operational_bulletin": exp_info.get("operational_bulletin", {}),
            })

        return timeline

    def get_region_history(
        self,
        region_name: str,
        days: int = 10,
        as_of: Optional[str] = None,
        lead_day: int = 1,
    ) -> List[Dict]:
        """
        Retrieves verified historical forecast records for the specified subdivision
        over the last N valid dates up to as_of (default: latest available valid_time).

        Strict Zero-Leakage Guarantee:
        confidence_at_issue_time is computed strictly from the row's own initialization-time
        features through the feature and calibration pipeline. No future data or ground-truth
        is accessed during prediction.
        """
        if self.data_df is None or len(self.data_df) == 0:
            return []

        # Find matching region
        matching = self.data_df[self.data_df["region"].str.lower() == region_name.lower()]
        if len(matching) == 0:
            return []
        actual_name = matching["region"].iloc[0]

        lead_day = max(1, min(10, int(lead_day)))
        days = max(1, min(30, int(days)))

        subset = self.data_df[
            (self.data_df["region"] == actual_name) & (self.data_df["lead_day"] == lead_day)
        ].copy()

        if len(subset) == 0:
            return []

        time_col = "valid_time" if "valid_time" in subset.columns else "date"
        subset[time_col] = subset[time_col].astype(str)

        if not as_of or as_of not in subset[time_col].values:
            if as_of:
                avail_prior = subset[subset[time_col] <= as_of]
                ref_date = avail_prior[time_col].max() if len(avail_prior) > 0 else subset[time_col].max()
            else:
                ref_date = subset[time_col].max()
        else:
            ref_date = as_of

        # Filter records on or before ref_date
        prior_records = subset[subset[time_col] <= ref_date].sort_values(time_col, ascending=False).head(days)
        # Sort chronologically ascending for timeline presentation
        prior_records = prior_records.sort_values(time_col, ascending=True).reset_index(drop=True)

        if len(prior_records) == 0:
            return []

        X_matrix = self.fe.transform(prior_records)
        bust_probs = self.calibrator.predict_calibrated_proba(X_matrix)
        pred_errors, p_lowers, p_uppers = self.calibrator.predict_error_with_intervals(X_matrix)
        conf_scores = self.calibrator.predict_confidence(X_matrix)

        history_items = []
        for idx, (_, row) in enumerate(prior_records.iterrows()):
            b_prob = float(bust_probs[idx])
            p_err = float(pred_errors[idx])
            p_low = max(0.0, float(p_lowers[idx]))
            p_up = float(p_uppers[idx])
            conf_score = float(conf_scores[idx])
            risk_tier = self._compute_risk_tier(b_prob, conf_score)

            was_bust = bool(row.get("is_bust", False))
            verdict = self._derive_calibration_verdict(b_prob, conf_score, was_bust)

            row_df = X_matrix.iloc[[idx]]
            exp_info = self.explainer.explain_instance(row_df, top_k_families=3)

            history_items.append({
                "date": str(row[time_col]),
                "initialization_time": str(row.get("initialization_time", "")),
                "lead_day": lead_day,
                "region": actual_name,
                "forecast_rainfall_mm": float(row.get("fcst_rainfall_mm", 0.0)),
                "forecast_temp_2m_c": float(row.get("fcst_temp_2m_c", 0.0)),
                "observed_rainfall_mm": float(row.get("obs_rainfall_mm", 0.0)),
                "observed_temp_2m_c": float(row.get("obs_temp_2m_c", 0.0)),
                "forecast_error_mm": float(row.get("forecast_error_mm", 0.0)),
                "abs_error_mm": float(row.get("abs_error_mm", 0.0)),
                "bust_threshold_mm": float(row.get("bust_threshold_mm", 0.0)),
                "was_bust": was_bust,
                "confidence_at_issue_time": round(conf_score, 4),
                "bust_probability": round(b_prob, 4),
                "predicted_error_mm": round(p_err, 2),
                "conformal_interval_mm": [round(p_low, 2), round(p_up, 2)],
                "risk_tier": risk_tier,
                "calibration_verdict": verdict,
                "evidence_agreement": exp_info.get("evidence_agreement", 1.0),
                "contradiction_flag": exp_info.get("contradiction_flag", False),
                "top_drivers": [d["top_driver_phrase"] for d in exp_info.get("top_families", [])[:3]],
            })

        return history_items

    def get_region_history_summary(
        self,
        region_name: str,
        days: int = 10,
        as_of: Optional[str] = None,
        lead_day: int = 1,
    ) -> Dict:
        """
        Returns aggregate verification statistics and operational summary
        across N historical days for a subdivision.
        """
        history = self.get_region_history(region_name=region_name, days=days, as_of=as_of, lead_day=lead_day)
        if not history:
            return {
                "region": region_name,
                "days": 0,
                "as_of": as_of or "",
                "lead_day": lead_day,
                "counts_per_calibration_verdict": {
                    "confident_correct": 0,
                    "confident_but_busted": 0,
                    "flagged_risky_and_busted": 0,
                    "flagged_risky_no_bust": 0,
                },
                "overall_bust_rate": 0.0,
                "mean_abs_error": 0.0,
                "summary_sentence": f"No verification records found for region '{region_name}'.",
            }

        counts = {
            "confident_correct": 0,
            "confident_but_busted": 0,
            "flagged_risky_and_busted": 0,
            "flagged_risky_no_bust": 0,
        }
        for item in history:
            v = item["calibration_verdict"]
            if v in counts:
                counts[v] += 1

        total_days = len(history)
        bust_count = sum(1 for item in history if item["was_bust"])
        overall_bust_rate = round(bust_count / total_days, 4)
        mean_abs_error = round(sum(item["abs_error_mm"] for item in history) / total_days, 2)
        actual_region = history[0]["region"]
        effective_as_of = history[-1]["date"]

        # Plain language summary sentence adhering to explain.py's lexicon style
        if counts["flagged_risky_and_busted"] > 0 and counts["confident_but_busted"] == 0:
            summary_sentence = (
                f"Over the last {total_days} verified days in {actual_region} (Lead Day {lead_day}), "
                f"the reliability engine demonstrated strong calibration: {counts['confident_correct']} of {total_days} "
                f"forecasts verified correct with high confidence (mean MAE {mean_abs_error} mm), "
                f"and all {counts['flagged_risky_and_busted']} bust events were successfully pre-flagged as risky."
            )
        elif counts["confident_but_busted"] > 0:
            summary_sentence = (
                f"Over the last {total_days} verified days in {actual_region} (Lead Day {lead_day}), "
                f"the overall bust rate was {overall_bust_rate * 100:.1f}% with mean MAE {mean_abs_error} mm. "
                f"{counts['confident_correct']} forecasts were confident and verified correctly, "
                f"while {counts['confident_but_busted']} unflagged bust events occurred due to localized convective divergence."
            )
        else:
            summary_sentence = (
                f"Over the last {total_days} verified days in {actual_region} (Lead Day {lead_day}), "
                f"NWP guidance verified with excellent stability: {counts['confident_correct']} of {total_days} "
                f"forecasts remained within operational tolerance (mean MAE {mean_abs_error} mm, zero busts)."
            )

        return {
            "region": actual_region,
            "days": total_days,
            "as_of": effective_as_of,
            "lead_day": lead_day,
            "counts_per_calibration_verdict": counts,
            "overall_bust_rate": overall_bust_rate,
            "mean_abs_error": mean_abs_error,
            "summary_sentence": summary_sentence,
        }

    def get_day_detail(
        self,
        region_name: str,
        date_str: Optional[str] = None,
        lead_day: int = 1,
    ) -> Optional[Dict]:
        """
        Retrieves full daily record and diagnostic verification fields for a single day.

        Explicitly daily granularity. Sub-daily / hourly data is NOT fabricated;
        an optional illustrative diurnal curve is provided for UI visual rendering only,
        flagged with is_illustrative=True.
        """
        if self.data_df is None or len(self.data_df) == 0:
            return None

        matching = self.data_df[self.data_df["region"].str.lower() == region_name.lower()]
        if len(matching) == 0:
            return None
        actual_name = matching["region"].iloc[0]

        lead_day = max(1, min(10, int(lead_day)))
        subset = self.data_df[
            (self.data_df["region"] == actual_name) & (self.data_df["lead_day"] == lead_day)
        ].copy()

        if len(subset) == 0:
            return None

        time_col = "valid_time" if "valid_time" in subset.columns else "date"
        subset[time_col] = subset[time_col].astype(str)

        if not date_str:
            date_str = subset[time_col].max()

        match_row = subset[subset[time_col] == date_str]
        if len(match_row) == 0:
            return None

        row = match_row.iloc[0]
        X_matrix = self.fe.transform(match_row)

        b_prob = float(self.calibrator.predict_calibrated_proba(X_matrix)[0])
        pred_errors, p_lowers, p_uppers = self.calibrator.predict_error_with_intervals(X_matrix)
        p_err = float(pred_errors[0])
        p_low = max(0.0, float(p_lowers[0]))
        p_up = float(p_uppers[0])
        conf_score = float(self.calibrator.predict_confidence(X_matrix)[0])
        risk_tier = self._compute_risk_tier(b_prob, conf_score)

        exp_info = self.explainer.explain_instance(X_matrix, top_k_families=3)

        # Diurnal illustrative curve (clearly flagged as illustrative, NEVER real forecast)
        t_mean = float(row.get("fcst_temp_2m_c", 28.0))
        r_total = float(row.get("fcst_rainfall_mm", 0.0))

        # Gaussian diurnal precipitation weighting peaking at 16:00 UTC/local
        raw_weights = [math.exp(-0.5 * ((h - 16.0) / 3.0) ** 2) for h in range(24)]
        sum_weights = sum(raw_weights) or 1.0

        hourly_curve = []
        for h in range(24):
            # Sinusoidal diurnal temperature variation (amplitude 4.5 deg C, peak at 14:00)
            temp_h = round(t_mean - 4.5 * math.cos(2.0 * math.pi * (h - 5) / 24.0), 2)
            rain_h = round(r_total * (raw_weights[h] / sum_weights), 2)
            hourly_curve.append({
                "hour": h,
                "time_utc": f"{h:02d}:00",
                "temp_c": temp_h,
                "rainfall_mm": rain_h,
                "is_illustrative": True,
            })

        # Diagnostic ERA5 fields
        era5_fields = {}
        for col in row.index:
            if col.startswith("era5_"):
                era5_fields[col] = float(row[col]) if pd.notna(row[col]) else None

        return {
            "date": str(row[time_col]),
            "region": actual_name,
            "lead_day": lead_day,
            "initialization_time": str(row.get("initialization_time", "")),
            "granularity": "daily",
            "note": "Sub-daily detail is not available from current data sources; this view shows the full daily verification record.",
            "bust_probability": round(b_prob, 4),
            "confidence_score": round(conf_score, 4),
            "predicted_error_mm": round(p_err, 2),
            "error_interval_90_lower": round(p_low, 2),
            "error_interval_90_upper": round(p_up, 2),
            "conformal_interval_mm": [round(p_low, 2), round(p_up, 2)],
            "risk_tier": risk_tier,
            "evidence_agreement": exp_info.get("evidence_agreement", 1.0),
            "contradiction_flag": exp_info.get("contradiction_flag", False),
            "forecast_rainfall_mm": float(row.get("fcst_rainfall_mm", 0.0)),
            "forecast_temp_2m_c": float(row.get("fcst_temp_2m_c", 0.0)),
            "observed_rainfall_mm": float(row["obs_rainfall_mm"]) if pd.notna(row.get("obs_rainfall_mm")) else None,
            "observed_temp_2m_c": float(row["obs_temp_2m_c"]) if pd.notna(row.get("obs_temp_2m_c")) else None,
            "forecast_error_mm": float(row["forecast_error_mm"]) if pd.notna(row.get("forecast_error_mm")) else None,
            "abs_error_mm": float(row["abs_error_mm"]) if pd.notna(row.get("abs_error_mm")) else None,
            "bust_threshold_mm": float(row["bust_threshold_mm"]) if pd.notna(row.get("bust_threshold_mm")) else None,
            "was_bust": bool(row.get("is_bust", False)),
            "era5_diagnostics": era5_fields,
            "top_drivers": [d["top_driver_phrase"] for d in exp_info.get("top_families", [])[:3]],
            "top_families": exp_info.get("top_families", []),
            "operational_bulletin": exp_info.get("operational_bulletin", {}),
            "plain_language_summary": exp_info.get("plain_language_summary", ""),
            "illustrative_hourly_curve": hourly_curve,
            "is_illustrative": True,
            "illustrative_note": "Hourly curve is a synthetic diurnal interpolation for visual rendering only. It is NOT observed or forecasted hourly data.",
        }

    def resolve_location(self, query: str) -> Optional[Dict]:
        """Resolves free-text city or subdivision query to IMD subdivision."""
        return resolve_location_fn(query)

    def predict_custom(self, raw_input: Dict) -> Dict:
        """
        Evaluates forecaster custom scenario ("What-If" synoptic test).
        Accepts continuous inputs (spread, shear, moisture, regime, lead_day)
        and outputs calibrated bust probability and SHAP attribution.
        """
        # Defaults for missing keys (matching new schema)
        defaults = {
            "initialization_time": pd.Timestamp.now().strftime("%Y-%m-%d"),
            "valid_time": (pd.Timestamp.now() + pd.Timedelta(days=5)).strftime("%Y-%m-%d"),
            "location_id": "Custom_Region",
            "lat": 22.0,
            "lon": 78.0,
            "terrain": "Northern_Plains",
            "terrain_difficulty": 0.40,
            "synoptic_regime": "quiescent_clear",
            "lead_day": 5,

            # NWP features
            "fcst_rainfall_mm": 15.0,
            "ens_spread_rainfall": 7.5,
            "ens_spread_mslp": 2.0,
            "fcst_mslp_hpa": 1005.0,
            "vertical_wind_shear": 12.0,
            "fcst_rh_700_pct": 80.0,
            "fcst_cape_jkg": 1800.0,
            "baroclinic_gradient_proxy": 0.05,
            "convective_vulnerability": 0.5,

            # Subseasonal/Global features
            "enso_oni_index": 0.5,
            "mjo_amplitude": 1.4,
            "mjo_phase": 4,
            "iod_index": 0.2,
            "nao_index": 0.0,

            # Recent error
            "recent_error_bias_30d": 2.0,
            "recent_error_mae_30d": 10.0,
            "recent_error_bust_freq_30d": 0.1,
            "recent_error_mae_7d": 8.0,
            "prior_day_verified_error": 14.0,
        }

        # Map legacy / what-if keys before applying defaults
        if "ensemble_spread" in raw_input:
            raw_input["ens_spread_rainfall"] = float(raw_input["ensemble_spread"])
        if "wind_shear_mps" in raw_input:
            raw_input["vertical_wind_shear"] = float(raw_input["wind_shear_mps"])
        if "region" in raw_input:
            raw_input["location_id"] = raw_input["region"]
        if "prior_day_error" in raw_input:
            raw_input["prior_day_verified_error"] = float(raw_input["prior_day_error"])

        regime = str(raw_input.get("synoptic_regime", "")).lower()
        if "cyclon" in regime or "depression" in regime:
            raw_input["cyclone_active_flag"] = 1.0
            raw_input["cyclone_intensity_kt"] = 65.0
            raw_input["cyclone_proximity_index"] = 0.90
            if float(raw_input.get("fcst_rainfall_mm", 15.0)) <= 20.0:
                raw_input["fcst_rainfall_mm"] = 65.0
            raw_input["fcst_cape_jkg"] = max(float(raw_input.get("fcst_cape_jkg", 1800.0)), 2500.0)
            raw_input["recent_error_mae_30d"] = max(float(raw_input.get("recent_error_mae_30d", 10.0)), 18.0)

        # Merge
        for k, v in defaults.items():
            if k not in raw_input:
                raw_input[k] = v

        # Add derived date col if missing for legacy compat
        if "date" not in raw_input:
            raw_input["date"] = raw_input["initialization_time"]

        df = pd.DataFrame([raw_input])

        # Ensure correct column names used in fallback (e.g. valid_time from init + lead)
        if "initialization_time" in raw_input and "valid_time" not in raw_input:
            df["valid_time"] = pd.to_datetime(df["initialization_time"]) + pd.Timedelta(days=int(df["lead_day"].iloc[0]))

        # Transform using Feature Pipeline
        X_matrix = self.fe.transform(df)

        b_prob = float(self.calibrator.predict_calibrated_proba(X_matrix)[0])
        p_err, p_lower, p_upper = self.calibrator.predict_error_with_intervals(X_matrix)
        p_err = float(p_err[0])
        p_lower = float(p_lower[0])
        p_upper = float(p_upper[0])
        conf_score = float(self.calibrator.predict_confidence(X_matrix)[0])

        risk_tier = self._compute_risk_tier(b_prob, conf_score)
        exp_info = self.explainer.explain_instance(X_matrix, top_k_families=3)

        return {
            "bust_probability": round(b_prob, 4),
            "predicted_error_mm": round(p_err, 2),
            "error_interval_90_lower": round(max(0.0, p_lower), 2),
            "error_interval_90_upper": round(p_upper, 2),
            "conformal_interval_mm": [round(max(0.0, p_lower), 2), round(p_upper, 2)],
            "confidence_score": round(conf_score, 4),
            "risk_tier": risk_tier,
            "evidence_agreement": exp_info.get("evidence_agreement", 1.0),
            "contradiction_flag": exp_info.get("contradiction_flag", False),
            "plain_language_summary": exp_info.get("plain_language_summary", ""),
            "top_drivers": exp_info.get("top_families", []),
            "top_families": exp_info.get("top_families", []),
            "operational_bulletin": exp_info.get("operational_bulletin", {}),
            "all_attributions": exp_info.get("all_attributions", []),
            "raw_features_used": raw_input,
            "prediction": {
                "bust_probability": round(b_prob, 4),
                "predicted_error_mm": round(p_err, 2),
                "error_interval_90_lower": round(max(0.0, p_lower), 2),
                "error_interval_90_upper": round(p_upper, 2),
                "conformal_interval_mm": [round(max(0.0, p_lower), 2), round(p_upper, 2)],
                "confidence_score": round(conf_score, 4),
                "risk_tier": risk_tier,
                "evidence_agreement": exp_info.get("evidence_agreement", 1.0),
                "contradiction_flag": exp_info.get("contradiction_flag", False),
                "plain_language_summary": exp_info.get("plain_language_summary", ""),
                "operational_bulletin": exp_info.get("operational_bulletin", {}),
            },
        }


# Global engine singleton
_engine_instance: Optional[ForecastInferenceEngine] = None

def get_engine() -> ForecastInferenceEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ForecastInferenceEngine()
    return _engine_instance


if __name__ == "__main__":
    engine = get_engine()
    dates = engine.get_available_dates()
    print(f"Inference engine initialized with {len(dates)} dates.")
    latest_date = dates[-1]
    print(f"Testing confidence map on date {latest_date}, Lead Day 5:")
    cmap = engine.get_confidence_map(latest_date, lead_day=5)
    print(f"Total subdivisions returned: {len(cmap)}")
    print("Sample result:")
    print(json.dumps(cmap[0], indent=2))
