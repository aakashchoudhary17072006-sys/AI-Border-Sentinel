import os
import shutil
from pathlib import Path
from typing import Dict, Optional
import cv2
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.models.schemas import VideoMetadata, VideoUploadResponse
from app.utils.file_utils import (
    generate_video_id,
    get_safe_relative_path,
    is_allowed_extension,
    sanitize_filename,
)


class VideoService:
    """Service handling video upload ingestion, validation, and stream inspection."""

    # In-memory registry of uploaded video records for querying in Step 1
    _video_registry: Dict[str, VideoUploadResponse] = {}

    @classmethod
    async def process_video_upload(cls, file: UploadFile) -> VideoUploadResponse:
        """
        Ingest an uploaded video file:
        1. Validate filename and extension.
        2. Stream file content safely to server storage.
        3. Validate video readability using OpenCV video stream decoder.
        4. Extract video properties (FPS, resolution, duration).
        5. Return structured metadata.
        """
        original_filename = file.filename or "unknown_video.mp4"

        # 1. Extension validation
        if not is_allowed_extension(original_filename):
            allowed = ", ".join(settings.ALLOWED_EXTENSIONS)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format for '{original_filename}'. Supported video formats: {allowed}",
            )

        # 2. Generate collision-resistant unique ID & filename
        video_id = generate_video_id()
        saved_filename = sanitize_filename(original_filename, video_id)
        destination_path = settings.UPLOAD_DIR / saved_filename

        # 3. Stream upload chunks to destination
        total_bytes = 0
        try:
            with destination_path.open("wb") as buffer:
                while chunk := await file.read(1024 * 1024):  # 1MB chunks
                    total_bytes += len(chunk)
                    if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File exceeds maximum allowed upload size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB.",
                        )
                    buffer.write(chunk)
        except Exception as e:
            # Clean up partial file on failure
            if destination_path.exists():
                destination_path.unlink()
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save uploaded video: {str(e)}",
            )
        finally:
            await file.close()

        # Check for empty file
        if total_bytes == 0:
            if destination_path.exists():
                destination_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes). Please upload a valid video.",
            )

        # 4. Validate and decode video with OpenCV
        metadata = cls._extract_video_metadata(destination_path)
        if metadata is None:
            # Invalid or corrupt video stream - delete immediately
            if destination_path.exists():
                destination_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not a valid video or could not be decoded. Ensure the file contains a playable video stream.",
            )

        # 5. Build structured response
        safe_path = get_safe_relative_path(destination_path)
        response_data = VideoUploadResponse(
            success=True,
            status="ready",
            video_id=video_id,
            filename=saved_filename,
            original_filename=original_filename,
            video_path=safe_path,
            metadata=metadata,
            message="Video successfully uploaded, validated, and ready for analysis",
        )

        # Store in registry
        cls._video_registry[video_id] = response_data
        return response_data

    @staticmethod
    def _extract_video_metadata(video_path: Path) -> Optional[VideoMetadata]:
        """
        Open video with OpenCV to verify stream integrity and extract parameters.
        Returns VideoMetadata on success, None if corrupted or non-video.
        """
        cap = cv2.VideoCapture(str(video_path))
        try:
            if not cap.isOpened():
                return None

            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
            codec = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)]).strip()

            # Attempt to read at least the first frame to ensure decoder works
            ret, frame = cap.read()
            if not ret or frame is None or frame.size == 0:
                return None

            # Fallback calculations if frame_count or fps is missing/invalid
            safe_fps = round(fps, 2) if fps and fps > 0 else 25.0
            safe_frame_count = frame_count if frame_count > 0 else 1
            duration_seconds = round(safe_frame_count / safe_fps, 2)

            return VideoMetadata(
                fps=safe_fps,
                width=width,
                height=height,
                frame_count=safe_frame_count,
                duration_seconds=duration_seconds,
                codec=codec or "unknown",
            )
        except Exception:
            return None
        finally:
            cap.release()

    @classmethod
    def get_video_by_id(cls, video_id: str) -> Optional[VideoUploadResponse]:
        """Retrieve stored metadata for an uploaded video."""
        return cls._video_registry.get(video_id)

    @classmethod
    def list_videos(cls) -> Dict[str, VideoUploadResponse]:
        """Retrieve all registered uploaded videos."""
        return cls._video_registry
