"""
Database connection utilities for retrievers.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

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


def query(sql: str, params: tuple = None) -> list[dict]:
    """Execute a query and return results as list of dicts."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
