"""Organize JAEB glycemic phase-map results for an npj Digital Medicine target."""

from __future__ import annotations

from pathlib import Path
import json

import pandas as pd


ROOT = Path(r"D:\ai for science")
PHASE = ROOT / "results" / "jaeb_glycemic_phase_completion"
OUT = ROOT / "results" / "npj_digital_medicine_phase_strategy"
DOCS = OUT / "docs"
for path in [OUT, DOCS]:
    path.mkdir(parents=True, exist_ok=True)


def read(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def write(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def fmt(x: float, digits: int = 3) -> str:
    if pd.isna(x):
        return "NA"
    return f"{x:.{digits}f}"


def main() -> None:
    tables = PHASE / "tables"
    docs = PHASE / "docs"
    ml = read(tables / "locked_processed_ml_table.csv")
    cgm = read(tables / "locked_cgm_summary_long.csv")
    phase = read(tables / "locked_glycemic_phase_features.csv")
    phase_dict = read(PHASE / "jaeb_phase_label_dictionary.csv")
    cohort = read(PHASE / "figure_source_data" / "figure1a_study_cohort_flow.csv")
    nested = read(tables / "locked_journal_nested_tuning_summary.csv")
    loso = read(tables / "locked_journal_loso_summary.csv")
    boot = read(tables / "locked_phase_bootstrap_stability.csv")
    hte = read(tables / "locked_journal_adjusted_hte_by_phase.csv")
    adjusted_global = read(tables / "locked_journal_adjusted_phase_global_tests.csv")
    calibration = read(tables / "locked_journal_calibration_metrics.csv")
    pairwise = read(tables / "locked_journal_model_pairwise_bootstrap.csv")
    incremental = read(tables / "locked_journal_incremental_phase_value.csv")

    n_total = len(ml)
    n_cgm = len(cgm)
    n_phase = len(phase)
    n_studies = cohort["study_id"].nunique()
    phase_counts = phase["phase_label"].value_counts()
    ari_median = boot["adjusted_rand_index"].median()
    ari_q25 = boot["adjusted_rand_index"].quantile(0.25)
    ari_q75 = boot["adjusted_rand_index"].quantile(0.75)
    sil_median = boot["silhouette"].median()
    top_hba1c_nested = nested[nested["target"].eq("y_hba1c_improved_ge_0_5")].sort_values("auroc_mean", ascending=False).iloc[0]
    top_tir_nested = nested[nested["target"].eq("y_tir_improved_ge_5pct")].sort_values("auroc_mean", ascending=False).iloc[0]
    top_hba1c_loso = loso[loso["target"].eq("y_hba1c_improved_ge_0_5")].sort_values("auroc_mean", ascending=False).iloc[0]
    top_tir_loso = loso[loso["target"].eq("y_tir_improved_ge_5pct")].sort_values("auroc_mean", ascending=False).iloc[0]
    hte_top = hte.sort_values("adjusted_risk_difference", ascending=False).iloc[0]
    tir_global = adjusted_global[adjusted_global["target"].eq("y_change_cgm_time_in_range_70_180_pct")].iloc[0]

    readiness = pd.DataFrame(
        [
            {
                "domain": "Digital phenotype novelty",
                "current_status": "moderate-strong",
                "current_evidence": f"{n_phase} baseline-CGM participants mapped into {phase_counts.shape[0]} interpretable glycaemic phases.",
                "gap_for_npj_digital_medicine": "Need to frame phases as a computable CGM digital phenotype with locked code and reproducible derivation.",
                "next_action": "Create a phase-map software specification, input schema, and test fixtures.",
            },
            {
                "domain": "External validation",
                "current_status": "moderate",
                "current_evidence": f"LOSO AUROC {fmt(top_hba1c_loso.auroc_mean)} for HbA1c improvement and {fmt(top_tir_loso.auroc_mean)} for TIR improvement.",
                "gap_for_npj_digital_medicine": "LOSO across studies is useful but reviewers may want a frozen external test or extra JAEB public datasets.",
                "next_action": "Hold out one or more untouched JAEB extra datasets as a frozen validation set.",
            },
            {
                "domain": "Clinical utility",
                "current_status": "moderate",
                "current_evidence": f"HTE top phase {hte_top.phase_label}: adjusted risk difference {fmt(hte_top.adjusted_risk_difference)} ({fmt(hte_top.bootstrap_ci_low)}-{fmt(hte_top.bootstrap_ci_high)}).",
                "gap_for_npj_digital_medicine": "Need decision-analytic presentation and workflow showing how a clinician or digital platform would use the phase.",
                "next_action": "Turn intervention framework into a clinical workflow diagram and net-benefit table.",
            },
            {
                "domain": "Prediction performance",
                "current_status": "moderate",
                "current_evidence": f"Nested CV AUROC {fmt(top_hba1c_nested.auroc_mean)} for HbA1c improvement and {fmt(top_tir_nested.auroc_mean)} for TIR improvement.",
                "gap_for_npj_digital_medicine": "Phase-map features do not dominate AUROC; narrative must avoid overclaiming prediction gain.",
                "next_action": "Position model performance as validation of digital phenotype, not as a leaderboard claim.",
            },
            {
                "domain": "Robustness and fairness",
                "current_status": "incomplete",
                "current_evidence": f"Bootstrap ARI median {fmt(ari_median)}; subgroup fairness not yet packaged.",
                "gap_for_npj_digital_medicine": "Need subgroup stability by age, sex, race/ethnicity, diabetes type/study, device context if available.",
                "next_action": "Run subgroup calibration, performance, phase distribution and missingness audits.",
            },
            {
                "domain": "Prospective translation",
                "current_status": "not yet done",
                "current_evidence": "Retrospective public-data analysis only.",
                "gap_for_npj_digital_medicine": "A digital medicine paper is stronger with prospective or silent-mode deployment validation.",
                "next_action": "Design a 60-100 participant silent-mode CGM phase feedback pilot.",
            },
        ]
    )
    readiness.to_csv(OUT / "npj_digital_medicine_readiness_dashboard.csv", index=False)

    tasks = pd.DataFrame(
        [
            ("NPJ-P0-01", "P0", "Manuscript framing", "Rewrite central claim as a computable CGM digital phenotype, not a clustering exercise", "not_started", "Draft title, abstract, significance, and overclaim guardrails."),
            ("NPJ-P0-02", "P0", "Software specification", "Create phase-map input schema, feature definitions, algorithm card, and reproducibility tests", "not_started", "Needed for digital medicine credibility."),
            ("NPJ-P0-03", "P0", "Frozen validation", "Identify untouched JAEB extra datasets and run frozen external validation", "not_started", "Use jaeb_public_extra when compatible CGM/outcomes exist."),
            ("NPJ-P0-04", "P0", "Subgroup audit", "Run calibration/performance/phase distribution by age, sex, race/ethnicity, study, diabetes type, device context", "not_started", "Fairness and transportability."),
            ("NPJ-P0-05", "P0", "Clinical utility", "Convert decision curves and HTE into a phase-guided digital care workflow", "not_started", "Net benefit plus workflow diagram."),
            ("NPJ-P0-06", "P0", "Figures", "Rebuild main figures for npj Digital Medicine narrative", "not_started", "Digital phenotype, validation, clinical utility, HTE."),
            ("NPJ-P1-01", "P1", "Raw CGM upgrade", "Move from CGM summaries to raw time-series state transitions where available", "not_started", "Would substantially raise novelty."),
            ("NPJ-P1-02", "P1", "Silent-mode pilot", "Design prospective CGM digital phenotype pilot without clinical action", "not_started", "Feasibility, acceptability, stability, clinician interpretability."),
            ("NPJ-P1-03", "P1", "TRIPOD-AI / CONSORT-AI alignment", "Prepare reporting checklist and bias assessment", "not_started", "Submission hygiene."),
            ("NPJ-P1-04", "P1", "Code release", "Package pipeline with environment lock, toy data, and figure reproduction script", "not_started", "Reproducible digital medicine artifact."),
        ],
        columns=["task_id", "priority", "workstream", "task", "status", "note"],
    )
    tasks.to_csv(OUT / "npj_digital_medicine_next_research_tasks.csv", index=False)

    figure_plan = pd.DataFrame(
        [
            ("Figure 1", "Computable CGM digital phenotype", "Cohort flow; phase-map algorithm; phase dictionary; phase coordinates", "figure1a, figure1b, figure2a"),
            ("Figure 2", "Phenotype validity", "Phase CGM signatures; outcome distributions; adjusted association with restrained interpretation", "figure2b, figure2c, figure3a-c"),
            ("Figure 3", "Predictive and external validation", "Nested CV; LOSO; calibration; pairwise bootstrap showing similar models", "figure4a-b, supplement_calibration, pairwise table"),
            ("Figure 4", "Clinical utility and HTE", "Decision curve; adjusted HTE; phase-guided intervention framework", "supplement_decision_curve, figure5b-c"),
            ("Extended Data", "Robustness and fairness", "Bootstrap stability; subgroup audit; missingness; study-level heterogeneity", "figure5a plus new subgroup outputs"),
        ],
        columns=["figure", "message", "panels", "source_data"],
    )
    figure_plan.to_csv(OUT / "npj_digital_medicine_figure_plan.csv", index=False)

    phase_distribution = "; ".join([f"{label}: n={int(n)}" for label, n in phase_counts.items()])
    strategy = f"""
# npj Digital Medicine 投稿定位与后续研究计划

## 期刊定位

我将目标期刊按 **npj Digital Medicine** 理解。该刊关注数字/移动技术、虚拟医疗、AI 与 informatics 在临床和医疗转化中的应用。JAEB 血糖相图如果要匹配这个期刊，核心不能是“我们做了聚类”，而应是：

**从连续血糖监测数据中构建一个可复现、可解释、可验证的 CGM digital phenotype，用于组织糖尿病动态风险、预测随访改善，并提示相位分层治疗响应。**

## 当前结果整理

- 数据规模：{n_total} 名受试者，{n_cgm} 行 harmonized CGM summary，{n_phase} 名具备基线 CGM 相图样本。
- 研究来源：{n_studies} 个 JAEB 公开研究。
- 相位结构：{phase_distribution}。
- 相图稳定性：bootstrap ARI 中位数 {fmt(ari_median)}（IQR {fmt(ari_q25)}-{fmt(ari_q75)}），silhouette 中位数 {fmt(sil_median)}。
- Nested CV：HbA1c 改善最佳 AUROC {fmt(top_hba1c_nested.auroc_mean)}；TIR 改善最佳 AUROC {fmt(top_tir_nested.auroc_mean)}。
- LOSO 泛化：HbA1c 改善最佳平均 AUROC {fmt(top_hba1c_loso.auroc_mean)}；TIR 改善最佳平均 AUROC {fmt(top_tir_loso.auroc_mean)}。
- HTE：{hte_top.phase_label} 的调整风险差最高，为 {fmt(hte_top.adjusted_risk_difference)}（95% bootstrap CI {fmt(hte_top.bootstrap_ci_low)}-{fmt(hte_top.bootstrap_ci_high)}）。
- 调整后相位主效应：TIR change 全局相位检验 p={fmt(tir_global.p_value)}，应解释为趋势和风险结构，而非确认性因果证据。

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
"""
    write(DOCS / "npj_digital_medicine_submission_strategy_zh.md", strategy)

    abstract = f"""
# npj Digital Medicine 摘要草案

## Working Title

A reproducible glycaemic phase map from continuous glucose monitoring identifies digital phenotypes of treatment response in public diabetes trials

## Abstract Draft

Continuous glucose monitoring (CGM) provides dense digital measurements of glycaemic control, but most clinical interpretation still relies on correlated summary metrics. We developed a reproducible glycaemic phase-map framework that converts harmonized baseline CGM summaries into interpretable digital phenotypes and evaluated its prognostic and treatment-response utility across public JAEB diabetes studies.

We harmonized {n_total} participants and {n_cgm} CGM summary records from {n_studies} public studies. Among {n_phase} participants with baseline CGM summaries, five glycaemic phases were identified: stable in-range, high-variability oscillatory, persistent hyperglycaemia, circadian-disruption, and hypoglycaemia-susceptible phases. Phase-map stability was moderate to high in bootstrap resampling (median adjusted Rand index {fmt(ari_median)}, IQR {fmt(ari_q25)}-{fmt(ari_q75)}). In nested cross-validation, models predicted HbA1c improvement with AUROC {fmt(top_hba1c_nested.auroc_mean)} and TIR improvement with AUROC {fmt(top_tir_nested.auroc_mean)}. Leave-one-study-out validation showed moderate generalization. Phase membership organized heterogeneous treatment response, with the hypoglycaemia-susceptible phase showing the largest adjusted risk difference ({fmt(hte_top.adjusted_risk_difference)}, 95% bootstrap CI {fmt(hte_top.bootstrap_ci_low)}-{fmt(hte_top.bootstrap_ci_high)}).

These findings support glycaemic phase mapping as an interpretable CGM digital phenotype for retrospective risk organization and treatment-response hypothesis generation. Prospective and raw time-series validation are required before clinical deployment.
"""
    write(DOCS / "npj_digital_medicine_abstract_draft.md", abstract)

    manuscript_outline = """
# npj Digital Medicine Manuscript Outline

## Introduction

1. CGM creates a continuous digital trace but clinical interpretation remains metric-by-metric.
2. Digital medicine needs reproducible phenotypes that compress dense sensor data into clinically interpretable states.
3. Public JAEB trials provide a testbed for external validation across heterogeneous studies.

## Results

1. Harmonized public JAEB data and constructed a CGM digital phenotype space.
2. Glycaemic phase map identified five interpretable CGM phenotypes.
3. Phase phenotypes associated with baseline risk and unadjusted outcomes, with attenuated adjusted main effects.
4. Prediction models generalized moderately across studies; phase features are interpretable rather than dominant predictors.
5. Phase membership organized heterogeneous treatment response and digital-care action logic.
6. Bootstrap, calibration, decision-curve and pairwise-bootstrap analyses define robustness and limits.

## Discussion

1. Main contribution: computable CGM phenotype and validation framework.
2. Why prediction leaderboard is not the core contribution.
3. Clinical workflow: silent-mode digital decision support.
4. Limitations: retrospective public data, summary CGM, study heterogeneity, no prospective deployment.
5. Next step: raw CGM transition map and frozen/prospective validation.
"""
    write(DOCS / "npj_digital_medicine_manuscript_outline_zh.md", manuscript_outline)

    manifest = {
        "outputs": sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file()),
        "source_package": str(PHASE),
    }
    (OUT / "npj_digital_medicine_phase_strategy_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote npj Digital Medicine strategy package to {OUT}")


if __name__ == "__main__":
    main()
