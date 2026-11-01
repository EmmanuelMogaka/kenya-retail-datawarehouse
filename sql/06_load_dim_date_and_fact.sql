-- 06_load_dim_date_and_fact.sql
-- PURPOSE: build dim_date and fill fact_sales from clean_sales.
-- The other four dimensions are loaded by load_warehouse.py (from the reference CSV files).
--
-- Safe to rerun: load_warehouse.py empties all six warehouse tables before this runs.
-- NOTE: no percent sign anywhere in this file (the database driver treats it as a placeholder).

-- 1) Add the receipt reference to the fact table (a "degenerate dimension").
--    Needed for: average transaction value, repeat purchases, products bought together.
ALTER TABLE "dukafresh-dw".fact_sales ADD COLUMN IF NOT EXISTS receipt_id TEXT;
ALTER TABLE "dukafresh-dw".fact_sales ADD COLUMN IF NOT EXISTS line_no INT;

-- 2) dim_date: one row for every calendar day between the first and last sale.
--    date_key looks like 20250131, a readable whole number.
--    isodow: Monday = 1 ... Sunday = 7, so 6 and 7 are the weekend.
INSERT INTO "dukafresh-dw".dim_date (date_key, full_date, month, quarter, year, is_weekend)
SELECT to_char(d, 'YYYYMMDD')::int,
       d::date,
       EXTRACT(month   FROM d)::int,
       EXTRACT(quarter FROM d)::int,
       EXTRACT(year    FROM d)::int,
       EXTRACT(isodow  FROM d) >= 6
FROM generate_series(
         (SELECT min(sale_date) FROM "dukafresh-dw".clean_sales),
         (SELECT max(sale_date) FROM "dukafresh-dw".clean_sales),
         interval '1 day'
     ) AS g(d);

-- 3) fact_sales: one row per clean sales line.
--    - store and payment keys are found by joining on their names
--    - walk-in customers (no customer_id) become key 0, the unknown member
--    - total_amount = quantity x unit price - discount (the discount is an amount in KES)
--    - sale_line_id is numbered in a fixed order, so reruns give the same ids
INSERT INTO "dukafresh-dw".fact_sales
    (sale_line_id, receipt_id, line_no, date_key, store_key, product_key,
     customer_key, payment_key, quantity, unit_price, discount, total_amount)
SELECT ROW_NUMBER() OVER (ORDER BY c.receipt_id, c.line_no),
       c.receipt_id,
       c.line_no,
       to_char(c.sale_date, 'YYYYMMDD')::int,
       s.store_key,
       c.product_id,                       -- product_key = product_id (source id reused)
       COALESCE(c.customer_id, 0),         -- 0 = walk-in customer
       p.payment_key,
       c.quantity,
       c.unit_price,
       c.discount,
       c.quantity * c.unit_price - c.discount
FROM "dukafresh-dw".clean_sales c
JOIN "dukafresh-dw".dim_store s            ON s.store_name  = c.store_name
JOIN "dukafresh-dw".dim_payment_method p   ON p.method_name = c.payment_method;
-- If a product id is missing from dim_product, the foreign key makes this fail loudly.
-- If a store or payment name has no match, the row would be dropped silently,
-- which is why the Python script checks that fact rows = clean rows.