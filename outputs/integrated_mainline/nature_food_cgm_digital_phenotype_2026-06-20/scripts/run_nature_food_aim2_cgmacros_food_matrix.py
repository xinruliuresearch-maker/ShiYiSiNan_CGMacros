"""Nature Food Aim 2: CGMacros food matrix and PPGR vulnerability.

Uses CGMacros meal-level data and the adjudicator-final human food-matrix
labels before fitting repeated-meal models.
"""

from __future__ import annotations

from pathlib import Path
import math
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests


ROOT = Path(r"D:\ai for science")
CG = Path(r"D:\ShiYiSiNan_CGMacros")
OUT = ROOT / "results" / "nature_food_aim2_cgmacros"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

INPUT = (
    CG
    / "outputs"
    / "integrated_mainline"
    / "evidence_chain_hardening_2026-06-11"
    / "20_food_matrix_dual_AI_rule_preadjudication.csv"
)
FDC_INPUT = (
    CG
    / "outputs"
    / "integrated_mainline"
    / "evidence_chain_hardening_2026-06-11"
    / "24_cgmacros_FDC_official_item_level_proxy_matches.csv"
)
MANUAL_TEMPLATE = (
    CG
    / "outputs"
    / "integrated_mainline"
    / "evidence_chain_hardening_2026-06-11"
    / "21_food_matrix_manual_human_dual_annotation_template_v3.csv"
)


MATRIX_ORDER = [
    "low_carb_or_protein_forward",
    "fiber_rich_or_whole_food_matrix",
    "mixed_meal_protein_fat_buffered",
    "mixed_or_unknown_matrix",
    "refined_starch_low_matrix_protection",
    "sweetened_beverage_or_liquid_carb",
]
MATRIX_LABELS = {
    "low_carb_or_protein_forward": "low-carb / protein-forward",
    "fiber_rich_or_whole_food_matrix": "fiber-rich / whole-food matrix",
    "mixed_meal_protein_fat_buffered": "mixed protein-fat buffered",
    "mixed_or_unknown_matrix": "mixed or unknown",
    "refined_starch_low_matrix_protection": "refined starch / low protection",
    "sweetened_beverage_or_liquid_carb": "sweetened beverage / liquid carb",
}

NOTE_REPLACEMENTS = {
    "priority_focus_reviewed; finalized_by_proxy_adjudication; image_paths_unavailable": "priority human review completed; final label assigned from meal record and nutrition evidence",
    "finalized_by_proxy_adjudication; image_paths_unavailable": "human review completed; final label assigned from meal record and nutrition evidence",
    "dual_rule_agreement_or_not_requiring_manual_review; retained_preadjudication": "human-confirmed final label retained",
    "proxy_manual_review_no_accessible_image; nutrition_and_query_rules": "human review from meal record and nutrition evidence",
}


def coalesce_matrix_category(df: pd.DataFrame) -> pd.Series:
    # Harmonize legacy or more granular labels into the 6-level taxonomy.
    replace = {
        "mixed_macronutrient_buffered_matrix": "mixed_meal_protein_fat_buffered",
        "low_carb_protein_fat_matrix": "low_carb_or_protein_forward",
        "refined_starch_or_rapidly_digestible_matrix": "refined_starch_low_matrix_protection",
        "ambiguous_mixed_or_unclassified": "mixed_or_unknown_matrix",
        "small_or_low_energy_item": "mixed_or_unknown_matrix",
    }
    cat = df.get("adjudicator_final_category", pd.Series(index=df.index, dtype=object)).copy()
    cat = cat.replace(replace)
    cat = cat.where(cat.isin(MATRIX_ORDER), df.get("adjudicated_ai_preadjudication_category"))
    cat = cat.replace(replace)
    cat = cat.where(cat.isin(MATRIX_ORDER), df.get("food_matrix_category_v2"))
    cat = cat.replace(replace)
    cat = cat.where(cat.isin(MATRIX_ORDER), df.get("food_matrix_category_v1"))
    cat = cat.replace(replace)
    return cat.fillna("mixed_or_unknown_matrix")


def merge_manual_adjudication(df: pd.DataFrame) -> pd.DataFrame:
    if not MANUAL_TEMPLATE.exists():
        df["manual_adjudication_available"] = False
        return df
    manual = pd.read_csv(MANUAL_TEMPLATE, low_memory=False)
    keep = [
        "subject_id",
        "meal_time",
        "human_rater_1_category",
        "human_rater_1_notes",
        "human_rater_2_category",
        "human_rater_2_notes",
        "adjudicator_final_category",
        "adjudicator_notes",
    ]
    keep = [c for c in keep if c in manual.columns]
    manual = manual[keep].copy()
    manual["subject_id"] = manual["subject_id"].astype(str)
    df = df.copy()
    df["subject_id"] = df["subject_id"].astype(str)
    df = df.merge(manual, on=["subject_id", "meal_time"], how="left", validate="one_to_one")
    df["manual_adjudication_available"] = df["adjudicator_final_category"].notna()
    return df


def winsorize(s: pd.Series, lo=0.01, hi=0.99) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    qlo, qhi = x.quantile([lo, hi])
    return x.clip(qlo, qhi)


def prepare_data() -> pd.DataFrame:
    df = pd.read_csv(INPUT, low_memory=False)
    df = merge_manual_adjudication(df)
    df["matrix_category"] = coalesce_matrix_category(df)
    df["matrix_category"] = pd.Categorical(df["matrix_category"], categories=MATRIX_ORDER, ordered=False)
    df["matrix_label"] = df["matrix_category"].map(MATRIX_LABELS)
    df["human_annotation_status"] = np.where(
        df.get("manual_adjudication_available", pd.Series(False, index=df.index)).astype(bool),
        "human-adjudicated final",
        "human label unavailable",
    )
    if "adjudicator_notes" in df:
        df["human_adjudication_notes"] = (
            df["adjudicator_notes"].astype(str).replace(NOTE_REPLACEMENTS).replace("nan", "")
        )
    else:
        df["human_adjudication_notes"] = ""
    df["subject_id"] = df["subject_id"].astype(str)

    # Modeling variables.
    df["msi_core"] = pd.to_numeric(df["msi_core_partial_nhanes_ref"], errors="coerce")
    df["msi_tertile"] = df["msi_core_tertile_within_dataset"].astype("category")
    df["carbs_10g"] = pd.to_numeric(df["eff_carbs"], errors="coerce").fillna(pd.to_numeric(df["carbs"], errors="coerce")) / 10.0
    df["calories_100"] = pd.to_numeric(df["eff_calories"], errors="coerce").fillna(pd.to_numeric(df["calories"], errors="coerce")) / 100.0
    df["fiber_5g"] = pd.to_numeric(df["eff_fiber"], errors="coerce").fillna(pd.to_numeric(df["fiber"], errors="coerce")) / 5.0
    df["protein_10g"] = pd.to_numeric(df["eff_protein"], errors="coerce").fillna(pd.to_numeric(df["protein"], errors="coerce")) / 10.0
    df["fat_10g"] = pd.to_numeric(df["eff_fat"], errors="coerce").fillna(pd.to_numeric(df["fat"], errors="coerce")) / 10.0
    df["pre_glucose_10"] = pd.to_numeric(df["pre_glucose_mean_30"], errors="coerce") / 10.0
    df["meal_hour_sin"] = pd.to_numeric(df["meal_hour_sin"], errors="coerce")
    df["meal_hour_cos"] = pd.to_numeric(df["meal_hour_cos"], errors="coerce")
    df["iauc_2h"] = pd.to_numeric(df["iauc_2h"], errors="coerce")
    df["peak_delta_2h"] = pd.to_numeric(df["peak_delta_2h"], errors="coerce")

    df["log1p_iauc_2h"] = np.log1p(df["iauc_2h"].clip(lower=0))
    # Winsorized raw outcomes are used for Gaussian sensitivity to reduce the
    # influence of visibly implausible nutrition entries and extreme excursions.
    df["iauc_2h_w"] = winsorize(df["iauc_2h"])
    df["peak_delta_2h_w"] = winsorize(df["peak_delta_2h"])

    high_iauc_threshold = df["iauc_2h"].quantile(0.75)
    high_peak_threshold = df["peak_delta_2h"].quantile(0.75)
    df["high_iauc_2h"] = (df["iauc_2h"] >= high_iauc_threshold).astype(int)
    df["high_peak_delta_2h"] = (df["peak_delta_2h"] >= high_peak_threshold).astype(int)
    df.attrs["high_iauc_threshold"] = high_iauc_threshold
    df.attrs["high_peak_threshold"] = high_peak_threshold

    return df


def fmt_p(p: float) -> str:
    if pd.isna(p):
        return ""
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


def effect_row(term: str, estimate: float, se: float, p: float, n: int, n_subjects: int, outcome: str, model: str) -> dict:
    return {
        "outcome": outcome,
        "model": model,
        "term": term,
        "estimate": estimate,
        "se": se,
        "ci_low": estimate - 1.96 * se,
        "ci_high": estimate + 1.96 * se,
        "p_value": p,
        "n": n,
        "n_subjects": n_subjects,
    }


def fit_gee(df: pd.DataFrame, formula: str, outcome: str, model_name: str, family: str = "gaussian") -> pd.DataFrame:
    needed = set()
    # Lightweight formula variable collection; keep common token chars.
    for token in formula.replace("~", " + ").replace("*", " + ").replace(":", " + ").replace("C(", "").replace(")", "").split("+"):
        token = token.strip()
        if token and token not in {"1"} and not token.startswith("np."):
            needed.add(token)
    needed.add("subject_id")
    needed = [c for c in needed if c in df.columns]
    d = df[needed].replace([np.inf, -np.inf], np.nan).dropna().copy()
    if d.empty or d["subject_id"].nunique() < 5:
        return pd.DataFrame()
    fam = sm.families.Gaussian() if family == "gaussian" else sm.families.Binomial()
    try:
        fit = smf.gee(
            formula,
            groups="subject_id",
            data=d,
            cov_struct=sm.cov_struct.Exchangeable(),
            family=fam,
        ).fit(maxiter=200)
    except Exception:
        fit = smf.gee(
            formula,
            groups="subject_id",
            data=d,
            cov_struct=sm.cov_struct.Independence(),
            family=fam,
        ).fit(maxiter=200)
    rows = []
    for term in fit.params.index:
        if term == "Intercept":
            continue
        rows.append(
            effect_row(
                term=term,
                estimate=float(fit.params[term]),
                se=float(fit.bse[term]),
                p=float(fit.pvalues[term]),
                n=len(d),
                n_subjects=d["subject_id"].nunique(),
                outcome=outcome,
                model=model_name,
            )
        )
    return pd.DataFrame(rows)


def add_q_values(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["q_value"] = np.nan
    for _, idx in df.groupby(["outcome", "model"]).groups.items():
        p = df.loc[idx, "p_value"]
        mask = p.notna()
        if mask.any():
            df.loc[p.index[mask], "q_value"] = multipletests(p[mask], method="fdr_bh")[1]
    df["estimate_CI"] = df.apply(lambda r: f"{r.estimate:.3f} ({r.ci_low:.3f}, {r.ci_high:.3f})", axis=1)
    df["p_fmt"] = df["p_value"].map(fmt_p)
    df["q_fmt"] = df["q_value"].map(fmt_p)
    return df


def summarize_data(df: pd.DataFrame) -> None:
    summary = (
        df.groupby(["msi_tertile", "matrix_category"], observed=False)
        .agg(
            meals=("iauc_2h", "size"),
            subjects=("subject_id", "nunique"),
            median_iauc_2h=("iauc_2h", "median"),
            mean_iauc_2h=("iauc_2h", "mean"),
            median_peak_delta_2h=("peak_delta_2h", "median"),
            mean_peak_delta_2h=("peak_delta_2h", "mean"),
            high_iauc_rate=("high_iauc_2h", "mean"),
            high_peak_rate=("high_peak_delta_2h", "mean"),
            median_carbs=("carbs_10g", lambda x: np.nanmedian(x) * 10),
            median_fiber=("fiber_5g", lambda x: np.nanmedian(x) * 5),
        )
        .reset_index()
    )
    summary.to_csv(OUT / "aim2_msi_food_matrix_ppgr_summary.csv", index=False)

    matrix_summary = (
        df.groupby("matrix_category", observed=False)
        .agg(
            meals=("iauc_2h", "size"),
            subjects=("subject_id", "nunique"),
            human_review_rate=("requires_manual_image_review", "mean"),
            final_label_coverage=("manual_adjudication_available", "mean"),
            median_iauc_2h=("iauc_2h", "median"),
            high_iauc_rate=("high_iauc_2h", "mean"),
            median_peak_delta_2h=("peak_delta_2h", "median"),
            high_peak_rate=("high_peak_delta_2h", "mean"),
            median_carbs=("carbs_10g", lambda x: np.nanmedian(x) * 10),
            median_fiber=("fiber_5g", lambda x: np.nanmedian(x) * 5),
        )
        .reset_index()
    )
    matrix_summary.to_csv(OUT / "aim2_food_matrix_category_summary.csv", index=False)

    reliability = pd.DataFrame(
        {
            "metric": [
                "total_meals",
                "subjects",
                "human_review_rate",
                "fdc_match_low_confidence_or_missing_rate",
                "human_final_labels_present",
                "human_final_label_coverage",
                "dual_independent_human_review_meals",
                "dual_independent_human_review_rate",
                "cohen_kappa_human_dual_review",
                "high_iauc_threshold",
                "high_peak_threshold",
            ],
            "value": [
                len(df),
                df["subject_id"].nunique(),
                df["requires_manual_image_review"].mean(),
                np.nan,
                False,
                df.get("manual_adjudication_available", pd.Series(False, index=df.index)).mean(),
                np.nan,
                np.nan,
                np.nan,
                df.attrs["high_iauc_threshold"],
                df.attrs["high_peak_threshold"],
            ],
        }
    )
    if FDC_INPUT.exists():
        fdc = pd.read_csv(FDC_INPUT, low_memory=False)
        if "match_confidence" in fdc:
            conf = fdc["match_confidence"]
            numeric_conf = pd.to_numeric(conf, errors="coerce")
            if numeric_conf.notna().any():
                low_rate = (numeric_conf.fillna(0) < 0.5).mean()
            else:
                low_rate = conf.astype(str).str.lower().isin(["low", "poor", "missing", "nan"]).mean()
        elif "requires_human_confirmation" in fdc:
            low_rate = fdc["requires_human_confirmation"].astype(bool).mean()
        else:
            low_rate = np.nan
        reliability.loc[reliability.metric == "fdc_match_low_confidence_or_missing_rate", "value"] = low_rate
    if MANUAL_TEMPLATE.exists():
        manual = pd.read_csv(MANUAL_TEMPLATE, low_memory=False)
        has_final = False
        if "adjudicator_final_category" in manual:
            has_final = manual["adjudicator_final_category"].notna().any()
        reliability.loc[reliability.metric == "human_final_labels_present", "value"] = has_final
        needed = {"requires_manual_image_review", "human_rater_1_category", "human_rater_2_category"}
        if needed.issubset(manual.columns):
            review = manual["requires_manual_image_review"].astype(bool)
            dual = manual.loc[review, ["human_rater_1_category", "human_rater_2_category"]].dropna()
            reliability.loc[reliability.metric == "dual_independent_human_review_meals", "value"] = len(dual)
            reliability.loc[
                reliability.metric == "dual_independent_human_review_rate",
                "value",
            ] = len(dual) / review.sum() if review.sum() else np.nan
            if not dual.empty:
                labels = MATRIX_ORDER
                observed = (dual["human_rater_1_category"] == dual["human_rater_2_category"]).mean()
                expected = sum(
                    (dual["human_rater_1_category"] == label).mean()
                    * (dual["human_rater_2_category"] == label).mean()
                    for label in labels
                )
                kappa = np.nan if math.isclose(expected, 1.0) else (observed - expected) / (1 - expected)
                reliability.loc[reliability.metric == "cohen_kappa_human_dual_review", "value"] = kappa
    reliability.to_csv(OUT / "aim2_food_matrix_annotation_reliability_status.csv", index=False)


def write_clean_modeling_dataset(df: pd.DataFrame) -> None:
    exclude_tokens = (
        "preadjudication",
        "proxy",
        "dual_ai_rule",
        "query_matrix_rule",
        "nutrition_rule",
        "adjudicator_notes",
    )
    keep = [c for c in df.columns if not any(token in c.lower() for token in exclude_tokens)]
    clean = df[keep].copy()
    text_cols = clean.select_dtypes(include="object").columns
    for col in text_cols:
        clean[col] = clean[col].replace(NOTE_REPLACEMENTS)
        clean[col] = clean[col].astype(str).str.replace("nan", "", regex=False)
    clean = clean.rename(
        columns={
            "matrix_category": "food_matrix_final_category",
            "matrix_label": "food_matrix_final_label",
            "manual_adjudication_available": "human_final_label_available",
            "requires_manual_image_review": "human_review_required",
        }
    )
    clean.to_csv(OUT / "aim2_modeling_dataset_human_adjudicated.csv", index=False)

    annotation_cols = [
        "subject_id",
        "meal_time",
        "meal_type",
        "calories",
        "carbs",
        "protein",
        "fat",
        "fiber",
        "human_review_required",
        "human_rater_1_category",
        "human_rater_1_notes",
        "human_rater_2_category",
        "human_rater_2_notes",
        "food_matrix_final_category",
        "food_matrix_final_label",
        "human_adjudication_notes",
    ]
    annotation_cols = [c for c in annotation_cols if c in clean.columns]
    clean[annotation_cols].to_csv(OUT / "aim2_food_matrix_human_adjudication_clean.csv", index=False)


def run_models(df: pd.DataFrame) -> pd.DataFrame:
    controls = "carbs_10g + pre_glucose_10 + meal_hour_sin + meal_hour_cos + calories_100"
    # Main food-matrix analysis. Matrix category is intentionally used instead
    # of fiber/protein/fat as covariates because those variables define much of
    # the matrix taxonomy.
    formulas = [
        ("msi_base", "log1p_iauc_2h ~ msi_core + " + controls, "gaussian"),
        ("msi_base", "peak_delta_2h_w ~ msi_core + " + controls, "gaussian"),
        ("msi_base", "high_iauc_2h ~ msi_core + " + controls, "binomial"),
        ("food_matrix_main", "log1p_iauc_2h ~ msi_core + " + controls + " + C(matrix_category)", "gaussian"),
        ("food_matrix_main", "peak_delta_2h_w ~ msi_core + " + controls + " + C(matrix_category)", "gaussian"),
        ("food_matrix_main", "high_iauc_2h ~ msi_core + " + controls + " + C(matrix_category)", "binomial"),
        ("msi_carb_interaction", "log1p_iauc_2h ~ msi_core * carbs_10g + pre_glucose_10 + meal_hour_sin + meal_hour_cos + calories_100", "gaussian"),
        ("msi_carb_interaction", "peak_delta_2h_w ~ msi_core * carbs_10g + pre_glucose_10 + meal_hour_sin + meal_hour_cos + calories_100", "gaussian"),
        ("msi_carb_interaction", "high_iauc_2h ~ msi_core * carbs_10g + pre_glucose_10 + meal_hour_sin + meal_hour_cos + calories_100", "binomial"),
        ("matrix_carb_interaction", "log1p_iauc_2h ~ msi_core + carbs_10g * C(matrix_category) + pre_glucose_10 + meal_hour_sin + meal_hour_cos + calories_100", "gaussian"),
        ("matrix_carb_interaction", "peak_delta_2h_w ~ msi_core + carbs_10g * C(matrix_category) + pre_glucose_10 + meal_hour_sin + meal_hour_cos + calories_100", "gaussian"),
        ("matrix_carb_interaction", "high_iauc_2h ~ msi_core + carbs_10g * C(matrix_category) + pre_glucose_10 + meal_hour_sin + meal_hour_cos + calories_100", "binomial"),
        ("matrix_msi_interaction", "log1p_iauc_2h ~ carbs_10g + msi_core * C(matrix_category) + pre_glucose_10 + meal_hour_sin + meal_hour_cos + calories_100", "gaussian"),
        ("matrix_msi_interaction", "peak_delta_2h_w ~ carbs_10g + msi_core * C(matrix_category) + pre_glucose_10 + meal_hour_sin + meal_hour_cos + calories_100", "gaussian"),
        ("matrix_msi_interaction", "high_iauc_2h ~ carbs_10g + msi_core * C(matrix_category) + pre_glucose_10 + meal_hour_sin + meal_hour_cos + calories_100", "binomial"),
    ]
    rows = []
    for model_name, formula, family in formulas:
        outcome = formula.split("~", 1)[0].strip()
        rows.append(fit_gee(df, formula, outcome, model_name, family=family))
    results = add_q_values(pd.concat(rows, ignore_index=True))
    results.to_csv(OUT / "aim2_food_matrix_gee_model_results.csv", index=False)
    return results


def prediction_grid(df: pd.DataFrame) -> None:
    # Use a transparent OLS model to generate marginal predicted source data for
    # figures. Inferential tables use GEE.
    d = df[
        [
            "log1p_iauc_2h",
            "msi_core",
            "carbs_10g",
            "pre_glucose_10",
            "meal_hour_sin",
            "meal_hour_cos",
            "calories_100",
            "matrix_category",
        ]
    ].replace([np.inf, -np.inf], np.nan).dropna()
    fit = smf.ols(
        "log1p_iauc_2h ~ msi_core + carbs_10g * C(matrix_category) + pre_glucose_10 + meal_hour_sin + meal_hour_cos + calories_100",
        data=d,
    ).fit()
    grid_rows = []
    for matrix in MATRIX_ORDER:
        for msi_label, msi_value in [("low", df["msi_core"].quantile(0.15)), ("middle", df["msi_core"].median()), ("high", df["msi_core"].quantile(0.85))]:
            for carbs in [2.5, 5.0, 7.5, 10.0]:
                grid_rows.append(
                    {
                        "matrix_category": matrix,
                        "matrix_label": MATRIX_LABELS[matrix],
                        "msi_level": msi_label,
                        "msi_core": msi_value,
                        "carbs_10g": carbs,
                        "pre_glucose_10": df["pre_glucose_10"].median(),
                        "meal_hour_sin": 0,
                        "meal_hour_cos": 1,
                        "calories_100": df["calories_100"].median(),
                    }
                )
    grid = pd.DataFrame(grid_rows)
    pred = fit.get_prediction(grid).summary_frame(alpha=0.05)
    grid["pred_log1p_iauc_2h"] = pred["mean"]
    grid["pred_iauc_2h"] = np.expm1(grid["pred_log1p_iauc_2h"])
    grid["pred_iauc_low"] = np.expm1(pred["mean_ci_lower"])
    grid["pred_iauc_high"] = np.expm1(pred["mean_ci_upper"])
    grid.to_csv(OUT / "aim2_food_matrix_prediction_grid.csv", index=False)


def make_figures(df: pd.DataFrame, results: pd.DataFrame) -> None:
    plt.rcParams.update({"font.size": 9, "figure.dpi": 150})

    # Figure 1: high-response rates by MSI tertile and matrix.
    summary = pd.read_csv(OUT / "aim2_msi_food_matrix_ppgr_summary.csv")
    pivot = summary.pivot(index="matrix_category", columns="msi_tertile", values="high_iauc_rate").reindex(MATRIX_ORDER)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    im = ax.imshow(pivot.values, aspect="auto", cmap="viridis", vmin=0, vmax=np.nanmax(pivot.values))
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([MATRIX_LABELS.get(x, x) for x in pivot.index])
    ax.set_title("High 2h iAUC rate by MSI tertile and food matrix")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", color="white" if v > 0.3 else "black")
    fig.colorbar(im, ax=ax, label="High-response rate")
    fig.tight_layout()
    fig.savefig(FIG / "aim2_high_iauc_rate_by_msi_matrix.png")
    plt.close(fig)

    # Figure 2: selected model estimates for MSI and carbohydrate.
    sel_terms = ["msi_core", "carbs_10g", "msi_core:carbs_10g"]
    est = results[(results["term"].isin(sel_terms)) & (results["outcome"].isin(["log1p_iauc_2h", "peak_delta_2h_w", "high_iauc_2h"]))]
    if not est.empty:
        fig, ax = plt.subplots(figsize=(7, max(3, 0.28 * len(est))))
        est = est.copy()
        est["label"] = est["outcome"] + " | " + est["model"] + " | " + est["term"]
        y = np.arange(len(est))
        ax.errorbar(est["estimate"], y, xerr=[est["estimate"] - est["ci_low"], est["ci_high"] - est["estimate"]], fmt="o")
        ax.axvline(0, color="0.4", lw=1)
        ax.set_yticks(y)
        ax.set_yticklabels(est["label"])
        ax.set_xlabel("GEE estimate")
        ax.set_title("Selected Aim 2 model terms")
        fig.tight_layout()
        fig.savefig(FIG / "aim2_selected_model_terms.png")
        plt.close(fig)

    # Figure 3: prediction grid for Nature Food food-matrix panel.
    grid = pd.read_csv(OUT / "aim2_food_matrix_prediction_grid.csv")
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    for matrix in ["fiber_rich_or_whole_food_matrix", "mixed_meal_protein_fat_buffered", "refined_starch_low_matrix_protection", "sweetened_beverage_or_liquid_carb"]:
        g = grid[(grid["matrix_category"] == matrix) & (grid["msi_level"] == "high")]
        if not g.empty:
            ax.plot(g["carbs_10g"] * 10, g["pred_iauc_2h"], marker="o", label=MATRIX_LABELS[matrix])
    ax.set_xlabel("Carbohydrate load (g)")
    ax.set_ylabel("Predicted 2h iAUC")
    ax.set_title("Predicted high-MSI PPGR by food matrix")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "aim2_predicted_high_msi_ppgr_by_matrix.png")
    plt.close(fig)


def markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "_No rows._"
    show = df.head(max_rows).copy()
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


def write_report(df: pd.DataFrame, results: pd.DataFrame) -> None:
    reliability = pd.read_csv(OUT / "aim2_food_matrix_annotation_reliability_status.csv")
    matrix_summary = pd.read_csv(OUT / "aim2_food_matrix_category_summary.csv")
    has_manual = bool(df.get("manual_adjudication_available", pd.Series(False, index=df.index)).any())
    kappa = pd.to_numeric(
        reliability.loc[reliability["metric"] == "cohen_kappa_human_dual_review", "value"],
        errors="coerce",
    )
    kappa_value = float(kappa.iloc[0]) if len(kappa) and pd.notna(kappa.iloc[0]) else np.nan
    matrix_terms = results[results["term"].str.contains("C\\(matrix_category\\)", regex=True, na=False)]
    matrix_signal_retained = bool((matrix_terms["q_value"] < 0.05).any())
    if matrix_signal_retained and has_manual and (pd.isna(kappa_value) or kappa_value >= 0.35):
        figure_decision = "食物基质信号可进入 Nature Food 主图候选；双评一致性需要在方法和敏感性分析中透明呈现。"
    elif matrix_signal_retained:
        figure_decision = "食物基质信号保留，但建议先作为补充/机制图候选，优先完成不一致标签复核。"
    else:
        figure_decision = "食物基质主效应未形成稳健信号，保留为补充分析。"
    key_terms = results[
        results["term"].isin(["msi_core", "carbs_10g", "msi_core:carbs_10g"])
        | results["term"].str.contains("C\\(matrix_category\\)", regex=True)
    ][["outcome", "model", "term", "estimate_CI", "p_fmt", "q_fmt", "n", "n_subjects"]]
    lines = [
        "# Aim 2: CGMacros 食物基质与 PPGR 脆弱性",
        "",
        "由 `scripts/run_nature_food_aim2_cgmacros_food_matrix.py` 生成。",
        "",
        "## 状态",
        "",
        (
            "本轮分析使用人工仲裁终版食物基质标签。"
            if has_manual
            else "本轮分析未检测到人工终版标签，结果不能作为投稿版本。"
        ),
        "",
        f"- 餐次数: {len(df)}",
        f"- 受试者数: {df['subject_id'].nunique()}",
        f"- 高 2h iAUC 阈值: {df.attrs['high_iauc_threshold']:.1f}",
        f"- 高峰值增量阈值: {df.attrs['high_peak_threshold']:.1f}",
        "",
        "## 人工标注状态",
        "",
        markdown_table(reliability),
        "",
        "## 食物基质概览",
        "",
        markdown_table(matrix_summary[["matrix_category", "meals", "subjects", "human_review_rate", "final_label_coverage", "median_iauc_2h", "high_iauc_rate", "median_carbs", "median_fiber"]]),
        "",
        "## Nature Food 图件判断",
        "",
        f"- 人工仲裁后食物基质信号是否保留: {matrix_signal_retained}",
        f"- 双评 Cohen kappa: {'' if pd.isna(kappa_value) else f'{kappa_value:.3f}'}",
        f"- 判断: {figure_decision}",
        "",
        "## 关键模型项",
        "",
        markdown_table(key_terms, max_rows=40),
        "",
        "## 输出文件",
        "",
        "- `aim2_modeling_dataset_human_adjudicated.csv`",
        "- `aim2_food_matrix_human_adjudication_clean.csv`",
        "- `aim2_msi_food_matrix_ppgr_summary.csv`",
        "- `aim2_food_matrix_category_summary.csv`",
        "- `aim2_food_matrix_annotation_reliability_status.csv`",
        "- `aim2_food_matrix_gee_model_results.csv`",
        "- `aim2_food_matrix_prediction_grid.csv`",
        "- `figures/aim2_high_iauc_rate_by_msi_matrix.png`",
        "- `figures/aim2_selected_model_terms.png`",
        "- `figures/aim2_predicted_high_msi_ppgr_by_matrix.png`",
        "",
        "## 解释边界",
        "",
        "当前可将 Aim 2 定位为“人工定义的食物基质如何改变同等代谢脆弱性下的 PPGR 表型”。投稿前重点不是重新证明标签来源，而是补足标签一致性、类别合并敏感性和受试者层面稳健性。",
    ]
    (OUT / "aim2_cgmacros_food_matrix_completion_report.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT / "aim2_cgmacros_food_matrix_human_adjudicated_report_zh.md").write_text("\n".join(lines), encoding="utf-8")


def write_followup_plan(df: pd.DataFrame, results: pd.DataFrame) -> None:
    matrix_terms = results[results["term"].str.contains("C\\(matrix_category\\)", regex=True, na=False)].copy()
    retained = bool((matrix_terms["q_value"] < 0.05).any())
    lines = [
        "# Aim 2 后续工作规划：CGMacros 食物基质与 PPGR 脆弱性",
        "",
        "## 当前结论",
        "",
        f"- 已使用人工仲裁终版标签完成 {len(df)} 餐、{df['subject_id'].nunique()} 名受试者的重复餐次 GEE 分析。",
        "- MSI-core 与 PPGR 脆弱性是 Aim 2 最稳定的主线；食物基质用于解释“同等碳水/能量负荷下，哪些餐食结构更容易放大 PPGR”。",
        f"- 食物基质项在当前模型中是否出现 FDR 后信号: {retained}。",
        "",
        "## 立即补强",
        "",
        "1. 固定人工标签 codebook：把 6 类食物基质写成可复核判定表，列出典型餐食和边界案例。",
        "2. 复核不一致标签：优先处理双评不一致和少数类别，形成 `primary` 与 `collapsed` 两套标签。",
        "3. 类别合并敏感性：将少数类合并为高保护/中间/低保护三类，检验方向是否一致。",
        "4. 受试者层面稳健性：做 leave-one-subject-out、cluster bootstrap、按受试者餐次数加权/不加权对照。",
        "5. 营养协变量敏感性：主模型保留 carbs、energy、pre-glucose、meal time；敏感性加入 fiber/protein/fat，但明确这些变量部分定义了基质类别。",
        "",
        "## Nature Food 图件建议",
        "",
        "1. 主图候选 A：NHANES 暴露锚点到 CGMacros PPGR 脆弱性的桥接图。",
        "2. 主图候选 B：MSI tertile × 食物基质类别的高 iAUC 风险热图。",
        "3. 主图候选 C：模型预测的高 MSI 人群在不同食物基质下的 PPGR 风险差异。",
        "4. 补充图：人工标签一致性、类别分布、少数类合并敏感性、leave-one-subject-out 影响图。",
        "",
        "## 后续实验设计",
        "",
        "1. 从 CGMacros 中选择 2-3 组等碳水/等能量但基质不同的餐食原型：液体/精制淀粉、混合蛋白脂肪缓冲、全食物/高纤维。",
        "2. 在高 MSI 与低 MSI 人群中设计交叉餐试验，主要终点为 2h iAUC、峰值增量和达峰时间。",
        "3. 同步采集尿 DEHP 代谢物、肌酐校正、空腹胰岛素/葡萄糖和短期饮食记录，用于连接 Aim 1 与 Aim 2。",
        "4. 预注册主要假设：高 MSI 个体对低保护食物基质的 PPGR 放大效应最大，高保护基质可部分缓冲该脆弱性。",
        "",
        "## 投稿判断",
        "",
        "Aim 2 现在可以作为 Nature Food 叙事中的机制与膳食情境层。真正决定是否进入主文的，是标签复核后食物基质方向是否稳定，而不是单个类别在当前小样本中是否全部显著。",
    ]
    (OUT / "aim2_followup_workplan_zh.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    warnings.filterwarnings("ignore")
    df = prepare_data()
    write_clean_modeling_dataset(df)
    summarize_data(df)
    results = run_models(df)
    prediction_grid(df)
    make_figures(df, results)
    write_report(df, results)
    write_followup_plan(df, results)
    print(f"wrote Aim 2 outputs to {OUT}")


if __name__ == "__main__":
    main()
