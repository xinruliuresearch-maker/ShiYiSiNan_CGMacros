# -*- coding: utf-8 -*-
"""
Stage 3 for the integrated mainline project.

Question:
    In CGMacros, does MSI-core predict meal-level PPGR vulnerability, and
    does it amplify the effect of meal carbohydrate load?

This script uses meal-level OLS / linear probability models with cluster-robust
standard errors by subject. The goal is not a final causal model, but a
transparent mainline test:

    PPGR ~ meal_load + MSI-core + meal_load x MSI-core + pre-meal state + context
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
OUT = ROOT / "outputs" / "integrated_mainline" / "stage3_cgmacros_msi_ppgr"
NHANES_OUT = NHANES_ROOT / "result" / "integrated_mainline" / "stage3_cgmacros_msi_ppgr"


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    NHANES_OUT.mkdir(parents=True, exist_ok=True)


def p_norm_2sided(z: float) -> float:
    if not np.isfinite(z):
        return np.nan
    return math.erfc(abs(float(z)) / math.sqrt(2.0))


def bh_fdr(pvals: pd.Series) -> pd.Series:
    p = pd.to_numeric(pvals, errors="coerce")
    out = pd.Series(np.nan, index=p.index, dtype=float)
    mask = p.notna()
    vals = p[mask].to_numpy()
    if len(vals) == 0:
        return out
    order = np.argsort(vals)
    ranked = vals[order]
    m = len(vals)
    q = ranked * m / (np.arange(m) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.clip(q, 0, 1)
    tmp = np.empty_like(q)
    tmp[order] = q
    out.loc[mask] = tmp
    return out


def zscore(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    sd = x.std(ddof=0)
    if not np.isfinite(sd) or sd == 0:
        return x * 0
    return (x - x.mean()) / sd


def winsorize(s: pd.Series, p_low: float = 0.01, p_high: float = 0.99) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    lo, hi = x.quantile([p_low, p_high])
    return x.clip(lo, hi)


def prepare_data() -> pd.DataFrame:
    df = pd.read_csv(STAGE1 / "cgmacros_meal_level_with_msi_core.csv")

    df["carbs_g_w"] = winsorize(df["carbs"], 0.01, 0.99)
    df["protein_g_w"] = winsorize(df["protein"], 0.01, 0.99)
    df["fat_g_w"] = winsorize(df["fat"], 0.01, 0.99)
    df["fiber_g_w"] = winsorize(df["fiber"], 0.01, 0.99)
    df["calories_w"] = winsorize(df["calories"], 0.01, 0.99)

    df["carbs_10g"] = df["carbs_g_w"] / 10.0
    df["protein_10g"] = df["protein_g_w"] / 10.0
    df["fat_10g"] = df["fat_g_w"] / 10.0
    df["fiber_5g"] = df["fiber_g_w"] / 5.0
    df["energy_100kcal"] = df["calories_w"] / 100.0

    df["msi_core"] = pd.to_numeric(df["msi_core_partial_nhanes_ref"], errors="coerce")
    df["msi_core_centered"] = df["msi_core"] - df["msi_core"].mean(skipna=True)
    df["msi_tertile"] = df["msi_core_tertile_within_dataset"]

    df["baseline_glucose_z"] = zscore(df["baseline_glucose"])
    df["pre_glucose_mean_30_z"] = zscore(df["pre_glucose_mean_30"])
    df["activity_calories_pre30_z"] = zscore(df["activity_calories_pre30"])
    df["mets_mean_pre30_z"] = zscore(df["mets_mean_pre30"])

    df["iauc_2h_per1000"] = df["iauc_2h"] / 1000.0
    df["high_iauc_top_quartile"] = (df["iauc_2h"] >= df["iauc_2h"].quantile(0.75)).astype(float)
    df["high_peak_top_quartile"] = (df["peak_delta_2h"] >= df["peak_delta_2h"].quantile(0.75)).astype(float)
    df["carbs_x_msi"] = df["carbs_10g"] * df["msi_core_centered"]
    return df


def design_matrix(df: pd.DataFrame, outcome: str, model: str) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    if model == "base_interaction":
        numeric = [
            "carbs_10g",
            "msi_core_centered",
            "carbs_x_msi",
            "baseline_glucose_z",
            "meal_hour_sin",
            "meal_hour_cos",
        ]
    elif model == "macro_context_interaction":
        numeric = [
            "carbs_10g",
            "protein_10g",
            "fat_10g",
            "fiber_5g",
            "msi_core_centered",
            "carbs_x_msi",
            "baseline_glucose_z",
            "meal_hour_sin",
            "meal_hour_cos",
            "activity_calories_pre30_z",
        ]
    else:
        raise ValueError(model)

    needed = [outcome, "subject_id"] + numeric
    d = df[needed].copy()
    for c in [outcome] + numeric:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna()

    x_parts = [pd.Series(1.0, index=d.index, name="Intercept")]
    for c in numeric:
        x_parts.append(d[c].rename(c))
    X = pd.concat(x_parts, axis=1).astype(float)
    y = d[outcome].astype(float)
    clusters = d["subject_id"].astype(str)
    return X, y, clusters


def fit_ols_cluster(X: pd.DataFrame, y: pd.Series, clusters: pd.Series) -> pd.DataFrame:
    x = X.to_numpy(dtype=float)
    yy = y.to_numpy(dtype=float)
    k = x.shape[1]
    n = x.shape[0]
    xtx = x.T @ x
    xtx_inv = np.linalg.pinv(xtx)
    beta = xtx_inv @ (x.T @ yy)
    resid = yy - x @ beta

    meat = np.zeros((k, k), dtype=float)
    cluster_values = clusters.to_numpy()
    unique_clusters = pd.unique(cluster_values)
    for g in unique_clusters:
        idx = cluster_values == g
        sg = x[idx, :].T @ resid[idx]
        meat += np.outer(sg, sg)

    g = len(unique_clusters)
    correction = (g / (g - 1)) * ((n - 1) / (n - k)) if g > 1 and n > k else 1.0
    cov = correction * xtx_inv @ meat @ xtx_inv
    se = np.sqrt(np.maximum(np.diag(cov), 0))

    rows = []
    for name, b, s in zip(X.columns, beta, se):
        z = b / s if s > 0 else np.nan
        rows.append(
            {
                "term": name,
                "estimate": float(b),
                "se": float(s),
                "z": float(z) if np.isfinite(z) else np.nan,
                "p_value": p_norm_2sided(z),
                "ci_low": float(b - 1.96 * s),
                "ci_high": float(b + 1.96 * s),
                "n": int(n),
                "n_subjects": int(g),
            }
        )
    return pd.DataFrame(rows)


def run_models(df: pd.DataFrame) -> pd.DataFrame:
    outcomes = {
        "iauc_2h_per1000": ("2h iAUC", "1000 mg/dL*min"),
        "peak_delta_2h": ("2h peak delta", "mg/dL"),
        "high_iauc_top_quartile": ("High iAUC top quartile", "risk difference"),
        "high_peak_top_quartile": ("High peak top quartile", "risk difference"),
    }
    models = ["base_interaction", "macro_context_interaction"]
    all_rows = []
    for outcome, (label, unit) in outcomes.items():
        for model in models:
            X, y, clusters = design_matrix(df, outcome, model)
            res = fit_ols_cluster(X, y, clusters)
            res.insert(0, "model", model)
            res.insert(0, "outcome", outcome)
            res.insert(1, "outcome_label", label)
            res["unit"] = unit
            all_rows.append(res)
    out = pd.concat(all_rows, ignore_index=True)
    out["q_value"] = bh_fdr(out["p_value"])
    out["estimate_CI"] = out.apply(
        lambda r: f"{r['estimate']:.3f} ({r['ci_low']:.3f}, {r['ci_high']:.3f})",
        axis=1,
    )
    return out


def subgroup_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for tertile, d in df.groupby("msi_tertile", dropna=False):
        rows.append(
            {
                "msi_tertile": tertile,
                "n_subjects": d["subject_id"].nunique(),
                "n_meals": len(d),
                "median_msi": d["msi_core"].median(),
                "median_carbs_g": d["carbs"].median(),
                "median_iauc_2h": d["iauc_2h"].median(),
                "mean_iauc_2h": d["iauc_2h"].mean(),
                "median_peak_delta_2h": d["peak_delta_2h"].median(),
                "mean_peak_delta_2h": d["peak_delta_2h"].mean(),
                "high_iauc_rate": d["high_iauc_top_quartile"].mean(),
                "high_peak_rate": d["high_peak_top_quartile"].mean(),
            }
        )
    order = {"low": 0, "middle": 1, "high": 2}
    out = pd.DataFrame(rows)
    out["_order"] = out["msi_tertile"].map(order).fillna(9)
    return out.sort_values("_order").drop(columns="_order")


def write_report(results: pd.DataFrame, sub: pd.DataFrame) -> Path:
    def get(outcome, model, term):
        r = results.loc[
            (results["outcome"] == outcome) & (results["model"] == model) & (results["term"] == term)
        ].iloc[0]
        q = "<0.001" if r.q_value < 0.001 else f"{r.q_value:.3f}"
        return f"{r.estimate_CI}, p={r.p_value:.3g}, q={q}, n={int(r.n)}"

    high = sub.loc[sub["msi_tertile"] == "high"].iloc[0]
    low = sub.loc[sub["msi_tertile"] == "low"].iloc[0]

    report = f"""# Stage 3 报告：CGMacros MSI-core 与 PPGR vulnerability

日期：2026-06-10

## 目的

检验 Stage 1 构建的 `MSI-core` 是否在 CGMacros 中表现为餐后动态血糖脆弱性，即：

1. 高 MSI 个体是否有更高 PPGR。
2. MSI 是否放大餐食碳水负荷对 PPGR 的影响。
3. 高 MSI 个体是否更容易出现 high-response meals。

## 数据

- 餐食级样本：{len(pd.read_csv(STAGE1 / 'cgmacros_meal_level_with_msi_core.csv'))}
- 受试者：{int(sub['n_subjects'].sum())}
- MSI 分层：数据集内部三分位 low / middle / high。

## MSI 分层描述

| MSI tertile | subjects | meals | median iAUC 2h | high iAUC rate | median peak delta |
|---|---:|---:|---:|---:|---:|
| low | {int(low.n_subjects)} | {int(low.n_meals)} | {low.median_iauc_2h:.1f} | {low.high_iauc_rate:.3f} | {low.median_peak_delta_2h:.1f} |
| high | {int(high.n_subjects)} | {int(high.n_meals)} | {high.median_iauc_2h:.1f} | {high.high_iauc_rate:.3f} | {high.median_peak_delta_2h:.1f} |

## 交互模型关键结果

模型形式：

`PPGR ~ carbs_10g + MSI-core + carbs_10g × MSI-core + pre-meal glucose + meal timing + context`

### 2h iAUC

- `carbs_10g`: {get('iauc_2h_per1000', 'macro_context_interaction', 'carbs_10g')}
- `MSI-core`: {get('iauc_2h_per1000', 'macro_context_interaction', 'msi_core_centered')}
- `carbs_10g × MSI-core`: {get('iauc_2h_per1000', 'macro_context_interaction', 'carbs_x_msi')}

### 2h peak delta

- `carbs_10g`: {get('peak_delta_2h', 'macro_context_interaction', 'carbs_10g')}
- `MSI-core`: {get('peak_delta_2h', 'macro_context_interaction', 'msi_core_centered')}
- `carbs_10g × MSI-core`: {get('peak_delta_2h', 'macro_context_interaction', 'carbs_x_msi')}

### High-response risk

- High iAUC `carbs_10g × MSI-core`: {get('high_iauc_top_quartile', 'macro_context_interaction', 'carbs_x_msi')}
- High peak `carbs_10g × MSI-core`: {get('high_peak_top_quartile', 'macro_context_interaction', 'carbs_x_msi')}

## 解释

Stage 3 的核心不是证明 DEHP 直接导致 PPGR，而是检验 NHANES 中定义的代谢易感性桥梁是否在 CGMacros 中表现为餐后动态血糖脆弱性。若 `MSI-core` 和 `carbs_10g × MSI-core` 为正，说明高代谢易感个体在面对更高碳水负荷时更容易产生高 PPGR，这正好连接 Stage 2 与 Stage 5。

## 输出文件

- `stage3_cgmacros_msi_ppgr_model_results.csv`
- `stage3_cgmacros_msi_ppgr_key_results.csv`
- `stage3_msi_tertile_ppgr_summary.csv`
- `stage3_cgmacros_msi_ppgr_report_2026-06-10.md`
"""
    out = OUT / "stage3_cgmacros_msi_ppgr_report_2026-06-10.md"
    out.write_text(textwrap.dedent(report), encoding="utf-8-sig")
    return out


def main() -> None:
    ensure_dirs()
    df = prepare_data()
    results = run_models(df)
    sub = subgroup_summary(df)

    key_terms = ["carbs_10g", "msi_core_centered", "carbs_x_msi", "baseline_glucose_z"]
    key = results.loc[results["term"].isin(key_terms)].copy()

    results_out = OUT / "stage3_cgmacros_msi_ppgr_model_results.csv"
    key_out = OUT / "stage3_cgmacros_msi_ppgr_key_results.csv"
    sub_out = OUT / "stage3_msi_tertile_ppgr_summary.csv"
    results.to_csv(results_out, index=False, encoding="utf-8-sig")
    key.to_csv(key_out, index=False, encoding="utf-8-sig")
    sub.to_csv(sub_out, index=False, encoding="utf-8-sig")
    report_out = write_report(results, sub)

    for path in [results_out, key_out, sub_out, report_out]:
        shutil.copy2(path, NHANES_OUT / path.name)

    print("Stage 3 CGMacros MSI -> PPGR completed.")
    print(f"Output directory: {OUT}")
    print(sub.to_string(index=False))
    print(key.loc[(key['model'] == 'macro_context_interaction') & (key['term'].isin(['carbs_10g','msi_core_centered','carbs_x_msi']))][['outcome_label','term','estimate_CI','p_value','q_value','n']].to_string(index=False))


if __name__ == "__main__":
    main()
