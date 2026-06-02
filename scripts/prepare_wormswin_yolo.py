from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile


SPLIT_MAP = {
    "train_annotations.json": "train",
    "test_annotations.json": "val",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert WormSwin COCO polygon annotations to YOLO segmentation format."
    )
    parser.add_argument(
        "--zip",
        dest="zip_path",
        type=Path,
        default=Path("data/raw/wormswin/md_dataset.zip"),
        help="WormSwin dataset zip archive.",
    )
    parser.add_argument(
        "--dataset-root",
        default="md_dataset",
        help="Root folder inside the zip archive.",
    )
    parser.add_argument(
        "--annotations-dir",
        default="",
        help="Optional annotation subdirectory inside the dataset root.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/wormswin_yolo/md"),
        help="Output YOLO dataset directory.",
    )
    parser.add_argument(
        "--yaml-name",
        default="wormswin_md.yaml",
        help="Dataset YAML filename to write inside the output directory.",
    )
    parser.add_argument(
        "--min-polygon-points",
        type=int,
        default=3,
        help="Drop polygons with fewer than this many points.",
    )
    args = parser.parse_args()

    if not args.zip_path.exists():
        raise SystemExit(f"Missing dataset zip: {args.zip_path}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.zip_path) as archive:
        for annotation_name, yolo_split in SPLIT_MAP.items():
            convert_split(
                archive=archive,
                dataset_root=args.dataset_root,
                annotations_dir=args.annotations_dir,
                annotation_name=annotation_name,
                yolo_split=yolo_split,
                output_dir=args.output_dir,
                min_polygon_points=args.min_polygon_points,
            )

    write_dataset_yaml(args.output_dir, args.yaml_name)
    print(f"YOLO dataset prepared: {args.output_dir}")
    print(f"Dataset YAML: {args.output_dir / args.yaml_name}")
    return 0


def convert_split(
    archive: ZipFile,
    dataset_root: str,
    annotations_dir: str,
    annotation_name: str,
    yolo_split: str,
    output_dir: Path,
    min_polygon_points: int,
) -> None:
    annotation_path_parts = [dataset_root, annotations_dir, annotation_name]
    annotation_path = "/".join(part.strip("/") for part in annotation_path_parts if part)
    coco = json.loads(archive.read(annotation_path))

    image_dir = output_dir / "images" / yolo_split
    label_dir = output_dir / "labels" / yolo_split
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)

    images = {int(item["id"]): item for item in coco["images"]}
    category_ids = sorted({int(item["id"]) for item in coco["categories"]})
    category_to_class = {category_id: index for index, category_id in enumerate(category_ids)}

    annotations_by_image: dict[int, list[dict[str, object]]] = defaultdict(list)
    for annotation in coco["annotations"]:
        if annotation.get("iscrowd", 0):
            continue
        annotations_by_image[int(annotation["image_id"])].append(annotation)

    written_images = 0
    written_objects = 0
    for image_id, image in images.items():
        file_name = str(image["file_name"])
        width = float(image["width"])
        height = float(image["height"])
        source_image_path = f"{dataset_root}/images/{file_name}"
        target_image_path = image_dir / file_name
        if not target_image_path.exists():
            target_image_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(source_image_path) as source, target_image_path.open("wb") as target:
                target.write(source.read())

        lines: list[str] = []
        for annotation in annotations_by_image.get(image_id, []):
            class_id = category_to_class[int(annotation["category_id"])]
            line = annotation_to_yolo_line(
                annotation=annotation,
                class_id=class_id,
                width=width,
                height=height,
                min_polygon_points=min_polygon_points,
            )
            if line is None:
                continue
            lines.append(line)

        label_path = label_dir / Path(file_name).with_suffix(".txt")
        label_path.parent.mkdir(parents=True, exist_ok=True)
        label_path.write_text(
            "\n".join(lines) + ("\n" if lines else ""),
            encoding="utf-8",
        )
        written_images += 1
        written_objects += len(lines)

    print(
        f"{yolo_split}: wrote {written_images} images and "
        f"{written_objects} segmentation objects"
    )


def annotation_to_yolo_line(
    annotation: dict[str, object],
    class_id: int,
    width: float,
    height: float,
    min_polygon_points: int,
) -> str | None:
    segmentation = annotation.get("segmentation")
    if not isinstance(segmentation, list) or not segmentation:
        return None

    polygons = [polygon for polygon in segmentation if isinstance(polygon, list)]
    polygons = [
        polygon
        for polygon in polygons
        if len(polygon) >= min_polygon_points * 2 and len(polygon) % 2 == 0
    ]
    if not polygons:
        return None

    polygon = max(polygons, key=len)
    normalized: list[str] = []
    for index in range(0, len(polygon), 2):
        x = clamp(float(polygon[index]) / width)
        y = clamp(float(polygon[index + 1]) / height)
        normalized.append(f"{x:.6f}")
        normalized.append(f"{y:.6f}")
    return f"{class_id} {' '.join(normalized)}"


def clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def write_dataset_yaml(output_dir: Path, yaml_name: str) -> None:
    yaml_path = output_dir / yaml_name
    dataset_path = output_dir.resolve().as_posix()
    yaml_path.write_text(
        "\n".join(
            [
                f"path: {dataset_path}",
                "train: images/train",
                "val: images/val",
                "names:",
                "  0: worm",
                "",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
