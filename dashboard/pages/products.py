"""Products: category revenue, freight, top sellers."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))
from src.eda_utils import chart_revenue_by_category

DB_PATH = ROOT / "data" / "ecommerce.db"
st.set_page_config(page_title="Products", page_icon="📦", layout="wide")
st.title("📦 Products")


@st.cache_data
def load() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    return pd.read_sql("SELECT * FROM master", create_engine(f"sqlite:///{DB_PATH}"))


df = st.session_state.get("filtered_df")
if df is None or df.empty:
    df = load()
if df.empty:
    st.warning("No data — run the ETL pipeline first.")
    st.stop()

top_n = st.slider("Top categories", 5, 30, 15)
st.plotly_chart(chart_revenue_by_category(df, top_n), use_container_width=True)

st.subheader("Category KPIs")
cat = (
    df.dropna(subset=["product_category_name"])
    .groupby("product_category_name")
    .agg(
        revenue=("revenue", "sum"),
        orders=("order_id", "nunique"),
        avg_price=("price", "mean"),
        avg_freight=("freight_value", "mean"),
        avg_review=("review_score", "mean"),
    )
    .sort_values("revenue", ascending=False)
    .head(top_n)
    .round(2)
    .reset_index()
)
st.dataframe(cat, use_container_width=True, height=420)

st.subheader("Price vs freight (sample of items)")
sample = df.dropna(subset=["price", "freight_value"]).sample(min(3000, len(df)), random_state=1)
st.plotly_chart(
    px.scatter(sample, x="price", y="freight_value", color="product_category_name",
               opacity=0.5, title="Price vs freight value", height=480)
    .update_layout(showlegend=False),
    use_container_width=True,
)
