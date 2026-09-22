import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from mapie.regression import SplitConformalRegressor

class CalibratorAndConformalPredictor:
    """
    Handles probability calibration for bust classification and conformal prediction 
    for expected error magnitude.
    """
    def __init__(self, base_classifier, base_regressor, method: str = "isotonic"):
        self.method = method
        from sklearn.frozen import FrozenEstimator
        self.calibrated_clf = CalibratedClassifierCV(
            estimator=FrozenEstimator(base_classifier),
            method=self.method
        )
        # Using Mapie for conformal prediction on the regressor
        self.conformal_regressor = SplitConformalRegressor(estimator=base_regressor, prefit=True, confidence_level=0.9)

    def fit(self, X_val: pd.DataFrame, y_val_clf: np.ndarray, y_val_reg: np.ndarray):
        """
        Fits the calibrator and conformal predictor on a strict holdout validation block.
        """
        self.calibrated_clf.fit(X_val, y_val_clf)
        self.conformal_regressor.conformalize(X_val, y_val_reg)
        return self

    def predict_calibrated_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Returns calibrated probabilities for the positive class (bust).
        """
        return self.calibrated_clf.predict_proba(X)[:, 1]

    def predict_confidence(self, X: pd.DataFrame) -> np.ndarray:
        """
        Confidence = 1 - calibrated_bust_probability.
        """
        probs = self.predict_calibrated_proba(X)
        return 1.0 - probs

    def predict_error_with_intervals(self, X: pd.DataFrame) -> tuple:
        """
        Returns expected error and prediction intervals.
        """
        pred, intervals = self.conformal_regressor.predict_interval(X)
        # MAPIE 1.5 SplitConformalRegressor predict_interval returns intervals shape (n_samples, 2, n_confidence_levels)
        lower_bound = intervals[:, 0, 0]
        upper_bound = intervals[:, 1, 0]
        return pred, lower_bound, upper_bound
