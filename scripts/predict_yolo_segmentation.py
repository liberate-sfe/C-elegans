from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a YOLO segmentation model on validation images and summarize counts."
    )
    parser.add_argument("--weights", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-csv", type=Path, default=Path("results/csv/yolo_predictions.csv"))
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--device", default="0")
    parser.add_argument("--project", default="runs/wormswin_predict")
    parser.add_argument("--name", default="user_validation")
    args = parser.parse_args()

    if not args.weights.exists():
        raise SystemExit(f"Missing model weights: {args.weights}")
    if not args.source.exists():
        raise SystemExit(f"Missing prediction source: {args.source}")
    if args.imgsz <= 0:
        raise SystemExit("--imgsz must be greater than zero.")
    if not 0 <= args.conf <= 1:
        raise SystemExit("--conf must be between 0 and 1.")

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "ultralytics is not installed. Install it with: "
            "python -m pip install ultralytics"
        ) from exc

    model = YOLO(str(args.weights))
    results = model.predict(
        source=str(args.source),
        imgsz=args.imgsz,
        conf=args.conf,
        device=args.device,
        project=args.project,
        name=args.name,
        save=True,
        save_txt=True,
        stream=True,
    )

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for result in results:
        image_path = Path(result.path)
        boxes = result.boxes
        count = 0 if boxes is None else len(boxes)
        mean_confidence = ""
        if boxes is not None and count:
            mean_confidence = float(boxes.conf.mean().item())
        rows.append(
            {
                "image_path": format_image_path(image_path, args.source),
                "predicted_worm_count": count,
                "mean_confidence": mean_confidence,
                "image_height": result.orig_shape[0],
                "image_width": result.orig_shape[1],
            }
        )

    with args.output_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "image_path",
                "predicted_worm_count",
                "mean_confidence",
                "image_height",
                "image_width",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Predicted {len(rows)} image(s).")
    print(f"Prediction CSV: {args.output_csv}")
    return 0


def format_image_path(image_path: Path, source: Path) -> str:
    source = source.resolve()
    image_path = image_path.resolve()
    if source.is_dir():
        try:
            return image_path.relative_to(source).as_posix()
        except ValueError:
            return image_path.name
    return image_path.name


if __name__ == "__main__":
    raise SystemExit(main())
