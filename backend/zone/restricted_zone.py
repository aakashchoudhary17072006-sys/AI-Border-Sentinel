"""
AI Border Sentinel - Step 5: Virtual Restricted Zone Module

Provides virtual polygon geofencing, proximity classification, one-shot transition events
(ENTERED / EXITED), and geometric heading determination (moving towards zone).

Pipeline Position:
    MovementAnalyzer (Step 4) -> RestrictedZone (Step 5) -> RiskEngine (Step 5)
"""

import math
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

# Zone Proximity States
ZONE_INSIDE = "INSIDE"
ZONE_NEAR = "NEAR_ZONE"
ZONE_FAR = "FAR_FROM_ZONE"

# Transition Events
EVENT_ENTERED = "ENTERED"
EVENT_EXITED = "EXITED"
EVENT_NONE = None


class RestrictedZone:
    """
    Virtual polygon geofence representing a secure boundary or restricted perimeter.
    Evaluates target center coordinates for inclusion, proximity, and boundary crossing.
    """

    # Default perimeter polygon scaled for standard 1080x720 surveillance view
    DEFAULT_POLYGON: List[List[int]] = [
        [30, 160],
        [820, 160],
        [820, 690],
        [30, 690],
    ]

    def __init__(
        self,
        polygon: Optional[List[List[int]]] = None,
        proximity_threshold_px: float = 80.0,
        zone_name: str = "SECURE_PERIMETER_ALPHA",
    ):
        """
        :param polygon: List of [x, y] vertices defining the restricted boundary polygon.
        :param proximity_threshold_px: Image-space distance (px) to qualify as NEAR_ZONE.
        :param zone_name: Human-readable identifier for this restricted sector.
        """
        self.polygon_pts = polygon if polygon is not None else self.DEFAULT_POLYGON
        if len(self.polygon_pts) >= 3:
            self.np_polygon = np.array(self.polygon_pts, dtype=np.int32).reshape((-1, 1, 2))
        else:
            self.np_polygon = np.empty((0, 1, 2), dtype=np.int32)
        self.proximity_threshold_px = proximity_threshold_px
        self.zone_name = zone_name

        # Track previous zone state for each target ID to detect transitions
        # track_id -> previous zone_status (ZONE_INSIDE, ZONE_NEAR, or ZONE_FAR)
        self._prev_states: Dict[int, str] = {}

        # Track previous distance to zone boundary to detect motion heading towards zone
        # track_id -> previous distance (px)
        self._prev_distances: Dict[int, float] = {}

    def reset(self) -> None:
        """Reset internal history for a new video stream."""
        self._prev_states.clear()
        self._prev_distances.clear()

    def get_distance_to_polygon(self, center: List[int]) -> Tuple[float, bool]:
        """
        Compute distance from a center point [x, y] to the polygon boundary.
        Returns (signed_distance, is_inside):
        - is_inside: True if point is inside or on boundary
        - signed_distance: Positive if inside, negative if outside, zero if on edge
        """
        if len(self.polygon_pts) < 3:
            return -999999.0, False
        pt = (float(center[0]), float(center[1]))
        dist = cv2.pointPolygonTest(self.np_polygon, pt, measureDist=True)
        is_inside = dist >= 0.0
        return dist, is_inside

    def evaluate_object(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a single tracked object against the restricted zone.

        Determines:
        - zone_status: INSIDE, NEAR_ZONE, or FAR_FROM_ZONE
        - zone_event: ENTERED (one-shot), EXITED (one-shot), or None
        - moving_toward_zone: True if distance to zone boundary is actively decreasing
        - distance_to_zone_px: Absolute Euclidean distance to perimeter (0.0 if inside)
        """
        track_id = obj["track_id"]
        center = obj["center"]

        raw_dist, is_inside = self.get_distance_to_polygon(center)

        # 1. Determine Zone Status
        if is_inside:
            current_status = ZONE_INSIDE
            abs_dist_to_zone = 0.0
        else:
            abs_dist_to_zone = abs(raw_dist)
            if abs_dist_to_zone <= self.proximity_threshold_px:
                current_status = ZONE_NEAR
            else:
                current_status = ZONE_FAR

        # 2. Detect Single-Fire Transition Events
        prev_status = self._prev_states.get(track_id, ZONE_FAR)
        zone_event = EVENT_NONE

        if prev_status != ZONE_INSIDE and current_status == ZONE_INSIDE:
            zone_event = EVENT_ENTERED
        elif prev_status == ZONE_INSIDE and current_status != ZONE_INSIDE:
            zone_event = EVENT_EXITED

        self._prev_states[track_id] = current_status

        # 3. Determine if Target is Moving Toward Restricted Zone
        moving_toward_zone = False
        if not is_inside:
            prev_dist = self._prev_distances.get(track_id)
            if prev_dist is not None:
                # If distance to perimeter decreased by at least 1.5px and target is moving
                speed = obj.get("estimated_speed_px_per_frame", 0.0)
                if (prev_dist - abs_dist_to_zone) >= 1.5 and speed >= 1.0:
                    moving_toward_zone = True

        self._prev_distances[track_id] = abs_dist_to_zone

        return {
            "zone_status": current_status,
            "zone_event": zone_event,
            "moving_toward_zone": moving_toward_zone,
            "distance_to_zone_px": round(abs_dist_to_zone, 1),
        }

    def evaluate_tracks(self, tracked_objects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluate all tracked objects and enrich them with restricted-zone signals.
        """
        enriched: List[Dict[str, Any]] = []
        for obj in tracked_objects:
            zone_info = self.evaluate_object(obj)
            merged = {**obj, **zone_info}
            enriched.append(merged)
        return enriched

    def draw_zone(
        self,
        frame: np.ndarray,
        alpha: float = 0.20,
        border_color: Tuple[int, int, int] = (0, 0, 240),
        fill_color: Tuple[int, int, int] = (0, 0, 180),
    ) -> np.ndarray:
        """
        Draw semi-transparent restricted zone polygon with high-visibility warning perimeter.
        """
        annotated = frame.copy()
        overlay = frame.copy()

        # Fill semi-transparent polygon
        cv2.fillPoly(overlay, [self.np_polygon], fill_color)
        cv2.addWeighted(overlay, alpha, annotated, 1.0 - alpha, 0, annotated)

        # Draw solid warning boundary
        cv2.polylines(annotated, [self.np_polygon], isClosed=True, color=border_color, thickness=2, lineType=cv2.LINE_AA)

        # Draw Zone Header Badge at top-left vertex of polygon
        min_x = min(pt[0] for pt in self.polygon_pts)
        min_y = min(pt[1] for pt in self.polygon_pts)
        badge_text = f"RESTRICTED BORDER ZONE: {self.zone_name}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.45
        thickness = 1
        (tw, th), _ = cv2.getTextSize(badge_text, font, font_scale, thickness)

        cv2.rectangle(annotated, (min_x, min_y - th - 8), (min_x + tw + 12, min_y), border_color, -1)
        cv2.putText(
            annotated,
            badge_text,
            (min_x + 6, min_y - 4),
            font,
            font_scale,
            (255, 255, 255),
            thickness,
            lineType=cv2.LINE_AA,
        )

        return annotated
