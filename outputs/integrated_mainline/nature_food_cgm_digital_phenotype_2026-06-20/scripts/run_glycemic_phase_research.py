"""Run glycemic phase-map, outcome, ML, and treatment-response analyses.

This script implements the five research objectives described in
docs/hu_jiliang_inspired_research_design_zh.md using the already cleaned public
JAEB diabetes datasets.

Outputs:
    data/processed/glycemic_phase_features.csv
    data/processed/glycemic_phase_labels.csv
    results/phase_outcome_summary.csv
    results/phase_association_tests.csv
    results/model_performance_cv.csv
    results/model_performance_loso.csv
    results/hte_by_phase.csv
    results/individualized_intervention_framework.csv
    docs/glycemic_phase_research_report_zh.md
    figures/*.png
"""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.base import clone
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    mean_absolute_error,
    mean_squared_error,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover - optional dependency
    XGBClassifier = None

try:
    from lightgbm import LGBMClassifier
except Exception:  # pragma: no cover - optional dependency
    LGBMClassifier = None

try:
    from catboost import CatBoostClassifier
except Exception:  # pragma: no cover - optional dependency
    CatBoostClassifier = None


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"
DOCS_DIR = ROOT / "docs"
RANDOM_STATE = 42

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
warnings.filterwarnings("ignore", message="X does not have valid feature names.*")


def ensure_dirs() -> None:
    for path in [DATA_DIR, RESULTS_DIR, FIGURES_DIR, DOCS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def normalize_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.lower().str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip()


def zscore(series: pd.Series) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    sd = x.std(ddof=0)
    if pd.isna(sd) or sd == 0:
        return pd.Series(np.zeros(len(x)), index=x.index)
    return (x - x.mean()) / sd


def is_baseline_overall(cgm: pd.DataFrame) -> pd.Series:
    period = normalize_text(cgm["period_label"])
    time_window = normalize_text(cgm["time_window"])
    analysis = normalize_text(cgm["analysis_label"])
    treatment = normalize_text(cgm["treatment_context"])
    baseline = period.str.contains("baseline", na=False) | treatment.eq("baseline")
    overall = (
        time_window.str.contains("overall", na=False)
        | time_window.str.contains("24 hr", na=False)
        | analysis.eq("1 24hr")
    )
    return baseline & overall


def is_followup_overall(cgm: pd.DataFrame) -> pd.Series:
    period = normalize_text(cgm["period_label"])
    time_window = normalize_text(cgm["time_window"])
    analysis = normalize_text(cgm["analysis_label"])
    treatment = normalize_text(cgm["treatment_context"])
    followup = (
        period.str.contains("follow", na=False)
        | period.str.contains("post randomization", na=False)
        | period.str.contains("weeks 11 12", na=False)
        | treatment.isin(["hcl", "plgs", "sap"])
    )
    overall = (
        time_window.str.contains("overall", na=False)
        | time_window.str.contains("24 hr", na=False)
        | analysis.eq("1 24hr")
    )
    return followup & overall


def build_day_night_features(cgm: pd.DataFrame) -> pd.DataFrame:
    work = cgm.copy()
    period = normalize_text(work["period_label"])
    time_window = normalize_text(work["time_window"])
    analysis = normalize_text(work["analysis_label"])
    treatment = normalize_text(work["treatment_context"])

    baseline = period.str.contains("baseline", na=False) | treatment.eq("baseline")
    day = time_window.str.contains("daytime", na=False) | ((analysis.eq("2 day night")) & work["time_window"].astype(str).eq("1"))
    night = time_window.str.contains("nighttime", na=False) | ((analysis.eq("2 day night")) & work["time_window"].astype(str).eq("0"))
    work = work[baseline & (day | night)].copy()
    if work.empty:
        return pd.DataFrame(columns=["participant_id"])
    work["daypart"] = np.where(day.loc[work.index], "day", "night")
    keep = [
        "participant_id",
        "daypart",
        "cgm_mean_glucose_mg_dl",
        "cgm_time_in_range_70_180_pct",
        "cgm_time_below_70_pct",
    ]
    pivot = work[keep].pivot_table(index="participant_id", columns="daypart", aggfunc="mean")
    pivot.columns = [f"{metric}_{part}" for metric, part in pivot.columns]
    pivot = pivot.reset_index()
    for metric in ["cgm_mean_glucose_mg_dl", "cgm_time_in_range_70_180_pct", "cgm_time_below_70_pct"]:
        d = f"{metric}_day"
        n = f"{metric}_night"
        if d in pivot.columns and n in pivot.columns:
            pivot[f"circadian_absdiff_{metric}"] = (pivot[d] - pivot[n]).abs()
    return pivot


def label_phase(row: pd.Series, global_quantiles: dict[str, float]) -> str:
    if row["cgm_time_in_range_70_180_pct"] >= global_quantiles["tir_q70"] and row["cgm_cv_pct"] <= global_quantiles["cv_q50"]:
        return "稳定达标相"
    if row["cgm_time_below_70_pct"] >= global_quantiles["below70_q75"] or row["cgm_time_below_54_pct"] >= global_quantiles["below54_q75"]:
        return "低血糖易感相"
    if row["circadian_disruption_score"] >= global_quantiles["circadian_q75"]:
        return "昼夜节律紊乱相"
    if row["cgm_cv_pct"] >= global_quantiles["cv_q75"] or row["dynamic_instability_score"] >= global_quantiles["instability_q75"]:
        return "高波动震荡相"
    if row["glycemic_burden_score"] >= global_quantiles["burden_q60"] or row["cgm_time_above_180_pct"] >= global_quantiles["above180_q60"]:
        return "高血糖持续相"
    return "混合过渡相"


def build_phase_map(ml: pd.DataFrame, cgm: pd.DataFrame) -> pd.DataFrame:
    base = cgm[is_baseline_overall(cgm)].copy()
    base_metrics = [
        "cgm_mean_glucose_mg_dl",
        "cgm_time_in_range_70_180_pct",
        "cgm_time_below_70_pct",
        "cgm_time_below_54_pct",
        "cgm_time_above_180_pct",
        "cgm_time_above_250_pct",
        "cgm_hours",
        "cgm_cv_pct",
        "cgm_sd_mg_dl",
    ]
    phase = base.groupby(["participant_id", "study_id"], as_index=False)[base_metrics].mean()
    day_night = build_day_night_features(cgm)
    phase = phase.merge(day_night, on="participant_id", how="left")
    phase = phase.merge(
        ml[
            [
                "participant_id",
                "study_id",
                "x_age_years",
                "x_baseline_hba1c_pct",
                "x_baseline_bmi",
                "x_randomized_arm",
                "y_hba1c_improved_ge_0_5",
                "y_hba1c_change_pct_points",
                "y_tir_improved_ge_5pct",
                "y_change_cgm_time_in_range_70_180_pct",
            ]
        ],
        on=["participant_id", "study_id"],
        how="left",
    )
    for col in base_metrics:
        phase[col] = pd.to_numeric(phase[col], errors="coerce")

    # Order parameters inspired by coarse-grained phase diagrams.
    phase["glycemic_burden_score"] = (
        zscore(phase["cgm_mean_glucose_mg_dl"])
        + zscore(phase["cgm_time_above_180_pct"])
        + zscore(phase["cgm_time_above_250_pct"])
        - zscore(phase["cgm_time_in_range_70_180_pct"])
    ) / 4.0
    phase["hypoglycemic_susceptibility_score"] = (
        zscore(phase["cgm_time_below_70_pct"]) + zscore(phase["cgm_time_below_54_pct"])
    ) / 2.0
    phase["dynamic_instability_score"] = (
        zscore(phase["cgm_cv_pct"]) + zscore(phase["cgm_sd_mg_dl"].fillna(phase["cgm_cv_pct"]))
    ) / 2.0
    circ_cols = [
        "circadian_absdiff_cgm_mean_glucose_mg_dl",
        "circadian_absdiff_cgm_time_in_range_70_180_pct",
        "circadian_absdiff_cgm_time_below_70_pct",
    ]
    for col in circ_cols:
        if col not in phase.columns:
            phase[col] = np.nan
    phase["circadian_disruption_score"] = (
        zscore(phase["circadian_absdiff_cgm_mean_glucose_mg_dl"].fillna(0))
        + zscore(phase["circadian_absdiff_cgm_time_in_range_70_180_pct"].fillna(0))
        + zscore(phase["circadian_absdiff_cgm_time_below_70_pct"].fillna(0))
    ) / 3.0
    phase["resilience_proxy_score"] = (
        zscore(phase["cgm_time_above_250_pct"]) + zscore(phase["cgm_cv_pct"]) + zscore(phase["cgm_mean_glucose_mg_dl"])
    ) / 3.0

    order_cols = [
        "glycemic_burden_score",
        "hypoglycemic_susceptibility_score",
        "dynamic_instability_score",
        "circadian_disruption_score",
        "resilience_proxy_score",
    ]
    cluster_input = phase[order_cols].copy()
    cluster_input = cluster_input.fillna(cluster_input.median(numeric_only=True)).fillna(0)
    scaled = StandardScaler().fit_transform(cluster_input)
    kmeans = KMeans(n_clusters=5, random_state=RANDOM_STATE, n_init=50)
    phase["phase_cluster"] = kmeans.fit_predict(scaled)

    q = {
        "tir_q70": phase["cgm_time_in_range_70_180_pct"].quantile(0.70),
        "cv_q50": phase["cgm_cv_pct"].quantile(0.50),
        "below70_q75": phase["cgm_time_below_70_pct"].quantile(0.75),
        "below54_q75": phase["cgm_time_below_54_pct"].quantile(0.75),
        "circadian_q75": phase["circadian_disruption_score"].quantile(0.75),
        "cv_q75": phase["cgm_cv_pct"].quantile(0.75),
        "instability_q75": phase["dynamic_instability_score"].quantile(0.75),
        "burden_q60": phase["glycemic_burden_score"].quantile(0.60),
        "above180_q60": phase["cgm_time_above_180_pct"].quantile(0.60),
    }
    cluster_centers = phase.groupby("phase_cluster", as_index=False).median(numeric_only=True)
    cluster_centers["phase_label"] = cluster_centers.apply(lambda row: label_phase(row, q), axis=1)
    phase = phase.merge(cluster_centers[["phase_cluster", "phase_label"]], on="phase_cluster", how="left")
    return phase


def plot_phase_map(phase: pd.DataFrame) -> None:
    color_map = {
        "稳定达标相": "#2E7D32",
        "高血糖持续相": "#C62828",
        "高波动震荡相": "#6A1B9A",
        "低血糖易感相": "#1565C0",
        "昼夜节律紊乱相": "#EF6C00",
        "混合过渡相": "#546E7A",
    }
    plt.figure(figsize=(8, 6))
    for label, group in phase.groupby("phase_label"):
        plt.scatter(
            group["glycemic_burden_score"],
            group["dynamic_instability_score"],
            label=label,
            s=42,
            alpha=0.78,
            c=color_map.get(label, "#333333"),
            edgecolor="white",
            linewidth=0.4,
        )
    plt.axhline(0, color="#CCCCCC", lw=0.8)
    plt.axvline(0, color="#CCCCCC", lw=0.8)
    plt.xlabel("Glycemic burden score")
    plt.ylabel("Dynamic instability score")
    plt.title("Glycemic Phase Map")
    plt.legend(loc="best", fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "glycemic_phase_map.png", dpi=220)
    plt.close()

    plt.figure(figsize=(8, 5))
    order = phase["phase_label"].value_counts().index.tolist()
    data = [phase.loc[phase["phase_label"] == label, "cgm_time_in_range_70_180_pct"].dropna() for label in order]
    plt.boxplot(data, tick_labels=order, patch_artist=True)
    plt.xticks(rotation=25, ha="right")
    plt.ylabel("Baseline CGM TIR (%)")
    plt.title("Baseline TIR by Glycemic Phase")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "phase_tir_boxplot.png", dpi=220)
    plt.close()


def summarize_phase_outcomes(phase: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows = []
    for label, g in phase.groupby("phase_label"):
        summary_rows.append(
            {
                "phase_label": label,
                "n": len(g),
                "study_count": g["study_id"].nunique(),
                "baseline_tir_mean": g["cgm_time_in_range_70_180_pct"].mean(),
                "baseline_mean_glucose": g["cgm_mean_glucose_mg_dl"].mean(),
                "baseline_cv": g["cgm_cv_pct"].mean(),
                "hba1c_improvement_n": g["y_hba1c_improved_ge_0_5"].notna().sum(),
                "hba1c_improvement_rate": g["y_hba1c_improved_ge_0_5"].mean(),
                "hba1c_change_mean": g["y_hba1c_change_pct_points"].mean(),
                "tir_improvement_n": g["y_tir_improved_ge_5pct"].notna().sum(),
                "tir_improvement_rate": g["y_tir_improved_ge_5pct"].mean(),
                "tir_change_mean": g["y_change_cgm_time_in_range_70_180_pct"].mean(),
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values("n", ascending=False)

    tests = []
    for outcome, kind in [
        ("y_hba1c_improved_ge_0_5", "binary"),
        ("y_tir_improved_ge_5pct", "binary"),
        ("y_hba1c_change_pct_points", "continuous"),
        ("y_change_cgm_time_in_range_70_180_pct", "continuous"),
    ]:
        dat = phase[["phase_label", outcome]].dropna()
        if dat.empty or dat["phase_label"].nunique() < 2:
            continue
        if kind == "binary":
            table = pd.crosstab(dat["phase_label"], dat[outcome])
            if table.shape[1] == 2:
                chi2, p, dof, _ = stats.chi2_contingency(table)
                tests.append({"outcome": outcome, "test": "chi_square", "statistic": chi2, "p_value": p, "df": dof, "n": len(dat)})
        else:
            groups = [g[outcome].values for _, g in dat.groupby("phase_label") if len(g) >= 3]
            if len(groups) >= 2:
                stat, p = stats.kruskal(*groups)
                tests.append({"outcome": outcome, "test": "kruskal_wallis", "statistic": stat, "p_value": p, "df": len(groups) - 1, "n": len(dat)})
    return summary, pd.DataFrame(tests)


@dataclass
class FeatureSet:
    name: str
    numeric: list[str]
    categorical: list[str]


def get_feature_sets(ml_phase: pd.DataFrame) -> list[FeatureSet]:
    available = set(ml_phase.columns)
    def keep(cols: Iterable[str]) -> list[str]:
        return [col for col in cols if col in available]

    return [
        FeatureSet(
            "C1_clinical",
            keep(["x_age_years", "x_baseline_hba1c_pct", "x_baseline_bmi", "x_diabetes_duration_years"]),
            keep(["study_id", "x_randomized_arm", "x_sex", "x_race", "x_ethnicity"]),
        ),
        FeatureSet(
            "C2_clinical_plus_cgm",
            keep(
                [
                    "x_age_years",
                    "x_baseline_hba1c_pct",
                    "x_baseline_bmi",
                    "x_diabetes_duration_years",
                    "cgm_mean_glucose_mg_dl",
                    "cgm_time_in_range_70_180_pct",
                    "cgm_time_below_70_pct",
                    "cgm_time_below_54_pct",
                    "cgm_time_above_180_pct",
                    "cgm_time_above_250_pct",
                    "cgm_cv_pct",
                ]
            ),
            keep(["study_id", "x_randomized_arm", "x_sex", "x_race", "x_ethnicity"]),
        ),
        FeatureSet(
            "C4_phase_map",
            keep(
                [
                    "x_age_years",
                    "x_baseline_hba1c_pct",
                    "x_baseline_bmi",
                    "x_diabetes_duration_years",
                    "cgm_mean_glucose_mg_dl",
                    "cgm_time_in_range_70_180_pct",
                    "cgm_time_below_70_pct",
                    "cgm_time_below_54_pct",
                    "cgm_time_above_180_pct",
                    "cgm_time_above_250_pct",
                    "cgm_cv_pct",
                    "glycemic_burden_score",
                    "hypoglycemic_susceptibility_score",
                    "dynamic_instability_score",
                    "circadian_disruption_score",
                    "resilience_proxy_score",
                ]
            ),
            keep(["study_id", "x_randomized_arm", "x_sex", "x_race", "x_ethnicity", "phase_label"]),
        ),
    ]


def make_preprocessor(feature_set: FeatureSet) -> ColumnTransformer:
    numeric_pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        [
            ("num", numeric_pipe, feature_set.numeric),
            ("cat", categorical_pipe, feature_set.categorical),
        ],
        remainder="drop",
        sparse_threshold=0.0,
    )


def get_models() -> dict[str, object]:
    models = {
        "dummy_majority": DummyClassifier(strategy="most_frequent"),
        "logistic_ridge": LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs"),
        "random_forest": RandomForestClassifier(
            n_estimators=220, min_samples_leaf=4, class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=220, min_samples_leaf=3, class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(max_iter=180, learning_rate=0.04, random_state=RANDOM_STATE),
        "svm_rbf": SVC(C=1.0, gamma="scale", class_weight="balanced", probability=True, random_state=RANDOM_STATE),
        "knn": KNeighborsClassifier(n_neighbors=15, weights="distance"),
        "mlp": MLPClassifier(
            hidden_layer_sizes=(48, 16),
            activation="relu",
            alpha=0.01,
            learning_rate_init=0.002,
            max_iter=450,
            early_stopping=True,
            random_state=RANDOM_STATE,
        ),
    }
    if XGBClassifier is not None:
        models["xgboost"] = XGBClassifier(
            n_estimators=260,
            max_depth=3,
            learning_rate=0.035,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_lambda=2.0,
            min_child_weight=3,
            eval_metric="logloss",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
    if LGBMClassifier is not None:
        models["lightgbm"] = LGBMClassifier(
            n_estimators=260,
            max_depth=3,
            learning_rate=0.035,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_lambda=2.0,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
            verbose=-1,
        )
    if CatBoostClassifier is not None:
        models["catboost"] = CatBoostClassifier(
            iterations=260,
            depth=3,
            learning_rate=0.035,
            l2_leaf_reg=4.0,
            loss_function="Logloss",
            eval_metric="AUC",
            random_seed=RANDOM_STATE,
            verbose=False,
            allow_writing_files=False,
            thread_count=-1,
        )
    return models


def model_predict_proba(model: Pipeline, x: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(x)
        if proba.shape[1] == 1:
            return np.zeros(len(x))
        return proba[:, 1]
    if hasattr(model, "decision_function"):
        score = model.decision_function(x)
        return 1.0 / (1.0 + np.exp(-score))
    pred = model.predict(x)
    return pred.astype(float)


def metric_row(y_true: np.ndarray, y_prob: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    row = {
        "n": len(y_true),
        "positive_rate": float(np.mean(y_true)),
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "brier": brier_score_loss(y_true, np.clip(y_prob, 0, 1)),
    }
    if len(np.unique(y_true)) == 2:
        row["auroc"] = roc_auc_score(y_true, y_prob)
        row["auprc"] = average_precision_score(y_true, y_prob)
    else:
        row["auroc"] = np.nan
        row["auprc"] = np.nan
    return row


def run_cv_benchmark(ml_phase: pd.DataFrame, target: str, feature_sets: list[FeatureSet]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    loso_rows = []
    models = get_models()
    data = ml_phase.dropna(subset=[target]).copy()
    data[target] = data[target].astype(int)
    if target == "y_tir_improved_ge_5pct":
        data = data[data["phase_label"].notna()].copy()
    for fs in feature_sets:
        if not fs.numeric and not fs.categorical:
            continue
        feature_cols = fs.numeric + fs.categorical
        for model_name, model in models.items():
            fold_probs = np.full(len(data), np.nan)
            fold_preds = np.full(len(data), np.nan)
            skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
            for fold, (train_idx, test_idx) in enumerate(skf.split(data[feature_cols], data[target]), start=1):
                pipe = Pipeline([("prep", make_preprocessor(fs)), ("model", clone(model))])
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    pipe.fit(data.iloc[train_idx][feature_cols], data.iloc[train_idx][target])
                prob = model_predict_proba(pipe, data.iloc[test_idx][feature_cols])
                pred = (prob >= 0.5).astype(int)
                fold_probs[test_idx] = prob
                fold_preds[test_idx] = pred
            metrics = metric_row(data[target].values, fold_probs, fold_preds.astype(int))
            rows.append({"target": target, "feature_set": fs.name, "model": model_name, "validation": "5fold_cv", **metrics})

            for held_out, test in data.groupby("study_id"):
                train = data[data["study_id"] != held_out]
                if train[target].nunique() < 2 or test[target].nunique() < 2 or len(test) < 20:
                    continue
                pipe = Pipeline([("prep", make_preprocessor(fs)), ("model", clone(model))])
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    pipe.fit(train[feature_cols], train[target])
                prob = model_predict_proba(pipe, test[feature_cols])
                pred = (prob >= 0.5).astype(int)
                metrics = metric_row(test[target].values, prob, pred)
                loso_rows.append(
                    {
                        "target": target,
                        "feature_set": fs.name,
                        "model": model_name,
                        "held_out_study": held_out,
                        "validation": "leave_one_study_out",
                        **metrics,
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(loso_rows)


def plot_model_performance(perf: pd.DataFrame) -> None:
    primary = perf[perf["target"].eq("y_hba1c_improved_ge_0_5")].copy()
    primary = primary.sort_values("auroc", ascending=False).head(18)
    if primary.empty:
        return
    labels = primary["feature_set"] + " / " + primary["model"]
    plt.figure(figsize=(9, 6))
    plt.barh(labels[::-1], primary["auroc"][::-1], color="#386CB0")
    plt.xlabel("5-fold CV AUROC")
    plt.title("Primary Task Model Benchmark")
    plt.xlim(0.45, max(0.9, float(primary["auroc"].max()) + 0.03))
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "model_benchmark_primary_auroc.png", dpi=220)
    plt.close()


def hte_by_phase(ml_phase: pd.DataFrame) -> pd.DataFrame:
    rows = []
    control_map = {
        "WISDM": "bgm",
        "CITY": "bgm",
        "SENCE": "bgm",
        "DCLP3": "sap",
    }
    data = ml_phase.dropna(subset=["phase_label", "y_hba1c_improved_ge_0_5", "x_randomized_arm"]).copy()
    for study, control in control_map.items():
        sdat = data[data["study_id"].eq(study)].copy()
        if sdat.empty:
            continue
        for phase, pdat in sdat.groupby("phase_label"):
            control_dat = pdat[pdat["x_randomized_arm"].eq(control)]
            for arm, adat in pdat.groupby("x_randomized_arm"):
                if arm == control:
                    continue
                if len(control_dat) < 5 or len(adat) < 5:
                    continue
                rate_c = control_dat["y_hba1c_improved_ge_0_5"].mean()
                rate_t = adat["y_hba1c_improved_ge_0_5"].mean()
                change_c = control_dat["y_hba1c_change_pct_points"].mean()
                change_t = adat["y_hba1c_change_pct_points"].mean()
                rows.append(
                    {
                        "study_id": study,
                        "phase_label": phase,
                        "control_arm": control,
                        "treatment_arm": arm,
                        "n_control": len(control_dat),
                        "n_treatment": len(adat),
                        "response_rate_control": rate_c,
                        "response_rate_treatment": rate_t,
                        "risk_difference_treatment_minus_control": rate_t - rate_c,
                        "hba1c_change_control_mean": change_c,
                        "hba1c_change_treatment_mean": change_t,
                        "hba1c_change_difference_treatment_minus_control": change_t - change_c,
                    }
                )
    return pd.DataFrame(rows)


def phase_recommendation(label: str) -> str:
    mapping = {
        "稳定达标相": "维持当前方案，避免过度强化；重点监测低血糖和生活方式稳定性。",
        "高血糖持续相": "优先考虑治疗强化、胰岛素/药物优化、饮食结构复盘，并密切跟踪 TIR 和 TAR。",
        "高波动震荡相": "优先降低波动：CGM 警报、胰岛素时机、餐后响应和 AID/闭环策略可能更有价值。",
        "低血糖易感相": "优先降低低血糖风险：夜间报警、目标范围调整、基础胰岛素/闭环参数审查。",
        "昼夜节律紊乱相": "重点评估夜间基础率、睡眠、晚餐/宵夜、运动时间和昼夜节律相关行为。",
        "混合过渡相": "建议结合 HbA1c、TIR 和低血糖指标进行个体化复评，避免单一指标决策。",
    }
    return mapping.get(label, "相位未定义，建议补充基线 CGM 后再做个体化判断。")


def build_individualized_framework(ml_phase: pd.DataFrame, perf: pd.DataFrame) -> pd.DataFrame:
    data = ml_phase.copy()
    target = "y_hba1c_improved_ge_0_5"
    feature_sets = get_feature_sets(data)
    c4 = [fs for fs in feature_sets if fs.name == "C4_phase_map"][0]
    best_rows = perf[(perf["target"].eq(target)) & (perf["feature_set"].eq("C4_phase_map"))].sort_values("auroc", ascending=False)
    best_model_name = best_rows.iloc[0]["model"] if not best_rows.empty else "logistic_ridge"
    model = get_models().get(best_model_name, get_models()["logistic_ridge"])
    train = data.dropna(subset=[target]).copy()
    feature_cols = c4.numeric + c4.categorical
    pipe = Pipeline([("prep", make_preprocessor(c4)), ("model", clone(model))])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipe.fit(train[feature_cols], train[target].astype(int))
    data["predicted_hba1c_improvement_probability_research_model"] = model_predict_proba(pipe, data[feature_cols])
    out_cols = [
        "participant_id",
        "study_id",
        "x_randomized_arm",
        "phase_label",
        "glycemic_burden_score",
        "hypoglycemic_susceptibility_score",
        "dynamic_instability_score",
        "circadian_disruption_score",
        "resilience_proxy_score",
        "predicted_hba1c_improvement_probability_research_model",
    ]
    out = data[out_cols].copy()
    out["phase_based_intervention_focus"] = out["phase_label"].map(phase_recommendation)
    out["model_caveat"] = "研究用回顾性模型分数；不能作为临床决策工具，需前瞻性验证。"
    return out.sort_values(["study_id", "participant_id"])


def markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "_无可用结果。_"
    work = df.head(max_rows).copy()
    for col in work.columns:
        if pd.api.types.is_float_dtype(work[col]):
            work[col] = work[col].map(lambda x: "" if pd.isna(x) else f"{x:.3f}")
        else:
            work[col] = work[col].map(lambda x: "" if pd.isna(x) else str(x))
    headers = list(work.columns)
    rows = work.values.tolist()
    widths = [len(h) for h in headers]
    for row in rows:
        widths = [max(w, len(str(v))) for w, v in zip(widths, row)]
    lines = [
        "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |",
        "| " + " | ".join("-" * w for w in widths) + " |",
    ]
    lines.extend("| " + " | ".join(str(v).ljust(w) for v, w in zip(row, widths)) + " |" for row in rows)
    return "\n".join(lines)


def write_report(
    phase: pd.DataFrame,
    phase_summary: pd.DataFrame,
    tests: pd.DataFrame,
    perf: pd.DataFrame,
    loso: pd.DataFrame,
    hte: pd.DataFrame,
    framework: pd.DataFrame,
) -> None:
    best_primary = perf[perf["target"].eq("y_hba1c_improved_ge_0_5")].sort_values("auroc", ascending=False).head(10)
    best_tir = perf[perf["target"].eq("y_tir_improved_ge_5pct")].sort_values("auroc", ascending=False).head(10)
    loso_summary = (
        loso.groupby(["target", "feature_set", "model"], as_index=False)
        .agg(mean_auroc=("auroc", "mean"), mean_auprc=("auprc", "mean"), mean_brier=("brier", "mean"), studies=("held_out_study", "nunique"))
        .sort_values(["target", "mean_auroc"], ascending=[True, False])
        if not loso.empty
        else pd.DataFrame()
    )
    report = f"""# 血糖动力学相图研究分析报告

生成脚本：`scripts/run_glycemic_phase_research.py`  
数据：`processed_ml_table.csv` 与 `cgm_summary_long.csv`

## 完成情况

本轮已完成五个目标的第一版可复现分析：

1. **构建血糖动力学相图**：基于 {len(phase)} 名有基线 CGM 汇总的受试者，构建高血糖负担、低血糖易感性、动态不稳定性、恢复力代理指标和昼夜节律紊乱 5 个粗粒化序参量，并用聚类得到血糖相位。
2. **验证相位与临床结局关系**：输出相位별 HbA1c 改善、TIR 改善和连续变化摘要，并进行卡方/Kruskal-Wallis 检验。
3. **比较不同机器学习方法预测能力**：比较 Dummy、Logistic、RandomForest、ExtraTrees、HistGradientBoosting、SVM、KNN、MLP 在临床特征、CGM 特征、相图特征三类特征集上的表现。
4. **识别异质性治疗响应**：在 WISDM、CITY、SENCE、DCLP3 等具备相位标签和可比较治疗臂的 RCT 内，估计相位分层治疗响应差异。
5. **形成可解释个体化干预框架**：为每位有相位标签的受试者输出相位、关键序参量、研究用预测概率和相位导向干预重点。

## 目标 1：血糖动力学相图

相位分布：

{markdown_table(phase["phase_label"].value_counts().rename_axis("phase_label").reset_index(name="n"))}

核心图：

- `figures/glycemic_phase_map.png`
- `figures/phase_tir_boxplot.png`

## 目标 2：相位与临床结局

相位结局摘要：

{markdown_table(phase_summary)}

关联检验：

{markdown_table(tests)}

## 目标 3：机器学习预测能力比较

HbA1c 改善主任务前 10 名：

{markdown_table(best_primary)}

TIR 改善任务前 10 名：

{markdown_table(best_tir)}

Leave-one-study-out 摘要：

{markdown_table(loso_summary, max_rows=20)}

核心图：

- `figures/model_benchmark_primary_auroc.png`

说明：当前环境已安装并运行 scikit-learn 模型。XGBoost、LightGBM、CatBoost、TabPFN、深度时间序列基础模型尚未在本轮脚本中运行，可作为下一步增强模型接入同一 pipeline。

## 目标 4：异质性治疗响应

相位分层治疗响应估计：

{markdown_table(hte, max_rows=25)}

解释限制：这些估计是 RCT 内相位分层的描述性/探索性治疗效应差异。由于相位子组样本量有限，不能等同于已验证的临床治疗规则。

## 目标 5：个体化干预框架

已输出：

- `results/individualized_intervention_framework.csv`

该表包含相位标签、相位序参量、研究用预测概率和相位导向干预重点。该框架用于科研解释和后续模型开发，不能直接作为临床决策工具。

## 主要产物

- `data/processed/glycemic_phase_features.csv`
- `data/processed/glycemic_phase_labels.csv`
- `results/phase_outcome_summary.csv`
- `results/phase_association_tests.csv`
- `results/model_performance_cv.csv`
- `results/model_performance_loso.csv`
- `results/hte_by_phase.csv`
- `results/individualized_intervention_framework.csv`
- `figures/glycemic_phase_map.png`
- `figures/phase_tir_boxplot.png`
- `figures/model_benchmark_primary_auroc.png`

## 下一步建议

1. 将 PEDAP、IOBP2、DCLP5、CLVer 等原始 device/CGM 明细聚合为日级和事件级动力学特征。
2. 接入 XGBoost、LightGBM、CatBoost、TabPFN 和时间序列基础模型。
3. 对相位标签做 bootstrap 稳定性和 leave-one-study-out 相位重建。
4. 对 HTE 使用 causal forest / doubly robust learner，并在单个 RCT 内独立报告。
5. 将本报告转化为论文结果章节和图表草稿。
"""
    (DOCS_DIR / "glycemic_phase_research_report_zh.md").write_text(report, encoding="utf-8")


def main() -> int:
    ensure_dirs()
    ml = pd.read_csv(DATA_DIR / "processed_ml_table.csv")
    cgm = pd.read_csv(DATA_DIR / "cgm_summary_long.csv")

    phase = build_phase_map(ml, cgm)
    plot_phase_map(phase)
    phase_summary, tests = summarize_phase_outcomes(phase)

    phase_features_cols = [
        "participant_id",
        "study_id",
        "phase_cluster",
        "phase_label",
        "glycemic_burden_score",
        "hypoglycemic_susceptibility_score",
        "dynamic_instability_score",
        "circadian_disruption_score",
        "resilience_proxy_score",
        "cgm_mean_glucose_mg_dl",
        "cgm_time_in_range_70_180_pct",
        "cgm_time_below_70_pct",
        "cgm_time_below_54_pct",
        "cgm_time_above_180_pct",
        "cgm_time_above_250_pct",
        "cgm_cv_pct",
        "cgm_hours",
    ]
    phase[phase_features_cols].to_csv(DATA_DIR / "glycemic_phase_features.csv", index=False)
    phase[["participant_id", "study_id", "phase_cluster", "phase_label"]].to_csv(DATA_DIR / "glycemic_phase_labels.csv", index=False)
    phase_summary.to_csv(RESULTS_DIR / "phase_outcome_summary.csv", index=False)
    tests.to_csv(RESULTS_DIR / "phase_association_tests.csv", index=False)

    ml_phase = ml.merge(
        phase[
            [
                "participant_id",
                "phase_cluster",
                "phase_label",
                "glycemic_burden_score",
                "hypoglycemic_susceptibility_score",
                "dynamic_instability_score",
                "circadian_disruption_score",
                "resilience_proxy_score",
                "cgm_mean_glucose_mg_dl",
                "cgm_time_in_range_70_180_pct",
                "cgm_time_below_70_pct",
                "cgm_time_below_54_pct",
                "cgm_time_above_180_pct",
                "cgm_time_above_250_pct",
                "cgm_cv_pct",
            ]
        ],
        on="participant_id",
        how="left",
    )
    feature_sets = get_feature_sets(ml_phase)
    perf_frames = []
    loso_frames = []
    for target in ["y_hba1c_improved_ge_0_5", "y_tir_improved_ge_5pct"]:
        perf, loso = run_cv_benchmark(ml_phase, target, feature_sets)
        perf_frames.append(perf)
        loso_frames.append(loso)
    perf_all = pd.concat(perf_frames, ignore_index=True)
    loso_all = pd.concat(loso_frames, ignore_index=True)
    perf_all.to_csv(RESULTS_DIR / "model_performance_cv.csv", index=False)
    loso_all.to_csv(RESULTS_DIR / "model_performance_loso.csv", index=False)
    plot_model_performance(perf_all)

    hte = hte_by_phase(ml_phase)
    hte.to_csv(RESULTS_DIR / "hte_by_phase.csv", index=False)
    framework = build_individualized_framework(ml_phase, perf_all)
    framework.to_csv(RESULTS_DIR / "individualized_intervention_framework.csv", index=False)

    write_report(phase, phase_summary, tests, perf_all, loso_all, hte, framework)
    print(json.dumps(
        {
            "phase_rows": int(len(phase)),
            "phase_count": int(phase["phase_label"].nunique()),
            "model_rows": int(len(perf_all)),
            "loso_rows": int(len(loso_all)),
            "hte_rows": int(len(hte)),
            "framework_rows": int(len(framework)),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
