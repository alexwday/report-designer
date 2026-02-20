"""
Generation API routes for Report Designer.
"""

from fastapi import APIRouter, HTTPException

from ..deps import CurrentUser
from ..models import StartGenerationRequest, GenerationRequirementsResponse
from ...generation import start_generation, get_generation_status, get_generation_requirements

router = APIRouter(prefix="/templates", tags=["Generation"])


@router.post("/{template_id}/generate")
async def start_generation_endpoint(
    template_id: str,
    current_user: CurrentUser,
    request: StartGenerationRequest | None = None,
) -> dict:
    """
    Start batch generation for all eligible subsections.

    Returns a job_id that can be used to poll for progress.
    """
    run_inputs = request.run_inputs if request else None
    result = await start_generation(template_id, run_inputs=run_inputs)

    if "error" in result:
        detail = result if "validation_errors" in result else result["error"]
        raise HTTPException(status_code=400, detail=detail)

    return result


@router.get("/{template_id}/generate/requirements", response_model=GenerationRequirementsResponse)
def get_generation_requirements_endpoint(
    template_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Get required run inputs before generation can start.

    This scans configured subsection parameters for variable bindings and
    reports which inputs must be provided for the current run.
    """
    return get_generation_requirements(template_id)


@router.get("/{template_id}/generate/status/{job_id}")
def get_generation_status_endpoint(
    template_id: str,
    job_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Get the current status of a generation job.

    Poll this endpoint to track progress of batch generation.
    """
    status = get_generation_status(job_id)

    if not status:
        raise HTTPException(status_code=404, detail="Generation job not found")

    if status["template_id"] != template_id:
        raise HTTPException(status_code=404, detail="Job not found for this template")

    return status
