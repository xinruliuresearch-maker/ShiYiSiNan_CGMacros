# -*- coding: utf-8 -*-
"""
04_make_figures.py

功能：
1. 读取 meal_level_dataset.csv、baseline_model_results.csv、
   personalization_results.csv、feature_importance.csv。
2. 生成论文可用的初版结果图：
   - outcome distribution
   - model comparison
   - few-shot personalization
   - feature importance
3. 输出到 outputs/figures/
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

meal_path = TABLES / "meal_level_dataset.csv"
results_path = TABLES / "baseline_model_results.csv"
fewshot_path = TABLES / "personalization_results.csv"
importance_path = TABLES / "feature_importance.csv"

meal_df = pd.read_csv(meal_path)
results = pd.read_csv(results_path)
fewshot = pd.read_csv(fewshot_path)
importance = pd.read_csv(importance_path)

# =========================
# Figure 1: outcome distribution
# =========================

for target in ["iauc_2h", "peak_delta_2h"]:
    if target not in meal_df.columns:
        continue

    plt.figure(figsize=(7, 5))
    plt.hist(meal_df[target].dropna(), bins=35)
    plt.xlabel(target)
    plt.ylabel("Number of meals")
    plt.title(f"Distribution of {target}")
    plt.tight_layout()
    plt.savefig(FIGURES / f"fig_outcome_distribution_{target}.png", dpi=300)
    plt.close()


# =========================
# Figure 2: model comparison
# =========================

for target in results["target"].unique():
    sub = results[results["target"] == target].copy()

    sub["label"] = sub["model"] + "\n" + sub["validation"]

    plt.figure(figsize=(10, 5))
    plt.bar(range(len(sub)), sub["RMSE"])
    plt.xticks(range(len(sub)), sub["label"], rotation=45, ha="right")
    plt.ylabel("RMSE")
    plt.title(f"Model comparison for {target}")
    plt.tight_layout()
    plt.savefig(FIGURES / f"fig_model_comparison_rmse_{target}.png", dpi=300)
    plt.close()

    plt.figure(figsize=(10, 5))
    plt.bar(range(len(sub)), sub["MAE"])
    plt.xticks(range(len(sub)), sub["label"], rotation=45, ha="right")
    plt.ylabel("MAE")
    plt.title(f"Model comparison for {target}")
    plt.tight_layout()
    plt.savefig(FIGURES / f"fig_model_comparison_mae_{target}.png", dpi=300)
    plt.close()


# =========================
# Figure 3: within-subject vs leave-subject-out
# =========================

for target in results["target"].unique():
    sub = results[results["target"] == target].copy()

    # 重点展示 tree-based 模型，避免 ridge 异常值压缩图形
    sub = sub[sub["model"].isin(["random_forest", "hist_gradient_boosting"])]

    if sub.empty:
        continue

    pivot = sub.pivot(index="model", columns="validation", values="MAE")

    plt.figure(figsize=(7, 5))
    pivot.plot(kind="bar")
    plt.ylabel("MAE")
    plt.title(f"Generalization vs personalization: {target}")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(FIGURES / f"fig_generalization_vs_personalization_{target}.png", dpi=300)
    plt.close()


# =========================
# Figure 4: few-shot personalization
# =========================

for target in fewshot["target"].unique():
    sub = fewshot[fewshot["target"] == target].copy()

    plt.figure(figsize=(7, 5))
    for model in sub["model"].unique():
        m = sub[sub["model"] == model].sort_values("shots")
        plt.plot(m["shots"], m["MAE"], marker="o", label=model)

    plt.xlabel("Number of subject-specific meals for adaptation")
    plt.ylabel("MAE")
    plt.title(f"Few-shot personalization for {target}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / f"fig_few_shot_mae_{target}.png", dpi=300)
    plt.close()

    plt.figure(figsize=(7, 5))
    for model in sub["model"].unique():
        m = sub[sub["model"] == model].sort_values("shots")
        plt.plot(m["shots"], m["RMSE"], marker="o", label=model)

    plt.xlabel("Number of subject-specific meals for adaptation")
    plt.ylabel("RMSE")
    plt.title(f"Few-shot personalization for {target}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / f"fig_few_shot_rmse_{target}.png", dpi=300)
    plt.close()


# =========================
# Figure 5: feature importance
# =========================

for target in importance["target"].unique():
    sub = importance[importance["target"] == target].copy()

    if "hist_gradient_boosting" in sub["model"].unique():
        sub = sub[sub["model"] == "hist_gradient_boosting"]

    sub = sub.sort_values("importance_mean", ascending=False).head(20)

    plt.figure(figsize=(8, 7))
    plt.barh(sub["feature"][::-1], sub["importance_mean"][::-1])
    plt.xlabel("Permutation importance")
    plt.title(f"Top predictive features for {target}")
    plt.tight_layout()
    plt.savefig(FIGURES / f"fig_feature_importance_{target}.png", dpi=300)
    plt.close()


print("Figures saved to:", FIGURES)
print("Done.")