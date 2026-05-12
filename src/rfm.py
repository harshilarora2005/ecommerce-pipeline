"""RFM (Recency, Frequency, Monetary) segmentation."""
from __future__ import annotations

import pandas as pd


SEGMENT_ORDER = [
    "Champions", "Loyal", "Potential Loyalist", "New / Recent",
    "Promising", "Needs Attention", "At Risk", "Hibernating", "Lost",
]


def compute_rfm(
    df: pd.DataFrame,
    customer_col: str = "customer_unique_id",
    ts_col: str = "order_purchase_timestamp",
    order_col: str = "order_id",
    value_col: str = "payment_value",
) -> pd.DataFrame:
    """Compute Recency (days), Frequency (orders), Monetary (sum) + 1-5 scores."""
    df = df.dropna(subset=[ts_col, customer_col]).copy()
    df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
    snapshot = df[ts_col].max() + pd.Timedelta(days=1)

    rfm = df.groupby(customer_col).agg(
        Recency=(ts_col, lambda x: (snapshot - x.max()).days),
        Frequency=(order_col, "nunique"),
        Monetary=(value_col, "sum"),
    ).reset_index()

    rfm["R"] = pd.qcut(rfm["Recency"], 5, labels=[5, 4, 3, 2, 1], duplicates="drop").astype(int)
    rfm["F"] = pd.qcut(
        rfm["Frequency"].rank(method="first"), 5,
        labels=[1, 2, 3, 4, 5], duplicates="drop",
    ).astype(int)
    rfm["M"] = pd.qcut(rfm["Monetary"], 5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)
    rfm["RFM_Score"] = rfm["R"].astype(str) + rfm["F"].astype(str) + rfm["M"].astype(str)
    rfm["RFM_Sum"] = rfm["R"] + rfm["F"] + rfm["M"]
    rfm["Segment"] = rfm.apply(lambda r: label_segment(r["R"], r["F"]), axis=1)
    return rfm


def label_segment(r: int, f: int) -> str:
    if r >= 4 and f >= 4:
        return "Champions"
    if r >= 4 and f >= 3:
        return "Loyal"
    if r >= 4 and f >= 2:
        return "Potential Loyalist"
    if r >= 4:
        return "New / Recent"
    if r >= 3 and f >= 3:
        return "Promising"
    if r >= 3:
        return "Needs Attention"
    if r >= 2 and f >= 2:
        return "At Risk"
    if r >= 2:
        return "Hibernating"
    return "Lost"


def segment_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    agg = rfm.groupby("Segment").agg(
        customers=("Recency", "size"),
        avg_recency=("Recency", "mean"),
        avg_frequency=("Frequency", "mean"),
        avg_monetary=("Monetary", "mean"),
        total_revenue=("Monetary", "sum"),
    ).reset_index()
    agg["Segment"] = pd.Categorical(agg["Segment"], categories=SEGMENT_ORDER, ordered=True)
    return agg.sort_values("Segment").reset_index(drop=True)
