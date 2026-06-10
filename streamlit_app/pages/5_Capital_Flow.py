"""
Page 5: Capital Flow
====================
Market inflow/outflow analysis, MFI indicators, and trend visualization.
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

# We compute capital flow on-the-fly from raw prices
# (same logic as src/capital_flow/analyzer.py but for the dashboard)
import numpy as np

setup_page("Capital Flow")

st.markdown("# <i class='fa-solid fa-sack-dollar'></i> Capital Flow Analysis", unsafe_allow_html=True)
st.markdown("Market inflow/outflow estimation using price movement and volume")


def compute_capital_flow_df(prices_df: pd.DataFrame) -> pd.DataFrame:
    """Compute capital flow metrics from raw prices DataFrame."""
    if prices_df.empty or len(prices_df) < 15:
        return pd.DataFrame()

    df = prices_df.copy()
    df = df.sort_values("trade_date").reset_index(drop=True)

    # Typical Price
    df["typical_price"] = (
        df["high_price"].astype(float)
        + df["low_price"].astype(float)
        + df["close_price"].astype(float)
    ) / 3

    # Raw Money Flow
    df["raw_money_flow"] = df["typical_price"] * df["volume"].astype(float)

    # Flow direction
    df["flow_direction"] = np.where(
        df["typical_price"] > df["typical_price"].shift(1), 1,
        np.where(df["typical_price"] < df["typical_price"].shift(1), -1, 0),
    )

    # Separate flows
    df["inflow"] = np.where(df["flow_direction"] == 1, df["raw_money_flow"], 0)
    df["outflow"] = np.where(df["flow_direction"] == -1, df["raw_money_flow"], 0)

    # 14-day MFI
    inflow_14 = df["inflow"].rolling(window=14, min_periods=1).sum()
    outflow_14 = df["outflow"].rolling(window=14, min_periods=1).sum()
    money_ratio = inflow_14 / outflow_14.replace(0, np.nan)
    df["mfi_14"] = 100 - (100 / (1 + money_ratio))

    # Net and cumulative
    df["net_flow"] = df["inflow"] - df["outflow"]
    df["cumulative_flow"] = df["net_flow"].cumsum()

    return df


try:
    stocks_df = load_stocks()

    if stocks_df.empty:
        st.warning("No stocks found. Run the backfill DAG first.")
        st.stop()

    stock_options = {
        f"{row['symbol']} — {row['company_name']}": row["stock_id"]
        for _, row in stocks_df.iterrows()
    }

    selected = st.selectbox("Select Stock", list(stock_options.keys()), index=0)
    selected_id = stock_options[selected]
    selected_symbol = selected.split(" — ")[0]

    prices_df = load_raw_prices(stock_id=selected_id)

    if prices_df.empty or len(prices_df) < 15:
        st.warning(f"Not enough data for {selected_symbol} (need ≥15 trading days).")
        st.stop()

    prices_df["trade_date"] = pd.to_datetime(prices_df["trade_date"])

    flow_df = compute_capital_flow_df(prices_df)

    if flow_df.empty:
        st.warning("Could not compute capital flow.")
        st.stop()

    color = STOCK_COLORS.get(selected_symbol, "#818cf8")

    # ---------------------------------------------------------------------------
    # KPI Cards
    # ---------------------------------------------------------------------------
    latest = flow_df.iloc[-1]
    total_inflow = flow_df["inflow"].sum()
    total_outflow = flow_df["outflow"].sum()
    net_total = total_inflow - total_outflow
    mfi_latest = float(latest["mfi_14"]) if pd.notna(latest["mfi_14"]) else 50

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "MFI (14-day)",
        f"{mfi_latest:.1f}",
        "Overbought" if mfi_latest > 80 else ("Oversold" if mfi_latest < 20 else "Neutral"),
    )
    c2.metric("Total Inflow", f"${total_inflow:,.0f}")
    c3.metric("Total Outflow", f"${total_outflow:,.0f}")
    c4.metric(
        "Net Flow",
        f"${net_total:,.0f}",
        "Positive" if net_total > 0 else "Negative",
    )

    st.markdown("---")

    # ---------------------------------------------------------------------------
    # MFI Gauge
    # ---------------------------------------------------------------------------
    st.markdown("### Money Flow Index (14-Day)")

    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=mfi_latest,
            title=dict(text=f"{selected_symbol} MFI", font=dict(size=18, color="#e2e8f0")),
            number=dict(font=dict(color="#e2e8f0")),
            gauge=dict(
                axis=dict(range=[0, 100], tickcolor="#94a3b8"),
                bar=dict(color=color),
                bgcolor="rgba(26, 31, 58, 0.8)",
                borderwidth=2,
                bordercolor="rgba(99, 102, 241, 0.3)",
                steps=[
                    dict(range=[0, 20], color="rgba(239, 68, 68, 0.3)"),
                    dict(range=[20, 80], color="rgba(99, 102, 241, 0.15)"),
                    dict(range=[80, 100], color="rgba(34, 197, 94, 0.3)"),
                ],
                threshold=dict(
                    line=dict(color="#fbbf24", width=3),
                    thickness=0.8,
                    value=mfi_latest,
                ),
            ),
        )
    )
    fig_gauge.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif"),
        height=300,
        margin=dict(l=30, r=30, t=50, b=20),
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

    # ---------------------------------------------------------------------------
    # Inflow / Outflow over time
    # ---------------------------------------------------------------------------
    st.markdown("### Daily Inflow vs Outflow")

    fig_flow = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.6, 0.4],
        subplot_titles=("Daily Net Flow", "Cumulative Flow"),
    )

    fig_flow.add_trace(
        go.Bar(
            x=flow_df["trade_date"],
            y=flow_df["net_flow"],
            marker_color=[
                "#22c55e" if v >= 0 else "#ef4444"
                for v in flow_df["net_flow"]
            ],
            name="Net Flow",
            opacity=0.8,
        ),
        row=1, col=1,
    )

    fig_flow.add_trace(
        go.Scatter(
            x=flow_df["trade_date"],
            y=flow_df["cumulative_flow"],
            fill="tozeroy",
            fillcolor=(
                "rgba(34, 197, 94, 0.2)" if flow_df["cumulative_flow"].iloc[-1] >= 0
                else "rgba(239, 68, 68, 0.2)"
            ),
            line=dict(
                color="#22c55e" if flow_df["cumulative_flow"].iloc[-1] >= 0 else "#ef4444",
                width=2,
            ),
            name="Cumulative",
        ),
        row=2, col=1,
    )

    fig_flow.update_layout(
        **CHART_LAYOUT,
        height=600,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
    )
    fig_flow.update_yaxes(title_text="Net Flow ($)", row=1, col=1)
    fig_flow.update_yaxes(title_text="Cumulative ($)", row=2, col=1)

    st.plotly_chart(fig_flow, use_container_width=True)

    # ---------------------------------------------------------------------------
    # MFI trend
    # ---------------------------------------------------------------------------
    st.markdown("### MFI Trend Over Time")

    fig_mfi = go.Figure()

    fig_mfi.add_trace(
        go.Scatter(
            x=flow_df["trade_date"],
            y=flow_df["mfi_14"],
            line=dict(color=color, width=2),
            name="MFI-14",
        )
    )

    # Overbought / Oversold bands
    fig_mfi.add_hline(y=80, line_dash="dash", line_color="#22c55e",
                       annotation_text="Overbought (80)")
    fig_mfi.add_hline(y=20, line_dash="dash", line_color="#ef4444",
                       annotation_text="Oversold (20)")
    fig_mfi.add_hrect(y0=80, y1=100, fillcolor="rgba(34, 197, 94, 0.1)",
                       line_width=0)
    fig_mfi.add_hrect(y0=0, y1=20, fillcolor="rgba(239, 68, 68, 0.1)",
                       line_width=0)

    fig_mfi.update_layout(
        **CHART_LAYOUT,
        height=350,
        yaxis_title="MFI",
        yaxis_range=[0, 100],
    )
    st.plotly_chart(fig_mfi, use_container_width=True)

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Make sure the database is accessible and data has been loaded.")
