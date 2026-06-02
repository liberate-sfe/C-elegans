from __future__ import annotations

import argparse
import csv
from pathlib import Path


SUMMARY_FIELDS = [
    "image_id",
    "image_path",
    "status",
    "error",
    "worm_count",
    "manual_worm_count",
    "absolute_error",
    "percentage_error",
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return analyze_command(args)

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
    analyze.add_argument(
        "--polarity",
        choices=["dark", "bright", "auto"],
        default="dark",
        help="Use dark for dark worms on a light background.",
    )
    analyze.add_argument("--min-area-px", type=float, default=80.0)
    analyze.add_argument("--max-area-px", type=float, default=50000.0)
    analyze.add_argument("--min-aspect-ratio", type=float, default=1.2)
    analyze.add_argument("--min-length-px", type=float, default=12.0)
    analyze.add_argument("--blur-kernel", type=int, default=5)
    analyze.add_argument("--background-kernel", type=int, default=51)
    analyze.add_argument("--morph-kernel", type=int, default=3)
    analyze.set_defaults(command="analyze")
    return parser


def analyze_command(args: argparse.Namespace) -> int:
    from .analysis import DetectorConfig, analyze_image, iter_image_paths

    if args.calibration_um_per_pixel <= 0:
        raise SystemExit("--calibration-um-per-pixel must be greater than zero.")

    config = DetectorConfig(
        polarity=args.polarity,
        min_area_px=args.min_area_px,
        max_area_px=args.max_area_px,
        min_aspect_ratio=args.min_aspect_ratio,
        min_length_px=args.min_length_px,
        blur_kernel=args.blur_kernel,
        background_kernel=args.background_kernel,
        morph_kernel=args.morph_kernel,
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


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
