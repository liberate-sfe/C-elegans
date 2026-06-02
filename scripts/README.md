# Scripts

This folder is for helper scripts that are useful but not part of the main
analysis package.

Possible scripts:

- convert annotation formats
- summarize manual count CSV files
- split data into train and validation sets
- generate validation plots
- package example data

## WormSwin Training Workflow

Download the smallest WormSwin archive first:

```powershell
python scripts/download_wormswin_dataset.py --dataset md
```

Convert the WormSwin COCO polygon masks into YOLO segmentation labels:

```powershell
python scripts/prepare_wormswin_yolo.py `
  --zip data/raw/wormswin/md_dataset.zip `
  --output-dir data/wormswin_yolo/md `
  --yaml-name wormswin_md.yaml
```

Optionally add the larger CSB-1 video-derived dataset:

```powershell
python scripts/download_wormswin_dataset.py --dataset csb1

python scripts/prepare_wormswin_yolo.py `
  --zip data/raw/wormswin/csb-1_dataset.zip `
  --dataset-root csb-1_dataset `
  --annotations-dir coco_annotations `
  --output-dir data/wormswin_yolo/csb1 `
  --yaml-name wormswin_csb1.yaml
```

Extract local validation frames from the user videos:

```powershell
python scripts/extract_user_video_frames.py `
  --input "C:\Users\shife\OneDrive\Desktop\example C elegans" `
  --output-dir data/validation_frames/user_videos `
  --frame-step 30 `
  --max-frames-per-video 10 `
  --preprocess balanced-gray
```

Train a lightweight segmentation model:

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

Fine-tune the MD model on a subset of CSB-1:

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

Large datasets, extracted validation frames, model weights, and YOLO runs are
ignored by git.
