# WormSwin Training Workflow

This workflow uses the public WormSwin dataset for model training and the local
pilot videos as an external validation set.

## Rationale

The first OpenCV baseline is useful for understanding illumination, ROI edges,
debris, and motion, but it is not accurate enough for dense or overlapping
worms. The next step is supervised segmentation:

1. train on public WormSwin instance masks;
2. extract frames from the local microscope videos;
3. run the trained model on the local frames;
4. manually label a small subset of local frames for external validation.

## Dataset

The WormSwin Zenodo record contains three archives:

- `md_dataset.zip`: 197 MB, 450 high-overlap grayscale patches with COCO masks;
- `csb-1_dataset.zip`: 2.9 GB, frames from C. elegans videos with instance masks;
- `synthetic_images_dataset.zip`: 7.5 GB, synthetic training images generated
  from CSB-1 foreground worms and background patches.

Start with `md_dataset.zip` because it is small and stresses overlapping worms.
Use CSB-1 and synthetic data later if the first model underfits or fails to
generalize.

## Commands

Download the MD archive:

```powershell
python scripts/download_wormswin_dataset.py --dataset md
```

Convert COCO polygon masks to YOLO segmentation format:

```powershell
python scripts/prepare_wormswin_yolo.py `
  --zip data/raw/wormswin/md_dataset.zip `
  --output-dir data/wormswin_yolo/md `
  --yaml-name wormswin_md.yaml
```

Optionally prepare the larger CSB-1 video-derived split:

```powershell
python scripts/download_wormswin_dataset.py --dataset csb1

python scripts/prepare_wormswin_yolo.py `
  --zip data/raw/wormswin/csb-1_dataset.zip `
  --dataset-root csb-1_dataset `
  --annotations-dir coco_annotations `
  --output-dir data/wormswin_yolo/csb1 `
  --yaml-name wormswin_csb1.yaml
```

Extract local validation frames:

```powershell
python scripts/extract_user_video_frames.py `
  --input "C:\Users\shife\OneDrive\Desktop\example C elegans" `
  --output-dir data/validation_frames/user_videos `
  --frame-step 30 `
  --max-frames-per-video 10 `
  --preprocess balanced-gray
```

Train and then predict on the local validation frames:

```powershell
python scripts/train_yolo_segmentation.py `
  --data data/wormswin_yolo/md/wormswin_md.yaml `
  --model yolov8n-seg.pt `
  --epochs 50 `
  --imgsz 640 `
  --batch 4 `
  --device 0 `
  --predict-source data/validation_frames/user_videos/images
```

Fine-tune the MD model on a fraction of CSB-1:

```powershell
python scripts/train_yolo_segmentation.py `
  --data data/wormswin_yolo/csb1/wormswin_csb1.yaml `
  --model runs/segment/runs/wormswin/yolo_seg_md_gpu_20e/weights/best.pt `
  --epochs 5 `
  --fraction 0.25 `
  --imgsz 640 `
  --batch 4 `
  --device 0 `
  --predict-source data/validation_frames/user_videos/images
```

For CPU-only smoke testing, reduce the workload:

```powershell
python scripts/train_yolo_segmentation.py `
  --data data/wormswin_yolo/md/wormswin_md.yaml `
  --model yolov8n-seg.pt `
  --epochs 1 `
  --imgsz 320 `
  --batch 1 `
  --device cpu `
  --workers 0
```

## Current Environment Note

This Windows machine has an NVIDIA GPU. For efficient training, the Python
environment needs CUDA-enabled PyTorch. The successful local run used
`torch==2.10.0+cu128` and `torchvision==0.25.0+cu128`.

## External Validation

The local videos should be used as external validation, not as training data at
first. The immediate validation set can be:

- 10 balanced-gray frames per local video for qualitative prediction review;
- 20-50 manually labelled frames for quantitative validation;
- separate notes for bubbles, debris, edge artifacts, and overlapping worms.

The key metrics should be instance count error, precision, recall, mask quality,
and failure cases by density level.
