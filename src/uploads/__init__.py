"""
File uploads module for Report Designer.

Handles file storage, text extraction, and metadata management.
"""

from .storage import (
    save_upload,
    get_upload,
    list_uploads,
    delete_upload,
    get_upload_content,
    TOOL_DEFINITION,
)

__all__ = [
    "save_upload",
    "get_upload",
    "list_uploads",
    "delete_upload",
    "get_upload_content",
    "TOOL_DEFINITION",
]
