"""
Unified Inference Engine for Forecast Bust Detection
Smart India Hackathon - NCMRWF / Ministry of Earth Sciences

Single source of truth used by both FastAPI and Streamlit Dashboard.
Produces region-wise confidence maps, 10-day lead time profiles,
calibrated bust probabilities, and plain-language explanations.
"""

import json
import os
import sys
# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Dict, List, Optional
import joblib
import numpy as np
import pandas as pd

from src.explain import ForecastExplainer
from src.features import FeatureEngineer
from src.generate_synthetic_data import SUBDIVISIONS


class ForecastInferenceEngine:
    """
    Central inference engine serving predictions, confidence maps,
    and explanations across Day 1 - Day 10 for operational forecasters.
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
            self.available_dates = sorted(self.data_df["date"].unique().tolist())
        else:
            self.data_df = None
            self.available_dates = []

    def _compute_risk_tier(self, bust_prob: float, confidence_score: float) -> str:
        """Categorizes operational risk into 3 intuitive tiers."""
        if bust_prob >= 0.50 or confidence_score <= 0.40:
            return "Low Confidence - Bust Risk"
        elif bust_prob >= 0.25 or confidence_score <= 0.65:
            return "Moderate Confidence"
        else:
            return "High Confidence"

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
        pred_errors, _, _ = self.calibrator.predict_error_with_intervals(X_matrix)
        conf_scores = self.calibrator.predict_confidence(X_matrix)

        results = []
        for idx, (_, row) in enumerate(subset.iterrows()):
            b_prob = float(bust_probs[idx])
            p_err = float(pred_errors[idx])
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
                "confidence_score": round(conf_score, 4),
                "risk_tier": risk_tier,
                "top_drivers": [d["top_driver_phrase"] for d in exp_info["top_families"][:3]],
                "plain_language_summary": exp_info["plain_language_summary"],
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
        pred_errors, _, _ = self.calibrator.predict_error_with_intervals(X_matrix)
        conf_scores = self.calibrator.predict_confidence(X_matrix)

        timeline = []
        for idx, (_, row) in enumerate(subset.iterrows()):
            b_prob = float(bust_probs[idx])
            p_err = float(pred_errors[idx])
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
                "confidence_score": round(conf_score, 4),
                "risk_tier": risk_tier,
                "plain_language_summary": exp_info["plain_language_summary"],
                "top_drivers": exp_info["top_families"],
            })

        return timeline

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
            "prediction": {
                "bust_probability": round(b_prob, 4),
                "predicted_error_mm": round(p_err, 2),
                "error_interval_90_lower": round(p_lower, 2),
                "error_interval_90_upper": round(p_upper, 2),
                "confidence_score": round(conf_score, 4),
                "risk_tier": risk_tier,
                "plain_language_summary": exp_info["plain_language_summary"]
            },
            "top_drivers": exp_info["top_families"],
            "raw_features_used": raw_input
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
