-- ---------------------------------------------------------------------------
-- Athena: external tables over Glue's Parquet output.
--
-- Replaces redshift_load.sql's staging tables — Athena queries the Parquet
-- in S3 directly, no COPY / no cluster / no idle cost. Genuinely within
-- AWS Free Tier (you pay a few cents per TB scanned, and this dataset is
-- nowhere near that).
--
-- Run in the Athena query editor. Replace <BUCKET> with your bucket name.
-- Uses the Glue Data Catalog as its metastore, so these tables are also
-- visible to Glue crawlers / other Glue jobs automatically.
-- ---------------------------------------------------------------------------

CREATE DATABASE IF NOT EXISTS olist;

-- master: partitioned by order_month, same partitioning glue_etl.py wrote
CREATE EXTERNAL TABLE IF NOT EXISTS olist.master_raw (
    order_id                    string,
    order_item_id               smallint,
    product_id                  string,
    seller_id                   string,
    price                       double,
    freight_value               double,
    customer_id                 string,
    order_purchase_timestamp    timestamp,
    delivery_days               int,
    delivery_delay_days         int,
    is_late                     boolean,
    payment_value               double,
    payment_installments        int,
    payment_type                string,
    review_score                double,
    review_sentiment            string,
    revenue                     double,
    profit_margin               double,
    item_count                  int,
    order_size                  string
)
PARTITIONED BY (order_month string)
STORED AS PARQUET
LOCATION 's3://<BUCKET>/processed/master/'
TBLPROPERTIES ('parquet.compression'='SNAPPY');

-- discovers the order_month=2017-01/ style partitions Glue wrote
MSCK REPAIR TABLE olist.master_raw;


CREATE EXTERNAL TABLE IF NOT EXISTS olist.customers_raw (
    customer_id               string,
    customer_unique_id        string,
    customer_zip_code_prefix  string,
    customer_city             string,
    customer_state            string
)
STORED AS PARQUET
LOCATION 's3://<BUCKET>/processed/customers/';

CREATE EXTERNAL TABLE IF NOT EXISTS olist.sellers_raw (
    seller_id                string,
    seller_zip_code_prefix   string,
    seller_city              string,
    seller_state             string
)
STORED AS PARQUET
LOCATION 's3://<BUCKET>/processed/sellers/';

CREATE EXTERNAL TABLE IF NOT EXISTS olist.products_raw (
    product_id                    string,
    product_category_name         string,
    product_name_length           int,
    product_description_length    int,
    product_photos_qty            int,
    product_weight_g               double,
    product_length_cm              double,
    product_height_cm              double,
    product_width_cm               double
)
STORED AS PARQUET
LOCATION 's3://<BUCKET>/processed/products/';

-- sanity check
SELECT COUNT(*) AS master_rows FROM olist.master_raw;
