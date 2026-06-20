# Nature Food 下一阶段执行备忘录

## 主张锁定

本稿不应写成“DEHP 直接导致餐后血糖异常”。更稳妥、更像 Nature Food 的中心主张是：

**塑化剂相关的代谢易感性在人群层面可由 DEHP 氧化代谢谱锚定；在自由生活餐食中，该易感性对应更高 PPGR，并且 PPGR 风险受到人工仲裁食物基质类别的调节，可转化为面向餐食重构的风险降低策略。**

## 已完成的新产物

- `nature_food_cross_dataset_evidence_bridge.csv`：Aim 1 与 Aim 2 的跨数据集证据桥接表。
- `nature_food_readiness_dashboard.csv`：按投稿模块标注 strong/medium 与阻塞缺口。
- `aim3_loso_model_ladder_metrics.csv`：受试者留一的模型阶梯评估。
- `aim3_counterfactual_meal_redesign_candidates.csv`：高 MSI、高 PPGR、低保护食物基质的餐食重构候选。
- `nature_food_next_task_board.csv`：下一阶段任务板。

## Aim 3 初版结果

当前 LOSO 最优模型为 `M4_full_matrix_nutrition`：

- high-iAUC AUC: 0.696
- average precision: 0.426
- Brier score: 0.221
- log1p iAUC RMSE: 2.973

餐食重构候选已筛出 40 条优先记录。下一步应在同一模型框架下生成“原餐 vs 重构餐”的预测差异，而不是只给规则建议。

## 接下来 7 天 P0

1. Aim 2 collapsed matrix：把 6 类人工标签压缩为高保护/中间/低保护三类，重跑 GEE 与模型阶梯。
2. Aim 2 subject leverage：对 MSI-core 和关键食物基质项做 leave-one-subject-out 影响分析。
3. Aim 3 counterfactual delta：用锁定模型估计高 MSI 人群从低保护基质替换到高保护基质的高 iAUC 风险差。
4. Figure source data：生成 Figure 1-4 每个 panel 的 CSV。
5. Results skeleton：用真实数值写 Nature Food Results 初稿，不写泛泛背景。

## 接下来 30 天 P1

1. 人工标签 codebook 定稿，补充双评不一致和少数类复核。
2. 选出 12-16 个等碳水/等能量餐食原型，用于 INFOGEST 或小型 CGM pilot。
3. 准备投稿用限制声明：NHANES 与 CGMacros 是三角验证，不声称个体层面 DEHP 暴露直接预测 CGM。
4. 完成 cover letter 的 novelty paragraph：塑化剂暴露、代谢易感性、自由生活 PPGR 与食物基质重构的跨数据证据链。
