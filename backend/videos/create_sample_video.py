"""
Utility script to generate backend/videos/sample.mp4 using real surveillance test imagery.
Produces an MP4 surveillance video clip with humans and vehicles for testing Step 2 YOLO detection.
"""

from pathlib import Path
import cv2
import numpy as np
import ultralytics


def create_sample_video(
    output_path: str = "videos/sample.mp4",
    fps: float = 25.0,
    duration_sec: int = 5,
):
    """
    Creates a sample surveillance video clip by creating dynamic surveillance
    pan/zoom frames from real test imagery containing persons and vehicles.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Locate Ultralytics bundled test image containing people and vehicle
    assets_dir = Path(ultralytics.__file__).parent / "assets"
    source_img_path = assets_dir / "bus.jpg"

    if not source_img_path.exists():
        print(f"[Error] Source image not found at {source_img_path}")
        return

    base_img = cv2.imread(str(source_img_path))
    if base_img is None:
        print("[Error] Could not read base image.")
        return

    h, w = base_img.shape[:2]
    # Standardize target video dimensions (e.g. 1080x720)
    target_w, target_h = 1080, 720
    base_resized = cv2.resize(base_img, (target_w, target_h))

    total_frames = int(fps * duration_sec)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_file), fourcc, fps, (target_w, target_h))

    print(f"[Sample Video] Generating {total_frames} frames ({duration_sec}s @ {fps}fps) -> {out_file}...")

    for i in range(total_frames):
        # Simulate slight camera shake / pan characteristic of border pole cameras
        t = i / total_frames
        dx = int(12 * np.sin(2 * np.pi * t * 2))
        dy = int(6 * np.cos(2 * np.pi * t * 2))

        # Affine translation matrix
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        frame = cv2.warpAffine(base_resized, M, (target_w, target_h), borderMode=cv2.BORDER_REFLECT)

        # Add timestamp simulation overlay (typical for CCTV / border security cameras)
        timestamp_str = f"BORDER_CAM_01  2026-09-11 21:15:{i % 60:02d} SEC"
        cv2.putText(
            frame,
            timestamp_str,
            (20, target_h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (220, 220, 220),
            1,
            cv2.LINE_AA,
        )

        writer.write(frame)

    writer.release()
    print(f"[Sample Video] Successfully generated '{out_file}' ({out_file.stat().st_size} bytes).")


if __name__ == "__main__":
    create_sample_video()
