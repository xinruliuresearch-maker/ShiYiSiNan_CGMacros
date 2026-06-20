# npj Digital Medicine 投稿定位与后续研究计划

## 期刊定位

我将目标期刊按 **npj Digital Medicine** 理解。该刊关注数字/移动技术、虚拟医疗、AI 与 informatics 在临床和医疗转化中的应用。JAEB 血糖相图如果要匹配这个期刊，核心不能是“我们做了聚类”，而应是：

**从连续血糖监测数据中构建一个可复现、可解释、可验证的 CGM digital phenotype，用于组织糖尿病动态风险、预测随访改善，并提示相位分层治疗响应。**

## 当前结果整理

- 数据规模：2144 名受试者，8638 行 harmonized CGM summary，748 名具备基线 CGM 相图样本。
- 研究来源：14 个 JAEB 公开研究。
- 相位结构：稳定达标相: n=234; 高波动震荡相: n=182; 高血糖持续相: n=178; 昼夜节律紊乱相: n=97; 低血糖易感相: n=57。
- 相图稳定性：bootstrap ARI 中位数 0.826（IQR 0.755-0.890），silhouette 中位数 0.268。
- Nested CV：HbA1c 改善最佳 AUROC 0.802；TIR 改善最佳 AUROC 0.795。
- LOSO 泛化：HbA1c 改善最佳平均 AUROC 0.727；TIR 改善最佳平均 AUROC 0.754。
- HTE：低血糖易感相 的调整风险差最高，为 0.281（95% bootstrap CI 0.105-0.408）。
- 调整后相位主效应：TIR change 全局相位检验 p=0.057，应解释为趋势和风险结构，而非确认性因果证据。

## 适合 npj Digital Medicine 的主张

推荐题目：

**A reproducible glycaemic phase map from continuous glucose monitoring identifies digital phenotypes of treatment response in public diabetes trials**

核心主张：

1. CGM summary features can be transformed into a reproducible low-dimensional glycaemic state space.
2. The resulting phase map captures clinically interpretable digital phenotypes.
3. Phase phenotypes generalize across public JAEB studies with moderate predictive performance.
4. Phase membership organizes heterogeneous treatment response and can support a digital-care workflow.

## 需要克制的地方

1. 不说相位是已验证的生物学亚型。
2. 不说相图显著优于所有机器学习模型。
3. 不把 HTE 解释成确定临床推荐。
4. 不把 retrospective public-data result 说成 deployed digital medicine tool。

## 主要缺口

| 缺口 | 为什么重要 | 下一步 |
|---|---|---|
| Frozen external validation | npj Digital Medicine 会看重真实泛化 | 从 `jaeb_public_extra` 中挑未用数据集做冻结验证 |
| Raw CGM time-series phase transitions | 当前相图基于 summary，数字表型深度不够 | 解析可用原始 CGM，构建状态转移/动态轨迹 |
| Fairness and subgroup audit | 数字医学审稿会问可迁移性和偏倚 | 按年龄、性别、种族/族裔、研究、设备做校准和性能 |
| Clinical workflow | 需要从模型结果走向数字医疗应用 | 输出 phase-guided digital care workflow 和 net benefit |
| Prospective feasibility | 回顾性证据不足以支撑临床工具 | 设计 silent-mode CGM phase feedback pilot |

## 后续研究计划

### P0：投稿前必须补强

1. **冻结验证集**  
   从额外 JAEB 公共数据集中挑选未参与建模的数据集，锁定后只跑一次外部验证。输出 AUROC、AUPRC、Brier、calibration、phase distribution shift。

2. **算法卡与软件规范**  
   定义输入字段、CGM feature harmonization、order parameters、phase assignment、缺失处理、版本号、适用边界。输出 `phase_map_algorithm_card.md`。

3. **公平性/可迁移性审计**  
   按 age group、sex、race/ethnicity、study、baseline HbA1c、diabetes type/device context 报告 phase distribution、AUROC、Brier、calibration slope/intercept。

4. **临床效用图件**  
   将 decision curve、HTE、phase-based intervention focus 合成一张 digital care workflow 图，强调 silent mode / decision support，而非自动治疗建议。

5. **主文图重构**  
   Figure 1 数字表型算法；Figure 2 相位有效性；Figure 3 验证与校准；Figure 4 HTE 与 workflow。

### P1：提高命中率

1. **原始 CGM 时序升级**  
   如果 JAEB zip 中有原始 CGM 时间序列，构建 phase transition、entropy、dwell time、night-to-day transition，而不是只用 summary。

2. **Silent-mode prospective pilot**  
   60-100 名 CGM 用户，算法只后台运行，不改变治疗。评估 phase stability、clinician interpretability、patient burden、prospective prediction。

3. **开源复现包**  
   发布可复现 pipeline、toy data、environment file、figure reproduction script。

4. **报告规范**  
   对齐 TRIPOD-AI / prediction model reporting、digital health implementation 和 model card/algorithm card。

## Go/No-Go

若 frozen external validation 和 subgroup calibration 仍保持方向稳定，可按 npj Digital Medicine 正式研究论文推进。若冻结验证明显失败，应转向 diabetes informatics / methodological 或 hypothesis-generating 期刊定位。
