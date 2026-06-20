"""Run the complete high-impact diabetes phase-map research pipeline."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"


STEPS = [
    {
        "name": "prepare_cleaned_public_diabetes_data",
        "command": [sys.executable, "scripts/prepare_diabetes_rct_ml_dataset.py"],
        "expected": ["data/processed/processed_ml_table.csv", "data/processed/cgm_summary_long.csv"],
    },
    {
        "name": "run_primary_phase_map_and_ml_experiments",
        "command": [sys.executable, "scripts/run_glycemic_phase_research.py"],
        "expected": ["results/model_performance_cv.csv", "results/hte_by_phase.csv"],
    },
    {
        "name": "run_journal_grade_secondary_experiments",
        "command": [sys.executable, "scripts/run_journal_grade_experiments.py"],
        "expected": ["results/journal_calibration_metrics.csv", "results/journal_loso_summary.csv"],
    },
    {
        "name": "run_adjusted_phase_outcome_models",
        "command": [sys.executable, "scripts/run_adjusted_phase_outcome_models.py"],
        "expected": ["results/journal_adjusted_phase_outcome_models.csv"],
    },
    {
        "name": "run_nested_tuning_experiments",
        "command": [sys.executable, "scripts/run_nested_tuning_experiments.py"],
        "expected": ["results/journal_nested_tuning_summary.csv", "figures/journal_nested_tuning_auroc.png"],
    },
    {
        "name": "build_manuscript_tables",
        "command": [sys.executable, "scripts/build_manuscript_tables.py"],
        "expected": ["results/table1_baseline_by_phase.csv", "docs/manuscript_tables_figures_index_zh.md"],
    },
    {
        "name": "build_manuscript_draft",
        "command": [sys.executable, "scripts/build_manuscript_draft.py"],
        "expected": ["docs/manuscript_draft_zh.md"],
    },
    {
        "name": "build_master_report_and_manifest",
        "command": [sys.executable, "scripts/build_high_impact_research_report.py"],
        "expected": ["results/research_artifact_manifest.csv", "docs/high_impact_study_completion_report_zh.md"],
    },
]


def run_step(step: dict) -> dict:
    start = time.perf_counter()
    proc = subprocess.run(step["command"], cwd=ROOT, capture_output=True, text=True)
    elapsed = time.perf_counter() - start
    expected_status = {path: (ROOT / path).exists() for path in step["expected"]}
    return {
        "step": step["name"],
        "command": " ".join(step["command"]),
        "returncode": proc.returncode,
        "elapsed_seconds": round(elapsed, 2),
        "expected_outputs_present": all(expected_status.values()),
        "expected_output_status": expected_status,
        "stdout_tail": proc.stdout[-1200:],
        "stderr_tail": proc.stderr[-1200:],
    }


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    failed = False
    for step in STEPS:
        record = run_step(step)
        records.append(record)
        if record["returncode"] != 0 or not record["expected_outputs_present"]:
            failed = True
            break
    out = pd.DataFrame(records)
    out.to_csv(RESULTS_DIR / "full_pipeline_run_status.csv", index=False)
    payload = {
        "status": "failed" if failed else "success",
        "steps_completed": len(records),
        "total_elapsed_seconds": round(sum(r["elapsed_seconds"] for r in records), 2),
        "status_csv": "results/full_pipeline_run_status.csv",
    }
    (RESULTS_DIR / "full_pipeline_run_status.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
