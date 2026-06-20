# Nature Food P0 稳健性与餐食重构结果

## 已完成

- 三类食物基质敏感性：保护型 whole-food/low-carb、中间 mixed/unknown、快速消化/液体碳水。
- 受试者留一影响分析：检验 MSI-core 与 collapsed matrix 项是否由单个受试者驱动。
- 餐食重构预测差：把候选高风险餐食的食物基质替换为 fiber-rich/whole-food matrix，估计 high-iAUC 风险变化。

## 三类食物基质关键模型项

| outcome         | term                                                    | estimate_CI            | p_value  | n    | subjects |
| --------------- | ------------------------------------------------------- | ---------------------- | -------- | ---- | -------- |
| log1p_iauc_2h   | C(matrix_collapsed3)[T.mixed_buffered_or_unknown]       | 0.616 (0.401, 0.831)   | 1.96e-08 | 1498 | 40       |
| log1p_iauc_2h   | C(matrix_collapsed3)[T.rapid_digestible_or_liquid_carb] | -0.104 (-0.493, 0.285) | 0.6015   | 1498 | 40       |
| peak_delta_2h_w | C(matrix_collapsed3)[T.mixed_buffered_or_unknown]       | 10.672 (6.261, 15.083) | 2.12e-06 | 1498 | 40       |
| peak_delta_2h_w | C(matrix_collapsed3)[T.rapid_digestible_or_liquid_carb] | -0.991 (-6.761, 4.779) | 0.7365   | 1498 | 40       |
| high_iauc_2h    | C(matrix_collapsed3)[T.mixed_buffered_or_unknown]       | 0.696 (0.425, 0.966)   | 4.47e-07 | 1498 | 40       |
| high_iauc_2h    | C(matrix_collapsed3)[T.rapid_digestible_or_liquid_carb] | -0.205 (-0.641, 0.231) | 0.3557   | 1498 | 40       |

## 受试者留一稳定性

| term                                                    | min_estimate | median_estimate | max_estimate | positive_leaveouts | leaveouts | positive_leaveout_rate |
| ------------------------------------------------------- | ------------ | --------------- | ------------ | ------------------ | --------- | ---------------------- |
| C(matrix_collapsed3)[T.mixed_buffered_or_unknown]       | 0.6499       | 0.6933          | 0.7494       | 40                 | 40        | 1                      |
| C(matrix_collapsed3)[T.rapid_digestible_or_liquid_carb] | -0.4001      | -0.2008         | -0.1036      | 0                  | 40        | 0                      |
| msi_core                                                | 1.248        | 1.384           | 1.469        | 40                 | 40        | 1                      |

## 餐食重构预测

- 候选餐食数: 40
- 中位 predicted high-iAUC 风险差: -0.157
- 负值表示重构后预测风险降低；该结果目前是模型内反事实，需要后续用等碳水/等能量餐食原型验证。
