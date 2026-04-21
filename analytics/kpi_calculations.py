"""
KPI Calculations
Computes core business metrics:
  - Total Revenue
  - Average Order Value (AOV)
  - Churn Rate
  - Retention Rate
  - Revenue by Month
  - Revenue by Category
  - Deal Usage Stats
"""

import pandas as pd
from sqlalchemy import create_engine, text
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [KPIs] %(message)s")
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


def compute_kpis() -> dict:
    """Return a dictionary of all core KPIs."""
    engine = get_engine()
    kpis   = {}

    with engine.connect() as conn:

        # ── Revenue & Orders ──────────────────────────────────────────────────
        row = conn.execute(text("""
            SELECT
                ROUND(SUM(net_amount)::NUMERIC, 2)              AS total_revenue,
                COUNT(transaction_key)                           AS total_orders,
                ROUND(AVG(net_amount)::NUMERIC, 2)              AS avg_order_value,
                ROUND(SUM(discount_amount)::NUMERIC, 2)         AS total_discounts,
                COUNT(CASE WHEN return_flag THEN 1 END)         AS total_returns
            FROM fact_transactions
        """)).fetchone()

        kpis["total_revenue"]   = float(row[0] or 0)
        kpis["total_orders"]    = int(row[1]   or 0)
        kpis["avg_order_value"] = float(row[2] or 0)
        kpis["total_discounts"] = float(row[3] or 0)
        kpis["total_returns"]   = int(row[4]   or 0)

        # ── Customer counts ───────────────────────────────────────────────────
        total_customers = conn.execute(
            text("SELECT COUNT(*) FROM dim_customers")).scalar()
        active_customers = conn.execute(text("""
            SELECT COUNT(DISTINCT customer_key) FROM fact_transactions
            WHERE return_flag = FALSE
        """)).scalar()

        kpis["total_customers"]  = int(total_customers)
        kpis["active_customers"] = int(active_customers)

        # ── Retention & Churn ─────────────────────────────────────────────────
        # A customer is "churned" if last purchase > 90 days ago
        churned = conn.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT dc.customer_key,
                       MAX(dd.full_date) AS last_purchase
                FROM fact_transactions ft
                JOIN dim_customers dc ON ft.customer_key = dc.customer_key
                JOIN dim_dates     dd ON ft.date_key      = dd.date_key
                WHERE ft.return_flag = FALSE
                GROUP BY dc.customer_key
                HAVING MAX(dd.full_date) < CURRENT_DATE - INTERVAL '90 days'
            ) sub
        """)).scalar()

        kpis["churned_customers"] = int(churned or 0)
        if kpis["active_customers"] > 0:
            kpis["churn_rate"]     = round(kpis["churned_customers"] / kpis["active_customers"] * 100, 2)
            kpis["retention_rate"] = round(100 - kpis["churn_rate"], 2)
        else:
            kpis["churn_rate"]     = 0
            kpis["retention_rate"] = 0

        # ── Revenue by month ─────────────────────────────────────────────────
        monthly = conn.execute(text("""
            SELECT
                dd.year,
                dd.month,
                dd.month_name,
                ROUND(SUM(ft.net_amount)::NUMERIC, 2) AS revenue
            FROM fact_transactions ft
            JOIN dim_dates dd ON ft.date_key = dd.date_key
            WHERE ft.return_flag = FALSE
            GROUP BY dd.year, dd.month, dd.month_name
            ORDER BY dd.year, dd.month
        """)).fetchall()
        kpis["revenue_by_month"] = [
            {"year": r[0], "month": r[1], "month_name": r[2], "revenue": float(r[3])}
            for r in monthly
        ]

        # ── Revenue by category ───────────────────────────────────────────────
        by_cat = conn.execute(text("""
            SELECT
                dp.category,
                ROUND(SUM(ft.net_amount)::NUMERIC, 2) AS revenue,
                COUNT(ft.transaction_key)             AS orders
            FROM fact_transactions ft
            JOIN dim_products dp ON ft.product_key = dp.product_key
            WHERE ft.return_flag = FALSE
            GROUP BY dp.category
            ORDER BY revenue DESC
        """)).fetchall()
        kpis["revenue_by_category"] = [
            {"category": r[0], "revenue": float(r[1]), "orders": int(r[2])}
            for r in by_cat
        ]

        # ── Deal usage ────────────────────────────────────────────────────────
        deal_usage = conn.execute(text("""
            SELECT
                dd2.deal_name,
                COUNT(ft.transaction_key)              AS usage_count,
                ROUND(SUM(ft.discount_amount)::NUMERIC, 2) AS total_discount_given
            FROM fact_transactions ft
            JOIN dim_deals dd2 ON ft.deal_key = dd2.deal_key
            GROUP BY dd2.deal_name
            ORDER BY usage_count DESC
        """)).fetchall()
        kpis["deal_usage"] = [
            {"deal_name": r[0], "usage_count": int(r[1]), "discount_given": float(r[2])}
            for r in deal_usage
        ]

    logger.info(f"KPIs computed: revenue=${kpis['total_revenue']:,.2f}, "
                f"churn={kpis['churn_rate']}%, retention={kpis['retention_rate']}%")
    return kpis


if __name__ == "__main__":
    import json
    kpis = compute_kpis()
    print(json.dumps(kpis, indent=2))
