"""
ML - Churn Prediction Inference
Loads the trained model and scaler to produce churn predictions
for individual customers or bulk from the database.
"""

import os
import pickle
import logging
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [PREDICT] %(message)s")
logger = logging.getLogger(__name__)

ML_DIR     = os.path.dirname(__file__)
MODEL_PATH  = os.path.join(ML_DIR, "churn_model.pkl")
SCALER_PATH = os.path.join(ML_DIR, "scaler.pkl")
FEATURES    = ["recency", "frequency", "monetary", "deal_count"]


def load_model():
    """Load the trained RandomForest model and scaler."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run ml/train_model.py first."
        )
    with open(MODEL_PATH, "rb")  as f: model  = pickle.load(f)
    with open(SCALER_PATH, "rb") as f: scaler = pickle.load(f)
    return model, scaler


def predict_single(recency: float, frequency: float, monetary: float,
                   deal_count: float = 0) -> dict:
    """
    Predict churn for a single customer.

    Returns:
        dict with churn_probability, churn_label, risk_category
    """
    model, scaler = load_model()

    X = np.array([[recency, frequency, monetary, deal_count]])
    X_scaled = scaler.transform(X)

    prob  = float(model.predict_proba(X_scaled)[0][1])
    label = int(model.predict(X_scaled)[0])

    if prob >= 0.7:
        risk = "High"
    elif prob >= 0.4:
        risk = "Medium"
    else:
        risk = "Low"

    return {
        "churn_probability": round(prob, 4),
        "churn_label":       label,
        "risk_category":     risk,
        "churn_pct":         round(prob * 100, 1),
    }


def predict_bulk() -> pd.DataFrame:
    """
    Run predictions for all customers and save to churn_predictions table.
    """
    model, scaler = load_model()

    db_url = (
        f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
        f"{os.getenv('DB_PASSWORD', 'password')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'shoppulse')}"
    )
    engine = get_engine = create_engine(db_url)

    query = """
        SELECT
            dc.customer_id,
            COALESCE(MAX(dd.full_date), CURRENT_DATE - 365) AS last_purchase,
            COALESCE(COUNT(ft.transaction_key), 0)          AS frequency,
            COALESCE(SUM(ft.net_amount), 0)                 AS monetary,
            COALESCE(COUNT(DISTINCT ft.deal_key), 0)        AS deal_count
        FROM dim_customers dc
        LEFT JOIN fact_transactions ft ON dc.customer_key = ft.customer_key AND ft.return_flag = FALSE
        LEFT JOIN dim_dates dd         ON ft.date_key = dd.date_key
        GROUP BY dc.customer_id
    """

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    if df.empty:
        logger.warning("No customers found for bulk prediction")
        return df

    ref_date = pd.Timestamp.today()
    df["last_purchase"] = pd.to_datetime(df["last_purchase"])
    df["recency"]  = (ref_date - df["last_purchase"]).dt.days.clip(lower=0)

    X        = df[FEATURES].fillna(0)
    X_scaled = scaler.transform(X)

    probs  = model.predict_proba(X_scaled)[:, 1]
    labels = model.predict(X_scaled)

    df["churn_probability"] = probs.round(4)
    df["churn_label"]       = labels
    df["risk_category"] = pd.cut(
        df["churn_probability"],
        bins=[-0.01, 0.4, 0.7, 1.01],
        labels=["Low", "Medium", "High"]
    )

    # Persist to DB
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE churn_predictions"))
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT INTO churn_predictions
                    (customer_id, recency, frequency, monetary,
                     churn_probability, churn_label, risk_category)
                VALUES
                    (:customer_id, :recency, :frequency, :monetary,
                     :churn_probability, :churn_label, :risk_category)
            """), {
                "customer_id":       row["customer_id"],
                "recency":           float(row["recency"]),
                "frequency":         float(row["frequency"]),
                "monetary":          float(row["monetary"]),
                "churn_probability": float(row["churn_probability"]),
                "churn_label":       int(row["churn_label"]),
                "risk_category":     str(row["risk_category"]),
            })
        conn.commit()

    logger.info(f"Bulk predictions saved: {len(df)} customers | "
                f"High risk: {(df['risk_category']=='High').sum()}")
    return df


if __name__ == "__main__":
    # Quick single prediction test
    result = predict_single(recency=120, frequency=2, monetary=150.0, deal_count=1)
    print("Single prediction:", result)
