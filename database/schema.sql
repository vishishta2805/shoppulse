-- =============================================================
-- ShopPulse Database Schema
-- Star Schema for Customer & Deal Intelligence Platform
-- =============================================================

-- Drop existing tables in reverse dependency order
DROP TABLE IF EXISTS fact_transactions CASCADE;
DROP TABLE IF EXISTS dim_customers CASCADE;
DROP TABLE IF EXISTS dim_products CASCADE;
DROP TABLE IF EXISTS dim_dates CASCADE;
DROP TABLE IF EXISTS dim_deals CASCADE;
DROP TABLE IF EXISTS customer_segments CASCADE;
DROP TABLE IF EXISTS churn_predictions CASCADE;

-- =============================================================
-- DIMENSION: dim_customers
-- =============================================================
CREATE TABLE dim_customers (
    customer_key    SERIAL PRIMARY KEY,
    customer_id     VARCHAR(20) UNIQUE NOT NULL,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    email           VARCHAR(255),
    phone           VARCHAR(50),
    city            VARCHAR(100),
    state           VARCHAR(50),
    country         VARCHAR(100),
    segment         VARCHAR(50),           -- Premium / Standard / Basic
    signup_date     DATE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- =============================================================
-- DIMENSION: dim_products
-- =============================================================
CREATE TABLE dim_products (
    product_key     SERIAL PRIMARY KEY,
    product_id      VARCHAR(20) UNIQUE NOT NULL,
    product_name    VARCHAR(255),
    category        VARCHAR(100),
    unit_price      NUMERIC(10, 2),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- =============================================================
-- DIMENSION: dim_dates
-- =============================================================
CREATE TABLE dim_dates (
    date_key        SERIAL PRIMARY KEY,
    full_date       DATE UNIQUE NOT NULL,
    day             INT,
    month           INT,
    month_name      VARCHAR(20),
    quarter         INT,
    year            INT,
    day_of_week     INT,
    day_name        VARCHAR(20),
    is_weekend      BOOLEAN
);

-- =============================================================
-- DIMENSION: dim_deals
-- =============================================================
CREATE TABLE dim_deals (
    deal_key        SERIAL PRIMARY KEY,
    deal_id         VARCHAR(20) UNIQUE NOT NULL,
    deal_name       VARCHAR(255),
    discount_percent NUMERIC(5, 2),
    start_date      DATE,
    end_date        DATE,
    category        VARCHAR(100),
    min_purchase    NUMERIC(10, 2),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- =============================================================
-- FACT: fact_transactions
-- =============================================================
CREATE TABLE fact_transactions (
    transaction_key SERIAL PRIMARY KEY,
    transaction_id  VARCHAR(20) UNIQUE NOT NULL,
    customer_key    INT REFERENCES dim_customers(customer_key),
    product_key     INT REFERENCES dim_products(product_key),
    date_key        INT REFERENCES dim_dates(date_key),
    deal_key        INT REFERENCES dim_deals(deal_key),  -- nullable
    quantity        INT,
    unit_price      NUMERIC(10, 2),
    discount        NUMERIC(5, 4),       -- e.g. 0.10 = 10%
    gross_amount    NUMERIC(10, 2),      -- quantity * unit_price
    discount_amount NUMERIC(10, 2),      -- gross * discount
    net_amount      NUMERIC(10, 2),      -- gross - discount
    return_flag     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- =============================================================
-- ANALYTICS: customer_segments
-- =============================================================
CREATE TABLE customer_segments (
    id              SERIAL PRIMARY KEY,
    customer_id     VARCHAR(20),
    recency_days    INT,
    frequency       INT,
    monetary        NUMERIC(10, 2),
    rfm_score       NUMERIC(5, 2),
    segment_label   VARCHAR(50),         -- Champions, Loyal, At Risk, Lost
    churn_risk      VARCHAR(20),         -- Low / Medium / High
    computed_at     TIMESTAMP DEFAULT NOW()
);

-- =============================================================
-- ANALYTICS: churn_predictions
-- =============================================================
CREATE TABLE churn_predictions (
    id              SERIAL PRIMARY KEY,
    customer_id     VARCHAR(20),
    recency         NUMERIC(10, 2),
    frequency       NUMERIC(10, 2),
    monetary        NUMERIC(10, 2),
    churn_probability NUMERIC(5, 4),
    churn_label     INT,                 -- 0 = No churn, 1 = Churn
    risk_category   VARCHAR(20),         -- Low / Medium / High
    predicted_at    TIMESTAMP DEFAULT NOW()
);

-- =============================================================
-- INDEXES for query performance
-- =============================================================
CREATE INDEX idx_fact_customer ON fact_transactions(customer_key);
CREATE INDEX idx_fact_date ON fact_transactions(date_key);
CREATE INDEX idx_fact_product ON fact_transactions(product_key);
CREATE INDEX idx_fact_deal ON fact_transactions(deal_key);
CREATE INDEX idx_segments_customer ON customer_segments(customer_id);
CREATE INDEX idx_churn_customer ON churn_predictions(customer_id);

-- =============================================================
-- SAMPLE DATA: dim_deals
-- =============================================================
INSERT INTO dim_deals (deal_id, deal_name, discount_percent, start_date, end_date, category, min_purchase) VALUES
('D001', 'New Year Sale',    10.00, '2023-01-01', '2023-03-31', 'All',         50.00),
('D002', 'Tech Week',        15.00, '2023-01-10', '2023-04-30', 'Electronics', 100.00),
('D003', 'Summer Blast',     20.00, '2023-05-01', '2023-08-31', 'All',         75.00),
('D004', 'Loyalty Reward',   25.00, '2023-09-01', '2023-12-31', 'All',         60.00);

-- =============================================================
-- SAMPLE DATA: dim_products
-- =============================================================
INSERT INTO dim_products (product_id, product_name, category, unit_price) VALUES
('P001', 'Laptop Stand',       'Electronics', 45.00),
('P002', 'Smart Watch',        'Electronics', 199.99),
('P003', 'Yoga Mat',           'Sports',      35.00),
('P004', 'Protein Powder',     'Health',      49.99),
('P005', 'Wireless Headphones','Electronics', 89.99),
('P006', 'Sunglasses',         'Fashion',     120.00),
('P007', 'Bluetooth Speaker',  'Electronics', 75.00),
('P008', 'Coffee Maker',       'Kitchen',     129.99),
('P009', 'Cooking Pan',        'Kitchen',     65.00),
('P010', 'Novel - Mystery',    'Books',       14.99),
('P011', 'Desk Lamp',          'Home',        49.99),
('P012', 'Running Shoes',      'Footwear',    59.99),
('P013', 'Air Purifier',       'Home',        149.99),
('P014', 'Backpack',           'Fashion',     79.99),
('P015', 'Face Cream',         'Beauty',      29.99),
('P016', 'Vitamin C',          'Health',      19.99),
('P017', 'Dumbbell Set',       'Sports',      95.00),
('P018', 'Scented Candle',     'Home',        12.99);
