from __future__ import annotations
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "ecommerce.db"

DATE_COLS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def load_raw(name: str) -> pd.DataFrame:
    """Load a raw Olist CSV by short name (e.g. 'orders', 'order_items')."""
    path = RAW_DIR / f"olist_{name}_dataset.csv"
    if not path.exists():
        alt = RAW_DIR / f"{name}.csv"
        if alt.exists():
            path = alt
        else:
            raise FileNotFoundError(f"Missing raw file: {path}")
    return pd.read_csv(path)


def clean_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Parse dates and derive delivery / lateness columns."""
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
    """Fix Olist's two misspelled column names and fill missing categories."""
    products = products.rename(columns={
        "product_name_lenght":        "product_name_length",       # typo fix
        "product_description_lenght": "product_description_length", # typo fix
    })
    products["product_category_name"] = products["product_category_name"].fillna("Unknown")
    return products


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------

def aggregate_payments(payments: pd.DataFrame) -> pd.DataFrame:
    """One row per order: total payment value and dominant method."""
    return payments.groupby("order_id").agg(
        payment_value        =("payment_value",        "sum"),
        payment_installments =("payment_installments", "max"),
        payment_type         =("payment_type", lambda s: s.mode().iat[0] if len(s.mode()) else None),
        n_payments           =("payment_sequential",   "max"),
    ).reset_index()


def aggregate_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    """One row per order: mean review score."""
    return reviews.groupby("order_id").agg(
        review_score=("review_score", "mean")
    ).reset_index()



def _classify_order_size(n: int) -> str:
    if n == 1:      return "Small"
    elif n <= 3:    return "Medium"
    else:           return "Large"


def _classify_sentiment(score: float) -> str | float:
    if pd.isna(score):  return pd.NA # type: ignore
    elif score >= 4:    return "positive"
    elif score == 3:    return "neutral"
    else:               return "negative"


def enrich_master(df: pd.DataFrame) -> pd.DataFrame:
    """Add all project-plan derived columns to the master table."""
    # revenue
    df["revenue"] = df["price"].fillna(0) + df["freight_value"].fillna(0)

    # profit_margin — guard divide-by-zero when price == 0
    safe_price = df["price"].replace(0, pd.NA)
    df["profit_margin"] = ((df["price"] - df["freight_value"]) / safe_price) * 100

    # item_count + order_size bucket
    item_counts = df.groupby("order_id").size().reset_index(name="item_count")
    df = df.merge(item_counts, on="order_id", how="left")
    df["order_size"] = df["item_count"].apply(_classify_order_size)

    # review_sentiment
    df["review_sentiment"] = df["review_score"].apply(_classify_sentiment)

    return df


# ---------------------------------------------------------------------------
# Master join
# ---------------------------------------------------------------------------

def build_master(
    orders: pd.DataFrame,
    items: pd.DataFrame,
    customers: pd.DataFrame,
    sellers: pd.DataFrame,
    payments: pd.DataFrame,
    products: pd.DataFrame,
    reviews: pd.DataFrame,
    category_translation: pd.DataFrame | None = None,
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

    df = enrich_master(df)
    return df


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def to_sqlite(df: pd.DataFrame, table: str, engine) -> None:
    df.to_sql(table, engine, if_exists="replace", index=False)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def run_pipeline() -> pd.DataFrame:
    """Full pipeline: load → clean → join → enrich → persist."""
    # Load
    orders   = clean_orders(load_raw("orders"))
    items    = load_raw("order_items")
    customers= load_raw("customers")
    sellers  = load_raw("sellers")        # NEW
    payments = load_raw("order_payments")
    products = clean_products(load_raw("products"))
    reviews  = load_raw("order_reviews")

    try:
        translation = load_raw("product_category_name_translation")
    except FileNotFoundError:
        translation = None

    # Build master
    master = build_master(orders, items, customers, sellers, payments, products, reviews, translation)

    # Save processed CSVs
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    master.to_csv(PROCESSED_DIR / "master.csv", index=False)
    orders.to_csv(PROCESSED_DIR / "orders_clean.csv", index=False)
    log.info("Saved master.csv and orders_clean.csv")

    # Write ALL tables to SQLite (was only 3 before)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH}")

    tables = {
        "master":    master,
        "orders":    orders,
        "customers": customers,
        "sellers":   sellers,   # NEW
        "products":  products,
        "payments":  payments,  # NEW (raw)
        "reviews":   reviews,   # NEW
    }
    for table_name, df in tables.items():
        to_sqlite(df, table_name, engine)

    return master


if __name__ == "__main__":
    run_pipeline()
