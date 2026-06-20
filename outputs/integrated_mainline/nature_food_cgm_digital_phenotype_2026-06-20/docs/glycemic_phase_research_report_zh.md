# 血糖动力学相图研究分析报告

生成脚本：`scripts/run_glycemic_phase_research.py`  
数据：`processed_ml_table.csv` 与 `cgm_summary_long.csv`

## 完成情况

本轮已完成五个目标的第一版可复现分析：

1. **构建血糖动力学相图**：基于 748 名有基线 CGM 汇总的受试者，构建高血糖负担、低血糖易感性、动态不稳定性、恢复力代理指标和昼夜节律紊乱 5 个粗粒化序参量，并用聚类得到血糖相位。
2. **验证相位与临床结局关系**：输出相位별 HbA1c 改善、TIR 改善和连续变化摘要，并进行卡方/Kruskal-Wallis 检验。
3. **比较不同机器学习方法预测能力**：比较 Dummy、Logistic、RandomForest、ExtraTrees、HistGradientBoosting、SVM、KNN、MLP 在临床特征、CGM 特征、相图特征三类特征集上的表现。
4. **识别异质性治疗响应**：在 WISDM、CITY、SENCE、DCLP3 等具备相位标签和可比较治疗臂的 RCT 内，估计相位分层治疗响应差异。
5. **形成可解释个体化干预框架**：为每位有相位标签的受试者输出相位、关键序参量、研究用预测概率和相位导向干预重点。

## 目标 1：血糖动力学相图

相位分布：

| phase_label | n   |
| ----------- | --- |
| 稳定达标相       | 234 |
| 高波动震荡相      | 182 |
| 高血糖持续相      | 178 |
| 昼夜节律紊乱相     | 97  |
| 低血糖易感相      | 57  |

核心图：

- `figures/glycemic_phase_map.png`
- `figures/phase_tir_boxplot.png`

## 目标 2：相位与临床结局

相位结局摘要：

| phase_label | n   | study_count | baseline_tir_mean | baseline_mean_glucose | baseline_cv | hba1c_improvement_n | hba1c_improvement_rate | hba1c_change_mean | tir_improvement_n | tir_improvement_rate | tir_change_mean |
| ----------- | --- | ----------- | ----------------- | --------------------- | ----------- | ------------------- | ---------------------- | ----------------- | ----------------- | -------------------- | --------------- |
| 稳定达标相       | 234 | 5           | 68.294            | 153.063               | 34.631      | 229                 | 0.210                  | -0.114            | 175               | 0.360                | 1.325           |
| 高波动震荡相      | 182 | 5           | 53.148            | 174.040               | 43.492      | 177                 | 0.271                  | -0.138            | 158               | 0.399                | 2.224           |
| 高血糖持续相      | 178 | 5           | 31.003            | 228.124               | 37.822      | 167                 | 0.413                  | -0.305            | 164               | 0.506                | 6.945           |
| 昼夜节律紊乱相     | 97  | 5           | 41.209            | 199.911               | 44.979      | 91                  | 0.352                  | -0.186            | 89                | 0.438                | 2.936           |
| 低血糖易感相      | 57  | 5           | 53.153            | 151.625               | 52.308      | 55                  | 0.255                  | -0.089            | 55                | 0.418                | 2.153           |

关联检验：

| outcome                               | test           | statistic | p_value | df | n   |
| ------------------------------------- | -------------- | --------- | ------- | -- | --- |
| y_hba1c_improved_ge_0_5               | chi_square     | 21.620    | 0.000   | 4  | 719 |
| y_tir_improved_ge_5pct                | chi_square     | 7.957     | 0.093   | 4  | 641 |
| y_hba1c_change_pct_points             | kruskal_wallis | 7.633     | 0.106   | 4  | 719 |
| y_change_cgm_time_in_range_70_180_pct | kruskal_wallis | 14.989    | 0.005   | 4  | 641 |

## 目标 3：机器学习预测能力比较

HbA1c 改善主任务前 10 名：

| target                  | feature_set          | model          | validation | n    | positive_rate | accuracy | balanced_accuracy | brier | auroc | auprc |
| ----------------------- | -------------------- | -------------- | ---------- | ---- | ------------- | -------- | ----------------- | ----- | ----- | ----- |
| y_hba1c_improved_ge_0_5 | C1_clinical          | lightgbm       | 5fold_cv   | 1955 | 0.367         | 0.734    | 0.724             | 0.177 | 0.800 | 0.742 |
| y_hba1c_improved_ge_0_5 | C1_clinical          | xgboost        | 5fold_cv   | 1955 | 0.367         | 0.756    | 0.707             | 0.167 | 0.800 | 0.741 |
| y_hba1c_improved_ge_0_5 | C1_clinical          | logistic_ridge | 5fold_cv   | 1955 | 0.367         | 0.736    | 0.729             | 0.179 | 0.799 | 0.738 |
| y_hba1c_improved_ge_0_5 | C4_phase_map         | xgboost        | 5fold_cv   | 1955 | 0.367         | 0.749    | 0.702             | 0.168 | 0.799 | 0.740 |
| y_hba1c_improved_ge_0_5 | C1_clinical          | catboost       | 5fold_cv   | 1955 | 0.367         | 0.759    | 0.706             | 0.168 | 0.798 | 0.742 |
| y_hba1c_improved_ge_0_5 | C2_clinical_plus_cgm | logistic_ridge | 5fold_cv   | 1955 | 0.367         | 0.734    | 0.727             | 0.179 | 0.797 | 0.737 |
| y_hba1c_improved_ge_0_5 | C2_clinical_plus_cgm | catboost       | 5fold_cv   | 1955 | 0.367         | 0.752    | 0.698             | 0.169 | 0.797 | 0.740 |
| y_hba1c_improved_ge_0_5 | C4_phase_map         | lightgbm       | 5fold_cv   | 1955 | 0.367         | 0.734    | 0.719             | 0.178 | 0.797 | 0.740 |
| y_hba1c_improved_ge_0_5 | C2_clinical_plus_cgm | xgboost        | 5fold_cv   | 1955 | 0.367         | 0.752    | 0.705             | 0.168 | 0.795 | 0.738 |
| y_hba1c_improved_ge_0_5 | C4_phase_map         | logistic_ridge | 5fold_cv   | 1955 | 0.367         | 0.731    | 0.723             | 0.180 | 0.795 | 0.735 |

TIR 改善任务前 10 名：

| target                 | feature_set          | model          | validation | n   | positive_rate | accuracy | balanced_accuracy | brier | auroc | auprc |
| ---------------------- | -------------------- | -------------- | ---------- | --- | ------------- | -------- | ----------------- | ----- | ----- | ----- |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | 5fold_cv   | 641 | 0.423         | 0.733    | 0.733             | 0.186 | 0.792 | 0.734 |
| y_tir_improved_ge_5pct | C4_phase_map         | logistic_ridge | 5fold_cv   | 641 | 0.423         | 0.719    | 0.719             | 0.188 | 0.787 | 0.734 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | xgboost        | 5fold_cv   | 641 | 0.423         | 0.735    | 0.721             | 0.191 | 0.770 | 0.701 |
| y_tir_improved_ge_5pct | C4_phase_map         | xgboost        | 5fold_cv   | 641 | 0.423         | 0.730    | 0.716             | 0.192 | 0.766 | 0.708 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | lightgbm       | 5fold_cv   | 641 | 0.423         | 0.718    | 0.714             | 0.196 | 0.766 | 0.692 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | svm_rbf        | 5fold_cv   | 641 | 0.423         | 0.699    | 0.686             | 0.194 | 0.766 | 0.697 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | catboost       | 5fold_cv   | 641 | 0.423         | 0.702    | 0.684             | 0.194 | 0.764 | 0.697 |
| y_tir_improved_ge_5pct | C4_phase_map         | lightgbm       | 5fold_cv   | 641 | 0.423         | 0.713    | 0.708             | 0.198 | 0.760 | 0.703 |
| y_tir_improved_ge_5pct | C4_phase_map         | catboost       | 5fold_cv   | 641 | 0.423         | 0.693    | 0.671             | 0.196 | 0.760 | 0.696 |
| y_tir_improved_ge_5pct | C4_phase_map         | mlp            | 5fold_cv   | 641 | 0.423         | 0.705    | 0.676             | 0.197 | 0.756 | 0.710 |

Leave-one-study-out 摘要：

| target                  | feature_set          | model          | mean_auroc | mean_auprc | mean_brier | studies |
| ----------------------- | -------------------- | -------------- | ---------- | ---------- | ---------- | ------- |
| y_hba1c_improved_ge_0_5 | C1_clinical          | logistic_ridge | 0.727      | 0.583      | 0.211      | 13      |
| y_hba1c_improved_ge_0_5 | C2_clinical_plus_cgm | logistic_ridge | 0.723      | 0.578      | 0.213      | 13      |
| y_hba1c_improved_ge_0_5 | C1_clinical          | extra_trees    | 0.721      | 0.561      | 0.210      | 13      |
| y_hba1c_improved_ge_0_5 | C1_clinical          | catboost       | 0.720      | 0.568      | 0.198      | 13      |
| y_hba1c_improved_ge_0_5 | C1_clinical          | xgboost        | 0.719      | 0.570      | 0.198      | 13      |
| y_hba1c_improved_ge_0_5 | C1_clinical          | lightgbm       | 0.718      | 0.565      | 0.204      | 13      |
| y_hba1c_improved_ge_0_5 | C4_phase_map         | logistic_ridge | 0.718      | 0.575      | 0.217      | 13      |
| y_hba1c_improved_ge_0_5 | C4_phase_map         | catboost       | 0.718      | 0.560      | 0.202      | 13      |
| y_hba1c_improved_ge_0_5 | C1_clinical          | mlp            | 0.717      | 0.574      | 0.200      | 13      |
| y_hba1c_improved_ge_0_5 | C4_phase_map         | xgboost        | 0.715      | 0.561      | 0.202      | 13      |
| y_hba1c_improved_ge_0_5 | C1_clinical          | random_forest  | 0.714      | 0.563      | 0.207      | 13      |
| y_hba1c_improved_ge_0_5 | C2_clinical_plus_cgm | catboost       | 0.712      | 0.565      | 0.201      | 13      |
| y_hba1c_improved_ge_0_5 | C1_clinical          | svm_rbf        | 0.712      | 0.568      | 0.203      | 13      |
| y_hba1c_improved_ge_0_5 | C4_phase_map         | lightgbm       | 0.712      | 0.553      | 0.207      | 13      |
| y_hba1c_improved_ge_0_5 | C2_clinical_plus_cgm | xgboost        | 0.709      | 0.554      | 0.202      | 13      |
| y_hba1c_improved_ge_0_5 | C2_clinical_plus_cgm | mlp            | 0.709      | 0.560      | 0.198      | 13      |
| y_hba1c_improved_ge_0_5 | C2_clinical_plus_cgm | lightgbm       | 0.708      | 0.552      | 0.206      | 13      |
| y_hba1c_improved_ge_0_5 | C2_clinical_plus_cgm | extra_trees    | 0.706      | 0.557      | 0.215      | 13      |
| y_hba1c_improved_ge_0_5 | C2_clinical_plus_cgm | svm_rbf        | 0.702      | 0.546      | 0.208      | 13      |
| y_hba1c_improved_ge_0_5 | C4_phase_map         | random_forest  | 0.700      | 0.547      | 0.212      | 13      |

核心图：

- `figures/model_benchmark_primary_auroc.png`

说明：当前环境已安装并运行 scikit-learn 模型。XGBoost、LightGBM、CatBoost、TabPFN、深度时间序列基础模型尚未在本轮脚本中运行，可作为下一步增强模型接入同一 pipeline。

## 目标 4：异质性治疗响应

相位分层治疗响应估计：

| study_id | phase_label | control_arm | treatment_arm | n_control | n_treatment | response_rate_control | response_rate_treatment | risk_difference_treatment_minus_control | hba1c_change_control_mean | hba1c_change_treatment_mean | hba1c_change_difference_treatment_minus_control |
| -------- | ----------- | ----------- | ------------- | --------- | ----------- | --------------------- | ----------------------- | --------------------------------------- | ------------------------- | --------------------------- | ----------------------------------------------- |
| WISDM    | 低血糖易感相      | bgm         | cgm           | 14        | 9           | 0.071                 | 0.333                   | 0.262                                   | 0.100                     | -0.111                      | -0.211                                          |
| WISDM    | 昼夜节律紊乱相     | bgm         | cgm           | 15        | 14          | 0.200                 | 0.500                   | 0.300                                   | -0.000                    | -0.421                      | -0.421                                          |
| WISDM    | 稳定达标相       | bgm         | cgm           | 41        | 42          | 0.049                 | 0.190                   | 0.142                                   | 0.060                     | -0.156                      | -0.216                                          |
| WISDM    | 高波动震荡相      | bgm         | cgm           | 14        | 22          | 0.286                 | 0.227                   | -0.058                                  | -0.150                    | -0.264                      | -0.114                                          |
| WISDM    | 高血糖持续相      | bgm         | cgm           | 12        | 15          | 0.333                 | 0.800                   | 0.467                                   | -0.267                    | -0.933                      | -0.667                                          |
| CITY     | 低血糖易感相      | bgm         | cgm           | 7         | 7           | 0.143                 | 0.429                   | 0.286                                   | -0.043                    | -0.171                      | -0.129                                          |
| CITY     | 昼夜节律紊乱相     | bgm         | cgm           | 13        | 15          | 0.231                 | 0.400                   | 0.169                                   | 0.231                     | -0.267                      | -0.497                                          |
| CITY     | 高波动震荡相      | bgm         | cgm           | 13        | 11          | 0.154                 | 0.545                   | 0.392                                   | 0.208                     | -0.473                      | -0.680                                          |
| CITY     | 高血糖持续相      | bgm         | cgm           | 36        | 31          | 0.250                 | 0.387                   | 0.137                                   | -0.014                    | -0.390                      | -0.376                                          |
| SENCE    | 昼夜节律紊乱相     | bgm         | cgm_+_fbi     | 10        | 8           | 0.400                 | 0.250                   | -0.150                                  | -0.240                    | -0.150                      | 0.090                                           |
| SENCE    | 昼夜节律紊乱相     | bgm         | standard_cgm  | 10        | 5           | 0.400                 | 0.200                   | -0.200                                  | -0.240                    | -0.050                      | 0.190                                           |
| SENCE    | 高波动震荡相      | bgm         | cgm_+_fbi     | 10        | 9           | 0.200                 | 0.444                   | 0.244                                   | 0.080                     | -0.344                      | -0.424                                          |
| SENCE    | 高波动震荡相      | bgm         | standard_cgm  | 10        | 12          | 0.200                 | 0.167                   | -0.033                                  | 0.080                     | 0.167                       | 0.087                                           |
| SENCE    | 高血糖持续相      | bgm         | cgm_+_fbi     | 19        | 23          | 0.316                 | 0.391                   | 0.076                                   | -0.063                    | -0.204                      | -0.141                                          |
| SENCE    | 高血糖持续相      | bgm         | standard_cgm  | 19        | 20          | 0.316                 | 0.350                   | 0.034                                   | -0.063                    | -0.085                      | -0.022                                          |
| DCLP3    | 昼夜节律紊乱相     | sap         | clc           | 5         | 5           | 0.400                 | 0.600                   | 0.200                                   | -0.280                    | -0.640                      | -0.360                                          |
| DCLP3    | 稳定达标相       | sap         | clc           | 25        | 54          | 0.120                 | 0.352                   | 0.232                                   | -0.088                    | -0.241                      | -0.153                                          |
| DCLP3    | 高波动震荡相      | sap         | clc           | 23        | 44          | 0.217                 | 0.341                   | 0.124                                   | 0.152                     | -0.302                      | -0.454                                          |

解释限制：这些估计是 RCT 内相位分层的描述性/探索性治疗效应差异。由于相位子组样本量有限，不能等同于已验证的临床治疗规则。

## 目标 5：个体化干预框架

已输出：

- `results/individualized_intervention_framework.csv`

该表包含相位标签、相位序参量、研究用预测概率和相位导向干预重点。该框架用于科研解释和后续模型开发，不能直接作为临床决策工具。

## 主要产物

- `data/processed/glycemic_phase_features.csv`
- `data/processed/glycemic_phase_labels.csv`
- `results/phase_outcome_summary.csv`
- `results/phase_association_tests.csv`
- `results/model_performance_cv.csv`
- `results/model_performance_loso.csv`
- `results/hte_by_phase.csv`
- `results/individualized_intervention_framework.csv`
- `figures/glycemic_phase_map.png`
- `figures/phase_tir_boxplot.png`
- `figures/model_benchmark_primary_auroc.png`

## 下一步建议

1. 将 PEDAP、IOBP2、DCLP5、CLVer 等原始 device/CGM 明细聚合为日级和事件级动力学特征。
2. 接入 XGBoost、LightGBM、CatBoost、TabPFN 和时间序列基础模型。
3. 对相位标签做 bootstrap 稳定性和 leave-one-study-out 相位重建。
4. 对 HTE 使用 causal forest / doubly robust learner，并在单个 RCT 内独立报告。
5. 将本报告转化为论文结果章节和图表草稿。
