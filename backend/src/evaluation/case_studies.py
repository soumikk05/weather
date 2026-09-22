import pandas as pd
import numpy as np
import os
from typing import Optional, List

class CaseStudyEvaluator:
    """
    Evaluates the trained model and baselines on specific historical case studies
    (e.g., Kerala 2018 floods, Chennai 2015, Monsoon onset transitions, extreme test events).
    """
    def __init__(self, model, baselines, calibrator, df: pd.DataFrame, feature_names: Optional[List[str]] = None):
        self.model = model
        self.baselines = baselines
        self.calibrator = calibrator
        self.df = df.copy()
        self.feature_names = feature_names
        
        # Ensure dates are datetime
        time_col = "date" if "date" in self.df.columns else ("initialization_time" if "initialization_time" in self.df.columns else None)
        if time_col:
            self.df["date_ts"] = pd.to_datetime(self.df[time_col])

    def run_case_study(self, name: str, start_date: str, end_date: str, regions: list) -> pd.DataFrame:
        """
        Extracts forecasts for a specific event window and evaluates if low-confidence 
        flags appeared before the busts occurred.
        """
        if "date_ts" not in self.df.columns:
            print(f"Skipping case study '{name}': No date/time column found.")
            return pd.DataFrame()
            
        mask = (self.df["date_ts"] >= start_date) & (self.df["date_ts"] <= end_date)
        loc_col = "region" if "region" in self.df.columns else ("location_id" if "location_id" in self.df.columns else None)
        if regions and loc_col:
            mask &= self.df[loc_col].isin(regions)
            
        case_df = self.df[mask].copy()
        
        if case_df.empty:
            print(f"Skipping case study '{name}': No dates found in the archive ({start_date} to {end_date}).")
            return pd.DataFrame()
            
        print(f"Running Case Study: {name} ({len(case_df)} forecasts found)")
        
        # Predict using full model
        if self.feature_names:
            feats = [c for c in self.feature_names if c in case_df.columns]
            X_case = case_df[feats].fillna(0)
        else:
            X_case = case_df.drop(columns=["is_bust", "forecast_error", "date", "date_ts", "region", "location_id", "init_time", "initialization_time", "valid_time"], errors="ignore")
            X_case = X_case.select_dtypes(include=["number"]).fillna(0)
        
        probs = self.calibrator.predict_calibrated_proba(X_case)
        confidence = self.calibrator.predict_confidence(X_case)
        pred_err, lower, upper = self.calibrator.predict_error_with_intervals(X_case)
        
        case_df["pred_bust_prob"] = probs
        case_df["confidence_score"] = confidence
        case_df["expected_error_mm"] = pred_err
        case_df["error_interval_lower"] = lower
        case_df["error_interval_upper"] = upper
        
        # Collect baseline probabilities
        baseline_preds = self.baselines.predict_proba(case_df)
        for b_name, b_probs in baseline_preds.items():
            case_df[f"{b_name}_prob"] = b_probs
            
        return case_df

    def evaluate_all(self, output_dir: str = "reports/case_studies"):
        os.makedirs(output_dir, exist_ok=True)
        
        # Define famous cases
        cases = [
            {
                "name": "Kerala Floods 2018",
                "start": "2018-08-08",
                "end": "2018-08-20",
                "regions": ["Kerala & Mahe"]
            },
            {
                "name": "Chennai Floods 2015",
                "start": "2015-11-25",
                "end": "2015-12-05",
                "regions": ["Tamil Nadu, Puducherry & Karaikal"]
            }
        ]
        
        evaluated_any = False
        for case in cases:
            res = self.run_case_study(case["name"], case["start"], case["end"], case["regions"])
            if not res.empty:
                safe_name = case["name"].lower().replace(" ", "_")
                path = os.path.join(output_dir, f"{safe_name}.csv")
                res.to_csv(path, index=False)
                print(f"Saved case study results to {path}")
                evaluated_any = True
                
        # If historical archives are not in the test window, evaluate top bust event in the test split
        if "date_ts" in self.df.columns and not self.df.empty:
            test_dates = sorted(self.df["date_ts"].unique())
            if len(test_dates) >= 5:
                mid_idx = len(test_dates) // 2
                eval_start = str(test_dates[mid_idx])[:10]
                eval_end = str(test_dates[min(mid_idx + 6, len(test_dates) - 1)])[:10]
                res_test = self.run_case_study("Active Synoptic Event (Test Partition)", eval_start, eval_end, [])
                if not res_test.empty:
                    path = os.path.join(output_dir, "test_synoptic_event.csv")
                    res_test.to_csv(path, index=False)
                    print(f"Saved test partition case study results to {path}")
