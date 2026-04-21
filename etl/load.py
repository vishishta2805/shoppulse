"""
ETL Step 3 - Load
Inserts transformed DataFrames into PostgreSQL using SQLAlchemy.
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import logging
import os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [LOAD] %(message)s")
logger = logging.getLogger(__name__)


def get_engine():
    """Create SQLAlchemy engine from environment variables."""
    db_url = (
        f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
        f"{os.getenv('DB_PASSWORD', 'password')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'shoppulse')}"
    )
    return create_engine(db_url)


def load_dim_customers(df: pd.DataFrame, engine):
    """Upsert customers into dim_customers."""
    logger.info("Loading dim_customers...")
    rows = []
    for _, row in df.iterrows():
        rows.append({
            "customer_id": row["customer_id"],
            "first_name":  row.get("first_name"),
            "last_name":   row.get("last_name"),
            "email":       row.get("email"),
            "phone":       row.get("phone"),
            "city":        row.get("city"),
            "state":       row.get("state"),
            "country":     row.get("country"),
            "segment":     row.get("segment"),
            "signup_date": row.get("signup_date"),
        })

    with engine.connect() as conn:
        for r in rows:
            conn.execute(text("""
                INSERT INTO dim_customers
                    (customer_id, first_name, last_name, email, phone,
                     city, state, country, segment, signup_date)
                VALUES
                    (:customer_id, :first_name, :last_name, :email, :phone,
                     :city, :state, :country, :segment, :signup_date)
                ON CONFLICT (customer_id) DO UPDATE SET
                    first_name  = EXCLUDED.first_name,
                    last_name   = EXCLUDED.last_name,
                    email       = EXCLUDED.email,
                    segment     = EXCLUDED.segment
            """), r)
        conn.commit()
    logger.info(f"Loaded {len(rows)} customers")


def load_dim_deals(df: pd.DataFrame, engine):
    """Upsert deals into dim_deals."""
    logger.info("Loading dim_deals...")
    with engine.connect() as conn:
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT INTO dim_deals
                    (deal_id, deal_name, discount_percent, start_date,
                     end_date, category, min_purchase)
                VALUES
                    (:deal_id, :deal_name, :discount_percent, :start_date,
                     :end_date, :category, :min_purchase)
                ON CONFLICT (deal_id) DO UPDATE SET
                    deal_name        = EXCLUDED.deal_name,
                    discount_percent = EXCLUDED.discount_percent
            """), {
                "deal_id":          row["deal_id"],
                "deal_name":        row["deal_name"],
                "discount_percent": float(row["discount_percent"]),
                "start_date":       row["start_date"],
                "end_date":         row["end_date"],
                "category":         row["category"],
                "min_purchase":     float(row["min_purchase"]),
            })
        conn.commit()
    logger.info(f"Loaded {len(df)} deals")


def load_dim_products(df: pd.DataFrame, engine):
    """Upsert products into dim_products."""
    logger.info("Loading dim_products...")
    with engine.connect() as conn:
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT INTO dim_products (product_id, product_name, category, unit_price)
                VALUES (:product_id, :product_name, :category, :unit_price)
                ON CONFLICT (product_id) DO UPDATE SET
                    product_name = EXCLUDED.product_name,
                    category     = EXCLUDED.category,
                    unit_price   = EXCLUDED.unit_price
            """), {
                "product_id":   row["product_id"],
                "product_name": row["product_name"],
                "category":     row["category"],
                "unit_price":   float(row["unit_price"]),
            })
        conn.commit()
    logger.info(f"Loaded {len(df)} products")


def load_dim_dates(df: pd.DataFrame, engine):
    """Insert date dimension rows (skip existing)."""
    logger.info("Loading dim_dates...")
    with engine.connect() as conn:
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT INTO dim_dates
                    (full_date, day, month, month_name, quarter,
                     year, day_of_week, day_name, is_weekend)
                VALUES
                    (:full_date, :day, :month, :month_name, :quarter,
                     :year, :day_of_week, :day_name, :is_weekend)
                ON CONFLICT (full_date) DO NOTHING
            """), {
                "full_date":    row["full_date"].date() if hasattr(row["full_date"], "date") else row["full_date"],
                "day":          int(row["day"]),
                "month":        int(row["month"]),
                "month_name":   row["month_name"],
                "quarter":      int(row["quarter"]),
                "year":         int(row["year"]),
                "day_of_week":  int(row["day_of_week"]),
                "day_name":     row["day_name"],
                "is_weekend":   bool(row["is_weekend"]),
            })
        conn.commit()
    logger.info(f"Loaded {len(df)} date rows")


def load_fact_transactions(df: pd.DataFrame, engine):
    """Insert transactions into fact_transactions, resolving dimension keys."""
    logger.info("Loading fact_transactions...")

    with engine.connect() as conn:
        # Fetch dimension key maps
        cust_map = {r[0]: r[1] for r in conn.execute(
            text("SELECT customer_id, customer_key FROM dim_customers")).fetchall()}
        prod_map = {r[0]: r[1] for r in conn.execute(
            text("SELECT product_id, product_key FROM dim_products")).fetchall()}
        date_map = {str(r[0]): r[1] for r in conn.execute(
            text("SELECT full_date, date_key FROM dim_dates")).fetchall()}
        deal_map = {r[0]: r[1] for r in conn.execute(
            text("SELECT deal_id, deal_key FROM dim_deals")).fetchall()}

        loaded = 0
        for _, row in df.iterrows():
            cust_key = cust_map.get(row["customer_id"])
            prod_key = prod_map.get(row.get("product_id"))
            date_str = str(row["transaction_date"].date()) if pd.notna(row["transaction_date"]) else None
            date_key = date_map.get(date_str)
            deal_id  = row.get("deal_id")
            deal_key = deal_map.get(deal_id) if pd.notna(deal_id) and deal_id else None

            if not all([cust_key, prod_key, date_key]):
                continue  # skip unmappable rows

            conn.execute(text("""
                INSERT INTO fact_transactions
                    (transaction_id, customer_key, product_key, date_key, deal_key,
                     quantity, unit_price, discount, gross_amount, discount_amount,
                     net_amount, return_flag)
                VALUES
                    (:transaction_id, :customer_key, :product_key, :date_key, :deal_key,
                     :quantity, :unit_price, :discount, :gross_amount, :discount_amount,
                     :net_amount, :return_flag)
                ON CONFLICT (transaction_id) DO NOTHING
            """), {
                "transaction_id":  row["transaction_id"],
                "customer_key":    cust_key,
                "product_key":     prod_key,
                "date_key":        date_key,
                "deal_key":        deal_key,
                "quantity":        int(row["quantity"]),
                "unit_price":      float(row["unit_price"]),
                "discount":        float(row["discount"]),
                "gross_amount":    float(row["gross_amount"]),
                "discount_amount": float(row["discount_amount"]),
                "net_amount":      float(row["net_amount"]),
                "return_flag":     bool(row["return_flag"]),
            })
            loaded += 1

        conn.commit()
    logger.info(f"Loaded {loaded} transaction rows")


def load_all(staging: dict):
    """Run full load pipeline."""
    engine = get_engine()
    load_dim_deals(staging["deals"], engine)
    load_dim_customers(staging["customers"], engine)
    load_dim_products(staging["dim_products"], engine)
    load_dim_dates(staging["dim_dates"], engine)
    load_fact_transactions(staging["transactions"], engine)
    logger.info("ETL Load complete.")


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from etl.extract import extract_all
    from etl.transform import transform_all
    raw     = extract_all()
    staging = transform_all(raw)
    load_all(staging)
