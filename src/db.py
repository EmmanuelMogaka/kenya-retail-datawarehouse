"""db.py - the ONE place that knows how to log in to the database.

Every other script imports get_engine() from here, so if the password or
the server ever changes, we only fix it in one file ("don't repeat yourself").
"""
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text

# Read the settings from the private .env file (kept off GitHub).
load_dotenv()

# Our warehouse tables live in this schema (a folder inside the database).
# The name has a hyphen, so we must wrap it in double quotes in SQL.
# Other scripts import this name, which is why load_staging.py needed it.
SCHEMA = os.environ.get("DB_SCHEMA", "dukafresh-dw")


def get_engine():
    """Return an 'engine': the object SQLAlchemy uses to talk to PostgreSQL."""
    user = os.environ["DB_USER"]
    # quote_plus makes special characters in a password safe to put in a web-style address
    password = quote_plus(os.environ["DB_PASSWORD"])
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ["DB_NAME"]

    # The connection address has the same shape as a web address:
    # postgresql+psycopg2://user:password@host:port/database
    engine = create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    )

    # Every time a new connection opens, tell PostgreSQL to look in our schema
    # first. This is what lets us write "stg_sales_raw" instead of the long form.
    @event.listens_for(engine, "connect")
    def set_schema(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f'SET search_path TO "{SCHEMA}", public')
        cursor.close()
        dbapi_connection.commit()

    return engine


# This block only runs when you run db.py directly (a quick self-test),
# not when another file imports it.
if __name__ == "__main__":
    with get_engine().connect() as conn:
        row = conn.execute(
            text("select current_database(), current_schema()")
        ).one()
        print("Connected to database:", row[0], "| schema:", row[1])