# C. elegans Computer Vision Pilot Project

A low-cost, microscope-mounted computer vision workflow for automated
*Caenorhabditis elegans* counting, density estimation, and basic behavior
analysis.

This repository is intended as a practical pilot project before extending a
similar imaging and tracking workflow to *Daphnia* behavior-based water quality
monitoring.

## Project Summary

Manual counting and video observation of small model organisms can be slow,
operator-dependent, and difficult to standardize. This project aims to combine
a low-cost imaging setup with an automated analysis pipeline that can:

- detect *C. elegans* in microscope videos;
- count worms in sampled video frames;
- estimate worm density, such as worms per mm2;
- export annotated videos and CSV result tables;
- compare automated counts against manual counts;
- provide a training workflow for future *Daphnia* detection and tracking.

The first version should be simple, reproducible, and useful in routine lab
workflows. It is not intended to replace specialized high-end worm tracking
systems.

## Why Start With C. elegans?

*C. elegans* is a good starting system because it is small, transparent, widely
used in laboratories, and easier to image under controlled conditions than
freely swimming *Daphnia*.

The core workflow is transferable even if the final biological model is not:

- image and video acquisition;
- annotation strategy;
- object detection;
- density estimation;
- multi-object tracking;
- behavior feature extraction;
- manual vs automated validation;
- error analysis under realistic lab conditions.

## First Vertical Slice

The first playable research workflow now has an OpenCV baseline CLI for video:

1. Import microscope videos.
2. Apply basic preprocessing and background correction.
3. Sample frames at a configurable interval.
4. Detect visible worms with an OpenCV baseline.
5. Count detected worms per sampled frame.
6. Convert pixel area to real-world area using calibration data.
7. Estimate density in worms/mm2 per sampled frame.
8. Export frame-level and detection-level CSV files.
9. Save an optional annotated video.

Still-image input remains available as a calibration and threshold-tuning helper.

## Quick Start

Install dependencies:

```bash
python -m pip install -r requirements.txt
python -m pip install -e software/c_elegans_counter
```

Run the baseline on a video folder. The input can contain `.mp4` videos directly
or `.zip` archives that contain videos:

```bash
c-elegans-counter analyze-video \
  --input data/example_videos \
  --calibration-um-per-pixel 2.5 \
  --frame-step 5 \
  --output results/csv/video_frames.csv \
  --detections-output results/csv/video_detections.csv \
  --annotated-video results/annotated_videos
```

On Windows PowerShell:

```powershell
c-elegans-counter analyze-video `
  --input data/example_videos `
  --calibration-um-per-pixel 2.5 `
  --frame-step 5 `
  --output results/csv/video_frames.csv `
  --detections-output results/csv/video_detections.csv `
  --annotated-video results/annotated_videos
```

For a local external data folder, point `--input` at that folder instead of
copying the raw videos into the repository.

The default assumes dark worms on a light background. If the imaging setup is
different, try `--polarity bright` or `--polarity auto`, then tune
`--min-area-px`, `--max-area-px`, `--min-aspect-ratio`, and `--min-length-px`.

## Repository Structure

```text
C_elegans_CV_Pilot_Project/
  README.md
  README.zh-CN.md
  requirements.txt
  .gitignore
  data/
    README.md
    example_images/
    example_videos/
    annotations/
  docs/
    imaging_protocol.md
    annotation_guide.md
    validation_plan.md
  hardware/
    README.md
  notebooks/
    README.md
  results/
    README.md
    annotated_images/
    annotated_videos/
    csv/
  scripts/
    README.md
  software/
    README.md
    c_elegans_counter/
      README.md
    daphnia_future/
      README.md
```

## Hardware Concept

The imaging system should use existing lab equipment where possible:

- stereomicroscope or dissecting microscope;
- smartphone, tablet, or USB camera;
- 3D-printable microscope-camera adapter;
- stable sample holder;
- controlled lighting;
- calibration slide for pixel-to-micrometer conversion.

The 3D-printed adapter is important because it standardizes camera distance,
angle, field of view, and sample positioning across sessions.

## Software Workflow

The initial software pipeline will use a simple OpenCV baseline before adding
more advanced machine learning models.

Planned video pipeline:

1. Load video input.
2. Normalize illumination and correct background.
3. Segment or detect worm-like objects.
4. Filter detections by size, shape, and confidence.
5. Count detected worms per sampled frame.
6. Apply calibration metadata.
7. Compute field area and density per frame.
8. Export frame-level and detection-level CSV results.
9. Save annotated videos.

Possible future model options:

- YOLO object detection;
- instance segmentation;
- egg, larva, and adult classification;
- simple tracking for locomotion features.

## Data And Annotation Plan

Recommended label stages:

| Stage | Labels | Purpose |
| --- | --- | --- |
| 1 | `worm` | Basic counting and density estimation |
| 2 | `worm`, `egg` | Egg-to-worm ratio and mixed sample analysis |
| 3 | `egg`, `larva`, `adult` | Developmental-stage composition |
| 4 | tracked worm IDs | Motion and activity analysis |

Manual counts should be stored with image metadata so automated results can be
validated against human analysis.

## Validation Metrics

The project should report:

- manual count vs automated count;
- mean absolute error;
- percentage error;
- precision;
- recall;
- correlation with manual counts;
- processing time per image;
- robustness across low, medium, and high density samples;
- common failure cases such as overlap, debris, eggs, and out-of-focus frames.

## Roadmap

### Phase 1: C. elegans Detection

- Collect example videos.
- Define calibration method.
- Build OpenCV baseline.
- Export annotated videos and CSV results.
- Compare with manual frame counts.

### Phase 2: Egg And Worm Detection

- Add `egg` annotation class.
- Measure egg-to-worm ratio.
- Evaluate false positives caused by debris or bubbles.

### Phase 3: Developmental Stage Classification

- Add `larva` and `adult` classes.
- Test whether image quality is sufficient for reliable classification.
- Report developmental composition.

### Phase 4: Basic Behavior Analysis

- Add short video input.
- Track worm movement.
- Extract speed, displacement, track length, activity state, and movement index.

### Phase 5: Daphnia Transfer

- Adapt the acquisition and annotation workflow to *Daphnia*.
- Track swimming behavior.
- Extract water quality stress indicators such as speed, turning frequency,
  immobility, vertical distribution, and abnormal movement.

## Expected Outputs

- 3D-printable microscope-camera adapter files.
- Standard imaging protocol.
- C. elegans detection and counting script.
- Density estimation module.
- Annotated image outputs.
- CSV result tables.
- Manual vs automated validation report.
- Small example dataset.
- GitHub repository suitable for collaboration and publication support.

## Status

This repository currently includes a project scaffold and a first OpenCV
video counting baseline. The next step is to add real microscope videos and
tune the baseline parameters against manual frame counts.

## License

License not selected yet. Choose an open-source license before public release.
