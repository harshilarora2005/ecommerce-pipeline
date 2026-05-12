# 🛒 E-Commerce Sales Intelligence Pipeline

End-to-end data analytics portfolio project — **ETL · EDA · RFM Segmentation · Forecasting · Churn · Streamlit Dashboard**.

Built on the [Brazilian Olist E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (100k+ orders across 9 relational tables).

## ✨ What's inside

| Layer | Tech | Output |
|---|---|---|
| ETL | pandas + SQLAlchemy + SQLite | Clean joined `master` table |
| EDA | plotly + seaborn | 6 business questions answered |
| Segmentation | RFM scoring | 9 actionable customer segments |
| Forecasting | Prophet | 90-day revenue forecast + holdout MAPE |
| Churn | scikit-learn RandomForest | Per-customer churn probability + ROC-AUC |
| Dashboard | Streamlit + Plotly | 4-page interactive app with filters |

## 🗂️ Folder structure

```
ecommerce-pipeline/
├── data/
│   ├── raw/              # Original CSVs from Kaggle
│   ├── processed/        # Cleaned outputs (master.csv, rfm_segments.csv, forecast_90d.csv)
│   └── ecommerce.db      # SQLite warehouse
├── notebooks/
│   ├── 01_etl_pipeline.ipynb
│   ├── 02_eda_analysis.ipynb
│   ├── 03_rfm_segmentation.ipynb
│   ├── 04_sales_forecast.ipynb
│   └── 05_churn_model.ipynb
├── src/
│   ├── etl.py            # Load · clean · join · persist
│   ├── eda_utils.py      # Plotly chart helpers
│   ├── rfm.py            # RFM scoring + segmentation rules
│   ├── forecast.py       # Prophet wrappers + holdout eval
│   ├── churn.py          # Feature engineering + RF model
│   └── sample_data.py    # Synthetic demo CSV generator
├── dashboard/
│   ├── app.py            # KPI home page with global filters
│   └── pages/
│       ├── overview.py   # Revenue, payments, weekday/hour patterns
│       ├── products.py   # Categories, freight, scatter
│       ├── customers.py  # RFM segments + top spenders
│       └── geo_map.py    # State leaderboard + Pareto
├── reports/
│   └── insights_summary.md
├── requirements.txt
├── README.md
└── .gitignore
```

## 🚀 Quickstart

```bash
# 1. Install
pip install -r requirements.txt

# 2A. Use real Olist data → drop the 7 Kaggle CSVs into data/raw/, then:
python -m src.etl

# 2B. ...or generate a synthetic demo dataset (no download needed):
python -m src.sample_data && python -m src.etl

# 3. Launch the dashboard
streamlit run dashboard/app.py

# 4. Explore the analysis notebooks
jupyter notebook notebooks/
```

## 📊 Key findings
See [`reports/insights_summary.md`](reports/insights_summary.md) for the full write-up.

Highlights:
- Top 10 categories drive ~70% of revenue (Pareto).
- SP alone = ~40% of revenue; northern states have 2–3× longer delivery and ~1.5★ lower reviews.
- Credit card dominates (~74%); boleto skews higher-ticket.
- Prophet 90-day forecast: ~12% MAPE on 30-day holdout.
- Churn model AUC ≈ 0.80; top drivers: recency, frequency, avg review, delivery days.

## 🛣️ Roadmap
- [x] ETL pipeline → SQLite
- [x] EDA notebook (6 business questions)
- [x] RFM segmentation (9 segments)
- [x] Streamlit multi-page dashboard with filters
- [x] Prophet forecasting + holdout eval
- [x] Churn classification model
- [ ] Deploy to Streamlit Community Cloud
- [ ] Add Folium choropleth (Brazil GeoJSON)
