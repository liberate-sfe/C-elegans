# Pilot ROI Video Run - 2026-06-02

This run tests automatic microscope field-of-view masking on the example
C. elegans videos.

## Input

- Local data folder: `C:\Users\shife\OneDrive\Desktop\example C elegans`
- Video containers: 2 zip files
- Videos analyzed: 19
- Sampled frames per video: 10
- Frame step: 30

## Command

```powershell
c-elegans-counter analyze-video `
  --input "C:\Users\shife\OneDrive\Desktop\example C elegans" `
  --calibration-um-per-pixel 2.5 `
  --frame-step 30 `
  --max-frames 10 `
  --output results/csv/video_sample_frames_roi.csv `
  --detections-output results/csv/video_sample_detections_roi.csv `
  --annotated-video results/annotated_videos_roi `
  --polarity auto `
  --min-area-px 180 `
  --max-area-px 25000 `
  --min-aspect-ratio 1.8 `
  --min-length-px 24 `
  --morph-kernel 3 `
  --roi-mode auto `
  --roi-margin-px 30
```

## Outputs

- One-row-per-video summary uploaded to GitHub:
  `results/csv/video_sample_summary_roi.csv`
- Frame-level CSV generated locally:
  `results/csv/video_sample_frames_roi.csv`
- Detection-level CSV generated locally:
  `results/csv/video_sample_detections_roi.csv`
- Contact-sheet preview generated locally:
  `results/annotated_images/video_sample_contact_sheet_roi.jpg`

The full annotated MP4 outputs and larger generated artifacts are kept local
because they are generated binary or run-specific artifacts.

## Result Summary

The automatic ROI mask reduced false positives from the circular microscope
edge and black background. Low-density videos that previously had small edge
detections were mostly reduced to zero or near-zero detections. High-density
videos still contain overlapping worms and debris, so they should be treated as
prototype estimates until manually validated.

| Video | Mean Count With Tuned Thresholds | Mean Count With ROI |
| --- | ---: | ---: |
| AH5615_T1 | 0.9 | 0.0 |
| JRG02_T2 | 1.0 | 0.0 |
| MIX_T3 | 0.7 | 1.8 |
| Pass_LT_T1 | 7.0 | 6.1 |
| Pass_Less_T1 | 53.4 | 45.1 |
| Pass_T2 | 70.8 | 58.3 |

## Remaining Issues

- Overlapping worms in dense samples are still difficult for contour-based
  detection.
- Debris can still be detected when it is elongated and similar in size to a
  worm.
- The next validation step is to manually count selected frames and compare
  against `video_sample_frames_roi.csv`.
