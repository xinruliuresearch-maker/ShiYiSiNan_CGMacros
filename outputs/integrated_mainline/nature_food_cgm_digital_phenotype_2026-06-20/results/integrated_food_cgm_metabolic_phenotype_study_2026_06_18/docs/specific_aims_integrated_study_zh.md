# Specific Aims：食品系统暴露、餐食基质与 CGM 数字代谢易感性

## 总体问题

目前两条研究线的关键不是“能否合并”，而是如何把它们统一到一个可检验的科学命题中：食品系统暴露和餐食基质如何塑造代谢易感性，并且这种易感性如何在急性餐后血糖反应和长期 CGM 数字表型中被捕捉。

## 中心假设

食品系统塑化剂暴露与食物基质共同塑造代谢易感性。该易感性在人群层面表现为 MSI/HOMA-IR/HbA1c 异常，在餐食层面表现为更高 PPGR/iAUC/high-iAUC risk，在连续监测层面表现为可复现、可迁移的 CGM phase-map 数字表型。

## Aim 1：定义食品系统暴露相关代谢易感性

数据：NHANES 2013-2018。

核心问题：DEHP oxidative profile 是否与 MSI-core、HOMA-IR 和 HbA1c 共同指向同一类人群代谢易感性？

当前证据：DEHP oxidative fraction 每升高 10 个百分点，与 MSI-core 升高相关，beta 0.168，95% CI 0.060 to 0.277，q=0.008；与 HOMA-IR 的差异为 19.958%；与 HbA1c 的 beta 为 0.110。总 DEHP 调整后，ILR oxidative-vs-primary 仍与 MSI-core 相关，beta 0.199。

角色：population exposure anchor。这个 Aim 不能单独证明 CGM 或 PPGR 链条，但能把研究锚定在食品系统化学暴露和人群代谢易感性上。

完成标准：保留复杂抽样设计、固定协变量、LOD/肌酐/尿稀释/糖尿病诊断或用药排除敏感性、周期复制和暴露组成模型；主文只声称 observational exposure anchor。

## Aim 2：证明代谢易感性在真实餐食中表达为 PPGR 脆弱性

数据：CGMacros。

核心问题：MSI-core 和 food matrix 是否共同决定真实餐食后的 PPGR/iAUC/high-risk meal？

当前证据：MSI-core 与 2h log1p iAUC 相关，1.141 (0.658, 1.624)；与 peak glucose delta 相关，28.896 (18.814, 38.979)；与 high-iAUC risk 相关，1.344 (0.727, 1.961)。Food matrix collapsed class 在宏量营养素和进餐时间之外仍保留信号。Subject-held-out high-iAUC AUC 从 0.573 提升到 0.677，counterfactual meal redesign 的 median predicted risk reduction 为 0.157。

角色：meal-expression and modifiable matrix layer。这个 Aim 把 Aim 1 的“代谢易感性”转译成真实餐食后的 CGM 反应，并提供可干预的 food matrix lever。

完成标准：保留 GEE/subject clustering、collapsed matrix、model ladder、leave-one-subject-out leverage、counterfactual delta；明确 counterfactual 是模型估计，不等同于干预证据。

## Aim 3：用 CGM phase-map 验证动态数字代谢表型

数据：JAEB + Loop + RacialDifferences + PSO3/4。

核心问题：能否把 CGM 总结为稳定、可迁移、可审计的数字表型，并用于 HbA1c/TIR response ranking？

当前证据：JAEB phase-map 包含 748 名参与者、8638 条 CGM summary rows；bootstrap ARI median 0.826。Loop frozen validation 中 phase-map HbA1c AUROC 为 0.758，TIR AUROC 为 0.827。PSO3/4 pooled phase-map HbA1c AUROC 为 0.779，TIR AUROC 为 0.729。

角色：dynamic digital phenotype and deployment layer。这个 Aim 不是重复普通 ML benchmark，而是证明 CGM phase-map 可以作为“代谢易感性”的长期数字表型语言。

完成标准：固定算法、外部验证、calibration/fairness audit、minimum-n subgroup rule、software package；如果校准不足，输出定位为 phenotype/ranking，而非绝对风险。

## Aim 4：桥接验证

新数据：80-120 人 bridge cohort。

核心问题：能否在同一批人中直接测试 exposure -> MSI -> PPGR -> CGM phase/order parameters 的链条？

设计：重复尿塑化剂测量、食品/包装 plasticizer panel、标准餐 2x2 matrix challenge、14-28 天 CGM、HbA1c/insulin/HOMA。2x2 标准餐建议为 high vs low matrix protection 交叉 higher vs lower measured food-contact burden，并匹配碳水和能量。

角色：把当前的多数据集 triangulated evidence 升级为同人群机制/数字表型验证。

完成标准：同人群 construct crosswalk、标准餐验证 CGMacros matrix result、locked phase-map 在 nutrition/food-exposure cohort 中稳定赋值、整合软件报告同时输出 MSI、meal-risk 和 CGM phase-map phenotype。

## 整体贡献边界

Aim 1-3 是现有数据可以完成的强三角证据；Aim 4 是冲击高水平综合期刊所需的关键增量。没有 Aim 4，主张必须克制为 triangulated digital-metabolic phenotype study；完成 Aim 4 后，研究才可以主张同人群 exposure-meal-CGM phenotype chain。
