"""
AI Border Sentinel - Step 5: Explainable Rule-Based Risk Engine Module

Evaluates physical, observable movement signals and virtual restricted-zone geofencing
to produce an explainable Prototype Risk / Suspicion Score from 0 to 100.

IMPORTANT:
- This is a rule-based engineering prototype score based on physical surveillance signals.
- It is NOT a scientifically validated probability of criminal, terrorist, or malicious intent.
- Every score is accompanied by an audit trail of transparent 'risk_reasons'.
"""

import math
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from detection.detector import (
    CATEGORY_ANIMAL,
    CATEGORY_COLORS,
    CATEGORY_HUMAN,
    CATEGORY_VEHICLE,
)
from zone.restricted_zone import (
    EVENT_ENTERED,
    EVENT_EXITED,
    ZONE_INSIDE,
    ZONE_NEAR,
)

# Prototype Risk Levels
LEVEL_NORMAL = "NORMAL"          # Score: 0 - 24
LEVEL_MONITOR = "MONITOR"        # Score: 25 - 49
LEVEL_SUSPICIOUS = "SUSPICIOUS"  # Score: 50 - 74
LEVEL_CRITICAL = "CRITICAL"      # Score: 75 - 100

# Visual Color Palette for Risk Levels (BGR format)
RISK_LEVEL_COLORS: Dict[str, Tuple[int, int, int]] = {
    LEVEL_NORMAL: (0, 220, 110),     # Muted Green
    LEVEL_MONITOR: (0, 220, 240),    # Bright Amber / Yellow
    LEVEL_SUSPICIOUS: (0, 140, 255), # Vibrant Orange
    LEVEL_CRITICAL: (0, 0, 240),     # Bright Red / Alert
}


class RiskConfig:
    """Configurable scoring weights and operational thresholds for Step 5."""

    def __init__(
        self,
        weight_zone_entry: int = 40,
        weight_near_zone: int = 15,
        weight_moving_toward_zone: int = 15,
        weight_direction_changes: int = 10,
        weight_high_speed: int = 10,
        weight_persistence: int = 5,
        weight_group_movement: int = 5,
        threshold_high_speed_px: float = 7.0,
        threshold_direction_changes: int = 3,
        threshold_persistence_frames: int = 50,
        group_distance_threshold_px: float = 160.0,
    ):
        self.weight_zone_entry = weight_zone_entry
        self.weight_near_zone = weight_near_zone
        self.weight_moving_toward_zone = weight_moving_toward_zone
        self.weight_direction_changes = weight_direction_changes
        self.weight_high_speed = weight_high_speed
        self.weight_persistence = weight_persistence
        self.weight_group_movement = weight_group_movement

        self.threshold_high_speed_px = threshold_high_speed_px
        self.threshold_direction_changes = threshold_direction_changes
        self.threshold_persistence_frames = threshold_persistence_frames
        self.group_distance_threshold_px = group_distance_threshold_px


class RiskEngine:
    """
    Modular explainable rule-based risk engine for surveillance targets.
    Consumes outputs from MovementAnalyzer & RestrictedZone to calculate 0-100 scores.
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config if config is not None else RiskConfig()
        self.total_intrusions_detected: int = 0
        self._intrusions_seen: set = set()

    def get_risk_level(self, score: int) -> str:
        """Map a numeric risk score (0-100) into a prototype level."""
        if score >= 75:
            return LEVEL_CRITICAL
        elif score >= 50:
            return LEVEL_SUSPICIOUS
        elif score >= 25:
            return LEVEL_MONITOR
        else:
            return LEVEL_NORMAL

    def detect_group_movement(self, objects: List[Dict[str, Any]]) -> Dict[int, bool]:
        """
        Detects clusters of 2+ human targets in close proximity moving together.
        Returns dict mapping track_id -> is_in_group (bool).
        """
        human_objects = [o for o in objects if o.get("category") == CATEGORY_HUMAN]
        group_map: Dict[int, bool] = {o["track_id"]: False for o in objects}

        if len(human_objects) < 2:
            return group_map

        for i in range(len(human_objects)):
            c1 = human_objects[i]["center"]
            tid1 = human_objects[i]["track_id"]
            dir1 = human_objects[i].get("movement_direction", "STATIONARY")

            for j in range(i + 1, len(human_objects)):
                c2 = human_objects[j]["center"]
                tid2 = human_objects[j]["track_id"]
                dir2 = human_objects[j].get("movement_direction", "STATIONARY")

                dist = math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2)
                if dist <= self.config.group_distance_threshold_px:
                    # If close and moving (or moving in same general direction)
                    group_map[tid1] = True
                    group_map[tid2] = True

        return group_map

    def evaluate_target_risk(
        self,
        obj: Dict[str, Any],
        is_in_group: bool = False,
    ) -> Tuple[int, str, List[str]]:
        """
        Calculate the rule-based risk score (0-100), risk level, and reasons list.
        """
        category = obj.get("category", "unknown")
        zone_status = obj.get("zone_status", "FAR_FROM_ZONE")
        moving_toward_zone = obj.get("moving_toward_zone", False)
        speed = obj.get("estimated_speed_px_per_frame", 0.0)
        direction_changes = obj.get("direction_changes", 0)
        frames_observed = obj.get("frames_observed", 0)

        score = 0
        reasons: List[str] = []

        # 1. Restricted Zone Intrusion (Dominant factor)
        if zone_status == ZONE_INSIDE:
            score += self.config.weight_zone_entry
            reasons.append("Entered restricted zone")
        elif zone_status == ZONE_NEAR:
            score += self.config.weight_near_zone
            reasons.append("Near restricted zone boundary")

        # 2. Movement Heading Toward Zone
        if moving_toward_zone and zone_status != ZONE_INSIDE:
            score += self.config.weight_moving_toward_zone
            reasons.append("Moving toward restricted zone")

        # 3. Erratic / Repeated Direction Changes
        if direction_changes >= self.config.threshold_direction_changes:
            score += self.config.weight_direction_changes
            reasons.append(f"Frequent direction changes ({direction_changes} turns)")

        # 4. High Image-Space Speed
        if speed >= self.config.threshold_high_speed_px:
            score += self.config.weight_high_speed
            reasons.append(f"High image-space speed ({speed:.1f} px/fr)")

        # 5. Persistent Presence in Surveillance Area
        if frames_observed >= self.config.threshold_persistence_frames:
            score += self.config.weight_persistence
            reasons.append(f"Persistent presence ({frames_observed} frames)")

        # 6. Group Movement (for humans)
        if category == CATEGORY_HUMAN and is_in_group:
            score += self.config.weight_group_movement
            reasons.append("Multiple tracked humans moving together")

        # Category Nuance: Animals are natural wildlife; cap wildlife risk
        if category == CATEGORY_ANIMAL:
            # Animal in restricted zone is an intrusion, but not malicious intent
            score = min(score, 35)
            if zone_status == ZONE_INSIDE:
                reasons = ["Wildlife entry into perimeter"]
            elif zone_status == ZONE_NEAR:
                reasons = ["Wildlife approaching perimeter"]

        # Clamp score to [0, 100]
        final_score = max(0, min(100, score))
        risk_level = self.get_risk_level(final_score)

        if not reasons:
            reasons.append("Normal observable activity within parameters")

        return final_score, risk_level, reasons

    def process_frame_objects(
        self,
        objects_with_zone: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Process all targets in current frame, calculating group clustering and risk scores.
        """
        group_map = self.detect_group_movement(objects_with_zone)
        risk_assessed: List[Dict[str, Any]] = []

        for obj in objects_with_zone:
            tid = obj["track_id"]
            is_group = group_map.get(tid, False)

            score, level, reasons = self.evaluate_target_risk(obj, is_in_group=is_group)

            # Track cumulative unique intrusions
            if obj.get("zone_status") == ZONE_INSIDE:
                self._intrusions_seen.add(tid)
                self.total_intrusions_detected = len(self._intrusions_seen)

            enriched = {
                **obj,
                "group_activity": is_group,
                "risk_score": score,
                "risk_level": level,
                "risk_reasons": reasons,
            }
            risk_assessed.append(enriched)

        return risk_assessed

    def draw_risk_visualizations(
        self,
        frame: np.ndarray,
        risk_objects: List[Dict[str, Any]],
        show_trajectory: bool = True,
        show_hud: bool = True,
    ) -> np.ndarray:
        """
        Draw risk-level colored bounding boxes, structured risk badges,
        motion trails, and top surveillance risk HUD banner.
        """
        annotated = frame.copy()

        level_counts = {
            LEVEL_NORMAL: 0,
            LEVEL_MONITOR: 0,
            LEVEL_SUSPICIOUS: 0,
            LEVEL_CRITICAL: 0,
        }

        for obj in risk_objects:
            level = obj["risk_level"]
            score = obj["risk_score"]
            level_counts[level] = level_counts.get(level, 0) + 1

            track_id = obj["track_id"]
            class_name = obj["class_name"].upper()
            x1, y1, x2, y2 = obj["bbox"]
            cx, cy = obj["center"]
            zone_status = obj.get("zone_status", "FAR_FROM_ZONE")
            speed = obj.get("estimated_speed_px_per_frame", 0.0)
            reasons = obj.get("risk_reasons", [])
            top_reason = reasons[0] if reasons else "Normal activity"
            trajectory = obj.get("trajectory", [])

            # Use risk level color for border & badge header
            color = RISK_LEVEL_COLORS.get(level, (0, 220, 110))

            # 1. Motion Trajectory Trail
            if show_trajectory and len(trajectory) > 1:
                pts = np.array(trajectory, dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(annotated, [pts], isClosed=False, color=color, thickness=2, lineType=cv2.LINE_AA)

            # 2. Bounding Box (Color-coded by Risk Level)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # 3. Center Dot
            cv2.circle(annotated, (cx, cy), 4, color, -1)

            # 4. Multi-Line Risk Information Badge
            # Line 1: Target & Risk Score (e.g. "PERSON #1 | Risk: 70/100 [SUSPICIOUS]")
            # Line 2: Zone & Speed (e.g. "Zone: INSIDE | Speed: 3.6 px/fr")
            # Line 3: Top Risk Reason (e.g. "* Entered restricted zone")
            line1 = f"{class_name} #{track_id} | Risk: {score}/100 [{level}]"
            line2 = f"Zone: {zone_status} | Speed: {speed:.1f} px/fr"
            line3 = f"* {top_reason}"[:38]

            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.42
            thickness = 1

            (w1, h1), _ = cv2.getTextSize(line1, font, font_scale, thickness)
            (w2, h2), _ = cv2.getTextSize(line2, font, font_scale, thickness)
            (w3, h3), _ = cv2.getTextSize(line3, font, font_scale, thickness)

            badge_w = max(w1, w2, w3) + 14
            badge_h = h1 + h2 + h3 + 18

            badge_y1 = max(y1 - badge_h - 4, 0)
            badge_y2 = badge_y1 + badge_h
            badge_x2 = x1 + badge_w

            # Dark badge backing with colored indicator bar
            cv2.rectangle(annotated, (x1, badge_y1), (badge_x2, badge_y2), (20, 24, 28), -1)
            cv2.rectangle(annotated, (x1, badge_y1), (x1 + 5, badge_y2), color, -1)
            cv2.rectangle(annotated, (x1, badge_y1), (badge_x2, badge_y2), color, 1)

            # Text render
            cv2.putText(annotated, line1, (x1 + 9, badge_y1 + h1 + 3), font, font_scale, color, thickness, cv2.LINE_AA)
            cv2.putText(annotated, line2, (x1 + 9, badge_y1 + h1 + h2 + 7), font, font_scale, (220, 220, 220), thickness, cv2.LINE_AA)
            cv2.putText(annotated, line3, (x1 + 9, badge_y1 + h1 + h2 + h3 + 12), font, font_scale, (0, 220, 255), thickness, cv2.LINE_AA)

        # 5. Top Surveillance Risk HUD
        if show_hud:
            h, w = annotated.shape[:2]
            total_active = len(risk_objects)
            hud_text = (
                f"AI BORDER SENTINEL (STEP 5: RISK ENGINE) | "
                f"ACTIVE: {total_active} | "
                f"NORMAL: {level_counts[LEVEL_NORMAL]} | "
                f"MONITOR: {level_counts[LEVEL_MONITOR]} | "
                f"SUSPICIOUS: {level_counts[LEVEL_SUSPICIOUS]} | "
                f"CRITICAL: {level_counts[LEVEL_CRITICAL]} | "
                f"INTRUSIONS: {self.total_intrusions_detected}"
            )

            overlay = annotated.copy()
            cv2.rectangle(overlay, (0, 0), (w, 36), (16, 20, 24), -1)
            cv2.addWeighted(overlay, 0.75, annotated, 0.25, 0, annotated)

            cv2.putText(
                annotated,
                hud_text,
                (14, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.50,
                (0, 255, 255),
                1,
                lineType=cv2.LINE_AA,
            )

        return annotated
