"""
ETL Pipeline Runner
Executes the full Extract → Transform → Load pipeline.
Run with: python etl/run.py
"""

import sys
import os
import logging
import time

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from etl.extract   import extract_all
from etl.transform import transform_all
from etl.load      import load_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PIPELINE] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("etl_run.log"),
    ]
)
logger = logging.getLogger(__name__)


def run_pipeline():
    start = time.time()
    logger.info("=" * 50)
    logger.info("ShopPulse ETL Pipeline starting...")
    logger.info("=" * 50)

    try:
        # Step 1: Extract
        logger.info("STEP 1/3 - Extracting raw data...")
        raw = extract_all()

        # Step 2: Transform
        logger.info("STEP 2/3 - Transforming data...")
        staging = transform_all(raw)

        # Step 3: Load
        logger.info("STEP 3/3 - Loading into PostgreSQL...")
        load_all(staging)

        elapsed = round(time.time() - start, 2)
        logger.info(f"Pipeline completed successfully in {elapsed}s")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
