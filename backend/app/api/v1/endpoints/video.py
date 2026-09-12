from typing import List
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.models.schemas import ErrorResponse, VideoUploadResponse
from app.services.video_service import VideoService

router = APIRouter()


@router.post(
    "/video",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Ingest Video",
    description="Upload a video file (MP4, AVI, MOV, MKV). Validates format, stream integrity via OpenCV, saves under unique ID, and returns metadata.",
    responses={
        201: {"model": VideoUploadResponse, "description": "Video uploaded and metadata extracted"},
        400: {"model": ErrorResponse, "description": "Invalid format or unreadable video file"},
        413: {"model": ErrorResponse, "description": "File exceeds maximum upload size"},
        422: {"description": "Missing file in multipart form payload"},
    },
)
async def upload_video(
    file: UploadFile = File(..., description="Video file to ingest (supported: .mp4, .avi, .mov, .mkv)")
) -> VideoUploadResponse:
    """Accepts a video upload and processes it through the video ingestion service."""
    return await VideoService.process_video_upload(file)


@router.get(
    "/video/{video_id}",
    response_model=VideoUploadResponse,
    summary="Get Uploaded Video Metadata",
    description="Retrieve stored metadata and status for a previously uploaded video by ID.",
    responses={
        200: {"model": VideoUploadResponse, "description": "Video details retrieved"},
        404: {"model": ErrorResponse, "description": "Video not found"},
    },
)
def get_video_details(video_id: str) -> VideoUploadResponse:
    video_record = VideoService.get_video_by_id(video_id)
    if not video_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with ID '{video_id}' not found.",
        )
    return video_record


@router.get(
    "/videos",
    response_model=List[VideoUploadResponse],
    summary="List Uploaded Videos",
    description="List all video files ingested during the current server lifecycle.",
)
def list_uploaded_videos() -> List[VideoUploadResponse]:
    return list(VideoService.list_videos().values())
