"""Nested cross-validation for tuned top tabular models."""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline

import run_glycemic_phase_research as primary
from run_journal_grade_experiments import make_ml_phase, target_data, markdown_table


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"
DOCS_DIR = ROOT / "docs"
RANDOM_STATE = 42

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
warnings.filterwarnings("ignore", message="X does not have valid feature names.*")


def ensure_dirs() -> None:
    for path in [RESULTS_DIR, FIGURES_DIR, DOCS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def top_tuning_experiments(ml_phase: pd.DataFrame) -> pd.DataFrame:
    metrics = pd.read_csv(RESULTS_DIR / "journal_calibration_metrics.csv")
    candidates = metrics[metrics["model"].isin(["logistic_ridge", "xgboost", "lightgbm"])].copy()
    rows = []
    for target, group in candidates.groupby("target"):
        rows.append(group.sort_values(["auroc", "brier"], ascending=[False, True]).head(3))
        c4 = group[group["feature_set"].eq("C4_phase_map")].sort_values(["auroc", "brier"], ascending=[False, True]).head(1)
        if not c4.empty:
            rows.append(c4)
    out = pd.concat(rows, ignore_index=True).drop_duplicates(subset=["target", "feature_set", "model"])
    feature_names = {fs.name for fs in primary.get_feature_sets(ml_phase)}
    out = out[out["feature_set"].isin(feature_names)]
    return out[["target", "feature_set", "model"]].reset_index(drop=True)


def search_space(model_name: str) -> tuple[dict, int | None, str]:
    if model_name == "logistic_ridge":
        return {"model__C": [0.03, 0.1, 0.3, 1.0, 3.0, 10.0]}, None, "grid"
    if model_name == "xgboost":
        return (
            {
                "model__n_estimators": [140, 220, 320],
                "model__max_depth": [2, 3, 4],
                "model__learning_rate": [0.02, 0.04, 0.07],
                "model__subsample": [0.75, 0.9, 1.0],
                "model__colsample_bytree": [0.75, 0.9, 1.0],
                "model__reg_lambda": [1.0, 2.0, 4.0],
            },
            12,
            "randomized",
        )
    if model_name == "lightgbm":
        return (
            {
                "model__n_estimators": [140, 220, 320],
                "model__max_depth": [2, 3, 4],
                "model__learning_rate": [0.02, 0.04, 0.07],
                "model__subsample": [0.75, 0.9, 1.0],
                "model__colsample_bytree": [0.75, 0.9, 1.0],
                "model__reg_lambda": [1.0, 2.0, 4.0],
            },
            12,
            "randomized",
        )
    raise ValueError(f"Unsupported model for tuning: {model_name}")


def make_search(pipe: Pipeline, model_name: str, inner_cv: StratifiedKFold):
    params, n_iter, mode = search_space(model_name)
    if mode == "grid":
        return GridSearchCV(pipe, params, scoring="roc_auc", cv=inner_cv, n_jobs=1, refit=True)
    return RandomizedSearchCV(
        pipe,
        params,
        n_iter=n_iter,
        scoring="roc_auc",
        cv=inner_cv,
        n_jobs=1,
        refit=True,
        random_state=RANDOM_STATE,
    )


def run_nested_cv(ml_phase: pd.DataFrame, experiments: pd.DataFrame) -> pd.DataFrame:
    feature_sets = {fs.name: fs for fs in primary.get_feature_sets(ml_phase)}
    models = primary.get_models()
    rows = []
    outer_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    inner_cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=RANDOM_STATE)
    for _, exp in experiments.iterrows():
        target = exp["target"]
        feature_set_name = exp["feature_set"]
        model_name = exp["model"]
        data = target_data(ml_phase, target).reset_index(drop=True)
        fs = feature_sets[feature_set_name]
        feature_cols = fs.numeric + fs.categorical
        x = data[feature_cols]
        y = data[target].astype(int)
        base_pipe = Pipeline([("prep", primary.make_preprocessor(fs)), ("model", clone(models[model_name]))])
        for fold, (train_idx, test_idx) in enumerate(outer_cv.split(x, y), start=1):
            search = make_search(clone(base_pipe), model_name, inner_cv)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                search.fit(x.iloc[train_idx], y.iloc[train_idx])
                prob = primary.model_predict_proba(search.best_estimator_, x.iloc[test_idx])
            y_test = y.iloc[test_idx].to_numpy()
            rows.append(
                {
                    "target": target,
                    "feature_set": feature_set_name,
                    "model": model_name,
                    "outer_fold": fold,
                    "n_train": int(len(train_idx)),
                    "n_test": int(len(test_idx)),
                    "positive_rate_test": float(np.mean(y_test)),
                    "inner_best_auroc": float(search.best_score_),
                    "test_auroc": float(roc_auc_score(y_test, prob)) if len(np.unique(y_test)) == 2 else np.nan,
                    "test_auprc": float(average_precision_score(y_test, prob)) if len(np.unique(y_test)) == 2 else np.nan,
                    "test_brier": float(brier_score_loss(y_test, np.clip(prob, 0, 1))),
                    "best_params": json.dumps(search.best_params_, ensure_ascii=False, sort_keys=True),
                }
            )
    return pd.DataFrame(rows)


def summarize_nested(nested: pd.DataFrame) -> pd.DataFrame:
    return (
        nested.groupby(["target", "feature_set", "model"], as_index=False)
        .agg(
            outer_folds=("outer_fold", "count"),
            total_test_n=("n_test", "sum"),
            auroc_mean=("test_auroc", "mean"),
            auroc_sd=("test_auroc", "std"),
            auprc_mean=("test_auprc", "mean"),
            brier_mean=("test_brier", "mean"),
            inner_auroc_mean=("inner_best_auroc", "mean"),
        )
        .sort_values(["target", "auroc_mean"], ascending=[True, False])
    )


def plot_nested(summary: pd.DataFrame) -> None:
    if summary.empty:
        return
    targets = summary["target"].unique().tolist()
    fig, axes = plt.subplots(1, len(targets), figsize=(8 * len(targets), 5), squeeze=False)
    for ax, target in zip(axes.ravel(), targets):
        dat = summary[summary["target"].eq(target)].sort_values("auroc_mean", ascending=True)
        labels = dat["feature_set"] + " / " + dat["model"]
        ax.barh(labels, dat["auroc_mean"], xerr=dat["auroc_sd"].fillna(0), color="#3f6f8f")
        ax.set_xlim(0.5, max(0.9, dat["auroc_mean"].max() + 0.05))
        ax.set_xlabel("Nested CV AUROC")
        ax.set_title(target)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "journal_nested_tuning_auroc.png", dpi=220)
    plt.close()


def write_report(experiments: pd.DataFrame, summary: pd.DataFrame) -> None:
    report = f"""# Nested CV 微调模型实验

生成脚本：`scripts/run_nested_tuning_experiments.py`

## 目的

该实验对表现靠前的 logistic ridge、XGBoost 和 LightGBM 进行内层调参、外层评估，减少“在同一交叉验证中选模型并报告性能”的乐观偏倚。它是主模型比较的稳健性补充，而不是替代全部模型基准。

## 纳入微调的候选模型

{markdown_table(experiments)}

## Nested CV 结果

{markdown_table(summary)}

图形：`figures/journal_nested_tuning_auroc.png`

## 解释

若 nested CV 的 AUROC 低于普通 5 折 CV，说明原始模型比较包含模型选择乐观偏倚；投稿时应优先报告 nested CV 或外部 LOSO 结果作为稳健估计。
"""
    (DOCS_DIR / "nested_tuning_experiment_report_zh.md").write_text(report, encoding="utf-8")


def main() -> int:
    ensure_dirs()
    ml_phase = make_ml_phase()
    experiments = top_tuning_experiments(ml_phase)
    nested = run_nested_cv(ml_phase, experiments)
    summary = summarize_nested(nested)
    experiments.to_csv(RESULTS_DIR / "journal_nested_tuning_experiments.csv", index=False)
    nested.to_csv(RESULTS_DIR / "journal_nested_tuning_results.csv", index=False)
    summary.to_csv(RESULTS_DIR / "journal_nested_tuning_summary.csv", index=False)
    plot_nested(summary)
    write_report(experiments, summary)
    print(
        json.dumps(
            {
                "nested_experiments": int(len(experiments)),
                "outer_fold_rows": int(len(nested)),
                "summary_rows": int(len(summary)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
