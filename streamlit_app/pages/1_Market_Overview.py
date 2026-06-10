"""
Page 1: Market Overview
=======================
Latest prices, daily changes, and market summary for all tracked stocks.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils import (
    setup_page,
    load_stocks,
    load_raw_prices,
    get_stock_symbol_map,
    STOCK_COLORS,
    CHART_TEMPLATE,
    CHART_LAYOUT,
)

setup_page("Market Overview")

st.markdown("# <i class='fa-solid fa-chart-line'></i> Market Overview", unsafe_allow_html=True)
st.markdown("Real-time snapshot of all tracked stocks")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
try:
    stocks_df = load_stocks()
    symbol_map = get_stock_symbol_map()

    if stocks_df.empty:
        st.warning("No stocks found in database. Run the backfill DAG first.")
        st.stop()

    # Get latest prices for each stock
    all_prices = load_raw_prices()

    if all_prices.empty:
        st.warning("No price data found. Run the historical backfill DAG first.")
        st.stop()

    all_prices["trade_date"] = pd.to_datetime(all_prices["trade_date"])

    # Build summary
    summary_rows = []
    for _, stock in stocks_df.iterrows():
        sid = stock["stock_id"]
        symbol = stock["symbol"]
        name = stock["company_name"]

        stock_prices = all_prices[all_prices["stock_id"] == sid].sort_values("trade_date")

        if len(stock_prices) < 2:
            continue

        latest = stock_prices.iloc[-1]
        previous = stock_prices.iloc[-2]

        close = float(latest["close_price"])
        prev_close = float(previous["close_price"])
        change = close - prev_close
        change_pct = (change / prev_close) * 100

        summary_rows.append({
            "Symbol": symbol,
            "Company": name,
            "Close": close,
            "Change": change,
            "Change %": change_pct,
            "High": float(latest["high_price"]),
            "Low": float(latest["low_price"]),
            "Volume": int(latest["volume"]),
            "Date": latest["trade_date"],
        })

    summary_df = pd.DataFrame(summary_rows)

    if summary_df.empty:
        st.warning("Not enough data to display summary.")
        st.stop()

    # ---------------------------------------------------------------------------
    # KPI Cards
    # ---------------------------------------------------------------------------
    st.markdown("### Latest Closing Prices")

    cols = st.columns(len(summary_df))
    for i, (_, row) in enumerate(summary_df.iterrows()):
        with cols[i]:
            delta_str = f"{row['Change']:+.2f} ({row['Change %']:+.2f}%)"
            st.metric(
                label=f"{row['Symbol']}",
                value=f"${row['Close']:.2f}",
                delta=delta_str,
            )

    st.markdown("---")

    # ---------------------------------------------------------------------------
    # Market Heatmap
    # ---------------------------------------------------------------------------
    st.markdown("### Market Heatmap — Daily Change %")

    fig_heatmap = go.Figure(
        data=go.Bar(
            x=summary_df["Symbol"],
            y=summary_df["Change %"],
            marker=dict(
                color=summary_df["Change %"],
                colorscale=[[0, "#ef4444"], [0.5, "#6b7280"], [1, "#22c55e"]],
                line=dict(width=0),
            ),
            text=summary_df["Change %"].apply(lambda x: f"{x:+.2f}%"),
            textposition="outside",
            textfont=dict(color="#e2e8f0", size=13, family="Inter"),
        )
    )
    fig_heatmap.update_layout(
        **CHART_LAYOUT,
        height=350,
        title=None,
        yaxis_title="Daily Change %",
        showlegend=False,
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

    # ---------------------------------------------------------------------------
    # Summary Table
    # ---------------------------------------------------------------------------
    st.markdown("### Market Summary")

    display_df = summary_df.copy()
    display_df["Close"] = display_df["Close"].apply(lambda x: f"${x:.2f}")
    display_df["Change"] = display_df["Change"].apply(lambda x: f"{x:+.2f}")
    display_df["Change %"] = display_df["Change %"].apply(lambda x: f"{x:+.2f}%")
    display_df["High"] = display_df["High"].apply(lambda x: f"${x:.2f}")
    display_df["Low"] = display_df["Low"].apply(lambda x: f"${x:.2f}")
    display_df["Volume"] = display_df["Volume"].apply(lambda x: f"{x:,.0f}")
    display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    # ---------------------------------------------------------------------------
    # Volume Comparison
    # ---------------------------------------------------------------------------
    st.markdown("### Trading Volume Comparison")

    fig_volume = go.Figure()
    for _, row in summary_df.iterrows():
        color = STOCK_COLORS.get(row["Symbol"], "#818cf8")
        fig_volume.add_trace(
            go.Bar(
                x=[row["Symbol"]],
                y=[row["Volume"]],
                name=row["Symbol"],
                marker_color=color,
                text=[f"{row['Volume']:,.0f}"],
                textposition="outside",
                textfont=dict(size=11),
            )
        )

    fig_volume.update_layout(
        **CHART_LAYOUT,
        height=400,
        yaxis_title="Volume",
        showlegend=False,
        barmode="group",
    )
    st.plotly_chart(fig_volume, use_container_width=True)

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Make sure the database is accessible and the backfill DAG has been run.")
