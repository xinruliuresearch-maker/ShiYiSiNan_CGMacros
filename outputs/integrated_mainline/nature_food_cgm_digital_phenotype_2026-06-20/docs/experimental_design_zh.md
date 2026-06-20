# 实验设计：糖尿病 RCT 响应预测的机器学习与微调模型比较

版本：1.0  
日期：2026-06-16  
数据基础：`data/processed/processed_ml_table.csv`

## 1. 研究总览

本研究拟使用公开可获取的糖尿病个体级 RCT/干预研究数据，系统比较传统机器学习、梯度提升树、深度表格模型、AutoML、TabPFN 等表格基础模型，以及可行的微调模型，用于预测糖尿病干预后的个体化结局。

核心科学问题：

> 基于基线临床特征、人口学特征、随机分组、CGM 指标等信息，能否预测糖尿病干预后的个体化血糖改善？在严格交叉验证、校准、外部可迁移性和临床净获益评价下，哪类机器学习方法表现最好？

当前清洗后的数据集规模如下：

| 任务 | 结局变量 | 可用样本量 | 阳性数 / 阳性率 |
|---|---:|---:|---:|
| HbA1c 改善分类 | `y_hba1c_improved_ge_0_5` | 940 | 246 / 26.2% |
| 随访 HbA1c 达标分类 | `y_hba1c_under_7_at_followup` | 940 | 210 / 22.3% |
| CGM TIR 改善分类 | `y_tir_improved_ge_5pct` | 473 | 183 / 38.7% |
| HbA1c 变化回归 | `y_hba1c_change_pct_points` | 940 | 连续变量 |
| CGM TIR 变化回归 | `y_change_cgm_time_in_range_70_180_pct` | 473 | 连续变量 |
| 体重变化回归 | `y_weight_change_kg` | 580 | 连续变量 |

本研究不应仅以 accuracy 选择最佳模型。若目标是领域顶尖期刊，模型优劣应按以下层级综合判断：

1. 内部交叉验证的区分能力或预测误差。
2. 概率校准表现。
3. Leave-one-study-out 外部可迁移性。
4. 决策曲线和临床净获益。
5. 亚组稳健性和敏感性分析。
6. 可解释性、复现性和部署可行性。

## 2. 文献和规范依据

实验设计应遵循当前临床 AI 与表格机器学习的主流要求：

- 使用 TRIPOD+AI 作为预测模型开发和验证的报告框架。
- 使用 PROBAST+AI 评估偏倚风险，重点关注研究对象、预测变量、结局定义和统计分析。
- 若未来将模型作为干预工具进行前瞻性试验，再参考 CONSORT-AI 和 SPIRIT-AI。
- CGM 结局采用国际共识定义，如 70-180 mg/dL 范围内时间、低血糖时间、高血糖时间和 TIR 改善幅度。
- 梯度提升树模型必须作为强基线，因为大量表格数据 benchmark 显示树模型仍然很难被深度模型稳定超越。
- 深度表格模型和基础模型可以纳入，但必须使用严格嵌套交叉验证，避免小样本过拟合。
- 除 AUROC/accuracy 外，必须报告校准、Brier score、AUPRC、决策曲线、亚组表现和敏感性分析。

## 3. 论文定位和潜在投稿方向

### 3.1 建议主张

一个更稳健、适合高水平期刊的论文主张是：

> 在多项公开糖尿病个体级 RCT 数据中，表格机器学习能够对血糖干预响应进行一定程度预测；但模型排名会受到校准和跨研究外部验证影响。基线 HbA1c、研究人群、干预类型和 CGM 基线状态是关键预测信息。

不建议声称“AI 可以完美预测糖尿病干预反应”。更合适的定位是：公开 RCT 个体级数据上的严谨模型 benchmark、可迁移性分析和个体化响应预测研究。

### 3.2 目标期刊

优先目标：

- `Diabetes Care`：如果临床糖尿病解释和分层治疗意义充分，这是最贴合的期刊。
- `The Lancet Digital Health`：需要非常强的外部验证、临床意义和可复现性。
- `Nature Medicine`：只有在基础模型/个体化治疗策略有明确创新且验证充分时才适合。
- `npj Digital Medicine`：适合严谨的公开数据临床 AI benchmark。
- `JAMA Network Open`：如果临床预测问题和透明报告足够扎实，可以考虑。
- `NEJM AI`：如果模型比较、部署意义和方法创新成熟，可以考虑。

备选方向：

- `Patterns`
- `PLOS Digital Health`
- `Journal of Biomedical Informatics`
- `Artificial Intelligence in Medicine`

## 4. 研究目标

### 4.1 主要目标

比较多种机器学习和微调/适配表格基础模型，预测个体是否达到临床有意义的 HbA1c 改善：

`y_hba1c_improved_ge_0_5 = 1` 表示随访 HbA1c 相比基线下降至少 0.5 个百分点。

### 4.2 次要目标

1. 预测连续型 HbA1c 变化。
2. 预测随访 HbA1c 是否小于 7%。
3. 在有 CGM 汇总指标的研究中，预测 TIR 是否改善至少 5 个百分点。
4. 预测连续型 CGM TIR 变化。
5. 预测体重变化。
6. 在适合的 RCT 内估计异质性治疗效应。
7. 使用 leave-one-study-out 验证模型跨研究人群的可迁移性。
8. 系统评估校准和临床净获益。

### 4.3 探索性目标

1. 比较 TabPFN 的 zero-shot/in-context 表现与可微调/适配版本。
2. 使用额外公开 JAEB 基线变量做自监督预训练，再进行监督微调。
3. 尝试 HbA1c、CGM、体重多任务学习。
4. 比较 pooled model、study-specific model、层级模型和 meta-learning 方案。

## 5. 数据和分析队列

### 5.1 已纳入的公开数据

当前 ML 表纳入 6 个 JAEB 公开去标识化个体级数据集：

| 研究 | 设计 | 对象 | 主要干预 |
|---|---|---|---|
| WISDM | 平行组 RCT | T1D 老年人 | CGM vs BGM |
| CITY | 平行组 RCT | T1D 青少年和年轻成人 | CGM vs BGM |
| SENCE | 阶乘/平行组 RCT | T1D 幼儿 | CGM + 家庭行为干预、标准 CGM、BGM |
| REPLACE-BG | 平行组 RCT | 使用 CGM 的 T1D 成人 | CGM-only vs CGM+BGM |
| FLAIR | 交叉 RCT | 使用 AID 系统的 T1D 人群 | AHCL/PID+fuzzy logic vs 对照算法 |
| METFORMIN_T1D | 平行组 RCT | 超重 T1D 青少年 | 二甲双胍 vs 安慰剂 |

### 5.2 任务特异性队列

- `队列 A`：基线和随访 HbA1c 均非缺失，n=940。
- `队列 B`：可判断随访 HbA1c 是否达标，n=940。
- `队列 C`：基线和随访 CGM TIR 均非缺失，n=473。
- `队列 D`：基线和随访体重均非缺失，n=580。
- `队列 E`：用于异质性治疗效应分析的单个 RCT 内队列。

### 5.3 排除标准

仅在以下情况从对应任务中排除样本：

- 随机分组缺失。
- 该任务必须的基线变量缺失且无法通过预设插补流程处理。
- 对应随访结局缺失。
- 单位标准化后仍存在无法解释的异常值。

不应因为某些非核心预测变量缺失而简单删除样本。

## 6. 预测时间点和数据泄漏控制

### 6.1 预测时间点

主要预测时间点定义为：

> 基线/随机化时点，即随访结局、干预后依从性、设备使用情况尚未发生或尚不可见时。

### 6.2 允许使用的预测变量

允许：

- 研究 ID。
- 试验干预类型。
- 随机分组，限于 assigned-treatment prediction。
- 年龄、性别、种族、族裔。
- 糖尿病诊断年龄和病程。
- 基线 HbA1c。
- 基线体重、身高、BMI。
- 基线胰岛素剂量或给药方式。
- 基线 CGM 汇总指标。
- 基线变量缺失指示。

不允许：

- 随访 HbA1c、CGM、体重、BMI。
- 随机化后的依从性、设备上传频率、CGM 佩戴情况。
- 基线后的访视完成情况。
- 干预后的不良事件。
- 任何用随访结局构造的变量。

### 6.3 两类预测设定

1. `预后模型`：不包含随机分组，用于回答“在治疗决策前，谁更可能改善？”
2. `给定治疗模型`：包含随机分组，用于回答“在已知分配治疗下，谁更可能改善？”

如果要做个体化治疗选择，应进一步使用异质性治疗效应方法，而不是仅凭普通模型的特征重要性做因果解释。

## 7. 结局变量

### 7.1 主要结局

`y_hba1c_improved_ge_0_5`

理由：HbA1c 下降至少 0.5 个百分点具有临床可解释性，也比“任何下降”更不易受实验室波动影响。

### 7.2 次要结局

分类任务：

- `y_hba1c_under_7_at_followup`
- `y_tir_improved_ge_5pct`

回归任务：

- `y_hba1c_change_pct_points`
- `y_change_cgm_time_in_range_70_180_pct`
- `y_weight_change_kg`

### 7.3 结局统一原则

- HbA1c 优先使用中心实验室/STA 结果；缺失时才回退到本地 HbA1c。
- CGM TIR 采用 70-180 mg/dL 范围。
- TIR 改善至少 5 个百分点作为临床可解释阈值。
- 不同研究随访时点不完全一致，因此必须纳入 `study_id` 并做 study-specific 敏感性分析。

## 8. 特征集和消融实验

所有模型都应在预设特征集上运行：

| 特征集 | 内容 | 目的 |
|---|---|---|
| FS0 | 仅基线 HbA1c | 最小临床基准 |
| FS1 | 人口学 + study ID + 基线 HbA1c | 简单临床模型 |
| FS2 | FS1 + 体重/BMI + 糖尿病病程 | 标准临床模型 |
| FS3 | FS2 + 随机分组 | 给定治疗模型 |
| FS4 | FS3 + 基线胰岛素/CGM 使用变量 | 扩展临床模型 |
| FS5 | FS4 + 基线 CGM 指标 | CGM 增强模型 |
| FS6 | 所有 baseline `x_` 变量和缺失指示 | 最大基线模型 |

HbA1c 主分析重点比较 FS3/FS4；CGM 任务重点比较 FS5。

## 9. 候选模型

### 9.1 临床统计基线

必须包含：

- 多数类分类器和均值/中位数回归器。
- Ridge logistic regression。
- Lasso logistic regression。
- Elastic net logistic regression。
- 线性回归、Ridge、Lasso、Elastic net 回归。
- 如时间允许，加入 GAM 或 spline logistic model。

目的：提供临床可解释的强基线，满足审稿人对传统模型比较的要求。

### 9.2 传统机器学习

纳入：

- Random forest。
- ExtraTrees。
- RBF kernel SVM。
- k-nearest neighbors。
- Naive Bayes 弱基线。

### 9.3 梯度提升树

高优先级模型：

- XGBoost。
- LightGBM。
- CatBoost。
- scikit-learn HistGradientBoosting。

预期：这类模型很可能在表格临床数据中表现最强或接近最强。

### 9.4 AutoML 和集成模型

若计算资源允许，加入：

- AutoGluon Tabular。
- FLAML。
- Optuna-tuned stacking ensemble。
- Super Learner，组合 logistic regression、CatBoost、XGBoost、LightGBM、TabPFN 等模型预测。

注意：AutoML 必须嵌入训练折内，不能提前看到验证集或测试集结局。

### 9.5 深度表格模型

候选：

- MLP + 类别变量 embedding。
- Tabular ResNet。
- FT-Transformer。
- TabTransformer。
- SAINT。
- TabNet。

训练保护：

- 内层验证集 early stopping。
- Dropout 和 weight decay。
- 控制超参数搜索预算。
- 多随机种子重复。
- 如果深度模型不如树模型，应如实报告，不应过度调参。

### 9.6 微调或适配基础模型

本研究最合理的“微调模型”方向是表格基础模型，而不是通用文本 LLM。

主要候选：

- TabPFN zero-shot/in-context 分类和回归。
- TabPFN + 后验概率校准。
- 若版本和许可允许，TabPFN fine-tuning 或 adapter tuning。
- TabPFN embedding + calibrated logistic/ridge/GBDT head。

微调流程：

1. 先划分外层训练/测试折。
2. 所有预处理只在训练折拟合。
3. 若微调 TabPFN，只使用内层训练折更新权重。
4. 学习率、epoch、adapter 规模等只用内层验证折选择。
5. 外层测试折只评估一次。
6. 概率校准只使用训练折内的验证预测，不能使用外层测试集。

探索性自监督微调：

- 使用更多公开 JAEB baseline `x_` 变量作为无标签数据。
- 采用 masked feature reconstruction 或 denoising objective。
- 不使用外层测试折的结局标签。
- 再在任务标签上训练 supervised head。
- 与同架构从零训练比较。

### 9.7 LLM 微调

通用 LLM 微调不应作为主方案，因为当前数据是结构化表格变量而非临床文本。可作为探索性负对照：

- 将每行数据转成稳定文本模板。
- 微调一个小型开源模型或 API 模型做 HbA1c 改善分类。
- 与 logistic regression、CatBoost 等强表格模型比较。
- 除非外部验证和校准明显优越，否则不应强调 LLM 优势。

预期风险：样本量小、过拟合、校准差、解释性弱。

## 10. 预处理流程

所有预处理必须封装在 scikit-learn pipeline 或等价 fold-contained pipeline 内。

### 10.1 数值变量

- 使用原始 baseline 数值列和 `_missing` 缺失指示。
- 在训练折内做中位数插补。
- 线性模型、SVM、KNN、神经网络需要标准化。
- 树模型通常不需要标准化。

### 10.2 分类变量

- 线性/SVM/树模型可使用 one-hot encoding。
- CatBoost 可使用原生类别变量处理。
- 深度模型使用 embedding。
- 训练折中少于 5 例的稀有类别合并为 `rare`。

### 10.3 类别不平衡

首选：

- class weight 或 loss weighting。

敏感性分析：

- SMOTE 或随机过采样，但必须仅在内层训练折内执行。

不能在交叉验证划分前做过采样。

## 11. 验证设计

### 11.1 主要内部验证

采用 repeated nested cross-validation：

- 外层：5 折，若计算允许重复 5 次。
- 内层：3-5 折用于超参数选择。
- 分类任务按结局和 study 分层。
- 显式按 participant ID 分组，虽然当前表每人一行。

主要性能使用外层测试折预测汇总得到。

### 11.2 外部可迁移性验证

采用 leave-one-study-out：

- 每次留出一个 study 作为测试集。
- 在其余 study 内完成调参。
- 在留出 study 上评估。
- 对有足够结局的 study 重复。

CGM TIR 任务仅限 WISDM、CITY、SENCE 三个具有 CGM 汇总的研究。

### 11.3 时间外部验证

当前不适用。JAEB 去标识化数据中的日期被平移或类似合成日期，不能作为真实时间序列外部验证。

### 11.4 最终模型

benchmark 完成后，可用全部可用开发数据重训最佳模型。该模型应标注为 final refit model，而不是独立验证模型。

## 12. 超参数调优

建议使用 Optuna 或 randomized search。内层搜索预算：

| 模型 | 每个外层 split 的 trial 数 | 说明 |
|---|---:|---|
| Logistic/ridge/lasso | 20 | 正则化强度和 penalty |
| Random forest/ExtraTrees | 50 | 树数、深度、叶节点最小样本 |
| XGBoost/LightGBM/CatBoost | 75-150 | learning rate、depth、subsampling、正则化 |
| SVM | 30 | C、gamma、class weight |
| MLP/ResNet | 50 | 宽度、深度、dropout、weight decay、学习率 |
| FT-Transformer/TabTransformer/SAINT | 50 | hidden dim、heads、layers、dropout、学习率 |
| TabNet | 50 | n_d、n_a、n_steps、gamma、lambda_sparse |
| TabPFN | 0-20 | 通常少调参，主要调校准器 |

所有 boosting 和神经网络模型都应使用 early stopping。

## 13. 性能指标

### 13.1 分类指标

主要指标：

- AUROC。

重要次要指标：

- AUPRC。
- Balanced accuracy。
- 预设阈值下 sensitivity 和 specificity。
- F1 score。
- Brier score。
- Calibration-in-the-large。
- Calibration slope。
- 校准曲线。
- Expected calibration error 作为辅助指标。
- 决策曲线 net benefit。

Accuracy 可以报告，但不能作为唯一选择标准。

### 13.2 回归指标

主要指标：

- RMSE。

次要指标：

- MAE。
- R-squared。
- Spearman correlation。
- 按预测十分位绘制预测均值 vs 观察均值。
- 临床可接受误差率，如 HbA1c 变化预测误差 <=0.5 个百分点。

### 13.3 模型排名规则

主分类任务建议：

1. 先按外层 CV AUROC 排序。
2. 若模型校准明显差，除非重校准后改善，否则不作为最佳模型。
3. 在前几名模型中比较 leave-one-study-out AUROC 和 Brier score。
4. 若两个模型表现相近，优先选择更简单、更可解释的模型。
5. 不能只根据最终测试集表现选择最佳模型。

## 14. 统计推断

### 14.1 置信区间

- 对外层测试折汇总预测进行 participant-level bootstrap。
- leave-one-study-out 可用 study-level bootstrap 或随机效应 meta-analysis。
- 成对模型比较可使用 paired bootstrap 或 DeLong 类方法。

### 14.2 多重比较

由于模型很多，需要预设主模型集：

- Logistic ridge。
- Random forest。
- XGBoost。
- LightGBM。
- CatBoost。
- TabPFN。
- FT-Transformer。

其他模型标记为探索性。可使用 Benjamini-Hochberg FDR，或明确报告未校正区间并说明探索性。

### 14.3 样本量和事件数

主分类任务有 940 名受试者、246 个阳性事件，属于中等样本量。复杂深度模型和微调模型必须强正则化，并以外部可迁移性结果判断是否可靠。

## 15. 校准和临床效用

### 15.1 校准

对候选最佳模型报告：

- 校准曲线。
- Calibration-in-the-large。
- Calibration slope。
- Brier score。
- Platt scaling、isotonic regression 或 temperature scaling，但必须只在训练/验证折内完成。

### 15.2 决策曲线分析

对前 3-5 个模型做 decision curve analysis：

- HbA1c 改善。
- 随访 HbA1c <7%。
- TIR 改善 >=5 个百分点。

阈值概率应预先设定，例如 HbA1c 改善任务可考虑 10%-50%，取决于模型用于加强随访、增加教育、或辅助治疗选择。

## 16. 可解释性和错误分析

### 16.1 全局解释

使用：

- 惩罚回归系数。
- 树模型 SHAP。
- 分组 permutation importance。
- Partial dependence 或 accumulated local effects。

预期重要预测因子：

- 基线 HbA1c。
- 年龄和 study 人群。
- 随机分组。
- 基线 CGM TIR 和低血糖指标。
- 基线 BMI/体重。
- 糖尿病病程。

### 16.2 个体解释

选取代表性个体展示：

- 预测概率。
- 推高/降低预测风险的主要特征。
- 与临床判断是否一致。

### 16.3 错误分析

按以下维度分析 false positives 和 false negatives：

- study。
- 基线 HbA1c 分层。
- 治疗臂。
- 年龄组。
- 种族/族裔，样本量允许时。
- 是否有基线 CGM。

## 17. 公平性和亚组评价

亚组：

- Study。
- 年龄组：幼儿、青少年/年轻成人、成人、老年人。
- 性别。
- 种族。
- 族裔。
- 基线 HbA1c：<7.5、7.5-8.5、>8.5。
- 治疗臂。

在样本量允许时报告：

- AUROC。
- AUPRC。
- 校准。
- 选定阈值下 sensitivity/specificity。
- 假阳性率和假阴性率。

小样本亚组不能做过强公平性结论。

## 18. 异质性治疗效应分析

该部分作为次要/探索性分析，因为不同研究干预差异较大。

在每个合适的平行组 RCT 内分别估计：

- Binary HbA1c improvement 的 CATE。
- Continuous HbA1c change 的 CATE。

候选方法：

- Causal forest。
- R-learner。
- X-learner。
- Doubly robust learner。

只使用基线协变量。不要跨不兼容干预直接解释治疗效应。

建议研究：

- WISDM：CGM vs BGM。
- CITY：CGM vs BGM。
- SENCE：三臂 CGM/行为干预比较。
- METFORMIN_T1D：二甲双胍 vs 安慰剂。
- REPLACE-BG：CGM-only vs CGM+BGM。

FLAIR 需要先构建 period-level crossover 数据后再做正式因果分析。

输出：

- 平均治疗效应和置信区间。
- CATE 分布。
- 主要 effect modifiers。
- 治疗效应预测校准。
- 若按模型分配治疗，预期结局与随机分配结局的 policy value 对比。

## 19. 敏感性分析

必须执行：

1. 仅使用中心/STA HbA1c，排除本地 HbA1c fallback。
2. 从 pooled HbA1c 模型中排除 FLAIR，因为其为交叉设计。
3. 仅训练 T1D 设备/CGM 相关试验，排除 Metformin。
4. 比较包含和不包含治疗臂的模型。
5. 比较包含和不包含 study ID 的模型。
6. 完整病例分析 vs 基线预测变量插补分析。
7. HbA1c 改善阈值改为 >=0.3、>=0.5、>=1.0 个百分点。
8. TIR 改善阈值改为 >=5 和 >=10 个百分点。
9. 对最佳模型至少重复 10 个随机种子。
10. 将 leave-one-study-out 作为核心稳健性分析。

## 20. 可复现计划

建议新增脚本：

- `scripts/model_benchmark.py`：主 benchmark 和嵌套交叉验证。
- `scripts/model_configs.yaml`：模型搜索空间和特征集配置。
- `scripts/evaluate_models.py`：性能指标、置信区间、校准、决策曲线。
- `scripts/interpret_models.py`：SHAP、permutation、ALE、错误分析。
- `scripts/hte_analysis.py`：异质性治疗效应分析。

建议输出：

- `results/model_performance_overall.csv`
- `results/model_performance_by_study.csv`
- `results/model_performance_by_subgroup.csv`
- `results/calibration_summary.csv`
- `results/decision_curve_summary.csv`
- `results/best_model_predictions.csv`
- `results/feature_importance.csv`
- `figures/roc_pr_curves.png`
- `figures/calibration_plots.png`
- `figures/decision_curves.png`
- `figures/shap_summary.png`

应记录所有随机种子、软件包版本、原始数据哈希和处理后数据哈希。

## 21. 推荐分析流程

### 阶段 1：数据审计

- 重新运行 `scripts/prepare_diabetes_rct_ml_dataset.py`。
- 确认结局样本量和缺失情况。
- 固化一份版本化的 `processed_ml_table.csv`。
- 为原始 ZIP 和 processed CSV 生成 SHA256。

### 阶段 2：基础 benchmark

- 使用 FS0-FS4。
- 先跑 logistic ridge、random forest、XGBoost、LightGBM、CatBoost。
- 使用 repeated nested CV。
- 生成第一版 leaderboard。

### 阶段 3：完整模型比较

- 加入 SVM、ExtraTrees、AutoML、MLP、FT-Transformer、TabNet、TabPFN。
- 对主要和次要结局建模。
- 执行 leave-one-study-out 验证。

### 阶段 4：校准和临床效用

- 对最佳候选模型重新校准。
- 做决策曲线。
- 选择最终候选模型。

### 阶段 5：解释性和亚组分析

- 生成 SHAP 或 permutation importance。
- 分析亚组性能。
- 做临床错误分析。

### 阶段 6：异质性治疗效应

- 在单个 RCT 内运行 causal forest 和 doubly robust learner。
- 比较模型治疗策略的 policy value。
- 保持谨慎结论。

### 阶段 7：论文材料

- 完成 TRIPOD+AI checklist。
- 完成 PROBAST+AI 风险偏倚表。
- 准备代码和数据可用性声明。
- 准备可复现性附录。

## 22. 预期审稿质疑和应对

| 可能质疑 | 设计应对 |
|---|---|
| 数据集异质性太强 | 使用 study ID、study-specific 报告、leave-one-study-out 验证和敏感性分析 |
| Accuracy 临床意义不足 | 报告 AUROC、AUPRC、Brier、校准、决策曲线和临床阈值 |
| 深度模型过拟合 | 使用嵌套 CV、early stopping、调参预算限制和外部验证 |
| RCT 数据不能直接证明临床效用 | 定位为回顾性二次分析和 benchmark，前瞻性验证作为未来工作 |
| 治疗臂跨研究不可比 | 区分给定治疗预测和单研究内 HTE 分析 |
| 缺失数据可能导致偏倚 | 报告缺失，比较插补和完整病例，不插补结局 |
| 基础模型概念炒作 | 将 TabPFN/微调模型作为 benchmark 分支，与强 GBDT 基线公平比较 |

## 23. 顶刊投稿最低标准

投稿前应具备：

- 锁定的分析方案。
- 公开可复现代码。
- 清晰的数据来源清单和原始数据溯源。
- 嵌套交叉验证和 leave-one-study-out 验证。
- 校准和决策曲线分析。
- 敏感性分析。
- 亚组分析。
- 模型解释和错误分析。
- TRIPOD+AI checklist。
- PROBAST+AI 偏倚风险评估。
- 克制、可信的临床结论。

## 24. 建议优先实现的第一组实验

优先从以下实验开始，性价比最高，也最容易形成论文核心结果。

主要目标：

- `y_hba1c_improved_ge_0_5`

特征集：

- FS1、FS3、FS4、FS6。

模型：

- Logistic ridge。
- Random forest。
- XGBoost。
- LightGBM。
- CatBoost。
- FT-Transformer。
- TabNet。
- TabPFN。
- Super Learner ensemble。

验证：

- 5x5 repeated nested CV。
- Leave-one-study-out validation。

指标：

- AUROC。
- AUPRC。
- Brier。
- Calibration slope/intercept。
- Balanced accuracy。
- Decision curve。

选择规则：

- 只有当校准和 leave-one-study-out 表现都可接受时，才按验证 AUROC 选择最佳模型。

## 25. 参考来源

- JAEB Center public diabetes datasets: https://public.jaeb.org/datasets/diabetes
- TRIPOD+AI, EQUATOR summary and BMJ reference: https://www.equator-network.org/reporting-guidelines/tripod-statement/
- TRIPOD+AI statement, PubMed: https://pubmed.ncbi.nlm.nih.gov/38626948/
- PROBAST+AI risk-of-bias tool summary: https://www.latitudes-network.org/tool/probastai/
- CONSORT-AI extension, Nature Medicine: https://www.nature.com/articles/s41591-020-1034-x
- SPIRIT-AI extension, Nature Medicine: https://www.nature.com/articles/s41591-020-1037-7
- International Consensus on Time in Range, Diabetes Care/PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC6973648/
- ADA Standards of Care 2026 glycemic goals: https://diabetesjournals.org/care/article/49/Supplement_1/S132/163927/6-Glycemic-Goals-Hypoglycemia-and-Hyperglycemic
- TabPFN Nature paper/PubMed: https://pubmed.ncbi.nlm.nih.gov/39780007/
- TabPFN ICLR 2023 OpenReview: https://openreview.net/forum?id=cp5PvcI6w8_
- Why tree-based models still outperform deep learning on tabular data: https://arxiv.org/abs/2207.08815
- Tabular Data: Deep Learning is Not All You Need: https://arxiv.org/abs/2106.03253
- Revisiting Deep Learning Models for Tabular Data: https://openreview.net/forum?id=i_Q1yrOegLY
- TabNet: Attentive Interpretable Tabular Learning: https://ojs.aaai.org/index.php/AAAI/article/view/16826
- Calibration in predictive analytics: https://link.springer.com/article/10.1186/s12916-019-1466-7
- Decision curve analysis original paper/PubMed: https://pubmed.ncbi.nlm.nih.gov/17099194/

