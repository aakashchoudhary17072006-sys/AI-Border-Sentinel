"""
AI Border Sentinel - Step 2: YOLO Object-Detection Module

Provides clean, modular object detection using pretrained YOLOv8 for border/perimeter monitoring.
Detects and categorizes:
- HUMAN: person
- ANIMAL: bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe
- VEHICLE: car, motorcycle, airplane, bus, train, truck, boat, bicycle

Outputs structured detection dictionaries formatted for seamless integration
with Step 3 (ByteTrack multi-object tracking) and Step 4 (movement/behavior analysis).
"""

from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
from ultralytics import YOLO


# Logical Surveillance Categories
CATEGORY_HUMAN = "human"
CATEGORY_ANIMAL = "animal"
CATEGORY_VEHICLE = "vehicle"

# Pretrained COCO class mappings for surveillance targets
HUMAN_CLASSES = {"person"}

ANIMAL_CLASSES = {
    "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe"
}

VEHICLE_CLASSES = {
    "bicycle", "car", "motorcycle", "airplane", "bus",
    "train", "truck", "boat"
}

# Color palette (BGR format for OpenCV)
CATEGORY_COLORS: Dict[str, Tuple[int, int, int]] = {
    CATEGORY_HUMAN: (0, 70, 255),    # Vibrant Orange/Red for Human Intrusion Alert
    CATEGORY_ANIMAL: (0, 230, 115),   # Bright Green for Wildlife / Animal activity
    CATEGORY_VEHICLE: (255, 190, 0),  # Bright Cyan/Sky Blue for Vehicles
}


class YOLODetector:
    """
    Modular YOLO detector for border and perimeter security.
    Uses pretrained weights (default: yolov8n.pt) without custom training.
    """

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        device: Optional[str] = None,
    ):
        """
        Initialize the YOLO detector.

        :param model_name: Pretrained model weights ('yolov8n.pt', 'yolov8s.pt', etc.).
        :param conf_threshold: Minimum confidence score to accept a detection (default: 0.35).
        :param iou_threshold: NMS IoU threshold (default: 0.45).
        :param device: 'cpu', 'cuda', '0', etc. If None, auto-selects available hardware.
        """
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self._model = None

    @property
    def model(self) -> YOLO:
        """Lazy-load the official pretrained YOLO model on demand."""
        if self._model is None:
            print(f"[YOLODetector] Lazy-loading pretrained model '{self.model_name}'...")
            self._model = YOLO(self.model_name)
            print(f"[YOLODetector] Model loaded successfully.")
        return self._model

    def get_category(self, class_name: str) -> Optional[str]:
        """
        Classify a detected COCO object class into surveillance categories:
        - 'human'
        - 'animal'
        - 'vehicle'
        Returns None if the object is outside these surveillance categories.
        """
        class_lower = class_name.lower().strip()
        if class_lower in HUMAN_CLASSES:
            return CATEGORY_HUMAN
        if class_lower in ANIMAL_CLASSES:
            return CATEGORY_ANIMAL
        if class_lower in VEHICLE_CLASSES:
            return CATEGORY_VEHICLE
        return None

    def detect_frame(
        self,
        frame: np.ndarray,
        conf_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run YOLO detection on a single video frame.

        Returns a list of structured detection dictionaries formatted for Step 3 (ByteTrack):
        [
            {
                "class_name": "person",
                "category": "human",
                "confidence": 0.94,
                "bbox": [x1, y1, x2, y2],
                "center": [cx, cy]
            },
            ...
        ]
        """
        if frame is None or frame.size == 0:
            return []

        conf = conf_threshold if conf_threshold is not None else self.conf_threshold

        # Run inference (verbose=False avoids flooding terminal on every frame)
        results = self.model.predict(
            source=frame,
            conf=conf,
            iou=self.iou_threshold,
            device=self.device,
            verbose=False,
        )

        detections: List[Dict[str, Any]] = []

        if not results or len(results) == 0:
            return detections

        first_result = results[0]
        boxes = first_result.boxes

        if boxes is None or len(boxes) == 0:
            return detections

        names = first_result.names  # Dict mapping class_id -> class_name

        for box in boxes:
            cls_id = int(box.cls[0].item())
            class_name = names.get(cls_id, "unknown")
            category = self.get_category(class_name)

            # Filter only targets relevant to border surveillance (human, animal, vehicle)
            if category is None:
                continue

            confidence = round(float(box.conf[0].item()), 2)

            # Bounding box coordinates: [x1, y1, x2, y2]
            xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()
            x1, y1, x2, y2 = xyxy

            # Compute bounding box center point [cx, cy]
            # Essential for Step 4 trajectory, estimated velocity, and restricted-zone proximity
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            detections.append({
                "class_name": class_name,
                "category": category,
                "confidence": confidence,
                "bbox": [x1, y1, x2, y2],
                "center": [cx, cy],
            })

        return detections

    def draw_detections(
        self,
        frame: np.ndarray,
        detections: List[Dict[str, Any]],
        show_center: bool = True,
        show_hud: bool = True,
    ) -> np.ndarray:
        """
        Draw bounding boxes, labels, and center points on the video frame.

        Labels display the category, class name, and confidence percentage:
        Example: 'HUMAN: PERSON 94%', 'ANIMAL: DOG 87%', 'VEHICLE: CAR 92%'
        """
        annotated_frame = frame.copy()

        # Category counters for HUD
        counts = {CATEGORY_HUMAN: 0, CATEGORY_ANIMAL: 0, CATEGORY_VEHICLE: 0}

        for det in detections:
            cat = det["category"]
            counts[cat] = counts.get(cat, 0) + 1

            x1, y1, x2, y2 = det["bbox"]
            cx, cy = det["center"]
            conf_pct = int(det["confidence"] * 100)
            class_name = det["class_name"].upper()
            cat_upper = cat.upper()

            # Select color based on category
            color = CATEGORY_COLORS.get(cat, (255, 255, 255))

            # 1. Draw Bounding Box (thickness: 2px)
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)

            # 2. Draw Center Point (radius: 4px, filled)
            if show_center:
                cv2.circle(annotated_frame, (cx, cy), 4, color, -1)
                cv2.circle(annotated_frame, (cx, cy), 6, (255, 255, 255), 1)

            # 3. Label text: e.g. "PERSON 94%" or "ANIMAL: DOG 87%"
            if class_name == cat_upper:
                label_text = f"{cat_upper} {conf_pct}%"
            else:
                label_text = f"{cat_upper}: {class_name} {conf_pct}%"

            # 4. Draw Label Banner with solid background for dark/night visibility
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            (text_w, text_h), baseline = cv2.getTextSize(label_text, font, font_scale, thickness)

            # Ensure label stays within top border of image
            label_y1 = max(y1 - text_h - 8, 0)
            label_y2 = label_y1 + text_h + 8
            label_x2 = x1 + text_w + 10

            cv2.rectangle(annotated_frame, (x1, label_y1), (label_x2, label_y2), color, -1)
            # Text in contrasting dark color on bright banners
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

        # 5. Top Surveillance HUD Banner
        if show_hud:
            h, w = annotated_frame.shape[:2]
            hud_text = (
                f"AI BORDER SENTINEL (STEP 2: YOLO) | "
                f"HUMANS: {counts[CATEGORY_HUMAN]} | "
                f"ANIMALS: {counts[CATEGORY_ANIMAL]} | "
                f"VEHICLES: {counts[CATEGORY_VEHICLE]}"
            )
            # Semi-transparent top ribbon
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
