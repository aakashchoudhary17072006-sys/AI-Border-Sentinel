"""
AI Border Sentinel - Step 4: Movement and Observable Behaviour Analysis Module

Consumes tracked target objects from Step 3 (ByteTracker) and computes
strictly observable, geometric physical motion metrics across time:
- Movement direction (8 compass directions + STATIONARY)
- Estimated image-space speed (pixels/frame, rolling average)
- Cumulative distance travelled (pixels)
- Direction changes count (filtering detection jitter)
- Persistence (total frames observed)
- Observable movement status (STATIONARY, MOVING, FAST_MOVING, DIRECTION_CHANGING)

IMPORTANT:
This module performs NO emotion recognition and generates NO subjective/psychological
inferences (no claims of anger, nervousness, fear, criminality, or threat levels).
Signals are purely objective physical observations prepared for Step 5 consumption.
"""

import math
from collections import deque
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from detection.detector import (
    CATEGORY_ANIMAL,
    CATEGORY_COLORS,
    CATEGORY_HUMAN,
    CATEGORY_VEHICLE,
)

# Standard Direction Constants
DIRECTION_STATIONARY = "STATIONARY"
DIRECTION_RIGHT = "RIGHT"
DIRECTION_UP_RIGHT = "UP-RIGHT"
DIRECTION_UP = "UP"
DIRECTION_UP_LEFT = "UP-LEFT"
DIRECTION_LEFT = "LEFT"
DIRECTION_DOWN_LEFT = "DOWN-LEFT"
DIRECTION_DOWN = "DOWN"
DIRECTION_DOWN_RIGHT = "DOWN-RIGHT"

# Standard Movement Status Constants (Observable Physical State)
STATUS_STATIONARY = "STATIONARY"
STATUS_MOVING = "MOVING"
STATUS_FAST_MOVING = "FAST_MOVING"
STATUS_DIRECTION_CHANGING = "DIRECTION_CHANGING"


class TrackMovementProfile:
    """
    Maintains persistent temporal motion statistics for a single tracked target ID.
    """

    def __init__(self, track_id: int, initial_center: List[int], window_size: int = 5):
        self.track_id: int = track_id
        self.frames_observed: int = 0
        self.distance_travelled_px: float = 0.0
        self.direction_changes: int = 0

        # Rolling history of recent center coordinates for velocity & direction smoothing
        self.center_history: deque = deque(maxlen=window_size)
        self.center_history.append(initial_center)

        # Rolling history of step speeds (pixels per frame)
        self.speed_history: deque = deque(maxlen=window_size)

        # Current observable state
        self.last_confirmed_direction: str = DIRECTION_STATIONARY
        self.current_direction: str = DIRECTION_STATIONARY
        self.estimated_speed_px_per_frame: float = 0.0
        self.movement_status: str = STATUS_STATIONARY

        # Recent direction sequence for detecting active wandering/weaving
        self.recent_directions: deque = deque(maxlen=15)

    def update(
        self,
        current_center: List[int],
        noise_threshold_px: float = 2.5,
        fast_speed_threshold_px: float = 7.0,
    ) -> None:
        """
        Update profile with the latest center coordinates observed in the current frame.
        """
        self.frames_observed += 1

        prev_center = self.center_history[-1] if self.center_history else current_center
        dx = current_center[0] - prev_center[0]
        dy = current_center[1] - prev_center[1]
        step_distance = math.sqrt(dx * dx + dy * dy)

        # Accumulate cumulative distance travelled
        self.distance_travelled_px += step_distance
        self.speed_history.append(step_distance)

        # Compute smoothed speed (rolling average)
        self.estimated_speed_px_per_frame = round(
            float(sum(self.speed_history) / len(self.speed_history)), 2
        )

        # Calculate vector displacement over window to reduce single-frame jitter
        ref_center = self.center_history[0]
        win_dx = current_center[0] - ref_center[0]
        win_dy = current_center[1] - ref_center[1]
        win_distance = math.sqrt(win_dx * win_dx + win_dy * win_dy)

        # Determine Direction
        if win_distance < noise_threshold_px:
            new_direction = DIRECTION_STATIONARY
        else:
            # In image space, +Y is downwards. Invert dy to get Cartesian angle
            angle_rad = math.atan2(-win_dy, win_dx)
            angle_deg = math.degrees(angle_rad)

            # Map angle into 8 compass sectors (45 degrees each)
            if -22.5 <= angle_deg < 22.5:
                new_direction = DIRECTION_RIGHT
            elif 22.5 <= angle_deg < 67.5:
                new_direction = DIRECTION_UP_RIGHT
            elif 67.5 <= angle_deg < 112.5:
                new_direction = DIRECTION_UP
            elif 112.5 <= angle_deg < 157.5:
                new_direction = DIRECTION_UP_LEFT
            elif angle_deg >= 157.5 or angle_deg < -157.5:
                new_direction = DIRECTION_LEFT
            elif -157.5 <= angle_deg < -112.5:
                new_direction = DIRECTION_DOWN_LEFT
            elif -112.5 <= angle_deg < -67.5:
                new_direction = DIRECTION_DOWN
            else:  # -67.5 <= angle_deg < -22.5
                new_direction = DIRECTION_DOWN_RIGHT

        # Detect and count meaningful direction changes
        # (Ignore transitions to/from stationary to avoid jitter false positives)
        if (
            new_direction != DIRECTION_STATIONARY
            and self.last_confirmed_direction != DIRECTION_STATIONARY
            and new_direction != self.last_confirmed_direction
        ):
            self.direction_changes += 1

        if new_direction != DIRECTION_STATIONARY:
            self.last_confirmed_direction = new_direction

        self.current_direction = new_direction
        self.recent_directions.append(new_direction)
        self.center_history.append(current_center)

        # Determine Movement Status based on objective metrics
        # Count non-stationary direction changes in recent window
        recent_unique_dirs = set(
            d for d in self.recent_directions if d != DIRECTION_STATIONARY
        )

        if self.estimated_speed_px_per_frame < 1.5:
            self.movement_status = STATUS_STATIONARY
        elif len(recent_unique_dirs) >= 3 and self.estimated_speed_px_per_frame >= 1.5:
            self.movement_status = STATUS_DIRECTION_CHANGING
        elif self.estimated_speed_px_per_frame >= fast_speed_threshold_px:
            self.movement_status = STATUS_FAST_MOVING
        else:
            self.movement_status = STATUS_MOVING


class MovementAnalyzer:
    """
    Modular movement analysis system for surveillance targets.
    Consumes tracked object outputs from ByteTracker and maintains temporal motion profiles.
    """

    def __init__(
        self,
        noise_threshold_px: float = 2.5,
        fast_speed_threshold_px: float = 7.0,
        history_window: int = 5,
    ):
        """
        :param noise_threshold_px: Minimum displacement to be recognized as non-stationary.
        :param fast_speed_threshold_px: Speed threshold (pixels/frame) for FAST_MOVING status.
        :param history_window: Window size for velocity and heading smoothing.
        """
        self.noise_threshold_px = noise_threshold_px
        self.fast_speed_threshold_px = fast_speed_threshold_px
        self.history_window = history_window

        # Registry of persistent movement profiles indexed by track_id
        self._profiles: Dict[int, TrackMovementProfile] = {}

    def reset(self) -> None:
        """Reset internal profiles for a new video stream."""
        self._profiles.clear()

    def analyze_tracks(
        self,
        tracked_objects: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Analyze a list of tracked objects for the current frame.

        :param tracked_objects: List of dicts from ByteTracker.update():
                                [{'track_id': int, 'category': str, 'class_name': str,
                                  'confidence': float, 'bbox': [x1, y1, x2, y2],
                                  'center': [cx, cy], 'trajectory': [[x, y], ...], ...}]
        :return: List of enriched dictionaries containing all Step 4 observable signals.
        """
        analyzed_objects: List[Dict[str, Any]] = []

        for obj in tracked_objects:
            track_id = obj["track_id"]
            current_center = obj["center"]

            # Initialize profile if new target
            if track_id not in self._profiles:
                self._profiles[track_id] = TrackMovementProfile(
                    track_id=track_id,
                    initial_center=current_center,
                    window_size=self.history_window,
                )

            profile = self._profiles[track_id]
            profile.update(
                current_center=current_center,
                noise_threshold_px=self.noise_threshold_px,
                fast_speed_threshold_px=self.fast_speed_threshold_px,
            )

            # Build enriched structured dictionary (Contract for Step 5)
            enriched_record = {
                "track_id": track_id,
                "category": obj.get("category", "unknown"),
                "class_name": obj.get("class_name", "unknown"),
                "confidence": obj.get("confidence", 0.0),
                "bbox": obj.get("bbox", [0, 0, 0, 0]),
                "center": current_center,
                "movement_direction": profile.current_direction,
                "estimated_speed_px_per_frame": profile.estimated_speed_px_per_frame,
                "distance_travelled_px": round(profile.distance_travelled_px, 1),
                "direction_changes": profile.direction_changes,
                "frames_observed": profile.frames_observed,
                "movement_status": profile.movement_status,
                "trajectory": obj.get("trajectory", [current_center]),
            }
            analyzed_objects.append(enriched_record)

        return analyzed_objects

    def draw_movement_analysis(
        self,
        frame: np.ndarray,
        analyzed_objects: List[Dict[str, Any]],
        show_trajectory: bool = True,
        show_center: bool = True,
        show_hud: bool = True,
    ) -> np.ndarray:
        """
        Draw bounding boxes, clear multi-line movement labels, trajectory paths,
        and an informational surveillance HUD banner.
        """
        annotated_frame = frame.copy()

        # Status counters for HUD
        status_counts = {
            STATUS_STATIONARY: 0,
            STATUS_MOVING: 0,
            STATUS_FAST_MOVING: 0,
            STATUS_DIRECTION_CHANGING: 0,
        }

        for obj in analyzed_objects:
            cat = obj["category"]
            color = CATEGORY_COLORS.get(cat, (255, 255, 255))
            status = obj["movement_status"]
            status_counts[status] = status_counts.get(status, 0) + 1

            track_id = obj["track_id"]
            class_name = obj["class_name"].upper()
            x1, y1, x2, y2 = obj["bbox"]
            cx, cy = obj["center"]
            direction = obj["movement_direction"]
            speed = obj["estimated_speed_px_per_frame"]
            trajectory = obj.get("trajectory", [])

            # 1. Draw Motion Trajectory Trail
            if show_trajectory and len(trajectory) > 1:
                pts = np.array(trajectory, dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(annotated_frame, [pts], isClosed=False, color=color, thickness=2, lineType=cv2.LINE_AA)

            # 2. Draw Bounding Box (thickness: 2px)
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)

            # 3. Draw Center Point Dot
            if show_center:
                cv2.circle(annotated_frame, (cx, cy), 4, color, -1)
                cv2.circle(annotated_frame, (cx, cy), 6, (255, 255, 255), 1)

            # 4. Multi-Line Clear Movement Information Badge
            # Line 1: Header (e.g., "PERSON #1 | 92%")
            # Line 2: Movement (e.g., "DIR: RIGHT | 8.4 px/fr | MOVING")
            conf_pct = int(obj["confidence"] * 100)
            line1 = f"{class_name} #{track_id} | {conf_pct}%"
            line2 = f"{direction} | {speed:.1f} px/fr | {status}"

            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.45
            thickness = 1

            (w1, h1), _ = cv2.getTextSize(line1, font, font_scale, thickness)
            (w2, h2), _ = cv2.getTextSize(line2, font, font_scale, thickness)

            badge_w = max(w1, w2) + 12
            badge_h = h1 + h2 + 14

            badge_y1 = max(y1 - badge_h - 4, 0)
            badge_y2 = badge_y1 + badge_h
            badge_x2 = x1 + badge_w

            # Draw background badge with dark backing and colored left indicator bar
            cv2.rectangle(annotated_frame, (x1, badge_y1), (badge_x2, badge_y2), (24, 28, 32), -1)
            cv2.rectangle(annotated_frame, (x1, badge_y1), (x1 + 4, badge_y2), color, -1)
            cv2.rectangle(annotated_frame, (x1, badge_y1), (badge_x2, badge_y2), color, 1)

            # Render text lines inside badge
            cv2.putText(
                annotated_frame,
                line1,
                (x1 + 8, badge_y1 + h1 + 3),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
                lineType=cv2.LINE_AA,
            )
            cv2.putText(
                annotated_frame,
                line2,
                (x1 + 8, badge_y1 + h1 + h2 + 8),
                font,
                font_scale,
                (0, 240, 255),
                thickness,
                lineType=cv2.LINE_AA,
            )

        # 5. Top Surveillance HUD Overlay Banner
        if show_hud:
            h, w = annotated_frame.shape[:2]
            total_active = len(analyzed_objects)
            hud_text = (
                f"AI BORDER SENTINEL (STEP 4: MOVEMENT) | "
                f"TRACKS: {total_active} | "
                f"MOVING: {status_counts[STATUS_MOVING]} | "
                f"FAST: {status_counts[STATUS_FAST_MOVING]} | "
                f"STATIONARY: {status_counts[STATUS_STATIONARY]} | "
                f"TURNING: {status_counts[STATUS_DIRECTION_CHANGING]}"
            )

            overlay = annotated_frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, 36), (18, 22, 26), -1)
            cv2.addWeighted(overlay, 0.75, annotated_frame, 0.25, 0, annotated_frame)

            cv2.putText(
                annotated_frame,
                hud_text,
                (14, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (0, 255, 255),
                1,
                lineType=cv2.LINE_AA,
            )

        return annotated_frame
