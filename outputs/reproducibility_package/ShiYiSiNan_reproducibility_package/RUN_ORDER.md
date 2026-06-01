# Run Order

Run scripts from the project root in numeric order.

| Order | Script | Purpose |
|---:|---|---|
| 1 | `1_inspect_dataset.py` | Initial data inspection or setup, if present |
| 2 | `02_build_meal_level_dataset.py` | Build meal-level CGMacros dataset |
| 3 | `03_train_baseline_models.py` | Baseline model training and evaluation, if present |
| 3 | `03_train_clean_models.py` | Baseline model training and evaluation, if present |
| 4 | `04_make_figures.py` | Feature-set ablation or core model evaluation, if present |
| 5 | `05_ablation_study.py` | Cleaned-feature analysis or model comparison, if present |
| 6 | `06_bootstrap_ci.py` | Subject-level bootstrap confidence intervals |
| 7 | `07_make_paper_tables_figures.py` | Clean paper tables and main figures, if present |
| 8 | `08_paired_delta_bootstrap.py` | Paired subject-level delta bootstrap |
| 9 | `09_subgroup_analysis.py` | Exploratory subgroup analysis |
| 10 | `10_error_analysis.py` | Error analysis |
| 11 | `11_calibration_analysis.py` | Calibration analysis |
| 12 | `12_counterfactual_meal_substitution.py` | Model-based counterfactual meal-substitution simulation |
| 13 | `13_lightweight_external_validation_ohio.py` | Lightweight external framework validation using OhioT1DM |
