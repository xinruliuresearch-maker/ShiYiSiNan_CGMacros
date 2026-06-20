# Nested CV 微调模型实验

生成脚本：`scripts/run_nested_tuning_experiments.py`

## 目的

该实验对表现靠前的 logistic ridge、XGBoost 和 LightGBM 进行内层调参、外层评估，减少“在同一交叉验证中选模型并报告性能”的乐观偏倚。它是主模型比较的稳健性补充，而不是替代全部模型基准。

## 纳入微调的候选模型

| target | feature_set | model |
| --- | --- | --- |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm |
| y_hba1c_improved_ge_0_5 | C1_clinical | xgboost |
| y_hba1c_improved_ge_0_5 | C1_clinical | logistic_ridge |
| y_hba1c_improved_ge_0_5 | C4_phase_map | xgboost |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge |
| y_tir_improved_ge_5pct | C4_phase_map | logistic_ridge |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | xgboost |

## Nested CV 结果

| target | feature_set | model | outer_folds | total_test_n | auroc_mean | auroc_sd | auprc_mean | brier_mean | inner_auroc_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| y_hba1c_improved_ge_0_5 | C1_clinical | lightgbm | 5 | 1955 | 0.802 | 0.038 | 0.745 | 0.180 | 0.796 |
| y_hba1c_improved_ge_0_5 | C1_clinical | xgboost | 5 | 1955 | 0.801 | 0.038 | 0.743 | 0.169 | 0.798 |
| y_hba1c_improved_ge_0_5 | C1_clinical | logistic_ridge | 5 | 1955 | 0.799 | 0.027 | 0.735 | 0.179 | 0.794 |
| y_hba1c_improved_ge_0_5 | C4_phase_map | xgboost | 5 | 1955 | 0.798 | 0.038 | 0.743 | 0.170 | 0.794 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | logistic_ridge | 5 | 641 | 0.795 | 0.053 | 0.744 | 0.185 | 0.781 |
| y_tir_improved_ge_5pct | C4_phase_map | logistic_ridge | 5 | 641 | 0.791 | 0.060 | 0.745 | 0.188 | 0.777 |
| y_tir_improved_ge_5pct | C2_clinical_plus_cgm | xgboost | 5 | 641 | 0.761 | 0.045 | 0.714 | 0.195 | 0.754 |

图形：`figures/journal_nested_tuning_auroc.png`

## 解释

若 nested CV 的 AUROC 低于普通 5 折 CV，说明原始模型比较包含模型选择乐观偏倚；投稿时应优先报告 nested CV 或外部 LOSO 结果作为稳健估计。
