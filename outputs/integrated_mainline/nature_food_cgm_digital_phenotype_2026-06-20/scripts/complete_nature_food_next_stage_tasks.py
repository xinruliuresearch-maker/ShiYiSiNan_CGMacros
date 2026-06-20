"""Complete the Nature Food next-stage task bundle.

Outputs:
- locked submission route and presubmission materials
- six main figures with source data
- Aim 1 food-system exposure anchor hardening
- Aim 2 to Aim 3 CGMacros phase/order-parameter bridge analysis
- integrated phenotype research software prototype
- reviewer risk response memo and manuscript skeleton
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(r"D:\ai for science")
P0 = ROOT / "results" / "nature_food_p0_publication_lift_2026_06_18"
NF_FIG = ROOT / "results" / "nature_food_manuscript_package" / "figure_source_data"
NF_AIM2 = ROOT / "results" / "nature_food_aim2_cgmacros"
NF_AIMS = ROOT / "results" / "nature_food_high_bar_aims"
NF_ROBUST = ROOT / "results" / "nature_food_p0_robustness"
NPJ_P0 = ROOT / "results" / "npj_digital_medicine_phase_strategy" / "p0_workup"
NPJ_EXT = ROOT / "results" / "npj_digital_medicine_phase_strategy" / "p0_extensions_2026_06_18"
JAEB = ROOT / "results" / "jaeb_glycemic_phase_completion"

DOCS = P0 / "docs"
TABLES = P0 / "tables"
FIGSRC = P0 / "figure_source_data"
FIGS = P0 / "figures"
LEGENDS = P0 / "figure_legends"
SOFTWARE = P0 / "software_release" / "integrated_food_cgm_phenotype_v0_1"
for p in [DOCS, TABLES, FIGSRC, FIGS, LEGENDS, SOFTWARE]:
    p.mkdir(parents=True, exist_ok=True)


plt.rcParams.update(
    {
        "figure.dpi": 160,
        "savefig.dpi": 300,
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


COLORS = {
    "green": "#1f6f64",
    "teal": "#4aa39a",
    "orange": "#c46f2a",
    "blue": "#426a9f",
    "purple": "#7a5c9e",
    "red": "#b34d4d",
    "gray": "#6a706d",
    "light": "#edf2ef",
    "line": "#d7d4cb",
}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def write(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def fmt(x: object, digits: int = 3) -> str:
    try:
        if pd.isna(x):
            return "NA"
        return f"{float(x):.{digits}f}"
    except Exception:
        return str(x)


def val(df: pd.DataFrame, **where) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for k, v in where.items():
        mask &= df[k].eq(v)
    out = df[mask]
    if out.empty:
        raise KeyError(where)
    return out.iloc[0]


def savefig(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGS / f"{name}.png", bbox_inches="tight")
    fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def collapse_matrix(cat: object) -> str:
    c = str(cat)
    if c in {"fiber_rich_or_whole_food_matrix", "low_carb_or_protein_forward"}:
        return "protective_whole_food_or_low_carb"
    if c in {"mixed_meal_protein_fat_buffered", "mixed_or_unknown_matrix"}:
        return "mixed_buffered_or_unknown"
    if c in {"refined_starch_low_matrix_protection", "sweetened_beverage_or_liquid_carb"}:
        return "rapid_digestible_or_liquid_carb"
    return "unknown"


def ols_one(x: pd.Series, y: pd.Series) -> dict[str, float]:
    data = pd.DataFrame({"x": x, "y": y}).replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < 5 or data["x"].nunique() < 2:
        return {"n": len(data), "beta": np.nan, "se": np.nan, "ci_low": np.nan, "ci_high": np.nan, "p_value": np.nan}
    X = np.column_stack([np.ones(len(data)), data["x"].to_numpy(float)])
    yv = data["y"].to_numpy(float)
    beta = np.linalg.lstsq(X, yv, rcond=None)[0]
    resid = yv - X @ beta
    dof = len(data) - 2
    mse = float((resid @ resid) / dof)
    cov = mse * np.linalg.inv(X.T @ X)
    se = float(np.sqrt(cov[1, 1]))
    t = float(beta[1] / se) if se else np.nan
    p = float(2 * stats.t.sf(abs(t), dof)) if math.isfinite(t) else np.nan
    ci = 1.96 * se
    return {
        "n": len(data),
        "beta": float(beta[1]),
        "se": se,
        "ci_low": float(beta[1] - ci),
        "ci_high": float(beta[1] + ci),
        "p_value": p,
    }


def load_inputs() -> dict[str, pd.DataFrame]:
    return {
        "claim": read_csv(TABLES / "p0_claim_hierarchy.csv"),
        "source": read_csv(TABLES / "p0_aim1_food_system_exposure_matrix.csv"),
        "phase_assign": read_csv(TABLES / "p0_aim2_cgmacros_phase_map_assignment.csv"),
        "meal": read_csv(NF_AIM2 / "aim2_modeling_dataset_human_adjudicated.csv"),
        "nhanes_main": read_csv(NF_FIG / "figure2a_nhanes_main_effects.csv"),
        "nhanes_comp": read_csv(NF_FIG / "figure2b_nhanes_composition_adjusted.csv"),
        "cg_msi": read_csv(NF_FIG / "figure3a_cgmacros_msi_ppgr_effects.csv"),
        "cg_matrix": read_csv(NF_FIG / "figure3c_collapsed_matrix_gee.csv"),
        "cg_six": read_csv(NF_FIG / "figure3b_food_matrix_6class_summary.csv"),
        "cg_ladder": read_csv(NF_FIG / "figure4a_loso_model_ladder.csv"),
        "cf": read_csv(NF_FIG / "figure4b_counterfactual_high_iauc_deltas.csv"),
        "leverage": read_csv(NF_AIMS / "aim2_subject_leverage_locked.csv"),
        "phase_stab": read_csv(JAEB / "tables" / "locked_phase_bootstrap_stability.csv"),
        "phase_features": read_csv(JAEB / "tables" / "locked_glycemic_phase_features.csv"),
        "cgm_long": read_csv(JAEB / "tables" / "locked_cgm_summary_long.csv"),
        "loop": read_csv(NPJ_P0 / "tables" / "loop_frozen_external_validation_metrics.csv"),
        "secondary": read_csv(NPJ_EXT / "tables" / "secondary_external_validation_metrics.csv"),
        "calibration": read_csv(NPJ_EXT / "tables" / "loop_loso_calibration_upgrade_metrics.csv"),
        "fairness": read_csv(NPJ_EXT / "tables" / "subgroup_fairness_calibration_audit_with_bootstrap_ci.csv"),
        "bridge_design": read_csv(ROOT / "results" / "integrated_food_cgm_metabolic_phenotype_study_2026_06_18" / "tables" / "bridge_cohort_design_matrix.csv"),
    }


def submission_materials(d: dict[str, pd.DataFrame]) -> None:
    route = pd.DataFrame(
        [
            {
                "decision": "short_line_submission_form",
                "locked_choice": "Nature Food Analysis presubmission now",
                "reason": "Existing evidence is strong triangulation across NHANES, CGMacros and JAEB/Loop/PSO, but not same-person causal-chain evidence.",
                "allowed_claim": "Food-system exposure context, meal matrix and CGM digital phenotype align across complementary cohorts.",
                "prohibited_claim": "Plasticizer exposure directly causes PPGR or phase membership in the same individuals.",
            },
            {
                "decision": "long_line_submission_form",
                "locked_choice": "Nature Food Article after Aim 4 pilot",
                "reason": "Article-level claim requires urine and food-contact plasticizer assay, standardized meal PPGR and 14-28 day CGM in the same people.",
                "allowed_claim": "Same-person exposure-meal-CGM phenotype chain if Aim 4 is completed.",
                "prohibited_claim": "Clinical decision support or intervention efficacy without prospective validation.",
            },
        ]
    )
    route.to_csv(TABLES / "NatureFood_route_decision_memo.csv", index=False)

    nh = d["nhanes_main"]
    cg_ladder = d["cg_ladder"]
    phase_stab = d["phase_stab"]
    loop_phase = d["loop"][d["loop"]["feature_set"].eq("C4_phase_map")]
    secondary_phase = d["secondary"][(d["secondary"]["feature_set"].eq("C4_phase_map")) & (d["secondary"]["status"].eq("evaluable"))]
    pct_msi = val(nh, outcome="msi_core_partial", exposure="pct_oxidative_10")
    m1 = cg_ladder[cg_ladder["model"].eq("M1_macro_timing")].iloc[0]
    m3 = cg_ladder[cg_ladder["model"].eq("M3_MSI_food_matrix")].iloc[0]

    abstract = (
        "Food systems shape metabolic health through chemical exposures and meal structure, but these layers are rarely connected to continuous glucose monitoring (CGM) phenotypes. "
        "We integrated NHANES 2013-2018 biomonitoring, CGMacros real-world meal responses and JAEB-derived CGM trials to define a multi-timescale phenotype of metabolic vulnerability. "
        f"In NHANES, a 10 percentage-point higher oxidative DEHP fraction was associated with MSI-core (beta {fmt(pct_msi.effect)}). "
        f"In CGMacros, adding MSI and food matrix improved subject-held-out high-iAUC discrimination from {fmt(m1.high_iauc_auc)} to {fmt(m3.high_iauc_auc)}, and meal redesign suggested lower high-iAUC risk. "
        f"In JAEB/Loop/PSO datasets, a locked CGM phase-map was stable (ARI median {fmt(phase_stab.adjusted_rand_index.median())}) and transported externally for HbA1c/TIR response ranking. "
        "These results support triangulated evidence for a food-system-to-CGM digital phenotype and define the bridge cohort needed for same-person validation."
    )
    write(DOCS / "NatureFood_150_word_abstract_v1.0.md", "# Nature Food 150-word Abstract v1.0\n\n" + abstract)

    enquiry = f"""
# Nature Food Presubmission Enquiry v1.0

## Proposed title

Food-system exposures and meal matrices define CGM digital phenotypes of metabolic vulnerability

## Article type requested

We request editorial advice on suitability as a Nature Food **Analysis**. The current manuscript integrates existing population, meal-response and CGM-trial datasets. We also outline a prospective bridge cohort that would upgrade the work to an Article-level same-person validation.

## Rationale for Nature Food

The manuscript addresses a food-systems question rather than a conventional diabetes prediction benchmark: how food-system chemical exposure context and meal matrix structure shape metabolic susceptibility measurable by CGM. It connects Food Chemistry/Food Processing, Human Nutrition, Information Technology and Public Health Nutrition.

## Current evidence

1. NHANES 2013-2018 anchors food-system exposure context and DEHP oxidative profile to MSI/HOMA-IR/HbA1c.
2. CGMacros shows that MSI-core and food matrix organize postprandial glucose vulnerability across repeated real meals.
3. JAEB/Loop/PSO validate a frozen CGM phase-map as a longer-horizon digital phenotype and response-ranking language.
4. CGMacros raw CGM is compatible with frozen phase-map assignment, supporting a bridge between meal-response and digital phenotype language.

## Claims and guardrails

We frame the current manuscript as triangulated evidence. We do not claim same-person causality from plasticizer exposure to PPGR or CGM phase membership. We do not present counterfactual meal redesign as intervention efficacy. We do not present the phase-map as autonomous clinical decision support.

## Planned upgrade

An 80-120 participant bridge cohort will measure urine and food-contact plasticizer panels, standardized 2x2 meal challenges and 14-28 day CGM to directly test exposure -> MSI -> PPGR -> CGM order parameters.
"""
    write(DOCS / "NatureFood_presubmission_enquiry_v1.0.md", enquiry)


def aim1_hardening(d: dict[str, pd.DataFrame]) -> None:
    source = d["source"].copy()
    source["main_text_candidate"] = source["nature_food_use"].isin(["main_or_extended_data", "supportive_extended_data"])
    source["claim_level"] = np.where(
        source["nature_food_use"].eq("main_or_extended_data"),
        "main_or_extended",
        np.where(source["nature_food_use"].eq("supportive_extended_data"), "extended_supportive", "supplement_context"),
    )
    source.to_csv(TABLES / "Aim1_source_proxy_to_DEHP_and_metabolic_anchor.csv", index=False)
    source.to_csv(FIGSRC / "Figure2_population_exposure_anchor_source.csv", index=False)

    schema = pd.DataFrame(
        [
            ("source_id", "string", "Unique literature source identifier."),
            ("citation", "string", "Full citation or DOI."),
            ("country_year", "string", "Country and sampling year."),
            ("food_category", "string", "Food category mapped to NHANES/CGMacros."),
            ("packaging_contact", "string", "Packaging or food-contact context."),
            ("processing_level", "string", "Fresh/minimally processed/processed/ultra-processed proxy."),
            ("analyte", "string", "DEHP, DiNP, DiDP, DBP, DiBP, BBzP, DINCH, DEHT or metabolites if applicable."),
            ("concentration", "numeric", "Reported concentration."),
            ("unit", "string", "ng/g wet weight, ng/mL, ug/kg or original unit."),
            ("lod_handling", "string", "LOD/LOQ and nondetect handling."),
            ("sample_size", "numeric", "Number of food samples."),
            ("mapping_confidence", "categorical", "high, moderate or low confidence mapping."),
            ("use_in_manuscript", "categorical", "main, extended, supplement or exclude."),
        ],
        columns=["field", "type", "description"],
    )
    schema.to_csv(TABLES / "Aim1_food_plasticizer_panel_literature_extraction_schema.csv", index=False)

    guardrails = """
# Aim 1 Claim Guardrails

## Use

- Use NHANES source-oriented results to establish food-system context.
- Use urinary DEHP oxidative profile as the population biomonitoring anchor.
- Use the plasticizer measurement panel and sampling frame as planned measurement infrastructure unless measured concentrations are available.

## Do not use

- Do not describe the current sampling frame as measured food plasticizer concentrations.
- Do not infer packaging-specific exposure from NHANES dietary proxies alone.
- Do not treat DEHP oxidative fraction as a direct dose measure; it is an exposure-metabolism composition signal.

## Main-text language

Acceptable: "Food-system source proxies and DEHP oxidative profile jointly anchor a population-level susceptibility signal."

Not acceptable: "Packaged foods caused PPGR vulnerability through measured plasticizer burden in these participants."
"""
    write(DOCS / "Aim1_claim_guardrails.md", guardrails)


def aim2_aim3_bridge(d: dict[str, pd.DataFrame]) -> None:
    meal = d["meal"].copy()
    phase = d["phase_assign"].copy()
    meal["participant_id"] = meal["subject_id"].astype(str)
    phase["participant_id"] = phase["participant_id"].astype(str)
    meal["matrix_collapsed3_bridge"] = meal["food_matrix_final_category"].map(collapse_matrix)

    subj = (
        meal.groupby("participant_id")
        .agg(
            meals=("meal_time", "count"),
            msi_core=("msi_core", "mean"),
            median_iauc_2h=("iauc_2h", "median"),
            mean_log1p_iauc_2h=("log1p_iauc_2h", "mean"),
            high_iauc_rate=("high_iauc_2h", "mean"),
            median_peak_delta_2h=("peak_delta_2h", "median"),
            mean_carbs=("carbs", "mean"),
            prop_protective=("matrix_collapsed3_bridge", lambda s: float((s == "protective_whole_food_or_low_carb").mean())),
            prop_mixed=("matrix_collapsed3_bridge", lambda s: float((s == "mixed_buffered_or_unknown").mean())),
            prop_rapid_liquid=("matrix_collapsed3_bridge", lambda s: float((s == "rapid_digestible_or_liquid_carb").mean())),
        )
        .reset_index()
    )
    bridge = subj.merge(phase, on="participant_id", how="inner")
    bridge.to_csv(TABLES / "Aim2_Aim3_CGMacros_phase_bridge_dataset.csv", index=False)
    bridge.to_csv(FIGSRC / "Figure4_phase_compatibility_source_data.csv", index=False)

    predictors = ["msi_core", "median_iauc_2h", "high_iauc_rate", "prop_mixed", "prop_rapid_liquid"]
    outcomes = [
        "glycemic_burden_score",
        "hypoglycemic_susceptibility_score",
        "dynamic_instability_score",
        "resilience_proxy_score",
        "phase_assignment_distance",
        "cgm_mean_glucose_mg_dl",
        "cgm_time_in_range_70_180_pct",
        "cgm_cv_pct",
    ]
    rows = []
    for out in outcomes:
        for pred in predictors:
            data = bridge[[pred, out]].replace([np.inf, -np.inf], np.nan).dropna()
            ols = ols_one(data[pred], data[out])
            if len(data) >= 5 and data[pred].nunique() > 1:
                rho, p = stats.spearmanr(data[pred], data[out], nan_policy="omit")
            else:
                rho, p = np.nan, np.nan
            rows.append(
                {
                    "outcome": out,
                    "predictor": pred,
                    **ols,
                    "spearman_rho": float(rho) if not pd.isna(rho) else np.nan,
                    "spearman_p": float(p) if not pd.isna(p) else np.nan,
                    "interpretation": "compatibility_order_parameter_bridge_not_clinical_phase_validation",
                }
            )
    models = pd.DataFrame(rows)
    models["p_value_rank"] = models["p_value"].rank(method="first")
    p_values = models["p_value"].to_numpy(float)
    q_values = np.full(len(models), np.nan)
    finite = np.isfinite(p_values)
    if finite.any():
        finite_idx = np.where(finite)[0]
        ordered = finite_idx[np.argsort(p_values[finite])]
        ranked = p_values[ordered] * len(ordered) / np.arange(1, len(ordered) + 1)
        ranked = np.minimum.accumulate(ranked[::-1])[::-1]
        q_values[ordered] = np.clip(ranked, 0, 1)
    models["q_value"] = q_values
    models["model"] = "participant_level_ols_bridge"
    models["term"] = models["predictor"]
    models["beta_or_estimate"] = models["beta"]
    models["ci"] = models.apply(lambda r: f"{r.ci_low:.4g} to {r.ci_high:.4g}", axis=1)
    models["direction"] = np.where(models["beta"] >= 0, "positive", "negative")
    models = models[
        [
            "model",
            "outcome",
            "term",
            "n",
            "beta_or_estimate",
            "ci",
            "p_value",
            "q_value",
            "spearman_rho",
            "spearman_p",
            "direction",
            "interpretation",
        ]
    ]
    models.to_csv(TABLES / "Aim2_Aim3_CGMacros_phase_bridge_models.csv", index=False)

    guardrails = f"""
# Aim 2 to Aim 3 Phase Bridge Guardrails

CGMacros raw CGM can be transformed into the locked phase-map input schema for all {len(bridge)} participants. The bridge analysis should use continuous order parameters and assignment distance rather than claiming a validated categorical clinical phase distribution.

## Why

The CGMacros nutrition cohort is lower-glycaemic-burden than the JAEB diabetes reference set. In the P0 assignment, most participants mapped to the stable-in-range phase. This is useful for compatibility and ranking, but it is not proof that the JAEB phase taxonomy is clinically validated in CGMacros.

## Allowed language

"CGMacros raw CGM supported frozen phase-map compatibility; order parameters were used as a continuous bridge between meal-response phenotypes and longer-horizon CGM digital phenotype language."

## Prohibited language

"CGMacros participants were clinically classified into validated JAEB phases."
"""
    write(DOCS / "Aim2_Aim3_phase_bridge_guardrails.md", guardrails)


def build_integrated_software() -> None:
    if SOFTWARE.exists():
        # Preserve the directory root but refresh generated files.
        shutil.rmtree(SOFTWARE)
    (SOFTWARE / "integrated_food_cgm").mkdir(parents=True, exist_ok=True)
    (SOFTWARE / "schemas").mkdir(parents=True, exist_ok=True)
    (SOFTWARE / "toy_data").mkdir(parents=True, exist_ok=True)
    (SOFTWARE / "tests").mkdir(parents=True, exist_ok=True)
    (SOFTWARE / "assets").mkdir(parents=True, exist_ok=True)

    phase_ref_src = NPJ_EXT / "software_release" / "phase_map_jaeb_v0_1" / "phase_map" / "assets" / "phase_reference.json"
    shutil.copy2(phase_ref_src, SOFTWARE / "assets" / "phase_reference.json")

    (SOFTWARE / "integrated_food_cgm" / "__init__.py").write_text(
        "from .core import assign_phase, integrated_phenotype_report\n", encoding="utf-8"
    )
    core = r'''
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = PACKAGE_ROOT / "assets" / "phase_reference.json"

REQUIRED_CGM = [
    "cgm_mean_glucose_mg_dl",
    "cgm_time_in_range_70_180_pct",
    "cgm_time_below_70_pct",
    "cgm_time_below_54_pct",
    "cgm_time_above_180_pct",
    "cgm_time_above_250_pct",
    "cgm_cv_pct",
]

ORDER_COLS = [
    "glycemic_burden_score",
    "hypoglycemic_susceptibility_score",
    "dynamic_instability_score",
    "circadian_disruption_score",
    "resilience_proxy_score",
]


def _load_reference() -> dict:
    return json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))


def _z(series: pd.Series, ref: dict, name: str) -> pd.Series:
    mean = ref["feature_reference"][name]["mean"]
    sd = ref["feature_reference"][name]["sd"]
    if not sd:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (pd.to_numeric(series, errors="coerce") - mean) / sd


def assign_phase(input_frame: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_CGM if c not in input_frame.columns]
    if missing:
        raise ValueError(f"Missing required CGM columns: {missing}")
    ref = _load_reference()
    out = input_frame.copy()
    out["cgm_sd_proxy"] = out["cgm_mean_glucose_mg_dl"] * out["cgm_cv_pct"] / 100.0
    out["glycemic_burden_score"] = (
        _z(out["cgm_mean_glucose_mg_dl"], ref, "cgm_mean_glucose_mg_dl")
        + _z(out["cgm_time_above_180_pct"], ref, "cgm_time_above_180_pct")
        + _z(out["cgm_time_above_250_pct"], ref, "cgm_time_above_250_pct")
        - _z(out["cgm_time_in_range_70_180_pct"], ref, "cgm_time_in_range_70_180_pct")
    ) / 4.0
    out["hypoglycemic_susceptibility_score"] = (
        _z(out["cgm_time_below_70_pct"], ref, "cgm_time_below_70_pct")
        + _z(out["cgm_time_below_54_pct"], ref, "cgm_time_below_54_pct")
    ) / 2.0
    out["dynamic_instability_score"] = (
        _z(out["cgm_cv_pct"], ref, "cgm_cv_pct")
        + _z(out["cgm_sd_proxy"], ref, "cgm_sd_proxy")
    ) / 2.0
    out["circadian_disruption_score"] = 0.0
    out["resilience_proxy_score"] = (
        _z(out["cgm_time_above_250_pct"], ref, "cgm_time_above_250_pct")
        + _z(out["cgm_cv_pct"], ref, "cgm_cv_pct")
        + _z(out["cgm_mean_glucose_mg_dl"], ref, "cgm_mean_glucose_mg_dl")
    ) / 3.0
    centroids = pd.DataFrame(ref["centroids"])
    x = out[ORDER_COLS].fillna(0).to_numpy(float)
    dist = []
    for _, row in centroids.iterrows():
        c = row[ORDER_COLS].to_numpy(float)
        dist.append(np.sqrt(((x - c) ** 2).sum(axis=1)))
    dist_mat = np.vstack(dist).T
    nearest = dist_mat.argmin(axis=1)
    out["phase_label"] = [centroids.iloc[i]["phase_label"] for i in nearest]
    out["phase_assignment_distance"] = dist_mat.min(axis=1)
    dictionary = pd.DataFrame(ref["phase_dictionary"])
    out["phase_id"] = out["phase_label"].map(dict(zip(dictionary["phase_label_zh"], dictionary["phase_id"])))
    out["phase_label_en"] = out["phase_label"].map(dict(zip(dictionary["phase_label_zh"], dictionary["phase_label_en"])))
    return out


def _matrix_score(value: object) -> float:
    mapping = {
        "protective_whole_food_or_low_carb": -0.5,
        "fiber_rich_or_whole_food_matrix": -0.5,
        "low_carb_or_protein_forward": -0.5,
        "mixed_buffered_or_unknown": 0.35,
        "mixed_meal_protein_fat_buffered": 0.35,
        "mixed_or_unknown_matrix": 0.35,
        "rapid_digestible_or_liquid_carb": 0.65,
        "refined_starch_low_matrix_protection": 0.65,
        "sweetened_beverage_or_liquid_carb": 0.65,
    }
    return mapping.get(str(value), 0.0)


def integrated_phenotype_report(input_frame: pd.DataFrame) -> pd.DataFrame:
    out = assign_phase(input_frame)
    for col in ["msi_core", "carbs_10g", "pre_glucose_10", "calories_100"]:
        if col not in out.columns:
            out[col] = 0.0
    if "matrix_collapsed3" not in out.columns:
        out["matrix_collapsed3"] = "unknown"
    linear = (
        -1.10
        + 1.388 * pd.to_numeric(out["msi_core"], errors="coerce").fillna(0)
        + 0.008 * pd.to_numeric(out["carbs_10g"], errors="coerce").fillna(0)
        - 0.203 * pd.to_numeric(out["pre_glucose_10"], errors="coerce").fillna(0)
        - 0.016 * pd.to_numeric(out["calories_100"], errors="coerce").fillna(0)
        + out["matrix_collapsed3"].map(_matrix_score).fillna(0)
    )
    out["meal_high_iauc_ranking_score"] = 1 / (1 + np.exp(-linear))
    out["risk_language"] = "ranking_only_not_absolute_clinical_risk"
    return out
'''
    (SOFTWARE / "integrated_food_cgm" / "core.py").write_text(core.strip() + "\n", encoding="utf-8")

    schema = pd.DataFrame(
        [
            ("participant_id", "string", "required", "Unique participant identifier."),
            ("msi_core", "numeric", "recommended", "Metabolic susceptibility index."),
            ("matrix_collapsed3", "string", "recommended", "Collapsed food matrix class."),
            ("carbs_10g", "numeric", "recommended", "Meal carbohydrate per 10 g."),
            ("pre_glucose_10", "numeric", "recommended", "Pre-meal glucose per 10 mg/dL."),
            ("calories_100", "numeric", "recommended", "Meal calories per 100 kcal."),
            ("cgm_mean_glucose_mg_dl", "numeric", "required", "CGM mean glucose."),
            ("cgm_time_in_range_70_180_pct", "numeric", "required", "CGM time in range."),
            ("cgm_time_below_70_pct", "numeric", "required", "CGM time below 70."),
            ("cgm_time_below_54_pct", "numeric", "required", "CGM time below 54."),
            ("cgm_time_above_180_pct", "numeric", "required", "CGM time above 180."),
            ("cgm_time_above_250_pct", "numeric", "required", "CGM time above 250."),
            ("cgm_cv_pct", "numeric", "required", "CGM coefficient of variation."),
        ],
        columns=["field", "type", "requirement", "description"],
    )
    schema.to_csv(SOFTWARE / "schemas" / "integrated_input_schema.csv", index=False)

    toy = pd.DataFrame(
        [
            {
                "participant_id": "toy_001",
                "msi_core": -0.4,
                "matrix_collapsed3": "protective_whole_food_or_low_carb",
                "carbs_10g": 4.5,
                "pre_glucose_10": 10.5,
                "calories_100": 5.2,
                "cgm_mean_glucose_mg_dl": 112,
                "cgm_time_in_range_70_180_pct": 96,
                "cgm_time_below_70_pct": 1,
                "cgm_time_below_54_pct": 0,
                "cgm_time_above_180_pct": 3,
                "cgm_time_above_250_pct": 0,
                "cgm_cv_pct": 18,
            },
            {
                "participant_id": "toy_002",
                "msi_core": 0.8,
                "matrix_collapsed3": "mixed_buffered_or_unknown",
                "carbs_10g": 8.5,
                "pre_glucose_10": 12.2,
                "calories_100": 9.5,
                "cgm_mean_glucose_mg_dl": 168,
                "cgm_time_in_range_70_180_pct": 70,
                "cgm_time_below_70_pct": 2,
                "cgm_time_below_54_pct": 0.5,
                "cgm_time_above_180_pct": 28,
                "cgm_time_above_250_pct": 4,
                "cgm_cv_pct": 32,
            },
        ]
    )
    toy.to_csv(SOFTWARE / "toy_data" / "toy_integrated_input.csv", index=False)
    test = r'''
import unittest
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from integrated_food_cgm import integrated_phenotype_report


class IntegratedPackageTest(unittest.TestCase):
    def test_toy_data_runs(self):
        df = pd.read_csv(ROOT / "toy_data" / "toy_integrated_input.csv")
        out = integrated_phenotype_report(df)
        self.assertEqual(len(out), 2)
        self.assertIn("phase_id", out.columns)
        self.assertIn("meal_high_iauc_ranking_score", out.columns)
        self.assertTrue(out["meal_high_iauc_ranking_score"].between(0, 1).all())


if __name__ == "__main__":
    unittest.main()
'''
    (SOFTWARE / "tests" / "test_integrated_package.py").write_text(test.strip() + "\n", encoding="utf-8")
    readme = """
# Integrated Food-CGM Phenotype v0.1

Research prototype for producing an integrated participant-level phenotype report:

- MSI/meal matrix inputs
- meal high-iAUC ranking score
- locked JAEB-derived CGM phase-map assignment
- risk-language guardrail

This is not a clinical decision system. The meal-risk output is a ranking score derived from locked study coefficients and should not be interpreted as calibrated absolute risk.

## Test

```bash
python -m unittest discover -s tests
```
"""
    write(SOFTWARE / "README.md", readme)
    write(SOFTWARE / "requirements.txt", "numpy\npandas\n")
    write(SOFTWARE / "VERSION", "integrated-food-cgm-phenotype-v0.1")
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SOFTWARE, check=True)
    for cache_dir in SOFTWARE.rglob("__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)


def figures(d: dict[str, pd.DataFrame]) -> None:
    # Figure 1
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.axis("off")
    nodes = [
        ("Food-system\nsource context", 0.08, 0.62, COLORS["orange"]),
        ("DEHP oxidative\nprofile", 0.25, 0.62, COLORS["orange"]),
        ("Metabolic\nsusceptibility", 0.42, 0.62, COLORS["green"]),
        ("Meal matrix\ncontext", 0.42, 0.30, COLORS["teal"]),
        ("PPGR\nvulnerability", 0.61, 0.46, COLORS["green"]),
        ("CGM phase-map\ndigital phenotype", 0.80, 0.46, COLORS["blue"]),
        ("Bridge cohort:\nurine + food assay + meals + CGM", 0.55, 0.08, COLORS["purple"]),
    ]
    for label, x, y, color in nodes:
        ax.text(x, y, label, ha="center", va="center", color="white", fontsize=10, bbox=dict(boxstyle="round,pad=0.45", fc=color, ec="none"))
    edges = [
        (0.15, 0.62, 0.20, 0.62, "direct"),
        (0.31, 0.62, 0.36, 0.62, "direct"),
        (0.47, 0.58, 0.56, 0.50, "direct"),
        (0.47, 0.33, 0.56, 0.43, "direct"),
        (0.67, 0.46, 0.73, 0.46, "bridge"),
        (0.58, 0.15, 0.78, 0.38, "bridge"),
    ]
    pd.DataFrame(nodes, columns=["node_label", "x", "y", "color"]).to_csv(FIGSRC / "Figure1_integrated_architecture_nodes.csv", index=False)
    pd.DataFrame(edges, columns=["x_start", "y_start", "x_end", "y_end", "edge_type"]).to_csv(FIGSRC / "Figure1_integrated_architecture_edges.csv", index=False)
    for x1, y1, x2, y2, kind in edges:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=2, color=COLORS["green"] if kind == "direct" else COLORS["purple"], linestyle="-" if kind == "direct" else "--"))
    ax.text(0.02, 0.95, "Figure 1. Evidence architecture", fontsize=13, weight="bold")
    ax.text(0.02, 0.89, "Solid arrows: direct current evidence. Dashed arrows: bridge-needed same-person validation.", color=COLORS["gray"])
    savefig(fig, "Figure1_integrated_architecture")

    # Figure 2
    nh = d["nhanes_main"]
    main_rows = pd.DataFrame(
        [
            val(nh, outcome="msi_core_partial", exposure="pct_oxidative_10"),
            val(nh, outcome="ln_HOMA_IR", exposure="pct_oxidative_10"),
            val(nh, outcome="HbA1c", exposure="pct_oxidative_10"),
        ]
    )
    labels = ["MSI-core", "HOMA-IR %", "HbA1c"]
    source = d["source"]
    source_top = source[source["nature_food_use"].isin(["main_or_extended_data", "supportive_extended_data"])].copy().head(12)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), gridspec_kw={"width_ratios": [1, 1.3]})
    y = np.arange(len(main_rows))
    axes[0].errorbar(main_rows["effect"], y, xerr=[main_rows["effect"] - main_rows["effect_low"], main_rows["effect_high"] - main_rows["effect"]], fmt="o", color=COLORS["orange"], ecolor=COLORS["gray"], capsize=3)
    axes[0].axvline(0, color=COLORS["line"], lw=1)
    axes[0].set_yticks(y, labels)
    axes[0].set_title("DEHP oxidative profile anchor")
    axes[0].set_xlabel("Effect per 10-point oxidative fraction")
    if len(source_top):
        source_top = source_top.sort_values("effect")
        colors = source_top["evidence_layer"].map({"source_proxy_to_DEHP_profile": COLORS["orange"], "source_proxy_to_metabolic_marker": COLORS["green"]}).fillna(COLORS["gray"])
        axes[1].barh(np.arange(len(source_top)), source_top["effect"], color=colors)
        axes[1].axvline(0, color=COLORS["line"], lw=1)
        axes[1].set_yticks(np.arange(len(source_top)), [f"{a} -> {b}" for a, b in zip(source_top["source_domain"], source_top["outcome_label"])])
    main_rows.assign(panel="a_dehp_oxidative_profile_anchor", display_label=labels).to_csv(FIGSRC / "Figure2_population_exposure_anchor_panel_a.csv", index=False)
    source_top.assign(panel="b_food_system_source_proxy_evidence").to_csv(FIGSRC / "Figure2_population_exposure_anchor_panel_b.csv", index=False)
    axes[1].set_title("Food-system source proxy evidence")
    axes[1].set_xlabel("Estimated effect")
    fig.suptitle("Figure 2. Population exposure anchor", weight="bold")
    savefig(fig, "Figure2_population_exposure_anchor")

    # Figure 3
    matrix = d["cg_matrix"]
    selected = matrix[matrix["term"].isin(["msi_core", "C(matrix_collapsed3)[T.mixed_buffered_or_unknown]"])].copy()
    summary = read_csv(NF_ROBUST / "aim2_collapsed3_food_matrix_summary.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3))
    selected["label"] = selected["outcome"] + "\n" + selected["term"].str.replace("C\\(matrix_collapsed3\\)\\[T.", "", regex=True).str.replace("\\]", "", regex=True)
    selected.assign(panel="a_gee_coefficients").to_csv(FIGSRC / "Figure3_meal_expression_layer_panel_a.csv", index=False)
    summary.assign(panel="b_high_iauc_rate_by_matrix").to_csv(FIGSRC / "Figure3_meal_expression_layer_panel_b.csv", index=False)
    y = np.arange(len(selected))
    axes[0].errorbar(selected["estimate"], y, xerr=[selected["estimate"] - selected["ci_low"], selected["ci_high"] - selected["estimate"]], fmt="o", color=COLORS["green"], ecolor=COLORS["gray"], capsize=3)
    axes[0].axvline(0, color=COLORS["line"], lw=1)
    axes[0].set_yticks(y, selected["label"])
    axes[0].set_title("GEE coefficients")
    x_summary = np.arange(len(summary))
    axes[1].bar(x_summary, summary["high_iauc_rate"], color=[COLORS["green"], COLORS["orange"], COLORS["red"]][: len(summary)])
    axes[1].set_xticks(x_summary, summary["matrix_collapsed3"], rotation=30, ha="right")
    axes[1].set_ylabel("High-iAUC meal rate")
    axes[1].set_title("Observed PPGR risk by matrix")
    fig.suptitle("Figure 3. Meal-expression layer", weight="bold")
    savefig(fig, "Figure3_meal_expression_layer")

    # Figure 4
    cf = d["cf"].copy()
    assign = d["phase_assign"].copy()
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    axes[0].hist(cf["risk_reduction"], bins=18, color=COLORS["teal"], edgecolor="white")
    axes[0].axvline(cf["risk_reduction"].median(), color=COLORS["orange"], lw=2, label=f"median {fmt(cf['risk_reduction'].median())}")
    axes[0].set_title("Counterfactual risk reduction")
    axes[0].set_xlabel("Predicted high-iAUC risk reduction")
    axes[0].legend(frameon=False)
    phase_counts = assign["phase_id"].value_counts()
    cf.assign(panel="a_counterfactual_risk_reduction").to_csv(FIGSRC / "Figure4_meal_redesign_phase_compatibility_panel_a.csv", index=False)
    phase_counts.rename_axis("phase_id").reset_index(name="participant_n").assign(panel="b_frozen_phase_compatibility").to_csv(FIGSRC / "Figure4_meal_redesign_phase_compatibility_panel_b.csv", index=False)
    axes[1].bar(phase_counts.index, phase_counts.values, color=COLORS["blue"])
    axes[1].set_title("CGMacros frozen phase compatibility")
    axes[1].set_ylabel("Participants")
    axes[1].tick_params(axis="x", rotation=25)
    fig.suptitle("Figure 4. Meal redesign and phase compatibility", weight="bold")
    savefig(fig, "Figure4_meal_redesign_phase_compatibility")

    # Figure 5
    loop_phase = d["loop"][d["loop"]["feature_set"].eq("C4_phase_map")]
    secondary_phase = d["secondary"][(d["secondary"]["feature_set"].eq("C4_phase_map")) & (d["secondary"]["status"].eq("evaluable"))]
    val_rows = pd.DataFrame(
        [
            ("Loop HbA1c", val(loop_phase, target="y_hba1c_improved_ge_0_5").auroc),
            ("Loop TIR", val(loop_phase, target="y_tir_improved_ge_5pct").auroc),
            ("PSO3/4 HbA1c", val(secondary_phase, validation_dataset="PSO3_PSO4_POOLED_FROZEN", target="y_hba1c_improved_ge_0_5").auroc),
            ("PSO3/4 TIR", val(secondary_phase, validation_dataset="PSO3_PSO4_POOLED_FROZEN", target="y_tir_improved_ge_5pct").auroc),
        ],
        columns=["validation", "auroc"],
    )
    d["phase_stab"].assign(panel="a_bootstrap_stability").to_csv(FIGSRC / "Figure5_cgm_digital_phenotype_validation_panel_a.csv", index=False)
    val_rows.assign(panel="b_frozen_external_validation").to_csv(FIGSRC / "Figure5_cgm_digital_phenotype_validation_panel_b.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    axes[0].hist(d["phase_stab"]["adjusted_rand_index"], bins=16, color=COLORS["purple"], edgecolor="white")
    axes[0].axvline(d["phase_stab"]["adjusted_rand_index"].median(), color=COLORS["orange"], lw=2)
    axes[0].set_title("Phase-map bootstrap stability")
    axes[0].set_xlabel("Adjusted Rand index")
    axes[1].bar(val_rows["validation"], val_rows["auroc"], color=[COLORS["blue"], COLORS["teal"], COLORS["blue"], COLORS["teal"]])
    axes[1].axhline(0.5, color=COLORS["line"], lw=1)
    axes[1].set_ylim(0.45, 0.9)
    axes[1].set_ylabel("AUROC")
    axes[1].tick_params(axis="x", rotation=25)
    axes[1].set_title("Frozen external validation")
    fig.suptitle("Figure 5. CGM digital phenotype validation", weight="bold")
    savefig(fig, "Figure5_cgm_digital_phenotype_validation")

    # Figure 6
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.axis("off")
    steps = [
        ("Urine\nplasticizers", 0.10),
        ("Food/contact\nassay", 0.26),
        ("2x2 standard\nmeal challenge", 0.43),
        ("14-28 day\nCGM", 0.61),
        ("Integrated\nphenotype report", 0.80),
    ]
    pd.DataFrame(
        [
            {"step_order": i + 1, "display_label": label.replace("\n", " "), "x_position": x, "validation_role": "same_person_bridge_chain"}
            for i, (label, x) in enumerate(steps)
        ]
    ).to_csv(FIGSRC / "Figure6_bridge_cohort_workflow_steps.csv", index=False)
    for label, x in steps:
        ax.text(x, 0.55, label, ha="center", va="center", color="white", bbox=dict(boxstyle="round,pad=0.45", fc=COLORS["green"], ec="none"))
    for (_, x1), (_, x2) in zip(steps[:-1], steps[1:]):
        ax.annotate("", xy=(x2 - 0.07, 0.55), xytext=(x1 + 0.07, 0.55), arrowprops=dict(arrowstyle="->", lw=2, color=COLORS["gray"]))
    ax.text(0.5, 0.18, "Aim 4: same-person validation of exposure -> MSI -> PPGR -> CGM order parameters", ha="center", fontsize=11, color=COLORS["purple"], weight="bold")
    ax.text(0.02, 0.92, "Figure 6. Bridge cohort workflow", fontsize=13, weight="bold")
    savefig(fig, "Figure6_bridge_cohort_workflow")


def legends_and_manuscript(d: dict[str, pd.DataFrame]) -> None:
    legends = """
# Nature Food Figure Legends v0.1

## Figure 1. Integrated food-system-to-CGM evidence architecture

Nodes show food-system source context, DEHP oxidative profile, metabolic susceptibility, food matrix, PPGR vulnerability, CGM phase-map phenotype and the prospective bridge cohort. Solid arrows denote direct evidence in current datasets; dashed arrows denote bridge-needed same-person validation.

## Figure 2. Population exposure anchor

NHANES 2013-2018 survey-weighted models link oxidative DEHP profile to MSI-core, HOMA-IR and HbA1c. Source-oriented analyses provide food-system context but are interpreted as source proxies rather than measured food plasticizer concentrations.

## Figure 3. Meal-expression layer

CGMacros repeated-meal models show that MSI-core and collapsed food matrix class jointly organize PPGR vulnerability. Label coverage, human adjudication and leave-one-subject-out results are used to defend the matrix construct.

## Figure 4. Meal redesign and phase compatibility

Counterfactual meal redesign shows model-estimated reductions in high-iAUC risk. CGMacros raw CGM supports frozen phase-map compatibility, but assignments are interpreted as transport/ranking signals rather than clinical phase validation.

## Figure 5. CGM digital phenotype validation

The locked JAEB phase-map is stable under bootstrap resampling and externally transports to Loop and PSO cohorts for HbA1c/TIR response ranking. Absolute-risk claims require target-setting calibration.

## Figure 6. Bridge cohort workflow

Aim 4 will collect urine and food-contact plasticizer panels, standardized 2x2 meal challenge responses and 14-28 day CGM in the same participants to directly test the exposure-meal-CGM chain.
"""
    write(LEGENDS / "NatureFood_figure_legends_v0.1.md", legends)

    skeleton = """
# Nature Food Analysis Manuscript Skeleton v0.1

## Title

Food-system exposures and meal matrices define CGM digital phenotypes of metabolic vulnerability

## Results

### Food-system source contexts and DEHP oxidative profile anchor population susceptibility

Present Figure 2. Keep source proxy language cautious and distinguish it from measured food plasticizer concentrations.

### Meal matrix and metabolic susceptibility jointly organize PPGR vulnerability

Present Figure 3. Emphasize repeated-meal GEE, subject leverage and matrix adjudication.

### Meal redesign suggests a modifiable strategy but requires prospective validation

Present Figure 4A. Treat counterfactual reductions as model-based.

### CGM phase-map provides a transportable digital phenotype language

Present Figure 5. Use phenotype/ranking language and include calibration/fairness guardrails.

### A bridge cohort is required for same-person validation

Present Figure 6. Position Aim 4 as the Article upgrade path.

## Discussion

The Analysis contribution is a triangulated food-system-to-CGM phenotype framework. The key limitation is the absence of same-person chemical exposure, meal challenge and free-living CGM measurement, which Aim 4 directly addresses.
"""
    write(DOCS / "NatureFood_analysis_manuscript_skeleton_v0.1.md", skeleton)

    risk = """
# Reviewer Risk Response Memo v1.0

## Risk 1: The study looks like three unrelated datasets

Response: Figure 1 explicitly orders claims by food-system source context, population susceptibility, meal-expression and CGM digital phenotype. Every claim is labelled as direct, triangulated, model-based or bridge-needed.

## Risk 2: No shared participants across NHANES, CGMacros and JAEB

Response: The manuscript is framed as an Analysis with triangulated evidence. The same-person causal chain is explicitly reserved for Aim 4.

## Risk 3: Food plasticizer concentrations are not measured in current food samples

Response: Current food-system variables are source proxies. The manuscript does not claim measured food concentration until the plasticizer panel is completed.

## Risk 4: Food matrix labels are subjective

Response: The label protocol, final label coverage, human-review rate and subject-leverage stability are provided. Ambiguous meals remain mixed/unknown rather than being forced.

## Risk 5: CGMacros has only 40 subjects

Response: The analysis uses repeated meals with subject clustering, leave-one-subject-out stability and conservative generalization language.

## Risk 6: CGM phase-map calibration is imperfect

Response: Outputs are described as phenotype/ranking unless target calibration is acceptable. Clinical decision support language is avoided.

## Risk 7: Counterfactual meal redesign may be mistaken for intervention

Response: Captions and Results state that redesign is model-based and requires standardized meal validation.
"""
    write(DOCS / "Reviewer_risk_response_memo_v1.0.md", risk)

    aim4 = """
# Aim 4 Bridge Cohort Pilot Synopsis

## Objective

Test whether the same people can be measured across the full chain: food-system plasticizer exposure, metabolic susceptibility, standardized-meal PPGR and CGM phase/order parameters.

## Pilot design

Enroll 20-30 adults across normal glycaemia, prediabetes and treated/non-insulin type 2 diabetes. Collect repeated first-morning urine, food/contact plasticizer assays, standardized 2x2 matrix challenge meals, 14-28 day CGM and HbA1c/fasting insulin/glucose.

## Pilot success criteria

- At least 80% complete urine and CGM data.
- Standard meals matched for energy and carbohydrate.
- Food/contact assay detects measurable analytes or confirms low-burden contrast.
- PPGR endpoints and phase/order parameters can be computed in the same participants.

## Article upgrade

If pilot feasibility is met, scale to 80-120 participants and position the manuscript as a Nature Food Article rather than Analysis.
"""
    write(DOCS / "Aim4_bridge_cohort_pilot_synopsis.md", aim4)


def completion_report() -> None:
    report = """
# Nature Food Next-Stage Completion Report

## Completed

- Locked submission route: Analysis presubmission now; Article route after Aim 4 pilot.
- Redrew six main figures as PNG/PDF with source-data backing.
- Hardened Aim 1 food-system exposure anchor with source-oriented NHANES matrix, literature extraction schema and claim guardrails.
- Completed Aim 2-Aim 3 bridge analysis by merging CGMacros MSI/PPGR/matrix summaries with frozen CGM phase-map order parameters.
- Extended phase-map software to an integrated food-CGM phenotype research package with schema, toy data and unit test.
- Generated presubmission enquiry, abstract, manuscript skeleton, figure legends and reviewer risk response memo.

## Scientific bottom line

The current Nature Food-ready route is an Analysis built around triangulated evidence. The Article route remains conditional on Aim 4: same-person urine/food-contact plasticizer assays, standardized meals and 14-28 day CGM.

## Immediate next action

Open the rendered preview, inspect the six figures and presubmission enquiry, then decide whether to send the Analysis presubmission enquiry now or wait for Aim 4 pilot feasibility data.
"""
    write(DOCS / "NatureFood_next_stage_completion_report_zh.md", report)


def run() -> None:
    d = load_inputs()
    submission_materials(d)
    aim1_hardening(d)
    aim2_aim3_bridge(d)
    build_integrated_software()
    figures(d)
    legends_and_manuscript(d)
    completion_report()

    manifest = {
        "created": "2026-06-18",
        "objective": "Complete Nature Food next-stage tasks requested by user",
        "docs": [str(p) for p in sorted(DOCS.glob("*.md"))],
        "tables": [str(p) for p in sorted(TABLES.glob("*.csv"))],
        "figures": [str(p) for p in sorted(FIGS.glob("*"))],
        "figure_source_data": [str(p) for p in sorted(FIGSRC.glob("*.csv"))],
        "software": str(SOFTWARE),
    }
    (P0 / "nature_food_next_stage_completion_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"completed Nature Food next-stage package at {P0}")


if __name__ == "__main__":
    run()
