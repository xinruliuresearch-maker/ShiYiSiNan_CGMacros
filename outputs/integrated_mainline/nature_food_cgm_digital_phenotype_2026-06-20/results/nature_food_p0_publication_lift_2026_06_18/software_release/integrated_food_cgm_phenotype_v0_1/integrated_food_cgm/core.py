from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = PACKAGE_ROOT / "assets" / "phase_reference.json"

REQUIRED_CGM = [
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


def _load_reference() -> dict:
    return json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))


def _z(series: pd.Series, ref: dict, name: str) -> pd.Series:
    mean = ref["feature_reference"][name]["mean"]
    sd = ref["feature_reference"][name]["sd"]
    if not sd:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (pd.to_numeric(series, errors="coerce") - mean) / sd


def assign_phase(input_frame: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_CGM if c not in input_frame.columns]
    if missing:
        raise ValueError(f"Missing required CGM columns: {missing}")
    ref = _load_reference()
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
    dist = []
    for _, row in centroids.iterrows():
        c = row[ORDER_COLS].to_numpy(float)
        dist.append(np.sqrt(((x - c) ** 2).sum(axis=1)))
    dist_mat = np.vstack(dist).T
    nearest = dist_mat.argmin(axis=1)
    out["phase_label"] = [centroids.iloc[i]["phase_label"] for i in nearest]
    out["phase_assignment_distance"] = dist_mat.min(axis=1)
    dictionary = pd.DataFrame(ref["phase_dictionary"])
    out["phase_id"] = out["phase_label"].map(dict(zip(dictionary["phase_label_zh"], dictionary["phase_id"])))
    out["phase_label_en"] = out["phase_label"].map(dict(zip(dictionary["phase_label_zh"], dictionary["phase_label_en"])))
    return out


def _matrix_score(value: object) -> float:
    mapping = {
        "protective_whole_food_or_low_carb": -0.5,
        "fiber_rich_or_whole_food_matrix": -0.5,
        "low_carb_or_protein_forward": -0.5,
        "mixed_buffered_or_unknown": 0.35,
        "mixed_meal_protein_fat_buffered": 0.35,
        "mixed_or_unknown_matrix": 0.35,
        "rapid_digestible_or_liquid_carb": 0.65,
        "refined_starch_low_matrix_protection": 0.65,
        "sweetened_beverage_or_liquid_carb": 0.65,
    }
    return mapping.get(str(value), 0.0)


def integrated_phenotype_report(input_frame: pd.DataFrame) -> pd.DataFrame:
    out = assign_phase(input_frame)
    for col in ["msi_core", "carbs_10g", "pre_glucose_10", "calories_100"]:
        if col not in out.columns:
            out[col] = 0.0
    if "matrix_collapsed3" not in out.columns:
        out["matrix_collapsed3"] = "unknown"
    linear = (
        -1.10
        + 1.388 * pd.to_numeric(out["msi_core"], errors="coerce").fillna(0)
        + 0.008 * pd.to_numeric(out["carbs_10g"], errors="coerce").fillna(0)
        - 0.203 * pd.to_numeric(out["pre_glucose_10"], errors="coerce").fillna(0)
        - 0.016 * pd.to_numeric(out["calories_100"], errors="coerce").fillna(0)
        + out["matrix_collapsed3"].map(_matrix_score).fillna(0)
    )
    out["meal_high_iauc_ranking_score"] = 1 / (1 + np.exp(-linear))
    out["risk_language"] = "ranking_only_not_absolute_clinical_risk"
    return out
