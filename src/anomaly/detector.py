"""
Anomaly detection module.
Detects abnormal volume, returns, volatility, and price movements.
"""

import logging
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy import text

from src.db import get_engine

logger = logging.getLogger(__name__)

# Features used for anomaly detection
ANOMALY_FEATURES = ["daily_return", "volatility", "volume_change_pct"]


def _get_stock_data(stock_id: int) -> pd.DataFrame:
    """
    Load raw prices and features for anomaly detection.
    Computes volume_change_pct from raw data.
    """
    engine = get_engine()

    query = text(
        """
        SELECT
            r.trade_date,
            r.close_price,
            r.volume,
            f.daily_return,
            f.volatility
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

    if df.empty:
        return df

    # Compute volume change %
    df["volume_change_pct"] = df["volume"].pct_change()

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


def detect_anomalies(
    stock_id: int,
    method: str = "isolation_forest",
    contamination: float = 0.05,
) -> list[dict]:
    """
    Detect anomalies in stock data using Isolation Forest.

    Parameters
    ----------
    stock_id : int
        The stock to analyze.
    method : str
        Detection method: "isolation_forest"
    contamination : float
        Expected proportion of anomalies (default 5%).

    Returns
    -------
    list[dict]
        Anomaly records ready for insertion:
        [{stock_id, trade_date, anomaly_score, anomaly_flag, model_name}, ...]
    """
    symbol = _get_symbol_for_stock_id(stock_id)
    logger.info("Running anomaly detection (%s) for %s", method, symbol)

    df = _get_stock_data(stock_id)

    if df.empty or len(df) < 30:
        logger.warning(
            "Insufficient data for anomaly detection on %s (%d rows)",
            symbol, len(df),
        )
        return []

    # Drop rows with NaN in anomaly features
    df_clean = df.dropna(subset=ANOMALY_FEATURES).copy()

    if len(df_clean) < 30:
        logger.warning("Too few clean rows for %s: %d", symbol, len(df_clean))
        return []

    X = df_clean[ANOMALY_FEATURES].values

    if method == "isolation_forest":
        model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
            n_jobs=-1,
        )
        model.fit(X)

        # Predictions: 1 = normal, -1 = anomaly
        labels = model.predict(X)
        scores = model.decision_function(X)

        df_clean["anomaly_flag"] = labels == -1
        df_clean["anomaly_score"] = scores
    else:
        raise ValueError(f"Unknown anomaly method: {method}")

    # Build records for insertion
    records = []
    for _, row in df_clean.iterrows():
        records.append(
            {
                "stock_id": stock_id,
                "trade_date": row["trade_date"],
                "anomaly_score": float(row["anomaly_score"]),
                "anomaly_flag": bool(row["anomaly_flag"]),
                "model_name": method,
            }
        )

    anomaly_count = df_clean["anomaly_flag"].sum()
    logger.info(
        "Detected %d anomalies out of %d data points for %s",
        anomaly_count, len(df_clean), symbol,
    )

    return records
