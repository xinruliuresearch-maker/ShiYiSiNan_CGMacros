# 面向 npj Digital Medicine 的当前结果整理与后续研究计划

生成日期：2026-06-18  
目标期刊：npj Digital Medicine  
官方定位参考：Nature npj Digital Medicine aims and scope，重点包括 digital medicine、validated digital biomarkers、AI/ML、software/sensors、virtual-care models；通常不适合仅有小样本或纯初步观察性描述的研究。

## 一句话判断

当前工作已经从“普通 CGM 机器学习 benchmark”推进到了“可计算 CGM digital phenotype + frozen external validation + algorithm card/software specification + subgroup audit + phase-guided care workflow”的雏形。  

如果现在立即投稿，风险仍偏高；主要短板不是模型 AUROC，而是：外部验证仍只有 Loop 一个 frozen dataset，TIR 绝对风险校准偏弱，公平性审计暴露了小样本 subgroup 风险，且尚无 prospective/silent-mode workflow evidence。若补齐软件发布、校准/公平性、第二外部验证或 clinician/silent-mode 验证，才更像 npj Digital Medicine 级别的数字医学论文。

## 当前结果盘点

### 1. 数据和数字表型

- JAEB development corpus：13 个已下载清洗的 JAEB development datasets。
- phase-map baseline 样本：748 名参与者。
- harmonized CGM summary：8638 行。
- 锁定相位：stable in-range、high-variability oscillatory、persistent hyperglycaemia、circadian-disruption、hypoglycaemia-susceptible。
- Bootstrap stability：ARI 中位数 0.826，IQR 0.755-0.890；silhouette 中位数 0.268。

解释：这足以支撑“research-grade CGM digital phenotype”，但不能写成已证实的生物学亚型。

### 2. 内部和跨研究验证

Nested CV 最佳结果：

        target  feature_set          model  total_test_n  auroc_mean  auprc_mean  brier_mean
HbA1c response     clinical       lightgbm          1955    0.802240    0.745487    0.179547
  TIR response clinical+CGM logistic_ridge           641    0.794893    0.744275    0.185407

Leave-one-study-out 最佳结果：

        target  feature_set          model  heldout_study_count  total_test_n  auroc_mean  auprc_mean  brier_mean
HbA1c response     clinical logistic_ridge                   13          1955    0.726769    0.582648    0.211162
  TIR response clinical+CGM logistic_ridge                    4           641    0.754154    0.688337    0.234429

解释：预测性能可用来证明 digital phenotype 的外部效度，但不能把论文写成“phase-map 模型显著优于所有 ML 模型”。

### 3. Loop frozen external validation

Loop 没有参与建模或调参。外部验证库存：

                             dataset                                 zip_file                               role  n_with_baseline_cgm  n_with_month6_cgm  n_with_baseline_hba1c  n_with_month6_hba1c                                                 phase_assignment                                 notes
Loop study public dataset 2023-01-31 Loop study public dataset 2023-01-31.zip primary frozen external validation                  668                633                    598                  545 nearest fixed centroid from original JAEB phase-map training set No retraining or tuning on Loop data.

Loop 外部验证结果：

target_display feature_display  test_n  positive_rate    auroc    auprc    brier  expected_calibration_error
HbA1c response    clinical+CGM     521       0.261036 0.764477 0.525878 0.163286                    0.044148
HbA1c response       phase-map     521       0.261036 0.757945 0.517518 0.177336                    0.103350
  TIR response    clinical+CGM     633       0.426540 0.828609 0.755848 0.244505                    0.234858
  TIR response       phase-map     633       0.426540 0.826946 0.755442 0.241566                    0.230581

Loop phase distribution：

                    phase_id                     phase_label_en   n
             stable_in_range              Stable in-range phase 543
high_variability_oscillation High-variability oscillatory phase  87
   persistent_hyperglycaemia    Persistent hyperglycaemia phase  34
   hypoglycaemia_susceptible    Hypoglycaemia-susceptible phase   4

解释：这是很关键的 P0 增强。优势是锁定验证成立；限制是 Loop 强烈偏 stable phase，且 phase-map 并未明显优于 clinical+CGM comparator。TIR 结局的 ECE 约 0.23，说明若要显示绝对风险，需要重新校准或改成 phenotype/ranking 支持。

### 4. HTE 与 digital care workflow

- 最大 adjusted risk difference：Hypoglycaemia-susceptible phase，RD 0.281，95% bootstrap CI 0.105-0.408。
- 这已经被转化为 phase-guided digital care workflow：phase assigned -> risk/context displayed -> clinician review -> care focus selected -> reassess with new CGM。

解释：这是 npj 叙事的转化支点。但必须写成 clinician-in-the-loop / silent-mode decision support，不能写成自动治疗建议。

### 5. 公平性和校准审计

Top subgroup audit signals：

                 target  feature_set          model    subgroup_variable           subgroup_display   n    auroc  delta_auroc_vs_overall    brier  expected_calibration_error
y_hba1c_improved_ge_0_5  C1_clinical logistic_ridge               x_race                      asian  29 0.361111               -0.437771 0.301007                    0.297055
y_hba1c_improved_ge_0_5  C1_clinical       lightgbm               x_race                      asian  29 0.444444               -0.355927 0.268726                    0.225873
y_hba1c_improved_ge_0_5  C1_clinical        xgboost               x_race                      asian  29 0.461111               -0.338434 0.256866                    0.173292
y_hba1c_improved_ge_0_5 C4_phase_map        xgboost               x_race                      asian  29 0.472222               -0.326615 0.253761                    0.169840
y_hba1c_improved_ge_0_5  C1_clinical        xgboost             study_id              METFORMIN_T1D 137 0.531041               -0.268504 0.182065                    0.055536
y_hba1c_improved_ge_0_5  C1_clinical       lightgbm             study_id              METFORMIN_T1D 137 0.540627               -0.259744 0.200233                    0.160702
y_hba1c_improved_ge_0_5 C4_phase_map        xgboost             study_id              METFORMIN_T1D 137 0.540475               -0.258362 0.179906                    0.050782
y_hba1c_improved_ge_0_5 C4_phase_map        xgboost baseline_hba1c_group                         <7 466 0.577644               -0.221193 0.094032                    0.046625
y_hba1c_improved_ge_0_5 C4_phase_map        xgboost          phase_label Circadian-disruption phase  91 0.583157               -0.215680 0.236289                    0.110301
y_hba1c_improved_ge_0_5  C1_clinical       lightgbm baseline_hba1c_group                         <7 466 0.589585               -0.210786 0.100294                    0.073936

Phase-map model focused audit：

                 target  feature_set   model    subgroup_variable                subgroup_display   n    auroc  delta_auroc_vs_overall    brier  expected_calibration_error
y_hba1c_improved_ge_0_5 C4_phase_map xgboost               x_race                           asian  29 0.472222               -0.326615 0.253761                    0.169840
y_hba1c_improved_ge_0_5 C4_phase_map xgboost             study_id                   METFORMIN_T1D 137 0.540475               -0.258362 0.179906                    0.050782
y_hba1c_improved_ge_0_5 C4_phase_map xgboost baseline_hba1c_group                              <7 466 0.577644               -0.221193 0.094032                    0.046625
y_hba1c_improved_ge_0_5 C4_phase_map xgboost          phase_label      Circadian-disruption phase  91 0.583157               -0.215680 0.236289                    0.110301
 y_tir_improved_ge_5pct C4_phase_map xgboost               x_race              more_than_one_race  34 0.575000               -0.190663 0.256349                    0.218716
y_hba1c_improved_ge_0_5 C4_phase_map xgboost             study_id                            CITY 142 0.613904               -0.184933 0.221101                    0.093740
y_hba1c_improved_ge_0_5 C4_phase_map xgboost          phase_label Hypoglycaemia-susceptible phase  55 0.627178               -0.171659 0.182102                    0.080810
y_hba1c_improved_ge_0_5 C4_phase_map xgboost             study_id                           SENCE 137 0.630628               -0.168209 0.210534                    0.061677
y_hba1c_improved_ge_0_5 C4_phase_map xgboost          phase_label Persistent hyperglycaemia phase 167 0.647146               -0.151691 0.228163                    0.079481
y_hba1c_improved_ge_0_5 C4_phase_map xgboost             study_id                      REPLACE_BG 216 0.649966               -0.148871 0.128434                    0.035300

解释：亚洲 subgroup 的 AUROC shortfall 很大但 n=29，不能过度解读；METFORMIN_T1D、baseline HbA1c <7、circadian-disruption phase 是需要在补充材料里透明呈现的 reviewer risk。

## 目标期刊投稿定位

推荐题目方向：

**A reproducible glycaemic phase map from continuous glucose monitoring identifies digital phenotypes of treatment response in public diabetes trials**

核心主张：

1. CGM summary 可以转化为可复现、可解释的 glycaemic state space。
2. 锁定 phase map 是一种 computable CGM digital phenotype，而不是普通聚类。
3. 该 phenotype 在 JAEB 多研究和 Loop frozen dataset 中具有可迁移性。
4. Phase membership 能组织治疗反应异质性，并支持 clinician-in-the-loop 的 digital care workflow。

禁止/弱化的说法：

- 不说 phase 是已证实的生物学亚型。
- 不说 phase-map 模型显著优于所有 ML 模型。
- 不把 HTE 解释成确定性临床治疗推荐。
- 不把 retrospective public-data result 写成已部署数字医疗工具。

## 后续研究计划

### P0：投稿前必须完成

1. **第二外部验证或外部数据兼容性矩阵**  
   继续筛查 `jaeb_public_extra`，对 GLAM、RacialDifferences、SevereHypo、CGMND、PSO 系列等做兼容性表。若有 baseline CGM + follow-up HbA1c/TIR，按 Loop 同样的 frozen rule 跑一次；若没有，明确说明为何不能作为验证集。

2. **校准升级**  
   对 Loop 和 LOSO 做 calibration curve、slope/intercept、ECE、Brier decomposition。对 TIR response 做预先声明的 intercept/slope recalibration sensitivity；若校准仍弱，就把输出定位为 phenotype/ranking，而非绝对风险。

3. **公平性和可迁移性不确定性**  
   对 subgroup AUROC/ECE 增加 bootstrap CI 和 minimum-n reporting rule。对 small-n subgroup 不给强结论，但要透明呈现。

4. **软件发布包**  
   输出 versioned phase-map package、schema、toy data、unit tests、figure reproduction script、environment lock。算法卡和 software spec 已有，但还需要可复现执行包。

5. **Results 初稿重写**  
   按四段写：phenotype derivation -> validity -> frozen validation/fairness -> phase-guided workflow。不要以模型排行榜开头。

### P1：显著提高 npj 命中率

1. **Raw CGM time-series upgrade**  
   从 summary-CGM 升级到 transition entropy、dwell time、nocturnal instability、day-night transitions、hypoglycaemia cluster recurrence。即使作为 sensitivity/extended analysis，也能显著提高数字表型深度。

2. **Clinician vignette validation**  
   让糖尿病临床医生在病例 vignette 中查看 phase-map 输出，评价可解释性、潜在误用、安全边界、治疗讨论价值。

3. **Silent-mode prospective pilot**  
   80-120 名 CGM 用户，算法后台运行，不给治疗建议。主要终点：phase assignment success、phase stability、prospective calibration、clinician interpretability、patient/clinician burden。

4. **TRIPOD-AI / algorithm-card 对齐**  
   把预测模型报告、校准、外部验证、数据偏倚、适用边界、human oversight 写入补充材料。

### P2：若要冲更强 digital medicine 转化

1. Phase-guided decision support 原型。
2. EHR/CGM app 集成的 silent workflow。
3. 小型 stepped-wedge 或 cluster-randomized workflow trial。

## Go/No-Go 建议

- **现在状态**：可作为强预投稿/内部评审包，但正式投 npj 风险仍高。
- **最小投稿条件**：完成第二外部验证可行性矩阵、校准升级、公平性 CI、软件发布包、Results 重写。
- **理想投稿条件**：再加 clinician vignette 或 silent-mode prospective pilot。
- **若 prospective pilot 做不了**：仍可投稿，但标题和结论必须非常克制，定位为 retrospective validation of a computable CGM digital phenotype。

## 本次生成的配套文件

- `tables/current_results_evidence_table.csv`
- `tables/npj_gap_matrix.csv`
- `tables/npj_90_180_day_workplan.csv`
- `tables/npj_go_no_go_criteria.csv`
- `tables/npj_manuscript_storyboard.csv`
