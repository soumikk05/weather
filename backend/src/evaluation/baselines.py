import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

class BaselineModels:
    """
    Implements 6 strict baselines for Forecast Bust prediction:
    1. Climatological bust frequency
    2. Location + season + lead historical bust rate
    3. Ensemble spread alone
    4. Recent-error persistence (30-day)
    5. Ensemble spread + recent error
    6. NWP-only features (no recent error, no analogs)
    """
    def __init__(self):
        self.climatology_freq = None
        self.loc_season_lead_rates = None
        self.ensemble_model = None
        self.recent_error_model = None
        self.ensemble_recent_model = None
        self.nwp_only_model = None

    def fit(self, train_df: pd.DataFrame):
        # 1. Climatological bust frequency
        self.climatology_freq = train_df["is_bust"].mean()

        # 2. Location + season + lead historical bust rate
        # Assuming we have region/subdivision, month/season, lead_day
        group_cols = ["region", "lead_day"] 
        if "season" in train_df.columns:
            group_cols.append("season")
        elif "month" in train_df.columns:
            group_cols.append("month")
            
        # We need to make sure we don't fail if some columns are missing
        existing_cols = [c for c in group_cols if c in train_df.columns]
        if existing_cols:
            self.loc_season_lead_rates = train_df.groupby(existing_cols)["is_bust"].mean().reset_index()
            self.loc_season_lead_rates.rename(columns={"is_bust": "pred_prob"}, inplace=True)
            self.loc_season_lead_cols = existing_cols
        
        # Helper for logistic regression baselines
        def fit_lr(features):
            X = train_df[features].fillna(0)
            y = train_df["is_bust"]
            model = Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', StandardScaler()),
                ('lr', LogisticRegression(class_weight='balanced', random_state=42, max_iter=500))
            ])
            model.fit(X, y)
            return model

        # 3. Ensemble spread alone — new column is ens_spread_rainfall
        ens_col = "ens_spread_rainfall" if "ens_spread_rainfall" in train_df.columns else ("ensemble_spread" if "ensemble_spread" in train_df.columns else None)
        if ens_col:
            self.ensemble_model = fit_lr([ens_col])
            self._ens_col = ens_col

        # 4. Recent-error persistence (30-day)
        recent_cols = [c for c in train_df.columns if c.startswith("recent_error_") or c == "prior_day_verified_error"]
        if recent_cols:
            self.recent_error_model = fit_lr(recent_cols)
        
        # 5. Ensemble spread + recent error
        ens_recent_cols = ([ens_col] if ens_col else []) + recent_cols
        if ens_recent_cols:
            self.ensemble_recent_model = fit_lr(ens_recent_cols)
            
        # 6. NWP-only features — match new feature schema names
        nwp_cols = [c for c in train_df.columns if c in [
            "ens_spread_rainfall", "ens_spread_mslp", "fcst_mslp_hpa", "vertical_wind_shear",
            "fcst_rh_700_pct", "fcst_cape_jkg", "baroclinic_gradient_proxy", "convective_vulnerability",
            # legacy names for backward compat
            "ensemble_spread", "pressure_gradient_hpa", "wind_shear_mps", "moisture_convergence",
            "cape_jkg", "surface_temp_c",
        ]]
        if nwp_cols:
            self.nwp_only_model = fit_lr(nwp_cols)
            self._nwp_cols = nwp_cols

        return self

    def predict_proba(self, test_df: pd.DataFrame) -> dict:
        """
        Returns a dictionary mapping baseline name to predicted probabilities.
        """
        results = {}
        n = len(test_df)
        
        # 1. Climatology
        results["Baseline_1_Climatology"] = np.full(n, self.climatology_freq)
        
        # 2. Location + Season + Lead
        if self.loc_season_lead_rates is not None:
            merged = test_df.merge(self.loc_season_lead_rates, on=self.loc_season_lead_cols, how="left")
            # Fill NaNs with global climatology
            results["Baseline_2_LocSeasonLead"] = merged["pred_prob"].fillna(self.climatology_freq).values
            
        # Helpers
        def predict_lr(model, features):
            if model is not None:
                return model.predict_proba(test_df[features].fillna(0))[:, 1]
            return np.full(n, self.climatology_freq)

        # 3. Ensemble spread alone
        ens_col = getattr(self, "_ens_col", None)
        if self.ensemble_model and ens_col and ens_col in test_df.columns:
            results["Baseline_3_EnsembleSpread"] = predict_lr(self.ensemble_model, [ens_col])
            
        # 4. Recent-error
        recent_cols = [c for c in test_df.columns if c.startswith("recent_error_") or c == "prior_day_verified_error"]
        if self.recent_error_model and recent_cols:
            results["Baseline_4_RecentError"] = predict_lr(self.recent_error_model, recent_cols)
            
        # 5. Ensemble + Recent
        ens_recent_cols = ([ens_col] if ens_col and ens_col in test_df.columns else []) + recent_cols
        if self.ensemble_recent_model and ens_recent_cols:
            results["Baseline_5_EnsRecent"] = predict_lr(self.ensemble_recent_model, ens_recent_cols)
            
        # 6. NWP Only
        nwp_cols = getattr(self, "_nwp_cols", [])
        nwp_cols = [c for c in nwp_cols if c in test_df.columns]
        if self.nwp_only_model and nwp_cols:
            results["Baseline_6_NWPOnly"] = predict_lr(self.nwp_only_model, nwp_cols)
            
        return results
