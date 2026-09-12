"""
AI Border Sentinel - Pipeline & Scenario Manager Service

Manages active surveillance video sequences, scenario selection, real-time telemetry,
tracked targets, alert generation, and range video streaming.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import cv2

from detection.detector import YOLODetector, CATEGORY_HUMAN, CATEGORY_ANIMAL, CATEGORY_VEHICLE
from tracking.tracker import ByteTracker
from analysis.movement import MovementAnalyzer
from zone.restricted_zone import RestrictedZone, EVENT_ENTERED, EVENT_EXITED
from risk.risk_engine import RiskEngine, RiskConfig, LEVEL_NORMAL, LEVEL_MONITOR, LEVEL_SUSPICIOUS, LEVEL_CRITICAL


class ScenarioManager:
    """Manages available surveillance video scenarios and scenario selection."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).resolve().parents[2]
        self._scenarios = self._discover_scenarios()
        self.active_scenario_id = "patrol1_final" if "patrol1_final" in self._scenarios else next(iter(self._scenarios.keys()), "default")

    def _discover_scenarios(self) -> Dict[str, Dict[str, Any]]:
        scenarios = {}

        # List of potential paths to look for video files
        search_candidates = [
            ("patrol1_final", "Patrol 1 Thermal Perimeter", "Primary thermal border surveillance sequence showing human perimeter approach.", [
                self.base_dir / "data" / "processed" / "patrol1_final.mp4",
                self.base_dir.parent / "data" / "processed" / "patrol1_final.mp4",
                self.base_dir / "backend" / "data" / "processed" / "patrol1_final.mp4",
                self.base_dir / "videos" / "sample.mp4",
            ]),
            ("sample", "Sample Multi-Target Surveillance", "Surveillance test clip with humans, animals, and vehicles.", [
                self.base_dir / "videos" / "sample.mp4",
                self.base_dir / "backend" / "videos" / "sample.mp4",
                self.base_dir / "data" / "processed" / "sample.mp4",
            ]),
            ("risk_output", "Risk Evaluated Feed", "Pre-analyzed perimeter risk and intrusion tracking video.", [
                self.base_dir / "output" / "risk_output.mp4",
                self.base_dir / "backend" / "output" / "risk_output.mp4",
            ]),
            ("detected_output", "Object Detection Feed", "YOLOv8 bounding box detection stream.", [
                self.base_dir / "output" / "detected_output.mp4",
                self.base_dir / "backend" / "output" / "detected_output.mp4",
            ]),
        ]

        for sc_id, title, desc, path_options in search_candidates:
            found_path = None
            for p in path_options:
                if p.exists() and p.stat().st_size > 0:
                    found_path = p
                    break

            if found_path:
                scenarios[sc_id] = {
                    "id": sc_id,
                    "title": title,
                    "description": desc,
                    "path": str(found_path.resolve()),
                    "filename": found_path.name,
                }

        # Fallback if no specific video files were found
        if not scenarios:
            fallback_path = self.base_dir / "videos" / "sample.mp4"
            scenarios["sample"] = {
                "id": "sample",
                "title": "Default Surveillance Feed",
                "description": "Default border surveillance video stream.",
                "path": str(fallback_path.resolve()),
                "filename": "sample.mp4",
            }

        return scenarios

    def list_scenarios(self) -> List[Dict[str, Any]]:
        res = []
        for sc_id, info in self._scenarios.items():
            res.append({
                "id": sc_id,
                "title": info["title"],
                "description": info["description"],
                "filename": info["filename"],
                "is_active": (sc_id == self.active_scenario_id),
            })
        return res

    def get_active_video_path(self) -> str:
        sc = self._scenarios.get(self.active_scenario_id)
        if sc and os.path.exists(sc["path"]):
            return sc["path"]
        # Fallback to first existing scenario
        for info in self._scenarios.values():
            if os.path.exists(info["path"]):
                return info["path"]
        return str(self.base_dir / "videos" / "sample.mp4")

    def select_scenario(self, scenario_id: str) -> bool:
        if scenario_id in self._scenarios:
            self.active_scenario_id = scenario_id
            return True
        # Match by partial string or filename
        for sc_id, info in self._scenarios.items():
            if scenario_id.lower() in sc_id.lower() or scenario_id.lower() in info["filename"].lower():
                self.active_scenario_id = sc_id
                return True
        return False


class SurveillancePipelineManager:
    """
    Central Manager orchestrating detection, tracking, movement analysis,
    restricted zone geofencing, risk engine scoring, and API telemetry payloads.
    """

    def __init__(self):
        self.scenario_manager = ScenarioManager()
        self._detector: Optional[YOLODetector] = None
        self.tracker = ByteTracker()
        self.analyzer = MovementAnalyzer()
        self.zone = RestrictedZone(zone_name="BORDER_SECTOR_ALPHA")
        self.risk_engine = RiskEngine()

        self.current_frame_number = 0
        self.active_targets: List[Dict[str, Any]] = []
        self.alerts_history: List[Dict[str, Any]] = []
        self.is_primed: bool = False

    @property
    def detector(self) -> YOLODetector:
        """Lazy-instantiate detector on demand."""
        if self._detector is None:
            self._detector = YOLODetector(model_name="yolov8n.pt", conf_threshold=0.35)
        return self._detector

    def ensure_primed(self):
        """Lazy-prime pipeline telemetry on demand without blocking server startup."""
        if not self.is_primed:
            self._prime_pipeline_from_active_video()
            self.is_primed = True

    def reset_pipeline(self):
        """Reset internal pipeline tracker state when switching scenarios or restarting."""
        self.tracker.reset()
        self.analyzer.reset()
        self.zone.reset()
        self.risk_engine = RiskEngine()
        self.current_frame_number = 0
        self.active_targets.clear()
        self.alerts_history.clear()
        self.is_primed = False

    def _prime_pipeline_from_active_video(self, max_frames: int = 15):
        """Read initial frames of the active video file to populate targets & telemetry."""
        video_path = self.scenario_manager.get_active_video_path()
        if not os.path.exists(video_path):
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return

        try:
            frames_read = 0
            while frames_read < max_frames:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                frames_read += 1
                self.current_frame_number = frames_read

                # Run surveillance pipeline
                detections = self.detector.detect_frame(frame)
                tracked = self.tracker.update(detections, frame_number=self.current_frame_number)
                analyzed = self.analyzer.analyze_tracks(tracked)
                zone_eval = self.zone.evaluate_tracks(analyzed)
                risk_eval = self.risk_engine.process_frame_objects(zone_eval)

                self.active_targets = risk_eval

                # Collect alerts
                for obj in risk_eval:
                    zone_ev = obj.get("zone_event")
                    cat = obj.get("category", "")
                    score = obj.get("risk_score", 0)
                    level = obj.get("risk_level", LEVEL_NORMAL)

                    if zone_ev in (EVENT_ENTERED, EVENT_EXITED):
                        alert_type = "ANIMAL_ACTIVITY" if cat == CATEGORY_ANIMAL else "RESTRICTED_ZONE_INTRUSION"
                        alert_title = "Wildlife Perimeter Activity" if cat == CATEGORY_ANIMAL else f"Border Intrusion Alert ({level})"
                        
                        alert_entry = {
                            "id": f"ALT-{len(self.alerts_history) + 1:04d}",
                            "timestamp": f"Frame #{self.current_frame_number}",
                            "track_id": obj["track_id"],
                            "category": cat,
                            "class_name": obj["class_name"],
                            "event": f"ZONE_{zone_ev}",
                            "type": alert_type,
                            "title": alert_title,
                            "risk_score": score,
                            "risk_level": level,
                            "details": obj.get("risk_reasons", ["Perimeter boundary activity"])[0],
                        }
                        self.alerts_history.append(alert_entry)

        finally:
            cap.release()

    def get_telemetry(self) -> Dict[str, Any]:
        """Return real-time telemetry summary for frontend dashboard."""
        self.ensure_primed()
        humans = sum(1 for t in self.active_targets if t.get("category") == CATEGORY_HUMAN)
        animals = sum(1 for t in self.active_targets if t.get("category") == CATEGORY_ANIMAL)
        vehicles = sum(1 for t in self.active_targets if t.get("category") == CATEGORY_VEHICLE)

        level_counts = {
            LEVEL_NORMAL: sum(1 for t in self.active_targets if t.get("risk_level") == LEVEL_NORMAL),
            LEVEL_MONITOR: sum(1 for t in self.active_targets if t.get("risk_level") == LEVEL_MONITOR),
            LEVEL_SUSPICIOUS: sum(1 for t in self.active_targets if t.get("risk_level") == LEVEL_SUSPICIOUS),
            LEVEL_CRITICAL: sum(1 for t in self.active_targets if t.get("risk_level") == LEVEL_CRITICAL),
        }

        max_score = max([t.get("risk_score", 0) for t in self.active_targets], default=0)
        overall_level = self.risk_engine.get_risk_level(max_score)

        return {
            "status": "OPERATIONAL",
            "active_scenario": self.scenario_manager.active_scenario_id,
            "frame_number": self.current_frame_number,
            "fps": 25.0,
            "targets": {
                "total": len(self.active_targets),
                "humans": humans,
                "animals": animals,
                "vehicles": vehicles,
            },
            "risk_summary": {
                "overall_level": overall_level,
                "max_score": max_score,
                "normal": level_counts[LEVEL_NORMAL],
                "monitor": level_counts[LEVEL_MONITOR],
                "suspicious": level_counts[LEVEL_SUSPICIOUS],
                "critical": level_counts[LEVEL_CRITICAL],
            },
            "intrusions_detected": self.risk_engine.total_intrusions_detected,
            "total_alerts": len(self.alerts_history),
        }

    def get_targets(self) -> List[Dict[str, Any]]:
        """Return active tracked targets list."""
        self.ensure_primed()
        return self.active_targets

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Return generated alert records."""
        self.ensure_primed()
        return self.alerts_history


# Global singleton instance
pipeline_manager = SurveillancePipelineManager()
