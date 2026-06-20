# Nature Food 下一阶段任务设计：从 P0 证据包到可预投稿/可投稿稿件

生成日期：2026-06-18

## 当前判断

P0 已经把现有数据整理成 Nature Food 叙事结构：food-system exposure context、DEHP oxidative profile、CGMacros food matrix/PPGR、CGM phase-map digital phenotype 和 bridge cohort 缺口。下一阶段不应继续横向堆结果，而应围绕两个目标推进：

1. **短线目标：形成可预投稿的 Analysis 版本。**  
   这个版本必须把当前证据定位为 triangulated evidence，不能声称同人群因果链。

2. **长线目标：启动 Aim 4，让文章具备 Article 级别的新增证据。**  
   Article 版本需要同一批人中的尿/食品 plasticizer panel、标准餐 PPGR 和 14-28 天 CGM phase-map。

## Nature Food 版主张边界

### 可以主张

- 食品系统来源 proxy 与 DEHP oxidative profile/代谢易感性存在人群锚点。
- MSI-core 和 food matrix 在真实餐食中共同组织 PPGR vulnerability。
- CGM phase-map 是可复现、可迁移的长期数字表型语言。
- 现有证据支持一条多数据集、多时间尺度的 triangulated evidence chain。

### 不能主张

- 不能说塑化剂暴露在同一个人身上直接导致 PPGR 或 CGM phase membership。
- 不能把 food plasticizer sampling frame 写成实测食品浓度结果。
- 不能把 CGMacros phase assignment 写成已验证的临床 phase 分类。
- 不能把 counterfactual meal redesign 写成干预疗效。

## 接下来 6 周的核心任务

### Week 1：锁定投稿形态和主图骨架

任务：
- 决定短线稿件按 Nature Food **Analysis** 预投稿，还是等 Aim 4 pilot 后按 **Article** 预投稿。
- 完成 150-word abstract、presubmission title、six-display-item figure spine。
- 把所有 claim 标注为 direct、triangulated、model-based 或 bridge-needed。

交付物：
- `NatureFood_presubmission_enquiry_v0.1.md`
- `NatureFood_150_word_abstract_v0.1.md`
- `NatureFood_figure_spine_v0.1.csv`

验收标准：
- 编辑能在第一页看到 food systems + human nutrition + information technology 的适配点。

### Week 2：重画 6 张主图

任务：
- 从 P0 source map 生成 Figure 1-6 初版。
- 每张图必须有一句 message、一句 limitation 和可追溯 source CSV。
- Figure 1 必须明确 direct evidence 与 bridge-needed edges，避免拼盘感。

交付物：
- `figures/Figure1_integrated_architecture.*`
- `figures/Figure2_population_exposure_anchor.*`
- `figures/Figure3_meal_expression_layer.*`
- `figures/Figure4_meal_redesign_phase_compatibility.*`
- `figures/Figure5_cgm_digital_phenotype_validation.*`
- `figures/Figure6_bridge_cohort_workflow.*`
- `figure_legends/NatureFood_figure_legends_v0.1.md`

验收标准：
- 不看正文，只看 6 张图也能读出完整故事。

### Week 3：Aim 1 food-system exposure anchor 加固

任务：
- 从 NHANES source-oriented results 中筛出可进主文/Extended Data 的结果。
- 把 source proxy、DEHP oxidative profile、MSI/HOMA-IR/HbA1c 三层结果连成 Figure 2。
- 明确 food plasticizer measurement panel 的状态：当前是 planned panel/sampling frame，不是实测结果。
- 如果要增强 Nature Food fit，启动文献级 food plasticizer measurement panel，记录真实来源、样本、浓度单位和食品/包装类别。

交付物：
- `Aim1_source_proxy_to_DEHP_and_metabolic_anchor.csv`
- `Aim1_food_plasticizer_panel_literature_extraction_schema.csv`
- `Aim1_claim_guardrails.md`

验收标准：
- Aim 1 能回答“食品系统情境为何相关”，而不是只回答“尿 DEHP 是否相关”。

### Week 4：Aim 2 与 Aim 3 的桥接分析

任务：
- 将 CGMacros phase-map assignment 与 MSI-core、PPGR、food matrix 合并。
- 因 CGMacros 37/40 为 stable-in-range，主分析不应强做多分类 phase 比较；优先用 phase order parameters/assignment distance 做连续桥接。
- 检验 MSI-core、PPGR/iAUC、food matrix 与 glycaemic burden、instability、resilience proxy 的关系。
- 输出 “CGMacros phase compatibility audit”，定位为 transport feasibility。

交付物：
- `Aim2_Aim3_CGMacros_phase_bridge_models.csv`
- `Aim2_Aim3_phase_bridge_guardrails.md`
- `Figure4_phase_compatibility_source_data.csv`

验收标准：
- 能把 Aim 2 的 meal-response 语言与 Aim 3 的 phase-map 语言接起来，但不声称临床 phase validation。

### Week 5：软件复现包从 phase-map 扩展到 integrated phenotype

任务：
- 在现有 phase-map package 基础上补 MSI calculator、meal matrix schema、meal-risk output schema。
- 增加 toy participant，输出一份 integrated phenotype report。
- 保留单元测试和 environment lock。

交付物：
- `integrated_food_cgm_phenotype_v0.1/`
- `schemas/integrated_input_schema.csv`
- `toy_data/toy_integrated_input.csv`
- `tests/test_integrated_package.py`

验收标准：
- 一个干净用户能从 toy data 生成 MSI、meal-risk 和 CGM phase-map 输出。

### Week 6：预投稿材料和审稿风险预案

任务：
- 写 Nature Food presubmission enquiry。
- 写 reviewer risk memo 的逐条回应。
- 准备 Analysis 版 manuscript skeleton。
- 同时完成 Article 版 Aim 4 pilot protocol 摘要，告诉编辑这条研究线如何升级。

交付物：
- `NatureFood_presubmission_enquiry_v1.0.md`
- `NatureFood_analysis_manuscript_skeleton_v0.1.md`
- `Reviewer_risk_response_memo_v1.0.md`
- `Aim4_bridge_cohort_pilot_synopsis.md`

验收标准：
- 即使编辑认为现在不够 Article，也能清楚看到 Analysis 版本的贡献和 Article 版本的升级路径。

## 关键新增数据任务：Aim 4

Aim 4 是 Article 版本的核心，不应等到所有 dry work 完成才启动。

### Aim 4A：IRB-ready protocol

设计 80-120 人 bridge cohort，覆盖 normal glycaemia、prediabetes、treated/non-insulin T2D。

测量：
- 重复晨尿 plasticizer panel。
- 食品/包装 plasticizer panel。
- 标准餐 2x2 matrix challenge。
- 14-28 天 CGM。
- HbA1c、fasting glucose、insulin、HOMA。

### Aim 4B：2x2 标准餐挑战

设计：
- high matrix protection / low food-contact burden。
- high matrix protection / higher food-contact burden。
- low matrix protection / low food-contact burden。
- low matrix protection / higher food-contact burden。

要求：
- 等碳水、等能量。
- 记录物理基质、加工、包装/加热接触。
- 体外消化/葡萄糖释放作为机制补充。

### Aim 4C：可行性 pilot

建议先做 20-30 人 pilot，目标不是完全证明效应，而是确认：
- 样本采集可行。
- 标准餐依从性可行。
- CGM 数据质量可行。
- plasticizer panel 有可测差异。
- PPGR 和 phase/order parameters 可连接。

## 决策门槛

### 走 Analysis 预投稿

满足以下条件即可：
- 6 张主图初版完成。
- P0 guardrails 写入摘要、主文和 Figure 1。
- CGMacros phase compatibility 审慎呈现。
- presubmission enquiry 准备完成。

### 走 Article 预投稿

至少需要：
- Aim 4 pilot 启动或已完成核心可行性数据。
- 食品/包装 plasticizer panel 有实测结果。
- 标准餐 PPGR 有初步 human validation。
- integrated phenotype software package 可运行。

## 立即优先级

1. **先做 Figure 1-6 初版。**  
   主图会立刻暴露故事是否仍然像拼盘。

2. **马上做 Aim2-Aim3 bridge analysis。**  
   CGMacros 已能分配 frozen phase-map，下一步要把 phase order parameters 与 MSI/PPGR/food matrix 接起来。

3. **并行写 presubmission enquiry。**  
   不等所有图完美，先形成编辑可读的一页 pitch。

4. **启动 Aim 4 pilot 的 IRB/SOP。**  
   这是 Nature Food Article 级别的真正增量。

## Go/No-Go

- 如果 2 周内主图不能形成清晰单线故事，应先降级到营养/数字健康方向期刊，而不是硬投 Nature Food。
- 如果 6 周内 Aim 4 pilot 无法启动，Nature Food 只能按 Analysis 版本尝试。
- 如果食品/包装实测 panel 能启动，并且 20-30 人 pilot 可行，继续按 Article 路线推进。
