"""
main.py  —  ShopPulse FastAPI Backend
Run: uvicorn backend.main:app --reload --port 8000
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ShopPulse API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
   allow_origins=[
    "http://localhost:5173",
    "http://localhost:3000",
    "https://shoppulse-gvr.vercel.app",
],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


def get_engine():
    url = (
        f"postgresql+psycopg2://"
        f"{os.getenv('DB_USER','postgres')}:{os.getenv('DB_PASSWORD','password')}"
        f"@{os.getenv('DB_HOST','localhost')}:{os.getenv('DB_PORT','5432')}"
        f"/{os.getenv('DB_NAME','shoppulse')}"
    )
    return create_engine(url)


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "ShopPulse API"}


@app.get("/health")
def health():
    try:
        with get_engine().connect() as c:
            c.execute(text("SELECT 1"))
        return {"status": "healthy", "db": "connected"}
    except Exception as e:
        raise HTTPException(503, str(e))


# ── Customers ────────────────────────────────────────────────────────────────

@app.get("/customers")
def list_customers(
    limit:  int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    city:   Optional[str] = None,
    gender: Optional[str] = None,
):
    conditions = ["1=1"]
    params: dict = {"limit": limit, "offset": offset}
    if city:
        conditions.append("LOWER(city) = LOWER(:city)")
        params["city"] = city
    where = " AND ".join(conditions)
    q = text(f"""
        SELECT
            customer_id,
            first_name || ' ' || last_name AS name,
            email, phone, city, state, country,
            signup_date, segment
        FROM dim_customers
        WHERE {where}
        ORDER BY signup_date DESC
        LIMIT :limit OFFSET :offset;
    """)
    with get_engine().connect() as c:
        df = pd.read_sql(q, c, params=params)
    return {"total": len(df), "customers": df.to_dict(orient="records")}


@app.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    engine = get_engine()
    with engine.connect() as c:
        cust = pd.read_sql(text("""
            SELECT customer_id, first_name || ' ' || last_name AS name,
                   email, phone, city, state, country, signup_date, segment
            FROM dim_customers WHERE customer_id = :id
        """), c, params={"id": customer_id})
        if cust.empty:
            raise HTTPException(404, "Customer not found")
        txns = pd.read_sql(text("""
            SELECT
                f.transaction_id,
                dd.full_date AS transaction_date,
                p.product_name, p.category,
                f.quantity, f.net_amount
            FROM fact_transactions f
            JOIN dim_customers dc ON dc.customer_key = f.customer_key
            JOIN dim_products   p  ON p.product_key  = f.product_key
            JOIN dim_dates      dd ON dd.date_key     = f.date_key
            WHERE dc.customer_id = :id
            ORDER BY dd.full_date DESC
        """), c, params={"id": customer_id})
        seg = pd.read_sql(text("""
            SELECT * FROM customer_segments WHERE customer_id = :id
        """), c, params={"id": customer_id})
    return {
        "customer":     cust.to_dict(orient="records")[0],
        "transactions": txns.to_dict(orient="records"),
        "segment":      seg.to_dict(orient="records")[0] if not seg.empty else None,
    }


# ── Transactions ─────────────────────────────────────────────────────────────

@app.get("/transactions")
def list_transactions(
    limit:       int = Query(100, ge=1, le=1000),
    offset:      int = Query(0, ge=0),
    customer_id: Optional[str] = None,
    start_date:  Optional[str] = None,
    end_date:    Optional[str] = None,
):
    conditions = ["1=1"]
    params: dict = {"limit": limit, "offset": offset}
    if customer_id:
        conditions.append("dc.customer_id = :customer_id")
        params["customer_id"] = customer_id
    if start_date:
        conditions.append("dd.full_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("dd.full_date <= :end_date")
        params["end_date"] = end_date
    where = " AND ".join(conditions)
    q = text(f"""
        SELECT
            f.transaction_id,
            dc.customer_id,
            dc.first_name || ' ' || dc.last_name AS customer_name,
            p.product_name, p.category,
            f.quantity, f.unit_price, f.discount,
            f.net_amount, f.gross_amount,
            dd.full_date AS transaction_date,
            COALESCE(dl.deal_name, 'None') AS deal_name
        FROM fact_transactions f
        JOIN dim_customers dc ON dc.customer_key = f.customer_key
        JOIN dim_products   p  ON p.product_key  = f.product_key
        JOIN dim_dates      dd ON dd.date_key     = f.date_key
        LEFT JOIN dim_deals dl ON dl.deal_key     = f.deal_key
        WHERE {where}
        ORDER BY dd.full_date DESC
        LIMIT :limit OFFSET :offset;
    """)
    with get_engine().connect() as c:
        df = pd.read_sql(q, c, params=params)
    return {"total": len(df), "transactions": df.to_dict(orient="records")}


# ── KPIs ─────────────────────────────────────────────────────────────────────

@app.get("/kpis")
def kpis():
    try:
        engine = get_engine()
        with engine.connect() as c:

            # Revenue, Orders, AOV, Total Discounts
            rev = c.execute(text("""
                SELECT
                    COALESCE(ROUND(SUM(net_amount)::NUMERIC,2), 0),
                    COUNT(*),
                    COALESCE(ROUND(AVG(net_amount)::NUMERIC,2), 0),
                    COALESCE(ROUND(SUM(discount_amount)::NUMERIC,2), 0)
                FROM fact_transactions WHERE return_flag = FALSE;
            """)).fetchone()

            # Total returns
            total_returns = c.execute(text("""
                SELECT COUNT(*) FROM fact_transactions WHERE return_flag = TRUE;
            """)).scalar() or 0

            # Total customers
            total_customers = c.execute(
                text("SELECT COUNT(*) FROM dim_customers;")
            ).scalar()

            # Active customers — purchased in last 90 days
            active_customers = c.execute(text("""
                SELECT COUNT(DISTINCT f.customer_key)
                FROM fact_transactions f
                JOIN dim_dates dd ON dd.date_key = f.date_key
                WHERE f.return_flag = FALSE
                AND dd.full_date >= CURRENT_DATE - INTERVAL '90 days';
            """)).scalar() or 0

            # Churned customers — no purchase in last 90 days
            churned_customers = c.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT f.customer_key, MAX(dd.full_date) AS last_date
                    FROM fact_transactions f
                    JOIN dim_dates dd ON dd.date_key = f.date_key
                    WHERE f.return_flag = FALSE
                    GROUP BY f.customer_key
                    HAVING MAX(dd.full_date) < CURRENT_DATE - INTERVAL '90 days'
                ) sub;
            """)).scalar() or 0

            # Deal participation
            deal_txns = c.execute(text("""
                SELECT COUNT(*) FROM fact_transactions
                WHERE deal_key IS NOT NULL AND return_flag = FALSE;
            """)).scalar() or 0

            # New customers last 30 days
            new_customers = c.execute(text("""
                SELECT COUNT(*) FROM dim_customers
                WHERE signup_date >= CURRENT_DATE - INTERVAL '30 days';
            """)).scalar() or 0

        total_orders  = int(rev[1])
        churn_rate    = round((int(churned_customers) / max(int(total_customers), 1)) * 100, 2)

        return {
            "total_revenue":      float(rev[0]),
            "total_orders":       total_orders,
            "total_customers":    int(total_customers),
            "avg_order_value":    float(rev[2]),
            "total_discounts":    float(rev[3]),
            "total_returns":      int(total_returns),
            "active_customers":   int(active_customers),
            "churned_customers":  int(churned_customers),
            "churn_rate":         churn_rate,
            "retention_rate":     round(100 - churn_rate, 2),
            "deal_participation": round((int(deal_txns) / total_orders) * 100, 2) if total_orders else 0,
            "new_customers_30d":  int(new_customers),
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/kpis/monthly-revenue")
def monthly_revenue():
    try:
        q = text("""
            SELECT
                dd.year, dd.month,
                TRIM(dd.month_name) AS month_name,
                ROUND(SUM(f.net_amount)::NUMERIC, 2) AS revenue,
                COUNT(f.transaction_key) AS orders
            FROM fact_transactions f
            JOIN dim_dates dd ON dd.date_key = f.date_key
            WHERE f.return_flag = FALSE
            GROUP BY dd.year, dd.month, dd.month_name
            ORDER BY dd.year, dd.month;
        """)
        with get_engine().connect() as c:
            df = pd.read_sql(q, c)
        df["label"] = df["month_name"].str.strip() + " " + df["year"].astype(str)
        return {"data": df[["label","revenue","orders"]].to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/kpis/top-products")
def top_products(limit: int = Query(10, ge=1, le=50)):
    try:
        q = text("""
            SELECT
                p.product_name, p.category,
                COUNT(f.transaction_key) AS orders,
                ROUND(SUM(f.net_amount)::NUMERIC, 2) AS revenue
            FROM fact_transactions f
            JOIN dim_products p ON p.product_key = f.product_key
            WHERE f.return_flag = FALSE
            GROUP BY p.product_name, p.category
            ORDER BY revenue DESC
            LIMIT :limit;
        """)
        with get_engine().connect() as c:
            df = pd.read_sql(q, c, params={"limit": limit})
        return {"data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/kpis/category-revenue")
def category_revenue():
    try:
        q = text("""
            SELECT p.category,
                   ROUND(SUM(f.net_amount)::NUMERIC, 2) AS revenue
            FROM fact_transactions f
            JOIN dim_products p ON p.product_key = f.product_key
            WHERE f.return_flag = FALSE
            GROUP BY p.category ORDER BY revenue DESC;
        """)
        with get_engine().connect() as c:
            df = pd.read_sql(q, c)
        return {"data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/segments")
def segments():
    try:
        q = text("""
            SELECT segment_label AS segment, COUNT(*) AS customer_count
            FROM customer_segments
            GROUP BY segment_label ORDER BY customer_count DESC;
        """)
        with get_engine().connect() as c:
            df = pd.read_sql(q, c)
        return {"data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/rfm")
def rfm():
    try:
        q = text("""
            SELECT
                cs.customer_id,
                dc.first_name || ' ' || dc.last_name AS name,
                cs.recency_days, cs.frequency, cs.monetary,
                cs.rfm_score,
                cs.segment_label AS segment,
                cs.churn_risk
            FROM customer_segments cs
            JOIN dim_customers dc ON dc.customer_id = cs.customer_id;
        """)
        with get_engine().connect() as c:
            df = pd.read_sql(q, c)
        return {"data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── ML ───────────────────────────────────────────────────────────────────────

class ChurnInput(BaseModel):
    recency_days: float = Field(..., ge=0)
    frequency:    float = Field(..., ge=0)
    monetary:     float = Field(..., ge=0)


@app.post("/predict-churn")
def predict_churn(data: ChurnInput):
    try:
        from ml.predict_churn import predict_single
        result = predict_single(data.recency_days, data.frequency, data.monetary)
        return result
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/predict-churn/batch")
def predict_churn_batch():
    try:
        from ml.predict_churn import predict_bulk
        df = predict_bulk()
        return {
            "message": f"Predictions saved for {len(df)} customers",
            "summary": df["risk_category"].value_counts().to_dict() if not df.empty else {}
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/predict-churn/all")
def get_all_predictions():
    try:
        q = text("""
            SELECT
                cp.customer_id,
                dc.first_name || ' ' || dc.last_name AS name,
                cp.churn_probability AS churn_prob,
                cp.churn_label,
                cp.risk_category,
                cp.predicted_at
            FROM churn_predictions cp
            JOIN dim_customers dc ON dc.customer_id = cp.customer_id
            ORDER BY cp.churn_probability DESC;
        """)
        with get_engine().connect() as c:
            df = pd.read_sql(q, c)
        return {"data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(500, str(e))