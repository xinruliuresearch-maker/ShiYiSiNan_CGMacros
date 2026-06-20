# 受胡脊梁系列研究启发的糖尿病公开数据研究设计

题目建议：

**从复杂生态相图到血糖动力学相图：基于公开 CGM/RCT 数据的糖尿病干预响应、稳定性与个体化治疗预测研究**

版本：1.0  
日期：2026-06-16  
数据基础：JAEB public diabetes datasets、当前已清洗 `processed_ml_table.csv`，以及后续可扩展的公开 CGM 时间序列数据。

## 1. 设计动机

胡脊梁的系列研究最值得借鉴的不是某一个具体疾病方向，而是一种物理生物学和复杂系统思维：

1. 将复杂生物系统粗粒化为少数关键参数。
2. 用“相图”描述系统在不同参数区间中的稳定状态。
3. 关注系统稳定性、扰动响应、可入侵性、震荡状态和相变。
4. 将实验数据、数学模型和机器学习结合起来，寻找可解释的系统规律。

这种思路可以自然迁移到糖尿病和 CGM 数据：

- 一个糖尿病患者的血糖动态可以被视为一个“个体血糖生态系统”。
- CGM 轨迹中的低血糖、目标范围、高血糖、波动、恢复速度和昼夜节律，类似系统中的不同状态和扰动响应。
- 干预，如 CGM、AID、二甲双胍、行为干预，可被视作外部控制变量。
- 治疗响应不只是 HbA1c 是否下降，也可以被理解为系统是否从“不稳定血糖相”转移到“稳定目标相”。

因此，本研究拟建立一个公开数据驱动的“血糖动力学相图”，并进一步验证该相图能否提高糖尿病干预响应预测、治疗异质性解释和个体化干预选择。

## 2. 核心科学问题

主要问题：

> 糖尿病患者是否存在可复现的血糖动力学相位？这些相位能否解释不同干预下的治疗响应差异，并提升机器学习模型对 HbA1c、CGM TIR 和体重变化的预测能力？

更具体地说：

1. 公开 CGM/RCT 数据中，是否存在稳定可复现的“血糖动力学状态”？
2. 这些状态是否对应不同的临床表型，如高血糖主导型、低血糖易感型、高波动型、昼夜节律紊乱型、稳定达标型？
3. 干预后，患者是否会发生可量化的“相位转移”？
4. 基线动力学相位能否预测谁更可能从 CGM、AID、行为干预或药物干预中获益？
5. 相图特征是否比传统特征，如年龄、HbA1c、BMI，带来额外预测价值？

## 3. 面向顶刊的创新点

### 3.1 概念创新

传统糖尿病机器学习研究多预测单点结局，如 HbA1c 或低血糖风险。本研究将血糖控制重新定义为一个动态系统问题：

- HbA1c 是长期平均状态。
- TIR 是系统驻留在目标状态的比例。
- CV、MAGE、低血糖时间、高血糖时间是波动与不稳定性。
- 从高血糖回到目标范围的速度是恢复力。
- 高血糖或低血糖事件后的连锁波动是扰动扩散。
- 干预后的 TIR/HbA1c 改善是系统状态转移。

这使研究从“预测一个结局”升级为“理解血糖系统的动力学结构”。

### 3.2 方法创新

研究将结合：

- CGM 时间序列特征工程。
- 动力系统指标。
- 无监督相位发现。
- 相图构建。
- 监督机器学习。
- 表格基础模型和时间序列基础模型微调。
- 异质性治疗效应分析。
- 决策曲线和临床净获益评估。

### 3.3 数据创新

完全基于公开数据，避免私有临床数据库不可复现的问题。当前已经有 6 个 JAEB 公共 RCT/干预数据包完成初步清洗，后续可继续扩展到更多公开 CGM 数据。

### 3.4 临床转化创新

最终目标不是单纯报告最高 AUROC，而是生成一种可解释的临床分层工具：

- 识别患者当前处于哪种血糖动力学相。
- 预测其在不同干预下可能向哪个相位迁移。
- 为 CGM、AID、药物强化、行为干预和随访频率提供个体化依据。

## 4. 胡脊梁研究思想到本研究的映射

| 胡脊梁系列研究中的思想 | 糖尿病研究中的对应设计 |
|---|---|
| 微生物群落复杂相互作用 | 血糖、胰岛素、饮食、运动、昼夜节律和干预共同作用 |
| 粗粒化参数 | TIR、TBR、TAR、CV、恢复时间、转移熵、昼夜节律强度 |
| 相图 | 血糖动力学相图 |
| 稳定性 | 日间/日际 TIR 稳定性、低血糖易感性、高血糖持续性 |
| 可入侵性 | 高血糖/低血糖事件对系统的扰动扩散能力 |
| 震荡状态 | 血糖大幅波动、反复高低血糖转换、昼夜节律异常 |
| 相变 | 干预后从不稳定相转入稳定达标相 |
| 理论模型 + 数据验证 | 动力学指标 + RCT 干预结局验证 |

## 5. 数据来源

### 5.1 当前已处理数据

当前工作区已经下载并清洗了 6 个 JAEB 公开个体级数据集：

| 研究 | 人群 | 干预 | 当前 ML 表样本量 |
|---|---|---|---:|
| WISDM | T1D 老年人 | CGM vs BGM | 203 |
| CITY | T1D 青少年和年轻成人 | CGM vs BGM | 153 |
| SENCE | T1D 幼儿 | CGM/FBI/BGM | 143 |
| REPLACE-BG | T1D 成人 | CGM-only vs CGM+BGM | 226 |
| FLAIR | T1D AID 人群 | AID 算法比较 | 113 |
| METFORMIN_T1D | 超重 T1D 青少年 | 二甲双胍 vs 安慰剂 | 139 |

当前受试者级表：

- 总样本量：977。
- HbA1c 改善任务可用样本量：940。
- CGM TIR 改善任务可用样本量：473。
- 体重变化任务可用样本量：580。

这些数据适合第一阶段构建“受试者级血糖相图”和治疗响应预测。

### 5.2 后续应扩展的公开数据

为了形成顶刊级证据，应继续纳入公开或可申请的时间序列数据：

1. JAEB DCLP3 / PEDAP / AIDE / IOBP2 等公开数据包。
2. JAEB 已下载数据包中的原始 `DeviceCGM` 表，用于逐点 CGM 动力学分析。
3. OhioT1DM 数据集：CGM、胰岛素、饮食、活动等多模态 T1D 数据，需按数据集要求申请。
4. D1NAMO：T1D 多模态生理和 CGM 数据。
5. OpenAPS / Open Humans 相关公开糖尿病数据，在许可允许下使用。
6. NIDDK / BioLINCC 中需申请的高质量 RCT，如 DPP/DPPOS、Look AHEAD、TODAY、GRADE、ACCORD、DCCT/EDIC，用作扩展验证，但不得伪造或违规下载。

## 6. 研究目标

### 6.1 目标 1：构建血糖动力学相图

使用公开 CGM 数据，为每位受试者在基线期构建一组粗粒化动力学参数，并识别可复现的血糖动力学相位。

预期相位包括：

- 稳定达标相：高 TIR、低波动、低低血糖风险。
- 高血糖持续相：高 TAR、恢复慢、HbA1c 高。
- 高波动震荡相：CV 高、高低血糖频繁切换。
- 低血糖易感相：TBR/TBR54 高、夜间低血糖突出。
- 昼夜节律紊乱相：夜间/日间状态差异异常。
- 数据稀疏或依从性不足相：CGM 小时数不足，需单独标记。

### 6.2 目标 2：验证相位与临床结局的关系

检验基线相位是否与以下结局相关：

- HbA1c 改善 >=0.5 个百分点。
- 随访 HbA1c <7%。
- TIR 改善 >=5 或 >=10 个百分点。
- 低血糖时间减少。
- 体重变化。
- 不良事件，如严重低血糖或 DKA，若数据可用。

### 6.3 目标 3：比较不同机器学习方法的预测能力

比较传统特征、相图特征、深度特征和微调模型的预测性能。

核心问题：

> 加入血糖动力学相图特征后，模型是否比仅使用传统临床特征更准确、更校准、更能跨研究泛化？

### 6.4 目标 4：识别异质性治疗响应

在单个 RCT 内评估：

- 哪些相位患者更受益于 CGM？
- 哪些相位患者更受益于行为干预？
- 哪些相位患者更可能从药物或 AID 中获益？
- 是否存在“相位依赖性治疗效应”？

### 6.5 目标 5：形成可解释的个体化干预框架

最终输出一个临床可解释框架：

1. 输入基线 CGM 和临床特征。
2. 定位患者血糖动力学相。
3. 预测不同干预下的相位迁移概率。
4. 输出个体化获益和风险。

## 7. 核心假设

### 假设 1：存在可复现的血糖动力学相位

不同公开数据集中，基于 TIR、TAR、TBR、CV、熵、恢复时间、昼夜节律等指标，可以识别出相似的动态状态。

### 假设 2：治疗响应由基线相位调节

例如：

- 高波动震荡相患者可能更受益于 CGM 或 AID。
- 高血糖持续相患者可能需要药物强化或更强行为干预。
- 低血糖易感相患者的最佳目标可能是减少低血糖，而非单纯降低 HbA1c。

### 假设 3：相图特征提高预测性能

与传统模型相比，加入相图特征后：

- AUROC/AUPRC 提高。
- RMSE/MAE 降低。
- 校准更好。
- Leave-one-study-out 泛化更强。
- 决策曲线净获益更高。

### 假设 4：干预效果可表现为相位迁移

有效干预不仅改变单个数值，而是推动个体从不稳定相迁移到更稳定、更安全的相。

## 8. 动力学特征体系

### 8.1 传统 CGM 指标

- Mean glucose。
- TIR 70-180 mg/dL。
- Time below 70。
- Time below 54。
- Time above 180。
- Time above 250。
- Glucose management indicator。
- Coefficient of variation。
- Standard deviation。
- MAGE，若原始 CGM 可计算。

### 8.2 状态占用和多样性指标

将 CGM 离散为状态：

- 严重低血糖：<54。
- 低血糖：54-69。
- 目标范围：70-180。
- 高血糖：181-250。
- 严重高血糖：>250。

计算：

- 各状态占用比例。
- Shannon entropy。
- Simpson diversity。
- 状态转换矩阵。
- 状态转移熵。
- 目标状态驻留时间分布。

### 8.3 稳定性指标

- 日间 TIR 方差。
- 日间平均血糖方差。
- 日间 CV 方差。
- 自相关函数衰减。
- Hurst exponent。
- Detrended fluctuation analysis。
- Recurrence quantification analysis。
- 夜间低血糖稳定性。

### 8.4 扰动和恢复力指标

若有饮食、胰岛素、运动数据：

- 餐后峰值。
- 餐后回到目标范围时间。
- 胰岛素后低血糖风险。
- 运动后低血糖风险。

若只有 CGM：

- 高血糖事件持续时间。
- 高血糖事件后恢复到 TIR 的时间。
- 低血糖事件后恢复时间。
- 高低血糖事件连锁概率。
- 极端事件后的波动扩散范围。

### 8.5 昼夜节律指标

- 日间 TIR。
- 夜间 TIR。
- 夜间 TBR。
- 夜间平均血糖。
- 24 小时周期强度。
- Cosinor 模型振幅和相位。
- 昼夜差异指数。

### 8.6 相图粗粒化参数

建议构建 3-5 个核心“序参量”：

1. `Glycemic burden`：高血糖负担，主要由 TAR、mean glucose、HbA1c 表征。
2. `Hypoglycemic susceptibility`：低血糖易感性，由 TBR70、TBR54、夜间 TBR 表征。
3. `Dynamical instability`：动态不稳定性，由 CV、状态转移熵、日间波动、MAGE 表征。
4. `Resilience`：恢复力，由高/低血糖事件恢复时间表征。
5. `Circadian disruption`：昼夜节律紊乱，由夜间/日间差异和 cosinor 参数表征。

这些粗粒化参数是受胡脊梁系列研究启发的关键设计：用少数可解释变量总结复杂动态。

## 9. 相图构建方法

### 9.1 无监督相位发现

候选方法：

- Gaussian mixture model。
- Bayesian Gaussian mixture。
- HDBSCAN。
- Spectral clustering。
- Leiden/Louvain graph clustering。
- Self-organizing map。
- Variational autoencoder latent space clustering。

选择原则：

- 不只看 silhouette score。
- 还要看跨数据集可复现性。
- 相位必须具备临床解释。
- 相位应该能预测随访结局或干预响应。

### 9.2 相图可视化

建议二维和三维相图：

- x 轴：高血糖负担。
- y 轴：动态不稳定性。
- 颜色：低血糖易感性。
- 点形状：干预臂。
- 箭头：干预前后相位迁移。

核心图：

1. 基线血糖动力学相图。
2. 不同研究人群在相图中的分布。
3. 不同干预导致的相位迁移箭头。
4. 相位与 HbA1c/TIR 改善概率。
5. 相位特异性治疗效应。

### 9.3 相位稳定性检验

- Bootstrap clustering。
- Study-stratified clustering。
- Leave-one-study-out 相位重建。
- Adjusted Rand index。
- Mutual information。
- 相位中心在不同数据集中的偏移。

## 10. 机器学习和微调模型设计

### 10.1 预测任务

主要任务：

- `y_hba1c_improved_ge_0_5`

次要任务：

- `y_hba1c_under_7_at_followup`
- `y_tir_improved_ge_5pct`
- `y_hba1c_change_pct_points`
- `y_change_cgm_time_in_range_70_180_pct`
- `y_weight_change_kg`

### 10.2 特征集

| 特征集 | 内容 | 目的 |
|---|---|---|
| C0 | 基线 HbA1c + 年龄 + study | 传统临床基线 |
| C1 | C0 + BMI + 糖尿病病程 + 治疗臂 | 标准临床模型 |
| C2 | C1 + 传统 CGM 指标 | 常规 CGM 模型 |
| C3 | C2 + 动力学稳定性和恢复力指标 | 相图增强模型 |
| C4 | C3 + 无监督相位标签和相位坐标 | 完整相图模型 |
| C5 | 原始 CGM 时间序列 embedding + C1 | 深度/基础模型 |

核心比较：

> C4 是否显著优于 C1/C2，并在外部验证和校准中保持优势？

### 10.3 模型类别

传统和强基线：

- Logistic regression。
- Elastic net。
- Random forest。
- ExtraTrees。
- XGBoost。
- LightGBM。
- CatBoost。

深度表格模型：

- MLP。
- FT-Transformer。
- TabTransformer。
- SAINT。
- TabNet。

表格基础模型：

- TabPFN zero-shot/in-context。
- TabPFN + calibration。
- TabPFN embedding + GBDT/logistic head。
- 若可行，TabPFN adapter/fine-tuning。

时间序列基础模型或预训练模型：

- Chronos。
- TimesFM。
- MOMENT。
- Lag-Llama。
- 自监督 CGM Transformer。

说明：时间序列基础模型是否真正适合 CGM，需要通过严格外部验证判断，不能预设其优于 GBDT。

### 10.4 微调策略

#### 表格模型微调

1. 使用训练折中的 baseline 表格特征。
2. 对类别和数值特征分别编码。
3. 进行 supervised fine-tuning。
4. 使用内层验证折选择学习率、epoch、adapter 维度。
5. 外层测试折只评估一次。

#### CGM 时间序列自监督预训练

预训练任务：

- Masked glucose reconstruction。
- Next-window prediction。
- Contrastive day-to-day representation learning。
- Event prediction，如未来 2 小时低血糖/高血糖。

微调任务：

- HbA1c 改善。
- TIR 改善。
- 低血糖减少。
- 相位迁移。

严格要求：

- 预训练可以使用无标签 CGM。
- 监督微调不能使用外层测试集标签。
- 如果同一个患者有多日 CGM，训练/测试必须按患者分组，不能按时间窗口随机拆分。

## 11. 验证设计

### 11.1 主验证

采用 repeated nested cross-validation：

- 外层 5 折，重复 5 次。
- 内层 3-5 折调参。
- 分类任务按结局和 study 分层。
- 所有窗口级模型必须按 participant ID 分组。

### 11.2 外部泛化验证

采用 leave-one-study-out：

- 留出 WISDM，训练其他研究。
- 留出 CITY，训练其他研究。
- 留出 SENCE，训练其他研究。
- 以此类推。

CGM TIR 任务至少在 WISDM、CITY、SENCE 间做 leave-one-study-out。

### 11.3 干预迁移验证

更高阶验证：

- 在 CGM vs BGM 研究训练，在另一个 CGM vs BGM 研究验证。
- 在儿童研究训练，在成人研究验证。
- 在设备干预研究训练，在药物干预研究验证，作为极端外推测试。

### 11.4 相图可复现性验证

- 每个研究独立构建相位。
- 比较相位中心和相位标签一致性。
- 使用公开外部 CGM 数据重建相图。

## 12. 评价指标

### 12.1 分类指标

- AUROC。
- AUPRC。
- Balanced accuracy。
- Sensitivity。
- Specificity。
- F1 score。
- Brier score。
- Calibration-in-the-large。
- Calibration slope。
- Decision curve net benefit。

Accuracy 只作为辅助指标，不作为主要模型选择标准。

### 12.2 回归指标

- RMSE。
- MAE。
- R-squared。
- Spearman correlation。
- 预测误差 <=0.5 HbA1c 百分点的比例。
- 按预测分位数的观察值校准图。

### 12.3 相图指标

- 相位稳定性。
- 相位可解释性。
- 相位对结局的预测增益。
- 相位迁移概率。
- 相位特异性治疗效应。

## 13. 统计分析

### 13.1 主要比较

比较以下模型：

1. 传统临床模型 C1。
2. 常规 CGM 模型 C2。
3. 相图增强模型 C4。
4. 深度/基础模型 C5。

主要检验：

- C4 是否较 C1/C2 提高 AUROC/AUPRC。
- C4 是否降低 Brier score。
- C4 是否在 leave-one-study-out 中仍保持优势。
- C4 是否增加决策曲线净获益。

### 13.2 置信区间

- 使用 bootstrap 估计 AUROC、AUPRC、Brier、RMSE 的 95% CI。
- 使用 paired bootstrap 比较模型。
- Leave-one-study-out 结果用 study-level summary 报告。

### 13.3 多重比较

预设主模型：

- Logistic regression。
- CatBoost。
- XGBoost。
- LightGBM。
- TabPFN。
- 相图增强 CatBoost。
- CGM Transformer。

其他模型作为探索性分析。

## 14. 异质性治疗效应

在每个 RCT 内分别分析，避免跨不兼容干预乱做因果推断。

方法：

- Causal forest。
- R-learner。
- X-learner。
- Doubly robust learner。
- Meta-learner。

关键问题：

- 哪些血糖相位更受益于 CGM？
- 哪些相位更受益于 AID？
- 哪些相位对二甲双胍更可能出现 HbA1c 或体重获益？
- 相位是否比传统 HbA1c 分层更能识别获益人群？

输出：

- 平均治疗效应。
- 相位特异性治疗效应。
- 个体化治疗获益分布。
- 模型分配策略 vs 随机分配策略的 policy value。

## 15. 预期关键图表

面向顶刊，建议准备以下主图：

### Figure 1：研究概念图

展示从胡脊梁式复杂系统相图思想到血糖动力学相图的迁移。

### Figure 2：公开数据整合流程

显示 JAEB、OhioT1DM、D1NAMO 等数据来源，清洗、特征构建、建模和验证流程。

### Figure 3：血糖动力学相图

以高血糖负担、动态不稳定性、低血糖易感性构建相图，并标注不同相位。

### Figure 4：干预前后相位迁移

显示 CGM、AID、二甲双胍或行为干预后患者在相图中的迁移箭头。

### Figure 5：模型性能比较

比较传统模型、CGM 模型、相图模型、深度/基础模型的 AUROC、AUPRC、Brier、校准。

### Figure 6：相位特异性治疗效应

展示不同相位中治疗获益的差异。

### Figure 7：外部验证和亚组稳健性

展示 leave-one-study-out、年龄组、性别、种族/族裔、HbA1c 分层的表现。

## 16. 敏感性分析

1. 仅使用中心实验室 HbA1c。
2. 排除 FLAIR 交叉设计研究。
3. 仅纳入 CGM 设备干预研究。
4. 仅纳入 T1D 研究。
5. 不包含随机分组，构建纯预后模型。
6. 包含随机分组，构建给定治疗模型。
7. 改变 HbA1c 改善阈值：0.3、0.5、1.0。
8. 改变 TIR 改善阈值：5、10。
9. 使用不同 CGM 缺失处理策略。
10. 使用不同相位聚类算法。
11. 完整病例 vs 插补分析。
12. 不含 study ID vs 含 study ID。

## 17. 偏倚和风险控制

### 17.1 数据泄漏

所有预测变量必须来自基线。随访 CGM、随访 HbA1c、随访体重、依从性变化、随访设备上传等不能进入 baseline 模型。

### 17.2 过拟合

使用嵌套交叉验证、外部验证、早停、正则化、随机种子重复和预设调参预算。

### 17.3 异质性

不同研究人群差异极大，因此必须：

- 报告 study-specific performance。
- 做 leave-one-study-out。
- 在模型中考虑 study ID。
- 谨慎解释 pooled model。

### 17.4 公平性

按年龄、性别、种族、族裔、基线 HbA1c、治疗臂报告性能。小样本亚组只做描述性分析。

## 18. 顶刊潜力判断

这项研究如果只做“哪个 ML 准度最高”，顶刊潜力有限；但如果形成以下完整叙事，则有较强潜力：

1. 受复杂系统相图启发，提出血糖动力学相图。
2. 基于多个公开 RCT/CGM 数据集构建可复现相位。
3. 证明相位能解释治疗响应和异质性。
4. 证明相图特征可提高预测、校准和临床净获益。
5. 给出外部验证和亚组稳健性。
6. 公开代码和数据处理流程。

最有潜力的投稿方向：

- `Diabetes Care`
- `The Lancet Digital Health`
- `npj Digital Medicine`
- `Nature Medicine`，前提是外部验证和相图创新非常强。
- `NEJM AI`，前提是模型验证、临床效用和可解释性充分。

## 19. 建议优先实施的第一版实验

第一版不宜一开始就做所有时间序列 foundation model。建议先完成最稳健、最容易产出结果的版本：

### 第一阶段数据

使用当前已清洗的 JAEB 6 个公开数据集：

- 主任务：`y_hba1c_improved_ge_0_5`。
- 次任务：`y_tir_improved_ge_5pct`。

### 第一阶段特征

- C1：传统临床特征。
- C2：传统临床特征 + 基线 CGM 指标。
- C4：传统特征 + CGM 指标 + 相图特征。

### 第一阶段模型

- Logistic regression。
- Random forest。
- XGBoost。
- LightGBM。
- CatBoost。
- TabPFN。
- FT-Transformer。

### 第一阶段验证

- 5x5 repeated nested CV。
- Leave-one-study-out。
- 校准曲线。
- 决策曲线。
- SHAP 解释。

### 第一阶段判断标准

如果相图增强模型相较传统模型：

- AUROC 提升 >=0.03。
- AUPRC 提升。
- Brier score 降低。
- 校准不变差。
- Leave-one-study-out 仍有优势。
- 决策曲线净获益提高。

则可以进入第二阶段，扩展原始 CGM 时间序列和外部公开数据。

## 20. 后续实现文件建议

建议新增：

- `scripts/build_cgm_dynamics_features.py`
- `scripts/build_glycemic_phase_map.py`
- `scripts/model_benchmark_phase_map.py`
- `scripts/evaluate_calibration_decision_curve.py`
- `scripts/hte_by_phase.py`
- `scripts/plot_phase_diagram.py`

建议输出：

- `data/processed/cgm_dynamics_features.csv`
- `data/processed/glycemic_phase_labels.csv`
- `results/phase_model_performance.csv`
- `results/leave_one_study_out_results.csv`
- `results/hte_by_phase.csv`
- `figures/glycemic_phase_diagram.png`
- `figures/phase_transition_arrows.png`
- `figures/model_calibration_curves.png`
- `figures/decision_curves.png`

## 21. 论文摘要草案

背景：

糖尿病干预响应高度异质，传统静态指标难以解释个体差异。复杂系统理论提示，动态生物系统可通过少数粗粒化参数和相图进行描述。

方法：

本研究整合公开糖尿病 RCT 和 CGM 数据，构建血糖动力学特征，包括高血糖负担、低血糖易感性、动态不稳定性、恢复力和昼夜节律紊乱。使用无监督学习建立血糖相图，并比较传统机器学习、梯度提升树、深度表格模型和基础模型在预测 HbA1c/TIR 改善中的表现。

结果预期：

我们预期识别出多个可复现血糖动力学相位。基线相位将与干预响应显著相关，并能提高模型预测性能、校准和临床净获益。

结论：

血糖动力学相图可能为糖尿病个体化干预提供一种新的可解释框架，并为公开数据驱动的临床 AI 研究提供可复现范式。

## 22. 参考来源

胡脊梁及其研究方向：

- SMART Fellow profile: https://smart.org.cn/smart-fellow/hujiliang
- Shenzhen Bay Laboratory PI profile: https://www.szbl.ac.cn/scientificresearch/researchteam/2115.html
- Phase diagram of early bacterial community dynamics, Science/PubMed: https://pubmed.ncbi.nlm.nih.gov/36952465/
- Dynamical regimes enhance ecosystems invasibility and diversity, Nature Ecology & Evolution: https://www.nature.com/articles/s41559-022-01921-4
- Phase diagram of cellular response to mechanical cues, PNAS: https://www.pnas.org/doi/10.1073/pnas.2308359120

糖尿病公开数据与 CGM 规范：

- JAEB Public Diabetes Datasets: https://public.jaeb.org/datasets/diabetes
- International Consensus on Time in Range, Diabetes Care/PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC6973648/
- ADA Standards of Care 2026 glycemic goals: https://diabetesjournals.org/care/article/49/Supplement_1/S132/163927/6-Glycemic-Goals-Hypoglycemia-and-Hyperglycemic
- OhioT1DM Dataset: https://smarthealth.cs.ohio.edu/OhioT1DM-dataset.html
- D1NAMO Dataset paper: https://dl.acm.org/doi/10.1145/2836041.2836066

临床 AI 和模型报告规范：

- TRIPOD+AI / EQUATOR: https://www.equator-network.org/reporting-guidelines/tripod-statement/
- PROBAST+AI: https://www.latitudes-network.org/tool/probastai/
- CONSORT-AI: https://www.nature.com/articles/s41591-020-1034-x
- SPIRIT-AI: https://www.nature.com/articles/s41591-020-1037-7

表格模型和基础模型：

- TabPFN ICLR 2023: https://openreview.net/forum?id=cp5PvcI6w8_
- TabPFN Nature/PubMed: https://pubmed.ncbi.nlm.nih.gov/39780007/
- Why tree-based models still outperform deep learning on tabular data: https://arxiv.org/abs/2207.08815
- Revisiting Deep Learning Models for Tabular Data: https://openreview.net/forum?id=i_Q1yrOegLY

