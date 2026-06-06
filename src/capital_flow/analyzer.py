"""
Capital flow analysis module.
Estimates market inflow and outflow using price movement and volume.
"""

import logging

import pandas as pd
import numpy as np
from sqlalchemy import text

from src.db import get_engine

logger = logging.getLogger(__name__)


def compute_capital_flow(stock_id: int) -> pd.DataFrame:
    """
    Compute capital flow metrics for a stock.

    Uses a simplified Money Flow Index (MFI) approach:
    - Typical Price = (High + Low + Close) / 3
    - Raw Money Flow = Typical Price × Volume
    - If Typical Price > Previous Typical Price → Positive (Inflow)
    - If Typical Price < Previous Typical Price → Negative (Outflow)

    Parameters
    ----------
    stock_id : int
        The stock to analyze.

    Returns
    -------
    pd.DataFrame
        Columns: trade_date, typical_price, raw_money_flow,
                 flow_direction, inflow, outflow, mfi_14,
                 net_flow, cumulative_flow
    """
    engine = get_engine()

    query = text(
        """
        SELECT trade_date, open_price as open, high_price as high,
               low_price as low, close_price as close, volume
        FROM raw_stock_prices
        WHERE stock_id = :stock_id
        ORDER BY trade_date ASC
        """
    )

    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"stock_id": stock_id})

    if df.empty or len(df) < 15:
        logger.warning("Insufficient data for capital flow (stock_id=%d)", stock_id)
        return pd.DataFrame()

    df["trade_date"] = pd.to_datetime(df["trade_date"])

    # Typical Price
    df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3

    # Raw Money Flow
    df["raw_money_flow"] = df["typical_price"] * df["volume"]

    # Flow direction: 1 = inflow (up day), -1 = outflow (down day)
    df["flow_direction"] = np.where(
        df["typical_price"] > df["typical_price"].shift(1), 1,
        np.where(df["typical_price"] < df["typical_price"].shift(1), -1, 0)
    )

    # Separate inflow and outflow
    df["inflow"] = np.where(
        df["flow_direction"] == 1, df["raw_money_flow"], 0
    )
    df["outflow"] = np.where(
        df["flow_direction"] == -1, df["raw_money_flow"], 0
    )

    # 14-day Money Flow Index
    inflow_14 = df["inflow"].rolling(window=14, min_periods=1).sum()
    outflow_14 = df["outflow"].rolling(window=14, min_periods=1).sum()

    money_ratio = inflow_14 / outflow_14.replace(0, np.nan)
    df["mfi_14"] = 100 - (100 / (1 + money_ratio))

    # Net flow per day
    df["net_flow"] = df["inflow"] - df["outflow"]

    # Cumulative net flow
    df["cumulative_flow"] = df["net_flow"].cumsum()

    result = df[
        [
            "trade_date", "typical_price", "raw_money_flow",
            "flow_direction", "inflow", "outflow", "mfi_14",
            "net_flow", "cumulative_flow",
        ]
    ].copy()

    logger.info("Computed capital flow for stock_id=%d (%d rows)", stock_id, len(result))

    return result
