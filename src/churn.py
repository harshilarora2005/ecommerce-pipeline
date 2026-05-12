"""Simple churn classification: predict if a customer will purchase again within N days."""
from __future__ import annotations

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score


def build_churn_features(df: pd.DataFrame, churn_window_days: int = 180) -> pd.DataFrame:
    df = df.dropna(subset=["order_purchase_timestamp", "customer_unique_id"]).copy()
    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"])
    snapshot = df["order_purchase_timestamp"].max()

    feats = df.groupby("customer_unique_id").agg(
        recency=("order_purchase_timestamp", lambda x: (snapshot - x.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("payment_value", "sum"),
        avg_review=("review_score", "mean"),
        avg_delivery_days=("delivery_days", "mean"),
        avg_freight=("freight_value", "mean"),
    ).reset_index()
    feats["churned"] = (feats["recency"] > churn_window_days).astype(int)
    return feats.fillna(0)


def train_churn_model(feats: pd.DataFrame):
    X = feats.drop(columns=["customer_unique_id", "churned"])
    y = feats["churned"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    clf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    clf.fit(X_tr, y_tr)
    proba = clf.predict_proba(X_te)[:, 1]
    pred = clf.predict(X_te)
    report = classification_report(y_te, pred, output_dict=True)
    auc = roc_auc_score(y_te, proba)
    importance = pd.Series(clf.feature_importances_, index=X.columns).sort_values(ascending=False)
    return clf, {"auc": auc, "report": report, "feature_importance": importance}
