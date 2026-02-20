"""
Template version management for Report Designer.

Provides snapshot/restore functionality for templates, enabling
users to save versions and revert to previous states.
"""

import json
import uuid
from ..db import ensure_column, get_connection


def _ensure_template_formatting_columns(cur) -> None:
    """Add template formatting column for backward-compatible upgrades."""
    ensure_column(cur, "templates", "formatting_profile", "JSON NOT NULL DEFAULT '{}'")


def _coerce_profile_value(raw_value) -> dict:
    """Parse formatting_profile values loaded from DB/json snapshots."""
    if isinstance(raw_value, dict):
        return raw_value
    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, dict):
                return parsed
        except (TypeError, ValueError):
            pass
    return {}


def _create_snapshot(template_id: str, conn) -> dict:
    """
    Create a complete snapshot of a template's current state.

    Captures: template metadata, sections, subsections, and current version content.
    """
    with conn.cursor() as cur:
        _ensure_template_formatting_columns(cur)
        # Get template metadata
        cur.execute("""
            SELECT name, description, output_format, orientation, status, formatting_profile
            FROM templates WHERE id = %s
        """, (template_id,))
        template_row = cur.fetchone()
        if not template_row:
            return None

        formatting_profile = template_row[5]
        if isinstance(formatting_profile, str):
            try:
                formatting_profile = json.loads(formatting_profile)
            except (TypeError, ValueError):
                formatting_profile = {}

        # Get sections with subsections
        cur.execute("""
            SELECT s.id, s.position, s.title,
                   sub.id as sub_id, sub.title as sub_title, sub.position as sub_position,
                   sub.widget_type, sub.data_source_config,
                   sub.notes, sub.instructions, sub.content, sub.content_type, sub.version_number
            FROM sections s
            LEFT JOIN subsections sub ON sub.section_id = s.id
            WHERE s.template_id = %s
            ORDER BY s.position, sub.position
        """, (template_id,))

        sections = {}
        for row in cur.fetchall():
            section_id = str(row[0])
            if section_id not in sections:
                sections[section_id] = {
                    "id": section_id,
                    "position": row[1],
                    "title": row[2],
                    "subsections": []
                }

            if row[3]:  # Has subsection
                sections[section_id]["subsections"].append({
                    "id": str(row[3]),
                    "title": row[4],
                    "position": row[5],
                    "widget_type": row[6],
                    "data_source_config": row[7],
                    "notes": row[8],
                    "instructions": row[9],
                    "content": row[10],
                    "content_type": row[11],
                    "version_number": row[12],
                })

        return {
            "template": {
                "name": template_row[0],
                "description": template_row[1],
                "output_format": template_row[2],
                "orientation": template_row[3],
                "status": template_row[4],
                "formatting_profile": formatting_profile,
            },
            "sections": list(sections.values()),
        }


def create_version(
    template_id: str,
    name: str = None,
    created_by: str = None,
) -> dict:
    """
    Create a new version snapshot of a template.

    Args:
        template_id: UUID of the template
        name: Optional version name/label
        created_by: User identifier

    Returns:
        Created version metadata
    """
    conn = get_connection()
    try:
        # Get next version number
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(MAX(version_number), 0) + 1
                FROM template_versions
                WHERE template_id = %s
            """, (template_id,))
            version_number = cur.fetchone()[0]

        # Create snapshot
        snapshot = _create_snapshot(template_id, conn)
        if snapshot is None:
            return {"error": f"Template not found: {template_id}"}

        # Generate version name if not provided
        if not name:
            name = f"Version {version_number}"

        # Insert version
        version_id = str(uuid.uuid4())
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO template_versions
                (id, template_id, version_number, name, description, snapshot, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, version_number, name, created_at
            """, (
                version_id,
                template_id,
                version_number,
                name,
                snapshot["template"].get("description"),
                json.dumps(snapshot),
                created_by,
            ))

            row = cur.fetchone()
            conn.commit()

            return {
                "id": str(row[0]),
                "template_id": template_id,
                "version_number": row[1],
                "name": row[2],
                "created_at": str(row[3]) if row[3] else None,
            }
    finally:
        conn.close()


def list_versions(template_id: str, limit: int = 20) -> list[dict]:
    """
    List version history for a template.

    Args:
        template_id: UUID of the template
        limit: Max results

    Returns:
        List of version summaries
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, version_number, name, created_by, created_at
                FROM template_versions
                WHERE template_id = %s
                ORDER BY version_number DESC
                LIMIT %s
            """, (template_id, limit))

            return [
                {
                    "id": str(row[0]),
                    "template_id": template_id,
                    "version_number": row[1],
                    "name": row[2],
                    "created_by": row[3],
                    "created_at": str(row[4]) if row[4] else None,
                }
                for row in cur.fetchall()
            ]
    finally:
        conn.close()


def get_version(version_id: str) -> dict:
    """
    Get a specific version with full snapshot.

    Args:
        version_id: UUID of the version

    Returns:
        Version metadata and snapshot
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, template_id, version_number, name, snapshot, created_by, created_at
                FROM template_versions
                WHERE id = %s
            """, (version_id,))

            row = cur.fetchone()
            if not row:
                return {"error": f"Version not found: {version_id}"}

            return {
                "id": str(row[0]),
                "template_id": str(row[1]),
                "version_number": row[2],
                "name": row[3],
                "snapshot": row[4],
                "created_by": row[5],
                "created_at": str(row[6]) if row[6] else None,
            }
    finally:
        conn.close()


def restore_version(template_id: str, version_id: str) -> dict:
    """
    Restore a template to a previous version state.

    This creates a new auto-save version of the current state before restoring,
    then applies the snapshot from the specified version.

    Args:
        template_id: UUID of the template
        version_id: UUID of the version to restore

    Returns:
        Restoration result
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _ensure_template_formatting_columns(cur)
            conn.commit()

        # Get the version to restore
        with conn.cursor() as cur:
            cur.execute("""
                SELECT snapshot FROM template_versions
                WHERE id = %s AND template_id = %s
            """, (version_id, template_id))

            row = cur.fetchone()
            if not row:
                return {"error": "Version not found or doesn't belong to this template"}

            snapshot = row[0]

        # Create auto-save of current state before restoring
        create_version(template_id, name="Auto-save before restore", created_by="system")

        # Now restore from snapshot
        with conn.cursor() as cur:
            # Update template metadata
            template_data = snapshot["template"]
            cur.execute("""
                UPDATE templates
                SET name = %s, description = %s, output_format = %s,
                    orientation = %s, formatting_profile = %s, updated_at = NOW()
                WHERE id = %s
            """, (
                template_data["name"],
                template_data.get("description"),
                template_data["output_format"],
                template_data.get("orientation"),
                json.dumps(_coerce_profile_value(template_data.get("formatting_profile"))),
                template_id,
            ))

            # Delete existing sections (cascades to subsections)
            cur.execute("DELETE FROM sections WHERE template_id = %s", (template_id,))

            # Recreate sections and subsections from snapshot
            for section in snapshot["sections"]:
                section_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO sections (id, template_id, position, title)
                    VALUES (%s, %s, %s, %s)
                """, (
                    section_id,
                    template_id,
                    section["position"],
                    section.get("title"),
                ))

                for subsection in section.get("subsections", []):
                    subsection_id = str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO subsections
                        (id, section_id, title, position, widget_type, data_source_config,
                         notes, instructions, content, content_type, version_number)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        subsection_id,
                        section_id,
                        subsection.get("title"),
                        subsection.get("position", 1),
                        subsection.get("widget_type"),
                        json.dumps(subsection["data_source_config"]) if subsection.get("data_source_config") else None,
                        subsection.get("notes"),
                        subsection.get("instructions"),
                        subsection.get("content"),
                        subsection.get("content_type"),
                        subsection.get("version_number", 0),
                    ))

            conn.commit()

            return {
                "success": True,
                "template_id": template_id,
                "restored_from": version_id,
                "sections_restored": len(snapshot["sections"]),
            }
    finally:
        conn.close()


def fork_template(
    template_id: str,
    new_name: str,
    created_by: str,
) -> dict:
    """
    Create a copy of a template with all its content.

    Args:
        template_id: UUID of the source template
        new_name: Name for the forked template
        created_by: User identifier

    Returns:
        Created template metadata
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _ensure_template_formatting_columns(cur)
            conn.commit()

        # Get current snapshot
        snapshot = _create_snapshot(template_id, conn)
        if snapshot is None:
            return {"error": f"Template not found: {template_id}"}

        # Create new template
        new_template_id = str(uuid.uuid4())
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO templates
                (id, name, description, created_by, output_format, orientation, status, formatting_profile)
                VALUES (%s, %s, %s, %s, %s, %s, 'draft', %s)
                RETURNING id, name, description, created_by, output_format, orientation, status,
                          created_at, formatting_profile
            """, (
                new_template_id,
                new_name,
                snapshot["template"].get("description"),
                created_by,
                snapshot["template"]["output_format"],
                snapshot["template"].get("orientation"),
                json.dumps(snapshot["template"].get("formatting_profile") or {}),
            ))

            template_row = cur.fetchone()

            # Create sections and subsections
            for section in snapshot["sections"]:
                section_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO sections (id, template_id, position, title)
                    VALUES (%s, %s, %s, %s)
                """, (
                    section_id,
                    new_template_id,
                    section["position"],
                    section.get("title"),
                ))

                for subsection in section.get("subsections", []):
                    subsection_id = str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO subsections
                        (id, section_id, title, position, widget_type, data_source_config,
                         notes, instructions, content, content_type, version_number)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        subsection_id,
                        section_id,
                        subsection.get("title"),
                        subsection.get("position", 1),
                        subsection.get("widget_type"),
                        json.dumps(subsection["data_source_config"]) if subsection.get("data_source_config") else None,
                        subsection.get("notes"),
                        subsection.get("instructions"),
                        subsection.get("content"),
                        subsection.get("content_type"),
                        subsection.get("version_number", 0),
                    ))

            conn.commit()

            return {
                "id": str(template_row[0]),
                "name": template_row[1],
                "description": template_row[2],
                "created_by": template_row[3],
                "output_format": template_row[4],
                "orientation": template_row[5],
                "status": template_row[6],
                "created_at": str(template_row[7]) if template_row[7] else None,
                "formatting_profile": _coerce_profile_value(template_row[8]),
                "forked_from": template_id,
            }
    finally:
        conn.close()


def list_shared_templates(limit: int = 50) -> list[dict]:
    """
    List templates that are marked as shared.

    Args:
        limit: Max results

    Returns:
        List of shared template summaries
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, description, created_by, output_format, status, created_at, updated_at
                FROM templates
                WHERE is_shared = TRUE AND status != 'archived'
                ORDER BY updated_at DESC
                LIMIT %s
            """, (limit,))

            return [
                {
                    "id": str(row[0]),
                    "name": row[1],
                    "description": row[2],
                    "created_by": row[3],
                    "output_format": row[4],
                    "status": row[5],
                    "created_at": str(row[6]) if row[6] else None,
                    "updated_at": str(row[7]) if row[7] else None,
                }
                for row in cur.fetchall()
            ]
    finally:
        conn.close()


def set_template_shared(template_id: str, is_shared: bool) -> dict:
    """
    Set a template's shared status.

    Args:
        template_id: UUID of the template
        is_shared: Whether to share the template

    Returns:
        Updated template
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE templates
                SET is_shared = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id, name, is_shared
            """, (is_shared, template_id))

            row = cur.fetchone()
            if not row:
                return {"error": f"Template not found: {template_id}"}

            conn.commit()

            return {
                "id": str(row[0]),
                "name": row[1],
                "is_shared": row[2],
            }
    finally:
        conn.close()
