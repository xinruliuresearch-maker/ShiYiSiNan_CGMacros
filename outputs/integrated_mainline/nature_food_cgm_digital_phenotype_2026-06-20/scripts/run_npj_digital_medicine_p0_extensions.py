"""P0 extensions for the npj Digital Medicine glycaemic phase-map package.

This script adds four submission-facing components:

1. Compatibility screening across jaeb_public_extra.
2. Additional frozen validation where baseline CGM and follow-up outcomes exist.
3. Loop and LOSO calibration upgrade with Brier decomposition and TIR
   recalibration sensitivity.
4. Subgroup uncertainty audit and a versioned phase-map software release bundle.
"""

from __future__ import annotations

import io
import json
import math
import shutil
import textwrap
import zipfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline

import run_npj_digital_medicine_p0_workup as p0


ROOT = Path(r"D:\ai for science")
PHASE = ROOT / "results" / "jaeb_glycemic_phase_completion"
STRATEGY = ROOT / "results" / "npj_digital_medicine_phase_strategy"
RAW_EXTRA = ROOT / "data" / "raw" / "jaeb_public_extra"
RESULTS = ROOT / "results"
P0 = STRATEGY / "p0_workup"
OUT = STRATEGY / "p0_extensions_2026_06_18"
DOCS = OUT / "docs"
TABLES = OUT / "tables"
FIGSRC = OUT / "figure_source_data"
FIGURES = OUT / "figures"
SOFTWARE = OUT / "software_release" / "phase_map_jaeb_v0_1"

for path in [OUT, DOCS, TABLES, FIGSRC, FIGURES, SOFTWARE]:
    path.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
MIN_BOOTSTRAP_N = 20
BOOTSTRAPS = 300
ORDER_COLS = p0.ORDER_COLS


TARGET_ZIPS = {
    "GLAM": "GLAM Public Dataset.zip",
    "RacialDifferences": "RacialDifferences_2024-02-22.zip",
    "SevereHypo": "SevereHypoDataset-c14d3739-6a20-449c-bbae-c02ff1764a91.zip",
    "CGMND": "CGMND-af920dee-2d6e-4436-bc89-7a7b51239837.zip",
    "CGMNDYoungChildren": "CGMNDYoungChildren.zip",
    "PSO1": "PSO1_Public_Dataset-1759d88a-2554-4c92-9193-ba59cdb7e810.zip",
    "PSO3": "PSO3_Public_Dataset-a2d5e5d2-36e2-4c0a-ba5e-5afebc5128e6.zip",
    "PSO4": "PSO4_Public_Dataset-cf7f24a6-7253-447b-a61c-3e7667b441da.zip",
}


def write(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("<", "", regex=False),
        errors="coerce",
    )


def read_zip_table(zip_name: str, member: str, nrows: int | None = None) -> pd.DataFrame:
    zpath = RAW_EXTRA / zip_name
    with zipfile.ZipFile(zpath) as archive:
        raw = archive.read(member)
    sniff = raw[:5000]
    sep = "|" if sniff.count(b"|") >= sniff.count(b",") else ","
    return pd.read_csv(io.BytesIO(raw), sep=sep, dtype=str, nrows=nrows, low_memory=False)


def zip_members(zip_name: str) -> list[str]:
    with zipfile.ZipFile(RAW_EXTRA / zip_name) as archive:
        return [m for m in archive.namelist() if not m.endswith("/")]


def count_unique_member(zip_name: str, member: str, id_col: str) -> int:
    zpath = RAW_EXTRA / zip_name
    with zipfile.ZipFile(zpath) as archive:
        with archive.open(member) as handle:
            sample = handle.read(5000)
        sep = "|" if sample.count(b"|") >= sample.count(b",") else ","
        with archive.open(member) as handle:
            ids: set[str] = set()
            for chunk in pd.read_csv(handle, sep=sep, dtype=str, usecols=[id_col], chunksize=500000, low_memory=False):
                ids.update(chunk[id_col].dropna().astype(str).unique().tolist())
    return len(ids)


def raw_cgm_summary(
    df: pd.DataFrame,
    id_col: str,
    glucose_col: str,
    time_col: str | None = None,
    day_col: str | None = None,
    units_col: str | None = None,
    prefix: str = "",
) -> pd.DataFrame:
    dat = df[[c for c in [id_col, glucose_col, time_col, day_col, units_col] if c]].copy()
    dat["glucose_mg_dl"] = to_num(dat[glucose_col])
    if units_col and units_col in dat.columns:
        metric = dat[units_col].astype(str).str.lower().str.contains("metric", na=False)
        dat.loc[metric, "glucose_mg_dl"] = dat.loc[metric, "glucose_mg_dl"] * 18.0182
    dat = dat[dat["glucose_mg_dl"].between(20, 600)].copy()
    if day_col:
        dat["day"] = to_num(dat[day_col])
    else:
        dt = pd.to_datetime(dat[time_col], errors="coerce")
        dat["dt"] = dt
        dat = dat.dropna(subset=["dt"])
        first_dt = dat.groupby(id_col)["dt"].transform("min")
        dat["day"] = (dat["dt"] - first_dt).dt.total_seconds() / 86400.0
    dat = dat.dropna(subset=[id_col, "day", "glucose_mg_dl"]).copy()

    rows = []
    for pid, g in dat.groupby(id_col):
        min_day = g["day"].min()
        max_day = g["day"].max()
        base = g[g["day"].between(min_day, min_day + 14, inclusive="both")]
        follow = g[g["day"].between(max_day - 14, max_day, inclusive="both")]
        for label, w in [("baseline", base), ("followup", follow)]:
            if len(w) == 0:
                continue
            glucose = w["glucose_mg_dl"].astype(float)
            out_prefix = "" if label == "baseline" else "followup_"
            rows.append(
                {
                    id_col: pid,
                    "window": label,
                    f"{out_prefix}cgm_mean_glucose_mg_dl": glucose.mean(),
                    f"{out_prefix}cgm_time_in_range_70_180_pct": glucose.between(70, 180).mean() * 100.0,
                    f"{out_prefix}cgm_time_below_70_pct": (glucose < 70).mean() * 100.0,
                    f"{out_prefix}cgm_time_below_54_pct": (glucose < 54).mean() * 100.0,
                    f"{out_prefix}cgm_time_above_180_pct": (glucose > 180).mean() * 100.0,
                    f"{out_prefix}cgm_time_above_250_pct": (glucose > 250).mean() * 100.0,
                    f"{out_prefix}cgm_cv_pct": glucose.std(ddof=0) / glucose.mean() * 100.0 if glucose.mean() else np.nan,
                    f"{out_prefix}cgm_hours": len(glucose) * 5.0 / 60.0,
                    f"{out_prefix}cgm_start_day": w["day"].min(),
                    f"{out_prefix}cgm_end_day": w["day"].max(),
                }
            )
    long = pd.DataFrame(rows)
    if long.empty:
        return pd.DataFrame()
    base_cols = [id_col] + [c for c in long.columns if c not in [id_col, "window"] and not c.startswith("followup_")]
    follow_cols = [id_col] + [c for c in long.columns if c.startswith("followup_")]
    base = long[long["window"].eq("baseline")][base_cols]
    follow = long[long["window"].eq("followup")][follow_cols]
    return base.merge(follow, on=id_col, how="outer", suffixes=("", "_dup"))


def add_phase_assignment(df: pd.DataFrame, train_phase: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    train_ref = train_phase.copy()
    train_ref["cgm_sd_proxy"] = train_ref["cgm_mean_glucose_mg_dl"] * train_ref["cgm_cv_pct"] / 100.0
    out["cgm_sd_proxy"] = out["cgm_mean_glucose_mg_dl"] * out["cgm_cv_pct"] / 100.0
    out["glycemic_burden_score"] = (
        p0.z_from_train(out["cgm_mean_glucose_mg_dl"], train_ref["cgm_mean_glucose_mg_dl"])
        + p0.z_from_train(out["cgm_time_above_180_pct"], train_ref["cgm_time_above_180_pct"])
        + p0.z_from_train(out["cgm_time_above_250_pct"], train_ref["cgm_time_above_250_pct"])
        - p0.z_from_train(out["cgm_time_in_range_70_180_pct"], train_ref["cgm_time_in_range_70_180_pct"])
    ) / 4.0
    out["hypoglycemic_susceptibility_score"] = (
        p0.z_from_train(out["cgm_time_below_70_pct"], train_ref["cgm_time_below_70_pct"])
        + p0.z_from_train(out["cgm_time_below_54_pct"], train_ref["cgm_time_below_54_pct"])
    ) / 2.0
    out["dynamic_instability_score"] = (
        p0.z_from_train(out["cgm_cv_pct"], train_ref["cgm_cv_pct"])
        + p0.z_from_train(out["cgm_sd_proxy"], train_ref["cgm_sd_proxy"])
    ) / 2.0
    out["circadian_disruption_score"] = 0.0
    out["resilience_proxy_score"] = (
        p0.z_from_train(out["cgm_time_above_250_pct"], train_ref["cgm_time_above_250_pct"])
        + p0.z_from_train(out["cgm_cv_pct"], train_ref["cgm_cv_pct"])
        + p0.z_from_train(out["cgm_mean_glucose_mg_dl"], train_ref["cgm_mean_glucose_mg_dl"])
    ) / 3.0

    centroids = train_ref.groupby("phase_label", as_index=False)[ORDER_COLS].mean()
    x = out[ORDER_COLS].fillna(0).to_numpy(float)
    dist = []
    for _, row in centroids.iterrows():
        c = row[ORDER_COLS].to_numpy(float)
        dist.append(np.sqrt(((x - c) ** 2).sum(axis=1)))
    dist = np.vstack(dist).T
    nearest = dist.argmin(axis=1)
    out["phase_label"] = [centroids.iloc[i]["phase_label"] for i in nearest]
    out["phase_assignment_distance"] = dist.min(axis=1)
    phase_dict = read_csv(PHASE / "jaeb_phase_label_dictionary.csv")
    out["phase_id"] = out["phase_label"].map(dict(zip(phase_dict["phase_label_zh"], phase_dict["phase_id"])))
    out["phase_label_en"] = out["phase_label"].map(dict(zip(phase_dict["phase_label_zh"], phase_dict["phase_label_en"])))
    return out


def finalize_external_dataset(df: pd.DataFrame, id_col: str, dataset_id: str, train_phase: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["participant_id"] = dataset_id + "_" + out[id_col].astype(str)
    out["study_id"] = dataset_id
    for col in ["x_randomized_arm", "x_sex", "x_race", "x_ethnicity"]:
        if col not in out.columns:
            out[col] = "missing"
    for col in ["x_age_years", "x_baseline_bmi", "x_diabetes_duration_years"]:
        if col not in out.columns:
            out[col] = np.nan
    out["y_hba1c_change_pct_points"] = out["y_followup_hba1c_pct"] - out["x_baseline_hba1c_pct"]
    out["y_hba1c_improved_ge_0_5"] = np.where(
        out["y_hba1c_change_pct_points"].notna(), (out["y_hba1c_change_pct_points"] <= -0.5).astype(int), np.nan
    )
    out["y_change_cgm_time_in_range_70_180_pct"] = (
        out["followup_cgm_time_in_range_70_180_pct"] - out["cgm_time_in_range_70_180_pct"]
    )
    out["y_tir_improved_ge_5pct"] = np.where(
        out["y_change_cgm_time_in_range_70_180_pct"].notna(),
        (out["y_change_cgm_time_in_range_70_180_pct"] >= 5).astype(int),
        np.nan,
    )
    out = add_phase_assignment(out, train_phase)
    return out


def build_racial_differences(train_phase: pd.DataFrame) -> pd.DataFrame:
    zip_name = TARGET_ZIPS["RacialDifferences"]
    raw = read_zip_table(zip_name, "RacialDifferences_2024-02-22/Data Tables/FDataCGM.txt")
    cgm = raw_cgm_summary(raw, "PtID", "Glucose", day_col="DeviceDaysFromEnroll")
    baseline = read_zip_table(zip_name, "RacialDifferences_2024-02-22/Data Tables/FBaseline.txt")
    final = read_zip_table(zip_name, "RacialDifferences_2024-02-22/Data Tables/FFinalVisit.txt")
    roster = read_zip_table(zip_name, "RacialDifferences_2024-02-22/Data Tables/FPtRoster.txt")
    baseline = baseline[["PtID", "Gender", "DiagT1DAge", "HbA1c"]].rename(columns={"HbA1c": "x_baseline_hba1c_pct"})
    final = final[["PtID", "HbA1c"]].rename(columns={"HbA1c": "y_followup_hba1c_pct"})
    roster = roster[["PtID", "RaceProtF", "ageAtEnroll"]].drop_duplicates("PtID")
    out = cgm.merge(baseline, on="PtID", how="left").merge(final, on="PtID", how="left").merge(roster, on="PtID", how="left")
    out["x_baseline_hba1c_pct"] = to_num(out["x_baseline_hba1c_pct"])
    out["y_followup_hba1c_pct"] = to_num(out["y_followup_hba1c_pct"])
    out["x_age_years"] = to_num(out["ageAtEnroll"])
    out["x_diabetes_duration_years"] = out["x_age_years"] - to_num(out["DiagT1DAge"])
    out["x_sex"] = out["Gender"].fillna("missing").str.lower()
    out["x_race"] = out["RaceProtF"].fillna("missing").str.lower().str.replace("non-hispanic ", "", regex=False)
    out["x_ethnicity"] = np.where(out["RaceProtF"].astype(str).str.contains("Hispanic", case=False, na=False), "hispanic", "not_hispanic_or_missing")
    out["x_randomized_arm"] = "observational_racial_differences"
    out["x_baseline_bmi"] = np.nan
    return finalize_external_dataset(out, "PtID", "RACIAL_DIFFERENCES_FROZEN", train_phase)


def build_pso3(train_phase: pd.DataFrame) -> pd.DataFrame:
    zip_name = TARGET_ZIPS["PSO3"]
    raw = read_zip_table(zip_name, "DataTables/cgm.txt")
    cgm = raw_cgm_summary(raw, "DeidentID", "CGM", time_col="DataDtTm", units_col="Units")
    baseline = read_zip_table(zip_name, "DataTables/randstudybaseline.txt")
    final = read_zip_table(zip_name, "DataTables/finalvisit.txt")
    baseline = baseline[["DeidentID", "HbA1CTest"]].rename(columns={"HbA1CTest": "x_baseline_hba1c_pct"})
    final = final[["DeidentID", "HbA1CTest"]].rename(columns={"HbA1CTest": "y_followup_hba1c_pct"})
    out = cgm.merge(baseline, on="DeidentID", how="left").merge(final, on="DeidentID", how="left")
    out["x_baseline_hba1c_pct"] = to_num(out["x_baseline_hba1c_pct"])
    out["y_followup_hba1c_pct"] = to_num(out["y_followup_hba1c_pct"])
    out["x_randomized_arm"] = "pso3"
    return finalize_external_dataset(out, "DeidentID", "PSO3_FROZEN", train_phase)


def build_pso4(train_phase: pd.DataFrame) -> pd.DataFrame:
    zip_name = TARGET_ZIPS["PSO4"]
    raw = read_zip_table(zip_name, "DataTables/PSO4CGM.txt")
    cgm = raw_cgm_summary(raw, "DeidentID", "CGM", time_col="DataDtTm", units_col="Units")
    baseline = read_zip_table(zip_name, "DataTables/PSO4RandStudyBaseline.txt")
    final = read_zip_table(zip_name, "DataTables/PSO4FinalVisit.txt")
    roster = read_zip_table(zip_name, "DataTables/PSO4PtRoster.txt")
    baseline = baseline[["DeidentID", "HbA1CTest"]].rename(columns={"HbA1CTest": "x_baseline_hba1c_pct"})
    final = final[["DeidentID", "HbA1CTest"]].rename(columns={"HbA1CTest": "y_followup_hba1c_pct"})
    roster = roster[["DeidentID", "PSO4AgeGroup"]].drop_duplicates("DeidentID")
    out = cgm.merge(baseline, on="DeidentID", how="left").merge(final, on="DeidentID", how="left").merge(roster, on="DeidentID", how="left")
    out["x_baseline_hba1c_pct"] = to_num(out["x_baseline_hba1c_pct"])
    out["y_followup_hba1c_pct"] = to_num(out["y_followup_hba1c_pct"])
    out["x_age_years"] = out["PSO4AgeGroup"].map({"3to6": 4.5, "7to10": 8.5, "11to14": 12.5})
    out["x_randomized_arm"] = "pso4"
    return finalize_external_dataset(out, "DeidentID", "PSO4_FROZEN", train_phase)


def compatibility_matrix() -> pd.DataFrame:
    rows = []
    rows.append(
        {
            "dataset": "GLAM",
            "zip_file": TARGET_ZIPS["GLAM"],
            "cgm_source": "Data Tables/tblGLAMDeviceCGM.txt",
            "n_with_cgm": count_unique_member(TARGET_ZIPS["GLAM"], "Data Tables/tblGLAMDeviceCGM.txt", "PtID"),
            "baseline_hba1c_source": "Data Tables/GLAMHbA1cResults.txt",
            "n_baseline_hba1c": read_zip_table(TARGET_ZIPS["GLAM"], "Data Tables/GLAMHbA1cResults.txt")["PtID"].nunique(),
            "followup_hba1c_source": "none",
            "n_followup_hba1c": 0,
            "followup_tir_possible": "yes_raw_cgm_but_no_followup_visit_anchor",
            "validation_decision": "not_eligible",
            "reason": "CGM is rich but HbA1c table has only four participants and no usable follow-up HbA1c response target.",
        }
    )
    racial_base = read_zip_table(TARGET_ZIPS["RacialDifferences"], "RacialDifferences_2024-02-22/Data Tables/FBaseline.txt")
    racial_final = read_zip_table(TARGET_ZIPS["RacialDifferences"], "RacialDifferences_2024-02-22/Data Tables/FFinalVisit.txt")
    rows.append(
        {
            "dataset": "RacialDifferences",
            "zip_file": TARGET_ZIPS["RacialDifferences"],
            "cgm_source": "FDataCGM raw CGM",
            "n_with_cgm": count_unique_member(TARGET_ZIPS["RacialDifferences"], "RacialDifferences_2024-02-22/Data Tables/FDataCGM.txt", "PtID"),
            "baseline_hba1c_source": "FBaseline.HbA1c",
            "n_baseline_hba1c": int(to_num(racial_base["HbA1c"]).notna().sum()),
            "followup_hba1c_source": "FFinalVisit.HbA1c",
            "n_followup_hba1c": int(to_num(racial_final["HbA1c"]).notna().sum()),
            "followup_tir_possible": "yes_last_14_days_raw_cgm",
            "validation_decision": "eligible_secondary_frozen",
            "reason": "Raw CGM, baseline HbA1c and final HbA1c are available; observational context differs from RCT training studies.",
        }
    )
    severe_sample = read_zip_table(TARGET_ZIPS["SevereHypo"], "Data Tables/BSampleResults.txt")
    rows.append(
        {
            "dataset": "SevereHypo",
            "zip_file": TARGET_ZIPS["SevereHypo"],
            "cgm_source": "Data Tables/BDataCGM.txt",
            "n_with_cgm": count_unique_member(TARGET_ZIPS["SevereHypo"], "Data Tables/BDataCGM.txt", "PtID"),
            "baseline_hba1c_source": "BSampleResults.HBA1C",
            "n_baseline_hba1c": int(severe_sample[severe_sample["Analyte"].eq("HBA1C")]["PtID"].nunique()),
            "followup_hba1c_source": "none",
            "n_followup_hba1c": 0,
            "followup_tir_possible": "no_clear_followup_outcome",
            "validation_decision": "not_eligible",
            "reason": "Case-control severe hypoglycaemia dataset has baseline HbA1c/CGM but no follow-up HbA1c or intervention-response target.",
        }
    )
    cgmnd_sample = read_zip_table(TARGET_ZIPS["CGMND"], "NonDiabSampleResults.csv")
    rows.append(
        {
            "dataset": "CGMND",
            "zip_file": TARGET_ZIPS["CGMND"],
            "cgm_source": "NonDiabDeviceCGM.csv",
            "n_with_cgm": count_unique_member(TARGET_ZIPS["CGMND"], "NonDiabDeviceCGM.csv", "PtID"),
            "baseline_hba1c_source": "NonDiabSampleResults baseline only",
            "n_baseline_hba1c": int(cgmnd_sample[cgmnd_sample["ResultName"].eq("HbA1c")]["PtID"].nunique()),
            "followup_hba1c_source": "none",
            "n_followup_hba1c": 0,
            "followup_tir_possible": "no_diabetes_response_target",
            "validation_decision": "not_eligible_for_diabetes_response",
            "reason": "Non-diabetic CGM reference cohort; useful for physiological contrast, not HbA1c/TIR treatment-response validation.",
        }
    )
    young = read_zip_table(TARGET_ZIPS["CGMNDYoungChildren"], "Data Tables/CGMNDTestResults.txt")
    rows.append(
        {
            "dataset": "CGMNDYoungChildren",
            "zip_file": TARGET_ZIPS["CGMNDYoungChildren"],
            "cgm_source": "CGMNDDeviceCGM raw CGM",
            "n_with_cgm": count_unique_member(TARGET_ZIPS["CGMNDYoungChildren"], "Data Tables/CGMNDDeviceCGM.txt", "DeidentID"),
            "baseline_hba1c_source": "CGMNDTestResults.Hba1cValue",
            "n_baseline_hba1c": int(to_num(young["Hba1cValue"]).notna().sum()),
            "followup_hba1c_source": "none",
            "n_followup_hba1c": 0,
            "followup_tir_possible": "no_diabetes_response_target",
            "validation_decision": "not_eligible_for_diabetes_response",
            "reason": "Young non-diabetic CGM reference cohort; no follow-up treatment-response target.",
        }
    )
    rows.append(
        {
            "dataset": "PSO1",
            "zip_file": TARGET_ZIPS["PSO1"],
            "cgm_source": "DataTables/CGM.txt",
            "n_with_cgm": count_unique_member(TARGET_ZIPS["PSO1"], "DataTables/CGM.txt", "DeidentID"),
            "baseline_hba1c_source": "none",
            "n_baseline_hba1c": 0,
            "followup_hba1c_source": "none",
            "n_followup_hba1c": 0,
            "followup_tir_possible": "yes_raw_cgm_but_n_too_small",
            "validation_decision": "not_eligible",
            "reason": "Only 20 participants and no HbA1c response target.",
        }
    )
    pso3_base = read_zip_table(TARGET_ZIPS["PSO3"], "DataTables/randstudybaseline.txt")
    pso3_final = read_zip_table(TARGET_ZIPS["PSO3"], "DataTables/finalvisit.txt")
    rows.append(
        {
            "dataset": "PSO3",
            "zip_file": TARGET_ZIPS["PSO3"],
            "cgm_source": "DataTables/cgm.txt",
            "n_with_cgm": count_unique_member(TARGET_ZIPS["PSO3"], "DataTables/cgm.txt", "DeidentID"),
            "baseline_hba1c_source": "randstudybaseline.HbA1CTest",
            "n_baseline_hba1c": int(to_num(pso3_base["HbA1CTest"]).notna().sum()),
            "followup_hba1c_source": "finalvisit.HbA1CTest",
            "n_followup_hba1c": int(to_num(pso3_final["HbA1CTest"]).notna().sum()),
            "followup_tir_possible": "yes_last_14_days_raw_cgm",
            "validation_decision": "eligible_small_descriptive",
            "reason": "Raw CGM, baseline HbA1c and final HbA1c exist, but sample size is small; pool with PSO4 for secondary validation.",
        }
    )
    pso4_base = read_zip_table(TARGET_ZIPS["PSO4"], "DataTables/PSO4RandStudyBaseline.txt")
    pso4_final = read_zip_table(TARGET_ZIPS["PSO4"], "DataTables/PSO4FinalVisit.txt")
    rows.append(
        {
            "dataset": "PSO4",
            "zip_file": TARGET_ZIPS["PSO4"],
            "cgm_source": "DataTables/PSO4CGM.txt",
            "n_with_cgm": count_unique_member(TARGET_ZIPS["PSO4"], "DataTables/PSO4CGM.txt", "DeidentID"),
            "baseline_hba1c_source": "PSO4RandStudyBaseline.HbA1CTest",
            "n_baseline_hba1c": int(to_num(pso4_base["HbA1CTest"]).notna().sum()),
            "followup_hba1c_source": "PSO4FinalVisit.HbA1CTest",
            "n_followup_hba1c": int(to_num(pso4_final["HbA1CTest"]).notna().sum()),
            "followup_tir_possible": "yes_last_14_days_raw_cgm",
            "validation_decision": "eligible_secondary_frozen",
            "reason": "Raw CGM, baseline HbA1c and final HbA1c exist; pediatric sensor/pump context differs from development corpus.",
        }
    )
    return pd.DataFrame(rows)


def external_metrics_for_dataset(ml_phase: pd.DataFrame, external: pd.DataFrame, validation_dataset: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    predictions = []
    metrics = []
    for target in ["y_hba1c_improved_ge_0_5", "y_tir_improved_ge_5pct"]:
        for fs_name, spec in p0.FEATURE_SETS.items():
            num_cols = [c for c in spec["numeric"] if c in ml_phase.columns and c in external.columns]
            cat_cols = [c for c in spec["categorical"] if c in ml_phase.columns and c in external.columns]
            train = ml_phase.dropna(subset=[target]).copy()
            test = external.dropna(subset=[target]).copy()
            if train[target].nunique() < 2 or test.empty or test[target].nunique() < 2:
                metrics.append(
                    {
                        "validation_dataset": validation_dataset,
                        "target": target,
                        "feature_set": fs_name,
                        "model": "logistic_ridge_locked_train",
                        "test_n": int(len(test)),
                        "status": "not_evaluable_single_class_or_empty",
                    }
                )
                continue
            pipe = Pipeline(
                [
                    ("pre", p0.make_preprocessor(num_cols, cat_cols)),
                    ("model", LogisticRegression(max_iter=2000, class_weight="balanced", solver="lbfgs")),
                ]
            )
            pipe.fit(train[num_cols + cat_cols], train[target].astype(int))
            prob = pipe.predict_proba(test[num_cols + cat_cols])[:, 1]
            pred_cols = ["participant_id", "study_id", "phase_label", "phase_id", "phase_label_en", target]
            pred = test[[c for c in pred_cols if c in test.columns]].copy()
            pred["validation_dataset"] = validation_dataset
            pred["target"] = target
            pred["feature_set"] = fs_name
            pred["model"] = "logistic_ridge_locked_train"
            pred["y_true"] = pred[target].astype(int)
            pred["y_prob"] = prob
            pred = pred.drop(columns=[target])
            predictions.append(pred)
            row = p0.binary_metrics(pred["y_true"], pred["y_prob"])
            row.update(
                {
                    "validation_dataset": validation_dataset,
                    "target": target,
                    "feature_set": fs_name,
                    "model": "logistic_ridge_locked_train",
                    "train_n": int(len(train)),
                    "test_n": int(len(test)),
                    "numeric_features": "; ".join(num_cols),
                    "categorical_features": "; ".join(cat_cols),
                    "status": "evaluable",
                }
            )
            metrics.append(row)
    return pd.DataFrame(metrics), pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()


def build_additional_external_validation(train_phase: pd.DataFrame, ml_phase: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    racial = build_racial_differences(train_phase)
    pso3 = build_pso3(train_phase)
    pso4 = build_pso4(train_phase)
    pooled = pd.concat([pso3, pso4], ignore_index=True)
    pooled["study_id"] = "PSO3_PSO4_POOLED_FROZEN"
    pooled["participant_id"] = pooled["participant_id"].str.replace("PSO3_FROZEN_", "PSO3_", regex=False).str.replace("PSO4_FROZEN_", "PSO4_", regex=False)

    datasets = {
        "RACIAL_DIFFERENCES_FROZEN": racial,
        "PSO3_FROZEN": pso3,
        "PSO4_FROZEN": pso4,
        "PSO3_PSO4_POOLED_FROZEN": pooled,
    }
    all_data = []
    all_metrics = []
    all_preds = []
    for name, dat in datasets.items():
        dat.to_csv(TABLES / f"{name.lower()}_external_dataset.csv", index=False)
        all_data.append(dat.assign(validation_dataset=name))
        m, p = external_metrics_for_dataset(ml_phase, dat, name)
        all_metrics.append(m)
        if not p.empty:
            all_preds.append(p)
    return pd.concat(all_data, ignore_index=True), pd.concat(all_metrics, ignore_index=True), pd.concat(all_preds, ignore_index=True) if all_preds else pd.DataFrame()


def calibration_bins(y: pd.Series, p: pd.Series, n_bins: int = 10) -> pd.DataFrame:
    y = pd.Series(y).astype(int).reset_index(drop=True)
    p = pd.Series(p).astype(float).clip(0, 1).reset_index(drop=True)
    cuts = pd.cut(p, np.linspace(0, 1, n_bins + 1), include_lowest=True, duplicates="drop")
    rows = []
    for interval, idx in p.groupby(cuts, observed=False).groups.items():
        if len(idx) == 0:
            continue
        rows.append(
            {
                "bin": str(interval),
                "n": int(len(idx)),
                "observed_rate": float(y.loc[idx].mean()),
                "mean_predicted_probability": float(p.loc[idx].mean()),
                "abs_calibration_error": float(abs(y.loc[idx].mean() - p.loc[idx].mean())),
            }
        )
    return pd.DataFrame(rows)


def brier_decomposition(y: pd.Series, p: pd.Series, n_bins: int = 10) -> dict[str, float]:
    y = pd.Series(y).astype(int).reset_index(drop=True)
    p = pd.Series(p).astype(float).clip(0, 1).reset_index(drop=True)
    overall = float(y.mean())
    bins = calibration_bins(y, p, n_bins)
    if bins.empty:
        return {"brier_reliability": np.nan, "brier_resolution": np.nan, "brier_uncertainty": overall * (1 - overall)}
    rel = ((bins["n"] / len(y)) * (bins["mean_predicted_probability"] - bins["observed_rate"]) ** 2).sum()
    res = ((bins["n"] / len(y)) * (bins["observed_rate"] - overall) ** 2).sum()
    unc = overall * (1 - overall)
    return {"brier_reliability": float(rel), "brier_resolution": float(res), "brier_uncertainty": float(unc)}


def summarize_predictions(preds: pd.DataFrame, source: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    bin_rows = []
    for keys, group in preds.groupby(["target", "feature_set", "model"]):
        target, feature_set, model = keys
        metrics = p0.binary_metrics(group["y_true"], group["y_prob"])
        metrics.update(brier_decomposition(group["y_true"], group["y_prob"]))
        metrics.update({"prediction_source": source, "target": target, "feature_set": feature_set, "model": model})
        rows.append(metrics)
        bins = calibration_bins(group["y_true"], group["y_prob"])
        if not bins.empty:
            bins.insert(0, "prediction_source", source)
            bins.insert(1, "target", target)
            bins.insert(2, "feature_set", feature_set)
            bins.insert(3, "model", model)
            bin_rows.append(bins)
    return pd.DataFrame(rows), pd.concat(bin_rows, ignore_index=True) if bin_rows else pd.DataFrame()


def loso_predictions_locked_logistic(ml_phase: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for target in ["y_hba1c_improved_ge_0_5", "y_tir_improved_ge_5pct"]:
        for fs_name, spec in p0.FEATURE_SETS.items():
            num_cols = [c for c in spec["numeric"] if c in ml_phase.columns]
            cat_cols = [c for c in spec["categorical"] if c in ml_phase.columns]
            data = ml_phase.dropna(subset=[target]).copy()
            if target == "y_tir_improved_ge_5pct":
                data = data[data["phase_label"].notna()].copy()
            if data[target].nunique() < 2:
                continue
            for study, test in data.groupby("study_id"):
                train = data[data["study_id"].ne(study)].copy()
                if train[target].nunique() < 2 or test[target].nunique() < 2 or len(test) < 20:
                    continue
                pipe = Pipeline(
                    [
                        ("pre", p0.make_preprocessor(num_cols, cat_cols)),
                        ("model", LogisticRegression(max_iter=2000, class_weight="balanced", solver="lbfgs")),
                    ]
                )
                pipe.fit(train[num_cols + cat_cols], train[target].astype(int))
                prob = pipe.predict_proba(test[num_cols + cat_cols])[:, 1]
                for pid, y, pr in zip(test["participant_id"], test[target].astype(int), prob):
                    rows.append(
                        {
                            "participant_id": pid,
                            "heldout_study_id": study,
                            "target": target,
                            "feature_set": fs_name,
                            "model": "logistic_ridge_loso",
                            "y_true": int(y),
                            "y_prob": float(np.clip(pr, 0, 1)),
                        }
                    )
    return pd.DataFrame(rows)


def recalibrate_probabilities(y: pd.Series, p: pd.Series) -> tuple[pd.Series, float, float]:
    y = pd.Series(y).astype(int)
    p = pd.Series(p).astype(float).clip(1e-6, 1 - 1e-6)
    if len(y) < 20 or y.nunique() < 2:
        return p, np.nan, np.nan
    x = p0.logit(p).to_numpy().reshape(-1, 1)
    model = LogisticRegression(penalty=None, solver="lbfgs", max_iter=1000)
    model.fit(x, y)
    recal = model.predict_proba(x)[:, 1]
    return pd.Series(recal, index=p.index), float(model.intercept_[0]), float(model.coef_[0][0])


def calibration_upgrade(ml_phase: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    loop_preds = read_csv(P0 / "tables" / "loop_frozen_external_validation_predictions.csv")
    loop_preds = loop_preds.rename(columns={"validation_dataset": "prediction_source"})
    if "prediction_source" not in loop_preds.columns:
        loop_preds["prediction_source"] = "LOOP_FROZEN"
    loop_preds["prediction_source"] = "LOOP_FROZEN"
    loop_metrics, loop_bins = summarize_predictions(loop_preds, "LOOP_FROZEN")

    loso_preds = loso_predictions_locked_logistic(ml_phase)
    loso_preds.to_csv(TABLES / "loso_locked_logistic_predictions.csv", index=False)
    loso_metrics, loso_bins = summarize_predictions(loso_preds, "LOSO_LOCKED_LOGISTIC")

    metrics = pd.concat([loop_metrics, loso_metrics], ignore_index=True)
    bins = pd.concat([loop_bins, loso_bins], ignore_index=True)

    sens_rows = []
    for source, preds in [("LOOP_FROZEN", loop_preds), ("LOSO_LOCKED_LOGISTIC", loso_preds)]:
        tir = preds[preds["target"].eq("y_tir_improved_ge_5pct")].copy()
        for keys, group in tir.groupby(["feature_set", "model"]):
            feature_set, model = keys
            raw = p0.binary_metrics(group["y_true"], group["y_prob"])
            recal, intercept, slope = recalibrate_probabilities(group["y_true"], group["y_prob"])
            recal_metrics = p0.binary_metrics(group["y_true"], recal)
            sens_rows.append(
                {
                    "prediction_source": source,
                    "target": "y_tir_improved_ge_5pct",
                    "feature_set": feature_set,
                    "model": model,
                    "method": "apparent_intercept_slope_recalibration_sensitivity",
                    "calibration_intercept_used": intercept,
                    "calibration_slope_used": slope,
                    "raw_brier": raw["brier"],
                    "recalibrated_brier": recal_metrics["brier"],
                    "raw_ece": raw["expected_calibration_error"],
                    "recalibrated_ece": recal_metrics["expected_calibration_error"],
                    "raw_mean_predicted_risk": raw["mean_predicted_risk"],
                    "recalibrated_mean_predicted_risk": recal_metrics["mean_predicted_risk"],
                    "observed_rate": raw["positive_rate"],
                    "interpretation": "sensitivity_only_not_a_new_frozen_model",
                }
            )
    sensitivity = pd.DataFrame(sens_rows)
    return metrics, bins, sensitivity


def plot_calibration(metrics: pd.DataFrame, bins: pd.DataFrame) -> None:
    if bins.empty:
        return
    focus = bins[
        bins["feature_set"].isin(["C2_clinical_plus_cgm", "C4_phase_map"])
        & bins["prediction_source"].isin(["LOOP_FROZEN", "LOSO_LOCKED_LOGISTIC"])
    ].copy()
    targets = ["y_hba1c_improved_ge_0_5", "y_tir_improved_ge_5pct"]
    sources = ["LOOP_FROZEN", "LOSO_LOCKED_LOGISTIC"]
    fig, axes = plt.subplots(len(targets), len(sources), figsize=(12, 9), sharex=True, sharey=True)
    for i, target in enumerate(targets):
        for j, source in enumerate(sources):
            ax = axes[i, j]
            sub = focus[(focus["target"].eq(target)) & (focus["prediction_source"].eq(source))]
            for feature_set, g in sub.groupby("feature_set"):
                label = "Clinical+CGM" if feature_set == "C2_clinical_plus_cgm" else "Phase-map"
                ax.plot(g["mean_predicted_probability"], g["observed_rate"], marker="o", label=label)
            ax.plot([0, 1], [0, 1], color="#333333", lw=0.8, linestyle="--")
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.set_title(f"{source} - {'HbA1c' if 'hba1c' in target else 'TIR'}")
            ax.set_xlabel("Predicted")
            ax.set_ylabel("Observed")
            ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES / "calibration_loop_loso_upgrade.png", dpi=220)
    plt.close(fig)

    brier = metrics[metrics["feature_set"].isin(["C2_clinical_plus_cgm", "C4_phase_map"])].copy()
    brier["label"] = brier["prediction_source"] + "\n" + brier["target"].str.replace("y_", "", regex=False) + "\n" + brier["feature_set"].replace(
        {"C2_clinical_plus_cgm": "Clinical+CGM", "C4_phase_map": "Phase-map"}
    )
    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(brier))
    ax.bar(x, brier["brier_reliability"], label="Reliability", color="#E15759")
    ax.bar(x, brier["brier_resolution"], bottom=brier["brier_reliability"], label="Resolution", color="#4E79A7")
    ax.set_xticks(x, brier["label"], rotation=70, ha="right", fontsize=7)
    ax.set_ylabel("Brier decomposition components")
    ax.set_title("Calibration decomposition")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "brier_decomposition_loop_loso.png", dpi=220)
    plt.close(fig)


def bootstrap_metric_ci(y: pd.Series, p: pd.Series, metric: str, n_boot: int = BOOTSTRAPS) -> tuple[float, float]:
    y = pd.Series(y).astype(int).reset_index(drop=True)
    p = pd.Series(p).astype(float).reset_index(drop=True)
    if len(y) < MIN_BOOTSTRAP_N:
        return np.nan, np.nan
    rng = np.random.default_rng(RANDOM_STATE)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        yy = y.iloc[idx]
        pp = p.iloc[idx]
        if metric == "auroc":
            if yy.nunique() < 2:
                continue
            vals.append(roc_auc_score(yy, pp))
        elif metric == "ece":
            vals.append(p0.ece_score(yy, pp))
        elif metric == "brier":
            if yy.nunique() < 2:
                continue
            vals.append(brier_score_loss(yy, pp.clip(0, 1)))
    if len(vals) < 20:
        return np.nan, np.nan
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def subgroup_uncertainty_audit() -> tuple[pd.DataFrame, pd.DataFrame]:
    fairness = read_csv(P0 / "tables" / "subgroup_fairness_calibration_audit.csv")
    oof = read_csv(RESULTS / "journal_oof_predictions.csv")
    ml_phase = p0.build_training_ml_phase()
    meta_cols = [
        "participant_id",
        "study_id",
        "x_age_years",
        "x_sex",
        "x_race",
        "x_ethnicity",
        "x_baseline_hba1c_pct",
        "phase_label",
    ]
    dat = oof.merge(ml_phase[meta_cols], on=["participant_id", "study_id"], how="left")
    dat["age_group"] = pd.cut(dat["x_age_years"], [-np.inf, 18, 45, 65, np.inf], labels=["<18", "18-44", "45-64", "65+"])
    dat["baseline_hba1c_group"] = pd.cut(
        dat["x_baseline_hba1c_pct"], [-np.inf, 7, 8, 9, np.inf], labels=["<7", "7-<8", "8-<9", ">=9"]
    )
    group_vars = ["age_group", "x_sex", "x_race", "x_ethnicity", "study_id", "phase_label", "baseline_hba1c_group"]

    selected = dat[
        (
            (dat["target"].eq("y_hba1c_improved_ge_0_5") & dat["feature_set"].isin(["C1_clinical", "C4_phase_map"]))
            | (dat["target"].eq("y_tir_improved_ge_5pct") & dat["feature_set"].isin(["C2_clinical_plus_cgm", "C4_phase_map"]))
        )
    ].copy()
    ci_rows = []
    for (target, feature_set, model), group in selected.groupby(["target", "feature_set", "model"]):
        overall_key = {
            "target": target,
            "feature_set": feature_set,
            "model": model,
            "subgroup_variable": "overall",
            "subgroup": "overall",
        }
        for gv in ["overall"] + group_vars:
            sub_iter = [("overall", group)] if gv == "overall" else group.dropna(subset=[gv]).groupby(gv, observed=False)
            for level, sub in sub_iter:
                if len(sub) < 20:
                    continue
                y = sub["y_true"].astype(int)
                p = sub["y_prob"].astype(float)
                n_events = int(y.sum())
                n_nonevents = int((1 - y).sum())
                if len(sub) >= 100 and min(n_events, n_nonevents) >= 20:
                    min_n_rule = "primary_interpretation"
                elif len(sub) >= 50 and min(n_events, n_nonevents) >= 10:
                    min_n_rule = "descriptive_only"
                else:
                    min_n_rule = "small_n_no_strong_conclusion"
                au_lo, au_hi = bootstrap_metric_ci(y, p, "auroc")
                ec_lo, ec_hi = bootstrap_metric_ci(y, p, "ece")
                br_lo, br_hi = bootstrap_metric_ci(y, p, "brier")
                ci_rows.append(
                    {
                        "target": target,
                        "feature_set": feature_set,
                        "model": model,
                        "subgroup_variable": gv,
                        "subgroup": str(level),
                        "n_events": n_events,
                        "n_nonevents": n_nonevents,
                        "minimum_n_rule": min_n_rule,
                        "auroc_ci_low": au_lo,
                        "auroc_ci_high": au_hi,
                        "ece_ci_low": ec_lo,
                        "ece_ci_high": ec_hi,
                        "brier_ci_low": br_lo,
                        "brier_ci_high": br_hi,
                    }
                )
    ci = pd.DataFrame(ci_rows)
    out = fairness.merge(ci, on=["target", "feature_set", "model", "subgroup_variable", "subgroup"], how="left")
    if "minimum_n_rule" not in out.columns:
        out["minimum_n_rule"] = "not_evaluable"

    phase_dict = read_csv(PHASE / "jaeb_phase_label_dictionary.csv")
    phase_en = dict(zip(phase_dict["phase_label_zh"], phase_dict["phase_label_en"]))
    dist_rows = []
    phase_base = ml_phase.copy()
    phase_base["age_group"] = pd.cut(phase_base["x_age_years"], [-np.inf, 18, 45, 65, np.inf], labels=["<18", "18-44", "45-64", "65+"])
    phase_base["baseline_hba1c_group"] = pd.cut(
        phase_base["x_baseline_hba1c_pct"], [-np.inf, 7, 8, 9, np.inf], labels=["<7", "7-<8", "8-<9", ">=9"]
    )
    for gv in group_vars:
        for level, sub in phase_base.dropna(subset=[gv, "phase_label"]).groupby(gv, observed=False):
            total = len(sub)
            if total == 0:
                continue
            counts = sub["phase_label"].value_counts()
            for phase_label, n in counts.items():
                dist_rows.append(
                    {
                        "subgroup_variable": gv,
                        "subgroup": str(level),
                        "phase_label": phase_label,
                        "phase_label_en": phase_en.get(phase_label, phase_label),
                        "n": int(n),
                        "subgroup_total": int(total),
                        "phase_proportion": float(n / total),
                    }
                )
    phase_distribution = pd.DataFrame(dist_rows)
    return out, phase_distribution


def build_software_release(train_phase: pd.DataFrame) -> pd.DataFrame:
    if SOFTWARE.exists():
        shutil.rmtree(SOFTWARE)
    (SOFTWARE / "phase_map" / "assets").mkdir(parents=True, exist_ok=True)
    (SOFTWARE / "schemas").mkdir(parents=True, exist_ok=True)
    (SOFTWARE / "toy_data").mkdir(parents=True, exist_ok=True)
    (SOFTWARE / "tests").mkdir(parents=True, exist_ok=True)
    (SOFTWARE / "scripts").mkdir(parents=True, exist_ok=True)

    phase_dict = read_csv(PHASE / "jaeb_phase_label_dictionary.csv")
    train_ref = train_phase.copy()
    train_ref["cgm_sd_proxy"] = train_ref["cgm_mean_glucose_mg_dl"] * train_ref["cgm_cv_pct"] / 100.0
    ref_cols = [
        "cgm_mean_glucose_mg_dl",
        "cgm_time_in_range_70_180_pct",
        "cgm_time_below_70_pct",
        "cgm_time_below_54_pct",
        "cgm_time_above_180_pct",
        "cgm_time_above_250_pct",
        "cgm_cv_pct",
        "cgm_sd_proxy",
    ]
    ref = {
        "version": "phase-map-jaeb-summary-v0.1",
        "feature_reference": {
            c: {"mean": float(pd.to_numeric(train_ref[c], errors="coerce").mean()), "sd": float(pd.to_numeric(train_ref[c], errors="coerce").std(ddof=0))}
            for c in ref_cols
        },
        "order_parameters": ORDER_COLS,
        "centroids": train_ref.groupby("phase_label", as_index=False)[ORDER_COLS].mean().to_dict(orient="records"),
        "phase_dictionary": phase_dict.to_dict(orient="records"),
        "missingness_rule": "circadian_disruption_score is set to 0.0 when day/night summaries are unavailable.",
    }
    (SOFTWARE / "phase_map" / "assets" / "phase_reference.json").write_text(json.dumps(ref, ensure_ascii=False, indent=2), encoding="utf-8")

    core = r'''
from __future__ import annotations

import json
from importlib.resources import files

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
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


def load_reference() -> dict:
    path = files("phase_map.assets").joinpath("phase_reference.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _z(series: pd.Series, ref: dict, name: str) -> pd.Series:
    mean = ref["feature_reference"][name]["mean"]
    sd = ref["feature_reference"][name]["sd"]
    if not sd:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (pd.to_numeric(series, errors="coerce") - mean) / sd


def assign_phase(input_frame: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in input_frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    ref = load_reference()
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
    distances = []
    for _, row in centroids.iterrows():
        c = row[ORDER_COLS].to_numpy(float)
        distances.append(np.sqrt(((x - c) ** 2).sum(axis=1)))
    dist = np.vstack(distances).T
    nearest = dist.argmin(axis=1)
    out["phase_label"] = [centroids.iloc[i]["phase_label"] for i in nearest]
    out["phase_assignment_distance"] = dist.min(axis=1)
    phase_dictionary = pd.DataFrame(ref["phase_dictionary"])
    phase_id = dict(zip(phase_dictionary["phase_label_zh"], phase_dictionary["phase_id"]))
    phase_en = dict(zip(phase_dictionary["phase_label_zh"], phase_dictionary["phase_label_en"]))
    out["phase_id"] = out["phase_label"].map(phase_id)
    out["phase_label_en"] = out["phase_label"].map(phase_en)
    return out
'''
    write(SOFTWARE / "phase_map" / "core.py", core)
    write(SOFTWARE / "phase_map" / "__init__.py", 'from .core import REQUIRED_COLUMNS, assign_phase, load_reference\n\n__all__ = ["REQUIRED_COLUMNS", "assign_phase", "load_reference"]')
    write(SOFTWARE / "phase_map" / "assets" / "__init__.py", "")

    input_schema = read_csv(P0 / "tables" / "phase_map_input_schema.csv")
    output_schema = read_csv(P0 / "tables" / "phase_map_output_schema.csv")
    input_schema.to_csv(SOFTWARE / "schemas" / "phase_map_input_schema.csv", index=False)
    output_schema.to_csv(SOFTWARE / "schemas" / "phase_map_output_schema.csv", index=False)

    toy_rows = []
    for label, group in train_ref.groupby("phase_label"):
        centroid = train_ref.groupby("phase_label")[ORDER_COLS].mean().loc[label]
        d = ((group[ORDER_COLS] - centroid) ** 2).sum(axis=1)
        row = group.loc[d.idxmin()].copy()
        toy_rows.append(row)
    toy = pd.DataFrame(toy_rows).reset_index(drop=True)
    toy_input_cols = ["participant_id"] + [
        "cgm_mean_glucose_mg_dl",
        "cgm_time_in_range_70_180_pct",
        "cgm_time_below_70_pct",
        "cgm_time_below_54_pct",
        "cgm_time_above_180_pct",
        "cgm_time_above_250_pct",
        "cgm_cv_pct",
    ]
    toy[toy_input_cols].to_csv(SOFTWARE / "toy_data" / "toy_input.csv", index=False)
    expected = add_phase_assignment(toy[toy_input_cols].copy(), train_phase)
    expected[["participant_id", "phase_id", "phase_label_en"]].to_csv(SOFTWARE / "toy_data" / "toy_output_expected.csv", index=False)

    test_code = r'''
from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from phase_map import assign_phase


class PhaseMapPackageTest(unittest.TestCase):
    def test_toy_phase_assignments_match_expected(self):
        toy = pd.read_csv(ROOT / "toy_data" / "toy_input.csv")
        expected = pd.read_csv(ROOT / "toy_data" / "toy_output_expected.csv")
        observed = assign_phase(toy)
        merged = observed[["participant_id", "phase_id"]].merge(expected[["participant_id", "phase_id"]], on="participant_id", suffixes=("_observed", "_expected"))
        self.assertGreaterEqual(len(merged), 5)
        self.assertTrue((merged["phase_id_observed"] == merged["phase_id_expected"]).all())

    def test_missing_required_column_raises(self):
        toy = pd.read_csv(ROOT / "toy_data" / "toy_input.csv").drop(columns=["cgm_cv_pct"])
        with self.assertRaises(ValueError):
            assign_phase(toy)


if __name__ == "__main__":
    unittest.main()
'''
    write(SOFTWARE / "tests" / "test_phase_map_package.py", test_code)
    write(SOFTWARE / "requirements.txt", "numpy\npandas\n")
    write(
        SOFTWARE / "environment.yml",
        """
name: phase-map-jaeb-v0-1
channels:
  - conda-forge
dependencies:
  - python>=3.10
  - numpy
  - pandas
""",
    )
    write(SOFTWARE / "VERSION", "phase-map-jaeb-summary-v0.1")
    write(
        SOFTWARE / "README.md",
        """
# Phase-map JAEB summary v0.1

Research software bundle for assigning a CGM summary window to a locked JAEB
glycaemic phase-map digital phenotype.

## Intended use

This package is for retrospective research, reproducibility checks, and
silent-mode workflow evaluation. It is not a standalone clinical decision
system and must not autonomously change therapy.

## Quick start

```python
import pandas as pd
from phase_map import assign_phase

df = pd.read_csv("toy_data/toy_input.csv")
assigned = assign_phase(df)
print(assigned[["participant_id", "phase_id", "phase_label_en"]])
```

## Test

```bash
python -m unittest discover -s tests
```

## Contents

- `phase_map/`: minimal assignment package.
- `schemas/`: input and output schemas.
- `toy_data/`: toy input and expected output fixtures.
- `scripts/reproduce_figures.py`: helper to rerun manuscript figure scripts from the repository root.
- `environment.yml` and `requirements.txt`: lightweight environment locks.
""",
    )
    reproduce = r'''
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=r"D:\ai for science")
    args = parser.parse_args()
    root = Path(args.repo_root)
    subprocess.run([sys.executable, str(root / "scripts" / "run_npj_digital_medicine_p0_workup.py")], check=True, cwd=root)
    subprocess.run([sys.executable, str(root / "scripts" / "run_npj_digital_medicine_p0_extensions.py")], check=True, cwd=root)


if __name__ == "__main__":
    main()
'''
    write(SOFTWARE / "scripts" / "reproduce_figures.py", reproduce)

    manifest_rows = []
    for path in sorted(SOFTWARE.rglob("*")):
        if path.is_file():
            manifest_rows.append({"relative_path": str(path.relative_to(SOFTWARE)), "bytes": path.stat().st_size})
    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(SOFTWARE / "software_release_manifest.csv", index=False)
    return manifest


def write_report(
    compat: pd.DataFrame,
    external_metrics: pd.DataFrame,
    calibration_metrics: pd.DataFrame,
    recalibration: pd.DataFrame,
    fairness_ci: pd.DataFrame,
    software_manifest: pd.DataFrame,
) -> None:
    evaluable = external_metrics[external_metrics["status"].eq("evaluable")].copy()
    fair_focus = (
        fairness_ci[fairness_ci["subgroup_variable"].ne("overall")]
        .dropna(subset=["delta_auroc_vs_overall"])
        .assign(abs_delta=lambda x: x["delta_auroc_vs_overall"].abs())
        .sort_values("abs_delta", ascending=False)
        .head(10)
    )
    report = f"""
# npj Digital Medicine P0 Extension Completion Report

## Completed items

1. External data compatibility matrix across GLAM, RacialDifferences, SevereHypo, CGMND, CGMNDYoungChildren and PSO1/3/4.
2. Additional frozen validation using eligible secondary datasets, without retraining or tuning on those datasets.
3. Loop and LOSO calibration upgrade with calibration bins, slope/intercept, ECE and Brier decomposition.
4. Prespecified TIR intercept/slope recalibration sensitivity.
5. Subgroup fairness and transportability uncertainty with bootstrap confidence intervals and minimum-n reporting rules.
6. Versioned phase-map research software release bundle with schema, toy data, tests and environment files.

## Compatibility summary

{compat[["dataset", "n_with_cgm", "n_baseline_hba1c", "n_followup_hba1c", "followup_tir_possible", "validation_decision", "reason"]].to_string(index=False)}

## Additional frozen validation

{evaluable[["validation_dataset", "target", "feature_set", "test_n", "positive_rate", "auroc", "auprc", "brier", "expected_calibration_error"]].to_string(index=False) if not evaluable.empty else "No secondary validation target was evaluable."}

Interpretation: RacialDifferences and PSO3/4 are transportability/sensitivity validations. They are not used for tuning. RacialDifferences is observational and PSO datasets have smaller sample sizes than Loop, so these are secondary evidence rather than a replacement for Loop.

## Calibration upgrade

{calibration_metrics[["prediction_source", "target", "feature_set", "model", "n", "auroc", "brier", "calibration_slope", "calibration_intercept", "expected_calibration_error", "brier_reliability", "brier_resolution", "brier_uncertainty"]].to_string(index=False)}

## TIR recalibration sensitivity

{recalibration.to_string(index=False)}

Interpretation: recalibration rows are apparent sensitivity analyses, not new frozen models. If recalibrated ECE improves materially but raw ECE remains high, the manuscript should present absolute-risk displays cautiously and emphasize phenotype/ranking use.

## Fairness uncertainty highlights

{fair_focus[["target", "feature_set", "model", "subgroup_variable", "subgroup_display", "n", "auroc", "auroc_ci_low", "auroc_ci_high", "expected_calibration_error", "ece_ci_low", "ece_ci_high", "minimum_n_rule"]].to_string(index=False)}

Minimum-n rule:

- primary_interpretation: n >= 100 and at least 20 events/non-events.
- descriptive_only: n >= 50 and at least 10 events/non-events.
- small_n_no_strong_conclusion: otherwise.

## Software release

Software bundle: `{SOFTWARE}`

Files: {len(software_manifest)} release files. Test command:

`python -m unittest discover -s tests`
"""
    write(DOCS / "npj_p0_extension_completion_report.md", report)


def main() -> None:
    train_phase = read_csv(PHASE / "tables" / "locked_glycemic_phase_features.csv")
    ml_phase = p0.build_training_ml_phase()

    compat = compatibility_matrix()
    compat.to_csv(TABLES / "jaeb_public_extra_compatibility_matrix.csv", index=False)

    external_data, external_metrics, external_preds = build_additional_external_validation(train_phase, ml_phase)
    external_data.to_csv(TABLES / "secondary_external_validation_datasets.csv", index=False)
    external_metrics.to_csv(TABLES / "secondary_external_validation_metrics.csv", index=False)
    external_preds.to_csv(TABLES / "secondary_external_validation_predictions.csv", index=False)

    calibration_metrics, calibration_bin_table, recalibration = calibration_upgrade(ml_phase)
    calibration_metrics.to_csv(TABLES / "loop_loso_calibration_upgrade_metrics.csv", index=False)
    calibration_bin_table.to_csv(FIGSRC / "loop_loso_calibration_curve_bins.csv", index=False)
    recalibration.to_csv(TABLES / "tir_recalibration_sensitivity.csv", index=False)
    plot_calibration(calibration_metrics, calibration_bin_table)

    fairness_ci, phase_dist = subgroup_uncertainty_audit()
    fairness_ci.to_csv(TABLES / "subgroup_fairness_calibration_audit_with_bootstrap_ci.csv", index=False)
    phase_dist.to_csv(TABLES / "subgroup_phase_distribution_audit.csv", index=False)

    software_manifest = build_software_release(train_phase)

    status = pd.DataFrame(
        [
            ("compatibility_matrix", "complete", "tables/jaeb_public_extra_compatibility_matrix.csv"),
            ("secondary_frozen_validation", "complete", "tables/secondary_external_validation_metrics.csv"),
            ("calibration_upgrade", "complete", "tables/loop_loso_calibration_upgrade_metrics.csv"),
            ("tir_recalibration_sensitivity", "complete", "tables/tir_recalibration_sensitivity.csv"),
            ("subgroup_uncertainty_ci", "complete", "tables/subgroup_fairness_calibration_audit_with_bootstrap_ci.csv"),
            ("software_release", "complete", "software_release/phase_map_jaeb_v0_1"),
        ],
        columns=["deliverable", "status", "primary_output"],
    )
    status.to_csv(OUT / "npj_p0_extension_status.csv", index=False)

    manifest = {
        "created": "2026-06-18",
        "objective": "P0 extension workup for npj Digital Medicine submission readiness",
        "outputs": status.to_dict(orient="records"),
    }
    (OUT / "npj_p0_extension_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(compat, external_metrics, calibration_metrics, recalibration, fairness_ci, software_manifest)
    print(f"wrote npj Digital Medicine P0 extension workup to {OUT}")


if __name__ == "__main__":
    main()
