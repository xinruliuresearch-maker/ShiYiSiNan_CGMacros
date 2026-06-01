# -*- coding: utf-8 -*-
"""
02_build_meal_level_dataset.py

功能：
1. 读取 CGMacros 原始分钟级数据。
2. 提取每一餐的餐前状态、餐食营养特征、餐后血糖反应表型。
3. 合并 bio.csv 和 gut_health_test.csv。
4. 输出 meal-level 建模数据表：
   outputs/tables/meal_level_dataset.csv

适配你的当前数据结构：
- 主文件路径类似：
  data/raw/CGMacros/CGMacros-001/CGMacros-001.csv
- 主文件列包括：
  Timestamp, Libre GL, Dexcom GL, HR, Calories (Activity), METs,
  Meal Type, Calories, Carbs, Protein, Fat, Fiber,
  Amount Consumed , Image path
"""

from pathlib import Path
import re
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

try:
    from tqdm import tqdm
except Exception:
    def tqdm(x, **kwargs):
        return x


# =========================
# 0. 路径设置
# =========================

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT_TABLES = ROOT / "outputs" / "tables"
OUT_TABLES.mkdir(parents=True, exist_ok=True)

PRIMARY_GLUCOSE_COL = "Dexcom GL"
SECONDARY_GLUCOSE_COL = "Libre GL"


# =========================
# 1. 通用工具函数
# =========================

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    标准化列名：
    - 去掉前后空格
    - 统一 METs / Mets
    - 统一 Image path / Image Path
    - 统一 Amount Consumed 后缀空格
    - 统一 bio.csv 中部分带空格的列名
    """
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


def safe_numeric(series):
    """安全转为数值，无法转换的变成 NaN。"""
    return pd.to_numeric(series, errors="coerce")


def find_file(filename: str):
    """在 data/raw 下递归查找某个文件。"""
    matches = list(RAW.rglob(filename))
    return matches[0] if matches else None


def get_subject_id_from_path(path: Path):
    """
    从路径中提取 subject_id。
    例如：
    CGMacros-001.csv -> 1
    CGMacros-040.csv -> 40
    """
    text = str(path)

    matches = re.findall(r"CGMacros-(\d+)", text)
    if matches:
        return int(matches[-1])

    nums = re.findall(r"(\d+)", text)
    if nums:
        return int(nums[-1])

    return None


def trapz_auc(minutes, values):
    """
    手动梯形积分，避免新版 numpy 中 np.trapz 不可用的问题。
    minutes: x 轴，单位为分钟
    values: y 轴，通常为血糖值或血糖增量
    """
    minutes = np.asarray(minutes, dtype=float)
    values = np.asarray(values, dtype=float)

    valid = np.isfinite(minutes) & np.isfinite(values)
    minutes = minutes[valid]
    values = values[valid]

    if len(minutes) < 2:
        return np.nan

    order = np.argsort(minutes)
    minutes = minutes[order]
    values = values[order]

    dx = np.diff(minutes)
    avg_y = (values[:-1] + values[1:]) / 2.0

    return float(np.sum(dx * avg_y))


def pick_glucose_col(df: pd.DataFrame):
    """
    优先使用 Dexcom GL。
    如果 Dexcom 缺失，则使用 Libre GL。
    """
    if PRIMARY_GLUCOSE_COL in df.columns and df[PRIMARY_GLUCOSE_COL].notna().sum() > 0:
        return PRIMARY_GLUCOSE_COL

    if SECONDARY_GLUCOSE_COL in df.columns and df[SECONDARY_GLUCOSE_COL].notna().sum() > 0:
        return SECONDARY_GLUCOSE_COL

    return None


def amount_to_factor(amount):
    """
    Amount Consumed 可能是：
    - 100 表示 100%
    - 50 表示 50%
    - 1 表示 100%
    - 0.5 表示 50%

    这里做兼容处理。
    """
    if pd.isna(amount):
        return 1.0

    try:
        amount = float(amount)
    except Exception:
        return 1.0

    if amount <= 0:
        return np.nan

    if amount <= 1.5:
        return amount

    return amount / 100.0


def is_valid_meal_marker(x):
    """
    判断 Meal Type 是否代表一餐开始。
    排除 NaN、空字符串、字符串 nan。
    """
    if pd.isna(x):
        return False

    s = str(x).strip()
    if s == "":
        return False

    if s.lower() in ["nan", "none", "null"]:
        return False

    return True


# =========================
# 2. 单餐特征提取
# =========================

def extract_meal_features(df: pd.DataFrame, meal_idx: int, subject_id: int):
    """
    对单个 meal marker 提取一餐的特征和标签。

    输入特征：
    - 餐食营养：Calories, Carbs, Protein, Fat, Fiber
    - 按 Amount Consumed 调整后的有效摄入量
    - 餐前血糖状态：餐前 30 分钟中位数/均值/波动
    - 餐前 60 分钟血糖趋势
    - 餐前心率、活动消耗、METs
    - 进餐时间特征

    输出标签：
    - auc_2h
    - iauc_2h
    - peak_glucose_2h
    - peak_delta_2h
    - time_to_peak_2h
    - recovery_time_2h
    - auc_3h
    - iauc_3h
    """

    meal_time = df.loc[meal_idx, "Timestamp"]

    glucose_col = pick_glucose_col(df)
    if glucose_col is None:
        return None

    temp = df.copy()
    temp["rel_min"] = (temp["Timestamp"] - meal_time).dt.total_seconds() / 60.0

    pre_30 = temp[(temp["rel_min"] >= -30) & (temp["rel_min"] <= 0)].copy()
    pre_60 = temp[(temp["rel_min"] >= -60) & (temp["rel_min"] <= 0)].copy()
    post_2h = temp[(temp["rel_min"] >= 0) & (temp["rel_min"] <= 120)].copy()
    post_3h = temp[(temp["rel_min"] >= 0) & (temp["rel_min"] <= 180)].copy()

    n_pre = pre_30[glucose_col].dropna().shape[0]
    n_post2h = post_2h[glucose_col].dropna().shape[0]

    # 数据质量门槛：
    # Dexcom 5分钟一次，2小时约24个点；
    # Libre 15分钟一次，2小时约8个点；
    # 所以设置为至少6个餐后点。
    if n_pre < 3:
        return None

    if n_post2h < 6:
        return None

    baseline = pre_30[glucose_col].median()

    if pd.isna(baseline):
        return None

    g2 = post_2h[["rel_min", glucose_col]].dropna()
    g3 = post_3h[["rel_min", glucose_col]].dropna()

    if g2.shape[0] < 6:
        return None

    g2_minutes = g2["rel_min"].values
    g2_values = g2[glucose_col].values

    delta2 = g2_values - baseline
    positive_delta2 = np.maximum(delta2, 0)

    auc_2h = trapz_auc(g2_minutes, g2_values)
    iauc_2h = trapz_auc(g2_minutes, positive_delta2)

    peak_glucose_2h = float(np.nanmax(g2_values))
    peak_delta_2h = float(peak_glucose_2h - baseline)
    time_to_peak_2h = float(g2_minutes[np.nanargmax(g2_values)])

    if g3.shape[0] >= 8:
        g3_minutes = g3["rel_min"].values
        g3_values = g3[glucose_col].values
        delta3 = g3_values - baseline
        auc_3h = trapz_auc(g3_minutes, g3_values)
        iauc_3h = trapz_auc(g3_minutes, np.maximum(delta3, 0))
    else:
        auc_3h = np.nan
        iauc_3h = np.nan

    # recovery time:
    # 从峰值之后开始，第一次回到 baseline + 10 mg/dL 以内的时间。
    recovery_time = np.nan
    after_peak = g2[g2["rel_min"] >= time_to_peak_2h].copy()
    recovered = after_peak[after_peak[glucose_col] <= baseline + 10]
    if recovered.shape[0] > 0:
        recovery_time = float(recovered["rel_min"].iloc[0])

    # 餐前血糖特征
    pre_glucose_mean_30 = float(pre_30[glucose_col].mean())
    pre_glucose_sd_30 = float(pre_30[glucose_col].std())

    if pre_60[glucose_col].dropna().shape[0] >= 5:
        pre_values = pre_60[glucose_col].dropna()
        first_g = pre_values.iloc[0]
        last_g = pre_values.iloc[-1]
        pre_glucose_slope_60 = float((last_g - first_g) / 60.0)
    else:
        pre_glucose_slope_60 = np.nan

    # 餐前可穿戴特征
    hr_mean_pre30 = pre_30["HR"].mean() if "HR" in pre_30.columns else np.nan

    activity_calories_pre30 = (
        pre_30["Calories (Activity)"].sum()
        if "Calories (Activity)" in pre_30.columns
        else np.nan
    )

    mets_mean_pre30 = (
        pre_30["Mets"].mean()
        if "Mets" in pre_30.columns
        else np.nan
    )

    # 餐食营养特征
    row = temp.loc[meal_idx]

    amount = row.get("Amount Consumed", np.nan)
    factor = amount_to_factor(amount)

    calories = row.get("Calories", np.nan)
    carbs = row.get("Carbs", np.nan)
    protein = row.get("Protein", np.nan)
    fat = row.get("Fat", np.nan)
    fiber = row.get("Fiber", np.nan)

    eff_calories = calories * factor if pd.notna(calories) and pd.notna(factor) else np.nan
    eff_carbs = carbs * factor if pd.notna(carbs) and pd.notna(factor) else np.nan
    eff_protein = protein * factor if pd.notna(protein) and pd.notna(factor) else np.nan
    eff_fat = fat * factor if pd.notna(fat) and pd.notna(factor) else np.nan
    eff_fiber = fiber * factor if pd.notna(fiber) and pd.notna(factor) else np.nan

    # 时间特征
    hour = meal_time.hour + meal_time.minute / 60.0
    hour_sin = np.sin(2 * np.pi * hour / 24.0)
    hour_cos = np.cos(2 * np.pi * hour / 24.0)

    return {
        "subject_id": subject_id,
        "meal_time": meal_time,
        "meal_date": meal_time.date(),
        "meal_hour": hour,
        "meal_hour_sin": hour_sin,
        "meal_hour_cos": hour_cos,

        "meal_type": row.get("Meal Type", np.nan),
        "image_path": row.get("Image Path", np.nan),

        "calories": calories,
        "carbs": carbs,
        "protein": protein,
        "fat": fat,
        "fiber": fiber,
        "amount_consumed": amount,
        "amount_factor": factor,

        "eff_calories": eff_calories,
        "eff_carbs": eff_carbs,
        "eff_protein": eff_protein,
        "eff_fat": eff_fat,
        "eff_fiber": eff_fiber,

        "baseline_glucose": baseline,
        "pre_glucose_mean_30": pre_glucose_mean_30,
        "pre_glucose_sd_30": pre_glucose_sd_30,
        "pre_glucose_slope_60": pre_glucose_slope_60,
        "hr_mean_pre30": hr_mean_pre30,
        "activity_calories_pre30": activity_calories_pre30,
        "mets_mean_pre30": mets_mean_pre30,

        "auc_2h": auc_2h,
        "iauc_2h": iauc_2h,
        "peak_glucose_2h": peak_glucose_2h,
        "peak_delta_2h": peak_delta_2h,
        "time_to_peak_2h": time_to_peak_2h,
        "recovery_time_2h": recovery_time,
        "auc_3h": auc_3h,
        "iauc_3h": iauc_3h,

        "glucose_source": glucose_col,
        "n_pre_points": n_pre,
        "n_post2h_points": n_post2h,
    }


# =========================
# 3. 读取补充表
# =========================

def load_bio():
    f = find_file("bio.csv")
    if f is None:
        print("bio.csv not found")
        return None

    bio = pd.read_csv(f)
    bio = normalize_columns(bio)

    if "subject" in bio.columns:
        bio = bio.rename(columns={"subject": "subject_id"})
    elif "Subject" in bio.columns:
        bio = bio.rename(columns={"Subject": "subject_id"})
    elif "subject_id" not in bio.columns:
        bio = bio.rename(columns={bio.columns[0]: "subject_id"})

    bio["subject_id"] = (
        bio["subject_id"]
        .astype(str)
        .str.extract(r"(\d+)")
        .astype(int)
    )

    # 只转换真正可能用于建模的数值型变量
    numeric_like_cols = [
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
        "#1 Contour Fingerstick GLU",
        " #2 Contour Fingerstick GLU",
        "#3 Contour Fingerstick GLU",
    ]

    for col in numeric_like_cols:
        if col in bio.columns:
            bio[col] = pd.to_numeric(bio[col], errors="coerce")

    return bio


def load_gut_health():
    f = find_file("gut_health_test.csv")
    if f is None:
        print("gut_health_test.csv not found")
        return None

    gut = pd.read_csv(f)
    gut = normalize_columns(gut)

    if "subject" in gut.columns:
        gut = gut.rename(columns={"subject": "subject_id"})
    elif "Subject" in gut.columns:
        gut = gut.rename(columns={"Subject": "subject_id"})
    elif "subject_id" not in gut.columns:
        gut = gut.rename(columns={gut.columns[0]: "subject_id"})

    gut["subject_id"] = gut["subject_id"].astype(str).str.extract(r"(\d+)").astype(int)

    for col in gut.columns:
        if col != "subject_id":
            gut[col] = pd.to_numeric(gut[col], errors="coerce")

    return gut


# =========================
# 4. 主流程
# =========================

def main():
    print("Project root:", ROOT)
    print("Raw data dir:", RAW)

    if not RAW.exists():
        print("ERROR: data/raw does not exist.")
        return

    csv_files = list(RAW.rglob("*.csv"))

    main_files = [
        f for f in csv_files
        if re.search(r"CGMacros-\d+\.csv$", f.name)
    ]

    main_files = sorted(main_files)

    print(f"\nFound participant files: {len(main_files)}")

    if len(main_files) == 0:
        print("No participant files found.")
        print("Please check whether files like CGMacros-001.csv are under data/raw.")
        return

    all_meals = []
    subject_summary = []

    for f in tqdm(main_files, desc="Extracting meals"):
        subject_id = get_subject_id_from_path(f)

        try:
            df = pd.read_csv(f)
        except Exception as e:
            print(f"\nFailed to read {f}: {e}")
            continue

        df = normalize_columns(df)

        required_cols = ["Timestamp", "Meal Type"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            print(f"\nSkip {f}, missing columns: {missing}")
            continue

        # 时间处理
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df = df.dropna(subset=["Timestamp"]).sort_values("Timestamp").reset_index(drop=True)

        # 数值列处理
        non_numeric_cols = ["Timestamp", "Meal Type", "Image Path"]
        for col in df.columns:
            if col not in non_numeric_cols:
                df[col] = safe_numeric(df[col])

        glucose_col = pick_glucose_col(df)

        if glucose_col is None:
            subject_summary.append({
                "subject_id": subject_id,
                "file": str(f),
                "n_rows": len(df),
                "n_meal_markers": 0,
                "n_extracted_meals": 0,
                "glucose_col": None,
                "status": "no_glucose"
            })
            continue

        meal_indices = [
            idx for idx in df.index
            if is_valid_meal_marker(df.loc[idx, "Meal Type"])
        ]

        n_extracted = 0

        for idx in meal_indices:
            features = extract_meal_features(df, idx, subject_id)
            if features is not None:
                all_meals.append(features)
                n_extracted += 1

        subject_summary.append({
            "subject_id": subject_id,
            "file": str(f),
            "n_rows": len(df),
            "n_meal_markers": len(meal_indices),
            "n_extracted_meals": n_extracted,
            "glucose_col": glucose_col,
            "status": "ok"
        })

    summary_df = pd.DataFrame(subject_summary)
    summary_out = OUT_TABLES / "subject_extraction_summary.csv"
    summary_df.to_csv(summary_out, index=False, encoding="utf-8-sig")

    print("\nSaved subject extraction summary:")
    print(summary_out)

    print("\nSubject extraction summary:")
    if not summary_df.empty:
        print(summary_df[[
            "subject_id",
            "n_rows",
            "n_meal_markers",
            "n_extracted_meals",
            "glucose_col",
            "status"
        ]].head(50))

    meal_df = pd.DataFrame(all_meals)

    print("\nMeal-level shape before merge:", meal_df.shape)

    if meal_df.empty:
        print("\nERROR: No meals were extracted.")
        print("Possible reasons:")
        print("1. Meal Type markers are missing or not recognized.")
        print("2. Glucose data are too sparse around meal times.")
        print("3. Timestamp parsing failed.")
        print("Please send subject_extraction_summary.csv or terminal output.")
        return

    # 合并 bio.csv
    bio = load_bio()
    if bio is not None:
        print("\nBio shape:", bio.shape)
        meal_df = meal_df.merge(
            bio,
            on="subject_id",
            how="left",
            suffixes=("", "_bio")
        )

    # 合并 gut_health_test.csv
    gut = load_gut_health()
    if gut is not None:
        print("\nGut health shape:", gut.shape)
        meal_df = meal_df.merge(
            gut,
            on="subject_id",
            how="left",
            suffixes=("", "_gut")
        )

    # 排序和上一餐间隔
    meal_df["meal_time"] = pd.to_datetime(meal_df["meal_time"], errors="coerce")
    meal_df = meal_df.sort_values(["subject_id", "meal_time"]).reset_index(drop=True)

    meal_df["prev_meal_time"] = meal_df.groupby("subject_id")["meal_time"].shift(1)
    meal_df["prev_meal_gap_min"] = (
        meal_df["meal_time"] - meal_df["prev_meal_time"]
    ).dt.total_seconds() / 60.0

    meal_df["meal_index_within_subject"] = meal_df.groupby("subject_id").cumcount() + 1

    # 保存主表
    out = OUT_TABLES / "meal_level_dataset.csv"
    meal_df.to_csv(out, index=False, encoding="utf-8-sig")

    print("\nSaved meal-level dataset:")
    print(out)

    print("\nFinal meal-level shape:", meal_df.shape)
    print("Number of subjects:", meal_df["subject_id"].nunique())

    print("\nMeals per subject summary:")
    print(meal_df["subject_id"].value_counts().describe())

    preview_cols = [
        "subject_id",
        "meal_time",
        "meal_type",
        "eff_calories",
        "eff_carbs",
        "eff_protein",
        "eff_fat",
        "eff_fiber",
        "baseline_glucose",
        "iauc_2h",
        "peak_delta_2h",
        "glucose_source",
        "n_pre_points",
        "n_post2h_points",
    ]
    preview_cols = [c for c in preview_cols if c in meal_df.columns]

    print("\nPreview:")
    print(meal_df[preview_cols].head(20))

    outcome_cols = [
        "iauc_2h",
        "peak_delta_2h",
        "time_to_peak_2h",
        "recovery_time_2h",
    ]

    print("\nOutcome summary:")
    print(meal_df[outcome_cols].describe())

    key_cols = [
        "eff_calories",
        "eff_carbs",
        "eff_protein",
        "eff_fat",
        "eff_fiber",
        "baseline_glucose",
        "iauc_2h",
        "peak_delta_2h",
        "hr_mean_pre30",
        "activity_calories_pre30",
        "mets_mean_pre30",
    ]
    key_cols = [c for c in key_cols if c in meal_df.columns]

    print("\nMissing rate of key variables:")
    print(meal_df[key_cols].isna().mean().sort_values(ascending=False))

    print("\nDone.")


if __name__ == "__main__":
    main()