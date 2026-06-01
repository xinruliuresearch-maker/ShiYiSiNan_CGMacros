# -*- coding: utf-8 -*-
"""
03_train_baseline_models.py

功能：
1. 读取 outputs/tables/meal_level_dataset.csv。
2. 训练 baseline 模型预测餐后血糖反应：
   - iauc_2h
   - peak_delta_2h
3. 比较两类验证方式：
   - leave_subject_out：新用户泛化
   - within_subject_temporal_split：已有用户预测未来餐
4. 进行 few-shot personalization：
   - 0 / 1 / 3 / 5 餐个体适配
5. 输出：
   - baseline_model_results.csv
   - personalization_results.csv
   - feature_importance.csv
"""

from pathlib import Path
import warnings
import numpy as np
import pandas as pd

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
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

DATA_PATH = TABLES / "meal_level_dataset.csv"


# =========================
# 1. 建模目标与特征
# =========================

TARGETS = [
    "iauc_2h",
    "peak_delta_2h",
]

NUMERIC_FEATURE_CANDIDATES = [
    # 餐食营养特征
    "eff_calories",
    "eff_carbs",
    "eff_protein",
    "eff_fat",
    "eff_fiber",
    "amount_factor",

    # 餐前血糖状态
    "baseline_glucose",
    "pre_glucose_mean_30",
    "pre_glucose_sd_30",
    "pre_glucose_slope_60",

    # 餐前可穿戴状态
    "hr_mean_pre30",
    "activity_calories_pre30",
    "mets_mean_pre30",

    # 时间与进餐历史
    "meal_hour",
    "meal_hour_sin",
    "meal_hour_cos",
    "prev_meal_gap_min",
    "meal_index_within_subject",

    # 个体基线，来自 bio.csv
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

    # gut_health_test.csv 中可能存在的特征，不确定具体列名；
    # 后面会自动筛选数值列加入，不需要在这里全部列出。
]

CATEGORICAL_FEATURE_CANDIDATES = [
    "meal_type",
    "Gender",
    "Self-identify",
]


# =========================
# 2. 工具函数
# =========================

def make_onehot_encoder():
    """
    兼容不同 scikit-learn 版本。
    新版本参数是 sparse_output=False；
    旧版本参数是 sparse=False。
    """
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
    """
    清洗建模数据：
    1. 去除目标缺失；
    2. 去除 subject_id 缺失；
    3. 对目标变量做 1% - 99% 截尾，减少极端值对 baseline 的影响。
    """
    data = df.copy()

    data = data.dropna(subset=[target, "subject_id"])

    q_low = data[target].quantile(0.01)
    q_high = data[target].quantile(0.99)
    data = data[(data[target] >= q_low) & (data[target] <= q_high)]

    data["subject_id"] = data["subject_id"].astype(int)
    data["meal_time"] = pd.to_datetime(data["meal_time"], errors="coerce")

    return data.reset_index(drop=True)


def select_features(df, include_subject_id=False, include_extra_numeric=True):
    """
    自动选择可用特征。
    include_subject_id:
        True 表示把 subject_id 当作类别特征，用于已有用户/个体化场景。
        False 表示不加入 subject_id，用于新用户泛化。
    include_extra_numeric:
        True 表示把未列入候选表、但明显是数值型的 gut health 等变量也加入。
    """

    numeric_features = [c for c in NUMERIC_FEATURE_CANDIDATES if c in df.columns]
    categorical_features = [c for c in CATEGORICAL_FEATURE_CANDIDATES if c in df.columns]

    exclude_cols = set([
        "subject_id",
        "meal_time",
        "meal_date",
        "prev_meal_time",
        "image_path",
        "glucose_source",

        # 原始和结果变量
        "auc_2h",
        "iauc_2h",
        "peak_glucose_2h",
        "peak_delta_2h",
        "time_to_peak_2h",
        "recovery_time_2h",
        "auc_3h",
        "iauc_3h",

        # 数据质量计数，不作为生理输入
        "n_pre_points",
        "n_post2h_points",

        # 纯索引列
        "Unnamed: 0",
    ])

    if include_extra_numeric:
        for col in df.columns:
            if col in exclude_cols:
                continue
            if col in numeric_features or col in categorical_features:
                continue

            if pd.api.types.is_numeric_dtype(df[col]):
                # 排除明显不适合作为输入的时间/指纹血糖采样时间等
                lower = col.lower()
                if "time" in lower:
                    continue
                numeric_features.append(col)

    if include_subject_id:
        df = df.copy()
        df["subject_id_cat"] = df["subject_id"].astype(str)
        categorical_features = categorical_features + ["subject_id_cat"]

    features = numeric_features + categorical_features

    return df, numeric_features, categorical_features, features


def make_pipeline(model, numeric_features, categorical_features):
    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", make_onehot_encoder()),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ],
        remainder="drop",
        sparse_threshold=0.0,
    )

    pipe = Pipeline(steps=[
        ("preprocess", preprocessor),
        ("model", model),
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
# 3. 验证方式一：Leave-subject-out
# =========================

def evaluate_leave_subject_out(df, target, model_name, model):
    """
    新用户泛化场景：
    训练集和测试集的 subject 完全不同。
    这是最严格、最接近“陌生新用户”的验证。
    """
    data = df.copy()
    data, numeric_features, categorical_features, features = select_features(
        data,
        include_subject_id=False,
        include_extra_numeric=True,
    )

    X = data[features]
    y = data[target].values
    groups = data["subject_id"].values

    n_subjects = data["subject_id"].nunique()
    n_splits = min(5, n_subjects)

    gkf = GroupKFold(n_splits=n_splits)

    all_true = []
    all_pred = []

    for fold, (train_idx, test_idx) in enumerate(gkf.split(X, y, groups), start=1):
        pipe = make_pipeline(model, numeric_features, categorical_features)
        pipe.fit(X.iloc[train_idx], y[train_idx])

        pred = pipe.predict(X.iloc[test_idx])

        all_true.extend(y[test_idx])
        all_pred.extend(pred)

    metrics = evaluate_predictions(np.array(all_true), np.array(all_pred))
    metrics.update({
        "target": target,
        "model": model_name,
        "validation": "leave_subject_out",
        "include_subject_id": False,
        "n_meals": int(len(data)),
        "n_subjects": int(n_subjects),
    })

    return metrics


# =========================
# 4. 验证方式二：Within-subject temporal split
# =========================

def evaluate_within_subject_temporal(df, target, model_name, model):
    """
    已有用户未来餐预测场景：
    对每个 subject 按时间排序；
    前 80% 餐用于训练，后 20% 餐用于测试。
    这是食以司南/Aura 最重要的产品场景。
    """
    data = df.copy()
    data = data.sort_values(["subject_id", "meal_time"]).reset_index(drop=True)

    train_indices = []
    test_indices = []

    for sid, sub in data.groupby("subject_id"):
        idx = sub.index.to_numpy()
        n = len(idx)

        if n < 5:
            # 餐数太少则全部用于训练，不进入测试
            train_indices.extend(idx.tolist())
            continue

        cut = int(np.floor(n * 0.8))
        cut = max(1, min(cut, n - 1))

        train_indices.extend(idx[:cut].tolist())
        test_indices.extend(idx[cut:].tolist())

    if len(test_indices) == 0:
        raise RuntimeError("No test meals available for within-subject temporal split.")

    data, numeric_features, categorical_features, features = select_features(
        data,
        include_subject_id=True,
        include_extra_numeric=True,
    )

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
        "model": model_name,
        "validation": "within_subject_temporal_split",
        "include_subject_id": True,
        "n_meals": int(len(data)),
        "n_subjects": int(data["subject_id"].nunique()),
    })

    return metrics


# =========================
# 5. Few-shot personalization
# =========================

def evaluate_few_shot_personalization(df, target, model_name, model, shots_list=(0, 1, 3, 5)):
    """
    Few-shot 个体化适配：
    对每个 subject：
    - 其他所有 subject 的数据作为基础训练集；
    - 加入该 subject 最早的 k 餐作为个体适配数据；
    - 测试该 subject 之后的所有餐。

    shots = 0 表示完全陌生用户；
    shots = 1/3/5 表示用户已经记录了 1/3/5 餐。
    """
    data = df.copy()
    data = data.sort_values(["subject_id", "meal_time"]).reset_index(drop=True)

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

            train, numeric_features, categorical_features, features = select_features(
                train,
                include_subject_id=True,
                include_extra_numeric=True,
            )

            test, _, _, _ = select_features(
                test,
                include_subject_id=True,
                include_extra_numeric=True,
            )

            # 确保测试集列与训练集一致
            missing_cols = [c for c in features if c not in test.columns]
            for c in missing_cols:
                test[c] = np.nan

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
                "model": model_name,
                "validation": "few_shot_personalization",
                "shots": int(k),
                "include_subject_id": True,
                "n_test_total": int(len(all_true)),
            })
            results.append(metrics)

    return results


# =========================
# 6. 特征重要性
# =========================

def calculate_permutation_importance(df, target, model_name, model):
    """
    用 within-subject temporal split 的测试集计算 permutation importance。
    注意：
    这个重要性是预测重要性，不是因果效应。
    """
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

    data, numeric_features, categorical_features, features = select_features(
        data,
        include_subject_id=True,
        include_extra_numeric=True,
    )

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
        "model": model_name,
        "feature": features,
        "importance_mean": result.importances_mean,
        "importance_std": result.importances_std,
    }).sort_values("importance_mean", ascending=False)

    return importance_df


# =========================
# 7. 主函数
# =========================

def main():
    print("Project root:", ROOT)
    print("Data path:", DATA_PATH)

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Cannot find {DATA_PATH}. Please run scripts/02_build_meal_level_dataset.py first."
        )

    df = pd.read_csv(DATA_PATH)
    print("\nLoaded meal-level dataset:", df.shape)

    df["meal_time"] = pd.to_datetime(df["meal_time"], errors="coerce")

    models = get_models()

    all_results = []
    all_fewshot_results = []
    all_importance = []

    for target in TARGETS:
        print("\n" + "=" * 80)
        print(f"Target: {target}")
        print("=" * 80)

        data = clean_dataset(df, target)

        print("Data shape after cleaning:", data.shape)
        print("Number of subjects:", data["subject_id"].nunique())
        print("Target summary:")
        print(data[target].describe())

        for model_name, model in models.items():
            print(f"\nRunning model: {model_name}")

            try:
                res_lso = evaluate_leave_subject_out(
                    data,
                    target,
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

            try:
                fs_results = evaluate_few_shot_personalization(
                    data,
                    target,
                    model_name,
                    model,
                    shots_list=(0, 1, 3, 5),
                )
                all_fewshot_results.extend(fs_results)
                print("  few-shot done.")
            except Exception as e:
                print(f"  few-shot failed: {e}")

        # 为了节省时间，只对 hist_gradient_boosting 计算特征重要性
        try:
            print("\nCalculating permutation importance for hist_gradient_boosting...")
            imp = calculate_permutation_importance(
                data,
                target,
                "hist_gradient_boosting",
                models["hist_gradient_boosting"],
            )
            all_importance.append(imp)
            print(imp.head(10))
        except Exception as e:
            print(f"  feature importance failed: {e}")

    results_df = pd.DataFrame(all_results)
    fewshot_df = pd.DataFrame(all_fewshot_results)

    if len(all_importance) > 0:
        importance_df = pd.concat(all_importance, axis=0, ignore_index=True)
    else:
        importance_df = pd.DataFrame()

    results_path = TABLES / "baseline_model_results.csv"
    fewshot_path = TABLES / "personalization_results.csv"
    importance_path = TABLES / "feature_importance.csv"

    results_df.to_csv(results_path, index=False, encoding="utf-8-sig")
    fewshot_df.to_csv(fewshot_path, index=False, encoding="utf-8-sig")
    importance_df.to_csv(importance_path, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 80)
    print("Saved results:")
    print(results_path)
    print(fewshot_path)
    print(importance_path)

    print("\nBaseline model results:")
    print(results_df)

    print("\nFew-shot personalization results:")
    print(fewshot_df)

    print("\nTop feature importance:")
    if not importance_df.empty:
        print(importance_df.head(30))
    else:
        print("No importance results.")

    print("\nDone.")


if __name__ == "__main__":
    main()