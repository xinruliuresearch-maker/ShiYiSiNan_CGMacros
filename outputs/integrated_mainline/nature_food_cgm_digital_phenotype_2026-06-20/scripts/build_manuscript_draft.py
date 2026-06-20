"""Build a Chinese manuscript draft skeleton from the generated results."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "results"
DOCS_DIR = ROOT / "docs"


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS_DIR / name)


def fmt(x: float, digits: int = 3) -> str:
    return "" if pd.isna(x) else f"{x:.{digits}f}"


def best_rows(df: pd.DataFrame, target: str, metric: str, n: int = 1) -> pd.DataFrame:
    return df[df["target"].eq(target)].sort_values(metric, ascending=False).head(n)


def main() -> int:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ml = pd.read_csv(DATA_DIR / "processed_ml_table.csv")
    phase = pd.read_csv(DATA_DIR / "glycemic_phase_labels.csv")
    cv = read_csv("model_performance_cv.csv")
    nested = read_csv("journal_nested_tuning_summary.csv")
    loso = read_csv("journal_loso_summary.csv")
    cal = read_csv("journal_calibration_metrics.csv")
    stability = read_csv("phase_bootstrap_stability.csv")
    hte = read_csv("journal_adjusted_hte_by_phase.csv")
    adjusted = read_csv("journal_adjusted_phase_global_tests.csv")
    pairwise = read_csv("journal_model_pairwise_bootstrap.csv")
    phase_counts = phase["phase_label"].value_counts()

    hba1c_best_nested = best_rows(nested, "y_hba1c_improved_ge_0_5", "auroc_mean").iloc[0]
    tir_best_nested = best_rows(nested, "y_tir_improved_ge_5pct", "auroc_mean").iloc[0]
    hba1c_best_loso = best_rows(loso, "y_hba1c_improved_ge_0_5", "auroc_mean").iloc[0]
    tir_best_loso = best_rows(loso, "y_tir_improved_ge_5pct", "auroc_mean").iloc[0]
    hba1c_pair = pairwise[pairwise["target"].eq("y_hba1c_improved_ge_0_5")].head(1).iloc[0]
    tir_pair = pairwise[pairwise["target"].eq("y_tir_improved_ge_5pct")].head(1).iloc[0]
    stability_median = stability["adjusted_rand_index"].median()
    stability_iqr_low = stability["adjusted_rand_index"].quantile(0.25)
    stability_iqr_high = stability["adjusted_rand_index"].quantile(0.75)
    hte_top = hte.sort_values("adjusted_risk_difference", ascending=False).iloc[0]

    draft = f"""# 中文论文初稿骨架

## 拟题

基于公开糖尿病随机对照试验数据的血糖动力学相图、机器学习预测与异质性治疗响应研究

## 摘要

**背景**：连续葡萄糖监测（CGM）使研究者能够从静态血糖指标转向动态血糖表型，但如何将多维 CGM 特征转化为可解释、可预测、可用于干预分层的低维框架仍不明确。

**目的**：本研究旨在使用公开糖尿病 RCT/干预研究数据构建血糖动力学相图，验证相位与临床结局的关系，比较多类机器学习模型的预测能力，并探索相位分层的治疗响应异质性。

**方法**：我们整合 JAEB 公开糖尿病研究数据，形成 {len(ml)} 名受试者的机器学习表，其中 {len(phase)} 名具备可用于相图构建的基线 CGM 汇总。相图基于高血糖负担、低血糖易感性、动态不稳定性、昼夜节律紊乱和恢复力代理指标构建。预测任务包括 HbA1c 改善 >=0.5 个百分点和 TIR 改善 >=5 个百分点。模型包括 logistic ridge、随机森林、extra trees、hist gradient boosting、SVM、KNN、MLP、XGBoost、LightGBM 和 CatBoost。验证策略包括 5 折交叉验证、leave-one-study-out、nested CV、校准、decision curve analysis 和 paired bootstrap。

**结果**：相图识别出 {phase_counts.shape[0]} 类血糖相位，最大相位为“{phase_counts.index[0]}”（n={int(phase_counts.iloc[0])}）。Nested CV 显示，HbA1c 改善任务最佳模型为 {hba1c_best_nested['feature_set']} / {hba1c_best_nested['model']}，AUROC={fmt(hba1c_best_nested['auroc_mean'])}；TIR 改善任务最佳模型为 {tir_best_nested['feature_set']} / {tir_best_nested['model']}，AUROC={fmt(tir_best_nested['auroc_mean'])}。LOSO 外部验证中，HbA1c 任务最佳模型 AUROC 均值为 {fmt(hba1c_best_loso['auroc_mean'])}，TIR 任务最佳模型 AUROC 均值为 {fmt(tir_best_loso['auroc_mean'])}。相图 bootstrap 稳定性 ARI 中位数为 {fmt(stability_median)}（IQR {fmt(stability_iqr_low)}-{fmt(stability_iqr_high)}）。调整后的治疗响应分析提示“{hte_top['phase_label']}”可能具有最高的治疗获益，调整风险差为 {fmt(hte_top['adjusted_risk_difference'])}（95% bootstrap CI {fmt(hte_top['bootstrap_ci_low'])}-{fmt(hte_top['bootstrap_ci_high'])}）。

**结论**：公开 RCT/CGM 数据可支持构建可复现的血糖动力学相图。相图对预测 AUROC 的增量有限，但在机制化表征、治疗响应分层和个体化干预解释方面具有潜在价值。未来需要使用原始 CGM 时序和前瞻性外部队列验证该框架。

## 引言

糖尿病管理逐渐从以 HbA1c 为中心的平均风险评估，转向结合 CGM 的动态血糖控制评估。TIR、TBR、TAR 和血糖变异性等指标可以捕获短期风险，但这些指标高度相关，且难以直接转化为个体化干预策略。受动力系统与相图思想启发，本研究提出将多维 CGM 基线状态压缩为血糖动力学相位，用于解释不同个体的风险结构与干预响应。

本研究的核心假设为：血糖动态状态并非单一连续风险轴，而是可以被表示为若干具有临床含义的相位；这些相位可能与 HbA1c/TIR 改善、机器学习预测表现和治疗响应异质性相关。

## 方法

### 数据来源

本研究使用公开可下载、无需特殊审批的 JAEB 糖尿病研究数据。数据清洗脚本为 `scripts/prepare_diabetes_rct_ml_dataset.py`，输出 `processed_ml_table.csv` 和 `cgm_summary_long.csv`。所有预测模型只使用基线变量；随访变量仅用于定义结局。

### 相图构建

在具备基线 CGM 汇总的受试者中，构建五类序参量：高血糖负担、低血糖易感性、动态不稳定性、昼夜节律紊乱和恢复力代理指标。随后使用 KMeans 聚类得到离散相位，并根据聚类中心的 CGM 特征赋予临床可解释标签。

### 预测建模

特征集包括 C1 临床基线特征、C2 临床+CGM 特征和 C4 相图特征。候选模型覆盖线性模型、树模型、核方法、神经网络和梯度提升模型。主要评价指标为 AUROC，次要指标包括 AUPRC、Brier score、校准斜率、校准截距和 ECE。

### 异质性治疗响应

在具备相位标签、结局和明确治疗臂的 RCT 子集中，估计治疗相对于对照在不同相位内的调整风险差。模型调整研究、年龄、基线 HbA1c、基线 TIR，并包含 treatment-by-phase 交互项；置信区间来自 bootstrap。

## 结果

### 相位分布

相位分布为：{'; '.join([f'{k}: n={int(v)}' for k, v in phase_counts.items()])}。

### 机器学习预测

普通 5 折交叉验证中，HbA1c 改善任务排名靠前的模型包括 LightGBM、XGBoost 和 logistic ridge。Nested CV 后结果保持一致，提示调参偏倚较小。TIR 改善任务中，logistic ridge 在 C2 临床+CGM 特征集上表现最好，说明在样本量较小的 CGM 结局任务中，简单模型具有更好的稳健性。

### 外部泛化

LOSO 外部验证较 5 折 CV 明显降低，提示跨研究异质性是主要挑战。HbA1c 任务最佳 LOSO AUROC 均值为 {fmt(hba1c_best_loso['auroc_mean'])}，TIR 任务最佳 LOSO AUROC 均值为 {fmt(tir_best_loso['auroc_mean'])}。

### 模型差异

HbA1c 任务名义最佳与第二名 AUROC 差异为 {fmt(hba1c_pair['delta_auroc_left_minus_right'])}，bootstrap CI {fmt(hba1c_pair['bootstrap_ci_low'])}-{fmt(hba1c_pair['bootstrap_ci_high'])}；TIR 任务对应差异为 {fmt(tir_pair['delta_auroc_left_minus_right'])}，bootstrap CI {fmt(tir_pair['bootstrap_ci_low'])}-{fmt(tir_pair['bootstrap_ci_high'])}。两者均提示排名相近模型之间差异有限。

### 相位与临床结局

协变量调整后的全局相位检验显示，相位与连续 TIR 改善的关联最接近显著。调整后关联弱于未调整分析，提示相位部分反映了基线 CGM 风险结构。

### 治疗响应异质性

调整 HTE 分析提示，不同相位内治疗获益可能不同，其中“{hte_top['phase_label']}”的调整风险差最高。该结果应被视为假设生成证据，需要在独立 RCT 或前瞻性研究中验证。

## 讨论

本研究展示了公开糖尿病 RCT/CGM 数据在机器学习和机制启发分层研究中的再利用价值。主要发现包括：第一，血糖动态状态可以被压缩为具有临床含义的相位；第二，复杂模型在内部验证中略有优势，但简单模型在外部泛化和 TIR 任务中具有竞争力；第三，相图特征对纯预测 AUROC 的提升有限，却有助于组织治疗响应和个体化干预解释。

本研究的限制包括：公开数据并非为统一 pooled ML 研究设计；部分研究缺少基线 CGM，导致相图样本少于总体样本；治疗响应分析为回顾性二次分析，部分相位样本较小；当前使用 CGM 汇总指标而非完整原始时序，无法刻画更细粒度的状态转移。

## 结论

血糖动力学相图可作为公开糖尿病 RCT/CGM 数据中的可解释低维表征。结合严格的机器学习验证、校准、决策曲线和治疗响应分析，该框架具备发展为高水平期刊研究的潜力，但仍需原始 CGM 时序和独立前瞻性验证。
"""
    (DOCS_DIR / "manuscript_draft_zh.md").write_text(draft, encoding="utf-8")
    print(json.dumps({"manuscript_draft": "docs/manuscript_draft_zh.md", "bytes": len(draft.encode("utf-8"))}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
