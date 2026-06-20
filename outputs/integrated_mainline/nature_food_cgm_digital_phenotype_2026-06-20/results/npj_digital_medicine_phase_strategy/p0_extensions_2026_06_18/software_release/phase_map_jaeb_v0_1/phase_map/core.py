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
