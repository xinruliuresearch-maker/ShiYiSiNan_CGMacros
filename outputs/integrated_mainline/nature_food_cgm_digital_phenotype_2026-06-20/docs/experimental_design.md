# Experimental Design: Machine Learning and Fine-Tuned Models for Diabetes RCT Response Prediction

Version: 1.0  
Date: 2026-06-16  
Data foundation: `data/processed/processed_ml_table.csv`

## 1. Executive Summary

This study will benchmark conventional machine learning, modern gradient-boosted trees, deep tabular models, AutoML, and fine-tuned or adapted tabular foundation models for predicting response to diabetes interventions using publicly available individual-level RCT/intervention data.

The central scientific question is:

> Can baseline clinical, demographic, treatment-assignment, and CGM-derived features predict individual glycemic response to diabetes interventions across public RCTs, and which modeling strategy gives the strongest validated, calibrated, and clinically useful performance?

The current cleaned dataset contains:

| Task | Outcome | Available n | Positive cases / rate |
|---|---:|---:|---:|
| HbA1c improvement classification | `y_hba1c_improved_ge_0_5` | 940 | 246 / 26.2% |
| Follow-up HbA1c target classification | `y_hba1c_under_7_at_followup` | 940 | 210 / 22.3% |
| CGM TIR improvement classification | `y_tir_improved_ge_5pct` | 473 | 183 / 38.7% |
| HbA1c change regression | `y_hba1c_change_pct_points` | 940 | continuous |
| CGM TIR change regression | `y_change_cgm_time_in_range_70_180_pct` | 473 | continuous |
| Weight change regression | `y_weight_change_kg` | 580 | continuous |

The primary publishable analysis should not select a winner by raw accuracy alone. For a top clinical or digital-health journal, the winning model should be chosen using a hierarchy:

1. Internal cross-validated discrimination or error.
2. Calibration.
3. External or leave-one-study-out transportability.
4. Decision-curve or clinical utility.
5. Robustness across subgroups and sensitivity analyses.
6. Interpretability and reproducibility.

## 2. Literature-Based Design Principles

The experimental design follows these principles from current clinical AI and tabular ML evidence:

- Use TRIPOD+AI as the reporting backbone for prediction model development and validation.
- Use PROBAST+AI to anticipate risk-of-bias concerns around participants, predictors, outcomes, and analysis.
- Use CONSORT-AI and SPIRIT-AI only as forward-looking guidance if this model later becomes an AI intervention evaluated prospectively.
- Use CGM outcomes aligned with international consensus definitions: time in range 70-180 mg/dL, time below range, time above range, and clinically meaningful TIR changes.
- Treat gradient-boosted tree models as strong primary comparators because tabular-data benchmarks repeatedly show they remain difficult to beat.
- Include deep tabular and foundation-model approaches, but require strict nested validation because the sample size is modest and overfitting risk is high.
- Report calibration, decision-curve analysis, and subgroup performance, not only AUROC/accuracy.

## 3. Candidate Manuscript Positioning

### 3.1 Main Claim

A strong top-journal claim would be:

> In harmonized individual-level public diabetes RCT data, tabular machine learning can predict glycemic treatment response with measurable but heterogeneous performance; model ranking changes when calibration and leave-one-study-out validation are considered, and baseline HbA1c plus treatment context dominate performance.

This is more credible than claiming "AI predicts diabetes response perfectly." The paper should be framed as a rigorous benchmark and transportability study.

### 3.2 Target Journals

Primary clinical/digital-health targets:

- `Diabetes Care`: best fit if the clinical diabetes interpretation is strong.
- `The Lancet Digital Health`: requires robust external validation, clinical relevance, and reproducible model reporting.
- `Nature Medicine`: possible only if the foundation-model or personalized-response contribution is clearly novel and externally validated.
- `npj Digital Medicine`: good fit for a rigorous public-data AI benchmark.
- `JAMA Network Open`: possible if the clinical prediction and transparent reporting are strong.
- `NEJM AI`: possible if the model-comparison and deployment implications are mature.

Backup technical/medical AI targets:

- `Patterns`
- `PLOS Digital Health`
- `Journal of Biomedical Informatics`
- `Artificial Intelligence in Medicine`

## 4. Study Objectives

### 4.1 Primary Objective

Compare multiple ML and fine-tuned/adapted tabular models for predicting whether a participant achieves clinically meaningful HbA1c improvement:

`y_hba1c_improved_ge_0_5 = 1` if follow-up HbA1c minus baseline HbA1c <= -0.5 percentage points.

### 4.2 Secondary Objectives

1. Predict continuous HbA1c change.
2. Predict follow-up HbA1c <7%.
3. Predict CGM TIR improvement >=5 percentage points among studies with CGM summaries.
4. Predict continuous CGM TIR change.
5. Predict weight change.
6. Estimate heterogeneous treatment response within trials where treatment arms are clinically comparable.
7. Evaluate model transportability across trial populations using leave-one-study-out validation.
8. Quantify calibration and clinical utility.

### 4.3 Exploratory Objectives

1. Compare zero-shot/in-context TabPFN to fine-tuned or adapted tabular foundation models.
2. Evaluate self-supervised pretraining on baseline-only public JAEB datasets before supervised fine-tuning.
3. Test multitask learning across HbA1c, CGM, and weight outcomes with missing-label masks.
4. Compare pooled models with study-specific models and hierarchical/meta-learning variants.

## 5. Data and Cohorts

### 5.1 Included Cleaned Public Datasets

The current ML table includes six JAEB public de-identified individual-level datasets:

| Study | Trial type | Population | Main intervention |
|---|---|---|---|
| WISDM | Parallel RCT | Older adults with T1D | CGM vs BGM |
| CITY | Parallel RCT | Teens/young adults with T1D | CGM vs BGM |
| SENCE | Factorial/parallel RCT | Young children with T1D | CGM + behavioral intervention, standard CGM, BGM |
| REPLACE-BG | Parallel RCT | Adults with T1D using CGM | CGM-only vs CGM+BGM |
| FLAIR | Crossover RCT | T1D using AID systems | AHCL/PID+fuzzy logic vs comparator |
| METFORMIN_T1D | Parallel RCT | Overweight adolescents with T1D | Metformin vs placebo |

### 5.2 Analysis Cohorts

Use separate task-specific cohorts:

- `Cohort A`: participants with non-missing baseline and follow-up HbA1c, n=940.
- `Cohort B`: participants with non-missing HbA1c target status, n=940.
- `Cohort C`: participants with baseline and follow-up CGM TIR, n=473.
- `Cohort D`: participants with baseline and follow-up weight, n=580.
- `Cohort E`: within-trial treatment-effect cohorts for WISDM, CITY, SENCE, REPLACE-BG, Metformin; FLAIR handled separately due to crossover design.

### 5.3 Exclusion Criteria

Exclude participants from a task only when:

- Randomized treatment arm is missing.
- Baseline value required for that task is missing and cannot be represented through the pre-specified imputation pipeline.
- Follow-up outcome for that specific target is missing.
- Implausible values remain after unit standardization and quality checks.

Do not exclude participants only because some non-essential predictors are missing.

## 6. Prediction Timepoints and Leakage Control

### 6.1 Prediction Timepoint

Primary prediction timepoint:

> At baseline/randomization, before follow-up outcome measurements and before post-randomization adherence or device-use information is observed.

### 6.2 Allowed Predictor Families

Allowed:

- Study ID.
- Trial intervention description.
- Randomized treatment arm, for assigned-treatment prediction models.
- Age, sex, race, ethnicity.
- Diabetes diagnosis age/duration.
- Baseline HbA1c.
- Baseline weight, height, BMI.
- Baseline insulin dose or insulin delivery method.
- Baseline CGM summaries when available.
- Baseline missingness indicators.

Not allowed for baseline prediction:

- Follow-up HbA1c, CGM, weight, BMI.
- Post-randomization adherence, device upload frequency, CGM wear after randomization.
- Visit completion variables after baseline.
- Adverse events after randomization.
- Any feature created using follow-up outcomes.

### 6.3 Two Prediction Settings

Run both settings because they answer different clinical questions:

1. `Prognostic model`: excludes randomized treatment arm. Predicts likely outcome before treatment assignment.
2. `Assigned-treatment model`: includes randomized treatment arm. Predicts outcome conditional on a known treatment/intervention.

For personalized treatment selection, use the assigned-treatment model plus formal heterogeneous-treatment-effect methods rather than interpreting ordinary feature importance as causal.

## 7. Outcomes

### 7.1 Primary Outcome

`y_hba1c_improved_ge_0_5`.

Rationale: a reduction of at least 0.5 HbA1c percentage points is clinically interpretable and less sensitive to minor laboratory noise than any improvement.

### 7.2 Secondary Outcomes

Classification:

- `y_hba1c_under_7_at_followup`
- `y_tir_improved_ge_5pct`

Regression:

- `y_hba1c_change_pct_points`
- `y_change_cgm_time_in_range_70_180_pct`
- `y_weight_change_kg`

### 7.3 Outcome Harmonization Notes

- HbA1c uses central/STA laboratory results when available; local HbA1c is used only as fallback.
- CGM TIR uses the 70-180 mg/dL range.
- TIR improvement >=5 percentage points is a clinically meaningful and interpretable endpoint.
- Trial follow-up horizons differ slightly; include `study_id` and run study-specific sensitivity analyses.

## 8. Feature Sets for Ablation

Run every model family across the following pre-specified feature sets:

| Feature set | Description | Purpose |
|---|---|---|
| FS0 | Baseline HbA1c only | Minimal clinical benchmark |
| FS1 | Demographics + study ID + baseline HbA1c | Simple clinical benchmark |
| FS2 | FS1 + baseline weight/BMI + diabetes duration | Standard clinical model |
| FS3 | FS2 + treatment arm | Assigned-treatment model |
| FS4 | FS3 + baseline insulin/CGM-use variables | Expanded baseline clinical model |
| FS5 | FS4 + baseline CGM metrics | CGM-enriched model for CGM-capable studies |
| FS6 | All baseline `x_` variables and missingness indicators | Maximal baseline model |

Primary comparison should focus on FS3/FS4 for HbA1c tasks and FS5 for CGM tasks.

## 9. Model Families

### 9.1 Clinical and Statistical Baselines

Use these as mandatory baselines:

- Majority-class classifier and mean/median regressor.
- Logistic regression with ridge penalty.
- Logistic regression with lasso and elastic net.
- Linear regression, ridge, lasso, elastic net for continuous targets.
- Generalized additive model or spline logistic model if implementation time allows.
- Bayesian logistic/ridge regression if uncertainty intervals are a priority.

Purpose: strong interpretability and top-journal reviewer expectations.

### 9.2 Conventional ML

Include:

- Random forest.
- ExtraTrees.
- Support vector machine with RBF kernel.
- k-nearest neighbors.
- Naive Bayes as a weak baseline.

Purpose: broad method coverage and historical comparability.

### 9.3 Gradient-Boosted Trees

Mandatory high-priority models:

- XGBoost.
- LightGBM.
- CatBoost.
- HistGradientBoosting from scikit-learn as a dependency-light comparator.

Expected behavior: likely strongest or among strongest on tabular clinical data.

### 9.4 AutoML and Ensembles

Include if computational budget permits:

- AutoGluon Tabular.
- FLAML.
- Optuna-tuned stacking ensemble.
- Super Learner ensemble combining logistic regression, CatBoost, XGBoost, LightGBM, and TabPFN predictions.

Important: AutoML must be run inside training folds only. Do not let AutoML see validation/test outcomes.

### 9.5 Deep Tabular Models

Candidate architectures:

- MLP with embeddings for categorical variables.
- Tabular ResNet / ResNet-like MLP.
- FT-Transformer.
- TabTransformer.
- SAINT.
- TabNet.

Training safeguards:

- Early stopping on inner-validation folds.
- Weight decay and dropout.
- Small hyperparameter budget because n is modest.
- Repeat seeds.
- Report when deep models underperform rather than over-tuning them.

### 9.6 Fine-Tuned or Adapted Foundation Models

The most appropriate "fine-tuned model" direction here is tabular foundation modeling, not a general text LLM.

Primary foundation-model candidates:

- TabPFN zero-shot/in-context classification and regression.
- TabPFN with post-hoc calibration.
- TabPFN fine-tuning or adapter tuning if the installed version and license allow it.
- TabPFN embeddings followed by calibrated logistic/ridge/GBDT heads.

Fine-tuning protocol:

1. Split data first.
2. Fit all preprocessing on training fold only.
3. If using TabPFN fine-tuning, update weights only on the inner-training fold.
4. Select fine-tuning epochs and learning rate only on inner-validation folds.
5. Evaluate once on outer test fold.
6. Calibrate probabilities on inner-validation predictions, not the outer test fold.

Exploratory self-supervised fine-tuning:

- Use all baseline `x_` predictors from additional public JAEB datasets as unlabeled data.
- Masked feature reconstruction or denoising objective.
- No outcome labels outside the training fold.
- Fine-tune supervised head on task labels.
- Compare against the same architecture trained from scratch.

### 9.7 LLM-Based Fine-Tuning

General-purpose LLM fine-tuning is not a primary plan because the data are structured tabular clinical variables without free text. It may be included only as a negative-control exploratory experiment:

- Convert each row to a stable text template.
- Fine-tune a small open model or API model to classify HbA1c improvement.
- Compare against logistic regression and CatBoost.
- Do not claim superiority unless externally validated and calibrated.

Expected risk: likely overfitting, poor calibration, and limited interpretability.

## 10. Preprocessing Pipeline

All preprocessing must be embedded in scikit-learn-style pipelines or equivalent fold-contained training objects.

### 10.1 Numeric Features

- Use raw baseline numeric columns plus `_missing` indicators.
- Impute within fold using median imputation.
- Scale numeric variables for linear, SVM, KNN, and neural-network models.
- Do not scale for tree models unless the implementation requires it.

### 10.2 Categorical Features

- One-hot encode for linear/SVM/tree models.
- Use native categorical handling for CatBoost when possible.
- Use learned embeddings for deep tabular models.
- Collapse rare categories if they occur in fewer than 5 participants in the training fold.

### 10.3 Class Imbalance

Primary: class weights or loss weighting.  
Secondary sensitivity: SMOTE or random oversampling inside inner-training folds only.

Do not oversample before cross-validation splitting.

## 11. Validation Design

### 11.1 Primary Internal Validation

Use repeated nested cross-validation:

- Outer loop: 5 folds, repeated 5 times if computationally feasible.
- Inner loop: 3-5 folds for hyperparameter tuning.
- Stratify classification folds by outcome and study.
- Group by participant ID. The current table has one row per participant, but grouping should remain explicit.

Primary performance is the distribution of outer-fold predictions pooled across repeats.

### 11.2 External/Transportability Validation

Use leave-one-study-out validation:

- Train on all eligible studies except one.
- Tune only inside the training studies.
- Test on the held-out study.
- Repeat for each study with sufficient outcome availability.

Expected issue: not every study has all outcomes. For CGM TIR, leave-one-study-out is limited to WISDM, CITY, and SENCE.

### 11.3 Temporal Validation

Not applicable in the current public de-identified JAEB data because dates are shifted/synthetic-like and trial cohorts are not a temporal EHR stream.

### 11.4 Final Model

After benchmark completion, refit the chosen model on all eligible development data using hyperparameters selected by nested CV. Clearly label it as a final refit model, not as independently validated.

## 12. Hyperparameter Tuning

Use Optuna or randomized search with fixed budgets. Suggested inner-fold budgets:

| Model | Trials per outer split | Notes |
|---|---:|---|
| Logistic/ridge/lasso | 20 | Regularization strength and penalty |
| Random forest/ExtraTrees | 50 | n_estimators, max_depth, min_samples_leaf |
| XGBoost/LightGBM/CatBoost | 75-150 | learning_rate, depth, subsampling, regularization |
| SVM | 30 | C, gamma, class weight |
| MLP/ResNet | 50 | width, depth, dropout, weight decay, LR |
| FT-Transformer/TabTransformer/SAINT | 50 | dimension, heads, layers, dropout, LR |
| TabNet | 50 | n_d, n_a, n_steps, gamma, lambda_sparse |
| TabPFN | 0-20 | usually little tuning; calibrator/tuning only |

Use early stopping for all boosting and neural methods.

## 13. Performance Metrics

### 13.1 Classification Metrics

Primary:

- AUROC.

Key secondary:

- AUPRC.
- Balanced accuracy.
- Sensitivity and specificity at pre-specified thresholds.
- F1 score.
- Brier score.
- Calibration-in-the-large.
- Calibration slope or flexible calibration curve.
- Expected calibration error as an auxiliary metric.
- Decision-curve net benefit across clinically plausible thresholds.

Accuracy should be reported, but not used as the sole winner metric.

### 13.2 Regression Metrics

Primary:

- RMSE.

Secondary:

- MAE.
- R-squared.
- Spearman correlation between predicted and observed change.
- Calibration plot of predicted vs observed mean outcome by prediction decile.
- Clinically tolerable error rates, for example absolute HbA1c-change error <=0.5 percentage points.

### 13.3 Model Ranking Rule

For the primary classification task:

1. Rank models by outer-CV AUROC.
2. Exclude models with clearly poor calibration unless recalibration fixes it.
3. Compare top models by leave-one-study-out AUROC and Brier score.
4. If two models are statistically and clinically similar, prefer the simpler and more interpretable model.
5. The manuscript's "best model" must not be chosen based only on the final test set.

## 14. Statistical Inference

### 14.1 Confidence Intervals

- Use bootstrap confidence intervals over participants for pooled outer-fold predictions.
- Use study-level bootstrap or random-effects meta-analysis for leave-one-study-out summaries when feasible.
- For AUROC comparisons, use paired bootstrap or DeLong-style tests when predictions are paired.

### 14.2 Multiple Comparisons

Because many models will be compared:

- Pre-specify a primary model set: logistic ridge, random forest, XGBoost, LightGBM, CatBoost, TabPFN, FT-Transformer.
- Treat all other comparisons as exploratory.
- Use Benjamini-Hochberg FDR or report unadjusted intervals with explicit exploratory labeling.

### 14.3 Sample Size and Events

Primary classification has 940 participants and 246 positive HbA1c responders. This is moderate, not large. Complex deep/fine-tuned models must be heavily regularized and judged by external validation.

## 15. Calibration and Clinical Utility

### 15.1 Calibration

For each candidate final model:

- Plot calibration curve.
- Report calibration-in-the-large.
- Report calibration slope or flexible calibration summary.
- Report Brier score.
- Apply Platt scaling, isotonic regression, or temperature scaling only within cross-validation.

### 15.2 Decision-Curve Analysis

Decision-curve analysis should be run for the top 3-5 models on:

- HbA1c improvement threshold.
- Follow-up HbA1c <7%.
- TIR improvement >=5 percentage points.

Clinically plausible threshold probabilities should be decided before analysis, for example 10-50% for HbA1c improvement depending on whether the model supports intensified follow-up, additional education, or treatment selection.

## 16. Interpretability and Clinical Error Analysis

### 16.1 Global Interpretability

Use:

- Coefficients for penalized regression.
- SHAP values for tree models.
- Permutation importance with grouped features.
- Partial dependence or accumulated local effects for top predictors.

Expected important predictors:

- Baseline HbA1c.
- Age/study population.
- Randomized treatment arm.
- Baseline CGM TIR and hypoglycemia metrics.
- Baseline BMI/weight.
- Diabetes duration.

### 16.2 Local Interpretability

For representative individuals:

- Show predicted probability.
- Show top positive and negative contributors.
- Compare model explanation with clinical plausibility.

### 16.3 Error Analysis

Manually review false positives and false negatives by:

- Study.
- Baseline HbA1c strata.
- Treatment arm.
- Age group.
- Race/ethnicity categories where sample size permits.
- Baseline CGM availability.

## 17. Fairness and Subgroup Evaluation

Subgroups:

- Study.
- Age group: young children, adolescents/young adults, adults, older adults.
- Sex.
- Race.
- Ethnicity.
- Baseline HbA1c strata: <7.5, 7.5-8.5, >8.5.
- Treatment arm.

Report, where sample size allows:

- AUROC.
- AUPRC.
- Calibration.
- Sensitivity/specificity at selected threshold.
- False-positive and false-negative rates.

Avoid strong fairness claims when subgroup n is small.

## 18. Heterogeneous Treatment Effect Analysis

This should be secondary because the harmonized table pools heterogeneous trials.

Within each suitable parallel RCT:

- Estimate CATE for binary HbA1c improvement and continuous HbA1c change.
- Use causal forests, R-learner, X-learner, and doubly robust learners.
- Include only baseline covariates.
- Estimate treatment effect heterogeneity within trial, not across incompatible interventions.

Recommended trials:

- WISDM: CGM vs BGM.
- CITY: CGM vs BGM.
- SENCE: three-arm CGM/behavioral intervention comparison.
- METFORMIN_T1D: metformin vs placebo.
- REPLACE_BG: CGM-only vs CGM+BGM.

FLAIR requires a period-level crossover dataset before formal causal modeling.

Outputs:

- Average treatment effect with confidence interval.
- CATE distribution.
- Top effect modifiers.
- Calibration of treatment-effect predictions if possible.
- Policy value: expected outcome if treatment assigned by model vs observed/randomized assignment.

## 19. Sensitivity Analyses

Required:

1. Exclude local HbA1c fallback values and use central/STA HbA1c only.
2. Exclude FLAIR from pooled HbA1c models due to crossover design.
3. Train T1D-device trials only, excluding Metformin.
4. Train with and without treatment arm.
5. Train with and without study ID.
6. Compare complete-case analysis vs imputed baseline predictors.
7. Use alternative HbA1c improvement thresholds: >=0.3, >=0.5, >=1.0 percentage points.
8. Use alternative TIR thresholds: >=5 and >=10 percentage points.
9. Re-run top models across at least 10 random seeds.
10. Evaluate leave-one-study-out results as the main robustness analysis.

## 20. Reproducibility Plan

Create these scripts:

- `scripts/model_benchmark.py`: main nested-CV benchmark.
- `scripts/model_configs.yaml`: model search spaces and feature sets.
- `scripts/evaluate_models.py`: metrics, CIs, calibration, decision curves.
- `scripts/interpret_models.py`: SHAP/permutation/ALE/error analysis.
- `scripts/hte_analysis.py`: treatment-effect modeling.

Create these outputs:

- `results/model_performance_overall.csv`
- `results/model_performance_by_study.csv`
- `results/model_performance_by_subgroup.csv`
- `results/calibration_summary.csv`
- `results/decision_curve_summary.csv`
- `results/best_model_predictions.csv`
- `results/feature_importance.csv`
- `figures/roc_pr_curves.png`
- `figures/calibration_plots.png`
- `figures/decision_curves.png`
- `figures/shap_summary.png`

All random seeds, package versions, and raw-data hashes should be logged.

## 21. Proposed Analysis Workflow

### Phase 1: Data Audit

- Re-run `scripts/prepare_diabetes_rct_ml_dataset.py`.
- Confirm outcome counts and missingness.
- Freeze a versioned copy of `processed_ml_table.csv`.
- Generate SHA256 hashes for raw zips and processed CSV.

### Phase 2: Baseline Benchmarks

- Fit FS0-FS4 with logistic ridge, random forest, XGBoost, LightGBM, CatBoost.
- Use repeated nested CV.
- Produce initial leaderboard.

### Phase 3: Full Model Benchmark

- Add SVM, ExtraTrees, AutoML, MLP, FT-Transformer, TabNet, TabPFN.
- Fit all primary and secondary outcomes.
- Run leave-one-study-out validation.

### Phase 4: Calibration and Clinical Utility

- Recalibrate top models.
- Run decision-curve analysis.
- Choose final candidate model.

### Phase 5: Interpretability and Subgroup Analyses

- Generate SHAP/permutation importance.
- Analyze subgroup performance.
- Perform clinically oriented error analysis.

### Phase 6: HTE and Personalized Treatment Exploratory Analysis

- Run causal forests and doubly robust learners within each RCT.
- Compare treatment assignment policies.
- Keep claims cautious unless effects are stable.

### Phase 7: Manuscript Package

- Write TRIPOD+AI checklist.
- Add PROBAST+AI risk-of-bias table.
- Prepare code/data availability statement.
- Create reproducibility appendix.

## 22. Expected Reviewer Critiques and Preemptive Responses

| Likely critique | Design response |
|---|---|
| "The dataset is too heterogeneous." | Use study ID, study-specific validation, leave-one-study-out validation, and study-level subgroup reporting. |
| "Accuracy is not clinically meaningful." | Use AUROC/AUPRC, calibration, Brier, decision curves, and clinical thresholds. |
| "Deep models are overfit." | Use nested CV, early stopping, strict tuning budgets, and external validation. |
| "RCT data do not imply prediction model clinical utility." | Frame as retrospective secondary analysis and benchmark; prospective validation is future work. |
| "Treatment arms differ across studies." | Separate assigned-treatment prediction from within-trial HTE analysis. |
| "Missing data may bias results." | Report missingness, compare imputed vs complete-case sensitivity analyses, no outcome imputation. |
| "Foundation model claims are overhyped." | Treat TabPFN/fine-tuning as a benchmark arm; compare against strong GBDT baselines. |

## 23. Minimum Bar for a Top-Journal Submission

Before submission, the project should have:

- A locked protocol or analysis plan.
- Public reproducible code.
- Clear data-source inventory and raw-data provenance.
- Nested CV and leave-one-study-out validation.
- Calibration and decision-curve analysis.
- Sensitivity analyses.
- Subgroup analysis.
- Model interpretability and error analysis.
- TRIPOD+AI checklist.
- PROBAST+AI risk-of-bias assessment.
- A restrained clinical claim.

## 24. Recommended Primary Experiment to Implement First

Run the following first because it is high-yield and publishable:

Primary target:

- `y_hba1c_improved_ge_0_5`

Feature sets:

- FS1, FS3, FS4, FS6.

Models:

- Logistic ridge.
- Random forest.
- XGBoost.
- LightGBM.
- CatBoost.
- FT-Transformer.
- TabNet.
- TabPFN.
- Super Learner ensemble.

Validation:

- 5x5 repeated nested CV.
- Leave-one-study-out validation.

Metrics:

- AUROC, AUPRC, Brier, calibration slope/intercept, balanced accuracy, decision curve.

Selection:

- Pick the model with best validated AUROC only if calibration and leave-one-study-out performance are acceptable.

## 25. Reference Sources Reviewed

- JAEB Center public diabetes datasets: https://public.jaeb.org/datasets/diabetes
- TRIPOD+AI, EQUATOR summary and BMJ reference: https://www.equator-network.org/reporting-guidelines/tripod-statement/
- TRIPOD+AI statement, PubMed: https://pubmed.ncbi.nlm.nih.gov/38626948/
- PROBAST+AI risk-of-bias tool summary: https://www.latitudes-network.org/tool/probastai/
- CONSORT-AI extension, Nature Medicine: https://www.nature.com/articles/s41591-020-1034-x
- SPIRIT-AI extension, Nature Medicine: https://www.nature.com/articles/s41591-020-1037-7
- International Consensus on Time in Range, Diabetes Care/PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC6973648/
- ADA Standards of Care 2026 glycemic goals: https://diabetesjournals.org/care/article/49/Supplement_1/S132/163927/6-Glycemic-Goals-Hypoglycemia-and-Hyperglycemic
- TabPFN Nature paper/PubMed: https://pubmed.ncbi.nlm.nih.gov/39780007/
- TabPFN ICLR 2023 OpenReview: https://openreview.net/forum?id=cp5PvcI6w8_
- Why tree-based models still outperform deep learning on tabular data: https://arxiv.org/abs/2207.08815
- Tabular Data: Deep Learning is Not All You Need: https://arxiv.org/abs/2106.03253
- Revisiting Deep Learning Models for Tabular Data: https://openreview.net/forum?id=i_Q1yrOegLY
- TabNet: Attentive Interpretable Tabular Learning: https://ojs.aaai.org/index.php/AAAI/article/view/16826
- Calibration in predictive analytics: https://link.springer.com/article/10.1186/s12916-019-1466-7
- Decision curve analysis original paper/PubMed: https://pubmed.ncbi.nlm.nih.gov/17099194/

