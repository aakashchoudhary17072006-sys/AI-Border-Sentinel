"""
AI Border Sentinel - Detection Module (Step 2)
Provides YOLO-based object detection categorized for border surveillance.
"""

from app.core import *  # noqa
from detection.detector import YOLODetector

__all__ = ["YOLODetector"]
