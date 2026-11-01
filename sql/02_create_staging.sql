-- 02_create_staging.sql
-- PURPOSE: create the staging table that receives the raw sales file.
--
-- WHY EVERYTHING IS TEXT: raw data is messy. A price might arrive as 'abc',
-- a date as '13/05/2025'. If the columns were numbers or dates, those rows
-- would crash the load. Text accepts anything, and we validate in the next step.
--
-- NOTE: the schema name has a hyphen, so it must be wrapped in double quotes.

CREATE TABLE IF NOT EXISTS "dukafresh-dw".stg_sales_raw (
    receipt_id      TEXT,   -- which receipt this line belongs to
    line_no         TEXT,   -- line number on that receipt
    sale_date       TEXT,   -- may arrive in different formats
    store_name      TEXT,   -- may contain typos
    product_id      TEXT,
    quantity        TEXT,   -- may be negative
    unit_price      TEXT,   -- may be missing
    discount        TEXT,
    customer_id     TEXT,   -- empty for walk-in shoppers (not an error)
    payment_method  TEXT,   -- may be written in different ways
    source_file     TEXT,   -- which file the row came from (for traceability)
    loaded_at       TIMESTAMP DEFAULT now()  -- the database stamps the load time
);