from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

import src.db as db


class SQLiteBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._original_backend = db.DB_BACKEND
        self._original_sqlite_path = db.SQLITE_DB_PATH
        self._original_init_done = db._SQLITE_INIT_DONE

        db.DB_BACKEND = "sqlite"
        db.SQLITE_DB_PATH = Path(self._tmpdir.name) / "report_designer.db"
        db._SQLITE_INIT_DONE = False

    def tearDown(self) -> None:
        db.DB_BACKEND = self._original_backend
        db.SQLITE_DB_PATH = self._original_sqlite_path
        db._SQLITE_INIT_DONE = self._original_init_done
        self._tmpdir.cleanup()

    def test_initialize_database_creates_and_seeds_sqlite(self):
        db.initialize_database(force=True)

        conn = sqlite3.connect(str(db.SQLITE_DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM transcripts")
            self.assertGreater(cur.fetchone()[0], 0)

            cur.execute("SELECT COUNT(*) FROM financials")
            self.assertGreater(cur.fetchone()[0], 0)

            cur.execute("SELECT COUNT(*) FROM stock_prices")
            self.assertGreater(cur.fetchone()[0], 0)

            cur.execute("SELECT COUNT(*) FROM data_source_registry")
            self.assertGreater(cur.fetchone()[0], 0)
        finally:
            conn.close()

    def test_sqlite_connection_accepts_postgres_style_placeholders(self):
        db.initialize_database(force=True)

        conn = db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM transcripts
                    WHERE bank_id = %s
                    """,
                    ("RY",),
                )
                count = cur.fetchone()[0]
            self.assertGreater(count, 0)
        finally:
            conn.close()

    def test_ensure_column_is_idempotent_for_sqlite(self):
        db.initialize_database(force=True)
        conn = db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE TABLE IF NOT EXISTS __column_test (id TEXT PRIMARY KEY)")
                db.ensure_column(cur, "__column_test", "new_col", "TEXT")
                db.ensure_column(cur, "__column_test", "new_col", "TEXT")
            conn.commit()

            with conn.cursor() as cur:
                cur.execute("PRAGMA table_info(__column_test)")
                columns = [row[1] for row in cur.fetchall()]
            self.assertIn("new_col", columns)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
