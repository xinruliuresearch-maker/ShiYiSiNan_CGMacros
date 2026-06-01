# -*- coding: utf-8 -*-
"""
06_bootstrap_ci.py

升级 3：Subject-level bootstrap 95% confidence intervals

目标：
1. 基于清洗后的无泄漏特征体系，重新生成 out-of-fold / temporal split / few-shot 预测。
2. 以 subject 为 bootstrap 单位，计算 MAE、RMSE、R2、Pearson r 的 95% CI。
3. 输出论文可报告的性能表和主图。

输出：
- outputs/tables/bootstrap_ci_prediction_records.csv
- outputs/tables/bootstrap_ci_ablation_results.csv
- outputs/tables/bootstrap_ci_fewshot_results.csv
- outputs/figures/bootstrap_ci_ablation_mae_iauc_2h.png
- outputs/figures/bootstrap_ci_ablation_mae_peak_delta_2h.png
- outputs/figures/bootstrap_ci_fewshot_mae_iauc_2h.png
- outputs/figures/bootstrap_ci_fewshot_mae_peak_delta_2h.png
"""

from pathlib import Path
import re
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.base import clone
from sklearn.model_selection import GroupKFold
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor

try:
    from sklearn.preprocessing import OneHotEncoder
except Exception as e:
    raise ImportError("scikit-learn is not installed correctly.") from e

warnings.filterwarnings("ignore")


# ============================================================
# 0. 全局设置
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

DATA_PATH = TABLES / "meal_level_dataset.csv"

TARGETS = [
    "iauc_2h",
    "peak_delta_2h",
]

# 主论文建议先只给 HGB 加 CI。
# 如果你想同时给 RF 加 CI，把这里改成 ["hist_gradient_boosting", "random_forest"]
MODEL_NAMES_TO_RUN = [
    "hist_gradient_boosting",
]

N_BOOTSTRAP = 1000
RANDOM_SEED = 42


# ============================================================
# 1. 特征定义：与升级 2 保持一致
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


# ============================================================
# 2. 禁止变量：防止泄漏
# ============================================================

FORBIDDEN_EXACT = {
    "calories",
    "carbs",
    "protein",
    "fat",
    "fiber",
    "amount_consumed",
    "amount_factor",

    "auc_2h",
    "iauc_2h",
    "peak_glucose_2h",
    "peak_delta_2h",
    "time_to_peak_2h",
    "recovery_time_2h",
    "auc_3h",
    "iauc_3h",

    "image_path",
    "glucose_source",
    "n_pre_points",
    "n_post2h_points",
    "Unnamed: 0",

    "Time (t)",
    "Time (t).1",
    "Time (t).2",
    "Collection time PDL (Lab)",

    "#1 Contour Fingerstick GLU",
    "#2 Contour Fingerstick GLU",
    "#3 Contour Fingerstick GLU",
    " #2 Contour Fingerstick GLU",
}

FORBIDDEN_REGEX = [
    r"fingerstick",
    r"contour",
    r"image",
    r"glucose_source",
    r"^auc_",
    r"^iauc_",
    r"^peak_",
    r"recovery",
    r"time_to_peak",
    r"n_pre_points",
    r"n_post2h_points",
    r"collection time",
    r"^time \(t\)",
]


# ============================================================
# 3. 工具函数
# ============================================================

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    rename_map = {
        "METs": "Mets",
        "mets": "Mets",
        "Image path": "Image Path",
        "Image Path": "Image Path",
        "Amount Consumed": "Amount Consumed",
        "Body weight": "Body weight",
        "Height": "Height",
        "Self-identify": "Self-identify",
        "Insulin": "Insulin",
        "Non HDL": "Non HDL",
    }

    return df.rename(columns={c: rename_map.get(c, c) for c in df.columns})


def find_file(filename: str):
    matches = list(RAW.rglob(filename))
    return matches[0] if matches else None


def forbidden_reason(col: str):
    c = str(col).strip()
    lower = c.lower()

    if c in FORBIDDEN_EXACT:
        return "explicitly_forbidden"

    if lower in ["calories", "carbs", "protein", "fat", "fiber", "amount consumed"]:
        return "raw_nutrient_duplicate"

    for pattern in FORBIDDEN_REGEX:
        if re.search(pattern, lower):
            return f"regex_forbidden:{pattern}"

    return None


def make_onehot_encoder():
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def rmse(y_true, y_pred):
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def pearson_r(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    if len(y_true) < 2:
        return np.nan

    if np.std(y_true) == 0 or np.std(y_pred) == 0:
        return np.nan

    return float(np.corrcoef(y_true, y_pred)[0, 1])


def compute_metrics(y_true, y_pred):
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": rmse(y_true, y_pred),
        "R2": float(r2_score(y_true, y_pred)),
        "Pearson_r": pearson_r(y_true, y_pred),
    }


def clean_dataset(df, target):
    data = df.copy()
    data = data.dropna(subset=[target, "subject_id"])

    q_low = data[target].quantile(0.01)
    q_high = data[target].quantile(0.99)
    data = data[(data[target] >= q_low) & (data[target] <= q_high)]

    data["subject_id"] = data["subject_id"].astype(int)
    data["meal_time"] = pd.to_datetime(data["meal_time"], errors="coerce")
    data = data.dropna(subset=["meal_time"])

    return data.reset_index(drop=True)


def filter_numeric_features(df, features):
    out = []

    for col in features:
        if col not in df.columns:
            continue

        if forbidden_reason(col) is not None:
            continue

        if not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = pd.to_numeric(df[col], errors="coerce")

        if df[col].notna().sum() == 0:
            continue

        out.append(col)

    return out


def filter_categorical_features(df, features):
    out = []

    for col in features:
        if col not in df.columns:
            continue

        if forbidden_reason(col) is not None:
            continue

        if df[col].notna().sum() == 0:
            continue

        out.append(col)

    return out


def get_gut_health_features(df: pd.DataFrame):
    f = find_file("gut_health_test.csv")
    if f is None:
        return []

    gut = pd.read_csv(f)
    gut = normalize_columns(gut)

    if "subject" in gut.columns:
        gut = gut.rename(columns={"subject": "subject_id"})
    elif "Subject" in gut.columns:
        gut = gut.rename(columns={"Subject": "subject_id"})
    elif "subject_id" not in gut.columns:
        gut = gut.rename(columns={gut.columns[0]: "subject_id"})

    gut_cols = [c for c in gut.columns if c != "subject_id"]

    out = []
    for c in gut_cols:
        candidate_names = [c, f"{c}_gut"]

        for name in candidate_names:
            if name in df.columns:
                if forbidden_reason(name) is None:
                    if pd.api.types.is_numeric_dtype(df[name]):
                        if df[name].notna().sum() > 0:
                            out.append(name)

    return sorted(list(set(out)))


def build_feature_sets(df: pd.DataFrame):
    gut_features = get_gut_health_features(df)

    specs = {}

    specs["M0_meal_only"] = {
        "order": 0,
        "numeric": filter_numeric_features(df, MEAL_FEATURES),
        "categorical": filter_categorical_features(df, MEAL_CATEGORICAL_FEATURES),
        "description": "meal composition only",
    }

    specs["M1_meal_pre_cgm"] = {
        "order": 1,
        "numeric": filter_numeric_features(df, MEAL_FEATURES + PRE_CGM_FEATURES),
        "categorical": filter_categorical_features(df, MEAL_CATEGORICAL_FEATURES),
        "description": "meal composition + preprandial CGM",
    }

    specs["M2_meal_pre_cgm_wearable_time"] = {
        "order": 2,
        "numeric": filter_numeric_features(
            df,
            MEAL_FEATURES + PRE_CGM_FEATURES + WEARABLE_TIME_FEATURES
        ),
        "categorical": filter_categorical_features(df, MEAL_CATEGORICAL_FEATURES),
        "description": "M1 + wearable and timing features",
    }

    specs["M3_clinical_enhanced"] = {
        "order": 3,
        "numeric": filter_numeric_features(
            df,
            MEAL_FEATURES
            + PRE_CGM_FEATURES
            + WEARABLE_TIME_FEATURES
            + CLINICAL_NUMERIC_FEATURES
        ),
        "categorical": filter_categorical_features(
            df,
            MEAL_CATEGORICAL_FEATURES + CLINICAL_CATEGORICAL_FEATURES
        ),
        "description": "M2 + clinical baseline features",
    }

    specs["M4_gut_exploratory"] = {
        "order": 4,
        "numeric": filter_numeric_features(
            df,
            MEAL_FEATURES
            + PRE_CGM_FEATURES
            + WEARABLE_TIME_FEATURES
            + CLINICAL_NUMERIC_FEATURES
            + gut_features
        ),
        "categorical": filter_categorical_features(
            df,
            MEAL_CATEGORICAL_FEATURES + CLINICAL_CATEGORICAL_FEATURES
        ),
        "description": "M3 + gut health features, exploratory",
    }

    for fs_name, spec in specs.items():
        all_features = spec["numeric"] + spec["categorical"]
        bad = [f for f in all_features if forbidden_reason(f) is not None]
        if bad:
            raise RuntimeError(f"Forbidden features found in {fs_name}: {bad}")

    return specs


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

    if len(transformers) == 0:
        raise RuntimeError("No valid features available.")

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


def get_models():
    return {
        "random_forest": RandomForestRegressor(
            n_estimators=300,
            max_depth=None,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
        ),

        "hist_gradient_boosting": HistGradientBoostingRegressor(
            max_iter=400,
            learning_rate=0.03,
            max_leaf_nodes=31,
            random_state=42,
        ),
    }


# ============================================================
# 4. 生成预测记录
# ============================================================

def predict_leave_subject_out(df, target, feature_set_name, feature_spec, model_name, model):
    data = df.copy()

    numeric_features = feature_spec["numeric"]
    categorical_features = feature_spec["categorical"]
    features = numeric_features + categorical_features

    X = data[features]
    y = data[target].values
    groups = data["subject_id"].values

    n_subjects = data["subject_id"].nunique()
    n_splits = min(5, n_subjects)

    gkf = GroupKFold(n_splits=n_splits)

    records = []

    for fold, (train_idx, test_idx) in enumerate(gkf.split(X, y, groups), start=1):
        pipe = make_pipeline(model, numeric_features, categorical_features)
        pipe.fit(X.iloc[train_idx], y[train_idx])
        pred = pipe.predict(X.iloc[test_idx])

        fold_df = pd.DataFrame({
            "subject_id": data.iloc[test_idx]["subject_id"].values,
            "meal_time": data.iloc[test_idx]["meal_time"].values,
            "target": target,
            "feature_set": feature_set_name,
            "feature_order": feature_spec["order"],
            "model": model_name,
            "validation": "leave_subject_out",
            "fold": fold,
            "shots": np.nan,
            "y_true": y[test_idx],
            "y_pred": pred,
        })

        records.append(fold_df)

    return pd.concat(records, axis=0, ignore_index=True)


def predict_within_subject_temporal(df, target, feature_set_name, feature_spec, model_name, model):
    data = df.copy()
    data = data.sort_values(["subject_id", "meal_time"]).reset_index(drop=True)

    train_indices = []
    test_indices = []

    for sid, sub in data.groupby("subject_id"):
        idx = sub.index.to_numpy()
        n = len(idx)

        if n < 5:
            train_indices.extend(idx.tolist())
            continue

        cut = int(np.floor(n * 0.8))
        cut = max(1, min(cut, n - 1))

        train_indices.extend(idx[:cut].tolist())
        test_indices.extend(idx[cut:].tolist())

    if len(test_indices) == 0:
        raise RuntimeError("No test meals available for within-subject temporal split.")

    numeric_features = feature_spec["numeric"]
    categorical_features = feature_spec["categorical"]
    features = numeric_features + categorical_features

    X = data[features]
    y = data[target].values

    train_idx = np.array(train_indices)
    test_idx = np.array(test_indices)

    pipe = make_pipeline(model, numeric_features, categorical_features)
    pipe.fit(X.iloc[train_idx], y[train_idx])
    pred = pipe.predict(X.iloc[test_idx])

    pred_df = pd.DataFrame({
        "subject_id": data.iloc[test_idx]["subject_id"].values,
        "meal_time": data.iloc[test_idx]["meal_time"].values,
        "target": target,
        "feature_set": feature_set_name,
        "feature_order": feature_spec["order"],
        "model": model_name,
        "validation": "within_subject_temporal_split",
        "fold": np.nan,
        "shots": np.nan,
        "y_true": y[test_idx],
        "y_pred": pred,
    })

    return pred_df


def predict_few_shot(df, target, feature_set_name, feature_spec, model_name, model, shots_list=(0, 1, 3, 5, 10)):
    data = df.copy()
    data = data.sort_values(["subject_id", "meal_time"]).reset_index(drop=True)

    numeric_features = feature_spec["numeric"]
    categorical_features = feature_spec["categorical"]
    features = numeric_features + categorical_features

    all_records = []

    for k in shots_list:
        for sid, sub in data.groupby("subject_id"):
            sub = sub.sort_values("meal_time").copy()

            if len(sub) <= k + 3:
                continue

            adaptation = sub.iloc[:k].copy()
            test = sub.iloc[k:].copy()

            train_base = data[data["subject_id"] != sid].copy()

            if k > 0:
                train = pd.concat([train_base, adaptation], axis=0, ignore_index=True)
            else:
                train = train_base

            X_train = train[features]
            y_train = train[target].values

            X_test = test[features]
            y_test = test[target].values

            pipe = make_pipeline(model, numeric_features, categorical_features)
            pipe.fit(X_train, y_train)
            pred = pipe.predict(X_test)

            pred_df = pd.DataFrame({
                "subject_id": test["subject_id"].values,
                "meal_time": test["meal_time"].values,
                "target": target,
                "feature_set": feature_set_name,
                "feature_order": feature_spec["order"],
                "model": model_name,
                "validation": "few_shot_personalization",
                "fold": np.nan,
                "shots": int(k),
                "y_true": y_test,
                "y_pred": pred,
            })

            all_records.append(pred_df)

    if len(all_records) == 0:
        return pd.DataFrame()

    return pd.concat(all_records, axis=0, ignore_index=True)


# ============================================================
# 5. Subject-level bootstrap
# ============================================================

def bootstrap_ci_for_predictions(pred_df, n_bootstrap=1000, seed=42):
    """
    对一个预测结果表进行 subject-level bootstrap。
    pred_df 必须包含：
    subject_id, y_true, y_pred
    """
    rng = np.random.default_rng(seed)

    subject_ids = np.array(sorted(pred_df["subject_id"].dropna().unique()))
    n_subjects = len(subject_ids)

    y_true = pred_df["y_true"].values
    y_pred = pred_df["y_pred"].values

    point_metrics = compute_metrics(y_true, y_pred)

    boot_metrics = {
        "MAE": [],
        "RMSE": [],
        "R2": [],
        "Pearson_r": [],
    }

    grouped = {
        sid: pred_df[pred_df["subject_id"] == sid]
        for sid in subject_ids
    }

    for _ in range(n_bootstrap):
        sampled_subjects = rng.choice(subject_ids, size=n_subjects, replace=True)

        sampled_parts = []
        for sid in sampled_subjects:
            sampled_parts.append(grouped[sid])

        sampled = pd.concat(sampled_parts, axis=0, ignore_index=True)

        yt = sampled["y_true"].values
        yp = sampled["y_pred"].values

        m = compute_metrics(yt, yp)

        for metric in boot_metrics:
            boot_metrics[metric].append(m[metric])

    summary = {}

    for metric, values in boot_metrics.items():
        arr = np.array(values, dtype=float)
        arr = arr[np.isfinite(arr)]

        if len(arr) == 0:
            lower = np.nan
            upper = np.nan
            boot_mean = np.nan
            boot_sd = np.nan
        else:
            lower = float(np.percentile(arr, 2.5))
            upper = float(np.percentile(arr, 97.5))
            boot_mean = float(np.mean(arr))
            boot_sd = float(np.std(arr, ddof=1))

        summary[f"{metric}"] = point_metrics[metric]
        summary[f"{metric}_boot_mean"] = boot_mean
        summary[f"{metric}_boot_sd"] = boot_sd
        summary[f"{metric}_ci_lower"] = lower
        summary[f"{metric}_ci_upper"] = upper

    summary["n_subjects"] = int(n_subjects)
    summary["n_meals"] = int(len(pred_df))
    summary["n_bootstrap"] = int(n_bootstrap)

    return summary


def summarize_bootstrap(pred_records, n_bootstrap=1000, seed=42):
    """
    对所有 prediction records 分组计算 bootstrap CI。
    """
    rows = []

    group_cols = [
        "target",
        "feature_set",
        "feature_order",
        "model",
        "validation",
        "shots",
    ]

    # 注意 shots 有 NaN，所以 dropna=False
    for keys, sub in pred_records.groupby(group_cols, dropna=False):
        target, feature_set, feature_order, model, validation, shots = keys

        summary = bootstrap_ci_for_predictions(
            sub,
            n_bootstrap=n_bootstrap,
            seed=seed,
        )

        summary.update({
            "target": target,
            "feature_set": feature_set,
            "feature_order": int(feature_order),
            "model": model,
            "validation": validation,
            "shots": shots,
        })

        rows.append(summary)

    result = pd.DataFrame(rows)
    result = result.sort_values(
        ["target", "validation", "model", "feature_order", "shots"],
        na_position="first"
    ).reset_index(drop=True)

    return result


# ============================================================
# 6. 作图
# ============================================================

def plot_ablation_ci(ci_df):
    """
    画 M0-M4 的 MAE with 95% CI。
    只画非 few-shot。
    """
    plot_df = ci_df[
        ci_df["validation"].isin(["leave_subject_out", "within_subject_temporal_split"])
    ].copy()

    short_names = {
        "M0_meal_only": "M0\nMeal",
        "M1_meal_pre_cgm": "M1\n+Pre-CGM",
        "M2_meal_pre_cgm_wearable_time": "M2\n+Wearable/Time",
        "M3_clinical_enhanced": "M3\n+Clinical",
        "M4_gut_exploratory": "M4\n+Gut",
    }

    for target in TARGETS:
        sub_target = plot_df[
            (plot_df["target"] == target)
            & (plot_df["model"] == "hist_gradient_boosting")
        ].copy()

        if sub_target.empty:
            continue

        plt.figure(figsize=(8, 5))

        for validation in ["leave_subject_out", "within_subject_temporal_split"]:
            sub = sub_target[sub_target["validation"] == validation].copy()
            sub = sub.sort_values("feature_order")

            x = np.arange(len(sub))
            y = sub["MAE"].values
            yerr_lower = y - sub["MAE_ci_lower"].values
            yerr_upper = sub["MAE_ci_upper"].values - y
            yerr = np.vstack([yerr_lower, yerr_upper])

            label = (
                "Leave-subject-out"
                if validation == "leave_subject_out"
                else "Within-subject temporal"
            )

            offset = -0.05 if validation == "leave_subject_out" else 0.05

            plt.errorbar(
                x + offset,
                y,
                yerr=yerr,
                marker="o",
                capsize=4,
                label=label,
            )

        labels = [
            short_names.get(fs, fs)
            for fs in sub_target.sort_values("feature_order")["feature_set"].unique()
        ]

        plt.xticks(np.arange(len(labels)), labels)
        plt.ylabel("MAE with 95% CI")

        title_target = (
            "2-h glucose iAUC"
            if target == "iauc_2h"
            else "2-h peak glucose excursion"
        )

        plt.title(f"Feature-set ablation with subject-level bootstrap CI\n{title_target}")
        plt.legend()
        plt.tight_layout()

        out = FIGURES / f"bootstrap_ci_ablation_mae_{target}.png"
        plt.savefig(out, dpi=300)
        plt.close()


def plot_fewshot_ci(ci_df):
    few = ci_df[ci_df["validation"] == "few_shot_personalization"].copy()

    if few.empty:
        return

    for target in TARGETS:
        sub = few[
            (few["target"] == target)
            & (few["feature_set"] == "M3_clinical_enhanced")
            & (few["model"] == "hist_gradient_boosting")
        ].copy()

        if sub.empty:
            continue

        sub = sub.sort_values("shots")

        x = sub["shots"].values.astype(float)
        y = sub["MAE"].values
        yerr_lower = y - sub["MAE_ci_lower"].values
        yerr_upper = sub["MAE_ci_upper"].values - y
        yerr = np.vstack([yerr_lower, yerr_upper])

        plt.figure(figsize=(7, 5))
        plt.errorbar(
            x,
            y,
            yerr=yerr,
            marker="o",
            capsize=4,
        )

        plt.xlabel("Number of subject-specific meals for adaptation")
        plt.ylabel("MAE with 95% CI")

        title_target = (
            "2-h glucose iAUC"
            if target == "iauc_2h"
            else "2-h peak glucose excursion"
        )

        plt.title(f"Few-shot personalization with subject-level bootstrap CI\n{title_target}")
        plt.tight_layout()

        out = FIGURES / f"bootstrap_ci_fewshot_mae_{target}.png"
        plt.savefig(out, dpi=300)
        plt.close()


# ============================================================
# 7. 主流程
# ============================================================

def main():
    print("Project root:", ROOT)
    print("Data path:", DATA_PATH)

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Cannot find {DATA_PATH}. Please run 02_build_meal_level_dataset.py first."
        )

    df = pd.read_csv(DATA_PATH)
    df.columns = [str(c).strip() for c in df.columns]
    df["meal_time"] = pd.to_datetime(df["meal_time"], errors="coerce")

    print("\nLoaded meal-level dataset:", df.shape)

    feature_sets = build_feature_sets(df)
    models = get_models()

    models = {
        name: model
        for name, model in models.items()
        if name in MODEL_NAMES_TO_RUN
    }

    print("\nModels to run:", list(models.keys()))
    print("Bootstrap iterations:", N_BOOTSTRAP)

    all_prediction_records = []

    # A. Ablation prediction records: M0-M4, HGB by default
    for target in TARGETS:
        print("\n" + "=" * 90)
        print(f"Target: {target}")
        print("=" * 90)

        data = clean_dataset(df, target)

        print("Data shape after cleaning:", data.shape)
        print("Number of subjects:", data["subject_id"].nunique())

        for fs_name, fs_spec in feature_sets.items():
            print("\n" + "-" * 80)
            print(f"Feature set: {fs_name}")
            print(fs_spec["description"])

            for model_name, model in models.items():
                print(f"Generating predictions: {model_name}")

                print("  leave_subject_out...")
                pred_lso = predict_leave_subject_out(
                    data,
                    target,
                    fs_name,
                    fs_spec,
                    model_name,
                    model,
                )
                all_prediction_records.append(pred_lso)

                print("  within_subject_temporal_split...")
                pred_ws = predict_within_subject_temporal(
                    data,
                    target,
                    fs_name,
                    fs_spec,
                    model_name,
                    model,
                )
                all_prediction_records.append(pred_ws)

        # B. Few-shot prediction records: 只对 M3 + HGB 跑
        fewshot_feature_set = "M3_clinical_enhanced"
        fewshot_model = "hist_gradient_boosting"

        if fewshot_model in models:
            print("\n" + "-" * 80)
            print(f"Few-shot predictions for {target}: {fewshot_feature_set} + {fewshot_model}")

            pred_fs = predict_few_shot(
                data,
                target,
                fewshot_feature_set,
                feature_sets[fewshot_feature_set],
                fewshot_model,
                models[fewshot_model],
                shots_list=(0, 1, 3, 5, 10),
            )

            all_prediction_records.append(pred_fs)

    prediction_records = pd.concat(all_prediction_records, axis=0, ignore_index=True)

    pred_path = TABLES / "bootstrap_ci_prediction_records.csv"
    prediction_records.to_csv(pred_path, index=False, encoding="utf-8-sig")

    print("\nSaved prediction records:")
    print(pred_path)
    print("Prediction records shape:", prediction_records.shape)

    # C. Bootstrap CI
    print("\nComputing subject-level bootstrap confidence intervals...")
    ci_df = summarize_bootstrap(
        prediction_records,
        n_bootstrap=N_BOOTSTRAP,
        seed=RANDOM_SEED,
    )

    # 分开保存 ablation 和 few-shot
    ablation_ci = ci_df[ci_df["validation"] != "few_shot_personalization"].copy()
    fewshot_ci = ci_df[ci_df["validation"] == "few_shot_personalization"].copy()

    ablation_path = TABLES / "bootstrap_ci_ablation_results.csv"
    fewshot_path = TABLES / "bootstrap_ci_fewshot_results.csv"
    all_ci_path = TABLES / "bootstrap_ci_all_results.csv"

    ci_df.to_csv(all_ci_path, index=False, encoding="utf-8-sig")
    ablation_ci.to_csv(ablation_path, index=False, encoding="utf-8-sig")
    fewshot_ci.to_csv(fewshot_path, index=False, encoding="utf-8-sig")

    print("\nSaved bootstrap CI results:")
    print(all_ci_path)
    print(ablation_path)
    print(fewshot_path)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 240)
    pd.set_option("display.max_rows", 300)

    print("\nAblation CI results:")
    print(ablation_ci)

    print("\nFew-shot CI results:")
    print(fewshot_ci)

    # D. Figures
    plot_ablation_ci(ci_df)
    plot_fewshot_ci(ci_df)

    print("\nFigures saved to:")
    print(FIGURES)

    print("\nDone.")


if __name__ == "__main__":
    main()