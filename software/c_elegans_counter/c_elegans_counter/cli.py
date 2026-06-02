from __future__ import annotations

import argparse
import csv
from pathlib import Path
from tempfile import TemporaryDirectory


SUMMARY_FIELDS = [
    "image_id",
    "image_path",
    "status",
    "error",
    "worm_count",
    "manual_worm_count",
    "absolute_error",
    "percentage_error",
    "roi_area_px",
    "field_area_mm2",
    "worm_density_per_mm2",
    "calibration_um_per_pixel",
    "width_px",
    "height_px",
    "mask_area_px",
    "polarity",
    "annotated_image",
    "processing_ms",
]

DETECTION_FIELDS = [
    "image_id",
    "detection_id",
    "x",
    "y",
    "width",
    "height",
    "centroid_x",
    "centroid_y",
    "area_px",
    "length_px",
    "aspect_ratio",
    "solidity",
]

VIDEO_FRAME_FIELDS = [
    "video_id",
    "video_path",
    "status",
    "error",
    "frame_index",
    "sampled_frame_index",
    "timestamp_s",
    "worm_count",
    "roi_area_px",
    "field_area_mm2",
    "worm_density_per_mm2",
    "calibration_um_per_pixel",
    "width_px",
    "height_px",
    "mask_area_px",
    "motion_mask_area_px",
    "polarity",
    "processing_ms",
]

VIDEO_DETECTION_FIELDS = [
    "video_id",
    "frame_index",
    "sampled_frame_index",
    "timestamp_s",
    "detection_id",
    "x",
    "y",
    "width",
    "height",
    "centroid_x",
    "centroid_y",
    "area_px",
    "length_px",
    "aspect_ratio",
    "solidity",
]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return analyze_command(args)
    if args.command == "analyze-video":
        return analyze_video_command(args)

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="c-elegans-counter",
        description="OpenCV baseline for C. elegans counting and density estimation.",
    )
    subparsers = parser.add_subparsers(dest="command")

    analyze = subparsers.add_parser(
        "analyze",
        help="Analyze one image or a directory of images.",
    )
    analyze.add_argument("--input", required=True, type=Path)
    analyze.add_argument(
        "--calibration-um-per-pixel",
        required=True,
        type=float,
        help="Micrometers per pixel for this camera and magnification setup.",
    )
    analyze.add_argument("--output", required=True, type=Path)
    analyze.add_argument("--annotated-dir", type=Path)
    analyze.add_argument("--detections-output", type=Path)
    analyze.add_argument("--manual-counts", type=Path)
    analyze.add_argument("--image-id-column", default="image_id")
    analyze.add_argument("--manual-count-column", default="manual_worm_count")
    add_detector_arguments(analyze)
    analyze.set_defaults(command="analyze")

    analyze_video = subparsers.add_parser(
        "analyze-video",
        help="Analyze one video or a directory of videos by sampling frames.",
    )
    analyze_video.add_argument("--input", required=True, type=Path)
    analyze_video.add_argument(
        "--calibration-um-per-pixel",
        required=True,
        type=float,
        help="Micrometers per pixel for this camera and magnification setup.",
    )
    analyze_video.add_argument("--output", required=True, type=Path)
    analyze_video.add_argument("--detections-output", type=Path)
    analyze_video.add_argument("--annotated-video", type=Path)
    analyze_video.add_argument(
        "--frame-step",
        type=int,
        default=1,
        help="Analyze every Nth frame; use higher values for long videos.",
    )
    analyze_video.add_argument(
        "--max-frames",
        type=int,
        help="Stop after this many sampled frames.",
    )
    add_detector_arguments(analyze_video)
    analyze_video.set_defaults(command="analyze-video")
    return parser


def add_detector_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--polarity",
        choices=["dark", "bright", "auto"],
        default="dark",
        help="Use dark for dark worms on a light background.",
    )
    parser.add_argument("--min-area-px", type=float, default=80.0)
    parser.add_argument("--max-area-px", type=float, default=50000.0)
    parser.add_argument("--min-aspect-ratio", type=float, default=1.2)
    parser.add_argument("--min-length-px", type=float, default=12.0)
    parser.add_argument("--blur-kernel", type=int, default=5)
    parser.add_argument("--background-kernel", type=int, default=51)
    parser.add_argument("--morph-kernel", type=int, default=3)
    parser.add_argument(
        "--contrast-mode",
        choices=["none", "clahe"],
        default="none",
        help="Use CLAHE to balance uneven microscope illumination before thresholding.",
    )
    parser.add_argument(
        "--clahe-clip-limit",
        type=float,
        default=2.0,
        help="CLAHE contrast limit; higher values increase local contrast.",
    )
    parser.add_argument(
        "--clahe-tile-size",
        type=int,
        default=8,
        help="CLAHE tile size in pixels.",
    )
    parser.add_argument(
        "--threshold-scale",
        type=float,
        default=1.0,
        help="Scale Otsu's threshold; values below 1.0 make detection more sensitive.",
    )
    parser.add_argument(
        "--roi-mode",
        choices=["auto", "none"],
        default="auto",
        help="Use auto to detect and crop the circular microscope field of view.",
    )
    parser.add_argument(
        "--roi-margin-px",
        type=int,
        default=30,
        help="Pixels to shrink inward from the detected microscope-field edge.",
    )
    parser.add_argument(
        "--motion-mode",
        choices=["off", "filter", "augment"],
        default="off",
        help="Use video motion to filter or augment static detections.",
    )
    parser.add_argument(
        "--motion-threshold-scale",
        type=float,
        default=1.0,
        help="Scale Otsu's threshold for frame-difference motion masks.",
    )
    parser.add_argument(
        "--motion-min-intensity",
        type=float,
        default=8.0,
        help="Minimum absolute frame-difference intensity for motion detection.",
    )
    parser.add_argument(
        "--motion-dilate-kernel",
        type=int,
        default=5,
        help="Dilate motion regions so moving worm edges overlap static detections.",
    )
    parser.add_argument(
        "--motion-min-area-px",
        type=float,
        default=5.0,
        help="Remove tiny motion regions before applying the motion mask.",
    )


def analyze_command(args: argparse.Namespace) -> int:
    from .analysis import DetectorConfig, analyze_image, iter_image_paths

    if args.calibration_um_per_pixel <= 0:
        raise SystemExit("--calibration-um-per-pixel must be greater than zero.")
    validate_detector_args(args)

    config = DetectorConfig(
        polarity=args.polarity,
        min_area_px=args.min_area_px,
        max_area_px=args.max_area_px,
        min_aspect_ratio=args.min_aspect_ratio,
        min_length_px=args.min_length_px,
        blur_kernel=args.blur_kernel,
        background_kernel=args.background_kernel,
        morph_kernel=args.morph_kernel,
        roi_mode=args.roi_mode,
        roi_margin_px=args.roi_margin_px,
        contrast_mode=args.contrast_mode,
        clahe_clip_limit=args.clahe_clip_limit,
        clahe_tile_size=args.clahe_tile_size,
        threshold_scale=args.threshold_scale,
        motion_mode=args.motion_mode,
        motion_threshold_scale=args.motion_threshold_scale,
        motion_min_intensity=args.motion_min_intensity,
        motion_dilate_kernel=args.motion_dilate_kernel,
        motion_min_area_px=args.motion_min_area_px,
    )

    manual_counts = load_manual_counts(
        args.manual_counts,
        image_id_column=args.image_id_column,
        manual_count_column=args.manual_count_column,
    )
    image_paths = iter_image_paths(args.input)
    if not image_paths:
        raise SystemExit(f"No supported images found in {args.input}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.detections_output is not None:
        args.detections_output.parent.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict[str, object]] = []
    detection_rows: list[dict[str, object]] = []

    for image_path in image_paths:
        try:
            result = analyze_image(
                image_path=image_path,
                calibration_um_per_pixel=args.calibration_um_per_pixel,
                annotated_dir=args.annotated_dir,
                config=config,
            )
            manual_count = manual_counts.get(result.image_id)
            summary_rows.append(
                build_summary_row(
                    result,
                    calibration_um_per_pixel=args.calibration_um_per_pixel,
                    manual_count=manual_count,
                )
            )
            detection_rows.extend(build_detection_rows(result))
        except Exception as exc:
            summary_rows.append(
                build_error_row(
                    image_path,
                    calibration_um_per_pixel=args.calibration_um_per_pixel,
                    error=str(exc),
                )
            )

    write_csv(args.output, SUMMARY_FIELDS, summary_rows)
    if args.detections_output is not None:
        write_csv(args.detections_output, DETECTION_FIELDS, detection_rows)

    print(f"Analyzed {len(image_paths)} image(s).")
    print(f"Summary CSV: {args.output}")
    if args.annotated_dir is not None:
        print(f"Annotated images: {args.annotated_dir}")
    if args.detections_output is not None:
        print(f"Detection CSV: {args.detections_output}")
    return 0


def analyze_video_command(args: argparse.Namespace) -> int:
    from .analysis import DetectorConfig, analyze_video, iter_video_paths

    if args.calibration_um_per_pixel <= 0:
        raise SystemExit("--calibration-um-per-pixel must be greater than zero.")
    if args.frame_step <= 0:
        raise SystemExit("--frame-step must be greater than zero.")
    if args.max_frames is not None and args.max_frames <= 0:
        raise SystemExit("--max-frames must be greater than zero.")
    validate_detector_args(args)

    config = DetectorConfig(
        polarity=args.polarity,
        min_area_px=args.min_area_px,
        max_area_px=args.max_area_px,
        min_aspect_ratio=args.min_aspect_ratio,
        min_length_px=args.min_length_px,
        blur_kernel=args.blur_kernel,
        background_kernel=args.background_kernel,
        morph_kernel=args.morph_kernel,
        roi_mode=args.roi_mode,
        roi_margin_px=args.roi_margin_px,
        contrast_mode=args.contrast_mode,
        clahe_clip_limit=args.clahe_clip_limit,
        clahe_tile_size=args.clahe_tile_size,
        threshold_scale=args.threshold_scale,
        motion_mode=args.motion_mode,
        motion_threshold_scale=args.motion_threshold_scale,
        motion_min_intensity=args.motion_min_intensity,
        motion_dilate_kernel=args.motion_dilate_kernel,
        motion_min_area_px=args.motion_min_area_px,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.detections_output is not None:
        args.detections_output.parent.mkdir(parents=True, exist_ok=True)

    frame_rows: list[dict[str, object]] = []
    detection_rows: list[dict[str, object]] = []

    with TemporaryDirectory(prefix="c_elegans_counter_") as temp_dir:
        video_paths = iter_video_paths(args.input, extraction_dir=Path(temp_dir))
        if not video_paths:
            raise SystemExit(f"No supported videos found in {args.input}")

        temp_root = Path(temp_dir)
        for video_path in video_paths:
            video_path_label = format_video_path_for_output(video_path, temp_root)
            try:
                annotated_video_path = resolve_annotated_video_path(
                    args.annotated_video,
                    video_path,
                    multiple_videos=len(video_paths) > 1,
                )
                frame_results = analyze_video(
                    video_path=video_path,
                    calibration_um_per_pixel=args.calibration_um_per_pixel,
                    annotated_video_path=annotated_video_path,
                    config=config,
                    frame_step=args.frame_step,
                    max_frames=args.max_frames,
                )
                frame_rows.extend(
                    build_video_frame_row(
                        result,
                        calibration_um_per_pixel=args.calibration_um_per_pixel,
                        video_path_label=video_path_label,
                    )
                    for result in frame_results
                )
                for result in frame_results:
                    detection_rows.extend(build_video_detection_rows(result))
            except Exception as exc:
                frame_rows.append(
                    build_video_error_row(
                        video_path,
                        calibration_um_per_pixel=args.calibration_um_per_pixel,
                        video_path_label=video_path_label,
                        error=str(exc),
                    )
                )

    write_csv(args.output, VIDEO_FRAME_FIELDS, frame_rows)
    if args.detections_output is not None:
        write_csv(args.detections_output, VIDEO_DETECTION_FIELDS, detection_rows)

    print(f"Analyzed {len(video_paths)} video(s).")
    print(f"Frame summary CSV: {args.output}")
    if args.detections_output is not None:
        print(f"Detection CSV: {args.detections_output}")
    if args.annotated_video is not None:
        print(f"Annotated video output: {args.annotated_video}")
    return 0


def load_manual_counts(
    manual_counts_path: Path | None,
    image_id_column: str,
    manual_count_column: str,
) -> dict[str, float]:
    if manual_counts_path is None:
        return {}

    counts: dict[str, float] = {}
    with manual_counts_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            image_id = row.get(image_id_column, "").strip()
            raw_count = row.get(manual_count_column, "").strip()
            if not image_id or not raw_count:
                continue
            counts[image_id] = float(raw_count)
    return counts


def validate_detector_args(args: argparse.Namespace) -> None:
    if args.min_area_px < 0:
        raise SystemExit("--min-area-px must be zero or greater.")
    if args.max_area_px <= 0:
        raise SystemExit("--max-area-px must be greater than zero.")
    if args.max_area_px < args.min_area_px:
        raise SystemExit("--max-area-px must be greater than or equal to --min-area-px.")
    if args.min_aspect_ratio <= 0:
        raise SystemExit("--min-aspect-ratio must be greater than zero.")
    if args.min_length_px < 0:
        raise SystemExit("--min-length-px must be zero or greater.")
    if args.blur_kernel <= 0:
        raise SystemExit("--blur-kernel must be greater than zero.")
    if args.background_kernel <= 0:
        raise SystemExit("--background-kernel must be greater than zero.")
    if args.morph_kernel <= 0:
        raise SystemExit("--morph-kernel must be greater than zero.")
    if args.roi_margin_px < 0:
        raise SystemExit("--roi-margin-px must be zero or greater.")
    if args.clahe_clip_limit <= 0:
        raise SystemExit("--clahe-clip-limit must be greater than zero.")
    if args.clahe_tile_size < 2:
        raise SystemExit("--clahe-tile-size must be at least 2.")
    if args.threshold_scale <= 0:
        raise SystemExit("--threshold-scale must be greater than zero.")
    if args.motion_threshold_scale <= 0:
        raise SystemExit("--motion-threshold-scale must be greater than zero.")
    if args.motion_min_intensity < 0:
        raise SystemExit("--motion-min-intensity must be zero or greater.")
    if args.motion_dilate_kernel <= 0:
        raise SystemExit("--motion-dilate-kernel must be greater than zero.")
    if args.motion_min_area_px < 0:
        raise SystemExit("--motion-min-area-px must be zero or greater.")


def build_summary_row(
    result: ImageResult,
    calibration_um_per_pixel: float,
    manual_count: float | None,
) -> dict[str, object]:
    absolute_error = ""
    percentage_error = ""
    if manual_count is not None:
        absolute_error = abs(result.worm_count - manual_count)
        if manual_count != 0:
            percentage_error = absolute_error / manual_count * 100.0

    return {
        "image_id": result.image_id,
        "image_path": str(result.image_path),
        "status": "ok",
        "error": "",
        "worm_count": result.worm_count,
        "manual_worm_count": "" if manual_count is None else manual_count,
        "absolute_error": absolute_error,
        "percentage_error": percentage_error,
        "roi_area_px": result.roi_area_px,
        "field_area_mm2": result.field_area_mm2,
        "worm_density_per_mm2": result.density_per_mm2,
        "calibration_um_per_pixel": calibration_um_per_pixel,
        "width_px": result.width_px,
        "height_px": result.height_px,
        "mask_area_px": result.mask_area_px,
        "polarity": result.polarity,
        "annotated_image": "" if result.annotated_image is None else str(result.annotated_image),
        "processing_ms": result.processing_ms,
    }


def build_error_row(
    image_path: Path,
    calibration_um_per_pixel: float,
    error: str,
) -> dict[str, object]:
    return {
        "image_id": image_path.stem,
        "image_path": str(image_path),
        "status": "error",
        "error": error,
        "worm_count": "",
        "manual_worm_count": "",
        "absolute_error": "",
        "percentage_error": "",
        "roi_area_px": "",
        "field_area_mm2": "",
        "worm_density_per_mm2": "",
        "calibration_um_per_pixel": calibration_um_per_pixel,
        "width_px": "",
        "height_px": "",
        "mask_area_px": "",
        "polarity": "",
        "annotated_image": "",
        "processing_ms": "",
    }


def build_detection_rows(result: ImageResult) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for detection in result.detections:
        rows.append(
            {
                "image_id": result.image_id,
                "detection_id": detection.detection_id,
                "x": detection.x,
                "y": detection.y,
                "width": detection.width,
                "height": detection.height,
                "centroid_x": detection.centroid_x,
                "centroid_y": detection.centroid_y,
                "area_px": detection.area_px,
                "length_px": detection.length_px,
                "aspect_ratio": detection.aspect_ratio,
                "solidity": detection.solidity,
            }
        )
    return rows


def resolve_annotated_video_path(
    annotated_video: Path | None,
    video_path: Path,
    multiple_videos: bool,
) -> Path | None:
    if annotated_video is None:
        return None
    if multiple_videos or annotated_video.suffix == "":
        annotated_video.mkdir(parents=True, exist_ok=True)
        return annotated_video / f"{video_path.stem}_annotated.mp4"
    return annotated_video


def build_video_frame_row(
    result: VideoFrameResult,
    calibration_um_per_pixel: float,
    video_path_label: str | None = None,
) -> dict[str, object]:
    return {
        "video_id": result.video_id,
        "video_path": video_path_label or str(result.video_path),
        "status": "ok",
        "error": "",
        "frame_index": result.frame_index,
        "sampled_frame_index": result.sampled_frame_index,
        "timestamp_s": result.timestamp_s,
        "worm_count": result.worm_count,
        "roi_area_px": result.roi_area_px,
        "field_area_mm2": result.field_area_mm2,
        "worm_density_per_mm2": result.density_per_mm2,
        "calibration_um_per_pixel": calibration_um_per_pixel,
        "width_px": result.width_px,
        "height_px": result.height_px,
        "mask_area_px": result.mask_area_px,
        "motion_mask_area_px": result.motion_area_px,
        "polarity": result.polarity,
        "processing_ms": result.processing_ms,
    }


def build_video_error_row(
    video_path: Path,
    calibration_um_per_pixel: float,
    video_path_label: str | None,
    error: str,
) -> dict[str, object]:
    return {
        "video_id": video_path.stem,
        "video_path": video_path_label or str(video_path),
        "status": "error",
        "error": error,
        "frame_index": "",
        "sampled_frame_index": "",
        "timestamp_s": "",
        "worm_count": "",
        "roi_area_px": "",
        "field_area_mm2": "",
        "worm_density_per_mm2": "",
        "calibration_um_per_pixel": calibration_um_per_pixel,
        "width_px": "",
        "height_px": "",
        "mask_area_px": "",
        "motion_mask_area_px": "",
        "polarity": "",
        "processing_ms": "",
    }


def format_video_path_for_output(video_path: Path, temp_root: Path) -> str:
    try:
        relative_path = video_path.relative_to(temp_root)
    except ValueError:
        return str(video_path)
    return f"zip:{relative_path.as_posix()}"


def build_video_detection_rows(result: VideoFrameResult) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for detection in result.detections:
        rows.append(
            {
                "video_id": result.video_id,
                "frame_index": result.frame_index,
                "sampled_frame_index": result.sampled_frame_index,
                "timestamp_s": result.timestamp_s,
                "detection_id": detection.detection_id,
                "x": detection.x,
                "y": detection.y,
                "width": detection.width,
                "height": detection.height,
                "centroid_x": detection.centroid_x,
                "centroid_y": detection.centroid_y,
                "area_px": detection.area_px,
                "length_px": detection.length_px,
                "aspect_ratio": detection.aspect_ratio,
                "solidity": detection.solidity,
            }
        )
    return rows


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
