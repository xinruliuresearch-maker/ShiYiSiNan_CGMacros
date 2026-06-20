# Project Organization Map

Generated: 2026-06-20 19:02:25

This folder is organized around a reproducible dry-lab research project linking
CGMacros meal-level glycemic responses, NHANES/exposome evidence, external CGM
validation, mechanism evidence, and journal-ready reporting.

## Start Here

1. `README.md` - human-facing overview and main entry point.
2. `00_PROJECT_ORGANIZATION/01_KEY_OUTPUTS_INDEX.md` - curated list of the most important current outputs.
3. `00_PROJECT_ORGANIZATION/02_RUNBOOK_BY_PHASE.md` - script order and workflow map.
4. `outputs/integrated_mainline/` - current integrated research line and high-impact publication materials.
5. `outputs/reproducibility_package/` - packaged reproducibility bundle.

## Top-Level Folder Roles

| Folder | Role |
| --- | --- |
| `scripts/` | Numbered executable workflow scripts. Later scripts extend the study from baseline CGMacros modeling to integrated NHANES, evidence-chain, and high-tier journal packages. |
| `data/raw/` | Local project/raw source data used by early CGMacros processing. |
| `data/external/` | Public external datasets, FDC assets, NHANES-related assets, CGM validation data, and download manifests. |
| `outputs/` | Generated reports, models, tables, figures, manuscripts, validation outputs, and reproducibility packages. |
| `00_PROJECT_ORGANIZATION/` | Navigation layer generated for fast review without changing existing analysis paths. |

## Scale Snapshot

- Files indexed: 5,466
- Indexed size excluding `.git`: 2.15 GB
- Largest-file register: `00_PROJECT_ORGANIZATION/05_LARGE_FILE_REGISTER.csv`
- Full manifest: `00_PROJECT_ORGANIZATION/04_FILE_MANIFEST.csv`

## Organization Principle

Existing analysis paths are preserved to protect reproducibility. This
organization layer makes the project easier to inspect, review, and hand off
without breaking scripts that refer to current data and output locations.
