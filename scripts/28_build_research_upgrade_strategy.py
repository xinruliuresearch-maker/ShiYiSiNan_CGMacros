from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAMP = "2026-06-11"
OUT_DIR = PROJECT_ROOT / "outputs" / "integrated_mainline" / f"research_upgrade_strategy_{STAMP}"
NHANES_MIRROR = (
    Path(r"C:\Users\liu12\OneDrive\Desktop\NHANES_MetS_Project")
    / "result"
    / "integrated_mainline"
    / f"research_upgrade_strategy_{STAMP}"
)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def md_table(rows: list[dict[str, str]], cols: list[str]) -> str:
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(c, "")).replace("\n", "<br>") for c in cols) + " |")
    return "\n".join([header, sep, *body])


literature_sources = [
    {
        "domain": "PPGR精准营养",
        "source": "Zeevi et al., Cell 2015, Personalized Nutrition by Prediction of Glycemic Responses",
        "key_message": "800人真实生活CGM与46898餐显示相同食物的PPGR高度个体化, 模型整合饮食、人体测量、血液、活动和微生物组后可预测个体反应。",
        "how_to_use": "作为本研究CGMacros个体化PPGR建模的理论锚点, 但需强调本项目样本量更小, 目标是外部证据三角互证而非复制大队列。",
        "url": "https://pubmed.ncbi.nlm.nih.gov/26590418/",
    },
    {
        "domain": "PPGR精准营养",
        "source": "Berry et al., Nature Medicine 2020, PREDICT 1",
        "key_message": "1002名参与者的餐后甘油三酯、葡萄糖和胰岛素反应存在显著个体差异, 机器学习可预测餐后反应。",
        "how_to_use": "支持将PPGR作为动态代谢表型, 并提示应将血脂、胰岛素和生活方式作为后续扩展方向。",
        "url": "https://pubmed.ncbi.nlm.nih.gov/32528151/",
    },
    {
        "domain": "PPGR外部验证",
        "source": "Mendes-Soares et al., JAMA Network Open 2019",
        "key_message": "在无糖尿病个体中验证个体化PPGR预测框架, 讨论模型相对热量/碳水规则的增益。",
        "how_to_use": "作为外部验证、模型泛化和临床可解释性的参照。",
        "url": "https://pubmed.ncbi.nlm.nih.gov/30735238/",
    },
    {
        "domain": "CGMacros数据",
        "source": "CGMacros, PhysioNet 2025; Scientific Data manuscript noted as under review on PhysioNet page",
        "key_message": "45名参与者, 包含双CGM、餐食宏量营养、餐食照片、活动、血液指标和肠道微生物组, 连续10天自由生活场景。",
        "how_to_use": "当前研究的动态生理核心数据源; 需使用受试者层面分割和层级模型控制小样本风险。",
        "url": "https://physionet.org/content/cgmacros/",
    },
    {
        "domain": "CGM外部数据",
        "source": "Stanford Continuous Glucose Monitoring Database",
        "key_message": "提供CGM、表型、脂质、代谢组和蛋白组等下载数据, 可用于CGM表型和跨数据集泛化边界分析。",
        "how_to_use": "作为外部边界验证数据, 不强求与CGMacros同构, 重点验证MSI/CGM曲线表型的可迁移性。",
        "url": "https://cgmdb.stanford.edu/data/",
    },
    {
        "domain": "环境暴露与代谢",
        "source": "Trasande et al., Pediatrics 2013, Urinary Phthalates and Insulin Resistance in Adolescents",
        "key_message": "NHANES青少年中尿DEHP代谢物与胰岛素抵抗呈正相关, 横断面限制明确。",
        "how_to_use": "支持DEHP-胰岛素抵抗方向的既有流行病学背景, 同时提醒避免过度因果表述。",
        "url": "https://pubmed.ncbi.nlm.nih.gov/23958772/",
    },
    {
        "domain": "环境暴露与代谢",
        "source": "James-Todd et al., Environmental Health Perspectives 2012",
        "key_message": "NHANES女性中多种邻苯二甲酸酯代谢物与糖尿病及血糖/胰岛素抵抗指标相关。",
        "how_to_use": "为成人人群暴露-糖代谢关联提供基础证据, 后续应按性别和年龄分层。",
        "url": "https://pubmed.ncbi.nlm.nih.gov/22796563/",
    },
    {
        "domain": "环境暴露与代谢",
        "source": "Shoshtari-Yeganeh et al., Systematic review/meta-analysis 2019",
        "key_message": "系统综述和Meta分析提示邻苯二甲酸酯暴露与HOMA-IR升高相关。",
        "how_to_use": "作为环境暴露与胰岛素抵抗关系的证据等级补强, 用于引言和讨论的证据基座。",
        "url": "https://pubmed.ncbi.nlm.nih.gov/30734259/",
    },
    {
        "domain": "环境混合物方法",
        "source": "Yi et al., Frontiers in Public Health 2025, NHANES Circadian Syndrome",
        "key_message": "使用加权回归、RCS、BKMR和qgcomp研究NHANES中邻苯二甲酸酯混合暴露与Circadian Syndrome。",
        "how_to_use": "提示本项目NHANES模块应采用混合物模型、非线性和敏感性分析, 不只做单暴露回归。",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12245799/",
    },
    {
        "domain": "食物基质与淀粉消化",
        "source": "INFOGEST 2.0, Nature Protocols 2019",
        "key_message": "标准化静态体外胃肠消化协议, 涵盖口腔、胃和小肠阶段。",
        "how_to_use": "作为后续少量仿生体外消化验证的标准参照, 也可用于干实验消化可得性评分构建。",
        "url": "https://pubmed.ncbi.nlm.nih.gov/30886367/",
    },
    {
        "domain": "食物基质与淀粉消化",
        "source": "Food Matrix Effects for Modulating Starch Bioavailability, Annual Review 2021",
        "key_message": "食物基质、结构、加工、纤维、蛋白脂质相互作用可调节淀粉生物可利用性。",
        "how_to_use": "支撑将宏量营养之外的食物结构/加工信息纳入PPGR解释模型。",
        "url": "https://pubmed.ncbi.nlm.nih.gov/33395539/",
    },
    {
        "domain": "食物结构证据",
        "source": "The impact of starchy food structure on postprandial glycemic response, systematic review/meta-analysis",
        "key_message": "淀粉类食物微结构改变可影响餐后血糖和胰岛素反应。",
        "how_to_use": "支持建立食物基质编码体系, 并为后续少量体外消化验证选择样本。",
        "url": "https://pubmed.ncbi.nlm.nih.gov/34049391/",
    },
    {
        "domain": "报告规范",
        "source": "TRIPOD+AI Statement, BMJ 2024",
        "key_message": "更新临床预测模型报告规范, 覆盖回归和机器学习模型。",
        "how_to_use": "用于PPGR预测模块的报告清单、训练/验证分割、校准、缺失处理和模型透明度。",
        "url": "https://www.bmj.com/content/385/bmj-2023-078378",
    },
    {
        "domain": "偏倚评估",
        "source": "PROBAST+AI, BMJ 2025",
        "key_message": "更新预测模型风险偏倚与适用性评估工具。",
        "how_to_use": "用于在论文中主动评估模型偏倚风险, 对抗'模型过拟合/不可推广'质疑。",
        "url": "https://www.bmj.com/content/388/bmj-2024-082505",
    },
    {
        "domain": "证据综述规范",
        "source": "PRISMA 2020 Statement, BMJ 2021",
        "key_message": "系统综述和Meta分析27项报告规范及流程图。",
        "how_to_use": "用于Module A的系统化证据图谱, 使文献调研达到可审稿级别。",
        "url": "https://www.bmj.com/content/372/bmj.n71",
    },
    {
        "domain": "观察性研究规范",
        "source": "STROBE Statement",
        "key_message": "队列、病例对照和横断面观察性研究报告规范。",
        "how_to_use": "用于NHANES横断面模块和CGMacros观察性模块的报告清单。",
        "url": "https://www.strobe-statement.org/checklists/",
    },
    {
        "domain": "因果推断",
        "source": "Lawlor et al., IJE 2016/2017, Triangulation in aetiological epidemiology",
        "key_message": "通过整合偏倚结构不同的多种方法增强病因学推断可信度。",
        "how_to_use": "作为本研究总设计的核心方法论: 不把跨数据桥接伪装为直接因果, 而是主动构建三角互证。",
        "url": "https://pubmed.ncbi.nlm.nih.gov/28108528/",
    },
    {
        "domain": "因果推断",
        "source": "Hernan and Robins, AJE 2016, Target trial emulation",
        "key_message": "观察性数据分析应显式模拟目标试验以减少设计偏倚。",
        "how_to_use": "用于定义可检验问题: 在高MSI人群中降低高消化可得性餐食是否可降低PPGR。",
        "url": "https://pubmed.ncbi.nlm.nih.gov/26994063/",
    },
    {
        "domain": "敏感性分析",
        "source": "VanderWeele and Ding, Annals of Internal Medicine 2017, E-value",
        "key_message": "E-value用于量化未测混杂需要多强才能解释掉观察性关联。",
        "how_to_use": "用于NHANES和CGMacros关键关联的稳健性解释。",
        "url": "https://pubmed.ncbi.nlm.nih.gov/28693043/",
    },
    {
        "domain": "负对照",
        "source": "Shi et al., Selective Review of Negative Control Methods in Epidemiology",
        "key_message": "负对照可用于检测/校正残余混杂, 但需清楚假设和局限。",
        "how_to_use": "用于NHANES暴露模块设计负对照结局/暴露, 避免把相关性过度解释为因果。",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8118596/",
    },
    {
        "domain": "数据库",
        "source": "CDC NHANES laboratory data",
        "key_message": "提供邻苯二甲酸酯、血糖、胰岛素、血脂等周期性实验室数据和XPT下载。",
        "how_to_use": "用于扩展暴露周期、统一权重、补充协变量和开展混合物模型。",
        "url": "https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx?Component=Laboratory",
    },
    {
        "domain": "数据库",
        "source": "USDA FoodData Central",
        "key_message": "提供可下载CSV/JSON和REST API的食物营养数据库。",
        "how_to_use": "用于餐食重编码、营养密度、纤维/淀粉/糖/加工类别补充。",
        "url": "https://fdc.nal.usda.gov/download-datasets",
    },
    {
        "domain": "数据库",
        "source": "EPA CompTox Chemicals Dashboard",
        "key_message": "提供化学物质、毒性、暴露信息和批量检索。",
        "how_to_use": "用于DEHP/MEHP及替代增塑剂的化学-毒理证据扩展。",
        "url": "https://www.epa.gov/comptox-tools/comptox-chemicals-dashboard",
    },
    {
        "domain": "数据库",
        "source": "Comparative Toxicogenomics Database (CTD)",
        "key_message": "汇总化学-基因、化学-疾病和基因-疾病关系。",
        "how_to_use": "用于机制网络和通路富集, 构建DEHP-胰岛素信号/氧化应激/炎症证据图。",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC2686584/",
    },
]


evidence_gaps = [
    {
        "gap_id": "G1",
        "current_status": "NHANES显示DEHP氧化代谢物与MSI/代谢风险相关, 但横断面且单次尿样。",
        "why_reviewers_attack": "无法判断时间顺序; 尿液稀释、饮食和生活方式混杂可能解释关联。",
        "upgrade_action": "按STROBE和目标试验框架重写设计; 加入多周期NHANES、survey权重、肌酐/比重敏感性、RCS、WQS/qgcomp/BKMR、负对照和E-value。",
        "priority": "最高",
        "expected_output": "NHANES_robust_exposure_mixture_report; Supplementary Methods; sensitivity forest plot。",
    },
    {
        "gap_id": "G2",
        "current_status": "MSI作为跨数据集桥梁, 但可能被认为是人为构造或与PPGR结局过近。",
        "why_reviewers_attack": "如果MSI包含HbA1c/HOMA等糖代谢变量, 容易被质疑循环论证。",
        "upgrade_action": "构建两套MSI: exposure-facing MSI(不含直接PPGR近端指标)和 response-vulnerability index; 用PCA/因子分析/IRT与测量不变性检验。",
        "priority": "最高",
        "expected_output": "MSI_construct_validity_report; invariant loading plot; leave-one-domain-out sensitivity table。",
    },
    {
        "gap_id": "G3",
        "current_status": "CGMacros受试者45人, 餐次数多但个体层样本小。",
        "why_reviewers_attack": "把餐次当独立样本会夸大有效样本量, 预测模型可能过拟合。",
        "upgrade_action": "全部模型受试者层分割; 层级/贝叶斯混合模型; cluster bootstrap; subject-disjoint nested CV; 报告subject-level和meal-level两个层面的不确定性。",
        "priority": "最高",
        "expected_output": "CGMacros_hierarchical_PPGR_report; subject-disjoint CV performance; calibration curves。",
    },
    {
        "gap_id": "G4",
        "current_status": "食物基质评分主要来自干实验代理变量。",
        "why_reviewers_attack": "食物照片/描述转成基质评分存在主观性, 未被验证。",
        "upgrade_action": "建立双人标注手册、Kappa/ICC一致性; 接入USDA FDC; 将加工、液固形态、纤维、脂肪蛋白包埋、淀粉来源和烹调方式拆成可复核变量。",
        "priority": "高",
        "expected_output": "Food_matrix_codebook; annotation_reliability_table; FDC_linkage_table。",
    },
    {
        "gap_id": "G5",
        "current_status": "缺少真实外部验证数据支撑模型可迁移。",
        "why_reviewers_attack": "CGMacros内验证不足以证明广泛适用。",
        "upgrade_action": "引入Stanford CGM数据库、公开PPGR/CGM队列或PREDICT可得数据; 设定同构验证和异构边界验证两类目标。",
        "priority": "高",
        "expected_output": "External_boundary_validation_report; transportability heatmap。",
    },
    {
        "gap_id": "G6",
        "current_status": "机制图谱仍偏文献拼接。",
        "why_reviewers_attack": "缺少新机制数据或可重复的数据库证据链。",
        "upgrade_action": "系统接入CTD、CompTox、Reactome/KEGG/STRING/DisGeNET; 计算DEHP/MEHP相关基因与胰岛素信号、氧化应激、炎症、线粒体通路的富集和重叠。",
        "priority": "高",
        "expected_output": "Mechanism_network_enrichment_report; target-pathway network figure; evidence source table。",
    },
    {
        "gap_id": "G7",
        "current_status": "当前论文表达容易被读成DEHP直接导致PPGR异常。",
        "why_reviewers_attack": "没有同一受试者同时拥有DEHP生物标志物和餐后CGM数据。",
        "upgrade_action": "重命名为triangulated cross-dataset bridge-phenotype study; 明确claim hierarchy: association, susceptibility bridge, prediction utility, mechanism plausibility。",
        "priority": "最高",
        "expected_output": "Claim_hierarchy_box; revised title/abstract; reviewer-safe interpretation rules。",
    },
    {
        "gap_id": "G8",
        "current_status": "预测模型结果尚未完全按TRIPOD+AI/PROBAST+AI呈现。",
        "why_reviewers_attack": "缺少校准、决策曲线、缺失处理、模型版本、特征处理和可复现代码说明。",
        "upgrade_action": "补充TRIPOD+AI清单、PROBAST+AI自评、校准斜率/截距、Brier score、decision curve、conformal interval和模型卡。",
        "priority": "中高",
        "expected_output": "Prediction_model_card; TRIPOD_AI_checklist; PROBAST_AI_self_assessment。",
    },
]


dry_lab_modules = [
    {
        "module": "Module A",
        "name": "可审稿级系统化证据图谱",
        "objective": "把文献调研从叙述性综述升级为PRISMA风格证据地图。",
        "methods": "PubMed/Web of Science/Scopus检索式; 纳入环境邻苯二甲酸酯-代谢综合征/胰岛素抵抗、PPGR精准营养、CGM建模、食物基质消化四条证据线; 提取设计、样本、暴露/结局、方法、方向和偏倚。",
        "deliverables": "PRISMA流程图; evidence_map.csv; literature_bias_table.csv; 引言/讨论可直接引用段落。",
        "acceptance_criteria": "每条主张至少有1个高质量人体研究或方法指南支撑; 明确横断面/前瞻性/试验/数据库证据等级。",
    },
    {
        "module": "Module B",
        "name": "NHANES环境暴露模块重分析",
        "objective": "把DEHP氧化代谢物从单模型相关性升级为稳健的混合暴露和敏感性证据。",
        "methods": "整合2005-2018或可用周期; survey design; 多重插补; creatinine covariate和creatinine-standardized双路线; RCS; WQS/qgcomp/BKMR; 分层; E-value; 负对照。",
        "deliverables": "weighted regression table; mixture model plot; dose-response curves; sensitivity matrix。",
        "acceptance_criteria": "关键方向在至少3类模型中一致; 报告不一致而非隐藏; 明确不能做因果结论。",
    },
    {
        "module": "Module C",
        "name": "MSI构念效度和跨数据集桥接",
        "objective": "使MSI从项目内部指标变成可防守的代谢易感性构念。",
        "methods": "PCA/因子分析; IRT或加权评分; leave-one-domain-out; 不含血糖近端指标的exposure-facing MSI; 跨NHANES/CGMacros分布校准; measurement invariance。",
        "deliverables": "MSI variants; loading heatmap; invariance report; construct validity appendix。",
        "acceptance_criteria": "主结论不依赖单一MSI版本; 近端糖代谢指标剔除后仍有可解释信号。",
    },
    {
        "module": "Module D",
        "name": "CGMacros PPGR层级建模",
        "objective": "把餐次级结果转化为受试者层面可信推断。",
        "methods": "meal nested within participant; random intercept/random slope; pre-meal glucose, time-of-day, activity, sleep proxy, meal size; functional curve phenotypes; cluster bootstrap。",
        "deliverables": "hierarchical model report; subject-level uncertainty intervals; curve phenotype atlas。",
        "acceptance_criteria": "所有显著性均以受试者聚类不确定性为主; 预测性能使用受试者层留出。",
    },
    {
        "module": "Module E",
        "name": "食物基质和消化可得性评分",
        "objective": "证明PPGR不只是碳水量, 还受食物结构、加工和复合基质调节。",
        "methods": "餐食照片/描述双人标注; USDA FDC营养补全; 加工等级、液固、淀粉来源、纤维、蛋白脂肪包埋、烹调方式; score reliability。",
        "deliverables": "food_matrix_codebook; FDC linkage; digestibility availability score; reliability table。",
        "acceptance_criteria": "Kappa/ICC达到可接受水平; 评分与PPGR关联在碳水量调整后仍提供增量解释。",
    },
    {
        "module": "Module F",
        "name": "外部边界验证",
        "objective": "将论文从内部数据探索提升为可推广边界明确的研究。",
        "methods": "Stanford CGM数据库; 公开PPGR/CGM队列; 构造可迁移CGM曲线表型; 训练于CGMacros, 测试外部或反向测试; 报告失败边界。",
        "deliverables": "external_validation_protocol; harmonized_variables.csv; transportability report。",
        "acceptance_criteria": "至少完成一个外部数据集的同类指标复现或边界验证; 不同构时明确不可比原因。",
    },
    {
        "module": "Module G",
        "name": "机制数据库网络",
        "objective": "把机制讨论从叙述性文献升级为可复核数据库证据。",
        "methods": "CompTox/CTD提取DEHP/MEHP相关基因疾病; Reactome/KEGG/GO富集; STRING网络; 与胰岛素信号、氧化应激、炎症、线粒体通路交集。",
        "deliverables": "chemical_gene_network; pathway_enrichment_table; mechanism_evidence_figure。",
        "acceptance_criteria": "每个机制边有数据库来源; 网络结论不作为直接机制证明, 只作为生物学可行性。",
    },
    {
        "module": "Module H",
        "name": "预测模型规范化",
        "objective": "使PPGR预测模块符合高水平期刊对AI/ML报告的基本要求。",
        "methods": "TRIPOD+AI清单; PROBAST+AI自评; nested subject-disjoint CV; calibration; decision curve; SHAP/partial dependence; conformal interval。",
        "deliverables": "model_card.md; TRIPOD_AI_checklist.csv; calibration plots; decision curve。",
        "acceptance_criteria": "性能报告不只AUC/R2, 包括校准和临床/营养决策价值; 特征处理完全可复现。",
    },
    {
        "module": "Module I",
        "name": "论文叙事和审稿防御",
        "objective": "把分散结果统一为一条主线, 并提前回应审稿人质疑。",
        "methods": "claim hierarchy; graphical abstract; target journal fit; reviewer attack-response matrix; limitations as design features。",
        "deliverables": "revised title/abstract; figure-to-claim map; reviewer_response_prebuttal。",
        "acceptance_criteria": "每张图只支撑一个清晰主张; 所有因果语言经过审核; 结果链条从人群到动态表型再到机制可行性。",
    },
]


database_plan = [
    {
        "database": "NHANES laboratory + demographics + diet + examination",
        "priority": "P0",
        "purpose": "扩展DEHP/邻苯二甲酸酯、代谢综合征、胰岛素抵抗、饮食与协变量。",
        "download_or_access": "CDC XPT files via NHANES search pages; cycles按变量可用性统一。",
        "integration": "R survey包或Python statsmodels处理复杂抽样; 统一SEQN、权重、周期和LOD变量。",
        "url": "https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx?Component=Laboratory",
    },
    {
        "database": "CGMacros",
        "priority": "P0",
        "purpose": "主CGM-餐食-个体表型数据源。",
        "download_or_access": "PhysioNet项目页; 注意数据使用协议和引用。",
        "integration": "餐次窗口提取, 受试者层分割, meal-photo/food description与宏量营养、活动和血液指标合并。",
        "url": "https://physionet.org/content/cgmacros/",
    },
    {
        "database": "USDA FoodData Central",
        "priority": "P0",
        "purpose": "补充食品营养、纤维、糖、淀粉代理、食品类别和加工线索。",
        "download_or_access": "CSV/JSON批量下载或API; API需key。",
        "integration": "餐食文本/图像描述到FDC food item的半自动匹配; 保留match confidence。",
        "url": "https://fdc.nal.usda.gov/download-datasets",
    },
    {
        "database": "Stanford CGM Database",
        "priority": "P1",
        "purpose": "CGM表型和外部边界验证。",
        "download_or_access": "网站直接下载CGM、表型、脂质、代谢组、蛋白组CSV。",
        "integration": "提取与CGMacros同定义的CGM曲线和变异性表型; 若缺餐食, 用于subject-level metabolic vulnerability外部验证。",
        "url": "https://cgmdb.stanford.edu/data/",
    },
    {
        "database": "EPA CompTox Chemicals Dashboard",
        "priority": "P1",
        "purpose": "DEHP、MEHP及替代塑化剂化学与毒理证据。",
        "download_or_access": "Dashboard和batch search; 可下载多种数据流。",
        "integration": "化学ID映射、暴露/毒性端点、替代增塑剂扩展分析。",
        "url": "https://www.epa.gov/comptox-tools/comptox-chemicals-dashboard",
    },
    {
        "database": "Comparative Toxicogenomics Database",
        "priority": "P1",
        "purpose": "化学-基因-疾病网络和机制富集。",
        "download_or_access": "CTD下载或页面检索; 若主站访问不稳定, 可用文献和镜像数据。",
        "integration": "DEHP/MEHP相关基因与insulin resistance, oxidative stress, inflammation, mitochondrial dysfunction交集。",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC2686584/",
    },
    {
        "database": "Reactome/KEGG/GO/STRING/DisGeNET",
        "priority": "P2",
        "purpose": "机制通路富集与网络可视化。",
        "download_or_access": "API或R/Python包访问; 需记录版本日期。",
        "integration": "将CTD/CompTox基因集做富集; 输出机制网络图和补充表。",
        "url": "https://reactome.org/",
    },
    {
        "database": "PREDICT/其他PPGR队列",
        "priority": "P2",
        "purpose": "若可获得, 用于更强外部验证和精准营养参照。",
        "download_or_access": "公开受限或申请制, 先完成可得性审查。",
        "integration": "只纳入变量定义可对齐的数据; 作为扩展而非当前论文必需前提。",
        "url": "https://clinicaltrials.gov/study/NCT03479866",
    },
]


reviewer_attacks = [
    {
        "reviewer_concern": "你们没有同一批受试者同时测DEHP和PPGR, 为什么能把两者放在一起?",
        "best_response": "承认不是直接中介或同一样本因果链, 将设计定义为cross-dataset bridge-phenotype triangulation。NHANES提供环境暴露-代谢易感性证据, CGMacros验证代谢易感性对PPGR的动态意义, 机制数据库和食物基质分析提供生物学可行性。",
        "needed_analysis": "Claim hierarchy; bias-structure table; no direct mediation wording.",
    },
    {
        "reviewer_concern": "NHANES横断面暴露可能被饮食、肥胖和尿液稀释混杂。",
        "best_response": "使用复杂抽样权重、多种尿液稀释处理、分层、负对照、E-value和混合物模型, 并将结论限定为关联和易感表型。",
        "needed_analysis": "Creatinine sensitivity; RCS; qgcomp/WQS/BKMR; E-value.",
    },
    {
        "reviewer_concern": "CGMacros只有45人, 餐次级N不能代表真实统计功效。",
        "best_response": "主推断以受试者为聚类单位, 使用层级模型和受试者层留出验证, 餐次级样本只作为重复测量提高表型估计精度。",
        "needed_analysis": "Mixed models; cluster bootstrap; leave-subject-out validation.",
    },
    {
        "reviewer_concern": "MSI像事后构造的指数。",
        "best_response": "预先定义MSI构建规则, 报告PCA/因子载荷、内部一致性、留一域敏感性和跨数据分布校准, 并提供不含近端糖代谢变量的版本。",
        "needed_analysis": "Construct validity and sensitivity report.",
    },
    {
        "reviewer_concern": "食物基质评分主观。",
        "best_response": "提供标注手册、双人标注一致性、FDC客观营养变量和消化文献支持, 将其作为解释性增强而非单独因果证据。",
        "needed_analysis": "Codebook; inter-rater reliability; FDC linkage.",
    },
    {
        "reviewer_concern": "机器学习模型过拟合, 预测价值不清楚。",
        "best_response": "按TRIPOD+AI和PROBAST+AI报告, 用subject-disjoint nested CV、校准、决策曲线、置信区间和模型卡展示透明度。",
        "needed_analysis": "TRIPOD+AI checklist; PROBAST+AI self-assessment; calibration and decision curves.",
    },
    {
        "reviewer_concern": "机制只是推测。",
        "best_response": "把机制定位为plausibility layer, 使用CTD/CompTox/Reactome/KEGG/STRING等可复核数据库生成证据网络, 不声称直接机制被证明。",
        "needed_analysis": "Database-backed mechanism network and enrichment.",
    },
]


roadmap = [
    {
        "week": "Week 1",
        "focus": "重写研究问题和claim hierarchy",
        "computer_tasks": "完成题目、摘要、DAG、证据链图、允许/禁止结论清单; 固化变量字典。",
        "success_metric": "任何一段讨论都不再出现直接DEHP-to-PPGR因果化表述。",
    },
    {
        "week": "Week 2",
        "focus": "NHANES稳健性补强",
        "computer_tasks": "下载/核对周期变量; survey加权; creatinine/LOD/缺失处理; 单暴露+混合物模型。",
        "success_metric": "输出一张主结果表、一张混合物图、一张敏感性矩阵。",
    },
    {
        "week": "Week 3",
        "focus": "MSI构念效度",
        "computer_tasks": "构建exposure-facing MSI和response-vulnerability index; PCA/因子/留一域; 分布校准。",
        "success_metric": "主结论在至少2种MSI版本中方向一致或解释清楚。",
    },
    {
        "week": "Week 4",
        "focus": "CGMacros层级PPGR模型",
        "computer_tasks": "重算餐次窗口; functional curve features; mixed models; cluster bootstrap。",
        "success_metric": "所有关键P值/CI以受试者聚类不确定性为准。",
    },
    {
        "week": "Week 5",
        "focus": "食物基质与FDC",
        "computer_tasks": "制定codebook; 半自动FDC匹配; 标注一致性; 消化可得性评分。",
        "success_metric": "评分在碳水量调整后仍有增量解释或明确无增量。",
    },
    {
        "week": "Week 6",
        "focus": "外部边界验证",
        "computer_tasks": "下载Stanford CGM数据; 对齐CGM表型; 完成transportability/boundary report。",
        "success_metric": "至少一个外部数据集完成可比或不可比的正式边界结论。",
    },
    {
        "week": "Week 7",
        "focus": "机制网络",
        "computer_tasks": "CompTox/CTD基因集; 通路富集; DEHP-oxidative stress-insulin signaling网络图。",
        "success_metric": "每条机制边均可追溯到数据库或文献来源。",
    },
    {
        "week": "Week 8",
        "focus": "论文升级和审稿预防",
        "computer_tasks": "按AJCN/Nature Food风格重写全文; TRIPOD+AI/STROBE/PRISMA补充材料; 重做图表说明。",
        "success_metric": "主文只保留4-6个强图; 补充材料承载全部敏感性和方法透明度。",
    },
]


target_journals = [
    {
        "journal_tier": "冲刺",
        "journal": "Nature Food / Cell Reports Medicine / Nature Communications",
        "fit": "需要外部验证和机制数据库或少量实验验证较强, 叙事必须从'单数据分析'升级为三角互证框架。",
        "minimum_extra_needed": "至少完成NHANES混合物模型、CGMacros层级模型、外部边界验证、机制网络和食物基质可靠性。",
    },
    {
        "journal_tier": "高水平营养方向",
        "journal": "American Journal of Clinical Nutrition / Clinical Nutrition / Journal of Nutrition",
        "fit": "适合以PPGR、食物基质、代谢易感性和人群暴露为主线, 方法透明度要求高。",
        "minimum_extra_needed": "NHANES survey严谨重分析, CGMacros subject-disjoint验证, 食物基质评分可靠性。",
    },
    {
        "journal_tier": "环境健康方向",
        "journal": "Environment International / Environmental Health Perspectives / Environmental Research",
        "fit": "若强化DEHP混合暴露、代谢综合征和机制网络, 可偏环境流行病学。",
        "minimum_extra_needed": "暴露模块需最强, 包括多周期、混合物模型、负对照和敏感性分析。",
    },
    {
        "journal_tier": "方法/数据整合方向",
        "journal": "Patterns / npj Digital Medicine / Scientific Data companion analysis",
        "fit": "若强调CGM动态表型、跨数据集桥接和可复现开放流程, 可作为数字健康/数据科学论文。",
        "minimum_extra_needed": "预测模型需符合TRIPOD+AI/PROBAST+AI, 外部验证和代码复现要充分。",
    },
]


optional_bionic = [
    {
        "stage": "样本选择",
        "design": "从CGMacros中选8-12个代表餐食: 高/低碳水, 高/低食物基质保护, 高/低预测PPGR, 高/低MSI交互效应。",
        "endpoint": "餐食原始图像/配方、FDC营养匹配、干实验消化可得性分数。",
    },
    {
        "stage": "仿生消化",
        "design": "使用陈晓东教授体外消化仿生系统或INFOGEST参照条件, 记录口腔/胃/小肠阶段。",
        "endpoint": "葡萄糖释放曲线、淀粉水解率、消化速率常数、释放AUC。",
    },
    {
        "stage": "物理化学表征",
        "design": "测定粒径、黏度/流变、含水率、可溶性固形物、微结构图像(若可行)。",
        "endpoint": "解释为什么同等碳水餐食PPGR不同。",
    },
    {
        "stage": "整合分析",
        "design": "将体外释放AUC与CGM PPGR、食物基质评分和MSI交互项比较。",
        "endpoint": "检验干实验评分是否可被体外消化动力学部分验证。",
    },
]


def build_report() -> str:
    module_cols = ["module", "name", "objective", "methods", "deliverables", "acceptance_criteria"]
    gap_cols = ["gap_id", "current_status", "why_reviewers_attack", "upgrade_action", "priority"]
    roadmap_cols = ["week", "focus", "computer_tasks", "success_metric"]
    journal_cols = ["journal_tier", "journal", "fit", "minimum_extra_needed"]

    return f"""
# 高水平期刊导向研究升级方案

生成日期: {STAMP}

## 一句话总判断

当前研究已经具备一个有潜力的跨数据整合雏形: NHANES环境暴露与代谢易感性, CGMacros动态餐后血糖反应, 食物基质解释层, 以及可视化论文包。但如果目标是高水平期刊, 现在最大的风险不是图表不够多, 而是证据链容易被审稿人认为'把两个不同数据集硬连成因果链'。因此下一步不应继续堆砌图, 而应把研究重构为一项**三角互证的跨数据桥接表型研究**。

## 建议主线

推荐标题方向:

**Environmental-metabolic susceptibility and food-matrix-dependent postprandial glycemic vulnerability: a triangulated NHANES-CGMacros study**

中文主线:

**以邻苯二甲酸酯氧化代谢暴露相关的代谢易感性为人群锚点, 以CGM餐后曲线为动态生理锚点, 以食物基质和消化可得性为机制解释锚点, 构建一个可复核、不过度因果化的个体化餐后血糖脆弱性证据链。**

## 可以主张什么, 不应主张什么

可以主张:

1. NHANES中邻苯二甲酸酯/DEHP氧化代谢物与代谢易感性表型相关。
2. CGMacros中代谢易感性表型与餐后血糖曲线脆弱性相关。
3. 食物基质和消化可得性解释了部分同等碳水下PPGR差异。
4. 外部数据库和机制网络支持氧化应激、炎症、胰岛素信号和线粒体功能作为生物学可行路径。
5. 该框架可用于识别'高代谢易感个体面对高消化可得性餐食'的高风险情境。

不应主张:

1. DEHP直接导致CGMacros参与者PPGR升高。
2. MSI是DEHP到PPGR的正式中介。
3. 当前CGMacros内部预测模型已经具备临床部署价值。
4. 食物基质评分已经等同于真实体内消化速度。

## 当前证据缺口矩阵

{md_table(evidence_gaps, gap_cols)}

## 干实验补强模块A-I

{md_table(dry_lab_modules, module_cols)}

## 后续8周执行路线

{md_table(roadmap, roadmap_cols)}

## 目标期刊定位

{md_table(target_journals, journal_cols)}

## 数据库接入优先级

优先级P0必须立即纳入下一轮分析; P1用于冲刺高水平期刊的关键补强; P2用于提高论文视野和外部边界。

## 推荐论文结构

1. Introduction: 从PPGR个体差异切入, 引出环境-代谢易感性和食物基质共同塑造餐后反应。
2. Methods: Triangulated cross-dataset bridge-phenotype design; NHANES exposure layer; CGMacros dynamic response layer; food matrix layer; mechanism database layer; prediction/reporting standards。
3. Results 1: NHANES中DEHP/邻苯二甲酸酯混合暴露与MSI/代谢风险。
4. Results 2: MSI构念验证和跨数据集分布校准。
5. Results 3: CGMacros中MSI、食物基质和PPGR曲线表型。
6. Results 4: 个体化预测模型的增量价值、校准和边界。
7. Results 5: 外部CGM边界验证与机制数据库网络。
8. Discussion: 三角互证如何增强可信度; 不能证明什么; 对精准营养和环境健康的意义。

## 最高优先级分析清单

1. 重新运行NHANES survey-weighted混合物模型: WQS, qgcomp, BKMR, RCS, E-value。
2. 重新构建MSI两个版本: exposure-facing MSI和response-vulnerability index。
3. CGMacros全部预测和统计推断改为subject-disjoint与层级模型。
4. 食物基质评分加codebook、FDC匹配和标注一致性。
5. 外部数据至少完成Stanford CGM边界验证。
6. 机制网络改为CTD/CompTox/Reactome/KEGG可复核流程。
7. 按TRIPOD+AI、PROBAST+AI、STROBE、PRISMA分别制作补充清单。

## 可选湿实验的最小高价值版本

如果后续恢复少量体外消化实验, 不建议大规模铺开。最有价值的是选择8-12个计算模型预测差异最大且机制上最有解释价值的餐食, 用仿生消化系统验证葡萄糖释放动力学是否支持干实验食物基质评分。这会显著提升Nature Food/AJCN方向的说服力。

## 文献和规范依据

详见 `03_literature_evidence_map.csv`。核心依据包括Zeevi Cell 2015、Berry Nature Medicine 2020、CGMacros/PhysioNet 2025、INFOGEST 2.0、TRIPOD+AI、PROBAST+AI、PRISMA 2020、STROBE、triangulation和target trial emulation方法学文献。
"""


def build_readme(files: list[str]) -> str:
    return f"""
# Research upgrade strategy package

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This folder contains a high-impact-journal-oriented upgrade plan for the integrated NHANES-CGMacros project.

## Central decision

Reframe the project as a triangulated cross-dataset bridge-phenotype study, not as a direct DEHP-to-PPGR causal mediation study.

## Files

{chr(10).join(f'- `{name}`' for name in files)}

## Immediate next move

Run the upgraded dry-lab pipeline in this order:

1. NHANES mixture and sensitivity analysis.
2. MSI construct validity and non-proximal variants.
3. CGMacros hierarchical PPGR modeling.
4. Food matrix codebook and FDC linkage.
5. External CGM boundary validation.
6. Database-backed mechanism network.
7. TRIPOD+AI/PROBAST+AI/STROBE/PRISMA reporting package.
"""


def build_qa(files: list[str]) -> str:
    return f"""
# Research upgrade strategy QA

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## File integrity

- Output directory: `{OUT_DIR}`
- Mirror directory: `{NHANES_MIRROR}`
- Total planned files excluding README: {len(files)}
- Encoding: UTF-8 for Markdown and UTF-8 with BOM for CSV, so Excel on Windows can read Chinese headers and content.

## Web verification notes

- CGMacros was checked on PhysioNet. The page lists version 1.0.0, publication date January 28, 2025, 45 participants, dual CGM, macronutrients, food photographs, physical activity, blood analyses and gut microbiome profiles.
- CDC NHANES laboratory search page was checked. Urinary phthalates/plasticizer metabolites are available across multiple cycles including 2005-2006 through 2017-2018, and fasting glucose/insulin files are listed for relevant cycles.
- USDA FoodData Central was checked. The download page provides CSV and JSON releases, including April 2026 downloads for major data types.
- Stanford CGM Database was checked. It provides phenotype, CGM, lipid, metadata, metabolomics and Olink data files.
- EPA CompTox Chemicals Dashboard was checked. The page describes chemistry, toxicity and exposure information for over one million chemicals and batch/advanced search functions.

## Interpretation guardrail

The package intentionally recommends a triangulated cross-dataset bridge-phenotype design. It does not recommend claiming direct DEHP-to-PPGR causality or formal mediation without same-participant exposure and CGM data.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    files = []

    report_path = OUT_DIR / "01_high_impact_research_upgrade_full_report.md"
    write_text(report_path, build_report())
    files.append(report_path.name)

    write_csv(OUT_DIR / "02_evidence_gap_matrix.csv", evidence_gaps)
    files.append("02_evidence_gap_matrix.csv")

    write_csv(OUT_DIR / "03_literature_evidence_map.csv", literature_sources)
    files.append("03_literature_evidence_map.csv")

    write_csv(OUT_DIR / "04_dry_lab_module_A_to_I_execution_plan.csv", dry_lab_modules)
    files.append("04_dry_lab_module_A_to_I_execution_plan.csv")

    write_csv(OUT_DIR / "05_database_download_and_integration_plan.csv", database_plan)
    files.append("05_database_download_and_integration_plan.csv")

    write_csv(OUT_DIR / "06_reviewer_attack_response_matrix.csv", reviewer_attacks)
    files.append("06_reviewer_attack_response_matrix.csv")

    write_csv(OUT_DIR / "07_no_wetlab_next_8_weeks_roadmap.csv", roadmap)
    files.append("07_no_wetlab_next_8_weeks_roadmap.csv")

    write_csv(OUT_DIR / "08_target_journal_positioning.csv", target_journals)
    files.append("08_target_journal_positioning.csv")

    write_csv(OUT_DIR / "09_optional_bionic_digestion_experiment_plan.csv", optional_bionic)
    files.append("09_optional_bionic_digestion_experiment_plan.csv")

    qa_path = OUT_DIR / "11_generation_QA.md"
    write_text(qa_path, build_qa(files))
    files.append(qa_path.name)

    index = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(PROJECT_ROOT),
        "output_dir": str(OUT_DIR),
        "mirror_dir": str(NHANES_MIRROR),
        "central_reframe": "triangulated cross-dataset bridge-phenotype study",
        "files": files,
        "core_guardrail": "No direct DEHP-to-PPGR causality or formal mediation is claimed without same-participant exposure and CGM data.",
    }
    index_path = OUT_DIR / "10_research_upgrade_strategy_index.json"
    write_text(index_path, json.dumps(index, ensure_ascii=False, indent=2))
    files.append(index_path.name)

    readme_path = OUT_DIR / "00_README_research_upgrade_strategy.md"
    write_text(readme_path, build_readme(files))

    NHANES_MIRROR.parent.mkdir(parents=True, exist_ok=True)
    if NHANES_MIRROR.exists():
        shutil.rmtree(NHANES_MIRROR)
    shutil.copytree(OUT_DIR, NHANES_MIRROR)

    print(f"Created research upgrade strategy package: {OUT_DIR}")
    print(f"Mirrored package: {NHANES_MIRROR}")
    print(f"Files: {len(files) + 1}")


if __name__ == "__main__":
    main()
