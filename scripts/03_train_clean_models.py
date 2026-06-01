# -*- coding: utf-8 -*-
"""
03_train_clean_models.py

升级 1：清洗主模型特征

功能：
1. 读取 outputs/tables/meal_level_dataset.csv。
2. 明确排除：
   - 指尖血糖变量 Contour Fingerstick GLU
   - 原始 nutrient 变量 calories/carbs/protein/fat/fiber
   - outcome 变量
   - 时间字符串变量
   - 数据质量计数变量
   - 图像路径、设备来源等非建模变量
3. 构建清洗后的特征组：
   - M2_deployable_core: meal + pre-CGM + wearable/time
   - M3_clinical_enhanced: M2 + clinical baseline
   - M4_gut_exploratory: M3 + gut health features
4. 重新训练模型：
   - Ridge
   - Random Forest
   - HistGradientBoosting
5. 输出：
   - clean_leakage_audit.csv
   - clean_feature_manifest.csv
   - clean_baseline_model_results.csv
   - clean_personalization_results.csv
   - clean_feature_importance.csv
"""

from pathlib import Path
import re
import warnings
import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.model_selection import GroupKFold
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance

try:
    from sklearn.preprocessing import OneHotEncoder
except Exception as e:
    raise ImportError("scikit-learn is not installed correctly.") from e

warnings.filterwarnings("ignore")


# =========================
# 0. 路径设置
# =========================

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

DATA_PATH = TABLES / "meal_level_dataset.csv"


# =========================
# 1. 目标变量
# =========================

TARGETS = [
    "iauc_2h",
    "peak_delta_2h",
]


# =========================
# 2. 清洗后允许进入主模型的特征组
# =========================

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

CLINICAL_FEATURES = [
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

BASE_CATEGORICAL_FEATURES = [
    "meal_type",
]

CLINICAL_CATEGORICAL_FEATURES = [
    "Gender",
]


# =========================
# 3. 禁止进入主模型的变量规则
# =========================

FORBIDDEN_EXACT = {
    # 原始营养变量：与 eff_* 重复，不进入主模型
    "calories",
    "carbs",
    "protein",
    "fat",
    "fiber",
    "amount_consumed",
    "amount_factor",

    # 结果变量
    "auc_2h",
    "iauc_2h",
    "peak_glucose_2h",
    "peak_delta_2h",
    "time_to_peak_2h",
    "recovery_time_2h",
    "auc_3h",
    "iauc_3h",

    # 非生理输入或数据质量变量
    "image_path",
    "glucose_source",
    "n_pre_points",
    "n_post2h_points",
    "Unnamed: 0",

    # 时间字符串或采样时间
    "Time (t)",
    "Time (t).1",
    "Time (t).2",
    "Collection time PDL (Lab)",

    # 指尖血糖，主模型禁用
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


# =========================
# 4. 工具函数
# =========================

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

    df = df.rename(columns={c: rename_map.get(c, c) for c in df.columns})
    return df


def find_file(filename: str):
    matches = list(RAW.rglob(filename))
    return matches[0] if matches else None


def forbidden_reason(col: str):
    """
    判断某个列是否应禁止进入主模型。
    返回 None 表示允许；返回字符串表示禁止原因。
    """
    c = str(col).strip()
    lower = c.lower()

    if c in FORBIDDEN_EXACT:
        return "explicitly_forbidden"

    for pattern in FORBIDDEN_REGEX:
        if re.search(pattern, lower):
            return f"regex_forbidden:{pattern}"

    # 原始营养变量大小写兜底
    if lower in ["calories", "carbs", "protein", "fat", "fiber", "amount consumed"]:
        return "raw_nutrient_duplicate"

    return None


def build_leakage_audit(df: pd.DataFrame):
    rows = []
    for col in df.columns:
        reason = forbidden_reason(col)
        if reason is not None:
            rows.append({
                "column": col,
                "reason": reason,
                "dtype": str(df[col].dtype),
                "missing_rate": float(df[col].isna().mean()),
            })

    audit = pd.DataFrame(rows).sort_values(["reason", "column"])
    return audit


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

    # 保守截尾，减少极端值对第一版模型比较的影响
    q_low = data[target].quantile(0.01)
    q_high = data[target].quantile(0.99)
    data = data[(data[target] >= q_low) & (data[target] <= q_high)]

    data["subject_id"] = data["subject_id"].astype(int)
    data["meal_time"] = pd.to_datetime(data["meal_time"], errors="coerce")

    data = data.dropna(subset=["meal_time"])

    return data.reset_index(drop=True)


def get_gut_health_features(df: pd.DataFrame):
    """
    从 gut_health_test.csv 中识别 gut health 特征。
    注意：只把 gut_health_test.csv 中出现、且已经 merge 到 meal_df 的列作为 gut features。
    不自动加入 microbes.csv 中的 1979 个细菌变量。
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

    candidate_cols = [c for c in gut.columns if c != "subject_id"]

    gut_features = []
    for col in candidate_cols:
        if col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                if forbidden_reason(col) is None:
                    gut_features.append(col)

    return gut_features


def filter_existing_numeric(df, features):
    """
    保留：
    - 在 df 中存在
    - 数值型
    - 不是全缺失
    - 不是禁用变量
    """
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


def filter_existing_categorical(df, features):
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


def build_feature_sets(df: pd.DataFrame):
    """
    构建清洗后的特征集。
    M2 是最接近真实部署的核心模型；
    M3 是临床增强模型；
    M4 是 gut health 探索模型。
    """
    gut_features = get_gut_health_features(df)

    feature_sets = {}

    # M2: deployable core
    m2_numeric = (
        MEAL_FEATURES
        + PRE_CGM_FEATURES
        + WEARABLE_TIME_FEATURES
    )
    m2_categorical = BASE_CATEGORICAL_FEATURES

    feature_sets["M2_deployable_core"] = {
        "numeric": filter_existing_numeric(df, m2_numeric),
        "categorical": filter_existing_categorical(df, m2_categorical),
        "description": "meal + preprandial CGM + wearable/time",
    }

    # M3: clinical-enhanced
    m3_numeric = m2_numeric + CLINICAL_FEATURES
    m3_categorical = BASE_CATEGORICAL_FEATURES + CLINICAL_CATEGORICAL_FEATURES

    feature_sets["M3_clinical_enhanced"] = {
        "numeric": filter_existing_numeric(df, m3_numeric),
        "categorical": filter_existing_categorical(df, m3_categorical),
        "description": "M2 + clinical baseline",
    }

    # M4: gut exploratory
    m4_numeric = m3_numeric + gut_features
    m4_categorical = m3_categorical

    feature_sets["M4_gut_exploratory"] = {
        "numeric": filter_existing_numeric(df, m4_numeric),
        "categorical": filter_existing_categorical(df, m4_categorical),
        "description": "M3 + gut health features, exploratory",
    }

    # 最终安全检查
    for fs_name, spec in feature_sets.items():
        all_features = spec["numeric"] + spec["categorical"]
        bad = [f for f in all_features if forbidden_reason(f) is not None]
        if bad:
            raise RuntimeError(
                f"Forbidden features found in {fs_name}: {bad}"
            )

    return feature_sets


def save_feature_manifest(feature_sets):
    rows = []

    for fs_name, spec in feature_sets.items():
        for f in spec["numeric"]:
            rows.append({
                "feature_set": fs_name,
                "feature": f,
                "type": "numeric",
                "description": spec["description"],
            })

        for f in spec["categorical"]:
            rows.append({
                "feature_set": fs_name,
                "feature": f,
                "type": "categorical",
                "description": spec["description"],
            })

    manifest = pd.DataFrame(rows)
    out = TABLES / "clean_feature_manifest.csv"
    manifest.to_csv(out, index=False, encoding="utf-8-sig")
    return manifest


def make_pipeline(model, numeric_features, categorical_features):
    transformers = []

    if len(numeric_features) > 0:
        numeric_transformer = Pipeline(steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])

        transformers.append(
            ("num", numeric_transformer, numeric_features)
        )

    if len(categorical_features) > 0:
        categorical_transformer = Pipeline(steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", make_onehot_encoder()),
        ])

        transformers.append(
            ("cat", categorical_transformer, categorical_features)
        )

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
        "ridge": Ridge(alpha=1.0),

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


# =========================
# 5. 验证方式
# =========================

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
        "feature_set_description": feature_spec["description"],
        "model": model_name,
        "validation": "leave_subject_out",
        "include_subject_id": False,
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
        "feature_set_description": feature_spec["description"],
        "model": model_name,
        "validation": "within_subject_temporal_split",
        "include_subject_id": False,
        "n_meals": int(len(data)),
        "n_subjects": int(data["subject_id"].nunique()),
        "n_numeric_features": int(len(numeric_features)),
        "n_categorical_features": int(len(categorical_features)),
    })

    return metrics


def evaluate_few_shot_personalization(df, target, feature_set_name, feature_spec, model_name, model, shots_list=(0, 1, 3, 5, 10)):
    """
    few-shot 只对清洗后的主模型做。
    注意：这里不把 subject_id 当作特征，避免用 ID 记忆个体。
    个体化来自于加入目标个体前 k 餐数据，而不是通过 subject_id。
    """
    data = df.copy()
    data = data.sort_values(["subject_id", "meal_time"]).reset_index(drop=True)

    numeric_features = feature_spec["numeric"]
    categorical_features = feature_spec["categorical"]
    features = numeric_features + categorical_features

    results = []

    for k in shots_list:
        all_true = []
        all_pred = []

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

            all_true.extend(y_test)
            all_pred.extend(pred)

        if len(all_true) > 0:
            metrics = evaluate_predictions(np.array(all_true), np.array(all_pred))
            metrics.update({
                "target": target,
                "feature_set": feature_set_name,
                "feature_set_description": feature_spec["description"],
                "model": model_name,
                "validation": "few_shot_personalization",
                "shots": int(k),
                "include_subject_id": False,
                "n_test_total": int(len(all_true)),
            })
            results.append(metrics)

    return results


def calculate_permutation_importance(df, target, feature_set_name, feature_spec, model_name, model):
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

    numeric_features = feature_spec["numeric"]
    categorical_features = feature_spec["categorical"]
    features = numeric_features + categorical_features

    X = data[features]
    y = data[target].values

    train_idx = np.array(train_indices)
    test_idx = np.array(test_indices)

    pipe = make_pipeline(model, numeric_features, categorical_features)
    pipe.fit(X.iloc[train_idx], y[train_idx])

    result = permutation_importance(
        pipe,
        X.iloc[test_idx],
        y[test_idx],
        n_repeats=15,
        random_state=42,
        scoring="neg_mean_absolute_error",
        n_jobs=-1,
    )

    importance_df = pd.DataFrame({
        "target": target,
        "feature_set": feature_set_name,
        "model": model_name,
        "feature": features,
        "importance_mean": result.importances_mean,
        "importance_std": result.importances_std,
    }).sort_values("importance_mean", ascending=False)

    return importance_df


# =========================
# 6. 主流程
# =========================

def main():
    print("Project root:", ROOT)
    print("Data path:", DATA_PATH)

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Cannot find {DATA_PATH}. Please run 02_build_meal_level_dataset.py first."
        )

    df = pd.read_csv(DATA_PATH)
    df.columns = [str(c).strip() for c in df.columns]

    print("\nLoaded meal-level dataset:", df.shape)

    df["meal_time"] = pd.to_datetime(df["meal_time"], errors="coerce")

    # 1. 输出泄漏审计表
    leakage_audit = build_leakage_audit(df)
    leakage_path = TABLES / "clean_leakage_audit.csv"
    leakage_audit.to_csv(leakage_path, index=False, encoding="utf-8-sig")

    print("\nSaved leakage audit:")
    print(leakage_path)

    print("\nForbidden/leakage-prone columns detected:")
    print(leakage_audit.head(50))

    # 2. 构建清洗后的特征集
    feature_sets = build_feature_sets(df)
    manifest = save_feature_manifest(feature_sets)

    print("\nSaved clean feature manifest:")
    print(TABLES / "clean_feature_manifest.csv")

    print("\nClean feature manifest:")
    print(manifest)

    # 3. 模型
    models = get_models()

    all_results = []
    all_fewshot = []
    all_importance = []

    # performance：三个 feature set 都跑
    feature_sets_to_evaluate = [
        "M2_deployable_core",
        "M3_clinical_enhanced",
        "M4_gut_exploratory",
    ]

    # few-shot：只对主模型 M3 跑 RF/HGB，避免计算过重
    fewshot_feature_set = "M3_clinical_enhanced"
    fewshot_models = ["random_forest", "hist_gradient_boosting"]

    # importance：只对主模型 M3 + HGB 跑
    importance_feature_set = "M3_clinical_enhanced"
    importance_model = "hist_gradient_boosting"

    for target in TARGETS:
        print("\n" + "=" * 90)
        print(f"Target: {target}")
        print("=" * 90)

        data = clean_dataset(df, target)

        print("Data shape after cleaning:", data.shape)
        print("Number of subjects:", data["subject_id"].nunique())
        print("Target summary:")
        print(data[target].describe())

        for fs_name in feature_sets_to_evaluate:
            feature_spec = feature_sets[fs_name]

            print("\n" + "-" * 80)
            print(f"Feature set: {fs_name}")
            print(feature_spec["description"])
            print("Numeric features:", feature_spec["numeric"])
            print("Categorical features:", feature_spec["categorical"])

            for model_name, model in models.items():
                print(f"\nRunning {model_name}...")

                try:
                    res_lso = evaluate_leave_subject_out(
                        data,
                        target,
                        fs_name,
                        feature_spec,
                        model_name,
                        model,
                    )
                    all_results.append(res_lso)

                    print("  leave_subject_out:", {
                        "MAE": round(res_lso["MAE"], 4),
                        "RMSE": round(res_lso["RMSE"], 4),
                        "R2": round(res_lso["R2"], 4),
                        "Pearson_r": round(res_lso["Pearson_r"], 4)
                        if pd.notna(res_lso["Pearson_r"]) else None,
                    })

                except Exception as e:
                    print(f"  leave_subject_out failed: {e}")

                try:
                    res_ws = evaluate_within_subject_temporal(
                        data,
                        target,
                        fs_name,
                        feature_spec,
                        model_name,
                        model,
                    )
                    all_results.append(res_ws)

                    print("  within_subject_temporal_split:", {
                        "MAE": round(res_ws["MAE"], 4),
                        "RMSE": round(res_ws["RMSE"], 4),
                        "R2": round(res_ws["R2"], 4),
                        "Pearson_r": round(res_ws["Pearson_r"], 4)
                        if pd.notna(res_ws["Pearson_r"]) else None,
                    })

                except Exception as e:
                    print(f"  within_subject_temporal_split failed: {e}")

        # few-shot personalization
        print("\n" + "-" * 80)
        print(f"Few-shot personalization for {target}")

        fs_spec = feature_sets[fewshot_feature_set]

        for model_name in fewshot_models:
            model = models[model_name]
            print(f"Few-shot model: {model_name}")

            try:
                fs_results = evaluate_few_shot_personalization(
                    data,
                    target,
                    fewshot_feature_set,
                    fs_spec,
                    model_name,
                    model,
                    shots_list=(0, 1, 3, 5, 10),
                )
                all_fewshot.extend(fs_results)
                for r in fs_results:
                    print("  shots:", r["shots"], "MAE:", round(r["MAE"], 4), "RMSE:", round(r["RMSE"], 4))
            except Exception as e:
                print(f"  few-shot failed: {e}")

        # feature importance
        print("\n" + "-" * 80)
        print(f"Feature importance for {target}")

        try:
            imp = calculate_permutation_importance(
                data,
                target,
                importance_feature_set,
                feature_sets[importance_feature_set],
                importance_model,
                models[importance_model],
            )
            all_importance.append(imp)
            print(imp.head(20))
        except Exception as e:
            print(f"  feature importance failed: {e}")

    # 4. 保存结果
    results_df = pd.DataFrame(all_results)
    fewshot_df = pd.DataFrame(all_fewshot)

    if len(all_importance) > 0:
        importance_df = pd.concat(all_importance, axis=0, ignore_index=True)
    else:
        importance_df = pd.DataFrame()

    results_path = TABLES / "clean_baseline_model_results.csv"
    fewshot_path = TABLES / "clean_personalization_results.csv"
    importance_path = TABLES / "clean_feature_importance.csv"

    results_df.to_csv(results_path, index=False, encoding="utf-8-sig")
    fewshot_df.to_csv(fewshot_path, index=False, encoding="utf-8-sig")
    importance_df.to_csv(importance_path, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 90)
    print("Saved clean results:")
    print(results_path)
    print(fewshot_path)
    print(importance_path)

    print("\nClean baseline model results:")
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 220)
    print(results_df)

    print("\nClean few-shot personalization results:")
    print(fewshot_df)

    print("\nClean top feature importance:")
    if not importance_df.empty:
        print(importance_df.head(40))
    else:
        print("No importance results.")

    print("\nDone.")


if __name__ == "__main__":
    main()