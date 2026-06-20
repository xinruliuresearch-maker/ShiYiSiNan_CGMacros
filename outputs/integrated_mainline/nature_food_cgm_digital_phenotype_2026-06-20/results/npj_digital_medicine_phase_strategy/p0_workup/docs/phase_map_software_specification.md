# Phase-Map Software Specification

## Version

`phase-map-jaeb-summary-v0.1`

## Pipeline

1. Validate input schema.
2. Convert percent strings to numeric percentages.
3. Derive or validate CGM summary metrics.
4. Compute order parameters using locked training reference statistics.
5. Assign phase by nearest locked centroid.
6. Run optional prediction model if required clinical covariates are present.
7. Emit warnings for missing circadian features, short CGM wear, missing HbA1c, or out-of-distribution assignment distance.

## Input Schema

See `phase_map_input_schema.csv`.

## Output Schema

See `phase_map_output_schema.csv`.

## Missingness Rules

- Numeric predictors are median-imputed inside locked model pipelines.
- Categorical predictors use an explicit `missing` category.
- If day/night CGM is unavailable, circadian disruption is set to the training-set average for phase assignment and flagged.

## Reproducibility

All phase centroids, feature definitions, model parameters, and figure source data are versioned in the project output directory. Frozen validation datasets are not used for model tuning.
