# AWS migration

Ports this pipeline from local pandas + SQLite to an S3 → Glue → Redshift
Serverless architecture, so it reflects an actual cloud data platform rather
than a script on one laptop.

## Pipeline

```
S3 (raw CSVs) → Glue (Python Shell, reuses etl.py logic) → S3 (Parquet, partitioned by month)
                                                                    │
                                                                    ▼
                                                      Redshift Serverless (star schema)
                                                                    │
                                                                    ▼
                                                              QuickSight
```

Athena can also query the Parquet in S3 directly via the Glue Data Catalog,
without touching Redshift — useful for ad-hoc exploration.

## Setup order

1. **`s3_upload.py`** — pushes the 8 raw Olist CSVs to `s3://<bucket>/raw/<table>/`.
2. **`glue_etl.py`** — same clean/join/enrich logic as `src/etl.py`, but reads
   from S3 and writes partitioned Parquet to `s3://<bucket>/processed/`.
   Run it as a Glue Python Shell job, or locally against S3 to test first:
   ```
   python aws/glue_etl.py --bucket your-bucket-name
   ```
3. **`redshift_schema.sql`** — creates the star schema (`fact_order_items` +
   `dim_customer`/`dim_seller`/`dim_product`/`dim_date`) in Redshift
   Serverless. Run once in the Redshift query editor.
4. **`redshift_load.sql`** — `COPY`s the Glue output from S3 into the star
   schema. Replace `<BUCKET>` and `<IAM_ROLE_ARN>` with your values before
   running (the Redshift Serverless namespace needs an IAM role with
   `s3:GetObject` on the bucket).

## Why a star schema instead of the flat `master` table

The original `master` table is a single wide join — fine for a Streamlit app
querying with pandas, but it repeats customer/seller/product attributes on
every row. `fact_order_items` + dimensions is closer to what BI tooling
(QuickSight, Redshift) and BIE-style SQL (window functions, cohort joins)
actually expect, and it's the schema shape that comes up in interviews.

## Free tier / cost notes

- **Glue**: free tier covers a monthly quota of DPU-hours for Python Shell
  jobs — this dataset (100K+ rows, ~8 small CSVs) runs well within it. Don't
  leave a Glue *dev endpoint* running; those aren't part of the free tier
  and bill hourly.
- **Redshift Serverless**: bills per RPU-second while a query runs, not for
  idle time — much safer for a portfolio project than a provisioned cluster.
  Still, set a usage limit (Redshift console → Serverless → Limits) as a
  backstop.
- **S3 / Athena**: effectively free at this data size.
- Set a billing alarm (Billing → Budgets) before running any of this if you
  haven't already — see the setup steps from earlier in this conversation.

## Local testing without touching Glue/Redshift proper

`glue_etl.py` and `s3_upload.py` are plain boto3 scripts — you can run both
from your laptop with `aws configure` credentials, no need to actually
create a Glue job to validate the S3 read/write logic. Only wire up an
actual Glue job once the local run against S3 works end to end.
