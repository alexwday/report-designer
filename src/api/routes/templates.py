"""
Template API routes.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from ..models import (
    TemplateCreateRequest,
    TemplateUpdateRequest,
)
from ..deps import CurrentUser
from ...workspace import (
    get_template,
    create_template,
    update_template,
    delete_template,
    list_templates,
)

router = APIRouter(prefix="/templates", tags=["Templates"])


def check_error(result: dict) -> None:
    """Check for error in workspace function result and raise HTTPException."""
    if "error" in result:
        error_msg = result["error"]
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)


@router.get("")
def list_templates_endpoint(
    current_user: CurrentUser,
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    status: Optional[str] = Query(None, description="Filter by status: draft, active, archived"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
) -> list[dict]:
    """
    List templates with optional filtering.

    Returns summaries of templates ordered by most recently updated.
    """
    return list_templates(created_by=created_by, status=status, limit=limit)


@router.post("", status_code=201)
def create_template_endpoint(
    request: TemplateCreateRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Create a new template workspace.

    A template is the core workspace container that holds sections,
    conversations, and all workspace state.
    """
    result = create_template(
        name=request.name,
        created_by=current_user,
        description=request.description,
        output_format=request.output_format,
        orientation=request.orientation,
        formatting_profile=request.formatting_profile,
    )
    check_error(result)
    return result


@router.get("/{template_id}")
def get_template_endpoint(
    template_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Get template overview with metadata and section summary.

    Updates last_opened_at timestamp.
    """
    result = get_template(template_id=template_id)
    check_error(result)
    return result


@router.patch("/{template_id}")
def update_template_endpoint(
    template_id: str,
    request: TemplateUpdateRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Update template properties.

    Can update name, description, output format, orientation, or status.
    """
    result = update_template(
        template_id=template_id,
        name=request.name,
        description=request.description,
        output_format=request.output_format,
        orientation=request.orientation,
        status=request.status,
        formatting_profile=request.formatting_profile,
    )
    check_error(result)
    return result


@router.delete("/{template_id}", status_code=204)
def delete_template_endpoint(
    template_id: str,
    current_user: CurrentUser,
) -> None:
    """
    Delete a template and all its associated data.

    This permanently deletes the template, all its sections, subsections,
    and related data. This action cannot be undone.
    """
    result = delete_template(template_id=template_id)
    check_error(result)
