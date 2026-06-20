"""Nature Food Aim 1 NHANES audit models.

This script is an executable fallback for the current machine, where R/Rscript
is not installed. It uses weighted least squares with cluster-robust standard
errors by NHANES stratum-PSU pairs. It is not a substitute for the final
R survey implementation in run_nature_food_aim1_nhanes_survey.R, but it checks
data flow, fixed covariates, sensitivity definitions, and result direction.
"""

from __future__ import annotations

from pathlib import Path
import math
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests


ROOT = Path(r"D:\ai for science")
NHANES = Path(r"D:\NHANES_MetS_Project")
CGMACROS = Path(r"D:\ShiYiSiNan_CGMacros")
OUT = ROOT / "results" / "nature_food_aim1_nhanes"
OUT.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def safe_log(x: pd.Series) -> pd.Series:
    y = pd.to_numeric(x, errors="coerce")
    y = y.where(y > 0)
    return np.log(y)


def ensure_vars(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "ln_URXUCR" not in df and "URXUCR" in df:
        df["ln_URXUCR"] = safe_log(df["URXUCR"])
    if "HbA1c" not in df and "LBXGH" in df:
        df["HbA1c"] = pd.to_numeric(df["LBXGH"], errors="coerce")
    if "ln_HOMA_IR" not in df and "HOMA_IR" in df:
        df["ln_HOMA_IR"] = safe_log(df["HOMA_IR"])
    if "ln_TG_HDL" not in df and "TG_HDL" in df:
        df["ln_TG_HDL"] = safe_log(df["TG_HDL"])
    if "pct_oxidative_10" not in df and "pct_oxidative" in df:
        df["pct_oxidative_10"] = pd.to_numeric(df["pct_oxidative"], errors="coerce") / 10
    if "pct_oxidative_10_comp" not in df and "pct_oxidative_comp" in df:
        df["pct_oxidative_10_comp"] = pd.to_numeric(df["pct_oxidative_comp"], errors="coerce") / 10
    return df


def load_data() -> pd.DataFrame:
    path = NHANES / "output" / "NHANES_2013_2018_diabetes_medication_sensitivity_dataset_with_DIQ050_DIQ070.csv"
    if not path.exists():
        path = NHANES / "output" / "NHANES_2013_2018_exposure_sensitivity_dataset.csv"
    df = read_csv(path)
    dual_path = (
        CGMACROS
        / "outputs"
        / "integrated_mainline"
        / "high_impact_computational_upgrade_2026-06-11"
        / "01_nhanes_dual_msi_dataset.csv"
    )
    if dual_path.exists():
        dual = read_csv(dual_path)
        keep = [
            c
            for c in [
                "SEQN",
                "msi_core_partial",
                "msi_core_complete",
                "msi_no_bmi",
                "msi_glycemia_ir",
                "exposure_facing_msi",
                "response_vulnerability_index",
            ]
            if c in dual.columns
        ]
        dual = dual[keep]
        overlap = [c for c in keep if c != "SEQN" and c in df.columns]
        df = df.merge(dual, on="SEQN", how="left", suffixes=("", "_dual"))
        for c in overlap:
            alt = f"{c}_dual"
            if alt in df:
                df[c] = df[c].combine_first(df[alt])
                df = df.drop(columns=[alt])
    df = ensure_vars(df)
    for c in ["RIAGENDR", "RIDRETH3", "DMDEDUC2", "ever_smoker", "alcohol_ever", "any_physical_activity", "cycle"]:
        if c in df:
            df[c] = df[c].astype("category")
    df["cluster_pair"] = df["SDMVSTRA"].astype(str) + "_" + df["SDMVPSU"].astype(str)
    return df


OUTCOMES = pd.DataFrame(
    [
        ("msi_core_partial", "MSI-core", False),
        ("ln_HOMA_IR", "ln(HOMA-IR)", True),
        ("HbA1c", "HbA1c", False),
        ("TyG", "TyG", False),
        ("ln_TG_HDL", "ln(TG/HDL-C)", True),
    ],
    columns=["outcome", "label", "log_outcome"],
)

EXPOSURES = pd.DataFrame(
    [
        ("ln_Sigma_DEHP", "ln(Sigma DEHP)"),
        ("pct_oxidative_10", "%Oxidative per 10 pp"),
        ("ln_oxidative_to_MEHP", "ln(Oxidative/MEHP)"),
        ("ilr_oxidative_vs_primary", "ILR oxidative-vs-primary"),
    ],
    columns=["exposure", "label"],
)

COVARS = [
    "RIDAGEYR",
    "C(RIAGENDR)",
    "C(RIDRETH3)",
    "C(DMDEDUC2)",
    "INDFMPIR",
    "DR1TKCAL",
    "C(ever_smoker)",
    "C(alcohol_ever)",
    "C(any_physical_activity)",
    "ln_URXUCR",
    "C(cycle)",
]


def formula_terms(drop_creatinine: bool = False) -> list[str]:
    terms = list(COVARS)
    if drop_creatinine:
        terms = [t for t in terms if t != "ln_URXUCR"]
    return terms


def raw_var_from_term(term: str) -> str:
    if term.startswith("C(") and term.endswith(")"):
        return term[2:-1]
    return term


def transform_effect(beta: float, se: float, log_outcome: bool) -> tuple[float, float, float]:
    low = beta - 1.96 * se
    high = beta + 1.96 * se
    if log_outcome:
        return (math.exp(beta) - 1) * 100, (math.exp(low) - 1) * 100, (math.exp(high) - 1) * 100
    return beta, low, high


def run_model(
    df: pd.DataFrame,
    outcome: str,
    exposure: str,
    log_outcome: bool,
    scenario: str = "main",
    weight: str = "WTSB6YR_MAIN",
    extra_terms: list[str] | None = None,
    drop_creatinine: bool = False,
) -> dict:
    extra_terms = extra_terms or []
    needed = [outcome, exposure, weight, "cluster_pair"] + [raw_var_from_term(t) for t in formula_terms(drop_creatinine)] + [
        raw_var_from_term(t) for t in extra_terms
    ]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        return {
            "scenario": scenario,
            "outcome": outcome,
            "exposure": exposure,
            "n": 0,
            "beta": np.nan,
            "se": np.nan,
            "p_value": np.nan,
            "effect": np.nan,
            "effect_low": np.nan,
            "effect_high": np.nan,
            "status": "missing:" + ";".join(missing),
        }
    d = df[needed].replace([np.inf, -np.inf], np.nan).dropna().copy()
    d = d[d[weight] > 0]
    if len(d) < 100 or d[exposure].nunique(dropna=True) < 5:
        return {
            "scenario": scenario,
            "outcome": outcome,
            "exposure": exposure,
            "n": len(d),
            "beta": np.nan,
            "se": np.nan,
            "p_value": np.nan,
            "effect": np.nan,
            "effect_low": np.nan,
            "effect_high": np.nan,
            "status": "too_few_rows",
        }
    rhs = " + ".join([exposure] + formula_terms(drop_creatinine) + extra_terms)
    formula = f"{outcome} ~ {rhs}"
    try:
        fit = smf.wls(formula, data=d, weights=d[weight]).fit(
            cov_type="cluster", cov_kwds={"groups": d["cluster_pair"]}
        )
        beta = float(fit.params[exposure])
        se = float(fit.bse[exposure])
        p = float(fit.pvalues[exposure])
        effect, effect_low, effect_high = transform_effect(beta, se, log_outcome)
        status = "ok_python_cluster_wls"
    except Exception as exc:  # pragma: no cover - diagnostic path
        beta = se = p = effect = effect_low = effect_high = np.nan
        status = f"error:{exc}"
    return {
        "scenario": scenario,
        "outcome": outcome,
        "exposure": exposure,
        "n": len(d),
        "beta": beta,
        "se": se,
        "p_value": p,
        "effect": effect,
        "effect_low": effect_low,
        "effect_high": effect_high,
        "status": status,
    }


def add_q(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["q_value"] = np.nan
    for _, idx in df.groupby("outcome").groups.items():
        p = df.loc[idx, "p_value"]
        mask = p.notna()
        if mask.any():
            df.loc[p.index[mask], "q_value"] = multipletests(p[mask], method="fdr_bh")[1]
    return df


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    show = df.copy()
    for col in show.columns:
        if pd.api.types.is_float_dtype(show[col]):
            show[col] = show[col].map(lambda x: "" if pd.isna(x) else f"{x:.4g}")
        else:
            show[col] = show[col].astype(str)
    headers = list(show.columns)
    rows = show.astype(str).values.tolist()
    widths = [len(h) for h in headers]
    for row in rows:
        widths = [max(w, len(v)) for w, v in zip(widths, row)]
    line = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |"
    sep = "| " + " | ".join("-" * w for w in widths) + " |"
    body = ["| " + " | ".join(v.ljust(w) for v, w in zip(row, widths)) + " |" for row in rows]
    return "\n".join([line, sep] + body)


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    df = load_data()

    rows = []
    for _, out in OUTCOMES.iterrows():
        for _, exp in EXPOSURES.iterrows():
            rows.append(run_model(df, out.outcome, exp.exposure, bool(out.log_outcome)))
    main_results = add_q(pd.DataFrame(rows))
    main_results.to_csv(OUT / "aim1_main_python_cluster_wls_results.csv", index=False)

    sens_specs = [
        ("main", "pct_oxidative_10", None, False),
        ("drop_urinary_creatinine_covariate", "pct_oxidative_10", None, True),
        ("valid_creatinine_30_300", "pct_oxidative_10", "urinary_creatinine_valid_30_300", False),
        ("all_oxidative_detected", "pct_oxidative_10", "all_oxidative_detected", False),
        ("winsorized_pct_oxidative", "pct_oxidative_10_w", None, False),
        ("creatinine_standardized_total_dehp", "ln_cr_Sigma_DEHP", None, True),
        ("all_dehp_detected_total", "ln_Sigma_DEHP", "all_dehp_detected", False),
    ]
    rows = []
    for name, exp, restriction, drop_cr in sens_specs:
        dat = df
        if restriction and restriction in dat:
            dat = dat[dat[restriction] == 1]
        for out in ["msi_core_partial", "ln_HOMA_IR", "HbA1c"]:
            log_out = bool(OUTCOMES.loc[OUTCOMES.outcome == out, "log_outcome"].iloc[0])
            rows.append(run_model(dat, out, exp, log_out, scenario=name, drop_creatinine=drop_cr))
    sensitivity = add_q(pd.DataFrame(rows))
    sensitivity.to_csv(OUT / "aim1_lod_creatinine_sensitivity_python_cluster_wls_results.csv", index=False)

    rows = []
    flags = [
        "flag_full",
        "flag_no_diagnosed_diabetes",
        "flag_no_diabetes_medication",
        "flag_no_diagnosed_or_medication",
        "flag_strict_non_diabetes",
        "flag_strict_normoglycemia",
    ]
    for flag in [f for f in flags if f in df]:
        dat = df[df[flag] == 1]
        for out in ["ln_HOMA_IR", "HbA1c", "TyG", "ln_TG_HDL"]:
            log_out = bool(OUTCOMES.loc[OUTCOMES.outcome == out, "log_outcome"].iloc[0])
            for exp in ["pct_oxidative_10", "ln_oxidative_to_MEHP"]:
                rows.append(run_model(dat, out, exp, log_out, scenario=flag))
    diabetes = add_q(pd.DataFrame(rows))
    diabetes.to_csv(OUT / "aim1_diabetes_medication_exclusion_python_cluster_wls_results.csv", index=False)

    rows = []
    for cy in sorted(df["cycle"].dropna().astype(str).unique()):
        dat = df[df["cycle"].astype(str) == cy]
        weight = "WTSB2YR_MAIN" if "WTSB2YR_MAIN" in dat.columns else "WTSB6YR_MAIN"
        for out in ["msi_core_partial", "ln_HOMA_IR", "HbA1c", "TyG", "ln_TG_HDL"]:
            log_out = bool(OUTCOMES.loc[OUTCOMES.outcome == out, "log_outcome"].iloc[0])
            for exp in ["pct_oxidative_10", "ln_oxidative_to_MEHP"]:
                rows.append(run_model(dat, out, exp, log_out, scenario=f"cycle_{cy}", weight=weight))
    cycle = add_q(pd.DataFrame(rows))
    cycle.to_csv(OUT / "aim1_cycle_replication_python_cluster_wls_results.csv", index=False)

    comp_exposures = [c for c in ["ln_oxidative_MEHP_ratio", "ilr_oxidative_vs_primary"] if c in df]
    if not comp_exposures and "ln_oxidative_to_MEHP" in df:
        comp_exposures = ["ln_oxidative_to_MEHP"]
    total_term = "ln_Sigma_DEHP_comp" if "ln_Sigma_DEHP_comp" in df else "ln_Sigma_DEHP"
    rows = []
    for out in ["msi_core_partial", "ln_HOMA_IR", "HbA1c", "TyG", "ln_TG_HDL"]:
        log_out = bool(OUTCOMES.loc[OUTCOMES.outcome == out, "log_outcome"].iloc[0])
        for exp in comp_exposures:
            rows.append(
                run_model(
                    df,
                    out,
                    exp,
                    log_out,
                    scenario=f"composition_adjusted_for_{total_term}",
                    extra_terms=[total_term],
                )
            )
    composition = add_q(pd.DataFrame(rows))
    composition.to_csv(OUT / "aim1_composition_total_adjusted_python_cluster_wls_results.csv", index=False)

    # Write compact markdown report with key rows.
    key = main_results[
        main_results["outcome"].isin(["msi_core_partial", "ln_HOMA_IR", "HbA1c"])
        & main_results["exposure"].isin(["pct_oxidative_10", "ln_oxidative_to_MEHP"])
    ].copy()
    lines = [
        "# Nature Food Aim 1 NHANES Python Audit Report",
        "",
        "R/Rscript was not available on this machine, so this report uses weighted least squares with cluster-robust standard errors by NHANES stratum-PSU pairs.",
        "It is an audit output, not the final R `survey` result.",
        "",
        f"Input rows: {len(df)}",
        "",
        "Fixed covariates: age, sex, race/ethnicity, education, PIR, energy intake, smoking, alcohol, physical activity, urinary creatinine, cycle.",
        "",
        "## Key Main-Model Rows",
        "",
        markdown_table(key[["outcome", "exposure", "n", "effect", "effect_low", "effect_high", "p_value", "q_value", "status"]]),
        "",
        "## Output Files",
        "",
        "- `aim1_main_python_cluster_wls_results.csv`",
        "- `aim1_lod_creatinine_sensitivity_python_cluster_wls_results.csv`",
        "- `aim1_diabetes_medication_exclusion_python_cluster_wls_results.csv`",
        "- `aim1_cycle_replication_python_cluster_wls_results.csv`",
        "- `aim1_composition_total_adjusted_python_cluster_wls_results.csv`",
        "- `run_nature_food_aim1_nhanes_survey.R` is the final intended R survey script.",
    ]
    (OUT / "aim1_nhanes_python_audit_report.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote outputs to {OUT}")


if __name__ == "__main__":
    main()
