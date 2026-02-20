"""
Export API routes for Report Designer.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..deps import CurrentUser
from ...export import get_preview_data, generate_pdf

router = APIRouter(prefix="/templates", tags=["Export"])


@router.get("/{template_id}/preview")
def get_preview_endpoint(
    template_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Get assembled template data for preview.

    Returns template metadata and all sections with subsections
    ordered by position, ready for rendering in the frontend preview.
    """
    result = get_preview_data(template_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/{template_id}/export/pdf")
def export_pdf_endpoint(
    template_id: str,
    current_user: CurrentUser,
) -> Response:
    """
    Generate and download PDF export of the template.

    Returns PDF file as binary response.
    """
    try:
        pdf_bytes, filename = generate_pdf(template_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
