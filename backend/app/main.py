from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.models.schemas import ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler: runs on startup and shutdown."""
    # Ensure storage paths exist
    settings.ensure_directories()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Production-oriented backend for AI-based surveillance system (Night/Border-area monitoring). "
        "STEP 1: Video and Camera Input ingestion pipeline."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Standardized JSON error handler for HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            status="error",
            error_code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all unexpected error handler."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            status="error",
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred while processing the request.",
            details={"error": str(exc)} if settings.DEBUG else None,
        ).model_dump(),
    )


# Register API Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", summary="Root Welcome Endpoint")
def root():
    return {
        "message": "AI Surveillance System Backend - STEP 1 (Video/Camera Input)",
        "docs": "/docs",
        "api_version": "v1",
        "endpoints": {
            "health": f"{settings.API_V1_STR}/health",
            "video_upload": f"{settings.API_V1_STR}/input/video",
            "video_list": f"{settings.API_V1_STR}/input/videos",
            "camera_status": f"{settings.API_V1_STR}/input/camera/status",
        },
    }
