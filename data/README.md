# Data

This folder is for example videos, example images, annotation files, and manual
count metadata.

Do not commit large raw datasets unless the repository is intended to host
them. For public release, use a small example dataset and document where the
full dataset can be obtained.

## Suggested Layout

```text
data/
  example_videos/
  example_images/
  annotations/
  manual_frame_counts.csv
  calibration.csv
```

## Manual Counts

Recommended CSV fields:

```text
image_id,manual_worm_count,manual_egg_count,annotator,date,notes
```

For videos, use frame-level manual counts:

```text
video_id,frame_index,timestamp_s,manual_worm_count,annotator,date,notes
```

## Calibration

Recommended CSV fields:

```text
setup_id,magnification,camera,adapter_version,um_per_pixel,calibration_date
```
