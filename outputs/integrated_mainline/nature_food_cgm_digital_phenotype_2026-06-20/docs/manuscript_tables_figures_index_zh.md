# 论文图表与补充材料索引

生成脚本：`scripts/build_manuscript_tables.py`

## 主文建议图表

Table 1. Baseline characteristics by glycemic phase  
文件：`results/table1_baseline_by_phase.csv`

Table 2. Internal and external predictive model performance  
文件：`results/model_performance_cv.csv`，`results/journal_loso_summary.csv`

Table 3. Adjusted heterogeneous treatment response by phase  
文件：`results/journal_adjusted_hte_by_phase.csv`

Figure 1. Study workflow and phase-map construction  
建议用 `results/study_cohort_flow.csv` 和 `figures/glycemic_phase_map.png` 绘制组合图。

Figure 2. Glycemic phase map and baseline TIR distribution  
文件：`figures/glycemic_phase_map.png`，`figures/phase_tir_boxplot.png`

Figure 3. Model discrimination, calibration, and decision curves  
文件：`figures/model_benchmark_primary_auroc.png`，`figures/journal_calibration_curves.png`，`figures/journal_decision_curve.png`

Figure 4. Phase-stratified treatment response and individualized intervention framework  
文件：`figures/journal_adjusted_hte_by_phase.png`，`results/individualized_intervention_framework.csv`

## 补充材料建议

Supplementary Table 1. Dataset inventory and availability  
文件：`data/processed/dataset_inventory.csv`

Supplementary Table 2. Missingness by variable  
文件：`results/key_variable_missingness.csv`

Supplementary Table 3. Outcomes by phase  
文件：`results/outcomes_by_phase_manuscript.csv`

Supplementary Table 4. Paired bootstrap model comparisons  
文件：`results/journal_model_pairwise_bootstrap.csv`

Supplementary Figure 1. Leave-one-study-out AUROC heatmap  
文件：`figures/journal_loso_heatmap.png`

Supplementary Figure 2. Phase bootstrap stability  
文件：`figures/phase_bootstrap_stability.png`

Supplementary Figure 3. Permutation importance  
文件：`figures/journal_permutation_importance.png`

## Table 1 预览

| section | variable | level | 稳定达标相 | 高波动震荡相 | 高血糖持续相 | 昼夜节律紊乱相 | 低血糖易感相 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cohort | N |  | 234 | 182 | 178 | 97 | 57 |
| Baseline numeric | Age, years | mean (SD) | 55.56 (20.91) | 34.79 (25.38) | 21.91 (22.05) | 31.87 (27.35) | 37.98 (28.13) |
| Baseline numeric | Diabetes duration, years | mean (SD) | 31.47 (18.72) | 20.09 (18.33) | 9.98 (12.30) | 15.80 (15.61) | 20.40 (17.84) |
| Baseline numeric | Baseline HbA1c, % | mean (SD) | 7.06 (0.70) | 7.74 (0.73) | 8.86 (0.86) | 8.48 (0.89) | 7.46 (1.02) |
| Baseline numeric | Baseline BMI, kg/m2 | mean (SD) | 26.89 (5.38) | 25.08 (5.82) | 24.07 (6.29) | 23.72 (6.08) | 23.79 (4.90) |
| Baseline numeric | Baseline CGM mean glucose, mg/dL | mean (SD) | 153.06 (18.31) | 174.04 (18.52) | 228.12 (26.54) | 199.91 (24.49) | 151.62 (24.30) |
| Baseline numeric | Baseline TIR 70-180 mg/dL, % | mean (SD) | 68.29 (11.31) | 53.15 (9.20) | 31.00 (9.38) | 41.21 (9.46) | 53.15 (11.61) |
| Baseline numeric | Baseline TBR <70 mg/dL, % | mean (SD) | 3.50 (3.11) | 5.46 (3.16) | 2.18 (1.72) | 5.57 (3.17) | 16.25 (3.97) |
| Baseline numeric | Baseline TAR >180 mg/dL, % | mean (SD) | 28.22 (12.32) | 41.37 (9.96) | 66.84 (10.02) | 53.25 (10.54) | 30.61 (11.98) |
| Baseline numeric | Baseline CGM coefficient of variation, % | mean (SD) | 34.63 (4.76) | 43.49 (4.89) | 37.82 (5.28) | 44.98 (4.82) | 52.31 (6.03) |
| Baseline categorical | Sex | female | 115 (49.1%) | 86 (47.3%) | 90 (50.6%) | 58 (59.8%) | 25 (43.9%) |
| Baseline categorical | Sex | male | 119 (50.9%) | 96 (52.7%) | 88 (49.4%) | 39 (40.2%) | 32 (56.1%) |
| Baseline categorical | Race | white | 216 (92.3%) | 150 (82.4%) | 147 (82.6%) | 76 (78.4%) | 44 (77.2%) |
| Baseline categorical | Race | black_african_american | 9 (3.8%) | 13 (7.1%) | 12 (6.7%) | 6 (6.2%) | 7 (12.3%) |
| Baseline categorical | Race | more_than_one_race | 6 (2.6%) | 11 (6.0%) | 7 (3.9%) | 7 (7.2%) | 3 (5.3%) |
| Baseline categorical | Race | missing_or_unknown | 2 (0.9%) | 3 (1.6%) | 6 (3.4%) | 5 (5.2%) | 2 (3.5%) |
| Baseline categorical | Race | asian | 0 (0.0%) | 4 (2.2%) | 5 (2.8%) | 3 (3.1%) | 1 (1.8%) |
| Baseline categorical | Race | american_indian_alaskan_native | 1 (0.4%) | 0 (0.0%) | 1 (0.6%) | 0 (0.0%) | 0 (0.0%) |

## Cohort Flow 预览

| study_id | participants | has_baseline_hba1c | has_followup_hba1c | has_hba1c_improvement_target | has_baseline_cgm_summary | has_phase_label | has_tir_improvement_target | randomized_arm_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AIDE_T1D | 82 | 82 | 75 | 75 | 82 | 82 | 0 | 6 |
| CITY | 153 | 153 | 142 | 142 | 152 | 152 | 139 | 2 |
| CLVER | 113 | 111 | 107 | 106 | 0 | 0 | 0 | 4 |
| DCLP3 | 168 | 168 | 168 | 168 | 168 | 168 | 168 | 2 |
| DCLP5 | 101 | 101 | 101 | 101 | 0 | 0 | 0 | 2 |
| FLAIR | 113 | 113 | 110 | 110 | 0 | 0 | 0 | 2 |
| HYCLO | 161 | 152 | 44 | 43 | 0 | 0 | 0 | 1 |
| IOBP2 | 440 | 440 | 427 | 427 | 0 | 0 | 0 | 3 |
| METFORMIN_T1D | 139 | 139 | 137 | 137 | 0 | 0 | 0 | 2 |
| PEDAP | 102 | 98 | 98 | 95 | 0 | 0 | 0 | 2 |
| REPLACE_BG | 226 | 226 | 216 | 216 | 0 | 0 | 0 | 2 |
| SENCE | 143 | 143 | 137 | 137 | 143 | 143 | 138 | 3 |
| WISDM | 203 | 203 | 198 | 198 | 203 | 203 | 196 | 2 |
| TOTAL | 2144 | 2129 | 1960 | 1955 | 748 | 748 | 641 | 27 |

## Missingness 预览

| variable | role | n | missing_n | missing_pct | available_n |
| --- | --- | --- | --- | --- | --- |
| x_baseline_cgm_mean_glucose_mg_dl | baseline_feature | 2144 | 1396 | 65.112 | 748 |
| x_baseline_cgm_time_in_range_70_180_pct | baseline_feature | 2144 | 1396 | 65.112 | 748 |
| x_baseline_cgm_time_below_70_pct | baseline_feature | 2144 | 1396 | 65.112 | 748 |
| x_baseline_cgm_time_above_180_pct | baseline_feature | 2144 | 1396 | 65.112 | 748 |
| x_baseline_cgm_cv_pct | baseline_feature | 2144 | 1396 | 65.112 | 748 |
| x_diabetes_duration_years | baseline_feature | 2144 | 119 | 5.550 | 2025 |
| x_baseline_bmi | baseline_feature | 2144 | 63 | 2.938 | 2081 |
| x_baseline_hba1c_pct | baseline_feature | 2144 | 15 | 0.700 | 2129 |
| x_age_years | baseline_feature | 2144 | 0 | 0.000 | 2144 |
| x_sex | baseline_feature | 2144 | 0 | 0.000 | 2144 |
| x_race | baseline_feature | 2144 | 0 | 0.000 | 2144 |
| x_ethnicity | baseline_feature | 2144 | 0 | 0.000 | 2144 |
| x_insulin_delivery_method | baseline_feature | 2144 | 0 | 0.000 | 2144 |
| x_current_cgm_use | baseline_feature | 2144 | 0 | 0.000 | 2144 |
| y_tir_improved_ge_5pct | outcome | 2144 | 1503 | 70.103 | 641 |
| y_change_cgm_time_in_range_70_180_pct | outcome | 2144 | 1503 | 70.103 | 641 |
| y_hba1c_improved_ge_0_5 | outcome | 2144 | 189 | 8.815 | 1955 |
| y_hba1c_change_pct_points | outcome | 2144 | 189 | 8.815 | 1955 |

## Outcomes by Phase 预览

| outcome | summary | 稳定达标相 | 高波动震荡相 | 高血糖持续相 | 昼夜节律紊乱相 | 低血糖易感相 |
| --- | --- | --- | --- | --- | --- | --- |
| HbA1c improvement >=0.5% | mean (SD) or event rate | 48/229 (21.0%) | 48/177 (27.1%) | 69/167 (41.3%) | 32/91 (35.2%) | 14/55 (25.5%) |
| HbA1c change, percentage points | mean (SD) or event rate | -0.11 (0.46) | -0.14 (0.59) | -0.31 (0.86) | -0.19 (0.86) | -0.09 (0.76) |
| TIR improvement >=5 percentage points | mean (SD) or event rate | 63/175 (36.0%) | 63/158 (39.9%) | 83/164 (50.6%) | 39/89 (43.8%) | 23/55 (41.8%) |
| TIR change, percentage points | mean (SD) or event rate | 1.32 (10.59) | 2.22 (11.25) | 6.94 (12.78) | 2.94 (10.62) | 2.15 (12.03) |
