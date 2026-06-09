"""
Streamlit Dashboard — Main Entry Point
=======================================
AI-Powered Stock Market Analytics Pipeline
"""

import streamlit as st
from utils import (
    setup_page,
    load_stocks,
    COMPANY_LOGOS,
)

# ---------------------------------------------------------------------------
# Page config (MUST be the first Streamlit command)
# ---------------------------------------------------------------------------
setup_page("Stock Market Analytics")

# ---------------------------------------------------------------------------
# Custom CSS for dark, premium financial theme
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global styles */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0e27 0%, #131842 100%);
    }

    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #e2e8f0;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1f3a 0%, #2d2b55 100%);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }

    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-weight: 500;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
    }

    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-weight: 700;
    }

    /* Headers */
    h1 {
        background: linear-gradient(90deg, #818cf8, #6366f1, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700 !important;
    }

    h2, h3 {
        color: #c7d2fe !important;
        font-weight: 600 !important;
    }

    /* DataFrames */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
    }

    /* Hero section */
    .hero-container {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%);
        border-radius: 16px;
        padding: 40px;
        margin-bottom: 24px;
        border: 1px solid rgba(99, 102, 241, 0.3);
        text-align: center;
    }

    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #818cf8, #c084fc, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
    }

    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        font-weight: 400;
    }

    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.03em;
    }

    .badge-active {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }

    /* Card grid */
    .info-card {
        background: linear-gradient(135deg, #1a1f3a 0%, #1e2348 100%);
        border: 1px solid rgba(99, 102, 241, 0.15);
        border-radius: 12px;
        padding: 24px;
        height: 100%;
    }

    .info-card h4 {
        color: #a5b4fc;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 8px;
    }

    .info-card p {
        color: #e2e8f0;
        font-size: 1rem;
    }

    /* Footer */
    .footer {
        text-align: center;
        color: #64748b;
        padding: 20px 0;
        font-size: 0.85rem;
        border-top: 1px solid rgba(99, 102, 241, 0.1);
        margin-top: 40px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("#### <i class='fa-solid fa-chart-pie'></i> Analytics Hub", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(
        """
        **Tracked Stocks:**
        - <i class='fa-brands fa-apple'></i> Apple (AAPL)
        - <i class='fa-brands fa-windows'></i> Microsoft (MSFT)
        - <i class='fa-solid fa-microchip'></i> NVIDIA (NVDA)
        - <i class='fa-brands fa-amazon'></i> Amazon (AMZN)
        - <i class='fa-brands fa-google'></i> Alphabet (GOOGL)
        - <i class='fa-brands fa-meta'></i> Meta (META)
        - <i class='fa-solid fa-car'></i> Tesla (TSLA)
        """,
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.markdown(
        """
        <div style="color: #64748b; font-size: 0.8rem;">
        <strong>Pipeline Status</strong><br>
        <span class="status-badge badge-active">● Active</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Main content — Landing page
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-title">STOCKIFY</div>
        <div class="hero-subtitle">
            AI-Powered Pipeline · Real-Time Insights · Predictive Intelligence
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Info cards
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        """
        <div class="info-card">
            <h4> Market Overview</h4>
            <p>Live prices, daily changes, and market summary across all tracked stocks.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div class="info-card">
            <h4> Stock Analysis</h4>
            <p>Deep-dive into historical trends, moving averages, and volume patterns.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """
        <div class="info-card">
            <h4> AI Predictions</h4>
            <p>ML-powered next-day close predictions with model performance tracking.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        """
        <div class="info-card">
            <h4> Anomaly Detection</h4>
            <p>Isolation Forest detects unusual volume, returns, and price movements.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


