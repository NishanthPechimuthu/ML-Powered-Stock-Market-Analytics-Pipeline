"""
Prediction module.
Loads trained models and generates next-day close predictions.
"""

import os
import logging
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import joblib
from sqlalchemy import text

from src.config import MODEL_DIR
from src.db import get_engine
from src.ml.train import FEATURE_COLS

logger = logging.getLogger(__name__)


def _get_symbol_for_stock_id(stock_id: int) -> str:
    """Look up the ticker symbol for a stock_id."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT symbol FROM stocks WHERE stock_id = :stock_id"),
            {"stock_id": stock_id},
        )
        row = result.fetchone()
        return row[0] if row else f"stock_{stock_id}"


def _get_latest_features(stock_id: int, limit: int = 8) -> pd.DataFrame:
    """Get the most recent feature rows for a stock."""
    engine = get_engine()

    query = text(
        f"""
        SELECT
            f.trade_date,
            f.daily_return,
            f.price_difference,
            f.volatility,
            f.ma_7,
            f.ma_30,
            f.capital_flow_indicator
        FROM stock_features f
        WHERE f.stock_id = :stock_id
        ORDER BY f.trade_date DESC
        LIMIT {limit}
        """
    )

    with engine.connect() as conn:
        result = conn.execute(query, {"stock_id": stock_id})
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    return df


def predict_next_close(
    stock_id: int,
    model_type: str = "linear_regression",
) -> list[dict] | None:
    """
    Predict the next-day closing price for a stock for the latest 8 days.

    Parameters
    ----------
    stock_id : int
        The stock to predict.
    model_type : str
        Which trained model to use.

    Returns
    -------
    list[dict] or None
        List of predictions:
        {
            "stock_id": int,
            "prediction_date": date,
            "predicted_close": float,
            "model_name": str,
        }
    """
    symbol = _get_symbol_for_stock_id(stock_id)

    # Load model
    model_filename = f"{symbol}_{model_type}.joblib"
    model_path = os.path.join(MODEL_DIR, model_filename)

    if not os.path.exists(model_path):
        logger.warning("No trained model found at %s", model_path)
        return None

    model = joblib.load(model_path)

    # Get latest features
    features_df = _get_latest_features(stock_id, limit=8)

    if features_df.empty:
        logger.warning("No features found for stock_id=%d", stock_id)
        return None

    predictions = []
    
    for _, row in features_df.iterrows():
        # Prepare feature vector
        feature_values = row[FEATURE_COLS].astype(float).values.reshape(1, -1)

        # Check for NaN
        if np.isnan(feature_values).any():
            logger.warning("NaN in features for %s on %s, skipping prediction", symbol, row["trade_date"])
            continue

        # Predict
        predicted_close = float(model.predict(feature_values)[0])

        # The prediction is for the next trading day
        trade_date = pd.to_datetime(row["trade_date"])
        prediction_date = trade_date + timedelta(days=1)

        # Skip weekends
        while prediction_date.weekday() >= 5:
            prediction_date += timedelta(days=1)

        predictions.append({
            "stock_id": stock_id,
            "prediction_date": prediction_date.date(),
            "predicted_close": round(predicted_close, 2),
            "model_name": model_type,
        })

    logger.info(
        "Generated %d predictions for %s using %s",
        len(predictions), symbol, model_type
    )

    return predictions if predictions else None
