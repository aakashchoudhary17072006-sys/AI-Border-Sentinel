"""
AI Border Sentinel - Step 5: Restricted-Zone Intrusion & Risk Engine Main Runner

Executes the end-to-end surveillance pipeline:
    Video Frame
        -> YOLODetector (Step 2)
        -> ByteTracker (Step 3)
        -> MovementAnalyzer (Step 4)
        -> RestrictedZone Geofence (Step 5)
        -> Explainable Risk Engine (Step 5)
        -> Video Output & Interactive Playback

Extracts:
- Virtual restricted-zone intrusion (INSIDE, NEAR, FAR) & transition events (ENTERED, EXITED)
- Moving toward restricted-zone heading vector
- Group movement clustering
- Explainable Prototype Risk Score (0-100) & Risk Level (NORMAL, MONITOR, SUSPICIOUS, CRITICAL)
- Human-readable risk reasons audit trail for every target

Saves output to 'backend/output/risk_output.mp4' and displays real-time playback.

Usage:
    python main_risk.py
    python main_risk.py --source videos/sample.mp4
    python main_risk.py --source 0                      # Live webcam
    python main_risk.py --headless                      # Run without GUI window
    python main_risk.py --conf 0.35

Press 'q' or 'Q' at any time while the video window is active to exit gracefully.
"""

import argparse
import sys
import time
from pathlib import Path
import cv2

# Step 2: Detection
from detection.detector import YOLODetector

# Step 3: Tracking
from tracking.tracker import ByteTracker

# Step 4: Movement Analysis
from analysis.movement import MovementAnalyzer

# Step 5: Restricted Zone & Risk Engine
from zone.restricted_zone import EVENT_ENTERED, EVENT_EXITED, RestrictedZone
from risk.risk_engine import (
    LEVEL_CRITICAL,
    LEVEL_MONITOR,
    LEVEL_NORMAL,
    LEVEL_SUSPICIOUS,
    RiskConfig,
    RiskEngine,
)


def parse_arguments():
    """Parse command-line arguments for Step 5 risk engine."""
    parser = argparse.ArgumentParser(
        description="AI Border Sentinel - Step 5: Restricted-Zone Intrusion & Risk Engine"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="videos/sample.mp4",
        help="Path to input video file or webcam index (default: 'videos/sample.mp4')",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/risk_output.mp4",
        help="Path to save the processed output video (default: 'output/risk_output.mp4')",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8n.pt",
        help="Pretrained YOLO model weights (default: 'yolov8n.pt')",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.35,
        help="Detection confidence threshold (default: 0.35)",
    )
    parser.add_argument(
        "--proximity-thresh",
        type=float,
        default=80.0,
        help="Image-space distance (px) to qualify as NEAR_ZONE (default: 80.0)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without opening an interactive GUI display window",
    )
    return parser.parse_args()


def run_risk_pipeline(args):
    """Main execution loop for full surveillance pipeline up to Step 5."""
    source_input = args.source
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    capture_source = int(source_input) if source_input.isdigit() else source_input

    print("=" * 76)
    print("  AI BORDER SENTINEL — STEP 5: RESTRICTED ZONE & EXPLAINABLE RISK ENGINE")
    print("=" * 76)
    print(f"[*] Video Source          : {source_input}")
    print(f"[*] Output Target         : {output_path}")
    print(f"[*] Pretrained YOLO Model : {args.model}")
    print(f"[*] Confidence Cutoff     : {args.conf}")
    print(f"[*] Zone Proximity Limit  : {args.proximity_thresh} px")
    print(f"[*] Headless Mode         : {args.headless}")
    print("=" * 76)

    cap = cv2.VideoCapture(capture_source)
    if not cap.isOpened():
        print(f"[Error] Failed to open video source '{source_input}'.")
        print("[Tip] Ensure the video file exists or run 'python videos/create_sample_video.py' first.")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = fps if fps and fps > 0 else 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"[*] Resolution            : {width}x{height}")
    print(f"[*] Frame Rate            : {fps:.2f} FPS")
    if total_frames > 0:
        print(f"[*] Total Frames          : {total_frames}")

    # Video Writer
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    # Initialize Sequential Modular Pipeline Components
    detector = YOLODetector(model_name=args.model, conf_threshold=args.conf)
    tracker = ByteTracker(
        high_thresh=args.conf,
        low_thresh=max(0.10, args.conf - 0.20),
        match_thresh=0.70,
        max_time_lost=30,
        max_trajectory_length=60,
    )
    analyzer = MovementAnalyzer(
        noise_threshold_px=2.5,
        fast_speed_threshold_px=7.0,
        history_window=5,
    )
    # Virtual Restricted Zone (configurable polygon)
    zone = RestrictedZone(
        polygon=[[30, 160], [820, 160], [820, 690], [30, 690]],
        proximity_threshold_px=args.proximity_thresh,
        zone_name="BORDER_SECTOR_ALPHA",
    )
    # Explainable Risk Engine
    risk_engine = RiskEngine(config=RiskConfig())

    frame_count = 0
    total_events_logged = []
    max_scores_by_track: dict = {}

    window_name = "AI Border Sentinel - Step 5 Risk Engine (Press 'Q' to Exit)"
    can_display = not args.headless

    print("\n[+] Running risk engine pipeline. Press 'Q' in the display window to stop.\n")
    start_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_count += 1
            frame_start = time.time()

            # 1. Step 2: YOLO Detection
            detections = detector.detect_frame(frame)

            # 2. Step 3: ByteTrack Tracking
            tracked_objects = tracker.update(detections, frame_number=frame_count)

            # 3. Step 4: Movement and Observable Behaviour Analysis
            analyzed_objects = analyzer.analyze_tracks(tracked_objects)

            # 4. Step 5 Part A: Restricted-Zone Geofencing & Heading Vector
            objects_with_zone = zone.evaluate_tracks(analyzed_objects)

            # Log one-shot transition events
            for obj in objects_with_zone:
                ev = obj.get("zone_event")
                if ev in (EVENT_ENTERED, EVENT_EXITED):
                    event_record = {
                        "frame": frame_count,
                        "track_id": obj["track_id"],
                        "category": obj["category"],
                        "event": f"RESTRICTED ZONE {ev}",
                    }
                    total_events_logged.append(event_record)
                    print(
                        f" [!] EVENT @ Frame {frame_count:03d}: "
                        f"{obj['category'].upper()} #{obj['track_id']} {ev} restricted zone!"
                    )

            # 5. Step 5 Part B: Explainable Risk Engine
            risk_assessed_objects = risk_engine.process_frame_objects(objects_with_zone)

            # Record max score seen for each track ID
            for obj in risk_assessed_objects:
                tid = obj["track_id"]
                score = obj["risk_score"]
                if tid not in max_scores_by_track or score > max_scores_by_track[tid]["score"]:
                    max_scores_by_track[tid] = {
                        "score": score,
                        "level": obj["risk_level"],
                        "category": obj["category"],
                        "reasons": obj["risk_reasons"],
                    }

            # 6. Visual Annotation: Draw Zone Polygon + Risk Badges + Trails + HUD
            frame_with_zone = zone.draw_zone(frame, alpha=0.18)
            annotated_frame = risk_engine.draw_risk_visualizations(
                frame_with_zone,
                risk_assessed_objects,
                show_trajectory=True,
                show_hud=True,
            )

            # Write to output file
            writer.write(annotated_frame)

            frame_fps = 1.0 / max(time.time() - frame_start, 1e-4)

            # Periodic console log
            if frame_count % 10 == 0 or frame_count == total_frames:
                crit_count = sum(1 for o in risk_assessed_objects if o["risk_level"] == LEVEL_CRITICAL)
                susp_count = sum(1 for o in risk_assessed_objects if o["risk_level"] == LEVEL_SUSPICIOUS)
                mon_count = sum(1 for o in risk_assessed_objects if o["risk_level"] == LEVEL_MONITOR)
                norm_count = sum(1 for o in risk_assessed_objects if o["risk_level"] == LEVEL_NORMAL)

                progress_info = (
                    f"Frame {frame_count}/{total_frames if total_frames > 0 else '?'}"
                    f" | Active: {len(risk_assessed_objects)}"
                    f" (Crit:{crit_count}, Susp:{susp_count}, Mon:{mon_count}, Norm:{norm_count})"
                    f" | Intrusions: {risk_engine.total_intrusions_detected}"
                    f" | Speed: {frame_fps:.1f} FPS"
                )
                print(f" -> {progress_info}")

            # Interactive display
            if can_display:
                try:
                    cv2.imshow(window_name, annotated_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), ord("Q"), 27):  # 'q', 'Q', or ESC
                        print("\n[!] Exit requested by user (pressed 'Q'). Stopping...")
                        break
                except cv2.error:
                    print("[Notice] Display window unavailable (headless). Continuing in background.")
                    can_display = False

    except KeyboardInterrupt:
        print("\n[!] Processing interrupted by user (Ctrl+C).")

    finally:
        cap.release()
        writer.release()
        if can_display:
            cv2.destroyAllWindows()

    elapsed_time = time.time() - start_time
    avg_fps = frame_count / max(elapsed_time, 1e-4)

    # Final Step 5 Summary Report
    print("\n" + "=" * 76)
    print("  STEP 5 RESTRICTED-ZONE & RISK ENGINE SUMMARY REPORT")
    print("=" * 76)
    print(f"[*] Frames Processed          : {frame_count}")
    print(f"[*] Processing Time           : {elapsed_time:.2f} seconds ({avg_fps:.1f} FPS average)")
    print(f"[*] Total Zone Events Emitted : {len(total_events_logged)}")
    print(f"[*] Total Targets in Perimeter: {risk_engine.total_intrusions_detected}")

    print("\n[*] Tracked Targets Threat/Suspicion Profiles (Audit Trail):")
    for tid in sorted(max_scores_by_track.keys()):
        item = max_scores_by_track[tid]
        print(f"\n  >> Target #{tid} ({item['category'].upper()}):")
        print(f"     Prototype Risk Score: {item['score']}/100 [{item['level']}]")
        print(f"     Explainable Reasons:")
        for r in item["reasons"]:
            print(f"       * {r}")

    print(f"\n[*] Saved Output File         : {output_path.resolve()}")
    if output_path.exists():
        print(f"[*] Output File Size          : {output_path.stat().st_size:,} bytes")
    print("=" * 76)
    print("[+] Step 5 successfully executed. Ready for Step 6 (Alert System).")


if __name__ == "__main__":
    args = parse_arguments()
    run_risk_pipeline(args)
