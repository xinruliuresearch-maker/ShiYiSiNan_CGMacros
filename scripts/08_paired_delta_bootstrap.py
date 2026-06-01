# -*- coding: utf-8 -*-
"""
08_paired_delta_bootstrap.py

升级 3.5：Paired subject-level bootstrap for Δperformance

目标：
1. 基于 outputs/tables/bootstrap_ci_prediction_records.csv 中已保存的预测记录；
2. 对同一批测试餐进行 paired comparison；
3. 以 subject 为 bootstrap 单位计算性能差值的 95% CI；
4. 输出：
   - paired_delta_ablation_results.csv
   - paired_delta_fewshot_results.csv
   - paired_delta_main_summary.csv
   - paired_delta_ablation_mae.png
   - paired_delta_fewshot_mae.png

Δ定义：
- 对误差指标：
  delta_MAE  = MAE(baseline) - MAE(comparator)
  delta_RMSE = RMSE(baseline) - RMSE(comparator)
  > 0 表示 comparator 更好

- 对越大越好的指标：
  delta_R2        = R2(comparator) - R2(baseline)
  delta_Pearson_r = r(comparator) - r(baseline)
  > 0 表示 comparator 更好
"""

from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

warnings.filterwarnings("ignore")


# ============================================================
# 0. 路径与参数
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

PRED_PATH = TABLES / "bootstrap_ci_prediction_records.csv"

N_BOOTSTRAP = 1000
RANDOM_SEED = 42

MODEL = "hist_gradient_boosting"

TARGETS = [
    "iauc_2h",
    "peak_delta_2h",
]

VALIDATIONS = [
    "leave_subject_out",
    "within_subject_temporal_split",
]

FEATURE_SET_ORDER = [
    "M0_meal_only",
    "M1_meal_pre_cgm",
    "M2_meal_pre_cgm_wearable_time",
    "M3_clinical_enhanced",
    "M4_gut_exploratory",
]

FEATURE_SET_LABELS = {
    "M0_meal_only": "M0 Meal only",
    "M1_meal_pre_cgm": "M1 + Pre-CGM",
    "M2_meal_pre_cgm_wearable_time": "M2 + Wearable/time",
    "M3_clinical_enhanced": "M3 + Clinical",
    "M4_gut_exploratory": "M4 + Gut",
}

TARGET_LABELS = {
    "iauc_2h": "2-h glucose iAUC",
    "peak_delta_2h": "2-h peak glucose excursion",
}

TARGET_UNITS = {
    "iauc_2h": "mg/dL·min",
    "peak_delta_2h": "mg/dL",
}

VALIDATION_LABELS = {
    "leave_subject_out": "Leave-subject-out",
    "within_subject_temporal_split": "Within-subject temporal",
    "few_shot_personalization": "Few-shot personalization",
}


# ============================================================
# 1. 指标函数
# ============================================================

def rmse(y_true, y_pred):
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def pearson_r(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    if len(y_true) < 2:
        return np.nan

    if np.nanstd(y_true) == 0 or np.nanstd(y_pred) == 0:
        return np.nan

    return float(np.corrcoef(y_true, y_pred)[0, 1])


def compute_metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[valid]
    y_pred = y_pred[valid]

    if len(y_true) < 2:
        return {
            "MAE": np.nan,
            "RMSE": np.nan,
            "R2": np.nan,
            "Pearson_r": np.nan,
        }

    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": rmse(y_true, y_pred),
        "R2": float(r2_score(y_true, y_pred)),
        "Pearson_r": pearson_r(y_true, y_pred),
    }


def compute_delta_metrics(y_true, pred_base, pred_comp):
    """
    base = baseline model / feature set / shot
    comp = comparator model / feature set / shot

    positive delta means comp is better.
    """
    base = compute_metrics(y_true, pred_base)
    comp = compute_metrics(y_true, pred_comp)

    out = {}

    for metric in ["MAE", "RMSE", "R2", "Pearson_r"]:
        out[f"{metric}_base"] = base[metric]
        out[f"{metric}_comp"] = comp[metric]

    out["delta_MAE"] = base["MAE"] - comp["MAE"]
    out["delta_RMSE"] = base["RMSE"] - comp["RMSE"]
    out["delta_R2"] = comp["R2"] - base["R2"]
    out["delta_Pearson_r"] = comp["Pearson_r"] - base["Pearson_r"]

    out["delta_MAE_percent"] = (
        out["delta_MAE"] / base["MAE"] * 100
        if np.isfinite(base["MAE"]) and base["MAE"] != 0
        else np.nan
    )

    out["delta_RMSE_percent"] = (
        out["delta_RMSE"] / base["RMSE"] * 100
        if np.isfinite(base["RMSE"]) and base["RMSE"] != 0
        else np.nan
    )

    return out


# ============================================================
# 2. 预测记录预处理与配对
# ============================================================

def load_prediction_records():
    if not PRED_PATH.exists():
        raise FileNotFoundError(
            f"Cannot find {PRED_PATH}. Please run scripts/06_bootstrap_ci.py first."
        )

    pred = pd.read_csv(PRED_PATH)

    required = [
        "subject_id",
        "meal_time",
        "target",
        "feature_set",
        "model",
        "validation",
        "shots",
        "y_true",
        "y_pred",
    ]

    missing = [c for c in required if c not in pred.columns]
    if missing:
        raise RuntimeError(f"Missing required columns in prediction records: {missing}")

    pred["subject_id"] = pred["subject_id"].astype(int)
    pred["meal_time"] = pd.to_datetime(pred["meal_time"], errors="coerce")
    pred["meal_time_key"] = pred["meal_time"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # 少数时间解析失败时，用原始字符串兜底
    bad = pred["meal_time_key"].isna()
    if bad.any():
        pred.loc[bad, "meal_time_key"] = pred.loc[bad, "meal_time"].astype(str)

    pred["y_true"] = pd.to_numeric(pred["y_true"], errors="coerce")
    pred["y_pred"] = pd.to_numeric(pred["y_pred"], errors="coerce")

    return pred


def prepare_for_pairing(df, group_keys):
    """
    防止同一 subject_id + meal_time_key 出现极少量重复导致 merge 交叉膨胀。
    对重复项取 y_true/y_pred 均值。
    """
    keep_cols = group_keys + ["y_true", "y_pred"]

    temp = df[keep_cols].copy()
    temp = temp.dropna(subset=["subject_id", "meal_time_key", "y_true", "y_pred"])

    agg = (
        temp
        .groupby(group_keys, dropna=False, as_index=False)
        .agg(
            y_true=("y_true", "mean"),
            y_pred=("y_pred", "mean"),
        )
    )

    return agg


def build_ablation_pair(pred, target, validation, base_feature_set, comp_feature_set, model=MODEL):
    """
    配对比较两个 feature set：
    例如 M3 vs M2。
    """
    base = pred[
        (pred["target"] == target)
        & (pred["validation"] == validation)
        & (pred["model"] == model)
        & (pred["feature_set"] == base_feature_set)
    ].copy()

    comp = pred[
        (pred["target"] == target)
        & (pred["validation"] == validation)
        & (pred["model"] == model)
        & (pred["feature_set"] == comp_feature_set)
    ].copy()

    keys = ["subject_id", "meal_time_key", "target", "model", "validation"]

    base = prepare_for_pairing(base, keys)
    comp = prepare_for_pairing(comp, keys)

    pair = base.merge(
        comp,
        on=keys,
        how="inner",
        suffixes=("_base", "_comp"),
    )

    if pair.empty:
        return pair

    # y_true 应完全一致；这里取均值兜底
    pair["y_true"] = (pair["y_true_base"] + pair["y_true_comp"]) / 2.0

    pair["base_label"] = base_feature_set
    pair["comp_label"] = comp_feature_set
    pair["comparison"] = f"{comp_feature_set} vs {base_feature_set}"

    return pair


def build_fewshot_pair(pred, target, base_shots, comp_shots, feature_set="M3_clinical_enhanced", model=MODEL):
    """
    配对比较 few-shot：
    例如 10-shot vs 0-shot。

    注意：
    这里会自动只保留共同测试餐次。
    因此 0-shot 的指标可能与之前 Table 3 中全测试餐的 0-shot 指标略有差异。
    """
    base = pred[
        (pred["target"] == target)
        & (pred["validation"] == "few_shot_personalization")
        & (pred["model"] == model)
        & (pred["feature_set"] == feature_set)
        & (pred["shots"].astype(float) == float(base_shots))
    ].copy()

    comp = pred[
        (pred["target"] == target)
        & (pred["validation"] == "few_shot_personalization")
        & (pred["model"] == model)
        & (pred["feature_set"] == feature_set)
        & (pred["shots"].astype(float) == float(comp_shots))
    ].copy()

    keys = ["subject_id", "meal_time_key", "target", "model", "validation", "feature_set"]

    base = prepare_for_pairing(base, keys)
    comp = prepare_for_pairing(comp, keys)

    pair = base.merge(
        comp,
        on=keys,
        how="inner",
        suffixes=("_base", "_comp"),
    )

    if pair.empty:
        return pair

    pair["y_true"] = (pair["y_true_base"] + pair["y_true_comp"]) / 2.0

    pair["base_label"] = f"{base_shots}-shot"
    pair["comp_label"] = f"{comp_shots}-shot"
    pair["comparison"] = f"{comp_shots}-shot vs {base_shots}-shot"
    pair["base_shots"] = int(base_shots)
    pair["comp_shots"] = int(comp_shots)

    return pair


# ============================================================
# 3. Paired subject-level bootstrap
# ============================================================

def paired_subject_bootstrap(pair_df, n_bootstrap=N_BOOTSTRAP, seed=RANDOM_SEED):
    """
    对已经配对好的预测记录做 subject-level bootstrap。

    pair_df 必须包含：
    subject_id, y_true, y_pred_base, y_pred_comp
    """
    rng = np.random.default_rng(seed)

    subject_ids = np.array(sorted(pair_df["subject_id"].dropna().unique()))
    n_subjects = len(subject_ids)

    if n_subjects < 2:
        raise RuntimeError("Not enough subjects for bootstrap.")

    point = compute_delta_metrics(
        pair_df["y_true"].values,
        pair_df["y_pred_base"].values,
        pair_df["y_pred_comp"].values,
    )

    grouped = {
        sid: pair_df[pair_df["subject_id"] == sid]
        for sid in subject_ids
    }

    boot_rows = []

    for _ in range(n_bootstrap):
        sampled_subjects = rng.choice(subject_ids, size=n_subjects, replace=True)

        sampled_parts = [grouped[sid] for sid in sampled_subjects]
        sampled = pd.concat(sampled_parts, axis=0, ignore_index=True)

        m = compute_delta_metrics(
            sampled["y_true"].values,
            sampled["y_pred_base"].values,
            sampled["y_pred_comp"].values,
        )

        boot_rows.append(m)

    boot = pd.DataFrame(boot_rows)

    summary = {}

    for metric in [
        "MAE_base",
        "MAE_comp",
        "RMSE_base",
        "RMSE_comp",
        "R2_base",
        "R2_comp",
        "Pearson_r_base",
        "Pearson_r_comp",
        "delta_MAE",
        "delta_RMSE",
        "delta_R2",
        "delta_Pearson_r",
        "delta_MAE_percent",
        "delta_RMSE_percent",
    ]:
        values = boot[metric].astype(float).replace([np.inf, -np.inf], np.nan).dropna()

        summary[metric] = point.get(metric, np.nan)
        summary[f"{metric}_ci_lower"] = float(np.percentile(values, 2.5)) if len(values) else np.nan
        summary[f"{metric}_ci_upper"] = float(np.percentile(values, 97.5)) if len(values) else np.nan
        summary[f"{metric}_boot_mean"] = float(values.mean()) if len(values) else np.nan
        summary[f"{metric}_boot_sd"] = float(values.std(ddof=1)) if len(values) > 1 else np.nan

    summary["n_subjects"] = int(n_subjects)
    summary["n_meals_paired"] = int(len(pair_df))
    summary["n_bootstrap"] = int(n_bootstrap)

    return summary


# ============================================================
# 4. 批量比较
# ============================================================

def run_ablation_delta(pred):
    rows = []

    stepwise_pairs = [
        ("M0_meal_only", "M1_meal_pre_cgm", "M1_vs_M0_pre_cgm_gain"),
        ("M1_meal_pre_cgm", "M2_meal_pre_cgm_wearable_time", "M2_vs_M1_wearable_time_gain"),
        ("M2_meal_pre_cgm_wearable_time", "M3_clinical_enhanced", "M3_vs_M2_clinical_gain"),
        ("M3_clinical_enhanced", "M4_gut_exploratory", "M4_vs_M3_gut_gain"),
    ]

    for target in TARGETS:
        for validation in VALIDATIONS:
            for base_fs, comp_fs, comparison_id in stepwise_pairs:
                print(f"Ablation paired delta: {target} | {validation} | {comp_fs} vs {base_fs}")

                pair = build_ablation_pair(
                    pred,
                    target=target,
                    validation=validation,
                    base_feature_set=base_fs,
                    comp_feature_set=comp_fs,
                    model=MODEL,
                )

                if pair.empty:
                    print("  skipped: no paired records")
                    continue

                summary = paired_subject_bootstrap(pair)

                summary.update({
                    "analysis": "ablation_stepwise",
                    "comparison_id": comparison_id,
                    "target": target,
                    "validation": validation,
                    "model": MODEL,
                    "baseline": base_fs,
                    "comparator": comp_fs,
                    "baseline_label": FEATURE_SET_LABELS.get(base_fs, base_fs),
                    "comparator_label": FEATURE_SET_LABELS.get(comp_fs, comp_fs),
                    "comparison": f"{FEATURE_SET_LABELS.get(comp_fs, comp_fs)} vs {FEATURE_SET_LABELS.get(base_fs, base_fs)}",
                })

                rows.append(summary)

    out = pd.DataFrame(rows)
    return out


def run_fewshot_delta(pred):
    rows = []

    # 与 0-shot 比较：最适合写主结果
    vs_zero_pairs = [
        (0, 1, "1shot_vs_0shot"),
        (0, 3, "3shot_vs_0shot"),
        (0, 5, "5shot_vs_0shot"),
        (0, 10, "10shot_vs_0shot"),
    ]

    # 阶梯式比较：用于补充材料
    stepwise_pairs = [
        (0, 1, "1shot_vs_0shot_step"),
        (1, 3, "3shot_vs_1shot_step"),
        (3, 5, "5shot_vs_3shot_step"),
        (5, 10, "10shot_vs_5shot_step"),
    ]

    all_pairs = []

    for base, comp, cid in vs_zero_pairs:
        all_pairs.append((base, comp, cid, "vs_zero"))

    for base, comp, cid in stepwise_pairs:
        all_pairs.append((base, comp, cid, "stepwise"))

    for target in TARGETS:
        for base_shots, comp_shots, comparison_id, comparison_type in all_pairs:
            print(f"Few-shot paired delta: {target} | {comp_shots}-shot vs {base_shots}-shot")

            pair = build_fewshot_pair(
                pred,
                target=target,
                base_shots=base_shots,
                comp_shots=comp_shots,
                feature_set="M3_clinical_enhanced",
                model=MODEL,
            )

            if pair.empty:
                print("  skipped: no paired records")
                continue

            summary = paired_subject_bootstrap(pair)

            summary.update({
                "analysis": "fewshot",
                "comparison_type": comparison_type,
                "comparison_id": comparison_id,
                "target": target,
                "validation": "few_shot_personalization",
                "model": MODEL,
                "feature_set": "M3_clinical_enhanced",
                "baseline_shots": int(base_shots),
                "comparator_shots": int(comp_shots),
                "baseline": f"{base_shots}-shot",
                "comparator": f"{comp_shots}-shot",
                "baseline_label": f"{base_shots}-shot",
                "comparator_label": f"{comp_shots}-shot",
                "comparison": f"{comp_shots}-shot vs {base_shots}-shot",
            })

            rows.append(summary)

    out = pd.DataFrame(rows)
    return out


# ============================================================
# 5. 作图
# ============================================================

def plot_ablation_delta(ablation_df):
    if ablation_df.empty:
        return

    for target in TARGETS:
        sub_target = ablation_df[
            (ablation_df["target"] == target)
            & (ablation_df["validation"].isin(VALIDATIONS))
        ].copy()

        if sub_target.empty:
            continue

        fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)

        for ax, validation in zip(axes, VALIDATIONS):
            sub = sub_target[sub_target["validation"] == validation].copy()

            # 固定顺序
            order = [
                "M1_vs_M0_pre_cgm_gain",
                "M2_vs_M1_wearable_time_gain",
                "M3_vs_M2_clinical_gain",
                "M4_vs_M3_gut_gain",
            ]

            sub["order"] = sub["comparison_id"].map({x: i for i, x in enumerate(order)})
            sub = sub.sort_values("order")

            x = np.arange(len(sub))
            y = sub["delta_MAE"].values
            yerr_lower = y - sub["delta_MAE_ci_lower"].values
            yerr_upper = sub["delta_MAE_ci_upper"].values - y
            yerr = np.vstack([yerr_lower, yerr_upper])

            labels = [
                "M1-M0\nPre-CGM",
                "M2-M1\nWearable/time",
                "M3-M2\nClinical",
                "M4-M3\nGut",
            ]

            ax.axhline(0, linestyle="--", linewidth=1)
            ax.errorbar(x, y, yerr=yerr, marker="o", capsize=4, linewidth=1.5)
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.set_title(VALIDATION_LABELS.get(validation, validation))
            ax.set_ylabel(f"ΔMAE improvement ({TARGET_UNITS[target]})")
            ax.set_xlabel("Stepwise feature-set comparison")

        fig.suptitle(
            f"Paired subject-level bootstrap Δperformance: {TARGET_LABELS[target]}",
            fontsize=14,
            fontweight="bold",
        )
        fig.tight_layout()

        out = FIGURES / f"paired_delta_ablation_mae_{target}.png"
        fig.savefig(out, dpi=300, bbox_inches="tight")
        plt.close(fig)


def plot_fewshot_delta(fewshot_df):
    if fewshot_df.empty:
        return

    df = fewshot_df[fewshot_df["comparison_type"] == "vs_zero"].copy()

    for target in TARGETS:
        sub = df[df["target"] == target].copy()
        sub = sub.sort_values("comparator_shots")

        if sub.empty:
            continue

        x = sub["comparator_shots"].values.astype(float)
        y = sub["delta_MAE"].values
        yerr_lower = y - sub["delta_MAE_ci_lower"].values
        yerr_upper = sub["delta_MAE_ci_upper"].values - y
        yerr = np.vstack([yerr_lower, yerr_upper])

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.axhline(0, linestyle="--", linewidth=1)
        ax.errorbar(x, y, yerr=yerr, marker="o", capsize=4, linewidth=1.5)

        ax.set_xticks(x)
        ax.set_xlabel("Comparator shots versus 0-shot")
        ax.set_ylabel(f"ΔMAE improvement ({TARGET_UNITS[target]})")
        ax.set_title(
            f"Paired Δperformance for few-shot personalization\n{TARGET_LABELS[target]}"
        )

        fig.tight_layout()

        out = FIGURES / f"paired_delta_fewshot_mae_{target}.png"
        fig.savefig(out, dpi=300, bbox_inches="tight")
        plt.close(fig)


# ============================================================
# 6. 结果格式化
# ============================================================

def format_ci(point, low, high, digits=1):
    if pd.isna(point) or pd.isna(low) or pd.isna(high):
        return ""
    return f"{point:.{digits}f} [{low:.{digits}f}, {high:.{digits}f}]"


def make_main_summary(ablation_df, fewshot_df):
    rows = []

    # 主比较 1：M3 vs M2
    m3_m2 = ablation_df[
        ablation_df["comparison_id"] == "M3_vs_M2_clinical_gain"
    ].copy()

    for _, r in m3_m2.iterrows():
        rows.append({
            "section": "Ablation",
            "comparison": r["comparison"],
            "target": TARGET_LABELS.get(r["target"], r["target"]),
            "validation": VALIDATION_LABELS.get(r["validation"], r["validation"]),
            "ΔMAE improvement [95% CI]": format_ci(
                r["delta_MAE"], r["delta_MAE_ci_lower"], r["delta_MAE_ci_upper"], 1
            ),
            "ΔMAE improvement, % [95% CI]": format_ci(
                r["delta_MAE_percent"],
                r["delta_MAE_percent_ci_lower"],
                r["delta_MAE_percent_ci_upper"],
                1,
            ),
            "ΔPearson r [95% CI]": format_ci(
                r["delta_Pearson_r"],
                r["delta_Pearson_r_ci_lower"],
                r["delta_Pearson_r_ci_upper"],
                3,
            ),
            "n_subjects": r["n_subjects"],
            "n_paired_meals": r["n_meals_paired"],
            "interpretation": "Clinical baseline gain",
        })

    # 主比较 2：M4 vs M3
    m4_m3 = ablation_df[
        ablation_df["comparison_id"] == "M4_vs_M3_gut_gain"
    ].copy()

    for _, r in m4_m3.iterrows():
        rows.append({
            "section": "Ablation",
            "comparison": r["comparison"],
            "target": TARGET_LABELS.get(r["target"], r["target"]),
            "validation": VALIDATION_LABELS.get(r["validation"], r["validation"]),
            "ΔMAE improvement [95% CI]": format_ci(
                r["delta_MAE"], r["delta_MAE_ci_lower"], r["delta_MAE_ci_upper"], 1
            ),
            "ΔMAE improvement, % [95% CI]": format_ci(
                r["delta_MAE_percent"],
                r["delta_MAE_percent_ci_lower"],
                r["delta_MAE_percent_ci_upper"],
                1,
            ),
            "ΔPearson r [95% CI]": format_ci(
                r["delta_Pearson_r"],
                r["delta_Pearson_r_ci_lower"],
                r["delta_Pearson_r_ci_upper"],
                3,
            ),
            "n_subjects": r["n_subjects"],
            "n_paired_meals": r["n_meals_paired"],
            "interpretation": "Gut exploratory gain",
        })

    # 主比较 3：10-shot vs 0-shot
    fs10 = fewshot_df[
        (fewshot_df["comparison_id"] == "10shot_vs_0shot")
        & (fewshot_df["comparison_type"] == "vs_zero")
    ].copy()

    for _, r in fs10.iterrows():
        rows.append({
            "section": "Few-shot",
            "comparison": r["comparison"],
            "target": TARGET_LABELS.get(r["target"], r["target"]),
            "validation": "Few-shot personalization",
            "ΔMAE improvement [95% CI]": format_ci(
                r["delta_MAE"], r["delta_MAE_ci_lower"], r["delta_MAE_ci_upper"], 1
            ),
            "ΔMAE improvement, % [95% CI]": format_ci(
                r["delta_MAE_percent"],
                r["delta_MAE_percent_ci_lower"],
                r["delta_MAE_percent_ci_upper"],
                1,
            ),
            "ΔPearson r [95% CI]": format_ci(
                r["delta_Pearson_r"],
                r["delta_Pearson_r_ci_lower"],
                r["delta_Pearson_r_ci_upper"],
                3,
            ),
            "n_subjects": r["n_subjects"],
            "n_paired_meals": r["n_meals_paired"],
            "interpretation": "10-shot personalization gain",
        })

    summary = pd.DataFrame(rows)
    return summary


# ============================================================
# 7. 主流程
# ============================================================

def main():
    print("Loading prediction records...")
    pred = load_prediction_records()
    print("Prediction records:", pred.shape)

    print("\nRunning paired ablation delta bootstrap...")
    ablation_df = run_ablation_delta(pred)

    print("\nRunning paired few-shot delta bootstrap...")
    fewshot_df = run_fewshot_delta(pred)

    ablation_path = TABLES / "paired_delta_ablation_results.csv"
    fewshot_path = TABLES / "paired_delta_fewshot_results.csv"

    ablation_df.to_csv(ablation_path, index=False, encoding="utf-8-sig")
    fewshot_df.to_csv(fewshot_path, index=False, encoding="utf-8-sig")

    print("\nSaved:")
    print(ablation_path)
    print(fewshot_path)

    main_summary = make_main_summary(ablation_df, fewshot_df)
    summary_path = TABLES / "paired_delta_main_summary.csv"
    main_summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print(summary_path)

    # Figures
    plot_ablation_delta(ablation_df)
    plot_fewshot_delta(fewshot_df)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 260)
    pd.set_option("display.max_rows", 300)

    print("\nMain paired delta summary:")
    print(main_summary)

    print("\nAblation paired delta results:")
    print(ablation_df[[
        "target",
        "validation",
        "comparison_id",
        "comparison",
        "delta_MAE",
        "delta_MAE_ci_lower",
        "delta_MAE_ci_upper",
        "delta_MAE_percent",
        "delta_MAE_percent_ci_lower",
        "delta_MAE_percent_ci_upper",
        "delta_Pearson_r",
        "delta_Pearson_r_ci_lower",
        "delta_Pearson_r_ci_upper",
        "n_subjects",
        "n_meals_paired",
    ]])

    print("\nFew-shot paired delta results:")
    print(fewshot_df[[
        "target",
        "comparison_type",
        "comparison_id",
        "comparison",
        "delta_MAE",
        "delta_MAE_ci_lower",
        "delta_MAE_ci_upper",
        "delta_MAE_percent",
        "delta_MAE_percent_ci_lower",
        "delta_MAE_percent_ci_upper",
        "delta_Pearson_r",
        "delta_Pearson_r_ci_lower",
        "delta_Pearson_r_ci_upper",
        "n_subjects",
        "n_meals_paired",
    ]])

    print("\nFigures saved to:")
    print(FIGURES)

    print("\nDone.")


if __name__ == "__main__":
    main()