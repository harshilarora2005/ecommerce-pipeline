"""Customers: RFM segmentation, cohorts, segment economics."""
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
st.set_page_config(page_title="Customers · Olist", page_icon="👥", layout="wide")

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

SEGMENT_COLORS = {
    "Champions":          "#00e5a0",
    "Loyal":              "#00b37a",
    "Potential Loyalist": "#66d9a8",
    "New / Recent":       "#88ccff",
    "Promising":          "#ffcc00",
    "Needs Attention":    "#ff9944",
    "At Risk":            "#ff6b35",
    "Hibernating":        "#cc4422",
    "Lost":               "#882200",
}


@st.cache_data(show_spinner=False)
def _load() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    df = pd.read_sql("SELECT * FROM master", create_engine(f"sqlite:///{DB_PATH}"))
    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"], errors="coerce")
    return df


def get_data() -> pd.DataFrame:
    df = st.session_state.get("filtered_df")
    return df if df is not None and not df.empty else _load()


@st.cache_data(show_spinner="Computing RFM…")
def compute_rfm_cached(df_hash: int, _df: pd.DataFrame) -> pd.DataFrame:
    """Cached RFM — keyed by a hash so filters invalidate it."""
    try:
        from src.rfm import compute_rfm
        return compute_rfm(_df)
    except ImportError:
        return _rfm_inline(_df)


def _rfm_inline(df: pd.DataFrame) -> pd.DataFrame:
    """Fallback inline RFM if src.rfm isn't importable."""
    df = df.dropna(subset=["order_purchase_timestamp", "customer_unique_id"]).copy()
    snapshot = df["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
    val_col = "payment_value" if "payment_value" in df.columns else "revenue"
    rfm = df.groupby("customer_unique_id").agg(
        Recency=("order_purchase_timestamp", lambda x: (snapshot - x.max()).days),
        Frequency=("order_id", "nunique"),
        Monetary=(val_col, "sum"),
    ).reset_index()
    rfm["R"] = pd.qcut(rfm["Recency"], 5, labels=[5,4,3,2,1], duplicates="drop").astype(int)
    rfm["F"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1,2,3,4,5], duplicates="drop").astype(int)
    rfm["M"] = pd.qcut(rfm["Monetary"], 5, labels=[1,2,3,4,5], duplicates="drop").astype(int)
    rfm["RFM_Sum"] = rfm["R"] + rfm["F"] + rfm["M"]

    def seg(r, f):
        if r >= 4 and f >= 4: return "Champions"
        if r >= 4 and f >= 3: return "Loyal"
        if r >= 4 and f >= 2: return "Potential Loyalist"
        if r >= 4:            return "New / Recent"
        if r >= 3 and f >= 3: return "Promising"
        if r >= 3:            return "Needs Attention"
        if r >= 2 and f >= 2: return "At Risk"
        if r >= 2:            return "Hibernating"
        return "Lost"

    rfm["Segment"] = rfm.apply(lambda row: seg(row["R"], row["F"]), axis=1)
    return rfm


# ── Page ──────────────────────────────────────────────────────────────────────
st.markdown("## 👥 Customer Segmentation")

df = get_data()
if df is None or df.empty:
    st.warning("No data — run the ETL pipeline and open the Home page first.")
    st.stop()

if df["customer_unique_id"].nunique() < 10 if "customer_unique_id" in df.columns else True:
    st.warning("Not enough customers in filtered view for meaningful RFM. Try widening your filters.")
    st.stop()

rfm = compute_rfm_cached(hash(str(df.shape) + str(df["order_id"].iloc[0])), df)

# Segment summary
seg_agg = (
    rfm.groupby("Segment").agg(
        customers=("Recency", "size"),
        avg_recency=("Recency", "mean"),
        avg_frequency=("Frequency", "mean"),
        avg_monetary=("Monetary", "mean"),
        total_revenue=("Monetary", "sum"),
    )
    .reset_index()
    .sort_values("total_revenue", ascending=False)
    .round(1)
)

# Top KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric("Customers Analyzed", f"{len(rfm):,}")
champions = (rfm["Segment"] == "Champions").sum()
c2.metric("Champions", f"{champions:,}",
          delta=f"{champions/len(rfm)*100:.1f}%")
at_risk = rfm["Segment"].isin(["At Risk", "Lost", "Hibernating"]).sum()
c3.metric("At Risk / Lost", f"{at_risk:,}",
          delta=f"-{at_risk/len(rfm)*100:.1f}%", delta_color="inverse")
c4.metric("Avg Customer Value", f"R$ {rfm['Monetary'].mean():,.2f}")

st.divider()

# ── Segment distribution ───────────────────────────────────────────────────────
st.markdown('<p class="section-label">Segment Breakdown</p>', unsafe_allow_html=True)
col_pie, col_bar = st.columns(2)

with col_pie:
    seg_counts = rfm["Segment"].value_counts().reset_index()
    seg_counts.columns = ["Segment", "Customers"]
    fig_pie = go.Figure(go.Pie(
        labels=seg_counts["Segment"],
        values=seg_counts["Customers"],
        hole=0.55,
        marker=dict(colors=[SEGMENT_COLORS.get(s, "#666") for s in seg_counts["Segment"]],
                    line=dict(color="#0d0f12", width=2)),
        textfont=dict(color="#e2e8f0", family="DM Mono", size=11),
    ))
    fig_pie.update_layout(
        title="Customers by Segment",
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
        height=380,
        annotations=[dict(text=f"{len(rfm):,}<br>customers",
                          font=dict(size=14, color="#e2e8f0", family="Syne"),
                          showarrow=False)]
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_bar:
    fig_seg = px.bar(
        seg_agg.sort_values("total_revenue", ascending=True),
        x="total_revenue", y="Segment", orientation="h",
        title="Revenue by Segment",
        color="Segment",
        color_discrete_map=SEGMENT_COLORS,
        text=seg_agg.sort_values("total_revenue")["total_revenue"].apply(
            lambda v: f"R$ {v/1000:.0f}K"),
    )
    fig_seg.update_traces(textposition="outside", textfont_color="#8892a4")
    fig_seg.update_layout(
        showlegend=False,
        yaxis=dict(tickfont=dict(color="#e2e8f0"), gridcolor="#1e2330"),
        xaxis=dict(gridcolor="#1e2330", tickfont=dict(color="#8892a4")),
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
        height=380,
    )
    st.plotly_chart(fig_seg, use_container_width=True)

# ── Scatter ────────────────────────────────────────────────────────────────────
st.markdown('<p class="section-label">Recency vs Monetary</p>', unsafe_allow_html=True)
sample_rfm = rfm.sample(min(5000, len(rfm)), random_state=42)
fig_scatter = px.scatter(
    sample_rfm, x="Recency", y="Monetary", color="Segment",
    color_discrete_map=SEGMENT_COLORS,
    opacity=0.55, log_y=True, height=480,
    title="Recency (days) vs Monetary Value — coloured by segment",
    hover_data=["Frequency", "RFM_Sum"],
)
fig_scatter.update_layout(**PLOTLY_LAYOUT)
st.plotly_chart(fig_scatter, use_container_width=True)

# ── Segment economics table ────────────────────────────────────────────────────
st.markdown('<p class="section-label">Segment Economics</p>', unsafe_allow_html=True)
st.dataframe(seg_agg, use_container_width=True, height=380,
             column_config={
                 "Segment": st.column_config.TextColumn("Segment"),
                 "customers": st.column_config.NumberColumn("Customers"),
                 "avg_recency": st.column_config.NumberColumn("Avg Recency (d)", format="%.1f"),
                 "avg_frequency": st.column_config.NumberColumn("Avg Orders", format="%.2f"),
                 "avg_monetary": st.column_config.NumberColumn("Avg Value (R$)", format="R$ %.2f"),
                 "total_revenue": st.column_config.ProgressColumn("Total Revenue",
                     min_value=0, max_value=float(seg_agg["total_revenue"].max()),
                     format="R$ %.0f"),
             })

# ── Top 20 customers ───────────────────────────────────────────────────────────
st.markdown('<p class="section-label">Top 20 Customers by Lifetime Value</p>', unsafe_allow_html=True)
st.dataframe(
    rfm.sort_values("Monetary", ascending=False).head(20).round(2).reset_index(drop=True),
    use_container_width=True,
    column_config={
        "Monetary": st.column_config.NumberColumn("LTV (R$)", format="R$ %.2f"),
        "Recency": st.column_config.NumberColumn("Recency (d)"),
    }
)