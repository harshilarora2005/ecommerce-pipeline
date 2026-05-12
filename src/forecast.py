"""Sales forecasting helpers (Prophet + simple fallback)."""
from __future__ import annotations
import pandas as pd


def daily_revenue(df: pd.DataFrame, ts_col: str = "order_purchase_timestamp",
                value_col: str = "revenue") -> pd.DataFrame:
    s = (
        df.dropna(subset=[ts_col])
        .set_index(ts_col)
        .resample("D")[value_col].sum()
        .reset_index()
    )
    s.columns = ["ds", "y"]
    return s


def fit_prophet(daily: pd.DataFrame, periods: int = 90):
    """Fit Prophet and return (model, forecast). Caller imports prophet lazily."""
    from prophet import Prophet
    m = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
    m.fit(daily)
    future = m.make_future_dataframe(periods=periods)
    forecast = m.predict(future)
    return m, forecast


def evaluate_holdout(daily: pd.DataFrame, holdout_days: int = 30) -> dict:
    from prophet import Prophet
    train = daily.iloc[:-holdout_days]
    test = daily.iloc[-holdout_days:]
    m = Prophet(yearly_seasonality=True, weekly_seasonality=True)
    m.fit(train)
    future = m.make_future_dataframe(periods=holdout_days)
    fc = m.predict(future).set_index("ds").loc[test["ds"].values]
    err = (fc["yhat"].values - test["y"].values)
    mae = float(abs(err).mean())
    rmse = float((err ** 2).mean() ** 0.5)
    mape = float((abs(err) / test["y"].replace(0, 1).values).mean() * 100)
    return {"MAE": mae, "RMSE": rmse, "MAPE": mape}
