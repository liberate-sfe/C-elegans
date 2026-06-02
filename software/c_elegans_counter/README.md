# C. elegans Counter

This module contains the first OpenCV baseline for video-based worm counting
and density estimation.

## Inputs

- microscope video, video folder, zip file, or folder containing zip archives;
- calibration value in micrometers per pixel;
- frame sampling interval.

## Outputs

- frame-level summary CSV;
- optional per-detection CSV;
- optional annotated video;
- worm count per sampled frame;
- density estimate in worms/mm2 per sampled frame.

## Install

```bash
python -m pip install -e software/c_elegans_counter
```

Run this from the repository root.

## CLI

```bash
c-elegans-counter analyze-video \
  --input data/example_videos \
  --calibration-um-per-pixel 2.5 \
  --frame-step 5 \
  --output results/csv/video_frames.csv \
  --detections-output results/csv/video_detections.csv \
  --annotated-video results/annotated_videos
```

PowerShell version:

```powershell
c-elegans-counter analyze-video `
  --input data/example_videos `
  --calibration-um-per-pixel 2.5 `
  --frame-step 5 `
  --output results/csv/video_frames.csv `
  --detections-output results/csv/video_detections.csv `
  --annotated-video results/annotated_videos
```

For external pilot data, pass the folder directly:

```powershell
c-elegans-counter analyze-video `
  --input "C:\path\to\example C elegans" `
  --calibration-um-per-pixel 2.5 `
  --frame-step 5 `
  --output results/csv/video_frames.csv `
  --detections-output results/csv/video_detections.csv
```

The default settings automatically detect the circular/elliptical microscope
field of view and ignore the black border around it. This reduces false
positives from the microscope edge:

```powershell
c-elegans-counter analyze-video `
  --input "C:\path\to\example C elegans" `
  --calibration-um-per-pixel 2.5 `
  --frame-step 30 `
  --polarity auto `
  --roi-mode auto `
  --roi-margin-px 30 `
  --output results/csv/video_frames_roi.csv `
  --detections-output results/csv/video_detections_roi.csv `
  --annotated-video results/annotated_videos_roi
```

When ROI mode is enabled, `field_area_mm2` is calculated from the detected
field of view area. The CSV also reports `roi_area_px` for transparency.

## Live Camera Interface

For microscope-camera use, start the local live interface from the repository
root:

```powershell
c-elegans-live-camera --host 127.0.0.1 --port 7860 --camera-index 0
```

Then open:

```text
http://127.0.0.1:7860
```

The interface supports project presets, camera selection, live annotated camera
feed, current worm count, FPS, and inference time. The default C. elegans YOLO
preset uses the local fine-tuned model when present:

```text
runs/segment/runs/wormswin/yolo_seg_md_to_csb1_gpu_5e_frac025/weights/best.pt
```

If the model file is missing, keep the interface in preview mode or select the
OpenCV baseline until a model has been trained locally.

## Image Calibration Helper

Still-image analysis remains available for calibration frames and quick tuning:

```bash
c-elegans-counter analyze \
  --input data/example_images \
  --calibration-um-per-pixel 2.5 \
  --output results/csv/image_results.csv \
  --annotated-dir results/annotated_images
```

## Manual Count Comparison

For video validation, manually count selected frames and compare against
`video_frames.csv`. Recommended columns:

```text
video_id,frame_index,manual_worm_count
```

## Important Parameters

| Parameter | Use |
| --- | --- |
| `--polarity` | `dark`, `bright`, or `auto`; default is dark worms on light background |
| `--min-area-px` | Remove small debris |
| `--max-area-px` | Remove very large artifacts |
| `--min-aspect-ratio` | Prefer elongated worm-like detections |
| `--min-length-px` | Remove tiny objects |
| `--background-kernel` | Controls broad illumination correction |
| `--frame-step` | Analyze every Nth frame for long videos |
| `--roi-mode` | `auto` detects the microscope field of view; `none` analyzes the full frame |
| `--roi-margin-px` | Shrinks the detected field inward to avoid edge artifacts |

This baseline is intentionally simple. It should be tuned against real videos
before being treated as a scientific counting method.
