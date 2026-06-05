"""
Transform module — Data cleaning and validation.
"""

import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def clean_stock_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean raw stock data.

    Steps:
    1. Drop rows with any null OHLCV values.
    2. Remove duplicate dates.
    3. Enforce correct dtypes.
    4. Sort by date ascending.

    Parameters
    ----------
    df : pd.DataFrame
        Raw data with columns: date, open, high, low, close, volume

    Returns
    -------
    pd.DataFrame
        Cleaned data.
    """
    if df.empty:
        logger.warning("Received empty DataFrame, nothing to clean")
        return df

    initial_rows = len(df)

    # Ensure date column is datetime
    df["date"] = pd.to_datetime(df["date"])

    # Drop rows where any OHLCV value is null
    ohlcv_cols = ["open", "high", "low", "close", "volume"]
    df = df.dropna(subset=ohlcv_cols)

    # Remove duplicate dates (keep first occurrence)
    df = df.drop_duplicates(subset=["date"], keep="first")

    # Enforce numeric types
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").astype("Int64")

    # Sort by date ascending
    df = df.sort_values("date").reset_index(drop=True)

    dropped = initial_rows - len(df)
    if dropped > 0:
        logger.info("Cleaned data: dropped %d rows (of %d)", dropped, initial_rows)

    return df


def validate_data_quality(df: pd.DataFrame, symbol: str = "") -> dict:
    """
    Run data quality checks on cleaned stock data.

    Checks:
    1. No null values remain.
    2. No zero-volume rows.
    3. Prices are positive.
    4. High >= Low for every row.
    5. No gaps > 5 calendar days (to allow for weekends/holidays).

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned stock data.
    symbol : str
        Ticker symbol for logging.

    Returns
    -------
    dict
        Validation results: {"passed": bool, "issues": list[str]}
    """
    issues: list[str] = []

    if df.empty:
        issues.append("DataFrame is empty")
        return {"passed": False, "issues": issues}

    # Check for remaining nulls
    null_counts = df[["open", "high", "low", "close", "volume"]].isnull().sum()
    if null_counts.any():
        issues.append(f"Null values found: {null_counts[null_counts > 0].to_dict()}")

    # Check for zero volume
    zero_vol = (df["volume"] == 0).sum()
    if zero_vol > 0:
        issues.append(f"{zero_vol} rows with zero volume")

    # Check prices are positive
    for col in ["open", "high", "low", "close"]:
        neg = (df[col] <= 0).sum()
        if neg > 0:
            issues.append(f"{neg} rows with non-positive {col}")

    # Check high >= low
    invalid_hl = (df["high"] < df["low"]).sum()
    if invalid_hl > 0:
        issues.append(f"{invalid_hl} rows where high < low")

    # Check for excessive date gaps (> 5 calendar days)
    df_sorted = df.sort_values("date")
    date_diffs = df_sorted["date"].diff().dt.days
    big_gaps = date_diffs[date_diffs > 5]
    if len(big_gaps) > 0:
        issues.append(
            f"{len(big_gaps)} date gaps > 5 days found "
            f"(max gap: {big_gaps.max()} days)"
        )

    passed = len(issues) == 0
    status = "PASSED" if passed else "FAILED"
    logger.info("Validation %s for %s: %d issues", status, symbol, len(issues))

    for issue in issues:
        logger.warning("  [%s] %s", symbol, issue)

    return {"passed": passed, "issues": issues}
