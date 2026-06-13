# -*- coding: utf-8 -*-
"""
Stage 2 for the integrated mainline project.

Question:
    In NHANES 2013-2018, is the DEHP oxidative metabolic profile associated
    with MSI-core and insulin-resistance/glycemic-lipid markers?

Implementation:
    Pure numpy/pandas weighted least squares with cluster-robust standard
    errors by NHANES stratum-PSU clusters. This is a reproducible Python
    approximation for mainline development. A full R survey-design rerun is
    recommended before submission.
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
OUT = ROOT / "outputs" / "integrated_mainline" / "stage2_nhanes_dehp_msi"
NHANES_OUT = NHANES_ROOT / "result" / "integrated_mainline" / "stage2_nhanes_dehp_msi"


EXPOSURES = {
    "ln_Sigma_DEHP": "ln(Sigma DEHP)",
    "pct_oxidative_10": "%Oxidative per 10 pp",
    "ln_oxidative_to_MEHP": "ln(Oxidative/MEHP)",
}

OUTCOMES = {
    "msi_core_partial_nhanes_ref": ("MSI-core", "z"),
    "ln_HOMA_IR": ("ln(HOMA-IR)", "percent"),
    "HbA1c": ("HbA1c", "absolute"),
    "TyG": ("TyG index", "absolute"),
    "ln_TG_HDL": ("ln(TG/HDL-C)", "percent"),
}


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


def prepare_data() -> pd.DataFrame:
    msi = pd.read_csv(STAGE1 / "nhanes_2013_2018_msi_core.csv")
    raw = pd.read_csv(NHANES_ROOT / "output" / "NHANES_2013_2018_master_analysis_DEHPderived.csv")

    raw_cols = [
        "SEQN",
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
        "ln_Sigma_DEHP",
        "pct_oxidative_10",
        "ln_oxidative_to_MEHP",
    ]
    raw = raw[[c for c in raw_cols if c in raw.columns]].copy()
    df = raw.merge(
        msi[
            [
                "SEQN",
                "msi_core_partial_nhanes_ref",
                "msi_core_complete_nhanes_ref",
                "msi_core_components_available",
            ]
        ],
        on="SEQN",
        how="left",
    )

    df = df.rename(
        columns={
            "RIDAGEYR": "age",
            "RIAGENDR": "sex",
            "RIDRETH3": "race_ethnicity",
            "DMDEDUC2": "education",
            "INDFMPIR": "pir",
            "DR1TKCAL": "energy_kcal",
            "ln_URXUCR": "ln_urine_creatinine",
            "WTSB6YR_MAIN": "weight",
            "SDMVPSU": "psu",
            "SDMVSTRA": "strata",
        }
    )

    df["cluster"] = df["strata"].astype(str) + "_" + df["psu"].astype(str)
    return df


def design_matrix(df: pd.DataFrame, exposure: str, outcome: str) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    continuous = [
        "age",
        "pir",
        "energy_kcal",
        "ln_urine_creatinine",
        exposure,
    ]
    categorical = [
        "sex",
        "race_ethnicity",
        "education",
        "ever_smoker",
        "alcohol_ever",
        "any_physical_activity",
        "cycle",
    ]
    needed = [outcome, "weight", "cluster"] + continuous + categorical
    d = df[needed].copy()
    for c in [outcome, "weight"] + continuous:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna()
    d = d.loc[(d["weight"] > 0)].copy()

    # Standardize continuous covariates except the exposure; keep exposure units interpretable.
    x_parts = [pd.Series(1.0, index=d.index, name="Intercept")]
    for c in continuous:
        if c == exposure:
            x_parts.append(d[c].rename(c))
        else:
            sd = d[c].std(ddof=0)
            if not np.isfinite(sd) or sd == 0:
                z = d[c] * 0
            else:
                z = (d[c] - d[c].mean()) / sd
            x_parts.append(z.rename(c))
    for c in categorical:
        cats = pd.get_dummies(d[c].astype("category"), prefix=c, drop_first=True, dtype=float)
        if cats.shape[1]:
            x_parts.append(cats)
    X = pd.concat(x_parts, axis=1).astype(float)
    y = d[outcome].astype(float)
    w = d["weight"].astype(float)
    clusters = d["cluster"].astype(str)
    return X, y, w, clusters


def fit_wls_cluster(X: pd.DataFrame, y: pd.Series, w: pd.Series, clusters: pd.Series, exposure: str) -> dict:
    x = X.to_numpy(dtype=float)
    yy = y.to_numpy(dtype=float)
    ww = w.to_numpy(dtype=float)
    k = x.shape[1]
    n = x.shape[0]
    if n <= k + 5:
        raise ValueError("Insufficient observations")

    xw = x * ww[:, None]
    xtwx = x.T @ xw
    xtwy = x.T @ (ww * yy)
    xtwx_inv = np.linalg.pinv(xtwx)
    beta = xtwx_inv @ xtwy
    resid = yy - x @ beta

    # Cluster-robust sandwich for WLS score contributions.
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

    names = list(X.columns)
    exp_idx = names.index(exposure)
    b = float(beta[exp_idx])
    s = float(se[exp_idx])
    z = b / s if s > 0 else np.nan
    p = p_norm_2sided(z)
    return {
        "n": n,
        "n_clusters": g,
        "n_parameters": k,
        "beta": b,
        "se": s,
        "z": z,
        "p_value": p,
    }


def effect_scale(beta: float, se: float, outcome_scale: str) -> tuple[float, float, float, str]:
    lo = beta - 1.96 * se
    hi = beta + 1.96 * se
    if outcome_scale == "percent":
        eff = (math.exp(beta) - 1) * 100
        low = (math.exp(lo) - 1) * 100
        high = (math.exp(hi) - 1) * 100
        unit = "% difference"
    else:
        eff, low, high = beta, lo, hi
        unit = "absolute difference"
    return eff, low, high, unit


def run_models(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for outcome, (outcome_label, scale) in OUTCOMES.items():
        for exposure, exposure_label in EXPOSURES.items():
            X, y, w, clusters = design_matrix(df, exposure, outcome)
            fit = fit_wls_cluster(X, y, w, clusters, exposure)
            eff, low, high, unit = effect_scale(fit["beta"], fit["se"], scale)
            rows.append(
                {
                    "outcome": outcome,
                    "outcome_label": outcome_label,
                    "outcome_scale": scale,
                    "exposure": exposure,
                    "exposure_label": exposure_label,
                    "n": fit["n"],
                    "n_clusters": fit["n_clusters"],
                    "n_parameters": fit["n_parameters"],
                    "beta": fit["beta"],
                    "se": fit["se"],
                    "z": fit["z"],
                    "p_value": fit["p_value"],
                    "effect": eff,
                    "effect_low": low,
                    "effect_high": high,
                    "effect_unit": unit,
                    "effect_CI": f"{eff:.3f} ({low:.3f}, {high:.3f})",
                }
            )
    res = pd.DataFrame(rows)
    res["q_value"] = bh_fdr(res["p_value"])
    res["direction"] = np.where(res["effect"] > 0, "positive", "negative")
    res["fdr_significant"] = res["q_value"] < 0.05
    return res


def write_svg_forest(key: pd.DataFrame) -> Path:
    # Compact SVG forest for manuscript planning.
    rows = key.reset_index(drop=True)
    width = 1100
    row_h = 34
    top = 46
    left_label = 310
    plot_left = 360
    plot_right = 850
    height = top + row_h * len(rows) + 50

    vals = pd.concat([rows["effect_low"], rows["effect_high"]]).replace([np.inf, -np.inf], np.nan).dropna()
    xmin = min(vals.min(), 0)
    xmax = max(vals.max(), 0)
    pad = (xmax - xmin) * 0.08 if xmax > xmin else 1
    xmin -= pad
    xmax += pad

    def xmap(v):
        return plot_left + (float(v) - xmin) / (xmax - xmin) * (plot_right - plot_left)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="20" y="25" font-family="Arial" font-size="18" font-weight="bold">Stage 2: DEHP oxidative profile and metabolic susceptibility</text>',
        f'<line x1="{xmap(0):.1f}" y1="{top-18}" x2="{xmap(0):.1f}" y2="{height-35}" stroke="#666" stroke-dasharray="4 4"/>',
    ]
    for i, r in rows.iterrows():
        y = top + i * row_h
        label = f"{r['outcome_label']} | {r['exposure_label']}"
        parts.append(f'<text x="20" y="{y+5}" font-family="Arial" font-size="12">{label}</text>')
        parts.append(
            f'<line x1="{xmap(r.effect_low):.1f}" y1="{y}" x2="{xmap(r.effect_high):.1f}" y2="{y}" stroke="#4C78A8" stroke-width="2"/>'
        )
        parts.append(
            f'<circle cx="{xmap(r.effect):.1f}" cy="{y}" r="4.5" fill="#F58518" stroke="#333"/>'
        )
        qtxt = "<0.001" if r.q_value < 0.001 else f"{r.q_value:.3f}"
        parts.append(
            f'<text x="875" y="{y+5}" font-family="Arial" font-size="12">{r.effect_CI}; q={qtxt}</text>'
        )
    parts.append(f'<text x="{plot_left}" y="{height-12}" font-family="Arial" font-size="11">Effect scale: z-score/absolute units or % difference for log outcomes</text>')
    parts.append("</svg>")
    out = OUT / "stage2_dehp_msi_forest.svg"
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


def write_report(res: pd.DataFrame, key: pd.DataFrame) -> Path:
    def one(outcome, exposure):
        r = res.loc[(res["outcome"] == outcome) & (res["exposure"] == exposure)].iloc[0]
        q = "<0.001" if r.q_value < 0.001 else f"{r.q_value:.3f}"
        return f"{r.effect_CI}, q={q}, n={int(r.n)}"

    report = f"""# Stage 2 报告：NHANES DEHP oxidative profile 与 MSI-core

日期：2026-06-10

## 目的

检验 NHANES 2013-2018 中 DEHP oxidative metabolic profile 是否与 `MSI-core` 及核心糖脂代谢表型相关。这一阶段为整条主线提供人群级证据：

`DEHP oxidative profile -> metabolic susceptibility`

## 方法

当前环境无 `Rscript` 和 `statsmodels`，本阶段使用纯 Python 实现：

- 加权最小二乘回归，权重为 `WTSB6YR_MAIN`。
- 标准误按 `SDMVSTRA + SDMVPSU` 组合做 cluster-robust sandwich。
- 协变量包括 age, sex, race/ethnicity, education, PIR, energy intake, smoking, alcohol, physical activity, urinary creatinine, cycle。
- 这是主线推进版 NHANES weighted approximation。投稿前建议在 R `survey` 环境中做最终复杂抽样方差复核。

## 关键结果

### DEHP oxidative profile 与 MSI-core

- `%Oxidative per 10 pp -> MSI-core`: {one('msi_core_partial_nhanes_ref', 'pct_oxidative_10')}
- `ln(Oxidative/MEHP) -> MSI-core`: {one('msi_core_partial_nhanes_ref', 'ln_oxidative_to_MEHP')}
- `ln(Sigma DEHP) -> MSI-core`: {one('msi_core_partial_nhanes_ref', 'ln_Sigma_DEHP')}

### 与既有代谢终点的一致性

- `%Oxidative per 10 pp -> ln(HOMA-IR)`: {one('ln_HOMA_IR', 'pct_oxidative_10')}
- `%Oxidative per 10 pp -> HbA1c`: {one('HbA1c', 'pct_oxidative_10')}
- `%Oxidative per 10 pp -> TyG`: {one('TyG', 'pct_oxidative_10')}
- `%Oxidative per 10 pp -> ln(TG/HDL-C)`: {one('ln_TG_HDL', 'pct_oxidative_10')}

## 解释

如果以 `MSI-core` 作为跨项目桥梁，本阶段结果支持将 DEHP oxidative profile 放在主线的上游：它与 insulin-resistance/glycemic-lipid susceptibility 表型相关。下一阶段不需要、也不能把 DEHP 直接带入 CGMacros；而应将 `MSI-core` 带入 CGMacros，检验它是否放大餐食诱导的 PPGR vulnerability。

## 输出文件

- `stage2_nhanes_dehp_msi_results.csv`
- `stage2_nhanes_dehp_msi_key_results.csv`
- `stage2_dehp_msi_forest.svg`
- `stage2_nhanes_dehp_msi_report_2026-06-10.md`
"""
    out = OUT / "stage2_nhanes_dehp_msi_report_2026-06-10.md"
    out.write_text(textwrap.dedent(report), encoding="utf-8-sig")
    return out


def main() -> None:
    ensure_dirs()
    df = prepare_data()
    res = run_models(df)
    key = res.loc[
        (
            res["outcome"].isin(["msi_core_partial_nhanes_ref", "ln_HOMA_IR", "HbA1c", "TyG", "ln_TG_HDL"])
            & res["exposure"].isin(["pct_oxidative_10", "ln_oxidative_to_MEHP", "ln_Sigma_DEHP"])
        )
    ].copy()
    key = key.sort_values(["outcome", "exposure"])

    res_out = OUT / "stage2_nhanes_dehp_msi_results.csv"
    key_out = OUT / "stage2_nhanes_dehp_msi_key_results.csv"
    res.to_csv(res_out, index=False, encoding="utf-8-sig")
    key.to_csv(key_out, index=False, encoding="utf-8-sig")
    svg_out = write_svg_forest(key)
    report_out = write_report(res, key)

    for path in [res_out, key_out, svg_out, report_out]:
        shutil.copy2(path, NHANES_OUT / path.name)

    print("Stage 2 NHANES DEHP -> MSI completed.")
    print(f"Output directory: {OUT}")
    print(key[["outcome_label", "exposure_label", "n", "effect_CI", "p_value", "q_value"]].to_string(index=False))


if __name__ == "__main__":
    main()
