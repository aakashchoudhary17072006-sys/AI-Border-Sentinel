"""
Unit tests for Step 3: ByteTrack Multi-Object Tracking Module.
Validates ID generation, ID persistence, trajectory accumulation, occlusion recovery,
and structured output format without regression.
"""

import pytest
from tracking.tracker import ByteTracker, STrack


@pytest.fixture(autouse=True)
def reset_track_counter():
    """Ensure ID counter starts fresh before each test."""
    STrack.reset_id_counter()


def test_strack_to_dict_structure():
    """Verify STrack outputs all required keys and correct types for Step 4."""
    track = STrack(
        bbox=[100, 150, 200, 350],
        confidence=0.92,
        category="human",
        class_name="person",
        frame_id=1,
    )
    d = track.to_dict()

    assert d["track_id"] == 1
    assert d["category"] == "human"
    assert d["class_name"] == "person"
    assert d["confidence"] == 0.92
    assert d["bbox"] == [100, 150, 200, 350]
    assert d["center"] == [150, 250]
    assert d["frame_number"] == 1
    assert d["trajectory"] == [[150, 250]]


def test_tracking_id_persistence():
    """Verify that moving bounding boxes retain the same persistent track_id across frames."""
    tracker = ByteTracker(high_thresh=0.5, match_thresh=0.7)

    # Frame 1: Person at position [100, 100, 150, 200]
    dets_f1 = [
        {
            "class_name": "person",
            "category": "human",
            "confidence": 0.90,
            "bbox": [100, 100, 150, 200],
            "center": [125, 150],
        }
    ]
    tracks_f1 = tracker.update(dets_f1, frame_number=1)
    assert len(tracks_f1) == 1
    assigned_id = tracks_f1[0]["track_id"]

    # Frame 2: Person moves slightly to [104, 102, 154, 202]
    dets_f2 = [
        {
            "class_name": "person",
            "category": "human",
            "confidence": 0.88,
            "bbox": [104, 102, 154, 202],
            "center": [129, 152],
        }
    ]
    tracks_f2 = tracker.update(dets_f2, frame_number=2)
    assert len(tracks_f2) == 1
    assert tracks_f2[0]["track_id"] == assigned_id, "Track ID must remain stable across frames"

    # Frame 3: Person continues moving to [109, 105, 159, 205]
    dets_f3 = [
        {
            "class_name": "person",
            "category": "human",
            "confidence": 0.87,
            "bbox": [109, 105, 159, 205],
            "center": [134, 155],
        }
    ]
    tracks_f3 = tracker.update(dets_f3, frame_number=3)
    assert len(tracks_f3) == 1
    assert tracks_f3[0]["track_id"] == assigned_id, "Track ID must remain identical on frame 3"


def test_trajectory_accumulation():
    """Verify trajectory history stores ordered center points over time."""
    tracker = ByteTracker(high_thresh=0.5, match_thresh=0.7)

    centers = [[125, 150], [129, 152], [134, 155], [140, 158]]
    for idx, (cx, cy) in enumerate(centers):
        x1, y1 = cx - 25, cy - 50
        x2, y2 = cx + 25, cy + 50
        dets = [
            {
                "class_name": "car",
                "category": "vehicle",
                "confidence": 0.91,
                "bbox": [x1, y1, x2, y2],
                "center": [cx, cy],
            }
        ]
        tracks = tracker.update(dets, frame_number=idx + 1)

    assert len(tracks) == 1
    assert tracks[0]["trajectory"] == centers


def test_multi_target_distinct_ids():
    """Verify multiple distinct targets receive unique IDs."""
    tracker = ByteTracker(high_thresh=0.5, match_thresh=0.7)

    # Frame with a person, a dog, and a truck far apart
    dets = [
        {
            "class_name": "person",
            "category": "human",
            "confidence": 0.92,
            "bbox": [50, 50, 100, 150],
            "center": [75, 100],
        },
        {
            "class_name": "dog",
            "category": "animal",
            "confidence": 0.85,
            "bbox": [300, 200, 360, 260],
            "center": [330, 230],
        },
        {
            "class_name": "truck",
            "category": "vehicle",
            "confidence": 0.89,
            "bbox": [500, 100, 650, 250],
            "center": [575, 175],
        },
    ]

    tracks = tracker.update(dets, frame_number=1)
    assert len(tracks) == 3
    ids = {t["track_id"] for t in tracks}
    assert len(ids) == 3, "Each detected target must receive a distinct unique ID"


def test_empty_frame_handling():
    """Verify tracker handles empty detection lists without crashing."""
    tracker = ByteTracker()
    tracks = tracker.update([], frame_number=1)
    assert tracks == []


def test_bytetrack_low_confidence_recovery():
    """
    Verify the core innovation of ByteTrack:
    An existing tracklet is recovered by a low-confidence detection in the 2nd association stage.
    """
    tracker = ByteTracker(high_thresh=0.6, low_thresh=0.15, match_thresh=0.7)

    # Frame 1: High confidence detection -> spawns Track #1
    dets_f1 = [
        {
            "class_name": "person",
            "category": "human",
            "confidence": 0.85,
            "bbox": [100, 100, 150, 200],
            "center": [125, 150],
        }
    ]
    tracks_f1 = tracker.update(dets_f1, frame_number=1)
    track_id = tracks_f1[0]["track_id"]

    # Frame 2: Person is partially occluded / in shadow (confidence drops to 0.35, below high_thresh)
    dets_f2 = [
        {
            "class_name": "person",
            "category": "human",
            "confidence": 0.35,  # Low confidence detection
            "bbox": [102, 101, 152, 201],
            "center": [127, 151],
        }
    ]
    tracks_f2 = tracker.update(dets_f2, frame_number=2)

    # ByteTrack stage 2 should associate the low-confidence box and preserve Track #1
    assert len(tracks_f2) == 1
    assert tracks_f2[0]["track_id"] == track_id
    assert tracks_f2[0]["confidence"] == 0.35
