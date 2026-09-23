from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import Settings, get_settings
from app.schemas.errors import ErrorResponse
from app.services.resume import latest_resume_pdf

router = APIRouter(tags=["resume"])


@router.get(
    "/resume",
    response_class=FileResponse,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "The newest resume, as a PDF."},
        404: {"model": ErrorResponse, "description": "There is no resume PDF yet."},
    },
)
async def get_resume(settings: Annotated[Settings, Depends(get_settings)]) -> FileResponse:
    """The newest resume PDF, shown inline so the site's resume link can open it in a new tab."""
    path = latest_resume_pdf(settings.knowledge_dir / "resume")
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename="resume.pdf",
        content_disposition_type="inline",
        # Public, so the CDN in front can keep a copy; a new resume goes out with a redeploy anyway.
        headers={"Cache-Control": "public, max-age=3600"},
    )
