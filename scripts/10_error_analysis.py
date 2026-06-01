# -*- coding: utf-8 -*-
"""
10_error_analysis.py

Enhancement 3: Error analysis

Goals:
1. Analyze where the main model makes errors.
2. Identify high-error subjects and high-error meals.
3. Detect systematic underprediction of high-response meals.
4. Evaluate high-response meal detection ability.
5. Analyze which meal / physiology / clinical features are associated with error.
6. Analyze what 10-shot personalization improves compared with 0-shot prediction.

Inputs:
- outputs/tables/meal_level_dataset.csv
- outputs/tables/bootstrap_ci_prediction_records.csv

Outputs:
- outputs/tables/error_prediction_records_main_model.csv
- outputs/tables/error_overall_metrics.csv
- outputs/tables/error_subject_summary.csv
- outputs/tables/error_high_error_subjects.csv
- outputs/tables/error_extreme_meals.csv
- outputs/tables/error_high_response_underpredicted_meals.csv
- outputs/tables/error_low_response_overpredicted_meals.csv
- outputs/tables/error_true_response_bin_summary.csv
- outputs/tables/error_high_response_classification.csv
- outputs/tables/error_feature_correlations.csv
- outputs/tables/error_fewshot_10vs0_records.csv
- outputs/tables/error_fewshot_subject_gain.csv
- outputs/tables/error_fewshot_feature_correlations.csv
- outputs/tables/error_analysis_main_summary.csv

Figures:
- outputs/figures/error_pred_vs_obs_*.png
- outputs/figures/error_calibration_by_decile_*.png
- outputs/figures/error_signed_by_decile_*.png
- outputs/figures/error_subject_mae_distribution_*.png
- outputs/figures/error_fewshot_subject_gain_*.png

Important:
This is an exploratory error analysis. It should be used to understand model limitations,
not to make causal claims.
"""

from pathlib import Path
import re
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
)

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

PRIMARY_VALIDATION = "within_subject_temporal_split"

N_TOP_MEALS = 50
MIN_SUBJECT_MEALS = 3

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


# Features to merge from meal-level dataset for error interpretation.
INTERPRETATION_FEATURES = [
    "meal_type",
    "eff_calories",
    "eff_carbs",
    "eff_protein",
    "eff_fat",
    "eff_fiber",
    "baseline_glucose",
    "pre_glucose_mean_30",
    "pre_glucose_sd_30",
    "pre_glucose_slope_60",
    "hr_mean_pre30",
    "activity_calories_pre30",
    "mets_mean_pre30",
    "meal_hour",
    "meal_hour_sin",
    "meal_hour_cos",
    "prev_meal_gap_min",
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
    "Non HDL",
    "LDL (Cal)",
    "VLDL (Cal)",
    "Cho/HDL Ratio",
    "Gender",
    "Self-identify",
]


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


def compute_metrics_from_arrays(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

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
            "n": int(len(y_true)),
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
        "n": int(len(y_true)),
    }


def safe_spearman(x, y, min_n=20):
    x = pd.to_numeric(x, errors="coerce")
    y = pd.to_numeric(y, errors="coerce")

    valid = x.notna() & y.notna()

    if valid.sum() < min_n:
        return np.nan, int(valid.sum())

    r = x[valid].corr(y[valid], method="spearman")
    return float(r), int(valid.sum())


# ============================================================
# 2. Loading and preprocessing
# ============================================================

def make_meal_time_key(series):
    s = pd.to_datetime(series, errors="coerce")
    out = s.dt.strftime("%Y-%m-%d %H:%M:%S")
    bad = out.isna()
    if bad.any():
        out.loc[bad] = series.loc[bad].astype(str)
    return out


def load_meal_dataset():
    if not MEAL_PATH.exists():
        raise FileNotFoundError(f"Cannot find {MEAL_PATH}")

    meal = pd.read_csv(MEAL_PATH)
    meal.columns = [str(c).strip() for c in meal.columns]

    if "meal_time" not in meal.columns:
        raise RuntimeError("meal_level_dataset.csv must contain meal_time")

    meal["subject_id"] = meal["subject_id"].astype(int)
    meal["meal_time"] = pd.to_datetime(meal["meal_time"], errors="coerce")
    meal["meal_time_key"] = meal["meal_time"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Keep only useful columns.
    cols = ["subject_id", "meal_time_key"]
    for c in INTERPRETATION_FEATURES:
        if c in meal.columns and c not in cols:
            cols.append(c)

    # Also keep outcomes for reference if present.
    for c in ["iauc_2h", "peak_delta_2h", "time_to_peak_2h", "recovery_time_2h"]:
        if c in meal.columns and c not in cols:
            cols.append(c)

    meal_small = meal[cols].copy()

    # Avoid duplicate merge explosion.
    agg_dict = {}
    for c in meal_small.columns:
        if c in ["subject_id", "meal_time_key"]:
            continue
        if pd.api.types.is_numeric_dtype(meal_small[c]):
            agg_dict[c] = "mean"
        else:
            agg_dict[c] = "first"

    meal_small = (
        meal_small
        .groupby(["subject_id", "meal_time_key"], as_index=False, dropna=False)
        .agg(agg_dict)
    )

    return meal_small


def load_prediction_records():
    if not PRED_PATH.exists():
        raise FileNotFoundError(
            f"Cannot find {PRED_PATH}. Please run scripts/06_bootstrap_ci.py first."
        )

    pred = pd.read_csv(PRED_PATH)
    pred.columns = [str(c).strip() for c in pred.columns]

    required = [
        "subject_id",
        "meal_time",
        "target",
        "feature_set",
        "model",
        "validation",
        "shots",
        "y_true",
        "y_pred",
    ]

    missing = [c for c in required if c not in pred.columns]
    if missing:
        raise RuntimeError(f"Missing required columns in prediction records: {missing}")

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


def prepare_main_model_error_records(pred, meal_small):
    main = pred[
        (pred["model"] == MODEL)
        & (pred["feature_set"] == MAIN_FEATURE_SET)
        & (pred["validation"].isin(VALIDATIONS))
    ].copy()

    main = main.merge(
        meal_small,
        on=["subject_id", "meal_time_key"],
        how="left",
        suffixes=("", "_meal"),
    )

    main["signed_error"] = main["y_pred"] - main["y_true"]
    main["abs_error"] = np.abs(main["signed_error"])
    main["squared_error"] = main["signed_error"] ** 2
    main["relative_abs_error"] = main["abs_error"] / (np.abs(main["y_true"]) + 1e-8)

    main.to_csv(
        TABLES / "error_prediction_records_main_model.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return main


# ============================================================
# 3. Overall error metrics
# ============================================================

def make_overall_metrics(error_records):
    rows = []

    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = error_records[
                (error_records["target"] == target)
                & (error_records["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            m = compute_metrics_from_arrays(sub["y_true"], sub["y_pred"])

            rows.append({
                "target": target,
                "target_label": TARGET_LABELS.get(target, target),
                "validation": validation,
                "validation_label": VALIDATION_LABELS.get(validation, validation),
                "model": MODEL,
                "feature_set": MAIN_FEATURE_SET,
                **m,
                "n_subjects": int(sub["subject_id"].nunique()),
                "n_meals": int(len(sub)),
                "y_true_mean": float(np.nanmean(sub["y_true"])),
                "y_true_sd": float(np.nanstd(sub["y_true"], ddof=1)),
                "y_pred_mean": float(np.nanmean(sub["y_pred"])),
                "y_pred_sd": float(np.nanstd(sub["y_pred"], ddof=1)),
            })

    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "error_overall_metrics.csv", index=False, encoding="utf-8-sig")
    return out


# ============================================================
# 4. Subject-level error analysis
# ============================================================

def make_subject_summary(error_records):
    rows = []

    for target in TARGETS:
        for validation in VALIDATIONS:
            sub_tv = error_records[
                (error_records["target"] == target)
                & (error_records["validation"] == validation)
            ].copy()

            if sub_tv.empty:
                continue

            high_threshold = np.nanpercentile(sub_tv["y_true"], 75)

            for sid, sub in sub_tv.groupby("subject_id"):
                m = compute_metrics_from_arrays(sub["y_true"], sub["y_pred"])

                high = sub[sub["y_true"] >= high_threshold]
                if len(high) > 0:
                    high_under_rate = float(np.mean(high["signed_error"] < 0))
                    high_mae = float(np.nanmean(high["abs_error"]))
                else:
                    high_under_rate = np.nan
                    high_mae = np.nan

                rows.append({
                    "target": target,
                    "target_label": TARGET_LABELS.get(target, target),
                    "validation": validation,
                    "validation_label": VALIDATION_LABELS.get(validation, validation),
                    "subject_id": int(sid),
                    "n_meals": int(len(sub)),
                    "n_high_response_meals": int(len(high)),
                    "high_response_threshold": float(high_threshold),
                    "high_response_underprediction_rate": high_under_rate,
                    "high_response_MAE": high_mae,
                    **m,
                    "mean_y_true": float(np.nanmean(sub["y_true"])),
                    "mean_y_pred": float(np.nanmean(sub["y_pred"])),
                    "mean_abs_error": float(np.nanmean(sub["abs_error"])),
                    "median_abs_error": float(np.nanmedian(sub["abs_error"])),
                    "max_abs_error": float(np.nanmax(sub["abs_error"])),
                })

    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "error_subject_summary.csv", index=False, encoding="utf-8-sig")

    high_error = (
        out[out["n_meals"] >= MIN_SUBJECT_MEALS]
        .sort_values(["target", "validation", "MAE"], ascending=[True, True, False])
        .groupby(["target", "validation"], as_index=False)
        .head(10)
        .reset_index(drop=True)
    )

    high_error.to_csv(
        TABLES / "error_high_error_subjects.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return out, high_error


# ============================================================
# 5. Meal-level extreme error analysis
# ============================================================

def make_extreme_meal_tables(error_records):
    extreme_rows = []
    high_under_rows = []
    low_over_rows = []

    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = error_records[
                (error_records["target"] == target)
                & (error_records["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            q75 = np.nanpercentile(sub["y_true"], 75)
            q25 = np.nanpercentile(sub["y_true"], 25)

            base_cols = [
                "target",
                "validation",
                "subject_id",
                "meal_time",
                "meal_type",
                "y_true",
                "y_pred",
                "signed_error",
                "abs_error",
                "eff_calories",
                "eff_carbs",
                "eff_protein",
                "eff_fat",
                "eff_fiber",
                "baseline_glucose",
                "pre_glucose_mean_30",
                "pre_glucose_slope_60",
                "prev_meal_gap_min",
                "BMI",
                "A1c PDL (Lab)",
                "Fasting GLU - PDL (Lab)",
            ]
            cols = [c for c in base_cols if c in sub.columns]

            extreme = sub.sort_values("abs_error", ascending=False).head(N_TOP_MEALS)
            extreme_rows.append(extreme[cols])

            high_under = (
                sub[(sub["y_true"] >= q75) & (sub["signed_error"] < 0)]
                .sort_values("signed_error", ascending=True)
                .head(N_TOP_MEALS)
            )
            high_under_rows.append(high_under[cols])

            low_over = (
                sub[(sub["y_true"] <= q25) & (sub["signed_error"] > 0)]
                .sort_values("signed_error", ascending=False)
                .head(N_TOP_MEALS)
            )
            low_over_rows.append(low_over[cols])

    extreme_all = pd.concat(extreme_rows, axis=0, ignore_index=True) if extreme_rows else pd.DataFrame()
    high_under_all = pd.concat(high_under_rows, axis=0, ignore_index=True) if high_under_rows else pd.DataFrame()
    low_over_all = pd.concat(low_over_rows, axis=0, ignore_index=True) if low_over_rows else pd.DataFrame()

    extreme_all.to_csv(TABLES / "error_extreme_meals.csv", index=False, encoding="utf-8-sig")
    high_under_all.to_csv(TABLES / "error_high_response_underpredicted_meals.csv", index=False, encoding="utf-8-sig")
    low_over_all.to_csv(TABLES / "error_low_response_overpredicted_meals.csv", index=False, encoding="utf-8-sig")

    return extreme_all, high_under_all, low_over_all


# ============================================================
# 6. Response-bin calibration and error analysis
# ============================================================

def assign_quantile_bin(series, q=10):
    s = pd.to_numeric(series, errors="coerce")
    valid = s.notna()

    out = pd.Series(pd.NA, index=series.index, dtype="object")

    if valid.sum() < q:
        return out

    ranks = s[valid].rank(method="first")

    try:
        bins = pd.qcut(
            ranks,
            q=q,
            labels=False,
            duplicates="drop",
        ) + 1
        out.loc[valid] = bins.astype(int).astype(str)
    except Exception:
        return out

    return out


def make_true_response_bin_summary(error_records):
    rows = []

    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = error_records[
                (error_records["target"] == target)
                & (error_records["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            sub["true_response_decile"] = assign_quantile_bin(sub["y_true"], q=10)

            for decile, g in sub.groupby("true_response_decile", dropna=True):
                if pd.isna(decile):
                    continue

                m = compute_metrics_from_arrays(g["y_true"], g["y_pred"])

                rows.append({
                    "target": target,
                    "target_label": TARGET_LABELS.get(target, target),
                    "validation": validation,
                    "validation_label": VALIDATION_LABELS.get(validation, validation),
                    "true_response_decile": int(decile),
                    "n_meals": int(len(g)),
                    "n_subjects": int(g["subject_id"].nunique()),
                    "observed_mean": float(np.nanmean(g["y_true"])),
                    "predicted_mean": float(np.nanmean(g["y_pred"])),
                    "mean_signed_error": float(np.nanmean(g["signed_error"])),
                    "median_signed_error": float(np.nanmedian(g["signed_error"])),
                    "MAE": m["MAE"],
                    "RMSE": m["RMSE"],
                    "underprediction_rate": float(np.mean(g["signed_error"] < 0)),
                })

    out = pd.DataFrame(rows)
    out.to_csv(
        TABLES / "error_true_response_bin_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return out


# ============================================================
# 7. High-response classification analysis
# ============================================================

def make_high_response_classification(error_records):
    rows = []

    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = error_records[
                (error_records["target"] == target)
                & (error_records["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            threshold_true = np.nanpercentile(sub["y_true"], 75)
            threshold_pred = np.nanpercentile(sub["y_pred"], 75)

            y_high = (sub["y_true"] >= threshold_true).astype(int)
            pred_score = sub["y_pred"]
            pred_high = (sub["y_pred"] >= threshold_pred).astype(int)

            if y_high.nunique() < 2:
                roc_auc = np.nan
                avg_precision = np.nan
            else:
                roc_auc = float(roc_auc_score(y_high, pred_score))
                avg_precision = float(average_precision_score(y_high, pred_score))

            precision = float(precision_score(y_high, pred_high, zero_division=0))
            recall = float(recall_score(y_high, pred_high, zero_division=0))

            high = sub[y_high == 1]

            rows.append({
                "target": target,
                "target_label": TARGET_LABELS.get(target, target),
                "validation": validation,
                "validation_label": VALIDATION_LABELS.get(validation, validation),
                "high_response_definition": "observed top quartile",
                "observed_high_response_threshold": float(threshold_true),
                "predicted_top_quartile_threshold": float(threshold_pred),
                "n_meals": int(len(sub)),
                "n_subjects": int(sub["subject_id"].nunique()),
                "n_high_response_meals": int(y_high.sum()),
                "ROC_AUC_for_high_response": roc_auc,
                "average_precision": avg_precision,
                "precision_at_predicted_top_quartile": precision,
                "recall_at_predicted_top_quartile": recall,
                "high_response_underprediction_rate": float(np.mean(high["signed_error"] < 0)) if len(high) else np.nan,
                "high_response_MAE": float(np.nanmean(high["abs_error"])) if len(high) else np.nan,
                "high_response_mean_signed_error": float(np.nanmean(high["signed_error"])) if len(high) else np.nan,
            })

    out = pd.DataFrame(rows)
    out.to_csv(
        TABLES / "error_high_response_classification.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return out


# ============================================================
# 8. Feature-error correlations
# ============================================================

def make_feature_error_correlations(error_records):
    rows = []

    numeric_features = []
    for c in INTERPRETATION_FEATURES:
        if c in error_records.columns:
            if pd.api.types.is_numeric_dtype(error_records[c]) or c not in ["meal_type", "Gender", "Self-identify"]:
                numeric_features.append(c)

    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = error_records[
                (error_records["target"] == target)
                & (error_records["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            for feature in numeric_features:
                if feature not in sub.columns:
                    continue

                r_abs, n_abs = safe_spearman(sub[feature], sub["abs_error"], min_n=20)
                r_signed, n_signed = safe_spearman(sub[feature], sub["signed_error"], min_n=20)
                r_true, n_true = safe_spearman(sub[feature], sub["y_true"], min_n=20)

                rows.append({
                    "target": target,
                    "target_label": TARGET_LABELS.get(target, target),
                    "validation": validation,
                    "validation_label": VALIDATION_LABELS.get(validation, validation),
                    "feature": feature,
                    "n_abs_error": n_abs,
                    "spearman_feature_abs_error": r_abs,
                    "n_signed_error": n_signed,
                    "spearman_feature_signed_error": r_signed,
                    "n_true_response": n_true,
                    "spearman_feature_true_response": r_true,
                })

    out = pd.DataFrame(rows)

    if not out.empty:
        out = out.sort_values(
            ["target", "validation", "spearman_feature_abs_error"],
            ascending=[True, True, False],
        ).reset_index(drop=True)

    out.to_csv(
        TABLES / "error_feature_correlations.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return out


# ============================================================
# 9. Few-shot error improvement analysis
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


def build_fewshot_10vs0_records(pred, meal_small):
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
        suffixes=("_0shot", "_10shot"),
    )

    if pair.empty:
        return pair

    pair["y_true"] = (pair["y_true_0shot"] + pair["y_true_10shot"]) / 2.0

    pair["signed_error_0shot"] = pair["y_pred_0shot"] - pair["y_true"]
    pair["signed_error_10shot"] = pair["y_pred_10shot"] - pair["y_true"]

    pair["abs_error_0shot"] = np.abs(pair["signed_error_0shot"])
    pair["abs_error_10shot"] = np.abs(pair["signed_error_10shot"])

    pair["delta_abs_error"] = pair["abs_error_0shot"] - pair["abs_error_10shot"]
    pair["delta_signed_error"] = pair["signed_error_10shot"] - pair["signed_error_0shot"]
    pair["improved_by_10shot"] = pair["delta_abs_error"] > 0

    pair = pair.merge(
        meal_small,
        on=["subject_id", "meal_time_key"],
        how="left",
        suffixes=("", "_meal"),
    )

    pair.to_csv(
        TABLES / "error_fewshot_10vs0_records.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return pair


def make_fewshot_subject_gain(fewshot_records):
    if fewshot_records.empty:
        out = pd.DataFrame()
        out.to_csv(TABLES / "error_fewshot_subject_gain.csv", index=False, encoding="utf-8-sig")
        return out

    rows = []

    for target in TARGETS:
        sub_t = fewshot_records[fewshot_records["target"] == target].copy()

        if sub_t.empty:
            continue

        for sid, sub in sub_t.groupby("subject_id"):
            rows.append({
                "target": target,
                "target_label": TARGET_LABELS.get(target, target),
                "subject_id": int(sid),
                "n_paired_meals": int(len(sub)),
                "MAE_0shot": float(np.nanmean(sub["abs_error_0shot"])),
                "MAE_10shot": float(np.nanmean(sub["abs_error_10shot"])),
                "delta_MAE_improvement": float(np.nanmean(sub["delta_abs_error"])),
                "percent_meals_improved_by_10shot": float(np.mean(sub["improved_by_10shot"])),
                "mean_true_response": float(np.nanmean(sub["y_true"])),
                "mean_pred_0shot": float(np.nanmean(sub["y_pred_0shot"])),
                "mean_pred_10shot": float(np.nanmean(sub["y_pred_10shot"])),
            })

    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "error_fewshot_subject_gain.csv", index=False, encoding="utf-8-sig")

    return out


def make_fewshot_feature_correlations(fewshot_records):
    if fewshot_records.empty:
        out = pd.DataFrame()
        out.to_csv(TABLES / "error_fewshot_feature_correlations.csv", index=False, encoding="utf-8-sig")
        return out

    rows = []

    numeric_features = []
    for c in INTERPRETATION_FEATURES:
        if c in fewshot_records.columns:
            if pd.api.types.is_numeric_dtype(fewshot_records[c]) or c not in ["meal_type", "Gender", "Self-identify"]:
                numeric_features.append(c)

    for target in TARGETS:
        sub_t = fewshot_records[fewshot_records["target"] == target].copy()

        for feature in numeric_features:
            if feature not in sub_t.columns:
                continue

            r_gain, n_gain = safe_spearman(sub_t[feature], sub_t["delta_abs_error"], min_n=20)
            r_true, n_true = safe_spearman(sub_t[feature], sub_t["y_true"], min_n=20)

            rows.append({
                "target": target,
                "target_label": TARGET_LABELS.get(target, target),
                "feature": feature,
                "n_gain": n_gain,
                "spearman_feature_delta_abs_error": r_gain,
                "n_true_response": n_true,
                "spearman_feature_true_response": r_true,
            })

    out = pd.DataFrame(rows)

    if not out.empty:
        out = out.sort_values(
            ["target", "spearman_feature_delta_abs_error"],
            ascending=[True, False],
        ).reset_index(drop=True)

    out.to_csv(
        TABLES / "error_fewshot_feature_correlations.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return out


# ============================================================
# 10. Main summary table
# ============================================================

def make_main_summary(overall, subject_summary, classification, feature_corr, fewshot_subject_gain):
    rows = []

    for target in TARGETS:
        for validation in VALIDATIONS:
            o = overall[
                (overall["target"] == target)
                & (overall["validation"] == validation)
            ]

            if o.empty:
                continue

            o = o.iloc[0]

            rows.append({
                "section": "overall_error",
                "target": TARGET_LABELS.get(target, target),
                "validation": VALIDATION_LABELS.get(validation, validation),
                "finding": "Main-model average error and signed error",
                "value": (
                    f"MAE={o['MAE']:.1f}, RMSE={o['RMSE']:.1f}, "
                    f"r={o['Pearson_r']:.3f}, mean_signed_error={o['mean_signed_error']:.1f}, "
                    f"underprediction_rate={o['underprediction_rate']:.3f}"
                ),
            })

    # High-response detection summary.
    for _, row in classification.iterrows():
        rows.append({
            "section": "high_response_detection",
            "target": row["target_label"],
            "validation": row["validation_label"],
            "finding": "Ability to detect observed top-quartile high-response meals",
            "value": (
                f"ROC_AUC={row['ROC_AUC_for_high_response']:.3f}, "
                f"AP={row['average_precision']:.3f}, "
                f"precision_at_top_quartile={row['precision_at_predicted_top_quartile']:.3f}, "
                f"recall_at_top_quartile={row['recall_at_predicted_top_quartile']:.3f}, "
                f"high_response_underprediction_rate={row['high_response_underprediction_rate']:.3f}"
            ),
        })

    # Feature-error correlation top 3 for abs error.
    if not feature_corr.empty:
        for target in TARGETS:
            for validation in VALIDATIONS:
                sub = feature_corr[
                    (feature_corr["target"] == target)
                    & (feature_corr["validation"] == validation)
                ].copy()

                sub = sub.dropna(subset=["spearman_feature_abs_error"])
                sub = sub.reindex(
                    sub["spearman_feature_abs_error"].abs().sort_values(ascending=False).index
                ).head(5)

                if sub.empty:
                    continue

                top_text = "; ".join(
                    [
                        f"{r['feature']} rho_abs_error={r['spearman_feature_abs_error']:.3f}"
                        for _, r in sub.iterrows()
                    ]
                )

                rows.append({
                    "section": "feature_error_association",
                    "target": TARGET_LABELS.get(target, target),
                    "validation": VALIDATION_LABELS.get(validation, validation),
                    "finding": "Top feature associations with absolute error",
                    "value": top_text,
                })

    # Few-shot improvement summary.
    if not fewshot_subject_gain.empty:
        for target in TARGETS:
            sub = fewshot_subject_gain[fewshot_subject_gain["target"] == target].copy()

            if sub.empty:
                continue

            rows.append({
                "section": "fewshot_error_reduction",
                "target": TARGET_LABELS.get(target, target),
                "validation": "Few-shot personalization",
                "finding": "Subject-level 10-shot improvement",
                "value": (
                    f"mean_subject_delta_MAE={sub['delta_MAE_improvement'].mean():.1f}, "
                    f"median_subject_delta_MAE={sub['delta_MAE_improvement'].median():.1f}, "
                    f"median_percent_meals_improved={sub['percent_meals_improved_by_10shot'].median():.3f}"
                ),
            })

    out = pd.DataFrame(rows)
    out.to_csv(
        TABLES / "error_analysis_main_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return out


# ============================================================
# 11. Figures
# ============================================================

def safe_filename(s):
    s = str(s)
    s = re.sub(r"[^A-Za-z0-9_]+", "_", s)
    return s.strip("_")


def plot_pred_vs_observed(error_records):
    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = error_records[
                (error_records["target"] == target)
                & (error_records["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            fig, ax = plt.subplots(figsize=(6, 6))
            ax.scatter(sub["y_true"], sub["y_pred"], alpha=0.35, s=16)

            mn = np.nanmin([sub["y_true"].min(), sub["y_pred"].min()])
            mx = np.nanmax([sub["y_true"].max(), sub["y_pred"].max()])
            ax.plot([mn, mx], [mn, mx], linestyle="--", linewidth=1)

            ax.set_xlabel(f"Observed {TARGET_LABELS[target]} ({TARGET_UNITS[target]})")
            ax.set_ylabel(f"Predicted {TARGET_LABELS[target]} ({TARGET_UNITS[target]})")
            ax.set_title(
                f"Predicted vs observed\n{TARGET_LABELS[target]} | {VALIDATION_LABELS[validation]}"
            )

            fig.tight_layout()
            out = FIGURES / f"error_pred_vs_obs_{target}_{validation}.png"
            fig.savefig(out, dpi=300, bbox_inches="tight")
            plt.close(fig)


def plot_decile_calibration(bin_summary):
    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = bin_summary[
                (bin_summary["target"] == target)
                & (bin_summary["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            sub = sub.sort_values("true_response_decile")

            fig, ax = plt.subplots(figsize=(7, 5))
            ax.plot(
                sub["true_response_decile"],
                sub["observed_mean"],
                marker="o",
                label="Observed mean",
            )
            ax.plot(
                sub["true_response_decile"],
                sub["predicted_mean"],
                marker="o",
                label="Predicted mean",
            )

            ax.set_xlabel("Observed response decile")
            ax.set_ylabel(f"Mean response ({TARGET_UNITS[target]})")
            ax.set_title(
                f"Calibration by observed response decile\n{TARGET_LABELS[target]} | {VALIDATION_LABELS[validation]}"
            )
            ax.legend()

            fig.tight_layout()
            out = FIGURES / f"error_calibration_by_decile_{target}_{validation}.png"
            fig.savefig(out, dpi=300, bbox_inches="tight")
            plt.close(fig)


def plot_signed_error_by_decile(bin_summary):
    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = bin_summary[
                (bin_summary["target"] == target)
                & (bin_summary["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            sub = sub.sort_values("true_response_decile")

            fig, ax = plt.subplots(figsize=(7, 5))
            ax.axhline(0, linestyle="--", linewidth=1)
            ax.bar(
                sub["true_response_decile"],
                sub["mean_signed_error"],
            )

            ax.set_xlabel("Observed response decile")
            ax.set_ylabel(f"Mean signed error ({TARGET_UNITS[target]})")
            ax.set_title(
                f"Signed error by observed response decile\n{TARGET_LABELS[target]} | {VALIDATION_LABELS[validation]}"
            )

            fig.tight_layout()
            out = FIGURES / f"error_signed_by_decile_{target}_{validation}.png"
            fig.savefig(out, dpi=300, bbox_inches="tight")
            plt.close(fig)


def plot_subject_mae_distribution(subject_summary):
    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = subject_summary[
                (subject_summary["target"] == target)
                & (subject_summary["validation"] == validation)
                & (subject_summary["n_meals"] >= MIN_SUBJECT_MEALS)
            ].copy()

            if sub.empty:
                continue

            fig, ax = plt.subplots(figsize=(7, 5))
            ax.hist(sub["MAE"].dropna(), bins=15)
            ax.set_xlabel(f"Subject-level MAE ({TARGET_UNITS[target]})")
            ax.set_ylabel("Number of subjects")
            ax.set_title(
                f"Distribution of subject-level MAE\n{TARGET_LABELS[target]} | {VALIDATION_LABELS[validation]}"
            )

            fig.tight_layout()
            out = FIGURES / f"error_subject_mae_distribution_{target}_{validation}.png"
            fig.savefig(out, dpi=300, bbox_inches="tight")
            plt.close(fig)


def plot_fewshot_subject_gain(fewshot_subject_gain):
    if fewshot_subject_gain.empty:
        return

    for target in TARGETS:
        sub = fewshot_subject_gain[fewshot_subject_gain["target"] == target].copy()

        if sub.empty:
            continue

        sub = sub.sort_values("delta_MAE_improvement", ascending=False)

        fig, ax = plt.subplots(figsize=(9, 5))
        x = np.arange(len(sub))
        ax.axhline(0, linestyle="--", linewidth=1)
        ax.bar(x, sub["delta_MAE_improvement"])
        ax.set_xlabel("Subjects sorted by 10-shot MAE improvement")
        ax.set_ylabel(f"Delta MAE improvement ({TARGET_UNITS[target]})")
        ax.set_title(
            f"Subject-level few-shot error reduction\n{TARGET_LABELS[target]}"
        )

        fig.tight_layout()
        out = FIGURES / f"error_fewshot_subject_gain_{target}.png"
        fig.savefig(out, dpi=300, bbox_inches="tight")
        plt.close(fig)


# ============================================================
# 12. Main
# ============================================================

def main():
    print("Loading data...")
    meal_small = load_meal_dataset()
    pred = load_prediction_records()

    print("Meal feature table:", meal_small.shape)
    print("Prediction records:", pred.shape)

    print("\nPreparing main-model error records...")
    error_records = prepare_main_model_error_records(pred, meal_small)
    print("Main-model error records:", error_records.shape)

    print("\nComputing overall metrics...")
    overall = make_overall_metrics(error_records)

    print("\nComputing subject-level error summaries...")
    subject_summary, high_error_subjects = make_subject_summary(error_records)

    print("\nComputing extreme meal tables...")
    extreme_meals, high_under_meals, low_over_meals = make_extreme_meal_tables(error_records)

    print("\nComputing response-bin summaries...")
    bin_summary = make_true_response_bin_summary(error_records)

    print("\nComputing high-response classification metrics...")
    classification = make_high_response_classification(error_records)

    print("\nComputing feature-error correlations...")
    feature_corr = make_feature_error_correlations(error_records)

    print("\nAnalyzing few-shot 10-shot vs 0-shot error reduction...")
    fewshot_records = build_fewshot_10vs0_records(pred, meal_small)
    fewshot_subject_gain = make_fewshot_subject_gain(fewshot_records)
    fewshot_feature_corr = make_fewshot_feature_correlations(fewshot_records)

    print("\nCreating main summary...")
    main_summary = make_main_summary(
        overall=overall,
        subject_summary=subject_summary,
        classification=classification,
        feature_corr=feature_corr,
        fewshot_subject_gain=fewshot_subject_gain,
    )

    print("\nGenerating figures...")
    plot_pred_vs_observed(error_records)
    plot_decile_calibration(bin_summary)
    plot_signed_error_by_decile(bin_summary)
    plot_subject_mae_distribution(subject_summary)
    plot_fewshot_subject_gain(fewshot_subject_gain)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 260)
    pd.set_option("display.max_rows", 300)

    print("\nSaved tables:")
    print(TABLES / "error_prediction_records_main_model.csv")
    print(TABLES / "error_overall_metrics.csv")
    print(TABLES / "error_subject_summary.csv")
    print(TABLES / "error_high_error_subjects.csv")
    print(TABLES / "error_extreme_meals.csv")
    print(TABLES / "error_high_response_underpredicted_meals.csv")
    print(TABLES / "error_low_response_overpredicted_meals.csv")
    print(TABLES / "error_true_response_bin_summary.csv")
    print(TABLES / "error_high_response_classification.csv")
    print(TABLES / "error_feature_correlations.csv")
    print(TABLES / "error_fewshot_10vs0_records.csv")
    print(TABLES / "error_fewshot_subject_gain.csv")
    print(TABLES / "error_fewshot_feature_correlations.csv")
    print(TABLES / "error_analysis_main_summary.csv")

    print("\nMain summary:")
    print(main_summary)

    print("\nHigh-response classification:")
    print(classification)

    print("\nTop feature-error correlations:")
    if not feature_corr.empty:
        print(feature_corr.head(40))
    else:
        print("No feature-error correlations.")

    print("\nTop high-error subjects:")
    if not high_error_subjects.empty:
        print(high_error_subjects.head(40))
    else:
        print("No high-error subjects.")

    print("\nFew-shot subject gain preview:")
    if not fewshot_subject_gain.empty:
        print(fewshot_subject_gain.head(40))
    else:
        print("No few-shot gain records.")

    print("\nFigures saved to:")
    print(FIGURES)

    print("\nDone.")


if __name__ == "__main__":
    main()