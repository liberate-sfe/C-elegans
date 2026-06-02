# C. elegans Counter

This module contains the first OpenCV baseline for image-based worm counting
and density estimation.

## Inputs

- microscope image or image folder;
- calibration value in micrometers per pixel;
- optional manual count CSV.

## Outputs

- summary CSV;
- optional per-detection CSV;
- annotated images;
- worm count;
- density estimate in worms/mm2;
- optional absolute and percentage error against manual counts.

## Install

```bash
python -m pip install -e software/c_elegans_counter
```

Run this from the repository root.

## CLI

```bash
c-elegans-counter analyze \
  --input data/example_images \
  --calibration-um-per-pixel 2.5 \
  --output results/csv/results.csv \
  --detections-output results/csv/detections.csv \
  --annotated-dir results/annotated_images
```

PowerShell version:

```powershell
c-elegans-counter analyze `
  --input data/example_images `
  --calibration-um-per-pixel 2.5 `
  --output results/csv/results.csv `
  --detections-output results/csv/detections.csv `
  --annotated-dir results/annotated_images
```

## Manual Count Comparison

Use a CSV with at least:

```text
image_id,manual_worm_count
```

Then run:

```bash
c-elegans-counter analyze \
  --input data/example_images \
  --calibration-um-per-pixel 2.5 \
  --output results/csv/results.csv \
  --manual-counts data/manual_counts.example.csv
```

`image_id` should match the image filename without extension.

## Important Parameters

| Parameter | Use |
| --- | --- |
| `--polarity` | `dark`, `bright`, or `auto`; default is dark worms on light background |
| `--min-area-px` | Remove small debris |
| `--max-area-px` | Remove very large artifacts |
| `--min-aspect-ratio` | Prefer elongated worm-like detections |
| `--min-length-px` | Remove tiny objects |
| `--background-kernel` | Controls broad illumination correction |

This baseline is intentionally simple. It should be tuned against real images
before being treated as a scientific counting method.
