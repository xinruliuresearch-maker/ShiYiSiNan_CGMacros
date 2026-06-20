# 高水平期刊导向二级实验报告

生成脚本：`scripts/run_journal_grade_experiments.py`  
主实验脚本：`scripts/run_glycemic_phase_research.py`

## 本轮新增证据

本轮在原有相图、模型比较、异质性治疗响应和个体化框架基础上，补充了六类更接近高水平医学与机器学习期刊审稿标准的分析：

1. 将 XGBoost、LightGBM、CatBoost 纳入主模型比较。
2. 对表现靠前的候选模型输出 5 折 out-of-fold 预测，避免用训练集预测评价模型。
3. 计算校准截距、校准斜率、Brier score 与 expected calibration error。
4. 进行 decision curve analysis，评估不同决策阈值下的净获益。
5. 用交叉验证内置的 permutation importance 识别可解释预测因子。
6. 用 bootstrap 评估血糖动力学相位图稳定性，并用调整模型估计相位分层治疗响应。

## 被纳入二级诊断的模型

| target | feature_set | model | auroc | auprc | brier | n |
| --- | --- | --- | --- | --- | --- | --- |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | 0.800 | 0.742 | 0.177 | 1955 |
| y_hba1c_improved_ge_0_5 | C1_clinical | xgboost | 0.800 | 0.741 | 0.167 | 1955 |
| y_hba1c_improved_ge_0_5 | C1_clinical | logistic_ridge | 0.799 | 0.738 | 0.179 | 1955 |
| y_hba1c_improved_ge_0_5 | C4_phase_map | xgboost | 0.799 | 0.740 | 0.168 | 1955 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | 0.792 | 0.734 | 0.186 | 641 |
| y_tir_improved_ge_5pct | C4_phase_map | logistic_ridge | 0.787 | 0.734 | 0.188 | 641 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | xgboost | 0.770 | 0.701 | 0.191 | 641 |
| y_tir_improved_ge_5pct | C4_phase_map | xgboost | 0.766 | 0.708 | 0.192 | 641 |

## 最佳模型与校准

| target | feature_set | model | n | positive_rate | auroc | auprc | brier | calibration_intercept | calibration_slope | expected_calibration_error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | 1955 | 0.367 | 0.800 | 0.742 | 0.177 | -0.500 | 1.040 | 0.090 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | 641 | 0.423 | 0.792 | 0.734 | 0.186 | -0.313 | 0.878 | 0.057 |

解释要点：

- AUROC/AUPRC 反映排序能力，但不能说明概率是否可信。
- calibration intercept 接近 0、calibration slope 接近 1、Brier 和 ECE 越低，越支持模型可作为风险分层工具。
- 当前二级诊断使用 out-of-fold 预测，因此比全数据拟合后的表观性能更接近真实泛化表现。

校准图：`figures/journal_calibration_curves.png`

## 决策曲线分析

| target | feature_set | model | max_net_benefit | median_net_benefit |
| --- | --- | --- | --- | --- |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | 0.335 | 0.125 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | 0.394 | 0.179 |

决策曲线图：`figures/journal_decision_curve.png`

该结果用于回答一个临床审稿问题：模型在何种阈值区间内比“全部干预”或“完全不干预”更有净获益。若目标期刊偏临床转化，后续应预先定义 2-3 个临床可解释阈值，例如 20%、30%、40% 的改善概率。

## 可解释性：Permutation Importance

| target | feature_set | model | feature | importance_mean | importance_sd |
| --- | --- | --- | --- | --- | --- |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | x_baseline_hba1c_pct | 0.208 | 0.034 |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | x_randomized_arm | 0.057 | 0.013 |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | study_id | 0.039 | 0.009 |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | x_baseline_bmi | 0.004 | 0.003 |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | x_race | 0.002 | 0.001 |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | x_ethnicity | -0.000 | 0.000 |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | x_diabetes_duration_years | -0.000 | 0.004 |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | x_age_years | -0.001 | 0.003 |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | x_sex | -0.001 | 0.001 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | x_randomized_arm | 0.148 | 0.030 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | cgm_time_in_range_70_180_pct | 0.132 | 0.060 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | cgm_time_above_180_pct | 0.081 | 0.049 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | x_baseline_hba1c_pct | 0.052 | 0.022 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | cgm_mean_glucose_mg_dl | 0.035 | 0.032 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | study_id | 0.027 | 0.018 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | cgm_time_below_54_pct | 0.014 | 0.020 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | cgm_time_above_250_pct | 0.011 | 0.019 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | x_age_years | 0.008 | 0.009 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | cgm_time_below_70_pct | 0.004 | 0.012 |

变量重要性图：`figures/journal_permutation_importance.png`

该分析没有使用随访变量作为输入，重要性仅反映基线临床、基线 CGM 和相图特征对预测任务的贡献，避免了随访后变量造成的数据泄漏。

## 相图稳定性

| n_bootstrap | ari_median | ari_iqr_low | ari_iqr_high | silhouette_median |
| --- | --- | --- | --- | --- |
| 150 | 0.826 | 0.755 | 0.890 | 0.268 |

相图 bootstrap 稳定性图：`figures/phase_bootstrap_stability.png`

Adjusted Rand Index 越高，说明相位结构对样本重抽样越稳定。若后续要冲击更高水平期刊，建议进一步做 leave-one-study-out 相图重建、不同相位数 K 的敏感性分析，以及连续相位坐标替代离散标签的稳健性分析。

## 调整后的异质性治疗响应

| phase_label | n | adjusted_risk_difference | bootstrap_ci_low | bootstrap_ci_high | bootstrap_successful_fits | adjustment_model | crude_risk_difference | crude_hba1c_change_difference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 低血糖易感相 | 54 | 0.281 | 0.105 | 0.408 | 200 | l2_logistic_with_study_phase_and_treatment_phase_interactions | 0.274 | -0.170 |
| 稳定达标相 | 177 | 0.181 | 0.095 | 0.253 | 200 | l2_logistic_with_study_phase_and_treatment_phase_interactions | 0.187 | -0.184 |
| 高血糖持续相 | 165 | 0.180 | 0.038 | 0.311 | 200 | l2_logistic_with_study_phase_and_treatment_phase_interactions | 0.178 | -0.302 |
| 昼夜节律紊乱相 | 90 | 0.113 | -0.051 | 0.242 | 200 | l2_logistic_with_study_phase_and_treatment_phase_interactions | 0.064 | -0.200 |
| 高波动震荡相 | 158 | 0.111 | -0.029 | 0.240 | 200 | l2_logistic_with_study_phase_and_treatment_phase_interactions | 0.134 | -0.317 |

异质性治疗响应图：`figures/journal_adjusted_hte_by_phase.png`

该模型调整了研究、年龄、基线 HbA1c 和基线 TIR，并估计不同相位内治疗相对于对照的 HbA1c 改善风险差。结果仍应被解释为探索性、假设生成证据，不应直接作为临床决策规则。

## 留一研究外部泛化

| target | feature_set | model | heldout_study_count | total_test_n | auroc_mean | auroc_sd | auroc_median | auroc_min | auroc_max | auprc_mean | brier_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| y_hba1c_improved_ge_0_5 | C1_clinical | logistic_ridge | 13 | 1955 | 0.727 | 0.079 | 0.743 | 0.624 | 0.859 | 0.583 | 0.211 |
| y_hba1c_improved_ge_0_5 | C2_clinical_plus_cgm | logistic_ridge | 13 | 1955 | 0.723 | 0.080 | 0.714 | 0.624 | 0.859 | 0.578 | 0.213 |
| y_hba1c_improved_ge_0_5 | C1_clinical | extra_trees | 13 | 1955 | 0.721 | 0.083 | 0.690 | 0.627 | 0.901 | 0.561 | 0.210 |
| y_hba1c_improved_ge_0_5 | C1_clinical | catboost | 13 | 1955 | 0.720 | 0.081 | 0.708 | 0.620 | 0.869 | 0.568 | 0.198 |
| y_hba1c_improved_ge_0_5 | C1_clinical | xgboost | 13 | 1955 | 0.719 | 0.080 | 0.708 | 0.615 | 0.857 | 0.570 | 0.198 |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | 13 | 1955 | 0.718 | 0.079 | 0.708 | 0.624 | 0.857 | 0.565 | 0.204 |
| y_hba1c_improved_ge_0_5 | C4_phase_map | logistic_ridge | 13 | 1955 | 0.718 | 0.081 | 0.666 | 0.626 | 0.859 | 0.575 | 0.217 |
| y_hba1c_improved_ge_0_5 | C4_phase_map | catboost | 13 | 1955 | 0.718 | 0.086 | 0.680 | 0.598 | 0.875 | 0.560 | 0.202 |
| y_hba1c_improved_ge_0_5 | C1_clinical | mlp | 13 | 1955 | 0.717 | 0.080 | 0.704 | 0.617 | 0.844 | 0.574 | 0.200 |
| y_hba1c_improved_ge_0_5 | C4_phase_map | xgboost | 13 | 1955 | 0.715 | 0.084 | 0.670 | 0.607 | 0.861 | 0.561 | 0.202 |
| y_hba1c_improved_ge_0_5 | C1_clinical | random_forest | 13 | 1955 | 0.714 | 0.076 | 0.692 | 0.618 | 0.853 | 0.563 | 0.207 |
| y_hba1c_improved_ge_0_5 | C2_clinical_plus_cgm | catboost | 13 | 1955 | 0.712 | 0.083 | 0.677 | 0.613 | 0.861 | 0.565 | 0.201 |
| y_hba1c_improved_ge_0_5 | C1_clinical | svm_rbf | 13 | 1955 | 0.712 | 0.064 | 0.717 | 0.618 | 0.801 | 0.568 | 0.203 |
| y_hba1c_improved_ge_0_5 | C4_phase_map | lightgbm | 13 | 1955 | 0.712 | 0.087 | 0.671 | 0.600 | 0.861 | 0.553 | 0.207 |
| y_hba1c_improved_ge_0_5 | C2_clinical_plus_cgm | xgboost | 13 | 1955 | 0.709 | 0.085 | 0.665 | 0.614 | 0.861 | 0.554 | 0.202 |

外部验证热图：`figures/journal_loso_heatmap.png`

LOSO 结果用于回答模型是否只学习了某一个研究的数据结构。若某个模型 5 折 AUROC 高但 LOSO 均值或最小值明显下降，投稿时应把它定位为内部预测模型，而不是可泛化临床工具。

## 相图特征增量价值

| validation | target | model | comparison | delta_auroc_mean | delta_auroc_median | delta_auroc_min | delta_positive_fraction | n_comparisons |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5fold_cv | y_hba1c_improved_ge_0_5 | knn | C4_phase_map_minus_C1_clinical | 0.006 | 0.006 | 0.006 | 1.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | hist_gradient_boosting | C4_phase_map_minus_C2_clinical_plus_cgm | 0.006 | 0.006 | 0.006 | 1.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | xgboost | C4_phase_map_minus_C2_clinical_plus_cgm | 0.003 | 0.003 | 0.003 | 1.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | knn | C4_phase_map_minus_C2_clinical_plus_cgm | 0.003 | 0.003 | 0.003 | 1.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | lightgbm | C4_phase_map_minus_C2_clinical_plus_cgm | 0.003 | 0.003 | 0.003 | 1.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | mlp | C4_phase_map_minus_C1_clinical | 0.001 | 0.001 | 0.001 | 1.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | mlp | C4_phase_map_minus_C2_clinical_plus_cgm | -0.000 | -0.000 | -0.000 | 0.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | random_forest | C4_phase_map_minus_C2_clinical_plus_cgm | -0.001 | -0.001 | -0.001 | 0.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | xgboost | C4_phase_map_minus_C1_clinical | -0.001 | -0.001 | -0.001 | 0.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | logistic_ridge | C4_phase_map_minus_C2_clinical_plus_cgm | -0.002 | -0.002 | -0.002 | 0.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | svm_rbf | C4_phase_map_minus_C2_clinical_plus_cgm | -0.003 | -0.003 | -0.003 | 0.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | catboost | C4_phase_map_minus_C2_clinical_plus_cgm | -0.003 | -0.003 | -0.003 | 0.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | svm_rbf | C4_phase_map_minus_C1_clinical | -0.003 | -0.003 | -0.003 | 0.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | extra_trees | C4_phase_map_minus_C1_clinical | -0.003 | -0.003 | -0.003 | 0.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | lightgbm | C4_phase_map_minus_C1_clinical | -0.004 | -0.004 | -0.004 | 0.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | extra_trees | C4_phase_map_minus_C2_clinical_plus_cgm | -0.004 | -0.004 | -0.004 | 0.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | logistic_ridge | C4_phase_map_minus_C1_clinical | -0.004 | -0.004 | -0.004 | 0.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | catboost | C4_phase_map_minus_C1_clinical | -0.005 | -0.005 | -0.005 | 0.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | hist_gradient_boosting | C4_phase_map_minus_C1_clinical | -0.005 | -0.005 | -0.005 | 0.000 | 1 |
| 5fold_cv | y_hba1c_improved_ge_0_5 | random_forest | C4_phase_map_minus_C1_clinical | -0.006 | -0.006 | -0.006 | 0.000 | 1 |

该表比较 C4 相图特征集相对于 C1 临床特征和 C2 临床+CGM 特征的 AUROC 变化。若相图特征没有明显提高 AUROC，它仍可能具有机制解释、分层治疗响应和可视化价值；论文叙事应避免仅以预测增益作为相图价值的唯一依据。

## 模型差异 paired bootstrap

| target | comparison | left_feature_set | left_model | right_feature_set | right_model | n | delta_auroc_left_minus_right | bootstrap_ci_low | bootstrap_ci_high | bootstrap_p_value | bootstrap_successful_resamples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| y_hba1c_improved_ge_0_5 | best_vs_runner_up | C1_clinical | lightgbm | C1_clinical | xgboost | 1955 | 0.001 | -0.002 | 0.004 | 0.622 | 1000 |
| y_hba1c_improved_ge_0_5 | best_phase_map_vs_best_non_phase | C4_phase_map | xgboost | C1_clinical | lightgbm | 1955 | -0.002 | -0.008 | 0.005 | 0.652 | 1000 |
| y_tir_improved_ge_5pct | best_vs_runner_up | C2_clinical_plus_cgm | logistic_ridge | C4_phase_map | logistic_ridge | 641 | 0.005 | -0.001 | 0.011 | 0.118 | 1000 |
| y_tir_improved_ge_5pct | best_phase_map_vs_best_non_phase | C4_phase_map | logistic_ridge | C2_clinical_plus_cgm | logistic_ridge | 641 | -0.005 | -0.011 | 0.002 | 0.138 | 1000 |

该分析基于 out-of-fold 预测进行配对 bootstrap，用来判断排名相近模型的 AUROC 差异是否稳定。若置信区间跨 0，应报告模型性能相近，而不是过度强调名义第一名。

## 新增输出文件

- `results/journal_oof_predictions.csv`
- `results/journal_calibration_metrics.csv`
- `results/journal_calibration_bins.csv`
- `results/journal_decision_curve.csv`
- `results/journal_permutation_importance.csv`
- `results/phase_bootstrap_stability.csv`
- `results/journal_adjusted_hte_by_phase.csv`
- `results/journal_loso_summary.csv`
- `results/journal_incremental_phase_value.csv`
- `results/journal_model_pairwise_bootstrap.csv`
- `figures/journal_calibration_curves.png`
- `figures/journal_decision_curve.png`
- `figures/journal_permutation_importance.png`
- `figures/phase_bootstrap_stability.png`
- `figures/journal_adjusted_hte_by_phase.png`
- `figures/journal_loso_heatmap.png`

## 面向投稿的下一步

1. 将 primary endpoint 固定为 HbA1c 改善 >=0.5%，key secondary endpoint 固定为 TIR 改善 >=5 个百分点。
2. 使用 nested cross-validation 或固定外部研究留出集，避免模型选择偏倚。
3. 对治疗响应结果采用 causal forest、R-learner 或 doubly robust learner 复核。
4. 在论文中把相图作为“机制启发的低维表征”，把机器学习作为预测与分层工具，而不是把聚类标签解释为确定的生物亚型。
5. 若申请到更细粒度 CGM 原始时序，扩展为动态系统论文：连续相轨迹、状态转移、治疗诱导相变和个体化干预窗口。
