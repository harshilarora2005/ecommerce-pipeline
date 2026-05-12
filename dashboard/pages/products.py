"""Products: category revenue, freight, top sellers, sentiment by category."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

DB_PATH = ROOT / "data" / "ecommerce.db"
st.set_page_config(page_title="Products · Olist", page_icon="📦", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap');
:root{--bg:#0d0f12;--surface:#141720;--border:#1e2330;--accent:#00e5a0;--accent2:#ff6b35;--muted:#4a5568;--text:#e2e8f0;--subtext:#8892a4;}
html,body,[data-testid="stAppViewContainer"]{background:var(--bg)!important;font-family:'DM Sans',sans-serif;color:var(--text);}
[data-testid="stSidebar"]{background:var(--surface)!important;border-right:1px solid var(--border);}
[data-testid="stSidebar"] *{color:var(--text)!important;}
.main .block-container{padding:2rem 2.5rem;max-width:1500px;}
[data-testid="metric-container"]{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1.2rem 1.4rem;position:relative;overflow:hidden;}
[data-testid="metric-container"]::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--accent),transparent);}
[data-testid="stMetricValue"]{font-family:'Syne',sans-serif!important;font-size:1.7rem!important;font-weight:800!important;color:var(--text)!important;}
[data-testid="stMetricLabel"]{font-family:'DM Mono',monospace!important;font-size:.7rem!important;color:var(--subtext)!important;text-transform:uppercase;letter-spacing:.08em;}
[data-testid="stPlotlyChart"]{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:.5rem;}
[data-testid="stDataFrame"]{background:var(--surface)!important;border:1px solid var(--border)!important;border-radius:10px;}
h1,h2,h3{font-family:'Syne',sans-serif;font-weight:800;color:var(--text);}
hr{border-color:var(--border)!important;}
.section-label{font-family:'DM Mono',monospace;font-size:.68rem;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-bottom:.5rem;}
</style>
""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#8892a4", size=12),
    title_font=dict(family="Syne", color="#e2e8f0", size=15),
    xaxis=dict(gridcolor="#1e2330", linecolor="#1e2330", tickfont=dict(color="#8892a4")),
    yaxis=dict(gridcolor="#1e2330", linecolor="#1e2330", tickfont=dict(color="#8892a4")),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8892a4")),
    margin=dict(t=50, b=40, l=40, r=20),
)


@st.cache_data(show_spinner=False)
def _load() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    return pd.read_sql("SELECT * FROM master", create_engine(f"sqlite:///{DB_PATH}"))


def get_data() -> pd.DataFrame:
    df = st.session_state.get("filtered_df")
    return df if df is not None and not df.empty else _load()


st.markdown("## 📦 Products")

df = get_data()
if df is None or df.empty:
    st.warning("No data — run the ETL pipeline and open the Home page first.")
    st.stop()

# Controls
st.markdown('<p class="section-label">Configure</p>', unsafe_allow_html=True)
top_n = st.slider("Top N categories", 5, 40, 15, label_visibility="collapsed")

# KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric("Unique Products", f"{df['product_id'].nunique():,}")
c2.metric("Unique Categories", f"{df['product_category_name'].nunique():,}")
c3.metric("Avg Item Price", f"R$ {df['price'].mean():,.2f}")
c4.metric("Avg Freight Value", f"R$ {df['freight_value'].mean():,.2f}")

st.divider()

# ── Revenue by category (horizontal bar) ──────────────────────────────────────
st.markdown('<p class="section-label">Revenue Ranking</p>', unsafe_allow_html=True)
cat_rev = (
    df.groupby("product_category_name", dropna=True)["revenue"]
    .sum()
    .sort_values(ascending=False)
    .head(top_n)
    .reset_index()
)
fig_cat = go.Figure(go.Bar(
    y=cat_rev["product_category_name"],
    x=cat_rev["revenue"],
    orientation="h",
    marker=dict(
        color=cat_rev["revenue"],
        colorscale=[[0, "#1e2330"], [0.5, "#00b37a"], [1, "#00e5a0"]],
        line=dict(width=0),
    ),
    text=cat_rev["revenue"].apply(lambda v: f"R$ {v/1000:.1f}K"),
    textposition="outside",
    textfont=dict(color="#8892a4", size=11),
))
fig_cat.update_layout(
    title=f"Top {top_n} Categories by Revenue",
    yaxis=dict(autorange="reversed", categoryorder="total ascending",
               gridcolor="#1e2330", tickfont=dict(color="#e2e8f0")),
    xaxis=dict(gridcolor="#1e2330", tickfont=dict(color="#8892a4")),
    **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
    height=max(380, top_n * 28),
)
st.plotly_chart(fig_cat, use_container_width=True)

# ── Category KPI table + avg review heatmap ───────────────────────────────────
st.markdown('<p class="section-label">Category KPIs</p>', unsafe_allow_html=True)
cat_kpi = (
    df.dropna(subset=["product_category_name"])
    .groupby("product_category_name")
    .agg(
        revenue=("revenue", "sum"),
        orders=("order_id", "nunique"),
        avg_price=("price", "mean"),
        avg_freight=("freight_value", "mean"),
        avg_review=("review_score", "mean"),
        avg_delivery=("delivery_days", "mean"),
    )
    .sort_values("revenue", ascending=False)
    .head(top_n)
    .round(2)
    .reset_index()
)
col_table, col_review = st.columns([3, 2])
with col_table:
    st.dataframe(cat_kpi, use_container_width=True, height=420,
                 column_config={
                     "product_category_name": st.column_config.TextColumn("Category"),
                     "revenue": st.column_config.NumberColumn("Revenue (R$)", format="R$ %.0f"),
                     "orders": st.column_config.NumberColumn("Orders"),
                     "avg_price": st.column_config.NumberColumn("Avg Price", format="R$ %.2f"),
                     "avg_freight": st.column_config.NumberColumn("Avg Freight", format="R$ %.2f"),
                     "avg_review": st.column_config.ProgressColumn("Avg Review", min_value=1, max_value=5, format="%.2f"),
                     "avg_delivery": st.column_config.NumberColumn("Avg Delivery (d)", format="%.1f"),
                 })
with col_review:
    fig_review_bar = go.Figure(go.Bar(
        x=cat_kpi["avg_review"],
        y=cat_kpi["product_category_name"],
        orientation="h",
        marker=dict(
            color=cat_kpi["avg_review"],
            colorscale=[[0, "#ff4444"], [0.5, "#ffcc00"], [1, "#00e5a0"]],
            cmin=1, cmax=5,
        ),
        text=cat_kpi["avg_review"].apply(lambda v: f"★ {v:.2f}"),
        textposition="outside",
        textfont=dict(size=10, color="#8892a4"),
    ))
    fig_review_bar.update_layout(
        title="Avg Review by Category",
        yaxis=dict(autorange="reversed", tickfont=dict(color="#e2e8f0", size=10),
                   gridcolor="#1e2330"),
        xaxis=dict(range=[0, 5.5], gridcolor="#1e2330", tickfont=dict(color="#8892a4")),
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
        height=420,
    )
    st.plotly_chart(fig_review_bar, use_container_width=True)

# ── Price vs freight scatter ───────────────────────────────────────────────────
st.markdown('<p class="section-label">Price vs Freight</p>', unsafe_allow_html=True)
sample = (
    df.dropna(subset=["price", "freight_value", "product_category_name"])
    .sample(min(4000, len(df)), random_state=42)
)
fig_scatter = px.scatter(
    sample, x="price", y="freight_value",
    color="product_category_name",
    opacity=0.5, height=460,
    title="Item Price vs Freight Value (sampled)",
    color_discrete_sequence=px.colors.qualitative.Dark24,
)
fig_scatter.update_layout(**PLOTLY_LAYOUT, showlegend=False)
st.plotly_chart(fig_scatter, use_container_width=True)

# ── Profit margin distribution ─────────────────────────────────────────────────
if "profit_margin" in df.columns:
    st.markdown('<p class="section-label">Profit Margin Distribution</p>', unsafe_allow_html=True)
    pm = df["profit_margin"].dropna().clip(-100, 100)
    fig_pm = go.Figure(go.Histogram(
        x=pm, nbinsx=80,
        marker=dict(color="#00e5a0", opacity=0.7, line=dict(width=0)),
    ))
    fig_pm.add_vline(x=0, line=dict(color="#ff6b35", dash="dash", width=1.5))
    fig_pm.update_layout(
        title="Profit Margin % (clipped to ±100)",
        **PLOTLY_LAYOUT, height=300,
    )
    st.plotly_chart(fig_pm, use_container_width=True)