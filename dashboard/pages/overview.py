"""Overview: revenue trend, payments, weekly patterns."""
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

st.set_page_config(page_title="Overview · Olist", page_icon="📊", layout="wide")

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
[data-testid="stMetricLabel"]{font-family:'DM Mono',monospace!important;font-size:0.7rem!important;color:var(--subtext)!important;text-transform:uppercase;letter-spacing:.08em;}
[data-testid="stPlotlyChart"]{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:.5rem;}
h1,h2,h3{font-family:'Syne',sans-serif;font-weight:800;color:var(--text);}
hr{border-color:var(--border)!important;}
.section-label{font-family:'DM Mono',monospace;font-size:.68rem;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-bottom:.5rem;}
</style>
""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#8892a4", size=12),
    title_font=dict(family="Syne", color="#e2e8f0", size=15),
    xaxis=dict(gridcolor="#1e2330", linecolor="#1e2330", tickfont=dict(color="#8892a4")),
    yaxis=dict(gridcolor="#1e2330", linecolor="#1e2330", tickfont=dict(color="#8892a4")),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8892a4")),
    margin=dict(t=50, b=40, l=40, r=20),
)


# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _load_from_db() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    df = pd.read_sql("SELECT * FROM master", create_engine(f"sqlite:///{DB_PATH}"))
    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"], errors="coerce")
    return df


def get_data() -> pd.DataFrame:
    df = st.session_state.get("filtered_df")
    if df is None or df.empty:
        df = _load_from_db()
    return df


def no_data():
    st.warning("No data — run the ETL pipeline and use the **Home** page first.")
    st.stop()


# ── Charts ────────────────────────────────────────────────────────────────────
def chart_monthly_revenue(df: pd.DataFrame) -> go.Figure:
    s = (
        df.dropna(subset=["order_purchase_timestamp"])
        .set_index("order_purchase_timestamp")
        .resample("MS")["revenue"].sum()
        .reset_index()
    )
    s.columns = ["month", "revenue"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=s["month"], y=s["revenue"], mode="lines",
        fill="tozeroy",
        line=dict(color="#00e5a0", width=2),
        fillcolor="rgba(0,229,160,0.08)",
        name="Revenue",
    ))
    fig.update_layout(title="Monthly Revenue (R$)", **PLOTLY_LAYOUT, height=340)
    return fig


def chart_payment(df: pd.DataFrame) -> go.Figure:
    pay = (
        df.drop_duplicates("order_id")
        .groupby("payment_type")
        .agg(orders=("order_id", "nunique"), revenue=("payment_value", "sum"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    fig = px.bar(pay, x="payment_type", y="revenue",
                 color="revenue", color_continuous_scale=[[0, "#1e2330"], [1, "#00e5a0"]],
                 title="Revenue by Payment Method")
    fig.update_coloraxes(showscale=False)
    fig.update_layout(**PLOTLY_LAYOUT, height=320)
    return fig


def chart_review_dist(df: pd.DataFrame) -> go.Figure:
    rd = (
        df.dropna(subset=["review_score"])
        .groupby("review_score").size()
        .reset_index(name="count")
    )
    colors = ["#ff4444", "#ff8800", "#ffcc00", "#88cc00", "#00e5a0"]
    fig = px.bar(rd, x="review_score", y="count",
                color="review_score",
                color_continuous_scale=[[i/4, c] for i, c in enumerate(colors)],
                title="Review Score Distribution")
    fig.update_coloraxes(showscale=False)
    fig.update_layout(**PLOTLY_LAYOUT, height=320)
    return fig


def chart_dow(df: pd.DataFrame) -> go.Figure:
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow = (
        df.dropna(subset=["order_purchase_timestamp"])
        .assign(dow=lambda d: d["order_purchase_timestamp"].dt.day_name())
        .groupby("dow")["order_id"].nunique()
        .reindex(order, fill_value=0)
        .reset_index()
    )
    dow.columns = ["dow", "orders"]
    fig = go.Figure(go.Bar(
        x=dow["dow"], y=dow["orders"],
        marker=dict(
            color=dow["orders"],
            colorscale=[[0, "#1e2330"], [1, "#00e5a0"]],
            line=dict(width=0),
        ),
    ))
    fig.update_layout(title="Orders by Day of Week", **PLOTLY_LAYOUT, height=300)
    return fig


def chart_hourly(df: pd.DataFrame) -> go.Figure:
    hourly = (
        df.dropna(subset=["order_purchase_timestamp"])
        .assign(hour=lambda d: d["order_purchase_timestamp"].dt.hour)
        .groupby("hour")["order_id"].nunique()
        .reset_index()
    )
    hourly.columns = ["hour", "orders"]
    fig = go.Figure(go.Scatter(
        x=hourly["hour"], y=hourly["orders"], mode="lines+markers",
        fill="tozeroy",
        line=dict(color="#ff6b35", width=2),
        fillcolor="rgba(255,107,53,0.07)",
        marker=dict(color="#ff6b35", size=5),
    ))
    fig.update_layout(
        title="Orders by Hour of Day",
        xaxis=dict(tickvals=list(range(24)), **PLOTLY_LAYOUT["xaxis"]),
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k != "xaxis"},
        height=300,
    )
    return fig


def chart_late_rate(df: pd.DataFrame) -> go.Figure:
    if "is_late" not in df.columns:
        return go.Figure()
    by_month = (
        df.dropna(subset=["order_purchase_timestamp", "is_late"])
        .set_index("order_purchase_timestamp")
        .resample("MS")["is_late"]
        .mean()
        .mul(100)
        .reset_index()
    )
    by_month.columns = ["month", "late_pct"]
    fig = go.Figure(go.Scatter(
        x=by_month["month"], y=by_month["late_pct"], mode="lines",
        line=dict(color="#ff6b35", width=2, dash="dot"),
        fill="tozeroy",
        fillcolor="rgba(255,107,53,0.07)",
    ))
    fig.update_layout(title="Late Delivery Rate (%) by Month", **PLOTLY_LAYOUT, height=300)
    return fig


# ── Page ──────────────────────────────────────────────────────────────────────
st.markdown("## 📊 Overview")

df = get_data()
if df is None or df.empty:
    no_data()

# Summary KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric("Revenue", f"R$ {df['revenue'].sum()/1000:,.1f}K")
c2.metric("Orders", f"{df['order_id'].nunique():,}")
c3.metric("Avg Order Value", f"R$ {df.drop_duplicates('order_id')['revenue'].mean():,.2f}")
c4.metric("Late Rate", f"{df['is_late'].mean()*100:.1f}%" if "is_late" in df.columns else "—")

st.divider()

# Revenue + payment
st.markdown('<p class="section-label">Revenue & Payments</p>', unsafe_allow_html=True)
col_l, col_r = st.columns([2, 1])
with col_l:
    st.plotly_chart(chart_monthly_revenue(df), use_container_width=True)
with col_r:
    st.plotly_chart(chart_payment(df), use_container_width=True)

# Sentiment + delivery
st.markdown('<p class="section-label">Quality & Satisfaction</p>', unsafe_allow_html=True)
col_l2, col_r2 = st.columns(2)
with col_l2:
    st.plotly_chart(chart_review_dist(df), use_container_width=True)
with col_r2:
    st.plotly_chart(chart_late_rate(df), use_container_width=True)

# Temporal patterns
st.markdown('<p class="section-label">Temporal Patterns</p>', unsafe_allow_html=True)
col_a, col_b = st.columns(2)
with col_a:
    st.plotly_chart(chart_dow(df), use_container_width=True)
with col_b:
    st.plotly_chart(chart_hourly(df), use_container_width=True)

# Sentiment breakdown
if "review_sentiment" in df.columns:
    st.markdown('<p class="section-label">Review Sentiment Split</p>', unsafe_allow_html=True)
    sent = df["review_sentiment"].value_counts(dropna=True)
    total = sent.sum()
    s_cols = st.columns(3)
    color_map = {"positive": "#00e5a0", "neutral": "#ffcc00", "negative": "#ff4444"}
    for col, label in zip(s_cols, ["positive", "neutral", "negative"]):
        count = sent.get(label, 0)
        pct = count / total * 100 if total else 0
        col.markdown(f"""
        <div style="background:#141720;border:1px solid #1e2330;border-radius:10px;
            padding:1.2rem;text-align:center;position:relative;overflow:hidden;">
            <div style="position:absolute;top:0;left:0;right:0;height:2px;
                background:{color_map[label]};"></div>
            <p style="font-family:'DM Mono',monospace;font-size:0.7rem;
                text-transform:uppercase;letter-spacing:.1em;color:{color_map[label]};
                margin:0 0 .4rem;">{label}</p>
            <p style="font-family:'Syne',sans-serif;font-size:1.6rem;
                font-weight:800;color:#e2e8f0;margin:0;">{count:,}</p>
            <p style="font-family:'DM Mono',monospace;font-size:.75rem;
                color:#8892a4;margin:0;">{pct:.1f}%</p>
            </div>
            """, unsafe_allow_html=True)