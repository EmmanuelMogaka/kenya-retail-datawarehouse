"""load_staging.

Design rules this script follows:
  1. NO cleaning here. We store the data exactly as received.
  2. Idempotent: running it twice gives the same result (we empty the table first).
  3. All-or-nothing: if anything fails halfway, nothing is saved (a transaction).
  4. Verified: after loading, we count rows to prove nothing was lost.
"""
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from db import SCHEMA, get_engine  

# ---- Settings (kept at the top so they are easy to find and change) ----
RAW_FILE = Path("data/raw/sales_raw.csv")      
STAGING_TABLE = "stg_sales_raw"      
CHUNK_SIZE = 5000            


def load_staging():
    engine = get_engine()

    # 1. READ the file. dtype=str means "keep everything as text".
    #    Without it, pandas would guess types and could silently change values
    #    (for example turning '007' into 7). We want the data exactly as received.
    df = pd.read_csv(RAW_FILE, dtype=str)
    rows_in_file = len(df)
    print(f"Read {rows_in_file:,} rows from {RAW_FILE.name}")

    # 2. TAG every row with the file it came from, so we can trace it later.
    df["source_file"] = RAW_FILE.name

    # 3. LOAD inside a transaction. engine.begin() opens one and saves it only if
    #    every line inside succeeds. If something fails, it is rolled back.
    with engine.begin() as conn:
        # Empty the table first. This is what makes the script idempotent:
        # run it twice and you still get one copy of the data, not two.
        conn.execute(text(f'TRUNCATE TABLE "{SCHEMA}".{STAGING_TABLE}'))

        # Insert the rows. if_exists="append" means "add to the existing table",
        # so pandas will not try to re-create the table we designed ourselves.
        df.to_sql(
            STAGING_TABLE,
            conn,
            schema=SCHEMA,
            if_exists="append",
            index=False,
            chunksize=CHUNK_SIZE,
            method="multi",
        )

        # 4. VERIFY: count what actually landed in the table.
        rows_in_table = conn.execute(
            text(f'SELECT count(*) FROM "{SCHEMA}".{STAGING_TABLE}')
        ).scalar()

        # A row-count check is a basic data quality control. If the numbers
        # differ, raising an error rolls the whole load back.
        if rows_in_table != rows_in_file:
            raise ValueError(
                f"Row count mismatch: file has {rows_in_file}, table has {rows_in_table}"
            )

    print(f"Staging table now holds {rows_in_table:,} rows. Counts match.")


if __name__ == "__main__":
    load_staging()