import pandas as pd
import os

class CaseStudyEvaluator:
    """
    Evaluates the trained model and baselines on specific historical case studies
    (e.g., Kerala 2018 floods, Chennai 2015, Monsoon onset transitions).
    """
    def __init__(self, model, baselines, calibrator, df: pd.DataFrame):
        self.model = model
        self.baselines = baselines
        self.calibrator = calibrator
        self.df = df
        
        # Ensure dates are datetime
        if "date" in self.df.columns:
            self.df["date_ts"] = pd.to_datetime(self.df["date"])

    def run_case_study(self, name: str, start_date: str, end_date: str, regions: list) -> pd.DataFrame:
        """
        Extracts forecasts for a specific event window and evaluates if low-confidence 
        flags appeared before the busts occurred.
        """
        if "date_ts" not in self.df.columns:
            print(f"Skipping case study '{name}': No 'date' column found.")
            return pd.DataFrame()
            
        mask = (self.df["date_ts"] >= start_date) & (self.df["date_ts"] <= end_date)
        if regions:
            mask &= self.df["region"].isin(regions)
            
        case_df = self.df[mask].copy()
        
        if case_df.empty:
            print(f"Skipping case study '{name}': No dates found in the archive ({start_date} to {end_date}).")
            return pd.DataFrame()
            
        print(f"Running Case Study: {name} ({len(case_df)} forecasts found)")
        
        # Predict using full model
        X_case = case_df.drop(columns=["is_bust", "forecast_error", "date", "date_ts", "region", "init_time", "valid_time"], errors="ignore")
        # Ensure only numeric columns
        X_case = X_case.select_dtypes(include=["number"]).fillna(0)
        
        probs = self.calibrator.predict_calibrated_proba(X_case)
        confidence = 1.0 - probs
        pred_err, lower, upper = self.calibrator.predict_error_with_intervals(X_case)
        
        case_df["pred_bust_prob"] = probs
        case_df["confidence"] = confidence
        case_df["expected_error"] = pred_err
        
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
        
        for case in cases:
            res = self.run_case_study(case["name"], case["start"], case["end"], case["regions"])
            if not res.empty:
                safe_name = case["name"].lower().replace(" ", "_")
                path = os.path.join(output_dir, f"{safe_name}.csv")
                res.to_csv(path, index=False)
                print(f"Saved case study results to {path}")
