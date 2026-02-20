"""
Template management tools for Report Designer.

Templates are the core workspace containers that hold sections,
conversations, and all workspace state.
"""

import copy
import json
import uuid
from typing import Any

from ..db import ensure_column, get_connection


THEME_PRESETS: dict[str, dict[str, Any]] = {
    "executive_blue": {
        "theme_name": "Executive Blue",
        "font_family": "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
        "title_font_size_pt": 20,
        "subsection_title_font_size_pt": 13,
        "body_font_size_pt": 11,
        "line_height": 1.6,
        "accent_color": "#1D4ED8",
        "heading_color": "#111827",
        "body_color": "#1F2937",
        "section_title_case": "title",
        "subsection_title_case": "title",
    },
    "modern_slate": {
        "theme_name": "Modern Slate",
        "font_family": "'Avenir Next', 'Segoe UI', Arial, sans-serif",
        "title_font_size_pt": 21,
        "subsection_title_font_size_pt": 13,
        "body_font_size_pt": 11,
        "line_height": 1.55,
        "accent_color": "#0F766E",
        "heading_color": "#0F172A",
        "body_color": "#334155",
        "section_title_case": "sentence",
        "subsection_title_case": "sentence",
    },
    "print_serif": {
        "theme_name": "Print Serif",
        "font_family": "'Georgia', 'Times New Roman', serif",
        "title_font_size_pt": 22,
        "subsection_title_font_size_pt": 14,
        "body_font_size_pt": 11,
        "line_height": 1.65,
        "accent_color": "#9A3412",
        "heading_color": "#1C1917",
        "body_color": "#292524",
        "section_title_case": "title",
        "subsection_title_case": "title",
    },
}

DEFAULT_THEME_ID = "executive_blue"


def get_default_formatting_profile(theme_id: str = DEFAULT_THEME_ID) -> dict[str, Any]:
    """Return a default formatting profile for the requested theme."""
    selected_theme_id = theme_id if theme_id in THEME_PRESETS else DEFAULT_THEME_ID
    preset = copy.deepcopy(THEME_PRESETS[selected_theme_id])
    preset["theme_id"] = selected_theme_id
    return preset


def normalize_formatting_profile(profile: Any) -> dict[str, Any]:
    """Normalize formatting profile payload to a complete, known-safe object."""
    default_profile = get_default_formatting_profile()
    if not isinstance(profile, dict):
        return default_profile

    requested_theme_id = profile.get("theme_id")
    if not isinstance(requested_theme_id, str) or requested_theme_id not in THEME_PRESETS:
        requested_theme_id = DEFAULT_THEME_ID

    base = get_default_formatting_profile(requested_theme_id)
    normalized = {**base, **profile}
    normalized["theme_id"] = requested_theme_id
    normalized["theme_name"] = THEME_PRESETS[requested_theme_id]["theme_name"]
    return normalized


def _coerce_profile_value(raw_value: Any) -> dict[str, Any]:
    """Parse a profile value from DB payloads before normalization."""
    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
            return normalize_formatting_profile(parsed)
        except (TypeError, ValueError):
            return normalize_formatting_profile(None)
    return normalize_formatting_profile(raw_value)


def _ensure_template_formatting_columns(cur) -> None:
    """Add template formatting columns when upgrading an existing database."""
    ensure_column(cur, "templates", "formatting_profile", "JSON NOT NULL DEFAULT '{}'")


def get_template(template_id: str) -> dict:
    """
    Get template overview with metadata and section summary.

    Args:
        template_id: UUID of the template

    Returns:
        Template metadata and section summary
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _ensure_template_formatting_columns(cur)
            conn.commit()
            # Get template metadata
            cur.execute("""
                SELECT id, name, description, created_by, output_format, orientation,
                       status, created_at, updated_at, last_opened_at, formatting_profile
                FROM templates
                WHERE id = %s
            """, (template_id,))
            row = cur.fetchone()

            if not row:
                return {"error": f"Template not found: {template_id}"}

            template = {
                "id": str(row[0]),
                "name": row[1],
                "description": row[2],
                "created_by": row[3],
                "output_format": row[4],
                "orientation": row[5],
                "status": row[6],
                "created_at": str(row[7]) if row[7] else None,
                "updated_at": str(row[8]) if row[8] else None,
                "last_opened_at": str(row[9]) if row[9] else None,
                "formatting_profile": _coerce_profile_value(row[10]),
            }

            # Get section summary with subsection counts
            cur.execute("""
                SELECT s.id, s.position, s.title,
                       COUNT(sub.id) as subsection_count
                FROM sections s
                LEFT JOIN subsections sub ON sub.section_id = s.id
                WHERE s.template_id = %s
                GROUP BY s.id, s.position, s.title
                ORDER BY s.position
            """, (template_id,))
            sections = [
                {
                    "id": str(r[0]),
                    "position": r[1],
                    "title": r[2],
                    "subsection_count": r[3],
                    "subsections": [{"count": r[3]}],  # Keep compatible structure
                }
                for r in cur.fetchall()
            ]

            # Update last_opened_at
            cur.execute("""
                UPDATE templates SET last_opened_at = NOW() WHERE id = %s
            """, (template_id,))
            conn.commit()

            return {
                "template": template,
                "sections_summary": {
                    "count": len(sections),
                    "sections": sections,
                }
            }
    finally:
        conn.close()


def create_template(
    name: str,
    created_by: str,
    description: str = None,
    output_format: str = "pdf",
    orientation: str = "landscape",
    formatting_profile: dict[str, Any] | None = None,
) -> dict:
    """
    Create a new template workspace.

    Args:
        name: Template name
        created_by: User identifier
        description: Optional description
        output_format: 'pdf' or 'ppt'
        orientation: 'landscape' or 'portrait'

    Returns:
        Created template with ID
    """
    template_id = str(uuid.uuid4())
    normalized_profile = normalize_formatting_profile(formatting_profile)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _ensure_template_formatting_columns(cur)
            conn.commit()
            cur.execute("""
                INSERT INTO templates (
                    id, name, description, created_by, output_format, orientation, formatting_profile
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, description, created_by, output_format, orientation,
                          status, created_at, formatting_profile
            """, (
                template_id,
                name,
                description,
                created_by,
                output_format,
                orientation,
                json.dumps(normalized_profile),
            ))

            row = cur.fetchone()
            conn.commit()

            return {
                "id": str(row[0]),
                "name": row[1],
                "description": row[2],
                "created_by": row[3],
                "output_format": row[4],
                "orientation": row[5],
                "status": row[6],
                "created_at": str(row[7]) if row[7] else None,
                "formatting_profile": _coerce_profile_value(row[8]),
            }
    finally:
        conn.close()


def update_template(
    template_id: str,
    name: str = None,
    description: str = None,
    output_format: str = None,
    orientation: str = None,
    status: str = None,
    formatting_profile: dict[str, Any] | None = None,
) -> dict:
    """
    Update template properties.

    Args:
        template_id: UUID of the template
        name: New name (optional)
        description: New description (optional)
        output_format: New format (optional)
        orientation: New orientation (optional)
        status: New status (optional)

    Returns:
        Updated template
    """
    updates = []
    params = []

    if name is not None:
        updates.append("name = %s")
        params.append(name)
    if description is not None:
        updates.append("description = %s")
        params.append(description)
    if output_format is not None:
        updates.append("output_format = %s")
        params.append(output_format)
    if orientation is not None:
        updates.append("orientation = %s")
        params.append(orientation)
    if status is not None:
        updates.append("status = %s")
        params.append(status)
    if formatting_profile is not None:
        updates.append("formatting_profile = %s")
        params.append(json.dumps(normalize_formatting_profile(formatting_profile)))

    if not updates:
        return {"error": "No updates provided"}

    params.append(template_id)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _ensure_template_formatting_columns(cur)
            conn.commit()
            cur.execute(f"""
                UPDATE templates
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING id, name, description, output_format, orientation, status, updated_at,
                          formatting_profile
            """, tuple(params))

            row = cur.fetchone()
            if not row:
                return {"error": f"Template not found: {template_id}"}

            conn.commit()

            return {
                "id": str(row[0]),
                "name": row[1],
                "description": row[2],
                "output_format": row[3],
                "orientation": row[4],
                "status": row[5],
                "updated_at": str(row[6]) if row[6] else None,
                "formatting_profile": _coerce_profile_value(row[7]),
            }
    finally:
        conn.close()


def delete_template(template_id: str) -> dict:
    """
    Delete a template and all its associated data.

    Args:
        template_id: UUID of the template to delete

    Returns:
        Success confirmation or error
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _ensure_template_formatting_columns(cur)
            conn.commit()
            # Check if template exists
            cur.execute("SELECT id FROM templates WHERE id = %s", (template_id,))
            if not cur.fetchone():
                return {"error": f"Template not found: {template_id}"}

            # Delete template (cascades to sections, subsections, etc.)
            cur.execute("DELETE FROM templates WHERE id = %s", (template_id,))
            conn.commit()

            return {"success": True, "deleted_id": template_id}
    finally:
        conn.close()


def list_templates(
    created_by: str = None,
    status: str = None,
    limit: int = 50,
) -> list[dict]:
    """
    List templates with optional filtering.

    Args:
        created_by: Filter by creator (optional)
        status: Filter by status (optional)
        limit: Max results

    Returns:
        List of template summaries
    """
    conditions = []
    params = []

    if created_by:
        conditions.append("created_by = %s")
        params.append(created_by)
    if status:
        conditions.append("status = %s")
        params.append(status)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _ensure_template_formatting_columns(cur)
            conn.commit()
            cur.execute(f"""
                SELECT id, name, description, created_by, output_format, status, created_at, updated_at,
                       formatting_profile
                FROM templates
                {where_clause}
                ORDER BY updated_at DESC
                LIMIT %s
            """, tuple(params))

            return [
                {
                    "id": str(r[0]),
                    "name": r[1],
                    "description": r[2],
                    "created_by": r[3],
                    "output_format": r[4],
                    "status": r[5],
                    "created_at": str(r[6]) if r[6] else None,
                    "updated_at": str(r[7]) if r[7] else None,
                    "formatting_profile": _coerce_profile_value(r[8]),
                }
                for r in cur.fetchall()
            ]
    finally:
        conn.close()


# Tool definitions for MCP server
TOOL_DEFINITIONS = {
    "get_template": {
        "name": "get_template",
        "description": """Get template workspace overview including metadata and section summary.

Returns:
- Template metadata (name, description, format, orientation, status)
- Section count and titles
- Last activity timestamps

Use this to understand the overall workspace structure before diving into specifics.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "string",
                    "description": "Template UUID"
                }
            },
            "required": ["template_id"]
        }
    },
    "create_template": {
        "name": "create_template",
        "description": """Create a new template workspace.

A template is a living workspace that contains sections, conversations,
and all the state needed to generate and regenerate reports.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Template name"
                },
                "created_by": {
                    "type": "string",
                    "description": "User identifier"
                },
                "description": {
                    "type": "string",
                    "description": "Optional description"
                },
                "output_format": {
                    "type": "string",
                    "enum": ["pdf", "ppt"],
                    "default": "pdf",
                    "description": "Output format"
                },
                "orientation": {
                    "type": "string",
                    "enum": ["landscape", "portrait"],
                    "default": "landscape",
                    "description": "Page orientation"
                },
                "formatting_profile": {
                    "type": "object",
                    "description": "Optional template formatting profile/theme tokens"
                }
            },
            "required": ["name", "created_by"]
        }
    },
    "update_template": {
        "name": "update_template",
        "description": """Update template properties.

Can update name, description, output format, orientation, or status.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "string",
                    "description": "Template UUID"
                },
                "name": {
                    "type": "string",
                    "description": "New name (optional)"
                },
                "description": {
                    "type": "string",
                    "description": "New description (optional)"
                },
                "output_format": {
                    "type": "string",
                    "enum": ["pdf", "ppt"],
                    "description": "New format (optional)"
                },
                "orientation": {
                    "type": "string",
                    "enum": ["landscape", "portrait"],
                    "description": "New orientation (optional)"
                },
                "status": {
                    "type": "string",
                    "enum": ["draft", "active", "archived"],
                    "description": "New status (optional)"
                },
                "formatting_profile": {
                    "type": "object",
                    "description": "Template formatting profile overrides (optional)"
                }
            },
            "required": ["template_id"]
        }
    },
    "list_templates": {
        "name": "list_templates",
        "description": """List templates with optional filtering.

Returns summaries of templates, ordered by most recently updated.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "created_by": {
                    "type": "string",
                    "description": "Filter by creator (optional)"
                },
                "status": {
                    "type": "string",
                    "enum": ["draft", "active", "archived"],
                    "description": "Filter by status (optional)"
                },
                "limit": {
                    "type": "integer",
                    "default": 50,
                    "description": "Max results"
                }
            },
            "required": []
        }
    }
}
