# Nature Food 投稿目标：下一阶段任务设计

生成日期：2026-06-18

## 投稿定位判断

Nature Food 的核心读者不是单纯的糖尿病预测或 CGM 算法读者，而是关心 food systems、food processing、food chemistry、human nutrition 和 public health nutrition 的读者。官方 scope 明确覆盖 Food Chemistry、Food Processing、Food Safety and Quality、Food Systems、Human Nutrition、Information Technology 和 Public Health Nutrition。因此，这篇文章必须把主轴写成“食品系统暴露和餐食基质如何塑造可由 CGM 捕捉的代谢易感性”，而不是“多个公开数据集上的代谢 ML benchmark”。

文章类型建议分两种情形：

1. **没有 Aim 4 新队列时**：更接近 Nature Food 的 **Analysis**，即基于已有数据的新分析，必须给出对 broad audience 有意义的新结论。主张应克制为 triangulated evidence。
2. **完成 Aim 4 bridge cohort 时**：可以冲击 **Article**，因为它会形成“人群暴露锚点 + 真实餐食表达 + CGM 数字表型 + 同人群桥接验证”的完整研究。Nature Food Article/Analysis 主文都很紧，约 3,000 words、摘要约 150 words、主文最多约 6 个展示项，所以后续任务必须服务一条主线和 5-6 张主图。

## 一句话主线

食品系统化学暴露和餐食基质共同塑造代谢易感性；这种易感性在人群层面表现为 MSI/HOMA-IR/HbA1c，在餐食层面表现为 PPGR vulnerability，在连续血糖监测中表现为可迁移的 CGM digital phenotype。

## P0：立刻完成，用现有数据把稿件抬到可预投稿水平

### P0-1：锁定 Nature Food 版 claim hierarchy

目标：把所有结果按“food-system exposure -> meal matrix expression -> CGM digital phenotype -> bridge validation”排序。

交付物：
- 150-word Nature Food abstract。
- 6-display-item 主图清单。
- 一页式 claim map：每个 claim 标注 direct evidence、triangulated inference 或 bridge-needed。

验收标准：
- 主文不再以 NHANES/CGMacros/JAEB 数据集顺序叙事，而以食品系统机制链叙事。
- 明确写出当前不能声称的内容：现有数据不能证明同一个人中 plasticizer exposure 直接导致 PPGR 或 phase membership。

### P0-2：Aim 1 从“尿代谢物相关性”升级为 food-system exposure anchor

目标：把 NHANES 结果从环境流行病学相关性推进到食品系统暴露问题。

任务：
- 完成 NHANES 2013-2018 survey-weighted 主模型、周期复制和敏感性表的最终冻结。
- 增加食品类别、加工/包装 proxy 与 plasticizer burden 的分析矩阵：24h recall food code、UPF/processing proxy、包装/外食/即食相关变量，作为 food-system exposure context。
- 建立 external food plasticizer measurement panel：从食品塑化剂测量文献或可用数据库中整理食品类别、包装/接触材料、DEHP/非 DEHP plasticizer 浓度范围，并映射到 NHANES/CGMacros 食物类别。
- 将 DEHP oxidative-vs-primary balance 明确定位为 exposure-metabolism composition，不把它写成单一污染物剂量。

交付物：
- `Aim1_food_system_exposure_matrix.csv`
- `Aim1_NHANES_final_survey_models.csv`
- `Aim1_cycle_replication_and_sensitivity.xlsx`
- Figure 2 source data：DEHP oxidative profile -> MSI/HOMA-IR/HbA1c；food category/processing/packaging -> burden。

验收标准：
- 结果能回答“哪些食品系统情境与 plasticizer burden 相关”，而不是只回答“尿 DEHP 和 HbA1c 是否相关”。

### P0-3：Aim 2 把 food matrix 做成可防守的营养机制层

目标：让 CGMacros 不只是 PPGR 预测，而是说明餐食基质如何调节易感性的表达。

任务：
- 锁定 collapsed food matrix 三分类：高保护、中间、低保护。
- 输出双人/盲法或规则化 adjudication protocol，说明人工标签不是随意主观判断。
- 对 MSI-core、matrix class 和关键交互项做 leave-one-subject-out、influence diagnostics 和 bootstrap CI。
- 用等能量/等碳水 counterfactual 重新定义 meal redesign：每个替换都必须说明宏量营养素匹配、matrix 改变和预期 PPGR 风险差。
- 检查 CGMacros 原始/free-living CGM 是否可被 locked JAEB phase-map 赋值，若可行，把 40 名受试者映射到 phase/order parameter；若不可行，形成兼容性报告。

交付物：
- `Aim2_matrix_adjudication_protocol.md`
- `Aim2_loso_and_influence_report.csv`
- `Aim2_counterfactual_isocaloric_redesign.csv`
- `Aim2_CGMacros_phase_map_feasibility.csv`

验收标准：
- Aim 2 能支撑“food matrix is a modifiable expression layer”，而不仅是“模型里多放了一个食物标签”。

### P0-4：Aim 3 改写成 CGM digital phenotype，不做普通 ML benchmark

目标：把 JAEB/Loop/PSO 的贡献写成可复现 CGM 表型系统，而不是预测比赛。

任务：
- 保持 frozen phase-map：不得因新数据重新调参。
- 主结果从 AUROC 排名改为 phenotype stability、external transport、calibration/fairness audit、phase-guided workflow。
- 校准仍弱的输出定位为 ranking/phenotype，不输出 clinical absolute risk。
- 软件包补齐 schema、toy data、unit tests、figure reproduction script、environment lock。

交付物：
- `phase_map_algorithm_card.md`
- `phase_map_software_release_v0.1`
- `Aim3_external_validation_calibration_fairness_tables.csv`
- Figure 4 source data：phase map、external validation、calibration/fairness。

验收标准：
- 审稿人看到的是“CGM digital phenotype for food-system metabolic vulnerability”，不是“又一个糖尿病预测模型”。

### P0-5：重画 Nature Food 主图，压到 5 张主图 + 1 张设计图

建议主文 6 display items：

1. **Figure 1：食品系统暴露-餐食基质-CGM 数字表型证据架构**  
   DAG/graph，标注 direct evidence、triangulated inference 和 bridge-needed edges。

2. **Figure 2：NHANES population exposure anchor**  
   DEHP oxidative profile 与 MSI/HOMA-IR/HbA1c；食品类别/加工/包装 proxy 与 plasticizer burden。

3. **Figure 3：CGMacros meal-expression layer**  
   MSI-core + matrix class -> PPGR/iAUC/high-iAUC；collapsed matrix 和 subject leverage。

4. **Figure 4：Meal redesign counterfactual and matrix mechanism**  
   等碳水/等能量替换、风险差、体外消化/葡萄糖释放机制占位。

5. **Figure 5：CGM digital phenotype validation**  
   JAEB phase-map stability、Loop/PSO external validation、calibration/fairness audit。

6. **Figure 6：Bridge cohort protocol and translational workflow**  
   尿/食品 plasticizer panel + 标准餐 + 14-28 天 CGM + integrated phenotype report。

交付物：
- 每个 panel 的 source CSV。
- 每张图一句 message 和一句 limitation。
- 主图 caption 草稿。

验收标准：
- 每张图都服务主线，不出现“为了展示已有结果而展示”的图。

## P1：Nature Food 级别的关键新增工作

### P1-1：Bridge cohort IRB-ready protocol

目标：直接补齐同人群链条。

设计：
- 80-120 人，覆盖 normal glycaemia、prediabetes、treated/non-insulin T2D。
- 重复晨尿 plasticizer panel。
- 目标食品/包装 plasticizer panel。
- 标准餐 2x2 matrix challenge：high/low matrix protection x higher/lower measured food-contact burden，等能量/等碳水。
- 14-28 天 CGM，HbA1c、fasting glucose、insulin、HOMA。

主要终点：
- exposure -> MSI-core / HOMA / HbA1c。
- matrix protection -> 2h iAUC / peak delta / high-iAUC probability。
- exposure/MSI/PPGR -> CGM phase/order parameters。

交付物：
- IRB protocol。
- Statistical analysis plan。
- Meal SOP。
- Lab assay SOP。
- Power/precision justification。

验收标准：
- 这个 cohort 能把文章从 “triangulated analysis” 升级为 “integrated Article”。

### P1-2：标准餐与体外机制

目标：让 meal matrix 不是黑箱标签。

任务：
- 设计 4 类标准餐：高保护低接触、高保护高接触、低保护低接触、低保护高接触。
- 每类匹配碳水、能量和尽量匹配脂肪/蛋白。
- 做体外消化/葡萄糖释放曲线。
- 同步测食品和接触材料中的 plasticizer panel。

交付物：
- `standard_meal_menu_and_matching_table.csv`
- `in_vitro_glucose_release_curves.csv`
- `food_contact_plasticizer_assay_results.csv`

验收标准：
- Figure 4 能从模型 counterfactual 升级为“可验证机制和可转化 meal redesign”。

### P1-3：Integrated phenotype software package

目标：输出一个可复现的软件化表型系统。

模块：
- MSI calculator。
- Meal matrix classifier。
- PPGR high-risk estimator。
- Locked CGM phase-map assignment。
- Calibration/ranking report。
- Participant-level integrated phenotype report。

交付物：
- versioned package。
- schema。
- toy data。
- unit tests。
- reproducible figures。
- environment lock。

验收标准：
- 软件不是补充材料装饰，而是整合研究的 deployment layer。

## P2：投稿前打磨与预投稿

任务：
- 写 150-word abstract、3,000-word main text 和 6 figure legends。
- 将 Methods 放到可复现层级，主文只保留核心设计和估计量。
- 写 presubmission enquiry：强调 food systems + human nutrition + information technology 的交叉价值。
- 准备 reviewer risk memo：逐条回应“数据集不一致”“暴露不是同人群”“人工食物标签”“校准不足”“CGMacros n=40”。

交付物：
- `NatureFood_presubmission_enquiry.docx`
- `NatureFood_main_text_v0.1.docx`
- `Reviewer_risk_response_memo.md`
- `Reporting_and_reproducibility_checklist.md`

## 立即执行顺序

1. 先做 **P0-1 claim hierarchy** 和 **P0-5 figure spine**，决定文章骨架。
2. 然后做 **P0-2 Aim 1 food-system exposure matrix**，这是 Nature Food fit 的关键。
3. 同步做 **P0-3 CGMacros phase feasibility**，把 Aim 2 和 Aim 3 接起来。
4. 再做 **P1-1 bridge cohort protocol**，这是高水平投稿的真正增量。
5. 最后写 presubmission enquiry，先探编辑口风。

## 最重要的决策

如果 3 个月内不能启动 Aim 4，建议投稿类型定位为 **Analysis**，标题和主张都强调 triangulation。  
如果可以启动 Aim 4 并拿到标准餐/CGM pilot 数据，才建议按 **Article** 冲击 Nature Food。

## 官方依据

- Nature Food aims and scope: https://www.nature.com/natfood/aims
- Nature Food submission guidelines: https://www.nature.com/natfood/submission-guidelines
