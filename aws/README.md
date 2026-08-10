# AWS migration

Ports this pipeline from local pandas + SQLite to an S3 → Glue → Athena
architecture, so it reflects an actual cloud data platform rather than a
script on one laptop.

## Pipeline

```
S3 (raw CSVs) → Glue (Python Shell, reuses etl.py logic) → S3 (Parquet, partitioned by month)
                                                                    │
                                                                    ▼
                                                    Athena (external tables + CTAS star schema)
                                                                    │
                                                                    ▼
                                                              QuickSight
```

Athena was chosen over Redshift on purpose: Redshift (Serverless or
provisioned) isn't part of AWS's permanent Free Tier — its $300/90-day
trial credit currently requires being on AWS's Paid plan. Athena is
genuinely serverless and pay-per-query-scanned, so it stays within Free
Tier at this data size with no provisioning step at all.

## Setup order

1. **`s3_upload.py`** — pushes the 8 raw Olist CSVs to `s3://<bucket>/raw/<table>/`.
2. **`glue_etl.py`** — same clean/join/enrich logic as `src/etl.py`, but reads
   from S3 and writes partitioned Parquet to `s3://<bucket>/processed/`.
   Run it as a Glue Python Shell job, or locally against S3 to test first:
   ```
   python aws/glue_etl.py --bucket your-bucket-name
   ```
3. **`athena_external_tables.sql`** — registers `master_raw`, `customers_raw`,
   `sellers_raw`, `products_raw` as external tables over the Glue Parquet
   output, using the Glue Data Catalog as the metastore. Run once in the
   Athena query editor (replace `<BUCKET>` first).
4. **`athena_star_schema.sql`** — `CREATE TABLE AS SELECT` statements that
   materialize `fact_order_items` + `dim_customer`/`dim_seller`/`dim_product`/
   `dim_date` as their own Parquet files in S3, same shape as a Redshift star
   schema but with nothing to provision.

### Optional: Redshift instead of Athena

`redshift_schema.sql` and `redshift_load.sql` are still in this folder if you
later switch to AWS's Paid plan and want the $300 Redshift Serverless trial —
same star schema, loaded via `COPY` instead of CTAS. Not needed for the
default path above.

## Running the existing Streamlit dashboard against Athena

`dashboard/data_source.py` toggles between SQLite (default) and Athena via
an env var, so the existing app/pages don't need further changes:

```bash
pip install "pyathena[pandas]"

export DATA_SOURCE=athena
export ATHENA_S3_STAGING_DIR=s3://your-bucket-name/athena-results/
export ATHENA_REGION=your-region      # e.g. ap-south-1

streamlit run dashboard/app.py
```

Behind the scenes it queries `olist.fact_order_items` joined back to the
three dimension tables, reconstructing the same flat shape the pages already
expect — so `overview.py`, `customers.py`, `geo_map.py`, and `products.py`
work unmodified.

One known gap: the Athena star schema doesn't carry raw columns like
`order_status`, `order_delivered_carrier_date`, or `order_approved_at` (only
the derived `delivery_days`/`delivery_delay_days`/`is_late` made it into
`fact_order_items`). Pages that reference those columns defensively check
`if column in df.columns` first, so nothing crashes — the order-status filter
on the Overview page just won't appear in Athena mode. Add those columns to
`athena_star_schema.sql`'s fact table if you want full parity.

## Why a star schema instead of the flat `master` table

The original `master` table is a single wide join — fine for a Streamlit app
querying with pandas, but it repeats customer/seller/product attributes on
every row. `fact_order_items` + dimensions is closer to what BI tooling
(QuickSight, Athena, Redshift) and BIE-style SQL (window functions, cohort
joins) actually expect, and it's the schema shape that comes up in
interviews.

## Free tier / cost notes

- **Glue**: free tier covers a monthly quota of DPU-hours for Python Shell
  jobs — this dataset (100K+ rows, ~8 small CSVs) runs well within it. Don't
  leave a Glue *dev endpoint* running; those aren't part of the free tier
  and bill hourly.
- **Athena**: billed per TB scanned (a few cents at this data size), nothing
  to provision or leave running. Parquet + the `order_month` partitioning
  keeps scans small.
- **S3**: effectively free at this data size.
- **QuickSight**: has a 30-day free trial, then bills per user/month — it's
  not part of the permanent free tier. Fine to use during the trial for
  dashboard screenshots, just don't leave it subscribed afterward.
- Set a billing alarm (Billing → Budgets) before running any of this if you
  haven't already — see the setup steps from earlier in this conversation.

## Local testing without touching Glue/Redshift proper

`glue_etl.py` and `s3_upload.py` are plain boto3 scripts — you can run both
from your laptop with `aws configure` credentials, no need to actually
create a Glue job to validate the S3 read/write logic. Only wire up an
actual Glue job once the local run against S3 works end to end.
