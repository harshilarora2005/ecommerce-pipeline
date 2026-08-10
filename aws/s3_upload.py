"""
One-off script to push the raw Olist CSVs into S3 under a partitioned
prefix, so Glue and Athena can find them.

Usage:
    python aws/s3_upload.py --bucket your-bucket-name --local data/raw

Bucket layout it creates:
    s3://<bucket>/raw/orders/olist_orders_dataset.csv
    s3://<bucket>/raw/order_items/olist_order_items_dataset.csv
    ...
    s3://<bucket>/processed/master/   <- Glue writes Parquet here later
"""
from __future__ import annotations
import argparse
from pathlib import Path
import boto3

RAW_FILES = {
    "orders":       "olist_orders_dataset.csv",
    "order_items":  "olist_order_items_dataset.csv",
    "customers":    "olist_customers_dataset.csv",
    "sellers":      "olist_sellers_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "products":     "olist_products_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bucket", required=True, help="Target S3 bucket name")
    ap.add_argument("--local", default="data/raw", help="Local raw CSV folder")
    ap.add_argument("--profile", default=None, help="AWS CLI profile name (optional)")
    args = ap.parse_args()

    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    s3 = session.client("s3")

    local_dir = Path(args.local)
    for short_name, filename in RAW_FILES.items():
        src = local_dir / filename
        if not src.exists():
            print(f"skip (not found): {src}")
            continue
        key = f"raw/{short_name}/{filename}"
        print(f"uploading {src} -> s3://{args.bucket}/{key}")
        s3.upload_file(str(src), args.bucket, key)

    print("done")


if __name__ == "__main__":
    main()
