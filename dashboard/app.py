"""Main Streamlit entry — Olist E-Commerce Intelligence Dashboard."""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from dashboard.data_source import load_master_df

st.set_page_config(
    page_title="Olist Intelligence",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global styles ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap');

:root {
  --bg:       #0d0f12;
  --surface:  #141720;
  --border:   #1e2330;
  --accent:   #00e5a0;
  --accent2:  #ff6b35;
  --muted:    #4a5568;
  --text:     #e2e8f0;
  --subtext:  #8892a4;
}

html, body, [data-testid="stAppViewContainer"] {
  background: var(--bg) !important;
  font-family: 'DM Sans', sans-serif;
  color: var(--text);
}

[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] * { color: var(--text) !important; }

.main .block-container { padding: 2rem 2.5rem; max-width: 1500px; }

/* Metrics */
[data-testid="metric-container"] {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.2rem 1.4rem;
  position: relative;
  overflow: hidden;
}
[data-testid="metric-container"]::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent), transparent);
}
[data-testid="stMetricValue"] {
  font-family: 'Syne', sans-serif !important;
  font-size: clamp(1.1rem, 1.4vw, 1.6rem) !important;
  font-weight: 800 !important;
  color: var(--text) !important;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
[data-testid="stMetricLabel"] {
  font-family: 'DM Mono', monospace !important;
  font-size: 0.72rem !important;
  color: var(--subtext) !important;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
[data-testid="stMetricDelta"] { font-size: 0.78rem !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  gap: 0;
  border-bottom: 1px solid var(--border);
  background: transparent;
}
.stTabs [data-baseweb="tab"] {
  font-family: 'DM Mono', monospace;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--subtext);
  padding: 0.65rem 1.2rem;
  border-bottom: 2px solid transparent;
}
.stTabs [aria-selected="true"] {
  color: var(--accent) !important;
  border-bottom: 2px solid var(--accent) !important;
  background: transparent !important;
}

/* Divider */
hr { border-color: var(--border) !important; }

/* Sidebar widgets */
[data-testid="stSelectbox"] > div,
[data-testid="stMultiSelect"] > div,
[data-testid="stDateInput"] > div {
  background: var(--bg) !important;
  border-color: var(--border) !important;
}

/* Plotly chart containers */
[data-testid="stPlotlyChart"] {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.5rem;
}

/* Dataframe */
[data-testid="stDataFrame"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px;
}

/* Warning / info */
[data-testid="stAlert"] {
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface) !important;
  font-family: 'DM Mono', monospace;
  font-size: 0.82rem;
}

/* Headings */
h1 { font-family: 'Syne', sans-serif; font-weight: 800; letter-spacing: -0.02em; }
h2, h3 {
  font-family: 'Syne', sans-serif;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.01em;
}

/* Sidebar section labels */
.sidebar-section {
  font-family: 'DM Mono', monospace;
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--muted);
  margin: 1.2rem 0 0.4rem 0;
}

/* Logo/brand strip */
.brand-strip {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  margin-bottom: 0.2rem;
}
.brand-name {
  font-family: 'Syne', sans-serif;
  font-size: 1.6rem;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.02em;
}
.brand-tag {
  font-family: 'DM Mono', monospace;
  font-size: 0.7rem;
  color: var(--accent);
  background: rgba(0,229,160,0.08);
  border: 1px solid rgba(0,229,160,0.2);
  border-radius: 4px;
  padding: 0.15rem 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
.brand-sub {
  font-family: 'DM Sans', sans-serif;
  font-size: 0.85rem;
  color: var(--subtext);
  margin-bottom: 1.5rem;
}

/* Metric row label */
.section-label {
  font-family: 'DM Mono', monospace;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted);
  margin-bottom: 0.6rem;
}

/* Delta positive/negative */
[data-testid="stMetricDeltaIcon-Up"] { color: var(--accent) !important; }
[data-testid="stMetricDeltaIcon-Down"] { color: var(--accent2) !important; }

button[kind="primary"] {
  background: var(--accent) !important;
  color: #000 !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.78rem !important;
  letter-spacing: 0.06em !important;
  border-radius: 6px !important;
  border: none !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="⏳ Loading warehouse…")
def load_master() -> pd.DataFrame:
    df = load_master_df()
    if df.empty:
        return df
    for c in ["order_purchase_timestamp", "order_delivered_customer_date",
              "order_estimated_delivery_date"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply sidebar filters and cache result in session_state."""
    st.sidebar.markdown('<p class="sidebar-section">Time Range</p>', unsafe_allow_html=True)
    ts = df["order_purchase_timestamp"].dropna()
    min_d, max_d = ts.min().date(), ts.max().date()
    date_range = st.sidebar.date_input(
        "Date range", value=(min_d, max_d),
        min_value=min_d, max_value=max_d, label_visibility="collapsed",
    )
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        d0, d1 = date_range
    else:
        d0, d1 = min_d, max_d

    st.sidebar.markdown('<p class="sidebar-section">Customer State</p>', unsafe_allow_html=True)
    states = sorted(df["customer_state"].dropna().unique().tolist())
    sel_states = st.sidebar.multiselect("States", states, default=states,
                                        label_visibility="collapsed")
    if not sel_states:
        sel_states = states

    st.sidebar.markdown('<p class="sidebar-section">Category</p>', unsafe_allow_html=True)
    cats = sorted(df["product_category_name"].dropna().unique().tolist())
    sel_cats = st.sidebar.multiselect("Categories", cats, default=[],
                                    placeholder="All categories",
                                    label_visibility="collapsed")

    st.sidebar.markdown('<p class="sidebar-section">Min Review Score</p>', unsafe_allow_html=True)
    min_review = st.sidebar.slider("Min review", 1.0, 5.0, 1.0, 0.5,
                                    label_visibility="collapsed")

    st.sidebar.markdown('<p class="sidebar-section">Order Status</p>', unsafe_allow_html=True)
    statuses = sorted(df["order_status"].dropna().unique().tolist()) if "order_status" in df.columns else []
    sel_status = st.sidebar.multiselect("Status", statuses, default=statuses,
                                        label_visibility="collapsed") if statuses else statuses

    # Build mask
    mask = (
        (df["order_purchase_timestamp"].dt.date >= d0)
        & (df["order_purchase_timestamp"].dt.date <= d1)
        & (df["customer_state"].isin(sel_states))
    )
    if sel_cats:
        mask &= df["product_category_name"].isin(sel_cats)
    if "review_score" in df.columns:
        mask &= df["review_score"].isna() | (df["review_score"] >= min_review)
    if statuses and sel_status:
        mask &= df["order_status"].isin(sel_status)

    filtered = df[mask].copy()

    # Reset button
    st.sidebar.markdown("---")
    if st.sidebar.button("↺ Reset filters", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown(
        f'<p style="font-family:\'DM Mono\',monospace;font-size:0.7rem;color:#4a5568;margin-top:0.5rem;">'
        f'{len(filtered):,} / {len(df):,} rows</p>',
        unsafe_allow_html=True,
    )
    return filtered


# ── Error states ───────────────────────────────────────────────────────────────
def show_no_data_error():
    st.markdown("""
    <div style="
      margin-top: 4rem;
      padding: 3rem;
      background: #141720;
      border: 1px solid #1e2330;
      border-radius: 16px;
      text-align: center;
    ">
      <div style="font-size:3rem;margin-bottom:1rem;">📭</div>
      <h2 style="font-family:'Syne',sans-serif;font-weight:800;color:#e2e8f0;margin-bottom:0.5rem;">
        No data found
      </h2>
      <p style="font-family:'DM Sans',sans-serif;color:#8892a4;max-width:480px;margin:0 auto 2rem;">
        The SQLite warehouse is missing or empty. Run the ETL pipeline to populate it.
      </p>
      <div style="
        font-family:'DM Mono',monospace;
        font-size:0.82rem;
        background:#0d0f12;
        border:1px solid #1e2330;
        border-radius:8px;
        padding:1.2rem 2rem;
        text-align:left;
        display:inline-block;
        color:#00e5a0;
        max-width:520px;
      ">
        <span style="color:#4a5568"># Step 1 — download data</span><br>
        kaggle datasets download olistbr/brazilian-ecommerce<br><br>
        <span style="color:#4a5568"># Step 2 — run ETL</span><br>
        jupyter nbconvert --to notebook --execute notebooks/01_etl_pipeline.ipynb<br><br>
        <span style="color:#4a5568"># or run the script directly</span><br>
        python -m src.etl
      </div>
    </div>
    """, unsafe_allow_html=True)


def show_empty_filter_warning(total: int):
    st.markdown(f"""
    <div style="
      padding: 1.5rem 2rem;
      background: #141720;
      border: 1px dashed #ff6b35;
      border-radius: 10px;
      display:flex;
      align-items:center;
      gap:1rem;
    ">
      <span style="font-size:1.5rem;">⚠️</span>
      <div>
        <p style="margin:0;font-family:'Syne',sans-serif;font-weight:700;color:#e2e8f0;">
          No rows match your filters
        </p>
        <p style="margin:0;font-family:'DM Sans',sans-serif;font-size:0.85rem;color:#8892a4;">
          {total:,} total rows available — try widening your date range, states, or categories.
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── KPI helpers ────────────────────────────────────────────────────────────────
def fmt_revenue(v: float) -> str:
    """Auto-scale R$ values: K / M / B so they never clip."""
    if v >= 1_000_000_000:
        return f"R$ {v/1_000_000_000:,.2f}B"
    if v >= 1_000_000:
        return f"R$ {v/1_000_000:,.2f}M"
    if v >= 1_000:
        return f"R$ {v/1_000:,.1f}K"
    return f"R$ {v:,.2f}"
def safe_pct_delta(a, b) -> float | None:
    """Percentage change from b → a."""
    try:
        if b == 0 or pd.isna(b):
            return None
        return round((a - b) / abs(b) * 100, 1)
    except Exception:
        return None


def kpi_row(filtered: pd.DataFrame, full: pd.DataFrame):
    """Five KPI cards with deltas vs. full dataset baseline."""
    rev_f = filtered["revenue"].sum()
    rev_a = full["revenue"].sum()
    ord_f = filtered["order_id"].nunique()
    ord_a = full["order_id"].nunique()
    cust_f = filtered["customer_unique_id"].nunique() if "customer_unique_id" in filtered.columns else 0
    cust_a = full["customer_unique_id"].nunique() if "customer_unique_id" in full.columns else 0
    rev_sc = filtered["review_score"].mean()
    del_d  = filtered["delivery_days"].mean()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💰 Revenue",
              fmt_revenue(rev_f),
              delta=f"{safe_pct_delta(rev_f, rev_a):+.1f}% vs all" if safe_pct_delta(rev_f, rev_a) else None)
    c2.metric("📦 Orders",
              f"{ord_f:,}",
              delta=f"{safe_pct_delta(ord_f, ord_a):+.1f}% vs all" if safe_pct_delta(ord_f, ord_a) else None)
    c3.metric("👥 Customers",
              f"{cust_f:,}",
              delta=f"{safe_pct_delta(cust_f, cust_a):+.1f}% vs all" if safe_pct_delta(cust_f, cust_a) else None)
    c4.metric("⭐ Avg Review",
              f"{rev_sc:.2f}" if pd.notna(rev_sc) else "—")
    c5.metric("🚚 Avg Delivery",
              f"{del_d:.1f}d" if pd.notna(del_d) else "—")


# ── Main ───────────────────────────────────────────────────────────────────────
# Brand header
st.markdown("""
<div class="brand-strip">
    <span class="brand-name">Olist Intelligence</span>
</div>
""", unsafe_allow_html=True)

df_full = load_master()

if df_full.empty:
    show_no_data_error()
    st.stop()

# Sidebar
st.sidebar.markdown("""
<div style="padding:0.5rem 0 1rem">
  <p style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.1rem;
     color:#e2e8f0;margin:0;">Filters</p>
  <p style="font-family:'DM Mono',monospace;font-size:0.65rem;color:#4a5568;
     text-transform:uppercase;letter-spacing:0.1em;margin:0;">All pages</p>
</div>
""", unsafe_allow_html=True)

filtered = apply_filters(df_full)

# Persist for all pages
st.session_state["filtered_df"] = filtered
st.session_state["full_df"] = df_full

if filtered.empty:
    show_empty_filter_warning(len(df_full))
    st.stop()

# KPIs
st.markdown('<p class="section-label">Key Performance Indicators</p>', unsafe_allow_html=True)
kpi_row(filtered, df_full)

st.divider()

# Navigation cards
st.markdown("### 📑 Dashboard Pages")
cols = st.columns(4)
pages = [
    ("📊", "Overview", "Revenue trend · Payments · Day-of-week patterns"),
    ("📦", "Products", "Top categories · Freight · Price vs quality"),
    ("👥", "Customers", "RFM segmentation · Champions vs At-Risk"),
    ("🗺️", "Geo Map", "State revenue · Delivery performance · Pareto"),
]
for col, (icon, name, desc) in zip(cols, pages):
    col.markdown(f"""
    <div style="
      background:#141720;border:1px solid #1e2330;border-radius:10px;
      padding:1.2rem;height:100%;position:relative;overflow:hidden;
    ">
      <div style="font-size:1.6rem;margin-bottom:0.5rem;">{icon}</div>
      <p style="font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;
         color:#e2e8f0;margin:0 0 0.3rem;">{name}</p>
      <p style="font-family:'DM Sans',sans-serif;font-size:0.8rem;
         color:#8892a4;margin:0;">{desc}</p>
      <div style="position:absolute;bottom:0;left:0;right:0;height:2px;
         background:linear-gradient(90deg,#00e5a0,transparent);"></div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<p style="font-family:'DM Mono',monospace;font-size:0.72rem;color:#4a5568;
   margin-top:1rem;">
  ← Use the sidebar to navigate pages. Filters apply globally.
</p>
""", unsafe_allow_html=True)