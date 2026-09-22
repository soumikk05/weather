import os
from typing import Tuple, Dict, Any
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler

class ForecastReliabilityModel:
    """
    Unified model pipeline for predicting Forecast Bust Probability and Expected Error.
    Uses LightGBM. Can be extended to use XGBoost.
    """
    def __init__(self, use_xgboost: bool = False):
        self.use_xgboost = use_xgboost
        self.classifier = None
        self.regressor = None

    def _build_model(self, is_classifier: bool):
        if self.use_xgboost:
            from xgboost import XGBClassifier, XGBRegressor
            if is_classifier:
                return XGBClassifier(n_estimators=150, max_depth=5, learning_rate=0.05, tree_method="hist", random_state=42)
            else:
                return XGBRegressor(n_estimators=150, max_depth=5, learning_rate=0.05, tree_method="hist", random_state=42)
        else:
            if is_classifier:
                return LGBMClassifier(n_estimators=150, max_depth=5, learning_rate=0.05, random_state=42)
            else:
                return LGBMRegressor(n_estimators=150, max_depth=5, learning_rate=0.05, random_state=42)

    def fit(self, X_train: pd.DataFrame, y_train_clf: np.ndarray, y_train_reg: np.ndarray):
        """
        Fits both the classifier (bust probability) and the regressor (expected error).
        """
        self.classifier = self._build_model(is_classifier=True)
        self.classifier.fit(X_train, y_train_clf)

        self.regressor = self._build_model(is_classifier=False)
        self.regressor.fit(X_train, y_train_reg)

        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return bust probability predictions (n_samples, 2)."""
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)
        return self.classifier.predict_proba(X)
        
    def predict_error(self, X: pd.DataFrame) -> np.ndarray:
        """Return expected error magnitude predictions."""
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)
        return self.regressor.predict(X)
