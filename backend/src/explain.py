"""
SHAP-Based Explainability Engine with Meteorological Translation
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Translates tree-based feature attributions into forecaster-accessible,
plain-language meteorological synopses grouped by the 8 feature families.
Provides operational bulletin synthesis and family-level importance shares.
"""

import os
import sys
# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Disable numba JIT to avoid blocked DLL on Windows AppLocker systems
os.environ["NUMBA_DISABLE_JIT"] = "1"

from typing import Dict, List, Optional, Union
import joblib
import numpy as np
import pandas as pd
try:
    import shap
except Exception:
    shap = None
from collections import defaultdict


# ---------------------------------------------------------------------------
# Comprehensive Meteorological Translation Lexicon (All 60 Features)
# ---------------------------------------------------------------------------
FEATURE_MET_TRANSLATION: Dict[str, str] = {
    # 1. NWP State Evolution
    "fcst_rainfall_mm": "Forecasted heavy precipitation",
    "fcst_temp_2m_c": "Extreme 2m surface temperature anomaly",
    "fcst_mslp_hpa": "Deep surface low pressure depression",
    "fcst_wind_850_mps": "Strong low-level monsoon jet (850 hPa)",
    "fcst_wind_200_mps": "Intense upper-tropospheric jet dynamics (200 hPa)",
    "fcst_rh_700_pct": "High mid-tropospheric moisture content",
    "fcst_geopot_500_m": "Anomalous 500 hPa geopotential height",
    "fcst_cape_jkg": "Severe convective potential (high CAPE)",
    "vertical_wind_shear": "Strong vertical wind shear (850-200 hPa)",
    "baroclinic_gradient_proxy": "Strong baroclinic instability gradient",
    "convective_vulnerability": "High convective cloudburst vulnerability",
    "dynamic_instability_composite": "High non-linear dynamic atmospheric instability",
    "heavy_rain_flag": "Forecast rainfall exceeding warning threshold (>35.5 mm)",

    # 2. Uncertainty
    "ens_spread_rainfall": "High ensemble disagreement on precipitation",
    "ens_spread_temp": "Elevated ensemble spread in temperature",
    "ens_spread_mslp": "High ensemble spread in surface pressure",
    "spread_lead_interaction": "Error compounding over extended forecast lead time",
    "spread_to_lead_ratio": "Accelerated rate of ensemble dispersion",
    "ens_prob_rain_gt10": "High ensemble consensus on moderate rain (>10 mm)",
    "ens_prob_rain_gt50": "Ensemble members signaling extreme rain (>50 mm)",
    "relative_spread_ratio": "High noise-to-signal ratio in ensemble forecast",
    "lead_day": "Extended forecast lead time",

    # 3. Recent Error
    "recent_error_bias_30d": "Persistent 30-day directional model forecast bias",
    "recent_error_mae_30d": "Elevated 30-day verification error baseline",
    "recent_error_bust_freq_30d": "High frequency of recent forecast busts",
    "recent_error_mae_7d": "Elevated short-term (7-day) verification error",
    "prior_day_verified_error": "High forecast error in the preceding verification cycle",
    "prior_day_error": "High forecast error in the preceding cycle",

    # 4. Run Consistency
    "run_to_run_rainfall_delta_mm": "Large run-to-run forecast shift in precipitation",
    "run_to_run_abs_delta_mm": "Large absolute forecast shift between consecutive runs",
    "run_to_run_relative_shift": "Significant proportional forecast shift between cycles",
    "run_flip_flop_flag": "Model flip-flopping across successive forecast runs",
    "run_to_run_mslp_delta_hpa": "Significant run-to-run pressure trend divergence",

    # 5. Seasonal Context
    "doy_sin": "Day-of-year seasonal climatological cycle",
    "doy_cos": "Day-of-year seasonal climatological cycle",
    "month_sin": "Seasonal climatological cycle",
    "month_cos": "Seasonal climatological cycle",
    "is_monsoon_season": "Active Southwest Monsoon seasonal window",
    "is_transition_window": "Volatile seasonal transition period (onset/withdrawal)",
    "days_from_june_1": "Monsoon progression timeline from June 1",
    "climatological_season_bust_rate": "Elevated historical bust frequency in this season",

    # 6. Analog Regime
    "analog_min_distance": "Poor historical analog match (unprecedented synoptic pattern)",
    "analog_mean_error_mm": "High historical error in similar synoptic analog states",
    "analog_bust_probability": "High bust rate in historical synoptic analogs",
    "synoptic_regime_index": "Complex synoptic weather regime",

    # 7. Spatial Ocean & Large Scale
    "enso_oni": "Active ENSO (El Niño/La Niña) teleconnection forcing",
    "mjo_amplitude": "Strong Madden-Julian Oscillation amplitude",
    "mjo_phase": "Convectively favorable MJO phase for Indian longitudes",
    "iod_dmi": "Active Indian Ocean Dipole phase",
    "era5_sst_c": "Anomalously warm Sea Surface Temperatures",
    "cyclone_active_flag": "Active tropical cyclonic disturbance in the basin",
    "cyclone_proximity_index": "Close proximity to active cyclonic disturbance",
    "cyclone_intensity_kt": "High intensity of nearby cyclonic vortex",
    "active_monsoon_teleconnection_index": "Active monsoon teleconnection pattern",

    # 8. Static Geography
    "elevation_m": "High mountain orography and complex elevation",
    "dist_coast_km": "Inland thermal contrast and coastal proximity",
    "land_fraction": "Complex coastal land-water boundary",
    "terrain_complexity": "Steep sub-grid orographic terrain complexity",
    "elevation_norm": "High elevation orographic barrier",
    "is_coastal_zone": "Coastal boundary layer marine dynamics",
    "is_high_mountain_barrier": "High mountain barrier inducing orographic lifting",
    "terrain_type_code": "Complex regional geomorphic terrain category",
}

# Directional translations when feature stabilizes the forecast (reduces bust risk)
FEATURE_MET_STABILIZING: Dict[str, str] = {
    "ens_spread_rainfall": "Strong ensemble consensus on precipitation",
    "ens_spread_temp": "Tight ensemble temperature agreement",
    "ens_spread_mslp": "Consistent ensemble surface pressure",
    "vertical_wind_shear": "Weak vertical wind shear (stable air column)",
    "fcst_cape_jkg": "Low convective energy (stable thermodynamic profile)",
    "fcst_rainfall_mm": "Benign / light precipitation forecast",
    "fcst_mslp_hpa": "Stable barometric surface pressure",
    "run_flip_flop_flag": "High run-to-run forecast consistency",
    "recent_error_mae_30d": "Low recent 30-day model error baseline",
    "prior_day_verified_error": "Accurate prior-cycle NWP forecast",
    "analog_min_distance": "Close historical analog matches (well-sampled regime)",
    "analog_bust_probability": "Low bust rate in historical analogs",
    "cyclone_active_flag": "Absence of active cyclonic disturbances",
    "is_transition_window": "Established non-transition seasonal period",
    "terrain_complexity": "Uniform, non-complex lowland terrain",
}

FAMILY_FRIENDLY_NAMES: Dict[str, str] = {
    "nwp_state_evolution": "Synoptic State Evolution",
    "uncertainty": "Ensemble Uncertainty",
    "recent_error": "Recent Model Error",
    "run_consistency": "Run-to-Run Consistency",
    "seasonal_context": "Seasonal Context",
    "analog_regime": "Historical Analogs",
    "spatial_ocean_large_scale": "Large-Scale Oceanic Forcing",
    "static_geography": "Static Geography & Terrain",
}


class ForecastExplainer:
    """
    SHAP-powered explainability engine that bridges machine learning attributions
    with operational numerical weather prediction semantics.

    Outputs:
    - Grouped SHAP feature family contributions with percentage shares
    - Granular top risk escalators (drivers pushing toward bust)
    - Granular top mitigators (drivers stabilizing forecast confidence)
    - Forecaster-ready plain-language meteorological advisory bulletins
    """

    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.model_path = os.path.join(model_dir, "reliability_model.joblib")
        self.pipeline_path = os.path.join(model_dir, "feature_pipeline.joblib")

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at {self.model_path}. Run train_model.py first.")

        self.model = joblib.load(self.model_path)
        self.pipeline = joblib.load(self.pipeline_path)

        # Build mapping from feature -> family
        self.feature_to_family = {}
        family_map = self.pipeline.get_family_features_map()
        for family, features in family_map.items():
            for feat in features:
                self.feature_to_family[feat] = family

        self.feature_names = self.pipeline.get_feature_names()

        # Initialize SHAP TreeExplainer on the classifier inside the model wrapper
        if shap is not None:
            try:
                self.explainer = shap.TreeExplainer(self.model.classifier)
            except Exception:
                self.explainer = None
        else:
            self.explainer = None

    def explain_instance(
        self,
        X_df: pd.DataFrame,
        top_k_families: int = 2,
        top_k: Optional[int] = None,
        **kwargs,
    ) -> Dict:
        """
        Computes SHAP feature attributions for a single verification instance.
        Groups impacts by feature family to build a high-level meteorological synopsis.

        Parameters
        ----------
        X_df : pd.DataFrame
            Single-row DataFrame (raw schema columns or pre-transformed feature matrix).
        top_k_families : int
            Number of top feature families to highlight in the synopsis.
        top_k : int, optional
            Alias for top_k_families (backward compatibility).

        Returns
        -------
        Dict with keys:
            - plain_language_summary: str
            - top_families: List[Dict] with family_key, family_name, total_impact, percentage_share, top_driver_phrase
            - top_drivers: List[str]
            - all_attributions: List[Dict] (sorted by absolute SHAP impact)
            - base_value: float
            - operational_bulletin: Dict with advisory level and recommendations
        """
        if top_k is not None:
            top_k_families = top_k
        if len(X_df) != 1:
            X_df = X_df.iloc[[0]]

        # If input is a raw record (not yet transformed), run through pipeline
        if "initialization_time" in X_df.columns or "location_id" in X_df.columns:
            X_transformed = self.pipeline.transform(X_df)
        else:
            X_transformed = X_df

        # Build fully aligned feature matrix — fill missing with 0
        X_aligned = pd.DataFrame(0.0, index=X_transformed.index, columns=self.feature_names)
        for col in self.feature_names:
            if col in X_transformed.columns:
                X_aligned[col] = X_transformed[col].values

        # Compute SHAP values with graceful fallback
        if self.explainer is not None:
            try:
                shap_obj = self.explainer(X_aligned)
                vals = shap_obj.values[0]
                if len(vals.shape) > 1 and vals.shape[-1] == 2:
                    vals = vals[:, 1]  # positive class (bust probability)
                base_val = float(shap_obj.base_values[0]) if hasattr(shap_obj.base_values, "__len__") else float(shap_obj.base_values)
            except Exception:
                vals = self._fallback_attributions(X_aligned)
                base_val = 0.10
        else:
            vals = self._fallback_attributions(X_aligned)
            base_val = 0.10

        family_impacts = defaultdict(float)
        family_abs_impacts = defaultdict(float)
        family_features = defaultdict(list)
        all_attributions = []

        total_abs_shap = float(np.sum(np.abs(vals)))

        for feat, val, shap_val in zip(self.feature_names, X_aligned.iloc[0], vals):
            # Directional phrase selection
            if shap_val >= 0:
                phrase = FEATURE_MET_TRANSLATION.get(feat, feat.replace("_", " ").title())
            else:
                phrase = FEATURE_MET_STABILIZING.get(feat, f"Stable {feat.replace('_', ' ')}")

            family = self.feature_to_family.get(feat, "nwp_state_evolution")

            family_impacts[family] += float(shap_val)
            family_abs_impacts[family] += abs(float(shap_val))

            feat_record = {
                "feature": feat,
                "family": family,
                "phrase": phrase,
                "raw_value": round(float(val), 3),
                "shap_value": round(float(shap_val), 4),
            }
            family_features[family].append(feat_record)
            all_attributions.append(feat_record)

        # Sort all individual feature attributions by absolute impact
        all_attributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

        # Build family-level summary with percentage contributions
        family_records = []
        for fam, total_impact in family_impacts.items():
            friendly_name = FAMILY_FRIENDLY_NAMES.get(fam, fam.replace("_", " ").title())
            abs_impact = family_abs_impacts[fam]
            pct_share = round((abs_impact / total_abs_shap) * 100.0, 1) if total_abs_shap > 1e-6 else 0.0

            feats = family_features[fam]
            feats.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
            top_feat = feats[0] if feats else None

            family_records.append({
                "family_key": fam,
                "family_name": friendly_name,
                "total_impact": round(total_impact, 4),
                "abs_impact": round(abs_impact, 4),
                "percentage_share": pct_share,
                "top_driver_phrase": top_feat["phrase"] if top_feat else "Multiple factors",
                "top_driver_impact": top_feat["shap_value"] if top_feat else 0.0,
            })

        # Separate risk escalators and mitigators
        escalators = [r for r in family_records if r["total_impact"] > 0]
        mitigators = [r for r in family_records if r["total_impact"] < 0]

        escalators.sort(key=lambda x: x["total_impact"], reverse=True)
        mitigators.sort(key=lambda x: x["total_impact"])  # most stabilizing first

        top_escalators = escalators[:top_k_families]

        # Generate Plain-Language Synopsis
        if top_escalators:
            reasons = []
            for r in top_escalators:
                reasons.append(f"{r['family_name']} (specifically {r['top_driver_phrase'].lower()})")
            reasons_str = " and ".join(reasons)

            plain_language_text = f"Elevated bust risk driven primarily by {reasons_str}."

            if mitigators:
                best_mit = mitigators[0]
                plain_language_text += f" Stabilizing factor: {best_mit['family_name']} (-{abs(best_mit['total_impact']):.2f})."
        else:
            plain_language_text = "Forecast confidence is high; synoptic dynamics and ensemble consistency remain stable."

        # Synthesize Operational Advisory Bulletin
        bulletin = self._build_operational_bulletin(escalators, mitigators, base_val)

        return {
            "plain_language_summary": plain_language_text,
            "top_families": family_records,
            "top_drivers": [r["top_driver_phrase"] for r in family_records if r.get("top_driver_phrase")],
            "all_attributions": all_attributions[:20],
            "base_value": round(base_val, 4),
            "operational_bulletin": bulletin,
        }

    def explain_dataset(self, X_df: pd.DataFrame, sample_size: int = 50) -> Dict:
        """
        Computes mean absolute SHAP values across a batch of forecasts.
        Provides global feature family importance ranking for model audits.
        """
        if len(X_df) > sample_size:
            X_df = X_df.sample(n=sample_size, random_state=42)

        if "initialization_time" in X_df.columns or "location_id" in X_df.columns:
            X_transformed = self.pipeline.transform(X_df)
        else:
            X_transformed = X_df

        X_aligned = pd.DataFrame(0.0, index=X_transformed.index, columns=self.feature_names)
        for col in self.feature_names:
            if col in X_transformed.columns:
                X_aligned[col] = X_transformed[col].values

        if self.explainer is not None:
            shap_obj = self.explainer(X_aligned)
            vals = shap_obj.values
            if len(vals.shape) > 2 and vals.shape[-1] == 2:
                vals = vals[:, :, 1]
        else:
            vals = np.array([self._fallback_attributions(X_aligned.iloc[[i]]) for i in range(len(X_aligned))])

        mean_abs_per_feature = np.mean(np.abs(vals), axis=0)

        family_global = defaultdict(float)
        for feat, score in zip(self.feature_names, mean_abs_per_feature):
            fam = self.feature_to_family.get(feat, "nwp_state_evolution")
            family_global[fam] += float(score)

        total_score = sum(family_global.values()) or 1.0
        family_ranking = [
            {
                "family_key": fam,
                "family_name": FAMILY_FRIENDLY_NAMES.get(fam, fam),
                "mean_abs_shap": round(score, 4),
                "percentage_importance": round((score / total_score) * 100, 1),
            }
            for fam, score in sorted(family_global.items(), key=lambda x: x[1], reverse=True)
        ]

        return {
            "sample_size": len(X_df),
            "family_ranking": family_ranking,
        }

    def _fallback_attributions(self, X_row: pd.DataFrame) -> np.ndarray:
        """Lightweight fallback attribution based on feature importances when SHAP is unavailable."""
        if hasattr(self.model.classifier, "feature_importances_"):
            importances = self.model.classifier.feature_importances_.astype(float)
            norm_imp = importances / (np.sum(importances) + 1e-7)
            # Scale by standardized feature divergence
            row_vals = X_row.iloc[0].values
            return (norm_imp * np.sign(row_vals - np.mean(row_vals))).round(4)
        return np.zeros(len(self.feature_names))

    def _build_operational_bulletin(
        self,
        escalators: List[Dict],
        mitigators: List[Dict],
        base_val: float,
    ) -> Dict[str, str]:
        """Synthesizes structured advisory text for duty forecasters."""
        total_escalation = sum(e["total_impact"] for e in escalators)
        total_mitigation = abs(sum(m["total_impact"] for m in mitigators))

        if total_escalation >= 0.8:
            advisory_level = "RED (Severe Bust Vulnerability)"
            recommendation = "High risk of sudden forecast degradation. Deploy multi-model ensemble consensus and issue localized precautionary watch."
        elif total_escalation >= 0.35:
            advisory_level = "AMBER (Elevated Uncertainty)"
            recommendation = "Moderate forecast spread. Verify against recent radar and satellite moisture convergence before issuing official warning."
        else:
            advisory_level = "GREEN (High Confidence)"
            recommendation = "NWP forecast demonstrates strong physical stability and high ensemble consensus. Proceed with standard deterministic guidance."

        primary_escalator = escalators[0]["top_driver_phrase"] if escalators else "None"
        primary_stabilizer = mitigators[0]["top_driver_phrase"] if mitigators else "None"

        return {
            "advisory_level": advisory_level,
            "primary_escalator": primary_escalator,
            "primary_stabilizer": primary_stabilizer,
            "net_synoptic_balance": f"{total_escalation - total_mitigation:+.2f}",
            "operational_recommendation": recommendation,
            "recommendation": recommendation,
        }


if __name__ == "__main__":
    explainer = ForecastExplainer()
    print("ForecastExplainer loaded successfully with 60 meteorological features.")

    test_df = pd.read_csv("data/nwp_forecast_bust_dataset.csv").tail(1)
    X_test = explainer.pipeline.transform(test_df)
    exp_res = explainer.explain_instance(X_test)

    print("\n--- Forecaster Advisory Synopsis ---")
    print(exp_res["plain_language_summary"])
    print(f"\nAdvisory Level: {exp_res['operational_bulletin']['advisory_level']}")
    print(f"Recommendation: {exp_res['operational_bulletin']['operational_recommendation']}")
    print("\nFeature Family Breakdown:")
    for f in exp_res["top_families"][:4]:
        print(f"  * {f['family_name']:30} Impact: {f['total_impact']:+.3f} ({f['percentage_share']}%) — Top Driver: {f['top_driver_phrase']}")
