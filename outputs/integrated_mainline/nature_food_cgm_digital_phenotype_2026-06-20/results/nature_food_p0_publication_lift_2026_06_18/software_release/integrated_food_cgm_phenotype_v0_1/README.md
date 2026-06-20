# Integrated Food-CGM Phenotype v0.1

Research prototype for producing an integrated participant-level phenotype report:

- MSI/meal matrix inputs
- meal high-iAUC ranking score
- locked JAEB-derived CGM phase-map assignment
- risk-language guardrail

This is not a clinical decision system. The meal-risk output is a ranking score derived from locked study coefficients and should not be interpreted as calibrated absolute risk.

## Test

```bash
python -m unittest discover -s tests
```
