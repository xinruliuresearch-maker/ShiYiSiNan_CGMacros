# -*- coding: utf-8 -*-
"""
Stage 1 for the integrated CGMacros + NHANES mainline project.

Build a shared metabolic susceptibility index (MSI-core) from clinical
metabolic markers that exist, or can be derived, in both projects.

The index intentionally excludes DEHP/phthalate exposure variables so that
NHANES DEHP analyses can treat MSI-core as a downstream metabolic phenotype,
while CGMacros analyses can use MSI-core as a bridge to PPGR vulnerability.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import textwrap
from statistics import NormalDist

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NHANES_ROOT = ROOT.parent / "NHANES_MetS_Project"
OUT = ROOT / "outputs" / "integrated_mainline" / "stage1_msi"
NHANES_OUT = NHANES_ROOT / "result" / "integrated_mainline" / "stage1_msi"


COMPONENTS = [
    "bmi",
    "hba1c",
    "fasting_glucose_mgdl",
    "ln_homa_ir",
    "ln_tg_hdl",
]


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    NHANES_OUT.mkdir(parents=True, exist_ok=True)


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def rank_inverse_normal(series: pd.Series) -> pd.Series:
    """Rank-based inverse normal transformation within non-missing values."""
    x = pd.to_numeric(series, errors="coerce")
    out = pd.Series(np.nan, index=x.index, dtype=float)
    mask = x.notna()
    n = int(mask.sum())
    if n == 0:
        return out
    ranks = x[mask].rank(method="average")
    probs = (ranks - 0.5) / n
    nd = NormalDist()
    out.loc[mask] = [nd.inv_cdf(float(p)) for p in probs]
    return out


def winsorize_with_limits(series: pd.Series, low: float, high: float) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    return x.clip(lower=low, upper=high)


def build_nhanes_table() -> pd.DataFrame:
    path = NHANES_ROOT / "output" / "NHANES_2013_2018_master_analysis_DEHPderived.csv"
    if not path.exists():
        raise FileNotFoundError(path)

    raw = pd.read_csv(path)
    df = pd.DataFrame(
        {
            "dataset": "NHANES_2013_2018",
            "participant_id": raw["SEQN"].astype(str),
            "SEQN": raw["SEQN"],
            "age": safe_numeric(raw.get("RIDAGEYR")),
            "sex_code": safe_numeric(raw.get("RIAGENDR")),
            "bmi": safe_numeric(raw.get("BMXBMI")),
            "hba1c": safe_numeric(raw.get("HbA1c")),
            "fasting_glucose_mgdl": safe_numeric(raw.get("LBXGLU")),
            "fasting_insulin_uUml": safe_numeric(raw.get("LBXIN")),
            "homa_ir": safe_numeric(raw.get("HOMA_IR")),
            "tg_hdl": safe_numeric(raw.get("TG_HDL")),
            "tyg": safe_numeric(raw.get("TyG")),
            "ln_sigma_dehp": safe_numeric(raw.get("ln_Sigma_DEHP")),
            "pct_oxidative_10": safe_numeric(raw.get("pct_oxidative_10")),
            "ln_oxidative_to_mehp": safe_numeric(raw.get("ln_oxidative_to_MEHP")),
            "wt_mec_6yr": safe_numeric(raw.get("WTSB6YR_MAIN")),
            "sdmvpsu": safe_numeric(raw.get("SDMVPSU")),
            "sdmvstra": safe_numeric(raw.get("SDMVSTRA")),
            "cycle": raw.get("cycle"),
        }
    )
    df["ln_homa_ir"] = np.where(df["homa_ir"] > 0, np.log(df["homa_ir"]), np.nan)
    df["ln_tg_hdl"] = np.where(df["tg_hdl"] > 0, np.log(df["tg_hdl"]), np.nan)
    return df


def first_nonmissing(series: pd.Series):
    vals = series.dropna()
    return vals.iloc[0] if len(vals) else np.nan


def build_cgmacros_subject_table() -> tuple[pd.DataFrame, pd.DataFrame]:
    path = ROOT / "outputs" / "tables" / "meal_level_dataset.csv"
    if not path.exists():
        raise FileNotFoundError(path)

    meal = pd.read_csv(path)

    clinical_cols = {
        "BMI": "bmi",
        "A1c PDL (Lab)": "hba1c",
        "Fasting GLU - PDL (Lab)": "fasting_glucose_mgdl",
        "Insulin": "fasting_insulin_uUml",
        "Triglycerides": "triglycerides_mgdl",
        "HDL": "hdl_mgdl",
        "Age": "age",
        "Gender": "gender",
    }

    agg_spec = {src: first_nonmissing for src in clinical_cols if src in meal.columns}
    sub = meal.groupby("subject_id", as_index=False).agg(agg_spec)
    sub = sub.rename(columns=clinical_cols)
    sub["dataset"] = "CGMacros"
    sub["participant_id"] = sub["subject_id"].astype(str)

    sub["bmi"] = safe_numeric(sub.get("bmi"))
    sub["hba1c"] = safe_numeric(sub.get("hba1c"))
    sub["fasting_glucose_mgdl"] = safe_numeric(sub.get("fasting_glucose_mgdl"))
    sub["fasting_insulin_uUml"] = safe_numeric(sub.get("fasting_insulin_uUml"))
    sub["triglycerides_mgdl"] = safe_numeric(sub.get("triglycerides_mgdl"))
    sub["hdl_mgdl"] = safe_numeric(sub.get("hdl_mgdl"))
    sub["age"] = safe_numeric(sub.get("age"))

    sub["homa_ir"] = np.where(
        (sub["fasting_glucose_mgdl"] > 0) & (sub["fasting_insulin_uUml"] > 0),
        (sub["fasting_glucose_mgdl"] * sub["fasting_insulin_uUml"]) / 405.0,
        np.nan,
    )
    sub["tg_hdl"] = np.where(
        (sub["triglycerides_mgdl"] > 0) & (sub["hdl_mgdl"] > 0),
        sub["triglycerides_mgdl"] / sub["hdl_mgdl"],
        np.nan,
    )
    sub["ln_homa_ir"] = np.where(sub["homa_ir"] > 0, np.log(sub["homa_ir"]), np.nan)
    sub["ln_tg_hdl"] = np.where(sub["tg_hdl"] > 0, np.log(sub["tg_hdl"]), np.nan)

    ppgr = meal.groupby("subject_id", as_index=False).agg(
        n_meals=("iauc_2h", "size"),
        mean_iauc_2h=("iauc_2h", "mean"),
        median_iauc_2h=("iauc_2h", "median"),
        mean_peak_delta_2h=("peak_delta_2h", "mean"),
        median_peak_delta_2h=("peak_delta_2h", "median"),
        high_iauc_rate=("iauc_2h", lambda x: np.mean(x >= np.nanpercentile(meal["iauc_2h"], 75))),
    )
    sub = sub.merge(ppgr, on="subject_id", how="left")
    return sub, meal


def derive_msi_tables(nhanes: pd.DataFrame, cg: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Use NHANES as the external population reference for unit-comparable z scores.
    scaler_rows = []
    nh = nhanes.copy()
    cg2 = cg.copy()

    for comp in COMPONENTS:
        ref = safe_numeric(nh[comp])
        low, high = ref.quantile([0.01, 0.99])
        ref_w = winsorize_with_limits(ref, low, high)
        mean = ref_w.mean(skipna=True)
        sd = ref_w.std(skipna=True, ddof=0)
        if not np.isfinite(sd) or sd == 0:
            sd = np.nan
        scaler_rows.append(
            {
                "component": comp,
                "reference_dataset": "NHANES_2013_2018",
                "winsor_p01": low,
                "winsor_p99": high,
                "mean_after_winsor": mean,
                "sd_after_winsor": sd,
                "n_reference_nonmissing": int(ref.notna().sum()),
            }
        )
        for table in (nh, cg2):
            x = winsorize_with_limits(table[comp], low, high)
            table[f"{comp}_z_nhanes_ref"] = (x - mean) / sd
            table[f"{comp}_ranknorm_within_dataset"] = rank_inverse_normal(table[comp])

    z_cols = [f"{c}_z_nhanes_ref" for c in COMPONENTS]
    rn_cols = [f"{c}_ranknorm_within_dataset" for c in COMPONENTS]

    for table in (nh, cg2):
        table["msi_core_components_available"] = table[COMPONENTS].notna().sum(axis=1)
        table["msi_core_complete_nhanes_ref"] = table[z_cols].mean(axis=1, skipna=False)
        table["msi_core_partial_nhanes_ref"] = table[z_cols].mean(axis=1, skipna=True)
        table.loc[table["msi_core_components_available"] < 3, "msi_core_partial_nhanes_ref"] = np.nan
        table["msi_core_ranknorm_within_dataset"] = table[rn_cols].mean(axis=1, skipna=True)
        table.loc[table["msi_core_components_available"] < 3, "msi_core_ranknorm_within_dataset"] = np.nan
        table["msi_core_percentile_within_dataset"] = table["msi_core_partial_nhanes_ref"].rank(pct=True)
        table["msi_core_tertile_within_dataset"] = pd.qcut(
            table["msi_core_percentile_within_dataset"],
            q=3,
            labels=["low", "middle", "high"],
            duplicates="drop",
        ).astype("object")

    scaler = pd.DataFrame(scaler_rows)
    return nh, cg2, scaler


def summarize(nh: pd.DataFrame, cg: pd.DataFrame, scaler: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for label, table in [("NHANES_2013_2018", nh), ("CGMacros_subjects", cg)]:
        rows.append(
            {
                "dataset": label,
                "n": len(table),
                "n_msi_partial": int(table["msi_core_partial_nhanes_ref"].notna().sum()),
                "n_msi_complete": int(table["msi_core_complete_nhanes_ref"].notna().sum()),
                "mean_msi_partial": table["msi_core_partial_nhanes_ref"].mean(skipna=True),
                "sd_msi_partial": table["msi_core_partial_nhanes_ref"].std(skipna=True),
                "median_msi_partial": table["msi_core_partial_nhanes_ref"].median(skipna=True),
                "p25_msi_partial": table["msi_core_partial_nhanes_ref"].quantile(0.25),
                "p75_msi_partial": table["msi_core_partial_nhanes_ref"].quantile(0.75),
                "n_high_tertile": int((table["msi_core_tertile_within_dataset"] == "high").sum()),
            }
        )
    summary = pd.DataFrame(rows)

    miss_rows = []
    for label, table in [("NHANES_2013_2018", nh), ("CGMacros_subjects", cg)]:
        for comp in COMPONENTS:
            miss_rows.append(
                {
                    "dataset": label,
                    "component": comp,
                    "n_nonmissing": int(table[comp].notna().sum()),
                    "n_missing": int(table[comp].isna().sum()),
                    "pct_nonmissing": float(table[comp].notna().mean() * 100),
                }
            )
    missingness = pd.DataFrame(miss_rows)
    return summary, missingness


def write_plot(nh: pd.DataFrame, cg: pd.DataFrame) -> Path | None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return None

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.hist(
        nh["msi_core_partial_nhanes_ref"].dropna(),
        bins=40,
        alpha=0.55,
        density=True,
        label="NHANES 2013-2018",
        color="#4C78A8",
    )
    ax.hist(
        cg["msi_core_partial_nhanes_ref"].dropna(),
        bins=16,
        alpha=0.65,
        density=True,
        label="CGMacros subjects",
        color="#F58518",
    )
    ax.axvline(0, color="#333333", lw=1, ls="--")
    ax.set_title("MSI-core distribution using NHANES reference scaling")
    ax.set_xlabel("MSI-core, NHANES-referenced z score")
    ax.set_ylabel("Density")
    ax.legend(frameon=False)
    fig.tight_layout()
    out = OUT / "stage1_msi_distribution.png"
    fig.savefig(out, dpi=300)
    plt.close(fig)
    return out


def write_report(summary: pd.DataFrame, missingness: pd.DataFrame, plot_path: Path | None) -> Path:
    cg_row = summary.loc[summary["dataset"] == "CGMacros_subjects"].iloc[0]
    nh_row = summary.loc[summary["dataset"] == "NHANES_2013_2018"].iloc[0]

    report = f"""# Stage 1 报告：MSI-core 代谢易感性指数构建

日期：2026-06-10

## 目的

构建一个不包含 DEHP/phthalate 暴露变量、可在 NHANES 与 CGMacros 之间桥接的 `MSI-core` 代谢易感性指数。该指数将在后续阶段承担两个角色：

1. 在 NHANES 中作为 DEHP oxidative profile 的下游代谢表型。
2. 在 CGMacros 中作为餐食级 PPGR vulnerability 的个体分层变量。

## 指数组件

`MSI-core` 使用 5 个共同临床代谢组件：

- BMI
- HbA1c
- fasting glucose
- ln(HOMA-IR)
- ln(TG/HDL-C)

CGMacros 的 HOMA-IR 由 `fasting glucose mg/dL × fasting insulin uU/mL / 405` 计算。TG/HDL-C 由 triglycerides / HDL 计算。

## 标准化策略

主指数 `msi_core_partial_nhanes_ref` 使用 NHANES 2013-2018 作为外部人群参考：

1. 对每个组件按 NHANES p1-p99 winsorization。
2. 用 NHANES winsorized mean/sd 标准化。
3. 对至少 3 个组件非缺失的个体取平均。

同时输出：

- `msi_core_complete_nhanes_ref`：5 个组件完整时的均值。
- `msi_core_ranknorm_within_dataset`：各数据集内部 rank-normalized 版本。
- `msi_core_tertile_within_dataset`：数据集内部 low/middle/high 三分位。

## 数据规模

| 数据集 | 总样本 | partial MSI 非缺失 | complete MSI 非缺失 | partial MSI 中位数 |
|---|---:|---:|---:|---:|
| NHANES 2013-2018 | {int(nh_row['n'])} | {int(nh_row['n_msi_partial'])} | {int(nh_row['n_msi_complete'])} | {nh_row['median_msi_partial']:.3f} |
| CGMacros subjects | {int(cg_row['n'])} | {int(cg_row['n_msi_partial'])} | {int(cg_row['n_msi_complete'])} | {cg_row['median_msi_partial']:.3f} |

## 输出文件

- `cgmacros_subject_msi_core.csv`：CGMacros 受试者级 MSI 表。
- `cgmacros_meal_level_with_msi_core.csv`：合并 MSI 的 CGMacros 餐食级表。
- `nhanes_2013_2018_msi_core.csv`：NHANES MSI 和 DEHP 关键变量表。
- `stage1_msi_component_scaler.csv`：NHANES 参考标准化参数。
- `stage1_msi_summary_by_dataset.csv`：两个数据集 MSI 概览。
- `stage1_msi_component_missingness.csv`：组件缺失情况。
{f"- `stage1_msi_distribution.png`：MSI 分布图。" if plot_path else ""}

## 下一步

Stage 2 将在 NHANES 中检验：

`DEHP oxidative profile -> MSI-core / HOMA-IR / HbA1c / TyG / TG/HDL-C`

Stage 3 将在 CGMacros 中检验：

`MSI-core -> PPGR vulnerability` 和 `MSI-core × meal load` 交互。
"""
    out = OUT / "stage1_msi_report_2026-06-10.md"
    out.write_text(textwrap.dedent(report), encoding="utf-8-sig")
    return out


def main() -> None:
    ensure_dirs()

    nhanes = build_nhanes_table()
    cg_subject, cg_meal = build_cgmacros_subject_table()
    nh_msi, cg_msi, scaler = derive_msi_tables(nhanes, cg_subject)
    summary, missingness = summarize(nh_msi, cg_msi, scaler)
    plot_path = write_plot(nh_msi, cg_msi)

    nh_cols = [
        "dataset",
        "participant_id",
        "SEQN",
        "age",
        "sex_code",
        "cycle",
        "bmi",
        "hba1c",
        "fasting_glucose_mgdl",
        "fasting_insulin_uUml",
        "homa_ir",
        "ln_homa_ir",
        "tg_hdl",
        "ln_tg_hdl",
        "tyg",
        "msi_core_components_available",
        "msi_core_partial_nhanes_ref",
        "msi_core_complete_nhanes_ref",
        "msi_core_ranknorm_within_dataset",
        "msi_core_percentile_within_dataset",
        "msi_core_tertile_within_dataset",
        "ln_sigma_dehp",
        "pct_oxidative_10",
        "ln_oxidative_to_mehp",
        "wt_mec_6yr",
        "sdmvpsu",
        "sdmvstra",
    ] + [f"{c}_z_nhanes_ref" for c in COMPONENTS]

    cg_cols = [
        "dataset",
        "participant_id",
        "subject_id",
        "age",
        "gender",
        "bmi",
        "hba1c",
        "fasting_glucose_mgdl",
        "fasting_insulin_uUml",
        "homa_ir",
        "ln_homa_ir",
        "triglycerides_mgdl",
        "hdl_mgdl",
        "tg_hdl",
        "ln_tg_hdl",
        "msi_core_components_available",
        "msi_core_partial_nhanes_ref",
        "msi_core_complete_nhanes_ref",
        "msi_core_ranknorm_within_dataset",
        "msi_core_percentile_within_dataset",
        "msi_core_tertile_within_dataset",
        "n_meals",
        "mean_iauc_2h",
        "median_iauc_2h",
        "mean_peak_delta_2h",
        "median_peak_delta_2h",
        "high_iauc_rate",
    ] + [f"{c}_z_nhanes_ref" for c in COMPONENTS]

    cg_subject_out = OUT / "cgmacros_subject_msi_core.csv"
    cg_meal_out = OUT / "cgmacros_meal_level_with_msi_core.csv"
    nhanes_out = OUT / "nhanes_2013_2018_msi_core.csv"
    scaler_out = OUT / "stage1_msi_component_scaler.csv"
    summary_out = OUT / "stage1_msi_summary_by_dataset.csv"
    missing_out = OUT / "stage1_msi_component_missingness.csv"

    cg_msi[cg_cols].to_csv(cg_subject_out, index=False, encoding="utf-8-sig")
    nh_msi[nh_cols].to_csv(nhanes_out, index=False, encoding="utf-8-sig")
    scaler.to_csv(scaler_out, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_out, index=False, encoding="utf-8-sig")
    missingness.to_csv(missing_out, index=False, encoding="utf-8-sig")

    merge_cols = [
        "subject_id",
        "msi_core_components_available",
        "msi_core_partial_nhanes_ref",
        "msi_core_complete_nhanes_ref",
        "msi_core_ranknorm_within_dataset",
        "msi_core_percentile_within_dataset",
        "msi_core_tertile_within_dataset",
        "homa_ir",
        "tg_hdl",
        "ln_homa_ir",
        "ln_tg_hdl",
    ] + [f"{c}_z_nhanes_ref" for c in COMPONENTS]
    meal_with_msi = cg_meal.merge(cg_msi[merge_cols], on="subject_id", how="left")
    meal_with_msi.to_csv(cg_meal_out, index=False, encoding="utf-8-sig")

    report_out = write_report(summary, missingness, plot_path)

    # Mirror compact Stage 1 deliverables into the NHANES project.
    for path in [nhanes_out, scaler_out, summary_out, missing_out, report_out]:
        shutil.copy2(path, NHANES_OUT / path.name)

    print("Stage 1 MSI-core completed.")
    print(f"Output directory: {OUT}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
