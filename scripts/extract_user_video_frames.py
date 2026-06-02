from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "software" / "c_elegans_counter"
sys.path.insert(0, str(PACKAGE_ROOT))

from c_elegans_counter.analysis import iter_video_paths  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract validation frames from local C. elegans videos."
    )
    parser.add_argument("--input", required=True, type=Path, help="Video, folder, or zip folder.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/validation_frames/user_videos"),
    )
    parser.add_argument(
        "--frame-step",
        type=int,
        default=30,
        help="Save every Nth frame.",
    )
    parser.add_argument(
        "--max-frames-per-video",
        type=int,
        default=10,
        help="Stop after this many saved frames per video.",
    )
    parser.add_argument(
        "--preprocess",
        choices=["raw", "balanced-gray"],
        default="balanced-gray",
        help="Save raw frames or CLAHE-balanced grayscale frames.",
    )
    parser.add_argument("--clahe-clip-limit", type=float, default=2.5)
    parser.add_argument("--clahe-tile-size", type=int, default=8)
    args = parser.parse_args()

    if args.frame_step <= 0:
        raise SystemExit("--frame-step must be greater than zero.")
    if args.max_frames_per_video <= 0:
        raise SystemExit("--max-frames-per-video must be greater than zero.")
    if args.clahe_clip_limit <= 0:
        raise SystemExit("--clahe-clip-limit must be greater than zero.")
    if args.clahe_tile_size < 2:
        raise SystemExit("--clahe-tile-size must be at least 2.")

    images_dir = args.output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "manifest.csv"

    rows: list[dict[str, object]] = []
    with TemporaryDirectory(prefix="c_elegans_validation_frames_") as temp_dir:
        video_paths = iter_video_paths(args.input, extraction_dir=Path(temp_dir))
        if not video_paths:
            raise SystemExit(f"No supported videos found in {args.input}")

        for video_path in video_paths:
            rows.extend(
                extract_frames_from_video(
                    video_path=video_path,
                    images_dir=images_dir,
                    frame_step=args.frame_step,
                    max_frames_per_video=args.max_frames_per_video,
                    preprocess=args.preprocess,
                    clahe_clip_limit=args.clahe_clip_limit,
                    clahe_tile_size=args.clahe_tile_size,
                )
            )

    with manifest_path.open("w", newline="", encoding="utf-8") as file:
        fieldnames = [
            "image_path",
            "video_id",
            "source_video_path",
            "frame_index",
            "sampled_frame_index",
            "timestamp_s",
            "preprocess",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Extracted {len(rows)} validation frame(s).")
    print(f"Images: {images_dir}")
    print(f"Manifest: {manifest_path}")
    return 0


def extract_frames_from_video(
    video_path: Path,
    images_dir: Path,
    frame_step: int,
    max_frames_per_video: int,
    preprocess: str,
    clahe_clip_limit: float,
    clahe_tile_size: int,
) -> list[dict[str, object]]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"OpenCV could not open video: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 30.0

    rows: list[dict[str, object]] = []
    frame_index = 0
    sampled_frame_index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % frame_step != 0:
                frame_index += 1
                continue
            if sampled_frame_index >= max_frames_per_video:
                break

            output_frame = preprocess_frame(
                frame=frame,
                preprocess=preprocess,
                clahe_clip_limit=clahe_clip_limit,
                clahe_tile_size=clahe_tile_size,
            )
            safe_video_id = safe_stem(video_path)
            image_name = f"{safe_video_id}_frame{frame_index:06d}.png"
            output_path = images_dir / image_name
            if not cv2.imwrite(str(output_path), output_frame):
                raise OSError(f"Could not write frame: {output_path}")

            rows.append(
                {
                    "image_path": str(output_path),
                    "video_id": video_path.stem,
                    "source_video_path": str(video_path),
                    "frame_index": frame_index,
                    "sampled_frame_index": sampled_frame_index,
                    "timestamp_s": frame_index / fps,
                    "preprocess": preprocess,
                }
            )
            sampled_frame_index += 1
            frame_index += 1
    finally:
        capture.release()

    return rows


def preprocess_frame(
    frame,
    preprocess: str,
    clahe_clip_limit: float,
    clahe_tile_size: int,
):
    if preprocess == "raw":
        return frame
    if preprocess == "balanced-gray":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(
            clipLimit=clahe_clip_limit,
            tileGridSize=(clahe_tile_size, clahe_tile_size),
        )
        balanced = clahe.apply(gray)
        return cv2.cvtColor(balanced, cv2.COLOR_GRAY2BGR)
    raise ValueError(f"Unsupported preprocess mode: {preprocess}")


def safe_stem(path: Path) -> str:
    return "".join(character if character.isalnum() else "_" for character in path.stem)


if __name__ == "__main__":
    raise SystemExit(main())
