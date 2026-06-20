"""Build a submission-oriented current-results synthesis and research plan.

The outputs are intentionally lightweight Markdown/CSV files so they can be
edited directly during manuscript planning.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(r"D:\ai for science")
PHASE = ROOT / "results" / "jaeb_glycemic_phase_completion"
STRATEGY = ROOT / "results" / "npj_digital_medicine_phase_strategy"
P0 = STRATEGY / "p0_workup"
OUT = STRATEGY / "research_plan_2026_06_18"
DOCS = OUT / "docs"
TABLES = OUT / "tables"

for path in [OUT, DOCS, TABLES]:
    path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def write(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def fmt(x: float, digits: int = 3) -> str:
    if pd.isna(x):
        return "NA"
    return f"{float(x):.{digits}f}"


def target_name(target: str) -> str:
    return {
        "y_hba1c_improved_ge_0_5": "HbA1c response",
        "y_tir_improved_ge_5pct": "TIR response",
    }.get(target, target)


def feature_name(feature_set: str) -> str:
    return {
        "C1_clinical": "clinical",
        "C2_clinical_plus_cgm": "clinical+CGM",
        "C4_phase_map": "phase-map",
    }.get(feature_set, feature_set)


def main() -> None:
    phase_features = read_csv(PHASE / "tables" / "locked_glycemic_phase_features.csv")
    cgm_long = read_csv(PHASE / "tables" / "locked_cgm_summary_long.csv")
    inventory = read_csv(PHASE / "tables" / "locked_dataset_inventory.csv")
    dev_inventory = inventory[inventory["status"].eq("downloaded_cleaned")].copy()
    phase_dict = read_csv(PHASE / "jaeb_phase_label_dictionary.csv")
    stability = read_csv(PHASE / "tables" / "locked_phase_bootstrap_stability.csv")
    nested = read_csv(PHASE / "tables" / "locked_journal_nested_tuning_summary.csv")
    loso = read_csv(PHASE / "tables" / "locked_journal_loso_summary.csv")
    hte = read_csv(PHASE / "tables" / "locked_journal_adjusted_hte_by_phase.csv")
    external = read_csv(P0 / "tables" / "loop_frozen_external_validation_metrics.csv")
    external_inventory = read_csv(P0 / "tables" / "frozen_external_validation_inventory.csv")
    loop_phase = read_csv(P0 / "figure_source_data" / "loop_frozen_phase_distribution.csv")
    fairness = read_csv(P0 / "tables" / "subgroup_fairness_calibration_audit.csv")

    phase_map = dict(zip(phase_dict["phase_label_zh"], phase_dict["phase_label_en"]))
    hte["phase_label_en"] = hte["phase_label"].map(phase_map).fillna(hte["phase_label"])
    top_hte = hte.sort_values("adjusted_risk_difference", ascending=False).iloc[0]

    nested_best = (
        nested.sort_values(["target", "auroc_mean"], ascending=[True, False])
        .groupby("target", as_index=False)
        .head(1)
        .copy()
    )
    loso_best = (
        loso.sort_values(["target", "auroc_mean"], ascending=[True, False])
        .groupby("target", as_index=False)
        .head(1)
        .copy()
    )
    external_pivot = external.copy()
    external_pivot["target_display"] = external_pivot["target"].map(target_name)
    external_pivot["feature_display"] = external_pivot["feature_set"].map(feature_name)

    fair_top_all = (
        fairness[fairness["subgroup_variable"].ne("overall")]
        .dropna(subset=["delta_auroc_vs_overall"])
        .assign(abs_delta=lambda x: x["delta_auroc_vs_overall"].abs())
        .sort_values("abs_delta", ascending=False)
        .head(10)
        .copy()
    )
    fair_focus = (
        fairness[
            fairness["subgroup_variable"].ne("overall")
            & fairness["feature_set"].eq("C4_phase_map")
            & fairness["model"].eq("xgboost")
        ]
        .dropna(subset=["delta_auroc_vs_overall"])
        .assign(abs_delta=lambda x: x["delta_auroc_vs_overall"].abs())
        .sort_values("abs_delta", ascending=False)
        .head(10)
        .copy()
    )

    current_results = pd.DataFrame(
        [
            {
                "domain": "Dataset",
                "result": "JAEB development corpus",
                "value": f"{dev_inventory.shape[0]} downloaded/cleaned JAEB development datasets; {phase_features['participant_id'].nunique()} baseline phase-map participants; {cgm_long.shape[0]} harmonized CGM summary rows",
                "interpretation_for_npj": "Good scale for retrospective digital phenotype development, but public JAEB studies are still not a prospective deployment setting.",
            },
            {
                "domain": "Digital phenotype",
                "result": "Locked phase map",
                "value": "Five clinically interpretable CGM phases: stable in-range, high-variability oscillatory, persistent hyperglycaemia, circadian-disruption, and hypoglycaemia-susceptible.",
                "interpretation_for_npj": "This is the central novelty. The manuscript should present a computable CGM digital phenotype, not a clustering benchmark.",
            },
            {
                "domain": "Robustness",
                "result": "Bootstrap stability",
                "value": f"ARI median {fmt(stability['adjusted_rand_index'].median())}, IQR {fmt(stability['adjusted_rand_index'].quantile(0.25))}-{fmt(stability['adjusted_rand_index'].quantile(0.75))}; silhouette median {fmt(stability['silhouette'].median())}.",
                "interpretation_for_npj": "Phase assignments are reproducible enough for a research-grade phenotype, but silhouette is modest and should not be oversold as discrete biology.",
            },
            {
                "domain": "Internal validation",
                "result": "Nested cross-validation",
                "value": "; ".join(
                    f"{target_name(r.target)} best AUROC {fmt(r.auroc_mean)} ({feature_name(r.feature_set)}, {r.model})"
                    for r in nested_best.itertuples()
                ),
                "interpretation_for_npj": "Performance supports construct validity, but clinical+CGM and phase-map models are close; leaderboard framing would be weak.",
            },
            {
                "domain": "Transportability",
                "result": "Leave-one-study-out validation",
                "value": "; ".join(
                    f"{target_name(r.target)} best mean AUROC {fmt(r.auroc_mean)} ({feature_name(r.feature_set)}, {r.model})"
                    for r in loso_best.itertuples()
                ),
                "interpretation_for_npj": "Useful evidence of study-level generalization, but reviewers may still ask for untouched external validation.",
            },
            {
                "domain": "Frozen external validation",
                "result": "Loop public dataset",
                "value": "; ".join(
                    f"{r.target_display} {r.feature_display} AUROC {fmt(r.auroc)}, AUPRC {fmt(r.auprc)}, Brier {fmt(r.brier)}, ECE {fmt(r.expected_calibration_error)}"
                    for r in external_pivot.itertuples()
                ),
                "interpretation_for_npj": "Strong P0 addition. It demonstrates locked transportability, but phase-map does not clearly outperform clinical+CGM and TIR calibration needs work.",
            },
            {
                "domain": "External phase shift",
                "result": "Loop phase distribution",
                "value": "; ".join(f"{r.phase_label_en}: {int(r.n)}" for r in loop_phase.itertuples()),
                "interpretation_for_npj": "The external population is heavily stable-phase enriched; this should be treated as distribution shift, not ignored.",
            },
            {
                "domain": "Treatment-response heterogeneity",
                "result": "Adjusted HTE by phase",
                "value": f"Largest adjusted risk difference: {top_hte.phase_label_en}, RD {fmt(top_hte.adjusted_risk_difference)} (95% bootstrap CI {fmt(top_hte.bootstrap_ci_low)}-{fmt(top_hte.bootstrap_ci_high)}).",
                "interpretation_for_npj": "Important for a phase-guided digital care workflow, but it remains retrospective and hypothesis-generating.",
            },
            {
                "domain": "Fairness and calibration",
                "result": "Subgroup audit",
                "value": f"Largest evaluable AUROC shortfall: {fair_top_all.iloc[0]['subgroup_variable']}={fair_top_all.iloc[0]['subgroup_display']}, n={int(fair_top_all.iloc[0]['n'])}, delta AUROC {fmt(fair_top_all.iloc[0]['delta_auroc_vs_overall'])}.",
                "interpretation_for_npj": "This is a critical reviewer risk. Small race subgroup sizes and study-specific underperformance need transparent uncertainty and mitigation.",
            },
            {
                "domain": "Software readiness",
                "result": "Algorithm card and software specification",
                "value": "Algorithm card, input/output schema, software specification, workflow source tables, and revised main figures are complete in p0_workup.",
                "interpretation_for_npj": "This moves the work from analysis-only toward a digital medicine artifact, but code packaging and test fixtures remain needed.",
            },
        ]
    )
    current_results.to_csv(TABLES / "current_results_evidence_table.csv", index=False)

    gap_matrix = pd.DataFrame(
        [
            ("Journal fit", "Moderate-strong", "Digital phenotype, external validation, algorithm card, software spec, workflow figures.", "Need explicit alignment with validated digital biomarkers/software/virtual-care use case, not a generic ML model.", "Rewrite abstract/introduction around CGM digital phenotype and silent-mode care workflow.", "P0"),
            ("Novelty", "Moderate", "Five-phase CGM state space with stability and HTE signal.", "Current phase map is still summary-CGM based; phase labels may be seen as post-hoc clusters.", "Add raw-CGM transition features or justify summary phenotype as deployable and robust.", "P1"),
            ("External validation", "Moderate-strong", "Loop frozen validation completed without tuning.", "Only one frozen external dataset; Loop phase distribution is skewed stable.", "Run secondary frozen validations in compatible jaeb_public_extra datasets and report transportability failure modes.", "P0"),
            ("Calibration", "Moderate", "Brier/ECE reported internally and externally.", "External TIR ECE is high (~0.23); clinical thresholds need calibration audit.", "Add prespecified intercept/slope recalibration sensitivity and calibration plots by phase/subgroup.", "P0"),
            ("Fairness", "Incomplete-moderate", "Subgroup audit available by age, sex, race/ethnicity, study, phase, baseline HbA1c.", "Small race subgroup n and study-specific AUROC shortfalls are visible.", "Report uncertainty, minimum-n rules, subgroup calibration, and mitigation boundaries.", "P0"),
            ("Clinical utility", "Moderate", "Decision curve and phase-based HTE have been converted to workflow source data.", "No prospective evidence that clinicians can use the output safely or consistently.", "Design silent-mode clinician-facing workflow study with no autonomous treatment changes.", "P1"),
            ("Software artifact", "Moderate", "Algorithm card/spec/schema exist.", "No installable package, test fixtures, model card versioning, or reproducible release bundle yet.", "Create locked Python/R package, Docker/conda environment, toy data, and reproduction script.", "P0"),
            ("Prospective translation", "Weak", "Retrospective JAEB and Loop only.", "npj reviewers may see no real digital care deployment validation.", "Launch 80-120 participant silent-mode pilot or at least clinician-vignette validation before submission.", "P1"),
            ("Manuscript risk", "Moderate", "Strong story if framed as computable phenotype.", "If framed as ML benchmark, contribution is not high enough.", "Rebuild manuscript around phenotype validity, transportability, calibration, and workflow.", "P0"),
        ],
        columns=["domain", "current_readiness", "supporting_evidence", "main_gap", "next_action", "priority"],
    )
    gap_matrix.to_csv(TABLES / "npj_gap_matrix.csv", index=False)

    workplan_rows = [
        ("W01", "0-2 weeks", "Manuscript claim", "Freeze the central claim and overclaim guardrails.", "One-page claim map: digital phenotype, not clustering; decision support, not autonomous treatment.", "PI/statistical lead", "P0", "Go if all figures map to one claim."),
        ("W02", "0-2 weeks", "Data lineage", "Create data provenance and leakage audit across all JAEB development and Loop external validation files.", "Data lineage table; train/external separation statement; reproducibility hash manifest.", "Data lead", "P0", "No shared participant/study leakage."),
        ("W03", "0-3 weeks", "Secondary external validation", "Screen remaining jaeb_public_extra datasets for compatible baseline CGM and follow-up outcomes.", "Compatibility matrix and at least one additional frozen validation if feasible.", "Data lead/statistician", "P0", "Proceed if >=1 additional dataset has >=100 evaluable participants or document infeasibility."),
        ("W04", "0-4 weeks", "Calibration upgrade", "Add calibration curves, slope/intercept, ECE, and prespecified recalibration sensitivity for Loop and LOSO.", "Calibration supplement; thresholds for HbA1c/TIR response.", "Statistician", "P0", "ECE <0.10 after simple recalibration for intended risk display, or restrict to ranking/phenotype use."),
        ("W05", "0-4 weeks", "Fairness audit", "Quantify subgroup performance uncertainty and phase distribution by age, sex, race/ethnicity, study, baseline HbA1c.", "Fairness table with minimum-n rules and uncertainty intervals.", "Statistician", "P0", "No unaddressed high-n subgroup with severe degradation."),
        ("W06", "2-6 weeks", "Software release", "Package phase-map code as a locked research software artifact.", "Versioned package; input/output schema; unit tests; toy data; figure reproduction script.", "Engineering lead", "P0", "Fresh-machine reproduction succeeds."),
        ("W07", "2-6 weeks", "Main manuscript", "Draft Results around four claims: phenotype derivation, validity, frozen transportability, digital care workflow.", "Nature-style Results draft with real numbers and figure calls.", "Writing lead", "P0", "No generic ML leaderboard language remains."),
        ("W08", "4-8 weeks", "Raw CGM upgrade", "Where raw CGM exists, derive transition entropy, nocturnal instability, dwell time, phase transitions, and rhythm features.", "Sensitivity analysis or upgraded phenotype appendix.", "Data science lead", "P1", "Improves novelty or supports why summary-CGM phenotype is sufficient."),
        ("W09", "6-10 weeks", "Clinician workflow validation", "Run vignette-based usability and interpretability evaluation with diabetes clinicians.", "Protocol, survey, clinician agreement/utility results.", "Clinical lead", "P1", "Median usefulness >=4/5 and no major safety misunderstanding."),
        ("W10", "8-16 weeks", "Silent-mode pilot protocol", "Design prospective CGM phase assignment study without treatment recommendations.", "IRB-ready protocol; analysis plan; data capture forms.", "Clinical lead", "P1", "Feasible recruitment and data capture plan."),
        ("W11", "12-24 weeks", "Silent-mode pilot execution", "Enroll 80-120 CGM users; run algorithm in background; collect prediction, stability, clinician review, burden outcomes.", "Prospective validation dataset and analysis report.", "Clinical/statistical team", "P1", ">=90% successful phase assignment; calibration acceptable for intended use."),
        ("W12", "20-28 weeks", "Submission package", "Finalize TRIPOD-AI style checklist, algorithm card, code/data availability, ethics, limitations.", "Submission-ready manuscript, supplement, source data, repository.", "Full team", "P0/P1", "Submit to npj Digital Medicine if prospective/workflow evidence is adequate."),
    ]
    workplan = pd.DataFrame(
        workplan_rows,
        columns=["task_id", "time_window", "workstream", "task", "deliverable", "owner", "priority", "success_criterion"],
    )
    workplan.to_csv(TABLES / "npj_90_180_day_workplan.csv", index=False)

    go_no_go = pd.DataFrame(
        [
            ("External discrimination", "Phase-map frozen AUROC should be >=0.75 for at least one clinically meaningful outcome, with clinical+CGM comparator reported.", "Current Loop phase-map AUROC: HbA1c 0.758; TIR 0.827.", "Go on discrimination, but avoid claiming superiority over clinical+CGM."),
            ("Calibration", "External ECE ideally <0.10 for displayed absolute risk or improved by prespecified simple recalibration.", "Current Loop ECE: HbA1c phase-map 0.103; TIR phase-map 0.231.", "Conditional go: TIR absolute-risk display needs recalibration or downgrade to ranking/phenotype context."),
            ("Transportability", "At least one untouched dataset plus LOSO validation, with phase distribution shift explicitly reported.", "Loop frozen validation and LOSO complete; Loop is stable-phase enriched.", "Go if framed transparently; strengthen with another frozen dataset if possible."),
            ("Fairness", "No high-confidence, high-n subgroup failure without mitigation or limitation.", "Asian subgroup shortfall is severe but n=29; METFORMIN_T1D and low baseline HbA1c underperformance visible.", "Conditional go after uncertainty intervals and minimum-n reporting."),
            ("Clinical utility", "Decision curve/HTE must be translated to a safe clinician-in-the-loop workflow.", "Workflow source data and Figure 4 complete.", "Go for retrospective workflow proposal; stronger go after clinician vignette or pilot."),
            ("Software reproducibility", "Independent rerun should regenerate tables/figures from locked inputs.", "Algorithm card/spec exist; package/release not yet complete.", "No-go for submission until release bundle and tests are finished."),
            ("Prospective evidence", "For high-confidence npj target, at least silent-mode or clinician-workflow validation should be added.", "Not yet done.", "Without this, submission is possible but high risk; with it, target becomes much more realistic."),
        ],
        columns=["criterion", "threshold_or_rule", "current_status", "recommendation"],
    )
    go_no_go.to_csv(TABLES / "npj_go_no_go_criteria.csv", index=False)

    manuscript = pd.DataFrame(
        [
            ("Figure 1", "Computable CGM digital phenotype", "Algorithm flow, order parameters, locked phase map.", str(P0 / "figures" / "figure1_cgm_digital_phenotype.png"), "Make the first visual signal a digital phenotype, not a model benchmark."),
            ("Figure 2", "Phenotype validity", "Phase CGM signatures, stability, baseline/follow-up outcome structure.", str(P0 / "figures" / "figure2_phenotype_validity.png"), "Demonstrate construct validity and reproducibility."),
            ("Figure 3", "Frozen validation and subgroup audit", "Loop AUROC; phase-map subgroup transportability.", str(P0 / "figures" / "figure3_validation_and_fairness.png"), "Show transportability and disclose fairness/calibration risks."),
            ("Figure 4", "Phase-guided digital care workflow", "HTE by phase and silent-mode workflow.", str(P0 / "figures" / "figure4_clinical_utility_workflow.png"), "Convert statistics into a clinical digital-care concept."),
            ("Extended Data 1", "Data provenance and cohort flow", "JAEB development datasets, Loop frozen dataset, missingness, leakage audit.", "To build", "Needed for reviewer trust."),
            ("Extended Data 2", "Calibration curves", "Internal, LOSO, Loop, subgroup calibration.", "To build", "Needed because external TIR ECE is high."),
            ("Supplementary Table 1", "Algorithm card and schema", "Inputs, outputs, missingness, phase assignment version.", str(P0 / "docs" / "phase_map_algorithm_card.md"), "Make software artifact explicit."),
            ("Supplementary Table 2", "Fairness audit", "All subgroup metrics and minimum-n rules.", str(P0 / "tables" / "subgroup_fairness_calibration_audit.csv"), "Transparent digital medicine audit."),
        ],
        columns=["item", "message", "content", "current_source", "npj_role"],
    )
    manuscript.to_csv(TABLES / "npj_manuscript_storyboard.csv", index=False)

    report = f"""
# 面向 npj Digital Medicine 的当前结果整理与后续研究计划

生成日期：2026-06-18  
目标期刊：npj Digital Medicine  
官方定位参考：Nature npj Digital Medicine aims and scope，重点包括 digital medicine、validated digital biomarkers、AI/ML、software/sensors、virtual-care models；通常不适合仅有小样本或纯初步观察性描述的研究。

## 一句话判断

当前工作已经从“普通 CGM 机器学习 benchmark”推进到了“可计算 CGM digital phenotype + frozen external validation + algorithm card/software specification + subgroup audit + phase-guided care workflow”的雏形。  

如果现在立即投稿，风险仍偏高；主要短板不是模型 AUROC，而是：外部验证仍只有 Loop 一个 frozen dataset，TIR 绝对风险校准偏弱，公平性审计暴露了小样本 subgroup 风险，且尚无 prospective/silent-mode workflow evidence。若补齐软件发布、校准/公平性、第二外部验证或 clinician/silent-mode 验证，才更像 npj Digital Medicine 级别的数字医学论文。

## 当前结果盘点

### 1. 数据和数字表型

- JAEB development corpus：{dev_inventory.shape[0]} 个已下载清洗的 JAEB development datasets。
- phase-map baseline 样本：{phase_features['participant_id'].nunique()} 名参与者。
- harmonized CGM summary：{cgm_long.shape[0]} 行。
- 锁定相位：stable in-range、high-variability oscillatory、persistent hyperglycaemia、circadian-disruption、hypoglycaemia-susceptible。
- Bootstrap stability：ARI 中位数 {fmt(stability['adjusted_rand_index'].median())}，IQR {fmt(stability['adjusted_rand_index'].quantile(0.25))}-{fmt(stability['adjusted_rand_index'].quantile(0.75))}；silhouette 中位数 {fmt(stability['silhouette'].median())}。

解释：这足以支撑“research-grade CGM digital phenotype”，但不能写成已证实的生物学亚型。

### 2. 内部和跨研究验证

Nested CV 最佳结果：

{nested_best.assign(target=lambda x: x['target'].map(target_name), feature_set=lambda x: x['feature_set'].map(feature_name))[['target','feature_set','model','total_test_n','auroc_mean','auprc_mean','brier_mean']].to_string(index=False)}

Leave-one-study-out 最佳结果：

{loso_best.assign(target=lambda x: x['target'].map(target_name), feature_set=lambda x: x['feature_set'].map(feature_name))[['target','feature_set','model','heldout_study_count','total_test_n','auroc_mean','auprc_mean','brier_mean']].to_string(index=False)}

解释：预测性能可用来证明 digital phenotype 的外部效度，但不能把论文写成“phase-map 模型显著优于所有 ML 模型”。

### 3. Loop frozen external validation

Loop 没有参与建模或调参。外部验证库存：

{external_inventory.to_string(index=False)}

Loop 外部验证结果：

{external_pivot[['target_display','feature_display','test_n','positive_rate','auroc','auprc','brier','expected_calibration_error']].to_string(index=False)}

Loop phase distribution：

{loop_phase[['phase_id','phase_label_en','n']].to_string(index=False)}

解释：这是很关键的 P0 增强。优势是锁定验证成立；限制是 Loop 强烈偏 stable phase，且 phase-map 并未明显优于 clinical+CGM comparator。TIR 结局的 ECE 约 0.23，说明若要显示绝对风险，需要重新校准或改成 phenotype/ranking 支持。

### 4. HTE 与 digital care workflow

- 最大 adjusted risk difference：{top_hte.phase_label_en}，RD {fmt(top_hte.adjusted_risk_difference)}，95% bootstrap CI {fmt(top_hte.bootstrap_ci_low)}-{fmt(top_hte.bootstrap_ci_high)}。
- 这已经被转化为 phase-guided digital care workflow：phase assigned -> risk/context displayed -> clinician review -> care focus selected -> reassess with new CGM。

解释：这是 npj 叙事的转化支点。但必须写成 clinician-in-the-loop / silent-mode decision support，不能写成自动治疗建议。

### 5. 公平性和校准审计

Top subgroup audit signals：

{fair_top_all[['target','feature_set','model','subgroup_variable','subgroup_display','n','auroc','delta_auroc_vs_overall','brier','expected_calibration_error']].to_string(index=False)}

Phase-map model focused audit：

{fair_focus[['target','feature_set','model','subgroup_variable','subgroup_display','n','auroc','delta_auroc_vs_overall','brier','expected_calibration_error']].to_string(index=False)}

解释：亚洲 subgroup 的 AUROC shortfall 很大但 n=29，不能过度解读；METFORMIN_T1D、baseline HbA1c <7、circadian-disruption phase 是需要在补充材料里透明呈现的 reviewer risk。

## 目标期刊投稿定位

推荐题目方向：

**A reproducible glycaemic phase map from continuous glucose monitoring identifies digital phenotypes of treatment response in public diabetes trials**

核心主张：

1. CGM summary 可以转化为可复现、可解释的 glycaemic state space。
2. 锁定 phase map 是一种 computable CGM digital phenotype，而不是普通聚类。
3. 该 phenotype 在 JAEB 多研究和 Loop frozen dataset 中具有可迁移性。
4. Phase membership 能组织治疗反应异质性，并支持 clinician-in-the-loop 的 digital care workflow。

禁止/弱化的说法：

- 不说 phase 是已证实的生物学亚型。
- 不说 phase-map 模型显著优于所有 ML 模型。
- 不把 HTE 解释成确定性临床治疗推荐。
- 不把 retrospective public-data result 写成已部署数字医疗工具。

## 后续研究计划

### P0：投稿前必须完成

1. **第二外部验证或外部数据兼容性矩阵**  
   继续筛查 `jaeb_public_extra`，对 GLAM、RacialDifferences、SevereHypo、CGMND、PSO 系列等做兼容性表。若有 baseline CGM + follow-up HbA1c/TIR，按 Loop 同样的 frozen rule 跑一次；若没有，明确说明为何不能作为验证集。

2. **校准升级**  
   对 Loop 和 LOSO 做 calibration curve、slope/intercept、ECE、Brier decomposition。对 TIR response 做预先声明的 intercept/slope recalibration sensitivity；若校准仍弱，就把输出定位为 phenotype/ranking，而非绝对风险。

3. **公平性和可迁移性不确定性**  
   对 subgroup AUROC/ECE 增加 bootstrap CI 和 minimum-n reporting rule。对 small-n subgroup 不给强结论，但要透明呈现。

4. **软件发布包**  
   输出 versioned phase-map package、schema、toy data、unit tests、figure reproduction script、environment lock。算法卡和 software spec 已有，但还需要可复现执行包。

5. **Results 初稿重写**  
   按四段写：phenotype derivation -> validity -> frozen validation/fairness -> phase-guided workflow。不要以模型排行榜开头。

### P1：显著提高 npj 命中率

1. **Raw CGM time-series upgrade**  
   从 summary-CGM 升级到 transition entropy、dwell time、nocturnal instability、day-night transitions、hypoglycaemia cluster recurrence。即使作为 sensitivity/extended analysis，也能显著提高数字表型深度。

2. **Clinician vignette validation**  
   让糖尿病临床医生在病例 vignette 中查看 phase-map 输出，评价可解释性、潜在误用、安全边界、治疗讨论价值。

3. **Silent-mode prospective pilot**  
   80-120 名 CGM 用户，算法后台运行，不给治疗建议。主要终点：phase assignment success、phase stability、prospective calibration、clinician interpretability、patient/clinician burden。

4. **TRIPOD-AI / algorithm-card 对齐**  
   把预测模型报告、校准、外部验证、数据偏倚、适用边界、human oversight 写入补充材料。

### P2：若要冲更强 digital medicine 转化

1. Phase-guided decision support 原型。
2. EHR/CGM app 集成的 silent workflow。
3. 小型 stepped-wedge 或 cluster-randomized workflow trial。

## Go/No-Go 建议

- **现在状态**：可作为强预投稿/内部评审包，但正式投 npj 风险仍高。
- **最小投稿条件**：完成第二外部验证可行性矩阵、校准升级、公平性 CI、软件发布包、Results 重写。
- **理想投稿条件**：再加 clinician vignette 或 silent-mode prospective pilot。
- **若 prospective pilot 做不了**：仍可投稿，但标题和结论必须非常克制，定位为 retrospective validation of a computable CGM digital phenotype。

## 本次生成的配套文件

- `tables/current_results_evidence_table.csv`
- `tables/npj_gap_matrix.csv`
- `tables/npj_90_180_day_workplan.csv`
- `tables/npj_go_no_go_criteria.csv`
- `tables/npj_manuscript_storyboard.csv`
"""
    write(DOCS / "npj_current_results_and_research_plan_zh.md", report)

    manifest = {
        "created": "2026-06-18",
        "objective": "npj Digital Medicine current results synthesis and next research plan",
        "source_roots": [str(PHASE), str(P0)],
        "outputs": [
            str(DOCS / "npj_current_results_and_research_plan_zh.md"),
            str(TABLES / "current_results_evidence_table.csv"),
            str(TABLES / "npj_gap_matrix.csv"),
            str(TABLES / "npj_90_180_day_workplan.csv"),
            str(TABLES / "npj_go_no_go_criteria.csv"),
            str(TABLES / "npj_manuscript_storyboard.csv"),
        ],
    }
    (OUT / "research_plan_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"wrote npj Digital Medicine current plan to {OUT}")


if __name__ == "__main__":
    main()
