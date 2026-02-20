"""
Template generation preset storage.

Stores last-used initialization inputs so generation setup can be reused
across reporting periods.
"""

from typing import Any

from ..db import get_connection


def _ensure_generation_presets_table(cur) -> None:
    """Ensure generation preset table exists."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS template_generation_presets (
            template_id UUID PRIMARY KEY REFERENCES templates(id) ON DELETE CASCADE,
            run_inputs JSONB NOT NULL DEFAULT '{}'::jsonb,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)


def get_template_generation_preset(template_id: str) -> dict:
    """
    Get saved generation preset (last run inputs) for a template.

    Returns:
        {
            "template_id": str,
            "run_inputs": dict,
            "updated_at": str | None
        }
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _ensure_generation_presets_table(cur)
            cur.execute("""
                SELECT template_id, run_inputs, updated_at
                FROM template_generation_presets
                WHERE template_id = %s
            """, (template_id,))
            row = cur.fetchone()
            conn.commit()

            if not row:
                return {
                    "template_id": template_id,
                    "run_inputs": {},
                    "updated_at": None,
                }

            run_inputs = row[1] if isinstance(row[1], dict) else {}
            return {
                "template_id": str(row[0]),
                "run_inputs": run_inputs,
                "updated_at": str(row[2]) if row[2] else None,
            }
    finally:
        conn.close()


def save_template_generation_preset(template_id: str, run_inputs: dict[str, Any]) -> dict:
    """
    Save (upsert) generation preset for a template.

    Returns:
        {
            "template_id": str,
            "run_inputs": dict,
            "updated_at": str | None
        }
    """
    normalized_inputs = run_inputs if isinstance(run_inputs, dict) else {}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _ensure_generation_presets_table(cur)
            cur.execute("""
                INSERT INTO template_generation_presets (template_id, run_inputs, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (template_id) DO UPDATE SET
                    run_inputs = EXCLUDED.run_inputs,
                    updated_at = NOW()
                RETURNING template_id, run_inputs, updated_at
            """, (template_id, normalized_inputs))
            row = cur.fetchone()
            conn.commit()
            return {
                "template_id": str(row[0]),
                "run_inputs": row[1] if isinstance(row[1], dict) else {},
                "updated_at": str(row[2]) if row[2] else None,
            }
    finally:
        conn.close()
