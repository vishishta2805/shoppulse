"""
Churn Label Generator
Creates binary churn labels from RFM data for ML model training.
Customers with recency > 90 days are labelled as churned (1).
"""

import pandas as pd
import numpy as np
import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [CHURN_LABELS] %(message)s")
logger = logging.getLogger(__name__)

CHURN_THRESHOLD_DAYS = 90   # days since last purchase → churned
ANALYTICS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "analytics")
os.makedirs(ANALYTICS_DIR, exist_ok=True)


def get_engine():
    db_url = (
        f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
        f"{os.getenv('DB_PASSWORD', 'password')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'shoppulse')}"
    )
    return create_engine(db_url)


def generate_churn_labels() -> pd.DataFrame:
    """
    Build a labelled dataset of [recency, frequency, monetary, churn_label].
    Saves to data/analytics/churn_training_data.csv.
    """
    engine = get_engine()

    query = """
        SELECT
            dc.customer_id,
            MAX(dd.full_date)             AS last_purchase_date,
            COUNT(ft.transaction_key)     AS frequency,
            SUM(ft.net_amount)            AS monetary,
            COUNT(DISTINCT ft.deal_key)   AS deal_count
        FROM fact_transactions ft
        JOIN dim_customers dc ON ft.customer_key = dc.customer_key
        JOIN dim_dates     dd ON ft.date_key      = dd.date_key
        WHERE ft.return_flag = FALSE
        GROUP BY dc.customer_id
    """

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    if df.empty:
        logger.warning("No data available for churn labelling")
        return df

    ref_date = pd.Timestamp.today()
    df["last_purchase_date"] = pd.to_datetime(df["last_purchase_date"])
    df["recency"]   = (ref_date - df["last_purchase_date"]).dt.days
    df["frequency"] = df["frequency"].astype(int)
    df["monetary"]  = df["monetary"].round(2)

    # Binary churn label: 1 = churned, 0 = retained
    df["churn_label"] = (df["recency"] > CHURN_THRESHOLD_DAYS).astype(int)

    logger.info(f"Total: {len(df)} | Churned: {df['churn_label'].sum()} "
                f"| Retained: {(df['churn_label'] == 0).sum()}")

    # Save training dataset
    out_path = os.path.join(ANALYTICS_DIR, "churn_training_data.csv")
    df.to_csv(out_path, index=False)
    logger.info(f"Saved training data → {out_path}")

    return df[["customer_id", "recency", "frequency", "monetary", "deal_count", "churn_label"]]


if __name__ == "__main__":
    df = generate_churn_labels()
    print(df)
