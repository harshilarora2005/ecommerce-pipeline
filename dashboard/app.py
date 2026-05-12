"""Main Streamlit entry — KPI dashboard for the Olist e-commerce dataset."""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"

st.set_page_config(
    page_title="E-Commerce Sales Intelligence",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- styling ----
st.markdown("""
<style>
  .main .block-container {padding-top: 2rem; max-width: 1400px;}
  [data-testid="stMetricValue"] {font-size: 2rem; font-weight: 700;}
  [data-testid="stMetricLabel"] {color: #64748b; font-size: 0.85rem;}
  .stTabs [data-baseweb="tab-list"] {gap: 8px;}
  h1, h2, h3 {font-family: -apple-system, BlinkMacSystemFont, sans-serif;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Loading data…")
def load_master() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    engine = create_engine(f"sqlite:///{DB_PATH}")
    df = pd.read_sql("SELECT * FROM master", engine)
    for c in ["order_purchase_timestamp", "order_delivered_customer_date",
              "order_estimated_delivery_date"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("🔎 Filters")
    if df.empty:
        return df

    min_d, max_d = df["order_purchase_timestamp"].min(), df["order_purchase_timestamp"].max()
    date_range = st.sidebar.date_input(
        "Date range", value=(min_d.date(), max_d.date()),
        min_value=min_d.date(), max_value=max_d.date(),
    )
    states = sorted(df["customer_state"].dropna().unique().tolist())
    sel_states = st.sidebar.multiselect("States", states, default=states)
    cats = sorted(df["product_category_name"].dropna().unique().tolist())
    sel_cats = st.sidebar.multiselect("Categories (top 30)", cats[:30], default=[])

    mask = (
        (df["order_purchase_timestamp"].dt.date >= date_range[0])
        & (df["order_purchase_timestamp"].dt.date <= date_range[1])
        & (df["customer_state"].isin(sel_states))
    )
    if sel_cats:
        mask &= df["product_category_name"].isin(sel_cats)
    return df[mask]


st.title("🛒 E-Commerce Sales Intelligence")
st.caption("End-to-end analytics on the Brazilian Olist dataset — ETL · EDA · RFM · Forecasting · Churn")

df = load_master()
if df.empty:
    st.warning(
        "**No data found.** Either:\n"
        "1. Drop Olist CSVs into `data/raw/` and run `notebooks/01_etl_pipeline.ipynb`, or\n"
        "2. Run `python -m src.sample_data` then `python -m src.etl` to generate a synthetic demo dataset."
    )
    st.stop()

filtered = sidebar_filters(df)
st.session_state["filtered_df"] = filtered  # share with pages

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💰 Revenue", f"R$ {filtered['revenue'].sum()/1000:,.1f}K")
c2.metric("📦 Orders", f"{filtered['order_id'].nunique():,}")
c3.metric("👥 Customers", f"{filtered['customer_unique_id'].nunique():,}")
c4.metric("⭐ Avg Review", f"{filtered['review_score'].mean():.2f}")
c5.metric("🚚 Avg Delivery", f"{filtered['delivery_days'].mean():.1f}d")

st.divider()
st.markdown("### 📑 Navigate")
st.markdown(
    "- **Overview** — revenue trend, payments, daily patterns\n"
    "- **Products** — top categories, freight, return signals\n"
    "- **Customers** — RFM segmentation & cohorts\n"
    "- **Geo Map** — state-level revenue and delivery performance"
)
st.info("Use the sidebar to switch pages and filter the dataset.", icon="👈")
