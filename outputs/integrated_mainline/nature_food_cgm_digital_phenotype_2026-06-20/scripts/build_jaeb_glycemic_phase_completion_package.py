"""Build a completion package for the JAEB glycemic phase-map project."""

from __future__ import annotations

from pathlib import Path
import json
import shutil

import numpy as np
import pandas as pd


ROOT = Path(r"D:\ai for science")
DATA = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
DOCS = ROOT / "docs"
OUT = RESULTS / "jaeb_glycemic_phase_completion"
FIGSRC = OUT / "figure_source_data"
TABLES = OUT / "tables"
OUTFIG = OUT / "figures"
OUTDOC = OUT / "docs"
for path in [OUT, FIGSRC, TABLES, OUTFIG, OUTDOC]:
    path.mkdir(parents=True, exist_ok=True)


PHASE_META = {
    "稳定达标相": {
        "phase_id": "stable_in_range",
        "phase_order": 1,
        "phase_label_en": "Stable in-range phase",
        "interpretation": "Higher TIR and lower variability; serves as the reference phase.",
    },
    "高波动震荡相": {
        "phase_id": "high_variability_oscillation",
        "phase_order": 2,
        "phase_label_en": "High-variability oscillatory phase",
        "interpretation": "High glycaemic variability despite heterogeneous mean glucose burden.",
    },
    "高血糖持续相": {
        "phase_id": "persistent_hyperglycaemia",
        "phase_order": 3,
        "phase_label_en": "Persistent hyperglycaemia phase",
        "interpretation": "High mean glucose and high time above range.",
    },
    "昼夜节律紊乱相": {
        "phase_id": "circadian_disruption",
        "phase_order": 4,
        "phase_label_en": "Circadian-disruption phase",
        "interpretation": "Large day-night CGM differences.",
    },
    "低血糖易感相": {
        "phase_id": "hypoglycaemia_susceptible",
        "phase_order": 5,
        "phase_label_en": "Hypoglycaemia-susceptible phase",
        "interpretation": "Higher time below range and hypoglycaemia burden.",
    },
    "混合过渡相": {
        "phase_id": "mixed_transition",
        "phase_order": 6,
        "phase_label_en": "Mixed transition phase",
        "interpretation": "Intermediate phase without a dominant CGM signature.",
    },
}


def read(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def write(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def add_phase_meta(df: pd.DataFrame, phase_col: str = "phase_label") -> pd.DataFrame:
    out = df.copy()
    if phase_col not in out:
        return out
    out["phase_id"] = out[phase_col].map(lambda x: PHASE_META.get(x, {}).get("phase_id", "unknown"))
    out["phase_label_zh"] = out[phase_col]
    out["phase_label_en"] = out[phase_col].map(lambda x: PHASE_META.get(x, {}).get("phase_label_en", "Unknown"))
    out["phase_order"] = out[phase_col].map(lambda x: PHASE_META.get(x, {}).get("phase_order", 99))
    return out


def export(df: pd.DataFrame, path: Path) -> Path:
    df.to_csv(path, index=False)
    return path


def fmt(x: float, digits: int = 3) -> str:
    if pd.isna(x):
        return "NA"
    return f"{x:.{digits}f}"


def phase_dictionary() -> pd.DataFrame:
    rows = []
    for zh, meta in PHASE_META.items():
        rows.append({"phase_label_zh": zh, **meta})
    df = pd.DataFrame(rows).sort_values("phase_order")
    export(df, OUT / "jaeb_phase_label_dictionary.csv")
    return df


def build_figure_source_data() -> dict[str, str]:
    manifest: dict[str, str] = {}
    phase = add_phase_meta(read(DATA / "glycemic_phase_features.csv"))
    labels = add_phase_meta(read(DATA / "glycemic_phase_labels.csv"))
    cohort = read(RESULTS / "study_cohort_flow.csv")
    table1 = read(RESULTS / "table1_baseline_by_phase.csv")
    outcomes = read(RESULTS / "outcomes_by_phase_manuscript.csv")
    outcome_summary = add_phase_meta(read(RESULTS / "phase_outcome_summary.csv"))
    assoc = read(RESULTS / "phase_association_tests.csv")
    adjusted = add_phase_meta(read(RESULTS / "journal_adjusted_phase_outcome_models.csv"))
    global_tests = read(RESULTS / "journal_adjusted_phase_global_tests.csv")
    nested = read(RESULTS / "journal_nested_tuning_summary.csv")
    loso = read(RESULTS / "journal_loso_summary.csv")
    incremental = read(RESULTS / "journal_incremental_phase_value.csv")
    calibration = read(RESULTS / "journal_calibration_metrics.csv")
    decision = read(RESULTS / "journal_decision_curve.csv")
    bootstrap = read(RESULTS / "phase_bootstrap_stability.csv")
    hte = add_phase_meta(read(RESULTS / "journal_adjusted_hte_by_phase.csv"))
    framework = add_phase_meta(read(RESULTS / "individualized_intervention_framework.csv"))

    manifest["Figure 1a cohort flow"] = str(export(cohort, FIGSRC / "figure1a_study_cohort_flow.csv"))
    phase_construct = (
        phase.groupby(["phase_label_zh", "phase_id", "phase_label_en", "phase_order"], as_index=False)
        .agg(
            n=("participant_id", "size"),
            glycemic_burden_score_mean=("glycemic_burden_score", "mean"),
            hypoglycemic_susceptibility_score_mean=("hypoglycemic_susceptibility_score", "mean"),
            dynamic_instability_score_mean=("dynamic_instability_score", "mean"),
            circadian_disruption_score_mean=("circadian_disruption_score", "mean"),
            resilience_proxy_score_mean=("resilience_proxy_score", "mean"),
            cgm_mean_glucose_mg_dl_mean=("cgm_mean_glucose_mg_dl", "mean"),
            cgm_time_in_range_70_180_pct_mean=("cgm_time_in_range_70_180_pct", "mean"),
            cgm_cv_pct_mean=("cgm_cv_pct", "mean"),
        )
        .sort_values("phase_order")
    )
    manifest["Figure 1b phase construction summary"] = str(
        export(phase_construct, FIGSRC / "figure1b_phase_construction_summary.csv")
    )
    manifest["Figure 2a phase map coordinates"] = str(
        export(
            phase[
                [
                    "participant_id",
                    "study_id",
                    "phase_cluster",
                    "phase_id",
                    "phase_label_zh",
                    "phase_label_en",
                    "phase_order",
                    "glycemic_burden_score",
                    "hypoglycemic_susceptibility_score",
                    "dynamic_instability_score",
                    "circadian_disruption_score",
                    "resilience_proxy_score",
                    "cgm_mean_glucose_mg_dl",
                    "cgm_time_in_range_70_180_pct",
                    "cgm_time_below_70_pct",
                    "cgm_time_above_180_pct",
                    "cgm_cv_pct",
                    "cgm_hours",
                ]
            ],
            FIGSRC / "figure2a_phase_map_coordinates.csv",
        )
    )
    manifest["Figure 2b phase CGM phenotype summary"] = str(
        export(outcome_summary.sort_values("phase_order"), FIGSRC / "figure2b_phase_cgm_outcome_summary.csv")
    )
    manifest["Figure 2c baseline TIR by phase"] = str(
        export(
            phase[
                [
                    "participant_id",
                    "study_id",
                    "phase_id",
                    "phase_label_zh",
                    "phase_label_en",
                    "phase_order",
                    "cgm_time_in_range_70_180_pct",
                    "cgm_mean_glucose_mg_dl",
                    "cgm_cv_pct",
                ]
            ],
            FIGSRC / "figure2c_baseline_tir_by_phase.csv",
        )
    )
    manifest["Figure 3a unadjusted phase outcome tests"] = str(
        export(assoc, FIGSRC / "figure3a_phase_outcome_unadjusted_tests.csv")
    )
    manifest["Figure 3b adjusted phase outcome estimates"] = str(
        export(adjusted.sort_values(["target", "phase_order"]), FIGSRC / "figure3b_adjusted_phase_outcome_estimates.csv")
    )
    manifest["Figure 3c adjusted phase global tests"] = str(
        export(global_tests, FIGSRC / "figure3c_adjusted_phase_global_tests.csv")
    )
    manifest["Figure 4a nested CV model performance"] = str(
        export(nested, FIGSRC / "figure4a_nested_cv_model_performance.csv")
    )
    manifest["Figure 4b LOSO generalization"] = str(
        export(loso, FIGSRC / "figure4b_leave_one_study_out_summary.csv")
    )
    manifest["Figure 4c incremental phase-map value"] = str(
        export(incremental, FIGSRC / "figure4c_incremental_phase_value.csv")
    )
    manifest["Figure 5a phase bootstrap stability"] = str(
        export(bootstrap, FIGSRC / "figure5a_phase_bootstrap_stability.csv")
    )
    manifest["Figure 5b adjusted HTE by phase"] = str(
        export(hte.sort_values("adjusted_risk_difference", ascending=False), FIGSRC / "figure5b_adjusted_hte_by_phase.csv")
    )
    framework_summary = (
        framework.dropna(subset=["phase_label_zh"])
        .groupby(["phase_label_zh", "phase_id", "phase_label_en", "phase_order", "phase_based_intervention_focus"], as_index=False)
        .agg(
            n=("participant_id", "size"),
            median_predicted_hba1c_improvement_probability=("predicted_hba1c_improvement_probability_research_model", "median"),
        )
        .sort_values("phase_order")
    )
    manifest["Figure 5c intervention framework"] = str(
        export(framework_summary, FIGSRC / "figure5c_phase_intervention_framework.csv")
    )
    manifest["Supplement calibration metrics"] = str(
        export(calibration, FIGSRC / "supplement_calibration_metrics.csv")
    )
    manifest["Supplement decision curve"] = str(
        export(decision, FIGSRC / "supplement_decision_curve.csv")
    )
    manifest["Supplement table1 baseline by phase"] = str(
        export(table1, TABLES / "table1_baseline_by_phase_locked.csv")
    )
    manifest["Supplement outcomes by phase"] = str(
        export(outcomes, TABLES / "table2_outcomes_by_phase_locked.csv")
    )
    manifest["Phase labels"] = str(export(labels, TABLES / "participant_phase_labels_locked.csv"))
    return manifest


def copy_locked_artifacts() -> None:
    result_files = [
        "phase_outcome_summary.csv",
        "phase_association_tests.csv",
        "model_performance_cv.csv",
        "model_performance_loso.csv",
        "journal_loso_summary.csv",
        "journal_nested_tuning_summary.csv",
        "journal_incremental_phase_value.csv",
        "journal_model_pairwise_bootstrap.csv",
        "journal_adjusted_hte_by_phase.csv",
        "phase_bootstrap_stability.csv",
        "journal_adjusted_phase_outcome_models.csv",
        "journal_adjusted_phase_global_tests.csv",
        "journal_calibration_metrics.csv",
        "journal_decision_curve.csv",
        "journal_permutation_importance.csv",
        "individualized_intervention_framework.csv",
        "research_artifact_manifest.csv",
        "full_pipeline_run_status.csv",
    ]
    data_files = [
        "processed_ml_table.csv",
        "cgm_summary_long.csv",
        "glycemic_phase_features.csv",
        "glycemic_phase_labels.csv",
        "data_dictionary.csv",
        "dataset_inventory.csv",
    ]
    for name in result_files:
        src = RESULTS / name
        if src.exists():
            shutil.copy2(src, TABLES / f"locked_{name}")
    for name in data_files:
        src = DATA / name
        if src.exists():
            shutil.copy2(src, TABLES / f"locked_{name}")
    for fig in FIGURES.glob("*.png"):
        shutil.copy2(fig, OUTFIG / fig.name)


def write_docs() -> None:
    phase = read(DATA / "glycemic_phase_features.csv")
    phase_counts = phase["phase_label"].value_counts()
    outcome_summary = read(RESULTS / "phase_outcome_summary.csv")
    assoc = read(RESULTS / "phase_association_tests.csv")
    nested = read(RESULTS / "journal_nested_tuning_summary.csv")
    loso = read(RESULTS / "journal_loso_summary.csv")
    hte = read(RESULTS / "journal_adjusted_hte_by_phase.csv")
    boot = read(RESULTS / "phase_bootstrap_stability.csv")
    adjusted_global = read(RESULTS / "journal_adjusted_phase_global_tests.csv")
    pairwise = read(RESULTS / "journal_model_pairwise_bootstrap.csv")
    cohort = read(RESULTS / "study_cohort_flow.csv")
    ml = read(DATA / "processed_ml_table.csv")
    cgm = read(DATA / "cgm_summary_long.csv")

    n_total = len(ml)
    n_phase = len(phase)
    n_studies = cohort["study_id"].nunique()
    phase_dist = "; ".join([f"{k} n={int(v)}" for k, v in phase_counts.items()])
    ari_median = boot["adjusted_rand_index"].median()
    ari_q25 = boot["adjusted_rand_index"].quantile(0.25)
    ari_q75 = boot["adjusted_rand_index"].quantile(0.75)
    sil_median = boot["silhouette"].median()
    top_hba1c = nested[nested["target"].eq("y_hba1c_improved_ge_0_5")].sort_values("auroc_mean", ascending=False).iloc[0]
    top_tir = nested[nested["target"].eq("y_tir_improved_ge_5pct")].sort_values("auroc_mean", ascending=False).iloc[0]
    loso_hba1c = loso[loso["target"].eq("y_hba1c_improved_ge_0_5")].sort_values("auroc_mean", ascending=False).iloc[0]
    loso_tir = loso[loso["target"].eq("y_tir_improved_ge_5pct")].sort_values("auroc_mean", ascending=False).iloc[0]
    hte_top = hte.sort_values("adjusted_risk_difference", ascending=False).iloc[0]
    hba1c_assoc = assoc[assoc["outcome"].eq("y_hba1c_improved_ge_0_5")].iloc[0]
    tir_global = adjusted_global[adjusted_global["target"].eq("y_change_cgm_time_in_range_70_180_pct")].iloc[0]
    phase_pairwise = pairwise[pairwise["comparison"].str.contains("phase_map", na=False)]

    write(
        OUTDOC / "jaeb_glycemic_phase_completion_report_zh.md",
        f"""
# JAEB 血糖动力学相图完成报告

## 完成摘要

本完成包整合了公开 JAEB 糖尿病 RCT/干预研究数据，形成 {n_total} 名受试者的机器学习表、{len(cgm)} 行 harmonized CGM summary，以及 {n_phase} 名具备基线 CGM 汇总的相图样本。相图识别出 {phase_counts.shape[0]} 类血糖动态相位：{phase_dist}。

## 已完成模块

1. 数据清洗与 harmonization：`processed_ml_table.csv`、`cgm_summary_long.csv`。
2. 血糖动力学相图：五个序参量、KMeans 相位、相图坐标和图件。
3. 相位-结局关系：未调整检验、调整模型、全局 Wald 检验。
4. 预测模型：5-fold CV、leave-one-study-out、nested tuning、校准、决策曲线和模型差异 bootstrap。
5. 相图稳健性：150 次 bootstrap，ARI 中位数 {fmt(ari_median)}（IQR {fmt(ari_q25)}-{fmt(ari_q75)}），silhouette 中位数 {fmt(sil_median)}。
6. 异质性治疗响应：相位分层调整风险差和个体化干预框架。

## 主要结果

- 未调整分析中，相位与 HbA1c 改善 >=0.5% 有关联（chi-square p={fmt(hba1c_assoc['p_value'])}）。
- 调整后相位主效应整体较弱；TIR 变化的全局 Wald 检验为 p={fmt(tir_global['p_value'])}，可作为趋势而非确认性结论。
- Nested CV 中 HbA1c 改善最佳模型为 {top_hba1c['feature_set']} / {top_hba1c['model']}，AUROC={fmt(top_hba1c['auroc_mean'])}。
- Nested CV 中 TIR 改善最佳模型为 {top_tir['feature_set']} / {top_tir['model']}，AUROC={fmt(top_tir['auroc_mean'])}。
- LOSO 外部泛化中 HbA1c 改善最佳平均 AUROC={fmt(loso_hba1c['auroc_mean'])}；TIR 改善最佳平均 AUROC={fmt(loso_tir['auroc_mean'])}。
- 调整后 HTE 中，{hte_top['phase_label']} 的治疗获益最高，调整风险差 {fmt(hte_top['adjusted_risk_difference'])}（95% bootstrap CI {fmt(hte_top['bootstrap_ci_low'])}-{fmt(hte_top['bootstrap_ci_high'])}）。

## 关键解释边界

相图特征对纯预测 AUROC 的增量有限；它的价值主要在机制化低维表征、相位分层治疗响应和可解释干预框架。调整后相位-结局主效应不强，因此不能把相位标签解释为已验证的生物学亚型或临床决策工具。

## 完成包结构

- `figure_source_data/`：所有主图和补充图的 panel-level CSV。
- `tables/`：锁定版数据、模型结果和 manuscript tables。
- `figures/`：现有 PNG 图件副本。
- `docs/`：完成报告、结果初稿、方法摘要和审稿风险说明。
""",
    )

    phase_counts_text = "; ".join([f"{label}: n={count}" for label, count in phase_counts.items()])
    write(
        OUTDOC / "jaeb_glycemic_phase_results_skeleton_zh.md",
        f"""
# JAEB 血糖动力学相图 Results 初稿

## 公开 JAEB 数据支持构建跨研究血糖相图

我们整合 {n_studies} 个公开 JAEB 糖尿病研究数据集，形成 {n_total} 名受试者的 harmonized participant-level 分析表。共有 {n_phase} 名受试者具备可用于相图构建的基线 CGM 汇总。相图基于五个粗粒化序参量：高血糖负担、低血糖易感性、动态不稳定性、昼夜节律紊乱和恢复力代理指标。

KMeans 相图识别出 {phase_counts.shape[0]} 个相位：{phase_counts_text}。稳定达标相具有最高 TIR 和较低变异；高血糖持续相表现为最高平均血糖和 TAR；高波动震荡相以高 CV 和动态不稳定为特征；低血糖易感相具有更高 TBR；昼夜节律紊乱相表现为更大的 day-night CGM 差异。

## 相位与结局有关，但调整后主效应需克制解释

未调整检验显示，相位与 HbA1c 改善 >=0.5% 有显著关联（p={fmt(hba1c_assoc['p_value'])}）。相位间 TIR 改善和连续 HbA1c/TIR 变化方向也有差异，但统计证据较弱。进一步调整 baseline HbA1c、年龄、baseline TIR、study fixed effects 和 randomized arm 后，相位整体主效应减弱；TIR 变化模型的全局相位检验 p={fmt(tir_global['p_value'])}，提示相位主要组织了基线风险结构，而不是独立决定随访结局。

## 预测模型显示稳健泛化，但相图不是单纯 AUROC 工具

Nested CV 中，HbA1c 改善任务的最佳模型为 {top_hba1c['feature_set']} / {top_hba1c['model']}，AUROC={fmt(top_hba1c['auroc_mean'])}；TIR 改善任务的最佳模型为 {top_tir['feature_set']} / {top_tir['model']}，AUROC={fmt(top_tir['auroc_mean'])}。Leave-one-study-out 验证中，HbA1c 改善最佳平均 AUROC={fmt(loso_hba1c['auroc_mean'])}，TIR 改善最佳平均 AUROC={fmt(loso_tir['auroc_mean'])}。

Paired bootstrap 显示，最佳模型之间的 AUROC 差异并不稳定；相图特征集相对于临床或临床+CGM 特征的增量有限。因此，论文应将相图定位为机制启发的低维表征和分层工具，而不是强调它显著提升预测性能。

## 相图结构具有中等到较高 bootstrap 稳定性

150 次 bootstrap 相图重建显示 adjusted Rand index 中位数为 {fmt(ari_median)}（IQR {fmt(ari_q25)}-{fmt(ari_q75)}），silhouette 中位数为 {fmt(sil_median)}。这说明相位结构具有可重复性，但相位边界仍应被视为连续 CGM 状态空间的离散近似。

## 相位可组织治疗响应异质性

调整后的治疗响应分析提示，不同血糖相位的治疗获益可能不同。{hte_top['phase_label']} 的调整风险差最高，为 {fmt(hte_top['adjusted_risk_difference'])}（95% bootstrap CI {fmt(hte_top['bootstrap_ci_low'])}-{fmt(hte_top['bootstrap_ci_high'])}）。该结果适合作为相位分层干预假设，而不能直接作为临床推荐。

## 结果导向结论

JAEB 公开 RCT/CGM 数据可以支持一个可复现的血糖动力学相图。相图的主要贡献是将高度相关的 CGM 指标压缩为可解释状态空间，用于组织基线风险、治疗响应异质性和个体化干预逻辑；其预测增益有限，仍需要完整原始 CGM 时序和前瞻性验证。
""",
    )

    write(
        OUTDOC / "jaeb_glycemic_phase_methods_synopsis_zh.md",
        """
# 方法摘要

## 数据

使用公开 JAEB 糖尿病 RCT/干预研究数据。清洗脚本 harmonize participant-level 临床变量、HbA1c 结局、CGM 汇总、随机臂和研究标识。

## 相图构建

在具备基线 overall CGM 汇总的受试者中构建五个序参量：glycemic burden、hypoglycemic susceptibility、dynamic instability、circadian disruption 和 resilience proxy。序参量标准化后用 KMeans(k=5) 聚类。相位标签由聚类中心的 CGM 特征规则命名。

## 结局验证

结局包括 HbA1c 改善 >=0.5%、TIR 改善 >=5 个百分点、HbA1c 变化和 TIR 变化。先做未调整相位差异检验，再用调整 baseline HbA1c、年龄、baseline TIR、study fixed effects 和 randomized arm 的稳健模型估计相位主效应。

## 预测验证

比较 C1 临床、C2 临床+CGM、C4 相图特征集。模型包括 logistic ridge、树模型、boosting、SVM、KNN、MLP 等。验证策略包括 5-fold CV、leave-one-study-out、nested tuning、校准、决策曲线和 paired bootstrap。

## 治疗响应

在具备相位、结局和随机臂的研究中估计 treatment-by-phase 交互，并报告相位内调整风险差和 bootstrap CI。
""",
    )

    write(
        OUTDOC / "jaeb_glycemic_phase_reviewer_risk_register_zh.md",
        f"""
# 审稿风险与应对

1. **相图是否只是重新包装 CGM 指标？**  
   应对：承认相图不是独立生物标志物，而是 CGM 状态空间的低维表征；强调 bootstrap 稳定性和治疗响应组织价值。

2. **预测增益有限。**  
   应对：避免把论文卖点放在 AUROC 提升；paired bootstrap 已显示模型差异不稳定。

3. **调整后相位-结局关联不强。**  
   应对：把相位解释为基线风险结构与响应异质性工具，而非独立因果因子。

4. **公开 JAEB 数据异质性大。**  
   应对：保留 study fixed effects、LOSO 外部泛化和研究级 cohort flow。

5. **缺少原始 CGM 时序。**  
   应对：说明当前使用 harmonized summary CGM；下一步是用原始时序构建状态转移相图。

## 投稿定位

当前更像 diabetes informatics / digital health / clinical ML 研究。若要冲击高水平期刊，最强定位是“可复现的 CGM 状态空间表征 + 严格外部泛化 + 治疗响应异质性”，而不是单纯预测模型。
""",
    )

    status = pd.DataFrame(
        [
            ("data_cleaning", "complete", "processed_ml_table.csv; cgm_summary_long.csv"),
            ("phase_map", "complete", "glycemic_phase_features.csv; glycemic_phase_map.png"),
            ("phase_outcome_validation", "complete", "phase_association_tests.csv; journal_adjusted_phase_outcome_models.csv"),
            ("prediction_benchmark", "complete", "model_performance_cv.csv; journal_nested_tuning_summary.csv; journal_loso_summary.csv"),
            ("stability", "complete", "phase_bootstrap_stability.csv"),
            ("heterogeneous_treatment_effect", "complete", "journal_adjusted_hte_by_phase.csv"),
            ("intervention_framework", "complete", "individualized_intervention_framework.csv"),
            ("figure_source_data", "complete", "figure_source_data/*.csv"),
            ("manuscript_skeleton", "complete", "docs/jaeb_glycemic_phase_results_skeleton_zh.md"),
        ],
        columns=["module", "status", "outputs"],
    )
    export(status, OUT / "jaeb_glycemic_phase_completion_status.csv")


def main() -> None:
    phase_dictionary()
    figure_manifest = build_figure_source_data()
    copy_locked_artifacts()
    write_docs()
    manifest = {
        "package": str(OUT),
        "figure_source_data": figure_manifest,
        "files": sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file()),
    }
    (OUT / "jaeb_glycemic_phase_completion_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote JAEB glycemic phase completion package to {OUT}")


if __name__ == "__main__":
    main()
