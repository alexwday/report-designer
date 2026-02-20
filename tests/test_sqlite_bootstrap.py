from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

import src.db as db
from src.workspace.generation_presets import (
    get_template_generation_preset,
    save_template_generation_preset,
)


class SQLiteBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._original_backend = db.DB_BACKEND
        self._original_sqlite_path = db.SQLITE_DB_PATH
        self._original_init_done = db._SQLITE_INIT_DONE

        db.DB_BACKEND = "sqlite"
        db.SQLITE_DB_PATH = Path(self._tmpdir.name) / "report_designer.db"
        db._SQLITE_INIT_DONE = False

        seed_payload = db._load_system_seed_template_payload()
        if seed_payload is None:
            raise RuntimeError("system seed template payload is required for sqlite bootstrap tests")
        self._seed_payload = seed_payload
        self._seed_name = str(seed_payload["template"]["name"])
        self._seed_section_count = len(seed_payload["sections"])
        self._seed_json_subsection_count = sum(
            1
            for section in seed_payload["sections"]
            for subsection in section.get("subsections", [])
            if subsection.get("content_type") == "json"
        )

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

            cur.execute(
                """
                SELECT id, name, status
                FROM templates
                WHERE name = ?
                """,
                (self._seed_name,),
            )
            template_row = cur.fetchone()
            self.assertIsNotNone(template_row)
            self.assertEqual(template_row[1], self._seed_name)

            template_id = template_row[0]
            cur.execute(
                """
                SELECT COUNT(*)
                FROM sections
                WHERE template_id = ?
                """,
                (template_id,),
            )
            self.assertEqual(cur.fetchone()[0], self._seed_section_count)

            cur.execute(
                """
                SELECT COUNT(*)
                FROM subsections sub
                JOIN sections sec ON sec.id = sub.section_id
                WHERE sec.template_id = ? AND sub.content_type = 'json'
                """,
                (template_id,),
            )
            self.assertEqual(cur.fetchone()[0], self._seed_json_subsection_count)
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

    def test_demo_template_seed_is_idempotent(self):
        db.initialize_database(force=True)
        db.initialize_database(force=True)

        conn = sqlite3.connect(str(db.SQLITE_DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(*)
                FROM templates
                WHERE name = ?
                """,
                (self._seed_name,),
            )
            self.assertEqual(cur.fetchone()[0], 1)

            cur.execute(
                """
                SELECT COUNT(*)
                FROM sections sec
                JOIN templates t ON t.id = sec.template_id
                WHERE t.name = ?
                """,
                (self._seed_name,),
            )
            self.assertEqual(cur.fetchone()[0], self._seed_section_count)
        finally:
            conn.close()

    def test_generation_presets_table_creation_works_in_sqlite(self):
        db.initialize_database(force=True)

        conn = sqlite3.connect(str(db.SQLITE_DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM templates ORDER BY created_at DESC LIMIT 1")
            template_id = cur.fetchone()[0]
        finally:
            conn.close()

        preset = get_template_generation_preset(template_id)
        self.assertEqual(preset["template_id"], template_id)
        self.assertEqual(preset["run_inputs"], {})

        saved = save_template_generation_preset(
            template_id,
            {"fiscal_year": 2025, "fiscal_quarter": "Q1"},
        )
        self.assertEqual(saved["template_id"], template_id)
        self.assertEqual(saved["run_inputs"]["fiscal_year"], 2025)

    def test_demo_template_is_upgraded_when_outdated(self):
        db.initialize_database(force=True)

        conn = sqlite3.connect(str(db.SQLITE_DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id
                FROM templates
                WHERE name = ?
                """,
                (self._seed_name,),
            )
            template_id = cur.fetchone()[0]

            # Simulate an older seed state with only one section.
            cur.execute("DELETE FROM sections WHERE template_id = ?", (template_id,))
            cur.execute(
                """
                INSERT INTO sections (id, template_id, title, position)
                VALUES (?, ?, ?, ?)
                """,
                (str(uuid4()), template_id, "Legacy Section", 1),
            )
            conn.commit()
        finally:
            conn.close()

        db.initialize_database(force=True)

        conn = sqlite3.connect(str(db.SQLITE_DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sections WHERE template_id = ?", (template_id,))
            self.assertEqual(cur.fetchone()[0], self._seed_section_count)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
