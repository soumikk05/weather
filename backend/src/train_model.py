import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import argparse
import pandas as pd
import numpy as np

from src.data.synthetic import NonCircularSyntheticGenerator
from src.feature_families.pipeline import FeaturePipeline
from src.evaluation.splits import get_time_blocked_splits
from src.models.model_pipeline import ForecastReliabilityModel
from src.models.calibration import CalibratorAndConformalPredictor
from src.evaluation.baselines import BaselineModels
from src.evaluation.ablation import AblationStudy
from src.evaluation.case_studies import CaseStudyEvaluator

def main():
    parser = argparse.ArgumentParser(description="Forecast Reliability Engine - Model Training Pipeline")
    parser.add_argument("--data-source", choices=["synthetic", "real"], required=True, help="Data source to use")
    parser.add_argument("--output-dir", type=str, default="models", help="Directory to save model artifacts")
    parser.add_argument("--data-path", type=str, default="data/nwp_forecast_bust_dataset.csv", help="Path to save/load dataset")
    parser.add_argument("--run-ablation", action="store_true", help="Run ablation study")
    parser.add_argument("--run-case-studies", action="store_true", help="Run historical case studies")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # 1. Load Data
    if args.data_source == "synthetic":
        print(f"Loading/Generating SYNTHETIC smoke-test data at {args.data_path}...")
        need_regen = not os.path.exists(args.data_path)
        if not need_regen:
            sample_df = pd.read_csv(args.data_path, nrows=5)
            if "initialization_time" not in sample_df.columns:
                print("Existing dataset has obsolete schema. Regenerating non-circular synthetic data...")
                need_regen = True

        if need_regen:
            print("Generating non-circular synthetic data (may take a minute)...")
            gen = NonCircularSyntheticGenerator(random_seed=42)
            df = gen.load(start_date="2022-01-01", end_date="2024-12-31")
            os.makedirs(os.path.dirname(args.data_path) or ".", exist_ok=True)
            df.to_csv(args.data_path, index=False)
        else:
            df = pd.read_csv(args.data_path)
            
        print("[WARNING] RUNNING ON SYNTHETIC SMOKE-TEST DATA [WARNING]")
    else:
        # Real data loaders would be called here
        if not os.path.exists(args.data_path):
            raise FileNotFoundError(f"Real data not found at {args.data_path}. Please provide data or run with --data-source synthetic")
        print(f"Loading REAL data from {args.data_path}...")
        df = pd.read_csv(args.data_path)

    # Convert init_time if available, else date
    time_col = "initialization_time" if "initialization_time" in df.columns else ("init_time" if "init_time" in df.columns else ("date" if "date" in df.columns else None))
    if time_col:
        df = df.sort_values(time_col).reset_index(drop=True)

    # 2. Extract Features
    print("\n--- Extracting Features ---")
    pipeline = FeaturePipeline()
    # Assuming pipeline transform adds columns directly to the DataFrame or returns a feature matrix
    # Based on pipeline.py, we fit on train only, but for simplicity of this script, we can split first
    train_df, val_df, test_df = get_time_blocked_splits(df, time_col=time_col)
    
    pipeline.fit(train_df)
    X_train_full = pipeline.transform(train_df)
    X_val_full = pipeline.transform(val_df)
    X_test_full = pipeline.transform(test_df)
    
    # Extract active features and targets
    feature_names = pipeline.get_feature_names()
    # filter out missing columns just in case
    feature_names = [c for c in feature_names if c in X_train_full.columns]

    X_train = X_train_full[feature_names].fillna(0)
    X_val = X_val_full[feature_names].fillna(0)
    X_test = X_test_full[feature_names].fillna(0)
    
    y_train_clf = train_df["is_bust"].values
    _err_col = "forecast_error_mm" if "forecast_error_mm" in train_df.columns else "forecast_error"
    y_train_reg = train_df[_err_col].values
    y_val_clf = val_df["is_bust"].values
    y_val_reg = val_df[_err_col].values
    y_test_clf = test_df["is_bust"].values
    y_test_reg = test_df[_err_col].values

    print(f"Train samples: {len(X_train)}, Val samples: {len(X_val)}, Test samples: {len(X_test)}")
    print(f"Train bust rate: {np.mean(y_train_clf):.2%}")
    print(f"Val bust rate: {np.mean(y_val_clf):.2%}")
    print(f"Test bust rate: {np.mean(y_test_clf):.2%}")

    # 3. Train Model
    print("\n--- Training Shared Model Pipeline ---")
    model = ForecastReliabilityModel(use_xgboost=False)
    model.fit(X_train, y_train_clf, y_train_reg)

    # 4. Calibration & Conformal Prediction (uses CalibratorAndConformalPredictor wrapper)
    print("Calibrating probabilities & computing conformal intervals on Validation set...")
    calibrator = CalibratorAndConformalPredictor(
        base_classifier=model.classifier,
        base_regressor=model.regressor,
        method="isotonic",
    )
    calibrator.fit(X_val, y_val_clf, y_val_reg)
    
    # 5. Baselines — fit on train with feature columns merged in
    print("\n--- Fitting Strict Baselines ---")
    train_full = pd.concat([train_df.reset_index(drop=True), X_train_full.reset_index(drop=True)], axis=1)
    train_full = train_full.loc[:, ~train_full.columns.duplicated()]
    test_full  = pd.concat([test_df.reset_index(drop=True),  X_test_full.reset_index(drop=True)],  axis=1)
    test_full  = test_full.loc[:, ~test_full.columns.duplicated()]
    baselines = BaselineModels()
    baselines.fit(train_full)
    
    # Evaluate baselines on test
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    from src.evaluation.metrics import (
        compute_comprehensive_evaluation,
        compute_continuous_error_metrics,
        compute_reliability_diagram_data,
    )
    import json

    print("\n[Test Set Results vs Baselines]")
    baseline_preds = baselines.predict_proba(test_full)
    baseline_summary = {}
    for b_name, b_probs in baseline_preds.items():
        pr = average_precision_score(y_test_clf, b_probs)
        bs = brier_score_loss(y_test_clf, b_probs)
        baseline_summary[b_name] = {
            "pr_auc": round(float(pr), 4),
            "brier_score": round(float(bs), 4),
        }
        print(f"{b_name:30} | PR-AUC: {pr:.4f} | Brier: {bs:.4f}")
        
    calibrated_probs = calibrator.predict_calibrated_proba(X_test)
    pred_errors, lower_err, upper_err = calibrator.predict_error_with_intervals(X_test)
    raw_probs = model.predict_proba(X_test)
    raw_probs_pos = raw_probs[:, 1] if (len(raw_probs.shape) > 1 and raw_probs.shape[1] == 2) else raw_probs

    model_pr = average_precision_score(y_test_clf, calibrated_probs)
    model_bs = brier_score_loss(y_test_clf, calibrated_probs)
    print("-" * 60)
    print(f"{'Integrated Model (Calibrated)':30} | PR-AUC: {model_pr:.4f} | Brier: {model_bs:.4f}")

    # Comprehensive Verification Metrics (Stage 6)
    print("\n--- Computing Stage 6 Meteorological Verification Metrics ---")
    comp_eval = compute_comprehensive_evaluation(y_test_clf, calibrated_probs)
    cont_eval = compute_continuous_error_metrics(y_test_reg, pred_errors)

    raw_brier = float(np.mean((raw_probs_pos - y_test_clf) ** 2))
    conf_coverage = float(np.mean((y_test_reg >= lower_err) & (y_test_reg <= upper_err)))
    conf_width = float(np.mean(upper_err - lower_err))

    baseline_summary["Integrated_Model_Calibrated"] = {
        "pr_auc": comp_eval["pr_auc"],
        "brier_score": comp_eval["brier_score"],
        "brier_skill_score": comp_eval["brier_skill_score"],
    }

    # Lead-day breakdown
    ld_col = "lead_day" if "lead_day" in test_df.columns else None
    lead_day_breakdown = []
    if ld_col:
        for ld in range(1, 11):
            mask = (test_df[ld_col].values == ld)
            if np.sum(mask) > 0:
                y_sub = y_test_clf[mask]
                p_sub = calibrated_probs[mask]
                e_sub = pred_errors[mask]
                t_err_sub = y_test_reg[mask]
                
                try:
                    ld_pr = float(average_precision_score(y_sub, p_sub))
                except Exception:
                    ld_pr = float(np.mean(y_sub))
                try:
                    ld_roc = float(roc_auc_score(y_sub, p_sub))
                except Exception:
                    ld_roc = 0.5
                ld_bs = float(brier_score_loss(y_sub, p_sub))
                ld_mae = float(np.mean(np.abs(e_sub - t_err_sub)))

                lead_day_breakdown.append({
                    "lead_day": int(ld),
                    "samples": int(np.sum(mask)),
                    "busts": int(np.sum(y_sub)),
                    "observed_bust_rate": round(float(np.mean(y_sub)), 4),
                    "mean_pred_bust_prob": round(float(np.mean(p_sub)), 4),
                    "pr_auc": round(ld_pr, 4),
                    "roc_auc": round(ld_roc, 4),
                    "brier_score": round(ld_bs, 4),
                    "error_mae": round(ld_mae, 2),
                })

    # Regime breakdown
    reg_col = "synoptic_regime" if "synoptic_regime" in test_df.columns else None
    regime_breakdown = []
    if reg_col:
        for regime in sorted(test_df[reg_col].dropna().unique()):
            mask = (test_df[reg_col].values == regime)
            if np.sum(mask) >= 10:
                y_sub = y_test_clf[mask]
                p_sub = calibrated_probs[mask]
                try:
                    r_pr = float(average_precision_score(y_sub, p_sub))
                except Exception:
                    r_pr = float(np.mean(y_sub))
                regime_breakdown.append({
                    "regime": str(regime),
                    "samples": int(np.sum(mask)),
                    "busts": int(np.sum(y_sub)),
                    "observed_bust_rate": round(float(np.mean(y_sub)), 4),
                    "pr_auc": round(r_pr, 4),
                    "brier_score": round(float(brier_score_loss(y_sub, p_sub)), 4),
                })

    # Calibration curve
    rel_diagram = compute_reliability_diagram_data(y_test_clf, calibrated_probs, n_bins=10)
    calibration_curve = {
        "prob_pred": rel_diagram["mean_pred_prob"],
        "prob_true": rel_diagram["observed_freq"],
        "sample_counts": rel_diagram["sample_counts"],
    }

    metrics_dict = {
        "overall": {
            "test_samples": int(len(test_df)),
            "bust_class_balance": round(float(np.mean(y_test_clf)), 4),
            "pr_auc": comp_eval["pr_auc"],
            "roc_auc": comp_eval["roc_auc"],
            "brier_score_raw": round(raw_brier, 4),
            "brier_score_calibrated": comp_eval["brier_score"],
            "brier_skill_score": comp_eval["brier_skill_score"],
            "expected_calibration_error": comp_eval["expected_calibration_error"],
            "max_calibration_error": comp_eval["max_calibration_error"],
            "csi": comp_eval["csi"],
            "ets": comp_eval["ets"],
            "pod": comp_eval["pod"],
            "far": comp_eval["far"],
            "precision": comp_eval["precision"],
            "recall": comp_eval["recall"],
            "f1": comp_eval["f1"],
            "error_mae_mm": cont_eval["mae"],
            "error_rmse_mm": cont_eval["rmse"],
            "error_mbe_bias_mm": cont_eval["mbe_bias"],
            "error_pearson_r": cont_eval["pearson_r"],
            "conformal_90_coverage": round(conf_coverage, 4),
            "conformal_90_mean_width_mm": round(conf_width, 2),
            "contingency": comp_eval["contingency"],
        },
        "lead_day_breakdown": lead_day_breakdown,
        "regime_breakdown": regime_breakdown,
        "calibration_curve": calibration_curve,
        "baselines": baseline_summary,
    }

    metrics_path = os.path.join(args.output_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics_dict, f, indent=2)
    print(f"Comprehensive metrics saved to {metrics_path}")

    # 6. Ablation Study
    if args.run_ablation:
        print("\n--- Running Ablation Study ---")
        ablation = AblationStudy(pipeline.get_family_features_map())
        ablation.run_ablation(train_full, test_full)
        
    # 7. Case Studies
    if args.run_case_studies:
        print("\n--- Running Case Studies ---")
        case_eval = CaseStudyEvaluator(
            model=model,
            baselines=baselines,
            calibrator=calibrator,
            df=test_full,
            feature_names=feature_names,
        )
        case_eval.evaluate_all()
        
    print("\n--- Saving Artifacts ---")
    import joblib
    joblib.dump(pipeline, os.path.join(args.output_dir, "feature_pipeline.joblib"))
    joblib.dump(model, os.path.join(args.output_dir, "reliability_model.joblib"))
    joblib.dump(calibrator, os.path.join(args.output_dir, "calibrator.joblib"))

    # Update metadata.json
    metadata_path = os.path.join(args.output_dir, "metadata.json")
    metadata_dict = {
        "model_type": "LightGBM + CalibratedClassifierCV (Isotonic) & SplitConformalRegressor",
        "features_count": len(feature_names),
        "features": feature_names,
        "feature_families": list(pipeline.get_family_features_map().keys()),
        "data_source": args.data_source,
        "train_range": [str(train_df[time_col].min()), str(train_df[time_col].max())] if time_col else [],
        "val_range": [str(val_df[time_col].min()), str(val_df[time_col].max())] if time_col else [],
        "test_range": [str(test_df[time_col].min()), str(test_df[time_col].max())] if time_col else [],
        "updated_at": pd.Timestamp.now().isoformat(),
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata_dict, f, indent=2)
    print(f"Artifacts and metadata saved to {args.output_dir}/")

    print("\nDone. Stage 6 Evaluation & Modeling Pipeline Complete.")

if __name__ == "__main__":
    main()
