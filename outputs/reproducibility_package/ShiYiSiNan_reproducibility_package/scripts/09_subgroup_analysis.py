# -*- coding: utf-8 -*-
"""
09_subgroup_analysis.py

Enhancement 2: Exploratory subgroup analysis

Goals:
1. Use saved prediction records without retraining models.
2. Evaluate the M3 clinical-enhanced HGB main model across subgroups.
3. Evaluate 10-shot vs 0-shot personalization gains across subgroups.
4. Analyze signed prediction error to identify systematic overprediction or underprediction.

Inputs:
- outputs/tables/meal_level_dataset.csv
- outputs/tables/bootstrap_ci_prediction_records.csv

Outputs:
- outputs/tables/subgroup_subject_manifest.csv
- outputs/tables/subgroup_overview.csv
- outputs/tables/subgroup_performance_main_model.csv
- outputs/tables/subgroup_error_bias_main_model.csv
- outputs/tables/subgroup_fewshot_delta_10vs0.csv
- outputs/tables/subgroup_main_summary.csv

- outputs/figures/subgroup_mae_*.png
- outputs/figures/subgroup_signed_error_*.png
- outputs/figures/subgroup_fewshot_delta_*.png

Important:
Subgroup analysis is exploratory because participant numbers are small.
"""

from pathlib import Path
import re
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

warnings.filterwarnings("ignore")


# ============================================================
# 0. Paths and parameters
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

MEAL_PATH = TABLES / "meal_level_dataset.csv"
PRED_PATH = TABLES / "bootstrap_ci_prediction_records.csv"

MODEL = "hist_gradient_boosting"
MAIN_FEATURE_SET = "M3_clinical_enhanced"

TARGETS = ["iauc_2h", "peak_delta_2h"]

VALIDATIONS = [
    "leave_subject_out",
    "within_subject_temporal_split",
]

N_BOOTSTRAP = 1000
RANDOM_SEED = 42
MIN_SUBJECTS_FOR_CI = 5

TARGET_LABELS = {
    "iauc_2h": "2-h glucose iAUC",
    "peak_delta_2h": "2-h peak glucose excursion",
}

TARGET_UNITS = {
    "iauc_2h": "mg/dL*min",
    "peak_delta_2h": "mg/dL",
}

VALIDATION_LABELS = {
    "leave_subject_out": "Leave-subject-out",
    "within_subject_temporal_split": "Within-subject temporal",
    "few_shot_personalization": "Few-shot personalization",
}


# ============================================================
# 1. Metric functions
# ============================================================

def rmse(y_true, y_pred):
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def pearson_r(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[valid]
    y_pred = y_pred[valid]

    if len(y_true) < 2:
        return np.nan

    if np.nanstd(y_true) == 0 or np.nanstd(y_pred) == 0:
        return np.nan

    return float(np.corrcoef(y_true, y_pred)[0, 1])


def compute_metrics(df):
    y_true = pd.to_numeric(df["y_true"], errors="coerce").values
    y_pred = pd.to_numeric(df["y_pred"], errors="coerce").values

    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[valid]
    y_pred = y_pred[valid]

    if len(y_true) < 2:
        return {
            "MAE": np.nan,
            "RMSE": np.nan,
            "R2": np.nan,
            "Pearson_r": np.nan,
            "mean_signed_error": np.nan,
            "median_signed_error": np.nan,
            "underprediction_rate": np.nan,
            "n_meals": int(len(y_true)),
        }

    signed_error = y_pred - y_true

    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": rmse(y_true, y_pred),
        "R2": float(r2_score(y_true, y_pred)),
        "Pearson_r": pearson_r(y_true, y_pred),
        "mean_signed_error": float(np.nanmean(signed_error)),
        "median_signed_error": float(np.nanmedian(signed_error)),
        "underprediction_rate": float(np.mean(signed_error < 0)),
        "n_meals": int(len(y_true)),
    }


def compute_delta_metrics(pair_df):
    """
    Positive delta_MAE means the comparator prediction has lower error.

    Required columns:
    - y_true
    - y_pred_base
    - y_pred_comp
    """

    base_df = pd.DataFrame({
        "y_true": pair_df["y_true"],
        "y_pred": pair_df["y_pred_base"],
    })

    comp_df = pd.DataFrame({
        "y_true": pair_df["y_true"],
        "y_pred": pair_df["y_pred_comp"],
    })

    base = compute_metrics(base_df)
    comp = compute_metrics(comp_df)

    out = {}

    for metric in ["MAE", "RMSE", "R2", "Pearson_r", "mean_signed_error"]:
        out[f"{metric}_base"] = base[metric]
        out[f"{metric}_comp"] = comp[metric]

    out["delta_MAE"] = base["MAE"] - comp["MAE"]
    out["delta_RMSE"] = base["RMSE"] - comp["RMSE"]
    out["delta_R2"] = comp["R2"] - base["R2"]
    out["delta_Pearson_r"] = comp["Pearson_r"] - base["Pearson_r"]
    out["delta_mean_signed_error"] = comp["mean_signed_error"] - base["mean_signed_error"]

    out["delta_MAE_percent"] = (
        out["delta_MAE"] / base["MAE"] * 100
        if np.isfinite(base["MAE"]) and base["MAE"] != 0
        else np.nan
    )

    return out


# ============================================================
# 2. Bootstrap functions
# ============================================================

def subject_bootstrap_metrics(df, n_bootstrap=N_BOOTSTRAP, seed=RANDOM_SEED):
    rng = np.random.default_rng(seed)

    subject_ids = np.array(sorted(df["subject_id"].dropna().unique()))
    n_subjects = len(subject_ids)

    point = compute_metrics(df)

    summary = {}
    for k, v in point.items():
        summary[k] = v

    summary["n_subjects"] = int(n_subjects)
    summary["n_meals"] = int(len(df))
    summary["n_bootstrap"] = int(n_bootstrap)

    if n_subjects < MIN_SUBJECTS_FOR_CI:
        for metric in [
            "MAE",
            "RMSE",
            "R2",
            "Pearson_r",
            "mean_signed_error",
            "median_signed_error",
            "underprediction_rate",
        ]:
            summary[f"{metric}_ci_lower"] = np.nan
            summary[f"{metric}_ci_upper"] = np.nan

        summary["reliability_flag"] = f"low_n_subjects(<{MIN_SUBJECTS_FOR_CI})"
        return summary

    grouped = {
        sid: df[df["subject_id"] == sid]
        for sid in subject_ids
    }

    boot_rows = []

    for _ in range(n_bootstrap):
        sampled_subjects = rng.choice(subject_ids, size=n_subjects, replace=True)
        sampled = pd.concat([grouped[sid] for sid in sampled_subjects], axis=0, ignore_index=True)
        boot_rows.append(compute_metrics(sampled))

    boot = pd.DataFrame(boot_rows)

    for metric in [
        "MAE",
        "RMSE",
        "R2",
        "Pearson_r",
        "mean_signed_error",
        "median_signed_error",
        "underprediction_rate",
    ]:
        values = boot[metric].astype(float).replace([np.inf, -np.inf], np.nan).dropna()

        if len(values) == 0:
            summary[f"{metric}_ci_lower"] = np.nan
            summary[f"{metric}_ci_upper"] = np.nan
        else:
            summary[f"{metric}_ci_lower"] = float(np.percentile(values, 2.5))
            summary[f"{metric}_ci_upper"] = float(np.percentile(values, 97.5))

    summary["reliability_flag"] = "ok"

    return summary


def subject_bootstrap_delta(pair_df, n_bootstrap=N_BOOTSTRAP, seed=RANDOM_SEED):
    rng = np.random.default_rng(seed)

    subject_ids = np.array(sorted(pair_df["subject_id"].dropna().unique()))
    n_subjects = len(subject_ids)

    point = compute_delta_metrics(pair_df)

    summary = {}
    for k, v in point.items():
        summary[k] = v

    summary["n_subjects"] = int(n_subjects)
    summary["n_paired_meals"] = int(len(pair_df))
    summary["n_bootstrap"] = int(n_bootstrap)

    if n_subjects < MIN_SUBJECTS_FOR_CI:
        for metric in [
            "delta_MAE",
            "delta_RMSE",
            "delta_R2",
            "delta_Pearson_r",
            "delta_MAE_percent",
            "delta_mean_signed_error",
        ]:
            summary[f"{metric}_ci_lower"] = np.nan
            summary[f"{metric}_ci_upper"] = np.nan

        summary["reliability_flag"] = f"low_n_subjects(<{MIN_SUBJECTS_FOR_CI})"
        return summary

    grouped = {
        sid: pair_df[pair_df["subject_id"] == sid]
        for sid in subject_ids
    }

    boot_rows = []

    for _ in range(n_bootstrap):
        sampled_subjects = rng.choice(subject_ids, size=n_subjects, replace=True)
        sampled = pd.concat([grouped[sid] for sid in sampled_subjects], axis=0, ignore_index=True)
        boot_rows.append(compute_delta_metrics(sampled))

    boot = pd.DataFrame(boot_rows)

    for metric in [
        "delta_MAE",
        "delta_RMSE",
        "delta_R2",
        "delta_Pearson_r",
        "delta_MAE_percent",
        "delta_mean_signed_error",
    ]:
        values = boot[metric].astype(float).replace([np.inf, -np.inf], np.nan).dropna()

        if len(values) == 0:
            summary[f"{metric}_ci_lower"] = np.nan
            summary[f"{metric}_ci_upper"] = np.nan
        else:
            summary[f"{metric}_ci_lower"] = float(np.percentile(values, 2.5))
            summary[f"{metric}_ci_upper"] = float(np.percentile(values, 97.5))

    summary["reliability_flag"] = "ok"

    return summary


# ============================================================
# 3. Subject manifest and subgroup definitions
# ============================================================

def first_valid(series):
    s = series.dropna()
    if len(s) == 0:
        return np.nan
    return s.iloc[0]


def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def find_col(df, candidates):
    lower_map = {c.lower(): c for c in df.columns}

    for cand in candidates:
        if cand in df.columns:
            return cand

        if cand.lower() in lower_map:
            return lower_map[cand.lower()]

    return None


def make_hba1c_category(x):
    if pd.isna(x):
        return np.nan

    x = float(x)

    if x < 5.7:
        return "<5.7"
    elif x < 6.5:
        return "5.7-6.4"
    else:
        return ">=6.5"


def make_fasting_glucose_category(x):
    if pd.isna(x):
        return np.nan

    x = float(x)

    if x < 100:
        return "<100"
    elif x < 126:
        return "100-125"
    else:
        return ">=126"


def make_bmi_category(x):
    if pd.isna(x):
        return np.nan

    x = float(x)

    if x < 25:
        return "<25"
    elif x < 30:
        return "25-29.9"
    else:
        return ">=30"


def clean_category_value(x):
    if pd.isna(x):
        return np.nan

    s = str(x).strip()

    if s == "" or s.lower() in ["nan", "none", "missing", "null"]:
        return np.nan

    return s


def add_empty_object_column(df, col):
    df[col] = pd.Series(pd.NA, index=df.index, dtype="object")
    return df


def add_binary_median_group(df, source_col, out_col, label):
    """
    Add a binary median split subgroup.

    Example:
    - HbA1c < median (5.9)
    - HbA1c >= median (5.9)

    Important:
    The output column must be object dtype, otherwise newer pandas versions
    may reject assigning string labels into a float column.
    """

    if source_col not in df.columns:
        return df

    df[source_col] = pd.to_numeric(df[source_col], errors="coerce")
    med = np.nanmedian(df[source_col])

    df = add_empty_object_column(df, out_col)

    if not np.isfinite(med):
        return df

    mask = df[source_col].notna()

    df.loc[mask & (df[source_col] < med), out_col] = (
        f"{label} < median ({med:.1f})"
    )
    df.loc[mask & (df[source_col] >= med), out_col] = (
        f"{label} >= median ({med:.1f})"
    )

    return df


def build_subject_manifest(meal_df):
    df = meal_df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df["meal_time"] = pd.to_datetime(df["meal_time"], errors="coerce")

    rows = []

    candidate_cols = [
        "Age",
        "BMI",
        "Body weight",
        "Height",
        "A1c PDL (Lab)",
        "Fasting GLU - PDL (Lab)",
        "Insulin",
        "Triglycerides",
        "Cholesterol",
        "HDL",
        "LDL (Cal)",
        "VLDL (Cal)",
        "Cho/HDL Ratio",
        "Gender",
        "Sex",
        "Self-identify",
        "Self identify",
        "self_identify",
        "diabetes_status",
        "Diabetes status",
        "Health Status",
        "status",
    ]

    for sid, sub in df.groupby("subject_id"):
        sub = sub.sort_values("meal_time")

        row = {
            "subject_id": int(sid),
            "n_meals": int(len(sub)),
        }

        for col in candidate_cols:
            if col in sub.columns:
                row[col] = first_valid(sub[col])

        if "baseline_glucose" in sub.columns:
            row["subject_median_premeal_glucose"] = np.nanmedian(
                safe_numeric(sub["baseline_glucose"])
            )

        rows.append(row)

    manifest = pd.DataFrame(rows)

    # Sex / gender subgroup
    gender_col = find_col(manifest, ["Gender", "Sex", "sex"])
    if gender_col is not None:
        manifest["subgroup_sex"] = manifest[gender_col].map(clean_category_value)

    # Glycemic status subgroup
    status_col = find_col(
        manifest,
        [
            "Self-identify",
            "Self identify",
            "self_identify",
            "diabetes_status",
            "Diabetes status",
            "Health Status",
            "status",
        ],
    )

    if status_col is not None:
        manifest["subgroup_glycemic_status"] = manifest[status_col].map(clean_category_value)

    # BMI subgroup
    if "BMI" in manifest.columns:
        manifest["BMI"] = pd.to_numeric(manifest["BMI"], errors="coerce")

        manifest = add_empty_object_column(manifest, "subgroup_bmi_30")

        mask = manifest["BMI"].notna()

        manifest.loc[
            mask & (manifest["BMI"] < 30),
            "subgroup_bmi_30"
        ] = "BMI <30"

        manifest.loc[
            mask & (manifest["BMI"] >= 30),
            "subgroup_bmi_30"
        ] = "BMI >=30"

        manifest["subgroup_bmi_category"] = manifest["BMI"].apply(make_bmi_category)

    # HbA1c subgroup
    if "A1c PDL (Lab)" in manifest.columns:
        manifest["A1c PDL (Lab)"] = pd.to_numeric(
            manifest["A1c PDL (Lab)"],
            errors="coerce",
        )
        manifest["subgroup_hba1c_category"] = manifest["A1c PDL (Lab)"].apply(
            make_hba1c_category
        )
        manifest = add_binary_median_group(
            manifest,
            source_col="A1c PDL (Lab)",
            out_col="subgroup_hba1c_median",
            label="HbA1c",
        )

    # Fasting glucose subgroup
    if "Fasting GLU - PDL (Lab)" in manifest.columns:
        manifest["Fasting GLU - PDL (Lab)"] = pd.to_numeric(
            manifest["Fasting GLU - PDL (Lab)"],
            errors="coerce",
        )
        manifest["subgroup_fasting_glucose_category"] = manifest[
            "Fasting GLU - PDL (Lab)"
        ].apply(make_fasting_glucose_category)

    # Age subgroup
    if "Age" in manifest.columns:
        manifest["Age"] = pd.to_numeric(manifest["Age"], errors="coerce")
        manifest = add_binary_median_group(
            manifest,
            source_col="Age",
            out_col="subgroup_age_median",
            label="Age",
        )

    # Subject median pre-meal glucose subgroup
    if "subject_median_premeal_glucose" in manifest.columns:
        manifest["subject_median_premeal_glucose"] = pd.to_numeric(
            manifest["subject_median_premeal_glucose"],
            errors="coerce",
        )
        manifest = add_binary_median_group(
            manifest,
            source_col="subject_median_premeal_glucose",
            out_col="subgroup_premeal_glucose_median",
            label="Subject pre-meal glucose",
        )

    manifest.to_csv(
        TABLES / "subgroup_subject_manifest.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return manifest


def get_subgroup_vars(manifest):
    candidates = [
        "subgroup_glycemic_status",
        "subgroup_hba1c_category",
        "subgroup_fasting_glucose_category",
        "subgroup_bmi_30",
        "subgroup_bmi_category",
        "subgroup_sex",
        "subgroup_age_median",
        "subgroup_hba1c_median",
        "subgroup_premeal_glucose_median",
    ]

    out = []

    for col in candidates:
        if col not in manifest.columns:
            continue

        s = manifest[col].dropna().astype(str)
        n_levels = s.nunique()

        if n_levels < 2 or n_levels > 6:
            continue

        counts = s.value_counts()

        # At least one level reaches the minimum subject count.
        if (counts >= MIN_SUBJECTS_FOR_CI).sum() >= 1:
            out.append(col)

    return out


def make_subgroup_overview(manifest, subgroup_vars):
    rows = []

    for var in subgroup_vars:
        counts = manifest[var].dropna().astype(str).value_counts()

        for level, count in counts.items():
            rows.append({
                "subgroup_variable": var,
                "subgroup_level": level,
                "n_subjects": int(count),
                "percent_subjects": float(count / len(manifest) * 100),
            })

    overview = pd.DataFrame(rows)
    overview.to_csv(
        TABLES / "subgroup_overview.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return overview


def load_prediction_records():
    pred = pd.read_csv(PRED_PATH)
    pred.columns = [str(c).strip() for c in pred.columns]

    pred["subject_id"] = pred["subject_id"].astype(int)
    pred["meal_time"] = pd.to_datetime(pred["meal_time"], errors="coerce")
    pred["meal_time_key"] = pred["meal_time"].dt.strftime("%Y-%m-%d %H:%M:%S")

    bad = pred["meal_time_key"].isna()
    if bad.any():
        pred.loc[bad, "meal_time_key"] = pred.loc[bad, "meal_time"].astype(str)

    pred["shots"] = pd.to_numeric(pred["shots"], errors="coerce")
    pred["y_true"] = pd.to_numeric(pred["y_true"], errors="coerce")
    pred["y_pred"] = pd.to_numeric(pred["y_pred"], errors="coerce")

    return pred


# ============================================================
# 4. Subgroup performance for the main model
# ============================================================

def run_subgroup_performance(pred, manifest, subgroup_vars):
    pred_main = pred[
        (pred["model"] == MODEL)
        & (pred["feature_set"] == MAIN_FEATURE_SET)
        & (pred["validation"].isin(VALIDATIONS))
    ].copy()

    pred_main = pred_main.merge(manifest, on="subject_id", how="left")

    rows = []

    for target in TARGETS:
        for validation in VALIDATIONS:
            data_tv = pred_main[
                (pred_main["target"] == target)
                & (pred_main["validation"] == validation)
            ].copy()

            for subgroup_var in subgroup_vars:
                if subgroup_var not in data_tv.columns:
                    continue

                for subgroup_level, sub in data_tv.groupby(subgroup_var, dropna=True):
                    if pd.isna(subgroup_level):
                        continue

                    summary = subject_bootstrap_metrics(sub)

                    summary.update({
                        "target": target,
                        "target_label": TARGET_LABELS.get(target, target),
                        "validation": validation,
                        "validation_label": VALIDATION_LABELS.get(validation, validation),
                        "model": MODEL,
                        "feature_set": MAIN_FEATURE_SET,
                        "subgroup_variable": subgroup_var,
                        "subgroup_level": str(subgroup_level),
                    })

                    rows.append(summary)

    out = pd.DataFrame(rows)

    if not out.empty:
        out = out.sort_values(
            ["target", "validation", "subgroup_variable", "subgroup_level"]
        ).reset_index(drop=True)

    out.to_csv(
        TABLES / "subgroup_performance_main_model.csv",
        index=False,
        encoding="utf-8-sig",
    )

    bias_cols = [
        "target",
        "target_label",
        "validation",
        "validation_label",
        "subgroup_variable",
        "subgroup_level",
        "mean_signed_error",
        "mean_signed_error_ci_lower",
        "mean_signed_error_ci_upper",
        "median_signed_error",
        "median_signed_error_ci_lower",
        "median_signed_error_ci_upper",
        "underprediction_rate",
        "underprediction_rate_ci_lower",
        "underprediction_rate_ci_upper",
        "n_subjects",
        "n_meals",
        "reliability_flag",
    ]

    bias = out[[c for c in bias_cols if c in out.columns]].copy()
    bias.to_csv(
        TABLES / "subgroup_error_bias_main_model.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return out, bias


# ============================================================
# 5. Few-shot 10-shot vs 0-shot subgroup delta
# ============================================================

def prepare_pairing(df, keys):
    temp = df[keys + ["y_true", "y_pred"]].dropna(
        subset=["y_true", "y_pred"]
    ).copy()

    out = (
        temp
        .groupby(keys, as_index=False, dropna=False)
        .agg(
            y_true=("y_true", "mean"),
            y_pred=("y_pred", "mean"),
        )
    )

    return out


def build_fewshot_10vs0_pair(pred):
    base = pred[
        (pred["model"] == MODEL)
        & (pred["feature_set"] == MAIN_FEATURE_SET)
        & (pred["validation"] == "few_shot_personalization")
        & (pred["shots"] == 0)
    ].copy()

    comp = pred[
        (pred["model"] == MODEL)
        & (pred["feature_set"] == MAIN_FEATURE_SET)
        & (pred["validation"] == "few_shot_personalization")
        & (pred["shots"] == 10)
    ].copy()

    keys = [
        "subject_id",
        "meal_time_key",
        "target",
        "model",
        "feature_set",
        "validation",
    ]

    base = prepare_pairing(base, keys)
    comp = prepare_pairing(comp, keys)

    pair = base.merge(
        comp,
        on=keys,
        how="inner",
        suffixes=("_base", "_comp"),
    )

    if pair.empty:
        return pair

    pair["y_true"] = (pair["y_true_base"] + pair["y_true_comp"]) / 2.0

    return pair


def run_subgroup_fewshot_delta(pred, manifest, subgroup_vars):
    pair = build_fewshot_10vs0_pair(pred)

    if pair.empty:
        out = pd.DataFrame()
        out.to_csv(
            TABLES / "subgroup_fewshot_delta_10vs0.csv",
            index=False,
            encoding="utf-8-sig",
        )
        return out

    pair = pair.merge(manifest, on="subject_id", how="left")

    rows = []

    for target in TARGETS:
        data_t = pair[pair["target"] == target].copy()

        for subgroup_var in subgroup_vars:
            if subgroup_var not in data_t.columns:
                continue

            for subgroup_level, sub in data_t.groupby(subgroup_var, dropna=True):
                if pd.isna(subgroup_level):
                    continue

                summary = subject_bootstrap_delta(sub)

                summary.update({
                    "target": target,
                    "target_label": TARGET_LABELS.get(target, target),
                    "comparison": "10-shot vs 0-shot",
                    "model": MODEL,
                    "feature_set": MAIN_FEATURE_SET,
                    "subgroup_variable": subgroup_var,
                    "subgroup_level": str(subgroup_level),
                })

                rows.append(summary)

    out = pd.DataFrame(rows)

    if not out.empty:
        out = out.sort_values(
            ["target", "subgroup_variable", "subgroup_level"]
        ).reset_index(drop=True)

    out.to_csv(
        TABLES / "subgroup_fewshot_delta_10vs0.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return out


# ============================================================
# 6. Main summary table
# ============================================================

def fmt_ci(row, metric, digits=1):
    point = row.get(metric, np.nan)
    lo = row.get(f"{metric}_ci_lower", np.nan)
    hi = row.get(f"{metric}_ci_upper", np.nan)

    if pd.isna(point) or pd.isna(lo) or pd.isna(hi):
        return ""

    return f"{point:.{digits}f} [{lo:.{digits}f}, {hi:.{digits}f}]"


def make_main_summary(perf, fewshot):
    rows = []

    selected_subgroups = [
        "subgroup_glycemic_status",
        "subgroup_hba1c_category",
        "subgroup_bmi_30",
        "subgroup_sex",
    ]

    if not perf.empty:
        p = perf[
            (perf["validation"] == "within_subject_temporal_split")
            & (perf["subgroup_variable"].isin(selected_subgroups))
        ].copy()

        for _, r in p.iterrows():
            rows.append({
                "analysis": "main_model_performance",
                "target": r["target_label"],
                "subgroup_variable": r["subgroup_variable"],
                "subgroup_level": r["subgroup_level"],
                "metric_1": "MAE [95% CI]",
                "value_1": fmt_ci(r, "MAE", 1),
                "metric_2": "Pearson r [95% CI]",
                "value_2": fmt_ci(r, "Pearson_r", 3),
                "metric_3": "Mean signed error [95% CI]",
                "value_3": fmt_ci(r, "mean_signed_error", 1),
                "n_subjects": r["n_subjects"],
                "n_meals": r["n_meals"],
                "reliability_flag": r["reliability_flag"],
            })

    if not fewshot.empty:
        f = fewshot[
            fewshot["subgroup_variable"].isin(selected_subgroups)
        ].copy()

        for _, r in f.iterrows():
            rows.append({
                "analysis": "fewshot_10vs0_delta",
                "target": r["target_label"],
                "subgroup_variable": r["subgroup_variable"],
                "subgroup_level": r["subgroup_level"],
                "metric_1": "Delta MAE improvement [95% CI]",
                "value_1": fmt_ci(r, "delta_MAE", 1),
                "metric_2": "Delta MAE % [95% CI]",
                "value_2": fmt_ci(r, "delta_MAE_percent", 1),
                "metric_3": "Delta Pearson r [95% CI]",
                "value_3": fmt_ci(r, "delta_Pearson_r", 3),
                "n_subjects": r["n_subjects"],
                "n_meals": r["n_paired_meals"],
                "reliability_flag": r["reliability_flag"],
            })

    out = pd.DataFrame(rows)
    out.to_csv(
        TABLES / "subgroup_main_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return out


# ============================================================
# 7. Figures
# ============================================================

def safe_filename(s):
    s = str(s)
    s = re.sub(r"[^A-Za-z0-9_]+", "_", s)
    return s.strip("_")


def plot_subgroup_mae(perf):
    main_vars = [
        "subgroup_glycemic_status",
        "subgroup_hba1c_category",
        "subgroup_bmi_30",
        "subgroup_sex",
    ]

    if perf.empty:
        return

    for target in TARGETS:
        for validation in ["within_subject_temporal_split"]:
            for var in main_vars:
                sub = perf[
                    (perf["target"] == target)
                    & (perf["validation"] == validation)
                    & (perf["subgroup_variable"] == var)
                ].copy()

                if sub.empty:
                    continue

                sub = sub.sort_values("subgroup_level")

                x = np.arange(len(sub))
                y = sub["MAE"].values

                if "MAE_ci_lower" in sub.columns and "MAE_ci_upper" in sub.columns:
                    yerr_lower = y - sub["MAE_ci_lower"].values
                    yerr_upper = sub["MAE_ci_upper"].values - y
                    yerr = np.vstack([yerr_lower, yerr_upper])
                else:
                    yerr = None

                fig, ax = plt.subplots(figsize=(7, 5))
                ax.errorbar(x, y, yerr=yerr, marker="o", capsize=4, linewidth=1.5)

                ax.set_xticks(x)
                ax.set_xticklabels(
                    sub["subgroup_level"].astype(str),
                    rotation=25,
                    ha="right",
                )
                ax.set_ylabel(f"MAE ({TARGET_UNITS[target]})")
                ax.set_title(
                    f"Subgroup performance: {TARGET_LABELS[target]}\n"
                    f"{VALIDATION_LABELS[validation]} | {var}"
                )

                fig.tight_layout()

                out = FIGURES / f"subgroup_mae_{target}_{validation}_{safe_filename(var)}.png"
                fig.savefig(out, dpi=300, bbox_inches="tight")
                plt.close(fig)


def plot_signed_error_bias(bias):
    main_vars = [
        "subgroup_glycemic_status",
        "subgroup_hba1c_category",
        "subgroup_bmi_30",
        "subgroup_sex",
    ]

    if bias.empty:
        return

    for target in TARGETS:
        for validation in ["within_subject_temporal_split"]:
            for var in main_vars:
                sub = bias[
                    (bias["target"] == target)
                    & (bias["validation"] == validation)
                    & (bias["subgroup_variable"] == var)
                ].copy()

                if sub.empty:
                    continue

                sub = sub.sort_values("subgroup_level")

                x = np.arange(len(sub))
                y = sub["mean_signed_error"].values

                if (
                    "mean_signed_error_ci_lower" in sub.columns
                    and "mean_signed_error_ci_upper" in sub.columns
                ):
                    yerr_lower = y - sub["mean_signed_error_ci_lower"].values
                    yerr_upper = sub["mean_signed_error_ci_upper"].values - y
                    yerr = np.vstack([yerr_lower, yerr_upper])
                else:
                    yerr = None

                fig, ax = plt.subplots(figsize=(7, 5))
                ax.axhline(0, linestyle="--", linewidth=1)
                ax.errorbar(x, y, yerr=yerr, marker="o", capsize=4, linewidth=1.5)

                ax.set_xticks(x)
                ax.set_xticklabels(
                    sub["subgroup_level"].astype(str),
                    rotation=25,
                    ha="right",
                )
                ax.set_ylabel(f"Mean signed error ({TARGET_UNITS[target]})")
                ax.set_title(
                    f"Subgroup prediction bias: {TARGET_LABELS[target]}\n"
                    f"{VALIDATION_LABELS[validation]} | {var}"
                )

                fig.tight_layout()

                out = FIGURES / f"subgroup_signed_error_{target}_{validation}_{safe_filename(var)}.png"
                fig.savefig(out, dpi=300, bbox_inches="tight")
                plt.close(fig)


def plot_fewshot_delta(fewshot):
    main_vars = [
        "subgroup_glycemic_status",
        "subgroup_hba1c_category",
        "subgroup_bmi_30",
        "subgroup_sex",
    ]

    if fewshot.empty:
        return

    for target in TARGETS:
        for var in main_vars:
            sub = fewshot[
                (fewshot["target"] == target)
                & (fewshot["subgroup_variable"] == var)
            ].copy()

            if sub.empty:
                continue

            sub = sub.sort_values("subgroup_level")

            x = np.arange(len(sub))
            y = sub["delta_MAE"].values

            if "delta_MAE_ci_lower" in sub.columns and "delta_MAE_ci_upper" in sub.columns:
                yerr_lower = y - sub["delta_MAE_ci_lower"].values
                yerr_upper = sub["delta_MAE_ci_upper"].values - y
                yerr = np.vstack([yerr_lower, yerr_upper])
            else:
                yerr = None

            fig, ax = plt.subplots(figsize=(7, 5))
            ax.axhline(0, linestyle="--", linewidth=1)
            ax.errorbar(x, y, yerr=yerr, marker="o", capsize=4, linewidth=1.5)

            ax.set_xticks(x)
            ax.set_xticklabels(
                sub["subgroup_level"].astype(str),
                rotation=25,
                ha="right",
            )
            ax.set_ylabel(f"Delta MAE improvement ({TARGET_UNITS[target]})")
            ax.set_title(
                f"Subgroup few-shot gain: 10-shot vs 0-shot\n"
                f"{TARGET_LABELS[target]} | {var}"
            )

            fig.tight_layout()

            out = FIGURES / f"subgroup_fewshot_delta_{target}_{safe_filename(var)}.png"
            fig.savefig(out, dpi=300, bbox_inches="tight")
            plt.close(fig)


# ============================================================
# 8. Main
# ============================================================

def main():
    if not MEAL_PATH.exists():
        raise FileNotFoundError(f"Cannot find {MEAL_PATH}")

    if not PRED_PATH.exists():
        raise FileNotFoundError(
            f"Cannot find {PRED_PATH}. Please run 06_bootstrap_ci.py first."
        )

    print("Loading data...")
    meal_df = pd.read_csv(MEAL_PATH)
    pred = load_prediction_records()

    print("meal_df:", meal_df.shape)
    print("prediction records:", pred.shape)

    print("\nBuilding subject manifest...")
    manifest = build_subject_manifest(meal_df)
    subgroup_vars = get_subgroup_vars(manifest)

    print("Detected subgroup variables:")
    for v in subgroup_vars:
        print(" -", v)

    overview = make_subgroup_overview(manifest, subgroup_vars)

    print("\nSubgroup overview:")
    print(overview)

    print("\nRunning subgroup performance analysis...")
    perf, bias = run_subgroup_performance(pred, manifest, subgroup_vars)

    print("\nRunning subgroup few-shot delta analysis...")
    fewshot = run_subgroup_fewshot_delta(pred, manifest, subgroup_vars)

    print("\nMaking main subgroup summary...")
    summary = make_main_summary(perf, fewshot)

    print("\nGenerating figures...")
    plot_subgroup_mae(perf)
    plot_signed_error_bias(bias)
    plot_fewshot_delta(fewshot)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 260)
    pd.set_option("display.max_rows", 300)

    print("\nSaved tables:")
    print(TABLES / "subgroup_subject_manifest.csv")
    print(TABLES / "subgroup_overview.csv")
    print(TABLES / "subgroup_performance_main_model.csv")
    print(TABLES / "subgroup_error_bias_main_model.csv")
    print(TABLES / "subgroup_fewshot_delta_10vs0.csv")
    print(TABLES / "subgroup_main_summary.csv")

    print("\nSubgroup main summary:")
    print(summary)

    print("\nFigures saved to:")
    print(FIGURES)

    print("\nDone.")


if __name__ == "__main__":
    main()