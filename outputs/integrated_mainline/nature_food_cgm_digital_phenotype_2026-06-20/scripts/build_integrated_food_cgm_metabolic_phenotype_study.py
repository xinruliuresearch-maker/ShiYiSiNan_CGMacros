"""Build an integrated study framework from the Nature Food and JAEB/npj work.

The intent is not to merge unrelated manuscripts mechanically. The outputs
separate direct evidence from inferential bridges and define the missing
analyses needed to make the combined project coherent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(r"D:\ai for science")
NF = ROOT / "results" / "nature_food_manuscript_package"
NF_AIMS = ROOT / "results" / "nature_food_high_bar_aims"
NF_P0 = ROOT / "results" / "nature_food_p0_robustness"
JAEB = ROOT / "results" / "jaeb_glycemic_phase_completion"
NPJ = ROOT / "results" / "npj_digital_medicine_phase_strategy"
NPJ_P0 = NPJ / "p0_workup"
NPJ_EXT = NPJ / "p0_extensions_2026_06_18"

OUT = ROOT / "results" / "integrated_food_cgm_metabolic_phenotype_study_2026_06_18"
DOCS = OUT / "docs"
TABLES = OUT / "tables"
FIGSRC = OUT / "figure_source_data"
for path in [OUT, DOCS, TABLES, FIGSRC]:
    path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def write(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def fmt(x: float, digits: int = 3) -> str:
    if pd.isna(x):
        return "NA"
    return f"{float(x):.{digits}f}"


def val(df: pd.DataFrame, **where) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for k, v in where.items():
        mask &= df[k].eq(v)
    sub = df[mask]
    if sub.empty:
        raise KeyError(where)
    return sub.iloc[0]


def main() -> None:
    nhanes_main = read_csv(NF / "figure_source_data" / "figure2a_nhanes_main_effects.csv")
    nhanes_comp = read_csv(NF / "figure_source_data" / "figure2b_nhanes_composition_adjusted.csv")
    cg_msi = read_csv(NF / "figure_source_data" / "figure3a_cgmacros_msi_ppgr_effects.csv")
    cg_matrix = read_csv(NF / "figure_source_data" / "figure3c_collapsed_matrix_gee.csv")
    cg_ladder = read_csv(NF / "figure_source_data" / "figure4a_loso_model_ladder.csv")
    cf = read_csv(NF / "figure_source_data" / "figure4b_counterfactual_high_iauc_deltas.csv")
    leverage = read_csv(NF_AIMS / "aim2_subject_leverage_locked.csv")

    phase_features = read_csv(JAEB / "tables" / "locked_glycemic_phase_features.csv")
    cgm_long = read_csv(JAEB / "tables" / "locked_cgm_summary_long.csv")
    phase_stab = read_csv(JAEB / "tables" / "locked_phase_bootstrap_stability.csv")
    hte = read_csv(JAEB / "tables" / "locked_journal_adjusted_hte_by_phase.csv")
    nested = read_csv(JAEB / "tables" / "locked_journal_nested_tuning_summary.csv")
    loop = read_csv(NPJ_P0 / "tables" / "loop_frozen_external_validation_metrics.csv")
    secondary = read_csv(NPJ_EXT / "tables" / "secondary_external_validation_metrics.csv")
    calibration = read_csv(NPJ_EXT / "tables" / "loop_loso_calibration_upgrade_metrics.csv")

    pct_msi = val(nhanes_main, outcome="msi_core_partial", exposure="pct_oxidative_10")
    comp_msi = val(nhanes_comp, outcome="msi_core_partial", exposure="ilr_oxidative_vs_primary")
    pct_homa = val(nhanes_main, outcome="ln_HOMA_IR", exposure="pct_oxidative_10")
    pct_hba1c = val(nhanes_main, outcome="HbA1c", exposure="pct_oxidative_10")

    msi_log = val(cg_msi, outcome="log1p_iauc_2h", model="msi_base", term="msi_core")
    msi_peak = val(cg_msi, outcome="peak_delta_2h_w", model="msi_base", term="msi_core")
    msi_high = val(cg_msi, outcome="high_iauc_2h", model="msi_base", term="msi_core")
    matrix_log = cg_matrix[
        (cg_matrix["outcome"].eq("log1p_iauc_2h"))
        & (cg_matrix["term"].str.contains("mixed_buffered_or_unknown", regex=False))
    ].iloc[0]
    matrix_high = cg_matrix[
        (cg_matrix["outcome"].eq("high_iauc_2h"))
        & (cg_matrix["term"].str.contains("mixed_buffered_or_unknown", regex=False))
    ].iloc[0]
    m3 = cg_ladder[cg_ladder["model"].eq("M3_MSI_food_matrix")].iloc[0]
    m1 = cg_ladder[cg_ladder["model"].eq("M1_macro_timing")].iloc[0]

    cf_summary = {
        "n_candidates": int(len(cf)),
        "median_original": float(cf["pred_high_iauc_original"].median()),
        "median_redesigned": float(cf["pred_high_iauc_redesigned"].median()),
        "median_delta": float(cf["pred_high_iauc_delta"].median()),
        "median_risk_reduction": float(cf["risk_reduction"].median()),
    }
    phase_counts = phase_features["phase_label"].value_counts().rename_axis("phase_label").reset_index(name="n")
    nested_best = nested.sort_values(["target", "auroc_mean"], ascending=[True, False]).groupby("target", as_index=False).head(1)
    loop_phase = loop[loop["feature_set"].eq("C4_phase_map")].copy()
    sec_phase = secondary[(secondary["feature_set"].eq("C4_phase_map")) & (secondary["status"].eq("evaluable"))].copy()

    evidence_chain = pd.DataFrame(
        [
            {
                "edge_id": "E1",
                "claim": "DEHP oxidative profile anchors metabolic susceptibility in a population sample",
                "from_construct": "food-system plasticizer exposure",
                "to_construct": "MSI/HOMA-IR/HbA1c susceptibility",
                "dataset": "NHANES 2013-2018",
                "directness": "direct_observational",
                "key_result": f"10-point higher oxidative DEHP fraction: MSI beta {fmt(pct_msi.effect)} ({fmt(pct_msi.effect_low)} to {fmt(pct_msi.effect_high)}), q={fmt(pct_msi.q_value)}; HOMA-IR {fmt(pct_homa.effect)}% ({fmt(pct_homa.effect_low)} to {fmt(pct_homa.effect_high)}); HbA1c beta {fmt(pct_hba1c.effect)}.",
                "current_limit": "Cross-sectional biomonitoring; no CGM phase or PPGR outcome measured.",
                "bridge_needed": "Measure urinary/food plasticizers and CGM in the same bridge cohort.",
            },
            {
                "edge_id": "E2",
                "claim": "Oxidative-vs-primary DEHP balance is not only total DEHP burden",
                "from_construct": "DEHP metabolism composition",
                "to_construct": "MSI-core",
                "dataset": "NHANES 2013-2018",
                "directness": "direct_composition_adjusted",
                "key_result": f"Total-DEHP-adjusted ILR oxidative-vs-primary: MSI beta {fmt(comp_msi.effect)} ({fmt(comp_msi.effect_low)} to {fmt(comp_msi.effect_high)}), q={fmt(comp_msi.q_value)}.",
                "current_limit": "Metabolite balance may reflect exposure, metabolism, timing, renal dilution or behavior.",
                "bridge_needed": "Add repeated urine and food-packaging assay metadata.",
            },
            {
                "edge_id": "E3",
                "claim": "MSI expresses as free-living postprandial glucose vulnerability",
                "from_construct": "MSI-core",
                "to_construct": "PPGR severity",
                "dataset": "CGMacros",
                "directness": "direct_repeated_meal",
                "key_result": f"MSI-core associated with log1p iAUC beta {msi_log.estimate_CI}, peak delta {msi_peak.estimate_CI}, high-iAUC log-odds {msi_high.estimate_CI}; n={int(msi_log.n)} meals, {int(msi_log.n_subjects)} subjects.",
                "current_limit": "Small subject count and no plasticizer biomarkers.",
                "bridge_needed": "Use CGM phase/order-parameter assignment in CGMacros or bridge cohort.",
            },
            {
                "edge_id": "E4",
                "claim": "Food matrix modifies PPGR beyond macros and MSI",
                "from_construct": "food matrix protection",
                "to_construct": "PPGR severity",
                "dataset": "CGMacros",
                "directness": "direct_human_adjudicated_meal",
                "key_result": f"Mixed/unknown matrix vs protective class: log1p iAUC beta {matrix_log.estimate_CI}; high-iAUC log-odds {matrix_high.estimate_CI}. MSI and matrix coefficients stayed positive in leave-one-subject-out checks.",
                "current_limit": "Meal labels are manually adjudicated; food chemical exposure is not directly measured.",
                "bridge_needed": "Standardized meal challenge with measured packaging/contact materials.",
            },
            {
                "edge_id": "E5",
                "claim": "MSI + food matrix improves PPGR risk stratification",
                "from_construct": "MSI + food-matrix class",
                "to_construct": "high-iAUC meal risk",
                "dataset": "CGMacros",
                "directness": "direct_subject_held_out_prediction",
                "key_result": f"Subject-held-out high-iAUC AUC improved from {fmt(m1.high_iauc_auc)} to {fmt(m3.high_iauc_auc)} after adding MSI + food matrix; median counterfactual risk reduction {fmt(cf_summary['median_risk_reduction'])}.",
                "current_limit": "Counterfactual redesign is model-based, not intervention evidence.",
                "bridge_needed": "Controlled meal redesign validation.",
            },
            {
                "edge_id": "E6",
                "claim": "CGM summaries can be converted to a reproducible dynamic phase-map phenotype",
                "from_construct": "CGM summary/order parameters",
                "to_construct": "CGM digital phenotype",
                "dataset": "JAEB public diabetes studies",
                "directness": "direct_digital_phenotype",
                "key_result": f"{phase_features['participant_id'].nunique()} phase-map participants; ARI median {fmt(phase_stab.adjusted_rand_index.median())}, IQR {fmt(phase_stab.adjusted_rand_index.quantile(0.25))}-{fmt(phase_stab.adjusted_rand_index.quantile(0.75))}; {phase_counts.shape[0]} phases.",
                "current_limit": "Phase-map is based on summary CGM and mostly diabetes trial populations.",
                "bridge_needed": "Assign the same phase-map to nutrition/food-exposure cohorts.",
            },
            {
                "edge_id": "E7",
                "claim": "CGM phase membership organizes treatment-response heterogeneity",
                "from_construct": "CGM digital phenotype",
                "to_construct": "HbA1c/TIR response",
                "dataset": "JAEB public diabetes studies",
                "directness": "direct_retrospective_hte",
                "key_result": f"Highest adjusted RD in hypoglycaemia-susceptible phase: {fmt(hte.adjusted_risk_difference.max())}; CI {fmt(hte.bootstrap_ci_low[hte.adjusted_risk_difference.idxmax()])}-{fmt(hte.bootstrap_ci_high[hte.adjusted_risk_difference.idxmax()])}.",
                "current_limit": "Therapy/device-response heterogeneity is not the same as food-matrix intervention response.",
                "bridge_needed": "Test whether food-matrix redesign changes phase/order parameters or PPGR in a prospective cohort.",
            },
            {
                "edge_id": "E8",
                "claim": "The phase-map software transports to additional public datasets",
                "from_construct": "locked phase-map model",
                "to_construct": "external HbA1c/TIR response prediction",
                "dataset": "Loop + RacialDifferences + PSO3/4",
                "directness": "direct_external_validation",
                "key_result": f"Loop phase-map AUROC: HbA1c {fmt(val(loop_phase, target='y_hba1c_improved_ge_0_5').auroc)}, TIR {fmt(val(loop_phase, target='y_tir_improved_ge_5pct').auroc)}. PSO3/4 pooled phase-map AUROC: HbA1c {fmt(val(sec_phase, validation_dataset='PSO3_PSO4_POOLED_FROZEN', target='y_hba1c_improved_ge_0_5').auroc)}, TIR {fmt(val(sec_phase, validation_dataset='PSO3_PSO4_POOLED_FROZEN', target='y_tir_improved_ge_5pct').auroc)}.",
                "current_limit": "Calibration for absolute risk is uneven; use phenotype/ranking unless recalibrated.",
                "bridge_needed": "Integrate PPGR/food matrix endpoints into the same software release.",
            },
        ]
    )
    evidence_chain.to_csv(TABLES / "integrated_evidence_chain.csv", index=False)

    crosswalk = pd.DataFrame(
        [
            ("metabolic susceptibility", "MSI-core/HOMA-IR/HbA1c", "participant MSI-core and glucose response phenotype", "phase glycaemic burden/order parameters", "shared latent vulnerability axis", "Use MSI and CGM order parameters as two measurement languages for vulnerability.", "Needs direct same-person bridge."),
            ("postprandial expression", "not measured", "2h iAUC, peak delta, high-iAUC", "not meal-level", "short-timescale phenotype", "Treat PPGR as acute expression of susceptibility.", "Need bridge meal challenge with CGM phase."),
            ("dynamic CGM phenotype", "not measured", "meal-window CGM only; locked phase-map not yet assigned", "locked five-phase map", "longer-horizon digital phenotype", "Assign phase-map to CGMacros/bridge cohort from raw CGM.", "Need wear-quality and phase transport checks."),
            ("food matrix", "dietary/food-system proxy only", "human-adjudicated meal matrix classes", "not available", "modifiable meal context", "Use food matrix as the actionable nutrition lever.", "Add food logs/standardized meals to phase cohort."),
            ("chemical exposure", "urinary DEHP metabolites", "not measured", "not measured", "food-system stressor", "Keep NHANES as exposure anchor until bridge data exist.", "Measure urine and food packaging/contact panel in bridge cohort."),
            ("outcome horizon", "population metabolic biomarkers", "post-meal glucose excursion", "months-long HbA1c/TIR response", "multi-timescale phenotype", "Connect biomarker, acute PPGR and CGM phase as nested horizons.", "Use bridge cohort with acute PPGR and 14-28 day phase stability."),
            ("software artifact", "analysis script", "meal-risk model", "phase-map package v0.1", "integrated digital phenotyping pipeline", "Combine MSI, meal-risk and phase-map APIs.", "Package needs schema, toy data and reproduction scripts."),
        ],
        columns=["construct", "NHANES_measure", "CGMacros_measure", "JAEB_measure", "integrated_role", "connection", "remaining_gap"],
    )
    crosswalk.to_csv(TABLES / "cross_study_construct_crosswalk.csv", index=False)

    disconnected = pd.DataFrame(
        [
            ("No shared participants across NHANES, CGMacros and JAEB", "Cannot claim one individual-level causal chain.", "State triangulated evidence; create bridge cohort with urine + meals + CGM.", "bridge_cohort_required", "P0 manuscript guardrail + P1 data collection"),
            ("DEHP exposure absent in CGMacros/JAEB", "Cannot claim plasticizers drive PPGR or phase membership.", "Add urinary plasticizer panel and food packaging/contact metadata in the bridge cohort.", "new_measurement_required", "P1"),
            ("MSI-core and CGM phase-map are different phenotype languages", "The two papers currently speak past each other.", "Define common axes: glycaemic burden, postprandial excursion, variability, insulin resistance, hypoglycaemic susceptibility.", "resolved_by_crosswalk", "P0"),
            ("CGMacros has meal windows, JAEB has longitudinal clinical trial CGM", "Food matrix effects and JAEB phase response are not directly comparable.", "Use CGMacros/bridge raw CGM to assign phase-map and test whether high MSI/high PPGR maps to high-burden/instability phases.", "analysis_needed", "P0/P1"),
            ("Food matrix not measured in JAEB", "Cannot infer dietary intervention response from JAEB HTE.", "Use JAEB only to validate CGM digital phenotype and response heterogeneity; keep food-matrix intervention evidence in CGMacros/pilot.", "manuscript_guardrail", "P0"),
            ("External validation calibration is uneven", "Digital care workflow cannot present raw absolute risk as clinically actionable.", "Use calibrated/ranking phenotype framing; add recalibration sensitivity and calibration plots.", "partly_resolved", "P0 done for JAEB; extend to integrated model"),
            ("CGMacros n=40 subjects", "Meal matrix results may be viewed as small-sample despite 1498 meals.", "Keep GEE/LOSO subject leverage; add standard meal challenge or pilot.", "partly_resolved", "P1"),
            ("Current software only assigns JAEB phase-map", "Integrated study needs more than a phase classifier.", "Add modules for MSI calculation, meal-matrix risk and phase-map output in one research package.", "software_extension_needed", "P0/P1"),
        ],
        columns=["disconnected_point", "risk_if_unfixed", "fix", "fix_type", "priority"],
    )
    disconnected.to_csv(TABLES / "disconnected_points_and_fixes.csv", index=False)

    aims = pd.DataFrame(
        [
            ("Aim 1", "Define food-system exposure-linked metabolic susceptibility", "NHANES 2013-2018", "DEHP oxidative profile, MSI-core, HOMA-IR, HbA1c", "Population anchor for susceptibility", "Complete; report as observational anchor."),
            ("Aim 2", "Show how susceptibility is expressed after real meals", "CGMacros", "MSI-core, food matrix, PPGR iAUC/peak/high-risk meal", "Mechanistic/nutritional expression layer", "Complete for retrospective analysis; needs standard meal validation."),
            ("Aim 3", "Validate a CGM digital phenotype for dynamic metabolic states", "JAEB + Loop + RacialDifferences + PSO3/4", "CGM phase-map, HbA1c/TIR response, calibration/fairness", "Digital phenotype and software layer", "Complete for retrospective validation; no food exposure measured."),
            ("Aim 4", "Bridge the three layers in the same people", "New bridge cohort / pilot", "Urinary plasticizers, food packaging/contact panel, standardized meals, free-living CGM, phase-map", "Direct test of exposure -> MSI/PPGR -> CGM phase pathway", "Not yet done; required for one high-level integrated study."),
        ],
        columns=["aim", "objective", "dataset", "key_variables", "role_in_integrated_study", "current_status"],
    )
    aims.to_csv(TABLES / "integrated_aims.csv", index=False)

    tasks = pd.DataFrame(
        [
            ("INT-P0-01", "P0", "Manuscript framing", "Retitle and rewrite as one multi-layer digital-metabolic phenotype study, not two manuscripts stapled together.", "One-page claim map and abstract."),
            ("INT-P0-02", "P0", "Construct crosswalk", "Use the crosswalk table as the formal bridge between MSI, PPGR and CGM phase-map.", "Methods subsection: phenotype harmonization."),
            ("INT-P0-03", "P0", "CGMacros phase feasibility", "Check whether raw/free-living CGM in CGMacros supports participant-level phase-map assignment.", "Feasibility table; if feasible, assign phase-map to 40 subjects."),
            ("INT-P0-04", "P0", "Integrated software package", "Extend phase-map package with MSI calculator and meal-matrix PPGR risk module.", "phase_map + meal_risk package with toy data."),
            ("INT-P0-05", "P0", "Calibration language", "State all risk outputs as ranking/phenotype unless calibrated in target setting.", "Risk-display limitation paragraph."),
            ("INT-P0-06", "P0", "Main figures", "Rebuild figures around one flow: exposure anchor -> meal expression -> CGM digital phenotype -> bridge cohort.", "Figure source data and storyboard."),
            ("INT-P1-01", "P1", "Bridge cohort protocol", "Design 80-120 participant study with urine plasticizers, food samples/packaging metadata, standardized meals and 14-28 day CGM.", "IRB-ready protocol and SAP."),
            ("INT-P1-02", "P1", "Standardized meal challenge", "2x2 high/low exposure-contact by high/low matrix protection design, equal carb/energy.", "Meal challenge menu, SOP, endpoints."),
            ("INT-P1-03", "P1", "Mechanistic add-on", "In vitro digestion/glucose release and plasticizer assay for selected meal prototypes.", "Mechanism supplement."),
        ],
        columns=["task_id", "priority", "workstream", "task", "deliverable"],
    )
    tasks.to_csv(TABLES / "integrated_next_tasks.csv", index=False)

    figure_nodes = pd.DataFrame(
        [
            ("N1", "Food-system plasticizer exposure", "exposure"),
            ("N2", "MSI / insulin-resistance susceptibility", "susceptibility"),
            ("N3", "Food matrix / meal context", "meal"),
            ("N4", "Postprandial glucose response", "acute_cgm"),
            ("N5", "CGM phase-map digital phenotype", "digital_phenotype"),
            ("N6", "HbA1c/TIR response and digital care workflow", "clinical_translation"),
            ("N7", "Bridge cohort with urine + meal + CGM", "missing_bridge"),
        ],
        columns=["node_id", "label", "node_type"],
    )
    figure_edges = pd.DataFrame(
        [
            ("N1", "N2", "NHANES direct evidence"),
            ("N2", "N4", "CGMacros direct evidence"),
            ("N3", "N4", "CGMacros direct evidence"),
            ("N4", "N5", "bridge needed: acute PPGR to phase state"),
            ("N5", "N6", "JAEB direct evidence"),
            ("N7", "N1", "measure exposure"),
            ("N7", "N2", "measure susceptibility"),
            ("N7", "N3", "standardized meals/food contact"),
            ("N7", "N4", "meal challenge PPGR"),
            ("N7", "N5", "free-living phase-map"),
        ],
        columns=["source", "target", "evidence_status"],
    )
    figure_nodes.to_csv(FIGSRC / "integrated_study_dag_nodes.csv", index=False)
    figure_edges.to_csv(FIGSRC / "integrated_study_dag_edges.csv", index=False)

    storyboard = pd.DataFrame(
        [
            ("Figure 1", "Integrated evidence architecture", "DAG showing direct and missing bridge edges", "Use nodes/edges CSV; color direct vs bridge-needed edges."),
            ("Figure 2", "Population exposure anchor", "NHANES DEHP oxidative profile -> MSI/HOMA/HbA1c", "Use existing Figure 2 source data."),
            ("Figure 3", "Meal expression layer", "CGMacros MSI + food matrix -> PPGR; model ladder and counterfactual redesign", "Use existing Figure 3/4 source data."),
            ("Figure 4", "CGM digital phenotype layer", "JAEB phase-map, external validation, calibration/fairness", "Use npj P0 and extension outputs."),
            ("Figure 5", "Bridge cohort design", "Urine/food assay + standardized meal + CGM phase-map + software output", "New protocol figure."),
        ],
        columns=["figure", "message", "content", "source_or_action"],
    )
    storyboard.to_csv(TABLES / "integrated_manuscript_storyboard.csv", index=False)

    bridge_design = pd.DataFrame(
        [
            ("Cohort", "80-120 adults spanning normoglycaemia, prediabetes and treated/non-insulin type 2 diabetes", "baseline demographics, diet, medication, HbA1c, fasting glucose, insulin, lipids, anthropometrics", "screening/baseline", "balanced coverage of susceptibility strata", "Creates the same-person bridge missing from NHANES, CGMacros and JAEB."),
            ("Food-system exposure", "all enrolled participants", "two first-morning urine plasticizer panels plus targeted food/packaging-contact plasticizer assays", "baseline and challenge days", "DEHP oxidative fraction, total plasticizer burden, food-contact burden", "Uses routinely encountered exposure; no intentional plasticizer dosing."),
            ("Free-living CGM", "all enrolled participants", "14-28 day CGM with meal logs and activity/sleep covariates", "before and after meal-challenge block", "phase-map assignment, glycaemic burden, variability, postprandial excursion features", "Connects acute meal response to longer-horizon digital phenotype."),
            ("Standardized meal challenge", "all enrolled participants, randomized crossover where feasible", "2x2 meals: high vs low matrix protection crossed with higher vs lower measured food-contact burden; matched energy and carbohydrate", "4 challenge visits or compact Latin-square schedule", "2h iAUC, peak delta, high-iAUC probability, time-to-peak", "Directly tests whether matrix protection modifies PPGR under controlled exposure-contact contexts."),
            ("Mechanistic add-on", "selected meal prototypes", "in vitro digestion/glucose release plus chemical migration assay", "pre-study assay and companion experiment", "glucose release rate, available carbohydrate kinetics, measured plasticizer concentration", "Links human PPGR effects to meal structure and measured food chemistry."),
            ("Software output", "all analysis-ready participants", "integrated pipeline for MSI, meal-risk score and phase-map phenotype", "analysis freeze", "reproducible phenotype report and versioned package", "Turns the integrated study into a reusable digital nutrition phenotype tool."),
        ],
        columns=["module", "population_or_unit", "measurement", "timing", "primary_endpoint", "why_it_fills_gap"],
    )
    bridge_design.to_csv(TABLES / "bridge_cohort_design_matrix.csv", index=False)

    endpoints = pd.DataFrame(
        [
            ("Primary 1", "Exposure-linked susceptibility", "Higher DEHP oxidative fraction and food-contact burden are associated with higher MSI-core and less favourable CGM phase/order parameters.", "Bridge cohort", "survey-style regression for biomarker outcomes; ordinal/multinomial or one-vs-rest phase models for phase membership", "standardized effect per prespecified exposure contrast", "Adjust for age, sex, race/ethnicity, BMI, energy intake, smoking/alcohol, activity, creatinine, diabetes medication and CGM wear quality."),
            ("Primary 2", "Meal matrix response", "High-protection matrix lowers PPGR severity, especially in high-MSI/high-exposure participants.", "Bridge cohort meal challenge + CGMacros prior", "mixed-effects/GEE model with subject random/intercept or exchangeable correlation; exposure x matrix x MSI interactions", "difference in 2h iAUC and high-iAUC risk", "Equal carbohydrate/energy design; report interaction as hypothesis-generating if precision is limited."),
            ("Primary 3", "Digital phenotype transport", "The locked phase-map assigns interpretable CGM phenotypes in nutrition/food-exposure cohorts and orders PPGR susceptibility.", "CGMacros feasibility + bridge cohort", "frozen phase-map assignment followed by calibration/ranking audit", "phase-specific PPGR and biomarker gradients", "Do not present absolute risk as clinical decision support unless target calibration is acceptable."),
            ("Secondary 1", "Counterfactual redesign", "Replacing low-protection meals with high-protection equivalents reduces predicted high-iAUC risk.", "CGMacros + bridge validation", "locked meal-risk model; prospective validation on standardized meals", "risk difference and observed iAUC difference", "Clearly separate model-estimated reduction from intervention-confirmed reduction."),
            ("Secondary 2", "Mediation/chain evidence", "MSI and PPGR partially link food-system exposure to CGM phase/order parameters.", "Bridge cohort", "predeclared mediation/path model with sensitivity analysis", "indirect-effect direction and uncertainty", "Only claim mechanistic consistency unless temporal ordering and repeated measures are strong."),
            ("Secondary 3", "Fairness/transportability", "Phase-map and meal-risk ordering remains transparent across sex, race/ethnicity and diabetes-status strata.", "JAEB external validation + bridge cohort", "bootstrap AUROC/ECE/calibration curves with minimum-n reporting", "subgroup performance with CI", "Small-n strata are descriptive only."),
        ],
        columns=["endpoint_id", "theme", "hypothesis", "dataset", "analysis_model", "estimand", "guardrail"],
    )
    endpoints.to_csv(TABLES / "integrated_primary_secondary_endpoints.csv", index=False)

    claim_map = f"""
# One-page claim map: one integrated study

## Working title

Food-system exposures and meal matrices define CGM digital phenotypes of metabolic vulnerability

## Central claim

Food-system chemical exposures and meal matrix structure should be treated as upstream determinants of metabolic susceptibility, while PPGR and CGM phase-map membership are two time scales of the same measurable vulnerability: acute meal expression and longer-horizon digital phenotype.

## What the present evidence can support now

1. NHANES gives the population exposure anchor: a 10 percentage-point higher oxidative DEHP fraction is associated with MSI-core (beta {fmt(pct_msi.effect)}, 95% CI {fmt(pct_msi.effect_low)} to {fmt(pct_msi.effect_high)}), HOMA-IR ({fmt(pct_homa.effect)}% difference) and HbA1c (beta {fmt(pct_hba1c.effect)}).
2. CGMacros gives the meal-expression layer: MSI-core is associated with log1p iAUC ({msi_log.estimate_CI}), peak delta ({msi_peak.estimate_CI}) and high-iAUC risk ({msi_high.estimate_CI}); food matrix class adds signal beyond macro/timing covariates.
3. JAEB/Loop/PSO gives the dynamic digital phenotype layer: the locked phase-map is stable (ARI median {fmt(phase_stab.adjusted_rand_index.median())}) and externally predictive in Loop and PSO3/4.

## What must not be overstated

The existing datasets do not yet prove that plasticizer exposure causes PPGR vulnerability or CGM phase membership in the same individuals. The honest current framing is triangulated evidence across complementary cohorts. The bridge cohort is the study component that turns the framework into a direct same-person test.

## Manuscript abstract skeleton

Food systems shape metabolic health through both chemical exposures and the physical structure of meals, yet these influences are rarely connected to continuous glucose monitoring (CGM) phenotypes. We integrated population biomonitoring, real-world meal response and public CGM trial data to define a multi-timescale digital phenotype of metabolic vulnerability. In NHANES 2013-2018, a higher oxidative DEHP profile was associated with MSI-core, HOMA-IR and HbA1c, providing a population exposure anchor. In CGMacros, MSI-core and food matrix protection jointly organized postprandial glucose response across repeated meals, and a subject-held-out model improved high-iAUC discrimination from {fmt(m1.high_iauc_auc)} to {fmt(m3.high_iauc_auc)}. In JAEB-derived CGM studies, a locked five-phase map was reproducible and transported to Loop and PSO cohorts for HbA1c/TIR response ranking. These findings support a unified model in which food-system exposure and meal matrix shape susceptibility that is expressed acutely as PPGR and dynamically as CGM phase membership. A prospective bridge cohort with urine and food-contact plasticizer assays, standardized meals and 14-28 day CGM is required for direct causal-pathway testing.

## Figure spine

Figure 1 should show the integrated evidence architecture and explicitly mark which edges are direct and which require the bridge cohort. Figure 2 anchors exposure in NHANES. Figure 3 shows meal-expression in CGMacros. Figure 4 shows the CGM digital phenotype and external validation. Figure 5 is the prospective bridge cohort design and analysis workflow.
"""
    write(DOCS / "one_page_claim_map_and_abstract_zh.md", claim_map)

    bridge_protocol = """
# Bridge cohort protocol and SAP skeleton

## Purpose

The bridge cohort is not an optional embellishment. It is the missing study layer that lets the integrated project test the same-person chain: food-system exposure -> metabolic susceptibility -> PPGR vulnerability -> CGM digital phenotype.

## Design

Enroll 80-120 adults across a deliberate susceptibility gradient: normoglycaemia, prediabetes and treated/non-insulin type 2 diabetes. The study should use repeated urine collection, targeted food and packaging-contact assays, standardized meals and 14-28 days of CGM. Participants should not be intentionally dosed with plasticizers. The exposure contrast should come from measured, routinely encountered food-contact and processing contexts, pre-assayed before human testing.

## Schedule

Baseline: demographics, medical history, medication inventory, diet record, anthropometrics, HbA1c, fasting glucose, fasting insulin, lipids, first-morning urine plasticizer panel and CGM placement.

Free-living phase: 7-14 days CGM with meal logs, activity/sleep covariates where available and repeat first-morning urine.

Challenge phase: randomized standardized meal visits using a 2x2 structure: high vs low matrix protection crossed with higher vs lower measured food-contact burden, matched for energy and carbohydrate. If four visits are not feasible, use a compact Latin-square subset with the high-value contrasts prioritized.

Follow-up phase: continue CGM to 14-28 days total, repeat urine on at least one challenge day and collect tolerability/adherence data.

## Primary endpoints

Primary endpoint 1: association of urinary DEHP oxidative fraction and measured food-contact burden with MSI-core and CGM phase/order parameters.

Primary endpoint 2: standardized-meal effect of matrix protection on 2h iAUC, peak glucose delta and high-iAUC probability, with prespecified effect modification by MSI-core and exposure burden.

Primary endpoint 3: feasibility and validity of assigning the locked CGM phase-map in a nutrition/food-exposure cohort, evaluated by wear-quality pass rate, phase distribution, phase stability and phase-wise PPGR gradients.

## Statistical analysis plan

Use the NHANES covariate logic as the exposure-anchor template and the CGMacros GEE/mixed model as the meal-response template. For exposure composition, keep the total-burden-adjusted oxidative-vs-primary contrast. For meal challenge outcomes, use repeated-meal models with participant clustering and prespecified covariates: age, sex, race/ethnicity, BMI, diabetes status/medication, energy intake, smoking/alcohol, physical activity, urinary creatinine, CGM wear quality and visit order. For phase membership, apply the locked JAEB phase-map first, then test associations with exposure and PPGR without refitting the phase algorithm.

## Decision rules

If calibration is weak, present outputs as phenotype/ranking rather than absolute risk. If subgroup sample size is small, report estimates with bootstrap intervals and avoid strong subgroup claims. If the food-contact assay does not generate a clean exposure contrast, keep the cohort as a susceptibility/meal-matrix validation and move chemical-exposure claims back to the NHANES anchor.

## Minimum publication value

Even as a pilot, this cohort must produce three concrete outputs: a same-person construct crosswalk, a standardized-meal validation of the CGMacros matrix result and an integrated software report that returns MSI, meal-risk and CGM phase-map phenotype for each participant.
"""
    write(DOCS / "bridge_cohort_protocol_and_sap_zh.md", bridge_protocol)

    claim_map_cn = f"""
# 一页式 claim map：整合为一项研究

## 工作题目

Food-system exposures and meal matrices define CGM digital phenotypes of metabolic vulnerability

## 中心论点

食品系统化学暴露和餐食基质结构应被视为代谢易感性的上游来源；PPGR 和 CGM phase-map membership 则是同一种易感性在两个时间尺度上的表达：前者是急性餐后表达，后者是较长时间尺度的连续血糖数字表型。

## 当前证据可以支撑什么

1. NHANES 提供人群暴露锚点：DEHP oxidative fraction 每升高 10 个百分点，与 MSI-core 升高相关，beta {fmt(pct_msi.effect)}，95% CI {fmt(pct_msi.effect_low)} to {fmt(pct_msi.effect_high)}；同时与 HOMA-IR 和 HbA1c 方向一致。
2. CGMacros 提供餐食表达层：MSI-core 与 2h log1p iAUC（{msi_log.estimate_CI}）、peak delta（{msi_peak.estimate_CI}）和 high-iAUC 风险（{msi_high.estimate_CI}）相关；food matrix class 在宏量营养素和进餐时间之外仍提供额外信息。
3. JAEB/Loop/PSO 提供动态数字表型层：locked phase-map 稳定，ARI median {fmt(phase_stab.adjusted_rand_index.median())}，并在 Loop 与 PSO3/4 中对 HbA1c/TIR response 具有外部验证价值。

## 现在不能过度声称什么

现有数据还不能证明“塑化剂暴露在同一个人身上导致 PPGR 脆弱性或 CGM phase membership”。目前最诚实、也最强的表述是：跨互补队列的 triangulated evidence。bridge cohort 是把这条证据链升级为同人群直接检验的关键。

## 摘要骨架

食品系统通过化学暴露和餐食物理结构共同影响代谢健康，但这些因素很少被连接到连续血糖监测表型。我们整合 NHANES 人群生物监测、CGMacros 真实餐食反应和 JAEB 公共 CGM 试验数据，定义一个多时间尺度的代谢易感性数字表型。在 NHANES 2013-2018 中，更高的 oxidative DEHP profile 与 MSI-core、HOMA-IR 和 HbA1c 相关，提供食品系统暴露锚点。在 CGMacros 中，MSI-core 与 food matrix protection 共同组织 repeated meals 的 PPGR，subject-held-out high-iAUC AUC 从 {fmt(m1.high_iauc_auc)} 提升到 {fmt(m3.high_iauc_auc)}。在 JAEB-derived CGM studies 中，locked five-phase map 可复现，并能迁移到 Loop 与 PSO 队列进行 HbA1c/TIR response ranking。整体结果支持一个统一模型：食品系统暴露和餐食基质塑造代谢易感性，该易感性急性表现为 PPGR，动态表现为 CGM phase membership。要直接检验这条链条，需要一个包含尿/食品接触塑化剂检测、标准餐和 14-28 天 CGM 的前瞻性 bridge cohort。

## 主图逻辑

Figure 1 显示整合证据架构，并明确标出哪些边是直接证据、哪些边需要 bridge cohort。Figure 2 锚定 NHANES 暴露层。Figure 3 展示 CGMacros 餐食表达层。Figure 4 展示 CGM 数字表型和外部验证。Figure 5 展示前瞻性 bridge cohort 设计和分析工作流。
"""
    write(DOCS / "one_page_claim_map_and_abstract_zh.md", claim_map_cn)

    bridge_protocol_cn = """
# Bridge cohort protocol and SAP skeleton

## 目的

Bridge cohort 不是锦上添花，而是整合研究缺失的核心层。它要在同一批人中直接测试：食品系统暴露 -> 代谢易感性 -> PPGR 脆弱性 -> CGM 数字表型。

## 设计

入组 80-120 名成年人，覆盖正常血糖、糖尿病前期和已治疗但非胰岛素依赖的 2 型糖尿病人群。研究包含重复尿样、目标食品/包装接触塑化剂检测、标准餐挑战和 14-28 天 CGM。不能主动给受试者“投加”塑化剂；暴露对比应来自真实生活中可遇到的食品接触和加工情境，并在人体试验前完成预检测。

## 流程

Baseline：人口学、病史、用药、饮食记录、体格测量、HbA1c、空腹血糖、空腹胰岛素、血脂、晨尿 plasticizer panel 和 CGM 佩戴。

Free-living phase：7-14 天 CGM，配合餐食日志、可获得的活动/睡眠协变量，并重复晨尿。

Challenge phase：随机化标准餐访问，采用 2x2 结构：高/低 matrix protection 交叉高/低 measured food-contact burden，并匹配能量和碳水。如果四次访问不可行，用紧凑 Latin-square 或优先保留最关键对比。

Follow-up phase：继续 CGM 至总计 14-28 天，至少在一个 challenge day 重复尿样，并记录依从性和耐受性。

## 主要终点

Primary endpoint 1：尿 DEHP oxidative fraction 与 measured food-contact burden 是否关联 MSI-core 和 CGM phase/order parameters。

Primary endpoint 2：matrix protection 是否降低标准餐 2h iAUC、peak glucose delta 和 high-iAUC probability，并检验 MSI-core 与 exposure burden 的预设效应修饰。

Primary endpoint 3：locked CGM phase-map 能否在 nutrition/food-exposure cohort 中稳定赋值，并通过 wear-quality pass rate、phase distribution、phase stability 和 phase-wise PPGR gradients 评估有效性。

## 统计分析计划

暴露锚点沿用 NHANES 的协变量逻辑，餐食反应沿用 CGMacros 的 GEE/mixed model 逻辑。暴露组成继续保留 total-burden-adjusted oxidative-vs-primary contrast。标准餐 outcome 使用 repeated-meal models，并按 participant 聚类；预设协变量包括 age、sex、race/ethnicity、BMI、diabetes status/medication、energy intake、smoking/alcohol、physical activity、urinary creatinine、CGM wear quality 和 visit order。Phase membership 先应用 locked JAEB phase-map，不重新训练 phase algorithm，再检验 exposure 和 PPGR 与 phase/order parameters 的关系。

## 决策规则

如果校准较弱，所有输出定位为 phenotype/ranking，而不是 absolute clinical risk。如果亚组样本量偏小，只报告 bootstrap intervals，不做强亚组结论。如果 food-contact assay 不能产生清晰暴露对比，则将 bridge cohort 定位为 susceptibility/meal-matrix validation，并把化学暴露主张保留在 NHANES anchor。

## 最低发表价值

即使作为 pilot，这个 cohort 也必须产出三件事：同人群 construct crosswalk、CGMacros matrix result 的标准餐验证，以及可对每个受试者输出 MSI、meal-risk 和 CGM phase-map phenotype 的整合软件报告。
"""
    write(DOCS / "bridge_cohort_protocol_and_sap_zh.md", bridge_protocol_cn)

    specific_aims_cn = f"""
# Specific Aims：食品系统暴露、餐食基质与 CGM 数字代谢易感性

## 总体问题

目前两条研究线的关键不是“能否合并”，而是如何把它们统一到一个可检验的科学命题中：食品系统暴露和餐食基质如何塑造代谢易感性，并且这种易感性如何在急性餐后血糖反应和长期 CGM 数字表型中被捕捉。

## 中心假设

食品系统塑化剂暴露与食物基质共同塑造代谢易感性。该易感性在人群层面表现为 MSI/HOMA-IR/HbA1c 异常，在餐食层面表现为更高 PPGR/iAUC/high-iAUC risk，在连续监测层面表现为可复现、可迁移的 CGM phase-map 数字表型。

## Aim 1：定义食品系统暴露相关代谢易感性

数据：NHANES 2013-2018。

核心问题：DEHP oxidative profile 是否与 MSI-core、HOMA-IR 和 HbA1c 共同指向同一类人群代谢易感性？

当前证据：DEHP oxidative fraction 每升高 10 个百分点，与 MSI-core 升高相关，beta {fmt(pct_msi.effect)}，95% CI {fmt(pct_msi.effect_low)} to {fmt(pct_msi.effect_high)}，q={fmt(pct_msi.q_value)}；与 HOMA-IR 的差异为 {fmt(pct_homa.effect)}%；与 HbA1c 的 beta 为 {fmt(pct_hba1c.effect)}。总 DEHP 调整后，ILR oxidative-vs-primary 仍与 MSI-core 相关，beta {fmt(comp_msi.effect)}。

角色：population exposure anchor。这个 Aim 不能单独证明 CGM 或 PPGR 链条，但能把研究锚定在食品系统化学暴露和人群代谢易感性上。

完成标准：保留复杂抽样设计、固定协变量、LOD/肌酐/尿稀释/糖尿病诊断或用药排除敏感性、周期复制和暴露组成模型；主文只声称 observational exposure anchor。

## Aim 2：证明代谢易感性在真实餐食中表达为 PPGR 脆弱性

数据：CGMacros。

核心问题：MSI-core 和 food matrix 是否共同决定真实餐食后的 PPGR/iAUC/high-risk meal？

当前证据：MSI-core 与 2h log1p iAUC 相关，{msi_log.estimate_CI}；与 peak glucose delta 相关，{msi_peak.estimate_CI}；与 high-iAUC risk 相关，{msi_high.estimate_CI}。Food matrix collapsed class 在宏量营养素和进餐时间之外仍保留信号。Subject-held-out high-iAUC AUC 从 {fmt(m1.high_iauc_auc)} 提升到 {fmt(m3.high_iauc_auc)}，counterfactual meal redesign 的 median predicted risk reduction 为 {fmt(cf_summary['median_risk_reduction'])}。

角色：meal-expression and modifiable matrix layer。这个 Aim 把 Aim 1 的“代谢易感性”转译成真实餐食后的 CGM 反应，并提供可干预的 food matrix lever。

完成标准：保留 GEE/subject clustering、collapsed matrix、model ladder、leave-one-subject-out leverage、counterfactual delta；明确 counterfactual 是模型估计，不等同于干预证据。

## Aim 3：用 CGM phase-map 验证动态数字代谢表型

数据：JAEB + Loop + RacialDifferences + PSO3/4。

核心问题：能否把 CGM 总结为稳定、可迁移、可审计的数字表型，并用于 HbA1c/TIR response ranking？

当前证据：JAEB phase-map 包含 {phase_features['participant_id'].nunique()} 名参与者、{len(cgm_long)} 条 CGM summary rows；bootstrap ARI median {fmt(phase_stab.adjusted_rand_index.median())}。Loop frozen validation 中 phase-map HbA1c AUROC 为 {fmt(val(loop_phase, target='y_hba1c_improved_ge_0_5').auroc)}，TIR AUROC 为 {fmt(val(loop_phase, target='y_tir_improved_ge_5pct').auroc)}。PSO3/4 pooled phase-map HbA1c AUROC 为 {fmt(val(sec_phase, validation_dataset='PSO3_PSO4_POOLED_FROZEN', target='y_hba1c_improved_ge_0_5').auroc)}，TIR AUROC 为 {fmt(val(sec_phase, validation_dataset='PSO3_PSO4_POOLED_FROZEN', target='y_tir_improved_ge_5pct').auroc)}。

角色：dynamic digital phenotype and deployment layer。这个 Aim 不是重复普通 ML benchmark，而是证明 CGM phase-map 可以作为“代谢易感性”的长期数字表型语言。

完成标准：固定算法、外部验证、calibration/fairness audit、minimum-n subgroup rule、software package；如果校准不足，输出定位为 phenotype/ranking，而非绝对风险。

## Aim 4：桥接验证

新数据：80-120 人 bridge cohort。

核心问题：能否在同一批人中直接测试 exposure -> MSI -> PPGR -> CGM phase/order parameters 的链条？

设计：重复尿塑化剂测量、食品/包装 plasticizer panel、标准餐 2x2 matrix challenge、14-28 天 CGM、HbA1c/insulin/HOMA。2x2 标准餐建议为 high vs low matrix protection 交叉 higher vs lower measured food-contact burden，并匹配碳水和能量。

角色：把当前的多数据集 triangulated evidence 升级为同人群机制/数字表型验证。

完成标准：同人群 construct crosswalk、标准餐验证 CGMacros matrix result、locked phase-map 在 nutrition/food-exposure cohort 中稳定赋值、整合软件报告同时输出 MSI、meal-risk 和 CGM phase-map phenotype。

## 整体贡献边界

Aim 1-3 是现有数据可以完成的强三角证据；Aim 4 是冲击高水平综合期刊所需的关键增量。没有 Aim 4，主张必须克制为 triangulated digital-metabolic phenotype study；完成 Aim 4 后，研究才可以主张同人群 exposure-meal-CGM phenotype chain。
"""
    write(DOCS / "specific_aims_integrated_study_zh.md", specific_aims_cn)

    report = f"""
# 整合研究框架：食品系统暴露、食物基质与 CGM 数字代谢易感性

生成日期：2026-06-18

## 核心判断

现在两条线不能简单拼成一篇“NHANES + CGMacros + JAEB 大杂烩”。更稳、更有投稿潜力的整合方式，是把它们定义为同一项多层证据研究：

**食品系统化学暴露和食物基质如何塑造可由 CGM 捕捉的代谢易感性数字表型。**

这项整合研究应有四层：

1. **Population exposure anchor**：NHANES 中 DEHP oxidative profile 与 MSI/HOMA-IR/HbA1c 相关。
2. **Meal-expression layer**：CGMacros 中 MSI 和食物基质决定 PPGR 脆弱性。
3. **Dynamic digital phenotype layer**：JAEB 中 CGM phase-map 将长期 CGM 状态组织为可复现数字表型，并预测 HbA1c/TIR response。
4. **Bridge cohort layer**：在同一批人中同时测尿/食品塑化剂、食物基质、标准餐 PPGR 和 free-living CGM phase-map，补齐当前无法直接证明的链条。

## 统一科学问题

> Food-system chemical exposures and meal matrices may shape metabolic susceptibility that is expressed acutely as PPGR vulnerability and dynamically as CGM phase-map digital phenotypes.

中文可以写成：

> 食品系统化学暴露与食物基质可能塑造代谢易感性；这种易感性在短时间尺度上表现为餐后血糖反应脆弱性，在长期连续血糖监测中表现为可计算的 CGM 数字表型。

## 当前直接证据

### 1. NHANES：食品系统塑化剂暴露锚定 MSI/代谢易感性

- 10 percentage-point higher oxidative DEHP fraction 与 MSI-core 相关：beta {fmt(pct_msi.effect)}，95% CI {fmt(pct_msi.effect_low)} to {fmt(pct_msi.effect_high)}，q={fmt(pct_msi.q_value)}。
- 同一暴露 contrast 与 HOMA-IR 相关：{fmt(pct_homa.effect)}% difference，95% CI {fmt(pct_homa.effect_low)} to {fmt(pct_homa.effect_high)}。
- 与 HbA1c 相关：beta {fmt(pct_hba1c.effect)}，95% CI {fmt(pct_hba1c.effect_low)} to {fmt(pct_hba1c.effect_high)}。
- 总 DEHP 调整后，ILR oxidative-vs-primary 仍与 MSI-core 相关：beta {fmt(comp_msi.effect)}，95% CI {fmt(comp_msi.effect_low)} to {fmt(comp_msi.effect_high)}。

这给出 population-level exposure anchor，但没有 CGM phase 和 PPGR。

### 2. CGMacros：MSI 与食物基质表达为 PPGR 脆弱性

- MSI-core 与 2h log1p iAUC 相关：{msi_log.estimate_CI}。
- MSI-core 与 peak glucose delta 相关：{msi_peak.estimate_CI}。
- MSI-core 与 high-iAUC meal risk 相关：log-odds {msi_high.estimate_CI}。
- Mixed/unknown matrix 相对 protective matrix：log1p iAUC beta {matrix_log.estimate_CI}；high-iAUC log-odds {matrix_high.estimate_CI}。
- Subject-held-out model ladder：macro/timing AUC {fmt(m1.high_iauc_auc)}；MSI + food matrix AUC {fmt(m3.high_iauc_auc)}。
- Counterfactual meal redesign：候选餐 median predicted risk reduction {fmt(cf_summary['median_risk_reduction'])}。

这给出 meal-expression layer，但没有塑化剂 biomarker，也没有长期 phase-map。

### 3. JAEB/Loop/PSO：CGM phase-map 是可验证数字表型

- JAEB phase-map 样本：{phase_features['participant_id'].nunique()} 名；CGM summary rows：{len(cgm_long)}。
- Bootstrap ARI median {fmt(phase_stab.adjusted_rand_index.median())}，IQR {fmt(phase_stab.adjusted_rand_index.quantile(0.25))}-{fmt(phase_stab.adjusted_rand_index.quantile(0.75))}。
- Loop frozen validation phase-map AUROC：HbA1c response {fmt(val(loop_phase, target='y_hba1c_improved_ge_0_5').auroc)}；TIR response {fmt(val(loop_phase, target='y_tir_improved_ge_5pct').auroc)}。
- PSO3/4 pooled phase-map AUROC：HbA1c response {fmt(val(sec_phase, validation_dataset='PSO3_PSO4_POOLED_FROZEN', target='y_hba1c_improved_ge_0_5').auroc)}；TIR response {fmt(val(sec_phase, validation_dataset='PSO3_PSO4_POOLED_FROZEN', target='y_tir_improved_ge_5pct').auroc)}。
- 最大 phase-stratified HTE：adjusted RD {fmt(hte.adjusted_risk_difference.max())}。

这给出 dynamic digital phenotype layer，但没有食物基质和塑化剂暴露。

## 断点与补法

最关键的断点不是统计结果不足，而是“同一个人身上没有同时测三类东西”：

1. NHANES 有塑化剂和 MSI/HOMA/HbA1c，但没有 CGM/PPGR。
2. CGMacros 有 CGM meal response 和食物基质，但没有塑化剂 biomarker。
3. JAEB 有强 CGM phase-map 和外部验证，但没有食物基质/塑化剂。

所以主文必须把当前证据写成 **triangulated evidence**，而不是完整 causal chain。真正补齐需要一个 bridge cohort。

## 整合后的 Aims

### Aim 1：定义食品系统暴露相关代谢易感性

数据：NHANES 2013-2018。  
输出：DEHP oxidative profile -> MSI/HOMA-IR/HbA1c。  
角色：population exposure anchor。

### Aim 2：证明代谢易感性在真实餐食中表达为 PPGR 脆弱性

数据：CGMacros。  
输出：MSI-core + food matrix -> PPGR/iAUC/high-risk meal；counterfactual meal redesign。  
角色：meal-expression and modifiable matrix layer。

### Aim 3：用 CGM phase-map 验证动态数字代谢表型

数据：JAEB + Loop + RacialDifferences + PSO3/4。  
输出：phase-map stability、external validation、calibration/fairness、software package。  
角色：dynamic digital phenotype and deployment layer。

### Aim 4：桥接验证

新数据：80-120 人 bridge cohort。  
测量：尿塑化剂、食品/包装 plasticizer panel、标准餐 2x2 matrix challenge、14-28 天 CGM、HbA1c/insulin/HOMA。  
输出：直接测试 exposure -> MSI -> PPGR -> CGM phase/order parameters 的同人群链条。  
角色：让这项整合研究从“多数据集三角证据”升级为“同人群机制/数字表型验证”。

## 建议题目

**Food-system exposures and meal matrices define CGM digital phenotypes of metabolic vulnerability**

备选更克制版本：

**Triangulating food-system exposures, meal matrices and CGM digital phenotypes of metabolic vulnerability across population, meal and trial cohorts**

## 投稿定位

如果没有 Aim 4 bridge cohort，文章应定位为高质量 integrative/triangulation study，适合数字营养、营养代谢信息学或 digital medicine 方向，但冲顶刊风险仍高。

如果完成 Aim 4，整合后才真正像一项完整高水平研究：有食品系统暴露、有真实餐食/标准餐机制、有 CGM 数字表型、有软件化输出和外部验证。

## 本次生成文件

- `tables/integrated_evidence_chain.csv`
- `tables/cross_study_construct_crosswalk.csv`
- `tables/disconnected_points_and_fixes.csv`
- `tables/integrated_aims.csv`
- `tables/integrated_next_tasks.csv`
- `tables/integrated_manuscript_storyboard.csv`
- `figure_source_data/integrated_study_dag_nodes.csv`
- `figure_source_data/integrated_study_dag_edges.csv`
"""
    write(DOCS / "integrated_study_framework_zh.md", report)

    manifest = {
        "created": "2026-06-18",
        "objective": "Integrate Nature Food and JAEB/npj Digital Medicine research lines into one coherent study framework",
        "outputs": [
            str(DOCS / "integrated_study_framework_zh.md"),
            str(TABLES / "integrated_evidence_chain.csv"),
            str(TABLES / "cross_study_construct_crosswalk.csv"),
            str(TABLES / "disconnected_points_and_fixes.csv"),
            str(TABLES / "integrated_aims.csv"),
            str(TABLES / "integrated_next_tasks.csv"),
            str(TABLES / "integrated_manuscript_storyboard.csv"),
            str(TABLES / "bridge_cohort_design_matrix.csv"),
            str(TABLES / "integrated_primary_secondary_endpoints.csv"),
            str(DOCS / "one_page_claim_map_and_abstract_zh.md"),
            str(DOCS / "bridge_cohort_protocol_and_sap_zh.md"),
            str(DOCS / "specific_aims_integrated_study_zh.md"),
            str(FIGSRC / "integrated_study_dag_nodes.csv"),
            str(FIGSRC / "integrated_study_dag_edges.csv"),
        ],
    }
    (OUT / "integrated_study_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote integrated study framework to {OUT}")


if __name__ == "__main__":
    main()
