from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORG_DIR = ROOT / "00_PROJECT_ORGANIZATION"

EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv"}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def human_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TB"


def iter_project_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if any(part in EXCLUDE_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.is_file():
            files.append(path)
    return sorted(files, key=lambda p: rel(p).lower())


def classify_path(path: Path) -> str:
    parts = path.relative_to(ROOT).parts
    if not parts:
        return "root"
    top = parts[0]
    if top == "scripts":
        return "analysis_code"
    if top == "data":
        if len(parts) > 1 and parts[1] == "raw":
            return "raw_data"
        if len(parts) > 1 and parts[1] == "external":
            return "external_data"
        return "data"
    if top == "outputs":
        if "manuscript" in parts:
            return "manuscript"
        if "figures" in parts or "main_figures" in parts or "extended_figures" in parts:
            return "figures"
        if "tables" in parts or "paper_tables" in parts:
            return "tables"
        if "reproducibility_package" in parts:
            return "reproducibility"
        return "analysis_output"
    if top == "00_PROJECT_ORGANIZATION":
        return "project_index"
    return "project_file"


def directory_summary(files: list[Path]) -> list[dict[str, str]]:
    totals: dict[str, dict[str, int]] = {}
    for file_path in files:
        rel_parts = file_path.relative_to(ROOT).parts
        if len(rel_parts) == 1:
            keys = ["."]
        else:
            keys = [rel_parts[0]]
            if len(rel_parts) >= 3:
                keys.append("/".join(rel_parts[:2]))
        for key in keys:
            bucket = totals.setdefault(key, {"files": 0, "bytes": 0})
            bucket["files"] += 1
            bucket["bytes"] += file_path.stat().st_size
    rows = []
    for key, item in sorted(totals.items(), key=lambda kv: kv[0].lower()):
        rows.append(
            {
                "directory": key,
                "files": str(item["files"]),
                "bytes": str(item["bytes"]),
                "size": human_size(item["bytes"]),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def key_output_rows() -> list[dict[str, str]]:
    candidates = [
        (
            "Start here",
            "Root project README",
            "README.md",
            "Top-level project purpose, folder map, and execution entry points.",
        ),
        (
            "Current integrated manuscript package",
            "AJCN manuscript package README",
            "outputs/integrated_mainline/ajcn_no_wetlab_manuscript_package_2026-06-10/README_AJCN_package.md",
            "Main manuscript, figures, tables, supplement, cover letter, and reporting checklists.",
        ),
        (
            "Current manuscript",
            "AJCN main manuscript DOCX",
            "outputs/integrated_mainline/ajcn_no_wetlab_manuscript_package_2026-06-10/manuscript/AJCN_main_manuscript_no_wetlab_2026-06-10.docx",
            "Word-format draft for journal-style manuscript review.",
        ),
        (
            "Publication displays",
            "High-impact display index",
            "outputs/integrated_mainline/high_impact_publication_figures_tables_2026-06-11/README_high_impact_publication_figures_tables.md",
            "Main and supplementary tables, figure legends, and source-data map.",
        ),
        (
            "Latest high-tier strategy",
            "Next-stage optimization report",
            "outputs/integrated_mainline/next_stage_high_tier_optimization_2026-06-11/00_next_stage_high_tier_optimization_report.md",
            "Most recent high-tier journal path and evidence-chain upgrade plan.",
        ),
        (
            "Evidence hardening",
            "Evidence-chain hardening execution report",
            "outputs/integrated_mainline/evidence_chain_hardening_2026-06-11/00_evidence_chain_hardening_execution_report.md",
            "Raw NHANES monomer mixture, directional mechanisms, and external validation upgrades.",
        ),
        (
            "Formal dry-lab strengthening",
            "Formal dry-lab strengthening report",
            "outputs/integrated_mainline/formal_drylab_strengthening_2026-06-11/00_formal_drylab_strengthening_report.md",
            "Formal NHANES re-runs, negative controls, bias analysis, and additional computational modules.",
        ),
        (
            "Phase 0-5 summary",
            "Master summary",
            "outputs/integrated_mainline/phase0_to_phase5_master_summary_2026-06-10.md",
            "Earlier integrated stage summary linking protocol, NHANES, CGMacros, external validation, and wet-lab design.",
        ),
        (
            "Reproducibility",
            "Packaged reproducibility README",
            "outputs/reproducibility_package/ShiYiSiNan_reproducibility_package/README_REPRODUCIBILITY.md",
            "Run order, data availability, scripts, and reproducibility notes.",
        ),
        (
            "External data",
            "External dataset manifest",
            "data/external/DATASET_MANIFEST.md",
            "Downloaded and integrated public datasets.",
        ),
    ]
    rows = []
    for role, title, path_text, note in candidates:
        path = ROOT / path_text
        rows.append(
            {
                "role": role,
                "title": title,
                "path": path_text,
                "exists": "yes" if path.exists() else "no",
                "note": note,
            }
        )
    return rows


def script_rows() -> list[dict[str, str]]:
    rows = []
    for script in sorted((ROOT / "scripts").glob("*"), key=lambda p: p.name.lower()):
        if not script.is_file():
            continue
        name = script.name
        stem = script.stem
        prefix = stem.split("_", 1)[0]
        if prefix.isdigit():
            order_number = int(prefix)
            order = prefix.zfill(2)
        else:
            order_number = 9999
            order = ""
        rows.append(
            {
                "_order_number": order_number,
                "order": order,
                "script": rel(script),
                "language": script.suffix.lstrip("."),
                "size": human_size(script.stat().st_size),
                "role": infer_script_role(name),
            }
        )
    rows.sort(key=lambda row: (int(row["_order_number"]), row["script"].lower()))
    for row in rows:
        row.pop("_order_number", None)
    return rows


def infer_script_role(name: str) -> str:
    lower = name.lower()
    if "inspect" in lower:
        return "data inspection"
    if "build_meal" in lower:
        return "meal-level dataset construction"
    if "train" in lower:
        return "model training"
    if "figure" in lower or "tables" in lower:
        return "paper displays"
    if "ablation" in lower:
        return "model robustness"
    if "counterfactual" in lower:
        return "counterfactual meal redesign"
    if "bootstrap" in lower or "subgroup" in lower or "error" in lower or "calibration" in lower:
        return "statistical robustness"
    if "external" in lower:
        return "external validation"
    if "reproducibility" in lower:
        return "reproducibility package"
    if "integrated_stage" in lower:
        return "integrated Stage 1-5 workflow"
    if "phase" in lower:
        return "Phase workflow"
    if "dry" in lower:
        return "dry-lab strengthening"
    if "manuscript" in lower:
        return "manuscript package"
    if "competition" in lower:
        return "competition-format report"
    if "current_results" in lower:
        return "result interpretation"
    if "nhanes" in lower or "mixture" in lower:
        return "NHANES mixture modeling"
    if "evidence" in lower or "mechanism" in lower or "geo" in lower:
        return "evidence-chain and mechanism"
    if "strategy" in lower or "optimization" in lower:
        return "high-tier strategy"
    return "analysis utility"


def write_project_map(files: list[Path], total_bytes: int) -> None:
    text = f"""# Project Organization Map

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

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

- Files indexed: {len(files):,}
- Indexed size excluding `.git`: {human_size(total_bytes)}
- Largest-file register: `00_PROJECT_ORGANIZATION/05_LARGE_FILE_REGISTER.csv`
- Full manifest: `00_PROJECT_ORGANIZATION/04_FILE_MANIFEST.csv`

## Organization Principle

Existing analysis paths are preserved to protect reproducibility. This
organization layer makes the project easier to inspect, review, and hand off
without breaking scripts that refer to current data and output locations.
"""
    (ORG_DIR / "00_README_PROJECT_MAP.md").write_text(text, encoding="utf-8")


def write_key_outputs() -> None:
    rows = key_output_rows()
    lines = [
        "# Key Outputs Index",
        "",
        "Use this file as the fastest route through the current research results.",
        "",
        "| Role | Title | Exists | Path | Note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['role']} | {row['title']} | {row['exists']} | `{row['path']}` | {row['note']} |"
        )
    lines.extend(
        [
            "",
            "## Suggested Review Order",
            "",
            "1. Read the root `README.md` for the folder map.",
            "2. Read `outputs/integrated_mainline/next_stage_high_tier_optimization_2026-06-11/00_next_stage_high_tier_optimization_report.md` for the current high-tier journal strategy.",
            "3. Review `outputs/integrated_mainline/evidence_chain_hardening_2026-06-11/00_evidence_chain_hardening_execution_report.md` for the latest evidence-hardening layer.",
            "4. Review `outputs/integrated_mainline/high_impact_publication_figures_tables_2026-06-11/README_high_impact_publication_figures_tables.md` for paper displays.",
            "5. Open the AJCN manuscript package under `outputs/integrated_mainline/ajcn_no_wetlab_manuscript_package_2026-06-10/`.",
        ]
    )
    (ORG_DIR / "01_KEY_OUTPUTS_INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_runbook() -> None:
    rows = script_rows()
    lines = [
        "# Runbook By Phase",
        "",
        "The scripts are intentionally kept in numeric order. Run only the modules needed for the current analysis, because later scripts may generate large tables, figures, and manuscript artifacts.",
        "",
        "## Script Inventory",
        "",
        "| Order | Script | Language | Size | Role |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['order']} | `{row['script']}` | {row['language']} | {row['size']} | {row['role']} |"
        )
    lines.extend(
        [
            "",
            "## Practical Workflow Blocks",
            "",
            "| Block | Scripts | Purpose |",
            "| --- | --- | --- |",
            "| Baseline CGMacros modeling | `01-14` | Inspect data, build meal-level dataset, train baseline/clean models, generate paper tables, robustness checks, calibration, counterfactuals, external Ohio validation, reproducibility package. |",
            "| Integrated Stage 1-5 | `15-20` | Build MSI core, NHANES DEHP/MSI layer, CGMacros PPGR link, personalization, external validation, and bionic digestion design. |",
            "| Dry-lab booster and no-wet-lab package | `21-27` | Literature/evidence modules, no-digestion Phase 0-4 package, AJCN package, publication figures/tables, competition-format report. |",
            "| High-tier evidence upgrades | `28-38` | Research strategy upgrades, formal NHANES mixture reruns, non-glycemic/evidence hardening, GEO/CompTox mechanism layer, and next-stage high-tier optimization. |",
            "| Folder organization | `39` | Regenerate this navigation layer and file inventory. |",
        ]
    )
    (ORG_DIR / "02_RUNBOOK_BY_PHASE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_log(files: list[Path], total_bytes: int) -> None:
    text = f"""# Organization Log

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Actions Performed

- Created `00_PROJECT_ORGANIZATION/` as a stable navigation layer.
- Generated a curated key-output index.
- Generated a script runbook by phase.
- Generated a directory size summary.
- Generated a full file manifest excluding `.git` and cache directories.
- Generated a large-file register to make LFS/data burden visible.

## Reproducibility Safeguards

- Existing `scripts/`, `data/`, and `outputs/` paths were not moved.
- No raw or external data files were deleted.
- This organization pass is additive and can be regenerated by running:

```powershell
python scripts/39_organize_project_folder.py
```

## Snapshot

- Indexed files: {len(files):,}
- Indexed size: {human_size(total_bytes)}
- Organization folder: `00_PROJECT_ORGANIZATION/`
"""
    (ORG_DIR / "06_ORGANIZATION_LOG.md").write_text(text, encoding="utf-8")


def main() -> None:
    ORG_DIR.mkdir(parents=True, exist_ok=True)
    files = iter_project_files()
    total_bytes = sum(path.stat().st_size for path in files)

    manifest_rows = []
    for path in files:
        stat = path.stat()
        manifest_rows.append(
            {
                "path": rel(path),
                "category": classify_path(path),
                "extension": path.suffix.lower(),
                "bytes": str(stat.st_size),
                "size": human_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    write_csv(
        ORG_DIR / "04_FILE_MANIFEST.csv",
        manifest_rows,
        ["path", "category", "extension", "bytes", "size", "modified"],
    )

    write_csv(
        ORG_DIR / "03_DIRECTORY_SIZE_SUMMARY.csv",
        directory_summary(files),
        ["directory", "files", "bytes", "size"],
    )

    large_rows = [
        row
        for row in manifest_rows
        if int(row["bytes"]) >= 50 * 1024 * 1024
    ]
    large_rows.sort(key=lambda row: int(row["bytes"]), reverse=True)
    write_csv(
        ORG_DIR / "05_LARGE_FILE_REGISTER.csv",
        large_rows,
        ["path", "category", "extension", "bytes", "size", "modified"],
    )

    write_project_map(files, total_bytes)
    write_key_outputs()
    write_runbook()
    write_log(files, total_bytes)

    print(f"Wrote organization layer to {rel(ORG_DIR)}")
    print(f"Indexed {len(files):,} files ({human_size(total_bytes)})")
    print(f"Large files >= 50 MB: {len(large_rows)}")


if __name__ == "__main__":
    main()
