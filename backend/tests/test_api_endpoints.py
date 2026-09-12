"""
Unit tests for AI Border Sentinel unified FastAPI backend endpoints.
Validates health check, demo scenarios, scenario selection, telemetry, target listing,
alert history, and video streaming HTTP 206 response.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_root_and_health_endpoints(client):
    """Test root and /api/health response."""
    resp_root = client.get("/")
    assert resp_root.status_code == 200
    assert resp_root.json()["service"] == "AI Border Sentinel API"

    resp_health = client.get("/api/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "healthy"


def test_scenarios_and_select_scenario(client):
    """Test /api/scenarios listing and /api/select-scenario dynamic switching."""
    resp_list = client.get("/api/scenarios")
    assert resp_list.status_code == 200
    data = resp_list.json()
    assert data["success"] is True
    assert "scenarios" in data
    assert len(data["scenarios"]) > 0

    sc_id = data["scenarios"][0]["id"]
    resp_select = client.post("/api/select-scenario", json={"scenario_id": sc_id})
    assert resp_select.status_code == 200
    res_data = resp_select.json()
    assert res_data["success"] is True
    assert res_data["active_scenario_id"] == sc_id


def test_telemetry_targets_alerts_endpoints(client):
    """Test /api/telemetry, /api/targets, and /api/alerts payloads."""
    resp_telem = client.get("/api/telemetry")
    assert resp_telem.status_code == 200
    telem = resp_telem.json()
    assert telem["status"] == "OPERATIONAL"
    assert "targets" in telem
    assert "risk_summary" in telem

    resp_targets = client.get("/api/targets")
    assert resp_targets.status_code == 200
    assert "targets" in resp_targets.json()

    resp_alerts = client.get("/api/alerts")
    assert resp_alerts.status_code == 200
    assert "alerts" in resp_alerts.json()


def test_video_stream_range_request(client):
    """Test /api/video HTTP 206 Partial Content range request."""
    # Test without Range header
    resp = client.get("/api/video")
    assert resp.status_code in (200, 206)

    # Test with Range header
    headers = {"Range": "bytes=0-1023"}
    resp_range = client.get("/api/video", headers=headers)
    assert resp_range.status_code == 206
    assert "Content-Range" in resp_range.headers
    assert resp_range.headers["Content-Type"] == "video/mp4"
