# -*- coding: utf-8 -*-
"""
05_ablation_study.py

升级 2：更细粒度 feature-set ablation

目标：
回答“哪一类数据真正提升了餐后血糖反应预测性能？”

特征集：
M0_meal_only:
    eff_calories, eff_carbs, eff_protein, eff_fat, eff_fiber

M1_meal_pre_cgm:
    M0 + baseline_glucose, pre_glucose_mean_30, pre_glucose_sd_30, pre_glucose_slope_60

M2_meal_pre_cgm_wearable_time:
    M1 + hr_mean_pre30, activity_calories_pre30, mets_mean_pre30,
         meal_hour_sin, meal_hour_cos, prev_meal_gap_min

M3_clinical_enhanced:
    M2 + Age, Gender, BMI, A1c, fasting glucose, insulin, lipids, etc.

M4_gut_exploratory:
    M3 + gut_health_test.csv 中的 gut health variables

输出：
- outputs/tables/ablation_feature_manifest.csv
- outputs/tables/ablation_results.csv
- outputs/tables/ablation_incremental_gain.csv
- outputs/tables/ablation_best_results.csv
- outputs/figures/ablation_*.png
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
from sklearn.inspection import permutation_importance

try:
    from sklearn.preprocessing import OneHotEncoder
except Exception as e:
    raise ImportError("scikit-learn is not installed correctly.") from e

warnings.filterwarnings("ignore")


# ============================================================
# 0. 路径
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

DATA_PATH = TABLES / "meal_level_dataset.csv"


# ============================================================
# 1. 目标变量
# ============================================================

TARGETS = [
    "iauc_2h",
    "peak_delta_2h",
]


# ============================================================
# 2. 特征组
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
# 3. 禁止进入模型的变量
# ============================================================

FORBIDDEN_EXACT = {
    # 原始营养变量，避免与 eff_* 重复
    "calories",
    "carbs",
    "protein",
    "fat",
    "fiber",
    "amount_consumed",
    "amount_factor",

    # 目标/派生结果变量
    "auc_2h",
    "iauc_2h",
    "peak_glucose_2h",
    "peak_delta_2h",
    "time_to_peak_2h",
    "recovery_time_2h",
    "auc_3h",
    "iauc_3h",

    # 质量控制/非输入变量
    "image_path",
    "glucose_source",
    "n_pre_points",
    "n_post2h_points",
    "Unnamed: 0",

    # 时间字符串
    "Time (t)",
    "Time (t).1",
    "Time (t).2",
    "Collection time PDL (Lab)",

    # 指尖血糖，主模型与消融实验中禁用
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
# 4. 工具函数
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


def evaluate_predictions(y_true, y_pred):
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": rmse(y_true, y_pred),
        "R2": float(r2_score(y_true, y_pred)),
        "Pearson_r": pearson_r(y_true, y_pred),
        "n_test": int(len(y_true)),
    }


def clean_dataset(df, target):
    data = df.copy()
    data = data.dropna(subset=[target, "subject_id"])

    # 与前面保持一致：1%–99% 截尾，防止极端餐次主导模型比较
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
    """
    只识别 gut_health_test.csv 中的变量。
    不加入 microbes.csv 的 1979 个细菌变量，避免高维小样本过拟合。
    """
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
    """
    构建 M0–M4 五层消融特征集。
    """
    gut_features = get_gut_health_features(df)

    specs = {}

    # M0: meal only
    specs["M0_meal_only"] = {
        "order": 0,
        "numeric": filter_numeric_features(df, MEAL_FEATURES),
        "categorical": filter_categorical_features(df, MEAL_CATEGORICAL_FEATURES),
        "description": "meal composition only",
    }

    # M1: meal + pre-CGM
    specs["M1_meal_pre_cgm"] = {
        "order": 1,
        "numeric": filter_numeric_features(df, MEAL_FEATURES + PRE_CGM_FEATURES),
        "categorical": filter_categorical_features(df, MEAL_CATEGORICAL_FEATURES),
        "description": "meal composition + preprandial CGM",
    }

    # M2: meal + pre-CGM + wearable/time
    specs["M2_meal_pre_cgm_wearable_time"] = {
        "order": 2,
        "numeric": filter_numeric_features(
            df,
            MEAL_FEATURES + PRE_CGM_FEATURES + WEARABLE_TIME_FEATURES
        ),
        "categorical": filter_categorical_features(df, MEAL_CATEGORICAL_FEATURES),
        "description": "M1 + wearable and timing features",
    }

    # M3: clinical-enhanced
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

    # M4: gut exploratory
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

    # 安全检查
    for fs_name, spec in specs.items():
        all_features = spec["numeric"] + spec["categorical"]
        bad = [f for f in all_features if forbidden_reason(f) is not None]
        if bad:
            raise RuntimeError(f"Forbidden features found in {fs_name}: {bad}")

    return specs


def save_feature_manifest(feature_sets):
    rows = []

    for fs_name, spec in feature_sets.items():
        for f in spec["numeric"]:
            rows.append({
                "feature_set": fs_name,
                "feature_order": spec["order"],
                "feature": f,
                "type": "numeric",
                "description": spec["description"],
            })

        for f in spec["categorical"]:
            rows.append({
                "feature_set": fs_name,
                "feature_order": spec["order"],
                "feature": f,
                "type": "categorical",
                "description": spec["description"],
            })

    manifest = pd.DataFrame(rows)
    out = TABLES / "ablation_feature_manifest.csv"
    manifest.to_csv(out, index=False, encoding="utf-8-sig")
    return manifest


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
# 5. 验证函数
# ============================================================

def evaluate_leave_subject_out(df, target, feature_set_name, feature_spec, model_name, model):
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

    all_true = []
    all_pred = []

    for train_idx, test_idx in gkf.split(X, y, groups):
        pipe = make_pipeline(model, numeric_features, categorical_features)
        pipe.fit(X.iloc[train_idx], y[train_idx])
        pred = pipe.predict(X.iloc[test_idx])

        all_true.extend(y[test_idx])
        all_pred.extend(pred)

    metrics = evaluate_predictions(np.array(all_true), np.array(all_pred))
    metrics.update({
        "target": target,
        "feature_set": feature_set_name,
        "feature_order": int(feature_spec["order"]),
        "feature_set_description": feature_spec["description"],
        "model": model_name,
        "validation": "leave_subject_out",
        "n_meals": int(len(data)),
        "n_subjects": int(n_subjects),
        "n_numeric_features": int(len(numeric_features)),
        "n_categorical_features": int(len(categorical_features)),
    })

    return metrics


def evaluate_within_subject_temporal(df, target, feature_set_name, feature_spec, model_name, model):
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

    metrics = evaluate_predictions(y[test_idx], pred)
    metrics.update({
        "target": target,
        "feature_set": feature_set_name,
        "feature_order": int(feature_spec["order"]),
        "feature_set_description": feature_spec["description"],
        "model": model_name,
        "validation": "within_subject_temporal_split",
        "n_meals": int(len(data)),
        "n_subjects": int(data["subject_id"].nunique()),
        "n_numeric_features": int(len(numeric_features)),
        "n_categorical_features": int(len(categorical_features)),
    })

    return metrics


# ============================================================
# 6. 增量收益计算
# ============================================================

def compute_incremental_gain(results_df):
    """
    对每个 target + validation + model，
    计算 M0→M1→M2→M3→M4 的增量收益。

    MAE / RMSE 越低越好；
    R2 / Pearson_r 越高越好。
    """
    rows = []

    group_cols = ["target", "validation", "model"]

    for keys, sub in results_df.groupby(group_cols):
        sub = sub.sort_values("feature_order").reset_index(drop=True)

        prev = None

        for _, row in sub.iterrows():
            current = row.to_dict()

            if prev is None:
                rows.append({
                    **{c: current[c] for c in group_cols},
                    "feature_set": current["feature_set"],
                    "feature_order": current["feature_order"],
                    "previous_feature_set": None,
                    "MAE": current["MAE"],
                    "RMSE": current["RMSE"],
                    "R2": current["R2"],
                    "Pearson_r": current["Pearson_r"],
                    "delta_MAE": np.nan,
                    "delta_MAE_percent": np.nan,
                    "delta_RMSE": np.nan,
                    "delta_RMSE_percent": np.nan,
                    "delta_R2": np.nan,
                    "delta_Pearson_r": np.nan,
                })
            else:
                delta_mae = prev["MAE"] - current["MAE"]
                delta_rmse = prev["RMSE"] - current["RMSE"]
                delta_r2 = current["R2"] - prev["R2"]
                delta_pr = current["Pearson_r"] - prev["Pearson_r"]

                rows.append({
                    **{c: current[c] for c in group_cols},
                    "feature_set": current["feature_set"],
                    "feature_order": current["feature_order"],
                    "previous_feature_set": prev["feature_set"],
                    "MAE": current["MAE"],
                    "RMSE": current["RMSE"],
                    "R2": current["R2"],
                    "Pearson_r": current["Pearson_r"],
                    "delta_MAE": delta_mae,
                    "delta_MAE_percent": delta_mae / prev["MAE"] * 100 if prev["MAE"] != 0 else np.nan,
                    "delta_RMSE": delta_rmse,
                    "delta_RMSE_percent": delta_rmse / prev["RMSE"] * 100 if prev["RMSE"] != 0 else np.nan,
                    "delta_R2": delta_r2,
                    "delta_Pearson_r": delta_pr,
                })

            prev = current

    return pd.DataFrame(rows)


def compute_best_results(results_df):
    """
    每个 target + validation + model 选择 MAE 最低的特征集。
    """
    rows = []

    for keys, sub in results_df.groupby(["target", "validation", "model"]):
        best = sub.sort_values("MAE", ascending=True).iloc[0].to_dict()
        rows.append(best)

    return pd.DataFrame(rows)


# ============================================================
# 7. 作图
# ============================================================

def plot_ablation(results_df):
    """
    生成清晰的 ablation 论文初图。
    仅画 hist_gradient_boosting 作为主模型。
    """
    model_to_plot = "hist_gradient_boosting"

    plot_df = results_df[results_df["model"] == model_to_plot].copy()
    plot_df = plot_df.sort_values(["target", "validation", "feature_order"])

    short_names = {
        "M0_meal_only": "M0\nMeal",
        "M1_meal_pre_cgm": "M1\n+Pre-CGM",
        "M2_meal_pre_cgm_wearable_time": "M2\n+Wearable/Time",
        "M3_clinical_enhanced": "M3\n+Clinical",
        "M4_gut_exploratory": "M4\n+Gut",
    }

    for target in TARGETS:
        for metric in ["MAE", "RMSE", "Pearson_r", "R2"]:
            sub_target = plot_df[plot_df["target"] == target].copy()

            if sub_target.empty:
                continue

            plt.figure(figsize=(8, 5))

            for validation in ["leave_subject_out", "within_subject_temporal_split"]:
                sub = sub_target[sub_target["validation"] == validation].copy()
                sub = sub.sort_values("feature_order")

                x = [short_names.get(fs, fs) for fs in sub["feature_set"]]
                y = sub[metric].values

                label = (
                    "Leave-subject-out"
                    if validation == "leave_subject_out"
                    else "Within-subject temporal"
                )

                plt.plot(x, y, marker="o", label=label)

            ylabel = metric
            if metric == "Pearson_r":
                ylabel = "Pearson r"

            title_target = (
                "2-h glucose iAUC"
                if target == "iauc_2h"
                else "2-h peak glucose excursion"
            )

            plt.xlabel("Feature set")
            plt.ylabel(ylabel)
            plt.title(f"Feature-set ablation for {title_target} ({model_to_plot})")
            plt.legend()
            plt.tight_layout()

            out = FIGURES / f"ablation_{metric.lower()}_{target}_{model_to_plot}.png"
            plt.savefig(out, dpi=300)
            plt.close()


# ============================================================
# 8. 主流程
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

    # 构建特征集
    feature_sets = build_feature_sets(df)
    manifest = save_feature_manifest(feature_sets)

    print("\nSaved ablation feature manifest:")
    print(TABLES / "ablation_feature_manifest.csv")
    print(manifest)

    models = get_models()

    all_results = []

    for target in TARGETS:
        print("\n" + "=" * 90)
        print(f"Target: {target}")
        print("=" * 90)

        data = clean_dataset(df, target)

        print("Data shape after target cleaning:", data.shape)
        print("Number of subjects:", data["subject_id"].nunique())
        print("Target summary:")
        print(data[target].describe())

        for fs_name, fs_spec in feature_sets.items():
            print("\n" + "-" * 80)
            print(f"Feature set: {fs_name}")
            print(fs_spec["description"])
            print("Numeric:", fs_spec["numeric"])
            print("Categorical:", fs_spec["categorical"])

            for model_name, model in models.items():
                print(f"\nRunning model: {model_name}")

                try:
                    res_lso = evaluate_leave_subject_out(
                        data,
                        target,
                        fs_name,
                        fs_spec,
                        model_name,
                        model,
                    )
                    all_results.append(res_lso)

                    print("  leave_subject_out:", {
                        "MAE": round(res_lso["MAE"], 4),
                        "RMSE": round(res_lso["RMSE"], 4),
                        "R2": round(res_lso["R2"], 4),
                        "Pearson_r": round(res_lso["Pearson_r"], 4),
                    })

                except Exception as e:
                    print(f"  leave_subject_out failed: {e}")

                try:
                    res_ws = evaluate_within_subject_temporal(
                        data,
                        target,
                        fs_name,
                        fs_spec,
                        model_name,
                        model,
                    )
                    all_results.append(res_ws)

                    print("  within_subject_temporal_split:", {
                        "MAE": round(res_ws["MAE"], 4),
                        "RMSE": round(res_ws["RMSE"], 4),
                        "R2": round(res_ws["R2"], 4),
                        "Pearson_r": round(res_ws["Pearson_r"], 4),
                    })

                except Exception as e:
                    print(f"  within_subject_temporal_split failed: {e}")

    results_df = pd.DataFrame(all_results)
    results_df = results_df.sort_values(
        ["target", "model", "validation", "feature_order"]
    ).reset_index(drop=True)

    gain_df = compute_incremental_gain(results_df)
    best_df = compute_best_results(results_df)

    results_path = TABLES / "ablation_results.csv"
    gain_path = TABLES / "ablation_incremental_gain.csv"
    best_path = TABLES / "ablation_best_results.csv"

    results_df.to_csv(results_path, index=False, encoding="utf-8-sig")
    gain_df.to_csv(gain_path, index=False, encoding="utf-8-sig")
    best_df.to_csv(best_path, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 90)
    print("Saved ablation results:")
    print(results_path)
    print(gain_path)
    print(best_path)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 240)
    pd.set_option("display.max_rows", 300)

    print("\nAblation results:")
    print(results_df)

    print("\nIncremental gain:")
    print(gain_df)

    print("\nBest results by target-validation-model:")
    print(best_df)

    # 画图
    plot_ablation(results_df)

    print("\nFigures saved to:")
    print(FIGURES)

    print("\nDone.")


if __name__ == "__main__":
    main()