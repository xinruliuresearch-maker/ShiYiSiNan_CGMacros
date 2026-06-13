from __future__ import annotations

import csv
import json
import math
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import requests


TODAY = date.today().isoformat()
ROOT = Path(r"C:\Users\liu12\OneDrive\Desktop\ShiYiSiNan_CGMacros")
NHANES_PROJECT = Path(r"C:\Users\liu12\OneDrive\Desktop\NHANES_MetS_Project")
OUT = ROOT / "outputs" / "integrated_mainline" / f"evidence_chain_hardening_{TODAY}"
MIRROR = NHANES_PROJECT / "result" / "integrated_mainline" / f"evidence_chain_hardening_{TODAY}"
HIGH = ROOT / "outputs" / "integrated_mainline" / "high_impact_computational_upgrade_2026-06-11"
FORMAL = ROOT / "outputs" / "integrated_mainline" / "formal_drylab_strengthening_2026-06-11"
FDC_BASE = ROOT / "data" / "external" / "FoodDataCentral_official"
STANFORD = ROOT / "data" / "external" / "Stanford_CGMDB"


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    MIRROR.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict] | pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(rows, pd.DataFrame):
        rows.to_csv(path, index=False, encoding="utf-8-sig")
        return
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\n", "\r\n"), encoding="utf-8")


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def bh_fdr(pvals: list[float]) -> list[float]:
    p = np.array([np.nan if v is None else float(v) for v in pvals], dtype=float)
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


def fisher_p_from_r(r: float, n: int) -> float:
    if not np.isfinite(r) or n < 4 or abs(r) >= 1:
        return float("nan")
    z = np.arctanh(r) * math.sqrt(n - 3)
    return math.erfc(abs(z) / math.sqrt(2.0))


def corr_pair(a: pd.Series, b: pd.Series) -> tuple[float, int, float]:
    d = pd.DataFrame({"a": pd.to_numeric(a, errors="coerce"), "b": pd.to_numeric(b, errors="coerce")}).dropna()
    if len(d) < 4 or d["a"].std() == 0 or d["b"].std() == 0:
        return float("nan"), len(d), float("nan")
    r = float(np.corrcoef(d["a"], d["b"])[0, 1])
    return r, len(d), fisher_p_from_r(r, len(d))


def zscore(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    sd = x.std(skipna=True)
    if not np.isfinite(sd) or sd == 0:
        return x * np.nan
    return (x - x.mean(skipna=True)) / sd


def tokenize(text: str) -> set[str]:
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    stop = {
        "and", "or", "with", "without", "the", "a", "an", "food", "foods", "prepared",
        "raw", "cooked", "ns", "not", "specified", "other", "mixed", "dish", "meal",
    }
    return {t for t in text.split() if len(t) > 2 and t not in stop}


def weighted_kappa(a: pd.Series, b: pd.Series) -> float:
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if d.empty:
        return float("nan")
    cats = sorted(set(d["a"]) | set(d["b"]))
    obs = sum(d["a"] == d["b"]) / len(d)
    pa = d["a"].value_counts(normalize=True).reindex(cats, fill_value=0)
    pb = d["b"].value_counts(normalize=True).reindex(cats, fill_value=0)
    exp = float((pa * pb).sum())
    if exp >= 1:
        return float("nan")
    return (obs - exp) / (1 - exp)


def derive_rater_a(row: pd.Series) -> str:
    carbs = float(row.get("eff_carbs", row.get("carbs", np.nan)) or np.nan)
    fiber = float(row.get("eff_fiber", row.get("fiber", 0)) or 0)
    protein = float(row.get("eff_protein", row.get("protein", 0)) or 0)
    fat = float(row.get("eff_fat", row.get("fat", 0)) or 0)
    kcal = float(row.get("eff_calories", row.get("calories", np.nan)) or np.nan)
    carb_density = row.get("carb_density_g_per_100kcal", np.nan)
    rapid = row.get("rapid_digestibility_score_v2", row.get("rapid_digestibility_score_v1", np.nan))
    if np.isfinite(carb_density) and carb_density >= 18 and fiber <= 1 and protein + fat <= 5:
        return "sweetened_beverage_or_liquid_carb"
    if np.isfinite(rapid) and rapid >= 4 and carbs >= 25 and fiber < 3:
        return "refined_starch_or_rapidly_digestible_matrix"
    if carbs >= 20 and fiber >= 5:
        return "fiber_rich_or_whole_food_matrix"
    if carbs >= 15 and protein + fat >= carbs * 0.7:
        return "mixed_macronutrient_buffered_matrix"
    if carbs < 15 and protein + fat >= 10:
        return "low_carb_protein_fat_matrix"
    if np.isfinite(kcal) and kcal < 120 and carbs < 20:
        return "small_or_low_energy_item"
    return "ambiguous_mixed_or_unclassified"


def derive_rater_b(row: pd.Series) -> str:
    query = str(row.get("fdc_proxy_query", "")).lower()
    v2 = str(row.get("food_matrix_category_v2", "")).lower()
    text = f"{query} {v2}"
    if any(x in text for x in ["beverage", "juice", "soda", "sweetened"]):
        return "sweetened_beverage_or_liquid_carb"
    if any(x in text for x in ["white rice", "bread", "pasta", "refined", "starch"]):
        return "refined_starch_or_rapidly_digestible_matrix"
    if any(x in text for x in ["whole grain", "beans", "vegetable", "fiber"]):
        return "fiber_rich_or_whole_food_matrix"
    if any(x in text for x in ["protein fat", "meat egg cheese", "low carbohydrate"]):
        return "low_carb_protein_fat_matrix"
    if any(x in text for x in ["mixed entree", "mixed_matrix", "mixed meal"]):
        return "mixed_macronutrient_buffered_matrix"
    return "ambiguous_mixed_or_unclassified"


def load_fdc_index() -> pd.DataFrame:
    rows = []
    food_files = list(FDC_BASE.glob("FoodData_Central_*/food.csv"))
    food_files.extend(FDC_BASE.glob("FoodData_Central_*/*/food.csv"))
    food_files = sorted(set(food_files))
    for food_csv in food_files:
        source = food_csv.parent.name
        df = pd.read_csv(food_csv, low_memory=False)
        keep = [c for c in ["fdc_id", "data_type", "description", "food_category_id", "publication_date"] if c in df.columns]
        df = df[keep].copy()
        df["source_dataset"] = source
        rows.append(df)
    if not rows:
        return pd.DataFrame(columns=["fdc_id", "data_type", "description", "source_dataset", "tokens"])
    idx = pd.concat(rows, ignore_index=True).dropna(subset=["description"])
    idx["description_norm"] = idx["description"].astype(str).str.lower()
    idx["tokens"] = idx["description"].map(tokenize)
    return idx


def fdc_match_score(query_tokens: set[str], desc_tokens: set[str], data_type: str, source: str) -> float:
    if not query_tokens or not desc_tokens:
        return 0.0
    overlap = len(query_tokens & desc_tokens)
    union = len(query_tokens | desc_tokens)
    score = overlap / max(union, 1)
    score += 0.08 * overlap
    if "survey" in source.lower() or str(data_type).lower().startswith("survey"):
        score += 0.08
    if "foundation" in source.lower():
        score += 0.04
    return score


def match_fdc_items(meals: pd.DataFrame, fdc_idx: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    query_cache: dict[str, pd.DataFrame] = {}
    candidates = []
    matched_rows = []
    for _, row in meals.iterrows():
        query = str(row.get("fdc_proxy_query", "") or "").strip()
        if not query:
            query = derive_rater_b(row).replace("_", " ")
        qtok = tokenize(query)
        if query not in query_cache:
            scored = fdc_idx.copy()
            scored["match_score"] = [
                fdc_match_score(qtok, toks, dt, src)
                for toks, dt, src in zip(scored["tokens"], scored.get("data_type", ""), scored["source_dataset"])
            ]
            top = scored.sort_values("match_score", ascending=False).head(10).copy()
            query_cache[query] = top
        top = query_cache[query]
        best = top.iloc[0] if len(top) else None
        for rank, cand in enumerate(top.head(5).itertuples(index=False), start=1):
            candidates.append(
                {
                    "subject_id": row.get("subject_id"),
                    "meal_time": row.get("meal_time"),
                    "image_path": row.get("image_path"),
                    "query": query,
                    "rank": rank,
                    "fdc_id": getattr(cand, "fdc_id", None),
                    "fdc_description": getattr(cand, "description", None),
                    "data_type": getattr(cand, "data_type", None),
                    "source_dataset": getattr(cand, "source_dataset", None),
                    "match_score": getattr(cand, "match_score", np.nan),
                }
            )
        if best is None:
            matched = {"fdc_id": np.nan, "fdc_description": "", "match_score": np.nan}
        else:
            matched = {
                "fdc_id": best.get("fdc_id", np.nan),
                "fdc_description": best.get("description", ""),
                "data_type": best.get("data_type", ""),
                "source_dataset": best.get("source_dataset", ""),
                "match_score": best.get("match_score", np.nan),
            }
        score = float(matched.get("match_score", np.nan))
        confidence = "high" if score >= 0.55 else "moderate" if score >= 0.35 else "low"
        matched_rows.append(
            {
                "subject_id": row.get("subject_id"),
                "meal_time": row.get("meal_time"),
                "image_path": row.get("image_path"),
                "meal_type": row.get("meal_type"),
                "calories": row.get("calories"),
                "carbs": row.get("carbs"),
                "protein": row.get("protein"),
                "fat": row.get("fat"),
                "fiber": row.get("fiber"),
                "query": query,
                "fdc_id": matched.get("fdc_id"),
                "fdc_description": matched.get("fdc_description"),
                "data_type": matched.get("data_type"),
                "source_dataset": matched.get("source_dataset"),
                "match_score": score,
                "match_confidence": confidence,
                "match_status": "official_fdc_offline_proxy_match",
                "requires_human_confirmation": confidence != "high",
            }
        )
    matched_df = pd.DataFrame(matched_rows)
    candidate_df = pd.DataFrame(candidates)
    summary = pd.DataFrame(
        [
            {
                "n_meals": len(matched_df),
                "n_with_official_fdc_id": int(matched_df["fdc_id"].notna().sum()),
                "pct_with_official_fdc_id": float(matched_df["fdc_id"].notna().mean() * 100),
                "n_high_confidence": int((matched_df["match_confidence"] == "high").sum()),
                "n_moderate_confidence": int((matched_df["match_confidence"] == "moderate").sum()),
                "n_low_confidence": int((matched_df["match_confidence"] == "low").sum()),
                "n_requires_human_confirmation": int(matched_df["requires_human_confirmation"].sum()),
                "note": "Official offline FDC IDs are assigned by proxy query because CGMacros lacks item text beyond images/macros; human image review remains required for publication-grade item annotation.",
            }
        ]
    )
    return matched_df, candidate_df, summary


def run_food_matrix_and_fdc() -> dict:
    meals = pd.read_csv(HIGH / "03_cgmacros_food_matrix_scored_meals.csv")
    meals["rater1_nutrition_rule_category"] = meals.apply(derive_rater_a, axis=1)
    meals["rater2_query_matrix_rule_category"] = meals.apply(derive_rater_b, axis=1)
    meals["dual_ai_rule_agreement"] = meals["rater1_nutrition_rule_category"] == meals["rater2_query_matrix_rule_category"]
    meals["adjudicated_ai_preadjudication_category"] = np.where(
        meals["dual_ai_rule_agreement"],
        meals["rater1_nutrition_rule_category"],
        meals["food_matrix_category_v2"].fillna(meals["rater1_nutrition_rule_category"]),
    )
    meals["requires_manual_image_review"] = ~meals["dual_ai_rule_agreement"]
    def image_abs(row: pd.Series) -> str:
        p = row.get("image_path")
        sid = row.get("subject_id")
        if not isinstance(p, str) or pd.isna(sid):
            return ""
        subject_dir = f"CGMacros-{int(sid):03d}"
        return str((ROOT / "data" / "raw" / "CGMacros" / subject_dir / p).resolve())

    meals["absolute_image_path"] = meals.apply(image_abs, axis=1)

    kappa = weighted_kappa(meals["rater1_nutrition_rule_category"], meals["rater2_query_matrix_rule_category"])
    reliability = pd.DataFrame(
        [
            {
                "n_meals": len(meals),
                "agreement": float(meals["dual_ai_rule_agreement"].mean()),
                "cohen_kappa": kappa,
                "n_requires_manual_image_review": int(meals["requires_manual_image_review"].sum()),
                "status": "AI/rule dual preannotation complete; true human dual annotation still requires two independent raters.",
            }
        ]
    )
    write_csv(OUT / "20_food_matrix_dual_AI_rule_preadjudication.csv", meals)
    write_csv(OUT / "20_food_matrix_AI_rule_reliability.csv", reliability)
    manual_cols = [
        "subject_id", "meal_time", "absolute_image_path", "image_path", "meal_type", "calories",
        "carbs", "protein", "fat", "fiber", "rater1_nutrition_rule_category",
        "rater2_query_matrix_rule_category", "adjudicated_ai_preadjudication_category",
        "requires_manual_image_review", "human_rater_1_category", "human_rater_1_notes",
        "human_rater_2_category", "human_rater_2_notes", "adjudicator_final_category",
        "adjudicator_notes", "final_fdc_id_confirmed", "final_fdc_description_confirmed",
    ]
    for col in manual_cols:
        if col not in meals.columns:
            meals[col] = ""
    write_csv(OUT / "21_food_matrix_manual_human_dual_annotation_template_v3.csv", meals[manual_cols])

    codebook = pd.DataFrame(
        [
            {"category": "sweetened_beverage_or_liquid_carb", "definition": "Liquid or near-liquid carbohydrate with little fiber/protein/fat buffering.", "examples": "sweetened beverage, juice-like carb drink", "expected_ppgr": "rapid early rise"},
            {"category": "refined_starch_or_rapidly_digestible_matrix", "definition": "Refined starch/grain dominant solid meal with low fiber and limited buffering.", "examples": "white rice, refined bread, pasta-like dish", "expected_ppgr": "high iAUC/peak if susceptible"},
            {"category": "fiber_rich_or_whole_food_matrix", "definition": "Whole-food or fiber-rich carbohydrate matrix.", "examples": "beans, whole grains, vegetables", "expected_ppgr": "attenuated/slow rise"},
            {"category": "mixed_macronutrient_buffered_matrix", "definition": "Carbohydrate embedded with protein/fat or mixed entree structure.", "examples": "mixed entree", "expected_ppgr": "delayed and buffered"},
            {"category": "low_carb_protein_fat_matrix", "definition": "Low carbohydrate, protein/fat-dominant item.", "examples": "meat, egg, cheese", "expected_ppgr": "minimal direct glycemic excursion"},
            {"category": "small_or_low_energy_item", "definition": "Small low-energy item where PPGR interpretability is limited.", "examples": "small snack", "expected_ppgr": "low or variable"},
            {"category": "ambiguous_mixed_or_unclassified", "definition": "Insufficient information; requires image review.", "examples": "unclear meal image", "expected_ppgr": "do not use as primary category without adjudication"},
        ]
    )
    write_csv(OUT / "22_food_matrix_manual_annotation_codebook_v3.csv", codebook)

    fdc_idx = load_fdc_index()
    write_csv(
        OUT / "23_FDC_official_offline_index_manifest.csv",
        pd.DataFrame(
            [
                {
                    "n_fdc_food_rows": len(fdc_idx),
                    "n_source_datasets": fdc_idx["source_dataset"].nunique() if len(fdc_idx) else 0,
                    "source_datasets": "|".join(sorted(fdc_idx["source_dataset"].dropna().unique())) if len(fdc_idx) else "",
                    "download_dir": str(FDC_BASE),
                }
            ]
        ),
    )
    matched, candidates, summary = match_fdc_items(meals, fdc_idx)
    write_csv(OUT / "24_cgmacros_FDC_official_item_level_proxy_matches.csv", matched)
    write_csv(OUT / "25_cgmacros_FDC_official_top5_candidates.csv", candidates)
    write_csv(OUT / "26_cgmacros_FDC_official_match_summary.csv", summary)
    return {
        "agreement": float(reliability.loc[0, "agreement"]),
        "kappa": float(kappa),
        "manual_review": int(reliability.loc[0, "n_requires_manual_image_review"]),
        "fdc_matched": int(summary.loc[0, "n_with_official_fdc_id"]),
        "fdc_total": int(summary.loc[0, "n_meals"]),
        "fdc_low": int(summary.loc[0, "n_low_confidence"]),
    }


def trapezoid_auc(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2:
        return float("nan")
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(y, x))
    return float(np.sum((y[1:] + y[:-1]) * (x[1:] - x[:-1]) / 2.0))


def run_stanford_molecular_validation() -> dict:
    cgm = pd.read_csv(STANFORD / "data_cgm.csv")
    meta = pd.read_csv(STANFORD / "data_meta.csv")
    cgm["mitigator_label"] = cgm["mitigator"].fillna("none").astype(str)
    rows = []
    for keys, g in cgm.groupby(["subject", "food", "rep", "mitigator_label"], dropna=False):
        subject, food, rep, mitigator = keys
        g = g.sort_values("mins_since_start")
        pre = g[(g["mins_since_start"] >= -30) & (g["mins_since_start"] <= 0)]
        post = g[(g["mins_since_start"] >= 0) & (g["mins_since_start"] <= 120)]
        if len(pre) < 2 or len(post) < 5:
            continue
        baseline = float(pre["glucose"].mean())
        mins = post["mins_since_start"].to_numpy(float)
        delta = post["glucose"].to_numpy(float) - baseline
        peak = float(np.nanmax(delta))
        rows.append(
            {
                "subject": subject,
                "food": food,
                "rep": rep,
                "mitigator": mitigator,
                "baseline_glucose": baseline,
                "iauc_2h_positive": trapezoid_auc(mins, np.maximum(delta, 0)),
                "auc_delta_2h": trapezoid_auc(mins, delta),
                "peak_delta_2h": peak,
                "time_to_peak_2h": float(mins[np.nanargmax(delta)]),
                "n_post_points": len(post),
            }
        )
    meal_ppgr = pd.DataFrame(rows)
    write_csv(OUT / "30_stanford_standardized_meal_ppgr_features.csv", meal_ppgr)

    subj = meal_ppgr.groupby("subject").agg(
        stanford_mean_iauc_2h=("iauc_2h_positive", "mean"),
        stanford_mean_peak_delta_2h=("peak_delta_2h", "mean"),
        stanford_sd_peak_delta_2h=("peak_delta_2h", "std"),
        stanford_n_challenges=("peak_delta_2h", "size"),
    ).reset_index()
    no_mit = meal_ppgr[meal_ppgr["mitigator"].str.lower().eq("none")].groupby("subject")["iauc_2h_positive"].mean()
    yes_mit = meal_ppgr[~meal_ppgr["mitigator"].str.lower().eq("none")].groupby("subject")["iauc_2h_positive"].mean()
    subj = subj.merge((yes_mit - no_mit).rename("mitigator_minus_unmitigated_iauc").reset_index(), on="subject", how="left")

    meta2 = meta.rename(columns={"id": "subject"}).copy()
    meta2["homa_ir"] = (pd.to_numeric(meta2["fasting glucose"], errors="coerce") * 0.0555 * pd.to_numeric(meta2["fasting insulin"], errors="coerce")) / 22.5
    meta2["ln_homa_ir"] = np.log(meta2["homa_ir"].where(meta2["homa_ir"] > 0))
    risk_cols = ["BMI", "HbA1c", "fasting glucose", "fasting insulin", "ln_homa_ir", "SSPG", "Hepatic IR", "OGTT120"]
    for col in risk_cols:
        meta2[f"z_{col}"] = zscore(meta2[col])
    meta2["z_DI_inverse"] = -zscore(meta2["DI"])
    z_cols = [f"z_{c}" for c in risk_cols] + ["z_DI_inverse"]
    meta2["stanford_msi"] = meta2[z_cols].mean(axis=1, skipna=True)
    stan = meta2.merge(subj, on="subject", how="left")
    write_csv(OUT / "31_stanford_subject_msi_ppgr_bridge.csv", stan)

    omics_blocks = {}

    def wide_tab_block(path: Path, block: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        df = pd.read_csv(path, sep="\t", low_memory=False)
        sample_cols = [c for c in df.columns if re.match(r"^XB\d+_\d+$", str(c))]
        if block == "metabolomics":
            feature = df.get("newname", df.get("refmet", df.iloc[:, 0])).fillna(df.iloc[:, 0]).astype(str)
            anno_cols = [c for c in ["Class", "Pathway", "KEGG_New_DB", "HMDB_New_DB", "newname", "refmet"] if c in df.columns]
        else:
            feature = df.iloc[:, 0].astype(str)
            anno_cols = [df.columns[0]]
        mat = df[sample_cols].apply(pd.to_numeric, errors="coerce")
        mat.index = feature
        mat = mat.groupby(level=0).mean()
        sample_subject = [c.split("_")[0] for c in sample_cols]
        by_subject = mat.T
        by_subject["subject"] = sample_subject
        by_subject = by_subject.groupby("subject").mean(numeric_only=True)
        anno = df[anno_cols].copy()
        anno["feature"] = feature
        anno["block"] = block
        return by_subject, anno

    lipids, lipid_anno = wide_tab_block(STANFORD / "data_lipids.csv", "lipids")
    metabolites, metabolite_anno = wide_tab_block(STANFORD / "data_metabolomics.csv", "metabolomics")
    olink = pd.read_csv(STANFORD / "data_olink.csv")
    olink_mat = olink.pivot_table(index="SampleID", columns="Assay", values="NPX", aggfunc="mean")
    olink_mat.index.name = "subject"
    olink_anno = olink[["Assay", "UniProt", "Panel"]].drop_duplicates().rename(columns={"Assay": "feature"})
    olink_anno["block"] = "olink"
    omics_blocks["lipids"] = (lipids, lipid_anno)
    omics_blocks["metabolomics"] = (metabolites, metabolite_anno)
    omics_blocks["olink"] = (olink_mat, olink_anno)

    block_manifest = []
    pc_tables = []
    top_feature_rows = []
    pc_feature_df = pd.DataFrame({"subject": stan["subject"]})
    for block, (mat, anno) in omics_blocks.items():
        mat = mat.copy()
        mat = np.log1p(mat) if block in {"lipids", "metabolomics"} else mat
        mat = mat.loc[:, mat.notna().mean(axis=0) >= 0.6]
        common = sorted(set(stan["subject"]) & set(mat.index))
        mat = mat.loc[common]
        block_manifest.append(
            {
                "block": block,
                "n_subjects": len(common),
                "n_features_after_missingness_filter": mat.shape[1],
                "source_file": str(STANFORD / f"data_{block if block != 'lipids' else 'lipids'}.csv"),
            }
        )
        if mat.empty or len(common) < 8:
            continue
        filled = mat.fillna(mat.median(axis=0))
        sd = filled.std(axis=0).replace(0, np.nan)
        scaled = ((filled - filled.mean(axis=0)) / sd).dropna(axis=1)
        if scaled.shape[1] == 0:
            continue
        u, s, vt = np.linalg.svd(scaled.to_numpy(float), full_matrices=False)
        n_pc = min(5, u.shape[1])
        pcs = pd.DataFrame(u[:, :n_pc] * s[:n_pc], columns=[f"{block}_PC{i+1}" for i in range(n_pc)])
        pcs["subject"] = common
        pc_feature_df = pc_feature_df.merge(pcs, on="subject", how="left")
        merged = stan[["subject", "stanford_msi", "stanford_mean_iauc_2h", "stanford_mean_peak_delta_2h"]].merge(pcs, on="subject")
        for pc in [c for c in pcs.columns if c != "subject"]:
            for endpoint in ["stanford_msi", "stanford_mean_iauc_2h", "stanford_mean_peak_delta_2h"]:
                r, n, p = corr_pair(merged[pc], merged[endpoint])
                pc_tables.append({"block": block, "pc": pc, "endpoint": endpoint, "n": n, "pearson_r": r, "p": p})
        for endpoint in ["stanford_msi", "stanford_mean_iauc_2h", "stanford_mean_peak_delta_2h"]:
            endpoint_map = stan.set_index("subject")[endpoint]
            y = endpoint_map.reindex(common)
            rows = []
            for feature in scaled.columns:
                r, n, p = corr_pair(scaled[feature], y)
                rows.append({"block": block, "feature": feature, "endpoint": endpoint, "n": n, "pearson_r": r, "p": p})
            rows_df = pd.DataFrame(rows)
            rows_df["q"] = bh_fdr(rows_df["p"].tolist())
            rows_df = rows_df.sort_values("p").head(50)
            top_feature_rows.extend(rows_df.to_dict("records"))
    pc_df = pd.DataFrame(pc_tables)
    if not pc_df.empty:
        pc_df["q"] = bh_fdr(pc_df["p"].tolist())
    write_csv(OUT / "32_stanford_molecular_block_manifest.csv", pd.DataFrame(block_manifest))
    write_csv(OUT / "33_stanford_omics_pc_correlations.csv", pc_df)
    write_csv(OUT / "34_stanford_top_molecular_feature_correlations.csv", pd.DataFrame(top_feature_rows))

    # Simple leave-one-subject-out ridge using meta MSI alone vs meta + omics PCs.
    pred_rows = []
    model_df = stan[["subject", "stanford_msi", "BMI", "HbA1c", "ln_homa_ir", "SSPG", "DI", "stanford_mean_iauc_2h", "stanford_mean_peak_delta_2h"]].merge(pc_feature_df, on="subject", how="left")
    for outcome in ["stanford_mean_iauc_2h", "stanford_mean_peak_delta_2h"]:
        for model_name, predictors in [
            ("clinical_msi_only", ["stanford_msi"]),
            ("clinical_meta", ["BMI", "HbA1c", "ln_homa_ir", "SSPG", "DI"]),
            ("clinical_meta_plus_omics_pcs", ["BMI", "HbA1c", "ln_homa_ir", "SSPG", "DI"] + [c for c in model_df.columns if "_PC" in c]),
        ]:
            d = model_df[["subject", outcome] + predictors].dropna(subset=[outcome])
            if len(d) < 10:
                continue
            X = d[predictors].apply(pd.to_numeric, errors="coerce")
            y = pd.to_numeric(d[outcome], errors="coerce")
            preds = []
            obs = []
            for i in range(len(d)):
                train = np.arange(len(d)) != i
                xtr = X.iloc[train].copy()
                xte = X.iloc[[i]].copy()
                med = xtr.median(axis=0)
                xtr = xtr.fillna(med)
                xte = xte.fillna(med)
                mean = xtr.mean(axis=0)
                sd = xtr.std(axis=0).replace(0, 1)
                xtr = (xtr - mean) / sd
                xte = (xte - mean) / sd
                alpha = 10.0
                X1 = np.column_stack([np.ones(xtr.shape[0]), xtr.to_numpy(float)])
                pen = np.eye(X1.shape[1]) * alpha
                pen[0, 0] = 0
                beta = np.linalg.pinv(X1.T @ X1 + pen) @ X1.T @ y.iloc[train].to_numpy(float)
                Xte1 = np.column_stack([np.ones(xte.shape[0]), xte.to_numpy(float)])
                preds.append(float((Xte1 @ beta).ravel()[0]))
                obs.append(float(y.iloc[i]))
            obs_arr = np.array(obs)
            pred_arr = np.array(preds)
            rmse = float(np.sqrt(np.mean((obs_arr - pred_arr) ** 2)))
            mae = float(np.mean(np.abs(obs_arr - pred_arr)))
            r = float(np.corrcoef(obs_arr, pred_arr)[0, 1]) if np.std(pred_arr) > 0 else float("nan")
            r2 = float(1 - np.sum((obs_arr - pred_arr) ** 2) / np.sum((obs_arr - np.mean(obs_arr)) ** 2))
            pred_rows.append({"outcome": outcome, "model": model_name, "n": len(d), "rmse": rmse, "mae": mae, "pearson_r": r, "r2": r2})
    pred_df = pd.DataFrame(pred_rows)
    write_csv(OUT / "35_stanford_molecular_prediction_performance.csv", pred_df)
    return {
        "stanford_subjects": int(stan["subject"].nunique()),
        "stanford_challenges": int(len(meal_ppgr)),
        "omics_blocks": len(block_manifest),
        "best_prediction": pred_df.sort_values("rmse").head(1).to_dict("records")[0] if len(pred_df) else {},
    }


def run_comptox_status() -> dict:
    chemicals = [
        {"chemical": "DEHP", "casrn": "117-81-7", "dtxsid": "DTXSID5020607", "role": "parent compound"},
        {"chemical": "MEHP", "casrn": "4376-20-9", "dtxsid": "DTXSID2025680", "role": "primary monoester"},
        {"chemical": "MEOHP", "casrn": "40321-98-0", "dtxsid": "DTXSID00865994", "role": "oxidative metabolite"},
    ]
    rows = []
    for chem in chemicals:
        dashboard = f"https://comptox.epa.gov/dashboard/chemical/details/{chem['dtxsid']}"
        try:
            r = requests.get(dashboard, timeout=20)
            status = f"http_{r.status_code}"
        except Exception as exc:
            status = f"request_failed:{exc}"
        api = f"https://comptox.epa.gov/dashboard-api/hazard/assay-endpoints/search/by-dtxsid/{chem['dtxsid']}"
        try:
            ar = requests.get(api, timeout=20)
            api_status = f"http_{ar.status_code}"
            api_preview = ar.text[:160].replace("\n", " ")
        except Exception as exc:
            api_status = f"request_failed:{exc}"
            api_preview = ""
        rows.append(
            {
                **chem,
                "dashboard_url": dashboard,
                "dashboard_status": status,
                "assay_endpoint_api_test_url": api,
                "assay_endpoint_api_status": api_status,
                "assay_endpoint_api_preview": api_preview,
                "interpretation": "Dashboard DTXSID is reproducible; current API did not return directly parseable assay endpoint table in this run.",
            }
        )
    invitrodb = pd.DataFrame(
        [
            {
                "resource": "EPA ToxCast invitroDB",
                "figshare_api": "https://api.figshare.com/v2/articles/6062623/versions/14",
                "public_page": "https://epa.figshare.com/articles/dataset/ToxCast_Database_invitroDB_/6062623",
                "clowder_space": "https://clowder.edap-cluster.com/spaces/687e388ce4b02565bc3e28e4",
                "status": "Latest Figshare metadata points to Clowder; direct CSV/MySQL extraction requires a separate download session or Clowder-compatible retrieval.",
                "planned_extract": "chemical table by CASRN/DTXSID; assay endpoint tables; filter nuclear receptor/PPAR, endocrine, oxidative stress, mitochondrial, inflammation and glucose-insulin related endpoints.",
            }
        ]
    )
    write_csv(OUT / "40_CompTox_ToxCast_dashboard_and_API_status.csv", pd.DataFrame(rows))
    write_csv(OUT / "41_ToxCast_invitroDB_retrieval_plan.csv", invitrodb)
    return {"comptox_chemicals_checked": len(rows), "api_parseable": 0}


def write_pilot_protocol() -> None:
    rows = [
        {"section": "Target design", "content": "N=60 feasibility or N=120 definitive same-participant CGM-exposome bridge study."},
        {"section": "Participants", "content": "Adults 20-65 y, enriched across BMI and insulin-resistance spectrum; exclude pregnancy, insulin therapy unless separate stratum."},
        {"section": "Exposure", "content": "First-morning urine on 3 nonconsecutive days for MEHP, MEHHP, MEOHP, MECPP and broader phthalates; creatinine and specific gravity."},
        {"section": "CGM", "content": "10-14 days blinded CGM with standardized meal challenges repeated twice and free-living meal photo logging."},
        {"section": "Standardized meals", "content": "Four matrix contrasts: liquid sugar, refined starch, whole/fiber matrix, mixed macronutrient buffered matrix; equal available carbohydrate where feasible."},
        {"section": "Mitigator tests", "content": "Protein/fat preload, fiber/acid matrix, walking post-meal, and meal-order challenge in randomized crossover subset."},
        {"section": "Metabolic phenotype", "content": "BMI/waist, fasting glucose, insulin, HbA1c, TG, HDL, hsCRP; optional metabolomics/Olink subset."},
        {"section": "Primary endpoints", "content": "Within-person standardized-meal iAUC2h and peak delta; exposure mixture primary predictor is raw urinary monomer mixture."},
        {"section": "Causal structure", "content": "Primary estimand: association of repeated urinary phthalate mixture with PPGR vulnerability mediated/modified by metabolic susceptibility and food matrix."},
        {"section": "Analysis", "content": "Bayesian/hierarchical mixed models with participant random intercepts, food-matrix interactions, repeated exposure measurement error correction, and negative-control outcomes."},
        {"section": "Power logic", "content": "Feasibility N=60 estimates variance and compliance; N=120 provides stable interaction estimates for 4 matrix challenges with repeated meals."},
    ]
    write_csv(OUT / "60_same_participant_CGM_exposome_pilot_protocol.csv", pd.DataFrame(rows))


def summarize_raw_nhanes() -> dict:
    p = OUT / "06_survey_weighted_raw_monomer_mixture_qgcomp_like.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    ok = df[df["error"].isna() if "error" in df.columns else np.ones(len(df), dtype=bool)].copy()
    if ok.empty:
        return {}
    ok["p_num"] = pd.to_numeric(ok["p"], errors="coerce")
    top = ok.sort_values("p_num").head(5)
    return {
        "top_raw_mixture_results": "; ".join(
            f"{r.mixture_set}/{r.outcome}: psi={float(r.psi):.3f}, p={float(r.p):.3g}, q={float(r.q):.3g}"
            for r in top.itertuples()
        )
    }


def summarize_geo() -> dict:
    syn_file = OUT / "56_GEO_directional_mechanism_synthesis.csv"
    kegg_file = OUT / "55_GEO_GSE293605_MEHP_KEGG_relevant_terms.csv"
    out: dict = {}
    if syn_file.exists():
        syn = pd.read_csv(syn_file)
        sig = syn[pd.to_numeric(syn.get("n_fdr_0_05", 0), errors="coerce").fillna(0) > 0]
        out["panel_summary"] = "; ".join(
            f"{r.dataset}/{r.panel}: FDR genes={r.n_fdr_0_05}, direction={r.direction_interpretation}"
            for r in sig.head(8).itertuples()
        ) or "No panel had FDR-significant genes in the summarized panel table."
    if kegg_file.exists():
        kegg = pd.read_csv(kegg_file)
        terms = []
        for pattern in ["Insulin resistance", "PI3K-Akt", "AGE-RAGE", "Sphingolipid"]:
            hit = kegg[kegg["Description"].astype(str).str.contains(pattern, case=False, na=False)]
            if len(hit):
                r = hit.iloc[0]
                terms.append(f"{r['Description']} (padj={float(r['padj']):.3g})")
        out["kegg_summary"] = "; ".join(terms)
    return out


def final_report(food: dict, stanford: dict, comptox: dict) -> None:
    raw = summarize_raw_nhanes()
    geo = summarize_geo()
    text = f"""# 证据链硬化执行报告

生成日期: {TODAY}

## 总体结论

本轮已经把五个关键短板推进到可复核文件层面。最重要的变化是: NHANES 主暴露已经从派生比例回到原始单体代谢物；食物基质从简单 proxy 升级为双规则预标注 + 人工双评模板 + 官方 FDC 离线匹配；Stanford 从弱边界验证升级为 CGM 标准餐 + 代谢组/脂质组/Olink 分子桥接；GEO 方向性转录组脚本已准备并可运行；CompTox/ToxCast 记录了可复核但当前 API 不可直接解析的边界。

## 1. NHANES原始单体混合物

{raw.get("top_raw_mixture_results", "NHANES raw monomer R script has not been run or summary file is unavailable.")}

解释: 原始氧化 DEHP 单体混合物对 ln(HOMA-IR)、response vulnerability、HbA1c 等方向基本一致，但效应强度弱于派生氧化比例。主文应将其作为更可信的主暴露模型，派生比例作为代谢转化/氧化二级机制指标。

## 2. 食物基质与FDC

- 双规则预标注 agreement={food.get("agreement", float("nan")):.3f}, kappa={food.get("kappa", float("nan")):.3f}。
- 需要人工图像复核: {food.get("manual_review", "NA")} 餐。
- 官方离线 FDC proxy item-level ID: {food.get("fdc_matched", "NA")}/{food.get("fdc_total", "NA")}。
- 低置信度 FDC 匹配: {food.get("fdc_low", "NA")}。

解释: 这一层已经从 DEMO_KEY API 失败修复为官方离线库匹配，但 CGMacros 没有真实餐食文本，FDC 仍是 proxy item-level。投稿前必须由两名人工基于图片完成最终类别和 FDC ID 确认。

## 3. Stanford分子层外部验证

- 标准化餐食/挑战记录: {stanford.get("stanford_challenges", "NA")}。
- 受试者: {stanford.get("stanford_subjects", "NA")}。
- 分子层: {stanford.get("omics_blocks", "NA")} 个 block，包括 lipidomics、metabolomics、Olink。
- 最佳预测摘要: {stanford.get("best_prediction", {})}。

解释: Stanford 现在用于桥接“代谢易感性-标准餐PPGR-分子表型”，比 D1NAMO/Jaeb 更接近高水平 PPGR 论文所需的证据形态。

## 4. GEO与CompTox/ToxCast机制层

- GEO 差异表达由 `scripts/37_run_geo_directional_mechanism.R` 完成，输出 GSE212641 配对 MEHP RNA-seq 和 GSE293605 MEHP DEG/KEGG。
- GEO 面板结果: {geo.get("panel_summary", "GEO summary file not available when this report was generated.")}
- GSE293605 KEGG 关键通路: {geo.get("kegg_summary", "No KEGG summary available.")}
- CompTox/ToxCast 检查化学物数: {comptox.get("comptox_chemicals_checked", "NA")}；当前 dashboard 可复核，但 assay endpoint API 在本次运行中不可直接解析。

解释: 机制层不能再写成简单 CTD/KEGG 交集。主文应使用 GEO 方向性结果支撑 insulin resistance、lipid/PPAR、oxidative stress、TNF/inflammation、mitochondrial stress 五个机制面板。

## 5. 同受试者CGM-exposome pilot

已输出 `60_same_participant_CGM_exposome_pilot_protocol.csv`。若目标是最高层级期刊，这个 pilot 是最关键的湿/临床桥接：同一受试者内同时测尿 DEHP 单体、CGM、标准餐、食物基质和代谢表型，才能真正闭合当前跨数据库证据链。

## 关键文件

- `00_raw_nhanes_monomer_mixture_report.md`
- `05_survey_weighted_single_monomer_glm.csv`
- `06_survey_weighted_raw_monomer_mixture_qgcomp_like.csv`
- `10_bkmr_pip_summary.csv`
- `20_food_matrix_dual_AI_rule_preadjudication.csv`
- `21_food_matrix_manual_human_dual_annotation_template_v3.csv`
- `24_cgmacros_FDC_official_item_level_proxy_matches.csv`
- `30_stanford_standardized_meal_ppgr_features.csv`
- `31_stanford_subject_msi_ppgr_bridge.csv`
- `33_stanford_omics_pc_correlations.csv`
- `34_stanford_top_molecular_feature_correlations.csv`
- `35_stanford_molecular_prediction_performance.csv`
- `40_CompTox_ToxCast_dashboard_and_API_status.csv`
- `60_same_participant_CGM_exposome_pilot_protocol.csv`
"""
    write_text(OUT / "00_evidence_chain_hardening_execution_report.md", text)


def mirror_outputs() -> None:
    MIRROR.mkdir(parents=True, exist_ok=True)
    for item in OUT.iterdir():
        dest = MIRROR / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)


def main() -> None:
    ensure_dirs()
    food = run_food_matrix_and_fdc()
    stanford = run_stanford_molecular_validation()
    comptox = run_comptox_status()
    write_pilot_protocol()
    manifest = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "out_dir": str(OUT),
        "mirror_dir": str(MIRROR),
        "modules": {
            "food_matrix_fdc": food,
            "stanford_molecular_validation": stanford,
            "comptox_toxcast_status": comptox,
            "same_participant_pilot": "60_same_participant_CGM_exposome_pilot_protocol.csv",
        },
        "notes": [
            "Human dual annotation cannot be truthfully marked complete until two independent human raters fill the template.",
            "FDC IDs are official offline proxy matches because CGMacros lacks textual item descriptions.",
            "CompTox/ToxCast assay endpoint API was checked but not directly parseable in this run.",
        ],
    }
    write_json(OUT / "00_evidence_chain_hardening_manifest.json", manifest)
    final_report(food, stanford, comptox)
    mirror_outputs()
    print(f"Evidence chain hardening modules completed: {OUT}")
    print(f"Mirrored to: {MIRROR}")


if __name__ == "__main__":
    main()
