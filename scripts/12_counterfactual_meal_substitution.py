# -*- coding: utf-8 -*-
"""
12_counterfactual_meal_substitution.py

Enhancement 5: Counterfactual meal substitution

Goals:
1. Train the M3 clinical-enhanced HGB model on the cleaned meal-level dataset.
2. Simulate realistic model-based meal substitution scenarios.
3. Estimate predicted changes in postprandial glucose outcomes.
4. Quantify heterogeneity across subjects and meal-risk strata.
5. Use subject-level bootstrap to estimate uncertainty for mean predicted changes.

Important:
This is a model-based counterfactual simulation, not a causal intervention study.
Results should be interpreted as hypothesis-generating.

Inputs:
- outputs/tables/meal_level_dataset.csv

Outputs:
- outputs/tables/counterfactual_meal_level_predictions.csv
- outputs/tables/counterfactual_scenario_summary.csv
- outputs/tables/counterfactual_subject_summary.csv
- outputs/tables/counterfactual_subgroup_summary.csv
- outputs/tables/counterfactual_bootstrap_summary.csv
- outputs/tables/counterfactual_top_benefit_meals.csv
- outputs/tables/counterfactual_main_summary.csv
- outputs/figures/counterfactual_mean_delta_*.png
- outputs/figures/counterfactual_percent_meals_reduced_*.png
- outputs/figures/counterfactual_subject_heterogeneity_*.png
- outputs/figures/counterfactual_high_risk_delta_*.png
"""

from pathlib import Path
import re
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

try:
    from sklearn.preprocessing import OneHotEncoder
except Exception as e:
    raise ImportError("scikit-learn OneHotEncoder import failed.") from e

warnings.filterwarnings("ignore")


# ============================================================
# 0. Paths and parameters
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

DATA_PATH = TABLES / "meal_level_dataset.csv"

TARGETS = ["iauc_2h", "peak_delta_2h"]

MODEL_NAME = "hist_gradient_boosting"
FEATURE_SET_NAME = "M3_clinical_enhanced"

N_BOOTSTRAP = 200
RANDOM_SEED = 42
RUN_BOOTSTRAP = True

TARGET_LABELS = {
    "iauc_2h": "2-h glucose iAUC",
    "peak_delta_2h": "2-h peak glucose excursion",
}

TARGET_UNITS = {
    "iauc_2h": "mg/dL*min",
    "peak_delta_2h": "mg/dL",
}


# ============================================================
# 1. M3 feature definition
# ============================================================

MEAL_FEATURES = [
    "eff_calories",
    "eff_carbs",
    "eff_protein",
    "eff_fat",
    "eff_fiber",
]

PRE_CGM_FEATURES = [
    "baseline_glucose",
    "pre_glucose_mean_30",
    "pre_glucose_sd_30",
    "pre_glucose_slope_60",
]

WEARABLE_TIME_FEATURES = [
    "hr_mean_pre30",
    "activity_calories_pre30",
    "mets_mean_pre30",
    "meal_hour_sin",
    "meal_hour_cos",
    "prev_meal_gap_min",
]

CLINICAL_NUMERIC_FEATURES = [
    "Age",
    "BMI",
    "Body weight",
    "Height",
    "A1c PDL (Lab)",
    "Fasting GLU - PDL (Lab)",
    "Insulin",
    "Triglycerides",
    "Cholesterol",
    "HDL",
    "Non HDL",
    "LDL (Cal)",
    "VLDL (Cal)",
    "Cho/HDL Ratio",
]

MEAL_CATEGORICAL_FEATURES = [
    "meal_type",
]

CLINICAL_CATEGORICAL_FEATURES = [
    "Gender",
]

NUMERIC_FEATURES_M3 = (
    MEAL_FEATURES
    + PRE_CGM_FEATURES
    + WEARABLE_TIME_FEATURES
    + CLINICAL_NUMERIC_FEATURES
)

CATEGORICAL_FEATURES_M3 = (
    MEAL_CATEGORICAL_FEATURES
    + CLINICAL_CATEGORICAL_FEATURES
)


# ============================================================
# 2. Utility functions
# ============================================================

def make_onehot_encoder():
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def make_pipeline(model, numeric_features, categorical_features):
    transformers = []

    if len(numeric_features) > 0:
        numeric_transformer = Pipeline(steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])
        transformers.append(("num", numeric_transformer, numeric_features))

    if len(categorical_features) > 0:
        categorical_transformer = Pipeline(steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", make_onehot_encoder()),
        ])
        transformers.append(("cat", categorical_transformer, categorical_features))

    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        sparse_threshold=0.0,
    )

    pipe = Pipeline(steps=[
        ("preprocess", preprocessor),
        ("model", clone(model)),
    ])

    return pipe


def get_model():
    return HistGradientBoostingRegressor(
        max_iter=400,
        learning_rate=0.03,
        max_leaf_nodes=31,
        random_state=42,
    )


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

    if np.nanstd(y_true) == 0 or np.nanstd(y_pred) == 0:
        return np.nan

    return float(np.corrcoef(y_true, y_pred)[0, 1])


def compute_basic_metrics(y_true, y_pred):
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
        }

    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": rmse(y_true, y_pred),
        "R2": float(r2_score(y_true, y_pred)),
        "Pearson_r": pearson_r(y_true, y_pred),
    }


def safe_numeric(df, cols):
    df = df.copy()
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def available_features(df, features):
    out = []
    for f in features:
        if f in df.columns:
            out.append(f)
    return out


def clean_target_dataset(df, target):
    data = df.copy()

    data = data.dropna(subset=[target, "subject_id"])

    q_low = data[target].quantile(0.01)
    q_high = data[target].quantile(0.99)
    data = data[(data[target] >= q_low) & (data[target] <= q_high)].copy()

    data["subject_id"] = data["subject_id"].astype(int)

    if "meal_time" in data.columns:
        data["meal_time"] = pd.to_datetime(data["meal_time"], errors="coerce")
    else:
        data["meal_time"] = pd.NaT

    return data.reset_index(drop=True)


def clip_nonnegative(df, cols):
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
            df[c] = df[c].clip(lower=0)
    return df


def set_meal_hour(df, hour):
    df = df.copy()

    hour = float(hour)

    if "meal_hour" in df.columns:
        df["meal_hour"] = hour

    if "meal_hour_sin" in df.columns:
        df["meal_hour_sin"] = np.sin(2 * np.pi * hour / 24.0)

    if "meal_hour_cos" in df.columns:
        df["meal_hour_cos"] = np.cos(2 * np.pi * hour / 24.0)

    return df


def make_subgroup_columns(df):
    df = df.copy()

    if "BMI" in df.columns:
        df["BMI"] = pd.to_numeric(df["BMI"], errors="coerce")
        df["subgroup_bmi_30"] = pd.Series(pd.NA, index=df.index, dtype="object")
        mask = df["BMI"].notna()
        df.loc[mask & (df["BMI"] < 30), "subgroup_bmi_30"] = "BMI <30"
        df.loc[mask & (df["BMI"] >= 30), "subgroup_bmi_30"] = "BMI >=30"

    if "A1c PDL (Lab)" in df.columns:
        df["A1c PDL (Lab)"] = pd.to_numeric(df["A1c PDL (Lab)"], errors="coerce")
        df["subgroup_hba1c_category"] = pd.Series(pd.NA, index=df.index, dtype="object")
        a = df["A1c PDL (Lab)"]
        df.loc[a.notna() & (a < 5.7), "subgroup_hba1c_category"] = "<5.7"
        df.loc[a.notna() & (a >= 5.7) & (a < 6.5), "subgroup_hba1c_category"] = "5.7-6.4"
        df.loc[a.notna() & (a >= 6.5), "subgroup_hba1c_category"] = ">=6.5"

    if "Fasting GLU - PDL (Lab)" in df.columns:
        df["Fasting GLU - PDL (Lab)"] = pd.to_numeric(
            df["Fasting GLU - PDL (Lab)"],
            errors="coerce",
        )
        df["subgroup_fasting_glucose_category"] = pd.Series(pd.NA, index=df.index, dtype="object")
        g = df["Fasting GLU - PDL (Lab)"]
        df.loc[g.notna() & (g < 100), "subgroup_fasting_glucose_category"] = "<100"
        df.loc[g.notna() & (g >= 100) & (g < 126), "subgroup_fasting_glucose_category"] = "100-125"
        df.loc[g.notna() & (g >= 126), "subgroup_fasting_glucose_category"] = ">=126"

    return df


# ============================================================
# 3. Counterfactual scenario definitions
# ============================================================

def scenario_no_change(df):
    return df.copy()


def scenario_carb_minus_20_energy_reduced(df):
    """
    Reduce effective carbohydrate by 20%.
    Total effective calories are reduced by 4 kcal per gram of carbohydrate removed.
    """
    out = df.copy()

    if "eff_carbs" not in out.columns:
        return out

    carbs = pd.to_numeric(out["eff_carbs"], errors="coerce").fillna(0)
    removed_carbs = 0.20 * carbs

    out["eff_carbs"] = carbs - removed_carbs

    if "eff_calories" in out.columns:
        kcal = pd.to_numeric(out["eff_calories"], errors="coerce")
        out["eff_calories"] = kcal - 4.0 * removed_carbs

    return clip_nonnegative(out, ["eff_calories", "eff_carbs"])


def scenario_carb_minus_20_to_protein_isocaloric(df):
    """
    Replace 20% of effective carbohydrate grams with protein grams.
    Approximate isocaloric swap: 1 g carbohydrate = 1 g protein = 4 kcal.
    """
    out = df.copy()

    if "eff_carbs" not in out.columns:
        return out

    carbs = pd.to_numeric(out["eff_carbs"], errors="coerce").fillna(0)
    removed_carbs = 0.20 * carbs

    out["eff_carbs"] = carbs - removed_carbs

    if "eff_protein" in out.columns:
        protein = pd.to_numeric(out["eff_protein"], errors="coerce").fillna(0)
        out["eff_protein"] = protein + removed_carbs

    return clip_nonnegative(out, ["eff_carbs", "eff_protein"])


def scenario_carb_minus_20_to_fat_isocaloric(df):
    """
    Replace 20% of effective carbohydrate energy with fat energy.
    4 kcal per gram carbohydrate; 9 kcal per gram fat.
    """
    out = df.copy()

    if "eff_carbs" not in out.columns:
        return out

    carbs = pd.to_numeric(out["eff_carbs"], errors="coerce").fillna(0)
    removed_carbs = 0.20 * carbs
    added_fat = removed_carbs * 4.0 / 9.0

    out["eff_carbs"] = carbs - removed_carbs

    if "eff_fat" in out.columns:
        fat = pd.to_numeric(out["eff_fat"], errors="coerce").fillna(0)
        out["eff_fat"] = fat + added_fat

    return clip_nonnegative(out, ["eff_carbs", "eff_fat"])


def scenario_fiber_plus_5(df):
    """
    Add 5 g effective fiber.
    Calories are left unchanged because this is a simplified fiber-enrichment scenario.
    """
    out = df.copy()

    if "eff_fiber" in out.columns:
        fiber = pd.to_numeric(out["eff_fiber"], errors="coerce").fillna(0)
        out["eff_fiber"] = fiber + 5.0

    return clip_nonnegative(out, ["eff_fiber"])


def scenario_protein_plus_10_energy_added(df):
    """
    Add 10 g protein and 40 kcal.
    """
    out = df.copy()

    if "eff_protein" in out.columns:
        protein = pd.to_numeric(out["eff_protein"], errors="coerce").fillna(0)
        out["eff_protein"] = protein + 10.0

    if "eff_calories" in out.columns:
        kcal = pd.to_numeric(out["eff_calories"], errors="coerce")
        out["eff_calories"] = kcal + 40.0

    return clip_nonnegative(out, ["eff_protein", "eff_calories"])


def scenario_cap_carbs_60g_energy_reduced(df):
    """
    Cap effective carbohydrates at 60 g.
    If carbs are reduced, calories are reduced accordingly.
    This primarily affects high-carbohydrate meals.
    """
    out = df.copy()

    if "eff_carbs" not in out.columns:
        return out

    carbs = pd.to_numeric(out["eff_carbs"], errors="coerce").fillna(0)
    capped = carbs.clip(upper=60.0)
    removed = carbs - capped

    out["eff_carbs"] = capped

    if "eff_calories" in out.columns:
        kcal = pd.to_numeric(out["eff_calories"], errors="coerce")
        out["eff_calories"] = kcal - 4.0 * removed

    return clip_nonnegative(out, ["eff_carbs", "eff_calories"])


def scenario_cap_carbs_45g_energy_reduced(df):
    """
    Cap effective carbohydrates at 45 g.
    More aggressive than the 60 g cap.
    """
    out = df.copy()

    if "eff_carbs" not in out.columns:
        return out

    carbs = pd.to_numeric(out["eff_carbs"], errors="coerce").fillna(0)
    capped = carbs.clip(upper=45.0)
    removed = carbs - capped

    out["eff_carbs"] = capped

    if "eff_calories" in out.columns:
        kcal = pd.to_numeric(out["eff_calories"], errors="coerce")
        out["eff_calories"] = kcal - 4.0 * removed

    return clip_nonnegative(out, ["eff_carbs", "eff_calories"])


def scenario_evening_to_noon_if_late(df):
    """
    If a meal occurs after 18:00, shift timing features to noon.
    Food composition is unchanged.

    This is not a meal substitution; it is a timing counterfactual.
    It is included as an exploratory behavior-timing scenario.
    """
    out = df.copy()

    if "meal_hour" not in out.columns:
        return out

    h = pd.to_numeric(out["meal_hour"], errors="coerce")
    late_mask = h >= 18.0

    if late_mask.sum() == 0:
        return out

    out.loc[late_mask, "meal_hour"] = 12.0

    if "meal_hour_sin" in out.columns:
        out.loc[late_mask, "meal_hour_sin"] = np.sin(2 * np.pi * 12.0 / 24.0)

    if "meal_hour_cos" in out.columns:
        out.loc[late_mask, "meal_hour_cos"] = np.cos(2 * np.pi * 12.0 / 24.0)

    return out


SCENARIOS = {
    "S0_no_change": {
        "label": "No change",
        "type": "reference",
        "function": scenario_no_change,
        "description": "Reference prediction using observed meal features.",
    },
    "S1_carb_minus_20_energy_reduced": {
        "label": "Carb -20%, energy reduced",
        "type": "meal_substitution",
        "function": scenario_carb_minus_20_energy_reduced,
        "description": "Reduce effective carbohydrates by 20%; reduce calories by 4 kcal/g carbohydrate removed.",
    },
    "S2_carb_minus_20_to_protein_isocaloric": {
        "label": "Carb -20% to protein, isocaloric",
        "type": "meal_substitution",
        "function": scenario_carb_minus_20_to_protein_isocaloric,
        "description": "Replace 20% of carbohydrate grams with protein grams at equal energy.",
    },
    "S3_carb_minus_20_to_fat_isocaloric": {
        "label": "Carb -20% to fat, isocaloric",
        "type": "meal_substitution",
        "function": scenario_carb_minus_20_to_fat_isocaloric,
        "description": "Replace 20% of carbohydrate energy with fat energy.",
    },
    "S4_fiber_plus_5": {
        "label": "Fiber +5 g",
        "type": "meal_substitution",
        "function": scenario_fiber_plus_5,
        "description": "Increase effective fiber by 5 g; keep energy unchanged.",
    },
    "S5_protein_plus_10_energy_added": {
        "label": "Protein +10 g, energy added",
        "type": "meal_substitution",
        "function": scenario_protein_plus_10_energy_added,
        "description": "Add 10 g protein and 40 kcal.",
    },
    "S6_cap_carbs_60g_energy_reduced": {
        "label": "Cap carbs at 60 g",
        "type": "meal_substitution",
        "function": scenario_cap_carbs_60g_energy_reduced,
        "description": "Cap effective carbohydrates at 60 g; reduce energy accordingly.",
    },
    "S7_cap_carbs_45g_energy_reduced": {
        "label": "Cap carbs at 45 g",
        "type": "meal_substitution",
        "function": scenario_cap_carbs_45g_energy_reduced,
        "description": "Cap effective carbohydrates at 45 g; reduce energy accordingly.",
    },
    "S8_late_meal_to_noon_exploratory": {
        "label": "Late meal to noon",
        "type": "timing_exploratory",
        "function": scenario_evening_to_noon_if_late,
        "description": "For meals after 18:00, shift timing features to noon; food unchanged.",
    },
}


# ============================================================
# 4. Model-based counterfactual prediction
# ============================================================

def fit_target_model(data, target, numeric_features, categorical_features):
    features = numeric_features + categorical_features
    X = data[features]
    y = data[target].values

    model = get_model()
    pipe = make_pipeline(model, numeric_features, categorical_features)
    pipe.fit(X, y)

    return pipe


def predict_counterfactuals_for_target(data, target, numeric_features, categorical_features):
    features = numeric_features + categorical_features

    pipe = fit_target_model(data, target, numeric_features, categorical_features)

    base_X = data[features]
    base_pred = pipe.predict(base_X)

    records = []

    for scenario_id, spec in SCENARIOS.items():
        if scenario_id == "S0_no_change":
            cf_data = data.copy()
        else:
            cf_data = spec["function"](data.copy())

        cf_X = cf_data[features]
        cf_pred = pipe.predict(cf_X)

        temp = pd.DataFrame({
            "subject_id": data["subject_id"].values,
            "meal_time": data["meal_time"].values,
            "target": target,
            "target_label": TARGET_LABELS.get(target, target),
            "scenario_id": scenario_id,
            "scenario_label": spec["label"],
            "scenario_type": spec["type"],
            "scenario_description": spec["description"],
            "y_observed": data[target].values,
            "y_pred_baseline": base_pred,
            "y_pred_counterfactual": cf_pred,
        })

        temp["delta_pred"] = temp["y_pred_counterfactual"] - temp["y_pred_baseline"]
        temp["predicted_reduction"] = -temp["delta_pred"]
        temp["is_predicted_reduction"] = temp["delta_pred"] < 0

        denom = np.abs(temp["y_pred_baseline"].values) + 1e-8
        temp["relative_delta_percent"] = temp["delta_pred"] / denom * 100.0
        temp["relative_reduction_percent"] = -temp["relative_delta_percent"]

        # Keep selected original features for interpretation.
        keep_features = [
            "meal_type",
            "eff_calories",
            "eff_carbs",
            "eff_protein",
            "eff_fat",
            "eff_fiber",
            "baseline_glucose",
            "pre_glucose_mean_30",
            "pre_glucose_slope_60",
            "prev_meal_gap_min",
            "meal_hour",
            "BMI",
            "A1c PDL (Lab)",
            "Fasting GLU - PDL (Lab)",
            "Gender",
        ]

        for col in keep_features:
            if col in data.columns:
                temp[col] = data[col].values

        records.append(temp)

    out = pd.concat(records, axis=0, ignore_index=True)

    return out


# ============================================================
# 5. Summary tables
# ============================================================

def summarize_scenarios(cf_records):
    rows = []

    for (target, scenario_id), sub in cf_records.groupby(["target", "scenario_id"]):
        if scenario_id == "S0_no_change":
            continue

        q75_baseline = np.nanpercentile(
            cf_records[
                (cf_records["target"] == target)
                & (cf_records["scenario_id"] == "S0_no_change")
            ]["y_pred_baseline"],
            75,
        )

        high_risk = sub[sub["y_pred_baseline"] >= q75_baseline]

        rows.append({
            "target": target,
            "target_label": TARGET_LABELS.get(target, target),
            "unit": TARGET_UNITS.get(target, ""),
            "scenario_id": scenario_id,
            "scenario_label": sub["scenario_label"].iloc[0],
            "scenario_type": sub["scenario_type"].iloc[0],
            "scenario_description": sub["scenario_description"].iloc[0],
            "n_meals": int(len(sub)),
            "n_subjects": int(sub["subject_id"].nunique()),
            "mean_baseline_prediction": float(np.nanmean(sub["y_pred_baseline"])),
            "mean_counterfactual_prediction": float(np.nanmean(sub["y_pred_counterfactual"])),
            "mean_delta_pred": float(np.nanmean(sub["delta_pred"])),
            "median_delta_pred": float(np.nanmedian(sub["delta_pred"])),
            "q25_delta_pred": float(np.nanpercentile(sub["delta_pred"], 25)),
            "q75_delta_pred": float(np.nanpercentile(sub["delta_pred"], 75)),
            "mean_predicted_reduction": float(np.nanmean(sub["predicted_reduction"])),
            "median_predicted_reduction": float(np.nanmedian(sub["predicted_reduction"])),
            "percent_meals_with_predicted_reduction": float(np.mean(sub["is_predicted_reduction"]) * 100.0),
            "mean_relative_reduction_percent": float(np.nanmean(sub["relative_reduction_percent"])),
            "median_relative_reduction_percent": float(np.nanmedian(sub["relative_reduction_percent"])),
            "high_risk_n_meals": int(len(high_risk)),
            "high_risk_mean_delta_pred": float(np.nanmean(high_risk["delta_pred"])) if len(high_risk) else np.nan,
            "high_risk_mean_predicted_reduction": float(np.nanmean(high_risk["predicted_reduction"])) if len(high_risk) else np.nan,
            "high_risk_percent_meals_with_predicted_reduction": float(np.mean(high_risk["is_predicted_reduction"]) * 100.0) if len(high_risk) else np.nan,
        })

    out = pd.DataFrame(rows)

    if not out.empty:
        out = out.sort_values(["target", "mean_delta_pred"]).reset_index(drop=True)

    out.to_csv(TABLES / "counterfactual_scenario_summary.csv", index=False, encoding="utf-8-sig")

    return out


def summarize_by_subject(cf_records):
    rows = []

    for (target, scenario_id, sid), sub in cf_records.groupby(["target", "scenario_id", "subject_id"]):
        if scenario_id == "S0_no_change":
            continue

        rows.append({
            "target": target,
            "target_label": TARGET_LABELS.get(target, target),
            "unit": TARGET_UNITS.get(target, ""),
            "scenario_id": scenario_id,
            "scenario_label": sub["scenario_label"].iloc[0],
            "subject_id": int(sid),
            "n_meals": int(len(sub)),
            "mean_baseline_prediction": float(np.nanmean(sub["y_pred_baseline"])),
            "mean_counterfactual_prediction": float(np.nanmean(sub["y_pred_counterfactual"])),
            "mean_delta_pred": float(np.nanmean(sub["delta_pred"])),
            "median_delta_pred": float(np.nanmedian(sub["delta_pred"])),
            "mean_predicted_reduction": float(np.nanmean(sub["predicted_reduction"])),
            "percent_meals_with_predicted_reduction": float(np.mean(sub["is_predicted_reduction"]) * 100.0),
            "mean_relative_reduction_percent": float(np.nanmean(sub["relative_reduction_percent"])),
        })

    out = pd.DataFrame(rows)

    if not out.empty:
        out = out.sort_values(["target", "scenario_id", "mean_delta_pred"]).reset_index(drop=True)

    out.to_csv(TABLES / "counterfactual_subject_summary.csv", index=False, encoding="utf-8-sig")

    return out


def summarize_by_subgroup(cf_records):
    subgroup_vars = [
        "subgroup_bmi_30",
        "subgroup_hba1c_category",
        "subgroup_fasting_glucose_category",
        "Gender",
    ]

    rows = []

    temp = make_subgroup_columns(cf_records)

    for subgroup_var in subgroup_vars:
        if subgroup_var not in temp.columns:
            continue

        for (target, scenario_id, level), sub in temp.groupby(["target", "scenario_id", subgroup_var], dropna=True):
            if scenario_id == "S0_no_change":
                continue

            if pd.isna(level):
                continue

            rows.append({
                "target": target,
                "target_label": TARGET_LABELS.get(target, target),
                "unit": TARGET_UNITS.get(target, ""),
                "scenario_id": scenario_id,
                "scenario_label": sub["scenario_label"].iloc[0],
                "subgroup_variable": subgroup_var,
                "subgroup_level": str(level),
                "n_meals": int(len(sub)),
                "n_subjects": int(sub["subject_id"].nunique()),
                "mean_delta_pred": float(np.nanmean(sub["delta_pred"])),
                "median_delta_pred": float(np.nanmedian(sub["delta_pred"])),
                "mean_predicted_reduction": float(np.nanmean(sub["predicted_reduction"])),
                "percent_meals_with_predicted_reduction": float(np.mean(sub["is_predicted_reduction"]) * 100.0),
                "mean_relative_reduction_percent": float(np.nanmean(sub["relative_reduction_percent"])),
            })

    out = pd.DataFrame(rows)

    if not out.empty:
        out = out.sort_values(
            ["target", "scenario_id", "subgroup_variable", "subgroup_level"]
        ).reset_index(drop=True)

    out.to_csv(TABLES / "counterfactual_subgroup_summary.csv", index=False, encoding="utf-8-sig")

    return out


def make_top_benefit_meals(cf_records):
    cols = [
        "target",
        "scenario_id",
        "scenario_label",
        "subject_id",
        "meal_time",
        "meal_type",
        "y_observed",
        "y_pred_baseline",
        "y_pred_counterfactual",
        "delta_pred",
        "predicted_reduction",
        "relative_reduction_percent",
        "eff_calories",
        "eff_carbs",
        "eff_protein",
        "eff_fat",
        "eff_fiber",
        "baseline_glucose",
        "prev_meal_gap_min",
        "BMI",
        "A1c PDL (Lab)",
        "Fasting GLU - PDL (Lab)",
    ]

    rows = []

    for (target, scenario_id), sub in cf_records.groupby(["target", "scenario_id"]):
        if scenario_id == "S0_no_change":
            continue

        top = sub.sort_values("predicted_reduction", ascending=False).head(30)
        rows.append(top[[c for c in cols if c in top.columns]])

    out = pd.concat(rows, axis=0, ignore_index=True) if rows else pd.DataFrame()
    out.to_csv(TABLES / "counterfactual_top_benefit_meals.csv", index=False, encoding="utf-8-sig")

    return out


# ============================================================
# 6. Subject-level bootstrap for counterfactual mean deltas
# ============================================================

def fit_and_predict_bootstrap_sample(sampled_data, target, scenario_id, numeric_features, categorical_features):
    features = numeric_features + categorical_features

    model = get_model()
    pipe = make_pipeline(model, numeric_features, categorical_features)

    X_train = sampled_data[features]
    y_train = sampled_data[target].values
    pipe.fit(X_train, y_train)

    base_pred = pipe.predict(sampled_data[features])

    cf_data = SCENARIOS[scenario_id]["function"](sampled_data.copy())
    cf_pred = pipe.predict(cf_data[features])

    delta = cf_pred - base_pred

    return delta


def bootstrap_counterfactual_summary(df_by_target, numeric_features, categorical_features):
    if not RUN_BOOTSTRAP:
        out = pd.DataFrame()
        out.to_csv(TABLES / "counterfactual_bootstrap_summary.csv", index=False, encoding="utf-8-sig")
        return out

    rng = np.random.default_rng(RANDOM_SEED)

    rows = []

    for target, data in df_by_target.items():
        subject_ids = np.array(sorted(data["subject_id"].dropna().unique()))
        n_subjects = len(subject_ids)

        grouped = {
            sid: data[data["subject_id"] == sid]
            for sid in subject_ids
        }

        scenario_ids = [s for s in SCENARIOS.keys() if s != "S0_no_change"]

        boot_values = {
            scenario_id: []
            for scenario_id in scenario_ids
        }

        print(f"Bootstrap counterfactuals for target={target}, subjects={n_subjects}")

        for b in range(N_BOOTSTRAP):
            if (b + 1) % 25 == 0:
                print(f"  bootstrap {b + 1}/{N_BOOTSTRAP}")

            sampled_subjects = rng.choice(subject_ids, size=n_subjects, replace=True)
            sampled_data = pd.concat([grouped[sid] for sid in sampled_subjects], axis=0, ignore_index=True)

            for scenario_id in scenario_ids:
                try:
                    delta = fit_and_predict_bootstrap_sample(
                        sampled_data=sampled_data,
                        target=target,
                        scenario_id=scenario_id,
                        numeric_features=numeric_features,
                        categorical_features=categorical_features,
                    )
                    boot_values[scenario_id].append(float(np.nanmean(delta)))
                except Exception:
                    boot_values[scenario_id].append(np.nan)

        for scenario_id in scenario_ids:
            arr = np.array(boot_values[scenario_id], dtype=float)
            arr = arr[np.isfinite(arr)]

            spec = SCENARIOS[scenario_id]

            if len(arr) == 0:
                mean_delta = np.nan
                low = np.nan
                high = np.nan
                sd = np.nan
            else:
                mean_delta = float(np.mean(arr))
                low = float(np.percentile(arr, 2.5))
                high = float(np.percentile(arr, 97.5))
                sd = float(np.std(arr, ddof=1)) if len(arr) > 1 else np.nan

            rows.append({
                "target": target,
                "target_label": TARGET_LABELS.get(target, target),
                "unit": TARGET_UNITS.get(target, ""),
                "scenario_id": scenario_id,
                "scenario_label": spec["label"],
                "scenario_type": spec["type"],
                "mean_delta_pred_boot_mean": mean_delta,
                "mean_delta_pred_ci_lower": low,
                "mean_delta_pred_ci_upper": high,
                "mean_delta_pred_boot_sd": sd,
                "mean_predicted_reduction_boot_mean": -mean_delta if np.isfinite(mean_delta) else np.nan,
                "mean_predicted_reduction_ci_lower": -high if np.isfinite(high) else np.nan,
                "mean_predicted_reduction_ci_upper": -low if np.isfinite(low) else np.nan,
                "n_bootstrap": int(N_BOOTSTRAP),
                "n_subjects": int(n_subjects),
            })

    out = pd.DataFrame(rows)

    if not out.empty:
        out = out.sort_values(["target", "mean_delta_pred_boot_mean"]).reset_index(drop=True)

    out.to_csv(TABLES / "counterfactual_bootstrap_summary.csv", index=False, encoding="utf-8-sig")

    return out


# ============================================================
# 7. Main text summary
# ============================================================

def make_main_summary(scenario_summary, bootstrap_summary, subject_summary):
    rows = []

    for target in TARGETS:
        sub = scenario_summary[scenario_summary["target"] == target].copy()

        if sub.empty:
            continue

        # Best predicted mean reduction
        best = sub.sort_values("mean_delta_pred", ascending=True).head(3)

        best_text = "; ".join([
            f"{r['scenario_label']}: mean_delta={r['mean_delta_pred']:.1f} {r['unit']}, "
            f"meals_reduced={r['percent_meals_with_predicted_reduction']:.1f}%"
            for _, r in best.iterrows()
        ])

        rows.append({
            "section": "best_average_counterfactual_scenarios",
            "target": TARGET_LABELS.get(target, target),
            "finding": "Scenarios with largest average model-predicted reduction",
            "value": best_text,
        })

        # Heterogeneity for best scenario
        if len(best) > 0:
            best_id = best.iloc[0]["scenario_id"]
            st = subject_summary[
                (subject_summary["target"] == target)
                & (subject_summary["scenario_id"] == best_id)
            ].copy()

            if not st.empty:
                rows.append({
                    "section": "subject_heterogeneity",
                    "target": TARGET_LABELS.get(target, target),
                    "finding": f"Subject-level heterogeneity for {best.iloc[0]['scenario_label']}",
                    "value": (
                        f"mean_subject_delta={st['mean_delta_pred'].mean():.1f}, "
                        f"median_subject_delta={st['mean_delta_pred'].median():.1f}, "
                        f"q25={st['mean_delta_pred'].quantile(0.25):.1f}, "
                        f"q75={st['mean_delta_pred'].quantile(0.75):.1f}, "
                        f"subjects_with_mean_reduction={(st['mean_delta_pred'] < 0).mean() * 100.0:.1f}%"
                    ),
                })

        # Bootstrap support
        if not bootstrap_summary.empty:
            bt = bootstrap_summary[bootstrap_summary["target"] == target].copy()
            bt = bt.sort_values("mean_delta_pred_boot_mean", ascending=True).head(3)

            bt_text = "; ".join([
                f"{r['scenario_label']}: mean_delta={r['mean_delta_pred_boot_mean']:.1f} "
                f"[{r['mean_delta_pred_ci_lower']:.1f}, {r['mean_delta_pred_ci_upper']:.1f}]"
                for _, r in bt.iterrows()
            ])

            rows.append({
                "section": "bootstrap_uncertainty",
                "target": TARGET_LABELS.get(target, target),
                "finding": "Subject-level bootstrap uncertainty for best scenarios",
                "value": bt_text,
            })

    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "counterfactual_main_summary.csv", index=False, encoding="utf-8-sig")

    return out


# ============================================================
# 8. Figures
# ============================================================

def safe_filename(s):
    s = str(s)
    s = re.sub(r"[^A-Za-z0-9_]+", "_", s)
    return s.strip("_")


def plot_mean_delta(scenario_summary):
    for target in TARGETS:
        sub = scenario_summary[scenario_summary["target"] == target].copy()

        if sub.empty:
            continue

        sub = sub.sort_values("mean_delta_pred", ascending=True)

        fig, ax = plt.subplots(figsize=(10, 5))
        x = np.arange(len(sub))
        ax.axhline(0, linestyle="--", linewidth=1)
        ax.bar(x, sub["mean_delta_pred"])
        ax.set_xticks(x)
        ax.set_xticklabels(sub["scenario_label"], rotation=35, ha="right")
        ax.set_ylabel(f"Mean predicted delta ({TARGET_UNITS[target]})")
        ax.set_title(f"Counterfactual meal-substitution scenarios\n{TARGET_LABELS[target]}")

        fig.tight_layout()
        out = FIGURES / f"counterfactual_mean_delta_{target}.png"
        fig.savefig(out, dpi=300, bbox_inches="tight")
        plt.close(fig)


def plot_percent_meals_reduced(scenario_summary):
    for target in TARGETS:
        sub = scenario_summary[scenario_summary["target"] == target].copy()

        if sub.empty:
            continue

        sub = sub.sort_values("percent_meals_with_predicted_reduction", ascending=False)

        fig, ax = plt.subplots(figsize=(10, 5))
        x = np.arange(len(sub))
        ax.bar(x, sub["percent_meals_with_predicted_reduction"])
        ax.set_xticks(x)
        ax.set_xticklabels(sub["scenario_label"], rotation=35, ha="right")
        ax.set_ylabel("Meals with predicted reduction (%)")
        ax.set_ylim(0, 100)
        ax.set_title(f"Proportion of meals predicted to improve\n{TARGET_LABELS[target]}")

        fig.tight_layout()
        out = FIGURES / f"counterfactual_percent_meals_reduced_{target}.png"
        fig.savefig(out, dpi=300, bbox_inches="tight")
        plt.close(fig)


def plot_subject_heterogeneity(subject_summary):
    for target in TARGETS:
        sub_target = subject_summary[subject_summary["target"] == target].copy()

        if sub_target.empty:
            continue

        # Plot top 4 scenarios by mean predicted reduction.
        scenario_order = (
            sub_target
            .groupby("scenario_id")["mean_delta_pred"]
            .mean()
            .sort_values()
            .head(4)
            .index
            .tolist()
        )

        for scenario_id in scenario_order:
            sub = sub_target[sub_target["scenario_id"] == scenario_id].copy()
            sub = sub.sort_values("mean_delta_pred")

            if sub.empty:
                continue

            label = sub["scenario_label"].iloc[0]

            fig, ax = plt.subplots(figsize=(9, 5))
            x = np.arange(len(sub))
            ax.axhline(0, linestyle="--", linewidth=1)
            ax.bar(x, sub["mean_delta_pred"])
            ax.set_xlabel("Subjects sorted by mean predicted delta")
            ax.set_ylabel(f"Subject mean predicted delta ({TARGET_UNITS[target]})")
            ax.set_title(f"Subject heterogeneity: {label}\n{TARGET_LABELS[target]}")

            fig.tight_layout()
            out = FIGURES / f"counterfactual_subject_heterogeneity_{target}_{safe_filename(scenario_id)}.png"
            fig.savefig(out, dpi=300, bbox_inches="tight")
            plt.close(fig)


def plot_high_risk_delta(scenario_summary):
    for target in TARGETS:
        sub = scenario_summary[scenario_summary["target"] == target].copy()

        if sub.empty:
            continue

        sub = sub.sort_values("high_risk_mean_delta_pred", ascending=True)

        fig, ax = plt.subplots(figsize=(10, 5))
        x = np.arange(len(sub))
        ax.axhline(0, linestyle="--", linewidth=1)
        ax.bar(x, sub["high_risk_mean_delta_pred"])
        ax.set_xticks(x)
        ax.set_xticklabels(sub["scenario_label"], rotation=35, ha="right")
        ax.set_ylabel(f"High-risk meal mean predicted delta ({TARGET_UNITS[target]})")
        ax.set_title(f"Counterfactual effects among baseline high-risk meals\n{TARGET_LABELS[target]}")

        fig.tight_layout()
        out = FIGURES / f"counterfactual_high_risk_delta_{target}.png"
        fig.savefig(out, dpi=300, bbox_inches="tight")
        plt.close(fig)


# ============================================================
# 9. Main
# ============================================================

def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Cannot find {DATA_PATH}. Please run previous scripts first.")

    print("Loading meal-level dataset...")
    df = pd.read_csv(DATA_PATH)
    df.columns = [str(c).strip() for c in df.columns]

    if "meal_time" in df.columns:
        df["meal_time"] = pd.to_datetime(df["meal_time"], errors="coerce")
    else:
        df["meal_time"] = pd.NaT

    df["subject_id"] = df["subject_id"].astype(int)

    df = safe_numeric(df, NUMERIC_FEATURES_M3 + TARGETS)

    numeric_features = available_features(df, NUMERIC_FEATURES_M3)
    categorical_features = available_features(df, CATEGORICAL_FEATURES_M3)

    print("Numeric features:", numeric_features)
    print("Categorical features:", categorical_features)

    df_by_target = {}
    all_cf_records = []

    for target in TARGETS:
        print("\n" + "=" * 90)
        print(f"Target: {target}")
        print("=" * 90)

        data = clean_target_dataset(df, target)

        print("Data shape:", data.shape)
        print("Subjects:", data["subject_id"].nunique())

        df_by_target[target] = data

        cf_records = predict_counterfactuals_for_target(
            data=data,
            target=target,
            numeric_features=numeric_features,
            categorical_features=categorical_features,
        )

        all_cf_records.append(cf_records)

    cf_all = pd.concat(all_cf_records, axis=0, ignore_index=True)
    cf_all.to_csv(TABLES / "counterfactual_meal_level_predictions.csv", index=False, encoding="utf-8-sig")

    print("\nCreating summaries...")
    scenario_summary = summarize_scenarios(cf_all)
    subject_summary = summarize_by_subject(cf_all)
    subgroup_summary = summarize_by_subgroup(cf_all)
    top_benefit = make_top_benefit_meals(cf_all)

    print("\nRunning bootstrap uncertainty analysis...")
    bootstrap_summary = bootstrap_counterfactual_summary(
        df_by_target=df_by_target,
        numeric_features=numeric_features,
        categorical_features=categorical_features,
    )

    main_summary = make_main_summary(
        scenario_summary=scenario_summary,
        bootstrap_summary=bootstrap_summary,
        subject_summary=subject_summary,
    )

    print("\nGenerating figures...")
    plot_mean_delta(scenario_summary)
    plot_percent_meals_reduced(scenario_summary)
    plot_subject_heterogeneity(subject_summary)
    plot_high_risk_delta(scenario_summary)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 260)
    pd.set_option("display.max_rows", 300)

    print("\nSaved tables:")
    print(TABLES / "counterfactual_meal_level_predictions.csv")
    print(TABLES / "counterfactual_scenario_summary.csv")
    print(TABLES / "counterfactual_subject_summary.csv")
    print(TABLES / "counterfactual_subgroup_summary.csv")
    print(TABLES / "counterfactual_bootstrap_summary.csv")
    print(TABLES / "counterfactual_top_benefit_meals.csv")
    print(TABLES / "counterfactual_main_summary.csv")

    print("\nScenario summary:")
    print(scenario_summary)

    print("\nBootstrap summary:")
    print(bootstrap_summary)

    print("\nMain summary:")
    print(main_summary)

    print("\nFigures saved to:")
    print(FIGURES)

    print("\nDone.")


if __name__ == "__main__":
    main()