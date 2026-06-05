"""
Historical Backfill DAG
=======================
One-time DAG that downloads ~1 year of historical stock data for all target
stocks, validates quality, loads into Supabase, and generates initial features.

Schedule: @once (manually triggered)
"""

import sys
import os
import logging

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# Ensure src is importable
sys.path.insert(0, "/opt/airflow")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default DAG args
# ---------------------------------------------------------------------------
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


# ---------------------------------------------------------------------------
# Task functions
# ---------------------------------------------------------------------------
def ensure_stocks(**kwargs):
    """Insert all target stocks into the stocks table if not present."""
    from src.config import TARGET_STOCKS
    from src.etl.load import ensure_stock_exists

    stock_ids = {}
    for symbol, name in TARGET_STOCKS.items():
        sid = ensure_stock_exists(symbol, name)
        stock_ids[symbol] = sid
        logger.info("Stock %s → id=%d", symbol, sid)

    # Push to XCom for downstream tasks
    kwargs["ti"].xcom_push(key="stock_ids", value=stock_ids)


def extract_validate_load_historical(**kwargs):
    """Fetch historical data, validate, and load to raw_stock_prices."""
    import pandas as pd
    from src.config import TARGET_STOCKS, BACKFILL_START, BACKFILL_END
    from src.etl.extract import fetch_historical_candles
    from src.etl.transform import clean_stock_data, validate_data_quality
    from src.etl.load import upsert_raw_prices

    stock_ids = kwargs["ti"].xcom_pull(
        task_ids="ensure_stocks", key="stock_ids"
    )

    for symbol in TARGET_STOCKS:
        sid = stock_ids[symbol]
        
        # 1. Extract
        df = fetch_historical_candles(symbol, BACKFILL_START, BACKFILL_END)
        logger.info("Extracted %d rows for %s", len(df), symbol)
        
        # 2. Validate & Clean
        df = clean_stock_data(df)
        report = validate_data_quality(df, symbol=symbol)
        if not report["passed"]:
            logger.warning("Validation issues for %s: %s", symbol, report["issues"])
            
        # 3. Load
        count = upsert_raw_prices(sid, df)
        logger.info("Loaded %d rows for %s (stock_id=%d)", count, symbol, sid)


def generate_features(**kwargs):
    """Compute features from raw prices and store in stock_features."""
    from src.config import TARGET_STOCKS
    from src.features.engineering import compute_features_for_stock
    from src.etl.load import upsert_features

    stock_ids = kwargs["ti"].xcom_pull(
        task_ids="ensure_stocks", key="stock_ids"
    )

    for symbol in TARGET_STOCKS:
        sid = stock_ids[symbol]
        features_df = compute_features_for_stock(sid)

        if features_df.empty:
            logger.warning("No features generated for %s", symbol)
            continue

        count = upsert_features(sid, features_df)
        logger.info("Stored %d feature rows for %s", count, symbol)


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------
with DAG(
    dag_id="historical_backfill_dag",
    default_args=default_args,
    description="One-time historical data backfill for all target stocks",
    schedule="@once",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["backfill", "etl"],
) as dag:

    t_ensure_stocks = PythonOperator(
        task_id="ensure_stocks",
        python_callable=ensure_stocks,
    )

    t_extract_validate_load = PythonOperator(
        task_id="extract_validate_load_historical",
        python_callable=extract_validate_load_historical,
    )

    t_features = PythonOperator(
        task_id="generate_features",
        python_callable=generate_features,
    )

    # Task dependencies
    t_ensure_stocks >> t_extract_validate_load >> t_features
