"""
Daily Market Pipeline DAG
=========================
Runs daily after US market close.
Extracts latest data → validates → loads → updates features →
runs predictions → detects anomalies.

Schedule: 0 22 * * 1-5 (10 PM UTC, Mon-Fri)
"""

import sys
import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow")

logger = logging.getLogger(__name__)

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
def get_stock_ids(**kwargs):
    """Retrieve all stock IDs from the database."""
    from sqlalchemy import text
    from src.db import get_engine

    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT stock_id, symbol FROM stocks"))
        stock_map = {row[1]: row[0] for row in result}

    kwargs["ti"].xcom_push(key="stock_ids", value=stock_map)
    logger.info("Found %d stocks: %s", len(stock_map), list(stock_map.keys()))


def extract_validate_load_daily(**kwargs):
    """Fetch latest daily candle, validate, and load for all stocks."""
    import pandas as pd
    from src.etl.extract import fetch_daily_candle
    from src.etl.transform import clean_stock_data, validate_data_quality
    from src.etl.load import upsert_raw_prices

    stock_ids = kwargs["ti"].xcom_pull(task_ids="get_stock_ids", key="stock_ids")

    for symbol, sid in stock_ids.items():
        # 1. Extract
        df = fetch_daily_candle(symbol)
        if df.empty:
            logger.warning("No daily data for %s", symbol)
            continue
        logger.info("Fetched daily data for %s", symbol)

        # 2. Validate & Clean
        df = clean_stock_data(df)
        validate_data_quality(df, symbol=symbol)

        # 3. Load
        upsert_raw_prices(sid, df)
        logger.info("Loaded daily data for %s", symbol)


def update_features(**kwargs):
    """Recompute features with latest data."""
    from src.features.engineering import compute_features_for_stock
    from src.etl.load import upsert_features

    stock_ids = kwargs["ti"].xcom_pull(task_ids="get_stock_ids", key="stock_ids")

    for symbol, sid in stock_ids.items():
        features_df = compute_features_for_stock(sid)
        if not features_df.empty:
            upsert_features(sid, features_df)
            logger.info("Updated features for %s", symbol)


def run_predictions(**kwargs):
    """Run predictions using trained models."""
    from src.ml.predict import predict_next_close
    from src.etl.load import insert_predictions

    stock_ids = kwargs["ti"].xcom_pull(task_ids="get_stock_ids", key="stock_ids")

    predictions = []
    for symbol, sid in stock_ids.items():
        for model_type in ["linear_regression", "xgboost", "stacking"]:
            results = predict_next_close(sid, model_type=model_type)
            if results:
                predictions.extend(results)
                logger.info(
                    "Generated %d predictions for %s using %s", len(results), symbol, model_type
                )

    if predictions:
        insert_predictions(predictions)


def run_anomaly_detection(**kwargs):
    """Run anomaly detection for all stocks."""
    from src.anomaly.detector import detect_anomalies
    from src.etl.load import insert_anomalies

    stock_ids = kwargs["ti"].xcom_pull(task_ids="get_stock_ids", key="stock_ids")

    for symbol, sid in stock_ids.items():
        records = detect_anomalies(sid)
        if records:
            insert_anomalies(records)
            anomaly_count = sum(1 for r in records if r["anomaly_flag"])
            logger.info(
                "Anomaly detection for %s: %d anomalies found",
                symbol, anomaly_count,
            )


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------
with DAG(
    dag_id="daily_market_pipeline_dag",
    default_args=default_args,
    description="Daily ETL + predictions + anomaly detection",
    schedule="0 22 * * 1-5",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["daily", "etl", "ml"],
) as dag:

    t_get_stocks = PythonOperator(
        task_id="get_stock_ids",
        python_callable=get_stock_ids,
    )

    t_extract_validate_load = PythonOperator(
        task_id="extract_validate_load_daily",
        python_callable=extract_validate_load_daily,
    )

    t_features = PythonOperator(
        task_id="update_features",
        python_callable=update_features,
    )

    t_predict = PythonOperator(
        task_id="run_predictions",
        python_callable=run_predictions,
    )

    t_anomaly = PythonOperator(
        task_id="run_anomaly_detection",
        python_callable=run_anomaly_detection,
    )

    # Pipeline flow
    (
        t_get_stocks
        >> t_extract_validate_load
        >> t_features
        >> t_predict
        >> t_anomaly
    )
