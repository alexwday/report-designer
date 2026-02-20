"""
Database Configuration

Connection settings for the report_designer Postgres database.
"""

import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "34532")),
    "dbname": os.getenv("DB_NAME", "report_designer"),
    "user": os.getenv("DB_USER", None),
    "password": os.getenv("DB_PASSWORD", None),
}


def get_connection_string() -> str:
    """Get psycopg2 connection string."""
    parts = [
        f"host={DB_CONFIG['host']}",
        f"port={DB_CONFIG['port']}",
        f"dbname={DB_CONFIG['dbname']}"
    ]
    if DB_CONFIG.get("user"):
        parts.append(f"user={DB_CONFIG['user']}")
    if DB_CONFIG.get("password"):
        parts.append(f"password={DB_CONFIG['password']}")
    return " ".join(parts)
