# Annotation Guide

This guide defines annotation classes for training and validating detection
models.

## Stage 1 Labels

| Label | Meaning | Notes |
| --- | --- | --- |
| `worm` | Visible C. elegans body | Use for basic counting and density estimation |

## Stage 2 Labels

| Label | Meaning | Notes |
| --- | --- | --- |
| `worm` | Visible C. elegans body | Includes larva and adult if not separated |
| `egg` | Egg | Use only when egg boundaries are visually clear |

## Stage 3 Labels

| Label | Meaning | Notes |
| --- | --- | --- |
| `egg` | Egg | Small oval structure |
| `larva` | Juvenile worm | Smaller worm, classify only when reliable |
| `adult` | Adult worm | Larger worm, classify only when reliable |

## Annotation Rules

1. Annotate only visible organisms or eggs.
2. Do not label ambiguous debris as biological objects.
3. Mark heavily overlapping worms only if individual bodies can be separated.
4. Keep a separate note for difficult frames instead of forcing labels.
5. Track annotation tool version and annotator ID.

## Recommended Formats

Useful formats include:

- YOLO bounding boxes
- COCO JSON
- CSV for manual count metadata

For the first version, manual count CSV can be enough before training a detector.

## Manual Count CSV Fields

```text
image_id,manual_worm_count,manual_egg_count,annotator,date,notes
```
