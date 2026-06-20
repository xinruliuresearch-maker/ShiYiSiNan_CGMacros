# Nature Food Aim 1 NHANES Python Audit Report

R/Rscript was not available on this machine, so this report uses weighted least squares with cluster-robust standard errors by NHANES stratum-PSU pairs.
It is an audit output, not the final R `survey` result.

Input rows: 5267

Fixed covariates: age, sex, race/ethnicity, education, PIR, energy intake, smoking, alcohol, physical activity, urinary creatinine, cycle.

## Key Main-Model Rows

| outcome          | exposure             | n    | effect | effect_low | effect_high | p_value   | q_value   | status                |
| ---------------- | -------------------- | ---- | ------ | ---------- | ----------- | --------- | --------- | --------------------- |
| msi_core_partial | pct_oxidative_10     | 1313 | 0.1684 | 0.06445    | 0.2724      | 0.001497  | 0.001997  | ok_python_cluster_wls |
| msi_core_partial | ln_oxidative_to_MEHP | 1313 | 0.1828 | 0.1061     | 0.2594      | 2.951e-06 | 1.181e-05 | ok_python_cluster_wls |
| ln_HOMA_IR       | pct_oxidative_10     | 1292 | 19.96  | 6.881      | 34.64       | 0.002002  | 0.002669  | ok_python_cluster_wls |
| ln_HOMA_IR       | ln_oxidative_to_MEHP | 1292 | 24.41  | 13.64      | 36.2        | 2.25e-06  | 9e-06     | ok_python_cluster_wls |
| HbA1c            | pct_oxidative_10     | 2671 | 0.1096 | 0.03107    | 0.1882      | 0.006237  | 0.006237  | ok_python_cluster_wls |
| HbA1c            | ln_oxidative_to_MEHP | 2671 | 0.1346 | 0.07649    | 0.1927      | 5.6e-06   | 1.12e-05  | ok_python_cluster_wls |

## Output Files

- `aim1_main_python_cluster_wls_results.csv`
- `aim1_lod_creatinine_sensitivity_python_cluster_wls_results.csv`
- `aim1_diabetes_medication_exclusion_python_cluster_wls_results.csv`
- `aim1_cycle_replication_python_cluster_wls_results.csv`
- `aim1_composition_total_adjusted_python_cluster_wls_results.csv`
- `run_nature_food_aim1_nhanes_survey.R` is the final intended R survey script.