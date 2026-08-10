-- ---------------------------------------------------------------------------
-- Load Glue's Parquet output (S3) into the Redshift star schema.
--
-- Prereqs:
--   1. aws/redshift_schema.sql already run.
--   2. aws/glue_etl.py already run, so s3://<bucket>/processed/... exists.
--   3. An IAM role attached to your Redshift Serverless namespace with
--      s3:GetObject on the bucket. Replace <IAM_ROLE_ARN> and <BUCKET> below.
--
-- Run top to bottom in the Redshift query editor (or via psql/redshift-data API).
-- ---------------------------------------------------------------------------

-- 1. Dimensions load directly from their own Parquet files -------------------

CREATE TEMP TABLE staging_customers (
    customer_id             VARCHAR(64),
    customer_unique_id      VARCHAR(64),
    customer_zip_code_prefix VARCHAR(16),
    customer_city           VARCHAR(128),
    customer_state          VARCHAR(8)
);

COPY staging_customers
FROM 's3://<BUCKET>/processed/customers/'
IAM_ROLE '<IAM_ROLE_ARN>'
FORMAT AS PARQUET;

INSERT INTO olist.dim_customer (customer_id, customer_unique_id, customer_city, customer_state, customer_zip_prefix)
SELECT DISTINCT customer_id, customer_unique_id, customer_city, customer_state, customer_zip_code_prefix
FROM staging_customers
WHERE customer_id NOT IN (SELECT customer_id FROM olist.dim_customer);


CREATE TEMP TABLE staging_sellers (
    seller_id             VARCHAR(64),
    seller_zip_code_prefix VARCHAR(16),
    seller_city           VARCHAR(128),
    seller_state          VARCHAR(8)
);

COPY staging_sellers
FROM 's3://<BUCKET>/processed/sellers/'
IAM_ROLE '<IAM_ROLE_ARN>'
FORMAT AS PARQUET;

INSERT INTO olist.dim_seller (seller_id, seller_city, seller_state, seller_zip_prefix)
SELECT DISTINCT seller_id, seller_city, seller_state, seller_zip_code_prefix
FROM staging_sellers
WHERE seller_id NOT IN (SELECT seller_id FROM olist.dim_seller);


CREATE TEMP TABLE staging_products (
    product_id                  VARCHAR(64),
    product_category_name       VARCHAR(128),
    product_name_length         INT,
    product_description_length  INT,
    product_photos_qty          INT,
    product_weight_g             REAL,
    product_length_cm            REAL,
    product_height_cm            REAL,
    product_width_cm             REAL
);

COPY staging_products
FROM 's3://<BUCKET>/processed/products/'
IAM_ROLE '<IAM_ROLE_ARN>'
FORMAT AS PARQUET;

INSERT INTO olist.dim_product
SELECT DISTINCT *
FROM staging_products
WHERE product_id NOT IN (SELECT product_id FROM olist.dim_product);


-- 2. dim_date — generate one row per calendar day covering the dataset range -

INSERT INTO olist.dim_date (date_key, full_date, year, month, day, day_name, month_name, year_month)
SELECT
    CAST(TO_CHAR(d, 'YYYYMMDD') AS INT)   AS date_key,
    d                                      AS full_date,
    EXTRACT(YEAR  FROM d)::SMALLINT        AS year,
    EXTRACT(MONTH FROM d)::SMALLINT        AS month,
    EXTRACT(DAY   FROM d)::SMALLINT        AS day,
    TO_CHAR(d, 'Day')                      AS day_name,
    TO_CHAR(d, 'Month')                    AS month_name,
    TO_CHAR(d, 'YYYY-MM')                  AS year_month
FROM (
    SELECT ('2016-09-01'::date + n) AS d
    FROM (SELECT ROW_NUMBER() OVER () - 1 AS n FROM olist.dim_customer LIMIT 1000) t
    -- 1000-day span comfortably covers the Olist dataset (Sep 2016 - Oct 2018);
    -- swap for a real Redshift date-spine generator if you extend the range.
) days
WHERE d <= '2018-12-31'
ON CONFLICT (date_key) DO NOTHING;


-- 3. Fact table — load the partitioned master Parquet, then map into the star schema

CREATE TEMP TABLE staging_master (
    order_id                VARCHAR(64),
    order_item_id           SMALLINT,
    product_id              VARCHAR(64),
    seller_id               VARCHAR(64),
    price                    REAL,
    freight_value            REAL,
    customer_id              VARCHAR(64),
    order_purchase_timestamp TIMESTAMP,
    delivery_days            SMALLINT,
    delivery_delay_days      SMALLINT,
    is_late                  BOOLEAN,
    payment_value            REAL,
    payment_installments     SMALLINT,
    payment_type             VARCHAR(32),
    review_score             REAL,
    review_sentiment         VARCHAR(16),
    revenue                  REAL,
    profit_margin            REAL,
    item_count               SMALLINT,
    order_size               VARCHAR(16)
);

COPY staging_master
FROM 's3://<BUCKET>/processed/master/'
IAM_ROLE '<IAM_ROLE_ARN>'
FORMAT AS PARQUET;

INSERT INTO olist.fact_order_items (
    order_id, order_item_id, product_id, seller_id, customer_id, order_date_key,
    price, freight_value, revenue, profit_margin,
    payment_value, payment_installments, payment_type,
    review_score, review_sentiment,
    item_count, order_size, delivery_days, delivery_delay_days, is_late
)
SELECT
    m.order_id, m.order_item_id, m.product_id, m.seller_id, m.customer_id,
    CAST(TO_CHAR(m.order_purchase_timestamp, 'YYYYMMDD') AS INT) AS order_date_key,
    m.price, m.freight_value, m.revenue, m.profit_margin,
    m.payment_value, m.payment_installments, m.payment_type,
    m.review_score, m.review_sentiment,
    m.item_count, m.order_size, m.delivery_days, m.delivery_delay_days, m.is_late
FROM staging_master m;


-- 4. Sanity check --------------------------------------------------------

SELECT
    (SELECT COUNT(*) FROM olist.fact_order_items) AS fact_rows,
    (SELECT COUNT(*) FROM olist.dim_customer)     AS customers,
    (SELECT COUNT(*) FROM olist.dim_product)      AS products,
    (SELECT COUNT(*) FROM olist.dim_seller)       AS sellers;
