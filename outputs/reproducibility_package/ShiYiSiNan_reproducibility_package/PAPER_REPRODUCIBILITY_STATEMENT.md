# Paper Reproducibility Statement

All analyses were implemented in Python and organized as a script-based workflow.
The workflow includes meal-level phenotype construction, leakage-aware feature-set evaluation, subject-level bootstrap confidence intervals, paired subject-level delta bootstrap, exploratory subgroup analysis, error analysis, calibration diagnostics, model-based counterfactual meal-substitution simulation, and lightweight external framework validation.

Leave-subject-out validation was used to assess new-user generalization.
Within-subject temporal splitting was used to assess future-meal prediction for previously observed individuals.
Few-shot personalization experiments used early subject-specific meals for adaptation and evaluated subsequent meals only.
Confidence intervals were estimated using participant-level resampling to account for repeated meals within individuals.

The reproducibility package includes analysis scripts, software environment files, aggregate output tables, figures, run-order documentation, and checksums.
Raw datasets are not redistributed and should be obtained from their original sources according to their data-use terms.
