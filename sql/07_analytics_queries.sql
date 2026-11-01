-- 07_analytics_queries.sql
-- PURPOSE: answer the business questions using the star schema.
-- HOW TO USE: in DBeaver (connection "postgres 2"), run the SET line first, then
-- click inside ONE query and press Ctrl + Enter to run just that query.
-- This file is NOT part of the pipeline; it is a reference of questions and answers.
-- DATA: synthetic. The results illustrate the method, not a real business.

SET search_path TO "dukafresh-dw", public;   -- lets us write table names without the schema


-- ======================================================================
-- Q1. Total sales and gross profit by store and month
-- Gross profit = sales amount - (cost price x quantity)
-- Skills: joins across a star schema, GROUP BY
-- ======================================================================
SELECT s.store_name,
       d.month,
       SUM(f.total_amount)                              AS total_sales,
       SUM(f.total_amount - p.cost_price * f.quantity)  AS gross_profit
FROM fact_sales f
JOIN dim_store   s ON s.store_key   = f.store_key
JOIN dim_date    d ON d.date_key    = f.date_key
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY s.store_name, d.month
ORDER BY s.store_name, d.month;


-- ======================================================================
-- Q2. Top 10 products by revenue, with their gross profit
-- Skills: GROUP BY, ORDER BY, LIMIT
-- ======================================================================
SELECT p.product_name,
       p.category,
       SUM(f.quantity)                                  AS units_sold,
       SUM(f.total_amount)                              AS revenue,
       SUM(f.total_amount - p.cost_price * f.quantity)  AS gross_profit
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.product_name, p.category
ORDER BY revenue DESC
LIMIT 10;


-- ======================================================================
-- Q2b. Top 3 products INSIDE each category (window function RANK)
-- A window function ranks rows within a group without collapsing them.
-- PARTITION BY = "restart the ranking for each category".
-- ======================================================================
WITH product_sales AS (
    SELECT p.category, p.product_name, SUM(f.total_amount) AS revenue
    FROM fact_sales f
    JOIN dim_product p ON p.product_key = f.product_key
    GROUP BY p.category, p.product_name
),
ranked AS (
    SELECT category, product_name, revenue,
           RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS rank_in_category
    FROM product_sales
)
SELECT * FROM ranked
WHERE rank_in_category <= 3
ORDER BY category, rank_in_category;


-- ======================================================================
-- Q3. Which categories are growing or declining month over month?
-- LAG() looks at the previous row, so we can compare a month with the month before.
-- NULLIF avoids dividing by zero. The first month has no previous month, so NULL.
-- ======================================================================
WITH monthly AS (
    SELECT p.category, d.year, d.month, SUM(f.total_amount) AS sales
    FROM fact_sales f
    JOIN dim_product p ON p.product_key = f.product_key
    JOIN dim_date    d ON d.date_key    = f.date_key
    GROUP BY p.category, d.year, d.month
)
SELECT category, year, month, sales,
       LAG(sales) OVER (PARTITION BY category ORDER BY year, month) AS previous_month_sales,
       ROUND(100.0 * (sales - LAG(sales) OVER (PARTITION BY category ORDER BY year, month))
             / NULLIF(LAG(sales) OVER (PARTITION BY category ORDER BY year, month), 0), 1)
           AS change_pct
FROM monthly
ORDER BY category, year, month;


-- ======================================================================
-- Q4. Weekday vs weekend sales
-- A fair comparison uses the AVERAGE PER DAY, because a week has 5 weekdays
-- but only 2 weekend days. Comparing totals would favour weekdays unfairly.
-- ======================================================================
WITH daily AS (
    SELECT d.full_date, d.is_weekend, SUM(f.total_amount) AS day_sales
    FROM fact_sales f
    JOIN dim_date d ON d.date_key = f.date_key
    GROUP BY d.full_date, d.is_weekend
)
SELECT CASE WHEN is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
       COUNT(*)                     AS days,
       ROUND(AVG(day_sales), 2)     AS avg_sales_per_day
FROM daily
GROUP BY is_weekend
ORDER BY day_type;


-- ======================================================================
-- Q6. Average transaction value by store
-- A "transaction" is one receipt, so we first total each receipt (a CTE),
-- then average those totals per store. This is why fact_sales keeps receipt_id.
-- ======================================================================
WITH receipts AS (
    SELECT f.store_key, f.receipt_id, SUM(f.total_amount) AS receipt_total
    FROM fact_sales f
    GROUP BY f.store_key, f.receipt_id
)
SELECT s.store_name,
       COUNT(*)                        AS receipts,
       ROUND(AVG(r.receipt_total), 2)  AS avg_transaction_value
FROM receipts r
JOIN dim_store s ON s.store_key = r.store_key
GROUP BY s.store_name
ORDER BY avg_transaction_value DESC;


-- ======================================================================
-- Q7. Payment mix: share of receipts by M-Pesa, Cash and Card
-- SUM(...) OVER () is a window over ALL rows: it gives the grand total,
-- so each row can be shown as a share of the whole.
-- ======================================================================
SELECT pm.method_name,
       COUNT(DISTINCT f.receipt_id)  AS receipts,
       SUM(f.total_amount)           AS sales,
       ROUND(100.0 * COUNT(DISTINCT f.receipt_id)
             / SUM(COUNT(DISTINCT f.receipt_id)) OVER (), 1) AS share_of_receipts_pct
FROM fact_sales f
JOIN dim_payment_method pm ON pm.payment_key = f.payment_key
GROUP BY pm.method_name
ORDER BY receipts DESC;


-- ======================================================================
-- Q9. Where do discounts cost the most? (by category)
-- LIMITATION: the data has no returns (negative quantities were rejected as
-- errors), so this answers the discount half of the question only.
-- ======================================================================
SELECT p.category,
       SUM(f.quantity * f.unit_price)                             AS sales_before_discount,
       SUM(f.discount)                                            AS discount_given,
       ROUND(100.0 * SUM(f.discount) / SUM(f.quantity * f.unit_price), 2) AS discount_share_pct,
       SUM(f.total_amount - p.cost_price * f.quantity)            AS gross_profit
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.category
ORDER BY discount_given DESC;


-- ======================================================================
-- Q10. Repeat customers: top 10 by spend
-- customer_key 0 is the "walk-in" placeholder, so we exclude it.
-- NOTE: this synthetic data assigns customers at random, so almost everyone is a
-- repeat customer. With real data this query would show real loyalty patterns.
-- ======================================================================
SELECT c.customer_name,
       COUNT(DISTINCT f.receipt_id)  AS visits,
       SUM(f.total_amount)           AS total_spend
FROM fact_sales f
JOIN dim_customer c ON c.customer_key = f.customer_key
WHERE f.customer_key <> 0
GROUP BY c.customer_name, f.customer_key
ORDER BY total_spend DESC
LIMIT 10;


-- ======================================================================
-- OLAP EXTENSIONS: SUBTOTALS INSIDE ONE QUERY
-- GROUPING(col) returns 1 on a subtotal row where that column was rolled up,
-- which lets us print a readable label instead of an empty NULL.
-- ======================================================================

-- ROLLUP: subtotals going UP a hierarchy: store -> region -> grand total.
SELECT CASE WHEN GROUPING(s.region) = 1     THEN 'ALL REGIONS' ELSE s.region     END AS region,
       CASE WHEN GROUPING(s.store_name) = 1 THEN 'All stores'  ELSE s.store_name END AS store,
       SUM(f.total_amount) AS total_sales
FROM fact_sales f
JOIN dim_store s ON s.store_key = f.store_key
GROUP BY ROLLUP (s.region, s.store_name)
ORDER BY GROUPING(s.region), s.region, GROUPING(s.store_name), s.store_name;


-- CUBE: subtotals for EVERY combination of category and payment method.
SELECT CASE WHEN GROUPING(p.category) = 1       THEN 'All categories' ELSE p.category       END AS category,
       CASE WHEN GROUPING(pm.method_name) = 1   THEN 'All methods'    ELSE pm.method_name   END AS payment_method,
       SUM(f.total_amount) AS total_sales
FROM fact_sales f
JOIN dim_product        p  ON p.product_key  = f.product_key
JOIN dim_payment_method pm ON pm.payment_key = f.payment_key
GROUP BY CUBE (p.category, pm.method_name)
ORDER BY GROUPING(p.category), p.category, GROUPING(pm.method_name), pm.method_name;


-- GROUPING SETS: YOU choose exactly which groupings you want in one result:
-- sales by region, sales by category, and the grand total (the empty brackets).
SELECT CASE WHEN GROUPING(s.region) = 1   THEN 'All regions'    ELSE s.region   END AS region,
       CASE WHEN GROUPING(p.category) = 1 THEN 'All categories' ELSE p.category END AS category,
       SUM(f.total_amount) AS total_sales
FROM fact_sales f
JOIN dim_store   s ON s.store_key   = f.store_key
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY GROUPING SETS ((s.region), (p.category), ())
ORDER BY GROUPING(s.region), s.region, GROUPING(p.category), p.category;