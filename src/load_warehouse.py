"""load_warehouse.py

PIPELINE STEP 5D: load the star schema from the clean data.

What this script does:
  1. Empties all six warehouse tables (so reruns never create duplicates).
  2. Loads dim_store, dim_product, dim_customer, dim_payment_method from the
     reference CSV files, plus an "unknown member" for walk-in customers.
  3. Runs 06_load_dim_date_and_fact.sql (builds dim_date and fact_sales).
  4. Checks the result against the clean data:
        - fact rows = clean rows        (nothing silently dropped by a join)
        - total sales match to the cent (the money adds up)

Everything runs in ONE transaction: if any check fails, nothing is saved.
"""
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from db import SCHEMA, get_engine

RAW = Path("data/raw")
SQL_FILE = Path("sql/06_load_dim_date_and_fact.sql")

# All six tables in ONE statement: the database refuses to empty a table that other
# tables point to, unless every related table is emptied together.
TRUNCATE_ALL = (
    f'TRUNCATE TABLE "{SCHEMA}".fact_sales, "{SCHEMA}".dim_date, "{SCHEMA}".dim_store, '
    f'"{SCHEMA}".dim_product, "{SCHEMA}".dim_customer, "{SCHEMA}".dim_payment_method'
)


def load_dimensions(conn):
    """Load the four dimensions that come from the reference CSV files."""
    # --- stores: store_id becomes store_key ---
    stores = pd.read_csv(RAW / "stores.csv").rename(columns={"store_id": "store_key"})
    stores.to_sql("dim_store", conn, schema=SCHEMA, if_exists="append", index=False)

    # --- products: keep only the descriptive columns plus cost price.
    #     (The selling price lives in fact_sales because it can change per sale.)
    products = pd.read_csv(RAW / "products.csv").rename(columns={"product_id": "product_key"})
    products = products[["product_key", "product_name", "category", "cost_price"]]
    products.to_sql("dim_product", conn, schema=SCHEMA, if_exists="append", index=False)

    # --- customers, plus the "unknown member" (key 0) for walk-in shoppers ---
    customers = pd.read_csv(RAW / "customers.csv").rename(columns={"customer_id": "customer_key"})
    customers["join_date"] = pd.to_datetime(customers["join_date"]).dt.date
    walk_in = pd.DataFrame(
        [{"customer_key": 0, "customer_name": "Walk-in customer", "join_date": None}]
    )
    pd.concat([walk_in, customers], ignore_index=True).to_sql(
        "dim_customer", conn, schema=SCHEMA, if_exists="append", index=False
    )

    # --- payment methods ---
    pay = pd.read_csv(RAW / "payment_methods.csv").rename(columns={"payment_id": "payment_key"})
    pay.to_sql("dim_payment_method", conn, schema=SCHEMA, if_exists="append", index=False)


def scalar(conn, sql):
    """Run a query that returns one value and give that value back."""
    return conn.execute(text(sql)).scalar()


def load_warehouse():
    engine = get_engine()

    with engine.begin() as conn:  # one transaction: all or nothing
        print("Emptying warehouse tables ...")
        conn.execute(text(TRUNCATE_ALL))

        print("Loading dimensions from reference files ...")
        load_dimensions(conn)

        print(f"Running {SQL_FILE.name} ...")
        conn.exec_driver_sql(SQL_FILE.read_text(encoding="utf-8"))

        # ---------- CHECKS ----------
        clean_rows = scalar(conn, f'SELECT count(*) FROM "{SCHEMA}".clean_sales')
        fact_rows = scalar(conn, f'SELECT count(*) FROM "{SCHEMA}".fact_sales')
        print(f"\nClean rows: {clean_rows:,} | Fact rows: {fact_rows:,}")
        if clean_rows != fact_rows:
            raise ValueError("Some clean rows did not reach fact_sales (a join dropped them)")

        clean_total = scalar(
            conn, f'SELECT SUM(quantity * unit_price - discount) FROM "{SCHEMA}".clean_sales'
        )
        fact_total = scalar(conn, f'SELECT SUM(total_amount) FROM "{SCHEMA}".fact_sales')
        print(f"Clean total: KES {clean_total:,.2f} | Fact total: KES {fact_total:,.2f}")
        if clean_total != fact_total:
            raise ValueError("Sales totals do not match between clean_sales and fact_sales")

        print("\nRow counts per table:")
        for table in ["dim_date", "dim_store", "dim_product", "dim_customer",
                      "dim_payment_method", "fact_sales"]:
            n = scalar(conn, f'SELECT count(*) FROM "{SCHEMA}".{table}')
            print(f"  {table:<20}{n:>10,}")

    print("\nWarehouse loaded. All checks passed.")


if __name__ == "__main__":
    load_warehouse()