"""
Unit tests for Step 4: Movement and Observable Behaviour Analysis Module.
Validates direction calculations, noise filtering, image-space speed,
cumulative distance, direction change counting, movement status classification,
and Step 5 contract schema.
"""

import pytest
from analysis.movement import (
    DIRECTION_DOWN,
    DIRECTION_DOWN_LEFT,
    DIRECTION_DOWN_RIGHT,
    DIRECTION_LEFT,
    DIRECTION_RIGHT,
    DIRECTION_STATIONARY,
    DIRECTION_UP,
    DIRECTION_UP_LEFT,
    DIRECTION_UP_RIGHT,
    MovementAnalyzer,
    STATUS_DIRECTION_CHANGING,
    STATUS_FAST_MOVING,
    STATUS_MOVING,
    STATUS_STATIONARY,
    TrackMovementProfile,
)


def test_direction_calculations():
    """Verify all 8 compass directions and STATIONARY with noise threshold."""
    prof = TrackMovementProfile(track_id=1, initial_center=[500, 500])

    # 1. Very small displacement (< 2.5px) -> STATIONARY
    prof.update([501, 500], noise_threshold_px=2.5)
    assert prof.current_direction == DIRECTION_STATIONARY

    # 2. Moving RIGHT (dx > 0, dy = 0)
    prof.update([530, 500], noise_threshold_px=2.5)
    assert prof.current_direction == DIRECTION_RIGHT

    # 3. Moving LEFT (dx < 0, dy = 0)
    prof.update([470, 500], noise_threshold_px=2.5)
    assert prof.current_direction == DIRECTION_LEFT

    # 4. Moving UP (dx = 0, dy < 0 in image space)
    prof.update([500, 460], noise_threshold_px=2.5)
    assert prof.current_direction == DIRECTION_UP

    # 5. Moving DOWN (dx = 0, dy > 0 in image space)
    prof.update([500, 540], noise_threshold_px=2.5)
    assert prof.current_direction == DIRECTION_DOWN

    # 6. Diagonal: UP-RIGHT (dx > 0, dy < 0)
    prof.update([540, 460], noise_threshold_px=2.5)
    assert prof.current_direction == DIRECTION_UP_RIGHT

    # 7. Diagonal: UP-LEFT (dx < 0, dy < 0)
    prof.update([460, 460], noise_threshold_px=2.5)
    assert prof.current_direction == DIRECTION_UP_LEFT

    # 8. Diagonal: DOWN-RIGHT (dx > 0, dy > 0)
    prof.update([540, 540], noise_threshold_px=2.5)
    assert prof.current_direction == DIRECTION_DOWN_RIGHT

    # 9. Diagonal: DOWN-LEFT (dx < 0, dy > 0)
    prof.update([460, 540], noise_threshold_px=2.5)
    assert prof.current_direction == DIRECTION_DOWN_LEFT


def test_speed_and_distance_accumulation():
    """Verify image-space speed (px/frame) and cumulative distance calculations."""
    analyzer = MovementAnalyzer(history_window=3)

    # Simulate an object moving 10 pixels to the right each frame
    coords = [[100, 200], [110, 200], [120, 200], [130, 200]]
    for f_idx, center in enumerate(coords):
        mock_track = [
            {
                "track_id": 1,
                "category": "human",
                "class_name": "person",
                "confidence": 0.92,
                "bbox": [center[0] - 20, center[1] - 40, center[0] + 20, center[1] + 40],
                "center": center,
                "frame_number": f_idx + 1,
                "trajectory": coords[: f_idx + 1],
            }
        ]
        results = analyzer.analyze_tracks(mock_track)

    res = results[0]
    # Total distance moved: 10 + 10 + 10 = 30.0 pixels
    assert res["distance_travelled_px"] == 30.0
    # Average speed should be ~10.0 pixels per frame
    assert 9.5 <= res["estimated_speed_px_per_frame"] <= 10.5
    assert res["movement_direction"] == DIRECTION_RIGHT
    assert res["frames_observed"] == 4


def test_direction_changes_counter():
    """Verify direction change counter increments on confirmed direction reversals."""
    prof = TrackMovementProfile(track_id=1, initial_center=[100, 100], window_size=2)

    # Move RIGHT
    prof.update([120, 100])
    # Continue RIGHT (no direction change)
    prof.update([140, 100])
    assert prof.direction_changes == 0

    # Turn DOWN (1st direction change)
    prof.update([140, 130])
    assert prof.direction_changes == 1

    # Turn LEFT (2nd direction change)
    prof.update([110, 130])
    assert prof.direction_changes == 2


def test_movement_status_classification():
    """Verify objective movement status classification."""
    analyzer = MovementAnalyzer(fast_speed_threshold_px=7.0)

    # 1. STATIONARY (speed < 1.5)
    mock_stat = [
        {
            "track_id": 1,
            "category": "human",
            "class_name": "person",
            "confidence": 0.9,
            "bbox": [100, 100, 150, 150],
            "center": [125, 125],
        }
    ]
    analyzer.analyze_tracks(mock_stat)
    mock_stat[0]["center"] = [125, 126]  # 1px step
    res_stat = analyzer.analyze_tracks(mock_stat)
    assert res_stat[0]["movement_status"] == STATUS_STATIONARY

    # 2. FAST_MOVING (speed >= 7.0)
    mock_fast = [
        {
            "track_id": 2,
            "category": "vehicle",
            "class_name": "car",
            "confidence": 0.88,
            "bbox": [200, 200, 280, 250],
            "center": [240, 225],
        }
    ]
    analyzer.analyze_tracks(mock_fast)
    mock_fast[0]["center"] = [255, 225]  # 15px step
    res_fast = analyzer.analyze_tracks(mock_fast)
    assert res_fast[0]["movement_status"] == STATUS_FAST_MOVING


def test_multi_category_support():
    """Verify identical movement analysis runs for human, animal, and vehicle."""
    analyzer = MovementAnalyzer()

    mock_tracks = [
        {
            "track_id": 1,
            "category": "human",
            "class_name": "person",
            "confidence": 0.94,
            "bbox": [50, 50, 100, 150],
            "center": [75, 100],
        },
        {
            "track_id": 2,
            "category": "animal",
            "class_name": "dog",
            "confidence": 0.87,
            "bbox": [200, 200, 250, 250],
            "center": [225, 225],
        },
        {
            "track_id": 3,
            "category": "vehicle",
            "class_name": "truck",
            "confidence": 0.91,
            "bbox": [400, 400, 550, 500],
            "center": [475, 450],
        },
    ]

    results = analyzer.analyze_tracks(mock_tracks)
    assert len(results) == 3
    categories = {r["category"] for r in results}
    assert categories == {"human", "animal", "vehicle"}


def test_step5_contract_schema():
    """Verify all fields required for Step 5 threat engine exist in output dictionary."""
    analyzer = MovementAnalyzer()
    mock_track = [
        {
            "track_id": 10,
            "category": "human",
            "class_name": "person",
            "confidence": 0.95,
            "bbox": [100, 100, 150, 200],
            "center": [125, 150],
            "trajectory": [[120, 145], [125, 150]],
        }
    ]

    results = analyzer.analyze_tracks(mock_track)
    assert len(results) == 1
    record = results[0]

    required_keys = [
        "track_id",
        "category",
        "class_name",
        "confidence",
        "bbox",
        "center",
        "movement_direction",
        "estimated_speed_px_per_frame",
        "distance_travelled_px",
        "direction_changes",
        "frames_observed",
        "movement_status",
        "trajectory",
    ]

    for key in required_keys:
        assert key in record, f"Missing required Step 5 key: {key}"

    # Verify no subjective/emotional fields are present
    disallowed_keys = ["emotion", "mood", "suspiciousness", "threat_score", "risk"]
    for d_key in disallowed_keys:
        assert d_key not in record, f"Subjective field '{d_key}' should not be present in Step 4"
