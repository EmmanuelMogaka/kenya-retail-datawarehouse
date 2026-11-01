-- 05_clean_sales.sql
-- PURPOSE: validate every staging row and sort it into clean_sales or rejected_sales.
--
-- RULES FOLLOWED
--   1. Fix only what can be fixed with certainty (spelling via lookup, date format).
--   2. If fixing would mean guessing (missing price, negative quantity), REJECT
--      the row and record the reason.
--   3. Nothing disappears: clean rows + rejected rows = staging rows (checked in Python).
--   4. Idempotent: both target tables are emptied first, so a rerun gives the same result.
--
-- ASSUMPTION (document it!): dates that look like 13/05/2025 are day/month/year.
-- LIMITATION: a repeated receipt line is treated as a duplicate even if its content
-- differs. The first copy is kept. A stricter rule could compare the content.

TRUNCATE TABLE "dukafresh-dw".clean_sales;
TRUNCATE TABLE "dukafresh-dw".rejected_sales;

-- A temporary table holds each row plus the verdict. It disappears after the
-- transaction. Computing verdicts here, BEFORE casting any text to numbers or
-- dates, means a bad value can never crash the cleaning step.
CREATE TEMP TABLE checked ON COMMIT DROP AS
WITH numbered AS (
    -- copy_no = 1 for the first copy of a receipt line, 2 for a repeat, and so on
    SELECT s.*,
           ROW_NUMBER() OVER (
               PARTITION BY s.receipt_id, s.line_no
               ORDER BY s.ctid
           ) AS copy_no
    FROM "dukafresh-dw".stg_sales_raw s
),
joined AS (
    -- look up the standard store and payment names (NULL when no match is found)
    SELECT n.*,
           sm.standard_name AS std_store,
           pm.standard_name AS std_payment
    FROM numbered n
    LEFT JOIN "dukafresh-dw".ref_store_name_map sm
           ON sm.raw_name = LOWER(TRIM(n.store_name))
    LEFT JOIN "dukafresh-dw".ref_payment_map pm
           ON pm.raw_name = LOWER(TRIM(n.payment_method))
)
SELECT j.*,
       -- The FIRST matching rule wins, so the order below is the priority order.
       CASE
           WHEN j.receipt_id IS NULL OR j.line_no IS NULL
                OR TRIM(j.line_no) !~ '^[0-9]+$'
               THEN 'INVALID_KEY'
           WHEN j.copy_no > 1
               THEN 'DUPLICATE_ROW'
           WHEN j.unit_price IS NULL OR TRIM(j.unit_price) = ''
               THEN 'MISSING_UNIT_PRICE'
           WHEN TRIM(j.unit_price) !~ '^[0-9]+(\.[0-9]+)?$'
               THEN 'INVALID_UNIT_PRICE'
           WHEN j.quantity IS NULL OR TRIM(j.quantity) !~ '^-?[0-9]+$'
               THEN 'INVALID_QUANTITY'
           WHEN TRIM(j.quantity)::int <= 0
               THEN 'NON_POSITIVE_QUANTITY'
           WHEN j.std_store IS NULL
               THEN 'UNKNOWN_STORE'
           WHEN j.std_payment IS NULL
               THEN 'UNKNOWN_PAYMENT_METHOD'
           WHEN j.sale_date IS NULL
                OR (TRIM(j.sale_date) !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                    AND TRIM(j.sale_date) !~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$')
               THEN 'INVALID_DATE'
           WHEN j.product_id IS NULL OR TRIM(j.product_id) !~ '^[0-9]+$'
               THEN 'INVALID_PRODUCT_ID'
           WHEN j.discount IS NOT NULL AND TRIM(j.discount) <> ''
                AND TRIM(j.discount) !~ '^[0-9]+(\.[0-9]+)?$'
               THEN 'INVALID_DISCOUNT'
           WHEN j.customer_id IS NOT NULL AND TRIM(j.customer_id) <> ''
                AND TRIM(j.customer_id) !~ '^[0-9]+$'
               THEN 'INVALID_CUSTOMER_ID'
           ELSE NULL      -- NULL means: no problem found, the row is good
       END AS reject_reason
FROM joined j;

-- 1) Rejected rows keep their ORIGINAL text, plus the reason they failed.
INSERT INTO "dukafresh-dw".rejected_sales
    (receipt_id, line_no, sale_date, store_name, product_id, quantity,
     unit_price, discount, customer_id, payment_method, source_file, reject_reason)
SELECT receipt_id, line_no, sale_date, store_name, product_id, quantity,
       unit_price, discount, customer_id, payment_method, source_file, reject_reason
FROM checked
WHERE reject_reason IS NOT NULL;

-- 2) Good rows are converted from text into proper types and standard names.
INSERT INTO "dukafresh-dw".clean_sales
    (receipt_id, line_no, sale_date, store_name, product_id, quantity,
     unit_price, discount, customer_id, payment_method, source_file)
SELECT receipt_id,
       TRIM(line_no)::int,
       CASE WHEN TRIM(sale_date) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
            THEN TRIM(sale_date)::date                    -- already YYYY-MM-DD
            ELSE to_date(TRIM(sale_date), 'DD/MM/YYYY')   -- day/month/year -> real date
       END,
       std_store,                                         -- standardised store name
       TRIM(product_id)::int,
       TRIM(quantity)::int,
       TRIM(unit_price)::numeric,
       COALESCE(NULLIF(TRIM(discount), ''), '0')::numeric, -- empty discount means 0
       NULLIF(TRIM(customer_id), '')::int,                 -- empty stays NULL (walk-in)
       std_payment,                                        -- standardised payment name
       source_file
FROM checked
WHERE reject_reason IS NULL;