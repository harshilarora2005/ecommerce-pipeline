"""Geo: state-level revenue & delivery performance."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

DB_PATH = ROOT / "data" / "ecommerce.db"
st.set_page_config(page_title="Geo", page_icon="🗺️", layout="wide")
st.title("🗺️ Geographic Performance")


@st.cache_data
def load() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM master", create_engine(f"sqlite:///{DB_PATH}"))


if not DB_PATH.exists():
    st.warning("No data — run the ETL pipeline first.")
    st.stop()

df = st.session_state.get("filtered_df")
if df is None or df.empty:
    df = load()

state = (
    df.groupby("customer_state")
    .agg(
        revenue=("revenue", "sum"),
        orders=("order_id", "nunique"),
        customers=("customer_unique_id", "nunique"),
        avg_delivery_days=("delivery_days", "mean"),
        avg_review=("review_score", "mean"),
    )
    .reset_index()
    .sort_values("revenue", ascending=False)
    .round(2)
)

c1, c2 = st.columns(2)
c1.plotly_chart(
    px.bar(state, x="customer_state", y="revenue",
           color="revenue", color_continuous_scale="Tealgrn",
           title="Revenue by state"),
    use_container_width=True,
)
c2.plotly_chart(
    px.bar(state, x="customer_state", y="avg_delivery_days",
           color="avg_delivery_days", color_continuous_scale="RdYlGn_r",
           title="Avg delivery days by state"),
    use_container_width=True,
)

st.subheader("State leaderboard")
st.dataframe(state, use_container_width=True, height=480)

st.subheader("Revenue concentration")
state["cum_share"] = (state["revenue"].cumsum() / state["revenue"].sum() * 100).round(1)
st.plotly_chart(
    px.line(state, x="customer_state", y="cum_share", markers=True,
            title="Cumulative revenue share (Pareto)"),
    use_container_width=True,
)
