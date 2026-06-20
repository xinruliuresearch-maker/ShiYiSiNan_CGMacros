# 以 Nature Food 为目标的重新设计任务书

生成日期：2026-06-17

## 一句话判断

当前 NHANES + CGMacros 分析只能支持“可行性与假设生成”。若以 Nature Food 原创研究为目标，必须新增真正的食品系统贡献：食品/包装/加工相关塑化剂暴露如何与食物基质共同决定人群餐后代谢风险，并证明该风险可通过餐食基质重构被降低。

Nature Food 的范围覆盖 food production、processing、distribution、consumption，以及 food chemistry、food processing、food safety and quality、food systems、human nutrition 和 public health nutrition。因此，稿件不能停留在环境流行病学或 CGM 预测模型，必须把“食品来源暴露”和“膳食/食品设计干预”放到中心。

## 当前缺口

1. NHANES 与 CGMacros 不是同一批人，不能证明 DEHP 暴露个体会出现更高 PPGR。
2. CGMacros 没有尿 DEHP 或食物中塑化剂测量，暴露桥接是间接的。
3. 食物基质标签虽然已人工仲裁，但 kappa 中等，仍需 codebook、复核与压缩分类稳定性。
4. counterfactual meal redesign 只是模型内估计，没有受控餐或体外消化验证。
5. Nature Food 更关心食品系统、加工、暴露、营养和公共健康的连接；当前稿件的 food systems 贡献还不够硬。

## 重新定位后的中心主张

工作题目：

**Food-system plasticizer exposure and food-matrix design jointly shape postprandial glycaemic vulnerability**

中心假设：

1. 食品接触材料、加工和包装相关塑化剂暴露在人群层面锚定一种代谢易感表型。
2. 这种易感表型在自由生活 CGM 餐食中表现为更高 PPGR。
3. 食物基质不是背景变量，而是决定该易感性是否转化为餐后血糖风险的食品设计维度。
4. 通过等碳水/等能量的食物基质重构，可在高易感人群中降低 PPGR。

## Nature Food 级别的必要新增贡献

### Contribution 1：食品系统暴露层

目标：证明塑化剂暴露不是抽象环境变量，而与食品包装、加工、外卖/预包装、液体/高脂食品基质有关。

任务：

1. 建立食品塑化剂暴露样本库。
   - 样本数：至少 80-120 个食品样本。
   - 类别：预包装即食、外卖/餐盒、高脂乳制品/肉类、饮料、精制淀粉、whole-food 对照。
   - 每类至少 10-15 个。
2. 测量食品中 DEHP/MEHP 或更广泛 plasticizer panel。
   - 方法：LC-MS/MS 或委托第三方检测。
   - 输出：食品中 plasticizer concentration，单位 ng/g 或 ug/kg。
3. 记录食品系统变量。
   - 包装材质、是否加热接触塑料、加工等级、脂肪含量、水分/液体形态、保质期、品牌/采购来源。
4. 分析。
   - plasticizer concentration ~ packaging + processing + fat + liquid/solid + matrix category。
   - 输出 Figure：食品系统来源塑化剂暴露热图。

成功标准：

- 至少一个食品系统维度与 plasticizer burden 稳定相关。
- 可将 NHANES 的尿 DEHP 结果解释为食品系统暴露链条的一部分。

### Contribution 2：前瞻性人体 CGM/尿暴露验证

目标：直接验证同一个人身上的塑化剂暴露、MSI/代谢易感性和 PPGR。

设计：

- 人群：n=60-100 成人，覆盖 BMI、HbA1c、性别和年龄范围。
- 设备：连续血糖监测 10-14 天。
- 生物样本：至少 2-3 次晨尿，测 DEHP metabolites，肌酐校正。
- 饮食：自由生活记录 + 2-4 次标准化餐挑战。

标准餐 2x2 设计：

1. 高保护基质，低塑料接触。
2. 高保护基质，高塑料接触/高包装来源。
3. 低保护基质，低塑料接触。
4. 低保护基质，高塑料接触/高包装来源。

更稳妥的伦理表述：

- 不人为添加 DEHP。
- 使用真实市场食品/包装场景，并测量实际食品 plasticizer burden。
- 若高暴露食品浓度不适合人体试验，则高暴露组只用于食品化学和体外消化，人体只比较基质。

主要终点：

- 2h iAUC。
- peak delta。
- time-to-peak。
- high-response meal。

主要模型：

PPGR ~ urinary oxidative DEHP profile + food-matrix arm + exposure x matrix + baseline MSI + premeal glucose + random subject effect。

成功标准：

- 高 MSI 或高 oxidative DEHP profile 个体在低保护基质餐中 PPGR 更高。
- 高保护基质可降低该差异。
- 若 exposure x matrix 不显著，至少 matrix x MSI 显著且方向稳定。

### Contribution 3：体外消化/食物基质机制验证

目标：证明食物基质重构不仅是统计分类，而有可测的营养释放机制。

任务：

1. 从 CGMacros 和市场样本中选择 12-16 对餐食原型。
   - 等碳水/等能量。
   - 低保护基质 vs 高保护基质。
   - 覆盖 breakfast/lunch/snack。
2. INFOGEST-style 体外消化。
   - 时间点：0、15、30、60、90、120 min。
   - 终点：可释放葡萄糖、淀粉水解率、黏度/粒径/可溶性纤维。
3. 将体外释放曲线与 CGM PPGR 模型连接。

成功标准：

- 高保护基质显示更慢 glucose release 或更低早期释放。
- 该机制解释部分 PPGR 预测差异。

### Contribution 4：外部验证或准外部验证

目标：避免只靠 CGMacros 40 人。

优先路径：

1. 寻找另一个公开 CGM+diet 数据集。
2. 若无法获得，进行新 pilot 的 holdout 验证。
3. 或将 CGMacros 拆成 development vs frozen test subjects，并只在 frozen test 中汇报最终性能。

成功标准：

- MSI/food matrix 模型在外部或 frozen test 中方向一致。
- 不要求 AUC 很高，但必须证明非单数据集偶然发现。

## 新的 Aim 结构

### Aim 1：食品系统塑化剂暴露与人群代谢易感性

数据：

- NHANES 2013-2018。
- 新增食品 plasticizer measurement panel。

关键输出：

- 尿 DEHP oxidative profile 与 MSI/HOMA-IR/HbA1c。
- 食品类别/包装/加工与 plasticizer burden。
- 食品系统暴露链条图。

### Aim 2：食物基质决定代谢易感性的 PPGR 表达

数据：

- CGMacros。
- 新前瞻性 CGM pilot 或标准餐挑战。

关键输出：

- MSI-core 与 PPGR。
- food matrix collapsed classes。
- subject leverage。
- 标准餐验证。

### Aim 3：餐食基质重构作为可转化干预策略

数据：

- CGMacros counterfactual。
- 体外消化。
- 可选 CGM pilot。

关键输出：

- 等碳水/等能量 meal redesign。
- predicted risk reduction。
- glucose release mechanism。
- human pilot validation。

## 接下来任务

### P0：重新定义和停止无效扩分析

1. 写一页 Nature Food go/no-go memo。
   - 当前数据能不能投稿？
   - 缺少什么硬证据？
   - 新增实验最低配置是什么？
2. 冻结现有 NHANES/CGMacros 结果，只作为 preliminary evidence。
3. 删除“接近投稿”的表述，改为“preliminary cross-dataset evidence”。
4. 写 pre-registration style analysis plan。

产物：

- `nature_food_go_no_go_memo.md`
- `preliminary_evidence_pack/`
- `prospective_validation_protocol_v1.md`

### P1：食品塑化剂暴露测量方案

1. 设计食品采样表。
2. 确定 80-120 个食品样本类别。
3. 确定检测实验室/方法。
4. 建立样本元数据模板。
5. 生成 power/precision justification。

产物：

- `food_plasticizer_sampling_frame.csv`
- `food_sample_metadata_template.csv`
- `plasticizer_lab_assay_brief.md`

### P2：前瞻性 CGM 标准餐 pilot

1. 写研究方案。
2. 设计纳排标准。
3. 设计 2x2 餐食挑战。
4. 定义尿样采集与 DEHP metabolite 面板。
5. 写统计分析计划。
6. 做样本量估算。

产物：

- `cgm_pilot_protocol.md`
- `standard_meal_challenge_menu.csv`
- `cgm_pilot_statistical_analysis_plan.md`
- `sample_size_simulation_report.md`

### P3：INFOGEST 体外消化验证

1. 选择 12-16 对餐食原型。
2. 写体外消化 SOP。
3. 定义 glucose release endpoint。
4. 建立图件模板。

产物：

- `meal_prototype_pairs.csv`
- `infogest_digestion_sop.md`
- `glucose_release_analysis_plan.md`

### P4：投稿架构重写

1. 重写 title、abstract、significance。
2. 把文章定位为 food systems plasticizer exposure + food matrix intervention。
3. 现有 NHANES/CGMacros 成为 preliminary/main epidemiologic anchor，不再冒充完整投稿证据链。

产物：

- `nature_food_storyline_v2.md`
- `nature_food_abstract_v2.md`
- `reviewer_risk_register.md`

## Go/no-go 决策门槛

### 进入 Nature Food 主投稿的最低门槛

必须满足至少三条：

1. 新食品样本中 plasticizer burden 与包装/加工/食品基质存在清晰梯度。
2. 前瞻性 CGM 或标准餐 pilot 显示 matrix 对 PPGR 有方向一致的调节作用。
3. 尿 DEHP oxidative profile 或 MSI 与标准餐 PPGR 方向一致。
4. 体外消化显示高保护基质的 glucose release 更慢或更低。
5. 外部或 frozen test 验证显示 MSI/food matrix 模型方向一致。

### 如果不能完成新增实验

则不建议继续以 Nature Food 为目标。更合理目标：

- Nature Communications / npj Science of Food：如果补足外部验证和机制。
- Environmental Health Perspectives / Environment International：如果主线转为 DEHP 代谢与代谢风险。
- American Journal of Clinical Nutrition / Diabetes Care 类方向：如果主线转为 PPGR 和食物基质。

## 最推荐的 8 周执行路线

第 1 周：

- 完成 go/no-go memo、食品采样框、CGM pilot protocol。

第 2 周：

- 锁定实验餐、样本量估算、伦理/IRB 材料。

第 3-4 周：

- 采购食品样本并送检 plasticizer panel。
- 同时准备体外消化 SOP。

第 5-6 周：

- 完成第一批食品 plasticizer 数据分析。
- 开始或模拟 CGM pilot 数据采集流程。

第 7 周：

- 完成体外消化 pilot。
- 将 glucose release 与 CGMacros counterfactual 连接。

第 8 周：

- 更新 Nature Food storyline。
- 决定是否继续 Nature Food，或转向更匹配期刊。

