# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NHANES_ROOT = ROOT.parent / "NHANES_MetS_Project"
STAMP = "2026-06-11"
SOURCE = ROOT / "outputs" / "integrated_mainline" / f"high_impact_computational_upgrade_{STAMP}"
FIG_PACKAGE = ROOT / "outputs" / "integrated_mainline" / f"high_impact_publication_figures_tables_{STAMP}"
OUT = ROOT / "outputs" / "integrated_mainline" / f"current_results_interpretation_{STAMP}"
MIRROR = NHANES_ROOT / "result" / "integrated_mainline" / f"current_results_interpretation_{STAMP}"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> Path:
    ensure_dir(path.parent)
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


def write_csv(path: Path, df: pd.DataFrame) -> Path:
    ensure_dir(path.parent)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def write_json(path: Path, payload: dict) -> Path:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_csv(name: str) -> pd.DataFrame:
    path = SOURCE / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def fmt(x: float | int | str | None, digits: int = 3) -> str:
    try:
        if pd.isna(x):
            return "NA"
        x = float(x)
        if abs(x) >= 1000:
            return f"{x:,.0f}"
        if abs(x) < 0.001 and x != 0:
            return f"{x:.2e}"
        return f"{x:.{digits}f}"
    except Exception:
        return str(x)


def get_row(df: pd.DataFrame, **filters) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=object)
    mask = pd.Series(True, index=df.index)
    for k, v in filters.items():
        if k not in df.columns:
            return pd.Series(dtype=object)
        mask &= df[k].astype(str).eq(str(v))
    if not mask.any():
        return pd.Series(dtype=object)
    return df.loc[mask].iloc[0]


def build_key_findings() -> tuple[pd.DataFrame, dict[str, str]]:
    qg = read_csv("02_nhanes_qgcomp_summary.csv")
    wqs = read_csv("02_nhanes_wqs_summary.csv")
    rcs = read_csv("02_nhanes_rcs_tests.csv")
    evalues = read_csv("02_nhanes_e_values.csv")
    msi_corr = read_csv("01_dual_msi_construct_correlations.csv")
    cg_perf = read_csv("04_cgmacros_subject_disjoint_performance.csv")
    cg_coef = read_csv("04_cgmacros_cluster_hierarchical_coefficients.csv")
    food_rel = read_csv("03_food_matrix_reliability.csv")
    stan_perf = read_csv("05_stanford_subject_disjoint_performance.csv")
    ctd_genes = read_csv("06_mechanism_ctd_gene_summary.csv")
    ctd_gene_edges = read_csv("06_mechanism_ctd_chemical_gene_edges.csv")
    ctd_disease = read_csv("06_mechanism_ctd_chemical_disease_edges.csv")
    kegg = read_csv("06_mechanism_kegg_pathway_overlap.csv")
    reactome = read_csv("06_mechanism_reactome_pathway_summary.csv")

    metrics: dict[str, str] = {}
    rows: list[dict[str, str]] = []

    q_resp = get_row(qg, outcome="response_vulnerability_index")
    q_exp = get_row(qg, outcome="exposure_facing_msi")
    q_homa = get_row(qg, outcome="ln_HOMA_IR")
    q_hba1c = get_row(qg, outcome="HbA1c")
    metrics["qg_response_beta"] = fmt(q_resp.get("psi_all_exposures_one_quantile"))
    metrics["qg_response_p"] = fmt(q_resp.get("p_value"))
    metrics["qg_response_fdr"] = fmt(q_resp.get("fdr"))
    metrics["qg_exposure_beta"] = fmt(q_exp.get("psi_all_exposures_one_quantile"))
    metrics["qg_homa_beta"] = fmt(q_homa.get("psi_all_exposures_one_quantile"))
    metrics["qg_hba1c_beta"] = fmt(q_hba1c.get("psi_all_exposures_one_quantile"))

    for outcome in ["exposure_facing_msi", "response_vulnerability_index", "ln_HOMA_IR", "HbA1c"]:
        row = get_row(qg, outcome=outcome)
        rows.append(
            {
                "module": "NHANES mixture",
                "finding": f"DEHP-related quantile mixture association with {outcome}",
                "key_result": f"psi={fmt(row.get('psi_all_exposures_one_quantile'))}, p={fmt(row.get('p_value'))}, FDR={fmt(row.get('fdr'))}, n={fmt(row.get('n'),0)}",
                "interpretation": "混合暴露与代谢易感性/糖代谢指标呈正向关联，支持人群层面的环境-代谢易感性锚点。",
                "evidence_strength": "较强",
            }
        )

    if not wqs.empty:
        wqs_pos = wqs[wqs["direction"].astype(str).eq("positive")].copy()
        sig = wqs_pos.sort_values("p_meta").head(4)
        metrics["wqs_positive_sig_outcomes"] = "; ".join(sig["outcome"].astype(str).tolist())
        rows.append(
            {
                "module": "NHANES WQS",
                "finding": "Repeated-holdout WQS positive-direction stability",
                "key_result": f"Top outcomes: {metrics['wqs_positive_sig_outcomes']}",
                "interpretation": "重复holdout WQS与qgcomp方向基本一致，说明混合暴露信号不是单一模型偶然产物。",
                "evidence_strength": "中等至较强",
            }
        )

    if not rcs.empty:
        rcs_sig = rcs.sort_values("nonlinear_p").head(3)
        metrics["rcs_top_nonlinear"] = "; ".join(
            f"{r.outcome}/{r.exposure}: p={fmt(r.nonlinear_p)}" for r in rcs_sig.itertuples()
        )
        rows.append(
            {
                "module": "NHANES RCS",
                "finding": "Nonlinear exposure-response patterns",
                "key_result": metrics["rcs_top_nonlinear"],
                "interpretation": "氧化比例相关指标呈非线性剂量-反应，提示简单线性模型可能低估或误读暴露-代谢关系。",
                "evidence_strength": "中等",
            }
        )

    if not evalues.empty:
        top_ev = evalues.sort_values("e_value", ascending=False).iloc[0]
        metrics["top_evalue"] = fmt(top_ev.get("e_value"))
        rows.append(
            {
                "module": "Sensitivity",
                "finding": "E-value sensitivity analysis",
                "key_result": f"Max E-value={fmt(top_ev.get('e_value'))} for {top_ev.get('outcome')}/{top_ev.get('exposure')}",
                "interpretation": "观察性关联对未测混杂的敏感性处于中等水平，应作为稳健性描述而非因果证明。",
                "evidence_strength": "辅助证据",
            }
        )

    msi_nh = get_row(msi_corr, dataset="NHANES", variable_1="exposure_facing_msi", variable_2="response_vulnerability_index")
    msi_cg = get_row(msi_corr, dataset="CGMacros", variable_1="exposure_facing_msi", variable_2="response_vulnerability_index")
    metrics["msi_corr_nhanes"] = fmt(msi_nh.get("pearson_r"))
    metrics["msi_corr_cgmacros"] = fmt(msi_cg.get("pearson_r"))
    rows.append(
        {
            "module": "Dual MSI",
            "finding": "Two MSI versions remain related but not identical",
            "key_result": f"NHANES r={metrics['msi_corr_nhanes']}; CGMacros r={metrics['msi_corr_cgmacros']}",
            "interpretation": "exposure-facing MSI与response-vulnerability index高度相关，说明它们共享代谢易感性核心；同时两者定义不同，有助于避免完全循环论证。",
            "evidence_strength": "较强",
        }
    )

    perf_macro_iauc = get_row(cg_perf, model="macro_only_subject_disjoint", outcome="iauc_2h")
    perf_full_iauc = get_row(cg_perf, model="full_msi_foodmatrix_subject_disjoint", outcome="iauc_2h")
    perf_macro_peak = get_row(cg_perf, model="macro_only_subject_disjoint", outcome="peak_delta_2h")
    perf_full_peak = get_row(cg_perf, model="full_msi_foodmatrix_subject_disjoint", outcome="peak_delta_2h")
    metrics["cg_iauc_r2_gain"] = fmt(float(perf_full_iauc.get("r2", 0)) - float(perf_macro_iauc.get("r2", 0)))
    metrics["cg_peak_r2_gain"] = fmt(float(perf_full_peak.get("r2", 0)) - float(perf_macro_peak.get("r2", 0)))
    rows.append(
        {
            "module": "CGMacros prediction",
            "finding": "MSI + food matrix improves subject-disjoint PPGR prediction",
            "key_result": f"iAUC R2 {fmt(perf_macro_iauc.get('r2'))}->{fmt(perf_full_iauc.get('r2'))}; peak R2 {fmt(perf_macro_peak.get('r2'))}->{fmt(perf_full_peak.get('r2'))}",
            "interpretation": "在严格受试者留出条件下，代谢易感性与食物基质特征增加了对餐后血糖反应的解释度。",
            "evidence_strength": "较强",
        }
    )

    coef_rvi_iauc = get_row(cg_coef, outcome="iauc_2h_per1000", term="response_vulnerability_index")
    coef_inter_iauc = get_row(cg_coef, outcome="iauc_2h_per1000", term="response_x_digestibility")
    coef_rvi_peak = get_row(cg_coef, outcome="peak_delta_2h", term="response_vulnerability_index")
    rows.append(
        {
            "module": "CGMacros inference",
            "finding": "Response-vulnerability index is a strong PPGR vulnerability marker",
            "key_result": f"iAUC beta={fmt(coef_rvi_iauc.get('estimate'))}, FDR={fmt(coef_rvi_iauc.get('fdr'))}; peak beta={fmt(coef_rvi_peak.get('estimate'))}, FDR={fmt(coef_rvi_peak.get('fdr'))}; RVI x digestibility iAUC beta={fmt(coef_inter_iauc.get('estimate'))}",
            "interpretation": "同样餐食负荷下，高反应易感个体表现出更高PPGR，且消化可得性与易感性之间存在交互信号。",
            "evidence_strength": "较强",
        }
    )

    kappa = get_row(food_rel, metric="category_cohen_kappa_v1_vs_v2")
    icc = get_row(food_rel, metric="rapid_digestibility_icc_v1_vs_v2")
    metrics["food_kappa"] = fmt(kappa.get("value"))
    metrics["food_icc"] = fmt(icc.get("value"))
    rows.append(
        {
            "module": "Food matrix",
            "finding": "Food-matrix scoring is internally stable under dual-rule stress test",
            "key_result": f"Category kappa={metrics['food_kappa']}; digestibility ICC={metrics['food_icc']}",
            "interpretation": "食物基质评分不是纯粹主观叙述，已形成可复核的干实验评分体系；但仍需人工双评或体外消化进一步验证。",
            "evidence_strength": "中等",
        }
    )

    stan_iauc = get_row(stan_perf, outcome="iauc_2h")
    stan_peak = get_row(stan_perf, outcome="peak_delta_2h")
    rows.append(
        {
            "module": "External boundary",
            "finding": "Stanford CGM boundary validation is positive but modest",
            "key_result": f"Stanford iAUC R2={fmt(stan_iauc.get('r2'))}, r={fmt(stan_iauc.get('pearson_r'))}; peak R2={fmt(stan_peak.get('r2'))}, r={fmt(stan_peak.get('pearson_r'))}",
            "interpretation": "外部数据支持CGM表型和易感性框架具有一定可迁移性，但跨数据结构差异明显，应表述为边界验证而非强外部复制。",
            "evidence_strength": "中等",
        }
    )

    n_edges = len(ctd_gene_edges)
    n_genes = len(ctd_genes)
    n_disease = len(ctd_disease)
    n_metabolic = int(ctd_disease.get("metabolic_relevance_flag", pd.Series(dtype=bool)).sum()) if not ctd_disease.empty else 0
    top_kegg = kegg.sort_values("n_overlap", ascending=False).head(4)
    top_reactome = reactome.sort_values("n_overlap", ascending=False).head(4)
    rows.append(
        {
            "module": "Mechanism network",
            "finding": "Database-backed DEHP/metabolite mechanism plausibility network",
            "key_result": f"CTD gene edges={n_edges}; genes={n_genes}; disease edges={n_disease}; metabolic-relevant disease edges={n_metabolic}; top KEGG={'; '.join(top_kegg['pathway_name'].astype(str).tolist())}",
            "interpretation": "机制层不再只是叙述性文献拼接，而是可追溯到CTD/KEGG/Reactome的数据库证据，集中于PPAR、PI3K-Akt、AMPK、胰岛素抵抗、TNF/炎症和脂质代谢。",
            "evidence_strength": "机制可行性证据",
        }
    )
    metrics["ctd_gene_edges"] = str(n_edges)
    metrics["ctd_genes"] = str(n_genes)
    metrics["ctd_disease_edges"] = str(n_disease)
    metrics["ctd_metabolic_edges"] = str(n_metabolic)
    metrics["top_kegg"] = "; ".join(top_kegg["pathway_name"].astype(str).tolist())
    metrics["top_reactome"] = "; ".join(top_reactome["pathway_name"].astype(str).tolist())

    return pd.DataFrame(rows), metrics


def build_claim_matrix(metrics: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "claim": "DEHP相关暴露混合物与代谢易感性相关",
                "supporting_results": f"qgcomp response-vulnerability beta={metrics.get('qg_response_beta')}, p={metrics.get('qg_response_p')}; WQS方向一致; RCS提示非线性",
                "claim_strength": "较强关联证据",
                "safe_wording": "associated with / linked to / indicates population-level metabolic susceptibility",
                "unsafe_wording": "causes PPGR abnormalities / mediates DEHP-to-PPGR",
            },
            {
                "claim": "MSI可以作为跨NHANES与CGMacros的桥接表型",
                "supporting_results": f"Dual MSI correlation: NHANES r={metrics.get('msi_corr_nhanes')}, CGMacros r={metrics.get('msi_corr_cgmacros')}",
                "claim_strength": "较强构念证据",
                "safe_wording": "bridge phenotype / susceptibility index",
                "unsafe_wording": "validated clinical diagnostic score",
            },
            {
                "claim": "代谢易感性和食物基质共同解释个体化PPGR差异",
                "supporting_results": f"Subject-disjoint R2 gains: iAUC +{metrics.get('cg_iauc_r2_gain')}, peak +{metrics.get('cg_peak_r2_gain')}; food score reliability kappa={metrics.get('food_kappa')}, ICC={metrics.get('food_icc')}",
                "claim_strength": "较强动态表型证据",
                "safe_wording": "improves prediction / marks vulnerability",
                "unsafe_wording": "ready for clinical deployment",
            },
            {
                "claim": "外部CGM数据支持但限制了模型可迁移边界",
                "supporting_results": "Stanford subject-disjoint boundary validation has modest positive R2 and correlations",
                "claim_strength": "中等外部边界证据",
                "safe_wording": "boundary validation / transportability signal",
                "unsafe_wording": "fully externally validated model",
            },
            {
                "claim": "DEHP-代谢易感性-PPGR框架具有生物学可行性",
                "supporting_results": f"CTD genes={metrics.get('ctd_genes')}; KEGG: {metrics.get('top_kegg')}; Reactome: {metrics.get('top_reactome')}",
                "claim_strength": "机制可行性证据",
                "safe_wording": "mechanistic plausibility",
                "unsafe_wording": "mechanism proven experimentally",
            },
        ]
    )


def build_value_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "dimension": "理论价值",
                "value": "将环境暴露流行病学与精准营养PPGR研究连接起来，提出环境-代谢易感性影响食物基质依赖性餐后血糖脆弱性的框架。",
                "why_it_matters": "传统PPGR研究多强调食物、微生物组和个体代谢状态，较少把环境化学暴露作为上游易感性线索纳入同一证据链。",
            },
            {
                "dimension": "方法学价值",
                "value": "采用NHANES复杂抽样/混合暴露、CGMacros受试者留出预测、Stanford外部边界验证、CTD/KEGG/Reactome机制网络和报告规范清单。",
                "why_it_matters": "这使研究从单一相关分析升级为偏倚结构不同的三角互证框架，更适合高水平期刊审稿逻辑。",
            },
            {
                "dimension": "营养学价值",
                "value": "证明同样宏量营养负荷下，代谢易感性和食物基质/消化可得性会改变PPGR风险。",
                "why_it_matters": "为精准营养从'按碳水克数建议'转向'个体易感性 x 食物结构'提供数据支持。",
            },
            {
                "dimension": "环境健康价值",
                "value": "DEHP及代谢物相关信号与胰岛素抵抗、HbA1c和代谢易感性相关，并与PPAR/AMPK/PI3K-Akt/炎症等机制网络相连。",
                "why_it_matters": "为内分泌干扰物影响代谢健康提供了人群关联、动态表型和数据库机制之间的整合证据。",
            },
            {
                "dimension": "转化价值",
                "value": "框架可用于识别高代谢易感个体面对高消化可得性餐食时的高风险情境。",
                "why_it_matters": "未来可发展为个体化饮食风险预警、食物加工/基质优化和环境暴露风险分层工具。",
            },
            {
                "dimension": "发表价值",
                "value": "目前已经具备AJCN/Clinical Nutrition/Environment International方向的计算型论文基础；若补齐R原版模型、人工食物标注和少量体外消化验证，可进一步冲击更高层级。",
                "why_it_matters": "研究主线已经从分散结果转为可防守的多层证据链，但最高级别期刊仍需要更强实验或外部复制。",
            },
        ]
    )


def build_limitations() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "limitation": "NHANES横断面和单次尿样限制",
                "impact": "无法证明时间顺序或长期暴露效应。",
                "mitigation": "使用复杂抽样、混合物模型、RCS、E-value和多MSI版本；最终投稿前建议用R survey/qgcomp/gWQS/bkmr复核。",
            },
            {
                "limitation": "没有同一受试者同时拥有DEHP生物标志物和餐后CGM",
                "impact": "不能声称DEHP直接导致PPGR异常，也不能做正式中介。",
                "mitigation": "将设计明确为cross-dataset bridge-phenotype triangulation。",
            },
            {
                "limitation": "CGMacros受试者层样本量较小",
                "impact": "餐次多不能替代受试者多，模型泛化需谨慎。",
                "mitigation": "已采用subject-disjoint验证和subject-cluster/hierarchical inference。",
            },
            {
                "limitation": "食物基质评分目前是干实验代理变量",
                "impact": "不能等同真实体内消化速度。",
                "mitigation": "已建立codebook、FDC proxy和双规则一致性；下一步需人工双评和/或体外消化验证。",
            },
            {
                "limitation": "Stanford外部验证与CGMacros数据结构不同",
                "impact": "只能说明边界可迁移性，不能作为完全外部复制。",
                "mitigation": "在论文中表述为boundary validation，并报告数据结构差异。",
            },
            {
                "limitation": "机制网络来自数据库",
                "impact": "支持机制可行性，但不能证明新机制。",
                "mitigation": "将CTD/KEGG/Reactome作为可复核plausibility layer；若冲击顶刊，需少量实验或独立组学验证。",
            },
        ]
    )


def build_report(key_df: pd.DataFrame, claim_df: pd.DataFrame, value_df: pd.DataFrame, lim_df: pd.DataFrame, metrics: dict[str, str]) -> str:
    key_bullets = "\n".join(
        f"- **{r.module}**: {r.finding}。{r.key_result}。解释: {r.interpretation}"
        for r in key_df.itertuples()
    )
    claims = "\n".join(
        f"- **{r.claim}**: {r.supporting_results}。证据等级: {r.claim_strength}。"
        for r in claim_df.itertuples()
    )
    values = "\n".join(
        f"- **{r.dimension}**: {r.value} {r.why_it_matters}"
        for r in value_df.itertuples()
    )
    limitations = "\n".join(
        f"- **{r.limitation}**: {r.impact} 应对: {r.mitigation}"
        for r in lim_df.itertuples()
    )
    return f"""
# 当前全部结果综合分析、研究意义与价值

生成日期: {STAMP}

## 总体判断

当前研究已经从最初分散的NHANES环境暴露分析、CGMacros餐后血糖预测、食物基质探索和机制文献讨论，升级为一条较清晰的多层证据链:

**DEHP/邻苯二甲酸酯氧化代谢暴露相关的代谢易感性 -> 跨数据集MSI桥接表型 -> CGMacros个体化PPGR脆弱性 -> 食物基质/消化可得性调节 -> Stanford外部CGM边界验证 -> CTD/KEGG/Reactome机制可行性。**

最重要的是，当前结果不应被包装为“DEHP直接导致PPGR升高”的单线因果故事，而应被定位为一项**三角互证的跨数据桥接表型研究**。这个定位更诚实，也更符合高水平期刊对观察性、多数据源研究的审稿预期。

## 核心结果整理

{key_bullets}

## 主要可支持论文主张

{claims}

## 研究意义与价值

{values}

## 结果的科学解释

1. **人群暴露层面**: NHANES结果说明DEHP相关暴露混合物与代谢易感性、胰岛素抵抗和HbA1c相关。qgcomp中response-vulnerability index的混合效应为{metrics.get('qg_response_beta')}，p={metrics.get('qg_response_p')}，FDR={metrics.get('qg_response_fdr')}。这为“环境暴露相关代谢易感性”提供了人群锚点。

2. **桥接表型层面**: exposure-facing MSI与response-vulnerability index在NHANES中相关r={metrics.get('msi_corr_nhanes')}，在CGMacros中相关r={metrics.get('msi_corr_cgmacros')}。这说明两个指标共享代谢易感性核心，同时又能分别承担暴露侧和反应侧解释任务。

3. **动态生理层面**: CGMacros受试者留出预测显示，加入MSI和食物基质后，iAUC模型R2提高{metrics.get('cg_iauc_r2_gain')}，peak delta模型R2提高{metrics.get('cg_peak_r2_gain')}。这说明MSI不是只存在于静态代谢指标里的统计构造，而是能解释真实生活餐后血糖动态差异。

4. **食物基质层面**: 食物基质评分的双规则一致性较好，类别kappa={metrics.get('food_kappa')}，消化可得性评分ICC={metrics.get('food_icc')}。这为“同等碳水不等于同等PPGR风险”的营养学主张提供了干实验支撑。

5. **外部边界层面**: Stanford CGM数据的外部边界验证结果为正但不强，说明该框架有可迁移信号，但不同数据集之间的餐食结构、挑战设计和变量可得性会限制模型泛化。因此更适合表述为“boundary validation”。

6. **机制可行性层面**: CTD中提取到{metrics.get('ctd_gene_edges')}条化学-基因边、{metrics.get('ctd_genes')}个基因、{metrics.get('ctd_disease_edges')}条疾病边，其中{metrics.get('ctd_metabolic_edges')}条具有代谢相关标记。KEGG和Reactome结果集中于{metrics.get('top_kegg')}以及{metrics.get('top_reactome')}。这使机制讨论从“文献拼接”提升为“可复核数据库证据网络”。

## 当前结果对发表的价值

以目前结果看，研究已经具备一篇较强计算型营养/环境健康交叉论文的骨架。其价值不在于单个模型p值，而在于多个偏倚结构不同的数据层共同指向一个解释框架:

**环境暴露相关的代谢易感性可能塑造个体面对不同食物基质时的餐后血糖脆弱性。**

这条主线具有三个特点: 第一，它连接了环境内分泌干扰物和精准营养两个通常分开的领域；第二，它把PPGR从单纯食物反应提升为“个体易感性 x 食物基质”的动态表型；第三，它主动承认跨数据集桥接限制，用三角互证而非过度因果化来增强可信度。

## 必须保留的限制与防守表述

{limitations}

## 对论文讨论部分的建议句式

1. “These findings support a triangulated bridge-phenotype framework linking phthalate-related oxidative metabolic profiles, metabolic susceptibility, and food-matrix-dependent postprandial glycemic vulnerability.”
2. “Because urinary phthalate biomarkers and CGM meal responses were not measured in the same individuals, the present study should not be interpreted as direct evidence of DEHP-to-PPGR causality.”
3. “The added predictive value of MSI and food-matrix features under subject-disjoint validation suggests that postprandial glycemic vulnerability is not fully captured by macronutrient load alone.”
4. “Mechanism database analyses converged on lipid metabolism, PPAR signaling, PI3K-Akt/insulin signaling, AMPK, inflammatory and cellular stress pathways, providing biological plausibility rather than experimental proof.”

## 下一步优先级

1. 用R原版`survey`、`qgcomp`、`gWQS`、`bkmr`复核NHANES混合物模型。
2. 对CGMacros餐食照片/描述进行人工双人食物基质标注，替代当前proxy FDC匹配。
3. 若冲击更高水平期刊，选择8-12个代表餐食开展体外消化/仿生消化动力学验证。
4. 将当前结果整合回主文，主文聚焦4-6个强图，补充材料承载全部敏感性、清单和机制网络。
"""


def main() -> None:
    ensure_dir(OUT)
    key_df, metrics = build_key_findings()
    claim_df = build_claim_matrix(metrics)
    value_df = build_value_table()
    lim_df = build_limitations()

    write_csv(OUT / "01_key_quantitative_findings.csv", key_df)
    write_csv(OUT / "02_claim_strength_matrix.csv", claim_df)
    write_csv(OUT / "03_research_value_table.csv", value_df)
    write_csv(OUT / "04_limitations_and_guardrails.csv", lim_df)
    write_text(OUT / "05_current_results_analysis_and_research_value.md", build_report(key_df, claim_df, value_df, lim_df, metrics))
    write_json(
        OUT / "00_current_results_interpretation_index.json",
        {
            "generated": datetime.now().isoformat(timespec="seconds"),
            "source_result_package": str(SOURCE),
            "figure_package": str(FIG_PACKAGE),
            "output_dir": str(OUT),
            "mirror_dir": str(MIRROR),
            "core_message": "Triangulated bridge-phenotype evidence links phthalate-related metabolic susceptibility, CGMacros PPGR vulnerability, food-matrix effects, external CGM boundaries, and mechanism plausibility.",
            "metrics": metrics,
        },
    )

    ensure_dir(MIRROR)
    for src in OUT.rglob("*"):
        if src.is_file():
            dst = MIRROR / src.relative_to(OUT)
            ensure_dir(dst.parent)
            shutil.copy2(src, dst)
    print(f"Created current results interpretation package: {OUT}")
    print(f"Mirrored to: {MIRROR}")
    print(f"Files: {len(list(OUT.glob('*')))}")


if __name__ == "__main__":
    main()
