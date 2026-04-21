"""
RFM Feature Engineering
Computes Recency, Frequency, and Monetary values per customer
from the fact_transactions table.
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [RFM] %(message)s")
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


def compute_rfm(reference_date: str = None) -> pd.DataFrame:
    """
    Compute RFM metrics for all customers.

    Args:
        reference_date: ISO date string for recency calc (defaults to today).

    Returns:
        DataFrame with columns: customer_id, recency_days, frequency, monetary
    """
    engine = get_engine()

    query = """
        SELECT
            dc.customer_id,
            dc.first_name || ' ' || dc.last_name AS customer_name,
            dc.segment,
            MAX(dd.full_date)                    AS last_purchase_date,
            COUNT(ft.transaction_key)            AS frequency,
            SUM(ft.net_amount)                   AS monetary
        FROM fact_transactions ft
        JOIN dim_customers dc ON ft.customer_key = dc.customer_key
        JOIN dim_dates     dd ON ft.date_key      = dd.date_key
        WHERE ft.return_flag = FALSE
        GROUP BY dc.customer_id, dc.first_name, dc.last_name, dc.segment
    """

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    if df.empty:
        logger.warning("No transaction data found for RFM computation")
        return df

    # Recency in days
    ref = pd.Timestamp(reference_date) if reference_date else pd.Timestamp.today()
    df["last_purchase_date"] = pd.to_datetime(df["last_purchase_date"])
    df["recency_days"] = (ref - df["last_purchase_date"]).dt.days

    # RFM scores (1-5 quintiles, higher = better)
    df["r_score"] = pd.qcut(df["recency_days"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    df["f_score"] = pd.qcut(df["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    df["m_score"] = pd.qcut(df["monetary"].rank(method="first"),  5, labels=[1, 2, 3, 4, 5]).astype(int)
    df["rfm_score"] = df["r_score"] + df["f_score"] + df["m_score"]

    logger.info(f"RFM computed for {len(df)} customers")
    return df[["customer_id", "customer_name", "segment",
               "last_purchase_date", "recency_days", "frequency",
               "monetary", "r_score", "f_score", "m_score", "rfm_score"]]


if __name__ == "__main__":
    rfm = compute_rfm()
    print(rfm.to_string(index=False))
