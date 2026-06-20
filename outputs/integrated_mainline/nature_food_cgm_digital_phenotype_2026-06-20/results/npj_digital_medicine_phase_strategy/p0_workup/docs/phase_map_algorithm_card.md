# Phase-Map Algorithm Card

## Intended Use

The glycaemic phase-map algorithm is a research-grade CGM digital phenotype. It summarizes a baseline CGM window into interpretable glycaemic phases for retrospective risk organization, model validation, and treatment-response hypothesis generation.

It is not a standalone clinical decision system and must not autonomously change therapy.

## Inputs

Required baseline CGM summary fields:

- mean glucose, mg/dL
- time in range 70-180%, time below 70%, time below 54%
- time above 180%, time above 250%
- glucose coefficient of variation
- CGM wear hours

Optional clinical fields used in prediction models:

- age, baseline HbA1c, BMI, diabetes duration
- sex, race, ethnicity, study/context, randomized arm or care mode

## Feature Construction

The algorithm computes five order parameters:

1. Glycaemic burden.
2. Hypoglycaemic susceptibility.
3. Dynamic instability.
4. Circadian disruption, when day/night summaries are available.
5. Resilience proxy.

For frozen validation, order parameters are scaled using training-set reference means and standard deviations. New participants are assigned to the nearest locked phase centroid in order-parameter space.

## Output

- phase_label and phase_id
- phase assignment distance
- order parameter values
- optional outcome risk estimates from locked prediction models

## Validation Status

Current evidence is retrospective. Internal and leave-one-study-out validation are available. Loop study is used as a frozen external validation in the P0 workup. Prospective silent-mode validation remains required before clinical deployment.

## Limitations

- Summary-CGM based; raw time-series transitions are not yet incorporated.
- Phase labels are digital phenotypes, not confirmed biological subtypes.
- Prediction gain from phase features is modest; interpretability and workflow support are the primary rationale.
- Subgroup performance and calibration must be audited before deployment.
