"""
Shared utility functions for the Streamlit dashboard.
"""

import os
import pandas as pd
import streamlit as st
from PIL import Image
from sqlalchemy import create_engine, text

import urllib.parse

# Build connection string from env vars
SUPABASE_HOST = os.environ.get("SUPABASE_HOST", "")
SUPABASE_PORT = os.environ.get("SUPABASE_PORT", "5432")
SUPABASE_NAME = os.environ.get("SUPABASE_NAME", "postgres")
SUPABASE_USER = os.environ.get("SUPABASE_USER", "postgres")
SUPABASE_PASSWORD = os.environ.get("SUPABASE_PASSWORD", "")

encoded_user = urllib.parse.quote_plus(SUPABASE_USER)
encoded_password = urllib.parse.quote_plus(SUPABASE_PASSWORD)

DATABASE_URL = f"postgresql://{encoded_user}:{encoded_password}@{SUPABASE_HOST}:{SUPABASE_PORT}/{SUPABASE_NAME}"

_engine = None


def get_engine():
    """Get or create SQLAlchemy engine for the dashboard."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            pool_size=3,
            max_overflow=5,
            pool_pre_ping=True,
            connect_args={"sslmode": "require"},
        )
    return _engine

def setup_page(title: str):
    """Common page setup with favicon and footer."""
    icon_path = os.path.join(os.path.dirname(__file__), "..", "assests", "favicon", "NP-512-WB.ico")
    try:
        icon = Image.open(icon_path)
    except Exception:
        icon = None

    st.set_page_config(page_title=title, page_icon=icon, layout="wide")

    st.markdown(
        """
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
        footer {visibility: hidden;}
        .custom-footer {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background-color: rgba(26, 31, 58, 0.9);
            text-align: center;
            padding: 10px;
            font-size: 13px;
            color: #888;
            z-index: 9999;
            border-top: 1px solid rgba(99, 102, 241, 0.2);
        }
        .custom-footer a {
            color: #6366f1;
            text-decoration: none;
            font-weight: 600;
        }
        </style>
        <div class="custom-footer">
            Developed by <a href="https://github.com/NishanthPechimuthu" target="_blank">Nishanth P</a>
        </div>
        """,
        unsafe_allow_html=True
    )

def load_stocks() -> pd.DataFrame:
    """Load all stocks from the stocks table."""
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text("SELECT * FROM stocks ORDER BY symbol"), conn)


def load_raw_prices(stock_id: int = None, days: int = None) -> pd.DataFrame:
    """Load raw stock prices, optionally filtered by stock and date range."""
    engine = get_engine()
    query = "SELECT * FROM raw_stock_prices"
    params = {}

    conditions = []
    if stock_id:
        conditions.append("stock_id = :stock_id")
        params["stock_id"] = stock_id
    if days:
        conditions.append("trade_date >= CURRENT_DATE - :days")
        params["days"] = days

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY trade_date ASC"

    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


def load_features(stock_id: int = None) -> pd.DataFrame:
    """Load engineered features."""
    engine = get_engine()
    query = "SELECT * FROM stock_features"
    params = {}

    if stock_id:
        query += " WHERE stock_id = :stock_id"
        params["stock_id"] = stock_id

    query += " ORDER BY trade_date ASC"

    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


def load_predictions(stock_id: int = None) -> pd.DataFrame:
    """Load prediction records."""
    engine = get_engine()
    query = "SELECT * FROM predictions"
    params = {}

    if stock_id:
        query += " WHERE stock_id = :stock_id"
        params["stock_id"] = stock_id

    query += " ORDER BY prediction_date DESC"

    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


def load_anomalies(stock_id: int = None) -> pd.DataFrame:
    """Load anomaly records."""
    engine = get_engine()
    query = "SELECT * FROM anomalies"
    params = {}

    if stock_id:
        query += " WHERE stock_id = :stock_id"
        params["stock_id"] = stock_id

    query += " ORDER BY trade_date DESC"

    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


def get_stock_symbol_map() -> dict:
    """Return {stock_id: symbol} mapping."""
    df = load_stocks()
    return dict(zip(df["stock_id"], df["symbol"]))


def get_stock_name_map() -> dict:
    """Return {symbol: company_name} mapping."""
    df = load_stocks()
    return dict(zip(df["symbol"], df["company_name"]))


# Official brand colors
STOCK_COLORS = {
    "AAPL": "#A3AAAE",  # Apple Silver
    "MSFT": "#00A4EF",  # Microsoft Blue
    "NVDA": "#76B900",  # NVIDIA Green
    "AMZN": "#FF9900",  # Amazon Orange
    "GOOGL": "#4285F4", # Google Blue
    "META": "#0668E1",  # Meta Blue
    "TSLA": "#E31937",  # Tesla Red
}

# High-contrast companion colors
STOCK_COLORS_OPPOSITE = {
    "AAPL": "#FF0000",  # Vibrant Orange
    "MSFT": "#FF6B35",  # Vibrant Orange
    "NVDA": "#8B5CF6",  # Purple
    "AMZN": "#2563EB",  # Strong Blue
    "GOOGL": "#F97316", # Orange
    "META": "#F59E0B",  # Amber
    "TSLA": "#06B6D4",  # Cyan
}

COMPANY_LOGOS = {
    "AAPL": "https://www.vectorlogo.zone/logos/apple/apple-icon.svg",
    "MSFT": "https://www.vectorlogo.zone/logos/microsoft/microsoft-icon.svg",
    "NVDA": "https://www.vectorlogo.zone/logos/nvidia/nvidia-icon.svg",
    "AMZN": "https://www.vectorlogo.zone/logos/amazon/amazon-icon.svg",
    "GOOGL": "https://www.vectorlogo.zone/logos/google/google-icon.svg",
    "META": "https://cdn.simpleicons.org/meta/0668E1",
    "TSLA": "https://www.vectorlogo.zone/logos/tesla/tesla-icon.svg",
}

# Plotly chart template
CHART_TEMPLATE = "plotly_dark"

CHART_LAYOUT = dict(
    font=dict(family="Inter, sans-serif", color="#e2e8f0"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(26, 31, 58, 0.8)",
    xaxis=dict(
        gridcolor="rgba(99, 102, 241, 0.1)",
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=3, label="3m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ]),
            bgcolor="#1e293b",
            activecolor="#6366f1"
        )
    ),
    yaxis=dict(gridcolor="rgba(99, 102, 241, 0.1)"),
    margin=dict(l=20, r=20, t=40, b=20),
)
