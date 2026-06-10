"""
Page 4: Anomaly Detection
=========================
Anomaly scatter plots, scores timeline, and alert summary.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils import (
    setup_page,
    load_stocks,
    load_raw_prices,
    load_anomalies,
    STOCK_COLORS,
    STOCK_COLORS_OPPOSITE,
    COMPANY_LOGOS,
    CHART_TEMPLATE,
    CHART_LAYOUT,
)

setup_page("Anomaly Detection")

st.markdown("# <i class='fa-solid fa-triangle-exclamation'></i> Anomaly Detection", unsafe_allow_html=True)
st.markdown("AI-powered detection of unusual market behavior")

try:
    stocks_df = load_stocks()

    if stocks_df.empty:
        st.warning("No stocks found. Run the backfill DAG first.")
        st.stop()

    # Load all anomalies for summary
    all_anomalies = load_anomalies()

    if all_anomalies.empty:
        st.info(
            "No anomalies detected yet. Run the daily pipeline DAG to generate anomaly data."
        )
        st.markdown("---")
        st.markdown(
            """
            ### How Anomaly Detection Works

            The system uses **Isolation Forest** to detect:
            -  **Abnormal Volume** — Sudden spikes or drops in trading volume
            -  **Abnormal Returns** — Unusually large price movements
            - 🌊 **Unusual Volatility** — High intraday price swings
            -  **Sudden Price Movements** — Rapid directional changes

            Anomalies are flagged with a **contamination rate of 5%**, meaning
            approximately 5% of data points are classified as anomalous.
            """
        )
        st.stop()

    all_anomalies["trade_date"] = pd.to_datetime(all_anomalies["trade_date"])

    # ---------------------------------------------------------------------------
    # Alert Summary
    # ---------------------------------------------------------------------------
    st.markdown("### Alert Summary by Stock")

    symbol_map = dict(zip(stocks_df["stock_id"], stocks_df["symbol"]))

    summary = (
        all_anomalies[all_anomalies["anomaly_flag"] == True]
        .groupby("stock_id")
        .agg(
            anomaly_count=("anomaly_flag", "sum"),
            avg_score=("anomaly_score", "mean"),
            latest_date=("trade_date", "max"),
        )
        .reset_index()
    )
    summary["Symbol"] = summary["stock_id"].map(symbol_map)

    cols = st.columns(min(len(summary), 7))
    for i, (_, row) in enumerate(summary.iterrows()):
        with cols[i % len(cols)]:
            st.metric(
                label=f"🔴 {row['Symbol']}",
                value=f"{int(row['anomaly_count'])} alerts",
                delta=f"Score: {row['avg_score']:.3f}",
                delta_color="inverse",
            )

    st.markdown("---")

    # ---------------------------------------------------------------------------
    # Per-stock analysis
    # ---------------------------------------------------------------------------
    stock_options = {
        f"{row['symbol']} — {row['company_name']}": row["stock_id"]
        for _, row in stocks_df.iterrows()
    }

    selected = st.selectbox("Analyze Stock", list(stock_options.keys()), index=0)
    selected_id = stock_options[selected]
    selected_symbol = selected.split(" — ")[0]

    logo_url = COMPANY_LOGOS.get(selected_symbol)
    if logo_url:
        st.markdown(
            f'<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">'
            f'<img src="{logo_url}" width="40" height="40" />'
            f'<h2 style="margin: 0;">{selected}</h2>'
            f'</div>',
            unsafe_allow_html=True
        )

    stock_anomalies = all_anomalies[all_anomalies["stock_id"] == selected_id]
    prices_df = load_raw_prices(stock_id=selected_id)

    if prices_df.empty:
        st.warning("No price data for this stock.")
        st.stop()

    prices_df["trade_date"] = pd.to_datetime(prices_df["trade_date"])

    color = STOCK_COLORS.get(selected_symbol, "#818cf8")
    opp_color = STOCK_COLORS_OPPOSITE.get(selected_symbol, "#ef4444")

    # ---------------------------------------------------------------------------
    # Anomaly scatter on price chart
    # ---------------------------------------------------------------------------
    st.markdown(f"### {selected_symbol} — Anomalies on Price Chart")

    fig = go.Figure()

    # Price line
    fig.add_trace(
        go.Scatter(
            x=prices_df["trade_date"],
            y=prices_df["close_price"],
            name="Close Price",
            line=dict(color=color, width=2),
        )
    )

    # Anomaly points
    if not stock_anomalies.empty:
        anomalies_flagged = stock_anomalies[stock_anomalies["anomaly_flag"] == True]

        # Merge to get close price on anomaly dates
        anomaly_prices = anomalies_flagged.merge(
            prices_df[["trade_date", "close_price"]],
            on="trade_date",
            how="left",
        )

        if not anomaly_prices.empty:
            fig.add_trace(
                go.Scatter(
                    x=anomaly_prices["trade_date"],
                    y=anomaly_prices["close_price"],
                    mode="markers",
                    name="Anomaly",
                    marker=dict(
                        color=opp_color,
                        size=10,
                        symbol="x",
                        line=dict(width=2, color=opp_color),
                    ),
                )
            )

    fig.update_layout(
        **CHART_LAYOUT,
        height=450,
        yaxis_title="Price ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------------------------
    # Anomaly scores timeline
    # ---------------------------------------------------------------------------
    if not stock_anomalies.empty:
        st.markdown("### Anomaly Scores Timeline")

        fig_scores = go.Figure()

        fig_scores.add_trace(
            go.Scatter(
                x=stock_anomalies["trade_date"],
                y=stock_anomalies["anomaly_score"],
                fill="tozeroy",
                fillcolor="rgba(239, 68, 68, 0.15)",
                line=dict(color="#f87171", width=1.5),
                name="Anomaly Score",
            )
        )

        # Add threshold line
        fig_scores.add_hline(
            y=0,
            line_dash="dash",
            line_color="#6b7280",
            annotation_text="Decision Boundary",
            annotation_position="bottom right",
        )

        fig_scores.update_layout(
            **CHART_LAYOUT,
            height=350,
            yaxis_title="Anomaly Score (lower = more anomalous)",
        )
        st.plotly_chart(fig_scores, use_container_width=True)

        # ---------------------------------------------------------------------------
        # Recent anomalies table
        # ---------------------------------------------------------------------------
        st.markdown("### Recent Anomalies")

        recent = stock_anomalies[stock_anomalies["anomaly_flag"] == True].head(20).copy()

        if not recent.empty:
            display_df = recent[["trade_date", "anomaly_score", "model_name"]].copy()
            display_df["trade_date"] = display_df["trade_date"].dt.strftime("%Y-%m-%d")
            display_df["anomaly_score"] = display_df["anomaly_score"].apply(
                lambda x: f"{float(x):.4f}"
            )
            display_df.columns = ["Date", "Anomaly Score", "Model"]

            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.success("No anomalies detected for this stock! ")

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Make sure the database is accessible and anomaly detection has been run.")
