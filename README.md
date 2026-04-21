# ShopPulse — Customer & Deal Intelligence Platform

> A full-stack data analytics + machine learning platform that converts raw customer and transaction data into actionable business insights.

---

## Architecture

```
CSV Files → ETL Pipeline → PostgreSQL (Star Schema)
                                 ↓
                    Analytics (RFM · KPIs · Segments)
                                 ↓
                    ML Model (Churn Prediction)
                                 ↓
                    FastAPI Backend (REST APIs)
                                 ↓
                    React Dashboard (Recharts · Tailwind)
```

---

## Folder Structure

```
shoppulse/
├── analytics/
│   ├── churn_labels.py        # Generate ML training labels
│   ├── customer_segments.py   # RFM-based segmentation
│   ├── kpi_calculations.py    # KPI metrics (revenue, AOV, churn rate…)
│   └── rfm_features.py        # Recency / Frequency / Monetary scores
├── backend/
│   └── main.py                # FastAPI app with all REST endpoints
├── data/
│   ├── raw/                   # Source CSV files
│   └── staging/               # Cleaned CSVs (auto-generated)
├── database/
│   └── schema.sql             # Star schema DDL + seed data
├── etl/
│   ├── extract.py             # Read CSV files
│   ├── transform.py           # Clean + feature engineering
│   ├── load.py                # Insert into PostgreSQL
│   └── run.py                 # Pipeline entry point
├── frontend/
│   └── src/
│       ├── api/               # Axios client + API functions
│       ├── components/        # KpiCard, Loader, RiskBadge…
│       └── pages/             # Dashboard, Customers, Transactions, ChurnPredict
├── ml/
│   ├── train_model.py         # Train + save churn model
│   └── predict_churn.py       # Load model + predict
├── .env.example               # Environment variable template
├── requirements.txt           # Python dependencies
└── README.md
```

---

## Setup Guide

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+

---

### Step 1 — Clone & environment

```bash
git clone <your-repo-url>
cd shoppulse

# Copy env template
cp .env.example .env
# Edit .env and set your DB_PASSWORD
```

---

### Step 2 — Python virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

---

### Step 3 — PostgreSQL setup

```bash
# Create database (run as postgres superuser)
psql -U postgres -c "CREATE DATABASE shoppulse;"

# Apply schema (creates all tables + seeds date dimension + sample data)
psql -U postgres -d shoppulse -f database/schema.sql
```

---

### Step 4 — Run ETL pipeline

```bash
# Reads data/raw/*.csv → cleans → loads into PostgreSQL
python etl/run.py
```

---

### Step 5 — Run analytics + segmentation

```bash
python analytics/customer_segments.py
```

---

### Step 6 — Train churn model

```bash
python ml/train_model.py
# Saves ml/churn_model.pkl
```

---

### Step 7 — Start FastAPI backend

```bash
uvicorn backend.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

---

### Step 8 — Start React frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard available at: http://localhost:5173

---

## API Reference

| Method | Endpoint                   | Description                        |
|--------|----------------------------|------------------------------------|
| GET    | `/health`                  | DB connectivity check              |
| GET    | `/customers`               | List customers (filter: city, gender) |
| GET    | `/customers/{id}`          | Single customer + transactions     |
| GET    | `/transactions`            | List transactions (filter: date, customer) |
| GET    | `/kpis`                    | Scalar KPI metrics                 |
| GET    | `/kpis/monthly-revenue`    | Monthly revenue trend              |
| GET    | `/kpis/top-products`       | Top N products by revenue          |
| GET    | `/kpis/category-revenue`   | Revenue by product category        |
| GET    | `/segments`                | Customer segment distribution      |
| GET    | `/rfm`                     | Full RFM table                     |
| POST   | `/predict-churn`           | Single customer churn prediction   |
| POST   | `/predict-churn/batch`     | Predict + save for all customers   |
| GET    | `/predict-churn/all`       | Retrieve saved predictions         |

---

## Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| Backend    | Python 3.10 · FastAPI · Uvicorn   |
| Database   | PostgreSQL 14 · SQLAlchemy        |
| Analytics  | Pandas · NumPy                    |
| ML         | Scikit-learn (LogReg + RandomForest) |
| Frontend   | React 18 · Vite · Tailwind CSS    |
| Charts     | Recharts                          |
| HTTP       | Axios                             |

---

## Sample Dataset

Three CSV files are provided in `data/raw/`:

- `customers.csv` — 20 customers with demographics
- `transactions.csv` — 50 transactions across 2023–2024
- `deals.csv` — 6 promotional deals

---

## Churn Model

Features used: `recency_days`, `frequency`, `monetary`

Label: customer is churned if last purchase > 90 days ago

Two models are evaluated (Logistic Regression & Random Forest) via 5-fold cross-validation; the best F1 scorer is saved.

Risk tiers:
- **Low** — churn probability < 33%
- **Medium** — 33% – 66%
- **High** — > 66%

---

## Interview Notes

- Star schema with `fact_transactions` + 4 dimension tables
- Idempotent ETL using `INSERT … ON CONFLICT DO NOTHING`
- Modular architecture (each layer is independently runnable)
- CORS configured for local dev; swap origin list for production
- `.pkl` model file excluded from git (regenerate with `train_model.py`)
