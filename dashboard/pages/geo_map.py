"""Geo: state-level revenue & delivery performance."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))
from dashboard.data_source import load_master_df
st.set_page_config(page_title="Geo · Olist", page_icon="🗺️", layout="wide")

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
    return load_master_df()


def get_data() -> pd.DataFrame:
    df = st.session_state.get("filtered_df")
    return df if df is not None and not df.empty else _load()


st.markdown("## 🗺️ Geographic Performance")

df = get_data()
if df is None or df.empty:
    st.warning("No data — run the ETL pipeline and open the Home page first.")
    st.stop()

# ── State aggregation ─────────────────────────────────────────────────────────
state = (
    df.groupby("customer_state")
    .agg(
        revenue=("revenue", "sum"),
        orders=("order_id", "nunique"),
        customers=("customer_unique_id", "nunique") if "customer_unique_id" in df.columns
            else ("order_id", "nunique"),
        avg_delivery_days=("delivery_days", "mean"),
        avg_review=("review_score", "mean"),
        late_rate=("is_late", "mean") if "is_late" in df.columns else ("order_id", "count"),
    )
    .reset_index()
    .sort_values("revenue", ascending=False)
    .round(2)
)
if "is_late" in df.columns:
    state["late_rate"] = (state["late_rate"] * 100).round(1)

# Pareto
state["cum_share"] = (state["revenue"].cumsum() / state["revenue"].sum() * 100).round(1)

# KPIs
c1, c2, c3, c4 = st.columns(4)
top_state = state.iloc[0]
c1.metric("Top State", top_state["customer_state"],
          delta=f"R$ {top_state['revenue']/1000:.0f}K revenue")
c2.metric("States in View", f"{len(state)}")
pareto_states = (state["cum_share"] <= 80).sum()
c3.metric("80% Revenue From", f"{pareto_states} states")
worst_delivery = state.loc[state["avg_delivery_days"].idxmax()]
c4.metric("Slowest Delivery", worst_delivery["customer_state"],
          delta=f"{worst_delivery['avg_delivery_days']:.1f}d avg", delta_color="inverse")

st.divider()

# ── Revenue bar ────────────────────────────────────────────────────────────────
st.markdown('<p class="section-label">Revenue by State</p>', unsafe_allow_html=True)
fig_rev = go.Figure(go.Bar(
    x=state["customer_state"],
    y=state["revenue"],
    marker=dict(
        color=state["revenue"],
        colorscale=[[0, "#1e2330"], [0.5, "#00b37a"], [1, "#00e5a0"]],
        line=dict(width=0),
    ),
    text=state["revenue"].apply(lambda v: f"R$ {v/1000:.0f}K"),
    textposition="outside",
    textfont=dict(color="#8892a4", size=10),
))
fig_rev.update_layout(title="Revenue by Customer State", **PLOTLY_LAYOUT, height=360)
st.plotly_chart(fig_rev, use_container_width=True)

# ── Delivery + review side by side ────────────────────────────────────────────
st.markdown('<p class="section-label">Delivery & Quality</p>', unsafe_allow_html=True)
col_del, col_rev2 = st.columns(2)

with col_del:
    fig_del = go.Figure(go.Bar(
        x=state.sort_values("avg_delivery_days", ascending=False)["customer_state"],
        y=state.sort_values("avg_delivery_days", ascending=False)["avg_delivery_days"],
        marker=dict(
            color=state.sort_values("avg_delivery_days", ascending=False)["avg_delivery_days"],
            colorscale=[[0, "#00e5a0"], [0.5, "#ffcc00"], [1, "#ff4444"]],
            line=dict(width=0),
        ),
    ))
    fig_del.update_layout(title="Avg Delivery Days by State", **PLOTLY_LAYOUT, height=340)
    st.plotly_chart(fig_del, use_container_width=True)

with col_rev2:
    fig_r = go.Figure(go.Bar(
        x=state.sort_values("avg_review", ascending=False)["customer_state"],
        y=state.sort_values("avg_review", ascending=False)["avg_review"],
        marker=dict(
            color=state.sort_values("avg_review", ascending=False)["avg_review"],
            colorscale=[[0, "#ff4444"], [0.5, "#ffcc00"], [1, "#00e5a0"]],
            cmin=1, cmax=5,
            line=dict(width=0),
        ),
    ))
    fig_r.update_layout(title="Avg Review Score by State", **PLOTLY_LAYOUT, height=340)
    st.plotly_chart(fig_r, use_container_width=True)

# ── Late rate ─────────────────────────────────────────────────────────────────
if "late_rate" in state.columns and "is_late" in df.columns:
    st.markdown('<p class="section-label">Late Delivery Rate</p>', unsafe_allow_html=True)
    sorted_late = state.sort_values("late_rate", ascending=False)
    fig_late = go.Figure(go.Bar(
        x=sorted_late["customer_state"],
        y=sorted_late["late_rate"],
        marker=dict(
            color=sorted_late["late_rate"],
            colorscale=[[0, "#00e5a0"], [0.5, "#ffcc00"], [1, "#ff4444"]],
            line=dict(width=0),
        ),
        text=sorted_late["late_rate"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
        textfont=dict(color="#8892a4", size=10),
    ))
    fig_late.update_layout(title="Late Delivery Rate (%) by State", **PLOTLY_LAYOUT, height=340)
    st.plotly_chart(fig_late, use_container_width=True)

# ── Pareto ─────────────────────────────────────────────────────────────────────
st.markdown('<p class="section-label">Revenue Concentration (Pareto)</p>', unsafe_allow_html=True)
fig_pareto = go.Figure()
fig_pareto.add_trace(go.Bar(
    x=state["customer_state"], y=state["revenue"] / 1000,
    name="Revenue (R$ K)",
    marker=dict(color="#1e2330", line=dict(width=0)),
    yaxis="y",
))
fig_pareto.add_trace(go.Scatter(
    x=state["customer_state"], y=state["cum_share"],
    name="Cumulative %",
    mode="lines+markers",
    line=dict(color="#00e5a0", width=2),
    marker=dict(color="#00e5a0", size=5),
    yaxis="y2",
))
fig_pareto.add_hline(y=80, line=dict(color="#ff6b35", dash="dash", width=1),
                      annotation_text="80% line",
                      annotation_font=dict(color="#ff6b35", family="DM Mono", size=10),
                      yref="y2")
fig_pareto.update_layout(
    title="Revenue Pareto — State Concentration",
    yaxis=dict(title="Revenue (R$ K)", gridcolor="#1e2330", tickfont=dict(color="#8892a4")),
    yaxis2=dict(title="Cumulative %", overlaying="y", side="right",
                range=[0, 105], gridcolor="rgba(0,0,0,0)",
                tickfont=dict(color="#00e5a0"), ticksuffix="%"),
    **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
    height=400,
)
st.plotly_chart(fig_pareto, use_container_width=True)

# ── Leaderboard ────────────────────────────────────────────────────────────────
st.markdown('<p class="section-label">State Leaderboard</p>', unsafe_allow_html=True)
display_cols = [c for c in ["customer_state", "revenue", "orders", "customers",
                              "avg_delivery_days", "avg_review", "late_rate", "cum_share"]
                if c in state.columns]
st.dataframe(
    state[display_cols],
    use_container_width=True, height=480,
    column_config={
        "customer_state": st.column_config.TextColumn("State"),
        "revenue": st.column_config.NumberColumn("Revenue (R$)", format="R$ %.0f"),
        "orders": st.column_config.NumberColumn("Orders"),
        "customers": st.column_config.NumberColumn("Customers"),
        "avg_delivery_days": st.column_config.NumberColumn("Avg Delivery (d)", format="%.1f"),
        "avg_review": st.column_config.ProgressColumn("Avg Review", min_value=1, max_value=5, format="%.2f"),
        "late_rate": st.column_config.NumberColumn("Late Rate (%)", format="%.1f%%"),
        "cum_share": st.column_config.NumberColumn("Cum. Share (%)", format="%.1f%%"),
    }
)