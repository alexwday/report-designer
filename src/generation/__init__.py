"""
Generation pipeline module for Report Designer.

Provides batch generation capabilities with progress tracking
and cross-section coherence.
"""

from .pipeline import (
    start_generation,
    get_generation_status,
    get_generation_requirements,
    generate_section,
    generate_subsection,
    GenerationStatus,
)

__all__ = [
    "start_generation",
    "get_generation_status",
    "get_generation_requirements",
    "generate_section",
    "generate_subsection",
    "GenerationStatus",
]
