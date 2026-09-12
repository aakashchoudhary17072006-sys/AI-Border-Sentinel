"""
AI Border Sentinel - Main API Server Entry Point

Consolidated production entry point for Render cloud deployment & local execution.
Provides range-compatible video streaming, real-time telemetry, target tracking,
alert monitoring, health probes, and demo scenario switching.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.api.v1.router import api_router
from app.core.config import settings
from app.services.pipeline_manager import pipeline_manager

app = FastAPI(
    title="AI Border Sentinel API",
    description="Production-ready backend service for AI-based border surveillance, target tracking, and risk analysis.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable Full CORS for Frontend Dashboard Communication
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
        content={
            "success": False,
            "status": "error",
            "error_code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all unexpected error handler."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "status": "error",
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected internal server error occurred while processing the request.",
            "details": {"error": str(exc)},
        },
    )



# Pydantic schema for scenario selection payload
class ScenarioSelectRequest(BaseModel):
    scenario_id: Optional[str] = None
    scenario: Optional[str] = None


@app.get("/", summary="Root Welcome Endpoint")
def root():
    return {
        "status": "online",
        "message": "AI Border Sentinel API running",
        "service": "AI Border Sentinel API",
        "docs": "/docs",
        "active_scenario": pipeline_manager.scenario_manager.active_scenario_id,
        "endpoints": {
            "health": "/api/health",
            "video": "/api/video",
            "telemetry": "/api/telemetry",
            "targets": "/api/targets",
            "alerts": "/api/alerts",
            "scenarios": "/api/scenarios",
            "select_scenario": "/api/select-scenario",
        },
    }


@app.get("/api/health", summary="Health Check")
def get_health():
    """Health check endpoint to verify backend service readiness."""
    return {
        "status": "healthy",
        "service": "AI Border Sentinel API",
        "version": "1.0.0",
        "active_scenario": pipeline_manager.scenario_manager.active_scenario_id,
    }


@app.get("/api/scenarios", summary="Get Available Demo Scenarios")
def get_scenarios():
    """Return list of available surveillance video sequences and scenarios."""
    scenarios = pipeline_manager.scenario_manager.list_scenarios()
    return {
        "success": True,
        "scenarios": scenarios,
        "active_scenario_id": pipeline_manager.scenario_manager.active_scenario_id,
    }


@app.post("/api/select-scenario", summary="Switch Active Demo Scenario")
def select_scenario(payload: Optional[ScenarioSelectRequest] = None, scenario_id: Optional[str] = None):
    """Switch active video feed and reset tracking telemetry state without server restart."""
    target_id = None
    if payload:
        target_id = payload.scenario_id or payload.scenario
    if not target_id and scenario_id:
        target_id = scenario_id

    if not target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide scenario_id in request body or query parameter.",
        )

    success = pipeline_manager.scenario_manager.select_scenario(target_id)
    if not success:
        available = [s["id"] for s in pipeline_manager.scenario_manager.list_scenarios()]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{target_id}' not found. Available scenarios: {available}",
        )

    # Re-initialize pipeline with new scenario video
    pipeline_manager.reset_pipeline()

    return {
        "success": True,
        "message": f"Successfully switched active scenario to '{pipeline_manager.scenario_manager.active_scenario_id}'.",
        "active_scenario_id": pipeline_manager.scenario_manager.active_scenario_id,
        "telemetry": pipeline_manager.get_telemetry(),
    }


@app.get("/api/telemetry", summary="Get Real-Time Telemetry Payload")
def get_telemetry():
    """Returns real-time surveillance statistics, target counts, and risk levels."""
    return pipeline_manager.get_telemetry()


@app.get("/api/targets", summary="Get Active Tracked Targets")
def get_targets():
    """Returns array of active tracked objects with bounding boxes, risk levels, and trajectory."""
    return {
        "success": True,
        "count": len(pipeline_manager.get_targets()),
        "targets": pipeline_manager.get_targets(),
    }


@app.get("/api/alerts", summary="Get Perimeter Alert History")
def get_alerts():
    """Returns history of restricted zone intrusion and wildlife activity alerts."""
    alerts = pipeline_manager.get_alerts()
    return {
        "success": True,
        "count": len(alerts),
        "alerts": alerts,
    }


@app.get("/api/video", summary="Stream Active Surveillance Video (HTTP 206 Range Compatible)")
def stream_video(request: Request):
    """
    HTTP 206 Range-compatible video streaming endpoint.
    Serves the active scenario video (H.264 MP4) with range header seeking support for HTML5 video tags.
    """
    video_path = pipeline_manager.scenario_manager.get_active_video_path()
    if not os.path.exists(video_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active video file not found at path: '{video_path}'",
        )

    file_size = os.path.getsize(video_path)
    range_header = request.headers.get("range")

    if range_header:
        # Parse standard Range: bytes=START-END header
        try:
            bytes_type, bytes_range = range_header.split("=")
            start_str, end_str = bytes_range.split("-")
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
            end = min(end, file_size - 1)
        except Exception:
            start = 0
            end = file_size - 1

        length = end - start + 1

        def file_iterator():
            with open(video_path, "rb") as video_file:
                video_file.seek(start)
                bytes_remaining = length
                chunk_size = 1024 * 512  # 512KB chunks
                while bytes_remaining > 0:
                    read_size = min(chunk_size, bytes_remaining)
                    chunk = video_file.read(read_size)
                    if not chunk:
                        break
                    bytes_remaining -= len(chunk)
                    yield chunk

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
            "Content-Type": "video/mp4",
        }
        return StreamingResponse(file_iterator(), status_code=206, headers=headers)
    else:
        return FileResponse(
            path=video_path,
            media_type="video/mp4",
            filename=os.path.basename(video_path),
        )


# Include API v1 router for backward compatibility
app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"[*] Launching AI Border Sentinel API on port {port}...")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
