"""Overview: revenue trend, payments, weekly patterns."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))
from src.eda_utils import (
    chart_monthly_revenue, chart_payment_breakdown, chart_review_distribution,
)

DB_PATH = ROOT / "data" / "ecommerce.db"
st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")
st.title("📊 Overview")


@st.cache_data
def load() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    df = pd.read_sql("SELECT * FROM master", create_engine(f"sqlite:///{DB_PATH}"))
    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"], errors="coerce")
    return df


df = st.session_state.get("filtered_df")
if df is None or df.empty:
    df = load()

if df.empty:
    st.warning("No data — run the ETL pipeline first.")
    st.stop()

st.plotly_chart(chart_monthly_revenue(df), use_container_width=True)

c1, c2 = st.columns(2)
c1.plotly_chart(chart_payment_breakdown(df), use_container_width=True)
c2.plotly_chart(chart_review_distribution(df), use_container_width=True)

st.subheader("Orders by day of week")
dow = (
    df.dropna(subset=["order_purchase_timestamp"])
    .assign(dow=lambda d: d["order_purchase_timestamp"].dt.day_name())
    .groupby("dow")["order_id"].nunique().reset_index()
)
order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
dow["dow"] = pd.Categorical(dow["dow"], categories=order, ordered=True)
dow = dow.sort_values("dow")
st.plotly_chart(
    px.bar(dow, x="dow", y="order_id", color="order_id",
           color_continuous_scale="Tealgrn", title="Order volume by weekday"),
    use_container_width=True,
)

st.subheader("Hourly purchase pattern")
hourly = (
    df.dropna(subset=["order_purchase_timestamp"])
    .assign(hour=lambda d: d["order_purchase_timestamp"].dt.hour)
    .groupby("hour")["order_id"].nunique().reset_index()
)
st.plotly_chart(
    px.area(hourly, x="hour", y="order_id", title="Orders by hour of day"),
    use_container_width=True,
)
