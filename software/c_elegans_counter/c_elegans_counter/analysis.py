from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from time import perf_counter
from typing import Iterable
from zipfile import ZipFile

import cv2
import numpy as np


IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff"}
VIDEO_SUFFIXES = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".wmv"}
VIDEO_CONTAINER_SUFFIXES = {".zip"}


@dataclass(frozen=True)
class DetectorConfig:
    polarity: str = "dark"
    min_area_px: float = 80.0
    max_area_px: float = 50000.0
    min_aspect_ratio: float = 1.2
    min_length_px: float = 12.0
    blur_kernel: int = 5
    background_kernel: int = 51
    morph_kernel: int = 3
    roi_mode: str = "auto"
    roi_margin_px: int = 30


@dataclass(frozen=True)
class Detection:
    detection_id: int
    x: int
    y: int
    width: int
    height: int
    centroid_x: float
    centroid_y: float
    area_px: float
    length_px: float
    aspect_ratio: float
    solidity: float


@dataclass(frozen=True)
class ImageResult:
    image_id: str
    image_path: Path
    width_px: int
    height_px: int
    worm_count: int
    roi_area_px: int
    field_area_mm2: float
    density_per_mm2: float
    mask_area_px: int
    polarity: str
    annotated_image: Path | None
    processing_ms: float
    detections: tuple[Detection, ...]


@dataclass(frozen=True)
class VideoFrameResult:
    video_id: str
    video_path: Path
    frame_index: int
    sampled_frame_index: int
    timestamp_s: float
    width_px: int
    height_px: int
    worm_count: int
    roi_area_px: int
    field_area_mm2: float
    density_per_mm2: float
    mask_area_px: int
    polarity: str
    processing_ms: float
    detections: tuple[Detection, ...]


def iter_image_paths(input_path: Path) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() not in IMAGE_SUFFIXES:
            raise ValueError(f"Unsupported image suffix: {input_path.suffix}")
        return [input_path]

    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    return sorted(
        path
        for path in input_path.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def iter_video_paths(input_path: Path, extraction_dir: Path | None = None) -> list[Path]:
    if input_path.is_file():
        suffix = input_path.suffix.lower()
        if suffix in VIDEO_SUFFIXES:
            return [input_path]
        if suffix in VIDEO_CONTAINER_SUFFIXES:
            return extract_video_paths_from_zip(input_path, extraction_dir)
        raise ValueError(f"Unsupported video suffix: {input_path.suffix}")

    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    video_paths = sorted(
        path
        for path in input_path.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
    )
    zip_paths = sorted(
        path
        for path in input_path.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_CONTAINER_SUFFIXES
    )
    for zip_path in zip_paths:
        video_paths.extend(extract_video_paths_from_zip(zip_path, extraction_dir))
    return video_paths


def extract_video_paths_from_zip(
    zip_path: Path,
    extraction_dir: Path | None,
) -> list[Path]:
    if extraction_dir is None:
        raise ValueError("A temporary extraction directory is required for zip input.")

    output_root = extraction_dir / zip_path.stem
    output_root.mkdir(parents=True, exist_ok=True)
    extracted_paths: list[Path] = []

    with ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            member_name = Path(member.filename)
            if member_name.suffix.lower() not in VIDEO_SUFFIXES:
                continue

            safe_name = "_".join(part for part in member_name.parts if part not in {"", ".", ".."})
            target_path = output_root / safe_name
            with archive.open(member) as source, target_path.open("wb") as target:
                shutil.copyfileobj(source, target)
            extracted_paths.append(target_path)

    return sorted(extracted_paths)


def analyze_image(
    image_path: Path,
    calibration_um_per_pixel: float,
    annotated_dir: Path | None,
    config: DetectorConfig,
) -> ImageResult:
    start = perf_counter()
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"OpenCV could not read image: {image_path}")

    frame_result = analyze_frame_array(
        image=image,
        calibration_um_per_pixel=calibration_um_per_pixel,
        config=config,
    )

    annotated_image = None
    if annotated_dir is not None:
        annotated_dir.mkdir(parents=True, exist_ok=True)
        annotated = draw_annotations(
            image,
            frame_result["detections"],
            roi_mask=frame_result["roi_mask"],
        )
        annotated_image = annotated_dir / f"{image_path.stem}_annotated.png"
        if not cv2.imwrite(str(annotated_image), annotated):
            raise OSError(f"Could not write annotated image: {annotated_image}")

    processing_ms = (perf_counter() - start) * 1000.0

    return ImageResult(
        image_id=image_path.stem,
        image_path=image_path,
        width_px=frame_result["width_px"],
        height_px=frame_result["height_px"],
        worm_count=frame_result["worm_count"],
        roi_area_px=frame_result["roi_area_px"],
        field_area_mm2=frame_result["field_area_mm2"],
        density_per_mm2=frame_result["density_per_mm2"],
        mask_area_px=frame_result["mask_area_px"],
        polarity=frame_result["polarity"],
        annotated_image=annotated_image,
        processing_ms=processing_ms,
        detections=frame_result["detections"],
    )


def analyze_video(
    video_path: Path,
    calibration_um_per_pixel: float,
    annotated_video_path: Path | None,
    config: DetectorConfig,
    frame_step: int = 1,
    max_frames: int | None = None,
) -> tuple[VideoFrameResult, ...]:
    frame_step = max(1, int(frame_step))
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"OpenCV could not open video: {video_path}")

    source_fps = capture.get(cv2.CAP_PROP_FPS)
    if not source_fps or source_fps <= 0:
        source_fps = 30.0

    width_px = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height_px = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    writer = None
    if annotated_video_path is not None:
        annotated_video_path.parent.mkdir(parents=True, exist_ok=True)
        output_fps = max(1.0, source_fps / frame_step)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(annotated_video_path),
            fourcc,
            output_fps,
            (width_px, height_px),
        )
        if not writer.isOpened():
            capture.release()
            raise OSError(f"Could not write annotated video: {annotated_video_path}")

    results: list[VideoFrameResult] = []
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

            if max_frames is not None and sampled_frame_index >= max_frames:
                break

            start = perf_counter()
            frame_result = analyze_frame_array(
                image=frame,
                calibration_um_per_pixel=calibration_um_per_pixel,
                config=config,
            )
            processing_ms = (perf_counter() - start) * 1000.0
            timestamp_s = frame_index / source_fps

            result = VideoFrameResult(
                video_id=video_path.stem,
                video_path=video_path,
                frame_index=frame_index,
                sampled_frame_index=sampled_frame_index,
                timestamp_s=timestamp_s,
                width_px=frame_result["width_px"],
                height_px=frame_result["height_px"],
                worm_count=frame_result["worm_count"],
                roi_area_px=frame_result["roi_area_px"],
                field_area_mm2=frame_result["field_area_mm2"],
                density_per_mm2=frame_result["density_per_mm2"],
                mask_area_px=frame_result["mask_area_px"],
                polarity=frame_result["polarity"],
                processing_ms=processing_ms,
                detections=frame_result["detections"],
            )
            results.append(result)

            if writer is not None:
                writer.write(
                    draw_annotations(
                        frame,
                        result.detections,
                        roi_mask=frame_result["roi_mask"],
                    )
                )

            sampled_frame_index += 1
            frame_index += 1
    finally:
        capture.release()
        if writer is not None:
            writer.release()

    return tuple(results)


def analyze_frame_array(
    image: np.ndarray,
    calibration_um_per_pixel: float,
    config: DetectorConfig,
) -> dict[str, object]:
    height_px, width_px = image.shape[:2]
    roi_mask = _build_roi_mask(image, config)
    mask, detections, selected_polarity = _detect_worms(image, config, roi_mask)
    if roi_mask is None:
        roi_area_px = width_px * height_px
    else:
        roi_area_px = int(np.count_nonzero(roi_mask))
    pixel_area_mm2 = (calibration_um_per_pixel / 1000.0) ** 2
    field_area_mm2 = roi_area_px * pixel_area_mm2
    worm_count = len(detections)
    density_per_mm2 = worm_count / field_area_mm2 if field_area_mm2 > 0 else 0.0

    return {
        "width_px": width_px,
        "height_px": height_px,
        "worm_count": worm_count,
        "roi_area_px": roi_area_px,
        "field_area_mm2": field_area_mm2,
        "density_per_mm2": density_per_mm2,
        "mask_area_px": int(np.count_nonzero(mask)),
        "polarity": selected_polarity,
        "roi_mask": roi_mask,
        "detections": tuple(detections),
    }


def draw_annotations(
    image: np.ndarray,
    detections: Iterable[Detection],
    roi_mask: np.ndarray | None = None,
) -> np.ndarray:
    annotated = image.copy()
    if roi_mask is not None:
        contours, _ = cv2.findContours(roi_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(annotated, contours, -1, (80, 220, 80), 2)
    for detection in detections:
        top_left = (detection.x, detection.y)
        bottom_right = (
            detection.x + detection.width,
            detection.y + detection.height,
        )
        cv2.rectangle(annotated, top_left, bottom_right, (0, 180, 255), 2)
        cv2.circle(
            annotated,
            (int(round(detection.centroid_x)), int(round(detection.centroid_y))),
            3,
            (0, 80, 255),
            -1,
        )
        cv2.putText(
            annotated,
            str(detection.detection_id),
            (detection.x, max(12, detection.y - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 80, 255),
            1,
            cv2.LINE_AA,
        )
    return annotated


def _detect_worms(
    image: np.ndarray,
    config: DetectorConfig,
    roi_mask: np.ndarray | None,
) -> tuple[np.ndarray, list[Detection], str]:
    if config.polarity == "auto":
        dark_mask, dark_detections = _detect_for_polarity(image, config, "dark", roi_mask)
        bright_mask, bright_detections = _detect_for_polarity(image, config, "bright", roi_mask)
        if len(bright_detections) > len(dark_detections):
            return bright_mask, bright_detections, "bright"
        return dark_mask, dark_detections, "dark"

    mask, detections = _detect_for_polarity(image, config, config.polarity, roi_mask)
    return mask, detections, config.polarity


def _detect_for_polarity(
    image: np.ndarray,
    config: DetectorConfig,
    polarity: str,
    roi_mask: np.ndarray | None,
) -> tuple[np.ndarray, list[Detection]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, _odd_kernel(config.blur_kernel), 0)
    background = cv2.GaussianBlur(gray, _odd_kernel(config.background_kernel), 0)

    if polarity == "dark":
        corrected = cv2.subtract(background, gray)
    elif polarity == "bright":
        corrected = cv2.subtract(gray, background)
    else:
        raise ValueError(f"Unsupported polarity: {polarity}")

    corrected = cv2.normalize(corrected, None, 0, 255, cv2.NORM_MINMAX)
    corrected = corrected.astype(np.uint8)

    _, mask = cv2.threshold(
        corrected,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        _odd_kernel(config.morph_kernel),
    )
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    if roi_mask is not None:
        mask = cv2.bitwise_and(mask, roi_mask)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detections = _filter_contours(contours, config)
    return mask, detections


def _build_roi_mask(image: np.ndarray, config: DetectorConfig) -> np.ndarray | None:
    if config.roi_mode == "none":
        return None
    if config.roi_mode != "auto":
        raise ValueError(f"Unsupported ROI mode: {config.roi_mode}")

    height_px, width_px = image.shape[:2]
    frame_area_px = width_px * height_px
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, _odd_kernel(config.background_kernel), 0)
    _, light_mask = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    cleanup_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, _odd_kernel(31))
    light_mask = cv2.morphologyEx(light_mask, cv2.MORPH_CLOSE, cleanup_kernel)
    light_mask = cv2.morphologyEx(light_mask, cv2.MORPH_OPEN, cleanup_kernel)

    contours, _ = cv2.findContours(light_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    field_contour = max(contours, key=cv2.contourArea)
    field_area_px = float(cv2.contourArea(field_contour))
    area_ratio = field_area_px / frame_area_px if frame_area_px > 0 else 0.0
    if area_ratio < 0.15 or area_ratio > 0.98:
        return None

    roi_mask = np.zeros((height_px, width_px), dtype=np.uint8)
    hull = cv2.convexHull(field_contour)
    cv2.drawContours(roi_mask, [hull], -1, 255, thickness=cv2.FILLED)

    margin_px = max(0, int(config.roi_margin_px))
    if margin_px > 0:
        distance = cv2.distanceTransform(roi_mask, cv2.DIST_L2, 5)
        roi_mask = np.where(distance > margin_px, 255, 0).astype(np.uint8)
        if np.count_nonzero(roi_mask) < frame_area_px * 0.05:
            return None

    return roi_mask


def _filter_contours(
    contours: Iterable[np.ndarray],
    config: DetectorConfig,
) -> list[Detection]:
    detections: list[Detection] = []
    for contour in contours:
        area_px = float(cv2.contourArea(contour))
        if area_px < config.min_area_px or area_px > config.max_area_px:
            continue

        x, y, width, height = cv2.boundingRect(contour)
        length_px = float(max(width, height))
        if length_px < config.min_length_px:
            continue

        short_side = max(1, min(width, height))
        aspect_ratio = float(max(width, height) / short_side)
        if aspect_ratio < config.min_aspect_ratio:
            continue

        hull = cv2.convexHull(contour)
        hull_area = float(cv2.contourArea(hull))
        solidity = area_px / hull_area if hull_area > 0 else 0.0
        moments = cv2.moments(contour)
        if moments["m00"] != 0:
            centroid_x = float(moments["m10"] / moments["m00"])
            centroid_y = float(moments["m01"] / moments["m00"])
        else:
            centroid_x = float(x + width / 2)
            centroid_y = float(y + height / 2)

        detections.append(
            Detection(
                detection_id=0,
                x=x,
                y=y,
                width=width,
                height=height,
                centroid_x=centroid_x,
                centroid_y=centroid_y,
                area_px=area_px,
                length_px=length_px,
                aspect_ratio=aspect_ratio,
                solidity=solidity,
            )
        )

    detections.sort(key=lambda detection: (detection.y, detection.x))
    return [
        Detection(
            detection_id=index,
            x=detection.x,
            y=detection.y,
            width=detection.width,
            height=detection.height,
            centroid_x=detection.centroid_x,
            centroid_y=detection.centroid_y,
            area_px=detection.area_px,
            length_px=detection.length_px,
            aspect_ratio=detection.aspect_ratio,
            solidity=detection.solidity,
        )
        for index, detection in enumerate(detections, start=1)
    ]


def _odd_kernel(value: int) -> tuple[int, int]:
    value = max(1, int(value))
    if value % 2 == 0:
        value += 1
    return value, value
