# Software

This folder contains the analysis software for the project.

## Initial Baseline

The first implementation should use OpenCV to create a simple baseline:

1. load image input;
2. preprocess and normalize background;
3. detect worm-like objects;
4. filter by size and shape;
5. count objects;
6. estimate density using calibration metadata;
7. export annotated image and CSV output.

## Future Extensions

- YOLO object detection
- instance segmentation
- egg detection
- developmental-stage classification
- video tracking
- behavior feature extraction

Keep code modular so that the *C. elegans* workflow can later inform the
*Daphnia* tracking workflow.
