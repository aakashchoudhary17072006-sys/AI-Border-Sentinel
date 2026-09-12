from typing import Optional
from pydantic import BaseModel, Field


class VideoMetadata(BaseModel):
    """Extracted video metadata using OpenCV video stream decoder."""
    fps: float = Field(..., description="Frames per second")
    width: int = Field(..., description="Video frame width in pixels")
    height: int = Field(..., description="Video frame height in pixels")
    frame_count: int = Field(..., description="Total number of frames in the video")
    duration_seconds: float = Field(..., description="Calculated duration of video in seconds")
    codec: Optional[str] = Field(None, description="FourCC codec identifier if available")


class VideoUploadResponse(BaseModel):
    """Structured response returned after a successful video upload."""
    success: bool = Field(True, description="Indicates whether the upload and validation succeeded")
    status: str = Field("ready", description="Current status of the ingested video (ready, processing, failed)")
    video_id: str = Field(..., description="Unique collision-resistant identifier for the video")
    filename: str = Field(..., description="Sanitized unique filename on server storage")
    original_filename: str = Field(..., description="Original filename provided by client")
    video_path: str = Field(..., description="Sanitized relative access reference for the video")
    metadata: VideoMetadata = Field(..., description="Extracted video stream parameters")
    message: str = Field("Video uploaded and validated successfully", description="Informational message")


class CameraStatusResponse(BaseModel):
    """Live camera/stream status response."""
    success: bool = Field(True, description="Whether camera status was retrieved")
    is_available: bool = Field(..., description="Whether a local camera or configured stream is accessible")
    source: str = Field(..., description="Camera device index (e.g., '0') or stream URL/RTSP")
    backend_mode: str = Field("ready_for_stream", description="Current camera service state")
    details: dict = Field(default_factory=dict, description="Camera properties if available (e.g. resolution, fps)")
    message: str = Field(..., description="Status description or next-step integration note")


class CameraConnectRequest(BaseModel):
    """Request payload to connect or configure a camera/video stream."""
    source: str = Field("0", description="Webcam device index (e.g. '0', '1') or RTSP/HTTP stream URL")
    stream_name: Optional[str] = Field("Live Monitor 1", description="Friendly identifier for this camera stream")


class CameraConnectResponse(BaseModel):
    """Response returned upon connecting or registering a camera stream."""
    success: bool
    stream_id: str
    source: str
    is_connected: bool
    message: str


class ErrorResponse(BaseModel):
    """Standardized error response payload."""
    success: bool = Field(False, description="Failure indicator")
    status: str = Field("error", description="Error state")
    error_code: str = Field(..., description="Machine-readable error classification")
    message: str = Field(..., description="Human-readable explanation of error")
    details: Optional[dict] = Field(None, description="Optional extra error details")
