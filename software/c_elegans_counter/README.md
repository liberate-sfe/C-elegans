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

This baseline is intentionally simple. It should be tuned against real videos
before being treated as a scientific counting method.
