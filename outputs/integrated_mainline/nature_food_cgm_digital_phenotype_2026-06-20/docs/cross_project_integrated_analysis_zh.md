# 跨项目整合分析整理

生成日期：2026-06-17

本文件把三个本地项目整理为一条统一研究主线：

- `D:\NHANES_MetS_Project`
- `D:\ShiYiSiNan_CGMacros`
- `D:\ai for science`

## 一句话主线

环境塑化剂/DEHP 相关代谢易感性可能定义一类更容易出现餐后血糖曲线脆弱性的个体；这种脆弱性可在餐食级 CGM 数据中表现为更高 PPGR，并可在糖尿病干预 RCT 中进一步映射为可解释的血糖动力学相位和治疗响应异质性。

更稳妥的投稿表述不是“DEHP 直接导致餐后血糖异常”，而是：

> DEHP 氧化代谢谱与代谢易感性相关；代谢易感性与餐后血糖反应脆弱性相关；血糖相图可在真实糖尿病干预数据中提供动态分型、预测和治疗响应分层框架。

## 三个项目的角色

| 项目 | 主要角色 | 关键数据规模 | 最有用产物 |
|---|---|---:|---|
| `NHANES_MetS_Project` | 上游人群证据：DEHP 氧化代谢谱、HOMA-IR、HbA1c、TyG、TG/HDL-C、MetS | NHANES 2013-2018 主表 n=5,267；2003-2018 DEHP-only 验证 n=13,655 | `docs/research_strategy_plan_DEHP_metabolic_profile.md`，`result/DEHP_summary_continuous_models_2013_2018.csv`，`result/DEHP_summary_logistic_models_2013_2018.csv` |
| `ShiYiSiNan_CGMacros` | 中游动态表型：CGMacros 餐食级 PPGR、MSI-core、少样本个体化、外部 CGM/食物矩阵 | CGMacros 餐食级 n=1,498，受试者 n=40；NHANES dual MSI n=5,267 | `outputs/integrated_mainline/stage3_cgmacros_msi_ppgr/`，`outputs/integrated_mainline/stage4_prediction_personalization/`，`outputs/integrated_mainline/high_impact_publication_figures_tables_2026-06-11/` |
| `ai for science` | 下游临床干预证据：JAEB 糖尿病 RCT/干预数据、血糖相图、预测、治疗响应异质性 | JAEB 个体级 n=2,144；基线 CGM 相图 n=748 | `docs/high_impact_study_completion_report_zh.md`，`data/processed/glycemic_phase_features.csv`，`results/journal_adjusted_hte_by_phase.csv` |

## 已有核心证据

### 1. NHANES：DEHP 氧化代谢谱与代谢易感性

项目已形成较完整环境流行病学证据链。最适合作为主线的是“DEHP 氧化代谢谱”而非泛泛的“总 DEHP 暴露”。

关键结果摘录：

- `%Oxidative per 10 pp -> MSI-core`: 0.168 (0.065, 0.272), q=0.006, n=1,313。
- `ln(Oxidative/MEHP) -> MSI-core`: 0.183 (0.106, 0.259), q<0.001, n=1,313。
- `%Oxidative per 10 pp -> ln(HOMA-IR)`: 19.958% (6.896%, 34.617%), q=0.006, n=1,292。
- `%Oxidative per 10 pp -> HbA1c`: 0.110 (0.031, 0.188), q=0.012, n=2,671。

解释：这部分提供上游锚点，支持“DEHP oxidative profile -> metabolic susceptibility”。投稿时应强调横断面和残余混杂限制，避免因果化。

### 2. CGMacros：MSI-core 与餐后血糖脆弱性

CGMacros 提供餐食级动态证据，用于把人群代谢易感性连接到餐后血糖反应。

关键结果摘录：

- 餐食级样本 n=1,498，受试者 n=40。
- Low MSI: 570 餐，median iAUC 2h=1,792.6，high iAUC rate=0.184，median peak delta=34.3。
- High MSI: 447 餐，median iAUC 2h=2,515.0，high iAUC rate=0.315，median peak delta=49.8。
- 2h iAUC 模型中 `MSI-core`: 1.170 (0.597, 1.742), q<0.001。
- 2h peak delta 模型中 `MSI-core`: 18.883 (10.551, 27.214), q<0.001。

解释：MSI-core 是强风险分层变量；`carbs_10g × MSI-core` 交互方向为正但统计强度有限，因此主文应说“MSI 标识 PPGR vulnerability”，不宜过度声称“显著放大所有餐食碳水效应”。

### 3. JAEB：血糖动力学相图与干预响应

当前项目提供糖尿病 RCT/干预场景下的动态分型和治疗响应异质性证据。

关键结果摘录：

- 13 个 JAEB 公开糖尿病研究数据包已清洗，个体级表 n=2,144。
- 基线 CGM 相图样本 n=748。
- 相位分布：稳定达标相 n=234，高波动震荡相 n=182，高血糖持续相 n=178，昼夜节律紊乱相 n=97，低血糖易感相 n=57。
- HbA1c 改善预测：最佳内部 CV AUROC 约 0.800。
- TIR 改善预测：临床+CGM logistic ridge AUROC 约 0.792。
- Leave-one-study-out HbA1c 改善：logistic ridge 平均 AUROC 0.727。
- 相图 bootstrap 稳定性：ARI median 0.826。
- 调整后 HTE：低血糖易感相 adjusted risk difference 0.281 (0.105, 0.408)；稳定达标相 0.181 (0.095, 0.253)；高血糖持续相 0.180 (0.038, 0.311)。

解释：相图特征对预测 AUROC 的增量有限，但对解释分层、机制叙事、治疗响应异质性和临床框架有价值。调整后的相位-结局关联弱于未调整关联，应写成“风险结构和响应分层工具”，而不是独立因果因子。

## 建议整合成两篇论文，而不是一篇巨型论文

### 论文 A：环境代谢易感性与 PPGR 脆弱性

推荐主线：

`DEHP oxidative profile -> MSI-core -> CGMacros PPGR vulnerability -> 食物基质/少样本个体化`

主要使用：

- `D:\NHANES_MetS_Project`
- `D:\ShiYiSiNan_CGMacros`

最适合目标：

- AJCN / Clinical Nutrition
- Environment International
- Environmental Health Perspectives，需进一步补强同受试者或机制证据

主文保留：

- NHANES DEHP oxidative profile 与 MSI/HOMA-IR/HbA1c。
- CGMacros MSI high vs low 的 PPGR 分层。
- MSI-aware prediction / few-shot personalization。
- 食物基质与消化验证作为设计或补充，除非人工标注完成。

不建议主文展开：

- 死亡分析。
- 过大的机制网络。
- 所有外部 CGM 数据集。
- 未人工确认的食物图像/食物矩阵。

### 论文 B：血糖动力学相图与糖尿病干预响应

推荐主线：

`公开糖尿病 RCT/干预数据 -> 基线 CGM 相图 -> HbA1c/TIR 预测 -> 治疗响应异质性 -> 个体化干预框架`

主要使用：

- `D:\ai for science`
- 可把 CGMacros 的 PPGR vulnerability 作为背景，不强行合并数据。

最适合目标：

- npj Digital Medicine / Diabetes Technology & Therapeutics
- Journal of Biomedical Informatics
- BMJ Health & Care Informatics
- Diabetes Care 需更强临床验证和更严格单研究内验证

主文保留：

- 相图构建和稳定性。
- Leave-one-study-out 泛化。
- 校准、decision curve、nested CV。
- 相位分层治疗响应作为探索性 HTE。

下一步增强：

- 聚合原始 DeviceCGM 到日级/事件级特征。
- 在单个 RCT 内独立报告相图重建和 HTE。
- 对相位做跨研究 transportability 检验。

## 文件入口地图

### NHANES

| 用途 | 路径 |
|---|---|
| 项目总览 | `D:\NHANES_MetS_Project\README.md` |
| 关键结果索引 | `D:\NHANES_MetS_Project\docs\KEY_RESULTS_INDEX.md` |
| 高水平策略 | `D:\NHANES_MetS_Project\docs\research_strategy_plan_DEHP_metabolic_profile.md` |
| 主分析数据 | `D:\NHANES_MetS_Project\output\NHANES_2013_2018_master_analysis.csv` |
| 连续代谢终点模型 | `D:\NHANES_MetS_Project\result\DEHP_summary_continuous_models_2013_2018.csv` |
| 二分类结局模型 | `D:\NHANES_MetS_Project\result\DEHP_summary_logistic_models_2013_2018.csv` |
| 机制证据 | `D:\NHANES_MetS_Project\result\evidence_synthesis_DEHP_metabolic_project.xlsx` |

### CGMacros

| 用途 | 路径 |
|---|---|
| 项目总览 | `D:\ShiYiSiNan_CGMacros\README.md` |
| 关键输出索引 | `D:\ShiYiSiNan_CGMacros\00_PROJECT_ORGANIZATION\01_KEY_OUTPUTS_INDEX.md` |
| 当前高阶优化建议 | `D:\ShiYiSiNan_CGMacros\outputs\integrated_mainline\next_stage_high_tier_optimization_2026-06-11\00_next_stage_high_tier_optimization_report.md` |
| Stage 3 PPGR 报告 | `D:\ShiYiSiNan_CGMacros\outputs\integrated_mainline\stage3_cgmacros_msi_ppgr\stage3_cgmacros_msi_ppgr_report_2026-06-10.md` |
| Stage 4 个体化报告 | `D:\ShiYiSiNan_CGMacros\outputs\integrated_mainline\stage4_prediction_personalization\stage4_prediction_personalization_report_2026-06-10.md` |
| CGMacros dual MSI 餐食表 | `D:\ShiYiSiNan_CGMacros\outputs\integrated_mainline\high_impact_computational_upgrade_2026-06-11\01_cgmacros_dual_msi_meal_dataset.csv` |
| 出版图表包 | `D:\ShiYiSiNan_CGMacros\outputs\integrated_mainline\high_impact_publication_figures_tables_2026-06-11\README_high_impact_publication_figures_tables.md` |

### 当前 JAEB 相图项目

| 用途 | 路径 |
|---|---|
| 数据清洗报告 | `D:\ai for science\docs\cleaning_report.md` |
| 相图主报告 | `D:\ai for science\docs\glycemic_phase_research_report_zh.md` |
| 高水平完成报告 | `D:\ai for science\docs\high_impact_study_completion_report_zh.md` |
| 个体级主表 | `D:\ai for science\data\processed\processed_ml_table.csv` |
| CGM 汇总长表 | `D:\ai for science\data\processed\cgm_summary_long.csv` |
| 相图特征 | `D:\ai for science\data\processed\glycemic_phase_features.csv` |
| HTE 结果 | `D:\ai for science\results\journal_adjusted_hte_by_phase.csv` |
| 图表索引 | `D:\ai for science\docs\manuscript_tables_figures_index_zh.md` |

## 需要人工完成或确认的部分

1. CGMacros 食物图像/食物基质人工复核：已有自动标注和 FDC proxy，但高水平投稿前需要人工确认，尤其是 `manual_review=932` 的餐食。
2. NHANES 死亡分析样本量下降和 cause-specific Cox 失败需要重新审计；建议放补充，不放主文核心。
3. 如果目标是顶级期刊，需要同受试者 pilot：尿邻苯/DEHP 暴露、标准餐、CGM 曲线、代谢表型、食物基质在同一批人内闭环。
4. JAEB 原始 DeviceCGM 明细还没有充分聚合为日级和事件级动态特征；这会显著提升相图论文质量。
5. 三个项目的脚本路径和环境尚未完全统一。正式投稿前应建立统一 `README`、环境锁定、变量字典、样本流图和一键复现说明。

## 立即可执行的下一步

1. 当前项目优先：把 `data/raw/jaeb_public_extra` 中新增 JAEB 数据包分为 RCT、观察性、健康对照、营养/食物、补充表五类，并判断哪些能接入相图 pipeline。
2. JAEB 相图增强：从 DeviceCGM 生成日级 CV、TIR、LBGI/HBGI、MAGE、夜间低血糖、恢复时间、餐后窗口等特征。
3. 跨项目统一指标：把 CGMacros 的 PPGR vulnerability、NHANES 的 MSI-core、JAEB 的 phase order parameters 映射到同一概念表：glycemic burden、instability、hypoglycemic susceptibility、circadian disruption、resilience。
4. 写作层面拆成两篇论文，避免一篇文章同时承担环境流行病学、精准营养、糖尿病 RCT 相图三件大事。
5. 建立 `docs/cross_project_evidence_matrix.csv`，逐条记录每个证据点的来源、样本量、统计模型、强度、限制和可投稿位置。

## 总体判断

三个项目可以整合成一个更大的研究体系，但不应强行合并成单一分析数据集。最佳策略是“证据链整合、论文主题拆分”：

- NHANES + CGMacros：讲环境代谢易感性如何连接到餐后血糖脆弱性。
- JAEB：讲血糖动力学相图如何在糖尿病干预研究中提供可解释预测和治疗响应分层。

当前 `D:\ai for science` 最适合作为新的总控目录，用来保存跨项目索引、整合报告和后续统一分析脚本；两个外部项目保留原始目录结构，避免破坏已有复现链。
