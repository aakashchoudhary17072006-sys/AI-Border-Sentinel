import pytest
from fastapi import status


def test_health_check(client):
    """Test the backend health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert "surveillance" in data["service"].lower()


def test_valid_video_upload(client, sample_valid_video):
    """Test uploading a genuine video file and verifying extracted metadata."""
    with open(sample_valid_video, "rb") as f:
        response = client.post(
            "/api/v1/input/video",
            files={"file": ("test_sample.mp4", f, "video/mp4")},
        )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "ready"
    assert "video_id" in data
    assert data["video_id"].startswith("vid_")
    assert "filename" in data
    assert "video_path" in data
    # Ensure absolute filesystem paths are NOT exposed
    assert "C:" not in data["video_path"]
    assert "\\" not in data["video_path"]

    # Verify metadata fields
    metadata = data["metadata"]
    assert metadata["width"] == 320
    assert metadata["height"] == 240
    assert metadata["frame_count"] == 10
    assert metadata["fps"] > 0
    assert metadata["duration_seconds"] > 0

    # Verify the video can be retrieved by video_id
    video_id = data["video_id"]
    get_res = client.get(f"/api/v1/input/video/{video_id}")
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["video_id"] == video_id


def test_invalid_disallowed_extension(client, sample_disallowed_file):
    """Test uploading a file with an unsupported extension (e.g. .txt)."""
    with open(sample_disallowed_file, "rb") as f:
        response = client.post(
            "/api/v1/input/video",
            files={"file": ("document.txt", f, "text/plain")},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["success"] is False
    assert "Unsupported file format" in data["message"]


def test_invalid_corrupted_video_stream(client, sample_invalid_video):
    """Test uploading a file with .mp4 extension but corrupted/non-video bytes."""
    with open(sample_invalid_video, "rb") as f:
        response = client.post(
            "/api/v1/input/video",
            files={"file": ("corrupt_video.mp4", f, "video/mp4")},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["success"] is False
    assert "not a valid video" in data["message"]


def test_missing_file_payload(client):
    """Test sending a POST request to video upload without providing a file."""
    response = client.post("/api/v1/input/video", data={})
    assert response.status_code == 422


def test_get_nonexistent_video(client):
    """Test querying a video ID that does not exist."""
    response = client.get("/api/v1/input/video/non_existent_id")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_camera_status_endpoint(client):
    """Test the camera hardware/stream probe endpoint."""
    response = client.get("/api/v1/input/camera/status?source=0")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert "is_available" in data
    assert data["backend_mode"] == "ready_for_stream"
    assert "message" in data


def test_camera_connect_endpoint(client):
    """Test connecting camera stream interface."""
    response = client.post(
        "/api/v1/input/camera/connect",
        json={"source": "0", "stream_name": "Test Camera 1"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert "stream_id" in data
    assert data["source"] == "0"
