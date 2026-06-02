# Live Camera Interface

The live interface is intended for microscope-camera use: open a local browser
page, select a project, select a camera, and monitor the current microscope
field of view with a live worm count.

## Start

Run from the repository root:

```powershell
python -m pip install -e software/c_elegans_counter

c-elegans-live-camera --host 127.0.0.1 --port 7860 --camera-index 0
```

Open:

```text
http://127.0.0.1:7860
```

## Project Presets

- `C. elegans - YOLO segmentation`: uses the locally trained YOLO segmentation
  model if available.
- `C. elegans - OpenCV baseline`: uses the lightweight OpenCV method.
- `Daphnia - camera preview`: reserved for future Daphnia model work.
- `Focus and illumination check`: camera preview for alignment and lighting.

## Current Default Model

The C. elegans YOLO preset points to:

```text
runs/segment/runs/wormswin/yolo_seg_md_to_csb1_gpu_5e_frac025/weights/best.pt
```

This model was trained from public WormSwin data and fine-tuned on a subset of
CSB-1. It is good enough for a first live prototype, but it still needs local
manual labels before it should be treated as a validated counting method.

## Practical Notes

- If the microscope camera does not appear as `Camera 0`, try another camera
  index in the interface.
- Use `Process N = 1` for maximum responsiveness on GPU.
- Increase confidence if debris is overcounted.
- Decrease confidence if clear worms are missed.
- Use preview mode first to focus and center the circular microscope field.

## Local Smoke Test

On 2026-06-02, the interface detected `Camera 0` at 640 x 480 and ran the
C. elegans YOLO preset at about 28 FPS with approximately 20 ms inference time
per processed frame on the local GPU.
