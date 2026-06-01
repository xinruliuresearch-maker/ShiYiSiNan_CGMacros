# -*- coding: utf-8 -*-
"""
13_lightweight_external_validation_ohio.py

Lightweight external validation using OhioT1DM-style XML files.

Purpose:
1. Parse an independent public CGM dataset with meal events.
2. Construct meal-level postprandial response phenotypes.
3. Evaluate simplified feature-set ablation:
   E0 meal/time
   E1 + pre-CGM
   E2 + insulin/physiology if available
4. Evaluate within-subject temporal prediction, leave-subject-out prediction,
   few-shot personalization, high-response detection, and calibration.
5. Output external-validation tables and figures.

Important:
This is external validation of the analytical framework, not direct validation
of the CGMacros M3 model weights.
"""

from pathlib import Path
import re
import warnings
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
    average_precision_score,
)

try:
    from sklearn.preprocessing import OneHotEncoder
except Exception as e:
    raise ImportError("Cannot import OneHotEncoder from scikit-learn.") from e

warnings.filterwarnings("ignore")


# ============================================================
# 0. Paths and parameters
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_ROOT = ROOT / "data" / "external" / "OhioT1DM"

OUT = ROOT / "outputs" / "external_validation"
TABLES = OUT / "tables"
FIGURES = OUT / "figures"

TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

TARGETS = ["iauc_2h", "peak_delta_2h"]
RANDOM_SEED = 42
N_BOOTSTRAP = 1000

MIN_POST_POINTS = 12      # 2h with 5-min CGM ideally has ~24 points
MIN_PRE_POINTS = 3
POST_WINDOW_MIN = 120
PRE_WINDOW_MIN = 60

TARGET_LABELS = {
    "iauc_2h": "2-h glucose iAUC",
    "peak_delta_2h": "2-h peak glucose excursion",
}

TARGET_UNITS = {
    "iauc_2h": "mg/dL*min",
    "peak_delta_2h": "mg/dL",
}


# ============================================================
# 1. General utilities
# ============================================================

def parse_datetime_any(x):
    if x is None:
        return pd.NaT

    x = str(x).strip()
    if x == "":
        return pd.NaT

    # OhioT1DM commonly uses strings like "01-01-2018 00:00:00"
    candidates = [
        "%m-%d-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]

    for fmt in candidates:
        try:
            return pd.to_datetime(x, format=fmt)
        except Exception:
            pass

    return pd.to_datetime(x, errors="coerce")


def extract_subject_id_from_path(path):
    name = Path(path).stem
    nums = re.findall(r"\d+", name)
    if nums:
        return nums[0]
    return name


def to_float_safe(x):
    try:
        return float(x)
    except Exception:
        return np.nan


def trapz_auc(minutes, values):
    minutes = np.asarray(minutes, dtype=float)
    values = np.asarray(values, dtype=float)

    valid = np.isfinite(minutes) & np.isfinite(values)
    minutes = minutes[valid]
    values = values[valid]

    if len(values) < 2:
        return np.nan

    order = np.argsort(minutes)
    minutes = minutes[order]
    values = values[order]

    try:
        return float(np.trapezoid(values, minutes))
    except AttributeError:
        return float(np.trapz(values, minutes))


def rmse(y_true, y_pred):
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def pearson_r(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[valid]
    y_pred = y_pred[valid]

    if len(y_true) < 2:
        return np.nan

    if np.std(y_true) == 0 or np.std(y_pred) == 0:
        return np.nan

    return float(np.corrcoef(y_true, y_pred)[0, 1])


def compute_metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[valid]
    y_pred = y_pred[valid]

    if len(y_true) < 2:
        return {
            "MAE": np.nan,
            "RMSE": np.nan,
            "R2": np.nan,
            "Pearson_r": np.nan,
            "n": int(len(y_true)),
        }

    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": rmse(y_true, y_pred),
        "R2": float(r2_score(y_true, y_pred)),
        "Pearson_r": pearson_r(y_true, y_pred),
        "n": int(len(y_true)),
    }


def calibration_metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[valid]
    y_pred = y_pred[valid]

    if len(y_true) < 3 or np.std(y_pred) == 0:
        return {
            "calibration_intercept": np.nan,
            "calibration_slope": np.nan,
            "prediction_sd_ratio": np.nan,
            "prediction_range_ratio_p95_p5": np.nan,
        }

    X = np.column_stack([np.ones(len(y_pred)), y_pred])
    beta = np.linalg.lstsq(X, y_true, rcond=None)[0]

    true_sd = np.std(y_true, ddof=1)
    pred_sd = np.std(y_pred, ddof=1)

    true_range = np.percentile(y_true, 95) - np.percentile(y_true, 5)
    pred_range = np.percentile(y_pred, 95) - np.percentile(y_pred, 5)

    return {
        "calibration_intercept": float(beta[0]),
        "calibration_slope": float(beta[1]),
        "prediction_sd_ratio": float(pred_sd / true_sd) if true_sd > 0 else np.nan,
        "prediction_range_ratio_p95_p5": float(pred_range / true_range) if true_range > 0 else np.nan,
    }


def high_response_metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[valid]
    y_pred = y_pred[valid]

    if len(y_true) < 10:
        return {
            "high_response_auc": np.nan,
            "high_response_average_precision": np.nan,
            "high_response_threshold": np.nan,
        }

    threshold = np.percentile(y_true, 75)
    y_high = (y_true >= threshold).astype(int)

    if len(np.unique(y_high)) < 2:
        auc = np.nan
        ap = np.nan
    else:
        auc = float(roc_auc_score(y_high, y_pred))
        ap = float(average_precision_score(y_high, y_pred))

    return {
        "high_response_auc": auc,
        "high_response_average_precision": ap,
        "high_response_threshold": float(threshold),
    }


# ============================================================
# 2. XML parsing
# ============================================================

def collect_events_from_xml(path):
    """
    Generic parser for OhioT1DM-style XML files.

    It collects all <event .../> nodes and records:
    - parent tag, e.g. glucose_level, meal, bolus, basis_heart_rate
    - timestamp
    - numeric attributes if present
    """
    subject_id = extract_subject_id_from_path(path)

    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except Exception as e:
        print(f"Failed to parse XML: {path} | {e}")
        return pd.DataFrame()

    rows = []

    for parent in root.iter():
        parent_tag = str(parent.tag).lower()

        for child in list(parent):
            child_tag = str(child.tag).lower()

            if child_tag != "event":
                continue

            attrs = dict(child.attrib)

            ts = None
            for key in ["ts", "time", "timestamp", "date", "datetime", "date_time"]:
                if key in attrs:
                    ts = attrs.get(key)
                    break

            dt = parse_datetime_any(ts)

            row = {
                "subject_id": str(subject_id),
                "source_file": str(path),
                "parent_tag": parent_tag,
                "timestamp": dt,
            }

            for k, v in attrs.items():
                row[str(k)] = v

            rows.append(row)

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.dropna(subset=["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

    return df


def detect_value_column(df, preferred_keywords):
    """
    Find a numeric-like attribute column.
    """
    if df.empty:
        return None

    candidates = []

    for col in df.columns:
        lc = col.lower()
        if col in ["subject_id", "source_file", "parent_tag", "timestamp"]:
            continue

        for kw in preferred_keywords:
            if kw.lower() in lc:
                candidates.append(col)

    for col in candidates + [c for c in df.columns if c not in candidates]:
        if col in ["subject_id", "source_file", "parent_tag", "timestamp"]:
            continue

        vals = pd.to_numeric(df[col], errors="coerce")
        if vals.notna().sum() > 0:
            return col

    return None


def split_event_tables(events):
    """
    Split generic XML events into glucose, meal, insulin, HR, steps/activity tables.
    """
    out = {}

    if events.empty:
        return out

    tag = events["parent_tag"].astype(str).str.lower()

    glucose_mask = tag.str.contains("glucose") | tag.str.contains("cgm")
    meal_mask = tag.str.contains("meal") | tag.str.contains("carb")
    bolus_mask = tag.str.contains("bolus") | tag.str.contains("insulin")
    hr_mask = tag.str.contains("heart") | tag.str.contains("hr")
    steps_mask = tag.str.contains("step") | tag.str.contains("activity") | tag.str.contains("basis_steps")

    glucose = events[glucose_mask].copy()
    if not glucose.empty:
        value_col = detect_value_column(glucose, ["value", "glucose", "bg"])
        glucose["glucose"] = pd.to_numeric(glucose[value_col], errors="coerce") if value_col else np.nan
        glucose = glucose[["subject_id", "timestamp", "glucose"]].dropna()
        glucose = glucose[(glucose["glucose"] >= 30) & (glucose["glucose"] <= 500)]
        out["glucose"] = glucose.sort_values(["subject_id", "timestamp"]).reset_index(drop=True)

    meal = events[meal_mask].copy()
    if not meal.empty:
        carb_col = detect_value_column(meal, ["carb", "value", "amount"])
        meal["meal_carbs"] = pd.to_numeric(meal[carb_col], errors="coerce") if carb_col else np.nan
        meal = meal[["subject_id", "timestamp", "meal_carbs"]].dropna(subset=["timestamp"])
        meal = meal[meal["meal_carbs"].fillna(0) >= 0]
        out["meal"] = meal.sort_values(["subject_id", "timestamp"]).reset_index(drop=True)

    bolus = events[bolus_mask].copy()
    if not bolus.empty:
        dose_col = detect_value_column(bolus, ["dose", "value", "amount", "normal"])
        bolus["insulin_value"] = pd.to_numeric(bolus[dose_col], errors="coerce") if dose_col else np.nan
        bolus = bolus[["subject_id", "timestamp", "insulin_value"]].dropna()
        bolus = bolus[bolus["insulin_value"] >= 0]
        out["insulin"] = bolus.sort_values(["subject_id", "timestamp"]).reset_index(drop=True)

    hr = events[hr_mask].copy()
    if not hr.empty:
        hr_col = detect_value_column(hr, ["heart", "hr", "value"])
        hr["heart_rate"] = pd.to_numeric(hr[hr_col], errors="coerce") if hr_col else np.nan
        hr = hr[["subject_id", "timestamp", "heart_rate"]].dropna()
        hr = hr[(hr["heart_rate"] >= 30) & (hr["heart_rate"] <= 220)]
        out["heart_rate"] = hr.sort_values(["subject_id", "timestamp"]).reset_index(drop=True)

    steps = events[steps_mask].copy()
    if not steps.empty:
        step_col = detect_value_column(steps, ["step", "value", "activity"])
        steps["steps"] = pd.to_numeric(steps[step_col], errors="coerce") if step_col else np.nan
        steps = steps[["subject_id", "timestamp", "steps"]].dropna()
        steps = steps[steps["steps"] >= 0]
        out["steps"] = steps.sort_values(["subject_id", "timestamp"]).reset_index(drop=True)

    return out


def load_ohio_dataset():
    xml_files = sorted(EXTERNAL_ROOT.rglob("*.xml"))

    if len(xml_files) == 0:
        raise FileNotFoundError(
            f"No XML files found under {EXTERNAL_ROOT}. "
            f"Please place OhioT1DM XML files there."
        )

    print(f"Found XML files: {len(xml_files)}")

    event_parts = []

    for path in xml_files:
        print("Parsing:", path)
        df = collect_events_from_xml(path)
        if not df.empty:
            event_parts.append(df)

    if len(event_parts) == 0:
        raise RuntimeError("No events parsed from XML files.")

    events = pd.concat(event_parts, axis=0, ignore_index=True)
    events.to_csv(TABLES / "external_ohio_all_parsed_events.csv", index=False, encoding="utf-8-sig")

    split = split_event_tables(events)

    for name, table in split.items():
        table.to_csv(TABLES / f"external_ohio_{name}_events.csv", index=False, encoding="utf-8-sig")
        print(f"{name} events:", table.shape)

    if "glucose" not in split or "meal" not in split:
        raise RuntimeError(
            "Could not detect both glucose and meal event tables. "
            "Inspect external_ohio_all_parsed_events.csv and adjust tag parsing."
        )

    return split


# ============================================================
# 3. Meal-level phenotype extraction
# ============================================================

def get_window(df, sid, start, end, time_col="timestamp"):
    sub = df[df["subject_id"].astype(str) == str(sid)].copy()
    return sub[(sub[time_col] >= start) & (sub[time_col] <= end)].copy()


def slope_minutes(times, values):
    if len(values) < 3:
        return np.nan

    t = (pd.to_datetime(times) - pd.to_datetime(times).min()).dt.total_seconds() / 60.0
    y = pd.to_numeric(values, errors="coerce")

    valid = np.isfinite(t) & np.isfinite(y)
    t = np.asarray(t[valid], dtype=float)
    y = np.asarray(y[valid], dtype=float)

    if len(y) < 3 or np.std(t) == 0:
        return np.nan

    return float(np.polyfit(t, y, 1)[0])


def build_external_meal_level(split):
    glucose = split["glucose"].copy()
    meals = split["meal"].copy()

    insulin = split.get("insulin", pd.DataFrame(columns=["subject_id", "timestamp", "insulin_value"]))
    hr = split.get("heart_rate", pd.DataFrame(columns=["subject_id", "timestamp", "heart_rate"]))
    steps = split.get("steps", pd.DataFrame(columns=["subject_id", "timestamp", "steps"]))

    rows = []

    for _, meal in meals.iterrows():
        sid = meal["subject_id"]
        meal_time = pd.to_datetime(meal["timestamp"])
        meal_carbs = to_float_safe(meal.get("meal_carbs", np.nan))

        pre_start = meal_time - pd.Timedelta(minutes=PRE_WINDOW_MIN)
        pre_end = meal_time
        post_start = meal_time
        post_end = meal_time + pd.Timedelta(minutes=POST_WINDOW_MIN)

        g_pre = get_window(glucose, sid, pre_start, pre_end)
        g_post = get_window(glucose, sid, post_start, post_end)

        if len(g_pre) < MIN_PRE_POINTS or len(g_post) < MIN_POST_POINTS:
            continue

        g_pre = g_pre.sort_values("timestamp")
        g_post = g_post.sort_values("timestamp")

        baseline = float(g_pre.tail(3)["glucose"].median())
        pre_mean_30 = float(
            g_pre[g_pre["timestamp"] >= meal_time - pd.Timedelta(minutes=30)]["glucose"].mean()
        )
        pre_sd_30 = float(
            g_pre[g_pre["timestamp"] >= meal_time - pd.Timedelta(minutes=30)]["glucose"].std()
        )
        pre_slope_60 = slope_minutes(g_pre["timestamp"], g_pre["glucose"])

        minutes = (g_post["timestamp"] - meal_time).dt.total_seconds() / 60.0
        delta = g_post["glucose"].values - baseline

        iauc_2h = trapz_auc(minutes, delta)
        peak_delta_2h = float(np.nanmax(delta))
        peak_glucose_2h = float(np.nanmax(g_post["glucose"]))

        bolus_pre2h = np.nan
        if not insulin.empty:
            ins = get_window(
                insulin,
                sid,
                meal_time - pd.Timedelta(minutes=120),
                meal_time + pd.Timedelta(minutes=30),
            )
            if len(ins) > 0:
                bolus_pre2h = float(ins["insulin_value"].sum())

        hr_mean_pre30 = np.nan
        if not hr.empty:
            h = get_window(hr, sid, meal_time - pd.Timedelta(minutes=30), meal_time)
            if len(h) > 0:
                hr_mean_pre30 = float(h["heart_rate"].mean())

        steps_pre30 = np.nan
        if not steps.empty:
            st = get_window(steps, sid, meal_time - pd.Timedelta(minutes=30), meal_time)
            if len(st) > 0:
                steps_pre30 = float(st["steps"].sum())

        hour = meal_time.hour + meal_time.minute / 60.0

        rows.append({
            "subject_id": str(sid),
            "meal_time": meal_time,
            "meal_carbs": meal_carbs,
            "meal_hour": hour,
            "meal_hour_sin": np.sin(2 * np.pi * hour / 24.0),
            "meal_hour_cos": np.cos(2 * np.pi * hour / 24.0),
            "baseline_glucose": baseline,
            "pre_glucose_mean_30": pre_mean_30,
            "pre_glucose_sd_30": pre_sd_30,
            "pre_glucose_slope_60": pre_slope_60,
            "bolus_insulin_pre2h": bolus_pre2h,
            "hr_mean_pre30": hr_mean_pre30,
            "steps_pre30": steps_pre30,
            "iauc_2h": iauc_2h,
            "peak_delta_2h": peak_delta_2h,
            "peak_glucose_2h": peak_glucose_2h,
            "n_pre_points": int(len(g_pre)),
            "n_post_points": int(len(g_post)),
        })

    out = pd.DataFrame(rows)

    if out.empty:
        raise RuntimeError("No valid meal-level records extracted.")

    out = out.sort_values(["subject_id", "meal_time"]).reset_index(drop=True)
    out.to_csv(TABLES / "external_ohio_meal_level_dataset.csv", index=False, encoding="utf-8-sig")

    return out


# ============================================================
# 4. Modeling
# ============================================================

def make_onehot_encoder():
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def make_pipeline(model, numeric_features, categorical_features):
    transformers = []

    if len(numeric_features) > 0:
        transformers.append((
            "num",
            Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]),
            numeric_features,
        ))

    if len(categorical_features) > 0:
        transformers.append((
            "cat",
            Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", make_onehot_encoder()),
            ]),
            categorical_features,
        ))

    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        sparse_threshold=0.0,
    )

    return Pipeline([
        ("preprocess", preprocessor),
        ("model", clone(model)),
    ])


def get_model():
    return HistGradientBoostingRegressor(
        max_iter=300,
        learning_rate=0.03,
        max_leaf_nodes=15,
        random_state=RANDOM_SEED,
    )


def get_feature_sets(df):
    E0 = ["meal_carbs", "meal_hour_sin", "meal_hour_cos"]
    E1 = E0 + [
        "baseline_glucose",
        "pre_glucose_mean_30",
        "pre_glucose_sd_30",
        "pre_glucose_slope_60",
    ]
    E2 = E1 + [
        "bolus_insulin_pre2h",
        "hr_mean_pre30",
        "steps_pre30",
    ]

    feature_sets = {
        "E0_meal_time": [f for f in E0 if f in df.columns and df[f].notna().sum() > 0],
        "E1_meal_time_pre_cgm": [f for f in E1 if f in df.columns and df[f].notna().sum() > 0],
        "E2_plus_insulin_physio": [f for f in E2 if f in df.columns and df[f].notna().sum() > 0],
    }

    # Drop duplicate feature sets if optional features unavailable.
    unique = {}
    seen = set()
    for name, feats in feature_sets.items():
        key = tuple(feats)
        if key not in seen and len(feats) > 0:
            unique[name] = feats
            seen.add(key)

    return unique


def clean_target_data(df, target):
    data = df.copy()
    data = data.dropna(subset=[target, "subject_id", "meal_time"])

    q_low = data[target].quantile(0.01)
    q_high = data[target].quantile(0.99)
    data = data[(data[target] >= q_low) & (data[target] <= q_high)].copy()

    data = data.sort_values(["subject_id", "meal_time"]).reset_index(drop=True)
    return data


def predict_leave_subject_out(data, target, feature_set, feature_name):
    X = data[feature_set]
    y = data[target].values
    groups = data["subject_id"].astype(str).values

    n_subjects = data["subject_id"].nunique()
    n_splits = min(5, n_subjects)

    if n_splits < 2:
        return pd.DataFrame()

    gkf = GroupKFold(n_splits=n_splits)
    model = get_model()

    records = []

    for fold, (train_idx, test_idx) in enumerate(gkf.split(X, y, groups), start=1):
        pipe = make_pipeline(model, feature_set, [])
        pipe.fit(X.iloc[train_idx], y[train_idx])
        pred = pipe.predict(X.iloc[test_idx])

        records.append(pd.DataFrame({
            "subject_id": data.iloc[test_idx]["subject_id"].values,
            "meal_time": data.iloc[test_idx]["meal_time"].values,
            "target": target,
            "feature_set": feature_name,
            "validation": "leave_subject_out",
            "fold": fold,
            "shots": np.nan,
            "y_true": y[test_idx],
            "y_pred": pred,
        }))

    return pd.concat(records, axis=0, ignore_index=True) if records else pd.DataFrame()


def predict_within_subject_temporal(data, target, feature_set, feature_name):
    data = data.sort_values(["subject_id", "meal_time"]).reset_index(drop=True)

    train_idx = []
    test_idx = []

    for sid, sub in data.groupby("subject_id"):
        idx = sub.index.to_numpy()
        if len(idx) < 6:
            continue

        cut = int(np.floor(len(idx) * 0.75))
        cut = max(1, min(cut, len(idx) - 1))

        train_idx.extend(idx[:cut].tolist())
        test_idx.extend(idx[cut:].tolist())

    if len(test_idx) == 0:
        return pd.DataFrame()

    X = data[feature_set]
    y = data[target].values

    train_idx = np.array(train_idx)
    test_idx = np.array(test_idx)

    pipe = make_pipeline(get_model(), feature_set, [])
    pipe.fit(X.iloc[train_idx], y[train_idx])
    pred = pipe.predict(X.iloc[test_idx])

    return pd.DataFrame({
        "subject_id": data.iloc[test_idx]["subject_id"].values,
        "meal_time": data.iloc[test_idx]["meal_time"].values,
        "target": target,
        "feature_set": feature_name,
        "validation": "within_subject_temporal_split",
        "fold": np.nan,
        "shots": np.nan,
        "y_true": y[test_idx],
        "y_pred": pred,
    })


def predict_few_shot(data, target, feature_set, feature_name, shots_list=(0, 1, 3, 5, 10)):
    data = data.sort_values(["subject_id", "meal_time"]).reset_index(drop=True)
    X_all = data[feature_set]
    y_all = data[target].values

    records = []

    for k in shots_list:
        for sid, sub in data.groupby("subject_id"):
            sub = sub.sort_values("meal_time")

            if len(sub) <= k + 3:
                continue

            adaptation = sub.iloc[:k]
            test = sub.iloc[k:]

            train_base = data[data["subject_id"] != sid]

            if k > 0:
                train = pd.concat([train_base, adaptation], axis=0, ignore_index=True)
            else:
                train = train_base

            if train.empty or test.empty:
                continue

            pipe = make_pipeline(get_model(), feature_set, [])
            pipe.fit(train[feature_set], train[target].values)
            pred = pipe.predict(test[feature_set])

            records.append(pd.DataFrame({
                "subject_id": test["subject_id"].values,
                "meal_time": test["meal_time"].values,
                "target": target,
                "feature_set": feature_name,
                "validation": "few_shot_personalization",
                "fold": np.nan,
                "shots": int(k),
                "y_true": test[target].values,
                "y_pred": pred,
            }))

    return pd.concat(records, axis=0, ignore_index=True) if records else pd.DataFrame()


# ============================================================
# 5. Summaries
# ============================================================

def subject_bootstrap_metrics(df, n_bootstrap=N_BOOTSTRAP, seed=RANDOM_SEED):
    rng = np.random.default_rng(seed)

    subject_ids = np.array(sorted(df["subject_id"].dropna().unique()))
    n_subjects = len(subject_ids)

    point = compute_metrics(df["y_true"], df["y_pred"])
    cal = calibration_metrics(df["y_true"], df["y_pred"])
    high = high_response_metrics(df["y_true"], df["y_pred"])

    summary = {**point, **cal, **high}
    summary["n_subjects"] = int(n_subjects)
    summary["n_meals"] = int(len(df))
    summary["n_bootstrap"] = int(n_bootstrap)

    metrics_for_ci = [
        "MAE", "RMSE", "R2", "Pearson_r",
        "calibration_slope", "prediction_sd_ratio",
        "prediction_range_ratio_p95_p5",
        "high_response_auc", "high_response_average_precision",
    ]

    if n_subjects < 3:
        for m in metrics_for_ci:
            summary[f"{m}_ci_lower"] = np.nan
            summary[f"{m}_ci_upper"] = np.nan
        return summary

    grouped = {sid: df[df["subject_id"] == sid] for sid in subject_ids}
    boot_rows = []

    for _ in range(n_bootstrap):
        sampled_sids = rng.choice(subject_ids, size=n_subjects, replace=True)
        sampled = pd.concat([grouped[sid] for sid in sampled_sids], axis=0, ignore_index=True)

        m = compute_metrics(sampled["y_true"], sampled["y_pred"])
        c = calibration_metrics(sampled["y_true"], sampled["y_pred"])
        h = high_response_metrics(sampled["y_true"], sampled["y_pred"])
        boot_rows.append({**m, **c, **h})

    boot = pd.DataFrame(boot_rows)

    for m in metrics_for_ci:
        vals = boot[m].astype(float).replace([np.inf, -np.inf], np.nan).dropna()
        if len(vals) == 0:
            summary[f"{m}_ci_lower"] = np.nan
            summary[f"{m}_ci_upper"] = np.nan
        else:
            summary[f"{m}_ci_lower"] = float(np.percentile(vals, 2.5))
            summary[f"{m}_ci_upper"] = float(np.percentile(vals, 97.5))

    return summary


def summarize_predictions(pred_records):
    rows = []

    group_cols = ["target", "feature_set", "validation", "shots"]

    for keys, sub in pred_records.groupby(group_cols, dropna=False):
        target, feature_set, validation, shots = keys

        summary = subject_bootstrap_metrics(sub)

        summary.update({
            "target": target,
            "target_label": TARGET_LABELS.get(target, target),
            "unit": TARGET_UNITS.get(target, ""),
            "feature_set": feature_set,
            "validation": validation,
            "shots": shots,
        })

        rows.append(summary)

    out = pd.DataFrame(rows)
    out = out.sort_values(["target", "validation", "feature_set", "shots"], na_position="first")
    return out


def make_main_summary(meal_df, perf):
    rows = []

    rows.append({
        "section": "external_dataset",
        "finding": "Meal-level external dataset",
        "value": (
            f"n_subjects={meal_df['subject_id'].nunique()}, "
            f"n_meals={len(meal_df)}, "
            f"median_meals_per_subject={meal_df.groupby('subject_id').size().median():.1f}"
        ),
    })

    for target in TARGETS:
        for validation in ["within_subject_temporal_split", "leave_subject_out"]:
            sub = perf[
                (perf["target"] == target)
                & (perf["validation"] == validation)
            ].copy()

            if sub.empty:
                continue

            best = sub.sort_values("MAE").head(1).iloc[0]

            rows.append({
                "section": "external_prediction",
                "finding": f"Best {validation} performance for {TARGET_LABELS[target]}",
                "value": (
                    f"feature_set={best['feature_set']}, "
                    f"MAE={best['MAE']:.2f}, r={best['Pearson_r']:.3f}, "
                    f"high_response_auc={best['high_response_auc']:.3f}, "
                    f"sd_ratio={best['prediction_sd_ratio']:.3f}"
                ),
            })

        fs = perf[
            (perf["target"] == target)
            & (perf["validation"] == "few_shot_personalization")
        ].copy()

        if not fs.empty:
            # Use the richest available feature set.
            richest = fs["feature_set"].iloc[-1]
            fsub = fs[fs["feature_set"] == richest].copy()

            s0 = fsub[fsub["shots"] == 0]
            s10 = fsub[fsub["shots"] == 10]

            if not s0.empty and not s10.empty:
                s0 = s0.iloc[0]
                s10 = s10.iloc[0]

                rows.append({
                    "section": "external_fewshot",
                    "finding": f"0-shot to 10-shot change for {TARGET_LABELS[target]}",
                    "value": (
                        f"feature_set={richest}, "
                        f"MAE_0shot={s0['MAE']:.2f}, MAE_10shot={s10['MAE']:.2f}, "
                        f"delta_MAE={s0['MAE'] - s10['MAE']:.2f}, "
                        f"r_0shot={s0['Pearson_r']:.3f}, r_10shot={s10['Pearson_r']:.3f}"
                    ),
                })

    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "external_validation_main_summary.csv", index=False, encoding="utf-8-sig")
    return out


# ============================================================
# 6. Figures
# ============================================================

def plot_performance(perf):
    for target in TARGETS:
        sub = perf[
            (perf["target"] == target)
            & (perf["validation"].isin(["leave_subject_out", "within_subject_temporal_split"]))
        ].copy()

        if sub.empty:
            continue

        fig, ax = plt.subplots(figsize=(8, 5))

        for validation in ["leave_subject_out", "within_subject_temporal_split"]:
            s = sub[sub["validation"] == validation].copy()
            if s.empty:
                continue

            s = s.sort_values("feature_set")
            x = np.arange(len(s))
            offset = -0.08 if validation == "leave_subject_out" else 0.08

            ax.plot(
                x + offset,
                s["MAE"],
                marker="o",
                label=validation,
            )

        labels = sorted(sub["feature_set"].unique())
        ax.set_xticks(np.arange(len(labels)))
        ax.set_xticklabels(labels, rotation=20, ha="right")
        ax.set_ylabel(f"MAE ({TARGET_UNITS[target]})")
        ax.set_title(f"External validation feature-set performance\n{TARGET_LABELS[target]}")
        ax.legend()
        fig.tight_layout()

        fig.savefig(FIGURES / f"external_performance_{target}.png", dpi=300, bbox_inches="tight")
        plt.close(fig)


def plot_fewshot(perf):
    for target in TARGETS:
        fs = perf[
            (perf["target"] == target)
            & (perf["validation"] == "few_shot_personalization")
        ].copy()

        if fs.empty:
            continue

        # Plot richest feature set only.
        richest = sorted(fs["feature_set"].unique())[-1]
        sub = fs[fs["feature_set"] == richest].copy()
        sub = sub.sort_values("shots")

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.plot(sub["shots"], sub["MAE"], marker="o")
        ax.set_xlabel("Subject-specific adaptation meals")
        ax.set_ylabel(f"MAE ({TARGET_UNITS[target]})")
        ax.set_title(f"External few-shot personalization\n{TARGET_LABELS[target]} | {richest}")

        fig.tight_layout()
        fig.savefig(FIGURES / f"external_fewshot_{target}.png", dpi=300, bbox_inches="tight")
        plt.close(fig)


def plot_scatter(pred_records):
    for target in TARGETS:
        sub = pred_records[
            (pred_records["target"] == target)
            & (pred_records["validation"] == "within_subject_temporal_split")
        ].copy()

        if sub.empty:
            continue

        # richest feature set
        richest = sorted(sub["feature_set"].unique())[-1]
        sub = sub[sub["feature_set"] == richest].copy()

        fig, ax = plt.subplots(figsize=(6, 6))
        ax.scatter(sub["y_true"], sub["y_pred"], alpha=0.4, s=18)

        mn = np.nanmin([sub["y_true"].min(), sub["y_pred"].min()])
        mx = np.nanmax([sub["y_true"].max(), sub["y_pred"].max()])
        ax.plot([mn, mx], [mn, mx], linestyle="--", linewidth=1)

        ax.set_xlabel(f"Observed {TARGET_LABELS[target]} ({TARGET_UNITS[target]})")
        ax.set_ylabel(f"Predicted {TARGET_LABELS[target]} ({TARGET_UNITS[target]})")
        ax.set_title(f"External predicted vs observed\n{TARGET_LABELS[target]} | {richest}")

        fig.tight_layout()
        fig.savefig(FIGURES / f"external_pred_vs_obs_{target}.png", dpi=300, bbox_inches="tight")
        plt.close(fig)


# ============================================================
# 7. Main
# ============================================================

def main():
    print("Loading OhioT1DM-style XML data...")
    split = load_ohio_dataset()

    print("\nBuilding external meal-level dataset...")
    meal_df = build_external_meal_level(split)

    print("\nExternal meal-level dataset:")
    print(meal_df.shape)
    print("Subjects:", meal_df["subject_id"].nunique())
    print(meal_df.head())

    feature_sets = get_feature_sets(meal_df)

    print("\nExternal feature sets:")
    for name, feats in feature_sets.items():
        print(name, ":", feats)

    all_preds = []

    for target in TARGETS:
        print("\n" + "=" * 90)
        print("Target:", target)
        print("=" * 90)

        data = clean_target_data(meal_df, target)

        print("Data shape:", data.shape)
        print("Subjects:", data["subject_id"].nunique())

        for fs_name, feats in feature_sets.items():
            print("Feature set:", fs_name)

            p1 = predict_leave_subject_out(data, target, feats, fs_name)
            p2 = predict_within_subject_temporal(data, target, feats, fs_name)
            p3 = predict_few_shot(data, target, feats, fs_name)

            for p in [p1, p2, p3]:
                if not p.empty:
                    all_preds.append(p)

    if len(all_preds) == 0:
        raise RuntimeError("No external prediction records generated.")

    pred_records = pd.concat(all_preds, axis=0, ignore_index=True)
    pred_records.to_csv(TABLES / "external_ohio_prediction_records.csv", index=False, encoding="utf-8-sig")

    print("\nSummarizing external predictions...")
    perf = summarize_predictions(pred_records)
    perf.to_csv(TABLES / "external_ohio_performance_summary.csv", index=False, encoding="utf-8-sig")

    main_summary = make_main_summary(meal_df, perf)

    print("\nGenerating figures...")
    plot_performance(perf)
    plot_fewshot(perf)
    plot_scatter(pred_records)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 260)
    pd.set_option("display.max_rows", 300)

    print("\nSaved tables:")
    print(TABLES / "external_ohio_all_parsed_events.csv")
    print(TABLES / "external_ohio_meal_level_dataset.csv")
    print(TABLES / "external_ohio_prediction_records.csv")
    print(TABLES / "external_ohio_performance_summary.csv")
    print(TABLES / "external_validation_main_summary.csv")

    print("\nPerformance summary:")
    print(perf)

    print("\nMain summary:")
    print(main_summary)

    print("\nFigures saved to:")
    print(FIGURES)

    print("\nDone.")


if __name__ == "__main__":
    main()