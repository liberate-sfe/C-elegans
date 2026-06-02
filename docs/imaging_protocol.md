# Imaging Protocol

This protocol should standardize image acquisition so that computer vision
results are comparable across operators, dates, and sample conditions.

## Required Equipment

- Stereomicroscope or dissecting microscope
- Smartphone, tablet, or USB camera
- 3D-printed microscope-camera adapter
- Stable sample holder
- Consistent light source
- Calibration slide

## Acquisition Metadata

Record the following for every image or video:

- sample ID
- date and operator
- microscope model
- objective or magnification setting
- camera model
- adapter version
- illumination setting
- field of view calibration
- sample medium
- expected density category: low, medium, or high

## Image Capture Guidelines

1. Fix the camera position using the printed adapter.
2. Use the same illumination setup for all comparable samples.
3. Capture a calibration image at each magnification setting.
4. Avoid saturated highlights and heavy shadows.
5. Keep sample depth and field of view consistent.
6. Capture manual count notes before automated analysis.

## File Naming

Recommended format:

```text
YYYYMMDD_sampleID_magnification_density_operator_frame.ext
```

Example:

```text
20260601_CE001_20x_low_user01_0001.jpg
```

## Calibration

Each magnification and camera setup should have a calibration value:

```text
micrometers_per_pixel
```

This value is required to convert image area into mm2 for density estimation.
