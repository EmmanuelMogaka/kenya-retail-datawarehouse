"""clean_sales.py

PIPELINE STEP 5C: validate and clean the staging data.

What this script does:
  1. Runs the SQL files in order (create tables, fill lookup maps, clean the data).
  2. Counts rows and checks:  clean + rejected = staging  (nothing silently lost).
  3. Prints WHY rows were rejected, and shows the generator's planted-problem
     tally so you can compare it with what the pipeline found.

All SQL runs in ONE transaction: if any step fails, nothing is saved.
NOTE: do not put the percent sign in the SQL files. The database driver reads
it as a placeholder marker when it runs a file.
"""
import json
from pathlib import Path

from sqlalchemy import text

from db import SCHEMA, get_engine

# The order matters: tables first, then lookup maps, then the cleaning rules.
SQL_FILES = [
    Path("sql/03_create_clean_and_rejected.sql"),
    Path("sql/04_lookup_maps.sql"),
    Path("sql/05_clean_sales.sql"),
]
PLANTED_FILE = Path("data/raw/planted_issues.json")


def count_rows(conn, table):
    """Return the number of rows in one table of our schema."""
    return conn.execute(text(f'SELECT count(*) FROM "{SCHEMA}".{table}')).scalar()


def clean_sales():
    engine = get_engine()

    with engine.begin() as conn:  # one transaction: all or nothing
        for sql_file in SQL_FILES:
            print(f"Running {sql_file.name} ...")
            conn.exec_driver_sql(sql_file.read_text(encoding="utf-8"))

        staging = count_rows(conn, "stg_sales_raw")
        clean = count_rows(conn, "clean_sales")
        rejected = count_rows(conn, "rejected_sales")

        print(f"\nStaging rows:  {staging:,}")
        print(f"Clean rows:    {clean:,}")
        print(f"Rejected rows: {rejected:,}")

        # RECONCILIATION: every staging row must end up in exactly one place.
        if clean + rejected != staging:
            raise ValueError(
                f"Rows lost or duplicated: {clean:,} + {rejected:,} != {staging:,}"
            )
        print("Reconciliation OK: clean + rejected = staging")

        reasons = conn.execute(
            text(
                f'SELECT reject_reason, count(*) FROM "{SCHEMA}".rejected_sales '
                "GROUP BY reject_reason ORDER BY 2 DESC"
            )
        ).all()
        print("\nRejected rows by reason:")
        for reason, n in reasons:
            print(f"  {reason:<26}{n:>8,}")

    # Compare with what the generator says it planted.
    if PLANTED_FILE.exists():
        planted = json.loads(PLANTED_FILE.read_text())
        print("\nProblems the generator planted (for comparison):")
        for name, n in planted.items():
            print(f"  {name:<26}{n:>8,}")


if __name__ == "__main__":
    clean_sales()