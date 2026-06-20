# 高水平期刊目标研究完成总报告

生成脚本：`scripts/build_high_impact_research_report.py`

## 完成摘要

本研究包已从公开糖尿病 RCT/干预研究数据出发，完成数据清洗、血糖动力学相图、相位-结局验证、多模型预测比较、异质性治疗响应和可解释个体化干预框架。当前结果已经形成一套可复现的投稿前分析基础。

## 五个目标对应产物

1. 构建血糖动力学相图：`data/processed/glycemic_phase_features.csv`，`figures/glycemic_phase_map.png`
2. 验证相位与临床结局关系：`results/phase_association_tests.csv`，`results/journal_adjusted_phase_outcome_models.csv`
3. 比较不同机器学习方法：`results/model_performance_cv.csv`，`results/model_performance_loso.csv`
4. 识别异质性治疗响应：`results/hte_by_phase.csv`，`results/journal_adjusted_hte_by_phase.csv`
5. 形成可解释个体化干预框架：`results/individualized_intervention_framework.csv`，`results/journal_permutation_importance.csv`

## 相位分布

| phase_label | n |
| --- | --- |
| 稳定达标相 | 234 |
| 高波动震荡相 | 182 |
| 高血糖持续相 | 178 |
| 昼夜节律紊乱相 | 97 |
| 低血糖易感相 | 57 |

## 内部交叉验证最佳模型

| target | feature_set | model | n | auroc | auprc | brier |
| --- | --- | --- | --- | --- | --- | --- |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | 1955 | 0.800 | 0.742 | 0.177 |
| y_hba1c_improved_ge_0_5 | C1_clinical | xgboost | 1955 | 0.800 | 0.741 | 0.167 |
| y_hba1c_improved_ge_0_5 | C1_clinical | logistic_ridge | 1955 | 0.799 | 0.738 | 0.179 |
| y_hba1c_improved_ge_0_5 | C4_phase_map | xgboost | 1955 | 0.799 | 0.740 | 0.168 |
| y_hba1c_improved_ge_0_5 | C1_clinical | catboost | 1955 | 0.798 | 0.742 | 0.168 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | 641 | 0.792 | 0.734 | 0.186 |
| y_tir_improved_ge_5pct | C4_phase_map | logistic_ridge | 641 | 0.787 | 0.734 | 0.188 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | xgboost | 641 | 0.770 | 0.701 | 0.191 |
| y_tir_improved_ge_5pct | C4_phase_map | xgboost | 641 | 0.766 | 0.708 | 0.192 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | lightgbm | 641 | 0.766 | 0.692 | 0.196 |

## Leave-One-Study-Out 外部泛化

| target | feature_set | model | heldout_study_count | auroc_mean | auroc_sd | auroc_min | auroc_max | brier_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| y_hba1c_improved_ge_0_5 | C1_clinical | logistic_ridge | 13 | 0.727 | 0.079 | 0.624 | 0.859 | 0.211 |
| y_hba1c_improved_ge_0_5 | C2_clinical_plus_cgm | logistic_ridge | 13 | 0.723 | 0.080 | 0.624 | 0.859 | 0.213 |
| y_hba1c_improved_ge_0_5 | C1_clinical | extra_trees | 13 | 0.721 | 0.083 | 0.627 | 0.901 | 0.210 |
| y_hba1c_improved_ge_0_5 | C1_clinical | catboost | 13 | 0.720 | 0.081 | 0.620 | 0.869 | 0.198 |
| y_hba1c_improved_ge_0_5 | C1_clinical | xgboost | 13 | 0.719 | 0.080 | 0.615 | 0.857 | 0.198 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | 4 | 0.754 | 0.033 | 0.718 | 0.792 | 0.234 |
| y_tir_improved_ge_5pct | C4_phase_map | logistic_ridge | 4 | 0.747 | 0.037 | 0.706 | 0.794 | 0.236 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | mlp | 4 | 0.723 | 0.041 | 0.677 | 0.765 | 0.253 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | extra_trees | 4 | 0.712 | 0.049 | 0.662 | 0.775 | 0.232 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | xgboost | 4 | 0.712 | 0.029 | 0.680 | 0.749 | 0.244 |

## 校准与临床效用

| target | feature_set | model | auroc | brier | calibration_intercept | calibration_slope | expected_calibration_error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | 0.800 | 0.177 | -0.500 | 1.040 | 0.090 |
| y_hba1c_improved_ge_0_5 | C1_clinical | xgboost | 0.800 | 0.167 | 0.009 | 1.001 | 0.023 |
| y_hba1c_improved_ge_0_5 | C1_clinical | logistic_ridge | 0.799 | 0.179 | -0.542 | 0.949 | 0.094 |
| y_hba1c_improved_ge_0_5 | C4_phase_map | xgboost | 0.799 | 0.168 | 0.002 | 1.000 | 0.028 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | 0.792 | 0.186 | -0.313 | 0.878 | 0.057 |
| y_tir_improved_ge_5pct | C4_phase_map | logistic_ridge | 0.787 | 0.188 | -0.316 | 0.844 | 0.057 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | xgboost | 0.770 | 0.191 | -0.035 | 0.882 | 0.053 |
| y_tir_improved_ge_5pct | C4_phase_map | xgboost | 0.766 | 0.192 | -0.026 | 0.883 | 0.065 |

校准图和决策曲线已输出到：

- `figures/journal_calibration_curves.png`
- `figures/journal_decision_curve.png`

## 相图稳健性

| n_bootstrap | ari_median | ari_q25 | ari_q75 | silhouette_median |
| --- | --- | --- | --- | --- |
| 150 | 0.826 | 0.755 | 0.890 | 0.268 |

## 异质性治疗响应

| phase_label | n | adjusted_risk_difference | bootstrap_ci_low | bootstrap_ci_high | crude_risk_difference |
| --- | --- | --- | --- | --- | --- |
| 低血糖易感相 | 54 | 0.281 | 0.105 | 0.408 | 0.274 |
| 稳定达标相 | 177 | 0.181 | 0.095 | 0.253 | 0.187 |
| 高血糖持续相 | 165 | 0.180 | 0.038 | 0.311 | 0.178 |
| 昼夜节律紊乱相 | 90 | 0.113 | -0.051 | 0.242 | 0.064 |
| 高波动震荡相 | 158 | 0.111 | -0.029 | 0.240 | 0.134 |

## 调整后的相位-结局关联

| target | target_label | outcome_type | n | reference_phase | test | statistic | df | p_value | covariates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| y_hba1c_improved_ge_0_5 | HbA1c improvement >=0.5% | binary | 719 | 稳定达标相 | robust_wald_phase_terms | 3.034 | 4 | 0.552 | baseline HbA1c, age, baseline TIR, study fixed effects, randomized arm fixed effects |
| y_tir_improved_ge_5pct | TIR improvement >=5 percentage points | binary | 641 | 稳定达标相 | robust_wald_phase_terms | 5.571 | 4 | 0.234 | baseline HbA1c, age, baseline TIR, study fixed effects, randomized arm fixed effects |
| y_hba1c_change_pct_points | HbA1c change, percentage points | continuous | 719 | 稳定达标相 | robust_wald_phase_terms | 3.083 | 4 | 0.544 | baseline HbA1c, age, baseline TIR, study fixed effects, randomized arm fixed effects |
| y_change_cgm_time_in_range_70_180_pct | TIR change, percentage points | continuous | 641 | 稳定达标相 | robust_wald_phase_terms | 9.155 | 4 | 0.057 | baseline HbA1c, age, baseline TIR, study fixed effects, randomized arm fixed effects |

## 模型差异检验

| target | comparison | left_feature_set | left_model | right_feature_set | right_model | n | delta_auroc_left_minus_right | bootstrap_ci_low | bootstrap_ci_high | bootstrap_p_value | bootstrap_successful_resamples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| y_hba1c_improved_ge_0_5 | best_vs_runner_up | C1_clinical | lightgbm | C1_clinical | xgboost | 1955 | 0.001 | -0.002 | 0.004 | 0.622 | 1000 |
| y_hba1c_improved_ge_0_5 | best_phase_map_vs_best_non_phase | C4_phase_map | xgboost | C1_clinical | lightgbm | 1955 | -0.002 | -0.008 | 0.005 | 0.652 | 1000 |
| y_tir_improved_ge_5pct | best_vs_runner_up | C2_clinical_plus_cgm | logistic_ridge | C4_phase_map | logistic_ridge | 641 | 0.005 | -0.001 | 0.011 | 0.118 | 1000 |
| y_tir_improved_ge_5pct | best_phase_map_vs_best_non_phase | C4_phase_map | logistic_ridge | C2_clinical_plus_cgm | logistic_ridge | 641 | -0.005 | -0.011 | 0.002 | 0.138 | 1000 |

## Nested CV 微调模型

| target | feature_set | model | outer_folds | total_test_n | auroc_mean | auroc_sd | auprc_mean | brier_mean | inner_auroc_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | 5 | 1955 | 0.802 | 0.038 | 0.745 | 0.180 | 0.796 |
| y_hba1c_improved_ge_0_5 | C1_clinical | xgboost | 5 | 1955 | 0.801 | 0.038 | 0.743 | 0.169 | 0.798 |
| y_hba1c_improved_ge_0_5 | C1_clinical | logistic_ridge | 5 | 1955 | 0.799 | 0.027 | 0.735 | 0.179 | 0.794 |
| y_hba1c_improved_ge_0_5 | C4_phase_map | xgboost | 5 | 1955 | 0.798 | 0.038 | 0.743 | 0.170 | 0.794 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | 5 | 641 | 0.795 | 0.053 | 0.744 | 0.185 | 0.781 |
| y_tir_improved_ge_5pct | C4_phase_map | logistic_ridge | 5 | 641 | 0.791 | 0.060 | 0.745 | 0.188 | 0.777 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | xgboost | 5 | 641 | 0.761 | 0.045 | 0.714 | 0.195 | 0.754 |

## 关键解释

- HbA1c 改善任务中，LightGBM、XGBoost、logistic ridge、CatBoost 的 AUROC 非常接近；paired bootstrap 显示名义最佳模型差异不稳定，论文应报告为“性能相近的一组模型”。
- TIR 改善任务中，临床+CGM 的 logistic ridge 仍最稳健，说明样本量较小时简单模型更容易泛化。
- 相图特征对 AUROC 的增量有限，但在可解释分层、治疗响应异质性和机制化可视化方面有明确价值。
- 调整后的相位-结局关联弱于未调整检验，提示相位捕获了部分基线风险结构；投稿叙事应克制，避免因果化。

## Artifact Manifest

完整 artifact 清单：`results/research_artifact_manifest.csv`

清单概览：

| path | kind | exists | rows | columns | description |
| --- | --- | --- | --- | --- | --- |
| data/processed/processed_ml_table.csv | processed_data | True | 2144.000 | 99.000 | participant-level baseline features and follow-up outcomes |
| data/processed/cgm_summary_long.csv | processed_data | True | 8638.000 | 21.000 | harmonized long-format CGM summaries |
| data/processed/glycemic_phase_features.csv | phase_data | True | 748.000 | 17.000 | phase-map order parameters and CGM state variables |
| data/processed/glycemic_phase_labels.csv | phase_data | True | 748.000 | 4.000 | participant phase labels |
| results/model_performance_cv.csv | model_results | True | 66.000 | 11.000 | 5-fold cross-validation benchmark |
| results/model_performance_loso.csv | model_results | True | 561.000 | 12.000 | leave-one-study-out external validation |
| results/journal_oof_predictions.csv | model_results | True | 10384.000 | 8.000 | out-of-fold predictions for selected models |
| results/journal_calibration_metrics.csv | model_results | True | 8.000 | 11.000 | calibration metrics from out-of-fold predictions |
| results/journal_decision_curve.csv | clinical_utility | True | 456.000 | 6.000 | decision curve analysis net-benefit estimates |
| results/journal_permutation_importance.csv | explainability | True | 25.000 | 6.000 | cross-validated permutation importance |
| results/phase_bootstrap_stability.csv | robustness | True | 150.000 | 3.000 | bootstrap phase-map stability |
| results/journal_adjusted_hte_by_phase.csv | hte | True | 5.000 | 9.000 | regularized adjusted treatment response by phase |
| results/journal_loso_summary.csv | robustness | True | 60.000 | 12.000 | aggregated LOSO model performance |
| results/journal_incremental_phase_value.csv | robustness | True | 80.000 | 9.000 | incremental AUROC of phase-map feature set |
| results/journal_model_pairwise_bootstrap.csv | model_results | True | 4.000 | 12.000 | paired bootstrap AUROC comparisons |
| results/journal_adjusted_phase_outcome_models.csv | association | True | 20.000 | 12.000 | adjusted phase-outcome effect estimates |
| results/journal_adjusted_phase_global_tests.csv | association | True | 4.000 | 10.000 | global robust Wald tests for phase terms |
| results/journal_nested_tuning_experiments.csv | model_results | True | 7.000 | 3.000 | candidate models selected for nested tuning |
| results/journal_nested_tuning_results.csv | model_results | True | 35.000 | 12.000 | outer-fold results from nested tuning |
| results/journal_nested_tuning_summary.csv | model_results | True | 7.000 | 10.000 | nested cross-validation summary for tuned models |
| results/table1_baseline_by_phase.csv | manuscript_table | True | 23.000 | 8.000 | baseline characteristics by glycemic phase |
| results/study_cohort_flow.csv | manuscript_table | True | 14.000 | 9.000 | study-level cohort and outcome availability |
| results/key_variable_missingness.csv | manuscript_table | True | 18.000 | 6.000 | missingness for key baseline and outcome variables |
| results/outcomes_by_phase_manuscript.csv | manuscript_table | True | 4.000 | 7.000 | clinical outcomes summarized by glycemic phase |
| figures/glycemic_phase_map.png | figure | True |  |  | glycemic phase map |
| figures/phase_tir_boxplot.png | figure | True |  |  | baseline TIR by phase |
| figures/model_benchmark_primary_auroc.png | figure | True |  |  | primary model benchmark |
| figures/journal_calibration_curves.png | figure | True |  |  | calibration curves |
| figures/journal_decision_curve.png | figure | True |  |  | decision curve analysis |
| figures/journal_permutation_importance.png | figure | True |  |  | permutation importance |
| figures/phase_bootstrap_stability.png | figure | True |  |  | phase bootstrap stability |
| figures/journal_adjusted_hte_by_phase.png | figure | True |  |  | adjusted HTE by phase |
| figures/journal_loso_heatmap.png | figure | True |  |  | LOSO AUROC heatmap |
| figures/journal_adjusted_phase_outcomes.png | figure | True |  |  | adjusted phase-outcome associations |
| figures/journal_nested_tuning_auroc.png | figure | True |  |  | nested CV tuned model AUROC |
| docs/cleaning_report.md | documentation | True |  |  | data cleaning report |
| docs/glycemic_phase_research_report_zh.md | documentation | True |  |  | primary phase-map research report |
| docs/journal_grade_experiment_report_zh.md | documentation | True |  |  | secondary journal-grade diagnostics report |
| docs/adjusted_phase_outcome_models_zh.md | documentation | True |  |  | adjusted association model report |
| docs/manuscript_tables_figures_index_zh.md | documentation | True |  |  | manuscript table and figure index |
