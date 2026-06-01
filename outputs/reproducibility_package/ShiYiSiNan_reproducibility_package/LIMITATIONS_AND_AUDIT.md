# Limitations and Audit Notes

## Dataset scope

The primary analysis uses CGMacros-derived meal-level data.
The external validation uses OhioT1DM as an independent disease-specific CGM dataset.
These datasets differ in population, disease context, available covariates, nutrition annotation quality, and event structure.

## External validation

The OhioT1DM analysis is a lightweight framework validation.
It does not directly validate CGMacros-trained model weights.

## Counterfactual simulations

Counterfactual meal-substitution results are model-based simulations.
They should be interpreted as hypothesis-generating rather than causal intervention effects.

## Calibration

Calibration analysis indicates prediction-range compression.
Deployment should combine point prediction with calibration monitoring, uncertainty estimation, high-response risk detection, and subject-specific updating.

## Privacy and sharing

Public packages should not contain raw data, XML files, token files, or row-level records that could be restricted by source dataset terms.
