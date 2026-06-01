# ShiYiSiNan CGMacros Analysis

Reproducible analysis project for CGMacros meal-level glycemic response modeling, personalization, calibration, error analysis, counterfactual meal substitution, lightweight external validation, and reproducibility packaging.

## Project Structure

- `scripts/`: executable analysis scripts in numbered run order.
- `data/`: local raw, processed, and external validation data.
- `outputs/`: generated tables, figures, paper-ready artifacts, external validation results, and reproducibility package.

## Main Workflow

Run scripts in numeric order:

```powershell
python scripts/02_build_meal_level_dataset.py
python scripts/03_train_baseline_models.py
python scripts/03_train_clean_models.py
python scripts/04_make_figures.py
python scripts/05_ablation_study.py
python scripts/06_bootstrap_ci.py
python scripts/07_make_paper_tables_figures.py
python scripts/08_paired_delta_bootstrap.py
python scripts/09_subgroup_analysis.py
python scripts/10_error_analysis.py
python scripts/11_calibration_analysis.py
python scripts/12_counterfactual_meal_substitution.py
python scripts/13_lightweight_external_validation_ohio.py
python scripts/14_build_reproducibility_package.py
```

## Reproducibility Package

The packaged reproducibility bundle is under:

```text
outputs/reproducibility_package/
```

Large data, images, zip archives, and generated artifacts are tracked with Git LFS.

