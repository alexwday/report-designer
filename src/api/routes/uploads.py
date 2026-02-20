"""
File uploads API routes for Report Designer.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from ..deps import CurrentUser
from ...uploads import save_upload, get_upload, list_uploads, delete_upload

router = APIRouter(prefix="/templates", tags=["Uploads"])


@router.post("/{template_id}/uploads")
async def upload_file_endpoint(
    template_id: str,
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> dict:
    """
    Upload a file to reference in content generation.

    Supported file types:
    - PDF (.pdf)
    - Plain text (.txt)
    - Markdown (.md)
    - CSV (.csv)
    - Word documents (.docx)

    Text will be automatically extracted for AI reference.
    Maximum file size: 10MB.
    """
    result = save_upload(
        template_id=template_id,
        file_data=file.file,
        original_filename=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/{template_id}/uploads")
def list_uploads_endpoint(
    template_id: str,
    current_user: CurrentUser,
) -> list[dict]:
    """
    List all uploaded files for a template.

    Returns metadata including extraction status.
    """
    return list_uploads(template_id)


@router.get("/{template_id}/uploads/{upload_id}")
def get_upload_endpoint(
    template_id: str,
    upload_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Get metadata for a specific upload.
    """
    result = get_upload(upload_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    if result.get("template_id") != template_id:
        raise HTTPException(status_code=404, detail="Upload not found for this template")

    return result


@router.delete("/{template_id}/uploads/{upload_id}")
def delete_upload_endpoint(
    template_id: str,
    upload_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Delete an uploaded file.

    Removes both the file and its database record.
    """
    # First verify upload belongs to template
    upload = get_upload(upload_id)
    if "error" in upload:
        raise HTTPException(status_code=404, detail=upload["error"])

    if upload.get("template_id") != template_id:
        raise HTTPException(status_code=404, detail="Upload not found for this template")

    result = delete_upload(upload_id)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result
