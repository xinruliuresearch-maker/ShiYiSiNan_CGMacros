# Runbook By Phase

The scripts are intentionally kept in numeric order. Run only the modules needed for the current analysis, because later scripts may generate large tables, figures, and manuscript artifacts.

## Script Inventory

| Order | Script | Language | Size | Role |
| --- | --- | --- | --- | --- |
| 01 | `scripts/1_inspect_dataset.py` | py | 1.21 KB | data inspection |
| 02 | `scripts/02_build_meal_level_dataset.py` | py | 19.35 KB | meal-level dataset construction |
| 03 | `scripts/03_train_baseline_models.py` | py | 20.21 KB | model training |
| 03 | `scripts/03_train_clean_models.py` | py | 27.77 KB | model training |
| 04 | `scripts/04_make_figures.py` | py | 5.03 KB | paper displays |
| 05 | `scripts/05_ablation_study.py` | py | 26.97 KB | model robustness |
| 06 | `scripts/06_bootstrap_ci.py` | py | 29.44 KB | statistical robustness |
| 07 | `scripts/07_make_paper_tables_figures.py` | py | 24.38 KB | paper displays |
| 08 | `scripts/08_paired_delta_bootstrap.py` | py | 26.03 KB | statistical robustness |
| 09 | `scripts/09_subgroup_analysis.py` | py | 35.23 KB | statistical robustness |
| 10 | `scripts/10_error_analysis.py` | py | 43.31 KB | statistical robustness |
| 11 | `scripts/11_calibration_analysis.py` | py | 41.83 KB | statistical robustness |
| 12 | `scripts/12_counterfactual_meal_substitution.py` | py | 42.51 KB | counterfactual meal redesign |
| 13 | `scripts/13_lightweight_external_validation_ohio.py` | py | 36.66 KB | external validation |
| 14 | `scripts/14_build_reproducibility_package.py` | py | 32.97 KB | reproducibility package |
| 15 | `scripts/15_integrated_stage1_build_msi_core.py` | py | 16.77 KB | integrated Stage 1-5 workflow |
| 16 | `scripts/16_integrated_stage2_nhanes_dehp_msi.py` | py | 13.87 KB | integrated Stage 1-5 workflow |
| 17 | `scripts/17_integrated_stage3_cgmacros_msi_ppgr.py` | py | 12.31 KB | integrated Stage 1-5 workflow |
| 18 | `scripts/18_integrated_stage4_prediction_personalization.py` | py | 13.70 KB | integrated Stage 1-5 workflow |
| 19 | `scripts/19_integrated_stage5_bionic_digestion_design.py` | py | 10.98 KB | integrated Stage 1-5 workflow |
| 20 | `scripts/20_integrated_phase0_to_phase5_computational_workflow.py` | py | 80.13 KB | Phase workflow |
| 21 | `scripts/21_run_dry_lab_booster_modules_A_to_I.py` | py | 91.87 KB | dry-lab strengthening |
| 22 | `scripts/22_no_digestion_phase0_to_phase4_package.py` | py | 41.95 KB | Phase workflow |
| 23 | `scripts/23_build_ajcn_no_wetlab_manuscript_package.py` | py | 74.29 KB | manuscript package |
| 24 | `scripts/24_build_publication_quality_ajcn_figures_v2.py` | py | 39.56 KB | paper displays |
| 25 | `scripts/25_design_high_impact_figures_tables.py` | py | 47.18 KB | paper displays |
| 26 | `scripts/26_build_high_impact_publication_figures_tables.py` | py | 94.17 KB | paper displays |
| 27 | `scripts/27_build_competition_template_report.py` | py | 29.51 KB | competition-format report |
| 28 | `scripts/28_build_research_upgrade_strategy.py` | py | 41.94 KB | high-tier strategy |
| 29 | `scripts/29_run_high_impact_computational_upgrade.py` | py | 75.95 KB | analysis utility |
| 30 | `scripts/30_build_current_results_interpretation.py` | py | 26.28 KB | result interpretation |
| 31 | `scripts/31_build_evidence_chain_optimization_plan.py` | py | 54.25 KB | evidence-chain and mechanism |
| 32 | `scripts/32_run_formal_nhanes_mixture_rerun.R` | R | 14.44 KB | NHANES mixture modeling |
| 33 | `scripts/33_run_drylab_strengthening_modules.py` | py | 47.43 KB | dry-lab strengthening |
| 34 | `scripts/34_build_next_level_evidence_strategy.py` | py | 35.67 KB | evidence-chain and mechanism |
| 35 | `scripts/35_run_raw_nhanes_monomer_mixture.R` | R | 23.08 KB | NHANES mixture modeling |
| 36 | `scripts/36_run_evidence_chain_hardening_modules.py` | py | 39.76 KB | evidence-chain and mechanism |
| 37 | `scripts/37_run_geo_directional_mechanism.R` | R | 8.37 KB | evidence-chain and mechanism |
| 38 | `scripts/38_build_next_stage_high_tier_optimization.py` | py | 24.97 KB | high-tier strategy |
| 39 | `scripts/39_organize_project_folder.py` | py | 16.69 KB | analysis utility |

## Practical Workflow Blocks

| Block | Scripts | Purpose |
| --- | --- | --- |
| Baseline CGMacros modeling | `01-14` | Inspect data, build meal-level dataset, train baseline/clean models, generate paper tables, robustness checks, calibration, counterfactuals, external Ohio validation, reproducibility package. |
| Integrated Stage 1-5 | `15-20` | Build MSI core, NHANES DEHP/MSI layer, CGMacros PPGR link, personalization, external validation, and bionic digestion design. |
| Dry-lab booster and no-wet-lab package | `21-27` | Literature/evidence modules, no-digestion Phase 0-4 package, AJCN package, publication figures/tables, competition-format report. |
| High-tier evidence upgrades | `28-38` | Research strategy upgrades, formal NHANES mixture reruns, non-glycemic/evidence hardening, GEO/CompTox mechanism layer, and next-stage high-tier optimization. |
| Folder organization | `39` | Regenerate this navigation layer and file inventory. |
