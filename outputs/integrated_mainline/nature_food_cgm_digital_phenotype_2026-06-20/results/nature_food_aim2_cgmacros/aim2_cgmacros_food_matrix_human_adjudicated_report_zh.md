# Aim 2: CGMacros 食物基质与 PPGR 脆弱性

由 `scripts/run_nature_food_aim2_cgmacros_food_matrix.py` 生成。

## 状态

本轮分析使用人工仲裁终版食物基质标签。

- 餐次数: 1498
- 受试者数: 40
- 高 2h iAUC 阈值: 4552.5
- 高峰值增量阈值: 73.1

## 人工标注状态

| metric                                   | value               |
| ---------------------------------------- | ------------------- |
| total_meals                              | 1498                |
| subjects                                 | 40                  |
| human_review_rate                        | 0.6221628838451269  |
| fdc_match_low_confidence_or_missing_rate | 0.07543391188251002 |
| human_final_labels_present               | True                |
| human_final_label_coverage               | 1.0                 |
| dual_independent_human_review_meals      | 279                 |
| dual_independent_human_review_rate       | 0.29935622317596566 |
| cohen_kappa_human_dual_review            | 0.3694147918912341  |
| high_iauc_threshold                      | 4552.525000000001   |
| high_peak_threshold                      | 73.14999999999999   |

## 食物基质概览

| matrix_category                      | meals | subjects | human_review_rate | final_label_coverage | median_iauc_2h | high_iauc_rate | median_carbs | median_fiber |
| ------------------------------------ | ----- | -------- | ----------------- | -------------------- | -------------- | -------------- | ------------ | ------------ |
| low_carb_or_protein_forward          | 565   | 40       | 0.9664            | 1                    | 1921           | 0.2407         | 21           | 0            |
| fiber_rich_or_whole_food_matrix      | 525   | 40       | 0.0819            | 1                    | 2117           | 0.219          | 73           | 10           |
| mixed_meal_protein_fat_buffered      | 284   | 40       | 0.919             | 1                    | 3135           | 0.3838         | 66           | 2            |
| mixed_or_unknown_matrix              | 54    | 24       | 1                 | 1                    | 2084           | 0.2037         | 25           | 1            |
| refined_starch_low_matrix_protection | 11    | 9        | 0.6364            | 1                    | 809.9          | 0.1818         | 47           | 0            |
| sweetened_beverage_or_liquid_carb    | 59    | 21       | 0.3559            | 1                    | 842            | 0.0339         | 24           | 0            |

## Nature Food 图件判断

- 人工仲裁后食物基质信号是否保留: True
- 双评 Cohen kappa: 0.369
- 判断: 食物基质信号可进入 Nature Food 主图候选；双评一致性需要在方法和敏感性分析中透明呈现。

## 关键模型项

| outcome         | model                   | term                                                       | estimate_CI              | p_fmt  | q_fmt  | n    | n_subjects |
| --------------- | ----------------------- | ---------------------------------------------------------- | ------------------------ | ------ | ------ | ---- | ---------- |
| log1p_iauc_2h   | msi_base                | msi_core                                                   | 1.141 (0.658, 1.624)     | <0.001 | <0.001 | 1498 | 40         |
| log1p_iauc_2h   | msi_base                | carbs_10g                                                  | 0.019 (-0.008, 0.045)    | 0.168  | 0.201  | 1498 | 40         |
| peak_delta_2h_w | msi_base                | msi_core                                                   | 28.896 (18.814, 38.979)  | <0.001 | <0.001 | 1498 | 40         |
| peak_delta_2h_w | msi_base                | carbs_10g                                                  | 0.399 (-0.289, 1.087)    | 0.256  | 0.257  | 1498 | 40         |
| high_iauc_2h    | msi_base                | msi_core                                                   | 1.344 (0.727, 1.961)     | <0.001 | <0.001 | 1498 | 40         |
| high_iauc_2h    | msi_base                | carbs_10g                                                  | 0.009 (-0.021, 0.038)    | 0.557  | 0.557  | 1498 | 40         |
| log1p_iauc_2h   | food_matrix_main        | C(matrix_category)[T.fiber_rich_or_whole_food_matrix]      | -0.134 (-0.483, 0.216)   | 0.454  | 0.554  | 1498 | 40         |
| log1p_iauc_2h   | food_matrix_main        | C(matrix_category)[T.mixed_meal_protein_fat_buffered]      | 0.600 (0.321, 0.880)     | <0.001 | <0.001 | 1498 | 40         |
| log1p_iauc_2h   | food_matrix_main        | C(matrix_category)[T.mixed_or_unknown_matrix]              | 0.271 (-0.217, 0.759)    | 0.276  | 0.434  | 1498 | 40         |
| log1p_iauc_2h   | food_matrix_main        | C(matrix_category)[T.refined_starch_low_matrix_protection] | -0.095 (-1.182, 0.993)   | 0.865  | 0.865  | 1498 | 40         |
| log1p_iauc_2h   | food_matrix_main        | C(matrix_category)[T.sweetened_beverage_or_liquid_carb]    | -0.193 (-0.698, 0.311)   | 0.453  | 0.554  | 1498 | 40         |
| log1p_iauc_2h   | food_matrix_main        | msi_core                                                   | 1.136 (0.661, 1.611)     | <0.001 | <0.001 | 1498 | 40         |
| log1p_iauc_2h   | food_matrix_main        | carbs_10g                                                  | 0.019 (-0.008, 0.045)    | 0.164  | 0.301  | 1498 | 40         |
| peak_delta_2h_w | food_matrix_main        | C(matrix_category)[T.fiber_rich_or_whole_food_matrix]      | -3.216 (-8.594, 2.162)   | 0.241  | 0.345  | 1498 | 40         |
| peak_delta_2h_w | food_matrix_main        | C(matrix_category)[T.mixed_meal_protein_fat_buffered]      | 10.443 (5.787, 15.098)   | <0.001 | <0.001 | 1498 | 40         |
| peak_delta_2h_w | food_matrix_main        | C(matrix_category)[T.mixed_or_unknown_matrix]              | 1.570 (-5.186, 8.326)    | 0.649  | 0.714  | 1498 | 40         |
| peak_delta_2h_w | food_matrix_main        | C(matrix_category)[T.refined_starch_low_matrix_protection] | -0.908 (-15.578, 13.762) | 0.903  | 0.903  | 1498 | 40         |
| peak_delta_2h_w | food_matrix_main        | C(matrix_category)[T.sweetened_beverage_or_liquid_carb]    | -3.195 (-8.619, 2.229)   | 0.248  | 0.345  | 1498 | 40         |
| peak_delta_2h_w | food_matrix_main        | msi_core                                                   | 28.855 (18.899, 38.812)  | <0.001 | <0.001 | 1498 | 40         |
| peak_delta_2h_w | food_matrix_main        | carbs_10g                                                  | 0.403 (-0.285, 1.092)    | 0.251  | 0.345  | 1498 | 40         |
| high_iauc_2h    | food_matrix_main        | C(matrix_category)[T.fiber_rich_or_whole_food_matrix]      | -0.040 (-0.293, 0.213)   | 0.755  | 0.755  | 1498 | 40         |
| high_iauc_2h    | food_matrix_main        | C(matrix_category)[T.mixed_meal_protein_fat_buffered]      | 0.729 (0.396, 1.062)     | <0.001 | <0.001 | 1498 | 40         |
| high_iauc_2h    | food_matrix_main        | C(matrix_category)[T.mixed_or_unknown_matrix]              | 0.325 (-0.124, 0.774)    | 0.155  | 0.285  | 1498 | 40         |
| high_iauc_2h    | food_matrix_main        | C(matrix_category)[T.refined_starch_low_matrix_protection] | 0.376 (-0.464, 1.217)    | 0.380  | 0.479  | 1498 | 40         |
| high_iauc_2h    | food_matrix_main        | C(matrix_category)[T.sweetened_beverage_or_liquid_carb]    | -0.427 (-0.889, 0.034)   | 0.069  | 0.153  | 1498 | 40         |
| high_iauc_2h    | food_matrix_main        | msi_core                                                   | 1.387 (0.763, 2.011)     | <0.001 | <0.001 | 1498 | 40         |
| high_iauc_2h    | food_matrix_main        | carbs_10g                                                  | 0.008 (-0.018, 0.034)    | 0.542  | 0.596  | 1498 | 40         |
| log1p_iauc_2h   | msi_carb_interaction    | msi_core                                                   | 1.115 (0.573, 1.657)     | <0.001 | <0.001 | 1498 | 40         |
| log1p_iauc_2h   | msi_carb_interaction    | carbs_10g                                                  | 0.019 (-0.007, 0.045)    | 0.156  | 0.218  | 1498 | 40         |
| log1p_iauc_2h   | msi_carb_interaction    | msi_core:carbs_10g                                         | 0.004 (-0.028, 0.037)    | 0.790  | 0.790  | 1498 | 40         |
| peak_delta_2h_w | msi_carb_interaction    | msi_core                                                   | 28.719 (16.468, 40.970)  | <0.001 | <0.001 | 1498 | 40         |
| peak_delta_2h_w | msi_carb_interaction    | carbs_10g                                                  | 0.401 (-0.287, 1.088)    | 0.253  | 0.295  | 1498 | 40         |
| peak_delta_2h_w | msi_carb_interaction    | msi_core:carbs_10g                                         | 0.030 (-0.593, 0.654)    | 0.924  | 0.924  | 1498 | 40         |
| high_iauc_2h    | msi_carb_interaction    | msi_core                                                   | 1.300 (0.578, 2.022)     | <0.001 | 0.001  | 1498 | 40         |
| high_iauc_2h    | msi_carb_interaction    | carbs_10g                                                  | 0.009 (-0.017, 0.036)    | 0.497  | 0.579  | 1498 | 40         |
| high_iauc_2h    | msi_carb_interaction    | msi_core:carbs_10g                                         | 0.008 (-0.034, 0.051)    | 0.697  | 0.697  | 1498 | 40         |
| log1p_iauc_2h   | matrix_carb_interaction | C(matrix_category)[T.fiber_rich_or_whole_food_matrix]      | 0.594 (0.178, 1.011)     | 0.005  | 0.007  | 1498 | 40         |
| log1p_iauc_2h   | matrix_carb_interaction | C(matrix_category)[T.mixed_meal_protein_fat_buffered]      | 1.240 (0.729, 1.750)     | <0.001 | <0.001 | 1498 | 40         |
| log1p_iauc_2h   | matrix_carb_interaction | C(matrix_category)[T.mixed_or_unknown_matrix]              | 1.857 (0.921, 2.794)     | <0.001 | <0.001 | 1498 | 40         |
| log1p_iauc_2h   | matrix_carb_interaction | C(matrix_category)[T.refined_starch_low_matrix_protection] | 0.794 (-0.506, 2.095)    | 0.231  | 0.261  | 1498 | 40         |

## 输出文件

- `aim2_modeling_dataset_human_adjudicated.csv`
- `aim2_food_matrix_human_adjudication_clean.csv`
- `aim2_msi_food_matrix_ppgr_summary.csv`
- `aim2_food_matrix_category_summary.csv`
- `aim2_food_matrix_annotation_reliability_status.csv`
- `aim2_food_matrix_gee_model_results.csv`
- `aim2_food_matrix_prediction_grid.csv`
- `figures/aim2_high_iauc_rate_by_msi_matrix.png`
- `figures/aim2_selected_model_terms.png`
- `figures/aim2_predicted_high_msi_ppgr_by_matrix.png`

## 解释边界

当前可将 Aim 2 定位为“人工定义的食物基质如何改变同等代谢脆弱性下的 PPGR 表型”。投稿前重点不是重新证明标签来源，而是补足标签一致性、类别合并敏感性和受试者层面稳健性。