# -*- coding: utf-8 -*-
"""
07_make_paper_tables_figures.py

升级 4：生成清洗版论文主表与主图

输入：
- outputs/tables/meal_level_dataset.csv
- outputs/tables/bootstrap_ci_ablation_results.csv
- outputs/tables/bootstrap_ci_fewshot_results.csv
- outputs/tables/clean_feature_importance.csv
- outputs/tables/ablation_feature_manifest.csv

输出：
- outputs/paper_tables/table1_dataset_summary.csv
- outputs/paper_tables/table2_ablation_main.csv
- outputs/paper_tables/table3_fewshot_main.csv
- outputs/paper_tables/table4_feature_importance_main.csv
- outputs/paper_tables/supplementary_feature_manifest.csv

- outputs/paper_figures/figure1_study_design.png/.pdf
- outputs/paper_figures/figure2_response_heterogeneity.png/.pdf
- outputs/paper_figures/figure3_ablation_ci.png/.pdf
- outputs/paper_figures/figure4_fewshot_ci.png/.pdf
- outputs/paper_figures/figure5_feature_importance.png/.pdf
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


# ============================================================
# 0. 路径设置
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
PAPER_TABLES = ROOT / "outputs" / "paper_tables"
PAPER_FIGURES = ROOT / "outputs" / "paper_figures"

PAPER_TABLES.mkdir(parents=True, exist_ok=True)
PAPER_FIGURES.mkdir(parents=True, exist_ok=True)

MEAL_PATH = TABLES / "meal_level_dataset.csv"
ABLATION_CI_PATH = TABLES / "bootstrap_ci_ablation_results.csv"
FEWSHOT_CI_PATH = TABLES / "bootstrap_ci_fewshot_results.csv"
FEATURE_IMPORTANCE_PATH = TABLES / "clean_feature_importance.csv"
FEATURE_MANIFEST_PATH = TABLES / "ablation_feature_manifest.csv"


# ============================================================
# 1. 名称映射
# ============================================================

OUTCOME_LABELS = {
    "iauc_2h": "2-h glucose iAUC",
    "peak_delta_2h": "2-h peak glucose excursion",
}

OUTCOME_UNITS = {
    "iauc_2h": "mg/dL·min",
    "peak_delta_2h": "mg/dL",
}

VALIDATION_LABELS = {
    "leave_subject_out": "Leave-subject-out",
    "within_subject_temporal_split": "Within-subject temporal",
    "few_shot_personalization": "Few-shot personalization",
}

FEATURE_SET_LABELS = {
    "M0_meal_only": "M0 Meal only",
    "M1_meal_pre_cgm": "M1 + Pre-CGM",
    "M2_meal_pre_cgm_wearable_time": "M2 + Wearable/time",
    "M3_clinical_enhanced": "M3 + Clinical",
    "M4_gut_exploratory": "M4 + Gut",
}

FEATURE_SET_SHORT = {
    "M0_meal_only": "M0\nMeal",
    "M1_meal_pre_cgm": "M1\n+Pre-CGM",
    "M2_meal_pre_cgm_wearable_time": "M2\n+Wearable/time",
    "M3_clinical_enhanced": "M3\n+Clinical",
    "M4_gut_exploratory": "M4\n+Gut",
}

FEATURE_LABELS = {
    "eff_calories": "Effective calories",
    "eff_carbs": "Effective carbohydrates",
    "eff_protein": "Effective protein",
    "eff_fat": "Effective fat",
    "eff_fiber": "Effective fiber",
    "baseline_glucose": "Pre-meal glucose baseline",
    "pre_glucose_mean_30": "Pre-meal glucose mean",
    "pre_glucose_sd_30": "Pre-meal glucose variability",
    "pre_glucose_slope_60": "Pre-meal glucose trend",
    "hr_mean_pre30": "Pre-meal heart rate",
    "activity_calories_pre30": "Pre-meal activity calories",
    "mets_mean_pre30": "Pre-meal METs",
    "meal_hour_sin": "Meal timing, sine",
    "meal_hour_cos": "Meal timing, cosine",
    "prev_meal_gap_min": "Inter-meal interval",
    "Age": "Age",
    "BMI": "BMI",
    "Body weight": "Body weight",
    "Height": "Height",
    "A1c PDL (Lab)": "HbA1c",
    "Fasting GLU - PDL (Lab)": "Fasting glucose",
    "Insulin": "Insulin",
    "Triglycerides": "Triglycerides",
    "Cholesterol": "Total cholesterol",
    "HDL": "HDL cholesterol",
    "Non HDL": "Non-HDL cholesterol",
    "LDL (Cal)": "LDL cholesterol",
    "VLDL (Cal)": "VLDL cholesterol",
    "Cho/HDL Ratio": "Cholesterol/HDL ratio",
    "meal_type": "Meal type",
    "Gender": "Sex",
}


# ============================================================
# 2. 工具函数
# ============================================================

def assert_file(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")


def fmt_number(x, digits=1):
    if pd.isna(x):
        return ""
    return f"{x:.{digits}f}"


def fmt_ci(row, metric, digits=1):
    point = row[metric]
    low = row[f"{metric}_ci_lower"]
    high = row[f"{metric}_ci_upper"]
    return f"{point:.{digits}f} [{low:.{digits}f}, {high:.{digits}f}]"


def fmt_ci_r(row, metric="Pearson_r", digits=3):
    point = row[metric]
    low = row[f"{metric}_ci_lower"]
    high = row[f"{metric}_ci_upper"]
    return f"{point:.{digits}f} [{low:.{digits}f}, {high:.{digits}f}]"


def save_figure(fig, name):
    png_path = PAPER_FIGURES / f"{name}.png"
    pdf_path = PAPER_FIGURES / f"{name}.pdf"
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)


def q25(x):
    return np.nanpercentile(x, 25)


def q75(x):
    return np.nanpercentile(x, 75)


def median_iqr(series, digits=1):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) == 0:
        return ""
    med = np.nanmedian(s)
    lo = q25(s)
    hi = q75(s)
    return f"{med:.{digits}f} [{lo:.{digits}f}, {hi:.{digits}f}]"


def mean_sd(series, digits=1):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) == 0:
        return ""
    return f"{np.nanmean(s):.{digits}f} ± {np.nanstd(s, ddof=1):.{digits}f}"


# ============================================================
# 3. Table 1：数据集概况
# ============================================================

def make_table1_dataset_summary(meal_df):
    rows = []

    n_meals = len(meal_df)
    n_subjects = meal_df["subject_id"].nunique()
    meals_per_subject = meal_df.groupby("subject_id").size()

    rows.append({
        "section": "Dataset",
        "variable": "Number of participants",
        "value": str(n_subjects),
    })
    rows.append({
        "section": "Dataset",
        "variable": "Number of meals",
        "value": str(n_meals),
    })
    rows.append({
        "section": "Dataset",
        "variable": "Meals per participant, median [IQR]",
        "value": f"{np.median(meals_per_subject):.1f} [{q25(meals_per_subject):.1f}, {q75(meals_per_subject):.1f}]",
    })
    rows.append({
        "section": "Dataset",
        "variable": "Meals per participant, range",
        "value": f"{meals_per_subject.min()}–{meals_per_subject.max()}",
    })

    baseline_vars = [
        ("Age", "Age, years"),
        ("BMI", "BMI, kg/m²"),
        ("Body weight", "Body weight"),
        ("Height", "Height"),
        ("A1c PDL (Lab)", "HbA1c"),
        ("Fasting GLU - PDL (Lab)", "Fasting glucose"),
        ("Insulin", "Insulin"),
        ("Triglycerides", "Triglycerides"),
        ("Cholesterol", "Total cholesterol"),
        ("HDL", "HDL cholesterol"),
        ("LDL (Cal)", "LDL cholesterol"),
    ]

    # participant-level baseline：每人取第一行，避免按餐重复统计
    participant_df = meal_df.sort_values("meal_time").groupby("subject_id").head(1).copy()

    for col, label in baseline_vars:
        if col in participant_df.columns:
            rows.append({
                "section": "Participant baseline",
                "variable": label + ", median [IQR]",
                "value": median_iqr(participant_df[col], digits=1),
            })

    if "Gender" in participant_df.columns:
        gender_counts = participant_df["Gender"].astype(str).value_counts(dropna=False)
        for gender, count in gender_counts.items():
            rows.append({
                "section": "Participant baseline",
                "variable": f"Gender: {gender}",
                "value": f"{count} ({count / n_subjects * 100:.1f}%)",
            })

    meal_vars = [
        ("eff_calories", "Effective calories"),
        ("eff_carbs", "Effective carbohydrate, g"),
        ("eff_protein", "Effective protein, g"),
        ("eff_fat", "Effective fat, g"),
        ("eff_fiber", "Effective fiber, g"),
        ("baseline_glucose", "Pre-meal glucose baseline"),
        ("prev_meal_gap_min", "Previous meal interval, min"),
    ]

    for col, label in meal_vars:
        if col in meal_df.columns:
            rows.append({
                "section": "Meal-level features",
                "variable": label + ", median [IQR]",
                "value": median_iqr(meal_df[col], digits=1),
            })

    outcome_vars = [
        ("iauc_2h", "2-h glucose iAUC, mg/dL·min"),
        ("peak_delta_2h", "2-h peak glucose excursion, mg/dL"),
        ("time_to_peak_2h", "Time-to-peak, min"),
        ("recovery_time_2h", "Recovery time, min"),
    ]

    for col, label in outcome_vars:
        if col in meal_df.columns:
            rows.append({
                "section": "Postprandial outcomes",
                "variable": label + ", median [IQR]",
                "value": median_iqr(meal_df[col], digits=1),
            })

            rows.append({
                "section": "Postprandial outcomes",
                "variable": label + ", mean ± SD",
                "value": mean_sd(meal_df[col], digits=1),
            })

    table1 = pd.DataFrame(rows)
    table1.to_csv(PAPER_TABLES / "table1_dataset_summary.csv", index=False, encoding="utf-8-sig")
    return table1


# ============================================================
# 4. Table 2：Ablation 主表
# ============================================================

def make_table2_ablation_main(ablation_ci):
    df = ablation_ci.copy()

    df = df[df["model"] == "hist_gradient_boosting"].copy()
    df = df[df["validation"].isin(["leave_subject_out", "within_subject_temporal_split"])].copy()
    df = df.sort_values(["target", "validation", "feature_order"])

    rows = []

    for _, row in df.iterrows():
        target = row["target"]
        rows.append({
            "outcome": OUTCOME_LABELS.get(target, target),
            "unit": OUTCOME_UNITS.get(target, ""),
            "validation": VALIDATION_LABELS.get(row["validation"], row["validation"]),
            "feature_set": FEATURE_SET_LABELS.get(row["feature_set"], row["feature_set"]),
            "MAE [95% CI]": fmt_ci(row, "MAE", digits=1),
            "RMSE [95% CI]": fmt_ci(row, "RMSE", digits=1),
            "R² [95% CI]": fmt_ci_r(row, "R2", digits=3),
            "Pearson r [95% CI]": fmt_ci_r(row, "Pearson_r", digits=3),
            "n_subjects": int(row["n_subjects"]),
            "n_meals": int(row["n_meals"]),
        })

    table2 = pd.DataFrame(rows)
    table2.to_csv(PAPER_TABLES / "table2_ablation_main.csv", index=False, encoding="utf-8-sig")
    return table2


# ============================================================
# 5. Table 3：Few-shot 主表
# ============================================================

def make_table3_fewshot_main(fewshot_ci):
    df = fewshot_ci.copy()

    df = df[
        (df["model"] == "hist_gradient_boosting")
        & (df["feature_set"] == "M3_clinical_enhanced")
    ].copy()

    df = df.sort_values(["target", "shots"])

    rows = []

    for _, row in df.iterrows():
        target = row["target"]
        rows.append({
            "outcome": OUTCOME_LABELS.get(target, target),
            "unit": OUTCOME_UNITS.get(target, ""),
            "shots": int(row["shots"]),
            "feature_set": FEATURE_SET_LABELS.get(row["feature_set"], row["feature_set"]),
            "MAE [95% CI]": fmt_ci(row, "MAE", digits=1),
            "RMSE [95% CI]": fmt_ci(row, "RMSE", digits=1),
            "R² [95% CI]": fmt_ci_r(row, "R2", digits=3),
            "Pearson r [95% CI]": fmt_ci_r(row, "Pearson_r", digits=3),
            "n_subjects": int(row["n_subjects"]),
            "n_meals": int(row["n_meals"]),
        })

    table3 = pd.DataFrame(rows)
    table3.to_csv(PAPER_TABLES / "table3_fewshot_main.csv", index=False, encoding="utf-8-sig")
    return table3


# ============================================================
# 6. Table 4：特征重要性主表
# ============================================================

def make_table4_feature_importance(importance_df):
    df = importance_df.copy()

    df = df[
        (df["model"] == "hist_gradient_boosting")
        & (df["feature_set"] == "M3_clinical_enhanced")
    ].copy()

    rows = []

    for target in ["iauc_2h", "peak_delta_2h"]:
        sub = df[df["target"] == target].copy()
        sub = sub.sort_values("importance_mean", ascending=False).head(15)

        for rank, (_, row) in enumerate(sub.iterrows(), start=1):
            rows.append({
                "outcome": OUTCOME_LABELS.get(target, target),
                "rank": rank,
                "feature": row["feature"],
                "feature_label": FEATURE_LABELS.get(row["feature"], row["feature"]),
                "importance_mean": row["importance_mean"],
                "importance_std": row["importance_std"],
            })

    table4 = pd.DataFrame(rows)
    table4.to_csv(PAPER_TABLES / "table4_feature_importance_main.csv", index=False, encoding="utf-8-sig")
    return table4


# ============================================================
# 7. Figure 1：研究流程图
# ============================================================

def add_box(ax, xy, width, height, text, fontsize=10):
    x, y = xy
    box = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        linewidth=1.2,
        facecolor="white",
        edgecolor="black",
    )
    ax.add_patch(box)
    ax.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        wrap=True,
    )


def add_arrow(ax, start, end):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="->",
        mutation_scale=15,
        linewidth=1.2,
        color="black",
    )
    ax.add_patch(arrow)


def make_figure1_study_design():
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    boxes = [
        ((0.03, 0.58), 0.18, 0.23, "Public multimodal CGM cohort\nCGMacros\n40 participants, 1498 meals"),
        ((0.27, 0.58), 0.18, 0.23, "Meal-level phenotype construction\nPre-meal window\nPostprandial glucose outcomes"),
        ((0.51, 0.58), 0.18, 0.23, "Feature availability tiers\nMeal\nPre-CGM\nWearable/time\nClinical\nGut health"),
        ((0.75, 0.58), 0.18, 0.23, "Model evaluation\nLeave-subject-out\nWithin-subject temporal\nSubject-level bootstrap CI"),
        ((0.27, 0.18), 0.18, 0.23, "Postprandial outcomes\n2-h iAUC\nPeak glucose excursion\nTime-to-peak\nRecovery time"),
        ((0.51, 0.18), 0.18, 0.23, "Adaptive personalization\n0/1/3/5/10-shot calibration\nFuture-meal prediction"),
        ((0.75, 0.18), 0.18, 0.23, "Translation concept\nPersonal metabolic digital twin\nDiet-response decision support"),
    ]

    for xy, w, h, text in boxes:
        add_box(ax, xy, w, h, text)

    add_arrow(ax, (0.21, 0.70), (0.27, 0.70))
    add_arrow(ax, (0.45, 0.70), (0.51, 0.70))
    add_arrow(ax, (0.69, 0.70), (0.75, 0.70))
    add_arrow(ax, (0.36, 0.58), (0.36, 0.41))
    add_arrow(ax, (0.60, 0.58), (0.60, 0.41))
    add_arrow(ax, (0.69, 0.30), (0.75, 0.30))

    ax.text(
        0.5,
        0.94,
        "Study design: adaptive diet-to-physiology response modeling",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
    )

    save_figure(fig, "figure1_study_design")


# ============================================================
# 8. Figure 2：反应异质性
# ============================================================

def make_figure2_response_heterogeneity(meal_df):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    targets = ["iauc_2h", "peak_delta_2h"]

    for ax, target in zip(axes, targets):
        data = pd.to_numeric(meal_df[target], errors="coerce").dropna()

        ax.hist(data, bins=40)
        ax.set_title(OUTCOME_LABELS[target], fontsize=12)
        ax.set_xlabel(f"{OUTCOME_LABELS[target]} ({OUTCOME_UNITS[target]})")
        ax.set_ylabel("Number of meals")

        med = np.nanmedian(data)
        ax.axvline(med, linestyle="--", linewidth=1.2)
        ax.text(
            0.98,
            0.95,
            f"Median = {med:.1f}",
            ha="right",
            va="top",
            transform=ax.transAxes,
            fontsize=10,
        )

    fig.suptitle("Postprandial glucose response heterogeneity", fontsize=14, fontweight="bold")
    fig.tight_layout()
    save_figure(fig, "figure2_response_heterogeneity")


# ============================================================
# 9. Figure 3：Ablation with CI
# ============================================================

def make_figure3_ablation_ci(ablation_ci):
    df = ablation_ci.copy()
    df = df[
        (df["model"] == "hist_gradient_boosting")
        & (df["validation"].isin(["leave_subject_out", "within_subject_temporal_split"]))
    ].copy()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=False)

    for ax, target in zip(axes, ["iauc_2h", "peak_delta_2h"]):
        sub_target = df[df["target"] == target].copy()

        for validation in ["leave_subject_out", "within_subject_temporal_split"]:
            sub = sub_target[sub_target["validation"] == validation].copy()
            sub = sub.sort_values("feature_order")

            x = np.arange(len(sub))
            y = sub["MAE"].values
            yerr_lower = y - sub["MAE_ci_lower"].values
            yerr_upper = sub["MAE_ci_upper"].values - y
            yerr = np.vstack([yerr_lower, yerr_upper])

            label = VALIDATION_LABELS[validation]
            offset = -0.05 if validation == "leave_subject_out" else 0.05

            ax.errorbar(
                x + offset,
                y,
                yerr=yerr,
                marker="o",
                capsize=4,
                linewidth=1.5,
                label=label,
            )

        labels = [
            FEATURE_SET_SHORT.get(fs, fs)
            for fs in sub_target.sort_values("feature_order")["feature_set"].unique()
        ]

        ax.set_xticks(np.arange(len(labels)))
        ax.set_xticklabels(labels)
        ax.set_title(OUTCOME_LABELS[target])
        ax.set_ylabel(f"MAE ({OUTCOME_UNITS[target]})")
        ax.set_xlabel("Feature set")
        ax.legend()

    fig.suptitle("Feature-set ablation with subject-level bootstrap 95% CI", fontsize=14, fontweight="bold")
    fig.tight_layout()
    save_figure(fig, "figure3_ablation_ci")


# ============================================================
# 10. Figure 4：Few-shot with CI
# ============================================================

def make_figure4_fewshot_ci(fewshot_ci):
    df = fewshot_ci.copy()
    df = df[
        (df["model"] == "hist_gradient_boosting")
        & (df["feature_set"] == "M3_clinical_enhanced")
    ].copy()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, target in zip(axes, ["iauc_2h", "peak_delta_2h"]):
        sub = df[df["target"] == target].copy()
        sub = sub.sort_values("shots")

        x = sub["shots"].values.astype(float)
        y = sub["MAE"].values
        yerr_lower = y - sub["MAE_ci_lower"].values
        yerr_upper = sub["MAE_ci_upper"].values - y
        yerr = np.vstack([yerr_lower, yerr_upper])

        ax.errorbar(
            x,
            y,
            yerr=yerr,
            marker="o",
            capsize=4,
            linewidth=1.5,
        )

        ax.set_xticks(x)
        ax.set_title(OUTCOME_LABELS[target])
        ax.set_xlabel("Number of subject-specific meals for adaptation")
        ax.set_ylabel(f"MAE ({OUTCOME_UNITS[target]})")

        first = sub.iloc[0]
        last = sub.iloc[-1]
        reduction = (first["MAE"] - last["MAE"]) / first["MAE"] * 100

        ax.text(
            0.98,
            0.95,
            f"0→10-shot MAE reduction: {reduction:.1f}%",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=10,
        )

    fig.suptitle("Few-shot personalization with subject-level bootstrap 95% CI", fontsize=14, fontweight="bold")
    fig.tight_layout()
    save_figure(fig, "figure4_fewshot_ci")


# ============================================================
# 11. Figure 5：Feature importance
# ============================================================

def make_figure5_feature_importance(importance_df):
    df = importance_df.copy()

    df = df[
        (df["model"] == "hist_gradient_boosting")
        & (df["feature_set"] == "M3_clinical_enhanced")
    ].copy()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for ax, target in zip(axes, ["iauc_2h", "peak_delta_2h"]):
        sub = df[df["target"] == target].copy()
        sub = sub.sort_values("importance_mean", ascending=False).head(12)

        labels = [
            FEATURE_LABELS.get(f, f)
            for f in sub["feature"]
        ]

        y_pos = np.arange(len(sub))[::-1]

        ax.barh(y_pos, sub["importance_mean"].values[::-1])
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels[::-1])
        ax.set_xlabel("Permutation importance")
        ax.set_title(OUTCOME_LABELS[target])

    fig.suptitle("Top predictive features in the clinical-enhanced model", fontsize=14, fontweight="bold")
    fig.tight_layout()
    save_figure(fig, "figure5_feature_importance")


# ============================================================
# 12. Supplementary feature manifest
# ============================================================

def make_supplementary_feature_manifest(feature_manifest):
    df = feature_manifest.copy()

    if "feature_set" in df.columns:
        df["feature_set_label"] = df["feature_set"].map(FEATURE_SET_LABELS).fillna(df["feature_set"])

    if "feature" in df.columns:
        df["feature_label"] = df["feature"].map(FEATURE_LABELS).fillna(df["feature"])

    df.to_csv(PAPER_TABLES / "supplementary_feature_manifest.csv", index=False, encoding="utf-8-sig")
    return df


# ============================================================
# 13. 主流程
# ============================================================

def main():
    for path in [
        MEAL_PATH,
        ABLATION_CI_PATH,
        FEWSHOT_CI_PATH,
        FEATURE_IMPORTANCE_PATH,
        FEATURE_MANIFEST_PATH,
    ]:
        assert_file(path)

    meal_df = pd.read_csv(MEAL_PATH)
    meal_df.columns = [str(c).strip() for c in meal_df.columns]
    meal_df["meal_time"] = pd.to_datetime(meal_df["meal_time"], errors="coerce")

    ablation_ci = pd.read_csv(ABLATION_CI_PATH)
    fewshot_ci = pd.read_csv(FEWSHOT_CI_PATH)
    importance_df = pd.read_csv(FEATURE_IMPORTANCE_PATH)
    feature_manifest = pd.read_csv(FEATURE_MANIFEST_PATH)

    print("Loaded:")
    print("meal_df:", meal_df.shape)
    print("ablation_ci:", ablation_ci.shape)
    print("fewshot_ci:", fewshot_ci.shape)
    print("importance_df:", importance_df.shape)
    print("feature_manifest:", feature_manifest.shape)

    # Tables
    table1 = make_table1_dataset_summary(meal_df)
    table2 = make_table2_ablation_main(ablation_ci)
    table3 = make_table3_fewshot_main(fewshot_ci)
    table4 = make_table4_feature_importance(importance_df)
    supp = make_supplementary_feature_manifest(feature_manifest)

    print("\nSaved paper tables to:")
    print(PAPER_TABLES)

    print("\nTable 1 preview:")
    print(table1.head(30))

    print("\nTable 2 preview:")
    print(table2.head(20))

    print("\nTable 3 preview:")
    print(table3.head(20))

    print("\nTable 4 preview:")
    print(table4.head(30))

    # Figures
    make_figure1_study_design()
    make_figure2_response_heterogeneity(meal_df)
    make_figure3_ablation_ci(ablation_ci)
    make_figure4_fewshot_ci(fewshot_ci)
    make_figure5_feature_importance(importance_df)

    print("\nSaved paper figures to:")
    print(PAPER_FIGURES)

    print("\nDone.")


if __name__ == "__main__":
    main()