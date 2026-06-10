"""
Page 3: Predictions
===================
AI model predictions: actual vs predicted, model performance metrics,
and prediction history.
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
    load_predictions,
    STOCK_COLORS,
    STOCK_COLORS_OPPOSITE,
    COMPANY_LOGOS,
    CHART_TEMPLATE,
    CHART_LAYOUT,
)

setup_page("Predictions")

st.markdown("# <i class='fa-solid fa-robot'></i> AI Predictions", unsafe_allow_html=True)
st.markdown("ML-powered next-day close price predictions and model performance")

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

    # Show company logo if available
    logo_url = COMPANY_LOGOS.get(selected_symbol)
    if logo_url:
        st.markdown(
            f'<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">'
            f'<img src="{logo_url}" width="40" height="40" />'
            f'<h2 style="margin: 0;">{selected}</h2>'
            f'</div>',
            unsafe_allow_html=True
        )

    # Load data
    predictions_df = load_predictions(stock_id=selected_id)
    prices_df = load_raw_prices(stock_id=selected_id)

    if predictions_df.empty:
        st.info(
            f"No predictions found for {selected_symbol}. "
            "Run the weekly training DAG followed by the daily pipeline."
        )
        st.markdown("---")
        st.markdown(
            """
            ### How Predictions Work

            1. **Train Models**: The weekly training DAG trains Linear Regression
               and Random Forest models on historical data.
            2. **Generate Predictions**: The daily pipeline uses trained models
               to predict next-day closing prices.
            3. **Track Performance**: Predictions are stored and compared against
               actual prices to measure accuracy.
            """
        )
        st.stop()

    predictions_df["prediction_date"] = pd.to_datetime(predictions_df["prediction_date"])
    prices_df["trade_date"] = pd.to_datetime(prices_df["trade_date"])

    available_models = predictions_df["model_name"].unique().tolist()
    selected_model = st.selectbox("Select Model to Preview", available_models, index=0)

    # Filter predictions for the selected model
    model_preds_df = predictions_df[predictions_df["model_name"] == selected_model].copy()

    color = STOCK_COLORS.get(selected_symbol, "#818cf8")
    opp_color = STOCK_COLORS_OPPOSITE.get(selected_symbol, "#fbbf24")

    # ---------------------------------------------------------------------------
    # Latest prediction
    # ---------------------------------------------------------------------------
    latest_pred = model_preds_df.iloc[0]
    st.markdown("### Latest Prediction")

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Predicted Close",
        f"${float(latest_pred['predicted_close']):.2f}",
    )
    c2.metric("For Date", str(latest_pred["prediction_date"].date()))
    formatted_model_name = latest_pred['model_name'].replace('_', ' ').title()
    c3.metric("Model", formatted_model_name)

    st.markdown("---")

    # ---------------------------------------------------------------------------
    # Actual vs Predicted chart
    # ---------------------------------------------------------------------------
    st.markdown("### Actual vs Predicted Close Price")

    # Merge predictions with actual prices
    merged = model_preds_df.merge(
        prices_df[["trade_date", "close_price"]],
        left_on="prediction_date",
        right_on="trade_date",
        how="left",
    )

    fig = go.Figure()

    # Actual prices
    fig.add_trace(
        go.Scatter(
            x=prices_df["trade_date"],
            y=prices_df["close_price"],
            name="Actual Close",
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=6, symbol="circle"),
        )
    )

    # Predicted values
    if not merged.empty:
        fig.add_trace(
            go.Scatter(
                x=merged["prediction_date"],
                y=merged["predicted_close"],
                name=f"Predicted ({selected_model})",
                mode="lines+markers",
                line=dict(color=opp_color, width=2, dash="dash"),
                marker=dict(size=8, symbol="diamond"),
            )
        )
        
        # Highlight tomorrow's prediction
        latest_row = merged.sort_values(by="prediction_date", ascending=False).iloc[0]
        fig.add_trace(
            go.Scatter(
                x=[latest_row["prediction_date"]],
                y=[latest_row["predicted_close"]],
                name="Tomorrow's Prediction",
                mode="markers",
                marker=dict(size=16, symbol="star", color="#facc15", line=dict(width=2, color="#ca8a04")),
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
    # Prediction accuracy (where we have actual data)
    # ---------------------------------------------------------------------------
    matched = merged.dropna(subset=["close_price"])

    if not matched.empty:
        st.markdown("### Model Accuracy")

        matched["error"] = matched["predicted_close"].astype(float) - matched["close_price"].astype(float)
        matched["abs_error"] = matched["error"].abs()
        matched["pct_error"] = (matched["abs_error"] / matched["close_price"].astype(float)) * 100

        # Group by model
        for model_name in matched["model_name"].unique():
            model_data = matched[matched["model_name"] == model_name]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Model", model_name)
            c2.metric("MAE", f"${model_data['abs_error'].mean():.2f}")
            c3.metric("Avg Error %", f"{model_data['pct_error'].mean():.2f}%")
            c4.metric("Predictions", str(len(model_data)))

    st.markdown("---")

    # ---------------------------------------------------------------------------
    # Prediction history table
    # ---------------------------------------------------------------------------
    st.markdown("### Prediction History")

    display_df = model_preds_df[["prediction_date", "predicted_close", "model_name", "created_at"]].copy()
    display_df["prediction_date"] = display_df["prediction_date"].dt.strftime("%Y-%m-%d")
    display_df["predicted_close"] = display_df["predicted_close"].apply(lambda x: f"${float(x):.2f}")
    display_df.columns = ["Prediction Date", "Predicted Close", "Model", "Created At"]

    st.dataframe(display_df.head(50), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Make sure the database is accessible and predictions have been generated.")
