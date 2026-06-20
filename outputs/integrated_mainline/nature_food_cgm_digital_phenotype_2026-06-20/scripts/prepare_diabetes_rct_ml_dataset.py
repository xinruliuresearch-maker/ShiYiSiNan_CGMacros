"""Prepare public diabetes RCT/intervention datasets for ML modeling.

The script downloads (optional) and cleans openly downloadable JAEB public
datasets into a participant-level modeling table. It also writes a source
inventory, data dictionary, and cleaning report.

Usage:
    python scripts/prepare_diabetes_rct_ml_dataset.py
    python scripts/prepare_diabetes_rct_ml_dataset.py --download
"""

from __future__ import annotations

import argparse
import io
import math
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from pandas.api.types import is_object_dtype, is_string_dtype


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "jaeb_public"
INTERIM_DIR = ROOT / "data" / "interim"
PROCESSED_DIR = ROOT / "data" / "processed"
DOCS_DIR = ROOT / "docs"

JAEB_PORTAL = "https://public.jaeb.org/datasets/diabetes"


@dataclass(frozen=True)
class PublicDataset:
    study_id: str
    dataset_name: str
    nct_id: str
    zip_filename: str
    dataset_url: str
    study_population: str
    intervention_type: str
    primary_outcome: str
    primary_followup: str
    source_tables: str
    direct_download: bool = True
    license_or_limit: str = "Public JAEB dataset; de-identified research use; cite source and protocol."


PUBLIC_DATASETS: list[PublicDataset] = [
    PublicDataset(
        study_id="WISDM",
        dataset_name="Wireless Innovation for Seniors with Diabetes Mellitus (WISDM)",
        nct_id="NCT03240432",
        zip_filename="WISDMPublicDataset.zip",
        dataset_url=(
            "https://live-jchrpublicdatasets.s3.amazonaws.com/Diabetes/Public Datasets/"
            "WISDMPublicDataset-18f24ae5-b4fb-4e93-bec6-7021086419fa.zip"
        ),
        study_population="Adults age >=60 years with type 1 diabetes.",
        intervention_type="CGM vs blood glucose meter usual care.",
        primary_outcome="Time spent with glucose <70 mg/dL at 26 weeks.",
        primary_followup="26 week",
        source_tables=(
            "PtRoster, DiabScreening, DiabPhysExam, STASampleResults, "
            "DiabLocalHbA1c, gluIndices RCT"
        ),
    ),
    PublicDataset(
        study_id="CITY",
        dataset_name="CGM Intervention in Teens and Young Adults with T1D (CITY)",
        nct_id="NCT03263494",
        zip_filename="CITYPublicDataset.zip",
        dataset_url=(
            "https://live-jchrpublicdatasets.s3.amazonaws.com/Diabetes/Public Datasets/"
            "CITYPublicDataset-344bea7d-8085-4deb-8038-6cb747a744e3.zip"
        ),
        study_population="Adolescents and young adults with type 1 diabetes.",
        intervention_type="CGM vs blood glucose meter usual care.",
        primary_outcome="Change in HbA1c from baseline to 26 weeks.",
        primary_followup="26 week visit",
        source_tables=(
            "PtRoster, DiabScreening, DiabPhysExam, vwCITY_STASampleResults, "
            "DiabLocalHbA1c, gluIndices RCT"
        ),
    ),
    PublicDataset(
        study_id="SENCE",
        dataset_name="Strategies to Enhance New CGM Use in Early Childhood (SENCE)",
        nct_id="NCT02912728",
        zip_filename="SENCEPublicDataset.zip",
        dataset_url=(
            "https://live-jchrpublicdatasets.s3.amazonaws.com/Diabetes/Public Datasets/"
            "SENCEPublicDataset-ed021673-573d-436c-9b15-49dbad67bd35.zip"
        ),
        study_population="Children younger than 8 years with type 1 diabetes.",
        intervention_type="Standard CGM or CGM plus family behavioral intervention vs BGM.",
        primary_outcome="Time in glucose range 70-180 mg/dL through 26 weeks.",
        primary_followup="26 week",
        source_tables=(
            "PtRoster, DiabScreening, DiabPhysExam, STASampleResults, "
            "DiabLocalHbA1c, gluIndices RCT"
        ),
    ),
    PublicDataset(
        study_id="REPLACE_BG",
        dataset_name="REPLACE-BG: CGM with and without routine BGM in adults with T1D",
        nct_id="NCT02258373",
        zip_filename="Replace-BG Dataset.zip",
        dataset_url="https://live-jchrpublicdatasets.s3.amazonaws.com/Diabetes/Public Datasets/Replace-BG Dataset.zip",
        study_population="Adults with type 1 diabetes using CGM.",
        intervention_type="CGM-only management vs CGM plus routine BGM.",
        primary_outcome="Percentage of time in range 70-180 mg/dL over 6 months.",
        primary_followup="Week 26 Visit",
        source_tables="HPtRoster, HScreening, HLocalHbA1c, HVisitInfo, HFollowUp",
    ),
    PublicDataset(
        study_id="FLAIR",
        dataset_name="Fuzzy Logic Automated Insulin Regulation (FLAIR)",
        nct_id="NCT03040414",
        zip_filename="FLAIRPublicDataSet.zip",
        dataset_url="https://live-jchrpublicdatasets.s3.amazonaws.com/Diabetes/Public Datasets/FLAIRPublicDataSet.zip",
        study_population="Individuals with type 1 diabetes in a crossover AID algorithm trial.",
        intervention_type="PID + fuzzy logic AHCL algorithm vs PID/670G comparator.",
        primary_outcome="Daytime time >180 mg/dL and non-inferiority for time <54 mg/dL.",
        primary_followup="End of Study",
        source_tables="PtRoster, FLAIRDiabScreening, FLAIRDiabPhysExam, STASampleResults, FLAIRDiabLocalHbA1c",
    ),
    PublicDataset(
        study_id="METFORMIN_T1D",
        dataset_name="Metformin adjunct therapy for overweight adolescents with type 1 diabetes",
        nct_id="NCT01881828",
        zip_filename="MetforminDataset_2024-02-22.zip",
        dataset_url=(
            "https://live-jchrpublicdatasets.s3.amazonaws.com/Diabetes/Public Datasets/"
            "MetforminDataset_2024-02-22.zip"
        ),
        study_population="Overweight adolescents with type 1 diabetes.",
        intervention_type="Metformin vs oral placebo adjunct to insulin.",
        primary_outcome="Change in HbA1c from baseline to 26 weeks.",
        primary_followup="26 Week",
        source_tables="CScreening, CRandomization, CTrtGroupUnmasked, SampleResults, CLabHbA1c, CFollowUpVisit",
    ),
    PublicDataset(
        study_id="PEDAP",
        dataset_name="Pediatric Artificial Pancreas Trial of Control-IQ in Young Children with T1D",
        nct_id="NCT04796779",
        zip_filename="PEDAP Public Dataset - Release 5 - 2025-05-12.zip",
        dataset_url=(
            "https://live-jchrpublicdatasets.s3.amazonaws.com/Diabetes/Public Datasets/"
            "PEDAP Public Dataset - Release 5 - 2025-05-12.zip"
        ),
        study_population="Young children with type 1 diabetes.",
        intervention_type="Control-IQ closed-loop technology vs standard care.",
        primary_outcome="CGM and HbA1c outcomes through the primary 13-week period.",
        primary_followup="13 Week",
        source_tables="PtRoster, PEDAPDiabScreening, PEDAPDiabPhysExam, STASampleResults, PEDAPFollowUpCTV",
    ),
    PublicDataset(
        study_id="AIDE_T1D",
        dataset_name="Automated Insulin Delivery in Elderly with Type 1 Diabetes (AIDE T1D)",
        nct_id="NCT04016662",
        zip_filename="AIDET1D_Public_Dataset.zip",
        dataset_url="https://live-jchrpublicdatasets.s3.amazonaws.com/Diabetes/Public Datasets/AIDET1D_Public_Dataset.zip",
        study_population="Older adults with type 1 diabetes.",
        intervention_type="Crossover sequence of HCL, PLGS, and SAP automated/digital insulin delivery modes.",
        primary_outcome="CGM glycemic outcomes and HbA1c across treatment periods.",
        primary_followup="End of P3 Visit",
        source_tables="PtRoster, AIDEDiabScreening, AIDEDiabPhysExam, STASampleResults, gluIndices",
    ),
    PublicDataset(
        study_id="CLVER",
        dataset_name="Hybrid Closed Loop Therapy and Verapamil for Beta Cell Preservation in New Onset T1D",
        nct_id="NCT04233034",
        zip_filename="CLVerPublicDataset.zip",
        dataset_url="https://live-jchrpublicdatasets.s3.amazonaws.com/Diabetes/Public Datasets/CLVerPublicDataset.zip",
        study_population="Children and adolescents with new-onset type 1 diabetes.",
        intervention_type="Hybrid closed loop and verapamil/usual-care factorial treatment labels.",
        primary_outcome="Beta-cell preservation and glycemic outcomes through 52 weeks.",
        primary_followup="52 Week",
        source_tables="PtRoster, Screening, DiabPhysExam, SampleResults, VisitInfo",
    ),
    PublicDataset(
        study_id="IOBP2",
        dataset_name="Insulin-Only Bionic Pancreas Pivotal Trial",
        nct_id="NCT04200313",
        zip_filename="IOBP2 RCT Public Dataset.zip",
        dataset_url="https://live-jchrpublicdatasets.s3.amazonaws.com/Diabetes/Public Datasets/IOBP2 RCT Public Dataset.zip",
        study_population="Children and adults with type 1 diabetes.",
        intervention_type="iLet bionic pancreas arms vs standard-of-care control.",
        primary_outcome="HbA1c and CGM glycemic outcomes at 13 weeks.",
        primary_followup="Week 13",
        source_tables="IOBP2PtRoster, IOBP2DiabScreening, IOBP2HeightWeight, STASampleResults, IOBP2RandBaseInfo",
    ),
    PublicDataset(
        study_id="DCLP5",
        dataset_name="Control-IQ Closed Loop System in Children with Type 1 Diabetes (DCLP5)",
        nct_id="NCT03844789",
        zip_filename="DCLP5_Dataset_2022-01-20.zip",
        dataset_url=(
            "https://live-jchrpublicdatasets.s3.amazonaws.com/Diabetes/Public Datasets/"
            "DCLP5_Dataset_2022-01-20-5e0f3b16-c890-4ace-9e3b-531f3687cf53.zip"
        ),
        study_population="Children with type 1 diabetes.",
        intervention_type="Control-IQ closed loop system pediatric study.",
        primary_outcome="HbA1c and CGM outcomes through 16 weeks.",
        primary_followup="16 Week",
        source_tables="PtRoster, DiabScreening, DiabPhysExam, SampleResults, DiabLocalHbA1c",
    ),
    PublicDataset(
        study_id="DCLP3",
        dataset_name="International Diabetes Closed Loop Trial (DCLP3 / iDCL Control-IQ)",
        nct_id="NCT03563313",
        zip_filename="DCLP3 Public Dataset - Release 3 - 2022-08-04.zip",
        dataset_url=(
            "https://live-jchrpublicdatasets.s3.amazonaws.com/Diabetes/Public Datasets/"
            "DCLP3 Public Dataset - Release 3 - 2022-08-04.zip"
        ),
        study_population="Children, adolescents, and adults with type 1 diabetes.",
        intervention_type="Control-IQ closed loop vs sensor-augmented pump.",
        primary_outcome="CGM time in range and HbA1c at 26 weeks.",
        primary_followup="26 Week",
        source_tables="PtRoster_a, DiabScreening_a, DiabPhysExam_a, SampleResults_a, gluIndices",
    ),
    PublicDataset(
        study_id="HYCLO",
        dataset_name="Hybrid Closed Loop Insulin Delivery System Data Collection (HYCLO)",
        nct_id="",
        zip_filename="HYCLOPublicDataset.zip",
        dataset_url="https://live-jchrpublicdatasets.s3.amazonaws.com/Diabetes/Public Datasets/HYCLOPublicDataset.zip",
        study_population="People with type 1 diabetes using hybrid closed-loop insulin delivery.",
        intervention_type="Observational hybrid closed-loop data collection; not randomized.",
        primary_outcome="Longitudinal HbA1c and clinical follow-up during hybrid closed-loop use.",
        primary_followup="Follow up 4",
        source_tables="PtRoster, HYCLODiabScreening, HYCLODiabPhysExam, HYCLODiabLocalHbA1c, HYCLOFollowUp",
    ),
]


INVENTORY_EXTRA_ROWS = [
    {
        "dataset_name": "ACCORD clinical trial",
        "source_link": "https://biolincc.nhlbi.nih.gov/studies/accord/",
        "study_population": "Adults with type 2 diabetes at high cardiovascular risk.",
        "intervention_type": "Intensive vs standard glycemia; BP and lipid factorial interventions.",
        "sample_size": "10,000+ participants; request platform metadata should be checked before use.",
        "primary_outcome": "Cardiovascular events; HbA1c and safety outcomes available.",
        "available_variables": "Individual participant clinical, labs, medication, outcomes.",
        "download_method": "Requires BioLINCC account, data request, and data use agreement.",
        "license_or_use_restrictions": "Restricted access; do not redistribute raw data.",
        "status": "requires_application",
    },
    {
        "dataset_name": "Diabetes Prevention Program / DPPOS",
        "source_link": "https://repository.niddk.nih.gov/study/40",
        "study_population": "Adults at high risk for type 2 diabetes.",
        "intervention_type": "Lifestyle intervention, metformin, placebo; long-term follow-up.",
        "sample_size": "3,000+ participants; request platform metadata should be checked before use.",
        "primary_outcome": "Incident diabetes, weight, glycemic measures.",
        "available_variables": "Individual participant baseline, labs, lifestyle, medication, outcomes.",
        "download_method": "Requires NIDDK Central Repository request and data use agreement.",
        "license_or_use_restrictions": "Restricted access; do not redistribute raw data.",
        "status": "requires_application",
    },
    {
        "dataset_name": "Look AHEAD",
        "source_link": "https://repository.niddk.nih.gov/studies/look-ahead/",
        "study_population": "Adults with type 2 diabetes and overweight/obesity.",
        "intervention_type": "Intensive lifestyle intervention vs diabetes support and education.",
        "sample_size": "5,000+ participants; request platform metadata should be checked before use.",
        "primary_outcome": "Cardiovascular outcomes, weight, HbA1c, fitness and safety.",
        "available_variables": "Individual participant longitudinal clinical and behavioral data.",
        "download_method": "Requires NIDDK Central Repository request and data use agreement.",
        "license_or_use_restrictions": "Restricted access; do not redistribute raw data.",
        "status": "requires_application",
    },
    {
        "dataset_name": "TODAY / TODAY2 study",
        "source_link": "https://repository.niddk.nih.gov/studies/today2/",
        "study_population": "Youth with type 2 diabetes.",
        "intervention_type": "Metformin alone, metformin plus rosiglitazone, metformin plus lifestyle.",
        "sample_size": "600+ participants; request platform metadata should be checked before use.",
        "primary_outcome": "Durable glycemic control and treatment failure.",
        "available_variables": "Individual participant clinical, labs, medications, complications.",
        "download_method": "Requires NIDDK Central Repository request and data use agreement.",
        "license_or_use_restrictions": "Restricted access; do not redistribute raw data.",
        "status": "requires_application",
    },
    {
        "dataset_name": "GRADE comparative effectiveness trial",
        "source_link": "https://repository.niddk.nih.gov/study/151",
        "study_population": "Adults with type 2 diabetes on metformin.",
        "intervention_type": "Randomized add-on glucose-lowering medications: sulfonylurea, DPP-4 inhibitor, GLP-1 receptor agonist, or insulin.",
        "sample_size": "5,000+ participants; request platform metadata should be checked before use.",
        "primary_outcome": "Time to confirmed HbA1c >=7.0% metabolic failure.",
        "available_variables": "Individual participant longitudinal clinical, medication, lab, adverse-event, and outcome data; CGM may require separate request.",
        "download_method": "Requires NIDDK Central Repository request and data use agreement.",
        "license_or_use_restrictions": "Restricted access; do not redistribute raw data.",
        "status": "requires_application",
    },
    {
        "dataset_name": "DCCT / EDIC",
        "source_link": "https://repository.niddk.nih.gov/studies/edic/",
        "study_population": "People with type 1 diabetes.",
        "intervention_type": "Intensive vs conventional diabetes therapy and long-term follow-up.",
        "sample_size": "1,000+ participants; request platform metadata should be checked before use.",
        "primary_outcome": "Microvascular complications, HbA1c, long-term outcomes.",
        "available_variables": "Individual participant longitudinal clinical and laboratory data.",
        "download_method": "Requires NIDDK Central Repository request and data use agreement.",
        "license_or_use_restrictions": "Restricted access; do not redistribute raw data.",
        "status": "requires_application",
    },
    {
        "dataset_name": "OhioT1DM dataset",
        "source_link": "https://smarthealth.cs.ohio.edu/OhioT1DM-dataset.html",
        "study_population": "People with type 1 diabetes using CGM and insulin.",
        "intervention_type": "Not an RCT; CGM/insulin/meal time-series useful as a public alternative.",
        "sample_size": "Small cohort; see data request page.",
        "primary_outcome": "CGM prediction and glucose forecasting tasks.",
        "available_variables": "CGM, insulin, meals, exercise/physiology depending on release.",
        "download_method": "Requires request/terms acceptance from dataset maintainers.",
        "license_or_use_restrictions": "Use agreement; do not redistribute without permission.",
        "status": "alternative_requires_request",
    },
    {
        "dataset_name": "D1NAMO",
        "source_link": "https://doi.org/10.1145/2836041.2836066",
        "study_population": "People with type 1 diabetes and healthy controls.",
        "intervention_type": "Not an RCT; multimodal diabetes time-series alternative.",
        "sample_size": "Small cohort; see dataset page/publication.",
        "primary_outcome": "Glucose dynamics and prediction.",
        "available_variables": "CGM, insulin, meals, activity/physiologic signals depending on subset.",
        "download_method": "Use public dataset instructions from maintainers.",
        "license_or_use_restrictions": "Check dataset license/terms before redistribution.",
        "status": "alternative_public_or_request",
    },
]


def ensure_dirs() -> None:
    for path in [RAW_DIR, INTERIM_DIR, PROCESSED_DIR, DOCS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def download_public_zips(overwrite: bool = False) -> None:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("requests is required for --download") from exc

    ensure_dirs()
    for spec in PUBLIC_DATASETS:
        target = RAW_DIR / spec.zip_filename
        if target.exists() and target.stat().st_size > 1000 and not overwrite:
            print(f"skip existing {target.name} ({target.stat().st_size:,} bytes)")
            continue
        tmp = target.with_suffix(target.suffix + ".part")
        print(f"download {spec.study_id}: {spec.dataset_url}")
        with requests.get(spec.dataset_url, stream=True, timeout=60) as response:
            response.raise_for_status()
            with open(tmp, "wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        tmp.replace(target)
        print(f"wrote {target} ({target.stat().st_size:,} bytes)")


def read_zip_table(zip_filename: str, member: str) -> pd.DataFrame:
    zip_path = RAW_DIR / zip_filename
    if not zip_path.exists():
        raise FileNotFoundError(f"Missing raw zip: {zip_path}")
    with zipfile.ZipFile(zip_path) as archive:
        raw = archive.read(member)
    encoding = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"
    frame = pd.read_csv(
        io.BytesIO(raw),
        sep="|",
        encoding=encoding,
        dtype=str,
        keep_default_na=True,
        na_values=["", " ", "NA", "N/A", "na", "n/a"],
        low_memory=False,
    )
    frame.columns = [str(col).strip() for col in frame.columns]
    return frame


def first_existing(df: pd.DataFrame, names: Iterable[str]) -> str | None:
    lookup = {col.lower(): col for col in df.columns}
    for name in names:
        found = lookup.get(name.lower())
        if found is not None:
            return found
    return None


def to_numeric(series: pd.Series | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype="float64")
    cleaned = (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("<", "", regex=False)
        .str.strip()
    )
    cleaned = cleaned.mask(cleaned.isin(["", "nan", "None"]), np.nan)
    return pd.to_numeric(cleaned, errors="coerce")


def normalize_text(value: object) -> str | float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    if not text:
        return np.nan
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_category(value: object) -> str:
    text = normalize_text(value)
    if pd.isna(text):
        return "missing_or_unknown"
    lowered = str(text).strip().lower()
    replacements = {
        "m": "male",
        "f": "female",
        "unknown/not reported": "missing_or_unknown",
        "unknown": "missing_or_unknown",
        "not reported": "missing_or_unknown",
        "nan": "missing_or_unknown",
    }
    return replacements.get(lowered, lowered.replace(" ", "_").replace("/", "_"))


def normalize_visit(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def match_visit(series: pd.Series, terms: Iterable[str]) -> pd.Series:
    normalized_terms = [normalize_visit(term) for term in terms]
    norm = series.map(normalize_visit)
    mask = pd.Series(False, index=series.index)
    for term in normalized_terms:
        mask = mask | norm.str.contains(re.escape(term), na=False)
    return mask


def participant_key(study_id: str, ptid: object) -> str:
    return f"{study_id}_{str(ptid).strip()}"


def convert_weight_to_kg(weight: pd.Series, units: pd.Series | None = None, assume_metric: bool = True) -> pd.Series:
    val = to_numeric(weight)
    if units is None:
        return val.where(~((val > 250) & assume_metric), val * 0.45359237)
    unit = units.fillna("").astype(str).str.lower()
    out = val.copy()
    out = out.where(~unit.str.contains("lb"), val * 0.45359237)
    if assume_metric:
        out = out.where(~((unit == "") & (val > 250)), val * 0.45359237)
    return out


def convert_height_to_cm(height: pd.Series, units: pd.Series | None = None, assume_metric: bool = True) -> pd.Series:
    val = to_numeric(height)
    if units is None:
        return val.where(~((val < 100) & assume_metric), val * 2.54)
    unit = units.fillna("").astype(str).str.lower()
    out = val.copy()
    out = out.where(~unit.str.contains(r"\bin\b|inch"), val * 2.54)
    if assume_metric:
        out = out.where(~((unit == "") & (val < 100)), val * 2.54)
    return out


def add_bmi(df: pd.DataFrame, weight_col: str, height_col: str, out_col: str) -> None:
    height_m = df[height_col] / 100.0
    df[out_col] = df[weight_col] / (height_m**2)
    df.loc[(df[out_col] < 8) | (df[out_col] > 80), out_col] = np.nan


def one_row_per_pt(df: pd.DataFrame, pt_col: str = "PtID") -> pd.DataFrame:
    return df.dropna(subset=[pt_col]).drop_duplicates(subset=[pt_col], keep="first").copy()


def extract_measure_by_visit(
    df: pd.DataFrame,
    value_col: str,
    visit_terms: Iterable[str],
    out_col: str,
    result_filter: tuple[str, str] | None = None,
) -> pd.DataFrame:
    if df.empty or value_col not in df.columns or "PtID" not in df.columns or "Visit" not in df.columns:
        return pd.DataFrame(columns=["PtID", out_col])
    work = df.copy()
    if result_filter is not None:
        col, wanted = result_filter
        if col not in work.columns:
            return pd.DataFrame(columns=["PtID", out_col])
        work = work[work[col].astype(str).str.lower() == wanted.lower()]
    work = work[match_visit(work["Visit"], visit_terms)].copy()
    if work.empty:
        return pd.DataFrame(columns=["PtID", out_col])
    work[out_col] = to_numeric(work[value_col])
    return work.groupby("PtID", as_index=False)[out_col].mean()


def extract_physical_exam(
    df: pd.DataFrame,
    visit_terms: Iterable[str] | None,
    prefix: str,
    assume_metric: bool = True,
) -> pd.DataFrame:
    if df.empty or "PtID" not in df.columns:
        return pd.DataFrame(columns=["PtID", f"{prefix}_weight_kg", f"{prefix}_height_cm", f"{prefix}_bmi"])
    work = df.copy()
    if visit_terms is not None and "Visit" in work.columns:
        work = work[match_visit(work["Visit"], visit_terms)].copy()
    if work.empty:
        return pd.DataFrame(columns=["PtID", f"{prefix}_weight_kg", f"{prefix}_height_cm", f"{prefix}_bmi"])
    work = one_row_per_pt(work)
    weight_col = first_existing(work, ["Weight"])
    height_col = first_existing(work, ["Height"])
    weight_units_col = first_existing(work, ["WeightUnits"])
    height_units_col = first_existing(work, ["HeightUnits"])
    out = work[["PtID"]].copy()
    if weight_col:
        out[f"{prefix}_weight_kg"] = convert_weight_to_kg(
            work[weight_col], work[weight_units_col] if weight_units_col else None, assume_metric=assume_metric
        )
    else:
        out[f"{prefix}_weight_kg"] = np.nan
    if height_col:
        out[f"{prefix}_height_cm"] = convert_height_to_cm(
            work[height_col], work[height_units_col] if height_units_col else None, assume_metric=assume_metric
        )
    else:
        out[f"{prefix}_height_cm"] = np.nan
    add_bmi(out, f"{prefix}_weight_kg", f"{prefix}_height_cm", f"{prefix}_bmi")
    return out


def extract_cgm_summary(zip_filename: str, member: str) -> pd.DataFrame:
    df = read_zip_table(zip_filename, member)
    if df.empty:
        return pd.DataFrame()
    df = df[df["time"].map(normalize_visit).eq("1 overall")].copy()
    if df.empty:
        return pd.DataFrame()
    metrics = {
        "gluMean": "cgm_mean_glucose_mg_dl",
        "gluInRange": "cgm_time_in_range_70_180_pct",
        "gluBelow70": "cgm_time_below_70_pct",
        "gluBelow54": "cgm_time_below_54_pct",
        "gluAbove180": "cgm_time_above_180_pct",
        "gluAbove250": "cgm_time_above_250_pct",
        "gluHours": "cgm_hours",
        "gluCV": "cgm_cv_pct",
    }
    for col in metrics:
        if col not in df.columns:
            df[col] = np.nan
    baseline = df[df["period"].map(normalize_visit).str.contains("baseline", na=False)].copy()
    followup = df[df["period"].map(normalize_visit).str.contains("follow up", na=False)].copy()
    base_out = baseline[["PtID"]].drop_duplicates().copy()
    follow_out = followup[["PtID"]].drop_duplicates().copy()
    for source_col, clean_col in metrics.items():
        base_vals = baseline.assign(_v=to_numeric(baseline[source_col])).groupby("PtID", as_index=False)["_v"].mean()
        follow_vals = followup.assign(_v=to_numeric(followup[source_col])).groupby("PtID", as_index=False)["_v"].mean()
        base_vals = base_vals.rename(columns={"_v": f"x_baseline_{clean_col}"})
        follow_vals = follow_vals.rename(columns={"_v": f"y_followup_{clean_col}"})
        base_out = base_out.merge(base_vals, on="PtID", how="left")
        follow_out = follow_out.merge(follow_vals, on="PtID", how="left")
    out = base_out.merge(follow_out, on="PtID", how="outer")
    for clean_col in metrics.values():
        b = f"x_baseline_{clean_col}"
        f = f"y_followup_{clean_col}"
        if b in out.columns and f in out.columns:
            out[f"y_change_{clean_col}"] = out[f] - out[b]
    return out


def extract_cgm_summary_config(
    zip_filename: str,
    member: str,
    *,
    period_col: str,
    baseline_terms: Iterable[str],
    followup_terms: Iterable[str] | None = None,
    time_col: str | None = None,
    overall_terms: Iterable[str] | None = None,
    analysis_col: str | None = None,
    analysis_terms: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Extract baseline/follow-up CGM summaries from non-standard JAEB tables."""
    df = read_zip_table(zip_filename, member)
    if df.empty or "PtID" not in df.columns:
        return pd.DataFrame()
    work = df.copy()
    if time_col and time_col in work.columns and overall_terms:
        time_norm = work[time_col].map(normalize_visit)
        mask = pd.Series(False, index=work.index)
        for term in overall_terms:
            mask = mask | time_norm.str.contains(re.escape(normalize_visit(term)), na=False)
        work = work[mask].copy()
    if analysis_col and analysis_col in work.columns and analysis_terms:
        analysis_norm = work[analysis_col].map(normalize_visit)
        mask = pd.Series(False, index=work.index)
        for term in analysis_terms:
            mask = mask | analysis_norm.str.contains(re.escape(normalize_visit(term)), na=False)
        work = work[mask].copy()
    if work.empty or period_col not in work.columns:
        return pd.DataFrame()

    metrics = {
        "gluMean": "cgm_mean_glucose_mg_dl",
        "gluInRange": "cgm_time_in_range_70_180_pct",
        "gluBelow70": "cgm_time_below_70_pct",
        "gluBelow54": "cgm_time_below_54_pct",
        "gluAbove180": "cgm_time_above_180_pct",
        "gluAbove250": "cgm_time_above_250_pct",
        "gluHours": "cgm_hours",
        "gluCV": "cgm_cv_pct",
    }
    for col in metrics:
        if col not in work.columns:
            work[col] = np.nan

    period_norm = work[period_col].map(normalize_visit)
    base_mask = pd.Series(False, index=work.index)
    for term in baseline_terms:
        base_mask = base_mask | period_norm.str.contains(re.escape(normalize_visit(term)), na=False)
    baseline = work[base_mask].copy()

    followup = pd.DataFrame()
    if followup_terms is not None:
        follow_mask = pd.Series(False, index=work.index)
        for term in followup_terms:
            follow_mask = follow_mask | period_norm.str.contains(re.escape(normalize_visit(term)), na=False)
        followup = work[follow_mask].copy()

    out = baseline[["PtID"]].drop_duplicates().copy()
    for source_col, clean_col in metrics.items():
        base_vals = baseline.assign(_v=to_numeric(baseline[source_col])).groupby("PtID", as_index=False)["_v"].mean()
        base_vals = base_vals.rename(columns={"_v": f"x_baseline_{clean_col}"})
        out = out.merge(base_vals, on="PtID", how="left")
    if not followup.empty:
        follow_out = followup[["PtID"]].drop_duplicates().copy()
        for source_col, clean_col in metrics.items():
            follow_vals = followup.assign(_v=to_numeric(followup[source_col])).groupby("PtID", as_index=False)["_v"].mean()
            follow_vals = follow_vals.rename(columns={"_v": f"y_followup_{clean_col}"})
            follow_out = follow_out.merge(follow_vals, on="PtID", how="left")
        out = out.merge(follow_out, on="PtID", how="outer")
        for clean_col in metrics.values():
            b = f"x_baseline_{clean_col}"
            f = f"y_followup_{clean_col}"
            if b in out.columns and f in out.columns:
                out[f"y_change_{clean_col}"] = out[f] - out[b]
    return out


def merge_left(base: pd.DataFrame, addon: pd.DataFrame) -> pd.DataFrame:
    if addon.empty:
        return base
    return base.merge(addon, on="PtID", how="left")


def build_common_roster(spec: PublicDataset, roster: pd.DataFrame, default_arm: str | None = None) -> pd.DataFrame:
    pt_col = first_existing(roster, ["PtID", "PtId"])
    if pt_col is None:
        raise ValueError(f"{spec.study_id}: no PtID-like column in roster")
    roster = roster.rename(columns={pt_col: "PtID"}).copy()
    age_col = first_existing(roster, ["AgeAsOfEnrollDt", "AgeAsofEnrollDt", "AgeAtEnrollment", "AgeAtEnroll", "ageRand"])
    arm_col = first_existing(roster, ["TrtGroup", "trtGroup", "TreatmentGroup"])
    site_col = first_existing(roster, ["SiteID", "SiteOrig"])
    out = roster[["PtID"]].copy()
    out["study_id"] = spec.study_id
    out["dataset_name"] = spec.dataset_name
    out["nct_id"] = spec.nct_id
    out["participant_id"] = out["PtID"].map(lambda x: participant_key(spec.study_id, x))
    out["participant_source_id"] = out["PtID"].astype(str)
    out["source_link"] = spec.dataset_url
    out["x_age_years"] = to_numeric(roster[age_col]) if age_col else np.nan
    out["x_site_id"] = roster[site_col].astype(str) if site_col else "missing_or_unknown"
    if arm_col:
        out["randomized_arm_original"] = roster[arm_col].map(normalize_text)
    elif default_arm is not None:
        out["randomized_arm_original"] = default_arm
    else:
        out["randomized_arm_original"] = np.nan
    out = out[~out["randomized_arm_original"].isna()].copy()
    out["x_randomized_arm"] = out["randomized_arm_original"].map(normalize_category)
    out["x_intervention_type"] = spec.intervention_type
    return out


def add_screening_features(base: pd.DataFrame, screening: pd.DataFrame) -> pd.DataFrame:
    if screening.empty:
        return base
    pt_col = first_existing(screening, ["PtID", "PtId"])
    if pt_col != "PtID":
        screening = screening.rename(columns={pt_col: "PtID"}).copy()
    screening = one_row_per_pt(screening)
    cols = ["PtID"]
    features = {}
    for out_col, candidates in {
        "x_sex": ["Sex", "Gender"],
        "x_ethnicity": ["Ethnicity"],
        "x_race": ["Race"],
        "x_insulin_delivery_method": ["InsDeliveryMethod"],
        "x_current_cgm_use": ["CurrUseCGM"],
    }.items():
        col = first_existing(screening, candidates)
        if col:
            features[out_col] = screening[col].map(normalize_category)
    for out_col, candidates in {
        "x_diabetes_diagnosis_age_years": ["DiagAge", "DiagT1DAge"],
        "x_units_insulin_total_baseline": ["UnitsInsTotal"],
        "x_bgm_checks_per_day_baseline": ["BGTestAvgNumMeter", "Fingerstick7DayAve", "NumFingReadLast7Days"],
        "x_current_cgm_days_per_week": ["CurrUseCGMAvgDaysWk"],
    }.items():
        col = first_existing(screening, candidates)
        if col:
            features[out_col] = to_numeric(screening[col])
    out = pd.DataFrame({"PtID": screening["PtID"]})
    for col, values in features.items():
        out[col] = values.values
    age_col = first_existing(screening, ["AgeAtEnrollment", "AgeAtEnroll", "AgeAsOfEnrollDt", "AgeAsofEnrollDt"])
    if age_col:
        out["x_age_years_from_screening"] = to_numeric(screening[age_col]).values
    merged = merge_left(base, out)
    if "x_age_years_from_screening" in merged.columns:
        age_current = to_numeric(merged["x_age_years"])
        age_screening = to_numeric(merged["x_age_years_from_screening"])
        merged["x_age_years"] = age_current.where(age_current.notna(), age_screening)
        merged = merged.drop(columns=["x_age_years_from_screening"])
    if "x_diabetes_diagnosis_age_years" in merged.columns:
        merged["x_diabetes_duration_years"] = merged["x_age_years"] - merged["x_diabetes_diagnosis_age_years"]
        merged.loc[
            (merged["x_diabetes_duration_years"] < 0) | (merged["x_diabetes_duration_years"] > 100),
            "x_diabetes_duration_years",
        ] = np.nan
    return merged


def build_wisdm_city_sence(spec: PublicDataset) -> pd.DataFrame:
    roster = read_zip_table(spec.zip_filename, "Data Tables/PtRoster.txt")
    screening = read_zip_table(spec.zip_filename, "Data Tables/DiabScreening.txt")
    phys = read_zip_table(spec.zip_filename, "Data Tables/DiabPhysExam.txt")
    sample_member = "Data Tables/vwCITY_STASampleResults.txt" if spec.study_id == "CITY" else "Data Tables/STASampleResults.txt"
    sample = read_zip_table(spec.zip_filename, sample_member)
    local_hba1c = read_zip_table(spec.zip_filename, "Data Tables/DiabLocalHbA1c.txt")
    base = build_common_roster(spec, roster)
    base = add_screening_features(base, screening)

    baseline_phys = extract_physical_exam(phys, ["Screening"], "x_baseline")
    follow_phys = extract_physical_exam(phys, [spec.primary_followup], "y_followup")
    base = merge_left(base, baseline_phys)
    base = merge_left(base, follow_phys[["PtID", "y_followup_weight_kg", "y_followup_height_cm", "y_followup_bmi"]])

    hba1c_baseline = extract_measure_by_visit(
        sample, "Value", ["Randomization", "randomization"], "x_baseline_hba1c_pct", ("ResultName", "GLYHB")
    )
    hba1c_follow = extract_measure_by_visit(
        sample, "Value", [spec.primary_followup], "y_followup_hba1c_pct", ("ResultName", "GLYHB")
    )
    local_base = extract_measure_by_visit(local_hba1c, "HbA1cTestRes", ["Screening"], "x_baseline_hba1c_pct_local")
    local_follow = extract_measure_by_visit(local_hba1c, "HbA1cTestRes", [spec.primary_followup], "y_followup_hba1c_pct_local")
    base = merge_left(base, hba1c_baseline)
    base = merge_left(base, hba1c_follow)
    base = merge_left(base, local_base)
    base = merge_left(base, local_follow)
    for primary, fallback in [
        ("x_baseline_hba1c_pct", "x_baseline_hba1c_pct_local"),
        ("y_followup_hba1c_pct", "y_followup_hba1c_pct_local"),
    ]:
        if fallback in base.columns:
            base[primary] = base[primary].combine_first(base[fallback]) if primary in base.columns else base[fallback]

    cgm = extract_cgm_summary(spec.zip_filename, "Data Tables/gluIndices RCT.txt")
    base = merge_left(base, cgm)
    return finalize_outcomes(base)


def build_configured_jaeb_dataset(
    spec: PublicDataset,
    *,
    roster_member: str,
    screening_member: str | None = None,
    phys_member: str | None = None,
    follow_phys_member: str | None = None,
    sample_member: str | None = None,
    local_hba1c_member: str | None = None,
    baseline_phys_terms: Iterable[str] | None = ("Screening",),
    followup_phys_terms: Iterable[str] | None = None,
    baseline_hba1c_terms: Iterable[str] = ("Randomization", "Baseline"),
    followup_hba1c_terms: Iterable[str] | None = None,
    local_baseline_terms: Iterable[str] = ("Screening",),
    default_arm: str | None = None,
    cgm_config: dict | None = None,
) -> pd.DataFrame:
    roster = read_zip_table(spec.zip_filename, roster_member)
    base = build_common_roster(spec, roster, default_arm=default_arm)

    if screening_member:
        screening = read_zip_table(spec.zip_filename, screening_member)
        base = add_screening_features(base, screening)

    if phys_member:
        phys = read_zip_table(spec.zip_filename, phys_member)
        base = merge_left(base, extract_physical_exam(phys, baseline_phys_terms, "x_baseline"))
        follow_terms = tuple((spec.primary_followup,) if followup_phys_terms is None else followup_phys_terms)
        follow_source = read_zip_table(spec.zip_filename, follow_phys_member) if follow_phys_member else phys
        follow_phys = extract_physical_exam(follow_source, follow_terms, "y_followup")
        base = merge_left(base, follow_phys[["PtID", "y_followup_weight_kg", "y_followup_height_cm", "y_followup_bmi"]])

    follow_terms = tuple((spec.primary_followup,) if followup_hba1c_terms is None else followup_hba1c_terms)
    if sample_member:
        sample = read_zip_table(spec.zip_filename, sample_member)
        hba1c_baseline = extract_measure_by_visit(
            sample, "Value", baseline_hba1c_terms, "x_baseline_hba1c_pct", ("ResultName", "GLYHB")
        )
        hba1c_follow = extract_measure_by_visit(
            sample, "Value", follow_terms, "y_followup_hba1c_pct", ("ResultName", "GLYHB")
        )
        base = merge_left(base, hba1c_baseline)
        base = merge_left(base, hba1c_follow)

    if local_hba1c_member:
        local_hba1c = read_zip_table(spec.zip_filename, local_hba1c_member)
        local_base = extract_measure_by_visit(local_hba1c, "HbA1cTestRes", local_baseline_terms, "x_baseline_hba1c_pct_local")
        local_follow = extract_measure_by_visit(local_hba1c, "HbA1cTestRes", follow_terms, "y_followup_hba1c_pct_local")
        base = merge_left(base, local_base)
        base = merge_left(base, local_follow)
        for primary, fallback in [
            ("x_baseline_hba1c_pct", "x_baseline_hba1c_pct_local"),
            ("y_followup_hba1c_pct", "y_followup_hba1c_pct_local"),
        ]:
            if fallback in base.columns:
                base[primary] = base[primary].combine_first(base[fallback]) if primary in base.columns else base[fallback]

    if cgm_config is not None:
        base = merge_left(base, extract_cgm_summary_config(spec.zip_filename, **cgm_config))

    return finalize_outcomes(base)


def build_pedap(spec: PublicDataset) -> pd.DataFrame:
    return build_configured_jaeb_dataset(
        spec,
        roster_member="Data Files/PtRoster.txt",
        screening_member="Data Files/PEDAPDiabScreening.txt",
        phys_member="Data Files/PEDAPDiabPhysExam.txt",
        follow_phys_member="Data Files/PEDAPFollowUpCTV.txt",
        sample_member="Data Files/STASampleResults.txt",
        baseline_hba1c_terms=("Randomization",),
        followup_hba1c_terms=("13 Week",),
        followup_phys_terms=("13 Week",),
    )


def build_aide_t1d(spec: PublicDataset) -> pd.DataFrame:
    return build_configured_jaeb_dataset(
        spec,
        roster_member="Data Tables/PtRoster.txt",
        screening_member="Data Tables/AIDEDiabScreening.txt",
        phys_member="Data Tables/AIDEDiabPhysExam.txt",
        sample_member="Data Tables/STASampleResults.txt",
        local_hba1c_member="Data Tables/AIDEDiabLocalHbA1c.txt",
        baseline_phys_terms=("SAP Initiation Visit",),
        followup_phys_terms=("End of P3 Visit",),
        baseline_hba1c_terms=("SAP Initiation Visit",),
        followup_hba1c_terms=("End of P3 Visit",),
        local_baseline_terms=("Screening Visit",),
        cgm_config={
            "member": "Data Tables/gluIndices.txt",
            "period_col": "treatment",
            "baseline_terms": ("Baseline",),
            "followup_terms": None,
            "time_col": "timeOfDay",
            "overall_terms": ("1.24 Hr",),
        },
    )


def build_clver(spec: PublicDataset) -> pd.DataFrame:
    return build_configured_jaeb_dataset(
        spec,
        roster_member="Data Tables/PtRoster.txt",
        screening_member="Data Tables/Screening.txt",
        phys_member="Data Tables/DiabPhysExam.txt",
        sample_member="Data Tables/SampleResults.txt",
        baseline_hba1c_terms=("Randomization",),
        followup_hba1c_terms=("52 Week",),
        followup_phys_terms=("52 Week",),
    )


def build_iobp2(spec: PublicDataset) -> pd.DataFrame:
    return build_configured_jaeb_dataset(
        spec,
        roster_member="Data Tables/IOBP2PtRoster.txt",
        screening_member="Data Tables/IOBP2DiabScreening.txt",
        phys_member="Data Tables/IOBP2HeightWeight.txt",
        sample_member="Data Tables/STASampleResults.txt",
        local_hba1c_member="Data Tables/IOBP2DiabLocalHbA1c.txt",
        baseline_phys_terms=("Randomization", "Screening"),
        followup_phys_terms=("Week 13",),
        baseline_hba1c_terms=("Randomization",),
        followup_hba1c_terms=("Week 13",),
        local_baseline_terms=("Screening",),
    )


def build_dclp5(spec: PublicDataset) -> pd.DataFrame:
    return build_configured_jaeb_dataset(
        spec,
        roster_member="PtRoster.txt",
        screening_member="DiabScreening.txt",
        phys_member="DiabPhysExam.txt",
        sample_member="SampleResults.txt",
        local_hba1c_member="DiabLocalHbA1c.txt",
        baseline_hba1c_terms=("Baseline",),
        followup_hba1c_terms=("16 Week", "16-Week"),
        followup_phys_terms=("16 Week", "16-Week"),
        local_baseline_terms=("Screening", "Randomization"),
    )


def build_dclp3(spec: PublicDataset) -> pd.DataFrame:
    return build_configured_jaeb_dataset(
        spec,
        roster_member="Data Files/PtRoster_a.txt",
        screening_member="Data Files/DiabScreening_a.txt",
        phys_member="Data Files/DiabPhysExam_a.txt",
        sample_member="Data Files/SampleResults_a.txt",
        local_hba1c_member="Data Files/DiabLocalHbA1c_a.txt",
        baseline_hba1c_terms=("Randomization",),
        followup_hba1c_terms=("26 Week", "26-Week"),
        followup_phys_terms=(),
        local_baseline_terms=("Screening", "Randomization"),
        cgm_config={
            "member": "Data Files/gluIndices.txt",
            "period_col": "period",
            "baseline_terms": ("Baseline",),
            "followup_terms": ("Post Randomization",),
            "analysis_col": "analysis",
            "analysis_terms": ("1. 24hr",),
        },
    )


def build_hyclo(spec: PublicDataset) -> pd.DataFrame:
    return build_configured_jaeb_dataset(
        spec,
        roster_member="Data Tables/PtRoster.txt",
        screening_member="Data Tables/HYCLODiabScreening.txt",
        phys_member="Data Tables/HYCLODiabPhysExam.txt",
        follow_phys_member="Data Tables/HYCLOFollowUp.txt",
        local_hba1c_member="Data Tables/HYCLODiabLocalHbA1c.txt",
        baseline_phys_terms=("Screening",),
        followup_phys_terms=("Follow up 4",),
        local_baseline_terms=("Screening",),
        followup_hba1c_terms=("Follow up 4",),
        default_arm="observational_hybrid_closed_loop",
    )


def build_replace_bg(spec: PublicDataset) -> pd.DataFrame:
    roster = read_zip_table(spec.zip_filename, "Data Tables/HPtRoster.txt")
    screening = read_zip_table(spec.zip_filename, "Data Tables/HScreening.txt")
    hba1c = read_zip_table(spec.zip_filename, "Data Tables/HLocalHbA1c.txt")
    base = build_common_roster(spec, roster)
    base = add_screening_features(base, screening)
    baseline_phys = extract_physical_exam(screening, None, "x_baseline")
    base = merge_left(base, baseline_phys)
    hba1c_baseline = extract_measure_by_visit(hba1c, "HbA1cTestRes", ["Randomization"], "x_baseline_hba1c_pct")
    hba1c_follow = extract_measure_by_visit(hba1c, "HbA1cTestRes", ["Week 26"], "y_followup_hba1c_pct")
    base = merge_left(base, hba1c_baseline)
    base = merge_left(base, hba1c_follow)
    return finalize_outcomes(base)


def build_flair(spec: PublicDataset) -> pd.DataFrame:
    roster = read_zip_table(spec.zip_filename, "Data Tables/PtRoster.txt")
    screening = read_zip_table(spec.zip_filename, "Data Tables/FLAIRDiabScreening.txt")
    phys = read_zip_table(spec.zip_filename, "Data Tables/FLAIRDiabPhysExam.txt")
    sample = read_zip_table(spec.zip_filename, "Data Tables/STASampleResults.txt")
    local_hba1c = read_zip_table(spec.zip_filename, "Data Tables/FLAIRDiabLocalHbA1c.txt")
    base = build_common_roster(spec, roster)
    base = add_screening_features(base, screening)
    base = merge_left(base, extract_physical_exam(phys, ["Screening"], "x_baseline"))
    base = merge_left(base, extract_physical_exam(phys, ["End of Study"], "y_followup"))
    hba1c_baseline = extract_measure_by_visit(sample, "Value", ["Randomization"], "x_baseline_hba1c_pct", ("ResultName", "GLYHB"))
    hba1c_follow = extract_measure_by_visit(sample, "Value", ["End of Study"], "y_followup_hba1c_pct", ("ResultName", "GLYHB"))
    local_base = extract_measure_by_visit(local_hba1c, "HbA1cTestRes", ["Screening"], "x_baseline_hba1c_pct_local")
    local_follow = extract_measure_by_visit(local_hba1c, "HbA1cTestRes", ["End of Study"], "y_followup_hba1c_pct_local")
    base = merge_left(base, hba1c_baseline)
    base = merge_left(base, hba1c_follow)
    base = merge_left(base, local_base)
    base = merge_left(base, local_follow)
    for primary, fallback in [
        ("x_baseline_hba1c_pct", "x_baseline_hba1c_pct_local"),
        ("y_followup_hba1c_pct", "y_followup_hba1c_pct_local"),
    ]:
        if fallback in base.columns:
            base[primary] = base[primary].combine_first(base[fallback]) if primary in base.columns else base[fallback]
    return finalize_outcomes(base)


def build_metformin(spec: PublicDataset) -> pd.DataFrame:
    arms = read_zip_table(spec.zip_filename, "MetforminDataset_2024-02-22/Data Tables/CTrtGroupUnmasked.txt")
    screening = read_zip_table(spec.zip_filename, "MetforminDataset_2024-02-22/Data Tables/CScreening.txt")
    rand = read_zip_table(spec.zip_filename, "MetforminDataset_2024-02-22/Data Tables/CRandomization.txt")
    follow = read_zip_table(spec.zip_filename, "MetforminDataset_2024-02-22/Data Tables/CFollowUpVisit.txt")
    sample = read_zip_table(spec.zip_filename, "MetforminDataset_2024-02-22/Data Tables/SampleResults.txt")
    roster = arms.merge(rand[["PtID", "ageRand"]], on="PtID", how="left")
    roster = roster.rename(columns={"ageRand": "AgeAsOfEnrollDt"})
    base = build_common_roster(spec, roster)
    base = add_screening_features(base, screening)
    base = merge_left(base, extract_physical_exam(rand, None, "x_baseline"))
    base = merge_left(base, extract_physical_exam(follow, ["26 week"], "y_followup"))
    hba1c_baseline = extract_measure_by_visit(sample, "Value", ["Randomization"], "x_baseline_hba1c_pct", ("ResultName", "HbA1c"))
    hba1c_follow = extract_measure_by_visit(sample, "Value", ["26 Week"], "y_followup_hba1c_pct", ("ResultName", "HbA1c"))
    base = merge_left(base, hba1c_baseline)
    base = merge_left(base, hba1c_follow)
    return finalize_outcomes(base)


def finalize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    if "x_baseline_hba1c_pct" in df.columns and "y_followup_hba1c_pct" in df.columns:
        df["y_hba1c_change_pct_points"] = df["y_followup_hba1c_pct"] - df["x_baseline_hba1c_pct"]
        df["y_hba1c_improved_ge_0_5"] = (df["y_hba1c_change_pct_points"] <= -0.5).astype("Int64")
        df.loc[df["y_hba1c_change_pct_points"].isna(), "y_hba1c_improved_ge_0_5"] = pd.NA
        df["y_hba1c_under_7_at_followup"] = (df["y_followup_hba1c_pct"] < 7.0).astype("Int64")
        df.loc[df["y_followup_hba1c_pct"].isna(), "y_hba1c_under_7_at_followup"] = pd.NA
    if "x_baseline_weight_kg" in df.columns and "y_followup_weight_kg" in df.columns:
        df["y_weight_change_kg"] = df["y_followup_weight_kg"] - df["x_baseline_weight_kg"]
    if "x_baseline_bmi" in df.columns and "y_followup_bmi" in df.columns:
        df["y_bmi_change"] = df["y_followup_bmi"] - df["x_baseline_bmi"]
    if "x_baseline_cgm_time_in_range_70_180_pct" in df.columns and "y_followup_cgm_time_in_range_70_180_pct" in df.columns:
        df["y_tir_improved_ge_5pct"] = (
            df["y_followup_cgm_time_in_range_70_180_pct"] - df["x_baseline_cgm_time_in_range_70_180_pct"] >= 5
        ).astype("Int64")
        df.loc[
            df["y_followup_cgm_time_in_range_70_180_pct"].isna()
            | df["x_baseline_cgm_time_in_range_70_180_pct"].isna(),
            "y_tir_improved_ge_5pct",
        ] = pd.NA
    return df


def add_missing_and_imputed_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    categorical_features = [
        col
        for col in out.columns
        if col.startswith("x_")
        and (
            out[col].dtype == object
            or col
            in {
                "x_site_id",
                "x_randomized_arm",
                "x_intervention_type",
                "x_sex",
                "x_ethnicity",
                "x_race",
                "x_insulin_delivery_method",
                "x_current_cgm_use",
            }
        )
    ]
    for col in categorical_features:
        out[col] = out[col].map(normalize_category)

    numeric_features = [
        col
        for col in out.columns
        if col.startswith("x_")
        and col not in categorical_features
        and pd.api.types.is_numeric_dtype(out[col])
    ]
    for col in numeric_features:
        miss_col = f"{col}_missing"
        imp_col = f"{col}_imputed"
        out[miss_col] = out[col].isna().astype(int)
        med_by_study = out.groupby("study_id")[col].transform("median")
        global_median = out[col].median()
        if math.isnan(global_median) if isinstance(global_median, float) else pd.isna(global_median):
            global_median = 0.0
        out[imp_col] = out[col].fillna(med_by_study).fillna(global_median)
    return out


def build_ml_table() -> tuple[pd.DataFrame, dict[str, dict[str, int]]]:
    frames = []
    counts: dict[str, dict[str, int]] = {}
    builders = {
        "WISDM": build_wisdm_city_sence,
        "CITY": build_wisdm_city_sence,
        "SENCE": build_wisdm_city_sence,
        "REPLACE_BG": build_replace_bg,
        "FLAIR": build_flair,
        "METFORMIN_T1D": build_metformin,
        "PEDAP": build_pedap,
        "AIDE_T1D": build_aide_t1d,
        "CLVER": build_clver,
        "IOBP2": build_iobp2,
        "DCLP5": build_dclp5,
        "DCLP3": build_dclp3,
        "HYCLO": build_hyclo,
    }
    for spec in PUBLIC_DATASETS:
        built = builders[spec.study_id](spec)
        counts[spec.study_id] = {
            "rows_after_randomized_arm_filter": int(len(built)),
            "hba1c_followup_available": int(built.get("y_followup_hba1c_pct", pd.Series(dtype=float)).notna().sum()),
            "cgm_followup_available": int(
                built.get("y_followup_cgm_time_in_range_70_180_pct", pd.Series(dtype=float)).notna().sum()
            ),
            "weight_followup_available": int(built.get("y_followup_weight_kg", pd.Series(dtype=float)).notna().sum()),
        }
        frames.append(built)
    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined = add_missing_and_imputed_features(combined)

    preferred_order = [
        "participant_id",
        "study_id",
        "dataset_name",
        "nct_id",
        "participant_source_id",
        "source_link",
        "randomized_arm_original",
        "x_randomized_arm",
        "x_intervention_type",
        "x_site_id",
        "x_age_years",
        "x_sex",
        "x_race",
        "x_ethnicity",
        "x_diabetes_diagnosis_age_years",
        "x_diabetes_duration_years",
        "x_insulin_delivery_method",
        "x_current_cgm_use",
        "x_current_cgm_days_per_week",
        "x_units_insulin_total_baseline",
        "x_bgm_checks_per_day_baseline",
        "x_baseline_weight_kg",
        "x_baseline_height_cm",
        "x_baseline_bmi",
        "x_baseline_hba1c_pct",
        "x_baseline_cgm_mean_glucose_mg_dl",
        "x_baseline_cgm_time_in_range_70_180_pct",
        "x_baseline_cgm_time_below_70_pct",
        "x_baseline_cgm_time_below_54_pct",
        "x_baseline_cgm_time_above_180_pct",
        "x_baseline_cgm_time_above_250_pct",
        "x_baseline_cgm_hours",
        "x_baseline_cgm_cv_pct",
        "y_followup_weight_kg",
        "y_followup_height_cm",
        "y_followup_bmi",
        "y_weight_change_kg",
        "y_bmi_change",
        "y_followup_hba1c_pct",
        "y_hba1c_change_pct_points",
        "y_hba1c_improved_ge_0_5",
        "y_hba1c_under_7_at_followup",
        "y_followup_cgm_mean_glucose_mg_dl",
        "y_followup_cgm_time_in_range_70_180_pct",
        "y_change_cgm_time_in_range_70_180_pct",
        "y_tir_improved_ge_5pct",
        "y_followup_cgm_time_below_70_pct",
        "y_change_cgm_time_below_70_pct",
        "y_followup_cgm_time_below_54_pct",
        "y_change_cgm_time_below_54_pct",
        "y_followup_cgm_time_above_180_pct",
        "y_change_cgm_time_above_180_pct",
        "y_followup_cgm_time_above_250_pct",
        "y_change_cgm_time_above_250_pct",
        "y_followup_cgm_hours",
        "y_followup_cgm_cv_pct",
    ]
    cols = [col for col in preferred_order if col in combined.columns]
    remaining = [col for col in combined.columns if col not in cols and col != "PtID"]
    combined = combined[cols + remaining].sort_values(["study_id", "participant_source_id"]).reset_index(drop=True)
    return combined, counts


def make_inventory(ml: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for spec in PUBLIC_DATASETS:
        subset = ml[ml["study_id"] == spec.study_id]
        available = [
            "randomized arm",
            "age",
            "sex/race/ethnicity",
            "baseline HbA1c",
            "baseline weight/BMI",
        ]
        if subset.get("x_baseline_cgm_time_in_range_70_180_pct", pd.Series(dtype=float)).notna().any():
            available.extend(["baseline/follow-up CGM TIR", "hypoglycemia/hyperglycemia CGM metrics"])
        if subset.get("y_followup_weight_kg", pd.Series(dtype=float)).notna().any():
            available.append("follow-up weight/BMI")
        rows.append(
            {
                "dataset_name": spec.dataset_name,
                "source_link": spec.dataset_url,
                "study_population": spec.study_population,
                "intervention_type": spec.intervention_type,
                "sample_size": int(len(subset)),
                "primary_outcome": spec.primary_outcome,
                "available_variables": "; ".join(available),
                "download_method": "Direct public JAEB zip downloaded to data/raw/jaeb_public.",
                "license_or_use_restrictions": spec.license_or_limit,
                "status": "downloaded_cleaned",
            }
        )
    rows.extend(INVENTORY_EXTRA_ROWS)
    return pd.DataFrame(rows)


def role_for_column(col: str) -> str:
    if col in {"participant_id", "participant_source_id", "study_id", "dataset_name", "nct_id", "source_link"}:
        return "identifier_or_metadata"
    if col.endswith("_missing"):
        return "baseline_feature_missing_indicator"
    if col.endswith("_imputed"):
        return "baseline_feature_imputed"
    if col.startswith("x_"):
        return "baseline_feature"
    if col.startswith("y_"):
        return "followup_outcome_or_target"
    if col == "randomized_arm_original":
        return "treatment_assignment_raw"
    return "derived_or_auxiliary"


def units_for_column(col: str) -> str:
    if "hba1c" in col:
        return "percent HbA1c"
    if col.endswith("_kg") or "weight_kg" in col:
        return "kg"
    if col.endswith("_cm") or "height_cm" in col:
        return "cm"
    if "bmi" in col:
        return "kg/m^2"
    if "glucose_mg_dl" in col:
        return "mg/dL"
    if "pct" in col or "percent" in col:
        return "percentage points"
    if "age_years" in col or "duration_years" in col:
        return "years"
    if "hours" in col:
        return "hours"
    if "per_week" in col:
        return "days/week"
    if "per_day" in col:
        return "count/day"
    return ""


def description_for_column(col: str) -> str:
    descriptions = {
        "participant_id": "Unique participant identifier prefixed by study_id.",
        "study_id": "Short study identifier.",
        "dataset_name": "Full dataset or trial name.",
        "nct_id": "ClinicalTrials.gov identifier when available.",
        "participant_source_id": "Original de-identified participant ID in source tables.",
        "source_link": "Public source zip URL or portal link.",
        "randomized_arm_original": "Treatment arm label exactly as provided in source table.",
        "x_randomized_arm": "Normalized randomized arm label known at baseline.",
        "x_intervention_type": "Trial-level intervention description.",
        "x_age_years": "Participant age at enrollment/randomization.",
        "x_sex": "Normalized sex/gender category.",
        "x_race": "Normalized race category.",
        "x_ethnicity": "Normalized ethnicity category.",
        "x_diabetes_diagnosis_age_years": "Age at type 1 diabetes diagnosis when available.",
        "x_diabetes_duration_years": "Age minus diagnosis age; capped to plausible range.",
        "x_baseline_hba1c_pct": "Baseline HbA1c, preferring central lab/STA result when available.",
        "y_followup_hba1c_pct": "Primary follow-up HbA1c for the trial horizon.",
        "y_hba1c_change_pct_points": "Follow-up HbA1c minus baseline HbA1c.",
        "y_hba1c_improved_ge_0_5": "Binary target: HbA1c decreased by at least 0.5 percentage points.",
        "y_hba1c_under_7_at_followup": "Binary target: follow-up HbA1c <7%.",
        "y_tir_improved_ge_5pct": "Binary target: CGM time in range improved by at least 5 percentage points.",
    }
    if col in descriptions:
        return descriptions[col]
    if col.endswith("_missing"):
        return f"Missingness indicator for {col[:-8]}."
    if col.endswith("_imputed"):
        return f"Median-imputed ML-ready value for {col[:-8]}."
    if "cgm_time_in_range" in col:
        return "CGM percent time in glucose range 70-180 mg/dL."
    if "cgm_time_below_70" in col:
        return "CGM percent time below 70 mg/dL."
    if "cgm_time_below_54" in col:
        return "CGM percent time below 54 mg/dL."
    if "cgm_time_above_180" in col:
        return "CGM percent time above 180 mg/dL."
    if "cgm_time_above_250" in col:
        return "CGM percent time above 250 mg/dL."
    if "cgm_mean_glucose" in col:
        return "Mean CGM glucose."
    if "cgm_cv" in col:
        return "CGM coefficient of variation."
    if "cgm_hours" in col:
        return "Hours of CGM data contributing to summary."
    if "weight" in col:
        return "Weight standardized to kg."
    if "height" in col:
        return "Height standardized to cm."
    if "bmi" in col:
        return "Body mass index derived from standardized weight and height."
    return col.replace("_", " ")


def make_data_dictionary(ml: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in ml.columns:
        values = ""
        if is_object_dtype(ml[col]) or is_string_dtype(ml[col]) or str(ml[col].dtype) == "str":
            unique = sorted([str(x) for x in ml[col].dropna().unique()[:20]])
            values = "; ".join(unique)
        rows.append(
            {
                "variable_name": col,
                "role": role_for_column(col),
                "data_type": str(ml[col].dtype),
                "unit": units_for_column(col),
                "description": description_for_column(col),
                "allowed_values_or_range": values,
                "missing_handling": (
                    "Original values retained; baseline numeric predictors have paired _missing and _imputed columns."
                    if col.startswith("x_") and not (col.endswith("_missing") or col.endswith("_imputed"))
                    else "Derived from retained source values."
                ),
                "source_notes": "JAEB public de-identified data tables; see dataset_inventory.csv.",
            }
        )
    return pd.DataFrame(rows)


def standardize_cgm_long(
    study_id: str,
    zip_filename: str,
    member: str,
    *,
    period_col: str,
    time_col: str | None = None,
    analysis_col: str | None = None,
    treatment_col: str | None = None,
    randomized_arm_map: pd.DataFrame | None = None,
) -> pd.DataFrame:
    df = read_zip_table(zip_filename, member)
    if df.empty or "PtID" not in df.columns:
        return pd.DataFrame()
    metrics = {
        "gluMean": "cgm_mean_glucose_mg_dl",
        "gluInRange": "cgm_time_in_range_70_180_pct",
        "gluBelow70": "cgm_time_below_70_pct",
        "gluBelow54": "cgm_time_below_54_pct",
        "gluAbove180": "cgm_time_above_180_pct",
        "gluAbove250": "cgm_time_above_250_pct",
        "gluAbove300": "cgm_time_above_300_pct",
        "gluHours": "cgm_hours",
        "gluCV": "cgm_cv_pct",
        "gluSD": "cgm_sd_mg_dl",
        "gluHypoRate": "cgm_hypo_rate",
        "gluHyperRate": "cgm_hyper_rate",
    }
    out = pd.DataFrame(index=df.index)
    out["study_id"] = study_id
    out["participant_source_id"] = df["PtID"].astype(str)
    out["participant_id"] = out["participant_source_id"].map(lambda x: participant_key(study_id, x))
    out["period_label"] = df[period_col].map(normalize_text) if period_col in df.columns else np.nan
    out["time_window"] = df[time_col].map(normalize_text) if time_col and time_col in df.columns else np.nan
    out["analysis_label"] = df[analysis_col].map(normalize_text) if analysis_col and analysis_col in df.columns else np.nan
    out["treatment_context"] = df[treatment_col].map(normalize_text) if treatment_col and treatment_col in df.columns else np.nan
    for source_col, clean_col in metrics.items():
        out[clean_col] = to_numeric(df[source_col]) if source_col in df.columns else np.nan
    out["source_table"] = member
    if randomized_arm_map is not None and not randomized_arm_map.empty:
        out = out.merge(randomized_arm_map, on="participant_source_id", how="left")
    return out


def make_randomized_arm_map(zip_filename: str, member: str, arm_candidates: Iterable[str] = ("TrtGroup", "trtGroup")) -> pd.DataFrame:
    roster = read_zip_table(zip_filename, member)
    pt_col = first_existing(roster, ["PtID", "PtId"])
    arm_col = first_existing(roster, arm_candidates)
    if pt_col is None or arm_col is None:
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "participant_source_id": roster[pt_col].astype(str),
            "randomized_arm_original": roster[arm_col].map(normalize_text),
        }
    ).drop_duplicates("participant_source_id")


def build_cgm_summary_long() -> pd.DataFrame:
    configs = [
        {
            "study_id": "WISDM",
            "zip_filename": "WISDMPublicDataset.zip",
            "member": "Data Tables/gluIndices RCT.txt",
            "period_col": "period",
            "time_col": "time",
            "treatment_col": "TrtGroup",
            "roster": "Data Tables/PtRoster.txt",
        },
        {
            "study_id": "CITY",
            "zip_filename": "CITYPublicDataset.zip",
            "member": "Data Tables/gluIndices RCT.txt",
            "period_col": "period",
            "time_col": "time",
            "treatment_col": "TrtGroup",
            "roster": "Data Tables/PtRoster.txt",
        },
        {
            "study_id": "SENCE",
            "zip_filename": "SENCEPublicDataset.zip",
            "member": "Data Tables/gluIndices RCT.txt",
            "period_col": "period",
            "time_col": "time",
            "treatment_col": "TrtGroup",
            "roster": "Data Tables/PtRoster.txt",
        },
        {
            "study_id": "AIDE_T1D",
            "zip_filename": "AIDET1D_Public_Dataset.zip",
            "member": "Data Tables/gluIndices.txt",
            "period_col": "weeks",
            "time_col": "timeOfDay",
            "treatment_col": "treatment",
            "roster": "Data Tables/PtRoster.txt",
        },
        {
            "study_id": "DCLP3",
            "zip_filename": "DCLP3 Public Dataset - Release 3 - 2022-08-04.zip",
            "member": "Data Files/gluIndices.txt",
            "period_col": "period",
            "time_col": "dayTime",
            "analysis_col": "analysis",
            "roster": "Data Files/PtRoster_a.txt",
        },
    ]
    frames = []
    for cfg in configs:
        zip_path = RAW_DIR / cfg["zip_filename"]
        if not zip_path.exists():
            continue
        arm_map = make_randomized_arm_map(cfg["zip_filename"], cfg["roster"]) if cfg.get("roster") else None
        frames.append(
            standardize_cgm_long(
                cfg["study_id"],
                cfg["zip_filename"],
                cfg["member"],
                period_col=cfg["period_col"],
                time_col=cfg.get("time_col"),
                analysis_col=cfg.get("analysis_col"),
                treatment_col=cfg.get("treatment_col"),
                randomized_arm_map=arm_map,
            )
        )
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def missing_summary(ml: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in ml.columns:
        rows.append({"variable": col, "missing_n": int(ml[col].isna().sum()), "missing_pct": ml[col].isna().mean() * 100})
    return pd.DataFrame(rows).sort_values(["missing_pct", "variable"], ascending=[False, True])


def markdown_table(df: pd.DataFrame, index: bool = False) -> str:
    """Render a small Markdown table without requiring pandas[tabulate]."""
    if index:
        work = df.reset_index()
    else:
        work = df.copy()
    if work.empty:
        return "_No rows._"
    text = work.copy()
    for col in text.columns:
        if pd.api.types.is_float_dtype(text[col]):
            text[col] = text[col].map(lambda x: "" if pd.isna(x) else f"{x:.2f}")
        else:
            text[col] = text[col].map(lambda x: "" if pd.isna(x) else str(x))
    headers = [str(col) for col in text.columns]
    rows = text.values.tolist()
    widths = [len(header) for header in headers]
    for row in rows:
        widths = [max(width, len(str(cell))) for width, cell in zip(widths, row)]
    header_line = "| " + " | ".join(header.ljust(width) for header, width in zip(headers, widths)) + " |"
    sep_line = "| " + " | ".join("-" * width for width in widths) + " |"
    body = ["| " + " | ".join(str(cell).ljust(width) for cell, width in zip(row, widths)) + " |" for row in rows]
    return "\n".join([header_line, sep_line, *body])


def write_report(ml: pd.DataFrame, inventory: pd.DataFrame, counts: dict[str, dict[str, int]]) -> None:
    miss = missing_summary(ml)
    core_missing = miss[miss["variable"].isin(
        [
            "x_baseline_hba1c_pct",
            "y_followup_hba1c_pct",
            "x_baseline_cgm_time_in_range_70_180_pct",
            "y_followup_cgm_time_in_range_70_180_pct",
            "x_baseline_weight_kg",
            "y_followup_weight_kg",
        ]
    )]
    hba1c_task_n = int(ml["y_hba1c_change_pct_points"].notna().sum()) if "y_hba1c_change_pct_points" in ml else 0
    cgm_task_n = (
        int(ml["y_change_cgm_time_in_range_70_180_pct"].notna().sum())
        if "y_change_cgm_time_in_range_70_180_pct" in ml
        else 0
    )
    weight_task_n = int(ml["y_weight_change_kg"].notna().sum()) if "y_weight_change_kg" in ml else 0
    by_study = ml.groupby("study_id").agg(
        n=("participant_id", "size"),
        hba1c_outcome_n=("y_followup_hba1c_pct", lambda s: int(s.notna().sum()) if s.name in ml else int(s.notna().sum())),
    )
    if "y_followup_cgm_time_in_range_70_180_pct" in ml:
        by_study["cgm_tir_outcome_n"] = ml.groupby("study_id")["y_followup_cgm_time_in_range_70_180_pct"].apply(
            lambda s: int(s.notna().sum())
        )
    if "y_followup_weight_kg" in ml:
        by_study["weight_outcome_n"] = ml.groupby("study_id")["y_followup_weight_kg"].apply(lambda s: int(s.notna().sum()))

    report = f"""# Cleaning Report: Public Diabetes RCT/Intervention ML Table

Generated by `scripts/prepare_diabetes_rct_ml_dataset.py`.

## Scope

This workspace searched for openly downloadable diabetes RCT or near-RCT intervention data suitable for machine learning. The main cleaned table now uses {len(PUBLIC_DATASETS)} public JAEB individual-level datasets downloaded into `data/raw/jaeb_public`:

{chr(10).join(f"- {spec.study_id}: {spec.dataset_name} ({spec.nct_id})" for spec in PUBLIC_DATASETS)}

The raw JAEB files are retained unchanged. Cleaned analysis outputs are written to `data/processed`.
When precomputed CGM summaries are available, the script also writes `data/processed/cgm_summary_long.csv`
as a harmonized long-format CGM table for later phase-map and time-series feature work.
The CSV output is authoritative in this run. The script also attempts Parquet export when `pyarrow` or
`fastparquet` is available; this environment did not have either engine installed.

## Source Selection Logic

- Included only datasets with direct public download links or clear public repository access.
- Did not fabricate or simulate unavailable data.
- RCT-quality sources that require a formal request, such as BioLINCC ACCORD and NIDDK DPP/Look AHEAD/TODAY/DCCT-EDIC, are listed in `dataset_inventory.csv` but not downloaded.
- Large raw device/CGM tables inside the downloaded JAEB ZIPs are retained unchanged for later time-series feature engineering; this participant-level table uses clinical tables and available precomputed CGM summaries.

## Cleaning Steps

1. Read pipe-delimited JAEB text tables directly from each ZIP archive.
2. Detected UTF-16 vs UTF-8 encodings from byte order marks.
3. Filtered to participants with a non-missing treatment/intervention label. HYCLO is observational and is explicitly labeled `observational_hybrid_closed_loop`, not treated as randomized.
4. Harmonized participant IDs as `study_id + '_' + PtID`; kept original de-identified IDs in `participant_source_id`.
5. Standardized baseline features with `x_` prefixes and follow-up outcomes with `y_` prefixes.
6. Preferred central/STA HbA1c (`GLYHB` or `HbA1c`) and used local HbA1c as fallback for JAEB tables where needed.
7. Standardized weight to kg and height to cm using unit columns when present; for sources without unit columns, assumed kg/cm and converted implausibly short heights (<100) as inches.
8. Calculated BMI from standardized weight and height.
9. Used only baseline/randomization/screening measurements as candidate predictors.
10. Used trial-primary or best-aligned public follow-up horizons where possible, including 13 weeks for PEDAP/IOBP2, 16 weeks for DCLP5, 26 weeks for WISDM/CITY/SENCE/DCLP3/REPLACE-BG/Metformin, 52 weeks for CLVer, End of P3 for AIDE, End of Study for FLAIR, and Follow up 4 for HYCLO.
11. Created target variables:
    - `y_hba1c_change_pct_points`
    - `y_hba1c_improved_ge_0_5`
    - `y_hba1c_under_7_at_followup`
    - `y_change_cgm_time_in_range_70_180_pct`
    - `y_tir_improved_ge_5pct`
    - `y_weight_change_kg`
12. Added missingness indicators and study-median/global-median imputed versions for baseline numeric `x_` predictors. Follow-up outcomes were not imputed.

## Exclusion and Availability Counts

Rows after filtering to a non-missing treatment/intervention label:

{markdown_table(by_study, index=True)}

Builder count details:

{markdown_table(pd.DataFrame(counts).T, index=True)}

Total participant rows in `processed_ml_table.csv`: {len(ml)}

## Missingness in Core Variables

{markdown_table(core_missing, index=False)}

Full missingness can be recomputed with the script from the processed table.

## Leakage Prevention

The modeling table uses a strict naming convention:

- `x_` columns are baseline, screening, randomization, treatment assignment, or trial-level information known before follow-up.
- `y_` columns are follow-up outcomes or derived targets.
- No follow-up HbA1c, CGM metric, weight, BMI, or post-baseline adherence variable is used to impute or create baseline `x_` features.
- Numeric imputation is applied only to baseline `x_` predictors. Outcome columns remain missing when unavailable.

## ML Tasks Supported

- Regression: predict `y_hba1c_change_pct_points`.
- Classification: predict `y_hba1c_improved_ge_0_5`.
- Classification: predict `y_hba1c_under_7_at_followup`.
- CGM regression/classification in WISDM, CITY, and SENCE: predict TIR change or `y_tir_improved_ge_5pct`.
- Weight/BMI change modeling where follow-up anthropometrics are available, mainly WISDM, CITY, FLAIR, and Metformin.
- Treatment-effect modeling using `x_randomized_arm` and study stratification. For pooled modeling, include `study_id` or fit study-specific models because interventions and age ranges differ.

## Limitations

- This is not a single homogeneous trial. It is a harmonized participant-level table across multiple JAEB trials, so trial heterogeneity must be modeled explicitly.
- Several studies have public CGM/device detail tables, but this participant-level pass did not compute new CGM summaries from the largest raw device files. DCLP3 and the earlier WISDM/CITY/SENCE datasets contribute precomputed CGM summaries; other device-heavy studies primarily contribute HbA1c/body-size outcomes until time-series aggregation is added.
- FLAIR and AIDE are crossover or sequence studies. Their participant-level end-of-period HbA1c outcomes are useful for general modeling but are not full period-level crossover analyses.
- HYCLO is an observational hybrid closed-loop data collection study and should be analyzed separately from randomized trials in causal analyses.
- Metformin ClinicalTrials.gov enrollment is larger than the public table cleaned here; this script uses the participants present in the downloaded public tables.
- De-identified dates in JAEB data are shifted or synthetic-like and should not be interpreted as calendar dates.
- Public-use terms should be checked before redistribution; this workspace keeps raw public zips local.

## Next Modeling Suggestions

- Split train/test within study or use leave-one-study-out validation to avoid over-optimistic pooled performance.
- For treatment-response questions, include `study_id`, baseline outcome value, and treatment arm, and consider causal/heterogeneous treatment-effect models.
- For CGM-specific tasks, start with WISDM, CITY, SENCE, DCLP3, and AIDE because they now have harmonized precomputed CGM summaries in `cgm_summary_long.csv`.
- For richer digital-health modeling, aggregate raw device/CGM time-series windows from PEDAP, IOBP2, DCLP5, CLVer, DCLP3, AIDE, WISDM, CITY, and SENCE before modeling.
- Avoid using post-randomization adherence, device-upload frequency, or follow-up visit variables as baseline predictors unless the prediction timepoint is explicitly later than baseline.
"""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "cleaning_report.md").write_text(report, encoding="utf-8")


def write_outputs(ml: pd.DataFrame, counts: dict[str, dict[str, int]]) -> None:
    ensure_dirs()
    inventory = make_inventory(ml)
    dictionary = make_data_dictionary(ml)
    cgm_long = build_cgm_summary_long()

    ml.to_csv(PROCESSED_DIR / "processed_ml_table.csv", index=False)
    try:
        ml.to_parquet(PROCESSED_DIR / "processed_ml_table.parquet", index=False)
    except Exception as exc:
        print(f"parquet export skipped: {exc}")
    inventory.to_csv(PROCESSED_DIR / "dataset_inventory.csv", index=False)
    inventory.to_csv(DOCS_DIR / "dataset_inventory.csv", index=False)
    dictionary.to_csv(PROCESSED_DIR / "data_dictionary.csv", index=False)
    dictionary.to_csv(DOCS_DIR / "data_dictionary.csv", index=False)
    if not cgm_long.empty:
        cgm_long.to_csv(PROCESSED_DIR / "cgm_summary_long.csv", index=False)
    write_report(ml, inventory, counts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="Download public JAEB ZIP files before cleaning.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing downloads when used with --download.")
    args = parser.parse_args(argv)

    ensure_dirs()
    if args.download:
        download_public_zips(overwrite=args.overwrite)
    ml, counts = build_ml_table()
    write_outputs(ml, counts)
    print(f"wrote {PROCESSED_DIR / 'processed_ml_table.csv'} with {len(ml)} rows and {ml.shape[1]} columns")
    print(f"wrote {PROCESSED_DIR / 'data_dictionary.csv'}")
    print(f"wrote {PROCESSED_DIR / 'dataset_inventory.csv'}")
    if (PROCESSED_DIR / "cgm_summary_long.csv").exists():
        print(f"wrote {PROCESSED_DIR / 'cgm_summary_long.csv'}")
    print(f"wrote {DOCS_DIR / 'cleaning_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
