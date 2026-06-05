"""
Load module — Upserts data into Supabase PostgreSQL tables.
"""

import logging
from datetime import datetime

import pandas as pd
from sqlalchemy import text

from src.db import get_engine

logger = logging.getLogger(__name__)


def ensure_stock_exists(symbol: str, company_name: str) -> int:
    """
    Ensure a stock record exists in the `stocks` table.
    Returns the stock_id.
    Also ensures necessary unique constraints exist on dependent tables.
    """
    engine = get_engine()

    # Ensure unique constraints exist on dependent tables (run in separate, isolated transactions)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE raw_stock_prices "
                    "ADD CONSTRAINT raw_stock_prices_stock_date_unique UNIQUE (stock_id, trade_date)"
                )
            )
            logger.info("Created unique constraint on raw_stock_prices(stock_id, trade_date)")
    except Exception as e:
        if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
            logger.warning("Could not create unique constraint on raw_stock_prices: %s", e)

    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE stock_features "
                    "ADD CONSTRAINT stock_features_stock_date_unique UNIQUE (stock_id, trade_date)"
                )
            )
            logger.info("Created unique constraint on stock_features(stock_id, trade_date)")
    except Exception as e:
        if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
            logger.warning("Could not create unique constraint on stock_features: %s", e)

    # Main stock check & insert (in its own transaction)
    with engine.begin() as conn:
        # Try to find existing
        result = conn.execute(
            text("SELECT stock_id FROM stocks WHERE symbol = :symbol"),
            {"symbol": symbol},
        )
        row = result.fetchone()
        if row:
            return row[0]

        # Insert new stock
        result = conn.execute(
            text(
                "INSERT INTO stocks (symbol, company_name) "
                "VALUES (:symbol, :company_name) "
                "RETURNING stock_id"
            ),
            {"symbol": symbol, "company_name": company_name},
        )
        stock_id = result.fetchone()[0]
        logger.info("Inserted stock %s (id=%d)", symbol, stock_id)
        return stock_id


def upsert_raw_prices(stock_id: int, df: pd.DataFrame) -> int:
    """
    Bulk upsert OHLCV data into `raw_stock_prices`.
    Uses ON CONFLICT to avoid duplicates on (stock_id, trade_date).

    Parameters
    ----------
    stock_id : int
        Foreign key to stocks table.
    df : pd.DataFrame
        Columns: date, open, high, low, close, volume

    Returns
    -------
    int
        Number of rows upserted.
    """
    if df.empty:
        return 0

    engine = get_engine()
    now = datetime.utcnow()

    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "stock_id": stock_id,
                "trade_date": row["date"].date() if hasattr(row["date"], "date") else row["date"],
                "open_price": float(row["open"]),
                "high_price": float(row["high"]),
                "low_price": float(row["low"]),
                "close_price": float(row["close"]),
                "volume": int(row["volume"]) if pd.notna(row["volume"]) else 0,
                "created_at": now,
            }
        )

    # Batch upsert using ON CONFLICT
    # raw_stock_prices has a unique constraint we'll handle via a DO UPDATE
    upsert_sql = text(
        """
        INSERT INTO raw_stock_prices
            (stock_id, trade_date, open_price, high_price, low_price,
             close_price, volume, created_at)
        VALUES
            (:stock_id, :trade_date, :open_price, :high_price, :low_price,
             :close_price, :volume, :created_at)
        ON CONFLICT (stock_id, trade_date) DO UPDATE SET
            open_price = EXCLUDED.open_price,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            close_price = EXCLUDED.close_price,
            volume = EXCLUDED.volume,
            created_at = EXCLUDED.created_at
        """
    )

    with engine.begin() as conn:
        conn.execute(upsert_sql, rows)

    logger.info("Upserted %d raw price rows for stock_id=%d", len(rows), stock_id)
    return len(rows)


def upsert_features(stock_id: int, df: pd.DataFrame) -> int:
    """
    Bulk upsert engineered features into `stock_features`.

    Parameters
    ----------
    stock_id : int
        Foreign key to stocks table.
    df : pd.DataFrame
        Columns: date, daily_return, price_difference, volatility,
                 ma_7, ma_30, capital_flow_indicator

    Returns
    -------
    int
        Number of rows upserted.
    """
    if df.empty:
        return 0

    engine = get_engine()
    now = datetime.utcnow()

    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "stock_id": stock_id,
                "trade_date": row["date"].date() if hasattr(row["date"], "date") else row["date"],
                "daily_return": float(row["daily_return"]) if pd.notna(row["daily_return"]) else None,
                "price_difference": float(row["price_difference"]) if pd.notna(row["price_difference"]) else None,
                "volatility": float(row["volatility"]) if pd.notna(row["volatility"]) else None,
                "ma_7": float(row["ma_7"]) if pd.notna(row["ma_7"]) else None,
                "ma_30": float(row["ma_30"]) if pd.notna(row["ma_30"]) else None,
                "capital_flow_indicator": float(row["capital_flow_indicator"]) if pd.notna(row["capital_flow_indicator"]) else None,
                "created_at": now,
            }
        )

    upsert_sql = text(
        """
        INSERT INTO stock_features
            (stock_id, trade_date, daily_return, price_difference, volatility,
             ma_7, ma_30, capital_flow_indicator, created_at)
        VALUES
            (:stock_id, :trade_date, :daily_return, :price_difference, :volatility,
             :ma_7, :ma_30, :capital_flow_indicator, :created_at)
        ON CONFLICT (stock_id, trade_date) DO UPDATE SET
            daily_return = EXCLUDED.daily_return,
            price_difference = EXCLUDED.price_difference,
            volatility = EXCLUDED.volatility,
            ma_7 = EXCLUDED.ma_7,
            ma_30 = EXCLUDED.ma_30,
            capital_flow_indicator = EXCLUDED.capital_flow_indicator,
            created_at = EXCLUDED.created_at
        """
    )

    with engine.begin() as conn:
        conn.execute(upsert_sql, rows)

    logger.info("Upserted %d feature rows for stock_id=%d", len(rows), stock_id)
    return len(rows)


def insert_predictions(records: list[dict]) -> int:
    """
    Insert prediction records into `predictions` table.

    Parameters
    ----------
    records : list[dict]
        Each dict: {stock_id, prediction_date, predicted_close, model_name}

    Returns
    -------
    int
        Number of rows inserted.
    """
    if not records:
        return 0

    engine = get_engine()
    now = datetime.utcnow()

    for r in records:
        r.setdefault("created_at", now)

    insert_sql = text(
        """
        INSERT INTO predictions
            (stock_id, prediction_date, predicted_close, model_name, created_at)
        VALUES
            (:stock_id, :prediction_date, :predicted_close, :model_name, :created_at)
        """
    )

    with engine.begin() as conn:
        conn.execute(insert_sql, records)

    logger.info("Inserted %d prediction records", len(records))
    return len(records)


def insert_anomalies(records: list[dict]) -> int:
    """
    Insert anomaly detection results into `anomalies` table.

    Parameters
    ----------
    records : list[dict]
        Each dict: {stock_id, trade_date, anomaly_score, anomaly_flag, model_name}

    Returns
    -------
    int
        Number of rows inserted.
    """
    if not records:
        return 0

    engine = get_engine()
    now = datetime.utcnow()

    from sqlalchemy import Table, MetaData

    for r in records:
        r.setdefault("created_at", now)

    metadata = MetaData()
    anomalies_table = Table("anomalies", metadata, autoload_with=engine)

    with engine.begin() as conn:
        conn.execute(anomalies_table.insert(), records)

    logger.info("Inserted %d anomaly records", len(records))
    return len(records)
