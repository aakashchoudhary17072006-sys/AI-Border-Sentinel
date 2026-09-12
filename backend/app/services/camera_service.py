from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import uuid
import cv2

from app.models.schemas import (
    CameraConnectRequest,
    CameraConnectResponse,
    CameraStatusResponse,
)


class BaseCameraStream(ABC):
    """Abstract interface for video capture sources (Webcam, RTSP, IP Cameras)."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection with the video camera or stream source."""
        pass

    @abstractmethod
    def read_frame(self) -> Optional[Any]:
        """Read a single frame from the camera stream."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Release camera resource and cleanup drivers/connections."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Return boolean status of active stream connection."""
        pass


class OpenCVCameraStream(BaseCameraStream):
    """Concrete camera stream implementation wrapping OpenCV VideoCapture."""

    def __init__(self, source: str = "0"):
        # If source is integer string (e.g. '0'), convert to int for webcam index
        self.source: Any = int(source) if source.isdigit() else source
        self.capture: Optional[cv2.VideoCapture] = None
        self._is_connected: bool = False

    def connect(self) -> bool:
        try:
            self.capture = cv2.VideoCapture(self.source)
            if self.capture.isOpened():
                self._is_connected = True
                return True
            self._is_connected = False
            return False
        except Exception:
            self._is_connected = False
            return False

    def read_frame(self) -> Optional[Any]:
        if not self._is_connected or not self.capture:
            return None
        ret, frame = self.capture.read()
        return frame if ret else None

    def release(self) -> None:
        if self.capture:
            self.capture.release()
            self.capture = None
        self._is_connected = False

    def is_connected(self) -> bool:
        return self._is_connected and (self.capture is not None and self.capture.isOpened())


class CameraService:
    """
    Service managing live camera connections, hardware probe, and stream interface.
    
    STEP 1 SCOPE:
    - Provides architecture & interface for live camera/webcam ingestion.
    - Probes camera availability and returns hardware status/details.
    
    STEP 2 HANDOFF:
    - Continuous frame generator loop, WebSocket/MJPEG stream broadcast,
      and YOLO person detection hook directly into read_frame().
    """

    _active_streams: Dict[str, BaseCameraStream] = {}

    @classmethod
    def check_camera_status(cls, source: str = "0") -> CameraStatusResponse:
        """
        Probe a camera source (hardware index or stream URI) to inspect availability
        without locking the camera device permanently.
        """
        src_val: Any = int(source) if source.isdigit() else source
        cap = cv2.VideoCapture(src_val)
        is_open = False
        details = {}

        try:
            is_open = cap.isOpened()
            if is_open:
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                details = {
                    "width": width,
                    "height": height,
                    "fps": round(fps, 2) if fps > 0 else 30.0,
                    "type": "hardware_webcam" if str(source).isdigit() else "network_stream",
                }
        except Exception as e:
            is_open = False
            details = {"error": str(e)}
        finally:
            cap.release()

        message = (
            "Camera source is detected and accessible for live monitoring"
            if is_open
            else "Camera device not detected or currently inaccessible. Service interface is ready for live stream input."
        )

        return CameraStatusResponse(
            success=True,
            is_available=is_open,
            source=source,
            backend_mode="ready_for_stream",
            details=details,
            message=message,
        )

    @classmethod
    def connect_camera(cls, request: CameraConnectRequest) -> CameraConnectResponse:
        """
        Register and connect a camera stream interface.
        """
        stream_id = f"stream_{uuid.uuid4().hex[:8]}"
        stream = OpenCVCameraStream(source=request.source)
        connected = stream.connect()

        if connected:
            cls._active_streams[stream_id] = stream
            msg = f"Camera '{request.stream_name}' connected successfully with stream ID {stream_id}."
        else:
            stream.release()
            msg = f"Camera '{request.stream_name}' interface initialized in standby mode (camera source {request.source} unavailable)."

        return CameraConnectResponse(
            success=True,
            stream_id=stream_id,
            source=request.source,
            is_connected=connected,
            message=msg,
        )

    @classmethod
    def release_stream(cls, stream_id: str) -> bool:
        """Disconnect and release a specific stream."""
        if stream_id in cls._active_streams:
            cls._active_streams[stream_id].release()
            del cls._active_streams[stream_id]
            return True
        return False
