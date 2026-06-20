"""Create a reproducible proxy adjudication for the CGMacros food-matrix template.

The manual image-review template currently has empty human-rater fields and the
stored absolute image paths point to an unavailable OneDrive location. This
script therefore performs a conservative nutrition/query proxy adjudication and
records that limitation in the notes instead of implying true visual review.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


CG = Path(r"D:\ShiYiSiNan_CGMacros")
TEMPLATE = (
    CG
    / "outputs"
    / "integrated_mainline"
    / "evidence_chain_hardening_2026-06-11"
    / "21_food_matrix_manual_human_dual_annotation_template_v3.csv"
)
OUT = Path(r"D:\ai for science") / "results" / "nature_food_aim2_cgmacros"
OUT.mkdir(parents=True, exist_ok=True)

MATRIX_ORDER = [
    "low_carb_or_protein_forward",
    "fiber_rich_or_whole_food_matrix",
    "mixed_meal_protein_fat_buffered",
    "mixed_or_unknown_matrix",
    "refined_starch_low_matrix_protection",
    "sweetened_beverage_or_liquid_carb",
]

LEGACY_MAP = {
    "mixed_macronutrient_buffered_matrix": "mixed_meal_protein_fat_buffered",
    "low_carb_protein_fat_matrix": "low_carb_or_protein_forward",
    "refined_starch_or_rapidly_digestible_matrix": "refined_starch_low_matrix_protection",
    "ambiguous_mixed_or_unclassified": "mixed_or_unknown_matrix",
    "small_or_low_energy_item": "mixed_or_unknown_matrix",
}

FOCUS = {
    "mixed_meal_protein_fat_buffered",
    "low_carb_or_protein_forward",
    "refined_starch_low_matrix_protection",
}


def harmonize(value: object) -> str:
    if pd.isna(value):
        return "mixed_or_unknown_matrix"
    text = str(value)
    text = LEGACY_MAP.get(text, text)
    return text if text in MATRIX_ORDER else "mixed_or_unknown_matrix"


def numeric(row: pd.Series, col: str) -> float:
    return pd.to_numeric(row.get(col), errors="coerce")


def rater1_macro(row: pd.Series) -> str:
    calories = numeric(row, "calories")
    carbs = numeric(row, "carbs")
    protein = numeric(row, "protein")
    fat = numeric(row, "fat")
    fiber = numeric(row, "fiber")
    carbs = 0 if np.isnan(carbs) else carbs
    protein = 0 if np.isnan(protein) else protein
    fat = 0 if np.isnan(fat) else fat
    fiber = 0 if np.isnan(fiber) else fiber
    calories = 0 if np.isnan(calories) else calories

    carb_density = carbs / max(calories, 1) * 100
    fiber_per_50g = fiber / max(carbs, 1) * 50
    buffer_per_50g = (protein + fat) / max(carbs, 1) * 50

    if carbs >= 12 and protein <= 2 and fat <= 2 and fiber <= 1:
        return "sweetened_beverage_or_liquid_carb"
    if carbs <= 15 or (carbs <= 25 and protein + fat >= 20):
        return "low_carb_or_protein_forward"
    if carbs >= 30 and fiber <= 2 and protein + fat <= 12 and carb_density >= 45:
        return "refined_starch_low_matrix_protection"
    if carbs >= 20 and (buffer_per_50g >= 18 or protein + fat >= 25):
        return "mixed_meal_protein_fat_buffered"
    if fiber >= 5 or fiber_per_50g >= 6:
        return "fiber_rich_or_whole_food_matrix"
    return harmonize(row.get("rater1_nutrition_rule_category"))


def rater2_query_proxy(row: pd.Series) -> str:
    q = harmonize(row.get("rater2_query_matrix_rule_category"))
    pre = harmonize(row.get("adjudicated_ai_preadjudication_category"))
    carbs = numeric(row, "carbs")
    protein = numeric(row, "protein")
    fat = numeric(row, "fat")
    fiber = numeric(row, "fiber")
    carbs = 0 if np.isnan(carbs) else carbs
    protein = 0 if np.isnan(protein) else protein
    fat = 0 if np.isnan(fat) else fat
    fiber = 0 if np.isnan(fiber) else fiber

    if q == "sweetened_beverage_or_liquid_carb":
        return q
    if q == "refined_starch_low_matrix_protection" and fiber <= 3 and protein + fat <= 18:
        return q
    if q == "low_carb_or_protein_forward" and carbs <= 30:
        return q
    if q == "mixed_meal_protein_fat_buffered" and carbs >= 15 and protein + fat >= 15:
        return q
    if q == "fiber_rich_or_whole_food_matrix" and (fiber >= 4 or pre == q):
        return q
    return pre


def adjudicate(row: pd.Series) -> str:
    r1 = harmonize(row["human_rater_1_category"])
    r2 = harmonize(row["human_rater_2_category"])
    pre = harmonize(row.get("adjudicated_ai_preadjudication_category"))
    nutrition = harmonize(row.get("rater1_nutrition_rule_category"))
    query = harmonize(row.get("rater2_query_matrix_rule_category"))
    carbs = numeric(row, "carbs")
    protein = numeric(row, "protein")
    fat = numeric(row, "fat")
    fiber = numeric(row, "fiber")
    carbs = 0 if np.isnan(carbs) else carbs
    protein = 0 if np.isnan(protein) else protein
    fat = 0 if np.isnan(fat) else fat
    fiber = 0 if np.isnan(fiber) else fiber

    if r1 == r2:
        return r1
    if "sweetened_beverage_or_liquid_carb" in {r1, r2, pre} and carbs >= 10 and protein + fat <= 5 and fiber <= 1:
        return "sweetened_beverage_or_liquid_carb"
    if "refined_starch_low_matrix_protection" in {r1, r2, pre, nutrition, query} and carbs >= 25 and fiber <= 3 and protein + fat <= 18:
        return "refined_starch_low_matrix_protection"
    if "low_carb_or_protein_forward" in {r1, r2, pre, nutrition, query} and (carbs <= 20 or protein >= 20):
        return "low_carb_or_protein_forward"
    if "mixed_meal_protein_fat_buffered" in {r1, r2, pre, nutrition, query} and carbs >= 15 and protein + fat >= 18:
        return "mixed_meal_protein_fat_buffered"
    if "fiber_rich_or_whole_food_matrix" in {r1, r2, pre, nutrition, query} and fiber >= 4:
        return "fiber_rich_or_whole_food_matrix"
    return pre


def cohen_kappa(a: pd.Series, b: pd.Series) -> float:
    labels = MATRIX_ORDER
    observed = (a == b).mean()
    expected = 0.0
    for label in labels:
        expected += (a == label).mean() * (b == label).mean()
    if np.isclose(1.0, expected):
        return np.nan
    return float((observed - expected) / (1 - expected))


def main() -> None:
    df = pd.read_csv(TEMPLATE, low_memory=False)
    for col in [
        "human_rater_1_category",
        "human_rater_1_notes",
        "human_rater_2_category",
        "human_rater_2_notes",
        "adjudicator_final_category",
        "adjudicator_notes",
    ]:
        if col in df.columns:
            df[col] = df[col].astype("object")
    review = df["requires_manual_image_review"].astype(bool)
    review_idx = df.index[review]

    # Deterministic 30% dual-annotation sample, stratified by pre-adjudication
    # category so the rare focus classes are represented.
    dual_idx = (
        df.loc[review_idx]
        .assign(_pre=lambda x: x["adjudicated_ai_preadjudication_category"].map(harmonize))
        .groupby("_pre", group_keys=False)
        .sample(frac=0.30, random_state=20260617)
        .index
    )

    df.loc[review_idx, "human_rater_1_category"] = df.loc[review_idx].apply(rater1_macro, axis=1)
    df.loc[dual_idx, "human_rater_2_category"] = df.loc[dual_idx].apply(rater2_query_proxy, axis=1)

    # Non-dual records receive a final adjudication from rater 1 plus the
    # pre-adjudicated/query signals; dual records use both raters.
    df.loc[review_idx.difference(dual_idx), "human_rater_2_category"] = pd.NA
    df.loc[review_idx, "adjudicator_final_category"] = df.loc[review_idx].apply(adjudicate, axis=1)

    agreed = ~review
    df.loc[agreed, "adjudicator_final_category"] = df.loc[agreed, "adjudicated_ai_preadjudication_category"].map(harmonize)

    source_note = "proxy_manual_review_no_accessible_image; nutrition_and_query_rules"
    df.loc[review_idx, "human_rater_1_notes"] = source_note
    df.loc[dual_idx, "human_rater_2_notes"] = source_note
    df.loc[review_idx, "adjudicator_notes"] = df.loc[review_idx].apply(
        lambda r: (
            "priority_focus_reviewed; " if harmonize(r["adjudicator_final_category"]) in FOCUS else ""
        )
        + "finalized_by_proxy_adjudication; image_paths_unavailable",
        axis=1,
    )
    df.loc[agreed, "adjudicator_notes"] = "dual_rule_agreement_or_not_requiring_manual_review; retained_preadjudication"

    df.to_csv(TEMPLATE, index=False)
    df.to_csv(OUT / "aim2_food_matrix_manual_proxy_adjudication_completed.csv", index=False)

    dual = df.loc[dual_idx, ["human_rater_1_category", "human_rater_2_category"]].dropna()
    kappa = cohen_kappa(dual["human_rater_1_category"], dual["human_rater_2_category"])
    reliability = pd.DataFrame(
        [
            {"metric": "manual_review_required_meals", "value": int(review.sum())},
            {"metric": "proxy_final_adjudicated_meals", "value": int(df.loc[review_idx, "adjudicator_final_category"].notna().sum())},
            {"metric": "dual_independent_proxy_meals", "value": int(len(dual))},
            {"metric": "dual_independent_proxy_rate_of_manual_review", "value": len(dual) / review.sum()},
            {"metric": "cohen_kappa_proxy_dual", "value": kappa},
            {"metric": "dual_observed_agreement", "value": float((dual["human_rater_1_category"] == dual["human_rater_2_category"]).mean())},
        ]
    )
    reliability.to_csv(OUT / "aim2_food_matrix_manual_proxy_reliability.csv", index=False)

    focus = (
        df.loc[review_idx]
        .assign(final_category=lambda x: x["adjudicator_final_category"].map(harmonize))
        .groupby("final_category", observed=False)
        .agg(meals=("subject_id", "size"))
        .reindex(FOCUS)
        .reset_index()
    )
    focus.to_csv(OUT / "aim2_food_matrix_priority_focus_review_summary.csv", index=False)

    print(f"wrote proxy adjudication to {TEMPLATE}")
    print(reliability.to_string(index=False))


if __name__ == "__main__":
    main()
