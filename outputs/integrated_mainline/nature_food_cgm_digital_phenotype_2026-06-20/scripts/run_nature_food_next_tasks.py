"""Nature Food next-task package: bridge evidence, Aim 3 prediction, and task board."""

from __future__ import annotations

from pathlib import Path
import json
import textwrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(r"D:\ai for science")
AIM1 = ROOT / "results" / "nature_food_aim1_nhanes"
AIM2 = ROOT / "results" / "nature_food_aim2_cgmacros"
OUT = ROOT / "results" / "nature_food_next_tasks"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def fmt_ci(row: pd.Series, digits: int = 3) -> str:
    return f"{row['effect']:.{digits}f} ({row['effect_low']:.{digits}f}, {row['effect_high']:.{digits}f})"


def build_bridge_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    aim1_main = read_csv(AIM1 / "aim1_main_survey_results.csv")
    aim1_comp = read_csv(AIM1 / "aim1_composition_total_adjusted_survey_results.csv")
    aim1_cycle = read_csv(AIM1 / "aim1_cycle_replication_survey_results.csv")
    aim2_models = read_csv(AIM2 / "aim2_food_matrix_gee_model_results.csv")
    aim2_rel = read_csv(AIM2 / "aim2_food_matrix_annotation_reliability_status.csv")
    aim2_matrix = read_csv(AIM2 / "aim2_food_matrix_category_summary.csv")

    bridge_rows = []
    key_aim1 = aim1_main[
        aim1_main["exposure"].isin(["pct_oxidative_10", "ln_oxidative_to_MEHP", "ilr_oxidative_vs_primary"])
        & aim1_main["outcome"].isin(["msi_core_partial", "ln_HOMA_IR", "HbA1c"])
    ].copy()
    for _, r in key_aim1.iterrows():
        bridge_rows.append(
            {
                "evidence_layer": "Aim 1 NHANES exposure anchor",
                "claim": f"{r['exposure']} -> {r['outcome']}",
                "estimate_ci": fmt_ci(r),
                "q_value": r["q_value"],
                "n": int(r["n"]),
                "interpretation": "DEHP oxidative profile tracks metabolic susceptibility phenotype.",
            }
        )

    comp = aim1_comp[
        aim1_comp["exposure"].isin(["ln_oxidative_MEHP_ratio", "ilr_oxidative_vs_primary"])
        & aim1_comp["outcome"].isin(["msi_core_partial", "ln_HOMA_IR", "HbA1c"])
    ].copy()
    for _, r in comp.iterrows():
        bridge_rows.append(
            {
                "evidence_layer": "Aim 1 composition model",
                "claim": f"{r['exposure']} adjusted for total DEHP -> {r['outcome']}",
                "estimate_ci": fmt_ci(r),
                "q_value": r["q_value"],
                "n": int(r["n"]),
                "interpretation": "Oxidative-vs-primary balance is not explained only by total DEHP burden.",
            }
        )

    cycle_focus = aim1_cycle[
        aim1_cycle["exposure"].isin(["pct_oxidative_10", "ln_oxidative_to_MEHP"])
        & aim1_cycle["outcome"].isin(["msi_core_partial", "ln_HOMA_IR", "HbA1c"])
    ].copy()
    cycle_summary = (
        cycle_focus.assign(direction_positive=cycle_focus["effect"] > 0)
        .groupby(["outcome", "exposure"], as_index=False)
        .agg(cycles=("scenario", "nunique"), positive_cycles=("direction_positive", "sum"), median_q=("q_value", "median"))
    )
    cycle_summary["directional_consistency"] = cycle_summary["positive_cycles"] / cycle_summary["cycles"]
    cycle_summary.to_csv(OUT / "aim1_cycle_directional_consistency.csv", index=False)

    aim2_key = aim2_models[
        (
            (aim2_models["model"].isin(["msi_base", "food_matrix_main", "msi_carb_interaction"]))
            & (
                aim2_models["term"].isin(["msi_core", "msi_core:carbs_10g"])
                | aim2_models["term"].str.contains("mixed_meal_protein_fat_buffered", na=False)
            )
        )
    ].copy()
    for _, r in aim2_key.iterrows():
        bridge_rows.append(
            {
                "evidence_layer": "Aim 2 CGMacros PPGR",
                "claim": f"{r['model']}: {r['term']} -> {r['outcome']}",
                "estimate_ci": r["estimate_CI"],
                "q_value": r["q_value"],
                "n": int(r["n"]),
                "interpretation": "MSI and human-adjudicated food matrix identify PPGR vulnerability in free-living meals.",
            }
        )

    metrics = dict(zip(aim2_rel["metric"], aim2_rel["value"]))
    bridge_rows.append(
        {
            "evidence_layer": "Aim 2 annotation quality",
            "claim": "Human-adjudicated food-matrix labels",
            "estimate_ci": f"coverage={float(metrics.get('human_final_label_coverage', np.nan)):.3f}; kappa={float(metrics.get('cohen_kappa_human_dual_review', np.nan)):.3f}",
            "q_value": np.nan,
            "n": int(float(metrics.get("total_meals", len(aim2_matrix)))),
            "interpretation": "Food-matrix labels are complete; disagreement review and collapsed-class sensitivity remain important.",
        }
    )

    bridge = pd.DataFrame(bridge_rows)
    bridge.to_csv(OUT / "nature_food_cross_dataset_evidence_bridge.csv", index=False)

    readiness = pd.DataFrame(
        [
            {
                "domain": "NHANES exposure anchor",
                "current_status": "strong",
                "evidence": "Survey-weighted oxidative DEHP profile associated with MSI-core, HOMA-IR, HbA1c; composition models retained.",
                "blocking_gap": "Need manuscript-ready figure and concise exposure construction audit.",
                "next_action": "Freeze Figure 2 source data and write methods paragraph.",
            },
            {
                "domain": "CGMacros PPGR vulnerability",
                "current_status": "strong",
                "evidence": "MSI-core robustly predicts log1p iAUC, peak delta, and high iAUC risk.",
                "blocking_gap": "Need prediction/counterfactual translation layer.",
                "next_action": "Run LOSO model ladder and meal redesign candidates.",
            },
            {
                "domain": "Food matrix annotation",
                "current_status": "medium",
                "evidence": "100% final-label coverage; dual-review kappa approximately 0.37.",
                "blocking_gap": "Moderate agreement requires collapsed taxonomy and disagreement sensitivity.",
                "next_action": "Create 3-class collapsed matrix analysis and reviewer audit trail.",
            },
            {
                "domain": "Nature Food translation",
                "current_status": "medium",
                "evidence": "Cross-dataset susceptibility-to-food-context story is coherent.",
                "blocking_gap": "Need direct meal redesign predictions and experimental validation plan.",
                "next_action": "Select matched meal prototypes and quantify predicted PPGR reduction.",
            },
        ]
    )
    readiness.to_csv(OUT / "nature_food_readiness_dashboard.csv", index=False)
    return bridge, readiness


def make_preprocessor(num_cols: list[str], cat_cols: list[str]) -> ColumnTransformer:
    numeric = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    categorical = Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))])
    return ColumnTransformer([("num", numeric, num_cols), ("cat", categorical, cat_cols)], remainder="drop")


def loso_predictions(df: pd.DataFrame, feature_sets: dict[str, dict[str, list[str]]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    records = []
    predictions = []
    subjects = sorted(df["subject_id"].astype(str).unique())
    y_bin = df["high_iauc_2h"].astype(int)
    y_cont = df["log1p_iauc_2h"].astype(float)

    for model_name, spec in feature_sets.items():
        num_cols = [c for c in spec["num"] if c in df.columns]
        cat_cols = [c for c in spec["cat"] if c in df.columns]
        pred_bin = pd.Series(index=df.index, dtype=float)
        pred_cont = pd.Series(index=df.index, dtype=float)
        for sid in subjects:
            test_idx = df.index[df["subject_id"].astype(str) == sid]
            train_idx = df.index.difference(test_idx)
            x_train, x_test = df.loc[train_idx], df.loc[test_idx]
            pre = make_preprocessor(num_cols, cat_cols)
            clf = Pipeline(
                [
                    ("pre", pre),
                    ("model", LogisticRegression(max_iter=2000, class_weight="balanced", solver="lbfgs")),
                ]
            )
            reg = Pipeline([("pre", make_preprocessor(num_cols, cat_cols)), ("model", Ridge(alpha=2.0))])
            clf.fit(x_train, y_bin.loc[train_idx])
            reg.fit(x_train, y_cont.loc[train_idx])
            pred_bin.loc[test_idx] = clf.predict_proba(x_test)[:, 1]
            pred_cont.loc[test_idx] = reg.predict(x_test)

        try:
            auc = roc_auc_score(y_bin, pred_bin)
        except ValueError:
            auc = np.nan
        records.append(
            {
                "model": model_name,
                "features": "; ".join(num_cols + cat_cols),
                "n": len(df),
                "subjects": len(subjects),
                "high_iauc_auc": auc,
                "high_iauc_average_precision": average_precision_score(y_bin, pred_bin),
                "high_iauc_brier": brier_score_loss(y_bin, pred_bin.clip(0, 1)),
                "log1p_iauc_rmse": mean_squared_error(y_cont, pred_cont) ** 0.5,
                "log1p_iauc_mae": mean_absolute_error(y_cont, pred_cont),
            }
        )
        predictions.append(
            pd.DataFrame(
                {
                    "subject_id": df["subject_id"],
                    "meal_time": df.get("meal_time", pd.Series(index=df.index)),
                    "model": model_name,
                    "observed_high_iauc": y_bin,
                    "pred_high_iauc": pred_bin,
                    "observed_log1p_iauc": y_cont,
                    "pred_log1p_iauc": pred_cont,
                }
            )
        )
    metrics = pd.DataFrame(records)
    preds = pd.concat(predictions, ignore_index=True)
    base_auc = metrics.loc[metrics["model"] == "M1_macro_timing", "high_iauc_auc"].iloc[0]
    base_rmse = metrics.loc[metrics["model"] == "M1_macro_timing", "log1p_iauc_rmse"].iloc[0]
    metrics["delta_auc_vs_M1"] = metrics["high_iauc_auc"] - base_auc
    metrics["delta_rmse_vs_M1"] = metrics["log1p_iauc_rmse"] - base_rmse
    metrics.to_csv(OUT / "aim3_loso_model_ladder_metrics.csv", index=False)
    preds.to_csv(OUT / "aim3_loso_oof_predictions.csv", index=False)
    return metrics, preds


def counterfactual_candidates(df: pd.DataFrame) -> pd.DataFrame:
    high_msi = df["msi_core"] >= df["msi_core"].quantile(0.67)
    high_risk = df["high_iauc_2h"].eq(1)
    low_protection = df["food_matrix_final_category"].isin(
        ["mixed_meal_protein_fat_buffered", "refined_starch_low_matrix_protection", "sweetened_beverage_or_liquid_carb"]
    )
    candidates = df.loc[high_msi & high_risk & low_protection].copy()
    if candidates.empty:
        candidates = df.loc[high_msi & high_risk].copy()
    candidates["redesign_target_matrix"] = "fiber_rich_or_whole_food_matrix"
    candidates["redesign_rule"] = np.select(
        [
            candidates["food_matrix_final_category"].eq("sweetened_beverage_or_liquid_carb"),
            candidates["food_matrix_final_category"].eq("refined_starch_low_matrix_protection"),
            candidates["food_matrix_final_category"].eq("mixed_meal_protein_fat_buffered"),
        ],
        [
            "replace liquid/sweetened carbohydrate with intact fruit or unsweetened whole-food carbohydrate",
            "replace refined starch with whole-grain or legume-rich matrix at similar carbohydrate dose",
            "increase intact fiber and reduce rapidly digestible starch while keeping energy comparable",
        ],
        default="increase intact fiber and whole-food structure while keeping carbohydrate dose comparable",
    )
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
        "protein",
        "fat",
        "food_matrix_final_category",
        "food_matrix_final_label",
        "redesign_target_matrix",
        "redesign_rule",
    ]
    cols = [c for c in cols if c in candidates.columns]
    out = candidates.sort_values(["iauc_2h", "peak_delta_2h"], ascending=False).head(40)[cols]
    out.to_csv(OUT / "aim3_counterfactual_meal_redesign_candidates.csv", index=False)
    return out


def make_figures(bridge: pd.DataFrame, readiness: pd.DataFrame, metrics: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    layer_counts = bridge["evidence_layer"].value_counts().sort_values()
    axes[0].barh(layer_counts.index, layer_counts.values, color=["#4E79A7", "#59A14F", "#F28E2B", "#E15759"][: len(layer_counts)])
    axes[0].set_title("Cross-dataset evidence layers")
    axes[0].set_xlabel("Rows in bridge table")
    m = metrics.set_index("model")
    axes[1].plot(m.index, m["high_iauc_auc"], marker="o", label="AUC")
    axes[1].set_ylim(max(0.45, m["high_iauc_auc"].min() - 0.03), min(1.0, m["high_iauc_auc"].max() + 0.03))
    axes[1].set_title("Aim 3 LOSO model ladder")
    axes[1].set_ylabel("High-iAUC AUC")
    axes[1].tick_params(axis="x", rotation=30)
    axes[1].grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG / "nature_food_bridge_and_aim3_ladder.png", dpi=200)
    plt.close(fig)

    color_map = {"strong": "#59A14F", "medium": "#F28E2B", "weak": "#E15759"}
    fig, ax = plt.subplots(figsize=(10, 3.8))
    y = np.arange(len(readiness))
    ax.barh(y, [1] * len(readiness), color=[color_map.get(x, "#999999") for x in readiness["current_status"]])
    ax.set_yticks(y, readiness["domain"])
    ax.set_xticks([])
    ax.set_title("Nature Food readiness dashboard")
    for i, status in enumerate(readiness["current_status"]):
        ax.text(0.5, i, status, va="center", ha="center", color="white", fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIG / "nature_food_readiness_dashboard.png", dpi=200)
    plt.close(fig)


def write_task_board(metrics: pd.DataFrame) -> pd.DataFrame:
    best_model = metrics.sort_values(["high_iauc_auc", "log1p_iauc_rmse"], ascending=[False, True]).iloc[0]["model"]
    tasks = [
        ("NF-NEXT-01", "P0", "Claim", "Freeze Nature Food main claim and overclaim guardrails", "complete", "Evidence bridge and readiness dashboard generated."),
        ("NF-NEXT-02", "P0", "Aim 1", "Convert NHANES survey results into final Figure 2 source data", "next", "Need forest plot and exposure derivation audit."),
        ("NF-NEXT-03", "P0", "Aim 2", "Run collapsed 3-class food-matrix sensitivity", "next", "Moderate kappa makes this essential."),
        ("NF-NEXT-04", "P0", "Aim 2", "Run leave-one-subject-out robustness for GEE key effects", "next", "Protects against 40-subject leverage concerns."),
        ("NF-NEXT-05", "P0", "Aim 3", "Run LOSO model ladder for MSI-aware prediction", "complete", f"Initial best model: {best_model}."),
        ("NF-NEXT-06", "P0", "Aim 3", "Quantify counterfactual meal redesign predictions with fitted model", "in_progress", "Candidate high-risk meals selected; next fit prediction deltas."),
        ("NF-NEXT-07", "P1", "Experiment", "Select matched meal prototype pairs for validation", "next", "Use counterfactual candidates and matrix categories."),
        ("NF-NEXT-08", "P1", "Manuscript", "Draft Results section with exact effect sizes", "next", "Use bridge table and Aim 3 model ladder."),
        ("NF-NEXT-09", "P1", "Reproducibility", "Create figure source-data manifest", "next", "Every panel should map to CSV output."),
    ]
    board = pd.DataFrame(tasks, columns=["task_id", "priority", "workstream", "task", "status", "note"])
    board.to_csv(OUT / "nature_food_next_task_board.csv", index=False)
    return board


def write_manuscript_memo(bridge: pd.DataFrame, readiness: pd.DataFrame, metrics: pd.DataFrame, candidates: pd.DataFrame) -> None:
    best = metrics.sort_values(["high_iauc_auc", "log1p_iauc_rmse"], ascending=[False, True]).iloc[0]
    memo = f"""
# Nature Food 下一阶段执行备忘录

## 主张锁定

本稿不应写成“DEHP 直接导致餐后血糖异常”。更稳妥、更像 Nature Food 的中心主张是：

**塑化剂相关的代谢易感性在人群层面可由 DEHP 氧化代谢谱锚定；在自由生活餐食中，该易感性对应更高 PPGR，并且 PPGR 风险受到人工仲裁食物基质类别的调节，可转化为面向餐食重构的风险降低策略。**

## 已完成的新产物

- `nature_food_cross_dataset_evidence_bridge.csv`：Aim 1 与 Aim 2 的跨数据集证据桥接表。
- `nature_food_readiness_dashboard.csv`：按投稿模块标注 strong/medium 与阻塞缺口。
- `aim3_loso_model_ladder_metrics.csv`：受试者留一的模型阶梯评估。
- `aim3_counterfactual_meal_redesign_candidates.csv`：高 MSI、高 PPGR、低保护食物基质的餐食重构候选。
- `nature_food_next_task_board.csv`：下一阶段任务板。

## Aim 3 初版结果

当前 LOSO 最优模型为 `{best['model']}`：

- high-iAUC AUC: {best['high_iauc_auc']:.3f}
- average precision: {best['high_iauc_average_precision']:.3f}
- Brier score: {best['high_iauc_brier']:.3f}
- log1p iAUC RMSE: {best['log1p_iauc_rmse']:.3f}

餐食重构候选已筛出 {len(candidates)} 条优先记录。下一步应在同一模型框架下生成“原餐 vs 重构餐”的预测差异，而不是只给规则建议。

## 接下来 7 天 P0

1. Aim 2 collapsed matrix：把 6 类人工标签压缩为高保护/中间/低保护三类，重跑 GEE 与模型阶梯。
2. Aim 2 subject leverage：对 MSI-core 和关键食物基质项做 leave-one-subject-out 影响分析。
3. Aim 3 counterfactual delta：用锁定模型估计高 MSI 人群从低保护基质替换到高保护基质的高 iAUC 风险差。
4. Figure source data：生成 Figure 1-4 每个 panel 的 CSV。
5. Results skeleton：用真实数值写 Nature Food Results 初稿，不写泛泛背景。

## 接下来 30 天 P1

1. 人工标签 codebook 定稿，补充双评不一致和少数类复核。
2. 选出 12-16 个等碳水/等能量餐食原型，用于 INFOGEST 或小型 CGM pilot。
3. 准备投稿用限制声明：NHANES 与 CGMacros 是三角验证，不声称个体层面 DEHP 暴露直接预测 CGM。
4. 完成 cover letter 的 novelty paragraph：塑化剂暴露、代谢易感性、自由生活 PPGR 与食物基质重构的跨数据证据链。
"""
    (OUT / "nature_food_next_stage_execution_memo_zh.md").write_text(textwrap.dedent(memo).strip() + "\n", encoding="utf-8")


def main() -> None:
    bridge, readiness = build_bridge_tables()
    df = read_csv(AIM2 / "aim2_modeling_dataset_human_adjudicated.csv")
    df["subject_id"] = df["subject_id"].astype(str)
    feature_sets = {
        "M1_macro_timing": {
            "num": ["carbs_10g", "calories_100", "pre_glucose_10", "meal_hour_sin", "meal_hour_cos"],
            "cat": [],
        },
        "M2_macro_timing_MSI": {
            "num": ["carbs_10g", "calories_100", "pre_glucose_10", "meal_hour_sin", "meal_hour_cos", "msi_core"],
            "cat": [],
        },
        "M3_MSI_food_matrix": {
            "num": ["carbs_10g", "calories_100", "pre_glucose_10", "meal_hour_sin", "meal_hour_cos", "msi_core"],
            "cat": ["food_matrix_final_category"],
        },
        "M4_full_matrix_nutrition": {
            "num": ["carbs_10g", "calories_100", "pre_glucose_10", "meal_hour_sin", "meal_hour_cos", "msi_core", "fiber_5g", "protein_10g", "fat_10g"],
            "cat": ["food_matrix_final_category"],
        },
    }
    metrics, _ = loso_predictions(df, feature_sets)
    candidates = counterfactual_candidates(df)
    make_figures(bridge, readiness, metrics)
    board = write_task_board(metrics)
    write_manuscript_memo(bridge, readiness, metrics, candidates)
    manifest = {
        "outputs": sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file()),
        "n_bridge_rows": int(len(bridge)),
        "n_task_rows": int(len(board)),
        "n_redesign_candidates": int(len(candidates)),
    }
    (OUT / "nature_food_next_tasks_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote Nature Food next-task package to {OUT}")


if __name__ == "__main__":
    main()
