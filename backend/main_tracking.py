"""
AI Border Sentinel - Step 3: ByteTrack Multi-Object Tracking Main Runner

Reads an input surveillance video, runs YOLOv8 detection, applies ByteTrack
multi-object tracking to assign persistent unique IDs (#1, #2, ...), tracks motion
trajectories over time, saves the annotated video to 'backend/output/tracked_output.mp4',
and displays real-time playback.

Pipeline Architecture:
    Video Frame -> YOLODetector -> Detections -> ByteTracker -> Tracked Objects -> Trajectory Trails

Usage:
    python main_tracking.py
    python main_tracking.py --source videos/sample.mp4
    python main_tracking.py --source 0                    # Live webcam
    python main_tracking.py --headless                    # Run without GUI display window
    python main_tracking.py --conf 0.35

Press 'q' or 'Q' at any time while the video window is active to exit gracefully.
"""

import argparse
import sys
import time
from pathlib import Path
import cv2

# Step 2: YOLO Detector (Modular import, no duplicate detection code)
from detection.detector import (
    CATEGORY_ANIMAL,
    CATEGORY_HUMAN,
    CATEGORY_VEHICLE,
    YOLODetector,
)

# Step 3: ByteTrack Tracker
from tracking.tracker import ByteTracker


def parse_arguments():
    """Parse command-line arguments for Step 3 tracking."""
    parser = argparse.ArgumentParser(
        description="AI Border Sentinel - Step 3: ByteTrack Multi-Object Tracking System"
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
        default="output/tracked_output.mp4",
        help="Path to save the processed output video (default: 'output/tracked_output.mp4')",
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
        help="YOLO detection confidence threshold (default: 0.35)",
    )
    parser.add_argument(
        "--match-thresh",
        type=float,
        default=0.70,
        help="ByteTrack max matching cost (1 - IoU, default: 0.70)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without opening an interactive GUI display window",
    )
    return parser.parse_args()


def run_tracking(args):
    """Main execution loop for video ingestion, YOLO detection, and ByteTrack tracking."""
    source_input = args.source
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Initialize Video Capture
    capture_source = int(source_input) if source_input.isdigit() else source_input

    print("=" * 72)
    print("  AI BORDER SENTINEL — STEP 3: BYTETRACK MULTI-OBJECT TRACKING")
    print("=" * 72)
    print(f"[*] Video Source       : {source_input}")
    print(f"[*] Output Target      : {output_path}")
    print(f"[*] Detection Model    : {args.model}")
    print(f"[*] Confidence Cutoff  : {args.conf}")
    print(f"[*] Matching Cost Limit: {args.match_thresh}")
    print(f"[*] Headless Mode      : {args.headless}")
    print("=" * 72)

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

    # 2. Initialize Video Writer
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    # 3. Initialize Step 2 Detector & Step 3 Tracker
    detector = YOLODetector(model_name=args.model, conf_threshold=args.conf)
    tracker = ByteTracker(
        high_thresh=args.conf,
        low_thresh=max(0.10, args.conf - 0.20),
        match_thresh=args.match_thresh,
        max_time_lost=30,
        max_trajectory_length=60,
    )

    frame_count = 0
    unique_ids_seen = set()
    category_id_counts = {CATEGORY_HUMAN: set(), CATEGORY_ANIMAL: set(), CATEGORY_VEHICLE: set()}

    window_name = "AI Border Sentinel - Step 3 ByteTrack Tracking (Press 'Q' to Exit)"
    can_display = not args.headless

    print("\n[+] Starting tracking pipeline. Press 'Q' in the display window to stop.\n")
    start_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_count += 1
            frame_start = time.time()

            # A. Step 2 Detection: extract bounding boxes from current frame
            detections = detector.detect_frame(frame)

            # B. Step 3 Tracking: associate detections across time and maintain persistent IDs
            tracked_objects = tracker.update(detections, frame_number=frame_count)

            # Accumulate unique IDs seen across video
            for obj in tracked_objects:
                tid = obj["track_id"]
                cat = obj["category"]
                unique_ids_seen.add(tid)
                if cat in category_id_counts:
                    category_id_counts[cat].add(tid)

            # C. Step 3 Visualization: render persistent IDs, bounding boxes, center dots, and motion trails
            annotated_frame = tracker.draw_tracks(
                frame,
                tracked_objects,
                show_trajectory=True,
                show_center=True,
                show_hud=True,
            )

            # Write to output video file
            writer.write(annotated_frame)

            frame_fps = 1.0 / max(time.time() - frame_start, 1e-4)

            # Periodic console progress
            if frame_count % 10 == 0 or frame_count == total_frames:
                active_humans = sum(1 for o in tracked_objects if o["category"] == CATEGORY_HUMAN)
                active_animals = sum(1 for o in tracked_objects if o["category"] == CATEGORY_ANIMAL)
                active_vehicles = sum(1 for o in tracked_objects if o["category"] == CATEGORY_VEHICLE)

                progress_info = (
                    f"Frame {frame_count}/{total_frames if total_frames > 0 else '?'}"
                    f" | Active Tracks: {len(tracked_objects)}"
                    f" (H:{active_humans}, A:{active_animals}, V:{active_vehicles})"
                    f" | Unique Targets So Far: {len(unique_ids_seen)}"
                    f" | Speed: {frame_fps:.1f} FPS"
                )
                print(f" -> {progress_info}")

            # Real-time interactive window
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

    # 4. Step 3 Summary Report
    print("\n" + "=" * 72)
    print("  STEP 3 BYTETRACK TRACKING SUMMARY REPORT")
    print("=" * 72)
    print(f"[*] Frames Processed        : {frame_count}")
    print(f"[*] Processing Time         : {elapsed_time:.2f} seconds ({avg_fps:.1f} FPS average)")
    print(f"[*] Total Unique Targets    : {len(unique_ids_seen)}")
    print(f"    - Unique Humans (IDs)   : {len(category_id_counts[CATEGORY_HUMAN])}")
    print(f"    - Unique Animals (IDs)  : {len(category_id_counts[CATEGORY_ANIMAL])}")
    print(f"    - Unique Vehicles (IDs) : {len(category_id_counts[CATEGORY_VEHICLE])}")
    print(f"[*] Saved Output File       : {output_path.resolve()}")
    if output_path.exists():
        print(f"[*] Output File Size        : {output_path.stat().st_size:,} bytes")
    print("=" * 72)
    print("[+] Step 3 successfully executed. Ready for Step 4 (Behaviour Analysis).")


if __name__ == "__main__":
    args = parse_arguments()
    run_tracking(args)
