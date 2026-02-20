"""
API routes for Report Designer.
"""

from .templates import router as templates_router
from .sections import router as sections_router
from .subsections import router as subsections_router
from .data_sources import router as data_sources_router
from .export import router as export_router
from .generate import router as generate_router
from .uploads import router as uploads_router
from .chat import router as chat_router
from .template_versions import router as template_versions_router

__all__ = [
    "templates_router",
    "sections_router",
    "subsections_router",
    "data_sources_router",
    "export_router",
    "generate_router",
    "uploads_router",
    "chat_router",
    "template_versions_router",
]
