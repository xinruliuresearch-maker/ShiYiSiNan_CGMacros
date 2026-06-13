# -*- coding: utf-8 -*-
"""
Computational workflow for Phase 0-5 of the integrated CGMacros + NHANES
mainline project.

The workflow only uses pandas/numpy/standard-library functionality so it can
run on the current Windows workstation without R, scipy, sklearn, statsmodels,
or matplotlib. It writes manuscript-facing tables/reports into:

    outputs/integrated_mainline/phase0_protocol
    outputs/integrated_mainline/phase1_qc_msi_sensitivity
    outputs/integrated_mainline/phase2_nhanes_survey_ready
    outputs/integrated_mainline/phase3_cgmacros_robust_inference
    outputs/integrated_mainline/phase4_prediction_upgrade
    outputs/integrated_mainline/phase5_external_validation

and mirrors the same deliverables into the NHANES project result folder.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import NormalDist
import math
import re
import shutil
import textwrap
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NHANES_ROOT = ROOT.parent / "NHANES_MetS_Project"
OUT_ROOT = ROOT / "outputs" / "integrated_mainline"
MIRROR_ROOT = NHANES_ROOT / "result" / "integrated_mainline"
STAGE1 = OUT_ROOT / "stage1_msi"
STAGE5 = OUT_ROOT / "stage5_bionic_digestion_design"
TODAY = "2026-06-10"
RNG = np.random.default_rng(20260610)


COMPONENT_Z = [
    "bmi_z_nhanes_ref",
    "hba1c_z_nhanes_ref",
    "fasting_glucose_mgdl_z_nhanes_ref",
    "ln_homa_ir_z_nhanes_ref",
    "ln_tg_hdl_z_nhanes_ref",
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def mirror_file(path: Path) -> None:
    if not path.exists():
        return
    rel = path.relative_to(OUT_ROOT)
    dest = MIRROR_ROOT / rel
    ensure_dir(dest.parent)
    shutil.copy2(path, dest)


def write_text(path: Path, content: str) -> Path:
    ensure_dir(path.parent)
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    mirror_file(path)
    return path


def write_csv(path: Path, df: pd.DataFrame) -> Path:
    ensure_dir(path.parent)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    mirror_file(path)
    return path


def safe_num(s: pd.Series | np.ndarray | list) -> pd.Series:
    return pd.to_numeric(pd.Series(s), errors="coerce")


def zscore(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    sd = x.std(ddof=0)
    if not np.isfinite(sd) or sd == 0:
        return pd.Series(np.nan, index=x.index)
    return (x - x.mean()) / sd


def winsorize(s: pd.Series, low: float = 0.01, high: float = 0.99) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    lo, hi = x.quantile([low, high])
    return x.clip(lo, hi)


def rank_inverse_normal(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    out = pd.Series(np.nan, index=x.index, dtype=float)
    mask = x.notna()
    n = int(mask.sum())
    if n == 0:
        return out
    ranks = x.loc[mask].rank(method="average")
    probs = (ranks - 0.5) / n
    nd = NormalDist()
    out.loc[mask] = [nd.inv_cdf(float(p)) for p in probs]
    return out


def p_norm_2sided(z: float) -> float:
    if not np.isfinite(z):
        return np.nan
    return math.erfc(abs(float(z)) / math.sqrt(2.0))


def bh_fdr(pvals: pd.Series) -> pd.Series:
    p = pd.to_numeric(pvals, errors="coerce")
    out = pd.Series(np.nan, index=p.index, dtype=float)
    mask = p.notna()
    vals = p.loc[mask].to_numpy()
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


def weighted_quantile(values: pd.Series, weights: pd.Series, probs: list[float]) -> np.ndarray:
    x = pd.to_numeric(values, errors="coerce")
    w = pd.to_numeric(weights, errors="coerce")
    mask = x.notna() & w.notna() & (w > 0)
    if mask.sum() == 0:
        return np.array([np.nan] * len(probs))
    xs = x.loc[mask].to_numpy(dtype=float)
    ws = w.loc[mask].to_numpy(dtype=float)
    order = np.argsort(xs)
    xs = xs[order]
    ws = ws[order]
    cdf = np.cumsum(ws) / np.sum(ws)
    return np.interp(probs, cdf, xs)


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    x = pd.to_numeric(values, errors="coerce")
    w = pd.to_numeric(weights, errors="coerce")
    mask = x.notna() & w.notna() & (w > 0)
    if mask.sum() == 0:
        return np.nan
    return float(np.sum(x.loc[mask] * w.loc[mask]) / np.sum(w.loc[mask]))


def pearson(x: pd.Series, y: pd.Series) -> float:
    d = pd.DataFrame({"x": pd.to_numeric(x, errors="coerce"), "y": pd.to_numeric(y, errors="coerce")}).dropna()
    if len(d) < 3:
        return np.nan
    if d["x"].std(ddof=0) == 0 or d["y"].std(ddof=0) == 0:
        return np.nan
    return float(np.corrcoef(d["x"], d["y"])[0, 1])


def spearman(x: pd.Series, y: pd.Series) -> float:
    d = pd.DataFrame({"x": pd.to_numeric(x, errors="coerce"), "y": pd.to_numeric(y, errors="coerce")}).dropna()
    if len(d) < 3:
        return np.nan
    return pearson(d["x"].rank(method="average"), d["y"].rank(method="average"))


def make_design(
    df: pd.DataFrame,
    outcome: str,
    predictors: list[str],
    categorical: list[str] | None = None,
    weight_col: str | None = None,
    cluster_col: str | None = None,
    standardize_predictors: set[str] | None = None,
) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    categorical = categorical or []
    standardize_predictors = standardize_predictors or set()
    needed = [outcome] + predictors + categorical
    if weight_col:
        needed.append(weight_col)
    if cluster_col:
        needed.append(cluster_col)
    d = df[[c for c in needed if c in df.columns]].copy()
    for c in [outcome] + predictors:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    if weight_col:
        d[weight_col] = pd.to_numeric(d[weight_col], errors="coerce")
    d = d.dropna()
    if weight_col:
        d = d.loc[d[weight_col] > 0].copy()
    x_parts = [pd.Series(1.0, index=d.index, name="Intercept")]
    for c in predictors:
        vals = d[c].astype(float)
        if c in standardize_predictors:
            sd = vals.std(ddof=0)
            vals = (vals - vals.mean()) / sd if np.isfinite(sd) and sd > 0 else vals * 0
        x_parts.append(vals.rename(c))
    for c in categorical:
        cats = pd.get_dummies(d[c].astype("category"), prefix=c, drop_first=True, dtype=float)
        if cats.shape[1]:
            x_parts.append(cats)
    X = pd.concat(x_parts, axis=1).astype(float)
    y = d[outcome].astype(float)
    w = d[weight_col].astype(float) if weight_col else pd.Series(1.0, index=d.index)
    clusters = d[cluster_col].astype(str) if cluster_col else pd.Series(np.arange(len(d)), index=d.index).astype(str)
    return X, y, w, clusters


def fit_linear_cluster(X: pd.DataFrame, y: pd.Series, clusters: pd.Series, w: pd.Series | None = None) -> pd.DataFrame:
    x = X.to_numpy(dtype=float)
    yy = y.to_numpy(dtype=float)
    ww = np.ones(len(yy), dtype=float) if w is None else w.to_numpy(dtype=float)
    k = x.shape[1]
    n = x.shape[0]
    if n <= k:
        raise ValueError("Insufficient observations for model")
    xw = x * ww[:, None]
    xtwx = x.T @ xw
    xtwy = x.T @ (ww * yy)
    xtwx_inv = np.linalg.pinv(xtwx)
    beta = xtwx_inv @ xtwy
    resid = yy - x @ beta
    meat = np.zeros((k, k), dtype=float)
    cluster_values = clusters.to_numpy()
    unique_clusters = pd.unique(cluster_values)
    for g in unique_clusters:
        idx = cluster_values == g
        sg = x[idx, :].T @ (ww[idx] * resid[idx])
        meat += np.outer(sg, sg)
    g = len(unique_clusters)
    correction = (g / (g - 1)) * ((n - 1) / (n - k)) if g > 1 and n > k else 1.0
    cov = correction * xtwx_inv @ meat @ xtwx_inv
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
                "n_clusters": int(g),
                "n_parameters": int(k),
            }
        )
    return pd.DataFrame(rows)


def fit_simple_linear(df: pd.DataFrame, outcome: str, predictors: list[str]) -> tuple[np.ndarray, list[str], pd.DataFrame]:
    d = df[[outcome] + predictors].copy()
    for c in [outcome] + predictors:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna()
    X = np.column_stack([np.ones(len(d))] + [d[c].to_numpy(dtype=float) for c in predictors])
    y = d[outcome].to_numpy(dtype=float)
    beta = np.linalg.pinv(X.T @ X) @ (X.T @ y)
    return beta, ["Intercept"] + predictors, d


def trapezoid_auc(times: np.ndarray, values: np.ndarray, start: float = 0, end: float = 120) -> float:
    mask = np.isfinite(times) & np.isfinite(values) & (times >= start) & (times <= end)
    if mask.sum() < 2:
        return np.nan
    t = times[mask]
    v = values[mask]
    order = np.argsort(t)
    tt = t[order]
    vv = v[order]
    return float(np.sum((tt[1:] - tt[:-1]) * (vv[1:] + vv[:-1]) / 2.0))


def auc_score(y_true: pd.Series, score: pd.Series) -> float:
    d = pd.DataFrame({"y": y_true.astype(float), "s": score.astype(float)}).dropna()
    if d["y"].nunique() < 2:
        return np.nan
    ranks = d["s"].rank(method="average")
    n_pos = int((d["y"] == 1).sum())
    n_neg = int((d["y"] == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return np.nan
    sum_ranks_pos = ranks.loc[d["y"] == 1].sum()
    return float((sum_ranks_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def auprc_score(y_true: pd.Series, score: pd.Series) -> float:
    d = pd.DataFrame({"y": y_true.astype(int), "s": score.astype(float)}).dropna()
    if len(d) == 0 or d["y"].sum() == 0:
        return np.nan
    d = d.sort_values("s", ascending=False)
    tp = np.cumsum(d["y"].to_numpy())
    fp = np.cumsum(1 - d["y"].to_numpy())
    precision = tp / np.maximum(tp + fp, 1)
    recall = tp / tp[-1]
    recall_prev = np.r_[0, recall[:-1]]
    return float(np.sum((recall - recall_prev) * precision))


def calibration_slope_intercept(y: pd.Series, p: pd.Series) -> tuple[float, float]:
    d = pd.DataFrame({"y": y, "p": p}).dropna()
    if len(d) < 3 or d["p"].std(ddof=0) == 0:
        return np.nan, np.nan
    X = np.column_stack([np.ones(len(d)), d["p"].to_numpy(dtype=float)])
    beta = np.linalg.pinv(X.T @ X) @ (X.T @ d["y"].to_numpy(dtype=float))
    return float(beta[0]), float(beta[1])


def regression_metrics(d: pd.DataFrame, y_col: str = "y_true", p_col: str = "y_pred") -> dict:
    y = d[y_col].to_numpy(dtype=float)
    p = d[p_col].to_numpy(dtype=float)
    err = p - y
    denom = np.sum((y - np.mean(y)) ** 2)
    intercept, slope = calibration_slope_intercept(d[y_col], d[p_col])
    return {
        "n": int(len(d)),
        "n_subjects": int(d["subject_id"].nunique()) if "subject_id" in d.columns else np.nan,
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(np.sqrt(np.mean(err**2))),
        "R2": float(1 - np.sum(err**2) / denom) if denom > 0 else np.nan,
        "mean_signed_error": float(np.mean(err)),
        "calibration_intercept": intercept,
        "calibration_slope": slope,
    }


def effect_ci_text(row: pd.Series, digits: int = 3) -> str:
    return f"{row['estimate']:.{digits}f} ({row['ci_low']:.{digits}f}, {row['ci_high']:.{digits}f})"


def md_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    """Small dependency-free markdown table renderer."""
    if df is None or df.empty:
        return "_No rows._"
    d = df.copy()
    if max_rows is not None:
        d = d.head(max_rows)
    cols = list(d.columns)

    def fmt(v) -> str:
        if pd.isna(v):
            return ""
        if isinstance(v, (float, np.floating)):
            return f"{float(v):.4g}"
        return str(v).replace("\n", " ")

    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(fmt(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def load_cg_meal() -> pd.DataFrame:
    return pd.read_csv(STAGE1 / "cgmacros_meal_level_with_msi_core.csv")


def load_nhanes_raw() -> pd.DataFrame:
    return pd.read_csv(NHANES_ROOT / "output" / "NHANES_2013_2018_master_analysis_DEHPderived.csv")


def load_nhanes_stage1() -> pd.DataFrame:
    return pd.read_csv(STAGE1 / "nhanes_2013_2018_msi_core.csv")


def compute_msi_versions(df: pd.DataFrame, pca_weights: pd.Series | None = None) -> pd.DataFrame:
    out = df.copy()
    zcols = [c for c in COMPONENT_Z if c in out.columns]
    out["msi_core_partial"] = pd.to_numeric(out.get("msi_core_partial_nhanes_ref"), errors="coerce")
    out["msi_core_complete"] = pd.to_numeric(out.get("msi_core_complete_nhanes_ref"), errors="coerce")
    out["msi_ranknorm"] = pd.to_numeric(out.get("msi_core_ranknorm_within_dataset"), errors="coerce")
    out["msi_no_bmi"] = out[[c for c in zcols if c != "bmi_z_nhanes_ref"]].mean(axis=1, skipna=True)
    out.loc[out[[c for c in zcols if c != "bmi_z_nhanes_ref"]].notna().sum(axis=1) < 3, "msi_no_bmi"] = np.nan
    out["msi_glycemia_ir"] = out[
        ["hba1c_z_nhanes_ref", "fasting_glucose_mgdl_z_nhanes_ref", "ln_homa_ir_z_nhanes_ref"]
    ].mean(axis=1, skipna=True)
    out.loc[
        out[["hba1c_z_nhanes_ref", "fasting_glucose_mgdl_z_nhanes_ref", "ln_homa_ir_z_nhanes_ref"]].notna().sum(axis=1)
        < 2,
        "msi_glycemia_ir",
    ] = np.nan
    out["msi_ir_lipid"] = out[["ln_homa_ir_z_nhanes_ref", "ln_tg_hdl_z_nhanes_ref"]].mean(axis=1, skipna=True)
    out.loc[out[["ln_homa_ir_z_nhanes_ref", "ln_tg_hdl_z_nhanes_ref"]].notna().sum(axis=1) < 2, "msi_ir_lipid"] = np.nan
    out["homa_ir_single"] = pd.to_numeric(out.get("ln_homa_ir_z_nhanes_ref"), errors="coerce")
    out["tg_hdl_single"] = pd.to_numeric(out.get("ln_tg_hdl_z_nhanes_ref"), errors="coerce")
    if pca_weights is not None:
        weighted_sum = pd.Series(0.0, index=out.index)
        weight_abs = pd.Series(0.0, index=out.index)
        for col, weight in pca_weights.items():
            vals = pd.to_numeric(out[col], errors="coerce")
            mask = vals.notna()
            weighted_sum.loc[mask] += vals.loc[mask] * weight
            weight_abs.loc[mask] += abs(weight)
        out["msi_pca"] = weighted_sum / weight_abs.replace(0, np.nan)
    return out


def pca_weights_from_nhanes(nh: pd.DataFrame) -> pd.Series:
    zcols = [c for c in COMPONENT_Z if c in nh.columns]
    z = nh[zcols].dropna()
    if len(z) < 20:
        return pd.Series({c: 1 / len(zcols) for c in zcols})
    mat = z.to_numpy(dtype=float)
    cov = np.cov(mat, rowvar=False)
    vals, vecs = np.linalg.eigh(cov)
    w = vecs[:, int(np.argmax(vals))]
    if np.nansum(w) < 0:
        w = -w
    w = w / np.sum(np.abs(w))
    return pd.Series(w, index=zcols)


def phase0_protocol() -> None:
    out = OUT_ROOT / "phase0_protocol"
    ensure_dir(out)
    registry = pd.DataFrame(
        [
            {
                "analysis_id": "P0-H1",
                "claim_level": "primary",
                "question": "NHANES 中 DEHP oxidative profile 是否与 MSI-core/insulin-resistance phenotype 相关",
                "primary_dataset": "NHANES 2013-2018",
                "primary_outputs": "Phase 2 survey-ready models",
            },
            {
                "analysis_id": "P0-H2",
                "claim_level": "primary",
                "question": "CGMacros 中 MSI-core 是否预测更高 PPGR vulnerability",
                "primary_dataset": "CGMacros",
                "primary_outputs": "Phase 3 robust repeated-meal inference",
            },
            {
                "analysis_id": "P0-H3",
                "claim_level": "secondary",
                "question": "MSI-aware 模型是否改善 high-response detection、calibration 或 few-shot personalization",
                "primary_dataset": "CGMacros",
                "primary_outputs": "Phase 4 nested leave-subject-out prediction",
            },
            {
                "analysis_id": "P0-H4",
                "claim_level": "boundary/mechanistic support",
                "question": "外部 CGM 数据是否支持 PPGR heterogeneity 和模型适用边界",
                "primary_dataset": "Stanford CGMDB; T1D-UOM; Jaeb CGMND",
                "primary_outputs": "Phase 5 external validation",
            },
        ]
    )
    write_csv(out / "phase0_analysis_registry.csv", registry)
    sap = """
    # Phase 0: Integrated Statistical Analysis Plan v1

    日期：2026-06-10

    ## 冻结后的主线

    DEHP oxidative profile -> MSI-core metabolic susceptibility -> PPGR vulnerability -> digestion-informed meal redesign.

    这条主线使用 MSI-core 作为跨项目桥梁。NHANES 负责上游人群暴露-代谢易感性证据；CGMacros 负责餐食级动态血糖脆弱性；外部 CGM 数据只作为边界验证；陈晓东教授体外消化仿生系统负责后续机制和干预验证。

    ## Primary hypotheses

    1. NHANES 中 `%Oxidative` 或 `ln(Oxidative/MEHP)` 与 MSI-core、ln(HOMA-IR)、HbA1c 等 insulin-resistant metabolic susceptibility 表型正相关。
    2. CGMacros 中 MSI-core 与更高 2h iAUC、2h peak delta 和 high-response risk 相关。
    3. MSI-aware prediction 至少在 high-response detection、calibration 或 few-shot personalization 中体现增益。

    ## Secondary hypotheses

    1. `meal load x MSI` 的方向应为正，但若不显著，主张降级为 susceptibility stratification。
    2. 外部 CGM 数据不要求复制 MSI 机制，只用于证明 PPGR heterogeneity 和疾病状态边界。
    3. 仿生消化实验的正式湿实验不在本计算阶段内；本阶段只完成候选餐食 QC、方案和数据结构准备。

    ## Main analysis sets

    - NHANES: 2013-2018 with phthalate subsample weights; current workstation lacks R, so Phase 2 produces a Python weighted/clustered approximation and a formal R `survey` script for final rerun.
    - CGMacros: meal-level dataset with 40 subjects and repeated meals; all inference must respect subject clustering or subject bootstrap.
    - External CGM: Stanford CGMDB food challenge as the main boundary dataset; T1D-UOM as disease-state meal-CGM boundary; Jaeb CGMND as healthy-CGM phenotype reference.

    ## Primary outcomes

    - NHANES: MSI-core, ln(HOMA-IR), HbA1c, TyG, ln(TG/HDL-C).
    - CGMacros: 2h iAUC, 2h peak delta, high-response meals.
    - Prediction: MAE/RMSE, calibration slope/intercept, high-response AUC/AUPRC, conformal interval coverage.
    - External: challenge/meal iAUC, peak delta, within-food/within-disease heterogeneity.

    ## Multiplicity and sensitivity

    Main results prioritize direction, effect size, confidence interval, and FDR q-values. Sensitivity analyses include alternative MSI definitions, exclusion of diabetes history, load-variable alternatives, subject bootstrap, and leave-one-subject-out influence.
    """
    no_overclaim = """
    # Phase 0: Main Claims and No-Overclaim Rules

    ## 可以主张

    - NHANES 中 DEHP oxidative profile 与 insulin-resistant metabolic susceptibility 相关。
    - CGMacros 中同一 MSI-core 表型表现为更高 PPGR vulnerability。
    - MSI 可作为 PPGR 风险分层变量，并可用于改进个体化预测/校准的评估。
    - 外部 CGM 数据用于说明 PPGR 异质性和适用边界。

    ## 不能主张

    - 不能说 DEHP 直接导致 CGMacros 受试者 PPGR 升高。
    - 不能说当前计算阶段已经证明仿生消化机制；目前只有设计和候选餐食 QC。
    - 如果 `meal load x MSI` 不显著，不能把 effect modification 写成确定结论。
    - 不能把 T1D/T2D 外部数据当作健康 CGMacros 人群的直接重复验证。

    ## 投稿语言模板

    推荐表述：

    > DEHP oxidative profile was associated with an insulin-resistant metabolic susceptibility phenotype in NHANES; the same susceptibility phenotype was expressed as higher postprandial glycemic vulnerability in CGMacros.

    避免表述：

    > DEHP exposure caused higher PPGR in CGMacros participants.
    """
    report = """
    # Phase 0 完成报告

    已冻结主线、主要假设、次要假设、分析集和禁止过度解释规则。后续 Phase 1-5 的所有计算结果都应服务于同一条证据链，而不是继续扩散为多个松散论文。
    """
    write_text(out / "phase0_statistical_analysis_plan_v1.md", sap)
    write_text(out / "phase0_main_claims_and_no_overclaim_rules.md", no_overclaim)
    write_text(out / "phase0_report_2026-06-10.md", report)


def phase1_qc_msi_sensitivity() -> tuple[pd.DataFrame, pd.DataFrame]:
    out = OUT_ROOT / "phase1_qc_msi_sensitivity"
    ensure_dir(out)
    cg_meal = load_cg_meal()
    nh_stage1 = load_nhanes_stage1()
    raw = load_nhanes_raw()

    weights = pca_weights_from_nhanes(nh_stage1)
    cg = compute_msi_versions(cg_meal, weights)
    nh = compute_msi_versions(nh_stage1, weights)
    nh = nh.merge(
        raw[
            [
                "SEQN",
                "ln_Sigma_DEHP",
                "pct_oxidative_10",
                "ln_oxidative_to_MEHP",
                "RIDAGEYR",
                "RIAGENDR",
                "RIDRETH3",
                "DMDEDUC2",
                "INDFMPIR",
                "DR1TKCAL",
                "ever_smoker",
                "alcohol_ever",
                "any_physical_activity",
                "ln_URXUCR",
                "cycle",
                "WTSB6YR_MAIN",
                "SDMVPSU",
                "SDMVSTRA",
                "ln_HOMA_IR",
                "HbA1c",
                "TyG",
                "ln_TG_HDL",
                "diabetes_history",
            ]
        ],
        on="SEQN",
        how="left",
        suffixes=("", "_raw"),
    )
    # Keep canonical names stable when Stage 1 and raw NHANES both contain
    # helper variables such as pct_oxidative_10 or cycle.
    for col in ["pct_oxidative_10", "cycle"]:
        raw_col = f"{col}_raw"
        if col not in nh.columns and raw_col in nh.columns:
            nh[col] = nh[raw_col]
    nh["cluster"] = nh["SDMVSTRA"].astype(str) + "_" + nh["SDMVPSU"].astype(str)

    msi_versions = [
        "msi_core_partial",
        "msi_core_complete",
        "msi_ranknorm",
        "msi_no_bmi",
        "msi_glycemia_ir",
        "msi_ir_lipid",
        "msi_pca",
        "homa_ir_single",
        "tg_hdl_single",
    ]
    write_csv(out / "phase1_msi_pca_component_weights.csv", weights.reset_index().rename(columns={"index": "component", 0: "weight"}))

    cg_subject = (
        cg.sort_values("meal_time")
        .groupby("subject_id", as_index=False)
        .agg({v: "first" for v in msi_versions if v in cg.columns})
    )
    nh_keep = ["SEQN"] + [v for v in msi_versions if v in nh.columns]
    write_csv(out / "phase1_msi_sensitivity_subjects_cgmacros.csv", cg_subject)
    write_csv(out / "phase1_msi_sensitivity_nhanes.csv", nh[nh_keep])

    corr_rows = []
    for dataset, table, id_col in [("CGMacros", cg_subject, "subject_id"), ("NHANES", nh, "SEQN")]:
        for i, a in enumerate(msi_versions):
            for b in msi_versions[i + 1 :]:
                if a in table.columns and b in table.columns:
                    corr_rows.append(
                        {
                            "dataset": dataset,
                            "msi_a": a,
                            "msi_b": b,
                            "n_pairwise": int(table[[a, b]].dropna().shape[0]),
                            "pearson": pearson(table[a], table[b]),
                            "spearman": spearman(table[a], table[b]),
                        }
                    )
    corr = pd.DataFrame(corr_rows)
    write_csv(out / "phase1_msi_version_correlations.csv", corr)

    # CGMacros MSI -> PPGR sensitivity.
    cg["carbs_10g"] = winsorize(cg["carbs"]) / 10.0
    cg["baseline_glucose_z"] = zscore(cg["baseline_glucose"])
    cg["iauc_2h_per1000"] = cg["iauc_2h"] / 1000.0
    ppgr_rows = []
    for msi in msi_versions:
        if msi not in cg.columns:
            continue
        tmp = cg.copy()
        tmp["msi_centered"] = tmp[msi] - tmp[msi].mean(skipna=True)
        tmp["carbs_x_msi"] = tmp["carbs_10g"] * tmp["msi_centered"]
        for outcome, label in [("iauc_2h_per1000", "2h iAUC / 1000"), ("peak_delta_2h", "2h peak delta")]:
            X, y, w, clusters = make_design(
                tmp,
                outcome,
                ["carbs_10g", "msi_centered", "carbs_x_msi", "baseline_glucose_z", "meal_hour_sin", "meal_hour_cos"],
                cluster_col="subject_id",
            )
            res = fit_linear_cluster(X, y, clusters, w)
            res = res.loc[res["term"].isin(["msi_centered", "carbs_x_msi"])].copy()
            res.insert(0, "msi_version", msi)
            res.insert(1, "outcome", outcome)
            res.insert(2, "outcome_label", label)
            ppgr_rows.append(res)
    ppgr = pd.concat(ppgr_rows, ignore_index=True)
    ppgr["q_value"] = bh_fdr(ppgr["p_value"])
    ppgr["estimate_CI"] = ppgr.apply(effect_ci_text, axis=1)
    write_csv(out / "phase1_msi_ppgr_sensitivity_models.csv", ppgr)

    # NHANES exposure -> alternative MSI sensitivity.
    cov_cont = ["RIDAGEYR", "INDFMPIR", "DR1TKCAL", "ln_URXUCR"]
    cov_cat = ["RIAGENDR", "RIDRETH3", "DMDEDUC2", "ever_smoker", "alcohol_ever", "any_physical_activity", "cycle"]
    exposure_rows = []
    for msi in ["msi_core_partial", "msi_core_complete", "msi_no_bmi", "msi_glycemia_ir", "msi_pca", "homa_ir_single"]:
        if msi not in nh.columns:
            continue
        for exposure in ["pct_oxidative_10", "ln_oxidative_to_MEHP", "ln_Sigma_DEHP"]:
            predictors = [exposure] + cov_cont
            X, y, w, clusters = make_design(
                nh,
                msi,
                predictors,
                categorical=cov_cat,
                weight_col="WTSB6YR_MAIN",
                cluster_col="cluster",
                standardize_predictors=set(cov_cont),
            )
            res = fit_linear_cluster(X, y, clusters, w)
            row = res.loc[res["term"] == exposure].iloc[0].to_dict()
            row.update({"outcome_msi_version": msi, "exposure": exposure})
            exposure_rows.append(row)
    nh_sens = pd.DataFrame(exposure_rows)
    nh_sens["q_value"] = bh_fdr(nh_sens["p_value"])
    nh_sens["estimate_CI"] = nh_sens.apply(effect_ci_text, axis=1)
    write_csv(out / "phase1_nhanes_msi_exposure_sensitivity_models.csv", nh_sens)

    # Candidate meal QC for bionic digestion.
    cand = pd.read_csv(STAGE5 / "stage5_candidate_meals_for_bionic_digestion.csv")
    qc_rows = []
    for _, r in cand.iterrows():
        sid = int(r["subject_id"])
        rel_img = str(r.get("image_path", ""))
        filename = Path(rel_img).name
        abs_img = ROOT / "data" / "raw" / "CGMacros" / f"CGMacros-{sid:03d}" / "photos" / filename
        calories = pd.to_numeric(pd.Series([r.get("calories")]), errors="coerce").iloc[0]
        carbs = pd.to_numeric(pd.Series([r.get("carbs")]), errors="coerce").iloc[0]
        protein = pd.to_numeric(pd.Series([r.get("protein")]), errors="coerce").iloc[0]
        fat = pd.to_numeric(pd.Series([r.get("fat")]), errors="coerce").iloc[0]
        fiber = pd.to_numeric(pd.Series([r.get("fiber")]), errors="coerce").iloc[0]
        macro_kcal = carbs * 4 + protein * 4 + fat * 9 if all(np.isfinite([carbs, protein, fat])) else np.nan
        kcal_ratio = calories / macro_kcal if np.isfinite(macro_kcal) and macro_kcal > 0 and np.isfinite(calories) else np.nan
        plausible = (
            np.isfinite(calories)
            and 50 <= calories <= 2000
            and np.isfinite(carbs)
            and 1 <= carbs <= 200
            and np.isfinite(protein)
            and 0 <= protein <= 160
            and np.isfinite(fat)
            and 0 <= fat <= 160
            and np.isfinite(fiber)
            and 0 <= fiber <= 80
            and (not np.isfinite(kcal_ratio) or 0.45 <= kcal_ratio <= 2.20)
        )
        qc_rows.append(
            {
                **r.to_dict(),
                "image_absolute_path": str(abs_img),
                "image_exists": bool(abs_img.exists()),
                "macro_kcal_calculated": macro_kcal,
                "calorie_to_macro_kcal_ratio": kcal_ratio,
                "macro_plausible": bool(plausible),
                "zero_fiber_flag": bool(np.isfinite(fiber) and fiber <= 0),
                "needs_manual_recipe_qc": bool((not abs_img.exists()) or (not plausible) or (np.isfinite(fiber) and fiber <= 0)),
            }
        )
    qc = pd.DataFrame(qc_rows)
    duplicate_cols = ["calories", "carbs", "protein", "fat", "fiber"]
    dup_counts = qc.groupby(duplicate_cols, dropna=False)["candidate_id"].transform("count")
    qc["duplicate_macro_fingerprint_count"] = dup_counts
    qc.loc[qc["duplicate_macro_fingerprint_count"] > 2, "needs_manual_recipe_qc"] = True
    write_csv(out / "phase1_candidate_meal_qc.csv", qc)
    qc_summary = pd.DataFrame(
        [
            {"metric": "candidate_meals", "value": len(qc)},
            {"metric": "images_found", "value": int(qc["image_exists"].sum())},
            {"metric": "macro_plausible", "value": int(qc["macro_plausible"].sum())},
            {"metric": "zero_fiber_flag", "value": int(qc["zero_fiber_flag"].sum())},
            {"metric": "needs_manual_recipe_qc", "value": int(qc["needs_manual_recipe_qc"].sum())},
            {"metric": "duplicate_macro_fingerprint_gt2", "value": int((qc["duplicate_macro_fingerprint_count"] > 2).sum())},
        ]
    )
    write_csv(out / "phase1_candidate_meal_qc_summary.csv", qc_summary)

    top_nh = nh_sens.sort_values("p_value").head(5)
    top_ppgr = ppgr.sort_values("p_value").head(5)
    report = f"""
    # Phase 1 完成报告：数据质量与 MSI 稳健性

    ## 已完成

    - 构建 9 个 MSI 敏感性版本：partial、complete、ranknorm、without BMI、glycemia/IR、IR/lipid、PCA、HOMA 单指标、TG/HDL 单指标。
    - 计算 NHANES 与 CGMacros 中 MSI 版本之间的 Pearson/Spearman 相关。
    - 在 CGMacros 中复核各 MSI 版本与 PPGR 的关联。
    - 在 NHANES 中复核各 MSI 版本与 DEHP oxidative profile 的关联。
    - 对 Stage 5 体外消化候选餐食做图片存在性、宏量营养合理性、0 纤维、重复宏量指纹 QC。

    ## 关键发现

    - PCA MSI 权重已保存到 `phase1_msi_pca_component_weights.csv`。
    - CGMacros/NHANES 的 MSI 版本高度相关性与模型结果见 `phase1_msi_version_correlations.csv`、`phase1_msi_ppgr_sensitivity_models.csv`、`phase1_nhanes_msi_exposure_sensitivity_models.csv`。
    - 体外消化候选餐食中，需要人工复核的候选数：{int(qc['needs_manual_recipe_qc'].sum())}/{len(qc)}；图片找到 {int(qc['image_exists'].sum())}/{len(qc)}；0 纤维候选 {int(qc['zero_fiber_flag'].sum())}/{len(qc)}。

    ## NHANES MSI 敏感性中最强的 5 个关联

    {md_table(top_nh[['outcome_msi_version','exposure','estimate_CI','p_value','q_value','n']])}

    ## CGMacros MSI-PPGR 敏感性中最强的 5 个关联

    {md_table(top_ppgr[['msi_version','outcome_label','term','estimate_CI','p_value','q_value','n']])}

    ## 投稿含义

    MSI 桥梁变量不是只依赖单一构造方式；后续主文可以用 `MSI-core partial NHANES-ref` 作为主版本，并把 PCA、without-BMI、ranknorm、单指标版本放入补充材料。Stage 5 候选餐食必须先做人工图片/配方复核，尤其是 0 纤维和重复宏量指纹候选。
    """
    write_text(out / "phase1_qc_msi_sensitivity_report_2026-06-10.md", report)
    return cg, nh


def phase2_nhanes_survey_ready(nh: pd.DataFrame) -> pd.DataFrame:
    out = OUT_ROOT / "phase2_nhanes_survey_ready"
    ensure_dir(out)
    raw = load_nhanes_raw()
    if "msi_core_partial" not in nh.columns:
        nh = compute_msi_versions(nh, pca_weights_from_nhanes(load_nhanes_stage1()))
    df = nh.copy()
    df["cluster"] = df["SDMVSTRA"].astype(str) + "_" + df["SDMVPSU"].astype(str)
    df["weight"] = pd.to_numeric(df["WTSB6YR_MAIN"], errors="coerce")
    if "BMXBMI" not in df.columns and "bmi" in df.columns:
        df["BMXBMI"] = df["bmi"]

    r_script = f'''
    # Formal NHANES survey script for final manuscript rerun.
    # Generated on {TODAY}. This workstation currently has no Rscript, so this
    # script is prepared for execution in an R environment with survey installed.

    library(survey)
    options(survey.lonely.psu = "adjust")

    nh <- read.csv("{(out / 'phase2_python_analysis_dataset.csv').as_posix()}")
    nh$cluster <- interaction(nh$SDMVSTRA, nh$SDMVPSU, drop = TRUE)
    des <- svydesign(
      ids = ~SDMVPSU,
      strata = ~SDMVSTRA,
      weights = ~WTSB6YR_MAIN,
      nest = TRUE,
      data = nh
    )

    main_covars <- "RIDAGEYR + factor(RIAGENDR) + factor(RIDRETH3) + factor(DMDEDUC2) + INDFMPIR + DR1TKCAL + ever_smoker + alcohol_ever + any_physical_activity + ln_URXUCR + factor(cycle)"
    outcomes <- c("msi_core_partial", "msi_no_bmi", "msi_pca", "ln_HOMA_IR", "HbA1c", "TyG", "ln_TG_HDL")
    exposures <- c("pct_oxidative_10", "ln_oxidative_to_MEHP", "ln_Sigma_DEHP")

    rows <- list()
    k <- 1
    for (y in outcomes) {{
      for (x in exposures) {{
        f <- as.formula(paste(y, "~", x, "+", main_covars))
        m <- svyglm(f, design = des)
        co <- coef(summary(m))[x, ]
        rows[[k]] <- data.frame(outcome = y, exposure = x, beta = co[1], se = co[2], t = co[3], p = co[4])
        k <- k + 1
      }}
    }}
    res <- do.call(rbind, rows)
    res$q <- p.adjust(res$p, method = "BH")
    write.csv(res, "{(out / 'phase2_R_survey_main_results.csv').as_posix()}", row.names = FALSE)
    '''
    write_text(out / "phase2_formal_R_survey_script.R", r_script)

    keep_cols = [
        "SEQN",
        "SDMVPSU",
        "SDMVSTRA",
        "WTSB6YR_MAIN",
        "RIDAGEYR",
        "RIAGENDR",
        "RIDRETH3",
        "DMDEDUC2",
        "INDFMPIR",
        "DR1TKCAL",
        "ever_smoker",
        "alcohol_ever",
        "any_physical_activity",
        "ln_URXUCR",
        "cycle",
        "diabetes_history",
        "BMXBMI",
        "ln_Sigma_DEHP",
        "pct_oxidative_10",
        "ln_oxidative_to_MEHP",
        "ln_HOMA_IR",
        "HbA1c",
        "TyG",
        "ln_TG_HDL",
        "msi_core_partial",
        "msi_core_complete",
        "msi_no_bmi",
        "msi_glycemia_ir",
        "msi_pca",
        "homa_ir_single",
    ]
    analysis = df[[c for c in keep_cols if c in df.columns]].copy()
    write_csv(out / "phase2_python_analysis_dataset.csv", analysis)

    # Weighted Table 1 by oxidative quartile.
    q = weighted_quantile(analysis["pct_oxidative_10"], analysis["WTSB6YR_MAIN"], [0.25, 0.50, 0.75])
    analysis["oxidative_quartile"] = pd.cut(
        analysis["pct_oxidative_10"],
        bins=[-np.inf, q[0], q[1], q[2], np.inf],
        labels=["Q1", "Q2", "Q3", "Q4"],
    )
    table_rows = []
    cont_vars = {
        "RIDAGEYR": "Age",
        "BMXBMI": "BMI",
        "HbA1c": "HbA1c",
        "ln_HOMA_IR": "ln(HOMA-IR)",
        "msi_core_partial": "MSI-core",
        "pct_oxidative_10": "%Oxidative/10",
    }
    for quartile, d in analysis.groupby("oxidative_quartile", dropna=False):
        table_rows.append({"quartile": quartile, "variable": "Unweighted n", "statistic": "n", "value": len(d)})
        table_rows.append(
            {
                "quartile": quartile,
                "variable": "Weighted n proxy",
                "statistic": "sum_weight",
                "value": float(pd.to_numeric(d["WTSB6YR_MAIN"], errors="coerce").sum()),
            }
        )
        for c, label in cont_vars.items():
            table_rows.append(
                {
                    "quartile": quartile,
                    "variable": label,
                    "statistic": "weighted_mean",
                    "value": weighted_mean(d[c], d["WTSB6YR_MAIN"]),
                }
            )
        for c, label, positive in [
            ("RIAGENDR", "Female", 2),
            ("ever_smoker", "Ever smoker", 1),
            ("diabetes_history", "Diabetes history", 1),
        ]:
            mask = pd.to_numeric(d[c], errors="coerce") == positive
            table_rows.append(
                {
                    "quartile": quartile,
                    "variable": label,
                    "statistic": "weighted_percent",
                    "value": 100 * weighted_mean(mask.astype(float), d["WTSB6YR_MAIN"]),
                }
            )
    table1 = pd.DataFrame(table_rows)
    write_csv(out / "phase2_weighted_table1_by_oxidative_quartile.csv", table1)

    cov_cont_full = ["RIDAGEYR", "INDFMPIR", "DR1TKCAL", "ln_URXUCR"]
    cov_cat_full = ["RIAGENDR", "RIDRETH3", "DMDEDUC2", "ever_smoker", "alcohol_ever", "any_physical_activity", "cycle"]
    cov_cont_min = ["RIDAGEYR", "ln_URXUCR"]
    cov_cat_min = ["RIAGENDR", "RIDRETH3", "cycle"]
    outcomes = {
        "msi_core_partial": "MSI-core",
        "msi_no_bmi": "MSI no BMI",
        "msi_pca": "MSI PCA",
        "ln_HOMA_IR": "ln(HOMA-IR)",
        "HbA1c": "HbA1c",
        "TyG": "TyG",
        "ln_TG_HDL": "ln(TG/HDL-C)",
    }
    exposures = {
        "pct_oxidative_10": "%Oxidative per 10 pp",
        "ln_oxidative_to_MEHP": "ln(Oxidative/MEHP)",
        "ln_Sigma_DEHP": "ln(Sigma DEHP)",
    }
    rows = []
    for outcome, outcome_label in outcomes.items():
        if outcome not in analysis.columns:
            continue
        for exposure, exposure_label in exposures.items():
            predictors = [exposure] + cov_cont_full
            X, y, w, clusters = make_design(
                analysis,
                outcome,
                predictors,
                categorical=cov_cat_full,
                weight_col="WTSB6YR_MAIN",
                cluster_col="cluster" if "cluster" in analysis.columns else None,
                standardize_predictors=set(cov_cont_full),
            )
            if "cluster" not in analysis.columns:
                clusters = (analysis["SDMVSTRA"].astype(str) + "_" + analysis["SDMVPSU"].astype(str)).loc[y.index]
            res = fit_linear_cluster(X, y, clusters, w)
            r = res.loc[res["term"] == exposure].iloc[0].to_dict()
            r.update(
                {
                    "model_set": "full_python_weighted_cluster",
                    "outcome": outcome,
                    "outcome_label": outcome_label,
                    "exposure": exposure,
                    "exposure_label": exposure_label,
                }
            )
            rows.append(r)
    main = pd.DataFrame(rows)
    main["q_value"] = bh_fdr(main["p_value"])
    main["estimate_CI"] = main.apply(effect_ci_text, axis=1)
    write_csv(out / "phase2_nhanes_python_weighted_cluster_main_results.csv", main)

    sens_rows = []
    for model_set, cov_cont, cov_cat, subset_expr in [
        ("minimal_covariates", cov_cont_min, cov_cat_min, None),
        ("full_covariates", cov_cont_full, cov_cat_full, None),
        ("exclude_diabetes_history", cov_cont_full, cov_cat_full, "exclude_diabetes"),
        ("non_obese_subset", cov_cont_full, cov_cat_full, "non_obese"),
    ]:
        dat = analysis.copy()
        if subset_expr == "exclude_diabetes":
            dat = dat.loc[pd.to_numeric(dat["diabetes_history"], errors="coerce") != 1].copy()
        elif subset_expr == "non_obese":
            dat = dat.loc[pd.to_numeric(dat["BMXBMI"], errors="coerce") < 30].copy()
        dat["cluster"] = dat["SDMVSTRA"].astype(str) + "_" + dat["SDMVPSU"].astype(str)
        for outcome in ["msi_core_partial", "msi_no_bmi", "ln_HOMA_IR", "HbA1c"]:
            for exposure in ["pct_oxidative_10", "ln_oxidative_to_MEHP"]:
                predictors = [exposure] + cov_cont
                X, y, w, clusters = make_design(
                    dat,
                    outcome,
                    predictors,
                    categorical=cov_cat,
                    weight_col="WTSB6YR_MAIN",
                    cluster_col="cluster",
                    standardize_predictors=set(cov_cont),
                )
                res = fit_linear_cluster(X, y, clusters, w)
                r = res.loc[res["term"] == exposure].iloc[0].to_dict()
                r.update({"model_set": model_set, "outcome": outcome, "exposure": exposure})
                sens_rows.append(r)
    sens = pd.DataFrame(sens_rows)
    sens["q_value"] = bh_fdr(sens["p_value"])
    sens["estimate_CI"] = sens.apply(effect_ci_text, axis=1)
    write_csv(out / "phase2_nhanes_python_sensitivity_results.csv", sens)

    dose_rows = []
    for exposure in ["pct_oxidative_10", "ln_oxidative_to_MEHP", "ln_Sigma_DEHP"]:
        qs = weighted_quantile(analysis[exposure], analysis["WTSB6YR_MAIN"], [0.25, 0.50, 0.75])
        qcol = f"{exposure}_quartile"
        analysis[qcol] = pd.cut(analysis[exposure], [-np.inf, qs[0], qs[1], qs[2], np.inf], labels=[1, 2, 3, 4])
        for outcome in ["msi_core_partial", "ln_HOMA_IR", "HbA1c"]:
            for quartile, d in analysis.groupby(qcol, dropna=False):
                dose_rows.append(
                    {
                        "exposure": exposure,
                        "outcome": outcome,
                        "quartile": quartile,
                        "n": len(d),
                        "weighted_mean_outcome": weighted_mean(d[outcome], d["WTSB6YR_MAIN"]),
                        "weighted_mean_exposure": weighted_mean(d[exposure], d["WTSB6YR_MAIN"]),
                    }
                )
    dose = pd.DataFrame(dose_rows)
    write_csv(out / "phase2_nhanes_dose_response_quartile_summary.csv", dose)

    r_found = shutil.which("Rscript") is not None or shutil.which("R") is not None
    top = main.sort_values("p_value").head(8)
    report = f"""
    # Phase 2 完成报告：NHANES survey-ready 分析

    ## 环境状态

    当前电脑未检测到 R/Rscript：{not r_found}。因此本阶段已完成 Python weighted + cluster-robust 近似分析，并生成正式 R `survey` 脚本 `phase2_formal_R_survey_script.R`，供安装 R 后作为投稿最终版复核。

    ## 已完成的计算输出

    - `phase2_python_analysis_dataset.csv`：已合并 MSI 敏感性版本和 NHANES 协变量。
    - `phase2_weighted_table1_by_oxidative_quartile.csv`：按 `%Oxidative` 四分位的加权基线表。
    - `phase2_nhanes_python_weighted_cluster_main_results.csv`：主模型。
    - `phase2_nhanes_python_sensitivity_results.csv`：minimal/full、排除糖尿病史、非肥胖子集敏感性。
    - `phase2_nhanes_dose_response_quartile_summary.csv`：四分位剂量反应描述。

    ## 最强主模型结果快照

    {md_table(top[['outcome_label','exposure_label','estimate_CI','p_value','q_value','n','n_clusters']])}

    ## 投稿判断

    Python 结果可作为当前主线推进和结果筛选依据，但正式投稿必须用 `phase2_formal_R_survey_script.R` 在 R `survey` 环境中复核。若 R 结果与当前方向一致，NHANES 端可以作为主文 Figure 2 的核心证据。
    """
    write_text(out / "phase2_nhanes_survey_ready_report_2026-06-10.md", report)
    return main


def phase3_cgmacros_robust(cg: pd.DataFrame) -> pd.DataFrame:
    out = OUT_ROOT / "phase3_cgmacros_robust_inference"
    ensure_dir(out)
    df = cg.copy()
    df["carbs_w"] = winsorize(df["carbs"])
    df["protein_w"] = winsorize(df["protein"])
    df["fat_w"] = winsorize(df["fat"])
    df["fiber_w"] = winsorize(df["fiber"])
    df["calories_w"] = winsorize(df["calories"])
    df["carbs_10g"] = df["carbs_w"] / 10
    df["available_carbs_10g"] = np.maximum(df["carbs_w"] - df["fiber_w"], 0) / 10
    df["carb_fiber_ratio_z"] = zscore(df["carbs_w"] / (df["fiber_w"] + 1))
    df["carb_protein_ratio_z"] = zscore(df["carbs_w"] / (df["protein_w"] + 1))
    df["energy_100kcal"] = df["calories_w"] / 100
    df["baseline_glucose_z"] = zscore(df["baseline_glucose"])
    df["msi"] = pd.to_numeric(df["msi_core_partial"], errors="coerce")
    df["msi_centered"] = df["msi"] - df["msi"].mean(skipna=True)
    df["iauc_2h_per1000"] = df["iauc_2h"] / 1000
    df["high_iauc_population"] = (df["iauc_2h"] >= df["iauc_2h"].quantile(0.75)).astype(float)
    df["high_peak_population"] = (df["peak_delta_2h"] >= df["peak_delta_2h"].quantile(0.75)).astype(float)
    df["high_peak_absolute40"] = (df["peak_delta_2h"] >= 40).astype(float)
    subject_q75 = df.groupby("subject_id")["iauc_2h"].transform(lambda x: x.quantile(0.75))
    df["high_iauc_subject_specific"] = (df["iauc_2h"] >= subject_q75).astype(float)

    load_vars = {
        "carbs_10g": "Carbohydrate per 10 g",
        "available_carbs_10g": "Available carbohydrate per 10 g",
        "carb_fiber_ratio_z": "Carb/fiber ratio z",
        "carb_protein_ratio_z": "Carb/protein ratio z",
        "energy_100kcal": "Energy per 100 kcal",
    }
    outcomes = {
        "iauc_2h_per1000": "2h iAUC / 1000",
        "peak_delta_2h": "2h peak delta",
        "high_iauc_population": "High iAUC population Q4",
        "high_iauc_subject_specific": "High iAUC subject-specific Q4",
        "high_peak_population": "High peak population Q4",
        "high_peak_absolute40": "Peak delta >=40 mg/dL",
    }
    rows = []
    for load, load_label in load_vars.items():
        tmp = df.copy()
        tmp["load_x_msi"] = tmp[load] * tmp["msi_centered"]
        for outcome, outcome_label in outcomes.items():
            predictors = [load, "msi_centered", "load_x_msi", "baseline_glucose_z", "meal_hour_sin", "meal_hour_cos"]
            X, y, w, clusters = make_design(tmp, outcome, predictors, cluster_col="subject_id")
            res = fit_linear_cluster(X, y, clusters, w)
            res.insert(0, "outcome", outcome)
            res.insert(1, "outcome_label", outcome_label)
            res.insert(2, "load_variable", load)
            res.insert(3, "load_label", load_label)
            rows.append(res)
    models = pd.concat(rows, ignore_index=True)
    models["q_value"] = bh_fdr(models["p_value"])
    models["estimate_CI"] = models.apply(effect_ci_text, axis=1)
    write_csv(out / "phase3_load_variant_cluster_models.csv", models)

    # Subject bootstrap for primary load and continuous outcomes.
    subjects = df["subject_id"].dropna().unique()
    boot_rows = []
    B = 500
    for outcome in ["iauc_2h_per1000", "peak_delta_2h", "high_iauc_population", "high_peak_population"]:
        estimates = {"carbs_10g": [], "msi_centered": [], "load_x_msi": []}
        for _ in range(B):
            sampled = RNG.choice(subjects, size=len(subjects), replace=True)
            parts = []
            for draw_id, sid in enumerate(sampled):
                block = df.loc[df["subject_id"] == sid].copy()
                block["boot_cluster"] = f"{sid}_{draw_id}"
                parts.append(block)
            bd = pd.concat(parts, ignore_index=True)
            bd["load_x_msi"] = bd["carbs_10g"] * bd["msi_centered"]
            try:
                X, y, w, clusters = make_design(
                    bd,
                    outcome,
                    ["carbs_10g", "msi_centered", "load_x_msi", "baseline_glucose_z", "meal_hour_sin", "meal_hour_cos"],
                    cluster_col="boot_cluster",
                )
                res = fit_linear_cluster(X, y, clusters, w)
                for term in estimates:
                    estimates[term].append(float(res.loc[res["term"] == term, "estimate"].iloc[0]))
            except Exception:
                continue
        for term, vals in estimates.items():
            arr = np.array(vals, dtype=float)
            arr = arr[np.isfinite(arr)]
            boot_rows.append(
                {
                    "outcome": outcome,
                    "term": term,
                    "B_success": len(arr),
                    "boot_mean": float(np.mean(arr)) if len(arr) else np.nan,
                    "boot_ci_low": float(np.quantile(arr, 0.025)) if len(arr) else np.nan,
                    "boot_ci_high": float(np.quantile(arr, 0.975)) if len(arr) else np.nan,
                    "positive_probability": float(np.mean(arr > 0)) if len(arr) else np.nan,
                }
            )
    boot = pd.DataFrame(boot_rows)
    write_csv(out / "phase3_subject_bootstrap_key_terms.csv", boot)

    influence_rows = []
    for sid in subjects:
        ld = df.loc[df["subject_id"] != sid].copy()
        ld["load_x_msi"] = ld["carbs_10g"] * ld["msi_centered"]
        for outcome in ["iauc_2h_per1000", "peak_delta_2h"]:
            X, y, w, clusters = make_design(
                ld,
                outcome,
                ["carbs_10g", "msi_centered", "load_x_msi", "baseline_glucose_z", "meal_hour_sin", "meal_hour_cos"],
                cluster_col="subject_id",
            )
            res = fit_linear_cluster(X, y, clusters, w)
            for term in ["carbs_10g", "msi_centered", "load_x_msi"]:
                r = res.loc[res["term"] == term].iloc[0]
                influence_rows.append(
                    {
                        "left_out_subject": sid,
                        "outcome": outcome,
                        "term": term,
                        "estimate": r["estimate"],
                        "se": r["se"],
                        "p_value": r["p_value"],
                        "n": r["n"],
                        "n_clusters": r["n_clusters"],
                    }
                )
    influence = pd.DataFrame(influence_rows)
    write_csv(out / "phase3_leave_one_subject_influence.csv", influence)

    subj = (
        df.groupby("subject_id", as_index=False)
        .agg(
            msi=("msi", "first"),
            msi_tertile=("msi_core_tertile_within_dataset", "first"),
            n_meals=("iauc_2h", "size"),
            median_iauc_2h=("iauc_2h", "median"),
            mean_iauc_2h=("iauc_2h", "mean"),
            median_peak_delta_2h=("peak_delta_2h", "median"),
            mean_peak_delta_2h=("peak_delta_2h", "mean"),
            high_iauc_rate=("high_iauc_population", "mean"),
            high_peak_rate=("high_peak_population", "mean"),
            median_carbs=("carbs", "median"),
        )
        .sort_values("msi")
    )
    write_csv(out / "phase3_subject_level_ppgr_msi_summary.csv", subj)

    high_def = []
    for high_col in ["high_iauc_population", "high_iauc_subject_specific", "high_peak_population", "high_peak_absolute40"]:
        for tertile, d in df.groupby("msi_core_tertile_within_dataset"):
            high_def.append(
                {
                    "definition": high_col,
                    "msi_tertile": tertile,
                    "n_meals": len(d),
                    "n_subjects": d["subject_id"].nunique(),
                    "high_rate": float(d[high_col].mean()),
                }
            )
    high_def_df = pd.DataFrame(high_def)
    write_csv(out / "phase3_high_response_definition_sensitivity.csv", high_def_df)

    primary = models.loc[
        (models["load_variable"] == "carbs_10g")
        & (models["outcome"].isin(["iauc_2h_per1000", "peak_delta_2h"]))
        & (models["term"].isin(["carbs_10g", "msi_centered", "load_x_msi"]))
    ].copy()
    report = f"""
    # Phase 3 完成报告：CGMacros 稳健重复测量推断

    ## 已完成

    - 对 5 种 meal load 定义运行 subject-clustered OLS/LPM：carbs、available carbs、carb/fiber ratio、carb/protein ratio、energy。
    - 对 6 类结局运行模型：iAUC、peak、population high response、subject-specific high response、peak high response、absolute peak>=40。
    - 对 primary carbs model 做 500 次 subject bootstrap。
    - 做 leave-one-subject-out influence analysis。
    - 生成 subject-level MSI-PPGR summary，避免只依赖餐食级 p 值。

    ## Primary carbs model 快照

    {md_table(primary[['outcome_label','term','estimate_CI','p_value','q_value','n','n_clusters']])}

    ## Subject-level 关联

    - MSI 与 subject median iAUC Spearman: {spearman(subj['msi'], subj['median_iauc_2h']):.3f}
    - MSI 与 subject high iAUC rate Spearman: {spearman(subj['msi'], subj['high_iauc_rate']):.3f}
    - MSI 与 subject median peak delta Spearman: {spearman(subj['msi'], subj['median_peak_delta_2h']):.3f}

    ## 投稿判断

    如果 `msi_centered` 在 bootstrap 和 leave-one-subject-out 后仍稳定，则 CGMacros 主文应强调 MSI 是 PPGR vulnerability 的强风险分层变量。若 `load_x_msi` 仍方向一致但置信区间跨 0，则主文应谨慎写为 directional effect modification evidence，而不是确定性交互结论。
    """
    write_text(out / "phase3_cgmacros_robust_inference_report_2026-06-10.md", report)
    return models


FEATURE_SETS = {
    "M0_carb_only": ["carbs"],
    "M1_macro_timing": ["calories", "carbs", "protein", "fat", "fiber", "meal_hour_sin", "meal_hour_cos", "prev_meal_gap_min"],
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
        "msi_core_partial",
        "homa_ir",
        "tg_hdl",
        "bmi_z_nhanes_ref",
        "hba1c_z_nhanes_ref",
        "fasting_glucose_mgdl_z_nhanes_ref",
        "ln_homa_ir_z_nhanes_ref",
        "ln_tg_hdl_z_nhanes_ref",
    ],
}


def fit_ridge(train: pd.DataFrame, features: list[str], target: str, alpha: float) -> dict:
    x_train = train[features].copy()
    y = train[target].astype(float).to_numpy()
    med = x_train.median(numeric_only=True)
    x_train = x_train.fillna(med)
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
    train_pred = X @ beta
    return {"features": features, "median": med, "q01": q01, "q99": q99, "mean": mean, "sd": sd, "beta": beta, "train_pred": train_pred}


def predict_ridge(model: dict, data: pd.DataFrame) -> np.ndarray:
    features = model["features"]
    x = data[features].copy().fillna(model["median"])
    x = x.clip(model["q01"], model["q99"], axis=1)
    xs = ((x - model["mean"]) / model["sd"]).to_numpy(dtype=float)
    X = np.column_stack([np.ones(xs.shape[0]), xs])
    return X @ model["beta"]


def tune_alpha(train: pd.DataFrame, features: list[str], target: str) -> float:
    alphas = [0.1, 1.0, 10.0, 100.0]
    subjects = sorted(train["subject_id"].dropna().unique())
    if len(subjects) < 8:
        return 10.0
    folds = {sid: i % 5 for i, sid in enumerate(subjects)}
    best_alpha, best_mae = 10.0, np.inf
    for alpha in alphas:
        errs = []
        for fold in range(5):
            val_subjects = [sid for sid, f in folds.items() if f == fold]
            tr = train.loc[~train["subject_id"].isin(val_subjects)].copy()
            va = train.loc[train["subject_id"].isin(val_subjects)].copy()
            if len(tr) < 30 or len(va) == 0:
                continue
            model = fit_ridge(tr, features, target, alpha)
            pred = predict_ridge(model, va)
            errs.extend(np.abs(pred - va[target].to_numpy(dtype=float)))
        mae = float(np.mean(errs)) if errs else np.inf
        if mae < best_mae:
            best_alpha, best_mae = alpha, mae
    return best_alpha


def phase4_prediction_upgrade(cg: pd.DataFrame) -> pd.DataFrame:
    out = OUT_ROOT / "phase4_prediction_upgrade"
    ensure_dir(out)
    df = cg.copy()
    df["meal_time"] = pd.to_datetime(df["meal_time"], errors="coerce")
    for c in set(sum(FEATURE_SETS.values(), [])) | {"iauc_2h", "peak_delta_2h"}:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    targets = {"iauc_2h": "2h iAUC", "peak_delta_2h": "2h peak delta"}
    records = []
    for target, target_label in targets.items():
        eligible = df.loc[df[target].notna()].copy()
        subjects = sorted(eligible["subject_id"].dropna().unique())
        for model_name, features in FEATURE_SETS.items():
            for sid in subjects:
                train = eligible.loc[eligible["subject_id"] != sid].copy()
                test = eligible.loc[eligible["subject_id"] == sid].copy()
                if len(train) < 50 or len(test) == 0:
                    continue
                alpha = tune_alpha(train, features, target)
                model = fit_ridge(train, features, target, alpha)
                pred = predict_ridge(model, test)
                train_pred = model["train_pred"]
                train_y = train[target].to_numpy(dtype=float)
                high_threshold = float(np.nanquantile(train_y, 0.75))
                residual_abs = np.abs(train_pred - train_y)
                q90 = float(np.nanquantile(residual_abs, 0.90))
                q95 = float(np.nanquantile(residual_abs, 0.95))
                for (_, row), yhat in zip(test.iterrows(), pred):
                    records.append(
                        {
                            "subject_id": row["subject_id"],
                            "meal_time": row["meal_time"],
                            "target": target,
                            "target_label": target_label,
                            "model": model_name,
                            "alpha": alpha,
                            "y_true": row[target],
                            "y_pred": yhat,
                            "high_threshold_train": high_threshold,
                            "high_true": float(row[target] >= high_threshold),
                            "high_pred_flag": float(yhat >= high_threshold),
                            "q90_abs_resid_train": q90,
                            "q95_abs_resid_train": q95,
                            "covered_q90": float(abs(yhat - row[target]) <= q90),
                            "covered_q95": float(abs(yhat - row[target]) <= q95),
                            "msi_core": row["msi_core_partial"],
                            "msi_tertile": row["msi_core_tertile_within_dataset"],
                        }
                    )
    pred = pd.DataFrame(records)
    write_csv(out / "phase4_nested_lso_prediction_records.csv", pred)

    perf_rows = []
    for keys, d in pred.groupby(["target", "target_label", "model"], dropna=False):
        row = dict(zip(["target", "target_label", "model"], keys))
        row.update(regression_metrics(d))
        row["AUC_high_response"] = auc_score(d["high_true"], d["y_pred"])
        row["AUPRC_high_response"] = auprc_score(d["high_true"], d["y_pred"])
        row["sensitivity_high_flag"] = float(((d["high_true"] == 1) & (d["high_pred_flag"] == 1)).sum() / max((d["high_true"] == 1).sum(), 1))
        row["specificity_high_flag"] = float(((d["high_true"] == 0) & (d["high_pred_flag"] == 0)).sum() / max((d["high_true"] == 0).sum(), 1))
        row["net_benefit_pt25"] = float(((d["high_true"] == 1) & (d["high_pred_flag"] == 1)).sum() / len(d) - ((d["high_true"] == 0) & (d["high_pred_flag"] == 1)).sum() / len(d) * (0.25 / 0.75))
        perf_rows.append(row)
    perf = pd.DataFrame(perf_rows)
    write_csv(out / "phase4_model_performance_overall.csv", perf)

    by_msi_rows = []
    for keys, d in pred.groupby(["target", "target_label", "model", "msi_tertile"], dropna=False):
        row = dict(zip(["target", "target_label", "model", "msi_tertile"], keys))
        row.update(regression_metrics(d))
        row["AUC_high_response"] = auc_score(d["high_true"], d["y_pred"])
        row["AUPRC_high_response"] = auprc_score(d["high_true"], d["y_pred"])
        by_msi_rows.append(row)
    by_msi = pd.DataFrame(by_msi_rows)
    write_csv(out / "phase4_performance_by_msi.csv", by_msi)

    conformal = (
        pred.groupby(["target", "target_label", "model"], as_index=False)
        .agg(
            n=("y_true", "size"),
            coverage_q90=("covered_q90", "mean"),
            coverage_q95=("covered_q95", "mean"),
            median_q90_width=("q90_abs_resid_train", lambda x: float(np.nanmedian(2 * x))),
            median_q95_width=("q95_abs_resid_train", lambda x: float(np.nanmedian(2 * x))),
        )
    )
    write_csv(out / "phase4_conformal_interval_coverage.csv", conformal)

    decile_rows = []
    for keys, d in pred.groupby(["target", "target_label", "model"]):
        d = d.copy()
        try:
            d["pred_decile"] = pd.qcut(d["y_pred"], 10, labels=False, duplicates="drop") + 1
        except ValueError:
            continue
        for dec, qd in d.groupby("pred_decile"):
            decile_rows.append(
                {
                    "target": keys[0],
                    "target_label": keys[1],
                    "model": keys[2],
                    "pred_decile": int(dec),
                    "n": len(qd),
                    "mean_pred": float(qd["y_pred"].mean()),
                    "mean_observed": float(qd["y_true"].mean()),
                    "high_rate": float(qd["high_true"].mean()),
                }
            )
    deciles = pd.DataFrame(decile_rows)
    write_csv(out / "phase4_calibration_deciles.csv", deciles)

    shots = [0, 1, 3, 5, 10]
    few_rows = []
    pred_sorted = pred.sort_values(["target", "model", "subject_id", "meal_time"]).copy()
    for (target, model, sid), d in pred_sorted.groupby(["target", "model", "subject_id"]):
        d = d.sort_values("meal_time").reset_index(drop=True)
        for shots_n in shots:
            if len(d) <= shots_n:
                continue
            calib = d.iloc[:shots_n]
            test = d.iloc[shots_n:].copy()
            if shots_n == 0:
                intercept, slope = 0.0, 1.0
            elif shots_n == 1 or calib["y_pred"].std(ddof=0) == 0:
                intercept, slope = float((calib["y_true"] - calib["y_pred"]).mean()), 1.0
            else:
                intercept, slope = calibration_slope_intercept(calib["y_true"], calib["y_pred"])
                if not np.isfinite(intercept) or not np.isfinite(slope):
                    intercept, slope = 0.0, 1.0
            adj = intercept + slope * test["y_pred"].to_numpy(dtype=float)
            for (_, row), yhat in zip(test.iterrows(), adj):
                few_rows.append(
                    {
                        "subject_id": row["subject_id"],
                        "target": row["target"],
                        "target_label": row["target_label"],
                        "model": row["model"],
                        "shots": shots_n,
                        "y_true": row["y_true"],
                        "y_pred": yhat,
                        "high_true": row["high_true"],
                        "msi_tertile": row["msi_tertile"],
                    }
                )
    few = pd.DataFrame(few_rows)
    few_perf_rows = []
    for keys, d in few.groupby(["target", "target_label", "model", "shots", "msi_tertile"], dropna=False):
        row = dict(zip(["target", "target_label", "model", "shots", "msi_tertile"], keys))
        row.update(regression_metrics(d))
        few_perf_rows.append(row)
    few_perf = pd.DataFrame(few_perf_rows)
    write_csv(out / "phase4_fewshot_recalibration_performance.csv", few_perf)

    compare = []
    for target in targets:
        for model_a, model_b in [("M2_macro_precgm_context", "M3_msi_enhanced"), ("M0_carb_only", "M3_msi_enhanced")]:
            a = perf.loc[(perf["target"] == target) & (perf["model"] == model_a)]
            b = perf.loc[(perf["target"] == target) & (perf["model"] == model_b)]
            if len(a) and len(b):
                compare.append(
                    {
                        "target": target,
                        "comparison": f"{model_b} minus {model_a}",
                        "MAE_delta": float(b.iloc[0]["MAE"] - a.iloc[0]["MAE"]),
                        "MAE_pct_change": float(100 * (b.iloc[0]["MAE"] - a.iloc[0]["MAE"]) / a.iloc[0]["MAE"]),
                        "AUC_delta": float(b.iloc[0]["AUC_high_response"] - a.iloc[0]["AUC_high_response"]),
                        "calibration_slope_delta": float(b.iloc[0]["calibration_slope"] - a.iloc[0]["calibration_slope"]),
                    }
                )
    compare_df = pd.DataFrame(compare)
    write_csv(out / "phase4_model_comparison_key_deltas.csv", compare_df)

    report = f"""
    # Phase 4 完成报告：MSI-aware 预测与个体化升级

    ## 已完成

    - 采用 nested leave-subject-out 设计：外层留一受试者，内层按受试者 5-fold 调参 alpha。
    - 模型阶梯：M0 carb-only、M1 macro/timing、M2 pre-CGM/context、M3 MSI-enhanced。
    - 输出连续结局 MAE/RMSE/R2/calibration，high-response AUC/AUPRC/sensitivity/specificity/net benefit。
    - 输出 conformal-style residual interval coverage。
    - 输出 0/1/3/5/10-shot 个体化校准表现。

    ## 总体模型表现

    {md_table(perf[['target_label','model','MAE','RMSE','calibration_slope','AUC_high_response','AUPRC_high_response','net_benefit_pt25','n']])}

    ## 关键模型差异

    {md_table(compare_df)}

    ## 投稿判断

    Phase 4 已经从简单 ridge benchmark 升级为更接近 TRIPOD+AI 思路的开发/验证框架。主文不应写成模型排行榜，而应集中回答：MSI 是否改善高风险餐食识别或校准，高 MSI 个体是否更难预测，以及 few-shot personalization 是否能补偿这种难度。
    """
    write_text(out / "phase4_prediction_upgrade_report_2026-06-10.md", report)
    return pred


def parse_dt(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", dayfirst=True)


def phase5_external_validation(cg: pd.DataFrame) -> None:
    out = OUT_ROOT / "phase5_external_validation"
    ensure_dir(out)
    ext = ROOT / "data" / "external"

    # Stanford CGMDB standardized food challenge.
    stan_meta = pd.read_csv(ext / "Stanford_CGMDB" / "data_meta.csv")
    stan_cgm = pd.read_csv(ext / "Stanford_CGMDB" / "data_cgm.csv")
    stan_rows = []
    for keys, d in stan_cgm.groupby(["subject", "foods", "food", "mitigator", "rep"], dropna=False):
        d = d.copy()
        t = pd.to_numeric(d["mins_since_start"], errors="coerce").to_numpy(dtype=float)
        g = pd.to_numeric(d["glucose"], errors="coerce").to_numpy(dtype=float)
        pre = (t >= -30) & (t < 0) & np.isfinite(g)
        post = (t >= 0) & (t <= 180) & np.isfinite(g)
        if pre.sum() < 2 or post.sum() < 5:
            continue
        baseline = float(np.nanmean(g[pre]))
        inc = g - baseline
        stan_rows.append(
            {
                "subject_id": keys[0],
                "foods": keys[1],
                "food": keys[2],
                "mitigator": keys[3],
                "rep": keys[4],
                "baseline_glucose": baseline,
                "iauc_2h": trapezoid_auc(t, inc, 0, 120),
                "iauc_3h": trapezoid_auc(t, inc, 0, 180),
                "peak_delta_2h": float(np.nanmax(inc[(t >= 0) & (t <= 120)])),
                "n_pre": int(pre.sum()),
                "n_post2h": int(((t >= 0) & (t <= 120)).sum()),
            }
        )
    stan = pd.DataFrame(stan_rows)
    meta = stan_meta.copy()
    meta["homa_ir_proxy"] = np.where(
        (pd.to_numeric(meta["fasting glucose"], errors="coerce") > 0)
        & (pd.to_numeric(meta["fasting insulin"], errors="coerce") > 0),
        pd.to_numeric(meta["fasting glucose"], errors="coerce") * pd.to_numeric(meta["fasting insulin"], errors="coerce") / 405,
        np.nan,
    )
    meta["ln_homa_ir_proxy"] = np.log(meta["homa_ir_proxy"].where(meta["homa_ir_proxy"] > 0))
    for c in ["BMI", "HbA1c", "fasting glucose", "ln_homa_ir_proxy"]:
        meta[f"{c}_z"] = zscore(meta[c])
    meta["stanford_msi_proxy"] = meta[["BMI_z", "HbA1c_z", "fasting glucose_z", "ln_homa_ir_proxy_z"]].mean(axis=1, skipna=True)
    stan = stan.merge(meta[["id", "BMI", "HbA1c", "fasting glucose", "homa_ir_proxy", "stanford_msi_proxy"]], left_on="subject_id", right_on="id", how="left")
    write_csv(out / "phase5_stanford_food_challenge_metrics.csv", stan)
    stan_summary = (
        stan.groupby("food", as_index=False)
        .agg(
            n_challenges=("iauc_2h", "size"),
            n_subjects=("subject_id", "nunique"),
            median_iauc_2h=("iauc_2h", "median"),
            mean_iauc_2h=("iauc_2h", "mean"),
            sd_iauc_2h=("iauc_2h", "std"),
            median_peak_delta_2h=("peak_delta_2h", "median"),
            high_response_rate=("iauc_2h", lambda x: float(np.mean(x >= stan["iauc_2h"].quantile(0.75)))),
        )
        .sort_values("median_iauc_2h", ascending=False)
    )
    stan_summary["cv_iauc_2h"] = stan_summary["sd_iauc_2h"] / stan_summary["mean_iauc_2h"].replace(0, np.nan)
    write_csv(out / "phase5_stanford_food_summary.csv", stan_summary)
    stan_model_rows = []
    for outcome in ["iauc_2h", "peak_delta_2h"]:
        tmp = stan.copy()
        tmp[f"{outcome}_scaled"] = tmp[outcome] / (1000 if outcome == "iauc_2h" else 1)
        X, y, w, clusters = make_design(
            tmp,
            f"{outcome}_scaled",
            ["stanford_msi_proxy", "baseline_glucose"],
            categorical=["food"],
            cluster_col="subject_id",
            standardize_predictors={"baseline_glucose"},
        )
        res = fit_linear_cluster(X, y, clusters, w)
        r = res.loc[res["term"] == "stanford_msi_proxy"].iloc[0].to_dict()
        r.update({"dataset": "Stanford_CGMDB", "outcome": outcome, "term": "stanford_msi_proxy"})
        stan_model_rows.append(r)
    stan_models = pd.DataFrame(stan_model_rows)
    stan_models["estimate_CI"] = stan_models.apply(effect_ci_text, axis=1)
    write_csv(out / "phase5_stanford_msi_proxy_models.csv", stan_models)

    # T1D-UOM meal-CGM boundary.
    uom_root = ext / "T1D_UOM_2025" / "sharpic-ManchesterCSCoordinatedDiabetesStudy-fdbd74f"
    meal_rows = []
    for nf in sorted((uom_root / "Nutrition Data").glob("UoMNutrition*.csv")):
        m = re.search(r"(\d{4})", nf.stem)
        if not m:
            continue
        pid = m.group(1)
        gf = uom_root / "Glucose Data" / f"UoMGlucose{pid}.csv"
        if not gf.exists():
            continue
        nut = pd.read_csv(nf)
        glu = pd.read_csv(gf)
        nut["meal_ts"] = parse_dt(nut["meal_ts"])
        glu["bg_ts"] = parse_dt(glu["bg_ts"])
        glu["glucose_mgdl"] = pd.to_numeric(glu["value"], errors="coerce") * 18.0182
        glu = glu.dropna(subset=["bg_ts", "glucose_mgdl"]).sort_values("bg_ts")
        for idx, meal in nut.dropna(subset=["meal_ts"]).iterrows():
            t0 = meal["meal_ts"]
            win = glu.loc[(glu["bg_ts"] >= t0 - pd.Timedelta(minutes=30)) & (glu["bg_ts"] <= t0 + pd.Timedelta(minutes=180))].copy()
            if len(win) < 12:
                continue
            mins = (win["bg_ts"] - t0).dt.total_seconds().to_numpy(dtype=float) / 60.0
            vals = win["glucose_mgdl"].to_numpy(dtype=float)
            pre = (mins >= -30) & (mins < 0)
            post2 = (mins >= 0) & (mins <= 120)
            if pre.sum() < 2 or post2.sum() < 8:
                continue
            baseline = float(np.nanmean(vals[pre]))
            inc = vals - baseline
            meal_rows.append(
                {
                    "dataset": "T1D_UOM",
                    "subject_id": pid,
                    "meal_ts": t0,
                    "meal_type": meal.get("meal_type"),
                    "meal_tag": meal.get("meal_tag"),
                    "carbs_g": pd.to_numeric(pd.Series([meal.get("carbs_g")]), errors="coerce").iloc[0],
                    "protein_g": pd.to_numeric(pd.Series([meal.get("prot_g")]), errors="coerce").iloc[0],
                    "fat_g": pd.to_numeric(pd.Series([meal.get("fat_g")]), errors="coerce").iloc[0],
                    "fiber_g": pd.to_numeric(pd.Series([meal.get("fibre_g")]), errors="coerce").iloc[0],
                    "baseline_glucose": baseline,
                    "iauc_2h": trapezoid_auc(mins, inc, 0, 120),
                    "peak_delta_2h": float(np.nanmax(inc[post2])),
                    "n_pre": int(pre.sum()),
                    "n_post2h": int(post2.sum()),
                }
            )
    uom = pd.DataFrame(meal_rows)
    if len(uom):
        uom = uom.loc[pd.to_numeric(uom["carbs_g"], errors="coerce").fillna(0) > 0].copy()
        write_csv(out / "phase5_t1d_uom_meal_ppgr_metrics.csv", uom)
        uom["iauc_2h_per1000"] = uom["iauc_2h"] / 1000
        uom["carbs_10g"] = pd.to_numeric(uom["carbs_g"], errors="coerce") / 10
        uom["protein_10g"] = pd.to_numeric(uom["protein_g"], errors="coerce") / 10
        uom["fat_10g"] = pd.to_numeric(uom["fat_g"], errors="coerce") / 10
        uom["fiber_5g"] = pd.to_numeric(uom["fiber_g"], errors="coerce") / 5
        uom_model_rows = []
        for outcome in ["iauc_2h_per1000", "peak_delta_2h"]:
            X, y, w, clusters = make_design(
                uom,
                outcome,
                ["carbs_10g", "protein_10g", "fat_10g", "fiber_5g", "baseline_glucose"],
                cluster_col="subject_id",
                standardize_predictors={"baseline_glucose"},
            )
            res = fit_linear_cluster(X, y, clusters, w)
            res.insert(0, "dataset", "T1D_UOM")
            res.insert(1, "outcome", outcome)
            uom_model_rows.append(res)
        uom_models = pd.concat(uom_model_rows, ignore_index=True)
        uom_models["estimate_CI"] = uom_models.apply(effect_ci_text, axis=1)
        write_csv(out / "phase5_t1d_uom_macro_ppgr_models.csv", uom_models)
    else:
        write_csv(out / "phase5_t1d_uom_meal_ppgr_metrics.csv", pd.DataFrame())
        uom_models = pd.DataFrame()

    # Jaeb healthy adults CGM phenotype reference.
    jaeb_path = ext / "Jaeb_CGMND_HealthyAdults_2017" / "NonDiabDeviceCGM.csv"
    jaeb = pd.read_csv(jaeb_path)
    jaeb = jaeb.loc[jaeb["RecordType"].astype(str).str.upper().str.contains("CGM|SENSOR", regex=True, na=False)].copy()
    if jaeb.empty:
        jaeb = pd.read_csv(jaeb_path).copy()
    jaeb["Value"] = pd.to_numeric(jaeb["Value"], errors="coerce")
    jaeb_subj = (
        jaeb.dropna(subset=["Value"])
        .groupby("PtID", as_index=False)
        .agg(
            n_readings=("Value", "size"),
            mean_glucose=("Value", "mean"),
            sd_glucose=("Value", "std"),
            median_glucose=("Value", "median"),
            time_above_140=("Value", lambda x: float(np.mean(x > 140))),
            time_below_70=("Value", lambda x: float(np.mean(x < 70))),
            time_70_180=("Value", lambda x: float(np.mean((x >= 70) & (x <= 180)))),
        )
    )
    jaeb_subj["cv_glucose"] = jaeb_subj["sd_glucose"] / jaeb_subj["mean_glucose"]
    write_csv(out / "phase5_jaeb_healthy_adults_cgm_summary.csv", jaeb_subj)

    cg_boundary = {
        "dataset": "CGMacros",
        "n_subjects": int(cg["subject_id"].nunique()),
        "n_events": int(len(cg)),
        "event_type": "free-living meals",
        "median_iauc_2h": float(cg["iauc_2h"].median()),
        "median_peak_delta_2h": float(cg["peak_delta_2h"].median()),
        "time_above_140_or_high_rate": np.nan,
    }
    boundary_rows = [cg_boundary]
    if len(stan):
        boundary_rows.append(
            {
                "dataset": "Stanford_CGMDB",
                "n_subjects": int(stan["subject_id"].nunique()),
                "n_events": int(len(stan)),
                "event_type": "standardized food challenges",
                "median_iauc_2h": float(stan["iauc_2h"].median()),
                "median_peak_delta_2h": float(stan["peak_delta_2h"].median()),
                "time_above_140_or_high_rate": float(np.mean(stan["iauc_2h"] >= stan["iauc_2h"].quantile(0.75))),
            }
        )
    if len(uom):
        boundary_rows.append(
            {
                "dataset": "T1D_UOM",
                "n_subjects": int(uom["subject_id"].nunique()),
                "n_events": int(len(uom)),
                "event_type": "T1D logged meals",
                "median_iauc_2h": float(uom["iauc_2h"].median()),
                "median_peak_delta_2h": float(uom["peak_delta_2h"].median()),
                "time_above_140_or_high_rate": float(np.mean(uom["iauc_2h"] >= uom["iauc_2h"].quantile(0.75))),
            }
        )
    if len(jaeb_subj):
        boundary_rows.append(
            {
                "dataset": "Jaeb_CGMND_HealthyAdults",
                "n_subjects": int(len(jaeb_subj)),
                "n_events": int(jaeb_subj["n_readings"].sum()),
                "event_type": "healthy adult CGM readings",
                "median_iauc_2h": np.nan,
                "median_peak_delta_2h": np.nan,
                "time_above_140_or_high_rate": float(jaeb_subj["time_above_140"].median()),
            }
        )
    boundary = pd.DataFrame(boundary_rows)
    write_csv(out / "phase5_external_boundary_summary.csv", boundary)

    report = f"""
    # Phase 5 完成报告：外部 CGM 验证与边界分析

    ## 已完成

    - Stanford CGMDB：从标准化食物挑战 CGM 曲线计算 baseline、2h iAUC、3h iAUC、2h peak delta，并构建 Stanford MSI proxy。
    - T1D-UOM：从营养日志和 CGM 文件自动配对餐食事件，计算 T1D 自由生活餐食 PPGR。
    - Jaeb healthy adults：提取健康成人 CGM phenotype 参考。
    - 生成跨数据集边界表，明确外部数据只用于边界验证，不作为同分布重复验证。

    ## 外部边界概览

    {md_table(boundary)}

    ## Stanford 标准化食物挑战最高反应食物

    {md_table(stan_summary.head(8)[['food','n_challenges','n_subjects','median_iauc_2h','median_peak_delta_2h','cv_iauc_2h']])}

    ## Stanford MSI proxy 模型

    {md_table(stan_models[['outcome','term','estimate_CI','p_value','n','n_clusters']])}

    ## 投稿判断

    Stanford CGMDB 适合作为主文外部边界图，因为它是标准化食物挑战，能够展示相同食物下的个体异质性。T1D-UOM 提供疾病状态下的自由生活餐食边界，但不应被解释为 CGMacros 的直接重复验证。Jaeb healthy adults 适合作为健康 CGM 波动范围参考。
    """
    write_text(out / "phase5_external_validation_report_2026-06-10.md", report)


def write_master_summary() -> None:
    out = OUT_ROOT / "phase0_to_phase5_master_summary_2026-06-10.md"
    phase_dirs = [
        "phase0_protocol",
        "phase1_qc_msi_sensitivity",
        "phase2_nhanes_survey_ready",
        "phase3_cgmacros_robust_inference",
        "phase4_prediction_upgrade",
        "phase5_external_validation",
    ]
    rows = []
    for d in phase_dirs:
        p = OUT_ROOT / d
        files = sorted([x.name for x in p.glob("*")]) if p.exists() else []
        rows.append({"phase": d, "n_files": len(files), "key_files": "; ".join(files[:8])})
    table = pd.DataFrame(rows)
    write_csv(OUT_ROOT / "phase0_to_phase5_file_manifest_2026-06-10.csv", table)
    report = f"""
    # Phase 0-5 计算工作流总报告

    日期：{TODAY}

    已完成 Phase 0-5 中所有当前电脑可以完成的计算部分。由于本机没有 R/Rscript，Phase 2 已生成正式 R `survey` 脚本，但正式复杂抽样复核需要在安装 R 和 `survey` 包后运行。

    ## 阶段输出概览

    {md_table(table)}

    ## 当前投稿级判断

    - Phase 0 已冻结主线和禁止过度解释规则。
    - Phase 1 已完成 MSI 稳健性和候选餐食 QC。
    - Phase 2 已完成 Python survey-like 近似和 R survey-ready 脚本。
    - Phase 3 已完成 CGMacros subject-cluster、subject bootstrap、leave-one-subject-out 稳健推断。
    - Phase 4 已完成 nested leave-subject-out 预测、校准、high-response detection、conformal coverage 和 few-shot personalization。
    - Phase 5 已完成 Stanford/T1D-UOM/Jaeb 的外部边界分析。

    下一步最关键的非计算任务是：安装 R 后运行 Phase 2 R `survey` 脚本，以及对 Stage 5 候选餐食做人工图片/配方复核后开展仿生消化 pilot。
    """
    write_text(out, report)


def main() -> None:
    ensure_dir(OUT_ROOT)
    ensure_dir(MIRROR_ROOT)
    print("Phase 0...")
    phase0_protocol()
    print("Phase 1...")
    cg, nh = phase1_qc_msi_sensitivity()
    print("Phase 2...")
    phase2_nhanes_survey_ready(nh)
    print("Phase 3...")
    phase3_cgmacros_robust(cg)
    print("Phase 4...")
    phase4_prediction_upgrade(cg)
    print("Phase 5...")
    phase5_external_validation(cg)
    write_master_summary()
    print("Phase 0-5 computational workflow completed.")
    print(f"Outputs: {OUT_ROOT}")
    print(f"Mirrored outputs: {MIRROR_ROOT}")


if __name__ == "__main__":
    main()
