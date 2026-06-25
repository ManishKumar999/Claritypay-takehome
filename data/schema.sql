-- ============================================================================
-- Clarity Pay (BNPL) — schema + load script  (PostgreSQL)
-- ============================================================================
-- Usage (from this data/ directory, with a running Postgres):
--     createdb claritypay
--     psql claritypay -f schema.sql
--
-- The \copy commands at the bottom load the CSVs. \copy runs client-side, so
-- paths are relative to where you launch psql. Empty CSV fields load as NULL.
-- ============================================================================

DROP TABLE IF EXISTS installments, account_links, plans, customers, merchants CASCADE;

-- ---------------------------------------------------------------------------
-- merchants : where customers shop (dimension)
-- ---------------------------------------------------------------------------
CREATE TABLE merchants (
    merchant_id   INTEGER PRIMARY KEY,
    name          TEXT        NOT NULL,
    category      TEXT        NOT NULL,   -- Fashion, Electronics, Travel, ...
    region        TEXT        NOT NULL,   -- NA / EU / APAC / LATAM
    mdr_bps       INTEGER     NOT NULL,   -- merchant discount rate (Clarity's fee), basis points
    onboarded_at  DATE        NOT NULL
);

-- ---------------------------------------------------------------------------
-- customers : BNPL accounts. Also the NODES of the account-linkage graph.
-- ---------------------------------------------------------------------------
CREATE TABLE customers (
    customer_id        INTEGER PRIMARY KEY,
    signup_at          DATE    NOT NULL,
    region             TEXT    NOT NULL,
    risk_band          CHAR(1) NOT NULL,   -- A (best) .. E (worst)
    credit_limit_usd   NUMERIC(10,2) NOT NULL,
    status             TEXT    NOT NULL,    -- active / defaulted
    is_confirmed_fraud BOOLEAN NOT NULL
);

-- ---------------------------------------------------------------------------
-- plans : one BNPL order / installment plan per row
-- ---------------------------------------------------------------------------
CREATE TABLE plans (
    plan_id             INTEGER PRIMARY KEY,
    customer_id         INTEGER NOT NULL REFERENCES customers(customer_id),
    merchant_id         INTEGER NOT NULL REFERENCES merchants(merchant_id),
    product_type        TEXT    NOT NULL,  -- pay_in_4 / pay_in_3 / pay_monthly_6 / pay_monthly_12
    num_installments    INTEGER NOT NULL,
    order_amount_usd    NUMERIC(12,2) NOT NULL,   -- principal
    total_repayable_usd NUMERIC(12,2) NOT NULL,   -- principal + interest (= principal when APR 0)
    apr_bps             INTEGER NOT NULL,         -- 0 for pay-in-N products
    created_at          DATE    NOT NULL,
    status              TEXT    NOT NULL   -- active / paid_off / delinquent / defaulted
);

-- ---------------------------------------------------------------------------
-- installments : the repayment ledger (one row per scheduled installment)
-- ---------------------------------------------------------------------------
CREATE TABLE installments (
    installment_id   INTEGER PRIMARY KEY,
    plan_id          INTEGER NOT NULL REFERENCES plans(plan_id),
    installment_no   INTEGER NOT NULL,         -- 1..num_installments
    due_date         DATE    NOT NULL,
    amount_due_usd   NUMERIC(12,2) NOT NULL,
    paid_date        DATE,                      -- NULL if not yet paid
    paid_amount_usd  NUMERIC(12,2),             -- NULL if not yet paid
    late_fee_usd     NUMERIC(8,2) NOT NULL DEFAULT 0,
    status           TEXT    NOT NULL           -- scheduled / paid / late / missed / written_off
);

-- ---------------------------------------------------------------------------
-- account_links : fraud / identity linkage graph (EDGES).
--   Stored in BOTH directions (a->b and b->a) so traversal needs no UNION.
--   link_distance: LOWER = STRONGER shared signal
--     shared_device 1, shared_card 2, shared_bank 3,
--     shared_phone 5, shared_address 8, shared_email_domain 20
--   "least-cost path" = strongest chain of evidence between two accounts.
-- ---------------------------------------------------------------------------
CREATE TABLE account_links (
    link_id          INTEGER PRIMARY KEY,
    src_customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
    dst_customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
    link_type        TEXT    NOT NULL,
    link_distance    NUMERIC(6,2) NOT NULL,
    detected_at      DATE    NOT NULL
);

-- ---------------------------------------------------------------------------
-- Load the CSVs (header row present; empty fields -> NULL)
-- ---------------------------------------------------------------------------
\copy merchants     FROM 'merchants.csv'     WITH (FORMAT csv, HEADER true);
\copy customers     FROM 'customers.csv'     WITH (FORMAT csv, HEADER true);
\copy plans         FROM 'plans.csv'         WITH (FORMAT csv, HEADER true);
\copy installments  FROM 'installments.csv'  WITH (FORMAT csv, HEADER true);
\copy account_links FROM 'account_links.csv' WITH (FORMAT csv, HEADER true);

-- ---------------------------------------------------------------------------
-- Helpful indexes (optional, but realistic)
-- ---------------------------------------------------------------------------
CREATE INDEX idx_plans_customer      ON plans(customer_id);
CREATE INDEX idx_plans_merchant      ON plans(merchant_id);
CREATE INDEX idx_inst_plan           ON installments(plan_id);
CREATE INDEX idx_inst_due            ON installments(due_date);
CREATE INDEX idx_inst_status         ON installments(status);
CREATE INDEX idx_links_src           ON account_links(src_customer_id);
CREATE INDEX idx_links_dst           ON account_links(dst_customer_id);

ANALYZE;
