"""Run journal-grade secondary analyses for the glycemic phase-map study.

The primary script builds the phase map and compares predictive models. This
script adds reviewer-facing diagnostics:

    results/journal_oof_predictions.csv
    results/journal_calibration_metrics.csv
    results/journal_calibration_bins.csv
    results/journal_decision_curve.csv
    results/journal_permutation_importance.csv
    results/phase_bootstrap_stability.csv
    results/journal_adjusted_hte_by_phase.csv
    docs/journal_grade_experiment_report_zh.md
    figures/journal_*.png
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.base import clone
from sklearn.cluster import KMeans
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    adjusted_rand_score,
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
    silhouette_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

import run_glycemic_phase_research as primary

try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
except Exception:  # pragma: no cover - optional dependency
    sm = None
    smf = None


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"
DOCS_DIR = ROOT / "docs"
RANDOM_STATE = 42

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

warnings.filterwarnings("ignore", message="X does not have valid feature names.*")
warnings.filterwarnings("ignore", category=UserWarning, module="lightgbm")


def ensure_dirs() -> None:
    for path in [RESULTS_DIR, FIGURES_DIR, DOCS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "_No rows._"
    show = df.head(max_rows).copy()
    for col in show.columns:
        if pd.api.types.is_float_dtype(show[col]):
            show[col] = show[col].map(lambda x: "" if pd.isna(x) else f"{x:.3f}")
    headers = list(show.columns)
    rows = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in show.iterrows():
        rows.append("| " + " | ".join(str(row[col]) for col in headers) + " |")
    return "\n".join(rows)


def make_ml_phase() -> pd.DataFrame:
    ml = pd.read_csv(DATA_DIR / "processed_ml_table.csv")
    phase = pd.read_csv(DATA_DIR / "glycemic_phase_features.csv")
    merge_cols = [
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
    return ml.merge(phase[merge_cols], on="participant_id", how="left")


def select_experiments(perf: pd.DataFrame) -> pd.DataFrame:
    rows = []
    scored = perf[perf["model"].ne("dummy_majority")].dropna(subset=["auroc"]).copy()
    for target, group in scored.groupby("target"):
        top = group.sort_values("auroc", ascending=False).head(4)
        rows.append(top)
        c4 = group[group["feature_set"].eq("C4_phase_map")].sort_values("auroc", ascending=False).head(1)
        if not c4.empty:
            rows.append(c4)
    selected = pd.concat(rows, ignore_index=True)
    selected = selected.drop_duplicates(subset=["target", "feature_set", "model"]).reset_index(drop=True)
    return selected[["target", "feature_set", "model", "auroc", "auprc", "brier", "n"]]


def target_data(ml_phase: pd.DataFrame, target: str) -> pd.DataFrame:
    data = ml_phase.dropna(subset=[target]).copy()
    if target == "y_tir_improved_ge_5pct":
        data = data[data["phase_label"].notna()].copy()
    data[target] = data[target].astype(int)
    return data


def fit_pipeline(feature_set: primary.FeatureSet, model_name: str) -> Pipeline:
    model = primary.get_models()[model_name]
    return Pipeline([("prep", primary.make_preprocessor(feature_set)), ("model", clone(model))])


def run_oof_predictions(ml_phase: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    feature_sets = {fs.name: fs for fs in primary.get_feature_sets(ml_phase)}
    rows = []
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    for _, exp in selected.iterrows():
        target = exp["target"]
        data = target_data(ml_phase, target).reset_index(drop=True)
        fs = feature_sets[exp["feature_set"]]
        feature_cols = fs.numeric + fs.categorical
        for fold, (train_idx, test_idx) in enumerate(skf.split(data[feature_cols], data[target]), start=1):
            pipe = fit_pipeline(fs, exp["model"])
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pipe.fit(data.iloc[train_idx][feature_cols], data.iloc[train_idx][target])
                prob = primary.model_predict_proba(pipe, data.iloc[test_idx][feature_cols])
            for original_index, y_true, y_prob in zip(test_idx, data.iloc[test_idx][target].to_numpy(), prob):
                rows.append(
                    {
                        "participant_id": data.iloc[original_index]["participant_id"],
                        "study_id": data.iloc[original_index]["study_id"],
                        "target": target,
                        "feature_set": exp["feature_set"],
                        "model": exp["model"],
                        "fold": fold,
                        "y_true": int(y_true),
                        "y_prob": float(np.clip(y_prob, 0, 1)),
                    }
                )
    return pd.DataFrame(rows)


def calibration_intercept_slope(y: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    if sm is None or len(np.unique(y)) < 2:
        return np.nan, np.nan
    eps = 1e-6
    logits = np.log(np.clip(p, eps, 1 - eps) / np.clip(1 - p, eps, 1 - eps))
    x = sm.add_constant(logits)
    try:
        model = sm.Logit(y, x).fit(disp=False, maxiter=200)
        return float(model.params[0]), float(model.params[1])
    except Exception:
        return np.nan, np.nan


def expected_calibration_error(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> tuple[float, pd.DataFrame]:
    bins = np.linspace(0, 1, n_bins + 1)
    idx = np.digitize(p, bins[1:-1], right=True)
    rows = []
    ece = 0.0
    for b in range(n_bins):
        mask = idx == b
        if not np.any(mask):
            continue
        n = int(mask.sum())
        observed = float(np.mean(y[mask]))
        predicted = float(np.mean(p[mask]))
        ece += n / len(y) * abs(observed - predicted)
        rows.append(
            {
                "bin": b + 1,
                "bin_low": bins[b],
                "bin_high": bins[b + 1],
                "n": n,
                "observed_rate": observed,
                "mean_predicted_probability": predicted,
            }
        )
    return float(ece), pd.DataFrame(rows)


def summarize_calibration(oof: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    metric_rows = []
    bin_frames = []
    for keys, group in oof.groupby(["target", "feature_set", "model"]):
        y = group["y_true"].to_numpy()
        p = group["y_prob"].to_numpy()
        intercept, slope = calibration_intercept_slope(y, p)
        ece, bins = expected_calibration_error(y, p)
        target, feature_set, model = keys
        row = {
            "target": target,
            "feature_set": feature_set,
            "model": model,
            "n": len(group),
            "positive_rate": float(np.mean(y)),
            "auroc": roc_auc_score(y, p) if len(np.unique(y)) == 2 else np.nan,
            "auprc": average_precision_score(y, p) if len(np.unique(y)) == 2 else np.nan,
            "brier": brier_score_loss(y, p),
            "calibration_intercept": intercept,
            "calibration_slope": slope,
            "expected_calibration_error": ece,
        }
        metric_rows.append(row)
        if not bins.empty:
            bins.insert(0, "model", model)
            bins.insert(0, "feature_set", feature_set)
            bins.insert(0, "target", target)
            bin_frames.append(bins)
    metrics = pd.DataFrame(metric_rows).sort_values(["target", "auroc"], ascending=[True, False])
    bin_table = pd.concat(bin_frames, ignore_index=True) if bin_frames else pd.DataFrame()
    return metrics, bin_table


def plot_calibration(metrics: pd.DataFrame, bins: pd.DataFrame) -> None:
    if bins.empty:
        return
    targets = metrics["target"].unique().tolist()
    fig, axes = plt.subplots(1, len(targets), figsize=(7 * len(targets), 5), squeeze=False)
    for ax, target in zip(axes.ravel(), targets):
        best = metrics[metrics["target"].eq(target)].sort_values("auroc", ascending=False).head(3)
        for _, row in best.iterrows():
            g = bins[
                bins["target"].eq(row["target"])
                & bins["feature_set"].eq(row["feature_set"])
                & bins["model"].eq(row["model"])
            ]
            label = f"{row['feature_set']} / {row['model']}"
            ax.plot(g["mean_predicted_probability"], g["observed_rate"], marker="o", label=label)
        ax.plot([0, 1], [0, 1], color="black", linestyle="--", linewidth=1)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Mean predicted probability")
        ax.set_ylabel("Observed event rate")
        ax.set_title(target)
        ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "journal_calibration_curves.png", dpi=220)
    plt.close()


def decision_curve(oof: pd.DataFrame, metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    thresholds = np.round(np.arange(0.05, 0.81, 0.01), 2)
    for target, target_metrics in metrics.groupby("target"):
        best = target_metrics.sort_values("auroc", ascending=False).head(1).iloc[0]
        group = oof[
            oof["target"].eq(target)
            & oof["feature_set"].eq(best["feature_set"])
            & oof["model"].eq(best["model"])
        ]
        y = group["y_true"].to_numpy()
        p = group["y_prob"].to_numpy()
        prevalence = float(np.mean(y))
        for threshold in thresholds:
            pred = p >= threshold
            tp = float(np.sum(pred & (y == 1)))
            fp = float(np.sum(pred & (y == 0)))
            n = len(y)
            model_nb = tp / n - fp / n * threshold / (1 - threshold)
            all_nb = prevalence - (1 - prevalence) * threshold / (1 - threshold)
            rows.extend(
                [
                    {
                        "target": target,
                        "feature_set": best["feature_set"],
                        "model": best["model"],
                        "strategy": "model",
                        "threshold": threshold,
                        "net_benefit": model_nb,
                    },
                    {
                        "target": target,
                        "feature_set": best["feature_set"],
                        "model": best["model"],
                        "strategy": "treat_all",
                        "threshold": threshold,
                        "net_benefit": all_nb,
                    },
                    {
                        "target": target,
                        "feature_set": best["feature_set"],
                        "model": best["model"],
                        "strategy": "treat_none",
                        "threshold": threshold,
                        "net_benefit": 0.0,
                    },
                ]
            )
    return pd.DataFrame(rows)


def plot_decision_curve(dca: pd.DataFrame) -> None:
    if dca.empty:
        return
    targets = dca["target"].unique().tolist()
    fig, axes = plt.subplots(1, len(targets), figsize=(7 * len(targets), 5), squeeze=False)
    for ax, target in zip(axes.ravel(), targets):
        for strategy, group in dca[dca["target"].eq(target)].groupby("strategy"):
            style = "-" if strategy == "model" else "--"
            ax.plot(group["threshold"], group["net_benefit"], linestyle=style, label=strategy)
        ax.set_xlabel("Decision threshold")
        ax.set_ylabel("Net benefit")
        ax.set_title(target)
        ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "journal_decision_curve.png", dpi=220)
    plt.close()


def run_permutation_importance(ml_phase: pd.DataFrame, metrics: pd.DataFrame) -> pd.DataFrame:
    feature_sets = {fs.name: fs for fs in primary.get_feature_sets(ml_phase)}
    rows = []
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    for target, target_metrics in metrics.groupby("target"):
        best = target_metrics.sort_values("auroc", ascending=False).head(1).iloc[0]
        data = target_data(ml_phase, target).reset_index(drop=True)
        fs = feature_sets[best["feature_set"]]
        feature_cols = fs.numeric + fs.categorical
        for fold, (train_idx, test_idx) in enumerate(skf.split(data[feature_cols], data[target]), start=1):
            pipe = fit_pipeline(fs, best["model"])
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pipe.fit(data.iloc[train_idx][feature_cols], data.iloc[train_idx][target])
                result = permutation_importance(
                    pipe,
                    data.iloc[test_idx][feature_cols],
                    data.iloc[test_idx][target],
                    scoring="roc_auc",
                    n_repeats=5,
                    random_state=RANDOM_STATE + fold,
                    n_jobs=-1,
                )
            for feature, mean, sd in zip(feature_cols, result.importances_mean, result.importances_std):
                rows.append(
                    {
                        "target": target,
                        "feature_set": best["feature_set"],
                        "model": best["model"],
                        "fold": fold,
                        "feature": feature,
                        "importance_mean": float(mean),
                        "importance_sd": float(sd),
                    }
                )
    raw = pd.DataFrame(rows)
    if raw.empty:
        return raw
    agg = (
        raw.groupby(["target", "feature_set", "model", "feature"], as_index=False)
        .agg(importance_mean=("importance_mean", "mean"), importance_sd=("importance_mean", "std"))
        .sort_values(["target", "importance_mean"], ascending=[True, False])
    )
    return agg


def plot_permutation_importance(importance: pd.DataFrame) -> None:
    if importance.empty:
        return
    targets = importance["target"].unique().tolist()
    fig, axes = plt.subplots(1, len(targets), figsize=(7 * len(targets), 6), squeeze=False)
    for ax, target in zip(axes.ravel(), targets):
        top = importance[importance["target"].eq(target)].sort_values("importance_mean", ascending=False).head(12)
        ax.barh(top["feature"][::-1], top["importance_mean"][::-1], color="#3f6f8f")
        ax.set_xlabel("Permutation drop in AUROC")
        ax.set_title(target)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "journal_permutation_importance.png", dpi=220)
    plt.close()


def phase_bootstrap_stability(n_boot: int = 150) -> pd.DataFrame:
    phase = pd.read_csv(DATA_DIR / "glycemic_phase_features.csv")
    order_cols = [
        "glycemic_burden_score",
        "hypoglycemic_susceptibility_score",
        "dynamic_instability_score",
        "circadian_disruption_score",
        "resilience_proxy_score",
    ]
    x = phase[order_cols].copy()
    original = phase["phase_cluster"].to_numpy()
    rng = np.random.default_rng(RANDOM_STATE)
    rows = []
    for b in range(1, n_boot + 1):
        idx = rng.integers(0, len(x), len(x))
        imputer = SimpleImputer(strategy="median")
        scaler = StandardScaler()
        x_sample = imputer.fit_transform(x.iloc[idx])
        x_sample = scaler.fit_transform(x_sample)
        x_all = scaler.transform(imputer.transform(x))
        km = KMeans(n_clusters=len(np.unique(original)), n_init=20, random_state=RANDOM_STATE + b)
        km.fit(x_sample)
        predicted = km.predict(x_all)
        ari = adjusted_rand_score(original, predicted)
        sil = silhouette_score(x_all, predicted) if len(np.unique(predicted)) > 1 else np.nan
        rows.append({"bootstrap": b, "adjusted_rand_index": ari, "silhouette": sil})
    return pd.DataFrame(rows)


def plot_phase_bootstrap(stability: pd.DataFrame) -> None:
    if stability.empty:
        return
    plt.figure(figsize=(7, 5))
    plt.hist(stability["adjusted_rand_index"], bins=22, color="#6a8f3f", edgecolor="white")
    plt.axvline(stability["adjusted_rand_index"].median(), color="black", linestyle="--", linewidth=1)
    plt.xlabel("Adjusted Rand Index vs original phase labels")
    plt.ylabel("Bootstrap count")
    plt.title("Phase Map Bootstrap Stability")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "phase_bootstrap_stability.png", dpi=220)
    plt.close()


def make_hte_design(frame: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    numeric_cols = [
        "treatment_binary",
        "x_baseline_hba1c_pct_model",
        "x_age_years_model",
        "x_baseline_cgm_time_in_range_70_180_pct_model",
    ]
    phase = pd.get_dummies(frame["phase_label"], prefix="phase", dtype=float)
    study = pd.get_dummies(frame["study_id"], prefix="study", dtype=float)
    x = pd.concat([frame[numeric_cols].astype(float).reset_index(drop=True), phase.reset_index(drop=True), study.reset_index(drop=True)], axis=1)
    treatment = frame["treatment_binary"].astype(float).reset_index(drop=True)
    for col in phase.columns:
        x[f"treat_x_{col}"] = treatment * phase.reset_index(drop=True)[col]
    if columns is not None:
        x = x.reindex(columns=columns, fill_value=0.0)
    return x.astype(float)


def adjusted_hte_by_phase(ml_phase: pd.DataFrame, n_boot: int = 200) -> pd.DataFrame:
    control_map = {"WISDM": "bgm", "CITY": "bgm", "SENCE": "bgm", "DCLP3": "sap"}
    dat = ml_phase[
        ml_phase["study_id"].isin(control_map.keys())
        & ml_phase["phase_label"].notna()
        & ml_phase["x_randomized_arm"].notna()
        & ml_phase["y_hba1c_improved_ge_0_5"].notna()
    ].copy()
    dat["control_arm"] = dat["study_id"].map(control_map)
    dat["treatment_binary"] = (dat["x_randomized_arm"] != dat["control_arm"]).astype(int)
    dat["outcome"] = dat["y_hba1c_improved_ge_0_5"].astype(int)
    for col in ["x_baseline_hba1c_pct", "x_age_years", "x_baseline_cgm_time_in_range_70_180_pct"]:
        dat[f"{col}_model"] = pd.to_numeric(dat[col], errors="coerce")
        dat[f"{col}_model"] = dat[f"{col}_model"].fillna(dat[f"{col}_model"].median())
    x = make_hte_design(dat)
    clf = LogisticRegression(
        penalty="l2",
        C=1.0,
        solver="lbfgs",
        max_iter=2000,
        random_state=RANDOM_STATE,
    )
    clf.fit(x, dat["outcome"])
    design_columns = x.columns.tolist()

    phases = sorted(dat["phase_label"].unique())

    def phase_risk_difference(fitted: LogisticRegression, source: pd.DataFrame, phase: str) -> float:
        sample = source[source["phase_label"].eq(phase)].copy()
        if sample.empty:
            return np.nan
        treated = sample.copy()
        control = sample.copy()
        treated["treatment_binary"] = 1
        control["treatment_binary"] = 0
        pt = fitted.predict_proba(make_hte_design(treated, design_columns))[:, 1]
        pc = fitted.predict_proba(make_hte_design(control, design_columns))[:, 1]
        return float(np.mean(pt - pc))

    point = {phase: phase_risk_difference(clf, dat, phase) for phase in phases}
    boot_values = {phase: [] for phase in phases}
    rng = np.random.default_rng(RANDOM_STATE)
    for _ in range(n_boot):
        sample_idx = rng.integers(0, len(dat), len(dat))
        sample = dat.iloc[sample_idx].copy()
        if sample["outcome"].nunique() < 2:
            continue
        try:
            boot_x = make_hte_design(sample, design_columns)
            boot_model = LogisticRegression(
                penalty="l2",
                C=1.0,
                solver="lbfgs",
                max_iter=2000,
                random_state=RANDOM_STATE,
            )
            boot_model.fit(boot_x, sample["outcome"])
            for phase in phases:
                boot_values[phase].append(phase_risk_difference(boot_model, dat, phase))
        except Exception:
            continue
    rows = []
    crude = primary.hte_by_phase(ml_phase)
    pooled_crude = (
        crude.groupby("phase_label", as_index=False)
        .agg(
            crude_risk_difference=("risk_difference_treatment_minus_control", "mean"),
            crude_hba1c_change_difference=("hba1c_change_difference_treatment_minus_control", "mean"),
        )
    )
    for phase in phases:
        vals = np.array([v for v in boot_values[phase] if pd.notna(v)], dtype=float)
        rows.append(
            {
                "phase_label": phase,
                "n": int((dat["phase_label"] == phase).sum()),
                "adjusted_risk_difference": point[phase],
                "bootstrap_ci_low": float(np.percentile(vals, 2.5)) if len(vals) else np.nan,
                "bootstrap_ci_high": float(np.percentile(vals, 97.5)) if len(vals) else np.nan,
                "bootstrap_successful_fits": int(len(vals)),
                "adjustment_model": "l2_logistic_with_study_phase_and_treatment_phase_interactions",
            }
        )
    out = pd.DataFrame(rows).merge(pooled_crude, on="phase_label", how="left")
    return out.sort_values("adjusted_risk_difference", ascending=False)


def plot_adjusted_hte(hte: pd.DataFrame) -> None:
    if hte.empty:
        return
    plot = hte.sort_values("adjusted_risk_difference")
    y = np.arange(len(plot))
    plt.figure(figsize=(8, 5))
    x = plot["adjusted_risk_difference"].to_numpy()
    lo = plot["bootstrap_ci_low"].to_numpy()
    hi = plot["bootstrap_ci_high"].to_numpy()
    xerr = np.vstack([x - lo, hi - x])
    plt.errorbar(x, y, xerr=xerr, fmt="o", color="#3f6f8f", ecolor="#7a7a7a", capsize=3)
    plt.axvline(0, color="black", linestyle="--", linewidth=1)
    plt.yticks(y, plot["phase_label"])
    plt.xlabel("Adjusted risk difference for HbA1c improvement")
    plt.title("Adjusted Heterogeneous Treatment Response by Phase")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "journal_adjusted_hte_by_phase.png", dpi=220)
    plt.close()


def loso_external_summary() -> pd.DataFrame:
    loso = pd.read_csv(RESULTS_DIR / "model_performance_loso.csv")
    loso = loso[loso["model"].ne("dummy_majority")].dropna(subset=["auroc"]).copy()
    summary = (
        loso.groupby(["target", "feature_set", "model"], as_index=False)
        .agg(
            heldout_study_count=("held_out_study", "nunique"),
            total_test_n=("n", "sum"),
            auroc_mean=("auroc", "mean"),
            auroc_sd=("auroc", "std"),
            auroc_median=("auroc", "median"),
            auroc_min=("auroc", "min"),
            auroc_max=("auroc", "max"),
            auprc_mean=("auprc", "mean"),
            brier_mean=("brier", "mean"),
        )
        .sort_values(["target", "auroc_mean"], ascending=[True, False])
    )
    return summary


def plot_loso_heatmap(loso_summary: pd.DataFrame) -> None:
    if loso_summary.empty:
        return
    loso = pd.read_csv(RESULTS_DIR / "model_performance_loso.csv")
    loso = loso[loso["model"].ne("dummy_majority")].dropna(subset=["auroc"]).copy()
    targets = loso_summary["target"].unique().tolist()
    fig, axes = plt.subplots(1, len(targets), figsize=(8 * len(targets), 6), squeeze=False)
    for ax, target in zip(axes.ravel(), targets):
        top = loso_summary[loso_summary["target"].eq(target)].head(8).copy()
        top["combo"] = top["feature_set"] + " / " + top["model"]
        dat = loso[loso["target"].eq(target)].copy()
        dat["combo"] = dat["feature_set"] + " / " + dat["model"]
        pivot = dat[dat["combo"].isin(top["combo"])].pivot_table(
            index="held_out_study", columns="combo", values="auroc", aggfunc="mean"
        )
        pivot = pivot.reindex(columns=top["combo"].tolist())
        im = ax.imshow(pivot.to_numpy(), aspect="auto", vmin=0.45, vmax=0.9, cmap="viridis")
        ax.set_xticks(np.arange(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns, rotation=60, ha="right", fontsize=8)
        ax.set_yticks(np.arange(len(pivot.index)))
        ax.set_yticklabels(pivot.index, fontsize=8)
        ax.set_title(target)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="LOSO AUROC")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "journal_loso_heatmap.png", dpi=220)
    plt.close()


def incremental_phase_value() -> pd.DataFrame:
    perf = pd.read_csv(RESULTS_DIR / "model_performance_cv.csv")
    loso = pd.read_csv(RESULTS_DIR / "model_performance_loso.csv")
    rows = []
    cv = perf[perf["model"].ne("dummy_majority")].dropna(subset=["auroc"]).copy()
    for (target, model), group in cv.groupby(["target", "model"]):
        values = group.set_index("feature_set")["auroc"]
        if "C4_phase_map" not in values:
            continue
        for comparator in ["C1_clinical", "C2_clinical_plus_cgm"]:
            if comparator in values:
                rows.append(
                    {
                        "validation": "5fold_cv",
                        "target": target,
                        "model": model,
                        "comparison": f"C4_phase_map_minus_{comparator}",
                        "delta_auroc_mean": float(values["C4_phase_map"] - values[comparator]),
                        "delta_auroc_median": float(values["C4_phase_map"] - values[comparator]),
                        "delta_auroc_min": float(values["C4_phase_map"] - values[comparator]),
                        "delta_positive_fraction": float(values["C4_phase_map"] > values[comparator]),
                        "n_comparisons": 1,
                    }
                )
    loso = loso[loso["model"].ne("dummy_majority")].dropna(subset=["auroc"]).copy()
    pivot = loso.pivot_table(
        index=["target", "model", "held_out_study"], columns="feature_set", values="auroc", aggfunc="mean"
    ).reset_index()
    for (target, model), group in pivot.groupby(["target", "model"]):
        if "C4_phase_map" not in group.columns:
            continue
        for comparator in ["C1_clinical", "C2_clinical_plus_cgm"]:
            if comparator not in group.columns:
                continue
            delta = group["C4_phase_map"] - group[comparator]
            delta = delta.dropna()
            if delta.empty:
                continue
            rows.append(
                {
                    "validation": "leave_one_study_out",
                    "target": target,
                    "model": model,
                    "comparison": f"C4_phase_map_minus_{comparator}",
                    "delta_auroc_mean": float(delta.mean()),
                    "delta_auroc_median": float(delta.median()),
                    "delta_auroc_min": float(delta.min()),
                    "delta_positive_fraction": float((delta > 0).mean()),
                    "n_comparisons": int(len(delta)),
                }
            )
    return pd.DataFrame(rows).sort_values(["target", "validation", "delta_auroc_mean"], ascending=[True, True, False])


def paired_bootstrap_model_comparison(oof: pd.DataFrame, metrics: pd.DataFrame, n_boot: int = 1000) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(RANDOM_STATE)
    for target, target_metrics in metrics.groupby("target"):
        candidates = target_metrics.sort_values("auroc", ascending=False).reset_index(drop=True)
        pairs = []
        if len(candidates) >= 2:
            pairs.append((candidates.iloc[0], candidates.iloc[1], "best_vs_runner_up"))
        c4 = candidates[candidates["feature_set"].eq("C4_phase_map")]
        non_c4 = candidates[candidates["feature_set"].ne("C4_phase_map")]
        if not c4.empty and not non_c4.empty:
            pairs.append((c4.iloc[0], non_c4.iloc[0], "best_phase_map_vs_best_non_phase"))
        for left, right, comparison in pairs:
            left_key = (left["feature_set"], left["model"])
            right_key = (right["feature_set"], right["model"])
            left_df = oof[
                oof["target"].eq(target) & oof["feature_set"].eq(left_key[0]) & oof["model"].eq(left_key[1])
            ][["participant_id", "y_true", "y_prob"]].rename(columns={"y_prob": "p_left"})
            right_df = oof[
                oof["target"].eq(target) & oof["feature_set"].eq(right_key[0]) & oof["model"].eq(right_key[1])
            ][["participant_id", "y_prob"]].rename(columns={"y_prob": "p_right"})
            merged = left_df.merge(right_df, on="participant_id", how="inner")
            if merged.empty or merged["y_true"].nunique() < 2:
                continue
            y = merged["y_true"].to_numpy()
            p_left = merged["p_left"].to_numpy()
            p_right = merged["p_right"].to_numpy()
            point = roc_auc_score(y, p_left) - roc_auc_score(y, p_right)
            diffs = []
            for _ in range(n_boot):
                idx = rng.integers(0, len(y), len(y))
                if len(np.unique(y[idx])) < 2:
                    continue
                diffs.append(roc_auc_score(y[idx], p_left[idx]) - roc_auc_score(y[idx], p_right[idx]))
            diffs = np.array(diffs, dtype=float)
            if len(diffs):
                p_value = 2 * min(float(np.mean(diffs <= 0)), float(np.mean(diffs >= 0)))
                ci_low = float(np.percentile(diffs, 2.5))
                ci_high = float(np.percentile(diffs, 97.5))
            else:
                p_value, ci_low, ci_high = np.nan, np.nan, np.nan
            rows.append(
                {
                    "target": target,
                    "comparison": comparison,
                    "left_feature_set": left_key[0],
                    "left_model": left_key[1],
                    "right_feature_set": right_key[0],
                    "right_model": right_key[1],
                    "n": int(len(merged)),
                    "delta_auroc_left_minus_right": float(point),
                    "bootstrap_ci_low": ci_low,
                    "bootstrap_ci_high": ci_high,
                    "bootstrap_p_value": p_value,
                    "bootstrap_successful_resamples": int(len(diffs)),
                }
            )
    return pd.DataFrame(rows)


def write_report(
    selected: pd.DataFrame,
    metrics: pd.DataFrame,
    dca: pd.DataFrame,
    importance: pd.DataFrame,
    stability: pd.DataFrame,
    hte: pd.DataFrame,
    loso_summary: pd.DataFrame,
    incremental: pd.DataFrame,
    pairwise: pd.DataFrame,
) -> None:
    best = metrics.sort_values(["target", "auroc"], ascending=[True, False]).groupby("target").head(1)
    dca_summary = (
        dca[dca["strategy"].eq("model")]
        .groupby(["target", "feature_set", "model"], as_index=False)
        .agg(max_net_benefit=("net_benefit", "max"), median_net_benefit=("net_benefit", "median"))
        if not dca.empty
        else pd.DataFrame()
    )
    stability_summary = pd.DataFrame(
        [
            {
                "n_bootstrap": len(stability),
                "ari_median": stability["adjusted_rand_index"].median(),
                "ari_iqr_low": stability["adjusted_rand_index"].quantile(0.25),
                "ari_iqr_high": stability["adjusted_rand_index"].quantile(0.75),
                "silhouette_median": stability["silhouette"].median(),
            }
        ]
    )
    top_importance = importance.sort_values(["target", "importance_mean"], ascending=[True, False]).groupby("target").head(10)
    report = f"""# 高水平期刊导向二级实验报告

生成脚本：`scripts/run_journal_grade_experiments.py`  
主实验脚本：`scripts/run_glycemic_phase_research.py`

## 本轮新增证据

本轮在原有相图、模型比较、异质性治疗响应和个体化框架基础上，补充了六类更接近高水平医学与机器学习期刊审稿标准的分析：

1. 将 XGBoost、LightGBM、CatBoost 纳入主模型比较。
2. 对表现靠前的候选模型输出 5 折 out-of-fold 预测，避免用训练集预测评价模型。
3. 计算校准截距、校准斜率、Brier score 与 expected calibration error。
4. 进行 decision curve analysis，评估不同决策阈值下的净获益。
5. 用交叉验证内置的 permutation importance 识别可解释预测因子。
6. 用 bootstrap 评估血糖动力学相位图稳定性，并用调整模型估计相位分层治疗响应。

## 被纳入二级诊断的模型

{markdown_table(selected)}

## 最佳模型与校准

{markdown_table(best)}

解释要点：

- AUROC/AUPRC 反映排序能力，但不能说明概率是否可信。
- calibration intercept 接近 0、calibration slope 接近 1、Brier 和 ECE 越低，越支持模型可作为风险分层工具。
- 当前二级诊断使用 out-of-fold 预测，因此比全数据拟合后的表观性能更接近真实泛化表现。

校准图：`figures/journal_calibration_curves.png`

## 决策曲线分析

{markdown_table(dca_summary)}

决策曲线图：`figures/journal_decision_curve.png`

该结果用于回答一个临床审稿问题：模型在何种阈值区间内比“全部干预”或“完全不干预”更有净获益。若目标期刊偏临床转化，后续应预先定义 2-3 个临床可解释阈值，例如 20%、30%、40% 的改善概率。

## 可解释性：Permutation Importance

{markdown_table(top_importance)}

变量重要性图：`figures/journal_permutation_importance.png`

该分析没有使用随访变量作为输入，重要性仅反映基线临床、基线 CGM 和相图特征对预测任务的贡献，避免了随访后变量造成的数据泄漏。

## 相图稳定性

{markdown_table(stability_summary)}

相图 bootstrap 稳定性图：`figures/phase_bootstrap_stability.png`

Adjusted Rand Index 越高，说明相位结构对样本重抽样越稳定。若后续要冲击更高水平期刊，建议进一步做 leave-one-study-out 相图重建、不同相位数 K 的敏感性分析，以及连续相位坐标替代离散标签的稳健性分析。

## 调整后的异质性治疗响应

{markdown_table(hte)}

异质性治疗响应图：`figures/journal_adjusted_hte_by_phase.png`

该模型调整了研究、年龄、基线 HbA1c 和基线 TIR，并估计不同相位内治疗相对于对照的 HbA1c 改善风险差。结果仍应被解释为探索性、假设生成证据，不应直接作为临床决策规则。

## 留一研究外部泛化

{markdown_table(loso_summary.head(15))}

外部验证热图：`figures/journal_loso_heatmap.png`

LOSO 结果用于回答模型是否只学习了某一个研究的数据结构。若某个模型 5 折 AUROC 高但 LOSO 均值或最小值明显下降，投稿时应把它定位为内部预测模型，而不是可泛化临床工具。

## 相图特征增量价值

{markdown_table(incremental.head(20))}

该表比较 C4 相图特征集相对于 C1 临床特征和 C2 临床+CGM 特征的 AUROC 变化。若相图特征没有明显提高 AUROC，它仍可能具有机制解释、分层治疗响应和可视化价值；论文叙事应避免仅以预测增益作为相图价值的唯一依据。

## 模型差异 paired bootstrap

{markdown_table(pairwise)}

该分析基于 out-of-fold 预测进行配对 bootstrap，用来判断排名相近模型的 AUROC 差异是否稳定。若置信区间跨 0，应报告模型性能相近，而不是过度强调名义第一名。

## 新增输出文件

- `results/journal_oof_predictions.csv`
- `results/journal_calibration_metrics.csv`
- `results/journal_calibration_bins.csv`
- `results/journal_decision_curve.csv`
- `results/journal_permutation_importance.csv`
- `results/phase_bootstrap_stability.csv`
- `results/journal_adjusted_hte_by_phase.csv`
- `results/journal_loso_summary.csv`
- `results/journal_incremental_phase_value.csv`
- `results/journal_model_pairwise_bootstrap.csv`
- `figures/journal_calibration_curves.png`
- `figures/journal_decision_curve.png`
- `figures/journal_permutation_importance.png`
- `figures/phase_bootstrap_stability.png`
- `figures/journal_adjusted_hte_by_phase.png`
- `figures/journal_loso_heatmap.png`

## 面向投稿的下一步

1. 将 primary endpoint 固定为 HbA1c 改善 >=0.5%，key secondary endpoint 固定为 TIR 改善 >=5 个百分点。
2. 使用 nested cross-validation 或固定外部研究留出集，避免模型选择偏倚。
3. 对治疗响应结果采用 causal forest、R-learner 或 doubly robust learner 复核。
4. 在论文中把相图作为“机制启发的低维表征”，把机器学习作为预测与分层工具，而不是把聚类标签解释为确定的生物亚型。
5. 若申请到更细粒度 CGM 原始时序，扩展为动态系统论文：连续相轨迹、状态转移、治疗诱导相变和个体化干预窗口。
"""
    (DOCS_DIR / "journal_grade_experiment_report_zh.md").write_text(report, encoding="utf-8")


def main() -> int:
    ensure_dirs()
    ml_phase = make_ml_phase()
    perf = pd.read_csv(RESULTS_DIR / "model_performance_cv.csv")
    selected = select_experiments(perf)

    oof = run_oof_predictions(ml_phase, selected)
    oof.to_csv(RESULTS_DIR / "journal_oof_predictions.csv", index=False)

    metrics, bins = summarize_calibration(oof)
    metrics.to_csv(RESULTS_DIR / "journal_calibration_metrics.csv", index=False)
    bins.to_csv(RESULTS_DIR / "journal_calibration_bins.csv", index=False)
    plot_calibration(metrics, bins)

    dca = decision_curve(oof, metrics)
    dca.to_csv(RESULTS_DIR / "journal_decision_curve.csv", index=False)
    plot_decision_curve(dca)

    importance = run_permutation_importance(ml_phase, metrics)
    importance.to_csv(RESULTS_DIR / "journal_permutation_importance.csv", index=False)
    plot_permutation_importance(importance)

    stability = phase_bootstrap_stability()
    stability.to_csv(RESULTS_DIR / "phase_bootstrap_stability.csv", index=False)
    plot_phase_bootstrap(stability)

    hte = adjusted_hte_by_phase(ml_phase)
    hte.to_csv(RESULTS_DIR / "journal_adjusted_hte_by_phase.csv", index=False)
    plot_adjusted_hte(hte)

    loso_summary = loso_external_summary()
    loso_summary.to_csv(RESULTS_DIR / "journal_loso_summary.csv", index=False)
    plot_loso_heatmap(loso_summary)

    incremental = incremental_phase_value()
    incremental.to_csv(RESULTS_DIR / "journal_incremental_phase_value.csv", index=False)

    pairwise = paired_bootstrap_model_comparison(oof, metrics)
    pairwise.to_csv(RESULTS_DIR / "journal_model_pairwise_bootstrap.csv", index=False)

    write_report(selected, metrics, dca, importance, stability, hte, loso_summary, incremental, pairwise)
    print(
        json.dumps(
            {
                "selected_experiments": int(len(selected)),
                "oof_rows": int(len(oof)),
                "calibration_rows": int(len(metrics)),
                "decision_curve_rows": int(len(dca)),
                "importance_rows": int(len(importance)),
                "phase_bootstrap_rows": int(len(stability)),
                "adjusted_hte_rows": int(len(hte)),
                "loso_summary_rows": int(len(loso_summary)),
                "incremental_phase_rows": int(len(incremental)),
                "pairwise_bootstrap_rows": int(len(pairwise)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
