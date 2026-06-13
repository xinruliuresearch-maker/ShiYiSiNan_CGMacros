# -*- coding: utf-8 -*-
"""
Stage 5 for the integrated mainline project.

Create a data-driven bionic digestion experiment design from CGMacros high-risk
meals. This stage does not perform wet-lab experiments; it produces the
candidate meal list, prototype matrix, and protocol needed to run Prof. Chen's
in vitro bionic digestion validation.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import textwrap

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NHANES_ROOT = ROOT.parent / "NHANES_MetS_Project"
STAGE1 = ROOT / "outputs" / "integrated_mainline" / "stage1_msi"
OUT = ROOT / "outputs" / "integrated_mainline" / "stage5_bionic_digestion_design"
NHANES_OUT = NHANES_ROOT / "result" / "integrated_mainline" / "stage5_bionic_digestion_design"


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    NHANES_OUT.mkdir(parents=True, exist_ok=True)


def z(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    sd = x.std(ddof=0)
    if not np.isfinite(sd) or sd == 0:
        return x * 0
    return (x - x.mean()) / sd


def load_data() -> pd.DataFrame:
    df = pd.read_csv(STAGE1 / "cgmacros_meal_level_with_msi_core.csv")
    df["meal_time"] = pd.to_datetime(df["meal_time"], errors="coerce")
    numeric = [
        "calories",
        "carbs",
        "protein",
        "fat",
        "fiber",
        "iauc_2h",
        "peak_delta_2h",
        "msi_core_partial_nhanes_ref",
    ]
    for c in numeric:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["carb_fiber_ratio"] = (df["carbs"] + 1) / (df["fiber"].clip(lower=0) + 1)
    df["carb_protein_ratio"] = (df["carbs"] + 1) / (df["protein"].clip(lower=0) + 1)
    df["carb_fat_combo"] = z(df["carbs"]) + z(df["fat"])
    df["ppgr_score"] = z(df["iauc_2h"]) + z(df["peak_delta_2h"])
    df["meal_risk_score"] = (
        1.4 * z(df["iauc_2h"]) +
        1.2 * z(df["peak_delta_2h"]) +
        1.0 * z(df["msi_core_partial_nhanes_ref"]) +
        0.8 * z(df["carbs"]) +
        0.5 * z(df["carb_fiber_ratio"]) +
        0.4 * z(df["fat"]) -
        0.3 * z(df["fiber"])
    )
    return df


def classify_meal(row: pd.Series) -> str:
    carbs = row["carbs"]
    fat = row["fat"]
    fiber = row["fiber"]
    protein = row["protein"]
    if carbs >= 70 and fiber <= 5:
        return "refined_high_carb_low_fiber"
    if carbs >= 50 and fat >= 25:
        return "high_carb_high_fat_processed_proxy"
    if carbs >= 50 and protein >= 35:
        return "high_carb_high_protein_mixed"
    if fiber >= 8 and carbs >= 45:
        return "high_carb_high_fiber_comparator"
    if row["msi_core_tertile_within_dataset"] == "high" and row["iauc_2h"] >= 4500:
        return "high_msi_high_ppgr_real_meal"
    return "model_high_risk_other"


def select_candidates(df: pd.DataFrame, n_total: int = 12) -> pd.DataFrame:
    d = df.dropna(subset=["meal_risk_score", "iauc_2h", "peak_delta_2h", "carbs"]).copy()
    # Keep candidates experimentally reproducible; extreme entries are likely
    # logging or portion-size artifacts and are poor wet-lab prototypes.
    d = d.loc[
        (d["carbs"].between(10, 200))
        & (d["calories"].between(50, 2000))
        & (d["protein"].between(0, 160))
        & (d["fat"].between(0, 160))
        & (d["fiber"].between(0, 80))
    ].copy()
    d["prototype_class"] = d.apply(classify_meal, axis=1)
    d = d.sort_values("meal_risk_score", ascending=False)

    selected = []
    per_subject = {}
    per_class = {}
    for _, row in d.iterrows():
        sid = row["subject_id"]
        cls = row["prototype_class"]
        if per_subject.get(sid, 0) >= 2:
            continue
        if per_class.get(cls, 0) >= 3:
            continue
        selected.append(row)
        per_subject[sid] = per_subject.get(sid, 0) + 1
        per_class[cls] = per_class.get(cls, 0) + 1
        if len(selected) >= n_total:
            break

    out = pd.DataFrame(selected).copy()
    out["candidate_id"] = [f"CGM_BD_{i:02d}" for i in range(1, len(out) + 1)]
    out["recommended_redesign"] = out.apply(recommend_redesign, axis=1)
    out["primary_mechanistic_contrast"] = out.apply(contrast, axis=1)
    keep = [
        "candidate_id",
        "subject_id",
        "meal_time",
        "meal_type",
        "prototype_class",
        "msi_core_tertile_within_dataset",
        "msi_core_partial_nhanes_ref",
        "calories",
        "carbs",
        "protein",
        "fat",
        "fiber",
        "carb_fiber_ratio",
        "iauc_2h",
        "peak_delta_2h",
        "meal_risk_score",
        "image_path",
        "recommended_redesign",
        "primary_mechanistic_contrast",
    ]
    return out[keep]


def recommend_redesign(row: pd.Series) -> str:
    cls = row["prototype_class"]
    if "low_fiber" in cls:
        return "Add 5 g soluble fiber and/or replace 25-30% refined starch with resistant-starch/whole-grain equivalent"
    if "high_fat" in cls:
        return "Reduce refined carbohydrate to 45 g available carbs and replace energy with lean protein/non-starchy vegetables"
    if "high_protein" in cls:
        return "Keep protein constant; compare intact-grain/low-gelatinization starch vs original starch structure"
    if "high_fiber" in cls:
        return "Use as lower-release comparator; match available carbohydrate with refined-starch prototype"
    return "Model-guided redesign: cap available carbs at 45 g and add 5 g fiber"


def contrast(row: pd.Series) -> str:
    cls = row["prototype_class"]
    if "low_fiber" in cls:
        return "Refined starch rapid-release vs fiber/resistant-starch slowed release"
    if "high_fat" in cls:
        return "High-fat high-carb mixed matrix vs lower-carb protein/fiber substitution"
    if "high_protein" in cls:
        return "Same carbohydrate load with altered starch physical structure"
    if "high_fiber" in cls:
        return "Naturally higher-fiber comparator for glucose-release attenuation"
    return "Observed high PPGR meal vs model-recommended low-risk redesign"


def prototype_matrix(candidates: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in candidates.iterrows():
        for version in ["original", "redesigned"]:
            rows.append(
                {
                    "candidate_id": r["candidate_id"],
                    "experiment_group": f"{r['candidate_id']}_{version}",
                    "version": version,
                    "prototype_class": r["prototype_class"],
                    "base_subject_id": r["subject_id"],
                    "base_meal_time": r["meal_time"],
                    "target_available_carbs_g": r["carbs"] if version == "original" else min(r["carbs"], 45),
                    "target_fiber_added_g": 0 if version == "original" else 5,
                    "technical_replicates": 3,
                    "primary_endpoint": "glucose_release_iAUC_0_60min",
                    "secondary_endpoints": "Cmax; Tmax; iAUC_0_120min; early_slope; half_release_time; viscosity; particle_size_D50",
                    "mechanistic_contrast": r["primary_mechanistic_contrast"],
                    "redesign_rule": "original recipe/prototype" if version == "original" else r["recommended_redesign"],
                }
            )
    return pd.DataFrame(rows)


def write_protocol(candidates: pd.DataFrame, matrix: pd.DataFrame) -> Path:
    class_counts = candidates["prototype_class"].value_counts()
    class_table = ["| prototype_class | n |", "|---|---:|"]
    for cls, n in class_counts.items():
        class_table.append(f"| {cls} | {int(n)} |")
    class_table_text = "\n".join(class_table)

    report = f"""# Stage 5 报告：仿生消化实验样本选择与方案

日期：2026-06-10

## 目的

用少量、数据驱动选择的餐食原型验证主线机制：

`high metabolic susceptibility + high-risk meal load -> exaggerated PPGR`

以及：

`digestion-informed meal redesign -> lower early glucose release`

## 样本选择

从 CGMacros meal-level 数据中按以下因素构建优先级：

- 2h iAUC 和 2h peak delta 高。
- 受试者 MSI-core 高。
- 碳水负荷高。
- carbohydrate/fiber ratio 高。
- 脂肪和碳水组合负荷高。
- 纤维低。

为避免样本过度集中，同一 subject 最多选 2 餐，同一 prototype class 最多选 3 餐。

本轮选出 {len(candidates)} 个候选真实餐，对应 {len(matrix)} 个 original/redesigned 实验组。每组 3 个技术重复，预计总实验单元 {len(matrix) * 3} 个。

## 候选类别

{class_table_text}

## 实验设计

每个候选餐建立两个版本：

1. original：按真实餐食宏量结构复原。
2. redesigned：按模型推荐进行低风险重构，包括可利用碳水上限、增加纤维、抗性淀粉/完整谷物替换、或碳水-蛋白/非淀粉蔬菜替换。

## 动态消化采样

建议采样时间点：

- gastric phase: 0, 15, 30, 60 min
- intestinal phase: 75, 90, 120, 180 min

主要终点：

- glucose release iAUC 0-60 min
- glucose release Cmax
- early release slope

次要终点：

- glucose release iAUC 0-120 min
- Tmax
- half-release time
- simulated gastric emptying half-time
- viscosity/rheology
- particle size D50
- resistant starch or starch gelatinization/retrogradation proxy

## 统计分析

1. 对每个 candidate 比较 original vs redesigned 的 paired difference。
2. 使用技术重复均值和 bootstrap CI。
3. 主判据：redesigned 版本的 early glucose release iAUC 0-60 min 下降，且方向与 CGMacros 模型预测的 PPGR 降低一致。
4. 将 release features 映射为 digestion-informed features，用于后续 M5 模型。

## 质量控制

- 每批包含空白消化液对照。
- 每批包含标准葡萄糖/淀粉阳性对照。
- 餐食制备重量、含水量、处理温度和冷却时间记录。
- 若涉及食品接触材料或塑化剂检测，必须使用玻璃器皿阴性对照、field blank、procedural blank 和回收率评估。

## 输出文件

- `stage5_candidate_meals_for_bionic_digestion.csv`
- `stage5_bionic_digestion_experiment_matrix.csv`
- `stage5_bionic_digestion_protocol_2026-06-10.md`
"""
    out = OUT / "stage5_bionic_digestion_protocol_2026-06-10.md"
    out.write_text(textwrap.dedent(report), encoding="utf-8-sig")
    return out


def main() -> None:
    ensure_dirs()
    df = load_data()
    candidates = select_candidates(df, 12)
    matrix = prototype_matrix(candidates)

    cand_out = OUT / "stage5_candidate_meals_for_bionic_digestion.csv"
    matrix_out = OUT / "stage5_bionic_digestion_experiment_matrix.csv"
    candidates.to_csv(cand_out, index=False, encoding="utf-8-sig")
    matrix.to_csv(matrix_out, index=False, encoding="utf-8-sig")
    protocol_out = write_protocol(candidates, matrix)

    for path in [cand_out, matrix_out, protocol_out]:
        shutil.copy2(path, NHANES_OUT / path.name)

    print("Stage 5 bionic digestion design completed.")
    print(f"Output directory: {OUT}")
    print(candidates[["candidate_id", "subject_id", "prototype_class", "msi_core_tertile_within_dataset", "carbs", "fiber", "iauc_2h", "peak_delta_2h", "recommended_redesign"]].to_string(index=False))


if __name__ == "__main__":
    main()
