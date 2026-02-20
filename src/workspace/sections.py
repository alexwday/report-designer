"""
Section management tools for Report Designer.

Sections are ordered content containers within a template.
Each section contains vertically-stacked subsections (A, B, C, etc.).
Sections can span multiple PDF pages when exported.
"""

import uuid
from ..db import get_connection


def get_sections(template_id: str, include_content: bool = False) -> list[dict]:
    """
    Get all sections for a template with their subsections.

    Args:
        template_id: UUID of the template
        include_content: Include full content text (can be large)

    Returns:
        Ordered list of sections with subsections
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get sections
            cur.execute("""
                SELECT id, position, title, created_at, updated_at
                FROM sections
                WHERE template_id = %s
                ORDER BY position
            """, (template_id,))

            sections = []
            for row in cur.fetchall():
                section_id = str(row[0])

                # Get subsections for this section
                content_field = ", content" if include_content else ""
                cur.execute(f"""
                    SELECT id, title, position, widget_type, data_source_config,
                           notes, instructions, content_type, version_number{content_field}
                    FROM subsections
                    WHERE section_id = %s
                    ORDER BY position
                """, (section_id,))

                subsections = []
                for sub_row in cur.fetchall():
                    subsection = {
                        "id": str(sub_row[0]),
                        "title": sub_row[1],
                        "position": sub_row[2],
                        "widget_type": sub_row[3],
                        "data_source_config": sub_row[4],
                        "has_notes": bool(sub_row[5]),
                        "has_instructions": bool(sub_row[6]),
                        "content_type": sub_row[7],
                        "version_number": sub_row[8],
                    }
                    if include_content:
                        subsection["content"] = sub_row[9]
                        subsection["notes"] = sub_row[5]
                        subsection["instructions"] = sub_row[6]
                    subsections.append(subsection)

                sections.append({
                    "id": section_id,
                    "position": row[1],
                    "title": row[2],
                    "created_at": str(row[3]) if row[3] else None,
                    "updated_at": str(row[4]) if row[4] else None,
                    "subsections": subsections,
                })

            return sections
    finally:
        conn.close()


def create_section(
    template_id: str,
    title: str = None,
    position: int = None,
) -> dict:
    """
    Create a new section in the template.

    Args:
        template_id: UUID of the template
        title: Optional section title
        position: Position in document (1-indexed). None to append at end.

    Returns:
        Created section with one default subsection
    """
    section_id = str(uuid.uuid4())

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Determine position
            if position is None:
                cur.execute("""
                    SELECT COALESCE(MAX(position), 0) + 1
                    FROM sections WHERE template_id = %s
                """, (template_id,))
                position = cur.fetchone()[0]
            else:
                # Shift existing sections to make room
                cur.execute("""
                    UPDATE sections
                    SET position = position + 1
                    WHERE template_id = %s AND position >= %s
                """, (template_id, position))

            # Create section
            cur.execute("""
                INSERT INTO sections (id, template_id, title, position)
                VALUES (%s, %s, %s, %s)
                RETURNING id, position, title, created_at
            """, (section_id, template_id, title, position))

            section_row = cur.fetchone()

            # Create one default subsection at position 1
            subsection_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO subsections (id, section_id, position)
                VALUES (%s, %s, 1)
                RETURNING id, title, position, widget_type
            """, (subsection_id, section_id))

            sub_row = cur.fetchone()
            subsections = [{
                "id": str(sub_row[0]),
                "title": sub_row[1],
                "position": sub_row[2],
                "widget_type": sub_row[3],
            }]

            conn.commit()

            return {
                "id": str(section_row[0]),
                "position": section_row[1],
                "title": section_row[2],
                "created_at": str(section_row[3]) if section_row[3] else None,
                "subsections": subsections,
            }
    finally:
        conn.close()


def update_section(
    section_id: str,
    title: str = None,
    position: int = None,
) -> dict:
    """
    Update section properties.

    Args:
        section_id: UUID of the section
        title: New title (optional)
        position: New position (optional)

    Returns:
        Updated section
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get current section
            cur.execute("""
                SELECT template_id, position FROM sections WHERE id = %s
            """, (section_id,))
            current = cur.fetchone()

            if not current:
                return {"error": f"Section not found: {section_id}"}

            template_id, current_position = current

            # Handle position change
            if position is not None and position != current_position:
                if position > current_position:
                    # Moving down: shift others up
                    cur.execute("""
                        UPDATE sections
                        SET position = position - 1
                        WHERE template_id = %s AND position > %s AND position <= %s
                    """, (template_id, current_position, position))
                else:
                    # Moving up: shift others down
                    cur.execute("""
                        UPDATE sections
                        SET position = position + 1
                        WHERE template_id = %s AND position >= %s AND position < %s
                    """, (template_id, position, current_position))

            # Build update query
            updates = []
            params = []

            if title is not None:
                updates.append("title = %s")
                params.append(title)
            if position is not None:
                updates.append("position = %s")
                params.append(position)

            if updates:
                params.append(section_id)
                cur.execute(f"""
                    UPDATE sections
                    SET {', '.join(updates)}
                    WHERE id = %s
                """, tuple(params))

            conn.commit()

            # Return updated section
            return get_section_by_id(section_id)
    finally:
        conn.close()


def get_section_by_id(section_id: str) -> dict:
    """Get a single section by ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, template_id, position, title, created_at, updated_at
                FROM sections WHERE id = %s
            """, (section_id,))

            row = cur.fetchone()
            if not row:
                return {"error": f"Section not found: {section_id}"}

            # Get subsections
            cur.execute("""
                SELECT id, title, position, widget_type, data_source_config
                FROM subsections WHERE section_id = %s ORDER BY position
            """, (section_id,))

            subsections = [
                {
                    "id": str(r[0]),
                    "title": r[1],
                    "position": r[2],
                    "widget_type": r[3],
                    "data_source_config": r[4],
                }
                for r in cur.fetchall()
            ]

            return {
                "id": str(row[0]),
                "template_id": str(row[1]),
                "position": row[2],
                "title": row[3],
                "created_at": str(row[4]) if row[4] else None,
                "updated_at": str(row[5]) if row[5] else None,
                "subsections": subsections,
            }
    finally:
        conn.close()


def delete_section(section_id: str) -> dict:
    """
    Delete a section and all its subsections.

    Args:
        section_id: UUID of the section

    Returns:
        Confirmation of deletion
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get section info
            cur.execute("""
                SELECT template_id, position FROM sections WHERE id = %s
            """, (section_id,))
            row = cur.fetchone()

            if not row:
                return {"error": f"Section not found: {section_id}"}

            template_id, position = row

            # Delete section (cascades to subsections)
            cur.execute("DELETE FROM sections WHERE id = %s", (section_id,))

            # Reorder remaining sections
            cur.execute("""
                UPDATE sections
                SET position = position - 1
                WHERE template_id = %s AND position > %s
            """, (template_id, position))

            conn.commit()

            return {
                "deleted": True,
                "section_id": section_id,
            }
    finally:
        conn.close()


# Tool definitions for MCP server
TOOL_DEFINITIONS = {
    "get_sections": {
        "name": "get_sections",
        "description": """Get all sections for a template with their subsections.

Returns ordered list of sections, each with:
- Section metadata (title, position)
- All subsections with title, position, notes, instructions, content preview
- Data source configurations

Subsections are labeled A, B, C based on position (1, 2, 3).

Use this to understand the document structure and what content exists.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "string",
                    "description": "Template UUID"
                },
                "include_content": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include full content text (can be large). Default: summary only."
                }
            },
            "required": ["template_id"]
        }
    },
    "create_section": {
        "name": "create_section",
        "description": """Create a new section in the template.

Sections contain vertically-stacked subsections (A, B, C, etc.).
Each new section starts with one empty subsection.

Position determines order. Use position=null to append at end.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "string",
                    "description": "Template UUID"
                },
                "title": {
                    "type": "string",
                    "description": "Section title (optional)"
                },
                "position": {
                    "type": "integer",
                    "description": "Position in document (1-indexed). Null to append."
                }
            },
            "required": ["template_id"]
        }
    },
    "update_section": {
        "name": "update_section",
        "description": """Update section properties (title, position).

Changing position will reorder sections.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "section_id": {
                    "type": "string",
                    "description": "Section reference (e.g., S1) or section UUID"
                },
                "title": {
                    "type": "string",
                    "description": "New title (optional)"
                },
                "position": {
                    "type": "integer",
                    "description": "New position (optional)"
                }
            },
            "required": ["section_id"]
        }
    },
    "delete_section": {
        "name": "delete_section",
        "description": """Delete a section and all its subsections.

This permanently removes the section, all subsections, and their version history.
Remaining sections will be reordered to fill the gap.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "section_id": {
                    "type": "string",
                    "description": "Section reference (e.g., S1) or section UUID"
                }
            },
            "required": ["section_id"]
        }
    }
}
