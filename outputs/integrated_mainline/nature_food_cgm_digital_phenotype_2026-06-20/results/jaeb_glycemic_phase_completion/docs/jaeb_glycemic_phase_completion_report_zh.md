# JAEB 血糖动力学相图完成报告

## 完成摘要

本完成包整合了公开 JAEB 糖尿病 RCT/干预研究数据，形成 2144 名受试者的机器学习表、8638 行 harmonized CGM summary，以及 748 名具备基线 CGM 汇总的相图样本。相图识别出 5 类血糖动态相位：稳定达标相 n=234; 高波动震荡相 n=182; 高血糖持续相 n=178; 昼夜节律紊乱相 n=97; 低血糖易感相 n=57。

## 已完成模块

1. 数据清洗与 harmonization：`processed_ml_table.csv`、`cgm_summary_long.csv`。
2. 血糖动力学相图：五个序参量、KMeans 相位、相图坐标和图件。
3. 相位-结局关系：未调整检验、调整模型、全局 Wald 检验。
4. 预测模型：5-fold CV、leave-one-study-out、nested tuning、校准、决策曲线和模型差异 bootstrap。
5. 相图稳健性：150 次 bootstrap，ARI 中位数 0.826（IQR 0.755-0.890），silhouette 中位数 0.268。
6. 异质性治疗响应：相位分层调整风险差和个体化干预框架。

## 主要结果

- 未调整分析中，相位与 HbA1c 改善 >=0.5% 有关联（chi-square p=0.000）。
- 调整后相位主效应整体较弱；TIR 变化的全局 Wald 检验为 p=0.057，可作为趋势而非确认性结论。
- Nested CV 中 HbA1c 改善最佳模型为 C1_clinical / lightgbm，AUROC=0.802。
- Nested CV 中 TIR 改善最佳模型为 C2_clinical_plus_cgm / logistic_ridge，AUROC=0.795。
- LOSO 外部泛化中 HbA1c 改善最佳平均 AUROC=0.727；TIR 改善最佳平均 AUROC=0.754。
- 调整后 HTE 中，低血糖易感相 的治疗获益最高，调整风险差 0.281（95% bootstrap CI 0.105-0.408）。

## 关键解释边界

相图特征对纯预测 AUROC 的增量有限；它的价值主要在机制化低维表征、相位分层治疗响应和可解释干预框架。调整后相位-结局主效应不强，因此不能把相位标签解释为已验证的生物学亚型或临床决策工具。

## 完成包结构

- `figure_source_data/`：所有主图和补充图的 panel-level CSV。
- `tables/`：锁定版数据、模型结果和 manuscript tables。
- `figures/`：现有 PNG 图件副本。
- `docs/`：完成报告、结果初稿、方法摘要和审稿风险说明。
