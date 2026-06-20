"""Fit adjusted phase-outcome association models.

Outputs:
    results/journal_adjusted_phase_outcome_models.csv
    results/journal_adjusted_phase_global_tests.csv
    figures/journal_adjusted_phase_outcomes.png
    docs/adjusted_phase_outcome_models_zh.md
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from run_journal_grade_experiments import make_ml_phase, markdown_table


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"
DOCS_DIR = ROOT / "docs"

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


TARGETS = [
    {
        "target": "y_hba1c_improved_ge_0_5",
        "label": "HbA1c improvement >=0.5%",
        "type": "binary",
        "effect_scale": "odds_ratio",
        "higher_is_better": True,
    },
    {
        "target": "y_tir_improved_ge_5pct",
        "label": "TIR improvement >=5 percentage points",
        "type": "binary",
        "effect_scale": "odds_ratio",
        "higher_is_better": True,
    },
    {
        "target": "y_hba1c_change_pct_points",
        "label": "HbA1c change, percentage points",
        "type": "continuous",
        "effect_scale": "beta",
        "higher_is_better": False,
    },
    {
        "target": "y_change_cgm_time_in_range_70_180_pct",
        "label": "TIR change, percentage points",
        "type": "continuous",
        "effect_scale": "beta",
        "higher_is_better": True,
    },
]


def ensure_dirs() -> None:
    for path in [RESULTS_DIR, FIGURES_DIR, DOCS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def choose_reference_phase(dat: pd.DataFrame) -> str:
    return dat.groupby("phase_label")["cgm_time_in_range_70_180_pct"].mean().idxmax()


def standardized_numeric(dat: pd.DataFrame, col: str) -> pd.Series:
    x = pd.to_numeric(dat[col], errors="coerce")
    x = x.fillna(x.median())
    sd = x.std(ddof=0)
    if not sd or pd.isna(sd):
        sd = 1.0
    return ((x - x.mean()) / sd).reset_index(drop=True).rename(col)


def build_design(dat: pd.DataFrame, reference_phase: str) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
    dat = dat.reset_index(drop=True)
    numeric = [
        standardized_numeric(dat, "x_baseline_hba1c_pct"),
        standardized_numeric(dat, "x_age_years"),
        standardized_numeric(dat, "x_baseline_cgm_time_in_range_70_180_pct"),
    ]
    phase_raw = pd.get_dummies(dat["phase_label"], dtype=float)
    phase_labels = [col for col in phase_raw.columns if col != reference_phase]
    phase_map = {f"phase_{i}": label for i, label in enumerate(phase_labels)}
    phase = phase_raw[phase_labels].copy()
    phase.columns = list(phase_map.keys())
    study = pd.get_dummies(dat["study_id"], prefix="study", drop_first=True, dtype=float)
    arm = pd.get_dummies(dat["x_randomized_arm"].fillna("missing_arm"), prefix="arm", drop_first=True, dtype=float)
    x = pd.concat(numeric + [phase.reset_index(drop=True), study.reset_index(drop=True), arm.reset_index(drop=True)], axis=1)
    x = sm.add_constant(x, has_constant="add")
    return x.astype(float), phase_map, list(phase_map.keys())


def fit_binary(y: np.ndarray, x: pd.DataFrame):
    return sm.Logit(y, x).fit(disp=False, maxiter=300, cov_type="HC3")


def fit_continuous(y: np.ndarray, x: pd.DataFrame):
    return sm.OLS(y, x).fit(cov_type="HC3")


def global_phase_test(model, phase_cols: list[str]) -> tuple[float, float, int]:
    if not phase_cols:
        return np.nan, np.nan, 0
    restriction = np.zeros((len(phase_cols), len(model.params)))
    names = list(model.params.index)
    for i, col in enumerate(phase_cols):
        restriction[i, names.index(col)] = 1.0
    try:
        test = model.wald_test(restriction, scalar=True)
        statistic = float(test.statistic)
        p_value = float(test.pvalue)
        df = int(len(phase_cols))
    except Exception:
        statistic, p_value, df = np.nan, np.nan, len(phase_cols)
    return statistic, p_value, df


def extract_phase_rows(model, phase_map: dict[str, str], reference_phase: str, target_info: dict, n: int) -> list[dict]:
    rows = [
        {
            "target": target_info["target"],
            "target_label": target_info["label"],
            "outcome_type": target_info["type"],
            "effect_scale": target_info["effect_scale"],
            "phase_label": reference_phase,
            "reference_phase": reference_phase,
            "n": n,
            "estimate": 1.0 if target_info["type"] == "binary" else 0.0,
            "ci_low": 1.0 if target_info["type"] == "binary" else 0.0,
            "ci_high": 1.0 if target_info["type"] == "binary" else 0.0,
            "p_value": np.nan,
            "term": "reference",
        }
    ]
    conf = model.conf_int()
    for term, label in phase_map.items():
        coef = float(model.params[term])
        low = float(conf.loc[term, 0])
        high = float(conf.loc[term, 1])
        if target_info["type"] == "binary":
            estimate, ci_low, ci_high = float(np.exp(coef)), float(np.exp(low)), float(np.exp(high))
        else:
            estimate, ci_low, ci_high = coef, low, high
        rows.append(
            {
                "target": target_info["target"],
                "target_label": target_info["label"],
                "outcome_type": target_info["type"],
                "effect_scale": target_info["effect_scale"],
                "phase_label": label,
                "reference_phase": reference_phase,
                "n": n,
                "estimate": estimate,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "p_value": float(model.pvalues[term]),
                "term": term,
            }
        )
    return rows


def run_models(ml_phase: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_rows = []
    global_rows = []
    for target_info in TARGETS:
        target = target_info["target"]
        dat = ml_phase.dropna(subset=[target, "phase_label"]).copy()
        dat = dat[dat["phase_label"].notna()].reset_index(drop=True)
        if dat.empty:
            continue
        reference_phase = choose_reference_phase(dat)
        x, phase_map, phase_cols = build_design(dat, reference_phase)
        y = pd.to_numeric(dat[target], errors="coerce").to_numpy()
        if target_info["type"] == "binary":
            y = y.astype(int)
            model = fit_binary(y, x)
        else:
            model = fit_continuous(y, x)
        all_rows.extend(extract_phase_rows(model, phase_map, reference_phase, target_info, len(dat)))
        statistic, p_value, df = global_phase_test(model, phase_cols)
        global_rows.append(
            {
                "target": target,
                "target_label": target_info["label"],
                "outcome_type": target_info["type"],
                "n": len(dat),
                "reference_phase": reference_phase,
                "test": "robust_wald_phase_terms",
                "statistic": statistic,
                "df": df,
                "p_value": p_value,
                "covariates": "baseline HbA1c, age, baseline TIR, study fixed effects, randomized arm fixed effects",
            }
        )
    return pd.DataFrame(all_rows), pd.DataFrame(global_rows)


def plot_adjusted_phase_outcomes(results: pd.DataFrame) -> None:
    if results.empty:
        return
    targets = results["target"].unique().tolist()
    fig, axes = plt.subplots(2, 2, figsize=(13, 10), squeeze=False)
    for ax, target in zip(axes.ravel(), targets):
        dat = results[results["target"].eq(target)].copy()
        dat = dat.sort_values("estimate")
        y = np.arange(len(dat))
        x = dat["estimate"].to_numpy()
        lo = dat["ci_low"].to_numpy()
        hi = dat["ci_high"].to_numpy()
        xerr = np.vstack([x - lo, hi - x])
        ax.errorbar(x, y, xerr=xerr, fmt="o", color="#3f6f8f", ecolor="#777777", capsize=3)
        null = 1 if dat["outcome_type"].iloc[0] == "binary" else 0
        ax.axvline(null, color="black", linestyle="--", linewidth=1)
        if dat["outcome_type"].iloc[0] == "binary":
            ax.set_xscale("log")
            ax.set_xlabel("Adjusted odds ratio")
        else:
            ax.set_xlabel("Adjusted beta")
        ax.set_yticks(y)
        ax.set_yticklabels(dat["phase_label"])
        ax.set_title(dat["target_label"].iloc[0])
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "journal_adjusted_phase_outcomes.png", dpi=220)
    plt.close()


def write_report(results: pd.DataFrame, global_tests: pd.DataFrame) -> None:
    report = f"""# 调整后的相位-临床结局关联模型

生成脚本：`scripts/run_adjusted_phase_outcome_models.py`

## 模型目的

该分析用于补强主报告中的相位-结局关联证据。主报告已提供未调整的卡方检验和 Kruskal-Wallis 检验；本脚本进一步调整基线 HbA1c、年龄、基线 TIR、研究固定效应和随机分组臂固定效应。

## 全局相位检验

{markdown_table(global_tests)}

## 相位效应估计

{markdown_table(results, max_rows=40)}

## 图形

- `figures/journal_adjusted_phase_outcomes.png`

## 解释原则

- 二分类结局报告调整 OR；连续结局报告调整 beta。
- 参考相位自动选择为基线 TIR 均值最高的相位，通常对应“稳定达标相”。
- 这些模型支持相图与临床结局存在独立关联，但仍是回顾性二次分析；不能把相位标签解释为已验证的生物学亚型。
"""
    (DOCS_DIR / "adjusted_phase_outcome_models_zh.md").write_text(report, encoding="utf-8")


def main() -> int:
    ensure_dirs()
    ml_phase = make_ml_phase()
    results, global_tests = run_models(ml_phase)
    results.to_csv(RESULTS_DIR / "journal_adjusted_phase_outcome_models.csv", index=False)
    global_tests.to_csv(RESULTS_DIR / "journal_adjusted_phase_global_tests.csv", index=False)
    plot_adjusted_phase_outcomes(results)
    write_report(results, global_tests)
    print(
        json.dumps(
            {
                "adjusted_phase_rows": int(len(results)),
                "global_test_rows": int(len(global_tests)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
