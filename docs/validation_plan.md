# Validation Plan

Automated results must be compared against manual analysis before the workflow
can be considered scientifically useful.

## Core Comparisons

- Manual count vs automated count
- Low, medium, and high density samples
- Different imaging dates
- Different operators
- Different sample backgrounds
- Time required for manual and automated analysis

## Metrics

| Metric | Purpose |
| --- | --- |
| Mean absolute error | Count error magnitude |
| Percentage error | Relative count error |
| Precision | False positive control |
| Recall | Missed worm control |
| Correlation | Agreement with manual counts |
| Processing time | Practical lab usability |

## Error Categories

Track common failure cases:

- overlapping worms
- eggs mistaken for worms
- debris mistaken for worms
- bubbles or plate edges
- out-of-focus images
- uneven illumination
- very dense samples

## Minimum Pilot Dataset

Recommended first validation set:

- 10 low-density images
- 10 medium-density images
- 10 high-density images
- manual counts from at least one trained user
- calibration image for the same setup

If possible, add a second annotator for inter-user comparison.
