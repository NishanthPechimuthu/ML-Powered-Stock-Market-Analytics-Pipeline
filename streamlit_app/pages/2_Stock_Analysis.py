"""
Page 2: Stock Analysis
======================
Deep-dive into individual stocks: candlestick charts, moving averages,
volume analysis, and historical trends.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils import (
    setup_page,
    load_stocks,
    load_raw_prices,
    load_features,
    STOCK_COLORS,
    CHART_TEMPLATE,
    CHART_LAYOUT,
)

setup_page("Stock Analysis")

st.markdown("# <i class='fa-solid fa-microscope'></i> Stock Analysis", unsafe_allow_html=True)
st.markdown("Deep-dive into historical trends, moving averages, and volume patterns")

# ---------------------------------------------------------------------------
# Stock selector
# ---------------------------------------------------------------------------
try:
    stocks_df = load_stocks()

    if stocks_df.empty:
        st.warning("No stocks found. Run the backfill DAG first.")
        st.stop()

    stock_options = {
        f"{row['symbol']} — {row['company_name']}": row["stock_id"]
        for _, row in stocks_df.iterrows()
    }

    selected = st.selectbox(
        "Select Stock",
        options=list(stock_options.keys()),
        index=0,
    )
    selected_id = stock_options[selected]
    selected_symbol = selected.split(" — ")[0]

    # Date range
    col1, col2 = st.columns(2)
    with col1:
        lookback = st.selectbox(
            "Time Period",
            ["30 Days", "90 Days", "180 Days", "1 Year", "All"],
            index=3,
        )

    days_map = {"30 Days": 30, "90 Days": 90, "180 Days": 180, "1 Year": 365, "All": None}
    days = days_map[lookback]

    # Load data
    prices_df = load_raw_prices(stock_id=selected_id, days=days)
    features_df = load_features(stock_id=selected_id)

    if prices_df.empty:
        st.warning(f"No price data for {selected_symbol}.")
        st.stop()

    prices_df["trade_date"] = pd.to_datetime(prices_df["trade_date"])
    if not features_df.empty:
        features_df["trade_date"] = pd.to_datetime(features_df["trade_date"])

    color = STOCK_COLORS.get(selected_symbol, "#818cf8")

    # ---------------------------------------------------------------------------
    # KPI summary for selected stock
    # ---------------------------------------------------------------------------
    latest = prices_df.iloc[-1]
    first = prices_df.iloc[0]

    period_change = float(latest["close_price"]) - float(first["close_price"])
    period_change_pct = (period_change / float(first["close_price"])) * 100
    avg_volume = prices_df["volume"].mean()
    high_52w = prices_df["high_price"].max()
    low_52w = prices_df["low_price"].min()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest Close", f"${float(latest['close_price']):.2f}")
    c2.metric("Period Change", f"${period_change:.2f}", f"{period_change_pct:+.2f}%")
    c3.metric("Period High", f"${float(high_52w):.2f}")
    c4.metric("Period Low", f"${float(low_52w):.2f}")

    st.markdown("---")

    # ---------------------------------------------------------------------------
    # Candlestick chart with moving averages
    # ---------------------------------------------------------------------------
    st.markdown("### Price Chart with Moving Averages")

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=("", "Volume"),
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=prices_df["trade_date"],
            open=prices_df["open_price"],
            high=prices_df["high_price"],
            low=prices_df["low_price"],
            close=prices_df["close_price"],
            name="OHLC",
            increasing_line_color="#22c55e",
            decreasing_line_color="#ef4444",
        ),
        row=1, col=1,
    )

    # Moving averages from features
    if not features_df.empty:
        # Filter features to match price date range
        merged = features_df[
            features_df["trade_date"].isin(prices_df["trade_date"])
        ]

        if not merged.empty:
            fig.add_trace(
                go.Scatter(
                    x=merged["trade_date"],
                    y=merged["ma_7"],
                    name="MA-7",
                    line=dict(color="#fbbf24", width=1.5),
                ),
                row=1, col=1,
            )

            fig.add_trace(
                go.Scatter(
                    x=merged["trade_date"],
                    y=merged["ma_30"],
                    name="MA-30",
                    line=dict(color="#60a5fa", width=1.5),
                ),
                row=1, col=1,
            )

    # Volume bars
    colors = [
        "#22c55e" if c >= o else "#ef4444"
        for c, o in zip(prices_df["close_price"], prices_df["open_price"])
    ]

    fig.add_trace(
        go.Bar(
            x=prices_df["trade_date"],
            y=prices_df["volume"],
            name="Volume",
            marker_color=colors,
            opacity=0.6,
        ),
        row=2, col=1,
    )

    fig.update_layout(
        **CHART_LAYOUT,
        height=650,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------------------------
    # Feature trends
    # ---------------------------------------------------------------------------
    if not features_df.empty:
        st.markdown("### Technical Indicators")

        tab1, tab2, tab3 = st.tabs(["Daily Return", "Volatility", "Capital Flow"])

        with tab1:
            fig_ret = go.Figure()
            fig_ret.add_trace(
                go.Bar(
                    x=features_df["trade_date"],
                    y=features_df["daily_return"],
                    marker_color=[
                        "#22c55e" if v >= 0 else "#ef4444"
                        for v in features_df["daily_return"]
                    ],
                    name="Daily Return",
                )
            )
            fig_ret.update_layout(**CHART_LAYOUT, height=350, yaxis_title="Return %")
            st.plotly_chart(fig_ret, use_container_width=True)

        with tab2:
            fig_vol = go.Figure()
            fig_vol.add_trace(
                go.Scatter(
                    x=features_df["trade_date"],
                    y=features_df["volatility"],
                    fill="tozeroy",
                    fillcolor="rgba(167, 139, 250, 0.2)",
                    line=dict(color="#a78bfa", width=1.5),
                    name="Volatility",
                )
            )
            fig_vol.update_layout(**CHART_LAYOUT, height=350, yaxis_title="Volatility")
            st.plotly_chart(fig_vol, use_container_width=True)

        with tab3:
            fig_cf = go.Figure()
            fig_cf.add_trace(
                go.Bar(
                    x=features_df["trade_date"],
                    y=features_df["capital_flow_indicator"],
                    marker_color=[
                        "#22c55e" if v >= 0 else "#ef4444"
                        for v in features_df["capital_flow_indicator"].fillna(0)
                    ],
                    name="Capital Flow",
                )
            )
            fig_cf.update_layout(**CHART_LAYOUT, height=350, yaxis_title="Flow Indicator")
            st.plotly_chart(fig_cf, use_container_width=True)

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Make sure the database is accessible and the backfill DAG has been run.")
