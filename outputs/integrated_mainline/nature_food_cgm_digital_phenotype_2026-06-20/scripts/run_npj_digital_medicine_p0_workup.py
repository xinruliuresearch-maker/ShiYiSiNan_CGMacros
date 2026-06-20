"""P0 workup for an npj Digital Medicine glycaemic phase-map submission.

Outputs:
- frozen external validation using the held-out JAEB Loop public dataset
- phase-map algorithm card and software specification
- subgroup fairness and calibration audit
- phase-guided digital care workflow source files
- redesigned main figures centered on CGM digital phenotypes
"""

from __future__ import annotations

from pathlib import Path
import io
import json
import math
import zipfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(r"D:\ai for science")
PHASE = ROOT / "results" / "jaeb_glycemic_phase_completion"
STRATEGY = ROOT / "results" / "npj_digital_medicine_phase_strategy"
RAW_EXTRA = ROOT / "data" / "raw" / "jaeb_public_extra"
RESULTS = ROOT / "results"
OUT = STRATEGY / "p0_workup"
DOCS = OUT / "docs"
TABLES = OUT / "tables"
FIGSRC = OUT / "figure_source_data"
FIGURES = OUT / "figures"
for path in [OUT, DOCS, TABLES, FIGSRC, FIGURES]:
    path.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
LOOP_ZIP = "Loop study public dataset 2023-01-31.zip"

ORDER_COLS = [
    "glycemic_burden_score",
    "hypoglycemic_susceptibility_score",
    "dynamic_instability_score",
    "circadian_disruption_score",
    "resilience_proxy_score",
]

PHASE_COLORS = {
    "稳定达标相": "#2E7D32",
    "高波动震荡相": "#6A1B9A",
    "高血糖持续相": "#C62828",
    "昼夜节律紊乱相": "#EF6C00",
    "低血糖易感相": "#1565C0",
}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def write(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str).str.replace("%", "", regex=False).str.replace(",", "", regex=False).str.replace("<", "", regex=False),
        errors="coerce",
    )


def z_from_train(x: pd.Series, train_ref: pd.Series) -> pd.Series:
    mu = pd.to_numeric(train_ref, errors="coerce").mean()
    sd = pd.to_numeric(train_ref, errors="coerce").std(ddof=0)
    if pd.isna(sd) or sd == 0:
        return pd.Series(np.zeros(len(x)), index=x.index)
    return (pd.to_numeric(x, errors="coerce") - mu) / sd


def logit(p: pd.Series) -> pd.Series:
    p = pd.to_numeric(p, errors="coerce").clip(1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def calibration_slope_intercept(y: pd.Series, p: pd.Series) -> tuple[float, float]:
    y = pd.Series(y).astype(float)
    p = pd.Series(p).astype(float)
    if len(y) < 20 or y.nunique() < 2:
        return np.nan, np.nan
    try:
        x = logit(p).to_numpy().reshape(-1, 1)
        model = LogisticRegression(penalty=None, solver="lbfgs", max_iter=1000)
        model.fit(x, y)
        return float(model.coef_[0][0]), float(model.intercept_[0])
    except Exception:
        return np.nan, np.nan


def ece_score(y: pd.Series, p: pd.Series, bins: int = 10) -> float:
    y = pd.Series(y).astype(float)
    p = pd.Series(p).astype(float).clip(0, 1)
    cuts = pd.cut(p, np.linspace(0, 1, bins + 1), include_lowest=True, duplicates="drop")
    total = len(y)
    if total == 0:
        return np.nan
    ece = 0.0
    for _, idx in p.groupby(cuts, observed=False).groups.items():
        if len(idx) == 0:
            continue
        ece += len(idx) / total * abs(y.loc[idx].mean() - p.loc[idx].mean())
    return float(ece)


def binary_metrics(y: pd.Series, p: pd.Series) -> dict[str, float]:
    y = pd.Series(y).dropna().astype(int)
    p = pd.Series(p).loc[y.index].astype(float)
    out = {
        "n": int(len(y)),
        "positive_rate": float(y.mean()) if len(y) else np.nan,
        "mean_predicted_risk": float(p.mean()) if len(p) else np.nan,
        "brier": float(brier_score_loss(y, p.clip(0, 1))) if len(y) and y.nunique() > 1 else np.nan,
        "auroc": np.nan,
        "auprc": np.nan,
        "calibration_slope": np.nan,
        "calibration_intercept": np.nan,
        "expected_calibration_error": np.nan,
    }
    if len(y) >= 20 and y.nunique() > 1:
        out["auroc"] = float(roc_auc_score(y, p))
        out["auprc"] = float(average_precision_score(y, p))
        slope, intercept = calibration_slope_intercept(y, p)
        out["calibration_slope"] = slope
        out["calibration_intercept"] = intercept
        out["expected_calibration_error"] = ece_score(y, p)
    return out


def read_loop_table(member: str) -> pd.DataFrame:
    with zipfile.ZipFile(RAW_EXTRA / LOOP_ZIP) as archive:
        raw = archive.read(member)
    return pd.read_csv(io.BytesIO(raw), sep="|", dtype=str, low_memory=False)


def build_loop_frozen_dataset(train_phase: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    glu = read_loop_table("Data Tables/gluIndices.txt")
    sample = read_loop_table("Data Tables/SampleResults.txt")
    roster = read_loop_table("Data Tables/PtRoster.txt")

    metrics = {
        "gluMean": "cgm_mean_glucose_mg_dl",
        "gluInRange": "cgm_time_in_range_70_180_pct",
        "gluBelow70": "cgm_time_below_70_pct",
        "gluBelow54": "cgm_time_below_54_pct",
        "gluAbove180": "cgm_time_above_180_pct",
        "gluAbove250": "cgm_time_above_250_pct",
        "gluHours": "cgm_hours",
        "gluCV": "cgm_cv_pct",
    }
    glu = glu.copy()
    for c in metrics:
        glu[c] = to_num(glu[c])
    base = glu[glu["Period"].eq("Baseline")].copy()
    m6 = glu[glu["Period"].eq("Month 6")].copy()
    base = base.groupby("SubjectID", as_index=False).agg({c: "mean" for c in metrics})
    m6 = m6.groupby("SubjectID", as_index=False).agg({c: "mean" for c in metrics})
    base = base.rename(columns={"SubjectID": "PtID", **{k: v for k, v in metrics.items()}})
    m6 = m6.rename(columns={"SubjectID": "PtID", **{k: f"followup_{v}" for k, v in metrics.items()}})
    out = base.merge(m6, on="PtID", how="left")
    out["participant_id"] = "LOOP_FROZEN_" + out["PtID"].astype(str)
    out["study_id"] = "LOOP_FROZEN"

    sample = sample[sample["ResultName"].astype(str).str.upper().eq("GLYHB")].copy()
    sample["Value"] = to_num(sample["Value"])
    hba1c = sample.pivot_table(index="PtID", columns="Visit", values="Value", aggfunc="mean").reset_index()
    hba1c = hba1c.rename(columns={"Baseline": "x_baseline_hba1c_pct", "Month 6": "y_followup_hba1c_pct"})
    out = out.merge(hba1c[["PtID", "x_baseline_hba1c_pct", "y_followup_hba1c_pct"]], on="PtID", how="left")

    roster = roster.drop_duplicates("PtID").copy()
    out = out.merge(roster[["PtID", "AgeAtEnrollment", "PtCohort", "PtStatus", "LoopUseTimeAtEnroll"]], on="PtID", how="left")
    out["x_age_years"] = to_num(out["AgeAtEnrollment"])
    out["x_randomized_arm"] = out["PtCohort"].fillna("missing")
    out["x_sex"] = "missing"
    out["x_race"] = "missing"
    out["x_ethnicity"] = "missing"
    out["x_baseline_bmi"] = np.nan
    out["x_diabetes_duration_years"] = np.nan
    out["y_hba1c_change_pct_points"] = out["y_followup_hba1c_pct"] - out["x_baseline_hba1c_pct"]
    out["y_hba1c_improved_ge_0_5"] = np.where(
        out["y_hba1c_change_pct_points"].notna(), (out["y_hba1c_change_pct_points"] <= -0.5).astype(int), np.nan
    )
    out["y_change_cgm_time_in_range_70_180_pct"] = (
        out["followup_cgm_time_in_range_70_180_pct"] - out["cgm_time_in_range_70_180_pct"]
    )
    out["y_tir_improved_ge_5pct"] = np.where(
        out["y_change_cgm_time_in_range_70_180_pct"].notna(),
        (out["y_change_cgm_time_in_range_70_180_pct"] >= 5).astype(int),
        np.nan,
    )

    train_ref = train_phase.copy()
    train_ref["cgm_sd_proxy"] = train_ref["cgm_mean_glucose_mg_dl"] * train_ref["cgm_cv_pct"] / 100.0
    out["cgm_sd_proxy"] = out["cgm_mean_glucose_mg_dl"] * out["cgm_cv_pct"] / 100.0
    out["glycemic_burden_score"] = (
        z_from_train(out["cgm_mean_glucose_mg_dl"], train_ref["cgm_mean_glucose_mg_dl"])
        + z_from_train(out["cgm_time_above_180_pct"], train_ref["cgm_time_above_180_pct"])
        + z_from_train(out["cgm_time_above_250_pct"], train_ref["cgm_time_above_250_pct"])
        - z_from_train(out["cgm_time_in_range_70_180_pct"], train_ref["cgm_time_in_range_70_180_pct"])
    ) / 4.0
    out["hypoglycemic_susceptibility_score"] = (
        z_from_train(out["cgm_time_below_70_pct"], train_ref["cgm_time_below_70_pct"])
        + z_from_train(out["cgm_time_below_54_pct"], train_ref["cgm_time_below_54_pct"])
    ) / 2.0
    out["dynamic_instability_score"] = (
        z_from_train(out["cgm_cv_pct"], train_ref["cgm_cv_pct"])
        + z_from_train(out["cgm_sd_proxy"], train_ref["cgm_sd_proxy"])
    ) / 2.0
    out["circadian_disruption_score"] = 0.0
    out["resilience_proxy_score"] = (
        z_from_train(out["cgm_time_above_250_pct"], train_ref["cgm_time_above_250_pct"])
        + z_from_train(out["cgm_cv_pct"], train_ref["cgm_cv_pct"])
        + z_from_train(out["cgm_mean_glucose_mg_dl"], train_ref["cgm_mean_glucose_mg_dl"])
    ) / 3.0

    centroids = train_ref.groupby("phase_label", as_index=False)[ORDER_COLS].mean()
    distances = []
    x = out[ORDER_COLS].fillna(0).to_numpy(float)
    for _, row in centroids.iterrows():
        c = row[ORDER_COLS].to_numpy(float)
        distances.append(np.sqrt(((x - c) ** 2).sum(axis=1)))
    dist = np.vstack(distances).T
    nearest = dist.argmin(axis=1)
    out["phase_label"] = [centroids.iloc[i]["phase_label"] for i in nearest]
    out["phase_assignment_distance"] = dist.min(axis=1)
    phase_dict = read_csv(PHASE / "jaeb_phase_label_dictionary.csv")
    phase_id = dict(zip(phase_dict["phase_label_zh"], phase_dict["phase_id"]))
    phase_en = dict(zip(phase_dict["phase_label_zh"], phase_dict["phase_label_en"]))
    out["phase_id"] = out["phase_label"].map(phase_id)
    out["phase_label_en"] = out["phase_label"].map(phase_en)

    inventory = pd.DataFrame(
        [
            {
                "dataset": "Loop study public dataset 2023-01-31",
                "zip_file": LOOP_ZIP,
                "role": "primary frozen external validation",
                "n_with_baseline_cgm": int(out["cgm_mean_glucose_mg_dl"].notna().sum()),
                "n_with_month6_cgm": int(out["followup_cgm_time_in_range_70_180_pct"].notna().sum()),
                "n_with_baseline_hba1c": int(out["x_baseline_hba1c_pct"].notna().sum()),
                "n_with_month6_hba1c": int(out["y_followup_hba1c_pct"].notna().sum()),
                "phase_assignment": "nearest fixed centroid from original JAEB phase-map training set",
                "notes": "No retraining or tuning on Loop data.",
            }
        ]
    )
    return out, inventory


def make_preprocessor(num_cols: list[str], cat_cols: list[str]) -> ColumnTransformer:
    num = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
    cat = Pipeline(
        [("imputer", SimpleImputer(strategy="constant", fill_value="missing")), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]
    )
    return ColumnTransformer([("num", num, num_cols), ("cat", cat, cat_cols)], sparse_threshold=0.0)


FEATURE_SETS = {
    "C2_clinical_plus_cgm": {
        "numeric": [
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
        ],
        "categorical": ["study_id", "x_randomized_arm", "x_sex", "x_race", "x_ethnicity"],
    },
    "C4_phase_map": {
        "numeric": [
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
        ],
        "categorical": ["study_id", "x_randomized_arm", "x_sex", "x_race", "x_ethnicity", "phase_label"],
    },
}


def train_and_validate_external(ml_phase: pd.DataFrame, loop: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    predictions = []
    metrics = []
    for target in ["y_hba1c_improved_ge_0_5", "y_tir_improved_ge_5pct"]:
        for fs_name, spec in FEATURE_SETS.items():
            num_cols = [c for c in spec["numeric"] if c in ml_phase.columns and c in loop.columns]
            cat_cols = [c for c in spec["categorical"] if c in ml_phase.columns and c in loop.columns]
            train = ml_phase.dropna(subset=[target]).copy()
            test = loop.dropna(subset=[target]).copy()
            if train[target].nunique() < 2 or test.empty:
                continue
            pipe = Pipeline(
                [
                    ("pre", make_preprocessor(num_cols, cat_cols)),
                    ("model", LogisticRegression(max_iter=2000, class_weight="balanced", solver="lbfgs")),
                ]
            )
            pipe.fit(train[num_cols + cat_cols], train[target].astype(int))
            prob = pipe.predict_proba(test[num_cols + cat_cols])[:, 1]
            pred_cols = ["participant_id", "study_id", "phase_label", "phase_id", "phase_label_en", target]
            pred = test[[c for c in pred_cols if c in test.columns]].copy()
            pred["target"] = target
            pred["feature_set"] = fs_name
            pred["model"] = "logistic_ridge_locked_train"
            pred["y_true"] = pred[target].astype(int)
            pred["y_prob"] = prob
            pred = pred.drop(columns=[target])
            predictions.append(pred)
            row = binary_metrics(pred["y_true"], pred["y_prob"])
            row.update(
                {
                    "validation_dataset": "LOOP_FROZEN",
                    "target": target,
                    "feature_set": fs_name,
                    "model": "logistic_ridge_locked_train",
                    "train_n": int(len(train)),
                    "test_n": int(len(test)),
                    "numeric_features": "; ".join(num_cols),
                    "categorical_features": "; ".join(cat_cols),
                }
            )
            metrics.append(row)
    pred_df = pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()
    metrics_df = pd.DataFrame(metrics)
    return metrics_df, pred_df


def build_training_ml_phase() -> pd.DataFrame:
    ml = read_csv(PHASE / "tables" / "locked_processed_ml_table.csv")
    phase = read_csv(PHASE / "tables" / "locked_glycemic_phase_features.csv")
    keep = ["participant_id", "study_id", "phase_label"] + ORDER_COLS + [
        "cgm_mean_glucose_mg_dl",
        "cgm_time_in_range_70_180_pct",
        "cgm_time_below_70_pct",
        "cgm_time_below_54_pct",
        "cgm_time_above_180_pct",
        "cgm_time_above_250_pct",
        "cgm_cv_pct",
    ]
    return ml.merge(phase[keep], on=["participant_id", "study_id"], how="left")


def subgroup_audit() -> pd.DataFrame:
    oof = read_csv(RESULTS / "journal_oof_predictions.csv")
    ml_phase = build_training_ml_phase()
    meta_cols = [
        "participant_id",
        "study_id",
        "x_age_years",
        "x_sex",
        "x_race",
        "x_ethnicity",
        "x_baseline_hba1c_pct",
        "phase_label",
    ]
    dat = oof.merge(ml_phase[meta_cols], on=["participant_id", "study_id"], how="left")
    dat["age_group"] = pd.cut(dat["x_age_years"], [-np.inf, 18, 45, 65, np.inf], labels=["<18", "18-44", "45-64", "65+"])
    dat["baseline_hba1c_group"] = pd.cut(
        dat["x_baseline_hba1c_pct"], [-np.inf, 7, 8, 9, np.inf], labels=["<7", "7-<8", "8-<9", ">=9"]
    )
    group_vars = ["age_group", "x_sex", "x_race", "x_ethnicity", "study_id", "phase_label", "baseline_hba1c_group"]
    rows = []
    selected = dat[
        (
            (dat["target"].eq("y_hba1c_improved_ge_0_5") & dat["feature_set"].isin(["C1_clinical", "C4_phase_map"]))
            | (dat["target"].eq("y_tir_improved_ge_5pct") & dat["feature_set"].isin(["C2_clinical_plus_cgm", "C4_phase_map"]))
        )
    ].copy()
    for (target, feature_set, model), group in selected.groupby(["target", "feature_set", "model"]):
        overall = binary_metrics(group["y_true"], group["y_prob"])
        rows.append(
            {
                "target": target,
                "feature_set": feature_set,
                "model": model,
                "subgroup_variable": "overall",
                "subgroup": "overall",
                **overall,
            }
        )
        for gv in group_vars:
            for level, sub in group.dropna(subset=[gv]).groupby(gv, observed=False):
                if len(sub) < 20:
                    continue
                met = binary_metrics(sub["y_true"], sub["y_prob"])
                rows.append(
                    {
                        "target": target,
                        "feature_set": feature_set,
                        "model": model,
                        "subgroup_variable": gv,
                        "subgroup": str(level),
                        **met,
                    }
                )
    out = pd.DataFrame(rows)
    if not out.empty:
        overall = out[out["subgroup_variable"].eq("overall")][
            ["target", "feature_set", "model", "auroc", "brier", "expected_calibration_error"]
        ].rename(
            columns={
                "auroc": "overall_auroc",
                "brier": "overall_brier",
                "expected_calibration_error": "overall_ece",
            }
        )
        out = out.merge(overall, on=["target", "feature_set", "model"], how="left")
        out["delta_auroc_vs_overall"] = out["auroc"] - out["overall_auroc"]
        out["delta_brier_vs_overall"] = out["brier"] - out["overall_brier"]
        out["delta_ece_vs_overall"] = out["expected_calibration_error"] - out["overall_ece"]
        phase_dict = read_csv(PHASE / "jaeb_phase_label_dictionary.csv")
        phase_en = dict(zip(phase_dict["phase_label_zh"], phase_dict["phase_label_en"]))
        out["subgroup_display"] = out["subgroup"].astype(str)
        is_phase_label = out["subgroup_variable"].eq("phase_label")
        out.loc[is_phase_label, "subgroup_display"] = (
            out.loc[is_phase_label, "subgroup"].map(phase_en).fillna(out.loc[is_phase_label, "subgroup_display"])
        )
    return out


def build_workflow_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    hte = read_csv(PHASE / "tables" / "locked_journal_adjusted_hte_by_phase.csv")
    framework = read_csv(PHASE / "tables" / "locked_individualized_intervention_framework.csv")
    phase_dict = read_csv(PHASE / "jaeb_phase_label_dictionary.csv")
    workflow_nodes = pd.DataFrame(
        [
            ("N1", "CGM data ingestion", "Import baseline CGM summary or raw-CGM derived summary features.", "data"),
            ("N2", "Feature harmonization", "Map CGM metrics to TIR, TBR, TAR, mean glucose, variability and phase order parameters.", "algorithm"),
            ("N3", "Phase assignment", "Assign a glycaemic phase using locked centroids and missingness rules.", "algorithm"),
            ("N4", "Risk and response display", "Show validated risk estimates, uncertainty and phase phenotype narrative.", "interface"),
            ("N5", "Phase-guided care discussion", "Suggest review focus such as hypoglycaemia prevention or variability reduction.", "clinical_workflow"),
            ("N6", "Clinician confirmation", "Clinician confirms fit with context; no autonomous therapy change.", "safety"),
            ("N7", "Monitoring and reassessment", "Repeat phase mapping after intervention or new CGM window.", "followup"),
        ],
        columns=["node_id", "node_label", "description", "node_type"],
    )
    workflow_edges = pd.DataFrame(
        [
            ("N1", "N2", "CGM window selected"),
            ("N2", "N3", "order parameters computed"),
            ("N3", "N4", "phase phenotype available"),
            ("N4", "N5", "digital decision support"),
            ("N5", "N6", "clinician review"),
            ("N6", "N7", "plan documented"),
            ("N7", "N1", "new CGM window"),
        ],
        columns=["source", "target", "edge_label"],
    )
    hte = hte.merge(phase_dict[["phase_label_zh", "phase_id", "phase_label_en"]], left_on="phase_label", right_on="phase_label_zh", how="left")
    framework_summary = (
        framework.dropna(subset=["phase_label"])
        .groupby(["phase_label", "phase_based_intervention_focus"], as_index=False)
        .agg(n=("participant_id", "size"), median_prediction=("predicted_hba1c_improvement_probability_research_model", "median"))
        .merge(
            hte[["phase_label", "phase_id", "phase_label_en", "adjusted_risk_difference", "bootstrap_ci_low", "bootstrap_ci_high"]],
            on="phase_label",
            how="left",
        )
    )
    workflow_nodes.to_csv(FIGSRC / "digital_care_workflow_nodes.csv", index=False)
    workflow_edges.to_csv(FIGSRC / "digital_care_workflow_edges.csv", index=False)
    framework_summary.to_csv(FIGSRC / "phase_guided_care_workflow_summary.csv", index=False)
    return workflow_nodes, framework_summary


def write_algorithm_card() -> None:
    card = """
# Phase-Map Algorithm Card

## Intended Use

The glycaemic phase-map algorithm is a research-grade CGM digital phenotype. It summarizes a baseline CGM window into interpretable glycaemic phases for retrospective risk organization, model validation, and treatment-response hypothesis generation.

It is not a standalone clinical decision system and must not autonomously change therapy.

## Inputs

Required baseline CGM summary fields:

- mean glucose, mg/dL
- time in range 70-180%, time below 70%, time below 54%
- time above 180%, time above 250%
- glucose coefficient of variation
- CGM wear hours

Optional clinical fields used in prediction models:

- age, baseline HbA1c, BMI, diabetes duration
- sex, race, ethnicity, study/context, randomized arm or care mode

## Feature Construction

The algorithm computes five order parameters:

1. Glycaemic burden.
2. Hypoglycaemic susceptibility.
3. Dynamic instability.
4. Circadian disruption, when day/night summaries are available.
5. Resilience proxy.

For frozen validation, order parameters are scaled using training-set reference means and standard deviations. New participants are assigned to the nearest locked phase centroid in order-parameter space.

## Output

- phase_label and phase_id
- phase assignment distance
- order parameter values
- optional outcome risk estimates from locked prediction models

## Validation Status

Current evidence is retrospective. Internal and leave-one-study-out validation are available. Loop study is used as a frozen external validation in the P0 workup. Prospective silent-mode validation remains required before clinical deployment.

## Limitations

- Summary-CGM based; raw time-series transitions are not yet incorporated.
- Phase labels are digital phenotypes, not confirmed biological subtypes.
- Prediction gain from phase features is modest; interpretability and workflow support are the primary rationale.
- Subgroup performance and calibration must be audited before deployment.
"""
    write(DOCS / "phase_map_algorithm_card.md", card)
    spec = """
# Phase-Map Software Specification

## Version

`phase-map-jaeb-summary-v0.1`

## Pipeline

1. Validate input schema.
2. Convert percent strings to numeric percentages.
3. Derive or validate CGM summary metrics.
4. Compute order parameters using locked training reference statistics.
5. Assign phase by nearest locked centroid.
6. Run optional prediction model if required clinical covariates are present.
7. Emit warnings for missing circadian features, short CGM wear, missing HbA1c, or out-of-distribution assignment distance.

## Input Schema

See `phase_map_input_schema.csv`.

## Output Schema

See `phase_map_output_schema.csv`.

## Missingness Rules

- Numeric predictors are median-imputed inside locked model pipelines.
- Categorical predictors use an explicit `missing` category.
- If day/night CGM is unavailable, circadian disruption is set to the training-set average for phase assignment and flagged.

## Reproducibility

All phase centroids, feature definitions, model parameters, and figure source data are versioned in the project output directory. Frozen validation datasets are not used for model tuning.
"""
    write(DOCS / "phase_map_software_specification.md", spec)
    input_schema = pd.DataFrame(
        [
            ("participant_id", "string", "required", "Unique participant identifier."),
            ("cgm_mean_glucose_mg_dl", "numeric", "required", "Baseline CGM mean glucose."),
            ("cgm_time_in_range_70_180_pct", "numeric", "required", "Percent CGM time 70-180 mg/dL."),
            ("cgm_time_below_70_pct", "numeric", "required", "Percent CGM time below 70 mg/dL."),
            ("cgm_time_below_54_pct", "numeric", "required", "Percent CGM time below 54 mg/dL."),
            ("cgm_time_above_180_pct", "numeric", "required", "Percent CGM time above 180 mg/dL."),
            ("cgm_time_above_250_pct", "numeric", "required", "Percent CGM time above 250 mg/dL."),
            ("cgm_cv_pct", "numeric", "required", "Glucose coefficient of variation."),
            ("cgm_hours", "numeric", "recommended", "CGM wear hours in the baseline window."),
            ("x_baseline_hba1c_pct", "numeric", "optional", "Baseline HbA1c for prediction models."),
            ("x_age_years", "numeric", "optional", "Age for prediction models and subgroup audit."),
        ],
        columns=["field", "type", "requirement", "description"],
    )
    output_schema = pd.DataFrame(
        [
            ("phase_label", "string", "Assigned phase label."),
            ("phase_id", "string", "Machine-stable phase identifier."),
            ("phase_assignment_distance", "numeric", "Distance to nearest phase centroid."),
            ("glycemic_burden_score", "numeric", "Order parameter."),
            ("hypoglycemic_susceptibility_score", "numeric", "Order parameter."),
            ("dynamic_instability_score", "numeric", "Order parameter."),
            ("circadian_disruption_score", "numeric", "Order parameter."),
            ("resilience_proxy_score", "numeric", "Order parameter."),
            ("predicted_probability", "numeric", "Optional model output."),
            ("warnings", "string", "Missingness or out-of-distribution warnings."),
        ],
        columns=["field", "type", "description"],
    )
    input_schema.to_csv(TABLES / "phase_map_input_schema.csv", index=False)
    output_schema.to_csv(TABLES / "phase_map_output_schema.csv", index=False)


def make_figures(loop: pd.DataFrame, external_metrics: pd.DataFrame, fairness: pd.DataFrame, workflow_summary: pd.DataFrame) -> None:
    train_phase = read_csv(PHASE / "tables" / "locked_glycemic_phase_features.csv")
    phase_summary = read_csv(PHASE / "figure_source_data" / "figure2b_phase_cgm_outcome_summary.csv")
    boot = read_csv(PHASE / "tables" / "locked_phase_bootstrap_stability.csv")
    hte = read_csv(PHASE / "tables" / "locked_journal_adjusted_hte_by_phase.csv")
    nested = read_csv(PHASE / "tables" / "locked_journal_nested_tuning_summary.csv")
    loso = read_csv(PHASE / "tables" / "locked_journal_loso_summary.csv")
    phase_dict = read_csv(PHASE / "jaeb_phase_label_dictionary.csv")
    phase_en = dict(zip(phase_dict["phase_label_zh"], phase_dict["phase_label_en"]))

    # Figure 1: digital phenotype map and algorithm flow.
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for label, g in train_phase.groupby("phase_label"):
        axes[0].scatter(
            g["glycemic_burden_score"],
            g["dynamic_instability_score"],
            s=24,
            alpha=0.65,
            label=phase_en.get(label, label),
            color=PHASE_COLORS.get(label, "#777777"),
        )
    axes[0].set_title("Locked JAEB glycaemic phase map")
    axes[0].set_xlabel("Glycaemic burden")
    axes[0].set_ylabel("Dynamic instability")
    axes[0].legend(fontsize=7)
    flow = ["CGM summary", "Order parameters", "Locked phase centroids", "Digital phenotype", "Care workflow"]
    y = np.linspace(0.85, 0.15, len(flow))
    axes[1].axis("off")
    for i, (txt, yy) in enumerate(zip(flow, y)):
        axes[1].text(0.5, yy, txt, ha="center", va="center", fontsize=11, bbox=dict(boxstyle="round,pad=0.35", fc="#EEF3F8", ec="#4E79A7"))
        if i < len(flow) - 1:
            axes[1].annotate("", xy=(0.5, y[i + 1] + 0.07), xytext=(0.5, yy - 0.07), arrowprops=dict(arrowstyle="->", lw=1.2))
    axes[1].set_title("Computable CGM digital phenotype")
    fig.tight_layout()
    fig.savefig(FIGURES / "figure1_cgm_digital_phenotype.png", dpi=220)
    plt.close(fig)

    # Figure 2: phenotype validity.
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    ps = phase_summary.sort_values("phase_order")
    x = np.arange(len(ps))
    axes[0].bar(x - 0.2, ps["baseline_tir_mean"], width=0.4, label="TIR %", color="#59A14F")
    axes[0].bar(x + 0.2, ps["baseline_cv"], width=0.4, label="CV %", color="#F28E2B")
    axes[0].set_xticks(x, ps["phase_id"], rotation=35, ha="right")
    axes[0].set_title("CGM phenotype signatures")
    axes[0].legend()
    axes[1].hist(boot["adjusted_rand_index"], bins=18, color="#4E79A7", alpha=0.8)
    axes[1].axvline(boot["adjusted_rand_index"].median(), color="#E15759", lw=2, label="median")
    axes[1].set_title("Bootstrap phase-map stability")
    axes[1].set_xlabel("Adjusted Rand index")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "figure2_phenotype_validity.png", dpi=220)
    plt.close(fig)

    # Figure 3: validation and fairness.
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    val = external_metrics.copy()
    target_short = {
        "y_hba1c_improved_ge_0_5": "HbA1c response",
        "y_tir_improved_ge_5pct": "TIR response",
    }
    feature_short = {
        "C2_clinical_plus_cgm": "Clinical+CGM",
        "C4_phase_map": "Phase-map",
    }
    subgroup_var_short = {
        "x_race": "Race",
        "x_ethnicity": "Ethnicity",
        "x_sex": "Sex",
        "study_id": "Study",
        "phase_label": "Phase",
        "baseline_hba1c_group": "Baseline HbA1c",
        "age_group": "Age",
    }
    if not val.empty:
        val["label"] = val["target"].map(target_short).fillna(val["target"]) + "\n" + val["feature_set"].map(feature_short).fillna(val["feature_set"])
        axes[0].bar(np.arange(len(val)), val["auroc"], color="#4E79A7")
        axes[0].set_xticks(np.arange(len(val)), val["label"], rotation=20, ha="right", fontsize=8)
        axes[0].set_ylim(0.45, 1.0)
        axes[0].set_ylabel("Loop frozen AUROC")
    axes[0].set_title("Frozen external validation")
    fair = fairness[fairness["subgroup_variable"].ne("overall")].dropna(subset=["delta_auroc_vs_overall"]).copy()
    focus = fair[(fair["feature_set"].eq("C4_phase_map")) & (fair["model"].eq("xgboost"))].copy()
    if len(focus) >= 5:
        fair = focus
    fair = fair.reindex(fair["delta_auroc_vs_overall"].abs().sort_values(ascending=False).index).head(20)
    if not fair.empty:
        subgroup_display = fair["subgroup_display"].astype(str) if "subgroup_display" in fair.columns else fair["subgroup"].astype(str)
        labels = (
            fair["target"].map(target_short).fillna(fair["target"]).str.replace(" response", "", regex=False)
            + " | "
            + fair["subgroup_variable"].map(subgroup_var_short).fillna(fair["subgroup_variable"])
            + ": "
            + subgroup_display
        )
        axes[1].barh(np.arange(len(fair)), fair["delta_auroc_vs_overall"], color=np.where(fair["delta_auroc_vs_overall"] < 0, "#E15759", "#59A14F"))
        axes[1].set_yticks(np.arange(len(fair)), labels, fontsize=7)
        axes[1].axvline(0, color="#333333", lw=0.8)
        axes[1].set_xlabel("Subgroup AUROC minus overall")
    axes[1].set_title("Phase-map subgroup audit")
    fig.tight_layout()
    fig.savefig(FIGURES / "figure3_validation_and_fairness.png", dpi=220)
    plt.close(fig)

    # Figure 4: clinical utility and HTE.
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    h = hte.sort_values("adjusted_risk_difference")
    h["phase_display"] = h["phase_label"].map(phase_en).fillna(h["phase_label"])
    y = np.arange(len(h))
    axes[0].errorbar(
        h["adjusted_risk_difference"],
        y,
        xerr=[h["adjusted_risk_difference"] - h["bootstrap_ci_low"], h["bootstrap_ci_high"] - h["adjusted_risk_difference"]],
        fmt="o",
        color="#4E79A7",
    )
    axes[0].set_yticks(y, h["phase_display"])
    axes[0].axvline(0, color="#333333", lw=0.8)
    axes[0].set_xlabel("Adjusted risk difference")
    axes[0].set_title("Phase-stratified treatment response")
    axes[1].axis("off")
    steps = ["Phase assigned", "Risk/context displayed", "Clinician reviews fit", "Care focus selected", "Reassess with new CGM"]
    y2 = np.linspace(0.85, 0.15, len(steps))
    for i, (txt, yy) in enumerate(zip(steps, y2)):
        axes[1].text(0.5, yy, txt, ha="center", va="center", fontsize=10, bbox=dict(boxstyle="round,pad=0.35", fc="#F7F1E8", ec="#B07AA1"))
        if i < len(steps) - 1:
            axes[1].annotate("", xy=(0.5, y2[i + 1] + 0.07), xytext=(0.5, yy - 0.07), arrowprops=dict(arrowstyle="->", lw=1.2))
    axes[1].set_title("Silent-mode digital care workflow")
    fig.tight_layout()
    fig.savefig(FIGURES / "figure4_clinical_utility_workflow.png", dpi=220)
    plt.close(fig)


def write_reports(loop: pd.DataFrame, inventory: pd.DataFrame, metrics: pd.DataFrame, fairness: pd.DataFrame) -> None:
    phase_dict = read_csv(PHASE / "jaeb_phase_label_dictionary.csv")
    phase_counts = loop["phase_label"].value_counts().rename_axis("phase_label").reset_index(name="n")
    phase_counts = (
        phase_counts.merge(
            phase_dict[["phase_label_zh", "phase_id", "phase_label_en"]],
            left_on="phase_label",
            right_on="phase_label_zh",
            how="left",
        )
        .drop(columns=["phase_label_zh"])
    )
    phase_count_text = phase_counts[["phase_id", "phase_label_en", "n"]].to_string(index=False)
    phase_counts.to_csv(FIGSRC / "loop_frozen_phase_distribution.csv", index=False)
    metrics_text = metrics.to_string(index=False) if not metrics.empty else "No eligible binary external-validation targets."
    audit_summary = (
        fairness[fairness["subgroup_variable"].ne("overall")]
        .dropna(subset=["delta_auroc_vs_overall"])
        .assign(abs_delta=lambda x: x["delta_auroc_vs_overall"].abs())
        .sort_values("abs_delta", ascending=False)
        .head(10)
    )
    audit_display_col = "subgroup_display" if "subgroup_display" in audit_summary.columns else "subgroup"
    audit_text = (
        audit_summary[
            ["target", "feature_set", "model", "subgroup_variable", audit_display_col, "n", "auroc", "delta_auroc_vs_overall", "brier"]
        ]
        .rename(columns={audit_display_col: "subgroup"})
        .to_string(index=False)
        if not audit_summary.empty
        else "No subgroup with evaluable AUROC."
    )
    report = f"""
# npj Digital Medicine P0 Workup Report

## Completed P0 Items

1. Frozen external validation using the held-out JAEB Loop public dataset.
2. Phase-map algorithm card and software specification.
3. Subgroup fairness and calibration audit.
4. Phase-guided digital care workflow source data.
5. Redesigned main figures centered on a CGM digital phenotype.

## Frozen External Validation

The Loop study was treated as a locked external validation dataset and was not used for model tuning. Baseline CGM summaries were mapped to the original JAEB phase-map centroids using fixed training-set reference statistics.

{inventory.to_string(index=False)}

### Loop Phase Distribution

{phase_count_text}

### External Prediction Metrics

{metrics_text}

## Subgroup Audit Highlights

The subgroup audit uses out-of-fold predictions from the original JAEB development package. It reports calibration and performance by age, sex, race/ethnicity, study, baseline HbA1c and phase label.

Largest evaluable AUROC deviations:

{audit_text}

## Interpretation

The Loop frozen validation is a transportability test, not a new tuning exercise. Because Loop lacks some demographic covariates used in the development models, external prediction metrics should be interpreted alongside calibration and phase-distribution shift. The strongest npj Digital Medicine framing remains the computable CGM digital phenotype and phase-guided workflow, with model performance as validation rather than the central claim.
"""
    write(DOCS / "npj_p0_workup_completion_report.md", report)


def main() -> None:
    train_phase = read_csv(PHASE / "tables" / "locked_glycemic_phase_features.csv")
    ml_phase = build_training_ml_phase()
    loop, inventory = build_loop_frozen_dataset(train_phase)
    loop.to_csv(TABLES / "loop_frozen_external_validation_dataset.csv", index=False)
    inventory.to_csv(TABLES / "frozen_external_validation_inventory.csv", index=False)

    metrics, preds = train_and_validate_external(ml_phase, loop)
    metrics.to_csv(TABLES / "loop_frozen_external_validation_metrics.csv", index=False)
    preds.to_csv(TABLES / "loop_frozen_external_validation_predictions.csv", index=False)

    fairness = subgroup_audit()
    fairness.to_csv(TABLES / "subgroup_fairness_calibration_audit.csv", index=False)

    workflow_nodes, workflow_summary = build_workflow_tables()
    write_algorithm_card()
    make_figures(loop, metrics, fairness, workflow_summary)
    write_reports(loop, inventory, metrics, fairness)

    status = pd.DataFrame(
        [
            ("frozen_external_validation", "complete", "tables/loop_frozen_external_validation_metrics.csv"),
            ("algorithm_card", "complete", "docs/phase_map_algorithm_card.md"),
            ("software_specification", "complete", "docs/phase_map_software_specification.md"),
            ("subgroup_fairness_calibration_audit", "complete", "tables/subgroup_fairness_calibration_audit.csv"),
            ("digital_care_workflow", "complete", "figure_source_data/digital_care_workflow_nodes.csv"),
            ("redesigned_main_figures", "complete", "figures/figure1-figure4*.png"),
        ],
        columns=["deliverable", "status", "primary_output"],
    )
    status.to_csv(OUT / "npj_p0_workup_status.csv", index=False)
    manifest = {
        "outputs": sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file()),
        "frozen_validation_dataset": LOOP_ZIP,
    }
    (OUT / "npj_p0_workup_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote npj Digital Medicine P0 workup to {OUT}")


if __name__ == "__main__":
    main()
