"""
Data sources API routes.
"""

from typing import Optional
from fastapi import APIRouter, Query

from ..deps import CurrentUser
from ...workspace import get_data_sources

router = APIRouter(prefix="/data-sources", tags=["Data Sources"])


@router.get("")
def get_data_sources_endpoint(
    current_user: CurrentUser,
    category: Optional[str] = Query(
        None,
        description="Filter by category (e.g., 'bank_data', 'document_data')",
    ),
    active_only: bool = Query(True, description="Only return active sources"),
) -> list[dict]:
    """
    Get available data sources from the registry.

    Returns list of data sources with retrieval methods, parameter requirements,
    and suggested widget types.
    """
    return get_data_sources(category=category, active_only=active_only)
