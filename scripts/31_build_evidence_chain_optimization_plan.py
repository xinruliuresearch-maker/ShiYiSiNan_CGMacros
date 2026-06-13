from __future__ import annotations

import csv
import json
import shutil
from datetime import date
from pathlib import Path


TODAY = date.today().isoformat()
ROOT = Path(r"C:\Users\liu12\OneDrive\Desktop\ShiYiSiNan_CGMacros")
OUT = ROOT / "outputs" / "integrated_mainline" / f"evidence_chain_optimization_{TODAY}"
NHANES_MIRROR = (
    Path(r"C:\Users\liu12\OneDrive\Desktop\NHANES_MetS_Project")
    / "result"
    / "integrated_mainline"
    / f"evidence_chain_optimization_{TODAY}"
)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\n", "\r\n"), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def current_result_snapshot() -> list[dict[str, object]]:
    return [
        {
            "evidence_layer": "NHANES mixture epidemiology",
            "current_result": "qgcomp: exposure-facing MSI psi=0.067, p=0.0043, FDR=0.0057; response-vulnerability index psi=0.091, p=5.26e-7, FDR=2.10e-6; ln_HOMA-IR psi=0.148, p=6.71e-8; HbA1c psi=0.107, p=3.46e-6.",
            "interpretation": "支持DEHP相关混合暴露与代谢易感性/糖代谢异常相关，是全研究的人群锚点。",
            "remaining_weakness": "NHANES横断面、尿样单次测量、Python近似混合物模型，不能证明时间顺序或长期暴露。",
            "upgrade_need": "R survey/qgcomp/gWQS/bkmr正式复核；加入负对照、定量偏倚分析、尿稀释敏感性、多周期一致性。",
        },
        {
            "evidence_layer": "Dose-response and robustness",
            "current_result": "RCS: pct_oxidative_10与response-vulnerability index p=3.07e-7、exposure-facing MSI p=2.04e-6、ln_HOMA-IR p=0.0069；E-value最高约1.51。",
            "interpretation": "非线性剂量反应增加生物学可信度，但E-value提示未测混杂仍可能解释部分关联。",
            "remaining_weakness": "非线性趋势不能替代因果识别；E-value较温和。",
            "upgrade_need": "用DAG明确最小调整集，报告限制立场；增加negative control和quantitative bias analysis。",
        },
        {
            "evidence_layer": "Dual MSI construct",
            "current_result": "NHANES exposure-facing MSI与response-vulnerability index r=0.845；CGMacros r=0.876；CGMacros response-vulnerability index与旧MSI r=0.997。",
            "interpretation": "两个MSI版本共享代谢易感性核心，可分别承担暴露侧和反应侧任务。",
            "remaining_weakness": "response-vulnerability index与PPGR结果存在构念接近风险；旧MSI几乎等同反应易感性版本。",
            "upgrade_need": "主文明确两个MSI的用途边界；做leave-one-component-out和不含糖代谢组分的敏感性指数。",
        },
        {
            "evidence_layer": "CGMacros subject-disjoint PPGR model",
            "current_result": "iAUC R2: macro_only 0.110, macro_context 0.112, full_msi_foodmatrix 0.183；peak R2: 0.098, 0.139, 0.247；Pearson r最高0.471/0.523。",
            "interpretation": "MSI和食物基质在受试者留出条件下增加PPGR解释度。",
            "remaining_weakness": "CGMacros受试者数量有限，餐次多不能替代人多；模型仍是中等预测强度。",
            "upgrade_need": "严格按TRIPOD+AI/PROBAST+AI报告；增加外部数据和nested subject-disjoint bootstrap。",
        },
        {
            "evidence_layer": "Food matrix",
            "current_result": "食物基质类别kappa=0.841，digestibility ICC=0.971；FDC为query-level proxy匹配。",
            "interpretation": "已形成可复核干实验评分体系，支持同等宏量营养下食物结构差异。",
            "remaining_weakness": "仍缺少真实人工双评、逐项FDC匹配和消化动力学实验证据。",
            "upgrade_need": "双人盲法标注、裁决流程、FDC item-level匹配、NOVA/GI/GL/加工度/纤维结构编码；可选体外消化验证。",
        },
        {
            "evidence_layer": "External CGM boundary validation",
            "current_result": "Stanford challenge-level validation: 588 records, 38 subjects；iAUC R2=0.060, r=0.394；peak R2=0.141, r=0.429。",
            "interpretation": "跨数据边界下仍有正向信号，但不是强复制。",
            "remaining_weakness": "Stanford是标准挑战食物，不等于CGMacros自由餐；缺少多个外部CGM数据集。",
            "upgrade_need": "加入D1NAMO、公开CGM挑战/餐食数据，统一PPGR特征与验证协议；把Stanford称为boundary validation。",
        },
        {
            "evidence_layer": "Mechanism network",
            "current_result": "CTD化学-基因边4717，基因3070；KEGG集中于PI3K-Akt、FoxO、AMPK、insulin resistance、TNF、PPAR；Reactome集中于脂质代谢、免疫细胞因子、应激、PIP3-AKT、PPARA。",
            "interpretation": "机制层从叙述性文献升级为可复核数据库证据。",
            "remaining_weakness": "CTD/KEGG/Reactome是plausibility layer，不是实验机制证明。",
            "upgrade_need": "加入CompTox/ToxCast assay endpoints、GEO/ArrayExpress DEHP/MEHP毒理转录组、方向一致的通路富集。",
        },
    ]


def literature_sources() -> list[dict[str, object]]:
    return [
        {
            "domain": "环境暴露-代谢",
            "source": "Stahlhut et al., Environmental Health Perspectives, 2007",
            "year": 2007,
            "url": "https://pubmed.ncbi.nlm.nih.gov/17805419/",
            "evidence_type": "NHANES横断面",
            "project_use": "作为成人尿邻苯二甲酸酯代谢物与腰围/胰岛素抵抗关联的早期人群证据。",
            "design_implication": "强调尿样横断面证据应定位为关联锚点，不能单独承担因果主张。",
        },
        {
            "domain": "环境暴露-代谢",
            "source": "James-Todd et al., Environmental Health Perspectives, 2012",
            "year": 2012,
            "url": "https://pubmed.ncbi.nlm.nih.gov/22796563/",
            "evidence_type": "NHANES女性糖尿病关联",
            "project_use": "支持邻苯二甲酸酯与糖代谢异常/糖尿病风险的人群背景。",
            "design_implication": "在论文引言中说明DEHP/邻苯二甲酸酯与代谢疾病已有流行病学线索。",
        },
        {
            "domain": "环境暴露-代谢",
            "source": "Trasande et al., Pediatrics, 2013",
            "year": 2013,
            "url": "https://pubmed.ncbi.nlm.nih.gov/23958772/",
            "evidence_type": "NHANES青少年胰岛素抵抗",
            "project_use": "支持邻苯二甲酸酯代谢物与胰岛素抵抗的人群相关性。",
            "design_implication": "提示研究不应局限成人，未来可做年龄分层或易感人群分析。",
        },
        {
            "domain": "环境暴露-代谢",
            "source": "Shoshtari-Yeganeh et al., systematic review/meta-analysis, 2019",
            "year": 2019,
            "url": "https://pubmed.ncbi.nlm.nih.gov/30734259/",
            "evidence_type": "系统综述/Meta分析",
            "project_use": "为邻苯二甲酸酯-胰岛素抵抗/代谢异常关联提供综合文献背景。",
            "design_implication": "论文讨论应承认既有证据异质性，并用三角互证而非单一相关来增强论证。",
        },
        {
            "domain": "混合暴露方法",
            "source": "Carrico et al., Environmental Health Perspectives, 2015",
            "year": 2015,
            "url": "https://pubmed.ncbi.nlm.nih.gov/25863182/",
            "evidence_type": "Weighted quantile sum regression方法",
            "project_use": "支撑WQS用于高度相关环境混合物分析。",
            "design_implication": "正式投稿前保留WQS重复holdout与权重稳定性图。",
        },
        {
            "domain": "混合暴露方法",
            "source": "Bobb et al., Biostatistics, 2015",
            "year": 2015,
            "url": "https://pubmed.ncbi.nlm.nih.gov/25532525/",
            "evidence_type": "BKMR方法",
            "project_use": "支撑非线性和交互混合物建模。",
            "design_implication": "R bkmr版本应作为敏感性/非线性证据，不宜作为唯一主模型。",
        },
        {
            "domain": "混合暴露方法",
            "source": "Keil et al., Environmental Health, 2020",
            "year": 2020,
            "url": "https://ehjournal.biomedcentral.com/articles/10.1186/s12940-020-00600-z",
            "evidence_type": "Quantile g-computation方法",
            "project_use": "支撑qgcomp总混合效应估计和正负权重分解。",
            "design_implication": "NHANES主结果建议以survey-weighted qgcomp/WQS/BKMR一致性呈现。",
        },
        {
            "domain": "精准营养/PPGR",
            "source": "Zeevi et al., Cell, 2015",
            "year": 2015,
            "url": "https://pubmed.ncbi.nlm.nih.gov/26590418/",
            "evidence_type": "个体化PPGR预测开创性研究",
            "project_use": "说明PPGR高度个体化，食物与宿主状态共同决定餐后反应。",
            "design_implication": "引言中把本研究定位为在精准营养框架中加入环境-代谢易感性维度。",
        },
        {
            "domain": "精准营养/PPGR",
            "source": "Berry et al., Nature Medicine, 2020 (PREDICT 1)",
            "year": 2020,
            "url": "https://pubmed.ncbi.nlm.nih.gov/32528151/",
            "evidence_type": "大规模多组学餐后反应研究",
            "project_use": "支持餐后血糖/脂质/炎症反应存在显著个体差异。",
            "design_implication": "若冲击顶刊，需要更接近PREDICT式的多层表型或同人群桥接。",
        },
        {
            "domain": "公开CGM数据",
            "source": "CGMacros, PhysioNet",
            "year": 2024,
            "url": "https://physionet.org/content/cgmacros/",
            "evidence_type": "CGM与标准餐/宏量营养公开数据",
            "project_use": "本研究PPGR动态表型和受试者留出建模主数据。",
            "design_implication": "必须严格报告数据结构、受试者数限制和subject-disjoint验证。",
        },
        {
            "domain": "公开CGM数据",
            "source": "Stanford CGM Database",
            "year": 2024,
            "url": "https://cgmdb.stanford.edu/data/",
            "evidence_type": "挑战食物CGM数据库",
            "project_use": "用于外部边界验证。",
            "design_implication": "只能称为boundary validation，因为挑战食物结构与CGMacros自由餐不同。",
        },
        {
            "domain": "公开CGM数据",
            "source": "D1NAMO dataset",
            "year": 2018,
            "url": "https://zenodo.org/records/1421616",
            "evidence_type": "可穿戴/CGM生活方式数据",
            "project_use": "候选外部验证/敏感性数据源。",
            "design_implication": "可用于验证PPGR特征工程和跨设备数据处理流程。",
        },
        {
            "domain": "食物基质/消化",
            "source": "Minekus et al., Food & Function, 2014",
            "year": 2014,
            "url": "https://pubmed.ncbi.nlm.nih.gov/24803111/",
            "evidence_type": "INFOGEST标准静态体外消化方法",
            "project_use": "为可选体外消化验证提供方法学标准。",
            "design_implication": "若开展仿生/体外消化，需报告酶活、pH、时间点、重复、葡萄糖释放曲线。",
        },
        {
            "domain": "食物基质/消化",
            "source": "Brodkorb et al., Nature Protocols, 2019",
            "year": 2019,
            "url": "https://pubmed.ncbi.nlm.nih.gov/30886367/",
            "evidence_type": "INFOGEST 2.0共识方案",
            "project_use": "为食物基质-消化可得性验证提供国际可复核规范。",
            "design_implication": "少量体外消化应作为验证食物基质评分的机制桥，而非另起一条研究线。",
        },
        {
            "domain": "食物加工/基质",
            "source": "Hall et al., Cell Metabolism, 2019",
            "year": 2019,
            "url": "https://pubmed.ncbi.nlm.nih.gov/31105044/",
            "evidence_type": "随机交叉饮食干预",
            "project_use": "支持食物加工和基质结构对代谢表型有独立意义。",
            "design_implication": "食物基质评分可纳入加工度、结构完整性、纤维/蛋白/脂肪保护矩阵。",
        },
        {
            "domain": "因果推断",
            "source": "Lawlor et al., International Journal of Epidemiology, 2016",
            "year": 2016,
            "url": "https://pubmed.ncbi.nlm.nih.gov/28108528/",
            "evidence_type": "Triangulation框架",
            "project_use": "为跨数据、不同偏倚结构证据整合提供理论基础。",
            "design_implication": "本文主框架应写成triangulated bridge-phenotype study。",
        },
        {
            "domain": "因果推断",
            "source": "Hernan and Robins, American Journal of Epidemiology, 2016",
            "year": 2016,
            "url": "https://pubmed.ncbi.nlm.nih.gov/26994063/",
            "evidence_type": "Target trial emulation",
            "project_use": "帮助把营养替换/暴露情境转化为更清晰的可检验问题。",
            "design_implication": "后续分析可构建高MSI人群中食物基质替换的target trial模拟。",
        },
        {
            "domain": "因果推断",
            "source": "VanderWeele and Ding, Annals of Internal Medicine, 2017",
            "year": 2017,
            "url": "https://pubmed.ncbi.nlm.nih.gov/28693043/",
            "evidence_type": "E-value",
            "project_use": "量化未测混杂需达到多强才能解释观察性关联。",
            "design_implication": "现有E-value温和，应作为防守性敏感性结果而非因果证明。",
        },
        {
            "domain": "预测模型报告",
            "source": "TRIPOD+AI, BMJ, 2024",
            "year": 2024,
            "url": "https://www.bmj.com/content/385/bmj-2023-078378",
            "evidence_type": "AI/预测模型报告指南",
            "project_use": "规范CGMacros和外部验证模型报告。",
            "design_implication": "补充材料必须给出数据划分、缺失、模型、调参、校准、外部验证和可复现信息。",
        },
        {
            "domain": "预测模型偏倚评估",
            "source": "PROBAST+AI, BMJ, 2025",
            "year": 2025,
            "url": "https://www.bmj.com/content/388/bmj-2024-082505",
            "evidence_type": "AI预测模型风险评估工具",
            "project_use": "用于审稿前自查预测模型偏倚和适用性。",
            "design_implication": "要主动标明CGMacros样本量、外部验证和数据泄漏控制。",
        },
        {
            "domain": "观察性报告",
            "source": "STROBE Statement checklists",
            "year": 2007,
            "url": "https://www.strobe-statement.org/checklists/",
            "evidence_type": "观察性研究报告规范",
            "project_use": "规范NHANES观察性分析和横断面限制表述。",
            "design_implication": "主文/补充材料需完整交代样本流程、权重、变量定义、敏感性分析。",
        },
        {
            "domain": "综述/机制报告",
            "source": "PRISMA 2020, BMJ, 2021",
            "year": 2021,
            "url": "https://www.bmj.com/content/372/bmj.n71",
            "evidence_type": "系统综述报告规范",
            "project_use": "规范机制文献/数据库检索流程。",
            "design_implication": "机制部分不能写成散文综述，应有检索式、筛选流程和数据库版本。",
        },
        {
            "domain": "机制数据库",
            "source": "Comparative Toxicogenomics Database",
            "year": 2026,
            "url": "https://ctdbase.org/",
            "evidence_type": "化学-基因-疾病数据库",
            "project_use": "支撑DEHP/MEHP相关基因、疾病、通路可复核网络。",
            "design_implication": "报告下载日期、化学同义词、筛选规则和边类型。",
        },
        {
            "domain": "机制数据库",
            "source": "EPA CompTox Chemicals Dashboard / ToxCast",
            "year": 2026,
            "url": "https://www.epa.gov/comptox-tools/comptox-chemicals-dashboard",
            "evidence_type": "化学结构、暴露、体外高通量生物活性",
            "project_use": "补强DEHP/代谢物的靶点、assay endpoint和毒理活性证据。",
            "design_implication": "下一步提取PPAR、ER、氧化应激、线粒体、胰岛素相关assay证据。",
        },
        {
            "domain": "机制数据库",
            "source": "Reactome pathway database",
            "year": 2026,
            "url": "https://reactome.org/",
            "evidence_type": "人工策展通路数据库",
            "project_use": "解释PPAR/AKT/炎症/应激等通路汇聚。",
            "design_implication": "与KEGG互证，避免单一数据库偏倚。",
        },
        {
            "domain": "机制数据库",
            "source": "KEGG pathway database",
            "year": 2026,
            "url": "https://www.kegg.jp/kegg/pathway.html",
            "evidence_type": "通路数据库",
            "project_use": "用于胰岛素抵抗、AMPK、PPAR、PI3K-Akt等通路重叠分析。",
            "design_implication": "保留基因列表、通路背景集和多重校正。",
        },
        {
            "domain": "食物成分数据库",
            "source": "USDA FoodData Central",
            "year": 2026,
            "url": "https://fdc.nal.usda.gov/",
            "evidence_type": "食物成分数据库",
            "project_use": "用于CGMacros食物基质逐项FDC匹配和营养补充变量。",
            "design_implication": "proxy query必须升级为item-level匹配、匹配置信度和人工审核。",
        },
        {
            "domain": "公共健康数据库",
            "source": "NHANES Laboratory and Questionnaire Data",
            "year": 2026,
            "url": "https://wwwn.cdc.gov/nchs/nhanes/",
            "evidence_type": "复杂抽样人群数据",
            "project_use": "DEHP/邻苯二甲酸酯暴露与代谢易感性主数据。",
            "design_implication": "必须使用CDC权重、分层、PSU和周期合并规则。",
        },
        {
            "domain": "毒理组学",
            "source": "NCBI GEO",
            "year": 2026,
            "url": "https://www.ncbi.nlm.nih.gov/geo/",
            "evidence_type": "公开转录组数据库",
            "project_use": "用于寻找DEHP/MEHP暴露细胞或动物模型转录组，做方向性机制验证。",
            "design_implication": "这是干实验补强机制证据的最高性价比模块之一。",
        },
    ]


def gap_solution_matrix() -> list[dict[str, object]]:
    return [
        {
            "gap_id": "G1",
            "critical_gap": "没有同一受试者同时测量尿DEHP/代谢物和餐后CGM/标准餐反应。",
            "why_it_matters_for_high_impact": "这是当前无法声称DEHP直接影响PPGR、也不能做正式中介分析的核心断点。",
            "current_evidence": "NHANES负责暴露-代谢易感性；CGMacros负责易感性-PPGR；两者通过MSI桥接。",
            "recommended_solution": "近期以triangulated bridge-phenotype作为主张；中期设计N=80-120同受试者CGM-exposome标准餐研究；资源有限则N=30-50可行性队列。",
            "priority": "最高",
            "dry_lab_feasible_now": "否，需新数据；但可做样本量估计、方案、伦理材料和模拟功效分析。",
            "expected_gain": "从跨数据关联框架升级为可检验的环境-精准营养因果链。",
        },
        {
            "gap_id": "G2",
            "critical_gap": "NHANES横断面和单次尿样暴露误差。",
            "why_it_matters_for_high_impact": "高水平期刊会质疑时间顺序、反向因果和暴露错分。",
            "current_evidence": "复杂抽样近似、qgcomp/WQS/BKMR-style/RCS/E-value已完成。",
            "recommended_solution": "R原版survey+qgcomp+gWQS+bkmr复核；加入尿肌酐/比重敏感性、负对照、定量偏倚分析、周期/性别/BMI分层。",
            "priority": "最高",
            "dry_lab_feasible_now": "是",
            "expected_gain": "把NHANES结果从探索性分析提升为可投稿级人群证据。",
        },
        {
            "gap_id": "G3",
            "critical_gap": "MSI response-vulnerability index与PPGR结果可能存在构念循环。",
            "why_it_matters_for_high_impact": "审稿人可能认为预测提升来自将糖代谢结果重新包装为预测因子。",
            "current_evidence": "dual MSI相关但不完全相同；no-BMI/core partial等敏感性已做一部分。",
            "recommended_solution": "建立三套指数：exposure-facing、response-vulnerability、non-glycemic susceptibility；做leave-one-component-out和完全剔除糖代谢组分的PPGR预测。",
            "priority": "最高",
            "dry_lab_feasible_now": "是",
            "expected_gain": "显著增强桥接表型的构念独立性和可防守性。",
        },
        {
            "gap_id": "G4",
            "critical_gap": "食物基质评分仍是算法/proxy，缺少人工标注和实验证据。",
            "why_it_matters_for_high_impact": "食物基质是论文营养学创新点，必须可复核、可解释。",
            "current_evidence": "kappa=0.841，digestibility ICC=0.971，FDC proxy matching已完成。",
            "recommended_solution": "双人盲法食物图像/描述标注；建立codebook v2；FDC item-level匹配；可选8-12餐体外/仿生消化验证。",
            "priority": "最高",
            "dry_lab_feasible_now": "大部分可做；体外消化需实验平台。",
            "expected_gain": "把营养学变量从辅助特征提升为机制桥。",
        },
        {
            "gap_id": "G5",
            "critical_gap": "外部验证仍只有Stanford边界验证且性能中等。",
            "why_it_matters_for_high_impact": "预测/精准营养研究最常见审稿问题是泛化性。",
            "current_evidence": "Stanford iAUC R2=0.060, r=0.394；peak R2=0.141, r=0.429。",
            "recommended_solution": "加入D1NAMO、更多公开CGM挑战数据；统一PPGR提取窗口；报告transportability而非夸大复制。",
            "priority": "高",
            "dry_lab_feasible_now": "是",
            "expected_gain": "从单数据模型转为跨数据稳健性框架。",
        },
        {
            "gap_id": "G6",
            "critical_gap": "机制网络主要来自知识库重叠，缺少方向性毒理组学验证。",
            "why_it_matters_for_high_impact": "顶刊需要更接近机制链条的证据，而不只是通路名称列表。",
            "current_evidence": "CTD/KEGG/Reactome/CompTox链接和重叠已完成。",
            "recommended_solution": "检索GEO/ArrayExpress中DEHP/MEHP暴露转录组；对差异基因做PPAR/AMPK/insulin/TNF/oxidative stress方向富集；与CTD交叉验证。",
            "priority": "高",
            "dry_lab_feasible_now": "是",
            "expected_gain": "机制层从plausibility升级为public-omics-supported plausibility。",
        },
        {
            "gap_id": "G7",
            "critical_gap": "论文主张过宽会削弱说服力。",
            "why_it_matters_for_high_impact": "跨领域研究如果主线不够窄，会被认为是多个弱相关模块拼接。",
            "current_evidence": "已有DEHP-MSI、MSI-PPGR、food matrix、external validation、mechanism五层。",
            "recommended_solution": "主张压缩为一条: phthalate-related oxidative metabolic profile -> metabolic susceptibility -> food-matrix-dependent PPGR vulnerability。",
            "priority": "最高",
            "dry_lab_feasible_now": "是",
            "expected_gain": "让结果、图表、讨论、限制都围绕同一条证据链服务。",
        },
        {
            "gap_id": "G8",
            "critical_gap": "报告规范和审稿防守仍需前置。",
            "why_it_matters_for_high_impact": "高水平期刊会严格审查预测模型、观察性分析和机制检索透明度。",
            "current_evidence": "TRIPOD+AI、PROBAST+AI、STROBE、PRISMA清单已生成。",
            "recommended_solution": "将清单与正文逐项交叉引用；建立reviewer prebuttal表和analysis decision log。",
            "priority": "高",
            "dry_lab_feasible_now": "是",
            "expected_gain": "降低被认为选择性报告或模型泄漏的风险。",
        },
    ]


def experimental_protocol() -> list[dict[str, object]]:
    return [
        {
            "phase": "Phase 0",
            "name": "主张收敛、DAG和预注册分析框架",
            "core_question": "本研究到底证明什么、不能证明什么？",
            "actions": "绘制DAG；定义primary/secondary/exploratory outcomes；写analysis decision log；明确不能做正式DEHP->PPGR因果中介。",
            "primary_outputs": "DAG图、claim ladder、analysis protocol、审稿防守表。",
            "success_criteria": "所有模型和图表都能映射到同一条证据链。",
            "timeline": "1周",
        },
        {
            "phase": "Phase 1",
            "name": "NHANES环境混合物主证据复核",
            "core_question": "DEHP相关氧化代谢暴露是否稳健关联代谢易感性？",
            "actions": "R survey-weighted GLM/qgcomp/gWQS/BKMR；RCS；E-value；负对照；尿稀释敏感性；周期/性别/BMI/糖尿病状态分层。",
            "primary_outputs": "主结果表、权重图、RCS图、敏感性森林图、bias analysis表。",
            "success_criteria": "主效应方向在至少3类模型中一致，关键结果FDR可控，负对照不过度阳性。",
            "timeline": "2-3周",
        },
        {
            "phase": "Phase 2",
            "name": "CGMacros食物基质和PPGR动态表型强化",
            "core_question": "代谢易感性是否解释食物基质依赖的PPGR脆弱性？",
            "actions": "双人食物标注；FDC item-level匹配；NOVA/GI/GL/结构完整性/消化可得性编码；subject-disjoint nested CV；层级模型；校准和误差分析。",
            "primary_outputs": "食物基质codebook v2、标注一致性、PPGR预测/推断表、个体差异图。",
            "success_criteria": "剔除糖代谢组分后的MSI仍提供增量解释；food matrix交互方向稳定。",
            "timeline": "3-5周",
        },
        {
            "phase": "Phase 3",
            "name": "外部CGM验证扩展",
            "core_question": "PPGR表型和易感性框架能否迁移到不同CGM数据结构？",
            "actions": "下载/整理D1NAMO等公开CGM数据；统一0-2h iAUC、peak、time-to-peak、recovery slope；复用subject-disjoint协议；比较Stanford/CGMacros/D1NAMO。",
            "primary_outputs": "external validation matrix、transportability图、跨数据异质性表。",
            "success_criteria": "方向一致、性能诚实报告；清晰说明哪些数据结构支持或限制该框架。",
            "timeline": "2-4周",
        },
        {
            "phase": "Phase 4",
            "name": "机制层干实验升级",
            "core_question": "DEHP/MEHP相关机制是否与MSI和PPGR脆弱性生物学路径一致？",
            "actions": "CompTox/ToxCast endpoints提取；GEO/ArrayExpress DEHP/MEHP转录组差异分析；CTD-omics-KEGG-Reactome交叉；构建方向性机制网络。",
            "primary_outputs": "机制证据网络、通路富集表、tox-omics overlap图、可复核检索日志。",
            "success_criteria": "PPAR/AMPK/PI3K-Akt/insulin resistance/inflammation/oxidative stress至少在两个独立来源中汇聚。",
            "timeline": "3-6周",
        },
        {
            "phase": "Phase 5",
            "name": "可选小规模同受试者桥接或仿生消化验证",
            "core_question": "能否补上同人群暴露-餐后反应闭环或验证食物基质消化机制？",
            "actions": "A方案: N=30-50可行性CGM+尿DEHP+标准餐；B方案: 8-12代表餐食仿生/体外消化葡萄糖释放曲线。",
            "primary_outputs": "pilot protocol、样本量模拟、digestion kinetics、桥接验证图。",
            "success_criteria": "同向趋势或消化动力学与预测PPGR/food matrix评分一致。",
            "timeline": "6-12周以上",
        },
    ]


def dry_lab_execution_plan() -> list[dict[str, object]]:
    return [
        {
            "module": "D1",
            "task": "R正式混合物模型复核",
            "input_data": "NHANES phthalate/metabolic dataset",
            "method": "survey GLM, qgcomp, gWQS, bkmr, RCS, E-value, FDR",
            "deliverable": "R scripts, model result CSV, WQS/qgcomp/BKMR/RCS figures",
            "manuscript_value": "把暴露主证据从Python近似提升为方法学正式实现。",
        },
        {
            "module": "D2",
            "task": "MSI构念独立性压力测试",
            "input_data": "NHANES + CGMacros dual MSI datasets",
            "method": "non-glycemic MSI, leave-one-component-out, partial residuals, bootstrap correlations",
            "deliverable": "MSI sensitivity tables and construct diagram",
            "manuscript_value": "防止审稿人质疑循环论证。",
        },
        {
            "module": "D3",
            "task": "CGMacros人工食物基质标注体系",
            "input_data": "CGMacros meal images/metadata",
            "method": "two-rater blinded annotation, adjudication, kappa/ICC, FDC item matching",
            "deliverable": "codebook v2, annotation sheet, agreement table, food matrix score v2",
            "manuscript_value": "把食物基质创新点从proxy提升为可复核营养表型。",
        },
        {
            "module": "D4",
            "task": "Subject-disjoint模型稳健性再强化",
            "input_data": "CGMacros meal-level PPGR features",
            "method": "nested CV, subject bootstrap, mixed-effects inference, calibration curves, residual diagnostics",
            "deliverable": "prediction/inference package and TRIPOD+AI appendix",
            "manuscript_value": "降低模型泄漏和过拟合质疑。",
        },
        {
            "module": "D5",
            "task": "外部CGM数据扩展验证",
            "input_data": "Stanford CGM, D1NAMO, other public CGM if accessible",
            "method": "standard PPGR feature extraction, harmonized validation, transportability analysis",
            "deliverable": "external validation matrix and figures",
            "manuscript_value": "把单一边界验证升级为跨数据可迁移性证据。",
        },
        {
            "module": "D6",
            "task": "GEO/CompTox毒理组学机制补强",
            "input_data": "CTD, CompTox/ToxCast, GEO/ArrayExpress DEHP/MEHP datasets",
            "method": "chemical synonym search, assay endpoint mapping, differential expression, pathway overlap",
            "deliverable": "mechanistic evidence network, enrichment tables, reproducible query manifest",
            "manuscript_value": "把机制讨论从数据库共现提升为方向性机制支持。",
        },
        {
            "module": "D7",
            "task": "负对照和定量偏倚分析",
            "input_data": "NHANES outcomes/exposures and covariates",
            "method": "negative control outcome/exposure, bias functions, E-value by outcome",
            "deliverable": "bias analysis supplement and reviewer prebuttal",
            "manuscript_value": "增强观察性暴露结果可信度。",
        },
        {
            "module": "D8",
            "task": "Target-trial式营养替换模拟",
            "input_data": "CGMacros annotated meals",
            "method": "define emulated interventions: high digestibility to protected matrix within carbohydrate bands; estimate within-subject/cross-subject contrasts",
            "deliverable": "emulated substitution effect tables and plots",
            "manuscript_value": "让食物基质结果更接近可干预营养问题。",
        },
        {
            "module": "D9",
            "task": "主文重写和图表重排",
            "input_data": "All result packages",
            "method": "claim hierarchy, figure economy, limitations upfront, supplementary completeness",
            "deliverable": "AJCN/Nature Food style manuscript skeleton and figure captions",
            "manuscript_value": "把分散模块统一成高水平论文叙事。",
        },
    ]


def wet_lab_plan() -> list[dict[str, object]]:
    return [
        {
            "experiment": "仿生/体外消化代表餐选择",
            "sample_selection": "从CGMacros按预测PPGR高/低、digestibility高/低、宏量营养相近原则选择8-12餐。",
            "measurements": "0/15/30/60/90/120 min葡萄糖释放、淀粉水解率、粘度/粒径可选、pH和酶活记录。",
            "analysis": "消化曲线iAUC、Cmax、Tmax与food matrix score和CGM PPGR的相关/分层一致性。",
            "minimum_n": "每餐技术重复>=3；若资源足够，重复批次>=2。",
            "main_value": "验证食物基质评分确实对应消化可得性，而不只是统计特征。",
        },
        {
            "experiment": "小规模同受试者CGM-exposome可行性研究",
            "sample_selection": "N=30-50可行性或N=80-120正式桥接；纳入非糖尿病成人，按BMI/性别平衡。",
            "measurements": "7-14天CGM、晨尿DEHP代谢物、标准餐挑战2-3次、3天饮食记录/照片、基础代谢指标。",
            "analysis": "尿DEHP氧化比例 -> MSI/胰岛素抵抗 -> 标准餐PPGR；仅作探索性桥接，不作过度因果。",
            "minimum_n": "可行性N=30-50用于效应量和流程；正式验证建议N>=100并重复尿样。",
            "main_value": "补上当前论文最大的同人群证据断点。",
        },
        {
            "experiment": "机制细胞实验可选",
            "sample_selection": "HepG2/脂肪细胞/肠上皮模型，根据平台可及性选择；MEHP/DEHP低剂量暴露。",
            "measurements": "PPAR/AMPK/AKT磷酸化、ROS、炎症因子、葡萄糖摄取/胰岛素刺激反应。",
            "analysis": "与CTD/GEO通路方向对照。",
            "minimum_n": "每条件生物重复>=3，剂量-反应>=3档。",
            "main_value": "若冲击顶级综合/机制期刊，可补强生物学机制；但不应分散主线。",
        },
    ]


def journal_matrix() -> list[dict[str, object]]:
    return [
        {
            "journal_tier": "Aspirational top-tier",
            "candidate_journals": "Nature Food, Nature Medicine, Cell Metabolism",
            "fit": "环境暴露-精准营养-动态代谢跨领域创新。",
            "current_readiness": "不足；缺同受试者DEHP+CGM闭环和更强外部/机制验证。",
            "must_have_before_submission": "同受试者pilot或强公共多组学机制；多外部CGM验证；主张极清晰。",
        },
        {
            "journal_tier": "High-impact specialty",
            "candidate_journals": "American Journal of Clinical Nutrition, Clinical Nutrition, Environment International, Environmental Health Perspectives",
            "fit": "营养流行病学、环境健康、预测模型和机制可行性整合。",
            "current_readiness": "接近但需补强R正式模型、食物标注、外部验证和机制组学。",
            "must_have_before_submission": "R模型复核；双人食物标注；外部验证扩展；报告规范清单完整。",
        },
        {
            "journal_tier": "Strong computational/interdisciplinary",
            "candidate_journals": "Nutrients, Frontiers in Nutrition, Environmental Research, Scientific Reports",
            "fit": "多数据计算框架和可复核分析包。",
            "current_readiness": "当前结果经整理后可投稿，但与用户目标不匹配。",
            "must_have_before_submission": "至少完成R复核和主文重写。",
        },
    ]


def reviewer_prebuttal() -> list[dict[str, object]]:
    return [
        {
            "likely_reviewer_concern": "You cannot infer DEHP causes PPGR because exposure and CGM were measured in different cohorts.",
            "prebuttal": "Agree. The manuscript is framed as a triangulated bridge-phenotype study, not direct mediation or causal proof. Same-participant CGM-exposome work is proposed as the next validation.",
            "evidence_to_show": "DAG, claim ladder, limitations paragraph, triangulation rationale.",
        },
        {
            "likely_reviewer_concern": "The MSI may be circular because it includes glycemic/metabolic variables that are close to PPGR.",
            "prebuttal": "Use separate exposure-facing, response-vulnerability, and non-glycemic MSI versions; report leave-one-component-out sensitivity and no-glycemic-component prediction.",
            "evidence_to_show": "MSI construct sensitivity table and correlation heatmap.",
        },
        {
            "likely_reviewer_concern": "CGMacros has limited participants, so meal-level sample size is misleading.",
            "prebuttal": "All prediction uses subject-disjoint validation; inference uses subject clustering/hierarchical models; performance is reported with subject bootstrap uncertainty.",
            "evidence_to_show": "Subject-level split diagram, ICC, bootstrap CI, calibration curves.",
        },
        {
            "likely_reviewer_concern": "Food matrix score is subjective.",
            "prebuttal": "Provide blinded dual-rater annotation, codebook, adjudication, kappa/ICC, FDC item-level matches, and optional digestion kinetics validation.",
            "evidence_to_show": "Codebook v2, agreement table, FDC manifest, digestion curve figure if available.",
        },
        {
            "likely_reviewer_concern": "Mechanistic pathway analysis is merely database overlap.",
            "prebuttal": "Report CTD/CompTox/Reactome/KEGG as plausibility, then add public toxicogenomic directionality from GEO where available.",
            "evidence_to_show": "Database query manifest, pathway overlap with FDR, GEO differential expression concordance.",
        },
        {
            "likely_reviewer_concern": "External validation is weak.",
            "prebuttal": "Describe Stanford as boundary validation and add at least one further public CGM dataset; emphasize transportability limits.",
            "evidence_to_show": "External validation matrix with data structure differences and harmonized PPGR metrics.",
        },
        {
            "likely_reviewer_concern": "NHANES mixture models may be sensitive to modeling choices.",
            "prebuttal": "Use multiple mixture approaches, survey weights, RCS, E-value, negative controls, and urinary dilution sensitivity.",
            "evidence_to_show": "qgcomp/WQS/BKMR concordance table, RCS plots, E-values, negative control table.",
        },
    ]


def database_plan() -> list[dict[str, object]]:
    return [
        {
            "resource": "NHANES",
            "url": "https://wwwn.cdc.gov/nchs/nhanes/",
            "priority": "必须",
            "what_to_get": "phthalate metabolites, creatinine/specific gravity if available, fasting glucose/insulin/HbA1c/lipids, demographics, diet covariates, survey design variables.",
            "use": "DEHP-related exposure mixture and metabolic susceptibility anchor.",
            "status_next": "继续使用当前数据；R正式复核与敏感性扩展。",
        },
        {
            "resource": "CGMacros PhysioNet",
            "url": "https://physionet.org/content/cgmacros/",
            "priority": "必须",
            "what_to_get": "raw CGM traces, meal timing, nutrients, food images/metadata.",
            "use": "PPGR dynamic phenotype, subject-disjoint prediction, food matrix annotation.",
            "status_next": "升级人工标注/FDC item-level matching。",
        },
        {
            "resource": "Stanford CGM Database",
            "url": "https://cgmdb.stanford.edu/data/",
            "priority": "必须",
            "what_to_get": "challenge foods, CGM responses, subject-level available descriptors.",
            "use": "boundary validation of PPGR feature extraction and transportability.",
            "status_next": "已完成初版；加入更详细异质性表。",
        },
        {
            "resource": "D1NAMO",
            "url": "https://zenodo.org/records/1421616",
            "priority": "高",
            "what_to_get": "CGM, meal/activity metadata if accessible.",
            "use": "second external CGM validation and harmonized PPGR extraction.",
            "status_next": "下载并评估餐食时间标注可用性。",
        },
        {
            "resource": "USDA FoodData Central",
            "url": "https://fdc.nal.usda.gov/",
            "priority": "高",
            "what_to_get": "branded/foundation/survey food item nutrient composition and FDC IDs.",
            "use": "food matrix item-level matching and nutrient detail enrichment.",
            "status_next": "用API或离线数据建立FDC match manifest。",
        },
        {
            "resource": "CTD",
            "url": "https://ctdbase.org/",
            "priority": "高",
            "what_to_get": "DEHP/MEHP/MEHHP/MEOHP chemical-gene and chemical-disease edges.",
            "use": "mechanism plausibility network.",
            "status_next": "保留版本、下载日期、同义词、过滤规则。",
        },
        {
            "resource": "EPA CompTox/ToxCast",
            "url": "https://www.epa.gov/comptox-tools/comptox-chemicals-dashboard",
            "priority": "高",
            "what_to_get": "chemical identifiers, assay endpoints, bioactivity calls for DEHP and metabolites.",
            "use": "toxicological endpoint support for PPAR/ER/oxidative stress/mitochondrial/insulin-related pathways.",
            "status_next": "从query links升级为assay-level table。",
        },
        {
            "resource": "GEO / ArrayExpress",
            "url": "https://www.ncbi.nlm.nih.gov/geo/",
            "priority": "高",
            "what_to_get": "DEHP/MEHP exposure transcriptomics in liver/adipocyte/beta-cell/intestinal or animal metabolic tissues.",
            "use": "directional toxicogenomics mechanism validation.",
            "status_next": "检索并筛选至少1-3个可用数据集。",
        },
        {
            "resource": "Reactome / KEGG",
            "url": "https://reactome.org/ ; https://www.kegg.jp/kegg/pathway.html",
            "priority": "中高",
            "what_to_get": "pathway membership and enrichment background.",
            "use": "mechanism enrichment and pathway map.",
            "status_next": "固定背景集并加入FDR校正。",
        },
    ]


def figure_plan() -> list[dict[str, object]]:
    return [
        {
            "figure": "Figure 1",
            "title": "Study design, DAG, and claim ladder",
            "panels": "A multi-dataset map; B DAG; C claim hierarchy from association to bridge phenotype to PPGR vulnerability.",
            "main_message": "研究是三角互证桥接表型设计，不是直接中介。",
        },
        {
            "figure": "Figure 2",
            "title": "NHANES DEHP-related mixture and metabolic susceptibility",
            "panels": "qgcomp/WQS effect forest; component weights; RCS dose-response; E-value/sensitivity strip.",
            "main_message": "DEHP相关混合暴露与代谢易感性稳健相关。",
        },
        {
            "figure": "Figure 3",
            "title": "Dual MSI construct validation",
            "panels": "component diagram; correlation matrix; leave-one-component-out stability; NHANES-CGMacros bridge comparability.",
            "main_message": "MSI是桥接表型，但不同版本承担不同推断任务。",
        },
        {
            "figure": "Figure 4",
            "title": "Food matrix-dependent PPGR vulnerability in CGMacros",
            "panels": "subject-disjoint performance; observed vs predicted; RVI x digestibility interaction; food matrix categories.",
            "main_message": "代谢易感性和食物结构共同解释PPGR。",
        },
        {
            "figure": "Figure 5",
            "title": "External CGM transportability",
            "panels": "Stanford and additional dataset validation metrics; dataset difference map; calibration by challenge/meal type.",
            "main_message": "框架有可迁移信号，但边界清晰。",
        },
        {
            "figure": "Figure 6",
            "title": "Mechanistic plausibility network",
            "panels": "DEHP/metabolites -> genes -> pathways; CTD/CompTox/GEO evidence layers; KEGG/Reactome convergence.",
            "main_message": "PPAR/AMPK/PI3K-Akt/insulin resistance/inflammation/oxidative stress形成机制汇聚。",
        },
        {
            "figure": "Figure 7",
            "title": "Next validation experiment",
            "panels": "same-participant CGM-exposome pilot or bionic digestion validation workflow.",
            "main_message": "明确下一步如何补上当前证据链最大断点。",
        },
    ]


def deep_report() -> str:
    return f"""# 证据链优化与后续高水平研究路径

生成日期: {TODAY}

## 一句话主线

建议将论文主线压缩为:

**DEHP/邻苯二甲酸酯相关氧化代谢暴露与代谢易感性相关；这种代谢易感性可作为跨数据集桥接表型，解释个体在不同食物基质和消化可得性条件下的餐后血糖反应脆弱性。**

这条主线比“DEHP直接导致PPGR异常”更强、更诚实，也更容易经受高水平期刊审稿。当前最大优势是多数据、多方法、偏倚结构不同的三角互证；当前最大短板是没有同一受试者内的尿DEHP暴露和餐后CGM反应闭环。

## 当前结果的真实强度

1. **强项一: NHANES人群锚点已经有统计强度。** qgcomp/WQS/RCS/E-value构成了较完整的观察性暴露证据，其中response-vulnerability index、ln_HOMA-IR、HbA1c等结果方向一致，支持DEHP相关混合暴露与代谢易感性相关。
2. **强项二: MSI已经成为可用的桥接表型。** exposure-facing MSI和response-vulnerability index在NHANES与CGMacros中高度相关，说明两套数据共享一个代谢易感性核心。
3. **强项三: CGMacros结果证明MSI不是静态概念。** 在subject-disjoint验证下，MSI和食物基质提高iAUC与peak delta预测，并且层级模型支持response-vulnerability index和digestibility交互。
4. **强项四: 外部边界验证和机制网络已经存在。** Stanford CGM结果为正但中等；CTD/KEGG/Reactome把机制集中到PPAR、AMPK、PI3K-Akt、insulin resistance、TNF/inflammation、oxidative stress和lipid metabolism。

## 目前还不足以冲击最高水平期刊的原因

1. **证据链最大断点:** NHANES有DEHP但没有餐后CGM；CGMacros有餐后CGM但没有DEHP。跨数据桥接可以发表，但若要冲击最高水平期刊，最好补同一受试者内的暴露-代谢-餐后反应闭环。
2. **因果识别仍弱:** NHANES横断面、单次尿样和温和E-value决定了当前只能谨慎表述为关联和易感性框架。
3. **MSI需防循环论证:** response-vulnerability index与糖代谢/PPGR概念接近，必须用non-glycemic MSI和leave-one-component-out证明结果不是构念重叠。
4. **食物基质证据仍偏proxy:** 当前kappa/ICC优秀，但仍需双人盲法标注、逐项FDC匹配、NOVA/GI/GL/加工度和可选消化动力学。
5. **外部验证还不够宽:** Stanford是boundary validation，不是完整复制。需要至少再加入一个公开CGM数据集，并统一PPGR特征提取。
6. **机制层仍是plausibility:** CTD/KEGG/Reactome不是功能实验。干实验上最有效的补强是加入CompTox/ToxCast assay和GEO毒理转录组方向性验证。

## 推荐的高水平论文结构

### Claim 1: Environmental anchor

DEHP相关氧化代谢混合暴露与代谢易感性和胰岛素抵抗相关。主证据来自NHANES survey-weighted mixture models，辅助证据来自RCS、E-value、负对照和偏倚分析。

### Claim 2: Bridge phenotype

MSI不是单一数据集内的统计产物，而是能在NHANES和CGMacros之间迁移的代谢易感性构念。这里要特别强调exposure-facing MSI和response-vulnerability index用途不同。

### Claim 3: Dynamic nutrition phenotype

在CGMacros中，代谢易感性与食物基质/消化可得性共同解释餐后血糖反应差异。重点不是追求极高R2，而是在subject-disjoint、层级模型和外部验证下保持方向一致。

### Claim 4: Biological plausibility

DEHP/MEHP相关靶点和通路与PPAR、AMPK、PI3K-Akt、胰岛素抵抗、炎症和氧化应激汇聚。该层只说“支持生物学可行性”，不说“证明机制”。

## 最优后续路径

### 最低成本但显著提升的干实验路径

1. R正式复核NHANES混合物模型，并加入负对照和定量偏倚分析。
2. 构建non-glycemic MSI，重新跑CGMacros预测和层级推断。
3. 人工双人标注CGMacros食物基质，完成FDC item-level匹配。
4. 扩展Stanford以外的CGM外部验证。
5. 加入CompTox/ToxCast和GEO毒理转录组机制层。
6. 按TRIPOD+AI、PROBAST+AI、STROBE、PRISMA把补充材料做成审稿友好结构。

### 若要冲击更高层级期刊，必须补的关键实验

最优实验不是大而散，而是补证据链断点:

**同受试者CGM-exposome桥接pilot:** 7-14天CGM + 晨尿DEHP代谢物 + 2-3个标准餐挑战 + 基础代谢指标 + 饮食照片/记录。可行性N=30-50，正式验证建议N=80-120并重复尿样。

**小规模仿生/体外消化验证:** 从CGMacros中选8-12个宏量营养相近但food matrix/digestibility高低不同的代表餐，测0-120分钟葡萄糖释放曲线。这个实验的角色是验证食物基质评分，而不是把论文改成纯消化实验。

## 投稿定位

如果只完成当前干实验补强，最合适目标是AJCN、Clinical Nutrition、Environment International或Environmental Health Perspectives方向。若补同受试者CGM-exposome或强机制组学验证，才更接近Nature Food/Nature Medicine/Cell Metabolism级别的审稿期待。

## 结论

这项研究不需要再横向堆更多零散模块，而要纵向补强同一条证据链。最重要的策略是: **主张更窄、证据更厚、限制更主动、验证更贴近最大断点。** 这样才能从“多个相关分析的集合”升级为“一篇有清晰科学问题和可防守证据链的高水平论文”。
"""


def readme(file_manifest: list[str]) -> str:
    files = "\n".join(f"- `{name}`" for name in file_manifest)
    return f"""# Evidence Chain Optimization Package

生成日期: {TODAY}

本文件夹用于回应“当前研究证据链还不够完整、论证还不够有力”的问题。它基于当前项目结果和最新权威文献/方法规范，重新组织高水平投稿主线、证据缺口、干实验补强模块和可选实验路径。

## 核心结论

当前研究应定位为:

**phthalate-related oxidative metabolic profile -> metabolic susceptibility -> food-matrix-dependent postprandial glycemic vulnerability**

也就是“DEHP/邻苯二甲酸酯相关代谢暴露与代谢易感性相关，而代谢易感性可解释不同食物基质下的PPGR脆弱性”。不要直接声称DEHP导致PPGR异常。

## 文件清单

{files}
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files: list[str] = []

    datasets = {
        "01_current_result_snapshot.csv": current_result_snapshot(),
        "02_literature_search_log.csv": literature_sources(),
        "03_evidence_chain_gap_to_solution_matrix.csv": gap_solution_matrix(),
        "04_next_stage_experimental_protocol.csv": experimental_protocol(),
        "05_dry_lab_upgrade_execution_plan.csv": dry_lab_execution_plan(),
        "06_optional_wet_lab_bionic_digestion_plan.csv": wet_lab_plan(),
        "07_target_journal_decision_matrix.csv": journal_matrix(),
        "08_reviewer_prebuttal_matrix.csv": reviewer_prebuttal(),
        "09_database_and_external_validation_acquisition_plan.csv": database_plan(),
        "10_figure_and_manuscript_reframing_plan.csv": figure_plan(),
    }

    for name, rows in datasets.items():
        write_csv(OUT / name, rows)
        files.append(name)

    report_name = "00_deep_evidence_chain_optimization_report.md"
    write_text(OUT / report_name, deep_report())
    files.insert(0, report_name)

    readme_name = "README.md"
    files.insert(0, readme_name)
    files.insert(1, "00_manifest.json")
    write_text(OUT / readme_name, readme(files))

    manifest = {
        "generated": TODAY,
        "output_dir": str(OUT),
        "mirror_dir": str(NHANES_MIRROR),
        "central_claim": "phthalate-related oxidative metabolic profile -> metabolic susceptibility -> food-matrix-dependent postprandial glycemic vulnerability",
        "guardrail": "Do not claim direct DEHP-to-PPGR causality without same-participant urinary phthalate and CGM meal-response data.",
        "files": files,
        "source_result_packages": [
            str(ROOT / "outputs" / "integrated_mainline" / "current_results_interpretation_2026-06-11"),
            str(ROOT / "outputs" / "integrated_mainline" / "high_impact_computational_upgrade_2026-06-11"),
        ],
    }
    write_json(OUT / "00_manifest.json", manifest)

    if NHANES_MIRROR.exists():
        shutil.rmtree(NHANES_MIRROR)
    shutil.copytree(OUT, NHANES_MIRROR)

    print(f"Built evidence-chain optimization package: {OUT}")
    print(f"Mirrored to: {NHANES_MIRROR}")
    print(f"Files: {len(files)}")


if __name__ == "__main__":
    main()
