"""
Section API routes.
"""

from fastapi import APIRouter, HTTPException, Query

from ..models import (
    SectionCreateRequest,
    SectionUpdateRequest,
)
from ..deps import CurrentUser
from ...generation import generate_section as generate_section_content
from ...workspace import (
    get_sections,
    create_section,
    update_section,
    delete_section,
)

router = APIRouter(tags=["Sections"])


def check_error(result: dict) -> None:
    """Check for error in workspace function result and raise HTTPException."""
    if "error" in result:
        error_msg = result["error"]
        detail = result if "validation_errors" in result else error_msg
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=detail)
        raise HTTPException(status_code=400, detail=detail)


@router.get("/templates/{template_id}/sections")
def get_sections_endpoint(
    template_id: str,
    current_user: CurrentUser,
    include_content: bool = Query(False, description="Include full content text (can be large)"),
) -> list[dict]:
    """
    Get all sections for a template with their subsections.

    Returns ordered list of sections. Each section contains subsections
    labeled A, B, C based on position. Use include_content=true to get
    full content text (can be large).
    """
    return get_sections(template_id=template_id, include_content=include_content)


@router.post("/templates/{template_id}/sections", status_code=201)
def create_section_endpoint(
    template_id: str,
    request: SectionCreateRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Create a new section in the template.

    Sections contain vertically-stacked subsections (A, B, C, etc.).
    Each new section starts with one empty subsection.
    """
    result = create_section(
        template_id=template_id,
        title=request.title,
        position=request.position,
    )
    check_error(result)
    return result


@router.patch("/sections/{section_id}")
def update_section_endpoint(
    section_id: str,
    request: SectionUpdateRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Update section properties.

    Changing position will reorder sections.
    """
    result = update_section(
        section_id=section_id,
        title=request.title,
        position=request.position,
    )
    check_error(result)
    return result


@router.post("/sections/{section_id}/generate")
async def generate_section_endpoint(
    section_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Generate content for all eligible subsections in a section.

    Generation is blocked unless each target subsection has a configured
    data source configuration with at least one valid input.
    """
    result = await generate_section_content(section_id=section_id)
    check_error(result)
    return result


@router.delete("/sections/{section_id}")
def delete_section_endpoint(
    section_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Delete a section and all its subsections.

    This permanently removes the section, all subsections, and their version history.
    Remaining sections will be reordered to fill the gap.
    """
    result = delete_section(section_id=section_id)
    check_error(result)
    return result
