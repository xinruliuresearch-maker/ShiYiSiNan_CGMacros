from __future__ import annotations

import json
import shutil
from datetime import date, datetime
from pathlib import Path

import pandas as pd


TODAY = date.today().isoformat()
ROOT = Path(r"C:\Users\liu12\OneDrive\Desktop\ShiYiSiNan_CGMacros")
NHANES_PROJECT = Path(r"C:\Users\liu12\OneDrive\Desktop\NHANES_MetS_Project")
OUT = ROOT / "outputs" / "integrated_mainline" / f"next_stage_high_tier_optimization_{TODAY}"
MIRROR = NHANES_PROJECT / "result" / "integrated_mainline" / f"next_stage_high_tier_optimization_{TODAY}"
HARD = ROOT / "outputs" / "integrated_mainline" / f"evidence_chain_hardening_{TODAY}"


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\n", "\r\n"), encoding="utf-8")


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def read_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def top_raw_nhanes() -> str:
    df = read_csv(HARD / "06_survey_weighted_raw_monomer_mixture_qgcomp_like.csv")
    if df.empty:
        return "未找到原始单体NHANES混合物结果。"
    df["p_num"] = pd.to_numeric(df["p"], errors="coerce")
    df = df.sort_values("p_num").head(5)
    return "; ".join(
        f"{r.mixture_set}/{r.outcome}: psi={float(r.psi):.3f}, p={float(r.p):.3g}, q={float(r.q):.3g}, n={int(r.n)}"
        for r in df.itertuples()
    )


def summarize_food() -> str:
    rel = read_csv(HARD / "20_food_matrix_AI_rule_reliability.csv")
    fdc = read_csv(HARD / "26_cgmacros_FDC_official_match_summary.csv")
    if rel.empty or fdc.empty:
        return "未找到食物基质/FDC结果。"
    return (
        f"AI/rule dual prelabel agreement={float(rel.loc[0, 'agreement']):.3f}, "
        f"kappa={float(rel.loc[0, 'cohen_kappa']):.3f}, "
        f"manual_review={int(rel.loc[0, 'n_requires_manual_image_review'])}; "
        f"official FDC proxy IDs={int(fdc.loc[0, 'n_with_official_fdc_id'])}/{int(fdc.loc[0, 'n_meals'])}, "
        f"low_confidence={int(fdc.loc[0, 'n_low_confidence'])}."
    )


def summarize_stanford() -> str:
    pred = read_csv(HARD / "35_stanford_molecular_prediction_performance.csv")
    bridge = read_csv(HARD / "31_stanford_subject_msi_ppgr_bridge.csv")
    if pred.empty:
        return "未找到Stanford分子预测结果。"
    pred = pred.sort_values("rmse").head(1)
    r = pred.iloc[0]
    return (
        f"Stanford subjects={bridge['subject'].nunique() if not bridge.empty else 'NA'}; "
        f"best model={r['model']} for {r['outcome']}, r={float(r['pearson_r']):.3f}, "
        f"R2={float(r['r2']):.3f}, RMSE={float(r['rmse']):.2f}."
    )


def summarize_geo() -> str:
    syn = read_csv(HARD / "56_GEO_directional_mechanism_synthesis.csv")
    kegg = read_csv(HARD / "55_GEO_GSE293605_MEHP_KEGG_relevant_terms.csv")
    parts = []
    if not syn.empty:
        sig = syn[pd.to_numeric(syn["n_fdr_0_05"], errors="coerce").fillna(0) > 0]
        parts.append(
            "; ".join(
                f"{r.dataset}/{r.panel}: FDR genes={r.n_fdr_0_05}, {r.direction_interpretation}"
                for r in sig.head(6).itertuples()
            )
        )
    if not kegg.empty:
        hits = []
        for term in ["Insulin resistance", "PI3K-Akt", "AGE-RAGE", "Sphingolipid"]:
            hit = kegg[kegg["Description"].astype(str).str.contains(term, case=False, na=False)]
            if len(hit):
                row = hit.iloc[0]
                hits.append(f"{row['Description']} padj={float(row['padj']):.3g}")
        parts.append("KEGG: " + "; ".join(hits))
    return " | ".join([p for p in parts if p]) or "未找到GEO方向性机制结果。"


def literature_rows() -> pd.DataFrame:
    rows = [
        {
            "domain": "PPGR benchmark",
            "source": "Nature Medicine 2025 standardized carbohydrate meal PPGR study",
            "url": "https://www.nature.com/articles/s41591-025-03719-2",
            "high_tier_message": "等量碳水餐可诱发不同PPGR类型，顶级PPGR论文正在强调标准餐重复挑战、多组学、mitigator response和个体反应类型。",
            "action_for_project": "当前CGMacros/Stanford应从单点iAUC/peak升级为标准餐反应类型、重复性、曲线形态和mitigator反应。",
        },
        {
            "domain": "Precision nutrition precedent",
            "source": "PREDICT 1 Nature Medicine 2020",
            "url": "https://pubmed.ncbi.nlm.nih.gov/32528151/",
            "high_tier_message": "高水平precision nutrition研究需要标准化餐食、自由生活数据、外部验证和高维表型共同支撑。",
            "action_for_project": "不能只依赖CGMacros机器学习预测；要把NHANES暴露锚点、Stanford分子层和同受试者pilot组织成三角证据。",
        },
        {
            "domain": "CGM modeling",
            "source": "Functional data analysis for postprandial glucose trajectories",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10568141/",
            "high_tier_message": "PPGR不仅是iAUC/peak，完整餐后曲线、恢复斜率和形态聚类更能捕捉生理差异。",
            "action_for_project": "下一轮对CGMacros和Stanford都应加入0-180 min曲线特征、functional PCA、curve clustering和recovery metrics。",
        },
        {
            "domain": "Environmental mixture methods",
            "source": "qgcomp / WQS / BKMR environmental mixture methodology",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7228100/",
            "high_tier_message": "环境混合物模型要求真实组分可解释，派生比例不能替代原始暴露单体。",
            "action_for_project": "原始MEHP/MEHHP/MEOHP/MECPP作为主模型是正确方向；派生氧化比例只能作为代谢转化二级机制指标。",
        },
        {
            "domain": "NHANES exposure source",
            "source": "CDC NHANES phthalates/plasticizers laboratory documentation",
            "url": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2013/DataFiles/PHTHTE_H.htm",
            "high_tier_message": "NHANES提供原始单体、LOD标记和化学物子样本权重。",
            "action_for_project": "主文需要完整报告LOD处理、尿稀释校正、周期权重、单体相关结构和替代权重敏感性。",
        },
        {
            "domain": "GEO toxicogenomics",
            "source": "GSE212641 and GSE293605 MEHP/DEHP toxicogenomics resources",
            "url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE212641 ; https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE293605",
            "high_tier_message": "机制层可从数据库交集升级为MEHP/DEHP暴露后的方向性转录组和通路证据。",
            "action_for_project": "需要把GEO panel结果与NHANES outcome和Stanford molecular signatures做同向性矩阵，而不是孤立报告。",
        },
        {
            "domain": "Exposome infrastructure",
            "source": "NIEHS HHEAR",
            "url": "https://hhearprogram.org/",
            "high_tier_message": "高水平环境健康研究越来越强调可复用exposome分析平台、标准化实验室测量和多层数据协调。",
            "action_for_project": "下一步应申请/利用HHEAR风格测量框架，至少在pilot中预注册尿邻苯单体、代谢组和CGM同步采集。",
        },
        {
            "domain": "Prediction reporting",
            "source": "TRIPOD+AI and PROBAST+AI",
            "url": "https://www.tripod-statement.org/ ; https://www.bmj.com/content/388/bmj-2024-082505",
            "high_tier_message": "AI/prediction模型必须报告数据源、分割、泄漏控制、校准、缺失、适用性和偏倚。",
            "action_for_project": "CGMacros/Stanford预测结果要降调为机制桥接或探索性预测，严格按TRIPOD+AI/PROBAST+AI补充清单报告。",
        },
        {
            "domain": "Food composition infrastructure",
            "source": "USDA FoodData Central",
            "url": "https://fdc.nal.usda.gov/download-datasets",
            "high_tier_message": "正式FDC离线库可避免DEMO_KEY限流，但图像餐食仍需人工item确认。",
            "action_for_project": "FDC proxy ID不等于人工确认的食物项；必须完成双人图片标注和adjudication。",
        },
        {
            "domain": "Reporting nutrition exposures",
            "source": "STROBE-nut",
            "url": "https://www.strobe-nut.org/",
            "high_tier_message": "营养暴露研究需要透明报告饮食评估、误差、处理和解释边界。",
            "action_for_project": "食物基质模块应按STROBE-nut扩展报告图像来源、标注流程、FDC映射、误差和复核。",
        },
    ]
    return pd.DataFrame(rows)


def evidence_gap_rows() -> pd.DataFrame:
    rows = [
        {
            "gap": "原始单体NHANES信号边界显著",
            "current_evidence": top_raw_nhanes(),
            "why_reviewers_will_attack": "主模型q值约0.05-0.08，强度低于派生氧化比例；审稿人会质疑多重比较和单次尿样暴露误差。",
            "upgrade": "加入多周期复制、LOD/尿稀释/Bayesian measurement-error敏感性、按单体相关结构的Bayesian mixture shrinkage、负对照和置换分层。",
            "priority": "P0",
        },
        {
            "gap": "食物基质还不是金标准",
            "current_evidence": summarize_food(),
            "why_reviewers_will_attack": "AI/rule kappa低，932餐需人工复核；FDC是proxy ID，不是人工确认item-level truth。",
            "upgrade": "两名营养学/食品科学背景评审独立标注全部餐图；第三方裁决；每餐保留image、category、FDC ID、confidence、reason code。",
            "priority": "P0",
        },
        {
            "gap": "Stanford分子层预测贡献弱",
            "current_evidence": summarize_stanford(),
            "why_reviewers_will_attack": "omics PCs没有提升预测，n较小，预测R2很低；不能声称强外部验证。",
            "upgrade": "把Stanford定位为机制桥接而非预测验证；改跑response-type clustering、mitigator response和molecular enrichment，不以R2作为主叙事。",
            "priority": "P1",
        },
        {
            "gap": "跨数据库证据缺少同一人内闭环",
            "current_evidence": "NHANES有暴露和代谢，CGMacros/Stanford有PPGR但无邻苯暴露。",
            "why_reviewers_will_attack": "主线跨数据库拼接，无法证明同一个体的DEHP暴露与PPGR脆弱性相连。",
            "upgrade": "设计N=60 feasibility / N=120 definitive同受试者CGM-exposome pilot，重复尿样+标准餐+CGM+代谢表型。",
            "priority": "P0 for top-tier; P2 for computational-only paper",
        },
        {
            "gap": "机制证据仍偏间接",
            "current_evidence": summarize_geo(),
            "why_reviewers_will_attack": "GEO细胞/类器官暴露浓度、组织和时间窗与NHANES人群暴露不同。",
            "upgrade": "建立mechanistic concordance matrix：NHANES outcome方向、GEO gene/pathway方向、Stanford molecule方向三方一致性；不把GEO解释为因果证明。",
            "priority": "P1",
        },
        {
            "gap": "CGM结局过度依赖iAUC/peak",
            "current_evidence": "当前主表以iAUC2h和peak delta为主。",
            "why_reviewers_will_attack": "PPGR是动态过程，单一标量丢失恢复、延迟、低血糖反弹和曲线类型。",
            "upgrade": "加入functional PCA、curve shape clustering、time-above-baseline、recovery slope、late excursion等曲线特征。",
            "priority": "P1",
        },
    ]
    return pd.DataFrame(rows)


def next_analyses_rows() -> pd.DataFrame:
    rows = [
        {
            "module": "A. NHANES raw-monomer replication and bias hardening",
            "specific_steps": "Run raw monomer mixtures by cycle; pooled random-effects meta-analysis; compare creatinine covariate vs creatinine-standardized exposure; LOD imputation sensitivity; bootstrap FDR; permutation negative controls.",
            "deliverables": "raw_monomer_cycle_replication.csv; meta_analysis_forest.png; measurement_error_sensitivity.csv; revised Supplementary Methods.",
            "decision_rule": "If oxidative-three mixture remains directionally consistent across cycles and q<0.10, keep as primary exposure anchor; otherwise demote to hypothesis-generating.",
            "time": "3-5 days",
        },
        {
            "module": "B. Food-matrix gold standard",
            "specific_steps": "Two independent human raters annotate all 1498 meal photos using v3 codebook; adjudicator resolves conflicts; confirm FDC IDs for high-impact categories and all low-confidence proxy matches.",
            "deliverables": "human_adjudicated_food_matrix.csv; kappa_before_after.csv; final_FDC_item_level_matches.csv; image audit trail.",
            "decision_rule": "Proceed to main food-matrix claims only if human kappa>=0.70 after training/adjudication and category prevalence is sufficient.",
            "time": "1-2 weeks human work; 1 day analysis",
        },
        {
            "module": "C. CGM functional phenotype upgrade",
            "specific_steps": "For CGMacros and Stanford, derive full 0-180 min curve features; cluster response types; test whether food matrix and MSI predict curve type, not just scalar iAUC.",
            "deliverables": "curve_feature_matrix.csv; response_type_clusters.csv; functional_ppgr_models.csv; curve phenotype figures.",
            "decision_rule": "Use scalar endpoints in main text only if functional phenotypes agree; otherwise reframe as curve-type vulnerability.",
            "time": "4-7 days",
        },
        {
            "module": "D. Stanford mechanistic bridge reframing",
            "specific_steps": "Analyze standardized food-specific response types, mitigator response, and molecular module enrichment; avoid claiming prediction superiority from omics PCs.",
            "deliverables": "stanford_response_type_molecular_enrichment.csv; mitigator_response_models.csv; molecular concordance table.",
            "decision_rule": "Use Stanford as external mechanistic bridge if molecular modules align with GEO/NHANES metabolic pathways.",
            "time": "3-5 days",
        },
        {
            "module": "E. GEO/NHANES/Stanford concordance matrix",
            "specific_steps": "Map genes/pathways/metabolites to five mechanism axes: insulin signaling, lipid/PPAR, oxidative stress, inflammation/TNF, mitochondrial stress; compute direction concordance.",
            "deliverables": "mechanism_concordance_matrix.csv; directionality_heatmap.png; text for Mechanisms section.",
            "decision_rule": "Only pathways with at least two independent evidence layers should be emphasized in abstract/discussion.",
            "time": "2-4 days",
        },
        {
            "module": "F. Same-participant CGM-exposome pilot protocol",
            "specific_steps": "Finalize sample size, visit schedule, standard meals, urine timing, CGM protocol, endpoints, biospecimen handling, DAG, statistical analysis plan and ethics-ready protocol.",
            "deliverables": "pilot_protocol_full.md; pilot_SAP.md; REDCap/codebook; budget/sample-size appendix.",
            "decision_rule": "Required for top-tier claim that exposure, metabolic susceptibility and PPGR vulnerability are linked within individuals.",
            "time": "1-2 weeks protocol writing; 2-4 months execution if funded",
        },
    ]
    return pd.DataFrame(rows)


def claim_ladder_rows() -> pd.DataFrame:
    rows = [
        {
            "tier": "Current defensible claim",
            "claim": "Urinary raw DEHP oxidative metabolite mixture is directionally associated with metabolic susceptibility markers in NHANES; metabolic susceptibility relates to food-matrix-dependent PPGR vulnerability across CGM datasets.",
            "allowed_journals": "AJCN/Clinical Nutrition style if framed as integrative computational evidence.",
        },
        {
            "tier": "After dry-lab upgrades",
            "claim": "A reproducible raw phthalate-metabolite mixture-metabolic susceptibility signal is supported by cycle replication, human-adjudicated food matrix PPGR phenotypes, Stanford standardized-meal molecular bridging and GEO toxicogenomic directionality.",
            "allowed_journals": "Environment International/EHP/Clinical Nutrition/AJCN stronger target.",
        },
        {
            "tier": "After same-participant pilot",
            "claim": "Within-person urinary phthalate metabolite profiles stratify standardized-meal PPGR vulnerability and food-matrix/mitigator response through metabolic susceptibility and molecular stress axes.",
            "allowed_journals": "Nature Food / Cell Metabolism / Nature Medicine style becomes plausible if effect sizes and reproducibility are strong.",
        },
    ]
    return pd.DataFrame(rows)


def pilot_rows() -> pd.DataFrame:
    rows = [
        {"domain": "Design", "recommendation": "Randomized repeated-meal crossover embedded in 10-14 day CGM monitoring, with 3 repeated first-morning urine samples for phthalate metabolites."},
        {"domain": "Sample size", "recommendation": "N=60 feasibility for variance/compliance; N=120 definitive for interaction estimates across four food matrices."},
        {"domain": "Exposure", "recommendation": "MEHP, MEHHP, MEOHP, MECPP, MEP, MnBP, MiBP, MBzP, MCOP/MCNP; urinary creatinine and specific gravity; pooled and repeated-sample reliability."},
        {"domain": "Meals", "recommendation": "Four 50g-available-carb standardized matrices: liquid sugar, refined starch, whole/fiber matrix, mixed macronutrient buffered matrix; each repeated twice."},
        {"domain": "Mitigator arms", "recommendation": "Protein/fat preload, fiber/acid matrix, post-meal walking, and meal order as optional randomized substudies."},
        {"domain": "Outcomes", "recommendation": "Primary: iAUC2h and peak delta. Secondary: curve type, recovery slope, time above baseline, late excursion, variability."},
        {"domain": "Analysis", "recommendation": "Hierarchical mixed models with participant random intercepts, meal matrix interactions, repeated exposure measurement error correction, and negative controls."},
        {"domain": "Success criteria", "recommendation": "Consistent within-person exposure-mixture association with PPGR vulnerability or a clear interaction with metabolic susceptibility/food matrix."},
    ]
    return pd.DataFrame(rows)


def journal_rows() -> pd.DataFrame:
    rows = [
        {"target": "AJCN / Clinical Nutrition", "minimum_needed": "Dry-lab upgrades, human-adjudicated food matrix, rigorous reporting, restrained causal language.", "risk": "Novelty may be seen as integrative but indirect."},
        {"target": "Environment International / EHP", "minimum_needed": "Raw monomer mixture replication, robust bias analysis, toxicogenomic concordance, clear environmental-health contribution.", "risk": "PPGR bridge may look outside environmental epidemiology unless same-participant evidence is added."},
        {"target": "Nature Food", "minimum_needed": "Food matrix gold standard, standardized meal response types, actionable mitigator or diet implication.", "risk": "DEHP exposure layer may be too indirect without pilot."},
        {"target": "Cell Metabolism / Nature Medicine style", "minimum_needed": "Same-participant CGM-exposome pilot plus multiomics, repeated standardized meals, validated response types.", "risk": "Computational-only cross-database evidence is not enough."},
    ]
    return pd.DataFrame(rows)


def report_text() -> str:
    return f"""# 下一阶段高水平期刊研究优化方案

生成日期: {TODAY}

## 总体判断

你认为“水平还不够充分、证据链还不够完整、论证还不够有力”是准确的。当前研究已经从松散整合推进到可复核证据链，但距离高水平期刊仍有一个核心问题:

**现在最强的是跨数据库三角证据，不是同一受试者内闭环证据。**

因此，下一步不应继续横向堆更多公共数据，而应把主线收束为:

**原始尿邻苯二甲酸酯/DEHP单体混合暴露 -> 代谢易感性 -> 食物基质依赖的PPGR曲线脆弱性 -> MEHP/DEHP相关转录组机制轴。**

这条主线比“DEHP直接导致餐后血糖异常”更窄，但更能经受审稿。

## 当前结果的真实强度

### NHANES暴露锚点

{top_raw_nhanes()}

解释: 原始单体模型方向是对的，但FDR大多在0.05-0.08边界。它比派生比例更可信，却没有强到可以做激进因果声称。下一步必须做周期复制、LOD/尿稀释/测量误差敏感性和多模型一致性。

### 食物基质

{summarize_food()}

解释: FDC离线匹配已经解决API失败，但食物基质仍未达到发表金标准。932餐需要人工图像复核，FDC proxy ID不能替代人工item confirmation。

### Stanford桥接

{summarize_stanford()}

解释: Stanford应从“预测外部验证”改为“标准化餐食+分子机制桥接”。当前omics PCs没有明显提升预测，不应在主文中宣称强预测能力。

### GEO机制层

{summarize_geo()}

解释: 机制层已有方向性证据，尤其GSE293605显示insulin resistance、PI3K-Akt、AGE-RAGE和sphingolipid signaling富集。但这些是细胞/类器官证据，不能直接替代人体因果验证。

## 下一阶段优先级

### P0: 不做就很难冲高水平期刊

1. 完成人工双人食物基质标注和FDC确认。
2. NHANES原始单体混合物做周期复制、尿稀释/LOD/测量误差敏感性。
3. 明确同受试者CGM-exposome pilot方案，作为顶刊版本的核心增量。

### P1: 能显著提升论证强度

1. CGM从iAUC/peak升级为完整曲线表型。
2. Stanford改做response type、mitigator response和分子模块桥接。
3. GEO/NHANES/Stanford三方机制方向一致性矩阵。

### P2: 有用但不能替代核心证据

1. 继续补CompTox/ToxCast assay endpoint。
2. 加更多外部CGM数据集。
3. 画更多机制网络图。

## 论文主张建议

当前主张应避免写成“DEHP导致PPGR异常”。更稳妥的高水平表述是:

**原始邻苯二甲酸酯/DEHP代谢物混合暴露与代谢易感性相关，而代谢易感性可能定义了一类面对快速消化或低保护食物基质时更易出现餐后血糖曲线脆弱性的个体；MEHP/DEHP相关转录组证据支持脂质/PPAR、胰岛素信号、氧化炎症和线粒体应激机制轴。**

## 最关键的后续路径

如果目标是AJCN/Clinical Nutrition/Environment International级别，完成P0干实验和人工标注即可形成较强稿件。

如果目标是Nature Food/Cell Metabolism/Nature Medicine风格，必须加入同受试者pilot。没有同一受试者内的尿邻苯暴露、标准餐CGM、代谢表型和食物基质闭环，顶级期刊会认为证据仍是聪明但拼接的跨数据库研究。
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    MIRROR.mkdir(parents=True, exist_ok=True)
    write_text(OUT / "00_next_stage_high_tier_optimization_report.md", report_text())
    write_csv(OUT / "01_literature_and_method_update.csv", literature_rows())
    write_csv(OUT / "02_current_evidence_gap_reviewer_matrix.csv", evidence_gap_rows())
    write_csv(OUT / "03_priority_next_analyses.csv", next_analyses_rows())
    write_csv(OUT / "04_claim_ladder_and_journal_positioning.csv", claim_ladder_rows())
    write_csv(OUT / "05_same_participant_pilot_design_v2.csv", pilot_rows())
    write_csv(OUT / "06_journal_target_decision_matrix.csv", journal_rows())
    write_json(
        OUT / "00_manifest.json",
        {
            "generated": datetime.now().isoformat(timespec="seconds"),
            "out_dir": str(OUT),
            "mirror_dir": str(MIRROR),
            "source_hardening_dir": str(HARD),
            "central_next_step": "Do not add more weak modules; harden raw exposure replication, human food-matrix truth, CGM functional phenotypes, mechanism concordance, and same-participant pilot.",
            "files": [
                "00_next_stage_high_tier_optimization_report.md",
                "01_literature_and_method_update.csv",
                "02_current_evidence_gap_reviewer_matrix.csv",
                "03_priority_next_analyses.csv",
                "04_claim_ladder_and_journal_positioning.csv",
                "05_same_participant_pilot_design_v2.csv",
                "06_journal_target_decision_matrix.csv",
            ],
        },
    )
    for item in OUT.iterdir():
        dest = MIRROR / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    print(f"Built next-stage high-tier optimization package: {OUT}")
    print(f"Mirrored to: {MIRROR}")


if __name__ == "__main__":
    main()
