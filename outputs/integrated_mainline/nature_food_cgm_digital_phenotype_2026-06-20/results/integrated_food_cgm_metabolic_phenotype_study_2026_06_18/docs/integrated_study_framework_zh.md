# 整合研究框架：食品系统暴露、食物基质与 CGM 数字代谢易感性

生成日期：2026-06-18

## 核心判断

现在两条线不能简单拼成一篇“NHANES + CGMacros + JAEB 大杂烩”。更稳、更有投稿潜力的整合方式，是把它们定义为同一项多层证据研究：

**食品系统化学暴露和食物基质如何塑造可由 CGM 捕捉的代谢易感性数字表型。**

这项整合研究应有四层：

1. **Population exposure anchor**：NHANES 中 DEHP oxidative profile 与 MSI/HOMA-IR/HbA1c 相关。
2. **Meal-expression layer**：CGMacros 中 MSI 和食物基质决定 PPGR 脆弱性。
3. **Dynamic digital phenotype layer**：JAEB 中 CGM phase-map 将长期 CGM 状态组织为可复现数字表型，并预测 HbA1c/TIR response。
4. **Bridge cohort layer**：在同一批人中同时测尿/食品塑化剂、食物基质、标准餐 PPGR 和 free-living CGM phase-map，补齐当前无法直接证明的链条。

## 统一科学问题

> Food-system chemical exposures and meal matrices may shape metabolic susceptibility that is expressed acutely as PPGR vulnerability and dynamically as CGM phase-map digital phenotypes.

中文可以写成：

> 食品系统化学暴露与食物基质可能塑造代谢易感性；这种易感性在短时间尺度上表现为餐后血糖反应脆弱性，在长期连续血糖监测中表现为可计算的 CGM 数字表型。

## 当前直接证据

### 1. NHANES：食品系统塑化剂暴露锚定 MSI/代谢易感性

- 10 percentage-point higher oxidative DEHP fraction 与 MSI-core 相关：beta 0.168，95% CI 0.060 to 0.277，q=0.008。
- 同一暴露 contrast 与 HOMA-IR 相关：19.958% difference，95% CI 6.300 to 35.371。
- 与 HbA1c 相关：beta 0.110，95% CI 0.022 to 0.197。
- 总 DEHP 调整后，ILR oxidative-vs-primary 仍与 MSI-core 相关：beta 0.199，95% CI 0.098 to 0.301。

这给出 population-level exposure anchor，但没有 CGM phase 和 PPGR。

### 2. CGMacros：MSI 与食物基质表达为 PPGR 脆弱性

- MSI-core 与 2h log1p iAUC 相关：1.141 (0.658, 1.624)。
- MSI-core 与 peak glucose delta 相关：28.896 (18.814, 38.979)。
- MSI-core 与 high-iAUC meal risk 相关：log-odds 1.344 (0.727, 1.961)。
- Mixed/unknown matrix 相对 protective matrix：log1p iAUC beta 0.616 (0.401, 0.831)；high-iAUC log-odds 0.696 (0.425, 0.966)。
- Subject-held-out model ladder：macro/timing AUC 0.573；MSI + food matrix AUC 0.677。
- Counterfactual meal redesign：候选餐 median predicted risk reduction 0.157。

这给出 meal-expression layer，但没有塑化剂 biomarker，也没有长期 phase-map。

### 3. JAEB/Loop/PSO：CGM phase-map 是可验证数字表型

- JAEB phase-map 样本：748 名；CGM summary rows：8638。
- Bootstrap ARI median 0.826，IQR 0.755-0.890。
- Loop frozen validation phase-map AUROC：HbA1c response 0.758；TIR response 0.827。
- PSO3/4 pooled phase-map AUROC：HbA1c response 0.779；TIR response 0.729。
- 最大 phase-stratified HTE：adjusted RD 0.281。

这给出 dynamic digital phenotype layer，但没有食物基质和塑化剂暴露。

## 断点与补法

最关键的断点不是统计结果不足，而是“同一个人身上没有同时测三类东西”：

1. NHANES 有塑化剂和 MSI/HOMA/HbA1c，但没有 CGM/PPGR。
2. CGMacros 有 CGM meal response 和食物基质，但没有塑化剂 biomarker。
3. JAEB 有强 CGM phase-map 和外部验证，但没有食物基质/塑化剂。

所以主文必须把当前证据写成 **triangulated evidence**，而不是完整 causal chain。真正补齐需要一个 bridge cohort。

## 整合后的 Aims

### Aim 1：定义食品系统暴露相关代谢易感性

数据：NHANES 2013-2018。  
输出：DEHP oxidative profile -> MSI/HOMA-IR/HbA1c。  
角色：population exposure anchor。

### Aim 2：证明代谢易感性在真实餐食中表达为 PPGR 脆弱性

数据：CGMacros。  
输出：MSI-core + food matrix -> PPGR/iAUC/high-risk meal；counterfactual meal redesign。  
角色：meal-expression and modifiable matrix layer。

### Aim 3：用 CGM phase-map 验证动态数字代谢表型

数据：JAEB + Loop + RacialDifferences + PSO3/4。  
输出：phase-map stability、external validation、calibration/fairness、software package。  
角色：dynamic digital phenotype and deployment layer。

### Aim 4：桥接验证

新数据：80-120 人 bridge cohort。  
测量：尿塑化剂、食品/包装 plasticizer panel、标准餐 2x2 matrix challenge、14-28 天 CGM、HbA1c/insulin/HOMA。  
输出：直接测试 exposure -> MSI -> PPGR -> CGM phase/order parameters 的同人群链条。  
角色：让这项整合研究从“多数据集三角证据”升级为“同人群机制/数字表型验证”。

## 建议题目

**Food-system exposures and meal matrices define CGM digital phenotypes of metabolic vulnerability**

备选更克制版本：

**Triangulating food-system exposures, meal matrices and CGM digital phenotypes of metabolic vulnerability across population, meal and trial cohorts**

## 投稿定位

如果没有 Aim 4 bridge cohort，文章应定位为高质量 integrative/triangulation study，适合数字营养、营养代谢信息学或 digital medicine 方向，但冲顶刊风险仍高。

如果完成 Aim 4，整合后才真正像一项完整高水平研究：有食品系统暴露、有真实餐食/标准餐机制、有 CGM 数字表型、有软件化输出和外部验证。

## 本次生成文件

- `tables/integrated_evidence_chain.csv`
- `tables/cross_study_construct_crosswalk.csv`
- `tables/disconnected_points_and_fixes.csv`
- `tables/integrated_aims.csv`
- `tables/integrated_next_tasks.csv`
- `tables/integrated_manuscript_storyboard.csv`
- `figure_source_data/integrated_study_dag_nodes.csv`
- `figure_source_data/integrated_study_dag_edges.csv`
