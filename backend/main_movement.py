"""
AI Border Sentinel - Step 4: Movement and Observable Behaviour Analysis Main Runner

Executes the end-to-end surveillance pipeline:
    Video Frame -> YOLODetector -> ByteTracker -> MovementAnalyzer -> Video Output & Display

Extracts physical, observable movement metrics:
- Direction (LEFT, RIGHT, UP, DOWN, diagonals, STATIONARY)
- Estimated image-space speed (px/frame)
- Cumulative distance travelled (px)
- Direction changes count
- Persistence (frames observed)
- Movement status (STATIONARY, MOVING, FAST_MOVING, DIRECTION_CHANGING)

Saves output to 'backend/output/movement_output.mp4' and displays real-time playback.

Usage:
    python main_movement.py
    python main_movement.py --source videos/sample.mp4
    python main_movement.py --source 0                    # Live webcam
    python main_movement.py --headless                    # Run without GUI window
    python main_movement.py --conf 0.35

Press 'q' or 'Q' at any time while the video window is active to exit gracefully.
"""

import argparse
import sys
import time
from pathlib import Path
import cv2

# Step 2: YOLO Detection
from detection.detector import YOLODetector

# Step 3: ByteTrack Multi-Object Tracking
from tracking.tracker import ByteTracker

# Step 4: Movement & Observable Behaviour Analysis
from analysis.movement import (
    MovementAnalyzer,
    STATUS_DIRECTION_CHANGING,
    STATUS_FAST_MOVING,
    STATUS_MOVING,
    STATUS_STATIONARY,
)


def parse_arguments():
    """Parse command-line arguments for Step 4 movement analysis."""
    parser = argparse.ArgumentParser(
        description="AI Border Sentinel - Step 4: Movement and Behaviour Analysis System"
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
        default="output/movement_output.mp4",
        help="Path to save the processed output video (default: 'output/movement_output.mp4')",
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
        "--headless",
        action="store_true",
        help="Run without opening an interactive GUI display window",
    )
    return parser.parse_args()


def run_movement_pipeline(args):
    """Main execution loop for video frame ingestion, detection, tracking, and movement analysis."""
    source_input = args.source
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    capture_source = int(source_input) if source_input.isdigit() else source_input

    print("=" * 74)
    print("  AI BORDER SENTINEL — STEP 4: MOVEMENT & OBSERVABLE BEHAVIOUR ANALYSIS")
    print("=" * 74)
    print(f"[*] Video Source       : {source_input}")
    print(f"[*] Output Target      : {output_path}")
    print(f"[*] Detection Model    : {args.model}")
    print(f"[*] Confidence Cutoff  : {args.conf}")
    print(f"[*] Headless Mode      : {args.headless}")
    print("=" * 74)

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

    print(f"[*] Resolution         : {width}x{height}")
    print(f"[*] Frame Rate         : {fps:.2f} FPS")
    if total_frames > 0:
        print(f"[*] Total Frames       : {total_frames}")

    # Video Writer for output
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    # Initialize Pipeline Components (Decoupled & Sequential)
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

    frame_count = 0
    all_observed_track_ids = set()

    window_name = "AI Border Sentinel - Step 4 Movement Analysis (Press 'Q' to Exit)"
    can_display = not args.headless

    print("\n[+] Running surveillance pipeline. Press 'Q' in the display window to stop.\n")
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

            # 2. Step 3: ByteTrack Multi-Object Tracking
            tracked_objects = tracker.update(detections, frame_number=frame_count)

            # 3. Step 4: Movement and Observable Behaviour Analysis
            analyzed_objects = analyzer.analyze_tracks(tracked_objects)

            for obj in analyzed_objects:
                all_observed_track_ids.add(obj["track_id"])

            # 4. Step 4 Visualization: render movement badges, motion trails, center dots, and HUD
            annotated_frame = analyzer.draw_movement_analysis(
                frame,
                analyzed_objects,
                show_trajectory=True,
                show_center=True,
                show_hud=True,
            )

            # Write to output file
            writer.write(annotated_frame)

            frame_fps = 1.0 / max(time.time() - frame_start, 1e-4)

            # Console logging
            if frame_count % 10 == 0 or frame_count == total_frames:
                status_summary = (
                    f"Frame {frame_count}/{total_frames if total_frames > 0 else '?'}"
                    f" | Active: {len(analyzed_objects)}"
                    f" (Mov:{sum(1 for o in analyzed_objects if o['movement_status'] == STATUS_MOVING)}, "
                    f"Fast:{sum(1 for o in analyzed_objects if o['movement_status'] == STATUS_FAST_MOVING)}, "
                    f"Stat:{sum(1 for o in analyzed_objects if o['movement_status'] == STATUS_STATIONARY)})"
                    f" | Speed: {frame_fps:.1f} FPS"
                )
                print(f" -> {status_summary}")

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

    # Final Step 4 Summary
    print("\n" + "=" * 74)
    print("  STEP 4 MOVEMENT & BEHAVIOUR ANALYSIS SUMMARY REPORT")
    print("=" * 74)
    print(f"[*] Total Frames Processed  : {frame_count}")
    print(f"[*] Processing Time          : {elapsed_time:.2f} seconds ({avg_fps:.1f} FPS average)")
    print(f"[*] Unique Targets Analyzed  : {len(all_observed_track_ids)}")

    # Print details for each tracked target profile
    print("\n[*] Track Profiles & Observable Movement Summary:")
    for tid in sorted(analyzer._profiles.keys()):
        prof = analyzer._profiles[tid]
        print(
            f"    - Target #{prof.track_id}: "
            f"Observed: {prof.frames_observed} frames | "
            f"Dist: {prof.distance_travelled_px:.1f} px | "
            f"Avg Speed: {prof.estimated_speed_px_per_frame:.1f} px/fr | "
            f"Dir: {prof.current_direction} | "
            f"Dir Changes: {prof.direction_changes} | "
            f"Status: {prof.movement_status}"
        )

    print(f"\n[*] Saved Output File        : {output_path.resolve()}")
    if output_path.exists():
        print(f"[*] Output File Size         : {output_path.stat().st_size:,} bytes")
    print("=" * 74)
    print("[+] Step 4 successfully executed. Ready for Step 5 (Threat Engine).")


if __name__ == "__main__":
    args = parse_arguments()
    run_movement_pipeline(args)
