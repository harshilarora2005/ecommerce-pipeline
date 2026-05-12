"""Customers: RFM segmentation."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))
from src.rfm import compute_rfm, segment_summary

DB_PATH = ROOT / "data" / "ecommerce.db"
st.set_page_config(page_title="Customers", page_icon="👥", layout="wide")
st.title("👥 Customer Segmentation (RFM)")


@st.cache_data
def load() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM master", create_engine(f"sqlite:///{DB_PATH}"))
    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"], errors="coerce")
    return df


@st.cache_data
def get_rfm(df: pd.DataFrame) -> pd.DataFrame:
    return compute_rfm(df)


if not DB_PATH.exists():
    st.warning("No data — run the ETL pipeline first.")
    st.stop()

df = st.session_state.get("filtered_df")
if df is None or df.empty:
    df = load()

rfm = get_rfm(df)
summary = segment_summary(rfm)

c1, c2, c3 = st.columns(3)
c1.metric("Customers analyzed", f"{len(rfm):,}")
c2.metric("Champions", f"{(rfm['Segment']=='Champions').sum():,}")
c3.metric("At Risk + Lost", f"{rfm['Segment'].isin(['At Risk','Lost','Hibernating']).sum():,}")

st.subheader("Segment distribution")
seg_counts = rfm["Segment"].value_counts().reset_index()
seg_counts.columns = ["Segment", "Customers"]
st.plotly_chart(
    px.bar(seg_counts, x="Segment", y="Customers", color="Segment",
           title="Customers per RFM segment"),
    use_container_width=True,
)

st.subheader("Segment economics")
st.dataframe(summary.round(2), use_container_width=True)

st.subheader("Recency vs Monetary (log)")
st.plotly_chart(
    px.scatter(rfm, x="Recency", y="Monetary", color="Segment",
               log_y=True, opacity=0.5, height=520),
    use_container_width=True,
)

st.subheader("Top 20 customers by revenue")
st.dataframe(
    rfm.sort_values("Monetary", ascending=False).head(20).round(2),
    use_container_width=True,
)
