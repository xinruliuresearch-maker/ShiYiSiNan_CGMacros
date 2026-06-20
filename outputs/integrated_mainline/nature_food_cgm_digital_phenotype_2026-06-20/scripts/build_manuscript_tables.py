"""Create manuscript-ready tables and figure/table index."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from run_journal_grade_experiments import make_ml_phase, markdown_table


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
DOCS_DIR = ROOT / "docs"


NUMERIC_VARS = [
    ("x_age_years", "Age, years"),
    ("x_diabetes_duration_years", "Diabetes duration, years"),
    ("x_baseline_hba1c_pct", "Baseline HbA1c, %"),
    ("x_baseline_bmi", "Baseline BMI, kg/m2"),
    ("x_baseline_cgm_mean_glucose_mg_dl", "Baseline CGM mean glucose, mg/dL"),
    ("x_baseline_cgm_time_in_range_70_180_pct", "Baseline TIR 70-180 mg/dL, %"),
    ("x_baseline_cgm_time_below_70_pct", "Baseline TBR <70 mg/dL, %"),
    ("x_baseline_cgm_time_above_180_pct", "Baseline TAR >180 mg/dL, %"),
    ("x_baseline_cgm_cv_pct", "Baseline CGM coefficient of variation, %"),
]

CATEGORICAL_VARS = [
    ("x_sex", "Sex"),
    ("x_race", "Race"),
    ("x_ethnicity", "Ethnicity"),
    ("x_insulin_delivery_method", "Insulin delivery method"),
    ("x_current_cgm_use", "Current CGM use"),
]

OUTCOME_VARS = [
    ("y_hba1c_improved_ge_0_5", "HbA1c improvement >=0.5%"),
    ("y_hba1c_change_pct_points", "HbA1c change, percentage points"),
    ("y_tir_improved_ge_5pct", "TIR improvement >=5 percentage points"),
    ("y_change_cgm_time_in_range_70_180_pct", "TIR change, percentage points"),
]


def ensure_dirs() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)


def fmt_mean_sd(x: pd.Series) -> str:
    val = pd.to_numeric(x, errors="coerce").dropna()
    if val.empty:
        return ""
    return f"{val.mean():.2f} ({val.std(ddof=1):.2f})"


def fmt_count_pct(x: pd.Series, level: object) -> str:
    denom = x.notna().sum()
    if denom == 0:
        return ""
    n = int((x == level).sum())
    return f"{n} ({100 * n / denom:.1f}%)"


def table1_by_phase(ml_phase: pd.DataFrame) -> pd.DataFrame:
    dat = ml_phase[ml_phase["phase_label"].notna()].copy()
    phases = dat["phase_label"].value_counts().index.tolist()
    rows = []
    n_row = {"section": "Cohort", "variable": "N", "level": ""}
    for phase in phases:
        n_row[phase] = int((dat["phase_label"] == phase).sum())
    rows.append(n_row)
    for col, label in NUMERIC_VARS:
        row = {"section": "Baseline numeric", "variable": label, "level": "mean (SD)"}
        for phase in phases:
            row[phase] = fmt_mean_sd(dat.loc[dat["phase_label"].eq(phase), col])
        rows.append(row)
    for col, label in CATEGORICAL_VARS:
        levels = dat[col].dropna().astype(str).value_counts().head(6).index.tolist()
        for level in levels:
            row = {"section": "Baseline categorical", "variable": label, "level": level}
            for phase in phases:
                row[phase] = fmt_count_pct(dat.loc[dat["phase_label"].eq(phase), col].astype(str), level)
            rows.append(row)
    return pd.DataFrame(rows)


def cohort_flow_table(ml_phase: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for study, g in ml_phase.groupby("study_id"):
        rows.append(
            {
                "study_id": study,
                "participants": len(g),
                "has_baseline_hba1c": int(g["x_baseline_hba1c_pct"].notna().sum()),
                "has_followup_hba1c": int(g["y_followup_hba1c_pct"].notna().sum()),
                "has_hba1c_improvement_target": int(g["y_hba1c_improved_ge_0_5"].notna().sum()),
                "has_baseline_cgm_summary": int(g["x_baseline_cgm_time_in_range_70_180_pct"].notna().sum()),
                "has_phase_label": int(g["phase_label"].notna().sum()),
                "has_tir_improvement_target": int(g["y_tir_improved_ge_5pct"].notna().sum()),
                "randomized_arm_count": int(g["x_randomized_arm"].nunique(dropna=True)),
            }
        )
    total = {
        "study_id": "TOTAL",
        "participants": len(ml_phase),
        "has_baseline_hba1c": int(ml_phase["x_baseline_hba1c_pct"].notna().sum()),
        "has_followup_hba1c": int(ml_phase["y_followup_hba1c_pct"].notna().sum()),
        "has_hba1c_improvement_target": int(ml_phase["y_hba1c_improved_ge_0_5"].notna().sum()),
        "has_baseline_cgm_summary": int(ml_phase["x_baseline_cgm_time_in_range_70_180_pct"].notna().sum()),
        "has_phase_label": int(ml_phase["phase_label"].notna().sum()),
        "has_tir_improvement_target": int(ml_phase["y_tir_improved_ge_5pct"].notna().sum()),
        "randomized_arm_count": int(ml_phase["x_randomized_arm"].nunique(dropna=True)),
    }
    rows.append(total)
    return pd.DataFrame(rows)


def missingness_table(ml_phase: pd.DataFrame) -> pd.DataFrame:
    cols = [col for col, _ in NUMERIC_VARS] + [col for col, _ in CATEGORICAL_VARS] + [col for col, _ in OUTCOME_VARS]
    rows = []
    for col in cols:
        rows.append(
            {
                "variable": col,
                "role": "outcome" if col.startswith("y_") else "baseline_feature",
                "n": len(ml_phase),
                "missing_n": int(ml_phase[col].isna().sum()),
                "missing_pct": float(100 * ml_phase[col].isna().mean()),
                "available_n": int(ml_phase[col].notna().sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(["role", "missing_pct"], ascending=[True, False])


def outcome_by_phase_table(ml_phase: pd.DataFrame) -> pd.DataFrame:
    dat = ml_phase[ml_phase["phase_label"].notna()].copy()
    phases = dat["phase_label"].value_counts().index.tolist()
    rows = []
    for col, label in OUTCOME_VARS:
        row = {"outcome": label, "summary": "mean (SD) or event rate"}
        for phase in phases:
            x = dat.loc[dat["phase_label"].eq(phase), col]
            if col.endswith("_ge_0_5") or col.endswith("_ge_5pct"):
                denom = x.notna().sum()
                if denom:
                    row[phase] = f"{int(x.sum())}/{denom} ({100 * x.mean():.1f}%)"
                else:
                    row[phase] = ""
            else:
                row[phase] = fmt_mean_sd(x)
        rows.append(row)
    return pd.DataFrame(rows)


def write_index_doc(table1: pd.DataFrame, flow: pd.DataFrame, missing: pd.DataFrame, outcome: pd.DataFrame) -> None:
    report = f"""# 论文图表与补充材料索引

生成脚本：`scripts/build_manuscript_tables.py`

## 主文建议图表

Table 1. Baseline characteristics by glycemic phase  
文件：`results/table1_baseline_by_phase.csv`

Table 2. Internal and external predictive model performance  
文件：`results/model_performance_cv.csv`，`results/journal_loso_summary.csv`

Table 3. Adjusted heterogeneous treatment response by phase  
文件：`results/journal_adjusted_hte_by_phase.csv`

Figure 1. Study workflow and phase-map construction  
建议用 `results/study_cohort_flow.csv` 和 `figures/glycemic_phase_map.png` 绘制组合图。

Figure 2. Glycemic phase map and baseline TIR distribution  
文件：`figures/glycemic_phase_map.png`，`figures/phase_tir_boxplot.png`

Figure 3. Model discrimination, calibration, and decision curves  
文件：`figures/model_benchmark_primary_auroc.png`，`figures/journal_calibration_curves.png`，`figures/journal_decision_curve.png`

Figure 4. Phase-stratified treatment response and individualized intervention framework  
文件：`figures/journal_adjusted_hte_by_phase.png`，`results/individualized_intervention_framework.csv`

## 补充材料建议

Supplementary Table 1. Dataset inventory and availability  
文件：`data/processed/dataset_inventory.csv`

Supplementary Table 2. Missingness by variable  
文件：`results/key_variable_missingness.csv`

Supplementary Table 3. Outcomes by phase  
文件：`results/outcomes_by_phase_manuscript.csv`

Supplementary Table 4. Paired bootstrap model comparisons  
文件：`results/journal_model_pairwise_bootstrap.csv`

Supplementary Figure 1. Leave-one-study-out AUROC heatmap  
文件：`figures/journal_loso_heatmap.png`

Supplementary Figure 2. Phase bootstrap stability  
文件：`figures/phase_bootstrap_stability.png`

Supplementary Figure 3. Permutation importance  
文件：`figures/journal_permutation_importance.png`

## Table 1 预览

{markdown_table(table1, max_rows=18)}

## Cohort Flow 预览

{markdown_table(flow, max_rows=20)}

## Missingness 预览

{markdown_table(missing, max_rows=20)}

## Outcomes by Phase 预览

{markdown_table(outcome, max_rows=10)}
"""
    (DOCS_DIR / "manuscript_tables_figures_index_zh.md").write_text(report, encoding="utf-8")


def main() -> int:
    ensure_dirs()
    ml_phase = make_ml_phase()
    table1 = table1_by_phase(ml_phase)
    flow = cohort_flow_table(ml_phase)
    missing = missingness_table(ml_phase)
    outcome = outcome_by_phase_table(ml_phase)
    table1.to_csv(RESULTS_DIR / "table1_baseline_by_phase.csv", index=False)
    flow.to_csv(RESULTS_DIR / "study_cohort_flow.csv", index=False)
    missing.to_csv(RESULTS_DIR / "key_variable_missingness.csv", index=False)
    outcome.to_csv(RESULTS_DIR / "outcomes_by_phase_manuscript.csv", index=False)
    write_index_doc(table1, flow, missing, outcome)
    print(
        json.dumps(
            {
                "table1_rows": int(len(table1)),
                "cohort_flow_rows": int(len(flow)),
                "missingness_rows": int(len(missing)),
                "outcome_by_phase_rows": int(len(outcome)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
