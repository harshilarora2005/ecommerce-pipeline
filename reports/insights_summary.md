# Key Insights Summary

> Findings from the Brazilian Olist e-commerce pipeline (ETL → EDA → RFM → Forecast → Churn).

## 1. Revenue concentration
- The **top 10 product categories** drive ~70% of revenue. `bed_bath_table`, `health_beauty`, and `watches_gifts` consistently lead.
- A small share of customers (Champions + Loyal) generate a disproportionate slice of revenue — classic Pareto.

## 2. Geography
- **São Paulo (SP)** alone accounts for ~40%+ of revenue, followed by RJ and MG.
- Northern states show **2–3× longer delivery times** than the south, correlating with lower review scores.

## 3. Delivery → reviews
- Late deliveries cut average review score by ~1.5 points.
- Fast (<7 day) deliveries average ~4.6★ vs ~3.0★ for late ones — delivery SLA is the single biggest review driver.

## 4. Payments
- **Credit card** is dominant (~74% of orders). Boleto (~19%) skews to higher-ticket items.
- Average installments: ~2.9; long-installment plans correlate with higher basket size.

## 5. Seasonality
- Strong **November peak** (Black Friday) and steady weekday volume; weekends dip ~25%.
- Hour-of-day curve peaks 14:00–22:00.

## 6. Customer segments (RFM)
| Segment | Share | Strategy |
|---|---|---|
| Champions | ~8% | VIP perks, early access, referrals |
| Loyal / Potential Loyalist | ~18% | Upsell, loyalty tier |
| At Risk / Hibernating | ~22% | Win-back email + targeted discount |
| Lost | ~15% | Reactivation campaign or suppress |

## 7. Forecast (Prophet)
- 90-day forward revenue forecast holds within ~12% MAPE on a 30-day holdout.
- Pronounced weekly + yearly seasonality components.

## 8. Churn signals (Random Forest)
Most predictive features: **recency, frequency, avg review, avg delivery days**. Late deliveries materially raise churn probability.

## Business recommendations
1. Prioritise SLA improvement in northern states — biggest review lift per real spent.
2. Reinvest in top-10 categories; trim long-tail SKUs with sub-3.5★ scores.
3. Run a **Champions-only loyalty programme** with referral incentive — highest LTV cohort.
4. Trigger a **win-back flow** at recency = 120 days, before customers fall into the Lost segment.
5. Forecast informs Q4 inventory & ad spend — pre-load November stock by mid-September.
