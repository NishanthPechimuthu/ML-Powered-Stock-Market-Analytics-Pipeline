"""
Feature engineering module.
Computes technical indicators from raw OHLCV data.
"""

import logging

import pandas as pd
import numpy as np
from sqlalchemy import text

from src.db import get_engine

logger = logging.getLogger(__name__)


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute engineered features from raw OHLCV data.

    Input columns : date, open, high, low, close, volume
    Output columns: date, daily_return, price_difference, volatility,
                    ma_7, ma_30, capital_flow_indicator

    Parameters
    ----------
    df : pd.DataFrame
        Raw OHLCV data sorted by date ascending.

    Returns
    -------
    pd.DataFrame
        Feature DataFrame aligned with input dates.
    """
    if df.empty or len(df) < 2:
        logger.warning("Not enough data to compute features (rows=%d)", len(df))
        return pd.DataFrame()

    df = df.sort_values("date").reset_index(drop=True)

    features = pd.DataFrame()
    features["date"] = df["date"]

    # Daily return: (close - prev_close) / prev_close
    features["daily_return"] = df["close"].pct_change()

    # Price difference: close - open (intraday movement)
    features["price_difference"] = df["close"] - df["open"]

    # Volatility: (high - low) / open (intraday range as % of open)
    features["volatility"] = (df["high"] - df["low"]) / df["open"]

    # Rolling mean: 7-day moving average of close
    features["ma_7"] = df["close"].rolling(window=7, min_periods=1).mean()

    # Rolling mean: 30-day moving average of close
    features["ma_30"] = df["close"].rolling(window=30, min_periods=1).mean()

    # Capital flow indicator: volume * (close - open) / open
    # Positive = buying pressure, Negative = selling pressure
    features["capital_flow_indicator"] = (
        df["volume"] * (df["close"] - df["open"]) / df["open"]
    )

    logger.info("Computed features for %d rows", len(features))
    return features


def compute_features_for_stock(stock_id: int) -> pd.DataFrame:
    """
    Load raw prices from DB for a stock and compute features.

    Parameters
    ----------
    stock_id : int
        The stock_id from the stocks table.

    Returns
    -------
    pd.DataFrame
        Computed features with 'date' column.
    """
    engine = get_engine()

    query = text(
        """
        SELECT trade_date as date, open_price as open, high_price as high,
               low_price as low, close_price as close, volume
        FROM raw_stock_prices
        WHERE stock_id = :stock_id
        ORDER BY trade_date ASC
        """
    )

    with engine.connect() as conn:
        result = conn.execute(query, {"stock_id": stock_id})
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    if df.empty:
        logger.warning("No raw prices found for stock_id=%d", stock_id)
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"])

    return compute_features(df)
