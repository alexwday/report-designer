"""
Template Version API routes.

Handles template versioning, restore, fork, and sharing.
"""

from fastapi import APIRouter, HTTPException, Query

from ..models import (
    CreateTemplateVersionRequest,
    ForkTemplateRequest,
    SetSharedRequest,
)
from ..deps import CurrentUser
from ...workspace import (
    create_template_version,
    list_template_versions,
    get_template_version,
    restore_template_version,
    fork_template,
    list_shared_templates,
    set_template_shared,
)

router = APIRouter(tags=["Template Versions"])


def check_error(result: dict) -> None:
    """Check for error in workspace function result and raise HTTPException."""
    if "error" in result:
        error_msg = result["error"]
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)


# ============================================================
# Version endpoints (under /templates/{template_id}/versions)
# ============================================================

@router.post("/templates/{template_id}/versions", status_code=201)
def create_version_endpoint(
    template_id: str,
    request: CreateTemplateVersionRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Create a new version snapshot of a template.

    Captures the current state of all sections, subsections, and content.
    """
    result = create_template_version(
        template_id=template_id,
        name=request.name,
        created_by=current_user,
    )
    check_error(result)
    return result


@router.get("/templates/{template_id}/versions")
def list_versions_endpoint(
    template_id: str,
    current_user: CurrentUser,
    limit: int = Query(20, ge=1, le=100, description="Max results"),
) -> list[dict]:
    """
    List version history for a template.

    Returns versions ordered by most recent first.
    """
    return list_template_versions(template_id=template_id, limit=limit)


@router.get("/templates/{template_id}/versions/{version_id}")
def get_version_endpoint(
    template_id: str,
    version_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Get a specific version with its full snapshot.

    The snapshot contains the complete state of the template at that point.
    """
    result = get_template_version(version_id=version_id)
    check_error(result)

    # Verify the version belongs to this template
    if result.get("template_id") != template_id:
        raise HTTPException(status_code=404, detail="Version not found for this template")

    return result


@router.post("/templates/{template_id}/versions/{version_id}/restore")
def restore_version_endpoint(
    template_id: str,
    version_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Restore a template to a previous version state.

    This creates an auto-save of the current state before restoring,
    then applies the snapshot from the specified version.
    """
    result = restore_template_version(
        template_id=template_id,
        version_id=version_id,
    )
    check_error(result)
    return result


# ============================================================
# Fork endpoint (under /templates/{template_id}/fork)
# ============================================================

@router.post("/templates/{template_id}/fork", status_code=201)
def fork_template_endpoint(
    template_id: str,
    request: ForkTemplateRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Create a copy of a template with all its content.

    The forked template is created with 'draft' status and
    owned by the current user.
    """
    result = fork_template(
        template_id=template_id,
        new_name=request.new_name,
        created_by=current_user,
    )
    check_error(result)
    return result


# ============================================================
# Shared templates endpoints
# ============================================================

@router.get("/templates/shared")
def list_shared_templates_endpoint(
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=100, description="Max results"),
) -> list[dict]:
    """
    List templates that are marked as shared.

    These are templates other users have made available for viewing/forking.
    """
    return list_shared_templates(limit=limit)


@router.patch("/templates/{template_id}/share")
def set_template_shared_endpoint(
    template_id: str,
    request: SetSharedRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Set a template's shared status.

    When shared, other users can view and fork the template.
    """
    result = set_template_shared(
        template_id=template_id,
        is_shared=request.is_shared,
    )
    check_error(result)
    return result
