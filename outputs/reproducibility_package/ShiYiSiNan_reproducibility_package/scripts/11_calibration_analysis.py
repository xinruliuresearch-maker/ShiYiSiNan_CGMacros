# -*- coding: utf-8 -*-
"""
11_calibration_analysis.py

Enhancement 4: Calibration analysis

Goals:
1. Quantify prediction calibration for the M3 clinical-enhanced HGB model.
2. Diagnose response-range compression using calibration slope, intercept, and range ratios.
3. Evaluate calibration by predicted response deciles.
4. Evaluate high-response risk calibration across predicted deciles.
5. Perform cross-fitted linear recalibration as a sensitivity analysis.
6. Compare calibration before and after 10-shot personalization.

Inputs:
- outputs/tables/bootstrap_ci_prediction_records.csv

Outputs:
Tables:
- outputs/tables/calibration_main_summary.csv
- outputs/tables/calibration_predicted_decile_table.csv
- outputs/tables/calibration_observed_decile_table.csv
- outputs/tables/calibration_crossfit_recalibrated_records.csv
- outputs/tables/calibration_crossfit_recalibration_metrics.csv
- outputs/tables/calibration_fewshot_summary.csv
- outputs/tables/calibration_fewshot_predicted_decile_table.csv
- outputs/tables/calibration_analysis_main_summary.csv

Figures:
- outputs/figures/calibration_scatter_*.png
- outputs/figures/calibration_predicted_decile_curve_*.png
- outputs/figures/calibration_signed_error_by_predicted_decile_*.png
- outputs/figures/calibration_high_response_rate_*.png
- outputs/figures/calibration_recalibrated_curve_*.png

Interpretation:
This analysis is diagnostic. It should not be used to claim clinical effectiveness.
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

PRED_PATH = TABLES / "bootstrap_ci_prediction_records.csv"

MODEL = "hist_gradient_boosting"
MAIN_FEATURE_SET = "M3_clinical_enhanced"

TARGETS = ["iauc_2h", "peak_delta_2h"]

VALIDATIONS = [
    "leave_subject_out",
    "within_subject_temporal_split",
]

FEWSHOT_SHOTS_TO_ANALYZE = [0, 10]

N_BOOTSTRAP = 1000
RANDOM_SEED = 42
N_DECILES = 10
N_RECALIBRATION_FOLDS = 5

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
# 1. Basic metric functions
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


def fit_linear_calibrator(y_true, y_pred):
    """
    Fit observed = intercept + slope * predicted.

    Ideal calibration:
    intercept = 0
    slope = 1

    If slope > 1, predictions are usually too compressed.
    If slope < 1, predictions may be too extreme.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[valid]
    y_pred = y_pred[valid]

    if len(y_true) < 3 or np.nanstd(y_pred) == 0:
        return np.nan, np.nan

    X = np.column_stack([np.ones(len(y_pred)), y_pred])

    try:
        beta = np.linalg.lstsq(X, y_true, rcond=None)[0]
        intercept = float(beta[0])
        slope = float(beta[1])
        return intercept, slope
    except Exception:
        return np.nan, np.nan


def compute_basic_metrics(y_true, y_pred):
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


def assign_quantile_bin(series, q=N_DECILES):
    s = pd.to_numeric(series, errors="coerce")
    out = pd.Series(pd.NA, index=series.index, dtype="object")

    valid = s.notna()

    if valid.sum() < q:
        return out

    # rank(method='first') avoids duplicate-edge failures in qcut.
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


# ============================================================
# 2. Loading prediction records
# ============================================================

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
    pred["shots"] = pd.to_numeric(pred["shots"], errors="coerce")
    pred["y_true"] = pd.to_numeric(pred["y_true"], errors="coerce")
    pred["y_pred"] = pd.to_numeric(pred["y_pred"], errors="coerce")

    return pred


def get_main_model_records(pred):
    out = pred[
        (pred["model"] == MODEL)
        & (pred["feature_set"] == MAIN_FEATURE_SET)
        & (pred["validation"].isin(VALIDATIONS))
    ].copy()

    out["signed_error"] = out["y_pred"] - out["y_true"]
    out["abs_error"] = np.abs(out["signed_error"])

    return out


def get_fewshot_records(pred):
    out = pred[
        (pred["model"] == MODEL)
        & (pred["feature_set"] == MAIN_FEATURE_SET)
        & (pred["validation"] == "few_shot_personalization")
        & (pred["shots"].isin(FEWSHOT_SHOTS_TO_ANALYZE))
    ].copy()

    out["signed_error"] = out["y_pred"] - out["y_true"]
    out["abs_error"] = np.abs(out["signed_error"])

    return out


# ============================================================
# 3. Calibration metric functions
# ============================================================

def predicted_decile_table(df, y_pred_col="y_pred", n_deciles=N_DECILES):
    """
    Calibration by predicted response deciles.

    For a calibrated regression model, observed_mean should be close to predicted_mean
    within each predicted decile.
    """
    temp = df.copy()
    temp["predicted_decile"] = assign_quantile_bin(temp[y_pred_col], q=n_deciles)

    if temp["predicted_decile"].dropna().empty:
        return pd.DataFrame()

    high_threshold = np.nanpercentile(temp["y_true"], 75)

    rows = []

    for decile, g in temp.groupby("predicted_decile", dropna=True):
        if pd.isna(decile):
            continue

        y_true = pd.to_numeric(g["y_true"], errors="coerce")
        y_pred = pd.to_numeric(g[y_pred_col], errors="coerce")
        signed_error = y_pred - y_true

        rows.append({
            "predicted_decile": int(decile),
            "n_meals": int(len(g)),
            "n_subjects": int(g["subject_id"].nunique()),
            "observed_mean": float(np.nanmean(y_true)),
            "predicted_mean": float(np.nanmean(y_pred)),
            "observed_median": float(np.nanmedian(y_true)),
            "predicted_median": float(np.nanmedian(y_pred)),
            "calibration_error": float(np.nanmean(y_pred) - np.nanmean(y_true)),
            "abs_calibration_error": float(abs(np.nanmean(y_pred) - np.nanmean(y_true))),
            "mean_signed_error": float(np.nanmean(signed_error)),
            "underprediction_rate": float(np.mean(signed_error < 0)),
            "observed_high_response_rate": float(np.mean(y_true >= high_threshold)),
            "observed_q25": float(np.nanpercentile(y_true, 25)),
            "observed_q75": float(np.nanpercentile(y_true, 75)),
            "predicted_q25": float(np.nanpercentile(y_pred, 25)),
            "predicted_q75": float(np.nanpercentile(y_pred, 75)),
        })

    out = pd.DataFrame(rows)
    out = out.sort_values("predicted_decile").reset_index(drop=True)

    return out


def observed_decile_table(df, y_pred_col="y_pred", n_deciles=N_DECILES):
    """
    Error pattern by observed response deciles.

    This is useful for detecting regression-to-the-mean:
    low observed deciles may be overpredicted, high observed deciles underpredicted.
    """
    temp = df.copy()
    temp["observed_decile"] = assign_quantile_bin(temp["y_true"], q=n_deciles)

    if temp["observed_decile"].dropna().empty:
        return pd.DataFrame()

    rows = []

    for decile, g in temp.groupby("observed_decile", dropna=True):
        if pd.isna(decile):
            continue

        y_true = pd.to_numeric(g["y_true"], errors="coerce")
        y_pred = pd.to_numeric(g[y_pred_col], errors="coerce")
        signed_error = y_pred - y_true

        rows.append({
            "observed_decile": int(decile),
            "n_meals": int(len(g)),
            "n_subjects": int(g["subject_id"].nunique()),
            "observed_mean": float(np.nanmean(y_true)),
            "predicted_mean": float(np.nanmean(y_pred)),
            "observed_median": float(np.nanmedian(y_true)),
            "predicted_median": float(np.nanmedian(y_pred)),
            "mean_signed_error": float(np.nanmean(signed_error)),
            "median_signed_error": float(np.nanmedian(signed_error)),
            "underprediction_rate": float(np.mean(signed_error < 0)),
            "MAE": float(mean_absolute_error(y_true, y_pred)),
        })

    out = pd.DataFrame(rows)
    out = out.sort_values("observed_decile").reset_index(drop=True)

    return out


def compute_calibration_metrics(df, y_pred_col="y_pred"):
    """
    Compute calibration and error metrics for one target-validation group.
    """
    y_true = pd.to_numeric(df["y_true"], errors="coerce").values
    y_pred = pd.to_numeric(df[y_pred_col], errors="coerce").values

    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[valid]
    y_pred = y_pred[valid]

    basic = compute_basic_metrics(y_true, y_pred)

    if len(y_true) < 3:
        out = dict(basic)
        out.update({
            "calibration_intercept": np.nan,
            "calibration_slope": np.nan,
            "prediction_sd_ratio": np.nan,
            "prediction_range_ratio_p95_p5": np.nan,
            "weighted_abs_bin_error": np.nan,
            "weighted_rmse_bin_error": np.nan,
            "max_abs_bin_error": np.nan,
            "n_calibration_bins": 0,
        })
        return out

    intercept, slope = fit_linear_calibrator(y_true, y_pred)

    true_sd = np.nanstd(y_true, ddof=1)
    pred_sd = np.nanstd(y_pred, ddof=1)

    true_range = np.nanpercentile(y_true, 95) - np.nanpercentile(y_true, 5)
    pred_range = np.nanpercentile(y_pred, 95) - np.nanpercentile(y_pred, 5)

    prediction_sd_ratio = pred_sd / true_sd if true_sd > 0 else np.nan
    prediction_range_ratio = pred_range / true_range if true_range > 0 else np.nan

    temp = pd.DataFrame({
        "subject_id": df.loc[valid, "subject_id"].values if "subject_id" in df.columns else np.arange(len(y_true)),
        "y_true": y_true,
        y_pred_col: y_pred,
    })

    dec = predicted_decile_table(temp, y_pred_col=y_pred_col, n_deciles=N_DECILES)

    if dec.empty:
        weighted_abs_bin_error = np.nan
        weighted_rmse_bin_error = np.nan
        max_abs_bin_error = np.nan
        n_bins = 0
    else:
        weights = dec["n_meals"].values.astype(float)
        err = dec["calibration_error"].values.astype(float)
        weighted_abs_bin_error = float(np.sum(weights * np.abs(err)) / np.sum(weights))
        weighted_rmse_bin_error = float(np.sqrt(np.sum(weights * err ** 2) / np.sum(weights)))
        max_abs_bin_error = float(np.max(np.abs(err)))
        n_bins = int(len(dec))

    out = dict(basic)
    out.update({
        "calibration_intercept": intercept,
        "calibration_slope": slope,
        "prediction_sd_ratio": float(prediction_sd_ratio),
        "prediction_range_ratio_p95_p5": float(prediction_range_ratio),
        "weighted_abs_bin_error": weighted_abs_bin_error,
        "weighted_rmse_bin_error": weighted_rmse_bin_error,
        "max_abs_bin_error": max_abs_bin_error,
        "n_calibration_bins": n_bins,
    })

    return out


def subject_bootstrap_calibration(df, y_pred_col="y_pred", n_bootstrap=N_BOOTSTRAP, seed=RANDOM_SEED):
    rng = np.random.default_rng(seed)

    subject_ids = np.array(sorted(df["subject_id"].dropna().unique()))
    n_subjects = len(subject_ids)

    point = compute_calibration_metrics(df, y_pred_col=y_pred_col)

    summary = dict(point)
    summary["n_subjects"] = int(n_subjects)
    summary["n_meals"] = int(len(df))
    summary["n_bootstrap"] = int(n_bootstrap)

    metrics_for_ci = [
        "MAE",
        "RMSE",
        "R2",
        "Pearson_r",
        "mean_signed_error",
        "underprediction_rate",
        "calibration_intercept",
        "calibration_slope",
        "prediction_sd_ratio",
        "prediction_range_ratio_p95_p5",
        "weighted_abs_bin_error",
        "weighted_rmse_bin_error",
        "max_abs_bin_error",
    ]

    if n_subjects < 5:
        for m in metrics_for_ci:
            summary[f"{m}_ci_lower"] = np.nan
            summary[f"{m}_ci_upper"] = np.nan
        summary["reliability_flag"] = "low_n_subjects"
        return summary

    grouped = {
        sid: df[df["subject_id"] == sid]
        for sid in subject_ids
    }

    boot_rows = []

    for _ in range(n_bootstrap):
        sampled_subjects = rng.choice(subject_ids, size=n_subjects, replace=True)
        sampled = pd.concat([grouped[sid] for sid in sampled_subjects], axis=0, ignore_index=True)

        boot_rows.append(compute_calibration_metrics(sampled, y_pred_col=y_pred_col))

    boot = pd.DataFrame(boot_rows)

    for m in metrics_for_ci:
        values = boot[m].astype(float).replace([np.inf, -np.inf], np.nan).dropna()
        if len(values) == 0:
            summary[f"{m}_ci_lower"] = np.nan
            summary[f"{m}_ci_upper"] = np.nan
        else:
            summary[f"{m}_ci_lower"] = float(np.percentile(values, 2.5))
            summary[f"{m}_ci_upper"] = float(np.percentile(values, 97.5))

    summary["reliability_flag"] = "ok"

    return summary


# ============================================================
# 4. Main calibration analysis
# ============================================================

def make_main_calibration_summary(main_records):
    rows = []
    pred_decile_rows = []
    obs_decile_rows = []

    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = main_records[
                (main_records["target"] == target)
                & (main_records["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            print(f"Calibration summary: {target} | {validation}")

            summary = subject_bootstrap_calibration(
                sub,
                y_pred_col="y_pred",
                n_bootstrap=N_BOOTSTRAP,
                seed=RANDOM_SEED,
            )

            summary.update({
                "target": target,
                "target_label": TARGET_LABELS.get(target, target),
                "validation": validation,
                "validation_label": VALIDATION_LABELS.get(validation, validation),
                "model": MODEL,
                "feature_set": MAIN_FEATURE_SET,
                "prediction_type": "raw",
            })

            rows.append(summary)

            dec_pred = predicted_decile_table(sub, y_pred_col="y_pred", n_deciles=N_DECILES)
            if not dec_pred.empty:
                dec_pred["target"] = target
                dec_pred["target_label"] = TARGET_LABELS.get(target, target)
                dec_pred["validation"] = validation
                dec_pred["validation_label"] = VALIDATION_LABELS.get(validation, validation)
                dec_pred["prediction_type"] = "raw"
                pred_decile_rows.append(dec_pred)

            dec_obs = observed_decile_table(sub, y_pred_col="y_pred", n_deciles=N_DECILES)
            if not dec_obs.empty:
                dec_obs["target"] = target
                dec_obs["target_label"] = TARGET_LABELS.get(target, target)
                dec_obs["validation"] = validation
                dec_obs["validation_label"] = VALIDATION_LABELS.get(validation, validation)
                dec_obs["prediction_type"] = "raw"
                obs_decile_rows.append(dec_obs)

    summary_df = pd.DataFrame(rows)
    pred_decile_df = pd.concat(pred_decile_rows, axis=0, ignore_index=True) if pred_decile_rows else pd.DataFrame()
    obs_decile_df = pd.concat(obs_decile_rows, axis=0, ignore_index=True) if obs_decile_rows else pd.DataFrame()

    summary_df.to_csv(TABLES / "calibration_main_summary.csv", index=False, encoding="utf-8-sig")
    pred_decile_df.to_csv(TABLES / "calibration_predicted_decile_table.csv", index=False, encoding="utf-8-sig")
    obs_decile_df.to_csv(TABLES / "calibration_observed_decile_table.csv", index=False, encoding="utf-8-sig")

    return summary_df, pred_decile_df, obs_decile_df


# ============================================================
# 5. Cross-fitted linear recalibration
# ============================================================

def make_subject_folds(subject_ids, n_folds=N_RECALIBRATION_FOLDS, seed=RANDOM_SEED):
    rng = np.random.default_rng(seed)
    subject_ids = np.array(sorted(subject_ids))
    rng.shuffle(subject_ids)

    folds = np.array_split(subject_ids, n_folds)

    return [np.array(f) for f in folds if len(f) > 0]


def crossfit_linear_recalibration_one_group(df):
    """
    Cross-fitted linear recalibration using participant-level folds.

    For each fold:
    - Fit observed = intercept + slope * predicted on other participants.
    - Apply to held-out participants.

    This avoids evaluating the calibrator on the same participants used to fit it.
    """
    temp = df.copy()
    temp["y_pred_recalibrated"] = np.nan
    temp["recalibration_intercept"] = np.nan
    temp["recalibration_slope"] = np.nan
    temp["recalibration_fold"] = np.nan

    subject_ids = sorted(temp["subject_id"].dropna().unique())

    if len(subject_ids) < 5:
        temp["y_pred_recalibrated"] = temp["y_pred"]
        temp["recalibration_intercept"] = 0.0
        temp["recalibration_slope"] = 1.0
        temp["recalibration_fold"] = 1
        return temp

    folds = make_subject_folds(subject_ids, n_folds=N_RECALIBRATION_FOLDS, seed=RANDOM_SEED)

    for fold_idx, test_subjects in enumerate(folds, start=1):
        test_mask = temp["subject_id"].isin(test_subjects)
        train_mask = ~test_mask

        train = temp[train_mask].copy()

        intercept, slope = fit_linear_calibrator(
            train["y_true"].values,
            train["y_pred"].values,
        )

        if not np.isfinite(intercept) or not np.isfinite(slope):
            intercept = 0.0
            slope = 1.0

        temp.loc[test_mask, "y_pred_recalibrated"] = (
            intercept + slope * temp.loc[test_mask, "y_pred"]
        )
        temp.loc[test_mask, "recalibration_intercept"] = intercept
        temp.loc[test_mask, "recalibration_slope"] = slope
        temp.loc[test_mask, "recalibration_fold"] = fold_idx

    return temp


def run_crossfit_recalibration(main_records):
    recalibrated_parts = []
    metric_rows = []

    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = main_records[
                (main_records["target"] == target)
                & (main_records["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            print(f"Cross-fitted recalibration: {target} | {validation}")

            rec = crossfit_linear_recalibration_one_group(sub)

            recalibrated_parts.append(rec)

            raw_metrics = subject_bootstrap_calibration(
                rec,
                y_pred_col="y_pred",
                n_bootstrap=N_BOOTSTRAP,
                seed=RANDOM_SEED,
            )
            raw_metrics.update({
                "target": target,
                "target_label": TARGET_LABELS.get(target, target),
                "validation": validation,
                "validation_label": VALIDATION_LABELS.get(validation, validation),
                "model": MODEL,
                "feature_set": MAIN_FEATURE_SET,
                "prediction_type": "raw",
            })
            metric_rows.append(raw_metrics)

            cal_metrics = subject_bootstrap_calibration(
                rec,
                y_pred_col="y_pred_recalibrated",
                n_bootstrap=N_BOOTSTRAP,
                seed=RANDOM_SEED,
            )
            cal_metrics.update({
                "target": target,
                "target_label": TARGET_LABELS.get(target, target),
                "validation": validation,
                "validation_label": VALIDATION_LABELS.get(validation, validation),
                "model": MODEL,
                "feature_set": MAIN_FEATURE_SET,
                "prediction_type": "crossfit_linear_recalibrated",
            })
            metric_rows.append(cal_metrics)

    recalibrated = pd.concat(recalibrated_parts, axis=0, ignore_index=True) if recalibrated_parts else pd.DataFrame()
    metrics = pd.DataFrame(metric_rows)

    recalibrated.to_csv(
        TABLES / "calibration_crossfit_recalibrated_records.csv",
        index=False,
        encoding="utf-8-sig",
    )

    metrics.to_csv(
        TABLES / "calibration_crossfit_recalibration_metrics.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return recalibrated, metrics


# ============================================================
# 6. Few-shot calibration analysis
# ============================================================

def make_fewshot_calibration_summary(fewshot_records):
    rows = []
    decile_rows = []

    for target in TARGETS:
        for shots in FEWSHOT_SHOTS_TO_ANALYZE:
            sub = fewshot_records[
                (fewshot_records["target"] == target)
                & (fewshot_records["shots"] == shots)
            ].copy()

            if sub.empty:
                continue

            print(f"Few-shot calibration: {target} | {shots}-shot")

            summary = subject_bootstrap_calibration(
                sub,
                y_pred_col="y_pred",
                n_bootstrap=N_BOOTSTRAP,
                seed=RANDOM_SEED,
            )

            summary.update({
                "target": target,
                "target_label": TARGET_LABELS.get(target, target),
                "validation": "few_shot_personalization",
                "validation_label": VALIDATION_LABELS["few_shot_personalization"],
                "model": MODEL,
                "feature_set": MAIN_FEATURE_SET,
                "shots": int(shots),
                "prediction_type": f"{shots}-shot",
            })

            rows.append(summary)

            dec = predicted_decile_table(sub, y_pred_col="y_pred", n_deciles=N_DECILES)
            if not dec.empty:
                dec["target"] = target
                dec["target_label"] = TARGET_LABELS.get(target, target)
                dec["validation"] = "few_shot_personalization"
                dec["validation_label"] = VALIDATION_LABELS["few_shot_personalization"]
                dec["shots"] = int(shots)
                dec["prediction_type"] = f"{shots}-shot"
                decile_rows.append(dec)

    summary_df = pd.DataFrame(rows)
    decile_df = pd.concat(decile_rows, axis=0, ignore_index=True) if decile_rows else pd.DataFrame()

    summary_df.to_csv(
        TABLES / "calibration_fewshot_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    decile_df.to_csv(
        TABLES / "calibration_fewshot_predicted_decile_table.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return summary_df, decile_df


# ============================================================
# 7. Main text summary
# ============================================================

def fmt_ci(row, metric, digits=3):
    point = row.get(metric, np.nan)
    low = row.get(f"{metric}_ci_lower", np.nan)
    high = row.get(f"{metric}_ci_upper", np.nan)

    if pd.isna(point) or pd.isna(low) or pd.isna(high):
        return ""

    return f"{point:.{digits}f} [{low:.{digits}f}, {high:.{digits}f}]"


def make_calibration_text_summary(main_summary, recalibration_metrics, fewshot_summary):
    rows = []

    for _, row in main_summary.iterrows():
        target = row["target_label"]
        validation = row["validation_label"]

        rows.append({
            "section": "raw_main_model_calibration",
            "target": target,
            "validation": validation,
            "finding": "Calibration slope, prediction-range compression, and binned calibration error",
            "value": (
                f"slope={fmt_ci(row, 'calibration_slope', 3)}, "
                f"intercept={fmt_ci(row, 'calibration_intercept', 1)}, "
                f"sd_ratio={fmt_ci(row, 'prediction_sd_ratio', 3)}, "
                f"range_ratio={fmt_ci(row, 'prediction_range_ratio_p95_p5', 3)}, "
                f"weighted_abs_bin_error={fmt_ci(row, 'weighted_abs_bin_error', 1)}"
            ),
        })

    if not recalibration_metrics.empty:
        for target in TARGETS:
            for validation in VALIDATIONS:
                sub = recalibration_metrics[
                    (recalibration_metrics["target"] == target)
                    & (recalibration_metrics["validation"] == validation)
                ].copy()

                if sub.empty:
                    continue

                raw = sub[sub["prediction_type"] == "raw"]
                cal = sub[sub["prediction_type"] == "crossfit_linear_recalibrated"]

                if raw.empty or cal.empty:
                    continue

                raw = raw.iloc[0]
                cal = cal.iloc[0]

                rows.append({
                    "section": "crossfit_linear_recalibration",
                    "target": TARGET_LABELS.get(target, target),
                    "validation": VALIDATION_LABELS.get(validation, validation),
                    "finding": "Raw versus cross-fitted linearly recalibrated prediction",
                    "value": (
                        f"raw_MAE={raw['MAE']:.1f}, recalibrated_MAE={cal['MAE']:.1f}; "
                        f"raw_slope={raw['calibration_slope']:.3f}, recalibrated_slope={cal['calibration_slope']:.3f}; "
                        f"raw_bin_error={raw['weighted_abs_bin_error']:.1f}, "
                        f"recalibrated_bin_error={cal['weighted_abs_bin_error']:.1f}"
                    ),
                })

    if not fewshot_summary.empty:
        for target in TARGETS:
            sub = fewshot_summary[fewshot_summary["target"] == target].copy()

            if sub.empty:
                continue

            s0 = sub[sub["shots"] == 0]
            s10 = sub[sub["shots"] == 10]

            if s0.empty or s10.empty:
                continue

            s0 = s0.iloc[0]
            s10 = s10.iloc[0]

            rows.append({
                "section": "fewshot_calibration",
                "target": TARGET_LABELS.get(target, target),
                "validation": "Few-shot personalization",
                "finding": "0-shot versus 10-shot calibration",
                "value": (
                    f"0shot_slope={s0['calibration_slope']:.3f}, 10shot_slope={s10['calibration_slope']:.3f}; "
                    f"0shot_sd_ratio={s0['prediction_sd_ratio']:.3f}, 10shot_sd_ratio={s10['prediction_sd_ratio']:.3f}; "
                    f"0shot_bin_error={s0['weighted_abs_bin_error']:.1f}, "
                    f"10shot_bin_error={s10['weighted_abs_bin_error']:.1f}"
                ),
            })

    out = pd.DataFrame(rows)
    out.to_csv(
        TABLES / "calibration_analysis_main_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return out


# ============================================================
# 8. Figures
# ============================================================

def safe_filename(s):
    s = str(s)
    s = re.sub(r"[^A-Za-z0-9_]+", "_", s)
    return s.strip("_")


def plot_scatter(main_records):
    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = main_records[
                (main_records["target"] == target)
                & (main_records["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            intercept, slope = fit_linear_calibrator(sub["y_true"], sub["y_pred"])

            fig, ax = plt.subplots(figsize=(6, 6))
            ax.scatter(sub["y_pred"], sub["y_true"], alpha=0.35, s=16)

            x_min = np.nanpercentile(sub["y_pred"], 1)
            x_max = np.nanpercentile(sub["y_pred"], 99)
            xs = np.linspace(x_min, x_max, 100)

            ax.plot(xs, xs, linestyle="--", linewidth=1, label="Ideal: observed = predicted")

            if np.isfinite(intercept) and np.isfinite(slope):
                ax.plot(xs, intercept + slope * xs, linewidth=1.5, label=f"Fit: slope={slope:.2f}")

            ax.set_xlabel(f"Predicted {TARGET_LABELS[target]} ({TARGET_UNITS[target]})")
            ax.set_ylabel(f"Observed {TARGET_LABELS[target]} ({TARGET_UNITS[target]})")
            ax.set_title(
                f"Calibration scatter\n{TARGET_LABELS[target]} | {VALIDATION_LABELS[validation]}"
            )
            ax.legend()

            fig.tight_layout()
            out = FIGURES / f"calibration_scatter_{target}_{validation}.png"
            fig.savefig(out, dpi=300, bbox_inches="tight")
            plt.close(fig)


def plot_predicted_decile_curve(pred_decile_df):
    if pred_decile_df.empty:
        return

    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = pred_decile_df[
                (pred_decile_df["target"] == target)
                & (pred_decile_df["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            sub = sub.sort_values("predicted_decile")

            fig, ax = plt.subplots(figsize=(7, 5))

            ax.plot(
                sub["predicted_decile"],
                sub["predicted_mean"],
                marker="o",
                label="Predicted mean",
            )
            ax.plot(
                sub["predicted_decile"],
                sub["observed_mean"],
                marker="o",
                label="Observed mean",
            )

            ax.set_xlabel("Predicted response decile")
            ax.set_ylabel(f"Mean response ({TARGET_UNITS[target]})")
            ax.set_title(
                f"Calibration by predicted decile\n{TARGET_LABELS[target]} | {VALIDATION_LABELS[validation]}"
            )
            ax.legend()

            fig.tight_layout()
            out = FIGURES / f"calibration_predicted_decile_curve_{target}_{validation}.png"
            fig.savefig(out, dpi=300, bbox_inches="tight")
            plt.close(fig)


def plot_signed_error_by_predicted_decile(pred_decile_df):
    if pred_decile_df.empty:
        return

    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = pred_decile_df[
                (pred_decile_df["target"] == target)
                & (pred_decile_df["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            sub = sub.sort_values("predicted_decile")

            fig, ax = plt.subplots(figsize=(7, 5))
            ax.axhline(0, linestyle="--", linewidth=1)
            ax.bar(
                sub["predicted_decile"],
                sub["mean_signed_error"],
            )

            ax.set_xlabel("Predicted response decile")
            ax.set_ylabel(f"Mean signed error ({TARGET_UNITS[target]})")
            ax.set_title(
                f"Mean signed error by predicted decile\n{TARGET_LABELS[target]} | {VALIDATION_LABELS[validation]}"
            )

            fig.tight_layout()
            out = FIGURES / f"calibration_signed_error_by_predicted_decile_{target}_{validation}.png"
            fig.savefig(out, dpi=300, bbox_inches="tight")
            plt.close(fig)


def plot_high_response_rate(pred_decile_df):
    if pred_decile_df.empty:
        return

    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = pred_decile_df[
                (pred_decile_df["target"] == target)
                & (pred_decile_df["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            sub = sub.sort_values("predicted_decile")

            fig, ax = plt.subplots(figsize=(7, 5))
            ax.plot(
                sub["predicted_decile"],
                sub["observed_high_response_rate"],
                marker="o",
            )
            ax.axhline(0.25, linestyle="--", linewidth=1, label="Overall top-quartile prevalence")

            ax.set_xlabel("Predicted response decile")
            ax.set_ylabel("Observed high-response rate")
            ax.set_ylim(0, 1)
            ax.set_title(
                f"High-response rate by predicted decile\n{TARGET_LABELS[target]} | {VALIDATION_LABELS[validation]}"
            )
            ax.legend()

            fig.tight_layout()
            out = FIGURES / f"calibration_high_response_rate_{target}_{validation}.png"
            fig.savefig(out, dpi=300, bbox_inches="tight")
            plt.close(fig)


def plot_recalibrated_curve(recalibrated_records):
    if recalibrated_records.empty:
        return

    for target in TARGETS:
        for validation in VALIDATIONS:
            sub = recalibrated_records[
                (recalibrated_records["target"] == target)
                & (recalibrated_records["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            raw_dec = predicted_decile_table(sub, y_pred_col="y_pred", n_deciles=N_DECILES)
            cal_dec = predicted_decile_table(sub, y_pred_col="y_pred_recalibrated", n_deciles=N_DECILES)

            if raw_dec.empty or cal_dec.empty:
                continue

            raw_dec = raw_dec.sort_values("predicted_decile")
            cal_dec = cal_dec.sort_values("predicted_decile")

            fig, ax = plt.subplots(figsize=(7, 5))

            ax.plot(
                raw_dec["predicted_decile"],
                raw_dec["observed_mean"],
                marker="o",
                label="Observed mean, raw prediction bins",
            )
            ax.plot(
                raw_dec["predicted_decile"],
                raw_dec["predicted_mean"],
                marker="o",
                label="Raw predicted mean",
            )
            ax.plot(
                cal_dec["predicted_decile"],
                cal_dec["predicted_mean"],
                marker="o",
                label="Recalibrated predicted mean",
            )

            ax.set_xlabel("Prediction decile")
            ax.set_ylabel(f"Mean response ({TARGET_UNITS[target]})")
            ax.set_title(
                f"Raw vs cross-fitted linear recalibration\n{TARGET_LABELS[target]} | {VALIDATION_LABELS[validation]}"
            )
            ax.legend()

            fig.tight_layout()
            out = FIGURES / f"calibration_recalibrated_curve_{target}_{validation}.png"
            fig.savefig(out, dpi=300, bbox_inches="tight")
            plt.close(fig)


def plot_fewshot_calibration(fewshot_decile_df):
    if fewshot_decile_df.empty:
        return

    for target in TARGETS:
        sub_t = fewshot_decile_df[fewshot_decile_df["target"] == target].copy()

        if sub_t.empty:
            continue

        fig, ax = plt.subplots(figsize=(7, 5))

        for shots in FEWSHOT_SHOTS_TO_ANALYZE:
            sub = sub_t[sub_t["shots"] == shots].copy()
            sub = sub.sort_values("predicted_decile")

            if sub.empty:
                continue

            ax.plot(
                sub["predicted_decile"],
                sub["observed_mean"],
                marker="o",
                label=f"Observed mean in {shots}-shot predicted bins",
            )
            ax.plot(
                sub["predicted_decile"],
                sub["predicted_mean"],
                marker="x",
                linestyle="--",
                label=f"Predicted mean, {shots}-shot",
            )

        ax.set_xlabel("Predicted response decile")
        ax.set_ylabel(f"Mean response ({TARGET_UNITS[target]})")
        ax.set_title(f"Few-shot calibration by predicted decile\n{TARGET_LABELS[target]}")
        ax.legend(fontsize=8)

        fig.tight_layout()
        out = FIGURES / f"calibration_fewshot_predicted_decile_curve_{target}.png"
        fig.savefig(out, dpi=300, bbox_inches="tight")
        plt.close(fig)


# ============================================================
# 9. Main
# ============================================================

def main():
    print("Loading prediction records...")
    pred = load_prediction_records()
    print("Prediction records:", pred.shape)

    print("\nPreparing main-model records...")
    main_records = get_main_model_records(pred)
    print("Main records:", main_records.shape)

    print("\nPreparing few-shot records...")
    fewshot_records = get_fewshot_records(pred)
    print("Few-shot records:", fewshot_records.shape)

    print("\nRunning raw main-model calibration analysis...")
    main_summary, pred_decile_df, obs_decile_df = make_main_calibration_summary(main_records)

    print("\nRunning cross-fitted linear recalibration analysis...")
    recalibrated_records, recalibration_metrics = run_crossfit_recalibration(main_records)

    print("\nRunning few-shot calibration analysis...")
    fewshot_summary, fewshot_decile_df = make_fewshot_calibration_summary(fewshot_records)

    print("\nCreating text summary...")
    text_summary = make_calibration_text_summary(
        main_summary=main_summary,
        recalibration_metrics=recalibration_metrics,
        fewshot_summary=fewshot_summary,
    )

    print("\nGenerating figures...")
    plot_scatter(main_records)
    plot_predicted_decile_curve(pred_decile_df)
    plot_signed_error_by_predicted_decile(pred_decile_df)
    plot_high_response_rate(pred_decile_df)
    plot_recalibrated_curve(recalibrated_records)
    plot_fewshot_calibration(fewshot_decile_df)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 260)
    pd.set_option("display.max_rows", 300)

    print("\nSaved tables:")
    print(TABLES / "calibration_main_summary.csv")
    print(TABLES / "calibration_predicted_decile_table.csv")
    print(TABLES / "calibration_observed_decile_table.csv")
    print(TABLES / "calibration_crossfit_recalibrated_records.csv")
    print(TABLES / "calibration_crossfit_recalibration_metrics.csv")
    print(TABLES / "calibration_fewshot_summary.csv")
    print(TABLES / "calibration_fewshot_predicted_decile_table.csv")
    print(TABLES / "calibration_analysis_main_summary.csv")

    print("\nCalibration main summary:")
    print(main_summary)

    print("\nCross-fitted recalibration metrics:")
    print(recalibration_metrics)

    print("\nFew-shot calibration summary:")
    print(fewshot_summary)

    print("\nText summary:")
    print(text_summary)

    print("\nFigures saved to:")
    print(FIGURES)

    print("\nDone.")


if __name__ == "__main__":
    main()