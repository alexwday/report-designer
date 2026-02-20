"""
Data Ingestion Script

Loads mock data from JSON files into Postgres tables.
Usage: python scripts/database/load_data.py
"""

import json
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

# Paths relative to this script
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = SCRIPT_DIR / "data"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"

# Import metrics config from same directory
from metrics import METRICS

# Database config
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "34532")),
    "dbname": os.getenv("DB_NAME", "report_designer"),
}
if os.getenv("DB_USER"):
    DB_CONFIG["user"] = os.getenv("DB_USER")
if os.getenv("DB_PASSWORD"):
    DB_CONFIG["password"] = os.getenv("DB_PASSWORD")


def get_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG)


def init_schema(conn):
    """Initialize database tables from SQL files."""
    cursor = conn.cursor()

    for sql_file in ["transcripts.sql", "financials.sql", "stock_prices.sql"]:
        filepath = SCHEMAS_DIR / sql_file
        print(f"  Running {sql_file}...")
        with open(filepath, "r") as f:
            cursor.execute(f.read())

    conn.commit()
    cursor.close()
    print("  Schema initialized successfully")


def load_transcripts(conn):
    """Load transcript data from JSON."""
    filepath = DATA_DIR / "transcripts.json"

    with open(filepath, "r") as f:
        data = json.load(f)

    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM transcripts")

    records = []
    for item in data:
        bank_id = item["bank_id"]
        fiscal_year = item["fiscal_year"]
        fiscal_quarter = item["fiscal_quarter"]
        call_date = item["call_date"]

        for section, content in item["sections"].items():
            record_id = f"{bank_id}_{fiscal_year}_{fiscal_quarter}_{section}"
            records.append((
                record_id,
                bank_id,
                fiscal_year,
                fiscal_quarter,
                section,
                content,
                call_date
            ))

    insert_sql = """
        INSERT INTO transcripts (id, bank_id, fiscal_year, fiscal_quarter, section, content_text, call_date)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            content_text = EXCLUDED.content_text,
            call_date = EXCLUDED.call_date
    """

    execute_values(cursor, insert_sql, records)
    conn.commit()
    cursor.close()

    print(f"  Loaded {len(records)} transcript records")


def load_financials(conn):
    """Load financial metrics data from JSON."""
    filepath = DATA_DIR / "financials.json"

    with open(filepath, "r") as f:
        data = json.load(f)

    # Build metric lookup
    metric_lookup = {m["id"]: m for m in METRICS}

    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM financials")

    records = []
    for item in data:
        bank_id = item["bank_id"]
        fiscal_year = item["fiscal_year"]
        fiscal_quarter = item["fiscal_quarter"]

        for metric_id, metric_data in item["metrics"].items():
            metric_def = metric_lookup.get(metric_id, {})
            metric_name = metric_def.get("name", metric_id)
            unit = metric_def.get("unit", "")

            record_id = f"{bank_id}_{fiscal_year}_{fiscal_quarter}_{metric_id}"
            records.append((
                record_id,
                bank_id,
                fiscal_year,
                fiscal_quarter,
                metric_id,
                metric_name,
                metric_data["value"],
                unit,
                metric_data["formatted"]
            ))

    insert_sql = """
        INSERT INTO financials (id, bank_id, fiscal_year, fiscal_quarter, metric_id, metric_name, value, unit, formatted_value)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            metric_name = EXCLUDED.metric_name,
            value = EXCLUDED.value,
            unit = EXCLUDED.unit,
            formatted_value = EXCLUDED.formatted_value
    """

    execute_values(cursor, insert_sql, records)
    conn.commit()
    cursor.close()

    print(f"  Loaded {len(records)} financial metric records")


def load_stock_prices(conn):
    """Load stock price data from JSON."""
    filepath = DATA_DIR / "stock_prices.json"

    with open(filepath, "r") as f:
        data = json.load(f)

    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM stock_prices")

    records = []
    for item in data:
        record_id = f"{item['bank_id']}_{item['fiscal_year']}_{item['fiscal_quarter']}"
        records.append((
            record_id,
            item["bank_id"],
            item["fiscal_year"],
            item["fiscal_quarter"],
            item["close_price"],
            item["qoq_change_pct"],
            item["yoy_change_pct"],
            item["period_end_date"]
        ))

    insert_sql = """
        INSERT INTO stock_prices (id, bank_id, fiscal_year, fiscal_quarter, close_price, qoq_change_pct, yoy_change_pct, period_end_date)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            close_price = EXCLUDED.close_price,
            qoq_change_pct = EXCLUDED.qoq_change_pct,
            yoy_change_pct = EXCLUDED.yoy_change_pct,
            period_end_date = EXCLUDED.period_end_date
    """

    execute_values(cursor, insert_sql, records)
    conn.commit()
    cursor.close()

    print(f"  Loaded {len(records)} stock price records")


def verify_data(conn):
    """Verify data was loaded correctly."""
    cursor = conn.cursor()

    print("\n  Data verification:")

    cursor.execute("SELECT COUNT(*) FROM transcripts")
    count = cursor.fetchone()[0]
    print(f"    transcripts: {count} records")

    cursor.execute("SELECT COUNT(*) FROM financials")
    count = cursor.fetchone()[0]
    print(f"    financials: {count} records")

    cursor.execute("SELECT COUNT(*) FROM stock_prices")
    count = cursor.fetchone()[0]
    print(f"    stock_prices: {count} records")

    # Show period breakdown
    print("\n  Period breakdown:")
    cursor.execute("""
        SELECT fiscal_year, fiscal_quarter, COUNT(DISTINCT bank_id) as banks
        FROM transcripts
        GROUP BY fiscal_year, fiscal_quarter
        ORDER BY fiscal_year, fiscal_quarter
    """)
    for row in cursor.fetchall():
        print(f"    {row[0]} {row[1]}: {row[2]} banks")

    cursor.close()


def main():
    """Run data ingestion pipeline."""
    print("\n=== Report Designer Data Ingestion ===\n")

    print("1. Connecting to database...")
    conn = get_connection()
    print(f"   Connected to {DB_CONFIG['dbname']} at {DB_CONFIG['host']}:{DB_CONFIG['port']}")

    print("\n2. Initializing schema...")
    init_schema(conn)

    print("\n3. Loading transcripts...")
    load_transcripts(conn)

    print("\n4. Loading financials...")
    load_financials(conn)

    print("\n5. Loading stock prices...")
    load_stock_prices(conn)

    print("\n6. Verifying data...")
    verify_data(conn)

    conn.close()
    print("\n=== Ingestion complete ===\n")


if __name__ == "__main__":
    main()
