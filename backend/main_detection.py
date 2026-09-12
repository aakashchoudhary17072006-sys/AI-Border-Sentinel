"""
AI Border Sentinel - Step 2: YOLO Object-Detection Main Runner

Reads an input surveillance video frame-by-frame, runs YOLOv8 detection,
categorizes targets (HUMAN, ANIMAL, VEHICLE), renders bounding boxes and center points,
saves the output video to 'backend/output/detected_output.mp4', and displays real-time playback.

Usage:
    python main_detection.py
    python main_detection.py --source videos/sample.mp4
    python main_detection.py --source 0                      # Use live webcam
    python main_detection.py --headless                      # Run without GUI window display
    python main_detection.py --conf 0.40                     # Custom confidence threshold

Press 'q' or 'Q' at any time while the video window is active to exit gracefully.
"""

import argparse
import sys
import time
from pathlib import Path
import cv2

# Import modular detector from Step 2 detection package
from detection.detector import (
    CATEGORY_ANIMAL,
    CATEGORY_HUMAN,
    CATEGORY_VEHICLE,
    YOLODetector,
)


def parse_arguments():
    """Parse command-line arguments for Step 2 detection."""
    parser = argparse.ArgumentParser(
        description="AI Border Sentinel - Step 2: YOLO Detection System"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="videos/sample.mp4",
        help="Path to input video file or webcam index (e.g., 'videos/sample.mp4' or '0')",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/detected_output.mp4",
        help="Path to save the processed output video (default: 'output/detected_output.mp4')",
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
        help="Confidence threshold for object detection (default: 0.35)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode without opening an interactive GUI display window",
    )
    return parser.parse_args()


def run_detection(args):
    """Main execution loop for video frame ingestion and YOLO detection."""
    source_input = args.source
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Initialize Video Capture Source
    # If source is a numeric digit string (e.g. '0'), treat it as a webcam index
    capture_source = int(source_input) if source_input.isdigit() else source_input

    print("=" * 70)
    print("  AI BORDER SENTINEL — STEP 2: YOLO OBJECT DETECTION")
    print("=" * 70)
    print(f"[*] Video Source    : {source_input}")
    print(f"[*] Output Target   : {output_path}")
    print(f"[*] Pretrained Model: {args.model}")
    print(f"[*] Confidence Cutoff: {args.conf}")
    print(f"[*] Headless Mode   : {args.headless}")
    print("=" * 70)

    cap = cv2.VideoCapture(capture_source)
    if not cap.isOpened():
        print(f"[Error] Failed to open video source '{source_input}'.")
        print("[Tip] Ensure the video file exists or run 'python videos/create_sample_video.py' first.")
        sys.exit(1)

    # 2. Extract Video Properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = fps if fps and fps > 0 else 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"[*] Input Resolution: {width}x{height}")
    print(f"[*] Frame Rate      : {fps:.2f} FPS")
    if total_frames > 0:
        print(f"[*] Total Frames    : {total_frames}")

    # 3. Initialize Video Writer for output
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    # 4. Initialize YOLO Detector
    detector = YOLODetector(model_name=args.model, conf_threshold=args.conf)

    # Tracking cumulative statistics across video
    frame_count = 0
    total_detections_count = 0
    category_totals = {CATEGORY_HUMAN: 0, CATEGORY_ANIMAL: 0, CATEGORY_VEHICLE: 0}

    window_name = "AI Border Sentinel - Step 2 YOLO Detection (Press 'Q' to Exit)"
    can_display = not args.headless

    print("\n[+] Starting frame-by-frame processing. Press 'Q' in the display window to stop.\n")
    start_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                # End of video stream reached
                break

            frame_count += 1
            frame_start = time.time()

            # Step 2 Core: Run YOLO object detection on the current frame
            # Returns structured list of dicts: class_name, category, confidence, bbox, center
            detections = detector.detect_frame(frame)

            # Update surveillance metrics
            for det in detections:
                cat = det["category"]
                category_totals[cat] = category_totals.get(cat, 0) + 1
                total_detections_count += 1

            # Step 2 Core: Render color-coded bounding boxes, labels, and center points
            annotated_frame = detector.draw_detections(frame, detections)

            # Write the annotated frame to output file
            writer.write(annotated_frame)

            # Compute processing FPS for this frame
            frame_fps = 1.0 / max(time.time() - frame_start, 1e-4)

            # Console log progress periodically
            if frame_count % 10 == 0 or frame_count == total_frames:
                progress_info = (
                    f"Frame {frame_count}/{total_frames if total_frames > 0 else '?'}"
                    f" | Detections: {len(detections)}"
                    f" (H:{sum(1 for d in detections if d['category'] == CATEGORY_HUMAN)}, "
                    f"A:{sum(1 for d in detections if d['category'] == CATEGORY_ANIMAL)}, "
                    f"V:{sum(1 for d in detections if d['category'] == CATEGORY_VEHICLE)})"
                    f" | Speed: {frame_fps:.1f} FPS"
                )
                print(f" -> {progress_info}")

            # Real-time interactive display
            if can_display:
                try:
                    cv2.imshow(window_name, annotated_frame)
                    # Check if user pressed 'q' or 'Q' to stop
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), ord("Q"), 27):  # 'q', 'Q', or ESC
                        print("\n[!] Exit requested by user (pressed 'Q'). Stopping...")
                        break
                except cv2.error:
                    # Graceful fallback if GUI backend is unavailable in this environment
                    print("[Notice] Display window unavailable (headless environment). Continuing in background.")
                    can_display = False

    except KeyboardInterrupt:
        print("\n[!] Processing interrupted by user (Ctrl+C).")

    finally:
        # Clean up resources
        cap.release()
        writer.release()
        if can_display:
            cv2.destroyAllWindows()

    elapsed_time = time.time() - start_time
    avg_fps = frame_count / max(elapsed_time, 1e-4)

    # 5. Summary Report
    print("\n" + "=" * 70)
    print("  STEP 2 DETECTION SUMMARY REPORT")
    print("=" * 70)
    print(f"[*] Frames Processed : {frame_count}")
    print(f"[*] Total Time       : {elapsed_time:.2f} seconds ({avg_fps:.1f} FPS average)")
    print(f"[*] Total Detections : {total_detections_count}")
    print(f"    - Humans Detected  : {category_totals[CATEGORY_HUMAN]}")
    print(f"    - Animals Detected : {category_totals[CATEGORY_ANIMAL]}")
    print(f"    - Vehicles Detected: {category_totals[CATEGORY_VEHICLE]}")
    print(f"[*] Saved Output File: {output_path.resolve()}")
    if output_path.exists():
        print(f"[*] Output File Size : {output_path.stat().st_size:,} bytes")
    print("=" * 70)
    print("[+] Step 2 successfully executed. Ready for Step 3 (ByteTrack Tracking).")


if __name__ == "__main__":
    args = parse_arguments()
    run_detection(args)
