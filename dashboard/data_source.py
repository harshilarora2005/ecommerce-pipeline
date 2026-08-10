from __future__ import annotations
import os
from pathlib import Path
from functools import lru_cache

import pandas as pd
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"

DATA_SOURCE = os.environ.get("DATA_SOURCE", "sqlite").lower()

ATHENA_MASTER_QUERY = """
SELECT
    f.order_id, f.order_item_id, f.product_id, f.seller_id, f.customer_id,
    f.price, f.freight_value, f.revenue, f.profit_margin,
    f.payment_value, f.payment_installments, f.payment_type,
    f.review_score, f.review_sentiment,
    f.item_count, f.order_size, f.delivery_days, f.delivery_delay_days, f.is_late,
    f.order_month,
    c.customer_unique_id, c.customer_city, c.customer_state, c.customer_zip_prefix,
    s.seller_city, s.seller_state, s.seller_zip_prefix,
    p.product_category_name, p.product_name_length, p.product_description_length,
    p.product_photos_qty, p.product_weight_g, p.product_length_cm,
    p.product_height_cm, p.product_width_cm
FROM olist.fact_order_items f
LEFT JOIN olist.dim_customer c ON f.customer_id = c.customer_id
LEFT JOIN olist.dim_seller   s ON f.seller_id   = s.seller_id
LEFT JOIN olist.dim_product  p ON f.product_id  = p.product_id
"""


@lru_cache(maxsize=1)
def load_master_df() -> pd.DataFrame:
    if DATA_SOURCE == "athena":
        df = _load_from_athena()
    else:
        df = _load_from_sqlite()

    if "order_purchase_timestamp" in df.columns:
        df["order_purchase_timestamp"] = pd.to_datetime(
            df["order_purchase_timestamp"], errors="coerce"
        )
    return df


def _load_from_sqlite() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    engine = create_engine(f"sqlite:///{DB_PATH}")
    return pd.read_sql("SELECT * FROM master", engine)


def _load_from_athena() -> pd.DataFrame:
    from pyathena import connect 

    staging_dir = os.environ.get("ATHENA_S3_STAGING_DIR")
    if not staging_dir:
        raise RuntimeError(
            "DATA_SOURCE=athena requires ATHENA_S3_STAGING_DIR to be set, "
            "e.g. s3://your-bucket-name/athena-results/ "
            "(same location used when setting up Athena)."
        )
    region = os.environ.get("ATHENA_REGION", "us-east-1")

    conn = connect(s3_staging_dir=staging_dir, region_name=region)
    return pd.read_sql(ATHENA_MASTER_QUERY, conn)
