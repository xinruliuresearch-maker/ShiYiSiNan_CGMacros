"""Build a master completion report and artifact manifest for the study."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"
DOCS_DIR = ROOT / "docs"


def markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "_No rows._"
    show = df.head(max_rows).copy()
    for col in show.columns:
        if pd.api.types.is_float_dtype(show[col]):
            show[col] = show[col].map(lambda x: "" if pd.isna(x) else f"{x:.3f}")
    headers = list(show.columns)
    rows = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in show.iterrows():
        rows.append("| " + " | ".join(str(row[col]) for col in headers) + " |")
    return "\n".join(rows)


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def artifact_row(path: Path, kind: str, description: str) -> dict:
    exists = path.exists()
    rows, cols = np.nan, np.nan
    if exists and path.suffix.lower() == ".csv":
        try:
            df = pd.read_csv(path)
            rows, cols = df.shape
        except Exception:
            pass
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "kind": kind,
        "exists": exists,
        "bytes": path.stat().st_size if exists else 0,
        "rows": rows,
        "columns": cols,
        "description": description,
    }


def build_manifest() -> pd.DataFrame:
    artifacts = [
        (DATA_DIR / "processed_ml_table.csv", "processed_data", "participant-level baseline features and follow-up outcomes"),
        (DATA_DIR / "cgm_summary_long.csv", "processed_data", "harmonized long-format CGM summaries"),
        (DATA_DIR / "glycemic_phase_features.csv", "phase_data", "phase-map order parameters and CGM state variables"),
        (DATA_DIR / "glycemic_phase_labels.csv", "phase_data", "participant phase labels"),
        (RESULTS_DIR / "model_performance_cv.csv", "model_results", "5-fold cross-validation benchmark"),
        (RESULTS_DIR / "model_performance_loso.csv", "model_results", "leave-one-study-out external validation"),
        (RESULTS_DIR / "journal_oof_predictions.csv", "model_results", "out-of-fold predictions for selected models"),
        (RESULTS_DIR / "journal_calibration_metrics.csv", "model_results", "calibration metrics from out-of-fold predictions"),
        (RESULTS_DIR / "journal_decision_curve.csv", "clinical_utility", "decision curve analysis net-benefit estimates"),
        (RESULTS_DIR / "journal_permutation_importance.csv", "explainability", "cross-validated permutation importance"),
        (RESULTS_DIR / "phase_bootstrap_stability.csv", "robustness", "bootstrap phase-map stability"),
        (RESULTS_DIR / "journal_adjusted_hte_by_phase.csv", "hte", "regularized adjusted treatment response by phase"),
        (RESULTS_DIR / "journal_loso_summary.csv", "robustness", "aggregated LOSO model performance"),
        (RESULTS_DIR / "journal_incremental_phase_value.csv", "robustness", "incremental AUROC of phase-map feature set"),
        (RESULTS_DIR / "journal_model_pairwise_bootstrap.csv", "model_results", "paired bootstrap AUROC comparisons"),
        (RESULTS_DIR / "journal_adjusted_phase_outcome_models.csv", "association", "adjusted phase-outcome effect estimates"),
        (RESULTS_DIR / "journal_adjusted_phase_global_tests.csv", "association", "global robust Wald tests for phase terms"),
        (RESULTS_DIR / "journal_nested_tuning_experiments.csv", "model_results", "candidate models selected for nested tuning"),
        (RESULTS_DIR / "journal_nested_tuning_results.csv", "model_results", "outer-fold results from nested tuning"),
        (RESULTS_DIR / "journal_nested_tuning_summary.csv", "model_results", "nested cross-validation summary for tuned models"),
        (RESULTS_DIR / "table1_baseline_by_phase.csv", "manuscript_table", "baseline characteristics by glycemic phase"),
        (RESULTS_DIR / "study_cohort_flow.csv", "manuscript_table", "study-level cohort and outcome availability"),
        (RESULTS_DIR / "key_variable_missingness.csv", "manuscript_table", "missingness for key baseline and outcome variables"),
        (RESULTS_DIR / "outcomes_by_phase_manuscript.csv", "manuscript_table", "clinical outcomes summarized by glycemic phase"),
        (FIGURES_DIR / "glycemic_phase_map.png", "figure", "glycemic phase map"),
        (FIGURES_DIR / "phase_tir_boxplot.png", "figure", "baseline TIR by phase"),
        (FIGURES_DIR / "model_benchmark_primary_auroc.png", "figure", "primary model benchmark"),
        (FIGURES_DIR / "journal_calibration_curves.png", "figure", "calibration curves"),
        (FIGURES_DIR / "journal_decision_curve.png", "figure", "decision curve analysis"),
        (FIGURES_DIR / "journal_permutation_importance.png", "figure", "permutation importance"),
        (FIGURES_DIR / "phase_bootstrap_stability.png", "figure", "phase bootstrap stability"),
        (FIGURES_DIR / "journal_adjusted_hte_by_phase.png", "figure", "adjusted HTE by phase"),
        (FIGURES_DIR / "journal_loso_heatmap.png", "figure", "LOSO AUROC heatmap"),
        (FIGURES_DIR / "journal_adjusted_phase_outcomes.png", "figure", "adjusted phase-outcome associations"),
        (FIGURES_DIR / "journal_nested_tuning_auroc.png", "figure", "nested CV tuned model AUROC"),
        (DOCS_DIR / "cleaning_report.md", "documentation", "data cleaning report"),
        (DOCS_DIR / "glycemic_phase_research_report_zh.md", "documentation", "primary phase-map research report"),
        (DOCS_DIR / "journal_grade_experiment_report_zh.md", "documentation", "secondary journal-grade diagnostics report"),
        (DOCS_DIR / "adjusted_phase_outcome_models_zh.md", "documentation", "adjusted association model report"),
        (DOCS_DIR / "manuscript_tables_figures_index_zh.md", "documentation", "manuscript table and figure index"),
        (DOCS_DIR / "nested_tuning_experiment_report_zh.md", "documentation", "nested tuning experiment report"),
        (DOCS_DIR / "manuscript_draft_zh.md", "documentation", "Chinese manuscript draft skeleton with live results"),
    ]
    return pd.DataFrame([artifact_row(*item) for item in artifacts])


def build_sap() -> str:
    return """# 统计分析计划与投稿级实验蓝图

## 研究问题

本研究使用公开 JAEB 糖尿病 RCT/干预研究数据，构建血糖动力学相图，并评估相位表征在结局预测、治疗响应分层和个体化干预建议中的价值。

## 主要终点

主要预测终点：随访 HbA1c 较基线改善 >=0.5 个百分点。

关键次要终点：随访 CGM time-in-range 70-180 mg/dL 改善 >=5 个百分点。

连续次要终点：HbA1c 变化、TIR 变化、低血糖时间变化、体重/BMI 变化。

## 暴露与特征集

C1 临床基线特征：研究、治疗臂、年龄、性别、种族/族裔、糖尿病病程、基线 HbA1c、BMI 等。

C2 临床+CGM 特征：C1 加基线 CGM 均值、TIR、TBR、TAR、CV、佩戴时长。

C4 相图特征：C2 加血糖负担、低血糖易感、动态不稳定、昼夜节律紊乱、恢复力代理指标和相位标签。

所有预测模型只能使用基线变量；随访变量只用于结局定义。

## 模型比较

候选模型包括 logistic ridge、random forest、extra trees、hist gradient boosting、SVM、KNN、MLP、XGBoost、LightGBM、CatBoost 和 dummy baseline。

内部验证使用分层 5 折交叉验证；外部泛化使用 leave-one-study-out。模型选择以 AUROC 为主，同时报告 AUPRC、Brier、校准斜率、校准截距和 expected calibration error。

## 临床效用

对表现靠前模型进行 decision curve analysis，在 0.05-0.80 决策阈值范围内比较模型、treat-all 与 treat-none 的净获益。

## 可解释性

使用交叉验证框架内的 permutation importance，避免用训练集重要性夸大解释。重要性解释以方向无关的预测贡献为主，不作因果解释。

## 异质性治疗响应

优先在具备相位标签和明确对照/干预臂的 RCT 中估计相位分层治疗响应。主分析使用治疗臂、研究固定效应、基线 HbA1c、年龄、基线 TIR 与 treatment-by-phase 交互的 L2 正则化逻辑模型，报告调整风险差和 bootstrap CI。

## 稳健性分析

1. 相图 bootstrap 稳定性，报告 adjusted Rand index 和 silhouette。
2. Leave-one-study-out 外部验证热图。
3. C4 相图特征相对于 C1/C2 的增量 AUROC。
4. 名义最佳模型之间的 paired bootstrap AUROC 差异。
5. 相位-结局关联的协变量调整模型。

## 投稿叙事

若相图特征未显著提高 AUROC，应将相图定位为机制启发的低维表征、分层工具和解释框架，而不是单纯预测增强器。高水平期刊更看重可复现数据处理、严格外部验证、校准、临床效用、稳健性与克制解释。
"""


def build_report() -> str:
    phase_labels = read_csv(DATA_DIR / "glycemic_phase_labels.csv")
    cv = read_csv(RESULTS_DIR / "model_performance_cv.csv")
    loso = read_csv(RESULTS_DIR / "journal_loso_summary.csv")
    cal = read_csv(RESULTS_DIR / "journal_calibration_metrics.csv")
    stability = read_csv(RESULTS_DIR / "phase_bootstrap_stability.csv")
    hte = read_csv(RESULTS_DIR / "journal_adjusted_hte_by_phase.csv")
    adjusted_global = read_csv(RESULTS_DIR / "journal_adjusted_phase_global_tests.csv")
    pairwise = read_csv(RESULTS_DIR / "journal_model_pairwise_bootstrap.csv")
    nested = read_csv(RESULTS_DIR / "journal_nested_tuning_summary.csv")
    manifest = read_csv(RESULTS_DIR / "research_artifact_manifest.csv")

    phase_counts = phase_labels["phase_label"].value_counts().rename_axis("phase_label").reset_index(name="n")
    best_cv = (
        cv[cv["model"].ne("dummy_majority")]
        .dropna(subset=["auroc"])
        .sort_values(["target", "auroc"], ascending=[True, False])
        .groupby("target")
        .head(5)
    )
    best_loso = loso.sort_values(["target", "auroc_mean"], ascending=[True, False]).groupby("target").head(5)
    stability_summary = pd.DataFrame(
        [
            {
                "n_bootstrap": len(stability),
                "ari_median": stability["adjusted_rand_index"].median(),
                "ari_q25": stability["adjusted_rand_index"].quantile(0.25),
                "ari_q75": stability["adjusted_rand_index"].quantile(0.75),
                "silhouette_median": stability["silhouette"].median(),
            }
        ]
    )
    report = f"""# 高水平期刊目标研究完成总报告

生成脚本：`scripts/build_high_impact_research_report.py`

## 完成摘要

本研究包已从公开糖尿病 RCT/干预研究数据出发，完成数据清洗、血糖动力学相图、相位-结局验证、多模型预测比较、异质性治疗响应和可解释个体化干预框架。当前结果已经形成一套可复现的投稿前分析基础。

## 五个目标对应产物

1. 构建血糖动力学相图：`data/processed/glycemic_phase_features.csv`，`figures/glycemic_phase_map.png`
2. 验证相位与临床结局关系：`results/phase_association_tests.csv`，`results/journal_adjusted_phase_outcome_models.csv`
3. 比较不同机器学习方法：`results/model_performance_cv.csv`，`results/model_performance_loso.csv`
4. 识别异质性治疗响应：`results/hte_by_phase.csv`，`results/journal_adjusted_hte_by_phase.csv`
5. 形成可解释个体化干预框架：`results/individualized_intervention_framework.csv`，`results/journal_permutation_importance.csv`

## 相位分布

{markdown_table(phase_counts)}

## 内部交叉验证最佳模型

{markdown_table(best_cv[["target", "feature_set", "model", "n", "auroc", "auprc", "brier"]], max_rows=12)}

## Leave-One-Study-Out 外部泛化

{markdown_table(best_loso[["target", "feature_set", "model", "heldout_study_count", "auroc_mean", "auroc_sd", "auroc_min", "auroc_max", "brier_mean"]], max_rows=12)}

## 校准与临床效用

{markdown_table(cal[["target", "feature_set", "model", "auroc", "brier", "calibration_intercept", "calibration_slope", "expected_calibration_error"]], max_rows=8)}

校准图和决策曲线已输出到：

- `figures/journal_calibration_curves.png`
- `figures/journal_decision_curve.png`

## 相图稳健性

{markdown_table(stability_summary)}

## 异质性治疗响应

{markdown_table(hte[["phase_label", "n", "adjusted_risk_difference", "bootstrap_ci_low", "bootstrap_ci_high", "crude_risk_difference"]])}

## 调整后的相位-结局关联

{markdown_table(adjusted_global)}

## 模型差异检验

{markdown_table(pairwise)}

## Nested CV 微调模型

{markdown_table(nested)}

## 关键解释

- HbA1c 改善任务中，LightGBM、XGBoost、logistic ridge、CatBoost 的 AUROC 非常接近；paired bootstrap 显示名义最佳模型差异不稳定，论文应报告为“性能相近的一组模型”。
- TIR 改善任务中，临床+CGM 的 logistic ridge 仍最稳健，说明样本量较小时简单模型更容易泛化。
- 相图特征对 AUROC 的增量有限，但在可解释分层、治疗响应异质性和机制化可视化方面有明确价值。
- 调整后的相位-结局关联弱于未调整检验，提示相位捕获了部分基线风险结构；投稿叙事应克制，避免因果化。

## Artifact Manifest

完整 artifact 清单：`results/research_artifact_manifest.csv`

清单概览：

{markdown_table(manifest[["path", "kind", "exists", "rows", "columns", "description"]], max_rows=40)}
"""
    return report


def main() -> int:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    manifest.to_csv(RESULTS_DIR / "research_artifact_manifest.csv", index=False)
    (DOCS_DIR / "statistical_analysis_plan_zh.md").write_text(build_sap(), encoding="utf-8")
    report = build_report()
    (DOCS_DIR / "high_impact_study_completion_report_zh.md").write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "manifest_rows": int(len(manifest)),
                "existing_artifacts": int(manifest["exists"].sum()),
                "report": "docs/high_impact_study_completion_report_zh.md",
                "sap": "docs/statistical_analysis_plan_zh.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
