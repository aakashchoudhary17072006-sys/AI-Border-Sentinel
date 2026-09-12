"""
Unit tests for Step 5: Restricted Zone Detection and Explainable Risk Engine.
Validates polygon geofencing, proximity, one-shot transition events,
rule-based 0-100 scoring, explainable reasons, threat level categorization,
group movement detection, and Step 6 contract schema.
"""

import numpy as np
import pytest

from risk.risk_engine import (
    CATEGORY_ANIMAL,
    CATEGORY_HUMAN,
    LEVEL_CRITICAL,
    LEVEL_MONITOR,
    LEVEL_NORMAL,
    LEVEL_SUSPICIOUS,
    RiskConfig,
    RiskEngine,
)
from zone.restricted_zone import (
    EVENT_ENTERED,
    EVENT_EXITED,
    ZONE_FAR,
    ZONE_INSIDE,
    ZONE_NEAR,
    RestrictedZone,
)


# ============================================================================
# RESTRICTED ZONE TESTS
# ============================================================================

def test_point_in_polygon_and_proximity():
    """Verify point inside polygon, near boundary, and far away."""
    # Define a 100x100 square from (100, 100) to (200, 200)
    polygon = [[100, 100], [200, 100], [200, 200], [100, 200]]
    zone = RestrictedZone(polygon=polygon, proximity_threshold_px=50.0)

    # 1. Inside point (150, 150)
    res_inside = zone.evaluate_object({"track_id": 1, "center": [150, 150]})
    assert res_inside["zone_status"] == ZONE_INSIDE
    assert res_inside["distance_to_zone_px"] == 0.0

    # 2. Near point (220, 150) -> 20px from right edge -> < 50px threshold
    res_near = zone.evaluate_object({"track_id": 2, "center": [220, 150]})
    assert res_near["zone_status"] == ZONE_NEAR
    assert pytest.approx(res_near["distance_to_zone_px"], abs=0.5) == 20.0

    # 3. Far point (350, 150) -> 150px from right edge -> > 50px threshold
    res_far = zone.evaluate_object({"track_id": 3, "center": [350, 150]})
    assert res_far["zone_status"] == ZONE_FAR
    assert pytest.approx(res_far["distance_to_zone_px"], abs=0.5) == 150.0


def test_transition_events_one_shot():
    """Verify ENTERED and EXITED events are emitted exactly once per transition."""
    polygon = [[100, 100], [200, 100], [200, 200], [100, 200]]
    zone = RestrictedZone(polygon=polygon, proximity_threshold_px=50.0)

    # Track 1 starts outside at (50, 150)
    t1_outside = zone.evaluate_object({"track_id": 1, "center": [50, 150]})
    assert t1_outside["zone_event"] is None
    assert t1_outside["zone_status"] == ZONE_NEAR

    # Track 1 moves inside at (150, 150) -> ENTERED event emitted
    t1_inside = zone.evaluate_object({"track_id": 1, "center": [150, 150]})
    assert t1_inside["zone_event"] == EVENT_ENTERED
    assert t1_inside["zone_status"] == ZONE_INSIDE

    # Track 1 stays inside at (160, 160) -> No duplicate event
    t1_inside_stay = zone.evaluate_object({"track_id": 1, "center": [160, 160]})
    assert t1_inside_stay["zone_event"] is None
    assert t1_inside_stay["zone_status"] == ZONE_INSIDE

    # Track 1 moves outside at (250, 150) -> EXITED event emitted
    t1_exit = zone.evaluate_object({"track_id": 1, "center": [250, 150]})
    assert t1_exit["zone_event"] == EVENT_EXITED
    assert t1_exit["zone_status"] == ZONE_NEAR

    # Track 1 stays outside at (260, 150) -> No duplicate event
    t1_outside_stay = zone.evaluate_object({"track_id": 1, "center": [260, 150]})
    assert t1_outside_stay["zone_event"] is None
    assert t1_outside_stay["zone_status"] == ZONE_FAR


def test_moving_towards_zone():
    """Verify heading towards zone detection."""
    polygon = [[200, 200], [300, 200], [300, 300], [200, 300]]
    zone = RestrictedZone(polygon=polygon, proximity_threshold_px=100.0)

    # Initial position far away (500, 250) -> distance ~ 200px
    zone.evaluate_object({"track_id": 2, "center": [500, 250], "estimated_speed_px_per_frame": 10.0})

    # Second position closer (400, 250) -> distance ~ 100px -> moving towards zone
    res_closer = zone.evaluate_object({"track_id": 2, "center": [400, 250], "estimated_speed_px_per_frame": 10.0})
    assert res_closer["moving_toward_zone"] is True

    # Third position moving away (450, 250) -> distance ~ 150px -> moving away
    res_away = zone.evaluate_object({"track_id": 2, "center": [450, 250], "estimated_speed_px_per_frame": 10.0})
    assert res_away["moving_toward_zone"] is False


def test_empty_polygon_fallback():
    """Verify graceful handling when polygon is empty."""
    zone = RestrictedZone(polygon=[])
    res = zone.evaluate_object({"track_id": 1, "center": [100, 100]})
    assert res["zone_status"] == ZONE_FAR
    assert res["distance_to_zone_px"] == 999999.0


# ============================================================================
# RISK ENGINE TESTS
# ============================================================================

def test_risk_score_calculation_and_reasons():
    """Verify rule weights are applied accurately and explainable reasons generated."""
    config = RiskConfig()
    engine = RiskEngine(config=config)

    # Synthetic track movement and zone result
    target_data = {
        "track_id": 10,
        "category": CATEGORY_HUMAN,
        "confidence": 0.85,
        "bbox": [100, 100, 150, 200],
        "center": [125, 150],
        "movement_direction": "RIGHT",
        "estimated_speed_px_per_frame": 15.0,  # >= 10.0 (high speed: +15)
        "cumulative_distance_px": 250.0,
        "direction_changes": 8,                # >= 6 (frequent turns: +15)
        "movement_status": "FAST_MOVING",
        "frames_observed": 60,                 # >= 50 (persistence: +15)
        "zone_status": ZONE_INSIDE,            # inside zone: +40
        "moving_toward_zone": False,
        "zone_event": EVENT_ENTERED,
    }

    score, level, reasons = engine.evaluate_target_risk(target_data, is_in_group=False)

    # Inside zone (40) + Erratic (10) + High speed (10) + Persistence (5) = 65
    assert score == 65
    assert level == LEVEL_SUSPICIOUS
    assert len(reasons) >= 4

    reasons_str = " ".join(reasons)
    assert "restricted zone" in reasons_str.lower()
    assert "speed" in reasons_str.lower()
    assert "direction changes" in reasons_str.lower()
    assert "persistent" in reasons_str.lower()


def test_score_clamping():
    """Verify risk score never exceeds 100 or drops below 0."""
    # Config with large weights that can sum to > 100
    config = RiskConfig(
        weight_zone_entry=60,
        weight_direction_changes=30,
        weight_high_speed=30,
        weight_persistence=20,
        weight_group_movement=20,
    )
    engine = RiskEngine(config=config)

    # Create scenario with extreme weights exceeding 100
    extreme_target = {
        "track_id": 1,
        "category": CATEGORY_HUMAN,
        "confidence": 0.9,
        "bbox": [0, 0, 10, 10],
        "center": [5, 5],
        "movement_direction": "LEFT",
        "estimated_speed_px_per_frame": 20.0,
        "cumulative_distance_px": 500.0,
        "direction_changes": 20,
        "movement_status": "FAST_MOVING",
        "frames_observed": 200,
        "zone_status": ZONE_INSIDE,
        "moving_toward_zone": True,
    }

    score, level, reasons = engine.evaluate_target_risk(extreme_target, is_in_group=True)
    assert score == 100
    assert level == LEVEL_CRITICAL


def test_risk_level_thresholds():
    """Verify mapping of 0-100 scores to NORMAL, MONITOR, SUSPICIOUS, CRITICAL."""
    engine = RiskEngine()

    assert engine.get_risk_level(0) == LEVEL_NORMAL
    assert engine.get_risk_level(24) == LEVEL_NORMAL
    assert engine.get_risk_level(25) == LEVEL_MONITOR
    assert engine.get_risk_level(49) == LEVEL_MONITOR
    assert engine.get_risk_level(50) == LEVEL_SUSPICIOUS
    assert engine.get_risk_level(74) == LEVEL_SUSPICIOUS
    assert engine.get_risk_level(75) == LEVEL_CRITICAL
    assert engine.get_risk_level(100) == LEVEL_CRITICAL


def test_group_movement_detection():
    """Verify detection of multiple humans moving within proximity."""
    engine = RiskEngine()

    target1 = {
        "track_id": 1,
        "category": CATEGORY_HUMAN,
        "center": [120, 150],
        "movement_direction": "RIGHT",
        "estimated_speed_px_per_frame": 5.0,
    }
    # Target 2 is 30px away from Target 1 (within group threshold 160px)
    target2 = {
        "track_id": 2,
        "category": CATEGORY_HUMAN,
        "center": [150, 150],
        "movement_direction": "RIGHT",
        "estimated_speed_px_per_frame": 5.0,
    }
    # Target 3 is an ANIMAL 30px away (should NOT trigger human group)
    target3 = {
        "track_id": 3,
        "category": CATEGORY_ANIMAL,
        "center": [150, 150],
    }

    # Only target 1 and animal target 3
    group_map_no = engine.detect_group_movement([target1, target3])
    assert group_map_no[1] is False

    # Target 1 and Target 2
    group_map_yes = engine.detect_group_movement([target1, target2])
    assert group_map_yes[1] is True
    assert group_map_yes[2] is True


def test_step6_contract_schema():
    """Verify the output dictionary satisfies all downstream contract requirements for Step 6 Alert Engine."""
    zone = RestrictedZone()
    engine = RiskEngine()

    raw_movement_object = {
        "track_id": 42,
        "category": CATEGORY_HUMAN,
        "confidence": 0.88,
        "bbox": [100, 100, 180, 250],
        "center": [140, 175],
        "movement_direction": "DOWN",
        "estimated_speed_px_per_frame": 4.5,
        "cumulative_distance_px": 110.2,
        "direction_changes": 3,
        "movement_status": "MOVING",
        "frames_observed": 32,
        "trajectory": [[140, 100], [140, 175]],
    }

    # Pipeline chaining: Movement -> Zone -> Risk
    zone_enriched = zone.evaluate_tracks([raw_movement_object])
    final_results = engine.process_frame_objects(zone_enriched)

    assert len(final_results) == 1
    target = final_results[0]

    required_keys = [
        "track_id",
        "category",
        "confidence",
        "bbox",
        "center",
        "movement_direction",
        "estimated_speed_px_per_frame",
        "cumulative_distance_px",
        "direction_changes",
        "movement_status",
        "frames_observed",
        "zone_status",
        "distance_to_zone_px",
        "moving_toward_zone",
        "zone_event",
        "risk_score",
        "risk_level",
        "risk_reasons",
        "group_activity",
    ]

    for key in required_keys:
        assert key in target, f"Missing required Step 6 contract key: {key}"

    assert isinstance(target["risk_score"], int)
    assert 0 <= target["risk_score"] <= 100
    assert target["risk_level"] in [LEVEL_NORMAL, LEVEL_MONITOR, LEVEL_SUSPICIOUS, LEVEL_CRITICAL]
    assert isinstance(target["risk_reasons"], list)
