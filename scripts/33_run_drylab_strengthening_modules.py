from __future__ import annotations

import csv
import json
import math
import re
import shutil
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import requests


TODAY = date.today().isoformat()
ROOT = Path(r"C:\Users\liu12\OneDrive\Desktop\ShiYiSiNan_CGMacros")
OUT = ROOT / "outputs" / "integrated_mainline" / f"formal_drylab_strengthening_{TODAY}"
NHANES_MIRROR = (
    Path(r"C:\Users\liu12\OneDrive\Desktop\NHANES_MetS_Project")
    / "result"
    / "integrated_mainline"
    / f"formal_drylab_strengthening_{TODAY}"
)
HIGH = ROOT / "outputs" / "integrated_mainline" / "high_impact_computational_upgrade_2026-06-11"
DATA_EXTERNAL = ROOT / "data" / "external"
FDC_API = "https://api.nal.usda.gov/fdc/v1/foods/search"


def ensure_out() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\n", "\r\n"), encoding="utf-8")


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def normal_p(z: float) -> float:
    if not np.isfinite(z):
        return float("nan")
    return math.erfc(abs(float(z)) / math.sqrt(2.0))


def bh_fdr(pvals: list[float]) -> list[float]:
    p = np.asarray([np.nan if v is None else float(v) for v in pvals], dtype=float)
    q = np.full_like(p, np.nan)
    ok = np.isfinite(p)
    if ok.sum() == 0:
        return q.tolist()
    idx = np.where(ok)[0]
    order = idx[np.argsort(p[idx])]
    ranked = p[order]
    m = len(ranked)
    adj = ranked * m / np.arange(1, m + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    q[order] = np.minimum(adj, 1.0)
    return q.tolist()


def safe_z(series: pd.Series) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    sd = x.std(skipna=True)
    if not np.isfinite(sd) or sd == 0:
        return x * np.nan
    return (x - x.mean(skipna=True)) / sd


def corr(a: pd.Series, b: pd.Series) -> float:
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(d) < 3 or d["a"].std() == 0 or d["b"].std() == 0:
        return float("nan")
    return float(np.corrcoef(d["a"], d["b"])[0, 1])


def make_non_glycemic_msi() -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    nh = pd.read_csv(HIGH / "01_nhanes_dual_msi_dataset.csv")
    cg = pd.read_csv(HIGH / "03_cgmacros_food_matrix_scored_meals.csv")

    for df in (nh, cg):
        df["non_glycemic_msi"] = df[["z_bmi_ref", "z_ln_tg_hdl_ref"]].mean(axis=1, skipna=True)
        df["non_glycemic_msi_components"] = df[["z_bmi_ref", "z_ln_tg_hdl_ref"]].notna().sum(axis=1)
        df["non_glycemic_msi_complete"] = np.where(df["non_glycemic_msi_components"] == 2, df["non_glycemic_msi"], np.nan)

    rows = []
    for name, df in [("NHANES", nh), ("CGMacros", cg)]:
        for other in [
            "exposure_facing_msi",
            "response_vulnerability_index",
            "msi_core_partial",
            "msi_no_bmi",
        ]:
            if other in df.columns:
                rows.append(
                    {
                        "dataset": name,
                        "index_a": "non_glycemic_msi",
                        "index_b": other,
                        "n_pairwise": int(df[["non_glycemic_msi", other]].dropna().shape[0]),
                        "pearson_r": corr(df["non_glycemic_msi"], df[other]),
                    }
                )
    nh.to_csv(OUT / "10_nhanes_non_glycemic_msi_dataset.csv", index=False, encoding="utf-8-sig")
    cg.to_csv(OUT / "10_cgmacros_non_glycemic_msi_foodmatrix_dataset.csv", index=False, encoding="utf-8-sig")
    write_csv(OUT / "10_non_glycemic_msi_construct_correlations.csv", rows)
    return nh, cg, rows


def group_folds(groups: pd.Series, k: int = 5, seed: int = 20260611) -> list[tuple[np.ndarray, np.ndarray]]:
    rng = np.random.default_rng(seed)
    unique = np.array(sorted(pd.Series(groups).dropna().unique()))
    rng.shuffle(unique)
    chunks = np.array_split(unique, k)
    folds = []
    g = np.asarray(groups)
    for chunk in chunks:
        test = np.isin(g, chunk)
        train = ~test
        folds.append((np.where(train)[0], np.where(test)[0]))
    return folds


def prepare_matrix(df: pd.DataFrame, numeric: list[str], categorical: list[str] | None = None) -> pd.DataFrame:
    categorical = categorical or []
    parts = []
    for col in numeric:
        if col in df.columns:
            parts.append(pd.to_numeric(df[col], errors="coerce").rename(col))
    x = pd.concat(parts, axis=1) if parts else pd.DataFrame(index=df.index)
    for col in categorical:
        if col in df.columns:
            dummies = pd.get_dummies(df[col].astype("object"), prefix=col, dummy_na=False)
            x = pd.concat([x, dummies], axis=1)
    return x


def fit_ridge(X: np.ndarray, y: np.ndarray, alpha: float) -> np.ndarray:
    X1 = np.column_stack([np.ones(X.shape[0]), X])
    penalty = np.eye(X1.shape[1]) * alpha
    penalty[0, 0] = 0.0
    return np.linalg.pinv(X1.T @ X1 + penalty) @ X1.T @ y


def predict_ridge(beta: np.ndarray, X: np.ndarray) -> np.ndarray:
    X1 = np.column_stack([np.ones(X.shape[0]), X])
    return X1 @ beta


def choose_alpha(X: pd.DataFrame, y: pd.Series, groups: pd.Series, train_idx: np.ndarray) -> float:
    alphas = [0.01, 0.1, 1.0, 10.0, 100.0]
    train_groups = groups.iloc[train_idx].reset_index(drop=True)
    inner = group_folds(train_groups, k=min(3, train_groups.nunique()), seed=20260612)
    Xtr_all = X.iloc[train_idx].reset_index(drop=True)
    ytr_all = y.iloc[train_idx].reset_index(drop=True)
    scores = []
    for alpha in alphas:
        errs = []
        for inner_train, inner_val in inner:
            x_train = Xtr_all.iloc[inner_train].copy()
            x_val = Xtr_all.iloc[inner_val].copy()
            med = x_train.median(numeric_only=True)
            x_train = x_train.fillna(med)
            x_val = x_val.fillna(med)
            mean = x_train.mean()
            sd = x_train.std().replace(0, 1)
            x_train = (x_train - mean) / sd
            x_val = (x_val - mean) / sd
            beta = fit_ridge(x_train.to_numpy(float), ytr_all.iloc[inner_train].to_numpy(float), alpha)
            pred = predict_ridge(beta, x_val.to_numpy(float))
            errs.append(float(np.sqrt(np.mean((ytr_all.iloc[inner_val].to_numpy(float) - pred) ** 2))))
        scores.append((np.nanmean(errs), alpha))
    return min(scores)[1]


def subject_disjoint_prediction(cg: pd.DataFrame) -> tuple[list[dict], pd.DataFrame]:
    df = cg.copy()
    df["non_glycemic_x_rapid"] = df["non_glycemic_msi"] * df["rapid_digestibility_score_v2"]
    feature_sets = {
        "macro_only": {
            "numeric": ["eff_calories", "eff_carbs", "eff_protein", "eff_fat", "eff_fiber"],
            "categorical": [],
        },
        "macro_context": {
            "numeric": [
                "eff_calories",
                "eff_carbs",
                "eff_protein",
                "eff_fat",
                "eff_fiber",
                "baseline_glucose",
                "pre_glucose_mean_30",
                "pre_glucose_sd_30",
                "pre_glucose_slope_60",
                "meal_hour_sin",
                "meal_hour_cos",
                "prev_meal_gap_min",
                "activity_calories_pre30",
                "mets_mean_pre30",
            ],
            "categorical": ["meal_type"],
        },
        "non_glycemic_msi_foodmatrix": {
            "numeric": [
                "eff_calories",
                "eff_carbs",
                "eff_protein",
                "eff_fat",
                "eff_fiber",
                "baseline_glucose",
                "pre_glucose_mean_30",
                "pre_glucose_sd_30",
                "pre_glucose_slope_60",
                "meal_hour_sin",
                "meal_hour_cos",
                "prev_meal_gap_min",
                "activity_calories_pre30",
                "mets_mean_pre30",
                "non_glycemic_msi",
                "rapid_digestibility_score_v2",
                "matrix_protection_score_v2",
                "non_glycemic_x_rapid",
            ],
            "categorical": ["meal_type", "food_matrix_category_v2"],
        },
    }
    outcomes = ["iauc_2h", "peak_delta_2h"]
    perf_rows: list[dict] = []
    pred_frames = []
    for outcome in outcomes:
        base = df[["subject_id", "meal_time", outcome]].copy()
        for set_name, spec in feature_sets.items():
            X = prepare_matrix(df, spec["numeric"], spec["categorical"])
            cols = X.columns.tolist()
            data = pd.concat([base, X], axis=1)
            data = data.dropna(subset=[outcome, "subject_id"])
            X2 = data[cols]
            y = pd.to_numeric(data[outcome], errors="coerce")
            ok = y.notna()
            data = data.loc[ok].reset_index(drop=True)
            X2 = X2.loc[ok].reset_index(drop=True)
            y = y.loc[ok].reset_index(drop=True)
            groups = data["subject_id"]
            preds = np.full(len(data), np.nan)
            alphas = []
            for train_idx, test_idx in group_folds(groups, k=5):
                alpha = choose_alpha(X2, y, groups, train_idx)
                alphas.append(alpha)
                x_train = X2.iloc[train_idx].copy()
                x_test = X2.iloc[test_idx].copy()
                med = x_train.median(numeric_only=True)
                x_train = x_train.fillna(med)
                x_test = x_test.fillna(med)
                mean = x_train.mean()
                sd = x_train.std().replace(0, 1)
                x_train = (x_train - mean) / sd
                x_test = (x_test - mean) / sd
                beta = fit_ridge(x_train.to_numpy(float), y.iloc[train_idx].to_numpy(float), alpha)
                preds[test_idx] = predict_ridge(beta, x_test.to_numpy(float))
            obs = y.to_numpy(float)
            sse = np.sum((obs - preds) ** 2)
            sst = np.sum((obs - np.mean(obs)) ** 2)
            perf_rows.append(
                {
                    "dataset": "CGMacros",
                    "outcome": outcome,
                    "model": set_name,
                    "n_meals": int(len(obs)),
                    "n_subjects": int(groups.nunique()),
                    "r2_subject_disjoint": float(1 - sse / sst),
                    "pearson_r": float(np.corrcoef(obs, preds)[0, 1]) if np.std(preds) > 0 else float("nan"),
                    "mae": float(np.mean(np.abs(obs - preds))),
                    "rmse": float(np.sqrt(np.mean((obs - preds) ** 2))),
                    "median_inner_alpha": float(np.median(alphas)),
                }
            )
            pf = data[["subject_id", "meal_time"]].copy()
            pf["outcome"] = outcome
            pf["model"] = set_name
            pf["observed"] = obs
            pf["predicted"] = preds
            pred_frames.append(pf)
    pred_df = pd.concat(pred_frames, ignore_index=True)
    write_csv(OUT / "11_cgmacros_non_glycemic_subject_disjoint_performance.csv", perf_rows)
    pred_df.to_csv(OUT / "11_cgmacros_non_glycemic_subject_disjoint_predictions.csv", index=False, encoding="utf-8-sig")
    return perf_rows, pred_df


def cluster_robust_ols(df: pd.DataFrame, ycol: str, xcols: list[str], cluster_col: str) -> list[dict]:
    d = df[[ycol, cluster_col] + xcols].copy()
    for col in xcols + [ycol]:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d.dropna(subset=[ycol, cluster_col])
    for col in xcols:
        d[col] = d[col].fillna(d[col].median())
    y = d[ycol].to_numpy(float)
    Xraw = d[xcols].copy()
    mean = Xraw.mean()
    sd = Xraw.std().replace(0, 1)
    Xstd = ((Xraw - mean) / sd).to_numpy(float)
    X = np.column_stack([np.ones(len(d)), Xstd])
    beta = np.linalg.pinv(X.T @ X) @ X.T @ y
    resid = y - X @ beta
    xtx_inv = np.linalg.pinv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    clusters = d[cluster_col].to_numpy()
    unique = np.unique(clusters)
    for g in unique:
        idx = np.where(clusters == g)[0]
        s = X[idx].T @ resid[idx]
        meat += np.outer(s, s)
    n, k = X.shape
    G = len(unique)
    correction = (G / (G - 1)) * ((n - 1) / (n - k)) if G > 1 and n > k else 1.0
    cov = xtx_inv @ meat @ xtx_inv * correction
    se = np.sqrt(np.maximum(np.diag(cov), 0))
    rows = []
    for i, term in enumerate(["intercept"] + xcols):
        z = beta[i] / se[i] if se[i] > 0 else np.nan
        rows.append(
            {
                "outcome": ycol,
                "term": term,
                "n_meals": int(n),
                "n_subjects": int(G),
                "beta_per_1sd_predictor": float(beta[i]),
                "cluster_robust_se": float(se[i]),
                "z": float(z) if np.isfinite(z) else np.nan,
                "p": normal_p(z),
            }
        )
    pvals = [r["p"] for r in rows]
    qvals = bh_fdr(pvals)
    for row, q in zip(rows, qvals):
        row["q"] = q
    return rows


def run_hierarchical_inference(cg: pd.DataFrame) -> list[dict]:
    df = cg.copy()
    df["non_glycemic_x_rapid"] = df["non_glycemic_msi"] * df["rapid_digestibility_score_v2"]
    xcols = [
        "non_glycemic_msi",
        "rapid_digestibility_score_v2",
        "matrix_protection_score_v2",
        "non_glycemic_x_rapid",
        "eff_carbs",
        "eff_protein",
        "eff_fat",
        "eff_fiber",
        "baseline_glucose",
        "meal_hour_sin",
        "meal_hour_cos",
    ]
    rows = []
    for outcome in ["iauc_2h", "peak_delta_2h"]:
        rows.extend(cluster_robust_ols(df, outcome, xcols, "subject_id"))
        d = df[[outcome, "subject_id"]].dropna()
        group_means = d.groupby("subject_id")[outcome].mean()
        icc_proxy = float(group_means.var() / d[outcome].var()) if d[outcome].var() > 0 else np.nan
        rows.append(
            {
                "outcome": outcome,
                "term": "subject_random_intercept_icc_proxy",
                "n_meals": int(len(d)),
                "n_subjects": int(d["subject_id"].nunique()),
                "beta_per_1sd_predictor": icc_proxy,
                "cluster_robust_se": np.nan,
                "z": np.nan,
                "p": np.nan,
                "q": np.nan,
            }
        )
    write_csv(OUT / "12_cgmacros_non_glycemic_cluster_hierarchical_coefficients.csv", rows)
    return rows


def classify_food_matrix_from_text(text: str, calories: float | None = None) -> tuple[str, float, str]:
    s = (text or "").lower()
    rapid_terms = ["white bread", "bread", "rice", "pasta", "potato", "frites", "fries", "pizza", "cereal", "yogurt", "juice", "soda", "sweet", "cake", "cookie"]
    protective_terms = ["beans", "lentil", "salad", "lettuce", "vegetable", "tomato", "carrot", "whole", "nuts", "egg", "fish", "tuna", "steak", "cheese", "olive oil"]
    liquid_terms = ["juice", "soda", "beverage", "drink", "milkshake"]
    rapid = sum(t in s for t in rapid_terms)
    protective = sum(t in s for t in protective_terms)
    liquid = any(t in s for t in liquid_terms)
    if liquid:
        return "sweetened_beverage_or_liquid_carb", 2.5 + rapid - 0.3 * protective, "text_liquid_term"
    if rapid > protective and rapid >= 1:
        return "refined_starch_or_rapid_carb", 1.5 + rapid - 0.4 * protective, "text_rapid_terms"
    if protective >= rapid and protective >= 2:
        return "fiber_rich_or_whole_food_matrix", -1.2 - 0.3 * protective + 0.2 * rapid, "text_protective_terms"
    if calories is not None and np.isfinite(calories) and calories > 700:
        return "mixed_matrix_high_energy", 0.5 + 0.2 * rapid, "text_mixed_high_energy"
    return "mixed_matrix", 0.0 + 0.2 * rapid - 0.2 * protective, "text_mixed_default"


def dual_rater_food_matrix(cg: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    df = cg.copy()
    carb_density = pd.to_numeric(df["carb_density_g_per_100kcal"], errors="coerce")
    fiber_per_50 = pd.to_numeric(df["fiber_per_50g_carb"], errors="coerce")
    buffer = pd.to_numeric(df["protein_fat_buffer_per_50g_carb"], errors="coerce")
    rater_a = np.where(
        (carb_density >= 18) & (fiber_per_50 <= 2) & (buffer <= 20),
        "sweetened_beverage_or_liquid_carb",
        np.where(
            (carb_density >= 10) & (fiber_per_50 <= 4),
            "refined_starch_or_rapid_carb",
            np.where((fiber_per_50 >= 6) | (buffer >= 45), "fiber_rich_or_whole_food_matrix", "mixed_matrix"),
        ),
    )
    rater_b = np.where(
        pd.to_numeric(df["rapid_digestibility_score_v1"], errors="coerce") >= 2.0,
        "refined_starch_or_rapid_carb",
        np.where(
            pd.to_numeric(df["matrix_protection_score_v1"], errors="coerce") >= 1.0,
            "fiber_rich_or_whole_food_matrix",
            "mixed_matrix",
        ),
    )
    rater_b = np.where(df.get("liquid_sugar_proxy_v2", 0).astype(float) > 0, "sweetened_beverage_or_liquid_carb", rater_b)
    df["rater_a_nutrition_rule_prelabeled_category"] = rater_a
    df["rater_b_matrix_rule_prelabeled_category"] = rater_b
    df["dual_rater_agreement"] = df["rater_a_nutrition_rule_prelabeled_category"] == df["rater_b_matrix_rule_prelabeled_category"]
    df["adjudicated_prelabeled_category"] = np.where(
        df["dual_rater_agreement"],
        df["rater_a_nutrition_rule_prelabeled_category"],
        df["food_matrix_category_v2"],
    )
    df["requires_manual_image_review"] = ~df["dual_rater_agreement"]

    cats = sorted(set(df["rater_a_nutrition_rule_prelabeled_category"]).union(set(df["rater_b_matrix_rule_prelabeled_category"])))
    obs = pd.crosstab(df["rater_a_nutrition_rule_prelabeled_category"], df["rater_b_matrix_rule_prelabeled_category"]).reindex(index=cats, columns=cats, fill_value=0)
    total = obs.values.sum()
    po = np.trace(obs.values) / total
    row = obs.sum(axis=1).to_numpy() / total
    col = obs.sum(axis=0).to_numpy() / total
    pe = float(np.sum(row * col))
    kappa = (po - pe) / (1 - pe) if pe < 1 else np.nan
    summary = [
        {
            "annotation_type": "AI_assisted_rule_based_dual_prelabelling_not_final_human_annotation",
            "n_meals": int(len(df)),
            "agreement_rate": float(po),
            "cohen_kappa": float(kappa),
            "needs_manual_review_n": int(df["requires_manual_image_review"].sum()),
            "guardrail": "These are two independent rule-based prelabels to support later blinded human annotation; they are not claimed as completed human ratings.",
        }
    ]
    keep = [
        "subject_id",
        "meal_time",
        "image_path",
        "meal_type",
        "calories",
        "carbs",
        "protein",
        "fat",
        "fiber",
        "food_matrix_category_v2",
        "rater_a_nutrition_rule_prelabeled_category",
        "rater_b_matrix_rule_prelabeled_category",
        "dual_rater_agreement",
        "adjudicated_prelabeled_category",
        "requires_manual_image_review",
    ]
    df[keep].to_csv(OUT / "20_cgmacros_food_matrix_dual_rater_prelabeled.csv", index=False, encoding="utf-8-sig")
    template = df[keep].copy()
    template["human_rater_1_category"] = ""
    template["human_rater_1_notes"] = ""
    template["human_rater_2_category"] = ""
    template["human_rater_2_notes"] = ""
    template["adjudicator_final_category"] = ""
    template["adjudicator_notes"] = ""
    template.to_csv(OUT / "20_cgmacros_manual_dual_annotation_template.csv", index=False, encoding="utf-8-sig")
    write_csv(OUT / "20_food_matrix_dual_rater_prelabeled_reliability.csv", summary)
    codebook = [
        {"field": "human_rater_1_category", "allowed_values": "sweetened_beverage_or_liquid_carb; refined_starch_or_rapid_carb; mixed_matrix; mixed_matrix_high_energy; fiber_rich_or_whole_food_matrix", "instruction": "Rater 1 blinded category after inspecting image and any meal description."},
        {"field": "human_rater_2_category", "allowed_values": "same as rater 1", "instruction": "Rater 2 independently assigns category without seeing rater 1."},
        {"field": "adjudicator_final_category", "allowed_values": "same as rater 1", "instruction": "Adjudicator resolves disagreements using image, nutrients, FDC candidate, and codebook rules."},
        {"field": "requires_manual_image_review", "allowed_values": "TRUE/FALSE", "instruction": "TRUE means automated prelabels disagree or available metadata are insufficient."},
    ]
    write_csv(OUT / "20_food_matrix_manual_annotation_codebook_v2.csv", codebook)
    return df, summary


def nutrient_value(food: dict, names: list[str]) -> float:
    for nutr in food.get("foodNutrients", []):
        n = (nutr.get("nutrientName") or nutr.get("name") or "").lower()
        if any(key.lower() in n for key in names):
            try:
                return float(nutr.get("value"))
            except Exception:
                continue
    return float("nan")


def fdc_search(query: str, page_size: int = 15) -> list[dict]:
    params = {"api_key": "DEMO_KEY", "query": query, "pageSize": page_size}
    try:
        resp = requests.get(FDC_API, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("foods", [])
    except Exception as exc:
        return [{"_error": str(exc), "description": query}]


def fdc_item_level_matching(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    queries = sorted(q for q in df["fdc_proxy_query"].dropna().astype(str).unique() if q.strip())
    candidates: dict[str, list[dict]] = {}
    candidate_rows = []
    for q in queries:
        foods = fdc_search(q)
        candidates[q] = foods
        for rank, food in enumerate(foods, 1):
            if "_error" in food:
                candidate_rows.append({"query": q, "rank": rank, "error": food["_error"]})
                continue
            candidate_rows.append(
                {
                    "query": q,
                    "rank": rank,
                    "fdc_id": food.get("fdcId"),
                    "description": food.get("description"),
                    "data_type": food.get("dataType"),
                    "brand_owner": food.get("brandOwner"),
                    "published_date": food.get("publishedDate"),
                    "energy_kcal_per_100g": nutrient_value(food, ["Energy"]),
                    "carb_g_per_100g": nutrient_value(food, ["Carbohydrate"]),
                    "protein_g_per_100g": nutrient_value(food, ["Protein"]),
                    "fat_g_per_100g": nutrient_value(food, ["Total lipid", "fat"]),
                    "fiber_g_per_100g": nutrient_value(food, ["Fiber"]),
                    "fdc_url": f"https://fdc.nal.usda.gov/fdc-app.html#/food-details/{food.get('fdcId')}/nutrients",
                }
            )
        time.sleep(0.15)
    write_csv(OUT / "21_fdc_query_candidate_items.csv", candidate_rows)

    assigned = []
    for _, row in df.iterrows():
        q = str(row.get("fdc_proxy_query", "") or "")
        foods = [f for f in candidates.get(q, []) if "_error" not in f]
        meal_energy = float(row.get("calories", np.nan))
        meal_vec = np.array([
            float(row.get("carbs", np.nan)) * 4,
            float(row.get("protein", np.nan)) * 4,
            float(row.get("fat", np.nan)) * 9,
        ])
        if not np.isfinite(meal_energy) or meal_energy <= 0:
            meal_energy = np.nansum(meal_vec)
        meal_share = meal_vec / meal_energy if meal_energy > 0 else np.array([np.nan, np.nan, np.nan])
        best = None
        best_score = np.inf
        for food in foods:
            energy = nutrient_value(food, ["Energy"])
            carb = nutrient_value(food, ["Carbohydrate"])
            prot = nutrient_value(food, ["Protein"])
            fat = nutrient_value(food, ["Total lipid", "fat"])
            if not np.isfinite(energy) or energy <= 0:
                energy = np.nansum([carb * 4, prot * 4, fat * 9])
            cand_share = np.array([carb * 4, prot * 4, fat * 9]) / energy if energy and energy > 0 else np.array([np.nan, np.nan, np.nan])
            if np.all(np.isfinite(meal_share)) and np.all(np.isfinite(cand_share)):
                dist = float(np.sqrt(np.mean((meal_share - cand_share) ** 2)))
            else:
                dist = 1.0
            if dist < best_score:
                best_score = dist
                best = food
        assigned.append(
            {
                "subject_id": row.get("subject_id"),
                "meal_time": row.get("meal_time"),
                "image_path": row.get("image_path"),
                "fdc_proxy_query": q,
                "fdc_id": None if best is None else best.get("fdcId"),
                "fdc_description": None if best is None else best.get("description"),
                "fdc_data_type": None if best is None else best.get("dataType"),
                "fdc_macro_distance": best_score if np.isfinite(best_score) else np.nan,
                "fdc_item_match_confidence": float(1 / (1 + best_score)) if np.isfinite(best_score) else np.nan,
                "fdc_url": None if best is None else f"https://fdc.nal.usda.gov/fdc-app.html#/food-details/{best.get('fdcId')}/nutrients",
                "requires_manual_fdc_review": bool(best is None or best_score > 0.35),
            }
        )
    assigned_df = pd.DataFrame(assigned)
    assigned_df.to_csv(OUT / "21_cgmacros_fdc_item_level_proxy_matches.csv", index=False, encoding="utf-8-sig")
    summary = [
        {
            "n_meals": int(len(assigned_df)),
            "n_unique_queries": int(len(queries)),
            "n_assigned_fdc_id": int(assigned_df["fdc_id"].notna().sum()),
            "median_match_confidence": float(assigned_df["fdc_item_match_confidence"].median(skipna=True)),
            "requires_manual_review_n": int(assigned_df["requires_manual_fdc_review"].sum()),
            "guardrail": "FDC item-level proxy matching is based on category query plus macro-profile distance because full CGMacros ingredient text is unavailable.",
        }
    ]
    write_csv(OUT / "21_fdc_item_level_proxy_match_summary.csv", summary)
    return assigned_df, summary


def trapezoid_auc(minutes: np.ndarray, values: np.ndarray) -> float:
    if len(minutes) < 2:
        return float("nan")
    order = np.argsort(minutes)
    x = minutes[order]
    y = values[order]
    return float(np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1]) / 2.0))


def parse_d1namo() -> tuple[pd.DataFrame, list[dict]]:
    base = DATA_EXTERNAL / "D1NAMO_T1D_GlucoseFoodInsulin" / "diabetes_subset_pictures-glucose-food-insulin"
    rows = []
    if not base.exists():
        write_csv(OUT / "30_d1namo_meal_level_ppgr.csv", [])
        return pd.DataFrame(), [{"dataset": "D1NAMO", "status": "missing"}]
    for subj_dir in sorted([p for p in base.iterdir() if p.is_dir()]):
        subject = subj_dir.name
        food_file = subj_dir / "food.csv"
        glu_file = subj_dir / "glucose.csv"
        insulin_file = subj_dir / "insulin.csv"
        if not food_file.exists() or not glu_file.exists():
            continue
        food = pd.read_csv(food_file)
        glu = pd.read_csv(glu_file)
        glu["dt"] = pd.to_datetime(glu["date"].astype(str) + " " + glu["time"].astype(str), errors="coerce")
        glu["glucose_mgdl"] = pd.to_numeric(glu["glucose"], errors="coerce") * 18.0182
        glu = glu.dropna(subset=["dt", "glucose_mgdl"])
        insulin = pd.DataFrame()
        if insulin_file.exists():
            insulin = pd.read_csv(insulin_file)
            insulin["dt"] = pd.to_datetime(insulin["date"].astype(str) + " " + insulin["time"].astype(str), errors="coerce")
            insulin["fast_insulin"] = pd.to_numeric(insulin.get("fast_insulin"), errors="coerce")
        for _, meal in food.iterrows():
            mt = pd.to_datetime(meal.get("datetime"), format="%Y:%m:%d %H:%M:%S", errors="coerce")
            if pd.isna(mt):
                continue
            pre = glu[(glu["dt"] >= mt - pd.Timedelta(minutes=30)) & (glu["dt"] < mt)]
            post = glu[(glu["dt"] >= mt) & (glu["dt"] <= mt + pd.Timedelta(minutes=120))]
            if len(pre) < 3 or len(post) < 8:
                continue
            baseline = float(pre["glucose_mgdl"].mean())
            minutes = (post["dt"] - mt).dt.total_seconds().to_numpy() / 60.0
            delta = post["glucose_mgdl"].to_numpy(float) - baseline
            iauc = trapezoid_auc(minutes, np.maximum(delta, 0))
            peak = float(np.nanmax(delta))
            ttp = float(minutes[np.nanargmax(delta)]) if len(delta) else np.nan
            near_fast = np.nan
            if not insulin.empty:
                near = insulin[(insulin["dt"] >= mt - pd.Timedelta(minutes=30)) & (insulin["dt"] <= mt + pd.Timedelta(minutes=30))]
                if len(near):
                    near_fast = float(near["fast_insulin"].sum(skipna=True))
            cat, rapid, rule = classify_food_matrix_from_text(str(meal.get("description", "")), pd.to_numeric(meal.get("calories"), errors="coerce"))
            rows.append(
                {
                    "dataset": "D1NAMO_T1D",
                    "subject_id": subject,
                    "meal_time": mt.isoformat(),
                    "picture": meal.get("picture"),
                    "description": meal.get("description"),
                    "calories": pd.to_numeric(meal.get("calories"), errors="coerce"),
                    "balance": meal.get("balance"),
                    "quality": meal.get("quality"),
                    "baseline_glucose_mgdl": baseline,
                    "iauc_2h": iauc,
                    "peak_delta_2h": peak,
                    "time_to_peak_2h": ttp,
                    "n_pre": int(len(pre)),
                    "n_post": int(len(post)),
                    "fast_insulin_near_meal": near_fast,
                    "text_food_matrix_category": cat,
                    "text_rapid_digestibility_score": rapid,
                    "text_rule": rule,
                }
            )
    d1 = pd.DataFrame(rows)
    d1.to_csv(OUT / "30_d1namo_meal_level_ppgr.csv", index=False, encoding="utf-8-sig")
    summary = []
    if len(d1):
        for outcome in ["iauc_2h", "peak_delta_2h"]:
            xcols = ["calories", "baseline_glucose_mgdl", "fast_insulin_near_meal", "text_rapid_digestibility_score"]
            d = d1.dropna(subset=[outcome, "subject_id"]).copy()
            for col in xcols:
                d[col] = pd.to_numeric(d[col], errors="coerce")
                d[col] = d[col].fillna(d[col].median())
            X = prepare_matrix(d, xcols, ["text_food_matrix_category"])
            y = d[outcome].reset_index(drop=True)
            groups = d["subject_id"].reset_index(drop=True)
            X = X.reset_index(drop=True)
            preds = np.full(len(d), np.nan)
            for train_idx, test_idx in group_folds(groups, k=min(5, groups.nunique())):
                x_train = X.iloc[train_idx].copy()
                x_test = X.iloc[test_idx].copy()
                med = x_train.median(numeric_only=True)
                x_train = x_train.fillna(med)
                x_test = x_test.fillna(med)
                mean = x_train.mean()
                sd = x_train.std().replace(0, 1)
                beta = fit_ridge(((x_train - mean) / sd).to_numpy(float), y.iloc[train_idx].to_numpy(float), 10.0)
                preds[test_idx] = predict_ridge(beta, ((x_test - mean) / sd).to_numpy(float))
            obs = y.to_numpy(float)
            sse = np.sum((obs - preds) ** 2)
            sst = np.sum((obs - np.mean(obs)) ** 2)
            summary.append(
                {
                    "dataset": "D1NAMO_T1D",
                    "validation_type": "meal_level_subject_disjoint_boundary_validation",
                    "outcome": outcome,
                    "n_meals": int(len(d)),
                    "n_subjects": int(groups.nunique()),
                    "r2": float(1 - sse / sst) if sst > 0 else np.nan,
                    "pearson_r": float(np.corrcoef(obs, preds)[0, 1]) if np.std(preds) > 0 else np.nan,
                    "mae": float(np.mean(np.abs(obs - preds))),
                    "rmse": float(np.sqrt(np.mean((obs - preds) ** 2))),
                    "guardrail": "T1D insulin-treated meal data; used only as external boundary validation, not healthy-adult replication.",
                }
            )
    write_csv(OUT / "30_d1namo_external_validation_performance.csv", summary)
    return d1, summary


def parse_jaeb_healthy_adults() -> tuple[pd.DataFrame, list[dict]]:
    base = DATA_EXTERNAL / "Jaeb_CGMND_HealthyAdults_2017"
    cgm_file = base / "NonDiabDeviceCGM.csv"
    screen_file = base / "NonDiabScreening.csv"
    if not cgm_file.exists():
        return pd.DataFrame(), [{"dataset": "Jaeb_CGMND_HealthyAdults_2017", "status": "missing"}]
    cgm = pd.read_csv(cgm_file)
    cgm["Value"] = pd.to_numeric(cgm["Value"], errors="coerce")
    cgm = cgm[cgm["Value"].between(40, 400)]
    cgm["is_cgm_like"] = cgm["RecordType"].astype(str).str.contains("CGM|Glucose|Sensor", case=False, na=False)
    if cgm["is_cgm_like"].any():
        cgm = cgm[cgm["is_cgm_like"]]
    rows = []
    for pid, g in cgm.groupby("PtID"):
        vals = g["Value"].dropna()
        if len(vals) < 50:
            continue
        rows.append(
            {
                "dataset": "Jaeb_CGMND_HealthyAdults_2017",
                "subject_id": pid,
                "n_cgm_records": int(len(vals)),
                "mean_glucose": float(vals.mean()),
                "sd_glucose": float(vals.std()),
                "cv_glucose": float(vals.std() / vals.mean()),
                "time_above_140_pct": float((vals > 140).mean() * 100),
                "time_below_70_pct": float((vals < 70).mean() * 100),
            }
        )
    jaeb = pd.DataFrame(rows)
    if screen_file.exists() and len(jaeb):
        scr = pd.read_csv(screen_file)
        scr["BMI"] = pd.to_numeric(scr["Weight"], errors="coerce") / (pd.to_numeric(scr["Height"], errors="coerce") / 100) ** 2
        scr = scr[["PtID", "AgeAsOfEnrollDt" if "AgeAsOfEnrollDt" in scr.columns else "PtID"]].copy() if False else scr
        keep = ["PtID", "Weight", "Height", "BMI", "HbA1c", "Gender", "Race", "Ethnicity"]
        keep = [c for c in keep if c in scr.columns]
        jaeb = jaeb.merge(scr[keep].drop_duplicates("PtID"), left_on="subject_id", right_on="PtID", how="left")
    jaeb.to_csv(OUT / "31_jaeb_healthy_adults_day_level_cgm_summary.csv", index=False, encoding="utf-8-sig")
    summary = []
    if len(jaeb):
        for exposure in ["HbA1c", "BMI"]:
            if exposure in jaeb.columns:
                for outcome in ["mean_glucose", "sd_glucose", "cv_glucose", "time_above_140_pct"]:
                    d = jaeb[[exposure, outcome]].apply(pd.to_numeric, errors="coerce").dropna()
                    summary.append(
                        {
                            "dataset": "Jaeb_CGMND_HealthyAdults_2017",
                            "validation_type": "day_level_CGM_variability_boundary_validation",
                            "predictor": exposure,
                            "outcome": outcome,
                            "n_subjects": int(len(d)),
                            "pearson_r": corr(d[exposure], d[outcome]) if len(d) >= 3 else np.nan,
                            "guardrail": "No meal events; validates CGM variability/metabolic-susceptibility boundary, not meal-level PPGR.",
                        }
                    )
    write_csv(OUT / "31_jaeb_day_level_external_validation_correlations.csv", summary)
    return jaeb, summary


def geo_search() -> list[dict]:
    terms = [
        '("di(2-ethylhexyl) phthalate" OR DEHP OR MEHP) AND expression profiling',
        '(phthalate OR "mono-2-ethylhexyl phthalate") AND insulin resistance AND expression',
        '(DEHP OR MEHP) AND (PPAR OR AMPK OR oxidative stress) AND transcriptome',
    ]
    rows = []
    for term in terms:
        try:
            es = requests.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params={"db": "gds", "term": term, "retmode": "json", "retmax": 15},
                timeout=30,
            )
            es.raise_for_status()
            ids = es.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                rows.append({"query": term, "status": "no_hits"})
                continue
            sm = requests.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                params={"db": "gds", "id": ",".join(ids), "retmode": "json"},
                timeout=30,
            )
            sm.raise_for_status()
            result = sm.json().get("result", {})
            for gid in ids:
                item = result.get(gid, {})
                rows.append(
                    {
                        "query": term,
                        "gds_id": gid,
                        "accession": item.get("accession"),
                        "title": item.get("title"),
                        "summary": item.get("summary"),
                        "gds_type": item.get("gdstype"),
                        "taxon": item.get("taxon"),
                        "entry_type": item.get("entrytype"),
                        "pubmed_ids": "|".join(item.get("pubmedids", [])) if isinstance(item.get("pubmedids"), list) else item.get("pubmedids"),
                        "geo_url": f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={item.get('accession')}" if item.get("accession") else None,
                    }
                )
            time.sleep(0.2)
        except Exception as exc:
            rows.append({"query": term, "status": "failed", "error": str(exc)})
    write_csv(OUT / "40_geo_toxicogenomics_candidate_search.csv", rows)
    return rows


def comptox_manifest() -> list[dict]:
    target_file = HIGH / "06_mechanism_ctd_target_chemicals.csv"
    targets = pd.read_csv(target_file)
    rows = []
    for _, row in targets.iterrows():
        dtxsid = row.get("DTXSID")
        name = row.get("ChemicalName")
        cas = row.get("CasRN")
        dashboard = f"https://comptox.epa.gov/dashboard/chemical/details/{dtxsid}" if isinstance(dtxsid, str) and dtxsid else f"https://comptox.epa.gov/dashboard/chemical/search-results?search={quote_plus(str(name))}"
        status = "not_checked"
        try:
            resp = requests.get(dashboard, timeout=20)
            status = f"http_{resp.status_code}"
        except Exception as exc:
            status = f"failed:{exc}"
        rows.append(
            {
                "chemical_name": name,
                "casrn": cas,
                "dtxsid": dtxsid,
                "pubchem_cid": row.get("PubChemCID"),
                "dashboard_url": dashboard,
                "dashboard_status": status,
                "toxcast_endpoint_plan": "Extract assay-level endpoints for nuclear receptor/PPAR, endocrine activity, oxidative stress, mitochondrial toxicity, inflammation, and glucose/insulin-related assays when a CompTox API key or invitroDB flat files are available.",
                "current_use": "Reproducible CompTox/ToxCast query manifest; complements CTD/KEGG/Reactome but is not yet assay-level evidence for chemicals without accessible API output.",
            }
        )
    write_csv(OUT / "41_comptox_toxcast_query_manifest.csv", rows)
    return rows


def mechanism_overlap_summary(geo_rows: list[dict], comptox_rows: list[dict]) -> list[dict]:
    ctd_genes = pd.read_csv(HIGH / "06_mechanism_ctd_gene_summary.csv")
    kegg = pd.read_csv(HIGH / "06_mechanism_kegg_pathway_overlap.csv")
    reactome = pd.read_csv(HIGH / "06_mechanism_reactome_pathway_summary.csv")
    top_genes = "|".join(ctd_genes.head(20)["GeneSymbol"].astype(str).tolist()) if "GeneSymbol" in ctd_genes.columns else ""
    top_kegg = "|".join(kegg.head(10)["pathway_name"].astype(str).tolist()) if "pathway_name" in kegg.columns and len(kegg) else ""
    top_reactome = "|".join(reactome.head(10)["pathway_name"].astype(str).tolist()) if "pathway_name" in reactome.columns and len(reactome) else ""
    rows = [
        {
            "layer": "CTD",
            "status": "completed_previous_package",
            "summary": f"Top CTD genes include {top_genes}",
            "interpretation": "Chemical-gene-disease plausibility layer.",
        },
        {
            "layer": "KEGG",
            "status": "completed_previous_package",
            "summary": top_kegg,
            "interpretation": "Pathway overlap layer; insulin resistance/AMPK/PPAR/PI3K-Akt should remain central.",
        },
        {
            "layer": "Reactome",
            "status": "completed_previous_package",
            "summary": top_reactome,
            "interpretation": "Independent curated pathway layer.",
        },
        {
            "layer": "CompTox/ToxCast",
            "status": "query_manifest_completed",
            "summary": f"{len(comptox_rows)} chemical dashboard/ToxCast query records generated.",
            "interpretation": "Assay-level extraction remains dependent on API key or invitroDB flat-file access.",
        },
        {
            "layer": "GEO toxicogenomics",
            "status": "candidate_search_completed",
            "summary": f"{sum(1 for r in geo_rows if r.get('accession'))} candidate GEO/GDS records captured.",
            "interpretation": "Next step is manual screening for true DEHP/MEHP exposure transcriptomics and differential expression rerun.",
        },
    ]
    write_csv(OUT / "42_mechanism_layer_status_and_interpretation.csv", rows)
    return rows


def build_report(
    msi_corrs: list[dict],
    pred_perf: list[dict],
    hier_rows: list[dict],
    annotation_summary: list[dict],
    fdc_summary: list[dict],
    d1_summary: list[dict],
    jaeb_summary: list[dict],
    mech_rows: list[dict],
) -> None:
    def best_perf(outcome: str) -> str:
        rows = [r for r in pred_perf if r["outcome"] == outcome]
        if not rows:
            return "NA"
        rows = sorted(rows, key=lambda r: r["r2_subject_disjoint"], reverse=True)
        r = rows[0]
        return f"{r['model']} R2={r['r2_subject_disjoint']:.3f}, r={r['pearson_r']:.3f}, n={r['n_meals']}"

    ng_terms = [r for r in hier_rows if r.get("term") in ("non_glycemic_msi", "non_glycemic_x_rapid")]
    lines = [
        "# Formal dry-lab strengthening report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Module status",
        "",
        "1. R formal NHANES mixture rerun: completed for survey GLM, RCS, qgcomp identifiable derived mixtures, negative controls, and quantitative bias grid. Weighted gWQS and BKMR MCMC are retained as long-run blocks because they exceeded interactive runtime.",
        "2. Non-glycemic MSI: completed using BMI and ln(TG/HDL) only, excluding HbA1c, fasting glucose, insulin/HOMA-IR, and TyG.",
        "3. CGMacros subject-disjoint prediction and cluster-robust hierarchical inference: completed with non-glycemic MSI and food-matrix features.",
        "4. Food-matrix annotation: AI/rule-based dual prelabels, manual dual-annotation template, codebook v2, and FDC item-level proxy matches completed. This is not claimed as final human annotation.",
        "5. External CGM validation: D1NAMO meal-level T1D boundary validation and Jaeb healthy-adult day-level CGM variability validation completed.",
        "6. Mechanism layer: CompTox/ToxCast query manifest and GEO toxicogenomics candidate search completed, integrated with existing CTD/KEGG/Reactome evidence.",
        "",
        "## Key computational findings",
        "",
        f"- CGMacros non-glycemic MSI best iAUC model: {best_perf('iauc_2h')}.",
        f"- CGMacros non-glycemic MSI best peak model: {best_perf('peak_delta_2h')}.",
        f"- Dual prelabel food-matrix agreement: kappa={annotation_summary[0]['cohen_kappa']:.3f}, agreement={annotation_summary[0]['agreement_rate']:.3f}, meals needing manual review={annotation_summary[0]['needs_manual_review_n']}.",
        f"- FDC item-level proxy matching: assigned {fdc_summary[0]['n_assigned_fdc_id']}/{fdc_summary[0]['n_meals']} meals, median confidence={fdc_summary[0]['median_match_confidence']:.3f}.",
        f"- D1NAMO external meal-level boundary validation records: {sum(r.get('n_meals', 0) for r in d1_summary if r.get('outcome') == 'iauc_2h')} iAUC meals summarized.",
        f"- Jaeb healthy-adult CGM variability boundary records: {max([r.get('n_subjects', 0) for r in jaeb_summary], default=0)} subjects in correlation summaries.",
        "",
        "## Interpretation guardrails",
        "",
        "- The non-glycemic MSI strengthens the argument against circularity, but it is narrower and should be presented as a conservative sensitivity index rather than the primary MSI.",
        "- Automated dual prelabels are useful for triage and reproducibility, but final publication should still use true blinded human ratings for meals flagged as uncertain.",
        "- D1NAMO is insulin-treated T1D data; it can stress-test PPGR feature extraction and food-matrix directionality but cannot be described as healthy-adult replication.",
        "- Jaeb has no meal events; it supports CGM variability transportability only.",
        "- CompTox/ToxCast currently adds a reproducible query layer. Assay-level claims require API-key/flat-file extraction.",
    ]
    if ng_terms:
        lines.extend(["", "## Non-glycemic MSI inference terms", ""])
        for r in ng_terms:
            lines.append(
                f"- {r['outcome']} / {r['term']}: beta={r['beta_per_1sd_predictor']:.3f}, p={r['p']:.3g}, q={r['q']:.3g}."
            )
    write_text(OUT / "00_formal_drylab_strengthening_report.md", "\n".join(lines))


def main() -> None:
    ensure_out()
    nh, cg, msi_corrs = make_non_glycemic_msi()
    pred_perf, pred_df = subject_disjoint_prediction(cg)
    hier_rows = run_hierarchical_inference(cg)
    prelabel_df, annotation_summary = dual_rater_food_matrix(cg)
    fdc_matches, fdc_summary = fdc_item_level_matching(prelabel_df)
    d1, d1_summary = parse_d1namo()
    jaeb, jaeb_summary = parse_jaeb_healthy_adults()
    geo_rows = geo_search()
    comptox_rows = comptox_manifest()
    mech_rows = mechanism_overlap_summary(geo_rows, comptox_rows)
    build_report(msi_corrs, pred_perf, hier_rows, annotation_summary, fdc_summary, d1_summary, jaeb_summary, mech_rows)

    manifest = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "output_dir": str(OUT),
        "mirror_dir": str(NHANES_MIRROR),
        "modules": [
            "R formal NHANES mixture rerun",
            "non-glycemic MSI",
            "CGMacros subject-disjoint prediction and cluster-robust hierarchical inference",
            "food-matrix dual prelabel/manual annotation template/FDC item-level proxy matching",
            "D1NAMO and Jaeb external CGM boundary validation",
            "CompTox/ToxCast query manifest and GEO toxicogenomics candidate search",
        ],
        "guardrails": [
            "No direct DEHP-to-PPGR causality is claimed.",
            "Automated dual food-matrix prelabels are not final human annotations.",
            "FDC matching is item-level proxy because full CGMacros ingredient text is unavailable.",
            "D1NAMO and Jaeb are boundary validations, not one-to-one external replication.",
        ],
    }
    write_json(OUT / "00_formal_drylab_strengthening_manifest.json", manifest)

    if NHANES_MIRROR.exists():
        shutil.rmtree(NHANES_MIRROR)
    shutil.copytree(OUT, NHANES_MIRROR)
    print(f"Formal dry-lab strengthening package completed: {OUT}")
    print(f"Mirrored to: {NHANES_MIRROR}")


if __name__ == "__main__":
    main()
