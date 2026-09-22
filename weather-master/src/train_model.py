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
        if not os.path.exists(args.data_path):
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
    test_full  = pd.concat([test_df.reset_index(drop=True),  X_test_full.reset_index(drop=True)],  axis=1)
    baselines = BaselineModels()
    baselines.fit(train_full)
    
    # Evaluate baselines on test
    from sklearn.metrics import average_precision_score, brier_score_loss
    print("\n[Test Set Results vs Baselines]")
    
    baseline_preds = baselines.predict_proba(test_full)
    for b_name, b_probs in baseline_preds.items():
        pr = average_precision_score(y_test_clf, b_probs)
        bs = brier_score_loss(y_test_clf, b_probs)
        print(f"{b_name:30} | PR-AUC: {pr:.4f} | Brier: {bs:.4f}")
        
    calibrated_probs = calibrator.predict_calibrated_proba(X_test)
    model_pr = average_precision_score(y_test_clf, calibrated_probs)
    model_bs = brier_score_loss(y_test_clf, calibrated_probs)
    print("-" * 60)
    print(f"{'Integrated Model (Calibrated)':30} | PR-AUC: {model_pr:.4f} | Brier: {model_bs:.4f}")

    # 6. Ablation Study
    if args.run_ablation:
        print("\n--- Running Ablation Study ---")
        ablation = AblationStudy(pipeline.get_family_features_map())
        # Provide train_df and test_df with features merged in
        train_full = pd.concat([train_df, X_train_full], axis=1)
        test_full = pd.concat([test_df, X_test_full], axis=1)
        ablation.run_ablation(train_full, test_full)
        
    # 7. Case Studies
    if args.run_case_studies:
        print("\n--- Running Case Studies ---")
        # Wrapper object for compatibility with CaseStudyEvaluator
        # calibrator is now a CalibratorAndConformalPredictor, use it directly
                
        case_eval = CaseStudyEvaluator(model, baselines, calibrator, pd.concat([test_df, X_test_full], axis=1))
        case_eval.evaluate_all()
        
    print("\n--- Saving Artifacts ---")
    import joblib
    joblib.dump(pipeline, os.path.join(args.output_dir, "feature_pipeline.joblib"))
    joblib.dump(model, os.path.join(args.output_dir, "reliability_model.joblib"))
    # calibrator wraps both CalibratedClassifierCV and SplitConformalRegressor
    joblib.dump(calibrator, os.path.join(args.output_dir, "calibrator.joblib"))
    print(f"Artifacts saved to {args.output_dir}/")

    print("\nDone. Stage 4/5 Models Complete.")

if __name__ == "__main__":
    main()
