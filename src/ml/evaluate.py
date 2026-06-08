"""
Model evaluation utilities.
"""

import logging

import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

logger = logging.getLogger(__name__)


def evaluate_model(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Compute evaluation metrics for regression models.

    Parameters
    ----------
    y_true : array-like
        Actual values.
    y_pred : array-like
        Predicted values.

    Returns
    -------
    dict
        {"rmse": float, "mae": float, "r2": float}
    """
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))

    logger.info("Model metrics — RMSE: %.4f | MAE: %.4f | R²: %.4f", rmse, mae, r2)

    return {"rmse": rmse, "mae": mae, "r2": r2}
