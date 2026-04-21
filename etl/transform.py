"""
ETL Step 2 - Transform
Cleans raw DataFrames, engineers features, and prepares dimension/fact tables.
"""

import pandas as pd
import numpy as np
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TRANSFORM] %(message)s")
logger = logging.getLogger(__name__)

STAGING_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "staging")
os.makedirs(STAGING_DIR, exist_ok=True)


# ─── Customers ────────────────────────────────────────────────────────────────

def transform_customers(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardise customer records."""
    logger.info("Transforming customers...")

    df = df.copy()

    # Normalise text columns
    for col in ["first_name", "last_name", "city", "state", "country", "segment"]:
        df[col] = df[col].str.strip().str.title()

    # Lowercase email
    df["email"] = df["email"].str.strip().str.lower()

    # Parse date
    df["signup_date"] = pd.to_datetime(df["signup_date"], errors="coerce")

    # Drop rows with missing critical fields
    before = len(df)
    df.dropna(subset=["customer_id", "email"], inplace=True)
    logger.info(f"Dropped {before - len(df)} rows with missing customer_id/email")

    # Remove duplicates
    df.drop_duplicates(subset=["customer_id"], keep="first", inplace=True)

    logger.info(f"Customers after transform: {len(df)}")
    return df


# ─── Deals ────────────────────────────────────────────────────────────────────

def transform_deals(df: pd.DataFrame) -> pd.DataFrame:
    """Clean deal records."""
    logger.info("Transforming deals...")
    df = df.copy()

    df["deal_name"] = df["deal_name"].str.strip()
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["end_date"]   = pd.to_datetime(df["end_date"],   errors="coerce")
    df["discount_percent"] = pd.to_numeric(df["discount_percent"], errors="coerce").fillna(0)
    df["min_purchase"]     = pd.to_numeric(df["min_purchase"],     errors="coerce").fillna(0)

    df.drop_duplicates(subset=["deal_id"], keep="first", inplace=True)
    logger.info(f"Deals after transform: {len(df)}")
    return df


# ─── Transactions ─────────────────────────────────────────────────────────────

def transform_transactions(df: pd.DataFrame, customers: pd.DataFrame, deals: pd.DataFrame) -> pd.DataFrame:
    """Clean transactions and engineer derived financial columns."""
    logger.info("Transforming transactions...")
    df = df.copy()

    # Parse & validate types
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["quantity"]   = pd.to_numeric(df["quantity"],   errors="coerce").fillna(1).astype(int)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0)
    df["discount"]   = pd.to_numeric(df["discount"],   errors="coerce").fillna(0)
    df["return_flag"] = df["return_flag"].fillna(0).astype(int).astype(bool)

    # Drop rows with missing critical fields
    before = len(df)
    df.dropna(subset=["transaction_id", "customer_id", "transaction_date"], inplace=True)
    logger.info(f"Dropped {before - len(df)} transaction rows with missing keys")

    # Filter to valid customers only
    valid_customers = set(customers["customer_id"])
    df = df[df["customer_id"].isin(valid_customers)]

    # Keep only valid deal_ids (or leave as NaN)
    if "deal_id" in df.columns:
        valid_deals = set(deals["deal_id"])
        df["deal_id"] = df["deal_id"].where(df["deal_id"].isin(valid_deals), other=np.nan)

    # Compute derived financial columns
    df["gross_amount"]    = (df["quantity"] * df["unit_price"]).round(2)
    df["discount_amount"] = (df["gross_amount"] * df["discount"]).round(2)
    df["net_amount"]      = (df["gross_amount"] - df["discount_amount"]).round(2)

    # Exclude returns from revenue (keep record but net_amount → 0)
    df.loc[df["return_flag"], "net_amount"] = 0.0

    df.drop_duplicates(subset=["transaction_id"], keep="first", inplace=True)
    logger.info(f"Transactions after transform: {len(df)}")
    return df


# ─── Date Dimension ───────────────────────────────────────────────────────────

def build_date_dimension(transactions: pd.DataFrame) -> pd.DataFrame:
    """Generate a date dimension from all transaction dates."""
    logger.info("Building date dimension...")

    dates = transactions["transaction_date"].dropna().dt.date.unique()
    date_range = pd.date_range(
        start=pd.Timestamp(min(dates)),
        end=pd.Timestamp(max(dates)),
        freq="D"
    )

    dim_dates = pd.DataFrame({"full_date": date_range})
    dim_dates["day"]        = dim_dates["full_date"].dt.day
    dim_dates["month"]      = dim_dates["full_date"].dt.month
    dim_dates["month_name"] = dim_dates["full_date"].dt.strftime("%B")
    dim_dates["quarter"]    = dim_dates["full_date"].dt.quarter
    dim_dates["year"]       = dim_dates["full_date"].dt.year
    dim_dates["day_of_week"] = dim_dates["full_date"].dt.dayofweek
    dim_dates["day_name"]   = dim_dates["full_date"].dt.strftime("%A")
    dim_dates["is_weekend"] = dim_dates["day_of_week"].isin([5, 6])

    logger.info(f"Date dimension: {len(dim_dates)} rows")
    return dim_dates


# ─── Products Dimension ───────────────────────────────────────────────────────

def build_product_dimension(transactions: pd.DataFrame) -> pd.DataFrame:
    """Derive product dimension from transaction data."""
    logger.info("Building product dimension...")
    products = (
        transactions[["product_id", "product_name", "category", "unit_price"]]
        .drop_duplicates(subset=["product_id"])
        .reset_index(drop=True)
    )
    logger.info(f"Products: {len(products)} rows")
    return products


# ─── Save to staging ─────────────────────────────────────────────────────────

def save_staging(data: dict):
    """Persist transformed DataFrames as CSVs in the staging layer."""
    for name, df in data.items():
        path = os.path.join(STAGING_DIR, f"{name}.csv")
        df.to_csv(path, index=False)
        logger.info(f"Saved staging/{name}.csv ({len(df)} rows)")


# ─── Main entry ───────────────────────────────────────────────────────────────

def transform_all(raw: dict) -> dict:
    """Run full transformation pipeline and return staging DataFrames."""
    customers    = transform_customers(raw["customers"])
    deals        = transform_deals(raw["deals"])
    transactions = transform_transactions(raw["transactions"], customers, deals)
    dim_dates    = build_date_dimension(transactions)
    dim_products = build_product_dimension(transactions)

    staging = {
        "customers":    customers,
        "deals":        deals,
        "transactions": transactions,
        "dim_dates":    dim_dates,
        "dim_products": dim_products,
    }

    save_staging(staging)
    return staging


if __name__ == "__main__":
    from extract import extract_all
    raw     = extract_all()
    staging = transform_all(raw)
    for name, df in staging.items():
        print(f"\n--- {name.upper()} ({len(df)} rows) ---")
        print(df.head(2))
