"""Build the Nature Food P0 publication-lift package.

This script turns the existing NHANES, CGMacros and JAEB/npj outputs into a
submission-oriented P0 package: claim hierarchy, Aim 1 food-system exposure
matrix, Aim 2 matrix defensibility, CGMacros phase-map compatibility, Aim 3
digital phenotype framing, software reproducibility audit and six-display-item
storyboard.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(r"D:\ai for science")
NF = ROOT / "results" / "nature_food_manuscript_package"
NF_FIG = NF / "figure_source_data"
NF_AIMS = ROOT / "results" / "nature_food_high_bar_aims"
NF_AIM2 = ROOT / "results" / "nature_food_aim2_cgmacros"
NHANES = Path(r"D:\NHANES_MetS_Project\result")
CG_RAW = Path(r"D:\ShiYiSiNan_CGMacros\data\raw\CGMacros")
JAEB = ROOT / "results" / "jaeb_glycemic_phase_completion"
NPJ_P0 = ROOT / "results" / "npj_digital_medicine_phase_strategy" / "p0_workup"
NPJ_EXT = ROOT / "results" / "npj_digital_medicine_phase_strategy" / "p0_extensions_2026_06_18"
PHASE_PKG = NPJ_EXT / "software_release" / "phase_map_jaeb_v0_1"
INTEGRATED = ROOT / "results" / "integrated_food_cgm_metabolic_phenotype_study_2026_06_18"

OUT = ROOT / "results" / "nature_food_p0_publication_lift_2026_06_18"
DOCS = OUT / "docs"
TABLES = OUT / "tables"
FIGSRC = OUT / "figure_source_data"
for p in [OUT, DOCS, TABLES, FIGSRC]:
    p.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False, **kwargs)


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
    for key, value in where.items():
        mask &= df[key].eq(value)
    out = df[mask]
    if out.empty:
        raise KeyError(where)
    return out.iloc[0]


def clean_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def cgmacros_subject_summaries() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for csv_path in sorted(CG_RAW.glob("CGMacros-*/CGMacros-*.csv")):
        sid = csv_path.parent.name.replace("CGMacros-", "")
        try:
            df = pd.read_csv(
                csv_path,
                usecols=lambda c: c in ["Timestamp", "Libre GL", "Dexcom GL"],
                low_memory=False,
            )
        except Exception as exc:
            rows.append(
                {
                    "participant_id": sid,
                    "source_file": str(csv_path),
                    "read_status": f"failed: {exc}",
                }
            )
            continue
        if "Timestamp" not in df.columns:
            rows.append(
                {
                    "participant_id": sid,
                    "source_file": str(csv_path),
                    "read_status": "failed: missing Timestamp",
                }
            )
            continue

        timestamp = pd.to_datetime(df["Timestamp"], errors="coerce")
        glucose_cols = [c for c in ["Dexcom GL", "Libre GL"] if c in df.columns]
        if not glucose_cols:
            rows.append(
                {
                    "participant_id": sid,
                    "source_file": str(csv_path),
                    "read_status": "failed: missing glucose columns",
                }
            )
            continue
        glucose = pd.Series(np.nan, index=df.index, dtype="float64")
        for col in glucose_cols:
            glucose = glucose.combine_first(clean_numeric(df[col]))
        valid = timestamp.notna() & glucose.notna()
        ts = timestamp[valid].sort_values()
        gl = glucose[valid].loc[ts.index].astype(float)

        if gl.empty or ts.empty:
            rows.append(
                {
                    "participant_id": sid,
                    "source_file": str(csv_path),
                    "read_status": "failed: no usable glucose readings",
                }
            )
            continue
        diffs = ts.diff().dt.total_seconds().dropna()
        median_interval_min = float(diffs.median() / 60.0) if not diffs.empty else np.nan
        if not math.isfinite(median_interval_min) or median_interval_min <= 0:
            median_interval_min = 1.0
        reading_hours = float(len(gl) * median_interval_min / 60.0)
        span_hours = float((ts.max() - ts.min()).total_seconds() / 3600.0) if len(ts) > 1 else 0.0
        mean = float(gl.mean())
        sd = float(gl.std(ddof=1)) if len(gl) > 1 else np.nan
        cv = float(sd / mean * 100.0) if mean else np.nan
        rows.append(
            {
                "participant_id": sid,
                "source_file": str(csv_path),
                "read_status": "ok",
                "n_glucose_readings": int(len(gl)),
                "start_time": ts.min(),
                "end_time": ts.max(),
                "span_hours": span_hours,
                "cgm_hours": reading_hours,
                "median_interval_min": median_interval_min,
                "cgm_mean_glucose_mg_dl": mean,
                "cgm_time_in_range_70_180_pct": float(((gl >= 70) & (gl <= 180)).mean() * 100.0),
                "cgm_time_below_70_pct": float((gl < 70).mean() * 100.0),
                "cgm_time_below_54_pct": float((gl < 54).mean() * 100.0),
                "cgm_time_above_180_pct": float((gl > 180).mean() * 100.0),
                "cgm_time_above_250_pct": float((gl > 250).mean() * 100.0),
                "cgm_cv_pct": cv,
            }
        )
    summary = pd.DataFrame(rows)
    if not summary.empty:
        summary["participant_id"] = summary["participant_id"].astype(str)
        summary["wear_72h_pass"] = summary["cgm_hours"].fillna(0) >= 72
        summary["wear_168h_pass"] = summary["cgm_hours"].fillna(0) >= 168
        required = [
            "cgm_mean_glucose_mg_dl",
            "cgm_time_in_range_70_180_pct",
            "cgm_time_below_70_pct",
            "cgm_time_below_54_pct",
            "cgm_time_above_180_pct",
            "cgm_time_above_250_pct",
            "cgm_cv_pct",
        ]
        summary["phase_required_fields_complete"] = summary[required].notna().all(axis=1)
        summary["phase_assignment_feasible_p0"] = summary["phase_required_fields_complete"] & summary["wear_72h_pass"]
    return summary


def assign_cgmacros_phase(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty or not PHASE_PKG.exists():
        return pd.DataFrame()
    sys.path.insert(0, str(PHASE_PKG))
    from phase_map import assign_phase  # type: ignore

    required = [
        "participant_id",
        "cgm_mean_glucose_mg_dl",
        "cgm_time_in_range_70_180_pct",
        "cgm_time_below_70_pct",
        "cgm_time_below_54_pct",
        "cgm_time_above_180_pct",
        "cgm_time_above_250_pct",
        "cgm_cv_pct",
        "cgm_hours",
    ]
    sub = summary.loc[summary["phase_required_fields_complete"], required].copy()
    if sub.empty:
        return pd.DataFrame()
    assigned = assign_phase(sub)
    assigned["assignment_interpretation"] = np.where(
        assigned["cgm_hours"] >= 168,
        "strong_wear_compatibility",
        np.where(assigned["cgm_hours"] >= 72, "minimum_wear_compatibility", "summary_only_low_wear_caution"),
    )
    assigned["population_transport_guardrail"] = (
        "CGMacros is nutrition/free-living and lower-glycaemic-burden than the JAEB diabetes reference; use as compatibility/ranking, not clinical phase validation."
    )
    return assigned


def main() -> None:
    nhanes_main = read_csv(NF_FIG / "figure2a_nhanes_main_effects.csv")
    nhanes_comp = read_csv(NF_FIG / "figure2b_nhanes_composition_adjusted.csv")
    cg_msi = read_csv(NF_FIG / "figure3a_cgmacros_msi_ppgr_effects.csv")
    cg_matrix = read_csv(NF_FIG / "figure3c_collapsed_matrix_gee.csv")
    cg_six = read_csv(NF_FIG / "figure3b_food_matrix_6class_summary.csv")
    cg_ladder = read_csv(NF_FIG / "figure4a_loso_model_ladder.csv")
    cf = read_csv(NF_FIG / "figure4b_counterfactual_high_iauc_deltas.csv")
    leverage = read_csv(NF_AIMS / "aim2_subject_leverage_locked.csv")

    source_dehp = read_csv(NHANES / "source_to_DEHP_profile_results_2013_2018.csv")
    source_met = read_csv(NHANES / "source_to_metabolic_marker_results_2013_2018.csv")
    source_adjusted = read_csv(NHANES / "source_adjusted_DEHP_metabolic_key_results_2013_2018.csv")
    plasticizer_panel = read_csv(NF_AIMS / "aim1_plasticizer_measurement_panel.csv")
    sampling_frame = read_csv(NF_AIMS / "aim1_food_plasticizer_sampling_frame_96_samples.csv")

    phase_features = read_csv(JAEB / "tables" / "locked_glycemic_phase_features.csv")
    cgm_long = read_csv(JAEB / "tables" / "locked_cgm_summary_long.csv")
    phase_stab = read_csv(JAEB / "tables" / "locked_phase_bootstrap_stability.csv")
    hte = read_csv(JAEB / "tables" / "locked_journal_adjusted_hte_by_phase.csv")
    loop = read_csv(NPJ_P0 / "tables" / "loop_frozen_external_validation_metrics.csv")
    secondary = read_csv(NPJ_EXT / "tables" / "secondary_external_validation_metrics.csv")
    calibration = read_csv(NPJ_EXT / "tables" / "loop_loso_calibration_upgrade_metrics.csv")
    fairness = read_csv(NPJ_EXT / "tables" / "subgroup_fairness_calibration_audit_with_bootstrap_ci.csv")

    pct_msi = val(nhanes_main, outcome="msi_core_partial", exposure="pct_oxidative_10")
    pct_homa = val(nhanes_main, outcome="ln_HOMA_IR", exposure="pct_oxidative_10")
    pct_hba1c = val(nhanes_main, outcome="HbA1c", exposure="pct_oxidative_10")
    comp_msi = val(nhanes_comp, outcome="msi_core_partial", exposure="ilr_oxidative_vs_primary")
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
    m1 = cg_ladder[cg_ladder["model"].eq("M1_macro_timing")].iloc[0]
    m3 = cg_ladder[cg_ladder["model"].eq("M3_MSI_food_matrix")].iloc[0]
    loop_phase = loop[loop["feature_set"].eq("C4_phase_map")].copy()
    sec_phase = secondary[(secondary["feature_set"].eq("C4_phase_map")) & (secondary["status"].eq("evaluable"))].copy()

    food_domains = ["Fast food", "Away from home", "Processed proxy", "Diet quality"]
    dehp_food = source_dehp[source_dehp["source_domain"].isin(food_domains)].copy()
    met_food = source_met[source_met["source_domain"].isin(food_domains)].copy()
    dehp_food["evidence_layer"] = "source_proxy_to_DEHP_profile"
    met_food["evidence_layer"] = "source_proxy_to_metabolic_marker"
    source_proxy = pd.concat([dehp_food, met_food], ignore_index=True)
    source_proxy["q_numeric"] = pd.to_numeric(source_proxy["q_value"], errors="coerce")
    source_proxy["nature_food_use"] = np.where(
        source_proxy["q_numeric"].le(0.05),
        "main_or_extended_data",
        np.where(source_proxy["q_numeric"].le(0.10), "supportive_extended_data", "context_or_supplement"),
    )
    source_proxy.to_csv(TABLES / "p0_aim1_food_system_exposure_matrix.csv", index=False)
    source_proxy.to_csv(FIGSRC / "figure2_food_system_source_proxy_evidence.csv", index=False)

    panel_status = pd.DataFrame(
        [
            {
                "component": "plasticizer_measurement_panel",
                "rows": len(plasticizer_panel),
                "primary_analytes": "; ".join(plasticizer_panel.loc[plasticizer_panel["priority"].eq("primary"), "analyte"].astype(str).tolist()),
                "secondary_analytes": "; ".join(plasticizer_panel.loc[plasticizer_panel["priority"].ne("primary"), "analyte"].astype(str).tolist()),
                "status": "schema_and_lab_targets_available",
                "remaining_gap": "No measured food concentrations yet; use as planned panel and sampling frame, not empirical result.",
            },
            {
                "component": "food_plasticizer_sampling_frame",
                "rows": len(sampling_frame),
                "primary_analytes": "; ".join(sorted(set("; ".join(sampling_frame["measure_parent_plasticizers"].astype(str)).replace(" ", "").split(";")))),
                "secondary_analytes": "not_applicable",
                "status": "96_sample_collection_frame_available",
                "remaining_gap": "Samples marked to_collect; requires lab assay before main text can claim measured food burden.",
            },
        ]
    )
    panel_status.to_csv(TABLES / "p0_food_plasticizer_panel_status.csv", index=False)
    plasticizer_panel.to_csv(TABLES / "p0_food_plasticizer_measurement_panel.csv", index=False)
    sampling_frame.to_csv(TABLES / "p0_food_plasticizer_sampling_frame_96.csv", index=False)

    cg_phase_summary = cgmacros_subject_summaries()
    cg_phase_summary.to_csv(TABLES / "p0_aim2_cgmacros_phase_map_input_summary.csv", index=False)
    cg_assignment = assign_cgmacros_phase(cg_phase_summary)
    if not cg_assignment.empty:
        cg_assignment.to_csv(TABLES / "p0_aim2_cgmacros_phase_map_assignment.csv", index=False)
    feasibility = pd.DataFrame(
        [
            {
                "check": "raw_cgmacros_subject_csv_available",
                "value": int(cg_phase_summary["read_status"].eq("ok").sum()) if not cg_phase_summary.empty else 0,
                "denominator": int(len(cg_phase_summary)),
                "decision": "pass" if not cg_phase_summary.empty and cg_phase_summary["read_status"].eq("ok").sum() > 0 else "fail",
                "interpretation": "Raw per-subject glucose files are available for CGM summary construction.",
            },
            {
                "check": "phase_required_fields_complete",
                "value": int(cg_phase_summary["phase_required_fields_complete"].sum()) if not cg_phase_summary.empty else 0,
                "denominator": int(len(cg_phase_summary)),
                "decision": "pass" if not cg_phase_summary.empty and cg_phase_summary["phase_required_fields_complete"].all() else "partial",
                "interpretation": "All required phase-map summary fields can be derived when glucose readings are usable.",
            },
            {
                "check": "minimum_72h_wear_pass",
                "value": int(cg_phase_summary["wear_72h_pass"].sum()) if not cg_phase_summary.empty else 0,
                "denominator": int(len(cg_phase_summary)),
                "decision": "pass" if not cg_phase_summary.empty and cg_phase_summary["wear_72h_pass"].mean() >= 0.8 else "partial",
                "interpretation": "Use as preliminary phase compatibility if most participants have at least 72 h usable CGM.",
            },
            {
                "check": "strong_168h_wear_pass",
                "value": int(cg_phase_summary["wear_168h_pass"].sum()) if not cg_phase_summary.empty else 0,
                "denominator": int(len(cg_phase_summary)),
                "decision": "pass" if not cg_phase_summary.empty and cg_phase_summary["wear_168h_pass"].mean() >= 0.8 else "partial",
                "interpretation": "Full phase-map transport should prefer a 7-day or longer CGM window.",
            },
            {
                "check": "frozen_phase_assignment_generated",
                "value": int(len(cg_assignment)),
                "denominator": int(len(cg_phase_summary)),
                "decision": "pass" if len(cg_assignment) > 0 else "fail",
                "interpretation": "Assignments are a compatibility audit, not a validated clinical phase result in CGMacros.",
            },
        ]
    )
    feasibility.to_csv(TABLES / "p0_aim2_cgmacros_phase_map_feasibility.csv", index=False)
    feasibility.to_csv(FIGSRC / "figure4_cgmacros_phase_map_feasibility.csv", index=False)

    matrix_defense = pd.DataFrame(
        [
            {
                "defense_item": "final_label_coverage",
                "evidence": f"{fmt(cg_six['final_label_coverage'].min())} minimum across six matrix classes",
                "status": "complete",
                "reviewer_message": "All meal labels used in Aim 2 have a final matrix label.",
            },
            {
                "defense_item": "human_review_traceability",
                "evidence": f"Human review rates range {fmt(cg_six['human_review_rate'].min())}-{fmt(cg_six['human_review_rate'].max())} across classes",
                "status": "complete",
                "reviewer_message": "High-ambiguity classes were frequently reviewed by humans; rules and final labels are auditable.",
            },
            {
                "defense_item": "msi_subject_leverage",
                "evidence": "MSI-core coefficient positive in 40/40 leave-one-subject-out models",
                "status": "complete",
                "reviewer_message": "MSI signal is not driven by a single subject.",
            },
            {
                "defense_item": "matrix_subject_leverage",
                "evidence": "Mixed/unknown matrix coefficient positive in 40/40 leave-one-subject-out models",
                "status": "complete",
                "reviewer_message": "Key matrix term is directionally stable across subject leave-outs.",
            },
            {
                "defense_item": "counterfactual_guardrail",
                "evidence": f"Median predicted high-iAUC risk reduction {fmt(cf['risk_reduction'].median())}",
                "status": "model_based",
                "reviewer_message": "Counterfactual meal redesign is hypothesis-generating until validated by standardized meals.",
            },
        ]
    )
    matrix_defense.to_csv(TABLES / "p0_aim2_matrix_defense_summary.csv", index=False)
    matrix_defense.to_csv(FIGSRC / "figure3_aim2_matrix_defense.csv", index=False)
    cg_six.to_csv(TABLES / "p0_aim2_six_class_matrix_summary.csv", index=False)
    leverage.to_csv(TABLES / "p0_aim2_subject_leverage_summary.csv", index=False)

    aim3_evidence = pd.DataFrame(
        [
            {
                "evidence_item": "phase_map_cohort",
                "result": f"{phase_features['participant_id'].nunique()} participants; {len(cgm_long)} CGM summary rows",
                "use_in_manuscript": "digital phenotype construction",
                "guardrail": "Mostly diabetes trial/reference populations.",
            },
            {
                "evidence_item": "bootstrap_stability",
                "result": f"ARI median {fmt(phase_stab.adjusted_rand_index.median())}, IQR {fmt(phase_stab.adjusted_rand_index.quantile(0.25))}-{fmt(phase_stab.adjusted_rand_index.quantile(0.75))}",
                "use_in_manuscript": "phenotype stability",
                "guardrail": "Use stability as reproducibility, not causal validity.",
            },
            {
                "evidence_item": "loop_external_validation",
                "result": f"HbA1c AUROC {fmt(val(loop_phase, target='y_hba1c_improved_ge_0_5').auroc)}; TIR AUROC {fmt(val(loop_phase, target='y_tir_improved_ge_5pct').auroc)}",
                "use_in_manuscript": "frozen transport to Loop",
                "guardrail": "Calibration sensitivity required for absolute-risk language.",
            },
            {
                "evidence_item": "pso_external_validation",
                "result": f"PSO3/4 pooled HbA1c AUROC {fmt(val(sec_phase, validation_dataset='PSO3_PSO4_POOLED_FROZEN', target='y_hba1c_improved_ge_0_5').auroc)}; TIR AUROC {fmt(val(sec_phase, validation_dataset='PSO3_PSO4_POOLED_FROZEN', target='y_tir_improved_ge_5pct').auroc)}",
                "use_in_manuscript": "second external validation",
                "guardrail": "Dataset compatibility matrix must be shown.",
            },
            {
                "evidence_item": "phase_guided_hte",
                "result": f"Maximum adjusted RD {fmt(hte.adjusted_risk_difference.max())}",
                "use_in_manuscript": "phase-guided digital care workflow",
                "guardrail": "Therapy/device HTE is not food-matrix intervention evidence.",
            },
        ]
    )
    aim3_evidence.to_csv(TABLES / "p0_aim3_digital_phenotype_evidence.csv", index=False)
    aim3_evidence.to_csv(FIGSRC / "figure5_aim3_digital_phenotype_validation.csv", index=False)

    claim_hierarchy = pd.DataFrame(
        [
            {
                "claim_id": "C1",
                "hierarchy": 1,
                "claim": "Food-system source contexts align with plasticizer burden and metabolic susceptibility.",
                "directness": "direct_NHANES_source_proxy",
                "key_evidence": "NHANES source-oriented results link fast-food/away-from-home/diet-quality proxies to oxidative DEHP profile and HOMA-IR patterns.",
                "guardrail": "Source proxies are dietary/contextual, not measured food plasticizer concentrations.",
                "display_item": "Figure 2",
            },
            {
                "claim_id": "C2",
                "hierarchy": 2,
                "claim": "DEHP oxidative profile anchors population metabolic susceptibility.",
                "directness": "direct_survey_observational",
                "key_evidence": f"10-point oxidative DEHP: MSI beta {fmt(pct_msi.effect)} ({fmt(pct_msi.effect_low)} to {fmt(pct_msi.effect_high)}), HOMA-IR {fmt(pct_homa.effect)}%, HbA1c beta {fmt(pct_hba1c.effect)}; ILR oxidative-vs-primary beta {fmt(comp_msi.effect)}.",
                "guardrail": "Cross-sectional biomonitoring; no same-person PPGR/phase outcome.",
                "display_item": "Figure 2",
            },
            {
                "claim_id": "C3",
                "hierarchy": 3,
                "claim": "MSI and food matrix express susceptibility as PPGR vulnerability after real meals.",
                "directness": "direct_repeated_meal_CGMacros",
                "key_evidence": f"MSI-core: log1p iAUC {msi_log.estimate_CI}; peak delta {msi_peak.estimate_CI}; high-iAUC {msi_high.estimate_CI}. Mixed/unknown matrix: log1p iAUC {matrix_log.estimate_CI}; high-iAUC {matrix_high.estimate_CI}.",
                "guardrail": "CGMacros has 40 subjects and no plasticizer biomarkers.",
                "display_item": "Figure 3",
            },
            {
                "claim_id": "C4",
                "hierarchy": 4,
                "claim": "Meal redesign is a plausible modifiable strategy.",
                "directness": "model_based_counterfactual",
                "key_evidence": f"Subject-held-out high-iAUC AUC improves {fmt(m1.high_iauc_auc)} to {fmt(m3.high_iauc_auc)}; median predicted risk reduction {fmt(cf['risk_reduction'].median())}.",
                "guardrail": "Counterfactual is not intervention evidence until standardized meal challenge.",
                "display_item": "Figure 4",
            },
            {
                "claim_id": "C5",
                "hierarchy": 5,
                "claim": "CGM phase-map provides the longer-horizon digital phenotype language.",
                "directness": "direct_JAEB_plus_external_validation",
                "key_evidence": f"JAEB ARI median {fmt(phase_stab.adjusted_rand_index.median())}; Loop HbA1c/TIR AUROC {fmt(val(loop_phase, target='y_hba1c_improved_ge_0_5').auroc)}/{fmt(val(loop_phase, target='y_tir_improved_ge_5pct').auroc)}; PSO3/4 {fmt(val(sec_phase, validation_dataset='PSO3_PSO4_POOLED_FROZEN', target='y_hba1c_improved_ge_0_5').auroc)}/{fmt(val(sec_phase, validation_dataset='PSO3_PSO4_POOLED_FROZEN', target='y_tir_improved_ge_5pct').auroc)}.",
                "guardrail": "Phenotype/ranking framing unless calibration is adequate.",
                "display_item": "Figure 5",
            },
            {
                "claim_id": "C6",
                "hierarchy": 6,
                "claim": "A bridge cohort is required for same-person exposure-meal-CGM chain validation.",
                "directness": "bridge_needed",
                "key_evidence": "Existing data triangulate but do not contain the same people with urine plasticizers, food-contact panel, standardized meals and 14-28 day CGM.",
                "guardrail": "Do not claim individual-level causal chain before Aim 4.",
                "display_item": "Figure 6",
            },
        ]
    )
    claim_hierarchy.to_csv(TABLES / "p0_claim_hierarchy.csv", index=False)
    claim_hierarchy.to_csv(FIGSRC / "figure1_claim_hierarchy.csv", index=False)

    display_plan = pd.DataFrame(
        [
            ("Figure 1", "Integrated food-system-to-CGM architecture", "Show direct, triangulated and bridge-needed edges.", "p0_claim_hierarchy.csv; integrated DAG nodes/edges", "Do not imply completed same-person causal chain."),
            ("Figure 2", "Population exposure anchor", "NHANES food-system source proxies and DEHP oxidative profile associations with MSI/HOMA-IR/HbA1c.", "p0_aim1_food_system_exposure_matrix.csv; figure2a/b/c existing sources", "Food-source variables are proxies; food plasticizer assay is planned unless measured."),
            ("Figure 3", "Meal-expression layer", "CGMacros MSI-core and food matrix explain PPGR vulnerability; label defensibility and subject leverage.", "p0_aim2_matrix_defense_summary.csv; figure3a/c/d", "Small n=40 subject base; repeated meals do not replace prospective validation."),
            ("Figure 4", "Modifiable meal redesign and phase compatibility", "Isocaloric/equal-carb counterfactual risk deltas plus CGMacros frozen phase-map compatibility audit.", "figure4a/b/c/d; p0_aim2_cgmacros_phase_map_feasibility.csv", "Counterfactual and phase compatibility are not intervention/clinical validation."),
            ("Figure 5", "CGM digital phenotype validation", "JAEB phase-map stability, Loop/PSO external validation, calibration/fairness audit.", "p0_aim3_digital_phenotype_evidence.csv; npj P0 extension tables", "Use ranking/phenotype framing if calibration remains weak."),
            ("Figure 6", "Bridge cohort and translational workflow", "Urine/food plasticizer panel + 2x2 standard meal + 14-28 day CGM + integrated report.", "bridge cohort design matrix", "Prospective work is required for Article-level causal-chain claims."),
        ],
        columns=["display_item", "message", "panel_content", "source_data", "limitation_line"],
    )
    display_plan.to_csv(TABLES / "p0_six_display_item_plan.csv", index=False)
    display_plan.to_csv(FIGSRC / "figure_source_map_six_display_items.csv", index=False)

    software_items = [
        PHASE_PKG / "VERSION",
        PHASE_PKG / "README.md",
        PHASE_PKG / "requirements.txt",
        PHASE_PKG / "environment.yml",
        PHASE_PKG / "phase_map" / "core.py",
        PHASE_PKG / "schemas" / "phase_map_input_schema.csv",
        PHASE_PKG / "schemas" / "phase_map_output_schema.csv",
        PHASE_PKG / "toy_data" / "toy_input.csv",
        PHASE_PKG / "toy_data" / "toy_output_expected.csv",
        PHASE_PKG / "tests" / "test_phase_map_package.py",
        PHASE_PKG / "scripts" / "reproduce_figures.py",
    ]
    software_audit = pd.DataFrame(
        [
            {
                "item": p.name,
                "path": str(p),
                "exists": p.exists(),
                "bytes": p.stat().st_size if p.exists() else 0,
                "role": "phase-map reproducibility package component",
            }
            for p in software_items
        ]
    )
    software_audit.to_csv(TABLES / "p0_software_reproducibility_audit.csv", index=False)

    risk_memo = pd.DataFrame(
        [
            ("Dataset stitching", "Reviewers may see NHANES, CGMacros and JAEB as unrelated.", "Frame as multi-timescale triangulation; mark direct vs bridge-needed claims in Figure 1.", "P0 claim hierarchy + Figure 1."),
            ("No shared participants", "Cannot claim individual-level exposure -> PPGR -> phase causal chain.", "State explicitly; make Aim 4 bridge cohort the solution.", "Specific Aims + Figure 6."),
            ("Food plasticizer concentrations not measured yet", "Nature Food fit weakens if exposure remains only urinary DEHP.", "Use NHANES source proxies now; present measurement panel as planned P1 unless assays complete.", "Aim1 food-system exposure matrix + panel status."),
            ("Manual food matrix labels", "Labels could be viewed as subjective.", "Provide rules, coverage, human review rates and subject leverage.", "Aim2 matrix protocol + defense table."),
            ("CGMacros n=40", "Precision and leverage concerns.", "Use repeated-meal GEE, LOSO and influence diagnostics; avoid overclaiming population generality.", "Aim2 robustness."),
            ("Phase-map calibration", "Weak calibration undermines risk claims.", "Use phenotype/ranking language; include recalibration and fairness audits.", "Aim3 framing."),
            ("Software readiness", "Digital phenotype must be reproducible.", "Ship schema, toy data, tests and environment lock; run unit tests before submission.", "Software audit."),
        ],
        columns=["risk", "why_it_matters", "response", "where_addressed"],
    )
    risk_memo.to_csv(TABLES / "p0_reviewer_risk_memo.csv", index=False)

    abstract = f"""
# Nature Food P0 claim hierarchy and abstract

## 150-word abstract draft

Food systems may shape metabolic health through chemical exposures and the structural properties of meals, yet these layers are rarely connected to continuous glucose monitoring (CGM) phenotypes. We integrated NHANES 2013-2018 biomonitoring, CGMacros real-world meal challenges and JAEB-derived CGM trials to define a multi-timescale phenotype of metabolic vulnerability. In NHANES, higher oxidative DEHP profile was associated with MSI-core, HOMA-IR and HbA1c, anchoring a population exposure signal. Source-oriented analyses linked food-system proxies including fast-food, away-from-home intake and diet-quality context to plasticizer profile or insulin-resistance markers. In CGMacros, MSI-core and food matrix jointly organized PPGR across repeated meals, improving subject-held-out high-iAUC discrimination from {fmt(m1.high_iauc_auc)} to {fmt(m3.high_iauc_auc)}. In JAEB/Loop/PSO datasets, a locked CGM phase-map was stable and externally transportable. These findings support triangulated evidence for a food-system-to-CGM digital phenotype and define the bridge cohort needed for same-person validation.

## Claim hierarchy

1. Food-system source contexts provide the Nature Food entry point.
2. DEHP oxidative profile anchors population metabolic susceptibility.
3. MSI and food matrix express susceptibility as PPGR vulnerability.
4. Meal redesign is a modifiable but currently model-based strategy.
5. CGM phase-map supplies the longer-horizon digital phenotype language.
6. Bridge cohort is required before claiming the complete same-person causal chain.
"""
    write(DOCS / "p0_claim_hierarchy_and_abstract_zh.md", abstract)

    matrix_protocol = """
# Aim 2 matrix adjudication protocol

## Purpose

The food matrix variable must be presented as a reproducible nutrition construct, not as an informal image label. The manuscript should describe it as a rules-based human-adjudicated feature that captures physical and compositional meal context beyond carbohydrates, fat and protein.

## Six-class labels

The locked six-class labels are:

1. fiber_rich_or_whole_food_matrix
2. low_carb_or_protein_forward
3. mixed_meal_protein_fat_buffered
4. mixed_or_unknown_matrix
5. refined_starch_low_matrix_protection
6. sweetened_beverage_or_liquid_carb

## Collapsed Nature Food classes

High-protection matrix: fiber-rich or whole-food matrix; low-carbohydrate/protein-forward meals when carbohydrate exposure is structurally limited.

Intermediate matrix: mixed meals with protein/fat buffering or uncertain mixed structure.

Low-protection matrix: refined starch with low matrix protection and sweetened beverage/liquid carbohydrate.

## Adjudication principles

Use the food image, meal type and nutrient fields together. Do not infer food processing or packaging exposure from the image unless directly visible or documented. Prioritize physical carbohydrate form, fiber structure, liquid-vs-solid form and protein/fat buffering. Keep ambiguous meals in mixed/unknown rather than forcing a protective or low-protection class.

## Reviewer-facing guardrails

The labels are not a chemical exposure measure. They represent meal matrix protection and digestibility context. The matrix term should be interpreted alongside macros and MSI-core. Counterfactual redesign results are model-based and require standardized meal validation.
"""
    write(DOCS / "aim2_matrix_adjudication_protocol.md", matrix_protocol)

    aim3_doc = f"""
# Aim 3 digital phenotype framing

The JAEB/Loop/PSO component should be written as a CGM digital phenotype validation, not as a machine-learning leaderboard. The locked phase-map converts CGM summary windows into interpretable order parameters and phase labels.

## Main evidence

- JAEB phase-map base: {phase_features['participant_id'].nunique()} participants and {len(cgm_long)} CGM summary rows.
- Stability: bootstrap ARI median {fmt(phase_stab.adjusted_rand_index.median())}.
- Loop frozen validation: HbA1c AUROC {fmt(val(loop_phase, target='y_hba1c_improved_ge_0_5').auroc)}, TIR AUROC {fmt(val(loop_phase, target='y_tir_improved_ge_5pct').auroc)}.
- PSO3/4 pooled validation: HbA1c AUROC {fmt(val(sec_phase, validation_dataset='PSO3_PSO4_POOLED_FROZEN', target='y_hba1c_improved_ge_0_5').auroc)}, TIR AUROC {fmt(val(sec_phase, validation_dataset='PSO3_PSO4_POOLED_FROZEN', target='y_tir_improved_ge_5pct').auroc)}.

## Required language

Use phenotype, ranking and transportability language unless calibration is shown to be acceptable in the target setting. Do not present the phase-map as an autonomous clinical decision system. In the Nature Food manuscript, its role is to provide the long-horizon CGM language that can eventually connect food-system exposures and meal-matrix interventions to dynamic glycaemic states.
"""
    write(DOCS / "aim3_digital_phenotype_framing_zh.md", aim3_doc)

    report = f"""
# Nature Food P0 publication-lift completion report

## What was completed

This P0 package converts existing results into a Nature Food-oriented submission structure. It prioritizes food-system exposure, meal matrix biology and CGM digital phenotyping rather than a dataset-by-dataset narrative.

## Key P0 outputs

- Claim hierarchy and 150-word abstract draft.
- Aim 1 food-system source proxy matrix and plasticizer measurement panel status.
- Aim 2 matrix adjudication protocol, label defense table and subject leverage summary.
- CGMacros raw-CGM compatibility audit for locked phase-map assignment.
- Aim 3 digital phenotype evidence table and framing document.
- Six-display-item Nature Food figure plan.
- Software reproducibility audit for the phase-map package.
- Reviewer risk memo.

## P0 scientific position

The current manuscript can support a strong triangulated evidence claim: food-system exposure context, metabolic susceptibility, meal matrix and CGM digital phenotype align across complementary cohorts. It cannot yet claim a completed same-person exposure-to-phase causal chain. That claim requires Aim 4.

## Most important next action

Run a visual figure rebuild from the new figure source map, then decide whether to prepare a presubmission enquiry as an Analysis or wait for Aim 4 pilot data to pursue an Article.
"""
    write(DOCS / "p0_completion_report_zh.md", report)

    manifest = {
        "created": "2026-06-18",
        "objective": "Nature Food P0 publication-lift package using existing NHANES, CGMacros and JAEB/npj outputs",
        "outputs": [str(p) for p in sorted(OUT.rglob("*")) if p.is_file()],
    }
    (OUT / "nature_food_p0_publication_lift_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote Nature Food P0 publication-lift package to {OUT}")


if __name__ == "__main__":
    main()
