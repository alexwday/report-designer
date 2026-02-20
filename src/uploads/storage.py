"""
File storage and text extraction for uploads.

Handles:
- Saving uploaded files to disk
- Extracting text from PDFs and documents
- Managing upload metadata in database
"""

import os
import uuid
from pathlib import Path
from typing import Optional, BinaryIO

from ..db import get_connection

# Storage configuration
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def _ensure_upload_dir():
    """Ensure the upload directory exists."""
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


def _get_file_path(filename: str) -> Path:
    """Get the full path for a stored file."""
    return Path(UPLOAD_DIR) / filename


def save_upload(
    template_id: str,
    file_data: BinaryIO,
    original_filename: str,
    content_type: str,
) -> dict:
    """
    Save an uploaded file and create database record.

    Args:
        template_id: Template this file belongs to
        file_data: File binary data
        original_filename: Original filename from upload
        content_type: MIME type

    Returns:
        Upload metadata dict
    """
    _ensure_upload_dir()

    # Validate content type
    if content_type not in ALLOWED_TYPES:
        return {"error": f"Unsupported file type: {content_type}. Allowed: {', '.join(ALLOWED_TYPES.keys())}"}

    # Read file data
    file_bytes = file_data.read()
    size_bytes = len(file_bytes)

    if size_bytes > MAX_FILE_SIZE:
        return {"error": f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"}

    # Generate unique filename
    upload_id = str(uuid.uuid4())
    ext = ALLOWED_TYPES.get(content_type, "")
    stored_filename = f"{upload_id}{ext}"

    # Save file to disk
    file_path = _get_file_path(stored_filename)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Extract text
    extracted_text = None
    extraction_status = "pending"
    extraction_error = None

    try:
        extracted_text = _extract_text(file_path, content_type, file_bytes)
        extraction_status = "completed" if extracted_text else "failed"
    except Exception as e:
        extraction_status = "failed"
        extraction_error = str(e)

    # Save to database
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO uploads (
                    id, template_id, filename, original_filename,
                    content_type, size_bytes, extracted_text,
                    extraction_status, extraction_error
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            """, (
                upload_id, template_id, stored_filename, original_filename,
                content_type, size_bytes, extracted_text,
                extraction_status, extraction_error,
            ))

            row = cur.fetchone()
            conn.commit()

            return {
                "id": upload_id,
                "template_id": template_id,
                "filename": stored_filename,
                "original_filename": original_filename,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "extraction_status": extraction_status,
                "has_extracted_text": bool(extracted_text),
                "created_at": str(row[1]) if row[1] else None,
            }
    except Exception as e:
        # Clean up file if database insert fails
        if file_path.exists():
            file_path.unlink()
        return {"error": f"Failed to save upload: {str(e)}"}
    finally:
        conn.close()


def _extract_text(file_path: Path, content_type: str, file_bytes: bytes) -> Optional[str]:
    """Extract text content from a file."""
    if content_type == "text/plain" or content_type == "text/markdown" or content_type == "text/csv":
        # Plain text files
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1")

    elif content_type == "application/pdf":
        # PDF extraction
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return "\n\n".join(text_parts) if text_parts else None
        except ImportError:
            # pypdf not installed, try basic extraction
            return None
        except Exception:
            return None

    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        # DOCX extraction
        try:
            import docx
            doc = docx.Document(file_path)
            text_parts = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n\n".join(text_parts) if text_parts else None
        except ImportError:
            return None
        except Exception:
            return None

    return None


def get_upload(upload_id: str) -> dict:
    """Get upload metadata by ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, template_id, filename, original_filename,
                       content_type, size_bytes, extraction_status,
                       extraction_error, created_at
                FROM uploads
                WHERE id = %s
            """, (upload_id,))

            row = cur.fetchone()
            if not row:
                return {"error": f"Upload not found: {upload_id}"}

            return {
                "id": str(row[0]),
                "template_id": str(row[1]),
                "filename": row[2],
                "original_filename": row[3],
                "content_type": row[4],
                "size_bytes": row[5],
                "extraction_status": row[6],
                "extraction_error": row[7],
                "created_at": str(row[8]) if row[8] else None,
            }
    finally:
        conn.close()


def list_uploads(template_id: str) -> list[dict]:
    """List all uploads for a template."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, filename, original_filename, content_type,
                       size_bytes, extraction_status, created_at
                FROM uploads
                WHERE template_id = %s
                ORDER BY created_at DESC
            """, (template_id,))

            return [
                {
                    "id": str(row[0]),
                    "filename": row[1],
                    "original_filename": row[2],
                    "content_type": row[3],
                    "size_bytes": row[4],
                    "extraction_status": row[5],
                    "created_at": str(row[6]) if row[6] else None,
                }
                for row in cur.fetchall()
            ]
    finally:
        conn.close()


def delete_upload(upload_id: str) -> dict:
    """Delete an upload and its file."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get filename first
            cur.execute("SELECT filename FROM uploads WHERE id = %s", (upload_id,))
            row = cur.fetchone()

            if not row:
                return {"error": f"Upload not found: {upload_id}"}

            filename = row[0]

            # Delete from database
            cur.execute("DELETE FROM uploads WHERE id = %s", (upload_id,))
            conn.commit()

            # Delete file
            file_path = _get_file_path(filename)
            if file_path.exists():
                file_path.unlink()

            return {"deleted": True, "upload_id": upload_id}
    finally:
        conn.close()


def get_upload_content(upload_id: str) -> dict:
    """
    Get the extracted text content of an upload.

    This is used by the agent to reference uploaded documents.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT original_filename, content_type, extracted_text,
                       extraction_status, extraction_error
                FROM uploads
                WHERE id = %s
            """, (upload_id,))

            row = cur.fetchone()
            if not row:
                return {"error": f"Upload not found: {upload_id}"}

            original_filename, content_type, extracted_text, status, error = row

            if status != "completed" or not extracted_text:
                return {
                    "error": f"Text extraction {status}" + (f": {error}" if error else ""),
                    "filename": original_filename,
                }

            return {
                "filename": original_filename,
                "content_type": content_type,
                "content": extracted_text,
                "content_length": len(extracted_text),
            }
    finally:
        conn.close()


def get_all_upload_contents(template_id: str) -> list[dict]:
    """
    Get extracted text from all uploads for a template.

    Used by the agent to reference all uploaded documents at once.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, original_filename, content_type, extracted_text
                FROM uploads
                WHERE template_id = %s AND extraction_status = 'completed'
                ORDER BY created_at DESC
            """, (template_id,))

            return [
                {
                    "upload_id": str(row[0]),
                    "filename": row[1],
                    "content_type": row[2],
                    "content": row[3],
                    "content_length": len(row[3]) if row[3] else 0,
                }
                for row in cur.fetchall()
                if row[3]  # Only include uploads with extracted text
            ]
    finally:
        conn.close()


# Tool definition for MCP/agent
TOOL_DEFINITION = {
    "name": "get_uploaded_document",
    "description": """Retrieve the text content of an uploaded document.

Use this to reference documents the user has uploaded to the template.
Returns the extracted text content from PDFs, Word docs, or text files.

First use list_uploads to see available documents, then use this tool
with a specific upload_id to get the content.""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "upload_id": {
                "type": "string",
                "description": "UUID of the upload to retrieve"
            }
        },
        "required": ["upload_id"]
    }
}
