"""
Conversation management for Report Designer.

Handles persistent chat history per template.
"""

import uuid
from ..db import get_connection


def get_or_create_conversation(template_id: str) -> dict:
    """
    Get existing conversation for template or create a new one.

    Args:
        template_id: UUID of the template

    Returns:
        {"id": str, "template_id": str, "created_at": str, "created": bool}
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Try to get existing conversation
            cur.execute("""
                SELECT id, template_id, created_at
                FROM conversations
                WHERE template_id = %s
            """, (template_id,))

            row = cur.fetchone()
            if row:
                return {
                    "id": str(row[0]),
                    "template_id": str(row[1]),
                    "created_at": str(row[2]) if row[2] else None,
                    "created": False,
                }

            # Create new conversation
            conversation_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO conversations (id, template_id)
                VALUES (%s, %s)
                RETURNING id, template_id, created_at
            """, (conversation_id, template_id))

            row = cur.fetchone()
            conn.commit()

            return {
                "id": str(row[0]),
                "template_id": str(row[1]),
                "created_at": str(row[2]) if row[2] else None,
                "created": True,
            }
    finally:
        conn.close()


def add_message(
    conversation_id: str,
    role: str,
    content: str,
    surface: str = "main",
    section_id: str = None,
    subsection_id: str = None,
) -> dict:
    """
    Add a message to the conversation.

    Args:
        conversation_id: UUID of the conversation
        role: Message role ('user', 'assistant', 'system')
        content: Message content
        surface: UI surface ('main', 'mini', 'agent_note')
        section_id: Optional related section
        subsection_id: Optional related subsection

    Returns:
        {"id": str, "sequence_number": int, "created_at": str}
    """
    message_id = str(uuid.uuid4())

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get next sequence number
            cur.execute("""
                SELECT COALESCE(MAX(sequence_number), 0) + 1
                FROM messages
                WHERE conversation_id = %s
            """, (conversation_id,))
            sequence_number = cur.fetchone()[0]

            # Insert message
            cur.execute("""
                INSERT INTO messages
                (id, conversation_id, role, content, surface, section_id, subsection_id, sequence_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, sequence_number, created_at
            """, (
                message_id, conversation_id, role, content, surface,
                section_id, subsection_id, sequence_number
            ))

            row = cur.fetchone()
            conn.commit()

            return {
                "id": str(row[0]),
                "sequence_number": row[1],
                "created_at": str(row[2]) if row[2] else None,
            }
    finally:
        conn.close()


def get_conversation_history(
    conversation_id: str,
    limit: int = 50,
    include_system: bool = False,
) -> list[dict]:
    """
    Get recent conversation history.

    Args:
        conversation_id: UUID of the conversation
        limit: Max messages to return (most recent)
        include_system: Include system messages

    Returns:
        List of messages ordered by sequence_number ascending (oldest first)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if include_system:
                role_filter = ""
                params = (conversation_id, limit)
            else:
                role_filter = "AND role != 'system'"
                params = (conversation_id, limit)

            # Get most recent messages, then reverse to get oldest first
            cur.execute(f"""
                SELECT id, role, content, surface, section_id, subsection_id,
                       sequence_number, created_at
                FROM messages
                WHERE conversation_id = %s {role_filter}
                ORDER BY sequence_number DESC
                LIMIT %s
            """, params)

            rows = cur.fetchall()

            # Reverse to get oldest first (for OpenAI context)
            messages = [
                {
                    "id": str(row[0]),
                    "role": row[1],
                    "content": row[2],
                    "surface": row[3],
                    "section_id": str(row[4]) if row[4] else None,
                    "subsection_id": str(row[5]) if row[5] else None,
                    "sequence_number": row[6],
                    "created_at": str(row[7]) if row[7] else None,
                }
                for row in reversed(rows)
            ]

            return messages
    finally:
        conn.close()


def get_messages_for_openai(
    conversation_id: str,
    limit: int = 20,
) -> list[dict]:
    """
    Get conversation history formatted for OpenAI API.

    Args:
        conversation_id: UUID of the conversation
        limit: Max messages to include

    Returns:
        List of {"role": str, "content": str} for OpenAI messages parameter
    """
    messages = get_conversation_history(conversation_id, limit=limit)
    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in messages
    ]
