"""Build high-bar Nature Food Aim 1-3 execution package.

This creates executable protocols, sampling frames, analysis plans, and locked
preliminary evidence summaries without fabricating uncollected experimental data.
"""

from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd


ROOT = Path(r"D:\ai for science")
OUT = ROOT / "results" / "nature_food_high_bar_aims"
DOCS = OUT / "docs"
TEMPLATES = OUT / "templates"
FIGSRC = OUT / "figure_source_data_templates"
for p in [OUT, DOCS, TEMPLATES, FIGSRC]:
    p.mkdir(parents=True, exist_ok=True)

AIM1 = ROOT / "results" / "nature_food_aim1_nhanes"
AIM2 = ROOT / "results" / "nature_food_aim2_cgmacros"
P0 = ROOT / "results" / "nature_food_p0_robustness"
MSPKG = ROOT / "results" / "nature_food_manuscript_package"


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def write(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def aim1_existing_anchor() -> pd.DataFrame:
    main = read(AIM1 / "aim1_main_survey_results.csv")
    comp = read(AIM1 / "aim1_composition_total_adjusted_survey_results.csv")
    key = main[
        main["exposure"].isin(["pct_oxidative_10", "ln_oxidative_to_MEHP", "ilr_oxidative_vs_primary"])
        & main["outcome"].isin(["msi_core_partial", "ln_HOMA_IR", "HbA1c"])
    ].copy()
    key["evidence_type"] = "NHANES survey-weighted anchor"
    comp_key = comp[
        comp["exposure"].isin(["ln_oxidative_MEHP_ratio", "ilr_oxidative_vs_primary"])
        & comp["outcome"].isin(["msi_core_partial", "ln_HOMA_IR", "HbA1c"])
    ].copy()
    comp_key["evidence_type"] = "composition adjusted for total DEHP"
    out = pd.concat([key, comp_key], ignore_index=True)
    out["effect_CI"] = out.apply(
        lambda r: f"{r['effect']:.3f} ({r['effect_low']:.3f}, {r['effect_high']:.3f})",
        axis=1,
    )
    out.to_csv(OUT / "aim1_nhanes_dehp_msi_anchor_locked.csv", index=False)
    return out


def build_food_sampling_frame() -> pd.DataFrame:
    strata = [
        ("S01", "fresh whole-food control", "apple/banana/whole vegetables", "protective_whole_food_or_low_carb", "none_or_paper", "minimally_processed", "low", "solid", "no_heat_contact"),
        ("S02", "whole-grain or legume packaged", "whole-grain bread/legume bowl", "protective_whole_food_or_low_carb", "plastic_film_or_bowl", "processed", "low", "solid", "no_heat_contact"),
        ("S03", "high-fat dairy plastic-packaged", "yogurt/cream dessert", "mixed_buffered_or_unknown", "plastic_cup", "processed", "high", "semi_solid", "no_heat_contact"),
        ("S04", "processed meat or cheese", "deli meat/cheese", "mixed_buffered_or_unknown", "plastic_vacuum_pack", "processed", "high", "solid", "no_heat_contact"),
        ("S05", "takeaway hot meal plastic contact", "rice/noodle/meat bowl", "mixed_buffered_or_unknown", "polypropylene_takeaway", "restaurant_processed", "medium", "mixed", "hot_contact"),
        ("S06", "microwave-ready plastic tray", "frozen entree", "mixed_buffered_or_unknown", "plastic_tray", "ultra_processed_like", "medium", "mixed", "heated_in_package"),
        ("S07", "refined starch packaged", "white bread/crackers/noodles", "rapid_digestible_or_liquid_carb", "plastic_film", "ultra_processed_like", "low", "solid", "no_heat_contact"),
        ("S08", "sweetened beverage PET", "sweetened tea/soda/sports drink", "rapid_digestible_or_liquid_carb", "PET_bottle", "ultra_processed_like", "low", "liquid", "no_heat_contact"),
        ("S09", "hot beverage plastic-lid contact", "takeaway coffee/milk tea", "rapid_digestible_or_liquid_carb", "coated_cup_plastic_lid", "restaurant_processed", "medium", "liquid", "hot_contact"),
        ("S10", "ready-to-eat salad plastic bowl", "salad/fruit cup", "protective_whole_food_or_low_carb", "plastic_bowl", "minimally_processed", "low", "mixed", "no_heat_contact"),
        ("S11", "oily snack plastic-packaged", "chips/pastry", "mixed_buffered_or_unknown", "plastic_film", "ultra_processed_like", "high", "solid", "no_heat_contact"),
        ("S12", "freshly prepared low-packaging matched meal", "rice/pasta/protein cooked in glass/steel", "mixed_buffered_or_unknown", "glass_or_steel", "home_prepared", "medium", "mixed", "no_plastic_heat_contact"),
    ]
    rows = []
    for sid, label, item, matrix, packaging, processing, fat, form, heat in strata:
        for rep in range(1, 9):
            rows.append(
                {
                    "sample_id": f"NF-A1-{sid}-{rep:02d}",
                    "stratum_id": sid,
                    "food_system_stratum": label,
                    "example_item": item,
                    "matrix_collapsed3": matrix,
                    "packaging_contact": packaging,
                    "processing_level": processing,
                    "fat_level": fat,
                    "physical_form": form,
                    "plastic_heat_contact": heat,
                    "planned_replicate": rep,
                    "target_status": "to_collect",
                    "measure_parent_plasticizers": "DEHP; DiNP; DiDP; DBP; DiBP; BBzP; DINCH; DEHT",
                    "measure_food_macros": "energy; carbohydrate; sugars; fiber; protein; fat; moisture",
                    "primary_contrast": "packaging/processing/matrix gradient",
                }
            )
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "aim1_food_plasticizer_sampling_frame_96_samples.csv", index=False)
    return df


def build_templates() -> None:
    metadata_cols = [
        "sample_id",
        "collection_date",
        "city",
        "store_or_vendor_type",
        "brand_or_vendor_blinded_id",
        "food_name",
        "lot_or_batch",
        "serving_size_g",
        "package_material_primary",
        "package_material_secondary",
        "time_in_package_days_estimated",
        "heated_in_original_packaging",
        "serving_temperature",
        "processing_level",
        "matrix_collapsed3",
        "fat_g_per_100g",
        "carb_g_per_100g",
        "fiber_g_per_100g",
        "moisture_percent",
        "field_blank_id",
        "lab_batch",
        "dehp_ng_g",
        "dinp_ng_g",
        "didp_ng_g",
        "dbp_ng_g",
        "bbzp_ng_g",
        "dinch_ng_g",
        "deht_ng_g",
        "measurement_status",
        "notes",
    ]
    pd.DataFrame(columns=metadata_cols).to_csv(TEMPLATES / "aim1_food_sample_metadata_template.csv", index=False)

    panel = pd.DataFrame(
        [
            ("DEHP", "parent plasticizer in food", "primary", "ng/g wet weight", "field blank, duplicate, matrix spike"),
            ("DiNP", "parent plasticizer in food", "secondary", "ng/g wet weight", "field blank, duplicate, matrix spike"),
            ("DiDP", "parent plasticizer in food", "secondary", "ng/g wet weight", "field blank, duplicate, matrix spike"),
            ("DBP", "parent plasticizer in food", "secondary", "ng/g wet weight", "field blank, duplicate, matrix spike"),
            ("DiBP", "parent plasticizer in food", "secondary", "ng/g wet weight", "field blank, duplicate, matrix spike"),
            ("BBzP", "parent plasticizer in food", "secondary", "ng/g wet weight", "field blank, duplicate, matrix spike"),
            ("DINCH", "alternative plasticizer in food", "secondary", "ng/g wet weight", "field blank, duplicate, matrix spike"),
            ("DEHT", "alternative plasticizer in food", "secondary", "ng/g wet weight", "field blank, duplicate, matrix spike"),
            ("MEHP", "urinary DEHP metabolite", "human exposure", "ng/mL and creatinine-corrected", "urine QC pool, duplicate"),
            ("MEHHP", "urinary oxidative DEHP metabolite", "human exposure", "ng/mL and creatinine-corrected", "urine QC pool, duplicate"),
            ("MEOHP", "urinary oxidative DEHP metabolite", "human exposure", "ng/mL and creatinine-corrected", "urine QC pool, duplicate"),
            ("MECPP", "urinary oxidative DEHP metabolite", "human exposure", "ng/mL and creatinine-corrected", "urine QC pool, duplicate"),
        ],
        columns=["analyte", "role", "priority", "unit", "minimum_qc"],
    )
    panel.to_csv(OUT / "aim1_plasticizer_measurement_panel.csv", index=False)


def build_exposure_chain() -> None:
    nodes = pd.DataFrame(
        [
            ("N1", "Food system source", "packaging, processing, heat contact, fat-rich matrix"),
            ("N2", "Food plasticizer burden", "parent plasticizer concentration in food"),
            ("N3", "Human internal exposure", "urinary DEHP metabolites and oxidative profile"),
            ("N4", "Metabolic susceptibility", "MSI-core, HOMA-IR, HbA1c"),
            ("N5", "Food matrix context", "protective vs mixed vs rapid-digestible matrix"),
            ("N6", "PPGR vulnerability", "2h iAUC, peak delta, high-response meal"),
            ("N7", "Meal redesign", "equal-carb/equal-energy matrix substitution"),
        ],
        columns=["node_id", "node_label", "definition"],
    )
    edges = pd.DataFrame(
        [
            ("N1", "N2", "measured in food panel"),
            ("N2", "N3", "validated in prospective urine substudy"),
            ("N3", "N4", "NHANES and pilot metabolic anchor"),
            ("N4", "N6", "CGMacros and prospective CGM"),
            ("N5", "N6", "GEE, standard meal challenge"),
            ("N7", "N6", "counterfactual, digestion, human validation"),
        ],
        columns=["source", "target", "evidence_required"],
    )
    nodes.to_csv(OUT / "aim1_food_system_exposure_chain_nodes.csv", index=False)
    edges.to_csv(OUT / "aim1_food_system_exposure_chain_edges.csv", index=False)
    mermaid = """
# 食品系统暴露链条图

```mermaid
flowchart LR
  N1["Food system source<br/>packaging/processing/heat/fat"] --> N2["Food plasticizer burden<br/>parent compounds in food"]
  N2 --> N3["Internal exposure<br/>urinary DEHP metabolites"]
  N3 --> N4["Metabolic susceptibility<br/>MSI/HOMA-IR/HbA1c"]
  N5["Food matrix context<br/>protective/mixed/rapid"] --> N6["PPGR vulnerability<br/>iAUC/peak/high response"]
  N4 --> N6
  N7["Meal redesign<br/>equal carb/energy matrix change"] --> N6
```
"""
    write(DOCS / "aim1_food_system_exposure_chain_figure.md", mermaid)


def aim1_docs() -> None:
    write(
        DOCS / "aim1_food_plasticizer_lab_assay_brief.md",
        """
# Aim 1 食品 plasticizer panel 检测说明

## 目标

建立食品系统塑化剂暴露层，而不是只依赖 NHANES 尿代谢物。检测对象是市场真实食品中的 parent plasticizer burden，并将其与包装、加工、热接触、脂肪含量和食物基质连接。

## 样本

- 96 个计划样本，12 个食品系统 strata，每个 stratum 8 个独立样本。
- 每批加入 field blank、运输 blank、实验室 blank、duplicate、matrix spike。
- 所有样本记录包装材质、加热接触、加工等级、物理形态、脂肪/碳水/纤维。

## 分析物

Primary: DEHP。

Secondary: DiNP、DiDP、DBP、DiBP、BBzP、DINCH、DEHT。

人体尿样对应：MEHP、MEHHP、MEOHP、MECPP；计算 Sigma DEHP、percent oxidative、oxidative/MEHP ratio、ILR oxidative-vs-primary。

## 实验室要求

- 使用经验证的 targeted MS 方法；食品样本报告 ng/g wet weight。
- 报告 LOD/LOQ、回收率、批次、空白校正规则。
- 对脂肪高、液体、固体基质分别提供 matrix spike recovery。
- 低于 LOD 的值保留原始标志，分析中使用 LOD/sqrt(2) 和 censored-model sensitivity。

## 主分析

log10(plasticizer concentration) ~ packaging + processing + heat contact + fat level + physical form + matrix class。

## 成功标准

至少一个食品系统维度与 plasticizer burden 有稳定梯度，并能支撑“食品接触/加工来源暴露链条”的 Figure 1。
""",
    )
    write(
        DOCS / "aim1_analysis_plan.md",
        """
# Aim 1 分析计划：食品系统塑化剂暴露与人群代谢易感性

## 已锁定的 NHANES 分析

使用 NHANES 2013-2018，保留复杂抽样设计。核心暴露为 ln(Sigma DEHP)、percent oxidative、ln(oxidative/MEHP)、ILR oxidative-vs-primary。固定协变量：age、sex、race/ethnicity、education、PIR、energy intake、smoking、alcohol、physical activity、urinary creatinine、cycle。

## 新增食品 panel 分析

1. 描述每个食品系统 stratum 的 plasticizer concentration 分布。
2. 以 DEHP 为 primary；以 sum parent plasticizer 和 alternatives 为 secondary。
3. 左删失处理：primary 使用 LOD/sqrt(2)，敏感性使用 Tobit 或 rank-based model。
4. 多重比较：同一 family 内 FDR。
5. 输出食品系统暴露链条图：source -> food burden -> urine metabolites -> metabolic susceptibility。

## 桥接模型

NHANES 层面证明尿 DEHP oxidative profile 与 MSI/HOMA-IR/HbA1c 相关；食品 panel 层面证明某些食品系统场景具有更高 plasticizer burden。两者只作为三角证据，不声称同一人群的直接因果链。
""",
    )


def aim2_existing_summary() -> pd.DataFrame:
    gee = read(AIM2 / "aim2_food_matrix_gee_model_results.csv")
    collapsed = read(P0 / "aim2_collapsed3_food_matrix_gee_results.csv")
    leverage = read(P0 / "aim2_loso_subject_leverage_stability.csv")
    key = gee[
        gee["model"].eq("msi_base") & gee["term"].eq("msi_core")
    ][["outcome", "model", "term", "estimate_CI", "p_fmt", "q_fmt", "n", "n_subjects"]].copy()
    key["evidence_layer"] = "CGMacros MSI-core and PPGR"
    mat = collapsed[collapsed["term"].str.contains("mixed_buffered_or_unknown", na=False)].copy()
    mat = mat[["outcome", "term", "estimate_CI", "p_value", "n", "subjects"]]
    mat["evidence_layer"] = "collapsed food matrix"
    key.to_csv(OUT / "aim2_existing_cgmacros_msi_ppgr_locked.csv", index=False)
    mat.to_csv(OUT / "aim2_collapsed_matrix_locked.csv", index=False)
    leverage.to_csv(OUT / "aim2_subject_leverage_locked.csv", index=False)
    return key


def aim2_protocols() -> None:
    menu = pd.DataFrame(
        [
            ("A", "high_protection_low_packaging", "steel/glass prepared oats + berries + nuts; water", 60, 550, 12, "low", "primary reference"),
            ("B", "high_protection_market_packaged", "pre-packaged whole-grain/legume bowl measured for plasticizer burden", 60, 550, 12, "measured_before_serving", "only if assay confirms acceptable levels"),
            ("C", "low_protection_low_packaging", "freshly prepared refined rice/noodle meal with low fiber in glass/steel", 60, 550, 2, "low", "matrix contrast without high packaging"),
            ("D", "low_protection_market_packaged", "market packaged refined starch/liquid-carb meal measured for plasticizer burden", 60, 550, 2, "measured_before_serving", "observational market scenario, no chemical spiking"),
        ],
        columns=[
            "arm",
            "challenge_condition",
            "meal_description",
            "target_available_carbs_g",
            "target_energy_kcal",
            "target_fiber_g",
            "plasticizer_exposure_context",
            "ethics_note",
        ],
    )
    menu.to_csv(OUT / "aim2_standard_meal_challenge_menu_2x2.csv", index=False)

    crf_cols = [
        "participant_id",
        "visit_id",
        "challenge_arm",
        "meal_start_time",
        "meal_completion_percent",
        "premeal_glucose_mgdl",
        "premeal_activity_30min",
        "sleep_hours_prior",
        "acute_illness_or_medication_change",
        "urine_sample_id_morning",
        "urine_creatinine_mgdl",
        "mehp_ngml",
        "mehhp_ngml",
        "meohp_ngml",
        "mecpp_ngml",
        "cgm_device_id",
        "cgm_wear_day",
        "iauc_2h",
        "peak_delta_2h",
        "time_to_peak_min",
        "adverse_event",
        "protocol_deviation",
    ]
    pd.DataFrame(columns=crf_cols).to_csv(TEMPLATES / "aim2_cgm_pilot_case_report_form_template.csv", index=False)

    write(
        DOCS / "aim2_cgm_pilot_protocol.md",
        """
# Aim 2 前瞻性 CGM/标准餐 pilot 方案

## 目标

在同一批受试者中验证代谢易感性、尿 DEHP oxidative profile、食物基质和 PPGR 的连接。

## 设计

- n=60-100 成人。
- CGM 10-14 天。
- 2-3 次晨尿：MEHP、MEHHP、MEOHP、MECPP 和肌酐。
- 2x2 标准餐挑战：高/低保护食物基质 × 低包装接触/真实市场包装来源。
- 不人为添加 DEHP；市场包装来源食品必须先检测 plasticizer burden，并经伦理审批后才进入人体挑战。

## 主要终点

2h iAUC、2h peak delta、time-to-peak、high-response meal。

## 主要模型

PPGR ~ urinary oxidative DEHP profile + matrix arm + exposure context + oxidative profile x matrix + MSI + premeal glucose + meal order + (1|participant)。

## 纳排标准

纳入：18-70 岁，可佩戴 CGM，可完成标准餐。

排除：妊娠、使用会强烈影响餐后血糖的药物且无法稳定、已知对标准餐过敏、急性感染、无法提供尿样。

## 主要解释边界

该 pilot 旨在验证方向和机制可行性，不以估计长期 DEHP 因果效应为目的。
""",
    )
    write(
        DOCS / "aim2_statistical_analysis_plan.md",
        """
# Aim 2 统计分析计划

## Primary

线性混合模型：log1p(iAUC_2h) ~ MSI + urinary oxidative DEHP profile + matrix arm + MSI x matrix + oxidative profile x matrix + premeal glucose + meal order + sex + age + BMI + (1|participant)。

## Secondary

- peak_delta_2h。
- high-response meal logistic mixed model。
- time-to-peak Cox 或 accelerated failure-time sensitivity。

## Sensitivity

1. 仅使用低 protocol deviation 餐次。
2. 排除尿肌酐极端值。
3. 用 percent oxidative、oxidative/MEHP ratio、ILR 三种暴露定义。
4. 用 CGMacros 训练得到的 MSI/food-matrix 模型预测 pilot PPGR，作为 external validation。

## 成功标准

高 MSI 或高 oxidative profile 在低保护基质餐中显示更高 PPGR；高保护基质方向性降低 PPGR。
""",
    )


def aim3_assets() -> None:
    cf = read(P0 / "aim3_counterfactual_high_iauc_prediction_deltas.csv")
    top = cf.sort_values("pred_high_iauc_delta").head(16).copy()
    pairs = []
    for i, (_, r) in enumerate(top.iterrows(), 1):
        pairs.append(
            {
                "pair_id": f"NF-A3-P{i:02d}",
                "source_subject_id": r["subject_id"],
                "source_meal_time": r["meal_time"],
                "original_matrix": r["food_matrix_final_category"],
                "redesigned_matrix": "fiber_rich_or_whole_food_matrix",
                "target_carbs_g": r["carbs"],
                "target_energy_kcal": r["calories"],
                "original_fiber_g": r["fiber"],
                "target_fiber_g_min": max(float(r["fiber"]), 8.0),
                "original_pred_high_iauc": r["pred_high_iauc_original"],
                "redesigned_pred_high_iauc": r["pred_high_iauc_redesigned"],
                "predicted_delta": r["pred_high_iauc_delta"],
                "prototype_status": "needs_kitchen_formulation_and_lab_validation",
            }
        )
    pd.DataFrame(pairs).to_csv(OUT / "aim3_equal_carb_energy_meal_prototype_pairs_16.csv", index=False)

    timepoints = [0, 15, 30, 60, 90, 120]
    rows = []
    for pair in pairs:
        for version in ["original", "redesigned"]:
            for rep in [1, 2, 3]:
                for t in timepoints:
                    rows.append(
                        {
                            "pair_id": pair["pair_id"],
                            "meal_version": version,
                            "lab_replicate": rep,
                            "time_min": t,
                            "released_glucose_mg_g": "",
                            "starch_hydrolysis_percent": "",
                            "viscosity_mpa_s": "",
                            "particle_size_d50_um": "",
                            "qc_flag": "",
                        }
                    )
    pd.DataFrame(rows).to_csv(TEMPLATES / "aim3_infogest_glucose_release_data_template.csv", index=False)

    write(
        DOCS / "aim3_infogest_digestion_sop.md",
        """
# Aim 3 INFOGEST-style 体外消化 SOP

## 目标

验证等碳水/等能量餐食重构是否通过更慢或更低的葡萄糖释放解释 PPGR 风险降低。

## 样本

- 16 对餐食原型：original vs redesigned。
- 每个版本至少 3 个实验重复。
- 餐食需记录实际可利用碳水、总能量、纤维、蛋白、脂肪、水分和粒径/均质化规则。

## 消化流程

采用 INFOGEST static in vitro digestion 框架：口腔、胃、小肠三个阶段；酶活、胆盐、pH 和空白/标准品按实验室验证方案记录。

## 时间点

0、15、30、60、90、120 min。

## 终点

1. released glucose。
2. starch hydrolysis percent。
3. early glucose release AUC 0-30 min。
4. total glucose release AUC 0-120 min。
5. viscosity 和 particle size 作为食物基质机制变量。

## 主要分析

paired model: glucose_release_AUC ~ meal_version + pair_id。

成功标准：redesigned 餐食的 early glucose release AUC 低于 original，并与 CGMacros counterfactual risk reduction 方向一致。
""",
    )
    write(
        DOCS / "aim3_human_pilot_validation_plan.md",
        """
# Aim 3 人体验证计划

## 目标

将 CGMacros counterfactual meal redesign 转化为可验证的标准餐挑战。

## 设计

- 交叉设计，每位受试者完成 original 与 redesigned 餐食。
- 餐食等可利用碳水、等能量；主要差异为 fiber-rich/whole-food matrix。
- 餐序随机，至少 48 小时 washout。

## 主要终点

2h iAUC、peak delta、time-to-peak。

## 分层

按 baseline MSI 或尿 DEHP oxidative profile 分层，检验高易感人群是否获益更大。

## 成功标准

redesigned 餐食降低 2h iAUC 或 peak delta，且方向在高 MSI 组更明显。
""",
    )


def master_docs() -> None:
    task_rows = [
        ("A1-01", "Aim 1", "NHANES urinary DEHP oxidative profile anchor", "complete", "aim1_nhanes_dehp_msi_anchor_locked.csv"),
        ("A1-02", "Aim 1", "Food plasticizer 96-sample sampling frame", "complete_template", "aim1_food_plasticizer_sampling_frame_96_samples.csv"),
        ("A1-03", "Aim 1", "Food sample metadata template", "complete_template", "templates/aim1_food_sample_metadata_template.csv"),
        ("A1-04", "Aim 1", "Plasticizer measurement panel and lab assay brief", "complete_protocol", "aim1_plasticizer_measurement_panel.csv; docs/aim1_food_plasticizer_lab_assay_brief.md"),
        ("A1-05", "Aim 1", "Food-system exposure chain graph", "complete_template", "aim1_food_system_exposure_chain_nodes.csv; aim1_food_system_exposure_chain_edges.csv"),
        ("A2-01", "Aim 2", "CGMacros MSI-core and PPGR locked evidence", "complete", "aim2_existing_cgmacros_msi_ppgr_locked.csv"),
        ("A2-02", "Aim 2", "Collapsed food matrix and subject leverage", "complete", "aim2_collapsed_matrix_locked.csv; aim2_subject_leverage_locked.csv"),
        ("A2-03", "Aim 2", "Prospective CGM pilot protocol", "complete_protocol", "docs/aim2_cgm_pilot_protocol.md"),
        ("A2-04", "Aim 2", "2x2 standard meal challenge menu", "complete_template", "aim2_standard_meal_challenge_menu_2x2.csv"),
        ("A2-05", "Aim 2", "Pilot CRF and SAP", "complete_template", "templates/aim2_cgm_pilot_case_report_form_template.csv; docs/aim2_statistical_analysis_plan.md"),
        ("A3-01", "Aim 3", "Counterfactual risk reduction locked candidates", "complete", "aim3_equal_carb_energy_meal_prototype_pairs_16.csv"),
        ("A3-02", "Aim 3", "INFOGEST glucose release template and SOP", "complete_protocol", "templates/aim3_infogest_glucose_release_data_template.csv; docs/aim3_infogest_digestion_sop.md"),
        ("A3-03", "Aim 3", "Human pilot validation plan", "complete_protocol", "docs/aim3_human_pilot_validation_plan.md"),
        ("A3-04", "Aim 3", "Actual food chemistry, digestion, and human pilot results", "requires_new_data", "pending lab/human data collection"),
    ]
    pd.DataFrame(task_rows, columns=["task_id", "aim", "task", "status", "output"]).to_csv(
        OUT / "nature_food_high_bar_aims_task_status.csv", index=False
    )

    write(
        DOCS / "nature_food_high_bar_aims_completion_report_zh.md",
        """
# Nature Food 高标准 Aim 1-3 完成报告

## 完成口径

本包完成的是可执行研究框架、已有数据锁定结果、实验采样框、人体 pilot 方案、体外消化方案、统计分析计划和数据模板。尚未采集的食品 plasticizer 浓度、前瞻性 CGM/尿样和体外消化读数不会被伪造成结果。

## Aim 1

已完成 NHANES 2013-2018 尿 DEHP oxidative profile 与 MSI/HOMA-IR/HbA1c 的锁定结果；新增 96 个食品样本的 plasticizer measurement sampling frame；建立食品样本 metadata template、plasticizer panel、实验室检测 brief 和食品系统暴露链条图。

## Aim 2

已锁定 CGMacros 中 MSI-core 与 PPGR、collapsed food matrix、subject leverage 结果；新增前瞻性 CGM/标准餐 pilot protocol、2x2 标准餐菜单、CRF template 和统计分析计划。

## Aim 3

已从 CGMacros counterfactual 中筛选 16 对等碳水/等能量餐食原型；新增 INFOGEST-style 体外消化 SOP、glucose release 数据模板和 human pilot validation plan。

## 下一步真正决定 Nature Food 的数据

1. 96 个食品样本的 plasticizer burden。
2. n=60-100 前瞻性 CGM + 尿 DEHP metabolite pilot。
3. 16 对餐食原型的 glucose release 曲线。
4. 至少一个 human pilot 或 frozen-test validation 结果。
""",
    )
    write(
        DOCS / "nature_food_go_no_go_memo.md",
        """
# Nature Food Go/No-Go Memo

## 当前状态

已有 NHANES 和 CGMacros 结果足以支持 preliminary evidence，但不足以单独投稿 Nature Food。

## Go 条件

至少满足以下三条，才建议继续 Nature Food 主投稿：

1. 食品 plasticizer panel 显示 packaging/processing/heat/fat/matrix 与 DEHP 或 total plasticizer burden 存在清晰梯度。
2. 前瞻性 CGM/标准餐 pilot 显示 MSI 或尿 DEHP oxidative profile 与 PPGR 方向一致。
3. 高保护食物基质在标准餐或体外消化中降低 PPGR 或 glucose release。
4. CGMacros 模型在 pilot 或 frozen test 中方向一致。

## No-Go 条件

如果无法完成食品化学检测或人体/体外验证，应停止以 Nature Food 为目标，将稿件转向 Environmental Health、npj Science of Food、AJCN 或 Diabetes Care 相关方向。
""",
    )


def main() -> None:
    aim1_existing_anchor()
    build_food_sampling_frame()
    build_templates()
    build_exposure_chain()
    aim1_docs()
    aim2_existing_summary()
    aim2_protocols()
    aim3_assets()
    master_docs()
    manifest = {
        "root": str(OUT),
        "files": sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file()),
        "note": "Experimental result templates are intentionally blank until new lab/human data are collected.",
    }
    (OUT / "nature_food_high_bar_aims_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote high-bar Aim 1-3 package to {OUT}")


if __name__ == "__main__":
    main()
