"""
ETL Step 1 - Extract
Reads raw CSV files from data/raw/ and returns DataFrames.
"""

import pandas as pd
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [EXTRACT] %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")


def extract_customers() -> pd.DataFrame:
    """Extract raw customer data from CSV."""
    path = os.path.join(RAW_DIR, "customers.csv")
    logger.info(f"Extracting customers from {path}")
    df = pd.read_csv(path)
    logger.info(f"Extracted {len(df)} customer records")
    return df


def extract_transactions() -> pd.DataFrame:
    """Extract raw transaction data from CSV."""
    path = os.path.join(RAW_DIR, "transactions.csv")
    logger.info(f"Extracting transactions from {path}")
    df = pd.read_csv(path)
    logger.info(f"Extracted {len(df)} transaction records")
    return df


def extract_deals() -> pd.DataFrame:
    """Extract deal/promotion data from CSV."""
    path = os.path.join(RAW_DIR, "deals.csv")
    logger.info(f"Extracting deals from {path}")
    df = pd.read_csv(path)
    logger.info(f"Extracted {len(df)} deal records")
    return df


def extract_all() -> dict:
    """Run all extractions and return a dictionary of DataFrames."""
    return {
        "customers":    extract_customers(),
        "transactions": extract_transactions(),
        "deals":        extract_deals(),
    }


if __name__ == "__main__":
    data = extract_all()
    for name, df in data.items():
        print(f"\n--- {name.upper()} ---")
        print(df.head(3))
