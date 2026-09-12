from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health", summary="Service Health Check")
def health_check():
    """Health check endpoint to verify that the surveillance backend is operational."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "step": "STEP 1 - Video and Camera Input Ingestion",
    }
