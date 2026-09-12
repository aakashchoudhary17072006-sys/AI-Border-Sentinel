import os
import sys
import tempfile
from pathlib import Path
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.main import app
from app.core.config import settings


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient session fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_valid_video():
    """
    Creates a small, valid synthetic MP4 video file (10 frames, 320x240, 10 fps)
    for automated testing, and cleans it up after the test.
    """
    temp_dir = tempfile.mkdtemp()
    video_path = Path(temp_dir) / "test_sample.mp4"

    width, height, fps, num_frames = 320, 240, 10.0, 10
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))

    for i in range(num_frames):
        # Generate a test frame with changing gradient
        frame = np.full((height, width, 3), (i * 20) % 255, dtype=np.uint8)
        out.write(frame)
    out.release()

    yield video_path

    # Teardown: remove generated temp video
    if video_path.exists():
        video_path.unlink()
    try:
        os.rmdir(temp_dir)
    except OSError:
        pass


@pytest.fixture
def sample_invalid_video():
    """
    Creates an invalid file disguised with a .mp4 extension
    (plain text content, not a valid video stream).
    """
    temp_dir = tempfile.mkdtemp()
    fake_path = Path(temp_dir) / "corrupt_video.mp4"
    fake_path.write_text("This is NOT a valid video stream, just plain text.")

    yield fake_path

    if fake_path.exists():
        fake_path.unlink()
    try:
        os.rmdir(temp_dir)
    except OSError:
        pass


@pytest.fixture
def sample_disallowed_file():
    """Creates a file with a disallowed extension (e.g. .txt)."""
    temp_dir = tempfile.mkdtemp()
    txt_path = Path(temp_dir) / "document.txt"
    txt_path.write_text("Disallowed file format content.")

    yield txt_path

    if txt_path.exists():
        txt_path.unlink()
    try:
        os.rmdir(temp_dir)
    except OSError:
        pass
