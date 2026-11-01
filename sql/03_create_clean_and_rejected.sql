-- 03_create_clean_and_rejected.sql
-- PURPOSE: create the two tables that the cleaning step writes into.
--
--   clean_sales    -> rows that passed every check, with proper data types
--   rejected_sales -> rows we could not trust, kept together with the reason
--
-- Unlike staging (all text), clean_sales uses REAL types: whole numbers,
-- decimals and dates. That is how the database protects us from bad data later.

CREATE TABLE IF NOT EXISTS "dukafresh-dw".clean_sales (
    receipt_id      TEXT NOT NULL,
    line_no         INT  NOT NULL,
    sale_date       DATE NOT NULL,          -- converted from text to a real date
    store_name      TEXT NOT NULL,          -- standardised spelling
    product_id      INT  NOT NULL,
    quantity        INT  NOT NULL,          -- must be positive (checked before loading)
    unit_price      NUMERIC(10,2) NOT NULL, -- must be present
    discount        NUMERIC(10,2) NOT NULL DEFAULT 0,
    customer_id     INT,                    -- empty is allowed: walk-in shoppers
    payment_method  TEXT NOT NULL,          -- one of M-Pesa, Cash, Card
    source_file     TEXT,
    cleaned_at      TIMESTAMP DEFAULT now(),
    PRIMARY KEY (receipt_id, line_no)       -- one row per receipt line; blocks duplicates
);

-- Rejected rows keep their ORIGINAL text values (nothing is changed) plus the reason.
CREATE TABLE IF NOT EXISTS "dukafresh-dw".rejected_sales (
    receipt_id      TEXT,
    line_no         TEXT,
    sale_date       TEXT,
    store_name      TEXT,
    product_id      TEXT,
    quantity        TEXT,
    unit_price      TEXT,
    discount        TEXT,
    customer_id     TEXT,
    payment_method  TEXT,
    source_file     TEXT,
    reject_reason   TEXT NOT NULL,          -- e.g. MISSING_UNIT_PRICE
    rejected_at     TIMESTAMP DEFAULT now()
);