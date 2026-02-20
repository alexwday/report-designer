"""
Subsection API routes.
"""

from fastapi import APIRouter, HTTPException, Query

from ..models import (
    SubsectionCreateRequest,
    UpdateTitleRequest,
    ReorderSubsectionRequest,
    UpdateNotesRequest,
    UpdateInstructionsRequest,
    ConfigureSubsectionRequest,
    SaveVersionRequest,
)
from ..deps import CurrentUser
from ...generation import generate_subsection as generate_subsection_content
from ...workspace import (
    get_subsection,
    get_version,
    create_subsection,
    update_subsection_title,
    reorder_subsection,
    delete_subsection,
    update_notes,
    update_instructions,
    configure_subsection,
    save_subsection_version,
)

router = APIRouter(prefix="/subsections", tags=["Subsections"])


def check_error(result: dict) -> None:
    """Check for error in workspace function result and raise HTTPException."""
    if "error" in result:
        error_msg = result["error"]
        detail = result if "validation_errors" in result else error_msg
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=detail)
        raise HTTPException(status_code=400, detail=detail)


@router.get("/{subsection_id}")
def get_subsection_endpoint(
    subsection_id: str,
    current_user: CurrentUser,
    include_versions: bool = Query(True, description="Include version history"),
    version_limit: int = Query(10, ge=1, le=50, description="Max versions to return"),
) -> dict:
    """
    Get detailed subsection information including version history.

    Returns full title, position, notes, instructions, current content,
    data source config, and version history.
    """
    result = get_subsection(
        subsection_id=subsection_id,
        include_versions=include_versions,
        version_limit=version_limit,
    )
    check_error(result)
    return result


@router.post("/sections/{section_id}/subsections", status_code=201)
def create_subsection_endpoint(
    section_id: str,
    request: SubsectionCreateRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Create a new subsection in a section.

    Subsections stack vertically within a section and are labeled A, B, C
    based on their position. Use position=null to append at end.
    """
    result = create_subsection(
        section_id=section_id,
        title=request.title,
        position=request.position,
    )
    check_error(result)
    return result


@router.patch("/{subsection_id}/title")
def update_title_endpoint(
    subsection_id: str,
    request: UpdateTitleRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Update the title of a subsection.

    Titles are optional headings displayed above the subsection content.
    Use an empty string to remove the title.
    """
    result = update_subsection_title(
        subsection_id=subsection_id,
        title=request.title,
    )
    check_error(result)
    return result


@router.patch("/{subsection_id}/reorder")
def reorder_subsection_endpoint(
    subsection_id: str,
    request: ReorderSubsectionRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Move a subsection to a new position within its section.

    Changes the A, B, C labeling by updating the position.
    """
    result = reorder_subsection(
        subsection_id=subsection_id,
        new_position=request.new_position,
    )
    check_error(result)
    return result


@router.delete("/{subsection_id}")
def delete_subsection_endpoint(
    subsection_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Delete a subsection.

    Cannot delete the last subsection in a section - delete the section instead.
    Remaining subsections will be reordered to fill the gap.
    """
    result = delete_subsection(subsection_id=subsection_id)
    check_error(result)
    return result


@router.patch("/{subsection_id}/notes")
def update_notes_endpoint(
    subsection_id: str,
    request: UpdateNotesRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Update the notes for a subsection.

    Notes are informal collaboration context. Use append=true to add to
    existing notes instead of replacing them.
    """
    result = update_notes(
        subsection_id=subsection_id,
        notes=request.notes,
        append=request.append,
    )
    check_error(result)
    return result


@router.patch("/{subsection_id}/instructions")
def update_instructions_endpoint(
    subsection_id: str,
    request: UpdateInstructionsRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Update the generation instructions for a subsection.

    Instructions are the formal prompt used to generate content.
    """
    result = update_instructions(
        subsection_id=subsection_id,
        instructions=request.instructions,
    )
    check_error(result)
    return result


@router.patch("/{subsection_id}/config")
def configure_subsection_endpoint(
    subsection_id: str,
    request: ConfigureSubsectionRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Configure a subsection's data source and widget type.

    Sets up which data source to use, retrieval parameters, and how to
    render the content.
    """
    configure_args = {"subsection_id": subsection_id}

    if request.widget_type is not None:
        configure_args["widget_type"] = request.widget_type

    # If the field was provided as null, treat that as an explicit clear.
    if "data_source_config" in request.model_fields_set:
        configure_args["data_source_config"] = (
            request.data_source_config.model_dump() if request.data_source_config else None
        )

    result = configure_subsection(**configure_args)
    check_error(result)
    return result


@router.post("/{subsection_id}/generate")
async def generate_subsection_endpoint(
    subsection_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Generate content for a subsection.

    Generation requires a configured data source configuration with at least one
    valid input. Non-chart widgets also require instructions.
    """
    result = await generate_subsection_content(subsection_id=subsection_id)
    check_error(result)
    return result


@router.post("/{subsection_id}/versions", status_code=201)
def save_version_endpoint(
    subsection_id: str,
    request: SaveVersionRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Save a new version of subsection content.

    Creates a new version in the history and updates current content.
    Optionally set a title for the subsection at the same time.
    Set is_final=true when the user approves the content as complete.
    """
    result = save_subsection_version(
        subsection_id=subsection_id,
        content=request.content,
        content_type=request.content_type,
        generated_by=request.generated_by,
        is_final=request.is_final,
        generation_context=request.generation_context,
        title=request.title,
    )
    check_error(result)
    return result


@router.get("/versions/{version_id}")
def get_version_endpoint(
    version_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Get a specific content version by ID.

    Returns full version content including instructions, notes, and
    generation context from when this version was created.
    """
    result = get_version(version_id=version_id)
    check_error(result)
    return result
