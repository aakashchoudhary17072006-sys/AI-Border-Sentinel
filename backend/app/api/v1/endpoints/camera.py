from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import (
    CameraConnectRequest,
    CameraConnectResponse,
    CameraStatusResponse,
)
from app.services.camera_service import CameraService

router = APIRouter()


@router.get(
    "/camera/status",
    response_model=CameraStatusResponse,
    summary="Probe Camera / Live Stream Status",
    description="Probes local webcam device index or RTSP/stream URL to check connectivity and capture properties.",
)
def get_camera_status(
    source: str = Query("0", description="Webcam device index (e.g. '0') or network stream URL (RTSP/HTTP)")
) -> CameraStatusResponse:
    """Check whether a camera device or stream source is accessible."""
    return CameraService.check_camera_status(source=source)


@router.post(
    "/camera/connect",
    response_model=CameraConnectResponse,
    summary="Connect / Initialize Camera Stream",
    description="Initializes camera stream capture session using the modular BaseCameraStream architecture.",
)
def connect_camera_stream(request: CameraConnectRequest) -> CameraConnectResponse:
    """Connect a camera stream and allocate an active stream handle."""
    return CameraService.connect_camera(request)


@router.delete(
    "/camera/{stream_id}",
    summary="Release Camera Stream",
    description="Releases and cleans up an active camera stream session.",
)
def release_camera_stream(stream_id: str):
    released = CameraService.release_stream(stream_id)
    if not released:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active stream with ID '{stream_id}' not found.",
        )
    return {"success": True, "message": f"Stream '{stream_id}' disconnected and released."}
