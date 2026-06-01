$ErrorActionPreference = 'Stop'
Write-Host 'Starting ShiYiSiNan reproducibility workflow...'

Write-Host 'Running 1_inspect_dataset.py'
python scripts\1_inspect_dataset.py

Write-Host 'Running 02_build_meal_level_dataset.py'
python scripts\02_build_meal_level_dataset.py

Write-Host 'Running 03_train_baseline_models.py'
python scripts\03_train_baseline_models.py

Write-Host 'Running 03_train_clean_models.py'
python scripts\03_train_clean_models.py

Write-Host 'Running 04_make_figures.py'
python scripts\04_make_figures.py

Write-Host 'Running 05_ablation_study.py'
python scripts\05_ablation_study.py

Write-Host 'Running 06_bootstrap_ci.py'
python scripts\06_bootstrap_ci.py

Write-Host 'Running 07_make_paper_tables_figures.py'
python scripts\07_make_paper_tables_figures.py

Write-Host 'Running 08_paired_delta_bootstrap.py'
python scripts\08_paired_delta_bootstrap.py

Write-Host 'Running 09_subgroup_analysis.py'
python scripts\09_subgroup_analysis.py

Write-Host 'Running 10_error_analysis.py'
python scripts\10_error_analysis.py

Write-Host 'Running 11_calibration_analysis.py'
python scripts\11_calibration_analysis.py

Write-Host 'Running 12_counterfactual_meal_substitution.py'
python scripts\12_counterfactual_meal_substitution.py

Write-Host 'Running 13_lightweight_external_validation_ohio.py'
python scripts\13_lightweight_external_validation_ohio.py

Write-Host 'Reproducibility workflow complete.'
