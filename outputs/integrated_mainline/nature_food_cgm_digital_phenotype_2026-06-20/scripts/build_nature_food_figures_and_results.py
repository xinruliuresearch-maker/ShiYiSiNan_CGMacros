"""Build Figure 1-4 source data and Nature Food Results skeleton from locked outputs."""

from __future__ import annotations

from pathlib import Path
import json
import shutil

import numpy as np
import pandas as pd


ROOT = Path(r"D:\ai for science")
AIM1 = ROOT / "results" / "nature_food_aim1_nhanes"
AIM2 = ROOT / "results" / "nature_food_aim2_cgmacros"
NEXT = ROOT / "results" / "nature_food_next_tasks"
P0 = ROOT / "results" / "nature_food_p0_robustness"
OUT = ROOT / "results" / "nature_food_manuscript_package"
FIGSRC = OUT / "figure_source_data"
OUT.mkdir(parents=True, exist_ok=True)
FIGSRC.mkdir(parents=True, exist_ok=True)


def read(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def fmt_p(p: float) -> str:
    if pd.isna(p):
        return "NA"
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


def fmt_num(x: float, digits: int = 3) -> str:
    if pd.isna(x):
        return "NA"
    return f"{x:.{digits}f}"


def fmt_effect(est: float, lo: float, hi: float, digits: int = 3) -> str:
    return f"{fmt_num(est, digits)} ({fmt_num(lo, digits)}, {fmt_num(hi, digits)})"


def export_csv(df: pd.DataFrame, name: str) -> Path:
    path = FIGSRC / name
    df.to_csv(path, index=False)
    return path


def build_figure_sources() -> dict[str, str]:
    manifest: dict[str, str] = {}
    aim1_main = read(AIM1 / "aim1_main_survey_results.csv")
    aim1_comp = read(AIM1 / "aim1_composition_total_adjusted_survey_results.csv")
    aim1_cycle = read(AIM1 / "aim1_cycle_replication_survey_results.csv")
    aim2_gee = read(AIM2 / "aim2_food_matrix_gee_model_results.csv")
    aim2_rel = read(AIM2 / "aim2_food_matrix_annotation_reliability_status.csv")
    aim2_matrix = read(AIM2 / "aim2_food_matrix_category_summary.csv")
    bridge = read(NEXT / "nature_food_cross_dataset_evidence_bridge.csv")
    model_ladder = read(NEXT / "aim3_loso_model_ladder_metrics.csv")
    collapsed = read(P0 / "aim2_collapsed3_food_matrix_gee_results.csv")
    collapsed_summary = read(P0 / "aim2_collapsed3_food_matrix_summary.csv")
    leverage = read(P0 / "aim2_loso_subject_leverage_stability.csv")
    cf = read(P0 / "aim3_counterfactual_high_iauc_prediction_deltas.csv")

    fig1a = pd.DataFrame(
        [
            {"dataset": "NHANES 2013-2018", "analytic_unit": "survey participant", "n": 2671, "primary_role": "DEHP oxidative-profile exposure anchor"},
            {"dataset": "NHANES insulin-resistance subset", "analytic_unit": "survey participant", "n": 1292, "primary_role": "HOMA-IR and insulin-metabolic susceptibility"},
            {"dataset": "CGMacros", "analytic_unit": "free-living meal", "n": int(aim2_rel.loc[aim2_rel.metric.eq("total_meals"), "value"].iloc[0]), "primary_role": "PPGR and food-matrix vulnerability"},
            {"dataset": "CGMacros", "analytic_unit": "participant", "n": int(aim2_rel.loc[aim2_rel.metric.eq("subjects"), "value"].iloc[0]), "primary_role": "subject-clustered repeated-meal inference"},
        ]
    )
    manifest["Figure 1a cohort overview"] = str(export_csv(fig1a, "figure1a_cohort_overview.csv"))

    fig1b = pd.DataFrame(
        [
            {"step": 1, "label": "NHANES DEHP oxidative profile", "output": "MSI-core, HOMA-IR, HbA1c association"},
            {"step": 2, "label": "CGMacros MSI transfer", "output": "PPGR vulnerability in free-living meals"},
            {"step": 3, "label": "Human-adjudicated food matrix", "output": "Meal-context modifiers of PPGR"},
            {"step": 4, "label": "Model ladder and redesign", "output": "MSI-aware risk stratification and counterfactual meal redesign"},
        ]
    )
    manifest["Figure 1b analysis roadmap"] = str(export_csv(fig1b, "figure1b_analysis_roadmap.csv"))

    fig1c = read(NEXT / "nature_food_readiness_dashboard.csv")
    manifest["Figure 1c readiness dashboard"] = str(export_csv(fig1c, "figure1c_readiness_dashboard.csv"))

    fig2a = aim1_main[
        aim1_main["exposure"].isin(["pct_oxidative_10", "ln_oxidative_to_MEHP", "ilr_oxidative_vs_primary"])
        & aim1_main["outcome"].isin(["msi_core_partial", "ln_HOMA_IR", "HbA1c", "TyG"])
    ].copy()
    fig2a["effect_CI"] = fig2a.apply(lambda r: fmt_effect(r.effect, r.effect_low, r.effect_high), axis=1)
    manifest["Figure 2a NHANES main effects"] = str(export_csv(fig2a, "figure2a_nhanes_main_effects.csv"))

    fig2b = aim1_comp[
        aim1_comp["exposure"].isin(["ln_oxidative_MEHP_ratio", "ilr_oxidative_vs_primary"])
        & aim1_comp["outcome"].isin(["msi_core_partial", "ln_HOMA_IR", "HbA1c", "TyG"])
    ].copy()
    fig2b["effect_CI"] = fig2b.apply(lambda r: fmt_effect(r.effect, r.effect_low, r.effect_high), axis=1)
    manifest["Figure 2b composition adjusted"] = str(export_csv(fig2b, "figure2b_nhanes_composition_adjusted.csv"))

    fig2c = read(NEXT / "aim1_cycle_directional_consistency.csv")
    manifest["Figure 2c cycle consistency"] = str(export_csv(fig2c, "figure2c_nhanes_cycle_consistency.csv"))

    fig3a = aim2_gee[
        aim2_gee["model"].isin(["msi_base", "food_matrix_main"])
        & aim2_gee["term"].eq("msi_core")
        & aim2_gee["outcome"].isin(["log1p_iauc_2h", "peak_delta_2h_w", "high_iauc_2h"])
    ].copy()
    manifest["Figure 3a MSI PPGR effects"] = str(export_csv(fig3a, "figure3a_cgmacros_msi_ppgr_effects.csv"))

    fig3b = aim2_matrix.copy()
    manifest["Figure 3b six-class food matrix summary"] = str(export_csv(fig3b, "figure3b_food_matrix_6class_summary.csv"))

    fig3c = collapsed[
        collapsed["term"].str.contains("matrix_collapsed3", na=False)
        | collapsed["term"].eq("msi_core")
    ].copy()
    manifest["Figure 3c collapsed matrix GEE"] = str(export_csv(fig3c, "figure3c_collapsed_matrix_gee.csv"))

    fig3d = leverage.copy()
    manifest["Figure 3d subject leverage"] = str(export_csv(fig3d, "figure3d_subject_leverage_stability.csv"))

    fig4a = model_ladder.copy()
    manifest["Figure 4a LOSO model ladder"] = str(export_csv(fig4a, "figure4a_loso_model_ladder.csv"))

    fig4b = cf.copy()
    fig4b["risk_reduction"] = -fig4b["pred_high_iauc_delta"]
    manifest["Figure 4b counterfactual deltas"] = str(export_csv(fig4b, "figure4b_counterfactual_high_iauc_deltas.csv"))

    fig4c = (
        cf.assign(risk_reduction=lambda x: -x["pred_high_iauc_delta"])
        .groupby(["food_matrix_final_category", "food_matrix_final_label"], as_index=False)
        .agg(
            candidate_meals=("subject_id", "size"),
            subjects=("subject_id", "nunique"),
            median_original_risk=("pred_high_iauc_original", "median"),
            median_redesigned_risk=("pred_high_iauc_redesigned", "median"),
            median_risk_reduction=("risk_reduction", "median"),
            median_iauc_2h=("iauc_2h", "median"),
            median_carbs=("carbs", "median"),
            median_fiber=("fiber", "median"),
        )
    )
    manifest["Figure 4c redesign summary"] = str(export_csv(fig4c, "figure4c_redesign_summary_by_original_matrix.csv"))

    fig4d = collapsed_summary.copy()
    manifest["Figure 4d collapsed matrix observed risk"] = str(export_csv(fig4d, "figure4d_collapsed_matrix_observed_risk.csv"))

    bridge_export = bridge.copy()
    manifest["Supplementary evidence bridge"] = str(export_csv(bridge_export, "supplementary_cross_dataset_evidence_bridge.csv"))
    manifest_path = OUT / "figure_source_data_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def get_row(df: pd.DataFrame, **kwargs) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for k, v in kwargs.items():
        mask &= df[k].eq(v)
    if not mask.any():
        raise KeyError(kwargs)
    return df.loc[mask].iloc[0]


def write_results_skeleton() -> None:
    aim1_main = read(AIM1 / "aim1_main_survey_results.csv")
    aim1_comp = read(AIM1 / "aim1_composition_total_adjusted_survey_results.csv")
    cycle = read(NEXT / "aim1_cycle_directional_consistency.csv")
    aim2_gee = read(AIM2 / "aim2_food_matrix_gee_model_results.csv")
    aim2_rel = read(AIM2 / "aim2_food_matrix_annotation_reliability_status.csv")
    model_ladder = read(NEXT / "aim3_loso_model_ladder_metrics.csv")
    collapsed = read(P0 / "aim2_collapsed3_food_matrix_gee_results.csv")
    leverage = read(P0 / "aim2_loso_subject_leverage_stability.csv")
    cf = read(P0 / "aim3_counterfactual_high_iauc_prediction_deltas.csv")

    pct_msi = get_row(aim1_main, outcome="msi_core_partial", exposure="pct_oxidative_10")
    pct_homa = get_row(aim1_main, outcome="ln_HOMA_IR", exposure="pct_oxidative_10")
    pct_hba1c = get_row(aim1_main, outcome="HbA1c", exposure="pct_oxidative_10")
    ilr_msi = get_row(aim1_main, outcome="msi_core_partial", exposure="ilr_oxidative_vs_primary")
    comp_msi = get_row(aim1_comp, outcome="msi_core_partial", exposure="ilr_oxidative_vs_primary")
    comp_homa = get_row(aim1_comp, outcome="ln_HOMA_IR", exposure="ilr_oxidative_vs_primary")
    comp_hba1c = get_row(aim1_comp, outcome="HbA1c", exposure="ilr_oxidative_vs_primary")

    msi_log = get_row(aim2_gee, model="msi_base", outcome="log1p_iauc_2h", term="msi_core")
    msi_peak = get_row(aim2_gee, model="msi_base", outcome="peak_delta_2h_w", term="msi_core")
    msi_high = get_row(aim2_gee, model="msi_base", outcome="high_iauc_2h", term="msi_core")
    matrix_log = collapsed[
        collapsed["outcome"].eq("log1p_iauc_2h")
        & collapsed["term"].str.contains("mixed_buffered_or_unknown", na=False)
    ].iloc[0]
    matrix_peak = collapsed[
        collapsed["outcome"].eq("peak_delta_2h_w")
        & collapsed["term"].str.contains("mixed_buffered_or_unknown", na=False)
    ].iloc[0]
    matrix_high = collapsed[
        collapsed["outcome"].eq("high_iauc_2h")
        & collapsed["term"].str.contains("mixed_buffered_or_unknown", na=False)
    ].iloc[0]

    m1 = get_row(model_ladder, model="M1_macro_timing")
    m2 = get_row(model_ladder, model="M2_macro_timing_MSI")
    m3 = get_row(model_ladder, model="M3_MSI_food_matrix")
    m4 = get_row(model_ladder, model="M4_full_matrix_nutrition")

    coverage = float(aim2_rel.loc[aim2_rel.metric.eq("human_final_label_coverage"), "value"].iloc[0])
    kappa = float(aim2_rel.loc[aim2_rel.metric.eq("cohen_kappa_human_dual_review"), "value"].iloc[0])
    meals = int(float(aim2_rel.loc[aim2_rel.metric.eq("total_meals"), "value"].iloc[0]))
    subjects = int(float(aim2_rel.loc[aim2_rel.metric.eq("subjects"), "value"].iloc[0]))
    cf_median_delta = cf["pred_high_iauc_delta"].median()
    cf_iqr = cf["pred_high_iauc_delta"].quantile([0.25, 0.75])
    cf_orig = cf["pred_high_iauc_original"].median()
    cf_red = cf["pred_high_iauc_redesigned"].median()
    msi_stability = get_row(leverage, term="msi_core")
    matrix_stability = leverage[leverage["term"].str.contains("mixed_buffered_or_unknown", na=False)].iloc[0]

    cycle_core = cycle[
        cycle["outcome"].isin(["msi_core_partial", "ln_HOMA_IR", "HbA1c"])
        & cycle["exposure"].isin(["pct_oxidative_10", "ln_oxidative_to_MEHP"])
    ].copy()
    direction_sentence = (
        f"Across cycle-specific models, primary oxidative-profile estimates were positive in "
        f"{int(cycle_core['positive_cycles'].sum())}/{int(cycle_core['cycles'].sum())} cycle-outcome-exposure checks."
    )

    text = f"""# Nature Food Results Skeleton

## DEHP oxidative metabolism anchored a metabolic-susceptibility phenotype in NHANES

In survey-weighted NHANES 2013-2018 models, a 10 percentage-point higher oxidative DEHP metabolite fraction was associated with higher MSI-core (beta {fmt_effect(pct_msi.effect, pct_msi.effect_low, pct_msi.effect_high)}, q={fmt_p(pct_msi.q_value)}, n={int(pct_msi.n)}). The same exposure contrast was associated with higher HOMA-IR ({fmt_effect(pct_homa.effect, pct_homa.effect_low, pct_homa.effect_high)}% difference, q={fmt_p(pct_homa.q_value)}, n={int(pct_homa.n)}) and HbA1c (beta {fmt_effect(pct_hba1c.effect, pct_hba1c.effect_low, pct_hba1c.effect_high)}, q={fmt_p(pct_hba1c.q_value)}, n={int(pct_hba1c.n)}).

The oxidative-vs-primary DEHP balance produced a similar pattern. The ILR oxidative-vs-primary contrast was associated with MSI-core (beta {fmt_effect(ilr_msi.effect, ilr_msi.effect_low, ilr_msi.effect_high)}, q={fmt_p(ilr_msi.q_value)}). After adjustment for total DEHP burden, this association remained for MSI-core (beta {fmt_effect(comp_msi.effect, comp_msi.effect_low, comp_msi.effect_high)}, q={fmt_p(comp_msi.q_value)}), HOMA-IR ({fmt_effect(comp_homa.effect, comp_homa.effect_low, comp_homa.effect_high)}% difference, q={fmt_p(comp_homa.q_value)}) and HbA1c (beta {fmt_effect(comp_hba1c.effect, comp_hba1c.effect_low, comp_hba1c.effect_high)}, q={fmt_p(comp_hba1c.q_value)}). {direction_sentence}

## The NHANES-derived susceptibility score predicted PPGR vulnerability in CGMacros

In CGMacros, the analysis included {meals} free-living meals from {subjects} participants with complete human-adjudicated food-matrix labels. MSI-core was strongly associated with all three PPGR endpoints: log1p 2h iAUC (beta {msi_log.estimate_CI}, q={fmt_p(msi_log.q_value)}), peak glucose delta (beta {msi_peak.estimate_CI}, q={fmt_p(msi_peak.q_value)}) and high-iAUC meal risk (log-odds {msi_high.estimate_CI}, q={fmt_p(msi_high.q_value)}).

## Collapsing food matrix labels retained a stable meal-context signal

Human final-label coverage was {coverage:.1%}; the dual-review Cohen kappa was {kappa:.3f}. To reduce sensitivity to sparse six-class labels, we collapsed the food matrix into protective whole-food/low-carb, mixed/unknown, and rapid-digestible/liquid-carbohydrate classes. Compared with the protective class, mixed/unknown meals had higher PPGR across outcomes: log1p 2h iAUC (beta {matrix_log.estimate_CI}, p={fmt_p(matrix_log.p_value)}), peak delta (beta {matrix_peak.estimate_CI}, p={fmt_p(matrix_peak.p_value)}) and high-iAUC risk (log-odds {matrix_high.estimate_CI}, p={fmt_p(matrix_high.p_value)}).

Leave-one-subject-out analyses supported stability rather than single-subject leverage. The MSI-core coefficient remained positive in {int(msi_stability.positive_leaveouts)}/{int(msi_stability.leaveouts)} leave-one-subject-out models, and the mixed/unknown food-matrix coefficient remained positive in {int(matrix_stability.positive_leaveouts)}/{int(matrix_stability.leaveouts)} leave-one-subject-out models.

## MSI and food matrix improved subject-held-out PPGR risk stratification

In leave-one-subject-out validation, a macro/timing model had high-iAUC AUC {m1.high_iauc_auc:.3f}. Adding MSI-core increased AUC to {m2.high_iauc_auc:.3f} (delta {m2.delta_auc_vs_M1:.3f}); adding human-adjudicated food matrix increased AUC to {m3.high_iauc_auc:.3f} (delta {m3.delta_auc_vs_M1:.3f}). The full nutrition plus matrix model had the highest high-iAUC AUC ({m4.high_iauc_auc:.3f}) but worse continuous log1p iAUC RMSE than the more parsimonious MSI-plus-matrix model ({m4.log1p_iauc_rmse:.3f} vs {m3.log1p_iauc_rmse:.3f}), so we treat the MSI-plus-matrix model as the primary interpretable prediction model and the full model as a risk-classification sensitivity analysis.

## Counterfactual meal redesign suggested a translatable risk-reduction layer

Among high-priority high-MSI/high-response candidate meals, replacing the original lower-protection food matrix with a fiber-rich/whole-food matrix reduced predicted high-iAUC risk from a median {cf_orig:.3f} to {cf_red:.3f}. The median predicted risk difference was {cf_median_delta:.3f} (IQR {cf_iqr.iloc[0]:.3f} to {cf_iqr.iloc[1]:.3f}); negative values indicate lower predicted high-iAUC risk after redesign. These estimates are model-based counterfactuals and define candidate meal prototypes for controlled validation rather than causal proof of diet substitution.

## Figure Mapping

- Figure 1: cohort overview, analysis roadmap, and readiness dashboard.
- Figure 2: NHANES oxidative DEHP profile, composition-adjusted models, and cycle consistency.
- Figure 3: CGMacros MSI-PPGR associations, human food-matrix distribution, collapsed matrix GEE, and subject leverage.
- Figure 4: LOSO model ladder, counterfactual high-iAUC deltas, redesign summary, and observed collapsed-matrix risk.
"""
    (OUT / "nature_food_results_skeleton_real_values.md").write_text(text, encoding="utf-8")


def write_locked_summary() -> None:
    srcs = {
        "collapsed_matrix_gee": P0 / "aim2_collapsed3_food_matrix_gee_results.csv",
        "subject_leverage": P0 / "aim2_loso_subject_leverage_stability.csv",
        "counterfactual_delta": P0 / "aim3_counterfactual_high_iauc_prediction_deltas.csv",
        "model_ladder": NEXT / "aim3_loso_model_ladder_metrics.csv",
    }
    for label, src in srcs.items():
        shutil.copy2(src, OUT / f"locked_{src.name}")
    summary = pd.DataFrame(
        [
            {"deliverable": "Aim 2 collapsed matrix GEE", "status": "complete", "file": str((OUT / 'locked_aim2_collapsed3_food_matrix_gee_results.csv').resolve())},
            {"deliverable": "Aim 2 subject leverage", "status": "complete", "file": str((OUT / 'locked_aim2_loso_subject_leverage_stability.csv').resolve())},
            {"deliverable": "Aim 3 counterfactual delta", "status": "complete", "file": str((OUT / 'locked_aim3_counterfactual_high_iauc_prediction_deltas.csv').resolve())},
            {"deliverable": "Figure 1-4 source data", "status": "complete", "file": str(FIGSRC.resolve())},
            {"deliverable": "Nature Food Results skeleton", "status": "complete", "file": str((OUT / 'nature_food_results_skeleton_real_values.md').resolve())},
        ]
    )
    summary.to_csv(OUT / "nature_food_requested_deliverables_status.csv", index=False)


def main() -> None:
    manifest = build_figure_sources()
    write_results_skeleton()
    write_locked_summary()
    package_manifest = {
        "figure_panels": manifest,
        "main_outputs": sorted(p.name for p in OUT.glob("*") if p.is_file()),
    }
    (OUT / "nature_food_manuscript_package_manifest.json").write_text(json.dumps(package_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote manuscript package to {OUT}")


if __name__ == "__main__":
    main()
