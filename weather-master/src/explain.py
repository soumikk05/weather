"""
SHAP-Based Explainability Engine with Meteorological Translation
Forecast Reliability Engine — NCMRWF / Ministry of Earth Sciences

Translates tree-based feature attributions into forecaster-accessible,
plain-language meteorological synopses grouped by feature family.
"""

import os
import sys
# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Dict, List
import joblib
import numpy as np
import pandas as pd
import shap
from collections import defaultdict


FEATURE_MET_TRANSLATION: Dict[str, str] = {
    # NWP State Evolution
    "fcst_rainfall_mm": "Forecasted heavy precipitation",
    "fcst_temp_2m_c": "Extreme surface temperature forecast",
    "fcst_mslp_hpa": "Anomalous mean sea level pressure",
    "fcst_wind_850_mps": "Strong low-level (850 hPa) wind shear",
    "fcst_wind_200_mps": "Strong upper-level (200 hPa) jet dynamics",
    "fcst_rh_700_pct": "High mid-tropospheric moisture",
    "fcst_geopot_500_m": "Anomalous 500 hPa geopotential height",
    "fcst_cape_jkg": "Severe convective potential (high CAPE)",
    
    # Uncertainty
    "ens_spread_temp": "High ensemble spread in temperature",
    "ens_spread_mslp": "High ensemble spread in pressure",
    "ens_spread_precip": "High ensemble disagreement on precipitation",
    "ens_members_total": "Reduced active ensemble members",
    "lead_day": "Extended forecast lead time",
    
    # Recent Error
    "prior_day_error": "High forecast error in the preceding cycle",
    "recent_30d_bias": "Persistent 30-day directional model bias",
    "recent_30d_mae": "Elevated 30-day mean absolute error",
    "recent_30d_bust_freq": "High frequency of recent forecast busts",
    
    # Run Consistency
    "d2_d1_forecast_shift": "Significant run-to-run forecast shift",
    "forecast_jumpiness": "High temporal forecast jumpiness",
    
    # Seasonal Context
    "month_sin": "Seasonal climatological cycle",
    "month_cos": "Seasonal climatological cycle",
    "days_from_monsoon_onset": "Proximity to monsoon onset transition",
    "days_from_monsoon_withdrawal": "Proximity to monsoon withdrawal transition",
    
    # Analog Regime
    "analog_min_distance": "Poor historical analog matches (unprecedented pattern)",
    "analog_mean_error_mm": "High historical error in similar synoptic analogs",
    "analog_bust_probability": "High bust rate in historical analogs",
    "synoptic_regime_index": "Complex synoptic weather regime",
    
    # Spatial Ocean / Large Scale
    "enso_oni": "Active ENSO (El Niño/La Niña) forcing",
    "mjo_amplitude": "Strong Madden-Julian Oscillation amplitude",
    "mjo_phase": "MJO phase favorable for tropical convection",
    "iod_dmi": "Active Indian Ocean Dipole",
    "era5_sst_c": "Anomalous Sea Surface Temperatures",
    "cyclone_active_flag": "Active cyclonic disturbance in the basin",
    "cyclone_proximity_index": "Proximity to active cyclone",
    "cyclone_intensity_kt": "High intensity of nearby cyclone",
    "active_monsoon_teleconnection_index": "Active monsoon teleconnection pattern",
    
    # Static Geography
    "elevation_m": "High elevation orography",
    "dist_coast_km": "Inland thermal contrast",
    "land_fraction": "Complex land-water boundary",
    "terrain_complexity": "High terrain complexity (sub-grid orography)",
    "terrain_type_code": "Complex regional terrain type",
    "elevation_norm": "Normalized elevation impact",
    "is_coastal_zone": "Coastal boundary layer dynamics",
    "is_high_mountain_barrier": "High mountain barrier interaction",
}

FAMILY_FRIENDLY_NAMES = {
    "nwp_state_evolution": "Synoptic State Evolution",
    "uncertainty": "Ensemble Uncertainty",
    "recent_error": "Recent Model Error",
    "run_consistency": "Run-to-Run Consistency",
    "seasonal_context": "Seasonal Context",
    "analog_regime": "Historical Analogs",
    "spatial_ocean_large_scale": "Large-Scale Oceanic Forcing",
    "static_geography": "Static Geography & Terrain"
}

class ForecastExplainer:
    """
    SHAP-powered explainer that bridges machine learning attributions
    with operational weather forecasting semantics, grouped by feature family.
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
        self.explainer = shap.TreeExplainer(self.model.classifier)

    def explain_instance(self, X_df: pd.DataFrame, top_k_families: int = 2) -> Dict:
        """
        Computes SHAP feature attributions for a single instance.
        Groups impacts by feature family to build a high-level synopsis.
        
        X_df may be raw (un-transformed) OR already a feature matrix.
        If it contains the raw schema columns, pipeline.transform() is called first.
        """
        if len(X_df) != 1:
            X_df = X_df.iloc[[0]]

        # If input is a raw record (not yet transformed), run the pipeline
        if "initialization_time" in X_df.columns or "location_id" in X_df.columns:
            X_df = self.pipeline.transform(X_df)

        # Build a fully aligned feature matrix — fill missing with 0
        X_aligned = pd.DataFrame(0.0, index=X_df.index, columns=self.feature_names)
        for col in self.feature_names:
            if col in X_df.columns:
                X_aligned[col] = X_df[col].values
        
        shap_values = self.explainer(X_aligned)
        
        # Handle binary classification SHAP dimensions
        vals = shap_values.values[0]
        if len(vals.shape) > 1 and vals.shape[-1] == 2:
            vals = vals[:, 1]  # positive class (bust)

        family_impacts = defaultdict(float)
        family_features = defaultdict(list)
        
        all_attributions = []

        for feat, val, shap_val in zip(self.feature_names, X_aligned.iloc[0], vals):
            phrase = FEATURE_MET_TRANSLATION.get(feat, feat.replace("_", " ").title())
            family = self.feature_to_family.get(feat, "Unknown")
            
            family_impacts[family] += float(shap_val)
            family_features[family].append({
                "feature": feat,
                "phrase": phrase,
                "raw_value": float(val),
                "shap_value": float(shap_val)
            })
            
            all_attributions.append({
                "feature": feat,
                "family": family,
                "phrase": phrase,
                "raw_value": float(val),
                "shap_value": float(shap_val),
            })

        # Sort all attributions for the UI
        all_attributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

        # Build family-level summary
        family_records = []
        for fam, total_impact in family_impacts.items():
            friendly_name = FAMILY_FRIENDLY_NAMES.get(fam, fam.replace("_", " ").title())
            
            # Find the top driving feature in this family
            feats = family_features[fam]
            # sort by absolute shap to find the most important driver in this family
            feats.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
            top_feat = feats[0] if feats else None
            
            family_records.append({
                "family_key": fam,
                "family_name": friendly_name,
                "total_impact": total_impact,
                "top_driver_phrase": top_feat["phrase"] if top_feat else "Multiple factors",
                "top_driver_impact": top_feat["shap_value"] if top_feat else 0.0
            })
            
        # Separate risk escalators and mitigators at the family level
        escalators = [r for r in family_records if r["total_impact"] > 0]
        mitigators = [r for r in family_records if r["total_impact"] < 0]
        
        escalators.sort(key=lambda x: x["total_impact"], reverse=True)
        mitigators.sort(key=lambda x: x["total_impact"]) # most negative first
        
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

        return {
            "plain_language_summary": plain_language_text,
            "top_families": family_records,
            "all_attributions": all_attributions[:15],
            "base_value": float(shap_values.base_values[0]) if hasattr(shap_values.base_values, "__len__") else float(shap_values.base_values),
        }

if __name__ == "__main__":
    explainer = ForecastExplainer()
    print("ForecastExplainer loaded successfully.")
    
    # Test on a single generated record using the pipeline
    test_df = pd.read_csv("data/nwp_forecast_bust_dataset.csv").tail(1)
    X_test = explainer.pipeline.transform(test_df)
    exp_res = explainer.explain_instance(X_test)
    
    print("\n--- Example Plain Language Forecaster Synopsis ---")
    print(exp_res["plain_language_summary"])
    print("\nTop Family Drivers:")
    for f in sorted(exp_res["top_families"], key=lambda x: abs(x["total_impact"]), reverse=True)[:3]:
        print(f"  * {f['family_name']}: Total Impact={f['total_impact']:+.3f} (Mainly: {f['top_driver_phrase']})")
