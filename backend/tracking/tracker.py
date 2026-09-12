"""
AI Border Sentinel - Step 3: ByteTrack Multi-Object Tracking Module

Implements ByteTrack multi-object tracking designed to sit cleanly downstream
of the Step 2 YOLODetector.

Pipeline Flow:
    Video Frame -> YOLODetector -> Detections -> ByteTracker -> Tracked Objects (Persistent IDs + Trajectory)

Key Features:
- Assigns unique, persistent integer tracking IDs (#1, #2, #3, ...).
- Implements ByteTrack two-stage data association (high-confidence matching + low-confidence occlusion recovery).
- Maintains trajectory history (ordered list of [cx, cy] center points over time) for each target.
- Formats structured outputs ready for Step 4 behavior, speed, and trajectory analysis.
- Renders color-coded bounding boxes, persistent ID tags, center points, motion trails, and surveillance HUD.
"""

from collections import deque
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

try:
    import lap
    HAS_LAP = True
except ImportError:
    HAS_LAP = False

from detection.detector import (
    CATEGORY_ANIMAL,
    CATEGORY_COLORS,
    CATEGORY_HUMAN,
    CATEGORY_VEHICLE,
)


def compute_iou_matrix(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """
    Computes pairwise IoU between two sets of bounding boxes [[x1, y1, x2, y2], ...].
    Returns an (N, M) matrix where element (i, j) is IoU(boxes_a[i], boxes_b[j]).
    """
    if len(boxes_a) == 0 or len(boxes_b) == 0:
        return np.zeros((len(boxes_a), len(boxes_b)), dtype=np.float32)

    boxes_a = np.asarray(boxes_a, dtype=np.float32)
    boxes_b = np.asarray(boxes_b, dtype=np.float32)

    # Coordinates of intersection boxes
    x1 = np.maximum(boxes_a[:, None, 0], boxes_b[None, :, 0])
    y1 = np.maximum(boxes_a[:, None, 1], boxes_b[None, :, 1])
    x2 = np.minimum(boxes_a[:, None, 2], boxes_b[None, :, 2])
    y2 = np.minimum(boxes_a[:, None, 3], boxes_b[None, :, 3])

    intersection = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)

    area_a = (boxes_a[:, 2] - boxes_a[:, 0]) * (boxes_a[:, 3] - boxes_a[:, 1])
    area_b = (boxes_b[:, 2] - boxes_b[:, 0]) * (boxes_b[:, 3] - boxes_b[:, 1])
    union = area_a[:, None] + area_b[None, :] - intersection

    return np.where(union > 0, intersection / union, 0.0)


def linear_assignment(cost_matrix: np.ndarray, thresh: float) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """
    Solves linear sum assignment using LAP (lap.lapjv) with fallback to greedy IoU.
    Returns: (matches, unmatched_a, unmatched_b)
    """
    if cost_matrix.size == 0:
        return [], list(range(cost_matrix.shape[0])), list(range(cost_matrix.shape[1]))

    matches = []
    num_rows, num_cols = cost_matrix.shape

    if HAS_LAP:
        # lap.lapjv minimizes cost
        _, x, y = lap.lapjv(cost_matrix, extend_cost=True, cost_limit=thresh)
        for row, col in enumerate(x):
            if col >= 0 and cost_matrix[row, col] <= thresh:
                matches.append((row, col))
    else:
        # Greedy fallback if lap is unavailable
        cost_copy = cost_matrix.copy()
        for _ in range(min(num_rows, num_cols)):
            min_idx = np.unravel_index(np.argmin(cost_copy), cost_copy.shape)
            r, c = min_idx
            if cost_copy[r, c] <= thresh:
                matches.append((r, c))
                cost_copy[r, :] = np.inf
                cost_copy[:, c] = np.inf
            else:
                break

    matched_rows = {r for r, _ in matches}
    matched_cols = {c for _, c in matches}
    unmatched_a = [r for r in range(num_rows) if r not in matched_rows]
    unmatched_b = [c for c in range(num_cols) if c not in matched_cols]

    return matches, unmatched_a, unmatched_b


class STrack:
    """
    Represents a single object tracklet across time.
    Maintains unique track_id, category, bounding box, center, and trajectory trail.
    """

    _count = 0  # Global auto-incrementing ID generator

    @classmethod
    def next_id(cls) -> int:
        cls._count += 1
        return cls._count

    @classmethod
    def reset_id_counter(cls) -> None:
        """Reset ID counter (useful for automated testing or new video streams)."""
        cls._count = 0

    def __init__(
        self,
        bbox: List[int],
        confidence: float,
        category: str,
        class_name: str,
        frame_id: int,
        max_trajectory_length: int = 60,
    ):
        self.track_id: int = STrack.next_id()
        self.bbox: List[int] = bbox
        self.confidence: float = confidence
        self.category: str = category
        self.class_name: str = class_name
        self.start_frame: int = frame_id
        self.frame_id: int = frame_id

        # Center point calculation
        x1, y1, x2, y2 = bbox
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        self.center: List[int] = [cx, cy]

        # Trajectory history: rolling buffer of center points [cx, cy]
        self.trajectory: deque = deque(maxlen=max_trajectory_length)
        self.trajectory.append(self.center)

        # State management
        self.is_activated: bool = True
        self.time_since_update: int = 0
        self.hit_streak: int = 1

    def update(self, bbox: List[int], confidence: float, frame_id: int) -> None:
        """Update track state with a matched detection in the current frame."""
        self.bbox = bbox
        self.confidence = confidence
        self.frame_id = frame_id
        self.time_since_update = 0
        self.hit_streak += 1

        x1, y1, x2, y2 = bbox
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        self.center = [cx, cy]
        self.trajectory.append(self.center)

    def mark_missed(self) -> None:
        """Increment time since last matched detection."""
        self.time_since_update += 1
        self.hit_streak = 0

    def to_dict(self) -> Dict[str, Any]:
        """
        Export structured dictionary contract for Step 4 (behaviour analysis).
        """
        return {
            "track_id": self.track_id,
            "category": self.category,
            "class_name": self.class_name,
            "confidence": round(float(self.confidence), 2),
            "bbox": self.bbox,
            "center": self.center,
            "frame_number": self.frame_id,
            "trajectory": list(self.trajectory),
        }


class ByteTracker:
    """
    Modular ByteTrack multi-object tracker.
    Consumes raw detections produced by YOLODetector and associates them over time.
    """

    def __init__(
        self,
        high_thresh: float = 0.50,
        low_thresh: float = 0.15,
        match_thresh: float = 0.70,  # Max cost (1.0 - IoU). 0.70 means min IoU of 0.30
        max_time_lost: int = 30,     # Keep lost tracks for 30 frames (~1.2s at 25fps)
        max_trajectory_length: int = 60,
    ):
        """
        :param high_thresh: Confidence threshold for high-priority detection matching.
        :param low_thresh: Confidence threshold for second-stage occlusion recovery.
        :param match_thresh: Maximum assignment cost threshold (1.0 - IoU).
        :param max_time_lost: Number of missed frames before a track is permanently removed.
        :param max_trajectory_length: Maximum number of trajectory points to retain per object.
        """
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        self.match_thresh = match_thresh
        self.max_time_lost = max_time_lost
        self.max_trajectory_length = max_trajectory_length

        self.tracked_tracks: List[STrack] = []  # Currently active tracks
        self.lost_tracks: List[STrack] = []     # Temporarily occluded tracks
        self.frame_id: int = 0
        self.total_unique_tracks_seen: int = 0

    def reset(self) -> None:
        """Reset tracking state for a new video stream."""
        self.tracked_tracks.clear()
        self.lost_tracks.clear()
        self.frame_id = 0
        self.total_unique_tracks_seen = 0
        STrack.reset_id_counter()

    def update(
        self,
        detections: List[Dict[str, Any]],
        frame_number: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Process detections from YOLODetector for the current frame.

        :param detections: List of dicts from YOLODetector.detect_frame():
                           [{'class_name': str, 'category': str, 'confidence': float, 'bbox': [x1, y1, x2, y2], 'center': [cx, cy]}]
        :param frame_number: Optional frame index. If None, auto-increments internal frame_id.
        :return: List of active tracked object dictionaries (with track_id and trajectory).
        """
        if frame_number is not None:
            self.frame_id = frame_number
        else:
            self.frame_id += 1

        # 1. Partition incoming detections into High and Low confidence pools
        high_dets: List[Dict[str, Any]] = []
        low_dets: List[Dict[str, Any]] = []

        for det in detections:
            conf = det.get("confidence", 0.0)
            if conf >= self.high_thresh:
                high_dets.append(det)
            elif conf >= self.low_thresh:
                low_dets.append(det)

        # Active pool of track candidates = currently tracked + lost
        pool_tracks = self.tracked_tracks + self.lost_tracks

        # ---------------------------------------------------------------------
        # STAGE 1: First Association (High Confidence Detections vs Active Tracks)
        # ---------------------------------------------------------------------
        high_boxes = np.array([d["bbox"] for d in high_dets]) if high_dets else np.empty((0, 4))
        track_boxes = np.array([t.bbox for t in pool_tracks]) if pool_tracks else np.empty((0, 4))

        iou_mat1 = compute_iou_matrix(track_boxes, high_boxes)
        cost_mat1 = 1.0 - iou_mat1

        matches_1, unmatched_tracks_1, unmatched_high_dets = linear_assignment(
            cost_mat1, thresh=self.match_thresh
        )

        matched_tracks: List[STrack] = []
        for t_idx, d_idx in matches_1:
            track = pool_tracks[t_idx]
            det = high_dets[d_idx]
            track.update(bbox=det["bbox"], confidence=det["confidence"], frame_id=self.frame_id)
            matched_tracks.append(track)

        # ---------------------------------------------------------------------
        # STAGE 2: Second Association (Low Confidence Detections vs Remaining Tracks)
        # Recovers partially occluded, shadowed, or distant border targets
        # ---------------------------------------------------------------------
        remaining_track_candidates = [pool_tracks[i] for i in unmatched_tracks_1]
        low_boxes = np.array([d["bbox"] for d in low_dets]) if low_dets else np.empty((0, 4))
        rem_track_boxes = (
            np.array([t.bbox for t in remaining_track_candidates])
            if remaining_track_candidates
            else np.empty((0, 4))
        )

        iou_mat2 = compute_iou_matrix(rem_track_boxes, low_boxes)
        cost_mat2 = 1.0 - iou_mat2

        # Use slightly looser matching threshold for occluded recovery
        matches_2, unmatched_tracks_2, _ = linear_assignment(
            cost_mat2, thresh=min(self.match_thresh + 0.1, 0.85)
        )

        for t_idx, d_idx in matches_2:
            track = remaining_track_candidates[t_idx]
            det = low_dets[d_idx]
            track.update(bbox=det["bbox"], confidence=det["confidence"], frame_id=self.frame_id)
            matched_tracks.append(track)

        # ---------------------------------------------------------------------
        # STAGE 3: Handle Unmatched Tracks (Mark as Lost or Remove)
        # ---------------------------------------------------------------------
        new_lost: List[STrack] = []
        for t_idx in unmatched_tracks_2:
            track = remaining_track_candidates[t_idx]
            track.mark_missed()
            if track.time_since_update <= self.max_time_lost:
                new_lost.append(track)

        # ---------------------------------------------------------------------
        # STAGE 4: Initialize New Tracks from Unmatched High Confidence Detections
        # ---------------------------------------------------------------------
        new_tracks: List[STrack] = []
        for d_idx in unmatched_high_dets:
            det = high_dets[d_idx]
            # Minimum confidence requirement to spawn a new tracking ID
            if det["confidence"] >= self.high_thresh:
                new_track = STrack(
                    bbox=det["bbox"],
                    confidence=det["confidence"],
                    category=det["category"],
                    class_name=det["class_name"],
                    frame_id=self.frame_id,
                    max_trajectory_length=self.max_trajectory_length,
                )
                new_tracks.append(new_track)
                self.total_unique_tracks_seen = max(self.total_unique_tracks_seen, new_track.track_id)

        # Update internal tracker state
        self.tracked_tracks = matched_tracks + new_tracks
        self.lost_tracks = new_lost

        # Return only currently active (updated this frame) tracks as structured dicts
        return [t.to_dict() for t in self.tracked_tracks]

    def draw_tracks(
        self,
        frame: np.ndarray,
        tracked_objects: List[Dict[str, Any]],
        show_trajectory: bool = True,
        show_center: bool = True,
        show_hud: bool = True,
    ) -> np.ndarray:
        """
        Draw bounding boxes with persistent Tracking IDs (e.g. 'PERSON #1 | 94%'),
        motion trajectory trails, target center points, and a surveillance HUD banner.
        """
        annotated_frame = frame.copy()

        # Category counters for active tracks
        active_counts = {CATEGORY_HUMAN: 0, CATEGORY_ANIMAL: 0, CATEGORY_VEHICLE: 0}

        for obj in tracked_objects:
            cat = obj["category"]
            active_counts[cat] = active_counts.get(cat, 0) + 1

            track_id = obj["track_id"]
            x1, y1, x2, y2 = obj["bbox"]
            cx, cy = obj["center"]
            conf_pct = int(obj["confidence"] * 100)
            class_name = obj["class_name"].upper()
            cat_upper = cat.upper()
            trajectory = obj.get("trajectory", [])

            # Category color
            color = CATEGORY_COLORS.get(cat, (255, 255, 255))

            # 1. Draw Motion Trajectory Trail (connecting past center coordinates)
            if show_trajectory and len(trajectory) > 1:
                pts = np.array(trajectory, dtype=np.int32).reshape((-1, 1, 2))
                # Draw fading / thick trail for movement direction visibility
                cv2.polylines(annotated_frame, [pts], isClosed=False, color=color, thickness=2, lineType=cv2.LINE_AA)

            # 2. Draw Bounding Box (thickness: 2px)
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)

            # 3. Draw Center Point
            if show_center:
                cv2.circle(annotated_frame, (cx, cy), 4, color, -1)
                cv2.circle(annotated_frame, (cx, cy), 6, (255, 255, 255), 1)

            # 4. Clear Tracking Label: e.g. "PERSON #1 | 94%" or "VEHICLE: CAR #3 | 89%"
            if class_name == cat_upper:
                label_text = f"{cat_upper} #{track_id} | {conf_pct}%"
            else:
                label_text = f"{class_name} #{track_id} | {conf_pct}%"

            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            (text_w, text_h), _ = cv2.getTextSize(label_text, font, font_scale, thickness)

            # Label banner coordinates
            label_y1 = max(y1 - text_h - 8, 0)
            label_y2 = label_y1 + text_h + 8
            label_x2 = x1 + text_w + 10

            cv2.rectangle(annotated_frame, (x1, label_y1), (label_x2, label_y2), color, -1)
            cv2.putText(
                annotated_frame,
                label_text,
                (x1 + 5, label_y2 - 4),
                font,
                font_scale,
                (10, 10, 10),
                thickness,
                lineType=cv2.LINE_AA,
            )

        # 5. Top Surveillance HUD Overlay
        if show_hud:
            h, w = annotated_frame.shape[:2]
            total_active = len(tracked_objects)
            hud_text = (
                f"AI BORDER SENTINEL (STEP 3: BYTETRACK) | "
                f"ACTIVE: {total_active} (H:{active_counts[CATEGORY_HUMAN]} A:{active_counts[CATEGORY_ANIMAL]} V:{active_counts[CATEGORY_VEHICLE]}) | "
                f"TOTAL SEEN: {self.total_unique_tracks_seen}"
            )

            overlay = annotated_frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, 36), (20, 24, 28), -1)
            cv2.addWeighted(overlay, 0.75, annotated_frame, 0.25, 0, annotated_frame)

            cv2.putText(
                annotated_frame,
                hud_text,
                (14, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 255),
                1,
                lineType=cv2.LINE_AA,
            )

        return annotated_frame
