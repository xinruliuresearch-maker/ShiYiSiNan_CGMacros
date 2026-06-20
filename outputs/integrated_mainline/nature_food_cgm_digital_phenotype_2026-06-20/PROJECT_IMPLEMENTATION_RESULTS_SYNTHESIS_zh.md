# 项目实现步骤、当前结果与研究价值总述

Date: 2026-06-20

## 一句话概括

本项目从 CGMacros 餐食级连续血糖反应出发，逐步扩展到 NHANES 食品系统塑化剂暴露锚点、CGMacros 餐食基质与 PPGR 脆弱性、JAEB/Loop/PSO CGM phase-map 数字表型验证，最终形成一个以 Nature Food 为目标的“食品系统暴露 - 餐食基质 - 动态数字代谢表型”整合研究。

当前最稳妥的投稿形态是 Nature Food **Analysis**：用多数据集、多时间尺度、多测量层的 triangulated evidence 支撑一个食品系统与代谢易感性相关的研究框架。Nature Food **Article** 级别主张需要 Aim 4 同人群桥接队列完成后再升级。

## 核心研究问题

本项目回答的不是“能否用机器学习预测血糖”这个普通问题，而是：

**食品系统中的塑化剂暴露背景和餐食基质结构，是否会在易感人群中表现为可由真实餐食 PPGR 和连续 CGM phase-map 捕捉的动态代谢脆弱性？**

这个问题被拆成四个互相连接的层次：

1. **人群暴露锚点**：NHANES 中 DEHP oxidative profile 与 MSI/HOMA-IR/HbA1c 是否相关。
2. **餐食表达层**：CGMacros 中 MSI-core 与 food matrix 是否共同组织真实餐食 PPGR/iAUC 脆弱性。
3. **动态数字表型层**：JAEB/Loop/PSO 中 CGM phase-map 是否能作为稳定、可迁移的 digital metabolic phenotype。
4. **同人群桥接层**：未来 Aim 4 是否能直接测试 exposure -> MSI -> PPGR -> CGM order parameters 的链条。

## 项目总体实现路径

### Step 1. 项目组织与数据治理

目标：把多个分散分析结果整理成可导航、可复现、可投稿的研究项目。

实现：

- 建立 `00_PROJECT_ORGANIZATION/` 项目导航层。
- 生成文件清单、目录体积摘要、大文件登记和运行脚本地图。
- 将当前 Nature Food / CGM digital phenotype 工作归档到：
  `outputs/integrated_mainline/nature_food_cgm_digital_phenotype_2026-06-20/`
- 原始外部数据约 4GB，没有直接推入 Git；以 `data_exclusion_manifest.csv` 记录排除清单。

当前结果：

- 当前发布包包含 445 个文件，约 19.85 MB；`package_file_manifest.csv` 记录 444 个内容文件，排除了 manifest 自身。
- 仓库通过 Git LFS 管理 CSV、PNG、PDF 等较大或二进制文件。
- 根 README 和 Key Outputs Index 已经指向最新 Nature Food / CGM 包。

### Step 2. CGMacros 餐食级数据构建

目标：从 CGMacros 原始餐食和 CGM 信息中构建可建模的 meal-level PPGR 数据集。

实现：

- 检查原始数据结构。
- 构建餐食级数据集，包括餐食时间、碳水、纤维、宏量营养素、血糖峰值、iAUC 和高风险餐食标签。
- 建立清洗报告、数据字典和数据清单。

产出：

- 餐食建模数据。
- PPGR/iAUC 结局变量。
- 后续 MSI、food matrix、counterfactual redesign 的基础数据。

意义：

这一步把 CGMacros 从普通营养数据集转换成真实餐食代谢反应平台，使后续研究可以讨论“餐食结构如何表达代谢易感性”。

### Step 3. 基线模型、稳健性和反事实餐食替换

目标：建立 PPGR 的可预测性、模型稳定性和可解释的 meal redesign 方向。

实现：

- 训练 baseline/clean models。
- 做 ablation、bootstrap CI、paired delta bootstrap、subgroup analysis、error analysis、calibration。
- 构建 counterfactual meal substitution 框架。

产出：

- 模型性能表。
- 校准图、决策曲线、个体化替换表。
- 用于后续 Nature Food Figure 4 的 meal redesign 证据。

意义：

这一步把“预测”转化为“可改变的餐食基质假设”：不是只报告模型 AUC，而是提出等能量/等碳水条件下，餐食基质重构可能降低高 iAUC 风险。

### Step 4. MSI-core 代谢易感性指标构建

目标：构建一个跨数据集可解释的 metabolic susceptibility index。

实现：

- 从基线代谢指标、血糖相关变量和人体代谢状态中提取 MSI-core。
- 在 CGMacros 中将 MSI-core 与 PPGR/iAUC、meal matrix 一起建模。
- 在 NHANES 中将 MSI/HOMA/HbA1c 作为人群代谢易感性锚点。

产出：

- MSI-core 变量。
- CGMacros PPGR 模型中的 MSI-core 效应。
- NHANES 暴露锚点中的 MSI/HOMA/HbA1c 结果。

意义：

MSI-core 是整篇研究的“中间语言”：它连接人群暴露、餐食 PPGR 和长期 CGM 动态表型。

### Step 5. Aim 1：NHANES 食品系统暴露锚点

目标：用 NHANES 2013-2018 建立 population exposure anchor。

实现：

- 使用复杂抽样设计重新分析 NHANES。
- 固定协变量集：age、sex、race/ethnicity、education、PIR、energy intake、smoking、alcohol、physical activity、urinary creatinine、cycle。
- 考虑 LOD、肌酐、尿稀释、糖尿病诊断/用药排除敏感性。
- 分周期复制：2013-2014、2015-2016、2017-2018。
- 在总 DEHP 调整后检验 oxidative-vs-primary balance。
- 增加 food-system source proxy matrix。

当前结果：

- `Aim1_source_proxy_to_DEHP_and_metabolic_anchor.csv`：64 行，23 列。
- `p0_aim1_food_system_exposure_matrix.csv`：64 行，21 列。
- `p0_food_plasticizer_measurement_panel.csv`：12 个测量 analyte 条目。
- `p0_food_plasticizer_sampling_frame_96.csv`：96 个未来食品/包装/contact sampling frame 条目。
- `Aim1_food_plasticizer_panel_literature_extraction_schema.csv`：13 个文献抽取字段。

价值：

Aim 1 让研究不只是 CGMacros 内部餐食建模，而是接入食品系统暴露问题。它提供的是“人群暴露锚点”，不是同人群因果证明。

关键边界：

- 可以说 DEHP oxidative profile 与代谢易感性在人群层面相关。
- 不可以说食品包装塑化剂已经在同一个 CGMacros 个体中直接导致 PPGR 或 CGM phase membership。

### Step 6. Aim 2：食物基质与 PPGR 脆弱性

目标：证明代谢易感性会在真实餐食中表达为 PPGR vulnerability，并且这种表达受 food matrix 调节。

实现：

- 对餐食进行人工 food matrix 标注。
- 将 6 类标签压缩为 3 类：
  high-protection / mixed-buffered / low-protection or rapid-digestible。
- 用 GEE 和模型阶梯分析 MSI-core、food matrix 与 iAUC/high-risk meal。
- 做 leave-one-subject-out subject leverage 分析。
- 生成 counterfactual meal redesign 风险差。

当前结果：

- `p0_aim2_six_class_matrix_summary.csv`：6 类 matrix summary。
- `p0_aim2_matrix_defense_summary.csv`：5 项 matrix 防守证据。
- `p0_aim2_subject_leverage_summary.csv`：3 个关键项的 leave-one-subject-out 稳定性。
- MSI-core 系数在 40/40 leave-one-subject-out 模型中为正。
- mixed/unknown matrix 系数在 40/40 leave-one-subject-out 模型中为正。
- counterfactual meal redesign 的 median predicted high-iAUC risk reduction 为 0.157。

价值：

Aim 2 是项目从“暴露与代谢指标相关”走向“真实餐食中可观察、可干预表达”的关键。它把 metabolic susceptibility 具体落到餐食层面的 PPGR/iAUC。

关键边界：

- counterfactual redesign 是模型估计和干预假设。
- 不能写成已经证明的临床干预效果。

### Step 7. Aim 3：CGM phase-map 动态数字代谢表型

目标：把 CGM 从单一 TIR/平均血糖指标提升为可迁移的动态数字表型。

实现：

- 基于 JAEB 数据构建 frozen phase-map。
- 做 bootstrap stability。
- 在 Loop 数据中做 frozen external validation。
- 在 RacialDifferences、PSO3/PSO4 等外部数据中做 compatibility matrix 和二次外部验证。
- 做 calibration curve、slope/intercept、ECE、Brier decomposition。
- 做 subgroup fairness 和 small-n reporting。
- 建立 phase-map algorithm card、software specification 和软件 release。

当前结果：

- phase-map 构建队列：748 participants，8638 CGM summary rows。
- bootstrap stability：ARI median 0.826，IQR 0.755-0.890。
- Loop external validation：HbA1c AUROC 0.758，TIR AUROC 0.827。
- PSO3/4 pooled external validation：HbA1c AUROC 0.779，TIR AUROC 0.729。
- phase-guided HTE：maximum adjusted RD 0.281。
- phase-map 软件包 unit tests：2 tests passed。

价值：

Aim 3 把项目从“营养和暴露分析”推进到 digital health/digital phenotype 层。它不是普通 ML benchmark，而是给食品系统代谢易感性提供动态、可复测、可部署的 CGM 表型语言。

关键边界：

- 校准仍需谨慎，输出更适合作 phenotype/ranking，而不是绝对临床风险。
- phase-map 不是自主临床决策系统。

### Step 8. Aim 2-Aim 3 桥接：CGMacros 到 CGM phase/order parameters

目标：测试 CGMacros 原始 CGM 是否能映射到 frozen phase-map 输入结构，并把 meal-response 语言连接到 dynamic CGM phenotype。

实现：

- 将 CGMacros subject-level MSI/PPGR/matrix summary 与 frozen phase-map order parameters 合并。
- 对 MSI-core、median iAUC、high-iAUC rate、matrix composition 与 CGM order parameters 做 participant-level bridge models。
- 使用连续 order parameters 和 phase assignment distance，而不是把 CGMacros phase assignment 写成临床 phase 验证。

当前结果：

- `Aim2_Aim3_CGMacros_phase_bridge_dataset.csv`：40 participants，31 列。
- CGMacros phase compatibility assignment：
  - stable_in_range：37
  - persistent_hyperglycaemia：2
  - hypoglycaemia_susceptible：1
- 40/40 参与者可生成 frozen phase assignment。
- 39/40 参与者满足 168h wear；40/40 满足 72h wear。
- high-iAUC rate 与 phase_assignment_distance 的 bridge model 最强，q = 1.27e-08。
- median iAUC、high-iAUC rate 与 dynamic_instability_score、resilience_proxy_score、CGM CV 等 order parameters 有方向性桥接信号。

价值：

这一步补上了 Aim 2 和 Aim 3 之间最容易断开的地方：真实餐食 PPGR 脆弱性不是孤立指标，而可以与自由生活 CGM 动态表型语言相容。

关键边界：

- 这是 compatibility/order-parameter bridge。
- 不是 CGMacros 中 JAEB phase taxonomy 的临床验证。

### Step 9. Nature Food 主图和稿件材料

目标：把多数据集结果压缩成一篇可以向 Nature Food 编辑解释的六图故事。

实现：

- 重画 6 张主图，并为每个 panel 输出 source data。
- 生成预投稿信、150-word abstract、Results skeleton、figure legends、reviewer risk response memo。
- 生成渲染后的 HTML preview，避免只看到 Markdown 源码。

当前结果：

- Nature Food 主包包含：
  - 14 份文档
  - 24 张表
  - 12 个 figure 文件，PNG/PDF 各 6 个
  - 19 个 figure source-data CSV
  - integrated phenotype 软件包
- 六张主图：
  1. Integrated evidence architecture
  2. Population exposure anchor
  3. Meal-expression layer
  4. Meal redesign and phase compatibility
  5. CGM digital phenotype validation
  6. Bridge cohort workflow

投稿判断：

- 当前锁定路线：Nature Food Analysis presubmission now。
- Article 路线：Aim 4 pilot/bridge cohort 后再考虑。

### Step 10. 软件复现包

目标：把 phase-map 扩展为 integrated food-CGM phenotype package。

实现：

- 输出 schema、toy data、core.py、unit tests、README、VERSION。
- 保留 risk-language guardrail：ranking only, not absolute clinical risk。
- 清理运行缓存，保证 release package 简洁。

当前结果：

- `integrated_food_cgm_phenotype_v0_1` unit test：1 test passed。
- `phase_map_jaeb_v0_1` unit tests：2 tests passed。
- 软件包提供：
  - MSI/meal matrix inputs
  - meal high-iAUC ranking score
  - locked JAEB-derived CGM phase-map assignment
  - explicit risk-language guardrail

价值：

软件包让项目从“结果展示”变成“可复现研究工具”。这对高水平期刊尤其重要：它降低审稿人对黑箱分析的怀疑，也为后续 bridge cohort 提供固定算法。

## 当前全部结果的证据层级

| 层级 | 数据/模块 | 当前结果 | 可主张内容 | 不可主张内容 |
| --- | --- | --- | --- | --- |
| 人群暴露锚点 | NHANES 2013-2018 | DEHP oxidative profile 与 MSI/HOMA/HbA1c 相关；64 行 source proxy matrix | 食品系统暴露背景与代谢易感性在人群层面相关 | 同人群塑化剂暴露导致 PPGR/CGM phase |
| 餐食表达 | CGMacros | MSI-core、food matrix 与 PPGR/high-iAUC 相关；subject leverage 稳定 | 易感性在真实餐食中表达为 PPGR vulnerability | 真实干预疗效 |
| 可改变策略 | Counterfactual redesign | median predicted high-iAUC risk reduction 0.157 | meal redesign 是可检验策略 | 已证明干预有效 |
| 动态数字表型 | JAEB/Loop/PSO | ARI median 0.826；Loop HbA1c AUROC 0.758；Loop TIR AUROC 0.827 | phase-map 是稳定、可迁移的数字表型/排序语言 | 绝对临床风险或自动决策 |
| 桥接分析 | CGMacros phase/order bridge | 40 participants；37 stable-in-range；bridge models 有方向性信号 | meal-response 与 CGM order parameters 相容 | CGMacros 中临床 phase taxonomy 已验证 |
| 复现与投稿 | Figure/source/software package | 6 主图、19 figure source-data、软件测试通过 | 具备 Analysis presubmission 包 | Article 级同人群因果链仍缺 |

## 研究价值

### 1. 概念价值

项目把三个原本分开的领域连起来：

- 食品系统化学暴露：plasticizers、packaging/contact、processing。
- 人体营养与代谢易感性：MSI、HOMA、HbA1c、PPGR。
- 数字健康表型：CGM phase-map、external validation、calibration/fairness。

因此，研究对象不是单个营养素或单个模型，而是食品系统如何通过餐食基质和个体易感性进入连续代谢动态。

### 2. 方法价值

项目的技术路线有四个特点：

- 多数据集三角验证，而不是单队列过拟合。
- 从 population anchor 到 meal expression 到 digital phenotype 的层次化证据链。
- 所有高风险主张都有 guardrail，避免把相关性写成因果性。
- 通过 source-data、manifest、software package 和 unit tests 保持可复现。

### 3. 投稿价值

Nature Food 的核心卖点不是“我们做了很多模型”，而是：

**食品系统暴露与餐食基质可以通过人群代谢易感性、真实餐食 PPGR 和 CGM 动态表型被整合成一个可验证、可转化的研究框架。**

当前适合作为 Analysis，因为它已经具备跨数据集整合和新解释框架；Article 仍需要 Aim 4 同人群桥接实验。

### 4. 转化价值

如果 Aim 4 完成，这条线可以走向：

- 食品/包装 plasticizer panel 的实测证据。
- 标准餐 2x2 matrix/contact challenge。
- 14-28 天 CGM 动态表型验证。
- 基于 phase-map 的个体化饮食和食品接触风险分层。

这使项目从“观察性整合分析”升级为“食品系统干预和数字表型验证”的平台。

## 当前最清晰的研究思路

### 中心假说

食品系统塑化剂暴露和餐食基质不是孤立因素。它们可能通过代谢易感性改变真实餐食后的 PPGR 表达，并在更长时间尺度上表现为 CGM phase-map/order-parameter 的动态表型差异。

### 证据路径

1. NHANES 证明 population exposure anchor。
2. CGMacros 证明 meal matrix + MSI-core 组织 PPGR vulnerability。
3. Counterfactual redesign 提供可转化的 meal redesign 假设。
4. JAEB/Loop/PSO 证明 CGM phase-map 可作为稳定、可迁移的数字表型。
5. CGMacros phase bridge 证明 meal-response 层和 CGM dynamic phenotype 层可以对接。
6. Aim 4 bridge cohort 负责把多数据集三角证据升级为同人群机制/数字表型验证。

### 当前论文主张应这样写

可以写：

- Food-system exposure context, meal matrix and CGM dynamics jointly define a digital metabolic vulnerability phenotype.
- Existing datasets provide triangulated evidence across population, meal-response and CGM-dynamic layers.
- Aim 4 is required for same-person causal-chain validation.

不应该写：

- Plasticizer exposure directly causes PPGR vulnerability in CGMacros participants.
- Counterfactual meal redesign is an established intervention.
- Phase-map is ready for autonomous clinical decision support.

## 后续任务优先级

### P0：7 天内完成

- 最终检查 presubmission enquiry。
- 精修 150-word abstract。
- 人工检查 Figures 1-6。
- 确认每条 claim 都标记为 direct、triangulated、model-based 或 bridge-needed。
- 发送 Nature Food Analysis presubmission enquiry。

### P1：21 天内完成

- 写完整 Analysis manuscript。
- 完成 main-versus-extended-data allocation。
- 补足 Aim 1 food plasticizer panel 文献抽取。
- 完成 Aim 2 matrix adjudication audit。
- 将 integrated phenotype package 升级到 v0.2，加入一键复现脚本和 environment lock。

### P2：90 天内完成

- 准备 Aim 4 IRB 和 pilot protocol。
- 确认 plasticizer assay vendor、LOD、样本量、费用和样本处理 SOP。
- 启动 20-30 人 feasibility pilot。
- 若可行，扩展到 80-120 人 bridge cohort。

## 最重要的入口文件

- 当前包 README：`outputs/integrated_mainline/nature_food_cgm_digital_phenotype_2026-06-20/README.md`
- Nature Food 渲染预览：`results/nature_food_p0_publication_lift_2026_06_18/preview/index.html`
- 六张主图预览：`results/nature_food_p0_publication_lift_2026_06_18/preview/nature_food_main_figures.html`
- 预投稿信：`results/nature_food_p0_publication_lift_2026_06_18/docs/NatureFood_presubmission_enquiry_v1.0.md`
- 下一阶段任务：`results/nature_food_p0_publication_lift_2026_06_18/docs/NatureFood_next_tasks_to_publication_zh_2026_06_18.md`
- 投稿路线锁定：`results/nature_food_p0_publication_lift_2026_06_18/tables/NatureFood_route_decision_memo.csv`
- 复现软件包：`results/nature_food_p0_publication_lift_2026_06_18/software_release/integrated_food_cgm_phenotype_v0_1/`

## 最终判断

这个项目目前已经从“CGMacros 餐食血糖预测”升级为“食品系统暴露、餐食基质与 CGM 数字代谢表型”的整合研究。它的价值不在于任何单个模型或单个数据集，而在于形成了一条可以被审稿人追踪的证据链：

**population exposure anchor -> meal-level PPGR expression -> CGM dynamic phenotype -> same-person bridge validation plan**

当前可以推动 Nature Food Analysis presubmission；若 Aim 4 同人群桥接数据完成，则有机会升级为 Nature Food Article 级别研究。
