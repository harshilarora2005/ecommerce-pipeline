"""Reusable plotting + analysis helpers for EDA notebooks and dashboard."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ---- Aggregations ---------------------------------------------------------

def revenue_by_category(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    return (
        df.groupby("product_category_name", dropna=True)["revenue"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index()
    )


def monthly_revenue(df: pd.DataFrame) -> pd.DataFrame:
    s = (
        df.dropna(subset=["order_purchase_timestamp"])
        .set_index("order_purchase_timestamp")
        .resample("MS")["revenue"]
        .sum()
        .reset_index()
    )
    s.columns = ["month", "revenue"]
    return s


def revenue_by_state(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("customer_state")["revenue"].sum()
        .sort_values(ascending=False)
        .reset_index()
    )


def review_score_distribution(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.dropna(subset=["review_score"])
        .groupby("review_score").size()
        .reset_index(name="count")
    )


def delivery_vs_review(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.dropna(subset=["delivery_days", "review_score"])
        .groupby("review_score")["delivery_days"].mean()
        .reset_index()
    )


def payment_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.drop_duplicates("order_id")
        .groupby("payment_type")
        .agg(orders=("order_id", "nunique"), revenue=("payment_value", "sum"))
        .reset_index()
    )


# ---- Charts ---------------------------------------------------------------

def chart_revenue_by_category(df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    data = revenue_by_category(df, top_n)
    fig = px.bar(
        data, x="revenue", y="product_category_name",
        orientation="h", title=f"Top {top_n} categories by revenue",
        color="revenue", color_continuous_scale="Tealgrn",
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=520)
    return fig


def chart_monthly_revenue(df: pd.DataFrame) -> go.Figure:
    data = monthly_revenue(df)
    fig = px.area(data, x="month", y="revenue", title="Monthly revenue trend")
    fig.update_traces(line_color="#10b981")
    fig.update_layout(height=380)
    return fig


def chart_state_revenue(df: pd.DataFrame) -> go.Figure:
    data = revenue_by_state(df)
    fig = px.bar(data, x="customer_state", y="revenue",
                 title="Revenue by customer state",
                 color="revenue", color_continuous_scale="Viridis")
    fig.update_layout(height=380)
    return fig


def chart_review_distribution(df: pd.DataFrame) -> go.Figure:
    data = review_score_distribution(df)
    fig = px.bar(data, x="review_score", y="count",
                 title="Review score distribution",
                 color="review_score", color_continuous_scale="RdYlGn")
    fig.update_layout(height=320)
    return fig


def chart_delivery_vs_review(df: pd.DataFrame) -> go.Figure:
    data = delivery_vs_review(df)
    fig = px.bar(data, x="review_score", y="delivery_days",
                 title="Avg delivery days by review score",
                 color="delivery_days", color_continuous_scale="RdYlGn_r")
    fig.update_layout(height=320)
    return fig


def chart_payment_breakdown(df: pd.DataFrame) -> go.Figure:
    data = payment_breakdown(df)
    fig = px.pie(data, names="payment_type", values="revenue",
                 title="Revenue share by payment type", hole=0.45)
    fig.update_layout(height=380)
    return fig
