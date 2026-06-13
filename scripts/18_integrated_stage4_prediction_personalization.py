# -*- coding: utf-8 -*-
"""
Stage 4 for the integrated mainline project.

Question:
    Does adding MSI-core improve PPGR prediction/calibration, and do high-MSI
    participants benefit more from few-shot personalization?

This is a transparent ridge-regression benchmark implemented with numpy only.
It does not replace the existing ensemble models in the project; it creates a
mainline-specific model ladder:

    M1 macro/timing
    M2 + pre-CGM/activity context
    M3 + MSI-core clinical susceptibility
    M4 few-shot recalibration of M2/M3
"""

from __future__ import annotations

from pathlib import Path
import math
import shutil
import textwrap

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NHANES_ROOT = ROOT.parent / "NHANES_MetS_Project"
STAGE1 = ROOT / "outputs" / "integrated_mainline" / "stage1_msi"
OUT = ROOT / "outputs" / "integrated_mainline" / "stage4_prediction_personalization"
NHANES_OUT = NHANES_ROOT / "result" / "integrated_mainline" / "stage4_prediction_personalization"

SHOTS = [0, 1, 3, 5, 10]


FEATURE_SETS = {
    "M1_macro_timing": [
        "calories",
        "carbs",
        "protein",
        "fat",
        "fiber",
        "meal_hour_sin",
        "meal_hour_cos",
        "prev_meal_gap_min",
    ],
    "M2_macro_precgm_context": [
        "calories",
        "carbs",
        "protein",
        "fat",
        "fiber",
        "meal_hour_sin",
        "meal_hour_cos",
        "prev_meal_gap_min",
        "baseline_glucose",
        "pre_glucose_mean_30",
        "pre_glucose_sd_30",
        "pre_glucose_slope_60",
        "activity_calories_pre30",
        "mets_mean_pre30",
    ],
    "M3_msi_enhanced": [
        "calories",
        "carbs",
        "protein",
        "fat",
        "fiber",
        "meal_hour_sin",
        "meal_hour_cos",
        "prev_meal_gap_min",
        "baseline_glucose",
        "pre_glucose_mean_30",
        "pre_glucose_sd_30",
        "pre_glucose_slope_60",
        "activity_calories_pre30",
        "mets_mean_pre30",
        "msi_core_partial_nhanes_ref",
        "homa_ir",
        "tg_hdl",
        "bmi_z_nhanes_ref",
        "hba1c_z_nhanes_ref",
        "fasting_glucose_mgdl_z_nhanes_ref",
        "ln_homa_ir_z_nhanes_ref",
        "ln_tg_hdl_z_nhanes_ref",
    ],
}

TARGETS = {
    "iauc_2h": "2h iAUC",
    "peak_delta_2h": "2h peak delta",
}


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    NHANES_OUT.mkdir(parents=True, exist_ok=True)


def load_data() -> pd.DataFrame:
    df = pd.read_csv(STAGE1 / "cgmacros_meal_level_with_msi_core.csv")
    df["meal_time"] = pd.to_datetime(df["meal_time"], errors="coerce")
    for c in set(sum(FEATURE_SETS.values(), [])) | set(TARGETS.keys()):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.sort_values(["subject_id", "meal_time"]).reset_index(drop=True)


def fit_ridge(train: pd.DataFrame, features: list[str], target: str, alpha: float = 10.0) -> dict:
    x_train = train[features].copy()
    y = train[target].astype(float).to_numpy()
    med = x_train.median(numeric_only=True)
    x_train = x_train.fillna(med)

    # Winsorize using training limits to reduce impact of food-entry outliers.
    q01 = x_train.quantile(0.01)
    q99 = x_train.quantile(0.99)
    x_train = x_train.clip(q01, q99, axis=1)
    mean = x_train.mean()
    sd = x_train.std(ddof=0).replace(0, 1.0)
    xs = ((x_train - mean) / sd).to_numpy(dtype=float)
    X = np.column_stack([np.ones(xs.shape[0]), xs])
    penalty = np.eye(X.shape[1]) * alpha
    penalty[0, 0] = 0
    beta = np.linalg.pinv(X.T @ X + penalty) @ (X.T @ y)
    return {
        "features": features,
        "median": med,
        "q01": q01,
        "q99": q99,
        "mean": mean,
        "sd": sd,
        "beta": beta,
    }


def predict_ridge(model: dict, data: pd.DataFrame) -> np.ndarray:
    features = model["features"]
    x = data[features].copy().fillna(model["median"])
    x = x.clip(model["q01"], model["q99"], axis=1)
    xs = ((x - model["mean"]) / model["sd"]).to_numpy(dtype=float)
    X = np.column_stack([np.ones(xs.shape[0]), xs])
    return X @ model["beta"]


def leave_subject_out_predictions(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    subjects = sorted(df["subject_id"].dropna().unique())
    for target in TARGETS:
        eligible = df.loc[df[target].notna()].copy()
        for feature_set, features in FEATURE_SETS.items():
            for sid in subjects:
                test = eligible.loc[eligible["subject_id"] == sid].copy()
                train = eligible.loc[eligible["subject_id"] != sid].copy()
                if len(test) == 0 or len(train) < 30:
                    continue
                model = fit_ridge(train, features, target)
                pred = predict_ridge(model, test)
                for (_, row), yhat in zip(test.iterrows(), pred):
                    records.append(
                        {
                            "subject_id": row["subject_id"],
                            "meal_time": row["meal_time"],
                            "target": target,
                            "target_label": TARGETS[target],
                            "feature_set": feature_set,
                            "validation": "leave_subject_out_ridge",
                            "y_true": row[target],
                            "y_pred_global": yhat,
                            "msi_core": row["msi_core_partial_nhanes_ref"],
                            "msi_tertile": row["msi_core_tertile_within_dataset"],
                        }
                    )
    return pd.DataFrame(records)


def fit_calibration(y_true: np.ndarray, y_pred: np.ndarray, shots: int) -> tuple[float, float]:
    if shots <= 0 or len(y_true) == 0:
        return 0.0, 1.0
    if shots == 1 or np.nanstd(y_pred) < 1e-9:
        return float(np.nanmean(y_true - y_pred)), 1.0
    X = np.column_stack([np.ones(len(y_pred)), y_pred])
    beta = np.linalg.pinv(X.T @ X) @ (X.T @ y_true)
    return float(beta[0]), float(beta[1])


def fewshot_records(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    pred = pred.sort_values(["target", "feature_set", "subject_id", "meal_time"]).copy()
    for (target, feature_set, sid), d in pred.groupby(["target", "feature_set", "subject_id"]):
        d = d.sort_values("meal_time").reset_index(drop=True)
        for shots in SHOTS:
            if len(d) <= shots:
                continue
            calib = d.iloc[:shots]
            test = d.iloc[shots:].copy()
            intercept, slope = fit_calibration(
                calib["y_true"].to_numpy(dtype=float),
                calib["y_pred_global"].to_numpy(dtype=float),
                shots,
            )
            y_adj = intercept + slope * test["y_pred_global"].to_numpy(dtype=float)
            for (_, row), yhat in zip(test.iterrows(), y_adj):
                rows.append(
                    {
                        "subject_id": row["subject_id"],
                        "meal_time": row["meal_time"],
                        "target": target,
                        "target_label": row["target_label"],
                        "feature_set": feature_set,
                        "shots": shots,
                        "y_true": row["y_true"],
                        "y_pred": yhat,
                        "y_pred_global": row["y_pred_global"],
                        "calibration_intercept": intercept,
                        "calibration_slope_subject": slope,
                        "msi_core": row["msi_core"],
                        "msi_tertile": row["msi_tertile"],
                    }
                )
    return pd.DataFrame(rows)


def calibration_slope(y_true: pd.Series, y_pred: pd.Series) -> float:
    y = y_true.to_numpy(dtype=float)
    x = y_pred.to_numpy(dtype=float)
    if len(y) < 3 or np.nanstd(x) < 1e-9:
        return np.nan
    X = np.column_stack([np.ones(len(x)), x])
    beta = np.linalg.pinv(X.T @ X) @ (X.T @ y)
    return float(beta[1])


def metrics(df: pd.DataFrame) -> dict:
    y = df["y_true"].to_numpy(dtype=float)
    p = df["y_pred"].to_numpy(dtype=float)
    err = p - y
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    denom = float(np.sum((y - np.mean(y)) ** 2))
    r2 = float(1 - np.sum(err**2) / denom) if denom > 0 else np.nan
    return {
        "n": len(df),
        "n_subjects": df["subject_id"].nunique(),
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
        "mean_signed_error": float(np.mean(err)),
        "calibration_slope": calibration_slope(df["y_true"], df["y_pred"]),
    }


def summarize_performance(fs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    group_cols = ["target", "target_label", "feature_set", "shots", "msi_tertile"]
    for keys, d in fs.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, keys))
        row.update(metrics(d))
        rows.append(row)
    out = pd.DataFrame(rows)
    return out.sort_values(["target", "feature_set", "shots", "msi_tertile"])


def model_comparison(perf: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for target in TARGETS:
        for tertile in ["low", "middle", "high"]:
            for shots in SHOTS:
                base = perf.loc[
                    (perf["target"] == target)
                    & (perf["msi_tertile"] == tertile)
                    & (perf["shots"] == shots)
                    & (perf["feature_set"] == "M2_macro_precgm_context")
                ]
                msi = perf.loc[
                    (perf["target"] == target)
                    & (perf["msi_tertile"] == tertile)
                    & (perf["shots"] == shots)
                    & (perf["feature_set"] == "M3_msi_enhanced")
                ]
                if len(base) and len(msi):
                    b = base.iloc[0]
                    m = msi.iloc[0]
                    rows.append(
                        {
                            "target": target,
                            "target_label": b["target_label"],
                            "msi_tertile": tertile,
                            "shots": shots,
                            "MAE_M2": b["MAE"],
                            "MAE_M3": m["MAE"],
                            "MAE_delta_M3_minus_M2": m["MAE"] - b["MAE"],
                            "MAE_pct_change": 100 * (m["MAE"] - b["MAE"]) / b["MAE"],
                            "calibration_slope_M2": b["calibration_slope"],
                            "calibration_slope_M3": m["calibration_slope"],
                            "n": int(m["n"]),
                        }
                    )
    return pd.DataFrame(rows)


def write_report(perf: pd.DataFrame, comp: pd.DataFrame) -> Path:
    def row(target, tertile, shots):
        d = comp.loc[(comp["target"] == target) & (comp["msi_tertile"] == tertile) & (comp["shots"] == shots)]
        return d.iloc[0] if len(d) else None

    hi0 = row("iauc_2h", "high", 0)
    hi10 = row("iauc_2h", "high", 10)
    lo0 = row("iauc_2h", "low", 0)

    def fmt(r):
        if r is None:
            return "NA"
        return f"M2 MAE={r.MAE_M2:.1f}, M3 MAE={r.MAE_M3:.1f}, delta={r.MAE_delta_M3_minus_M2:.1f} ({r.MAE_pct_change:.1f}%), n={int(r.n)}"

    report = f"""# Stage 4 报告：MSI-aware PPGR prediction and personalization

日期：2026-06-10

## 目的

检验加入 `MSI-core` 后是否改善 PPGR 预测、校准和少样本个体化，尤其是高 MSI 个体。

## 方法

由于当前 Python 环境无 `sklearn`，本阶段使用纯 numpy 实现 ridge regression，并采用 leave-subject-out 验证。

模型阶梯：

- M1: macro + meal timing
- M2: M1 + pre-CGM/activity context
- M3: M2 + MSI-core / HOMA-IR / TG-HDL 等代谢易感性特征
- M4: 对 M2/M3 进行 0/1/3/5/10-shot subject-specific recalibration

## 关键结果快照：2h iAUC

- Low MSI, 0-shot: {fmt(lo0)}
- High MSI, 0-shot: {fmt(hi0)}
- High MSI, 10-shot: {fmt(hi10)}

## 如何解释

Stage 4 的主线问题是：MSI 是否提升模型对 PPGR vulnerability 的识别，以及高 MSI 个体是否更需要少样本个体化。若 M3 在高 MSI 组降低 MAE 或改善 calibration slope，可作为主文证据；若改善不稳定，也仍可报告为“MSI 是强风险分层变量，但进入简单线性模型后的预测增益有限”，将重点放在分层风险和个体化收益。

## 输出文件

- `stage4_global_prediction_records.csv`
- `stage4_fewshot_prediction_records.csv`
- `stage4_performance_by_msi.csv`
- `stage4_msi_model_comparison.csv`
- `stage4_prediction_personalization_report_2026-06-10.md`
"""
    out = OUT / "stage4_prediction_personalization_report_2026-06-10.md"
    out.write_text(textwrap.dedent(report), encoding="utf-8-sig")
    return out


def main() -> None:
    ensure_dirs()
    df = load_data()
    pred = leave_subject_out_predictions(df)
    fs = fewshot_records(pred)
    perf = summarize_performance(fs)
    comp = model_comparison(perf)

    pred_out = OUT / "stage4_global_prediction_records.csv"
    fs_out = OUT / "stage4_fewshot_prediction_records.csv"
    perf_out = OUT / "stage4_performance_by_msi.csv"
    comp_out = OUT / "stage4_msi_model_comparison.csv"
    pred.to_csv(pred_out, index=False, encoding="utf-8-sig")
    fs.to_csv(fs_out, index=False, encoding="utf-8-sig")
    perf.to_csv(perf_out, index=False, encoding="utf-8-sig")
    comp.to_csv(comp_out, index=False, encoding="utf-8-sig")
    report_out = write_report(perf, comp)

    for path in [perf_out, comp_out, report_out]:
        shutil.copy2(path, NHANES_OUT / path.name)

    print("Stage 4 prediction/person personalization completed.")
    print(f"Output directory: {OUT}")
    view = comp.loc[(comp["target"] == "iauc_2h") & (comp["shots"].isin([0, 5, 10]))]
    print(view[["target_label", "msi_tertile", "shots", "MAE_M2", "MAE_M3", "MAE_delta_M3_minus_M2", "MAE_pct_change", "n"]].to_string(index=False))


if __name__ == "__main__":
    main()
