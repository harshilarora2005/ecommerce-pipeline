
CREATE TABLE olist.dim_customer
WITH (
    format = 'PARQUET',
    write_compression = 'SNAPPY',
    external_location = 's3://harshil-olist-pipeline/star/dim_customer/'
) AS
SELECT DISTINCT
    customer_id,
    customer_unique_id,
    customer_city,
    customer_state,
    customer_zip_code_prefix AS customer_zip_prefix
FROM olist.customers_raw;


CREATE TABLE olist.dim_seller
WITH (
    format = 'PARQUET',
    write_compression = 'SNAPPY',
    external_location = 's3://harshil-olist-pipeline/star/dim_seller/'
) AS
SELECT DISTINCT
    seller_id,
    seller_city,
    seller_state,
    seller_zip_code_prefix AS seller_zip_prefix
FROM olist.sellers_raw;

CREATE TABLE olist.dim_product
WITH (
    format = 'PARQUET',
    write_compression = 'SNAPPY',
    external_location = 's3://harshil-olist-pipeline/star/dim_product/'
) AS
SELECT DISTINCT *
FROM olist.products_raw;


CREATE TABLE olist.dim_date
WITH (
    format = 'PARQUET',
    write_compression = 'SNAPPY',
    external_location = 's3://harshil-olist-pipeline/star/dim_date/'
) AS
SELECT
    CAST(date_format(d, '%Y%m%d') AS INT) AS date_key,
    d AS full_date,
    year(d) AS year,
    month(d) AS month,
    day(d) AS day,
    date_format(d, '%W') AS day_name,
    date_format(d, '%M') AS month_name,
    date_format(d, '%Y-%m') AS year_month
FROM UNNEST(
    sequence(
        date('2016-09-01'),
        date('2018-10-31'),
        interval '1' day
    )
) AS t(d);



CREATE TABLE olist.fact_order_items
WITH (
    format = 'PARQUET',
    write_compression = 'SNAPPY',
    external_location = 's3://harshil-olist-pipeline/star/fact_order_items/',
    partitioned_by = ARRAY['order_month']
) AS
SELECT
    order_id,
    order_item_id,
    product_id,
    seller_id,
    customer_id,

    CAST(
        date_format(
            order_purchase_timestamp,
            '%Y%m%d'
        ) AS INTEGER
    ) AS order_date_key,

    price,
    freight_value,
    revenue,
    profit_margin,
    payment_value,

    -- Parquet source is DOUBLE
    payment_installments,

    payment_type,
    review_score,
    review_sentiment,
    item_count,
    order_size,
    delivery_days,
    delivery_delay_days,
    is_late,

    -- Partition column must be last
    order_month

FROM olist.master_raw;

SELECT
    (SELECT COUNT(*) FROM olist.fact_order_items) AS fact_rows,
    (SELECT COUNT(*) FROM olist.dim_customer)     AS customers,
    (SELECT COUNT(*) FROM olist.dim_product)      AS products,
    (SELECT COUNT(*) FROM olist.dim_seller)       AS sellers;
