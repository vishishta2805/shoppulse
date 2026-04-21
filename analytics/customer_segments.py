"""
Customer Segmentation
Labels customers into segments using RFM scores and writes
results to the customer_segments table.
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [SEGMENTS] %(message)s")
logger = logging.getLogger(__name__)


def get_engine():
    db_url = (
        f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
        f"{os.getenv('DB_PASSWORD', 'password')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'shoppulse')}"
    )
    return create_engine(db_url)


def assign_segment_label(row) -> str:
    """Map RFM scores to human-readable segment labels."""
    score = row["rfm_score"]
    r     = row["r_score"]
    f     = row["f_score"]

    if score >= 13:
        return "Champions"
    elif score >= 10:
        return "Loyal Customers"
    elif r >= 4 and f <= 2:
        return "Promising"
    elif r >= 3 and f >= 3:
        return "Potential Loyalists"
    elif r == 2:
        return "At Risk"
    elif r == 1 and f >= 3:
        return "Cannot Lose Them"
    elif r == 1:
        return "Lost"
    else:
        return "Needs Attention"


def assign_churn_risk(row) -> str:
    """Classify churn risk based on recency and RFM score."""
    recency = row["recency_days"]
    score   = row["rfm_score"]

    if recency > 120 or score <= 5:
        return "High"
    elif recency > 60 or score <= 9:
        return "Medium"
    else:
        return "Low"


def compute_segments(rfm_df: pd.DataFrame) -> pd.DataFrame:
    """Add segment label and churn risk to RFM DataFrame."""
    df = rfm_df.copy()
    df["segment_label"] = df.apply(assign_segment_label, axis=1)
    df["churn_risk"]    = df.apply(assign_churn_risk, axis=1)
    logger.info(f"Segments computed:\n{df['segment_label'].value_counts().to_string()}")
    return df


def save_segments(df: pd.DataFrame):
    """Persist segments into the customer_segments table."""
    engine = get_engine()
    with engine.connect() as conn:
        # Clear previous computation
        conn.execute(text("TRUNCATE TABLE customer_segments"))
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT INTO customer_segments
                    (customer_id, recency_days, frequency, monetary,
                     rfm_score, segment_label, churn_risk)
                VALUES
                    (:customer_id, :recency_days, :frequency, :monetary,
                     :rfm_score, :segment_label, :churn_risk)
            """), {
                "customer_id":   row["customer_id"],
                "recency_days":  int(row["recency_days"]),
                "frequency":     int(row["frequency"]),
                "monetary":      float(row["monetary"]),
                "rfm_score":     float(row["rfm_score"]),
                "segment_label": row["segment_label"],
                "churn_risk":    row["churn_risk"],
            })
        conn.commit()
    logger.info(f"Saved {len(df)} segment rows")


if __name__ == "__main__":
    from rfm_features import compute_rfm
    rfm  = compute_rfm()
    segs = compute_segments(rfm)
    save_segments(segs)
    print(segs[["customer_id", "segment_label", "churn_risk", "rfm_score"]])
