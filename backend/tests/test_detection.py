"""
Unit tests for Step 2: YOLO Object-Detection Module.
Validates detector initialization, structured output formatting, category mapping,
and frame annotation without regressions.
"""

from pathlib import Path
import cv2
import numpy as np
import pytest

from detection.detector import (
    CATEGORY_ANIMAL,
    CATEGORY_HUMAN,
    CATEGORY_VEHICLE,
    YOLODetector,
)


@pytest.fixture(scope="session")
def detector():
    """Initializes a shared YOLODetector instance using yolov8n.pt."""
    return YOLODetector(model_name="yolov8n.pt", conf_threshold=0.30)


def test_category_mappings(detector):
    """Test COCO class categorization into human, animal, vehicle."""
    assert detector.get_category("person") == CATEGORY_HUMAN
    assert detector.get_category("dog") == CATEGORY_ANIMAL
    assert detector.get_category("cat") == CATEGORY_ANIMAL
    assert detector.get_category("horse") == CATEGORY_ANIMAL
    assert detector.get_category("car") == CATEGORY_VEHICLE
    assert detector.get_category("truck") == CATEGORY_VEHICLE
    assert detector.get_category("motorcycle") == CATEGORY_VEHICLE
    assert detector.get_category("bus") == CATEGORY_VEHICLE
    # Items outside border surveillance scope should return None
    assert detector.get_category("backpack") is None
    assert detector.get_category("chair") is None


def test_empty_frame_handling(detector):
    """Test detector gracefully returns empty list for empty/None frames."""
    assert detector.detect_frame(None) == []
    assert detector.detect_frame(np.array([])) == []


def test_detect_frame_structured_output(detector):
    """
    Test detection output structure matches Step 2 requirements:
    - class_name
    - category (human/animal/vehicle)
    - confidence (float between 0 and 1)
    - bbox: [x1, y1, x2, y2]
    - center: [cx, cy]
    """
    import ultralytics

    assets_dir = Path(ultralytics.__file__).parent / "assets"
    bus_img_path = assets_dir / "bus.jpg"
    assert bus_img_path.exists(), "Test asset bus.jpg missing"

    img = cv2.imread(str(bus_img_path))
    assert img is not None

    detections = detector.detect_frame(img)
    assert len(detections) > 0, "Expected detections on test asset"

    for det in detections:
        # 1. Check required dictionary keys
        assert "class_name" in det
        assert "category" in det
        assert "confidence" in det
        assert "bbox" in det
        assert "center" in det

        # 2. Check types and values
        assert isinstance(det["class_name"], str)
        assert det["category"] in {CATEGORY_HUMAN, CATEGORY_ANIMAL, CATEGORY_VEHICLE}
        assert 0.0 <= det["confidence"] <= 1.0
        assert len(det["bbox"]) == 4
        assert len(det["center"]) == 2

        # 3. Check bounding box geometry
        x1, y1, x2, y2 = det["bbox"]
        assert x1 < x2
        assert y1 < y2

        # 4. Check center point calculation
        expected_cx = int((x1 + x2) / 2)
        expected_cy = int((y1 + y2) / 2)
        assert det["center"] == [expected_cx, expected_cy]


def test_draw_detections(detector):
    """Test rendering bounding boxes, labels, and HUD onto a frame."""
    h, w = 480, 640
    blank_frame = np.zeros((h, w, 3), dtype=np.uint8)

    mock_detections = [
        {
            "class_name": "person",
            "category": CATEGORY_HUMAN,
            "confidence": 0.94,
            "bbox": [50, 60, 180, 320],
            "center": [115, 190],
        },
        {
            "class_name": "dog",
            "category": CATEGORY_ANIMAL,
            "confidence": 0.88,
            "bbox": [220, 200, 310, 310],
            "center": [265, 255],
        },
        {
            "class_name": "truck",
            "category": CATEGORY_VEHICLE,
            "confidence": 0.91,
            "bbox": [340, 120, 580, 380],
            "center": [460, 250],
        },
    ]

    annotated = detector.draw_detections(blank_frame, mock_detections, show_center=True, show_hud=True)
    assert annotated is not None
    assert annotated.shape == (h, w, 3)
    # Check that pixels were altered from black
    assert np.any(annotated > 0)
