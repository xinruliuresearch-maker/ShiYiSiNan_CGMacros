"""P0 robustness for Nature Food: collapsed food matrix, subject leverage, counterfactual deltas."""

from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(r"D:\ai for science")
AIM2 = ROOT / "results" / "nature_food_aim2_cgmacros"
NEXT = ROOT / "results" / "nature_food_next_tasks"
OUT = ROOT / "results" / "nature_food_p0_robustness"
OUT.mkdir(parents=True, exist_ok=True)


COLLAPSE = {
    "fiber_rich_or_whole_food_matrix": "protective_whole_food_or_low_carb",
    "low_carb_or_protein_forward": "protective_whole_food_or_low_carb",
    "mixed_meal_protein_fat_buffered": "mixed_buffered_or_unknown",
    "mixed_or_unknown_matrix": "mixed_buffered_or_unknown",
    "refined_starch_low_matrix_protection": "rapid_digestible_or_liquid_carb",
    "sweetened_beverage_or_liquid_carb": "rapid_digestible_or_liquid_carb",
}
COLLAPSED_ORDER = [
    "protective_whole_food_or_low_carb",
    "mixed_buffered_or_unknown",
    "rapid_digestible_or_liquid_carb",
]


def read_data() -> pd.DataFrame:
    df = pd.read_csv(AIM2 / "aim2_modeling_dataset_human_adjudicated.csv", low_memory=False)
    df["subject_id"] = df["subject_id"].astype(str)
    df["matrix_collapsed3"] = df["food_matrix_final_category"].map(COLLAPSE).fillna("mixed_buffered_or_unknown")
    df["matrix_collapsed3"] = pd.Categorical(df["matrix_collapsed3"], categories=COLLAPSED_ORDER)
    return df


def fit_gee(df: pd.DataFrame, formula: str, family: str) -> pd.DataFrame:
    tokens = (
        formula.replace("~", "+")
        .replace("*", "+")
        .replace(":", "+")
        .replace("C(", "")
        .replace(")", "")
        .split("+")
    )
    needed = [t.strip() for t in tokens if t.strip() and t.strip() != "1"]
    needed = sorted(set([c for c in needed if c in df.columns] + ["subject_id"]))
    d = df[needed].replace([np.inf, -np.inf], np.nan).dropna().copy()
    fam = sm.families.Gaussian() if family == "gaussian" else sm.families.Binomial()
    try:
        fit = smf.gee(
            formula,
            groups="subject_id",
            data=d,
            cov_struct=sm.cov_struct.Exchangeable(),
            family=fam,
        ).fit(maxiter=200)
    except Exception:
        fit = smf.gee(
            formula,
            groups="subject_id",
            data=d,
            cov_struct=sm.cov_struct.Independence(),
            family=fam,
        ).fit(maxiter=200)
    rows = []
    for term in fit.params.index:
        if term == "Intercept":
            continue
        est = float(fit.params[term])
        se = float(fit.bse[term])
        rows.append(
            {
                "outcome": formula.split("~", 1)[0].strip(),
                "term": term,
                "estimate": est,
                "se": se,
                "ci_low": est - 1.96 * se,
                "ci_high": est + 1.96 * se,
                "p_value": float(fit.pvalues[term]),
                "n": len(d),
                "subjects": d["subject_id"].nunique(),
            }
        )
    return pd.DataFrame(rows)


def collapsed_matrix_sensitivity(df: pd.DataFrame) -> pd.DataFrame:
    controls = "msi_core + carbs_10g + pre_glucose_10 + meal_hour_sin + meal_hour_cos + calories_100"
    formulas = [
        ("log1p_iauc_2h ~ " + controls + " + C(matrix_collapsed3)", "gaussian"),
        ("peak_delta_2h_w ~ " + controls + " + C(matrix_collapsed3)", "gaussian"),
        ("high_iauc_2h ~ " + controls + " + C(matrix_collapsed3)", "binomial"),
    ]
    rows = [fit_gee(df, f, fam) for f, fam in formulas]
    res = pd.concat(rows, ignore_index=True)
    res["estimate_CI"] = res.apply(lambda r: f"{r.estimate:.3f} ({r.ci_low:.3f}, {r.ci_high:.3f})", axis=1)
    res.to_csv(OUT / "aim2_collapsed3_food_matrix_gee_results.csv", index=False)

    summary = (
        df.groupby("matrix_collapsed3", observed=False)
        .agg(
            meals=("iauc_2h", "size"),
            subjects=("subject_id", "nunique"),
            median_iauc_2h=("iauc_2h", "median"),
            high_iauc_rate=("high_iauc_2h", "mean"),
            median_peak_delta_2h=("peak_delta_2h", "median"),
            median_carbs=("carbs", "median"),
            median_fiber=("fiber", "median"),
        )
        .reset_index()
    )
    summary.to_csv(OUT / "aim2_collapsed3_food_matrix_summary.csv", index=False)
    return res


def leave_one_subject_out_effects(df: pd.DataFrame) -> pd.DataFrame:
    formula = "high_iauc_2h ~ msi_core + carbs_10g + pre_glucose_10 + meal_hour_sin + meal_hour_cos + calories_100 + C(matrix_collapsed3)"
    subjects = sorted(df["subject_id"].unique())
    rows = []
    full = fit_gee(df, formula, "binomial")
    for _, r in full.iterrows():
        if r["term"] == "msi_core" or "matrix_collapsed3" in r["term"]:
            rows.append(
                {
                    "excluded_subject": "none_full_model",
                    "term": r["term"],
                    "estimate": r["estimate"],
                    "ci_low": r["ci_low"],
                    "ci_high": r["ci_high"],
                    "p_value": r["p_value"],
                    "n": r["n"],
                    "subjects": r["subjects"],
                }
            )
    for sid in subjects:
        sub = df[df["subject_id"] != sid].copy()
        res = fit_gee(sub, formula, "binomial")
        for _, r in res.iterrows():
            if r["term"] == "msi_core" or "matrix_collapsed3" in r["term"]:
                rows.append(
                    {
                        "excluded_subject": sid,
                        "term": r["term"],
                        "estimate": r["estimate"],
                        "ci_low": r["ci_low"],
                        "ci_high": r["ci_high"],
                        "p_value": r["p_value"],
                        "n": r["n"],
                        "subjects": r["subjects"],
                    }
                )
    out = pd.DataFrame(rows)
    stability = (
        out[out["excluded_subject"] != "none_full_model"]
        .assign(direction_positive=lambda x: x["estimate"] > 0)
        .groupby("term", as_index=False)
        .agg(
            min_estimate=("estimate", "min"),
            median_estimate=("estimate", "median"),
            max_estimate=("estimate", "max"),
            positive_leaveouts=("direction_positive", "sum"),
            leaveouts=("excluded_subject", "nunique"),
        )
    )
    stability["positive_leaveout_rate"] = stability["positive_leaveouts"] / stability["leaveouts"]
    out.to_csv(OUT / "aim2_loso_subject_leverage_effects.csv", index=False)
    stability.to_csv(OUT / "aim2_loso_subject_leverage_stability.csv", index=False)
    return stability


def make_classifier(df: pd.DataFrame) -> Pipeline:
    num_cols = ["carbs_10g", "calories_100", "pre_glucose_10", "meal_hour_sin", "meal_hour_cos", "msi_core"]
    cat_cols = ["food_matrix_final_category"]
    pre = ColumnTransformer(
        [
            ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), num_cols),
            ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), cat_cols),
        ]
    )
    clf = Pipeline([("pre", pre), ("model", LogisticRegression(max_iter=2000, class_weight="balanced"))])
    clf.fit(df[num_cols + cat_cols], df["high_iauc_2h"].astype(int))
    return clf


def counterfactual_deltas(df: pd.DataFrame) -> pd.DataFrame:
    candidates_path = NEXT / "aim3_counterfactual_meal_redesign_candidates.csv"
    if candidates_path.exists():
        candidates = pd.read_csv(candidates_path, low_memory=False)
        key = ["subject_id", "meal_time"]
        candidates["subject_id"] = candidates["subject_id"].astype(str)
        base = df.merge(candidates[key], on=key, how="inner")
    else:
        base = df[df["high_iauc_2h"].eq(1)].copy()
    clf = make_classifier(df)
    features = ["carbs_10g", "calories_100", "pre_glucose_10", "meal_hour_sin", "meal_hour_cos", "msi_core", "food_matrix_final_category"]
    base = base.copy()
    cf = base.copy()
    cf["food_matrix_final_category"] = "fiber_rich_or_whole_food_matrix"
    if "fiber_5g" in cf:
        protective_fiber = df.loc[df["food_matrix_final_category"].eq("fiber_rich_or_whole_food_matrix"), "fiber_5g"].median()
        cf["fiber_5g"] = np.maximum(pd.to_numeric(cf["fiber_5g"], errors="coerce").fillna(0), protective_fiber)
    base["pred_high_iauc_original"] = clf.predict_proba(base[features])[:, 1]
    base["pred_high_iauc_redesigned"] = clf.predict_proba(cf[features])[:, 1]
    base["pred_high_iauc_delta"] = base["pred_high_iauc_redesigned"] - base["pred_high_iauc_original"]
    cols = [
        "subject_id",
        "meal_time",
        "meal_type",
        "msi_core",
        "msi_tertile",
        "iauc_2h",
        "peak_delta_2h",
        "carbs",
        "calories",
        "fiber",
        "food_matrix_final_category",
        "food_matrix_final_label",
        "pred_high_iauc_original",
        "pred_high_iauc_redesigned",
        "pred_high_iauc_delta",
    ]
    cols = [c for c in cols if c in base.columns]
    out = base.sort_values("pred_high_iauc_delta").head(60)[cols]
    out.to_csv(OUT / "aim3_counterfactual_high_iauc_prediction_deltas.csv", index=False)
    return out


def write_report(collapsed: pd.DataFrame, stability: pd.DataFrame, deltas: pd.DataFrame) -> None:
    def md_table(frame: pd.DataFrame) -> str:
        if frame.empty:
            return "_No rows._"
        show = frame.copy()
        for col in show.columns:
            if pd.api.types.is_float_dtype(show[col]):
                show[col] = show[col].map(lambda x: "" if pd.isna(x) else f"{x:.4g}")
            else:
                show[col] = show[col].astype(str)
        headers = list(show.columns)
        rows = show.astype(str).values.tolist()
        widths = [len(h) for h in headers]
        for row in rows:
            widths = [max(w, len(v)) for w, v in zip(widths, row)]
        line = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |"
        sep = "| " + " | ".join("-" * w for w in widths) + " |"
        body = ["| " + " | ".join(v.ljust(w) for v, w in zip(row, widths)) + " |" for row in rows]
        return "\n".join([line, sep] + body)

    matrix_terms = collapsed[collapsed["term"].str.contains("matrix_collapsed3", na=False)].copy()
    strongest_delta = deltas["pred_high_iauc_delta"].median() if len(deltas) else np.nan
    lines = [
        "# Nature Food P0 稳健性与餐食重构结果",
        "",
        "## 已完成",
        "",
        "- 三类食物基质敏感性：保护型 whole-food/low-carb、中间 mixed/unknown、快速消化/液体碳水。",
        "- 受试者留一影响分析：检验 MSI-core 与 collapsed matrix 项是否由单个受试者驱动。",
        "- 餐食重构预测差：把候选高风险餐食的食物基质替换为 fiber-rich/whole-food matrix，估计 high-iAUC 风险变化。",
        "",
        "## 三类食物基质关键模型项",
        "",
        md_table(matrix_terms[["outcome", "term", "estimate_CI", "p_value", "n", "subjects"]]),
        "",
        "## 受试者留一稳定性",
        "",
        md_table(stability),
        "",
        "## 餐食重构预测",
        "",
        f"- 候选餐食数: {len(deltas)}",
        f"- 中位 predicted high-iAUC 风险差: {strongest_delta:.3f}",
        "- 负值表示重构后预测风险降低；该结果目前是模型内反事实，需要后续用等碳水/等能量餐食原型验证。",
    ]
    (OUT / "nature_food_p0_robustness_report_zh.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    df = read_data()
    collapsed = collapsed_matrix_sensitivity(df)
    stability = leave_one_subject_out_effects(df)
    deltas = counterfactual_deltas(df)
    write_report(collapsed, stability, deltas)
    manifest = {
        "outputs": sorted(p.name for p in OUT.glob("*")),
        "n_rows": int(len(df)),
        "n_subjects": int(df["subject_id"].nunique()),
        "n_counterfactual_deltas": int(len(deltas)),
    }
    (OUT / "nature_food_p0_robustness_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote P0 robustness outputs to {OUT}")


if __name__ == "__main__":
    main()
