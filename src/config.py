"""
Configuration module.
Loads all settings from environment variables.
"""

import os
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Finnhub
# ---------------------------------------------------------------------------
FINNHUB_API_KEY: str = os.environ.get("FINNHUB_API_KEY", "")

# ---------------------------------------------------------------------------
# Supabase PostgreSQL
# ---------------------------------------------------------------------------
import urllib.parse

SUPABASE_HOST: str = os.environ.get("SUPABASE_HOST", "")
SUPABASE_PORT: str = os.environ.get("SUPABASE_PORT", "5432")
SUPABASE_NAME: str = os.environ.get("SUPABASE_NAME", "postgres")
SUPABASE_USER: str = os.environ.get("SUPABASE_USER", "postgres")
SUPABASE_PASSWORD: str = os.environ.get("SUPABASE_PASSWORD", "")

encoded_user = urllib.parse.quote_plus(SUPABASE_USER)
encoded_password = urllib.parse.quote_plus(SUPABASE_PASSWORD)

DATABASE_URL: str = (
    f"postgresql://{encoded_user}:{encoded_password}@{SUPABASE_HOST}:{SUPABASE_PORT}/{SUPABASE_NAME}"
)

# ---------------------------------------------------------------------------
# Target stocks
# ---------------------------------------------------------------------------
TARGET_STOCKS: dict[str, str] = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com Inc.",
    "GOOGL": "Alphabet Inc.",
    "META": "Meta Platforms Inc.",
    "TSLA": "Tesla Inc.",
}

# ---------------------------------------------------------------------------
# Historical backfill window
# ---------------------------------------------------------------------------
BACKFILL_DAYS: int = 365
BACKFILL_END: datetime = datetime.utcnow()
BACKFILL_START: datetime = BACKFILL_END - timedelta(days=BACKFILL_DAYS)

# ---------------------------------------------------------------------------
# Model storage
# ---------------------------------------------------------------------------
MODEL_DIR: str = os.environ.get("MODEL_DIR", "/opt/airflow/models")

# ---------------------------------------------------------------------------
# Finnhub rate-limit (calls per second)
# ---------------------------------------------------------------------------
API_CALL_DELAY: float = 1.0  # seconds between Finnhub calls
