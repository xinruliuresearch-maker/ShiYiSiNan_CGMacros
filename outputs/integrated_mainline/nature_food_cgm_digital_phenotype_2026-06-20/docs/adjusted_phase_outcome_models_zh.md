# 调整后的相位-临床结局关联模型

生成脚本：`scripts/run_adjusted_phase_outcome_models.py`

## 模型目的

该分析用于补强主报告中的相位-结局关联证据。主报告已提供未调整的卡方检验和 Kruskal-Wallis 检验；本脚本进一步调整基线 HbA1c、年龄、基线 TIR、研究固定效应和随机分组臂固定效应。

## 全局相位检验

| target | target_label | outcome_type | n | reference_phase | test | statistic | df | p_value | covariates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| y_hba1c_improved_ge_0_5 | HbA1c improvement >=0.5% | binary | 719 | 稳定达标相 | robust_wald_phase_terms | 3.034 | 4 | 0.552 | baseline HbA1c, age, baseline TIR, study fixed effects, randomized arm fixed effects |
| y_tir_improved_ge_5pct | TIR improvement >=5 percentage points | binary | 641 | 稳定达标相 | robust_wald_phase_terms | 5.571 | 4 | 0.234 | baseline HbA1c, age, baseline TIR, study fixed effects, randomized arm fixed effects |
| y_hba1c_change_pct_points | HbA1c change, percentage points | continuous | 719 | 稳定达标相 | robust_wald_phase_terms | 3.083 | 4 | 0.544 | baseline HbA1c, age, baseline TIR, study fixed effects, randomized arm fixed effects |
| y_change_cgm_time_in_range_70_180_pct | TIR change, percentage points | continuous | 641 | 稳定达标相 | robust_wald_phase_terms | 9.155 | 4 | 0.057 | baseline HbA1c, age, baseline TIR, study fixed effects, randomized arm fixed effects |

## 相位效应估计

| target | target_label | outcome_type | effect_scale | phase_label | reference_phase | n | estimate | ci_low | ci_high | p_value | term |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| y_hba1c_improved_ge_0_5 | HbA1c improvement >=0.5% | binary | odds_ratio | 稳定达标相 | 稳定达标相 | 719 | 1.000 | 1.000 | 1.000 |  | reference |
| y_hba1c_improved_ge_0_5 | HbA1c improvement >=0.5% | binary | odds_ratio | 低血糖易感相 | 稳定达标相 | 719 | 1.808 | 0.842 | 3.883 | 0.129 | phase_0 |
| y_hba1c_improved_ge_0_5 | HbA1c improvement >=0.5% | binary | odds_ratio | 昼夜节律紊乱相 | 稳定达标相 | 719 | 1.260 | 0.598 | 2.657 | 0.544 | phase_1 |
| y_hba1c_improved_ge_0_5 | HbA1c improvement >=0.5% | binary | odds_ratio | 高波动震荡相 | 稳定达标相 | 719 | 0.990 | 0.565 | 1.734 | 0.971 | phase_2 |
| y_hba1c_improved_ge_0_5 | HbA1c improvement >=0.5% | binary | odds_ratio | 高血糖持续相 | 稳定达标相 | 719 | 1.440 | 0.662 | 3.136 | 0.358 | phase_3 |
| y_tir_improved_ge_5pct | TIR improvement >=5 percentage points | binary | odds_ratio | 稳定达标相 | 稳定达标相 | 641 | 1.000 | 1.000 | 1.000 |  | reference |
| y_tir_improved_ge_5pct | TIR improvement >=5 percentage points | binary | odds_ratio | 低血糖易感相 | 稳定达标相 | 641 | 1.050 | 0.495 | 2.230 | 0.898 | phase_0 |
| y_tir_improved_ge_5pct | TIR improvement >=5 percentage points | binary | odds_ratio | 昼夜节律紊乱相 | 稳定达标相 | 641 | 0.641 | 0.294 | 1.397 | 0.264 | phase_1 |
| y_tir_improved_ge_5pct | TIR improvement >=5 percentage points | binary | odds_ratio | 高波动震荡相 | 稳定达标相 | 641 | 0.556 | 0.302 | 1.024 | 0.060 | phase_2 |
| y_tir_improved_ge_5pct | TIR improvement >=5 percentage points | binary | odds_ratio | 高血糖持续相 | 稳定达标相 | 641 | 0.506 | 0.215 | 1.189 | 0.118 | phase_3 |
| y_hba1c_change_pct_points | HbA1c change, percentage points | continuous | beta | 稳定达标相 | 稳定达标相 | 719 | 0.000 | 0.000 | 0.000 |  | reference |
| y_hba1c_change_pct_points | HbA1c change, percentage points | continuous | beta | 低血糖易感相 | 稳定达标相 | 719 | -0.089 | -0.298 | 0.121 | 0.408 | phase_0 |
| y_hba1c_change_pct_points | HbA1c change, percentage points | continuous | beta | 昼夜节律紊乱相 | 稳定达标相 | 719 | 0.082 | -0.127 | 0.292 | 0.441 | phase_1 |
| y_hba1c_change_pct_points | HbA1c change, percentage points | continuous | beta | 高波动震荡相 | 稳定达标相 | 719 | 0.067 | -0.058 | 0.192 | 0.293 | phase_2 |
| y_hba1c_change_pct_points | HbA1c change, percentage points | continuous | beta | 高血糖持续相 | 稳定达标相 | 719 | 0.002 | -0.218 | 0.221 | 0.989 | phase_3 |
| y_change_cgm_time_in_range_70_180_pct | TIR change, percentage points | continuous | beta | 稳定达标相 | 稳定达标相 | 641 | 0.000 | 0.000 | 0.000 |  | reference |
| y_change_cgm_time_in_range_70_180_pct | TIR change, percentage points | continuous | beta | 低血糖易感相 | 稳定达标相 | 641 | 0.878 | -2.228 | 3.984 | 0.580 | phase_0 |
| y_change_cgm_time_in_range_70_180_pct | TIR change, percentage points | continuous | beta | 昼夜节律紊乱相 | 稳定达标相 | 641 | -1.041 | -4.019 | 1.937 | 0.493 | phase_1 |
| y_change_cgm_time_in_range_70_180_pct | TIR change, percentage points | continuous | beta | 高波动震荡相 | 稳定达标相 | 641 | -2.005 | -4.051 | 0.041 | 0.055 | phase_2 |
| y_change_cgm_time_in_range_70_180_pct | TIR change, percentage points | continuous | beta | 高血糖持续相 | 稳定达标相 | 641 | 0.517 | -2.719 | 3.753 | 0.754 | phase_3 |

## 图形

- `figures/journal_adjusted_phase_outcomes.png`

## 解释原则

- 二分类结局报告调整 OR；连续结局报告调整 beta。
- 参考相位自动选择为基线 TIR 均值最高的相位，通常对应“稳定达标相”。
- 这些模型支持相图与临床结局存在独立关联，但仍是回顾性二次分析；不能把相位标签解释为已验证的生物学亚型。
