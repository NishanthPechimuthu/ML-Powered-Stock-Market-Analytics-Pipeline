"""
Model training module.
Trains regression models to predict next-day closing price.
"""

import os
import logging

import pandas as pd
import numpy as np
import joblib
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.ensemble import RandomForestRegressor, StackingRegressor
from xgboost import XGBRegressor
from sqlalchemy import text

from src.config import MODEL_DIR, TARGET_STOCKS
from src.db import get_engine
from src.ml.evaluate import evaluate_model

logger = logging.getLogger(__name__)

# Feature columns used for training
FEATURE_COLS = [
    "daily_return",
    "price_difference",
    "volatility",
    "ma_7",
    "ma_30",
    "capital_flow_indicator",
]

MODEL_REGISTRY = {
    "linear_regression": LinearRegression,
    "xgboost": lambda: XGBRegressor(n_estimators=100, random_state=42, n_jobs=-1),
    "stacking": lambda: StackingRegressor(
        estimators=[
            ("lr", LinearRegression()),
            ("xgb", XGBRegressor(n_estimators=100, random_state=42, n_jobs=-1)),
        ],
        final_estimator=RidgeCV(),
        n_jobs=-1,
    ),
}


def _get_training_data(stock_id: int) -> pd.DataFrame:
    """
    Load joined raw prices + features for a stock.
    Creates the target: next-day close price (shifted).
    """
    engine = get_engine()

    query = text(
        """
        SELECT
            r.trade_date,
            r.close_price,
            f.daily_return,
            f.price_difference,
            f.volatility,
            f.ma_7,
            f.ma_30,
            f.capital_flow_indicator
        FROM raw_stock_prices r
        JOIN stock_features f
            ON r.stock_id = f.stock_id AND r.trade_date = f.trade_date
        WHERE r.stock_id = :stock_id
        ORDER BY r.trade_date ASC
        """
    )

    with engine.connect() as conn:
        result = conn.execute(query, {"stock_id": stock_id})
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    return df


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


def train_model(
    stock_id: int,
    model_type: str = "linear_regression",
) -> dict:
    """
    Train a regression model for next-day close prediction.

    Parameters
    ----------
    stock_id : int
        Stock to train on.
    model_type : str
        One of: "linear_regression", "random_forest"

    Returns
    -------
    dict
        {
            "model_path": str,
            "metrics": {"rmse": float, "mae": float, "r2": float},
            "train_size": int,
            "test_size": int,
        }
    """
    symbol = _get_symbol_for_stock_id(stock_id)
    logger.info("Training %s model for %s (id=%d)", model_type, symbol, stock_id)

    # Load data
    df = _get_training_data(stock_id)

    if df.empty or len(df) < 60:
        raise ValueError(
            f"Insufficient data for {symbol}: {len(df)} rows (need ≥60)"
        )

    # Create target: next-day close
    df["target"] = df["close_price"].shift(-1)
    df = df.dropna(subset=FEATURE_COLS + ["target"])

    X = df[FEATURE_COLS].astype(float).values
    y = df["target"].astype(float).values

    # Chronological train/test split (80/20)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    # Train
    if model_type in MODEL_REGISTRY:
        model_factory = MODEL_REGISTRY[model_type]
        model = model_factory() if callable(model_factory) and not isinstance(model_factory, type) else model_factory()
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    metrics = evaluate_model(y_test, y_pred)

    # Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_filename = f"{symbol}_{model_type}.joblib"
    model_path = os.path.join(MODEL_DIR, model_filename)
    joblib.dump(model, model_path)

    logger.info(
        "Saved %s model for %s to %s (R²=%.4f)",
        model_type, symbol, model_path, metrics["r2"],
    )

    return {
        "model_path": model_path,
        "metrics": metrics,
        "train_size": len(X_train),
        "test_size": len(X_test),
    }
