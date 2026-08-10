"""
AWS Glue Python Shell job.

Same transform logic as src/etl.py (load -> clean -> join -> enrich),
but source/sink are S3 instead of local disk, and output is Parquet
instead of CSV/SQLite so Athena and Redshift COPY can read it directly.

Glue job setup (console or CLI):
    - Job type: Python Shell
    - Python version: 3.9
    - Script location: s3://<bucket>/scripts/glue_etl.py  (upload this file)
    - Job parameters:
        --bucket        your-bucket-name
        --additional-python-modules  pandas==2.2.0,pyarrow==15.0.0,s3fs==2024.2.0

Run manually to test:
    python aws/glue_etl.py --bucket your-bucket-name

Output layout:
    s3://<bucket>/processed/master/order_month=2017-01/part.parquet
    s3://<bucket>/processed/master/order_month=2017-02/part.parquet
    ...
    s3://<bucket>/processed/orders_clean/orders_clean.parquet
"""
from __future__ import annotations
import argparse
import io
import sys
import boto3
import pandas as pd

DATE_COLS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

RAW_KEYS = {
    "orders":       "raw/orders/olist_orders_dataset.csv",
    "order_items":  "raw/order_items/olist_order_items_dataset.csv",
    "customers":    "raw/customers/olist_customers_dataset.csv",
    "sellers":      "raw/sellers/olist_sellers_dataset.csv",
    "order_payments": "raw/order_payments/olist_order_payments_dataset.csv",
    "products":     "raw/products/olist_products_dataset.csv",
    "order_reviews": "raw/order_reviews/olist_order_reviews_dataset.csv",
    "category_translation": "raw/category_translation/product_category_name_translation.csv",
}


# ---------------------------------------------------------------------------
# S3 I/O
# ---------------------------------------------------------------------------

def read_csv_from_s3(s3, bucket: str, key: str) -> pd.DataFrame:
    obj = s3.get_object(Bucket=bucket, Key=key)
    return pd.read_csv(io.BytesIO(obj["Body"].read()))


def write_parquet_to_s3(s3, df: pd.DataFrame, bucket: str, key: str) -> None:
    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow")
    buf.seek(0)
    s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())


def load_raw(s3, bucket: str, name: str) -> pd.DataFrame:
    key = RAW_KEYS[name]
    return read_csv_from_s3(s3, bucket, key)


# ---------------------------------------------------------------------------
# Transform logic — unchanged from src/etl.py
# ---------------------------------------------------------------------------

def clean_orders(orders: pd.DataFrame) -> pd.DataFrame:
    for col in DATE_COLS:
        if col in orders.columns:
            orders[col] = pd.to_datetime(orders[col], errors="coerce")

    orders["delivery_days"] = (
        orders["order_delivered_customer_date"] - orders["order_purchase_timestamp"]
    ).dt.days

    orders["delivery_delay_days"] = (
        orders["order_delivered_customer_date"] - orders["order_estimated_delivery_date"]
    ).dt.days

    orders["is_late"]     = orders["delivery_delay_days"] > 0
    orders["order_month"] = orders["order_purchase_timestamp"].dt.to_period("M").astype(str)
    orders["order_dow"]   = orders["order_purchase_timestamp"].dt.day_name()
    return orders


def clean_products(products: pd.DataFrame) -> pd.DataFrame:
    products = products.rename(columns={
        "product_name_lenght":        "product_name_length",
        "product_description_lenght": "product_description_length",
    })
    products["product_category_name"] = products["product_category_name"].fillna("Unknown")
    return products


def aggregate_payments(payments: pd.DataFrame) -> pd.DataFrame:
    return payments.groupby("order_id").agg(
        payment_value        =("payment_value",        "sum"),
        payment_installments =("payment_installments", "max"),
        payment_type         =("payment_type", lambda s: s.mode().iat[0] if len(s.mode()) else None),
        n_payments           =("payment_sequential",   "max"),
    ).reset_index()


def aggregate_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    return reviews.groupby("order_id").agg(
        review_score=("review_score", "mean")
    ).reset_index()


def _classify_order_size(n: int) -> str:
    if n == 1:      return "Small"
    elif n <= 3:    return "Medium"
    else:           return "Large"


def _classify_sentiment(score: float) -> str | float:
    if pd.isna(score):  return pd.NA  # type: ignore
    elif score >= 4:    return "positive"
    elif score == 3:    return "neutral"
    else:               return "negative"


def enrich_master(df: pd.DataFrame) -> pd.DataFrame:
    df["revenue"] = df["price"].fillna(0) + df["freight_value"].fillna(0)

    safe_price = df["price"].replace(0, pd.NA)
    df["profit_margin"] = ((df["price"] - df["freight_value"]) / safe_price) * 100

    item_counts = df.groupby("order_id").size().reset_index(name="item_count")
    df = df.merge(item_counts, on="order_id", how="left")
    df["order_size"] = df["item_count"].apply(_classify_order_size)

    df["review_sentiment"] = df["review_score"].apply(_classify_sentiment)
    return df


def build_master(
    orders, items, customers, sellers, payments, products, reviews,
    category_translation=None,
) -> pd.DataFrame:
    pay = aggregate_payments(payments)
    rev = aggregate_reviews(reviews)

    df = (
        items
        .merge(orders,    on="order_id",   how="left")
        .merge(customers, on="customer_id", how="left")
        .merge(sellers,   on="seller_id",  how="left")
        .merge(pay,       on="order_id",   how="left")
        .merge(products,  on="product_id", how="left")
        .merge(rev,       on="order_id",   how="left")
    )

    if category_translation is not None:
        df = df.merge(category_translation, on="product_category_name", how="left")
        df["product_category_name"] = (
            df["product_category_name_english"].fillna(df["product_category_name"])
        )
        df.drop(columns=["product_category_name_english"], inplace=True, errors="ignore")

    return enrich_master(df)


# ---------------------------------------------------------------------------
# Glue entrypoint
# ---------------------------------------------------------------------------

def run_pipeline(bucket: str) -> None:
    s3 = boto3.client("s3")

    print("loading raw tables from S3...")
    orders    = clean_orders(load_raw(s3, bucket, "orders"))
    items     = load_raw(s3, bucket, "order_items")
    customers = load_raw(s3, bucket, "customers")
    sellers   = load_raw(s3, bucket, "sellers")
    payments  = load_raw(s3, bucket, "order_payments")
    products  = clean_products(load_raw(s3, bucket, "products"))
    reviews   = load_raw(s3, bucket, "order_reviews")

    try:
        translation = load_raw(s3, bucket, "category_translation")
    except Exception:
        translation = None

    print("building master table...")
    master = build_master(orders, items, customers, sellers, payments, products, reviews, translation)

    print(f"writing processed output to s3://{bucket}/processed/ ...")
    # partition master by order_month so Athena/Redshift can prune scans
    for month, part in master.groupby("order_month"):
        key = f"processed/master/order_month={month}/part.parquet"
        write_parquet_to_s3(s3, part, bucket, key)

    write_parquet_to_s3(s3, orders, bucket, "processed/orders_clean/orders_clean.parquet")
    write_parquet_to_s3(s3, customers, bucket, "processed/customers/customers.parquet")
    write_parquet_to_s3(s3, sellers, bucket, "processed/sellers/sellers.parquet")
    write_parquet_to_s3(s3, products, bucket, "processed/products/products.parquet")

    print("done. wrote", master["order_month"].nunique(), "month partitions.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bucket", required=True)
    args, _unknown = ap.parse_known_args()  # Glue injects extra --job-* args
    run_pipeline(args.bucket)
