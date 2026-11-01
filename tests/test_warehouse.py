"""test_warehouse.py - data quality checks on the loaded warehouse.

HOW TO RUN (from the project folder):  python -m pytest -v
NOTE: these are 'integration tests'. They read the REAL database, so the pipeline
must have run first (load_staging, clean_sales, load_warehouse).
Each test follows the same pattern: run a query that counts the BAD things.
The test passes when that count is zero.
"""
import pytest
from sqlalchemy import text

from db import SCHEMA, get_engine


@pytest.fixture(scope="module")
def conn():
    """One database connection shared by all the tests in this file."""
    engine = get_engine()
    with engine.connect() as connection:
        yield connection


def value(conn, sql):
    """Run a query that returns one value and give that value back."""
    return conn.execute(text(sql)).scalar()


def test_every_staging_row_is_accounted_for(conn):
    # Nothing may vanish: staging rows = clean rows + rejected rows.
    staging = value(conn, f'SELECT count(*) FROM "{SCHEMA}".stg_sales_raw')
    clean = value(conn, f'SELECT count(*) FROM "{SCHEMA}".clean_sales')
    rejected = value(conn, f'SELECT count(*) FROM "{SCHEMA}".rejected_sales')
    assert staging == clean + rejected


def test_no_duplicate_receipt_lines_in_clean(conn):
    # A receipt line must appear only once.
    bad = value(conn, f'''
        SELECT count(*) FROM (
            SELECT receipt_id, line_no FROM "{SCHEMA}".clean_sales
            GROUP BY receipt_id, line_no HAVING count(*) > 1
        ) x''')
    assert bad == 0


def test_clean_rows_have_valid_quantity_and_price(conn):
    bad = value(conn, f'''
        SELECT count(*) FROM "{SCHEMA}".clean_sales
        WHERE quantity <= 0 OR unit_price IS NULL OR unit_price <= 0''')
    assert bad == 0


def test_only_five_official_store_names(conn):
    # If a typo slipped through, there would be more than 5 names.
    assert value(conn, f'SELECT count(DISTINCT store_name) FROM "{SCHEMA}".clean_sales') == 5


def test_only_three_payment_methods(conn):
    assert value(conn, f'SELECT count(DISTINCT payment_method) FROM "{SCHEMA}".clean_sales') == 3


def test_fact_rows_equal_clean_rows(conn):
    # A join that quietly drops rows would make these differ.
    clean = value(conn, f'SELECT count(*) FROM "{SCHEMA}".clean_sales')
    fact = value(conn, f'SELECT count(*) FROM "{SCHEMA}".fact_sales')
    assert clean == fact


def test_fact_total_matches_clean_total(conn):
    # The money must add up exactly.
    clean_total = value(conn, f'SELECT SUM(quantity * unit_price - discount) FROM "{SCHEMA}".clean_sales')
    fact_total = value(conn, f'SELECT SUM(total_amount) FROM "{SCHEMA}".fact_sales')
    assert clean_total == fact_total


def test_total_amount_follows_the_formula(conn):
    # total_amount = quantity x unit price - discount, on every row.
    bad = value(conn, f'''
        SELECT count(*) FROM "{SCHEMA}".fact_sales
        WHERE total_amount <> quantity * unit_price - discount''')
    assert bad == 0


def test_discount_never_exceeds_the_line_amount(conn):
    bad = value(conn, f'''
        SELECT count(*) FROM "{SCHEMA}".fact_sales
        WHERE discount > quantity * unit_price OR discount < 0''')
    assert bad == 0


def test_walk_in_customer_row_exists(conn):
    # Customer key 0 stands for walk-in shoppers, so sales without a customer still join.
    assert value(conn, f'SELECT count(*) FROM "{SCHEMA}".dim_customer WHERE customer_key = 0') == 1


def test_every_rejected_row_has_a_reason(conn):
    # LENGTH(TRIM(...)) = 0 catches empty or blank reasons without any tricky quote marks.
    bad = value(conn, f"""
        SELECT count(*) FROM "{SCHEMA}".rejected_sales
        WHERE reject_reason IS NULL OR LENGTH(TRIM(reject_reason)) = 0""")
    assert bad == 0