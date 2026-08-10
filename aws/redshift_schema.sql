CREATE SCHEMA IF NOT EXISTS olist;

-- ---------------------------------------------------------------------------
-- Dimensions
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS olist.dim_customer (
    customer_id            VARCHAR(64)  PRIMARY KEY,
    customer_unique_id     VARCHAR(64),
    customer_city          VARCHAR(128),
    customer_state         VARCHAR(8),
    customer_zip_prefix    VARCHAR(16)
)
DISTSTYLE ALL;  -- small dim, replicate to every node for fast joins

CREATE TABLE IF NOT EXISTS olist.dim_seller (
    seller_id              VARCHAR(64)  PRIMARY KEY,
    seller_city            VARCHAR(128),
    seller_state           VARCHAR(8),
    seller_zip_prefix      VARCHAR(16)
)
DISTSTYLE ALL;

CREATE TABLE IF NOT EXISTS olist.dim_product (
    product_id                     VARCHAR(64) PRIMARY KEY,
    product_category_name          VARCHAR(128),
    product_name_length            INT,
    product_description_length     INT,
    product_photos_qty             INT,
    product_weight_g                REAL,
    product_length_cm               REAL,
    product_height_cm               REAL,
    product_width_cm                REAL
)
DISTSTYLE ALL;

CREATE TABLE IF NOT EXISTS olist.dim_date (
    date_key        INT         PRIMARY KEY,   -- YYYYMMDD
    full_date       DATE        NOT NULL,
    year             SMALLINT,
    month            SMALLINT,
    day              SMALLINT,
    day_name         VARCHAR(16),
    month_name       VARCHAR(16),
    year_month       VARCHAR(8)                 -- e.g. '2017-01', matches order_month
)
DISTSTYLE ALL;

-- ---------------------------------------------------------------------------
-- Fact
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS olist.fact_order_items (
    order_id                VARCHAR(64),
    order_item_id           SMALLINT,
    product_id              VARCHAR(64)  REFERENCES olist.dim_product(product_id),
    seller_id               VARCHAR(64)  REFERENCES olist.dim_seller(seller_id),
    customer_id              VARCHAR(64)  REFERENCES olist.dim_customer(customer_id),
    order_date_key            INT          REFERENCES olist.dim_date(date_key),

    price                    REAL,
    freight_value            REAL,
    revenue                  REAL,
    profit_margin            REAL,

    payment_value            REAL,
    payment_installments     SMALLINT,
    payment_type             VARCHAR(32),

    review_score             REAL,
    review_sentiment         VARCHAR(16),

    item_count               SMALLINT,
    order_size               VARCHAR(16),
    delivery_days            SMALLINT,
    delivery_delay_days      SMALLINT,
    is_late                  BOOLEAN,

    PRIMARY KEY (order_id, order_item_id)
)
DISTSTYLE KEY
DISTKEY (customer_id)      -- co-locate a customer's rows for cohort/retention queries
SORTKEY (order_date_key);  -- most BIE queries filter/aggregate by date range first
