# ShiYiSiNan CGMacros Integrated Research Project

This repository contains a reproducible dry-lab research project linking
CGMacros meal-level glycemic response modeling, NHANES/exposome evidence,
metabolic susceptibility indexing, external CGM validation, mechanism evidence,
and journal-ready manuscript materials.

## Start Here

Use the generated organization layer as the main navigation entry:

- `00_PROJECT_ORGANIZATION/00_README_PROJECT_MAP.md` - folder map and project scale snapshot.
- `00_PROJECT_ORGANIZATION/01_KEY_OUTPUTS_INDEX.md` - curated list of the most important current reports and manuscript assets.
- `00_PROJECT_ORGANIZATION/02_RUNBOOK_BY_PHASE.md` - script inventory and phase-based workflow map.
- `00_PROJECT_ORGANIZATION/03_DIRECTORY_SIZE_SUMMARY.csv` - directory-level file count and size summary.
- `00_PROJECT_ORGANIZATION/04_FILE_MANIFEST.csv` - full file manifest excluding `.git` and cache directories.
- `00_PROJECT_ORGANIZATION/05_LARGE_FILE_REGISTER.csv` - files larger than 50 MB.
- `00_PROJECT_ORGANIZATION/06_ORGANIZATION_LOG.md` - record of the current organization pass.

Regenerate the organization layer with:

```powershell
python scripts/39_organize_project_folder.py
```

## Folder Map

| Folder | Role |
| --- | --- |
| `scripts/` | Numbered executable workflow scripts from baseline CGMacros modeling through high-tier evidence-chain upgrades. |
| `data/raw/` | Local raw/input data used by early CGMacros processing. |
| `data/external/` | External public datasets, FoodData Central assets, CGM validation data, NHANES-related assets, and dataset manifests. |
| `outputs/` | Generated reports, figures, tables, manuscript packages, external validation results, and reproducibility bundles. |
| `00_PROJECT_ORGANIZATION/` | Human-facing navigation and inventory layer; existing analysis paths are preserved for reproducibility. |

## Current Research Spine

The current integrated research story is:

1. Build CGMacros meal-level glycemic phenotypes and prediction baselines.
2. Construct metabolic susceptibility and response-vulnerability indices.
3. Link NHANES/exposome evidence with CGMacros postprandial glycemic response patterns.
4. Strengthen inference using survey-weighted models, mixture models, sensitivity checks, negative controls, and bias analysis.
5. Validate transportability with external CGM datasets where possible.
6. Upgrade mechanism evidence using reproducible database and transcriptomic evidence layers.
7. Package the result into manuscript, figures, tables, checklists, and reproducibility materials.

## Key Current Outputs

| Purpose | Primary path |
| --- | --- |
| Nature Food / CGM digital phenotype package | `outputs/integrated_mainline/nature_food_cgm_digital_phenotype_2026-06-20/README.md` |
| Latest high-tier journal strategy | `outputs/integrated_mainline/next_stage_high_tier_optimization_2026-06-11/00_next_stage_high_tier_optimization_report.md` |
| Evidence-chain hardening report | `outputs/integrated_mainline/evidence_chain_hardening_2026-06-11/00_evidence_chain_hardening_execution_report.md` |
| Formal dry-lab strengthening report | `outputs/integrated_mainline/formal_drylab_strengthening_2026-06-11/00_formal_drylab_strengthening_report.md` |
| Publication display package | `outputs/integrated_mainline/high_impact_publication_figures_tables_2026-06-11/README_high_impact_publication_figures_tables.md` |
| AJCN-style manuscript package | `outputs/integrated_mainline/ajcn_no_wetlab_manuscript_package_2026-06-10/README_AJCN_package.md` |
| Main manuscript DOCX | `outputs/integrated_mainline/ajcn_no_wetlab_manuscript_package_2026-06-10/manuscript/AJCN_main_manuscript_no_wetlab_2026-06-10.docx` |
| Reproducibility package | `outputs/reproducibility_package/ShiYiSiNan_reproducibility_package/README_REPRODUCIBILITY.md` |
| External dataset manifest | `data/external/DATASET_MANIFEST.md` |

## Script Blocks

| Block | Scripts | Purpose |
| --- | --- | --- |
| Baseline CGMacros modeling | `01-14` | Inspect data, build meal-level dataset, train models, create tables/figures, run robustness checks, calibration, counterfactuals, external Ohio validation, and reproducibility packaging. |
| Integrated Stage 1-5 | `15-20` | Build MSI core, NHANES DEHP/MSI layer, CGMacros PPGR link, personalization, external validation, and bionic digestion design. |
| Dry-lab booster and no-wet-lab package | `21-27` | Literature/evidence modules, no-digestion Phase 0-4 package, AJCN package, publication figures/tables, and competition-format report. |
| High-tier evidence upgrades | `28-38` | Research strategy upgrades, formal NHANES mixture reruns, dry-lab strengthening, raw monomer mixture, evidence-chain hardening, GEO mechanism layer, and next-stage optimization. |
| Project organization | `39` | Regenerate the navigation layer and file inventories. |

See `00_PROJECT_ORGANIZATION/02_RUNBOOK_BY_PHASE.md` for the full script inventory.

## Data And Large Files

Large data, images, zip archives, and generated artifacts are tracked with Git
LFS through `.gitattributes`. The current large-file register is:

```text
00_PROJECT_ORGANIZATION/05_LARGE_FILE_REGISTER.csv
```

The largest generated and external data files should be reviewed before any
public release, journal submission, or repository migration.

## Reproducibility Notes

- Preserve current `scripts/`, `data/`, and `outputs/` paths unless a script-level path migration is performed.
- Treat `outputs/integrated_mainline/` as the current main research line.
- Treat `outputs/reproducibility_package/` as the packaged reproducibility snapshot.
- Re-run `scripts/39_organize_project_folder.py` after major new analyses so the manifest and key-output map stay current.
