"""
ShopPulse FastAPI Backend
Serves data, analytics, and ML prediction APIs.
Run with: uvicorn main:app --reload
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os, logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ShopPulse API",
    description="Customer & Deal Intelligence Platform",
    version="1.0.0",
)

# ── CORS (allow React dev server) ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_engine():
    db_url = (
        f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
        f"{os.getenv('DB_PASSWORD', 'password')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'shoppulse')}"
    )
    return create_engine(db_url)


# ── Pydantic models ───────────────────────────────────────────────────────────

class ChurnInput(BaseModel):
    recency:    float
    frequency:  float
    monetary:   float
    deal_count: Optional[float] = 0


# ═══════════════════════════════════════════════════════════════════════════════
# DATA ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {"message": "ShopPulse API is running", "version": "1.0.0"}


@app.get("/customers")
def get_customers(
    segment: Optional[str] = None,
    limit:   int = Query(default=100, le=1000),
    offset:  int = 0,
):
    """List customers with optional segment filter."""
    engine = get_engine()
    where  = "WHERE segment = :segment" if segment else ""
    query  = f"""
        SELECT customer_id, first_name, last_name, email,
               city, state, segment, signup_date
        FROM dim_customers
        {where}
        ORDER BY customer_key
        LIMIT :limit OFFSET :offset
    """
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(query), {
                "segment": segment, "limit": limit, "offset": offset
            }).fetchall()
        return {"count": len(rows), "data": [dict(r._mapping) for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    """Get a single customer and their transaction history."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            cust = conn.execute(text(
                "SELECT * FROM dim_customers WHERE customer_id = :cid"
            ), {"cid": customer_id}).fetchone()

            if not cust:
                raise HTTPException(status_code=404, detail="Customer not found")

            txns = conn.execute(text("""
                SELECT ft.transaction_id, dp.product_name, dp.category,
                       ft.quantity, ft.net_amount, dd.full_date, ft.return_flag
                FROM fact_transactions ft
                JOIN dim_products dp ON ft.product_key = dp.product_key
                JOIN dim_dates    dd ON ft.date_key     = dd.date_key
                JOIN dim_customers dc ON ft.customer_key = dc.customer_key
                WHERE dc.customer_id = :cid
                ORDER BY dd.full_date DESC
            """), {"cid": customer_id}).fetchall()

        return {
            "customer":     dict(cust._mapping),
            "transactions": [dict(r._mapping) for r in txns],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/transactions")
def get_transactions(
    start_date: Optional[str] = None,
    end_date:   Optional[str] = None,
    category:   Optional[str] = None,
    limit:      int = Query(default=200, le=1000),
):
    """List transactions with optional date and category filters."""
    engine = get_engine()
    conditions = ["ft.return_flag = FALSE"]
    params: dict = {"limit": limit}

    if start_date:
        conditions.append("dd.full_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("dd.full_date <= :end_date")
        params["end_date"] = end_date
    if category:
        conditions.append("dp.category = :category")
        params["category"] = category

    where = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT ft.transaction_id, dc.customer_id,
               dp.product_name, dp.category,
               ft.quantity, ft.unit_price, ft.net_amount,
               dd.full_date AS transaction_date
        FROM fact_transactions ft
        JOIN dim_customers dc ON ft.customer_key = dc.customer_key
        JOIN dim_products  dp ON ft.product_key  = dp.product_key
        JOIN dim_dates     dd ON ft.date_key      = dd.date_key
        {where}
        ORDER BY dd.full_date DESC
        LIMIT :limit
    """
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(query), params).fetchall()
        return {"count": len(rows), "data": [dict(r._mapping) for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/kpis")
def get_kpis():
    """Return all core business KPIs."""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from analytics.kpi_calculations import compute_kpis
        return compute_kpis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/segments")
def get_segments():
    """Return customer segment distribution."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT segment_label, churn_risk,
                       COUNT(*)          AS customer_count,
                       AVG(monetary)     AS avg_monetary,
                       AVG(recency_days) AS avg_recency,
                       AVG(frequency)    AS avg_frequency
                FROM customer_segments
                GROUP BY segment_label, churn_risk
                ORDER BY customer_count DESC
            """)).fetchall()

            all_segs = conn.execute(text("""
                SELECT cs.customer_id, cs.segment_label, cs.churn_risk,
                       cs.rfm_score, cs.recency_days, cs.frequency, cs.monetary,
                       dc.first_name, dc.last_name
                FROM customer_segments cs
                JOIN dim_customers dc ON cs.customer_id = dc.customer_id
                ORDER BY cs.rfm_score DESC
            """)).fetchall()

        return {
            "summary":   [dict(r._mapping) for r in rows],
            "customers": [dict(r._mapping) for r in all_segs],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rfm")
def get_rfm():
    """Return full RFM analysis results."""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from analytics.rfm_features import compute_rfm
        df = compute_rfm()
        return {"count": len(df), "data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# ML ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/predict-churn")
def predict_churn(data: ChurnInput):
    """Predict churn probability for a customer given their RFM metrics."""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from ml.predict_churn import predict_single
        result = predict_single(
            recency=data.recency,
            frequency=data.frequency,
            monetary=data.monetary,
            deal_count=data.deal_count,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/churn-summary")
def get_churn_summary():
    """Return churn risk distribution from the predictions table."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT risk_category,
                       COUNT(*)                      AS customer_count,
                       AVG(churn_probability) * 100  AS avg_churn_pct
                FROM churn_predictions
                GROUP BY risk_category
                ORDER BY
                    CASE risk_category
                        WHEN 'High'   THEN 1
                        WHEN 'Medium' THEN 2
                        ELSE 3
                    END
            """)).fetchall()

            all_preds = conn.execute(text("""
                SELECT cp.customer_id, dc.first_name, dc.last_name,
                       cp.recency, cp.frequency, cp.monetary,
                       cp.churn_probability, cp.churn_label, cp.risk_category
                FROM churn_predictions cp
                JOIN dim_customers dc ON cp.customer_id = dc.customer_id
                ORDER BY cp.churn_probability DESC
                LIMIT 50
            """)).fetchall()

        return {
            "summary":     [dict(r._mapping) for r in rows],
            "top_at_risk": [dict(r._mapping) for r in all_preds],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
