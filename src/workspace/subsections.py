"""
Subsection management tools for Report Designer.

Subsections are content areas within sections. They stack vertically
and are labeled A, B, C based on their position (1, 2, 3).

Each subsection has:
- Optional title
- Position (determines A, B, C label)
- Notes: Informal collaboration context
- Instructions: Formal generation prompt
- Content: Generated or edited content
- Version history: Iteration tracking
"""

import uuid
import json
from ..db import get_connection
from .data_sources import validate_data_source_config

_UNSET = object()


def _save_subsection_version_with_cursor(
    cur,
    subsection_id: str,
    *,
    content: str | None = _UNSET,
    content_type: str | None = None,
    instructions: str | None = _UNSET,
    notes: str | None = _UNSET,
    generated_by: str = "agent",
    is_final: bool = False,
    generation_context: dict = None,
    title: str = None,
) -> dict:
    """
    Create a subsection version and update current subsection state.

    This helper runs inside an existing transaction/cursor so callers can
    compose additional reads/writes atomically.
    """
    cur.execute("""
        SELECT version_number, instructions, notes, content, content_type
        FROM subsections WHERE id = %s
    """, (subsection_id,))
    row = cur.fetchone()
    if not row:
        return {"error": f"Subsection not found: {subsection_id}"}

    current_version = row[0]
    current_instructions = row[1]
    current_notes = row[2]
    current_content = row[3]
    current_content_type = row[4]

    resolved_instructions = (
        current_instructions if instructions is _UNSET else instructions
    )
    resolved_notes = current_notes if notes is _UNSET else notes
    resolved_content = current_content if content is _UNSET else content
    resolved_content_type = (
        current_content_type if content_type is None else content_type
    )
    if resolved_content_type is None:
        resolved_content_type = "markdown"

    new_version = current_version + 1
    version_id = str(uuid.uuid4())

    cur.execute("""
        INSERT INTO subsection_versions
        (id, subsection_id, version_number, instructions, notes, content,
         content_type, generated_by, is_final, generation_context)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, version_number, created_at
    """, (
        version_id,
        subsection_id,
        new_version,
        resolved_instructions,
        resolved_notes,
        resolved_content,
        resolved_content_type,
        generated_by,
        is_final,
        json.dumps(generation_context) if generation_context else None,
    ))
    version_row = cur.fetchone()

    if title is not None:
        cur.execute("""
            UPDATE subsections
            SET instructions = %s,
                notes = %s,
                content = %s,
                content_type = %s,
                version_number = %s,
                title = %s
            WHERE id = %s
        """, (
            resolved_instructions,
            resolved_notes,
            resolved_content,
            resolved_content_type,
            new_version,
            title,
            subsection_id,
        ))
    else:
        cur.execute("""
            UPDATE subsections
            SET instructions = %s,
                notes = %s,
                content = %s,
                content_type = %s,
                version_number = %s
            WHERE id = %s
        """, (
            resolved_instructions,
            resolved_notes,
            resolved_content,
            resolved_content_type,
            new_version,
            subsection_id,
        ))

    if is_final:
        cur.execute("""
            UPDATE subsection_versions
            SET is_final = FALSE
            WHERE subsection_id = %s AND id != %s
        """, (subsection_id, version_id))

    return {
        "version_id": str(version_row[0]),
        "version_number": version_row[1],
        "subsection_id": subsection_id,
        "content_type": resolved_content_type,
        "generated_by": generated_by,
        "is_final": is_final,
        "title": title,
        "instructions": resolved_instructions,
        "notes": resolved_notes,
        "content": resolved_content,
        "created_at": str(version_row[2]) if version_row[2] else None,
    }


def get_subsection(
    subsection_id: str,
    include_versions: bool = True,
    version_limit: int = 10,
) -> dict:
    """
    Get detailed subsection information including version history.

    Args:
        subsection_id: UUID of the subsection
        include_versions: Include version history
        version_limit: Max versions to return (most recent first)

    Returns:
        Full subsection details with versions
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get subsection
            cur.execute("""
                SELECT s.id, s.section_id, s.title, s.position, s.widget_type,
                       s.data_source_config, s.notes, s.instructions,
                       s.content, s.content_type, s.version_number,
                       s.created_at, s.updated_at,
                       sec.template_id, sec.title as section_title
                FROM subsections s
                JOIN sections sec ON s.section_id = sec.id
                WHERE s.id = %s
            """, (subsection_id,))

            row = cur.fetchone()
            if not row:
                return {"error": f"Subsection not found: {subsection_id}"}

            subsection = {
                "id": str(row[0]),
                "section_id": str(row[1]),
                "title": row[2],
                "position": row[3],
                "widget_type": row[4],
                "data_source_config": row[5],
                "notes": row[6],
                "instructions": row[7],
                "content": row[8],
                "content_type": row[9],
                "version_number": row[10],
                "created_at": str(row[11]) if row[11] else None,
                "updated_at": str(row[12]) if row[12] else None,
                "template_id": str(row[13]),
                "section_title": row[14],
            }

            # Get version history
            if include_versions:
                cur.execute("""
                    SELECT id, version_number, instructions, notes, content,
                           content_type, generated_by, is_final, created_at
                    FROM subsection_versions
                    WHERE subsection_id = %s
                    ORDER BY version_number DESC
                    LIMIT %s
                """, (subsection_id, version_limit))

                subsection["versions"] = [
                    {
                        "id": str(r[0]),
                        "version_number": r[1],
                        "instructions": r[2],
                        "notes": r[3],
                        "content_preview": r[4][:200] + "..." if r[4] and len(r[4]) > 200 else r[4],
                        "content_type": r[5],
                        "generated_by": r[6],
                        "is_final": r[7],
                        "created_at": str(r[8]) if r[8] else None,
                    }
                    for r in cur.fetchall()
                ]

            return subsection
    finally:
        conn.close()


def create_subsection(
    section_id: str,
    title: str = None,
    position: int = None,
) -> dict:
    """
    Create a new subsection in a section.

    Args:
        section_id: UUID of the section
        title: Optional subsection title
        position: Position within section. None to append at end.

    Returns:
        Created subsection
    """
    subsection_id = str(uuid.uuid4())

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Verify section exists
            cur.execute("SELECT id FROM sections WHERE id = %s", (section_id,))
            if not cur.fetchone():
                return {"error": f"Section not found: {section_id}"}

            # Determine position
            if position is None:
                cur.execute("""
                    SELECT COALESCE(MAX(position), 0) + 1
                    FROM subsections WHERE section_id = %s
                """, (section_id,))
                position = cur.fetchone()[0]
            else:
                # Shift existing subsections to make room
                cur.execute("""
                    UPDATE subsections
                    SET position = position + 1
                    WHERE section_id = %s AND position >= %s
                """, (section_id, position))

            # Create subsection
            cur.execute("""
                INSERT INTO subsections (id, section_id, title, position)
                VALUES (%s, %s, %s, %s)
                RETURNING id, title, position, widget_type, created_at
            """, (subsection_id, section_id, title, position))

            row = cur.fetchone()
            conn.commit()

            return {
                "id": str(row[0]),
                "section_id": section_id,
                "title": row[1],
                "position": row[2],
                "widget_type": row[3],
                "created_at": str(row[4]) if row[4] else None,
            }
    finally:
        conn.close()


def update_title(
    subsection_id: str,
    title: str,
) -> dict:
    """
    Update the title of a subsection.

    Args:
        subsection_id: UUID of the subsection
        title: New title (can be None/empty to remove)

    Returns:
        Updated subsection summary
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE subsections
                SET title = %s
                WHERE id = %s
                RETURNING id, title
            """, (title if title else None, subsection_id))

            row = cur.fetchone()
            if not row:
                return {"error": f"Subsection not found: {subsection_id}"}

            conn.commit()

            return {
                "id": str(row[0]),
                "title": row[1],
                "updated": True,
            }
    finally:
        conn.close()


def reorder_subsection(
    subsection_id: str,
    new_position: int,
) -> dict:
    """
    Move a subsection to a new position within its section.

    Args:
        subsection_id: UUID of the subsection
        new_position: New position (1-indexed)

    Returns:
        Updated subsection
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get current position
            cur.execute("""
                SELECT section_id, position FROM subsections WHERE id = %s
            """, (subsection_id,))
            row = cur.fetchone()

            if not row:
                return {"error": f"Subsection not found: {subsection_id}"}

            section_id, current_position = row

            if new_position == current_position:
                return get_subsection(subsection_id, include_versions=False)

            # Validate new position
            cur.execute("""
                SELECT COUNT(*) FROM subsections WHERE section_id = %s
            """, (section_id,))
            max_position = cur.fetchone()[0]

            if new_position < 1 or new_position > max_position:
                return {"error": f"Invalid position: {new_position}. Must be 1-{max_position}."}

            if new_position > current_position:
                # Moving down: shift others up
                cur.execute("""
                    UPDATE subsections
                    SET position = position - 1
                    WHERE section_id = %s AND position > %s AND position <= %s
                """, (section_id, current_position, new_position))
            else:
                # Moving up: shift others down
                cur.execute("""
                    UPDATE subsections
                    SET position = position + 1
                    WHERE section_id = %s AND position >= %s AND position < %s
                """, (section_id, new_position, current_position))

            # Update subsection position
            cur.execute("""
                UPDATE subsections SET position = %s WHERE id = %s
            """, (new_position, subsection_id))

            conn.commit()

            return get_subsection(subsection_id, include_versions=False)
    finally:
        conn.close()


def delete_subsection(subsection_id: str) -> dict:
    """
    Delete a subsection.

    Args:
        subsection_id: UUID of the subsection

    Returns:
        Confirmation of deletion
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get subsection info
            cur.execute("""
                SELECT section_id, position FROM subsections WHERE id = %s
            """, (subsection_id,))
            row = cur.fetchone()

            if not row:
                return {"error": f"Subsection not found: {subsection_id}"}

            section_id, position = row

            # Check if this is the last subsection in the section
            cur.execute("""
                SELECT COUNT(*) FROM subsections WHERE section_id = %s
            """, (section_id,))
            count = cur.fetchone()[0]

            if count <= 1:
                return {"error": "Cannot delete the last subsection in a section. Delete the section instead."}

            # Delete subsection (cascades to versions)
            cur.execute("DELETE FROM subsections WHERE id = %s", (subsection_id,))

            # Reorder remaining subsections
            cur.execute("""
                UPDATE subsections
                SET position = position - 1
                WHERE section_id = %s AND position > %s
            """, (section_id, position))

            conn.commit()

            return {
                "deleted": True,
                "subsection_id": subsection_id,
            }
    finally:
        conn.close()


def update_notes(
    subsection_id: str,
    notes: str,
    append: bool = False,
) -> dict:
    """
    Update the notes for a subsection.

    Saving notes creates a new subsection version so history stays aligned
    with collaborative context changes.

    Args:
        subsection_id: UUID of the subsection
        notes: Updated notes text
        append: If true, append to existing notes

    Returns:
        Updated subsection summary
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            next_notes = notes
            if append:
                cur.execute("""
                    SELECT notes FROM subsections WHERE id = %s
                """, (subsection_id,))
                row = cur.fetchone()
                if not row:
                    return {"error": f"Subsection not found: {subsection_id}"}
                existing_notes = row[0] or ""
                next_notes = existing_notes + "\n\n" + notes

            save_result = _save_subsection_version_with_cursor(
                cur,
                subsection_id,
                notes=next_notes,
                generated_by="user_edit",
            )
            if "error" in save_result:
                return save_result

            conn.commit()

            return {
                "id": subsection_id,
                "notes": next_notes,
                "version_id": save_result["version_id"],
                "version_number": save_result["version_number"],
                "updated": True,
            }
    finally:
        conn.close()


def update_instructions(
    subsection_id: str,
    instructions: str,
) -> dict:
    """
    Update the generation instructions for a subsection.

    Saving instructions creates a new subsection version so users can
    revisit prior prompt iterations.

    Args:
        subsection_id: UUID of the subsection
        instructions: Updated instructions text

    Returns:
        Updated subsection summary
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            save_result = _save_subsection_version_with_cursor(
                cur,
                subsection_id,
                instructions=instructions,
                generated_by="user_edit",
            )
            if "error" in save_result:
                return save_result

            conn.commit()

            return {
                "id": subsection_id,
                "instructions": instructions,
                "version_id": save_result["version_id"],
                "version_number": save_result["version_number"],
                "updated": True,
            }
    finally:
        conn.close()


def configure_subsection(
    subsection_id: str,
    widget_type: str = None,
    data_source_config: dict | None = _UNSET,
) -> dict:
    """
    Configure a subsection's data source and widget type.

    Args:
        subsection_id: UUID of the subsection
        widget_type: Content rendering type
        data_source_config: Data source configuration

    Returns:
        Updated subsection
    """
    updates = []
    params = []

    if widget_type is not None:
        updates.append("widget_type = %s")
        params.append(widget_type)
    if data_source_config is not _UNSET:
        if data_source_config is not None:
            validation = validate_data_source_config(data_source_config)
            if not validation["valid"]:
                return {
                    "error": "Invalid data source configuration",
                    "validation_errors": validation["errors"],
                }
            data_source_config = validation["normalized_config"]
        updates.append("data_source_config = %s")
        params.append(json.dumps(data_source_config) if data_source_config is not None else None)

    if not updates:
        return {"error": "No configuration provided"}

    params.append(subsection_id)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                UPDATE subsections
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING id, widget_type, data_source_config
            """, tuple(params))

            row = cur.fetchone()
            if not row:
                return {"error": f"Subsection not found: {subsection_id}"}

            conn.commit()

            return {
                "id": str(row[0]),
                "widget_type": row[1],
                "data_source_config": row[2],
                "updated": True,
            }
    finally:
        conn.close()


def save_subsection_version(
    subsection_id: str,
    content: str | None = _UNSET,
    content_type: str | None = None,
    generated_by: str = "agent",
    is_final: bool = False,
    generation_context: dict = None,
    title: str = None,
    instructions: str | None = _UNSET,
    notes: str | None = _UNSET,
) -> dict:
    """
    Save a new version of subsection content.

    Args:
        subsection_id: UUID of the subsection
        content: Generated/edited content. Omit to keep current content.
        content_type: Content format (text, markdown, html, json). Omit to keep current type.
        generated_by: How this version was created (agent, user_edit, import)
        is_final: Mark this version as finalized
        generation_context: Optional metadata about generation
        title: Optional title to set for the subsection
        instructions: Optional instructions override for this version/state
        notes: Optional notes override for this version/state

    Returns:
        Created version info
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            save_result = _save_subsection_version_with_cursor(
                cur,
                subsection_id,
                content=content,
                content_type=content_type,
                instructions=instructions,
                notes=notes,
                generated_by=generated_by,
                is_final=is_final,
                generation_context=generation_context,
                title=title,
            )
            if "error" in save_result:
                return save_result

            conn.commit()

            return save_result
    finally:
        conn.close()


def get_version(version_id: str) -> dict:
    """Get a specific version by ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, subsection_id, version_number, instructions, notes,
                       content, content_type, generated_by, is_final,
                       generation_context, created_at
                FROM subsection_versions WHERE id = %s
            """, (version_id,))

            row = cur.fetchone()
            if not row:
                return {"error": f"Version not found: {version_id}"}

            return {
                "id": str(row[0]),
                "subsection_id": str(row[1]),
                "version_number": row[2],
                "instructions": row[3],
                "notes": row[4],
                "content": row[5],
                "content_type": row[6],
                "generated_by": row[7],
                "is_final": row[8],
                "generation_context": row[9],
                "created_at": str(row[10]) if row[10] else None,
            }
    finally:
        conn.close()


# Tool definitions for MCP server
TOOL_DEFINITIONS = {
    "get_subsection": {
        "name": "get_subsection",
        "description": """Get detailed subsection information including all content and version history.

Returns:
- Title and position (A, B, C based on position 1, 2, 3)
- Full notes and instructions
- Current content
- Data source configuration
- Version history (all previous iterations)

Use this when focusing on a specific content area for generation or review.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subsection_id": {
                    "type": "string",
                    "description": "Subsection reference (e.g., S1A) or subsection UUID"
                },
                "include_versions": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include version history"
                },
                "version_limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Max versions to return (most recent first)"
                }
            },
            "required": ["subsection_id"]
        }
    },
    "create_subsection": {
        "name": "create_subsection",
        "description": """Create a new subsection in a section.

Subsections stack vertically within a section and are labeled A, B, C
based on their position (1, 2, 3).

Position determines order. Use position=null to append at end.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "section_id": {
                    "type": "string",
                    "description": "Section reference (e.g., S1) or section UUID"
                },
                "title": {
                    "type": "string",
                    "description": "Subsection title (optional)"
                },
                "position": {
                    "type": "integer",
                    "description": "Position within section (1-indexed). Null to append."
                }
            },
            "required": ["section_id"]
        }
    },
    "update_subsection_title": {
        "name": "update_subsection_title",
        "description": """Update the title of a subsection.

Titles are optional headings displayed above the subsection content.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subsection_id": {
                    "type": "string",
                    "description": "Subsection reference (e.g., S1A) or subsection UUID"
                },
                "title": {
                    "type": "string",
                    "description": "New title (empty string to remove)"
                }
            },
            "required": ["subsection_id", "title"]
        }
    },
    "reorder_subsection": {
        "name": "reorder_subsection",
        "description": """Move a subsection to a new position within its section.

Changes the A, B, C labeling by updating the position.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subsection_id": {
                    "type": "string",
                    "description": "Subsection reference (e.g., S1A) or subsection UUID"
                },
                "new_position": {
                    "type": "integer",
                    "description": "New position (1-indexed)"
                }
            },
            "required": ["subsection_id", "new_position"]
        }
    },
    "delete_subsection": {
        "name": "delete_subsection",
        "description": """Delete a subsection.

Cannot delete the last subsection in a section - delete the section instead.
Remaining subsections will be reordered to fill the gap.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subsection_id": {
                    "type": "string",
                    "description": "Subsection reference (e.g., S1A) or subsection UUID"
                }
            },
            "required": ["subsection_id"]
        }
    },
    "update_notes": {
        "name": "update_notes",
        "description": """Update the notes for a subsection.

Notes are informal collaboration context - use them to:
- Record user preferences ("prefers executive tone")
- Track what was tried ("tried table format, preferred bullets")
- Add observations for future reference
- Keep context for the next generation iteration

Both you and the user can edit notes. They persist across sessions.
Each save also creates a new subsection version.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subsection_id": {
                    "type": "string",
                    "description": "Subsection reference (e.g., S1A) or subsection UUID"
                },
                "notes": {
                    "type": "string",
                    "description": "Updated notes text"
                },
                "append": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, append to existing notes instead of replacing"
                }
            },
            "required": ["subsection_id", "notes"]
        }
    },
    "update_instructions": {
        "name": "update_instructions",
        "description": """Update the generation instructions for a subsection.

Instructions are the formal prompt used to generate content:
- Be specific about format ("3 bullet points", "2-paragraph summary")
- Include what data to emphasize
- Specify comparisons or context to include
- Note any constraints (length, tone, etc.)

Instructions are used when generating or regenerating content.
Each save also creates a new subsection version.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subsection_id": {
                    "type": "string",
                    "description": "Subsection reference (e.g., S1A) or subsection UUID"
                },
                "instructions": {
                    "type": "string",
                    "description": "Updated instructions text"
                }
            },
            "required": ["subsection_id", "instructions"]
        }
    },
    "configure_subsection": {
        "name": "configure_subsection",
        "description": """Configure a subsection's data source and widget type.

Sets up:
- Data source: which source and retrieval method to use
- Parameters: values for retrieval (bank_id, quarter, etc.)
- Widget type: how to render the content (summary, table, chart, etc.)

Call this before generating content for the subsection.

Widget types: summary, key_points, table, chart, comparison, custom""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subsection_id": {
                    "type": "string",
                    "description": "Subsection reference (e.g., S1A) or subsection UUID"
                },
                "widget_type": {
                    "type": "string",
                    "enum": ["summary", "key_points", "table", "chart", "comparison", "custom"],
                    "description": "Content rendering type"
                },
                "data_source_config": {
                    "type": "object",
                    "description": "Data source configuration",
                    "properties": {
                        "inputs": {
                            "type": "array",
                            "description": "One or more data inputs used to generate this subsection",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "source_id": {
                                        "type": "string",
                                        "description": "Data source ID from registry"
                                    },
                                    "method_id": {
                                        "type": "string",
                                        "description": "Retrieval method ID"
                                    },
                                    "parameters": {
                                        "type": "object",
                                        "description": "Parameters for retrieval method"
                                    }
                                },
                                "required": ["source_id", "method_id"]
                            }
                        },
                        "dependencies": {
                            "type": "object",
                            "description": "Optional context dependencies for ordering and prompt context",
                            "properties": {
                                "section_ids": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Sections whose subsection outputs should be used as context (use refs like S1 when possible)"
                                },
                                "subsection_ids": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Specific subsections to include as context dependencies (use refs like S1A when possible)"
                                }
                            }
                        },
                        "visualization": {
                            "type": "object",
                            "description": "Optional chart/visualization configuration",
                            "properties": {
                                "chart_type": {
                                    "type": "string",
                                    "enum": ["bar", "line"],
                                    "description": "Preferred chart type for chart widgets"
                                },
                                "title": {
                                    "type": "string",
                                    "description": "Optional chart title override"
                                },
                                "x_key": {
                                    "type": "string",
                                    "description": "Field used for x-axis labels"
                                },
                                "y_key": {
                                    "type": "string",
                                    "description": "Field used for y-axis values"
                                },
                                "series_key": {
                                    "type": "string",
                                    "description": "Field used to split series"
                                },
                                "metric_id": {
                                    "type": "string",
                                    "description": "Metric ID to chart (for metric-rich sources)"
                                }
                            }
                        }
                    },
                    "required": ["inputs"]
                }
            },
            "required": ["subsection_id"]
        }
    },
    "save_subsection_version": {
        "name": "save_subsection_version",
        "description": """Save a new version of subsection content.

Creates a new version in the history and updates current content.
Each generation iteration should be saved as a version.

Optionally set a title for the subsection at the same time.

Set is_final=true when the user approves the content as complete.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subsection_id": {
                    "type": "string",
                    "description": "Subsection reference (e.g., S1A) or subsection UUID"
                },
                "content": {
                    "type": "string",
                    "description": "Generated/edited content"
                },
                "content_type": {
                    "type": "string",
                    "enum": ["text", "markdown", "html", "json"],
                    "default": "markdown",
                    "description": "Content format"
                },
                "generated_by": {
                    "type": "string",
                    "enum": ["agent", "user_edit", "import"],
                    "default": "agent",
                    "description": "How this version was created"
                },
                "is_final": {
                    "type": "boolean",
                    "default": False,
                    "description": "Mark this version as the finalized version"
                },
                "generation_context": {
                    "type": "object",
                    "description": "Optional metadata about generation (data used, etc.)"
                },
                "title": {
                    "type": "string",
                    "description": "Optional title to set for the subsection"
                }
            },
            "required": ["subsection_id", "content"]
        }
    }
}
