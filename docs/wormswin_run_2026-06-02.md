# WormSwin Training Run - 2026-06-02

This run uses public WormSwin data for training and the local pilot videos as
external validation frames.

## Public Training Data

Downloaded locally, not committed:

- `data/raw/wormswin/md_dataset.zip`
- `data/raw/wormswin/csb-1_dataset.zip`

Converted locally, not committed:

- `data/wormswin_yolo/md`
- `data/wormswin_yolo/csb1`

Converted YOLO segmentation data:

| Dataset | Train Images | Train Masks | Validation Images | Validation Masks |
| --- | ---: | ---: | ---: | ---: |
| MD | 214 | 2,205 | 215 | 1,736 |
| CSB-1 | 4,165 | 51,220 | 465 | 9,351 |

## External Validation Frames

Local validation frames were extracted from:

`C:\Users\shife\OneDrive\Desktop\example C elegans`

Extraction settings:

- 19 videos
- 10 frames per video
- 190 validation frames total
- frame step: 30
- preprocessing: CLAHE balanced grayscale

The extracted frames are local-only under
`data/validation_frames/user_videos`.

## Models Trained

### MD 20 Epochs

Command:

```powershell
python scripts/train_yolo_segmentation.py `
  --data data/wormswin_yolo/md/wormswin_md.yaml `
  --model yolov8n-seg.pt `
  --epochs 20 `
  --imgsz 640 `
  --batch 4 `
  --device 0 `
  --workers 0 `
  --project runs/wormswin `
  --name yolo_seg_md_gpu_20e `
  --predict-source data/validation_frames/user_videos/images
```

Internal WormSwin MD validation:

- box precision: 0.9302
- box recall: 0.9303
- box mAP50: 0.9733
- mask precision: 0.9170
- mask recall: 0.8976
- mask mAP50: 0.9467

External local-video result summary:

`results/csv/yolo_gpu20_user_validation_summary.csv`

### MD then CSB-1 Fine-Tune

Command:

```powershell
python scripts/train_yolo_segmentation.py `
  --data data/wormswin_yolo/csb1/wormswin_csb1.yaml `
  --model runs/segment/runs/wormswin/yolo_seg_md_gpu_20e/weights/best.pt `
  --epochs 5 `
  --fraction 0.25 `
  --imgsz 640 `
  --batch 4 `
  --device 0 `
  --workers 0 `
  --project runs/wormswin `
  --name yolo_seg_md_to_csb1_gpu_5e_frac025 `
  --predict-source data/validation_frames/user_videos/images
```

Internal CSB-1 validation:

- box precision: 0.9465
- box recall: 0.9581
- box mAP50: 0.9794
- mask precision: 0.9293
- mask recall: 0.9404
- mask mAP50: 0.9626

External local-video result summary:

`results/csv/yolo_csb1_finetune_user_validation_summary.csv`

## External Validation Counts

Mean predicted count across 10 sampled frames per video:

| Video | MD 20e | MD to CSB-1 Fine-Tune |
| --- | ---: | ---: |
| AH5615_T1 | 1.0 | 0.0 |
| AH5615_T2 | 0.0 | 0.0 |
| AH5615_T3 | 0.0 | 0.0 |
| JRG02_T1 | 0.0 | 0.0 |
| JRG02_T2 | 0.9 | 0.0 |
| JRG03_T3 | 1.0 | 0.7 |
| MIX_T1 | 4.6 | 0.0 |
| MIX_T2 | 7.7 | 2.3 |
| MIX_T3 | 7.9 | 3.8 |
| One_weak_ago_T1 | 2.0 | 0.9 |
| One_weak_ago_T2 | 0.1 | 0.0 |
| One_weak_ago_T3 | 0.0 | 0.0 |
| Pass_LT_T1 | 8.5 | 5.1 |
| Pass_LT_T2 | 0.0 | 0.0 |
| Pass_Less_T1 | 0.0 | 31.2 |
| Pass_Less_T2 | 2.0 | 8.2 |
| Pass_T1 | 58.9 | 72.6 |
| Pass_T2 | 16.9 | 195.2 |
| Pass_T3 | 32.9 | 144.2 |

## Interpretation

The CSB-1 fine-tune substantially improved some dense local videos, especially
`Pass_T2` and `Pass_T3`. However, it still fails on several low-contrast or
very dense frames, including `Pass_LT_T2`.

The local videos should therefore remain an external validation set. The next
scientifically useful step is to manually label a small local subset and
fine-tune against that labelled local domain.

Recommended first local-label set:

- 3 low-density frames;
- 3 medium-density frames;
- 3 dense frames;
- 3 failure-case frames with bubbles, debris, or extreme overlap.
