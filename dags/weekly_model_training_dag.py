"""
Weekly Model Training DAG
=========================
Retrains ML models every Sunday.
Trains all model types, evaluates, and logs metrics.

Schedule: 0 6 * * 0 (Sunday 6 AM UTC)
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
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
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


def train_linear_regression(**kwargs):
    """Train Linear Regression models for all stocks."""
    from src.ml.train import train_model

    stock_ids = kwargs["ti"].xcom_pull(task_ids="get_stock_ids", key="stock_ids")
    results = {}

    for symbol, sid in stock_ids.items():
        try:
            result = train_model(sid, model_type="linear_regression")
            results[symbol] = result["metrics"]
            logger.info(
                "Trained LR for %s — R²=%.4f, RMSE=%.4f",
                symbol, result["metrics"]["r2"], result["metrics"]["rmse"],
            )
        except ValueError as e:
            logger.warning("Skipping %s: %s", symbol, e)

    kwargs["ti"].xcom_push(key="lr_results", value=results)


def train_xgboost(**kwargs):
    """Train XGBoost models for all stocks."""
    from src.ml.train import train_model

    stock_ids = kwargs["ti"].xcom_pull(task_ids="get_stock_ids", key="stock_ids")
    results = {}

    for symbol, sid in stock_ids.items():
        try:
            result = train_model(sid, model_type="xgboost")
            results[symbol] = result["metrics"]
            logger.info(
                "Trained XGB for %s — R²=%.4f, RMSE=%.4f",
                symbol, result["metrics"]["r2"], result["metrics"]["rmse"],
            )
        except ValueError as e:
            logger.warning("Skipping %s: %s", symbol, e)

    kwargs["ti"].xcom_push(key="xgb_results", value=results)


def train_stacking(**kwargs):
    """Train Stacking models for all stocks."""
    from src.ml.train import train_model

    stock_ids = kwargs["ti"].xcom_pull(task_ids="get_stock_ids", key="stock_ids")
    results = {}

    for symbol, sid in stock_ids.items():
        try:
            result = train_model(sid, model_type="stacking")
            results[symbol] = result["metrics"]
            logger.info(
                "Trained Stacking for %s — R²=%.4f, RMSE=%.4f",
                symbol, result["metrics"]["r2"], result["metrics"]["rmse"],
            )
        except ValueError as e:
            logger.warning("Skipping %s: %s", symbol, e)

    kwargs["ti"].xcom_push(key="stacking_results", value=results)


def compare_models(**kwargs):
    """Compare model performance and log best models."""
    lr_results = kwargs["ti"].xcom_pull(
        task_ids="train_linear_regression", key="lr_results"
    )
    xgb_results = kwargs["ti"].xcom_pull(
        task_ids="train_xgboost", key="xgb_results"
    )
    stacking_results = kwargs["ti"].xcom_pull(
        task_ids="train_stacking", key="stacking_results"
    )

    logger.info("=" * 60)
    logger.info("MODEL COMPARISON REPORT")
    logger.info("=" * 60)

    for symbol in lr_results:
        lr_r2 = lr_results[symbol]["r2"]
        xgb_r2 = xgb_results.get(symbol, {}).get("r2", float("-inf"))
        stack_r2 = stacking_results.get(symbol, {}).get("r2", float("-inf"))

        scores = {"Linear Regression": lr_r2, "XGBoost": xgb_r2, "Stacking": stack_r2}
        best = max(scores, key=scores.get)
        best_r2 = scores[best]

        logger.info(
            "%s: LR R²=%.4f | XGB R²=%.4f | Stacking R²=%.4f → Best: %s (R²=%.4f)",
            symbol, lr_r2, xgb_r2, stack_r2, best, best_r2,
        )

    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------
with DAG(
    dag_id="weekly_model_training_dag",
    default_args=default_args,
    description="Weekly model retraining and evaluation",
    schedule="0 6 * * 0",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["ml", "training", "weekly"],
) as dag:

    t_get_stocks = PythonOperator(
        task_id="get_stock_ids",
        python_callable=get_stock_ids,
    )

    t_train_lr = PythonOperator(
        task_id="train_linear_regression",
        python_callable=train_linear_regression,
    )

    t_train_xgb = PythonOperator(
        task_id="train_xgboost",
        python_callable=train_xgboost,
    )

    t_train_stacking = PythonOperator(
        task_id="train_stacking",
        python_callable=train_stacking,
    )

    t_compare = PythonOperator(
        task_id="compare_models",
        python_callable=compare_models,
    )

    # Training can happen in parallel, then compare
    t_get_stocks >> [t_train_lr, t_train_xgb, t_train_stacking] >> t_compare
