# -*- coding: utf-8 -*-
"""
14_build_reproducibility_package.py

Build a reproducibility package for the ShiYiSiNan diet-to-physiology modeling project.

This script creates a shareable package containing:
- analysis scripts
- aggregate result tables
- figures
- reproducibility documentation
- environment files
- manifests
- SHA256 checksums
- a zip archive

Important:
Public mode excludes raw data, XML files, row-level prediction records,
Kaggle credentials, access tokens, and other sensitive local files.
"""

from pathlib import Path
import argparse
import csv
import datetime as dt
import fnmatch
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import zipfile

try:
    import importlib.metadata as importlib_metadata
except Exception:
    import importlib_metadata


# ============================================================
# 0. Project paths
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

OUTPUT_ROOT = ROOT / "outputs" / "reproducibility_package"
PACKAGE_BASENAME = "ShiYiSiNan_reproducibility_package"

SCRIPTS_DIR = ROOT / "scripts"

MAIN_TABLES_DIR = ROOT / "outputs" / "tables"
MAIN_FIGURES_DIR = ROOT / "outputs" / "figures"

EXTERNAL_TABLES_DIR = ROOT / "outputs" / "external_validation" / "tables"
EXTERNAL_FIGURES_DIR = ROOT / "outputs" / "external_validation" / "figures"


# ============================================================
# 1. Public sharing rules
# ============================================================

AGGREGATE_INCLUDE_PATTERNS = [
    "*summary*.csv",
    "*performance*.csv",
    "*metrics*.csv",
    "*overview*.csv",
    "*bootstrap*.csv",
    "*feature_importance*.csv",
    "*feature_correlations*.csv",
    "*classification*.csv",
    "*decile_table*.csv",
    "*calibration*.csv",
    "*counterfactual_scenario_summary.csv",
    "*counterfactual_bootstrap_summary.csv",
    "*counterfactual_subgroup_summary.csv",
    "*counterfactual_main_summary.csv",
    "*external_ohio_performance_summary.csv",
    "*external_validation_main_summary.csv",
]

PUBLIC_EXCLUDE_PATTERNS = [
    "*meal_level_dataset.csv",
    "*meal_level_predictions.csv",
    "*prediction_records*.csv",
    "*parsed_events*.csv",
    "*all_parsed_events.csv",
    "*_events.csv",
    "*subject_manifest.csv",
    "*subject_summary.csv",
    "*subject_gain.csv",
    "*fewshot_10vs0_records.csv",
    "*error_extreme_meals.csv",
    "*error_high_error_subjects.csv",
    "*error_high_response_underpredicted_meals.csv",
    "*error_low_response_overpredicted_meals.csv",
    "*counterfactual_meal_level_predictions.csv",
    "*counterfactual_top_benefit_meals.csv",
    "*external_ohio_meal_level_dataset.csv",
    "*external_ohio_prediction_records.csv",
    "*.xml",
    "*.zip",
]

SECRET_EXCLUDE_PATTERNS = [
    "kaggle.json",
    "access_token",
    ".env",
    "*.env",
    "*.key",
    "*.pem",
    "*.p12",
    "*token*",
    "*secret*",
    "*credential*",
    "*password*",
]


# ============================================================
# 2. Basic utilities
# ============================================================

def timestamp():
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def write_text(path, text):
    path = Path(path)
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def write_json(path, obj):
    path = Path(path)
    ensure_dir(path.parent)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def sha256_file(path, block_size=1024 * 1024):
    path = Path(path)
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            block = f.read(block_size)
            if not block:
                break
            h.update(block)

    return h.hexdigest()


def safe_rel(path):
    path = Path(path)
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def matches_any(name, patterns):
    name = str(name).lower()
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern.lower()):
            return True
    return False


def is_secret_file(path):
    path = Path(path)
    name = path.name.lower()
    parts = [p.lower() for p in path.parts]

    if ".kaggle" in parts:
        return True

    return matches_any(name, SECRET_EXCLUDE_PATTERNS)


def should_include_public_table(path):
    path = Path(path)
    name = path.name

    if is_secret_file(path):
        return False

    if matches_any(name, PUBLIC_EXCLUDE_PATTERNS):
        return False

    return matches_any(name, AGGREGATE_INCLUDE_PATTERNS)


def copy_file(src, dst):
    src = Path(src)
    dst = Path(dst)
    ensure_dir(dst.parent)
    shutil.copy2(src, dst)


def write_csv(path, rows):
    path = Path(path)
    ensure_dir(path.parent)

    fieldnames = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def numeric_prefix(file_name):
    try:
        return int(str(file_name).split("_", 1)[0])
    except Exception:
        return None


# ============================================================
# 3. Environment capture
# ============================================================

def get_pip_freeze():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    return ""


def get_package_version(package_name):
    try:
        return importlib_metadata.version(package_name)
    except Exception:
        return None


def write_environment_files(package_dir):
    package_dir = Path(package_dir)

    freeze = get_pip_freeze()
    write_text(package_dir / "requirements_freeze.txt", freeze + "\n")

    env_lines = [
        "name: cgmacros_reproducibility",
        "channels:",
        "  - conda-forge",
        "  - defaults",
        "dependencies:",
        f"  - python={sys.version_info.major}.{sys.version_info.minor}",
        "  - pip",
        "  - pip:",
    ]

    for line in freeze.splitlines():
        line = line.strip()
        if line:
            env_lines.append(f"      - {line}")

    write_text(
        package_dir / "environment_reproducibility.yml",
        "\n".join(env_lines) + "\n",
    )

    important_packages = [
        "numpy",
        "pandas",
        "scikit-learn",
        "matplotlib",
        "scipy",
        "tqdm",
        "openpyxl",
        "kaggle",
    ]

    versions = {
        "generated_at": dt.datetime.now().isoformat(),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "package_versions": {
            pkg: get_package_version(pkg)
            for pkg in important_packages
        },
    }

    write_json(package_dir / "software_versions.json", versions)

    return versions


# ============================================================
# 4. Copy scripts, tables, figures
# ============================================================

def create_package_dirs(package_dir):
    subdirs = [
        "scripts",
        "tables/main",
        "tables/external_validation",
        "figures/main",
        "figures/external_validation",
        "docs",
        "manifests",
        "checksums",
        "configs",
    ]

    for sub in subdirs:
        ensure_dir(package_dir / sub)


def copy_scripts(package_dir):
    rows = []

    if not SCRIPTS_DIR.exists():
        return rows

    for src in sorted(SCRIPTS_DIR.glob("*.py")):
        if is_secret_file(src):
            continue

        dst = package_dir / "scripts" / src.name
        copy_file(src, dst)

        rows.append({
            "category": "script",
            "file_name": src.name,
            "source_path": safe_rel(src),
            "package_path": dst.relative_to(package_dir).as_posix(),
            "size_bytes": src.stat().st_size,
            "sha256": sha256_file(src),
        })

    return rows


def copy_tables_from_dir(src_dir, dst_dir, mode, category_label):
    rows = []
    src_dir = Path(src_dir)
    dst_dir = Path(dst_dir)

    if not src_dir.exists():
        return rows

    for src in sorted(src_dir.glob("*")):
        if not src.is_file():
            continue

        if is_secret_file(src):
            continue

        if src.suffix.lower() not in [".csv", ".xlsx", ".json", ".txt"]:
            continue

        if mode == "public":
            if not should_include_public_table(src):
                continue

        dst = dst_dir / src.name
        copy_file(src, dst)

        rows.append({
            "category": category_label,
            "mode": mode,
            "file_name": src.name,
            "source_path": safe_rel(src),
            "package_path": dst.relative_to(dst_dir.parents[1]).as_posix()
            if len(dst_dir.parents) > 1 else dst.name,
            "size_bytes": src.stat().st_size,
            "sha256": sha256_file(src),
        })

    return rows


def copy_tables(package_dir, mode):
    rows = []

    rows.extend(
        copy_tables_from_dir(
            MAIN_TABLES_DIR,
            package_dir / "tables" / "main",
            mode,
            "main_table",
        )
    )

    rows.extend(
        copy_tables_from_dir(
            EXTERNAL_TABLES_DIR,
            package_dir / "tables" / "external_validation",
            mode,
            "external_validation_table",
        )
    )

    return rows


def copy_figures_from_dir(src_dir, dst_dir, category_label):
    rows = []
    src_dir = Path(src_dir)
    dst_dir = Path(dst_dir)

    if not src_dir.exists():
        return rows

    for src in sorted(src_dir.glob("*")):
        if not src.is_file():
            continue

        if is_secret_file(src):
            continue

        if src.suffix.lower() not in [".png", ".jpg", ".jpeg", ".svg", ".pdf"]:
            continue

        dst = dst_dir / src.name
        copy_file(src, dst)

        rows.append({
            "category": category_label,
            "file_name": src.name,
            "source_path": safe_rel(src),
            "package_path": dst.relative_to(dst_dir.parents[1]).as_posix()
            if len(dst_dir.parents) > 1 else dst.name,
            "size_bytes": src.stat().st_size,
            "sha256": sha256_file(src),
        })

    return rows


def copy_figures(package_dir):
    rows = []

    rows.extend(
        copy_figures_from_dir(
            MAIN_FIGURES_DIR,
            package_dir / "figures" / "main",
            "main_figure",
        )
    )

    rows.extend(
        copy_figures_from_dir(
            EXTERNAL_FIGURES_DIR,
            package_dir / "figures" / "external_validation",
            "external_validation_figure",
        )
    )

    return rows


# ============================================================
# 5. Documentation
# ============================================================

def get_ordered_scripts():
    if not SCRIPTS_DIR.exists():
        return []

    out = []

    for p in sorted(SCRIPTS_DIR.glob("*.py")):
        n = numeric_prefix(p.name)
        if n is None:
            continue
        if n == 14:
            continue
        out.append((n, p.name))

    out.sort(key=lambda x: x[0])
    return out


def write_readme(package_dir, mode):
    lines = [
        "# ShiYiSiNan Reproducibility Package",
        "",
        "This package supports reproducibility of the diet-to-physiology modeling analysis.",
        "",
        "## Contents",
        "",
        "- Analysis scripts",
        "- Aggregate result tables",
        "- Figures",
        "- Software environment files",
        "- Run-order documentation",
        "- Data availability notes",
        "- SHA256 checksums and file manifests",
        "",
        "## Package mode",
        "",
        f"This package was generated in mode: {mode}",
        "",
        "Public mode excludes raw datasets, XML files, row-level prediction records, tokens, and local credentials.",
        "",
        "## Not included",
        "",
        "The following files are intentionally not included:",
        "",
        "- Raw CGMacros files",
        "- Raw OhioT1DM XML files",
        "- Kaggle credentials",
        "- API tokens",
        "- Local .env files",
        "- Row-level prediction records in public mode",
        "",
        "## Minimal workflow",
        "",
        "1. Create or activate the Python environment.",
        "2. Obtain CGMacros and OhioT1DM from their original sources.",
        "3. Place raw data according to DATA_AVAILABILITY.md.",
        "4. Run scripts in the order described in RUN_ORDER.md.",
        "5. Compare regenerated aggregate outputs with the included tables and manifests.",
        "",
        "## Windows command",
        "",
        "Run from the project root:",
        "",
        "powershell -ExecutionPolicy Bypass -File .\\run_all_windows.ps1",
        "",
        "## Python command",
        "",
        "Run from the project root:",
        "",
        "python run_all.py",
        "",
        "## Integrity check",
        "",
        "Run from the package directory:",
        "",
        "python verify_package_integrity.py",
        "",
        f"Generated at: {dt.datetime.now().isoformat()}",
        "",
    ]

    write_text(package_dir / "README_REPRODUCIBILITY.md", "\n".join(lines))


def write_run_order(package_dir, ordered_scripts):
    purpose_map = {
        1: "Initial data inspection or setup, if present",
        2: "Build meal-level CGMacros dataset",
        3: "Baseline model training and evaluation, if present",
        4: "Feature-set ablation or core model evaluation, if present",
        5: "Cleaned-feature analysis or model comparison, if present",
        6: "Subject-level bootstrap confidence intervals",
        7: "Clean paper tables and main figures, if present",
        8: "Paired subject-level delta bootstrap",
        9: "Exploratory subgroup analysis",
        10: "Error analysis",
        11: "Calibration analysis",
        12: "Model-based counterfactual meal-substitution simulation",
        13: "Lightweight external framework validation using OhioT1DM",
    }

    lines = [
        "# Run Order",
        "",
        "Run scripts from the project root in numeric order.",
        "",
        "| Order | Script | Purpose |",
        "|---:|---|---|",
    ]

    for n, script_name in ordered_scripts:
        purpose = purpose_map.get(n, "Analysis step")
        lines.append(f"| {n} | `{script_name}` | {purpose} |")

    lines.append("")

    write_text(package_dir / "RUN_ORDER.md", "\n".join(lines))


def write_data_availability(package_dir):
    lines = [
        "# Data Availability",
        "",
        "## Primary dataset: CGMacros",
        "",
        "CGMacros is used as the primary public dataset for diet-to-postprandial-glucose modeling.",
        "Raw CGMacros files are not redistributed in this reproducibility package.",
        "Researchers should obtain the dataset from its original public source and place it under the local data directory expected by the preprocessing scripts.",
        "",
        "## External validation dataset: OhioT1DM",
        "",
        "OhioT1DM is used for lightweight external framework validation.",
        "Raw OhioT1DM XML files are not redistributed in this package.",
        "",
        "Expected local placement:",
        "",
        "data/external/OhioT1DM/",
        "",
        "The external validation script searches recursively for XML files under that folder.",
        "",
        "## Credentials",
        "",
        "Do not share or commit the following files:",
        "",
        "- kaggle.json",
        "- access_token",
        "- .env",
        "- API keys",
        "- passwords",
        "- private credentials",
        "",
        "## Reproducibility principle",
        "",
        "Another researcher with authorized access to the same public datasets should be able to regenerate meal-level datasets, prediction records, aggregate tables, and figures by following RUN_ORDER.md.",
        "",
    ]

    write_text(package_dir / "DATA_AVAILABILITY.md", "\n".join(lines))


def write_paper_statement(package_dir):
    lines = [
        "# Paper Reproducibility Statement",
        "",
        "All analyses were implemented in Python and organized as a script-based workflow.",
        "The workflow includes meal-level phenotype construction, leakage-aware feature-set evaluation, subject-level bootstrap confidence intervals, paired subject-level delta bootstrap, exploratory subgroup analysis, error analysis, calibration diagnostics, model-based counterfactual meal-substitution simulation, and lightweight external framework validation.",
        "",
        "Leave-subject-out validation was used to assess new-user generalization.",
        "Within-subject temporal splitting was used to assess future-meal prediction for previously observed individuals.",
        "Few-shot personalization experiments used early subject-specific meals for adaptation and evaluated subsequent meals only.",
        "Confidence intervals were estimated using participant-level resampling to account for repeated meals within individuals.",
        "",
        "The reproducibility package includes analysis scripts, software environment files, aggregate output tables, figures, run-order documentation, and checksums.",
        "Raw datasets are not redistributed and should be obtained from their original sources according to their data-use terms.",
        "",
    ]

    write_text(package_dir / "PAPER_REPRODUCIBILITY_STATEMENT.md", "\n".join(lines))


def write_limitations(package_dir):
    lines = [
        "# Limitations and Audit Notes",
        "",
        "## Dataset scope",
        "",
        "The primary analysis uses CGMacros-derived meal-level data.",
        "The external validation uses OhioT1DM as an independent disease-specific CGM dataset.",
        "These datasets differ in population, disease context, available covariates, nutrition annotation quality, and event structure.",
        "",
        "## External validation",
        "",
        "The OhioT1DM analysis is a lightweight framework validation.",
        "It does not directly validate CGMacros-trained model weights.",
        "",
        "## Counterfactual simulations",
        "",
        "Counterfactual meal-substitution results are model-based simulations.",
        "They should be interpreted as hypothesis-generating rather than causal intervention effects.",
        "",
        "## Calibration",
        "",
        "Calibration analysis indicates prediction-range compression.",
        "Deployment should combine point prediction with calibration monitoring, uncertainty estimation, high-response risk detection, and subject-specific updating.",
        "",
        "## Privacy and sharing",
        "",
        "Public packages should not contain raw data, XML files, token files, or row-level records that could be restricted by source dataset terms.",
        "",
    ]

    write_text(package_dir / "LIMITATIONS_AND_AUDIT.md", "\n".join(lines))


def write_citation(package_dir):
    lines = [
        "cff-version: 1.2.0",
        'message: "If you use this reproducibility package, please cite the associated manuscript and the original public datasets."',
        'title: "ShiYiSiNan Diet-to-Physiology Modeling Reproducibility Package"',
        "authors:",
        "  - family-names: Liu",
        "    given-names: Xinru",
        'version: "0.1.0"',
        'date-released: "2026-06-01"',
        "",
    ]

    write_text(package_dir / "CITATION.cff", "\n".join(lines))


def write_all_docs(package_dir, mode, ordered_scripts):
    write_readme(package_dir, mode)
    write_run_order(package_dir, ordered_scripts)
    write_data_availability(package_dir)
    write_paper_statement(package_dir)
    write_limitations(package_dir)
    write_citation(package_dir)


# ============================================================
# 6. Run scripts
# ============================================================

def write_run_all_scripts(package_dir, ordered_scripts):
    ps_lines = [
        "$ErrorActionPreference = 'Stop'",
        "Write-Host 'Starting ShiYiSiNan reproducibility workflow...'",
        "",
    ]

    for _, script_name in ordered_scripts:
        ps_lines.append(f"Write-Host 'Running {script_name}'")
        ps_lines.append(f"python scripts\\{script_name}")
        ps_lines.append("")

    ps_lines.append("Write-Host 'Reproducibility workflow complete.'")
    ps_lines.append("")

    write_text(package_dir / "run_all_windows.ps1", "\n".join(ps_lines))

    py_lines = [
        "# -*- coding: utf-8 -*-",
        '"""Run all analysis scripts in numeric order."""',
        "",
        "from pathlib import Path",
        "import argparse",
        "import subprocess",
        "import sys",
        "",
        "ROOT = Path(__file__).resolve().parent",
        "SCRIPTS = ROOT / 'scripts'",
        "",
        "def numeric_prefix(name):",
        "    try:",
        "        return int(str(name).split('_', 1)[0])",
        "    except Exception:",
        "        return None",
        "",
        "def main():",
        "    parser = argparse.ArgumentParser()",
        "    parser.add_argument('--start', type=int, default=1)",
        "    parser.add_argument('--end', type=int, default=13)",
        "    parser.add_argument('--skip-external', action='store_true')",
        "    args = parser.parse_args()",
        "",
        "    selected = []",
        "    for path in sorted(SCRIPTS.glob('*.py')):",
        "        n = numeric_prefix(path.name)",
        "        if n is None:",
        "            continue",
        "        if n < args.start or n > args.end:",
        "            continue",
        "        if args.skip_external and 'external' in path.name.lower():",
        "            continue",
        "        selected.append(path)",
        "",
        "    if not selected:",
        "        print('No scripts selected.')",
        "        return",
        "",
        "    for script in selected:",
        "        print('=' * 90)",
        "        print('Running:', script.name)",
        "        print('=' * 90)",
        "        result = subprocess.run([sys.executable, str(script)], cwd=str(ROOT))",
        "        if result.returncode != 0:",
        "            raise SystemExit(result.returncode)",
        "",
        "    print('All selected scripts completed.')",
        "",
        "if __name__ == '__main__':",
        "    main()",
        "",
    ]

    write_text(package_dir / "run_all.py", "\n".join(py_lines))


# ============================================================
# 7. Configs, manifests, integrity checker, zip
# ============================================================

def write_analysis_config(package_dir, mode, script_rows, table_rows, figure_rows):
    config = {
        "project_name": "ShiYiSiNan diet-to-physiology modeling",
        "package_name": PACKAGE_BASENAME,
        "package_mode": mode,
        "generated_at": dt.datetime.now().isoformat(),
        "project_root": str(ROOT),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "script_count": len(script_rows),
        "table_count": len(table_rows),
        "figure_count": len(figure_rows),
        "primary_dataset": "CGMacros",
        "external_validation_dataset": "OhioT1DM",
        "analysis_steps": [
            "meal-level phenotype construction",
            "feature-set ablation",
            "subject-level bootstrap",
            "paired delta bootstrap",
            "subgroup analysis",
            "error analysis",
            "calibration analysis",
            "counterfactual meal-substitution simulation",
            "lightweight external framework validation",
            "reproducibility packaging",
        ],
    }

    write_json(package_dir / "analysis_config.json", config)
    write_json(package_dir / "configs" / "analysis_config.json", config)


def write_integrity_checker(package_dir):
    lines = [
        "# -*- coding: utf-8 -*-",
        '"""Verify SHA256 checksums for this package."""',
        "",
        "from pathlib import Path",
        "import csv",
        "import hashlib",
        "import sys",
        "",
        "ROOT = Path(__file__).resolve().parent",
        "MANIFEST = ROOT / 'checksums' / 'sha256_manifest.csv'",
        "",
        "def sha256_file(path, block_size=1024 * 1024):",
        "    h = hashlib.sha256()",
        "    with Path(path).open('rb') as f:",
        "        while True:",
        "            block = f.read(block_size)",
        "            if not block:",
        "                break",
        "            h.update(block)",
        "    return h.hexdigest()",
        "",
        "def main():",
        "    if not MANIFEST.exists():",
        "        print('Missing manifest:', MANIFEST)",
        "        sys.exit(1)",
        "",
        "    failures = []",
        "    checked = 0",
        "",
        "    with MANIFEST.open('r', encoding='utf-8-sig', newline='') as f:",
        "        reader = csv.DictReader(f)",
        "        for row in reader:",
        "            rel = row['relative_path']",
        "            expected = row['sha256']",
        "            path = ROOT / rel",
        "            if not path.exists():",
        "                failures.append((rel, 'missing'))",
        "                continue",
        "            observed = sha256_file(path)",
        "            checked += 1",
        "            if observed != expected:",
        "                failures.append((rel, 'checksum_mismatch'))",
        "",
        "    if failures:",
        "        print('Integrity check failed:')",
        "        for rel, reason in failures:",
        "            print(' -', rel, reason)",
        "        sys.exit(1)",
        "",
        "    print(f'Integrity check passed for {checked} files.')",
        "",
        "if __name__ == '__main__':",
        "    main()",
        "",
    ]

    write_text(package_dir / "verify_package_integrity.py", "\n".join(lines))


def build_package_manifest(package_dir):
    package_dir = Path(package_dir)
    rows = []

    for path in sorted(package_dir.rglob("*")):
        if not path.is_file():
            continue

        rel = path.relative_to(package_dir).as_posix()

        # These manifests are generated from the collected rows.
        # Including them is okay, but checksums change if rewritten.
        # We exclude checksum manifests from their own checksum list.
        if rel in [
            "manifests/package_manifest.csv",
            "checksums/sha256_manifest.csv",
        ]:
            continue

        rows.append({
            "relative_path": rel,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })

    write_csv(package_dir / "manifests" / "package_manifest.csv", rows)
    write_csv(package_dir / "checksums" / "sha256_manifest.csv", rows)

    return rows


def create_zip_archive(package_dir):
    package_dir = Path(package_dir)
    zip_path = OUTPUT_ROOT / f"{package_dir.name}_{timestamp()}.zip"

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(package_dir.rglob("*")):
            if not path.is_file():
                continue
            arcname = path.relative_to(package_dir.parent)
            z.write(path, arcname)

    return zip_path


# ============================================================
# 8. Safety audit
# ============================================================

def audit_package_for_sensitive_files(package_dir):
    package_dir = Path(package_dir)

    flagged = []

    for path in sorted(package_dir.rglob("*")):
        if not path.is_file():
            continue

        name = path.name.lower()
        rel = path.relative_to(package_dir).as_posix()

        if is_secret_file(path):
            flagged.append(rel)
            continue

        if name.endswith(".xml"):
            flagged.append(rel)
            continue

        if "kaggle" in name:
            flagged.append(rel)
            continue

        if "token" in name or "secret" in name or "credential" in name:
            flagged.append(rel)
            continue

    audit = {
        "generated_at": dt.datetime.now().isoformat(),
        "n_flagged_files": len(flagged),
        "flagged_files": flagged,
        "status": "pass" if len(flagged) == 0 else "review_required",
    }

    write_json(package_dir / "manifests" / "safety_audit.json", audit)

    return audit


# ============================================================
# 9. Main
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["public", "full-local"],
        default="public",
        help="public excludes raw/row-level/sensitive outputs; full-local copies more local outputs.",
    )
    parser.add_argument(
        "--no-zip",
        action="store_true",
        help="Do not create zip archive.",
    )

    args = parser.parse_args()

    mode = args.mode

    ensure_dir(OUTPUT_ROOT)

    package_dir = OUTPUT_ROOT / PACKAGE_BASENAME

    if package_dir.exists():
        shutil.rmtree(package_dir)

    ensure_dir(package_dir)
    create_package_dirs(package_dir)

    print("Building reproducibility package")
    print("Project root:", ROOT)
    print("Package dir:", package_dir)
    print("Mode:", mode)

    print("\nCopying scripts...")
    script_rows = copy_scripts(package_dir)
    write_csv(package_dir / "manifests" / "script_manifest.csv", script_rows)

    print("Copying tables...")
    table_rows = copy_tables(package_dir, mode)
    write_csv(package_dir / "manifests" / "table_manifest.csv", table_rows)

    print("Copying figures...")
    figure_rows = copy_figures(package_dir)
    write_csv(package_dir / "manifests" / "figure_manifest.csv", figure_rows)

    print("Writing environment files...")
    write_environment_files(package_dir)

    print("Writing run scripts...")
    ordered_scripts = get_ordered_scripts()
    write_run_all_scripts(package_dir, ordered_scripts)

    print("Writing documentation...")
    write_all_docs(package_dir, mode, ordered_scripts)

    print("Writing analysis config...")
    write_analysis_config(package_dir, mode, script_rows, table_rows, figure_rows)

    print("Writing integrity checker...")
    write_integrity_checker(package_dir)

    print("Running safety audit...")
    audit = audit_package_for_sensitive_files(package_dir)

    print("Building package manifest...")
    package_manifest = build_package_manifest(package_dir)

    zip_path = None
    if not args.no_zip:
        print("Creating zip archive...")
        zip_path = create_zip_archive(package_dir)

    print("\nDone.")
    print("Package directory:")
    print(package_dir)

    if zip_path is not None:
        print("Zip archive:")
        print(zip_path)

    print("\nCounts:")
    print("Scripts copied:", len(script_rows))
    print("Tables copied:", len(table_rows))
    print("Figures copied:", len(figure_rows))
    print("Package files:", len(package_manifest))
    print("Safety audit status:", audit["status"])
    print("Flagged files:", audit["n_flagged_files"])

    print("\nNext checks:")
    print("1. Open README_REPRODUCIBILITY.md")
    print("2. Open DATA_AVAILABILITY.md")
    print("3. Run integrity check:")
    print("   cd outputs\\reproducibility_package\\ShiYiSiNan_reproducibility_package")
    print("   python verify_package_integrity.py")
    print("4. Confirm public package contains no raw data, XML files, kaggle.json, or tokens.")


if __name__ == "__main__":
    main()