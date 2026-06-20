# npj Digital Medicine P0 Workup Report

## Completed P0 Items

1. Frozen external validation using the held-out JAEB Loop public dataset.
2. Phase-map algorithm card and software specification.
3. Subgroup fairness and calibration audit.
4. Phase-guided digital care workflow source data.
5. Redesigned main figures centered on a CGM digital phenotype.

## Frozen External Validation

The Loop study was treated as a locked external validation dataset and was not used for model tuning. Baseline CGM summaries were mapped to the original JAEB phase-map centroids using fixed training-set reference statistics.

                             dataset                                 zip_file                               role  n_with_baseline_cgm  n_with_month6_cgm  n_with_baseline_hba1c  n_with_month6_hba1c                                                 phase_assignment                                 notes
Loop study public dataset 2023-01-31 Loop study public dataset 2023-01-31.zip primary frozen external validation                  668                633                    598                  545 nearest fixed centroid from original JAEB phase-map training set No retraining or tuning on Loop data.

### Loop Phase Distribution

                    phase_id                     phase_label_en   n
             stable_in_range              Stable in-range phase 543
high_variability_oscillation High-variability oscillatory phase  87
   persistent_hyperglycaemia    Persistent hyperglycaemia phase  34
   hypoglycaemia_susceptible    Hypoglycaemia-susceptible phase   4

### External Prediction Metrics

  n  positive_rate  mean_predicted_risk    brier    auroc    auprc  calibration_slope  calibration_intercept  expected_calibration_error validation_dataset                  target          feature_set                       model  train_n  test_n                                                                                                                                                                                                                                                                                                                                                                      numeric_features                                                categorical_features
521       0.261036             0.233745 0.163286 0.764477 0.525878           1.214209               0.403385                    0.044148        LOOP_FROZEN y_hba1c_improved_ge_0_5 C2_clinical_plus_cgm logistic_ridge_locked_train     1955     521                                                                                                                                          x_age_years; x_baseline_hba1c_pct; x_baseline_bmi; x_diabetes_duration_years; cgm_mean_glucose_mg_dl; cgm_time_in_range_70_180_pct; cgm_time_below_70_pct; cgm_time_below_54_pct; cgm_time_above_180_pct; cgm_time_above_250_pct; cgm_cv_pct              study_id; x_randomized_arm; x_sex; x_race; x_ethnicity
521       0.261036             0.160226 0.177336 0.757945 0.517518           1.115584               0.902284                    0.103350        LOOP_FROZEN y_hba1c_improved_ge_0_5         C4_phase_map logistic_ridge_locked_train     1955     521 x_age_years; x_baseline_hba1c_pct; x_baseline_bmi; x_diabetes_duration_years; cgm_mean_glucose_mg_dl; cgm_time_in_range_70_180_pct; cgm_time_below_70_pct; cgm_time_below_54_pct; cgm_time_above_180_pct; cgm_time_above_250_pct; cgm_cv_pct; glycemic_burden_score; hypoglycemic_susceptibility_score; dynamic_instability_score; circadian_disruption_score; resilience_proxy_score study_id; x_randomized_arm; x_sex; x_race; x_ethnicity; phase_label
633       0.426540             0.194044 0.244505 0.828609 0.755848           1.199412               1.821905                    0.234858        LOOP_FROZEN  y_tir_improved_ge_5pct C2_clinical_plus_cgm logistic_ridge_locked_train      641     633                                                                                                                                          x_age_years; x_baseline_hba1c_pct; x_baseline_bmi; x_diabetes_duration_years; cgm_mean_glucose_mg_dl; cgm_time_in_range_70_180_pct; cgm_time_below_70_pct; cgm_time_below_54_pct; cgm_time_above_180_pct; cgm_time_above_250_pct; cgm_cv_pct              study_id; x_randomized_arm; x_sex; x_race; x_ethnicity
633       0.426540             0.197909 0.241566 0.826946 0.755442           1.134418               1.700129                    0.230581        LOOP_FROZEN  y_tir_improved_ge_5pct         C4_phase_map logistic_ridge_locked_train      641     633 x_age_years; x_baseline_hba1c_pct; x_baseline_bmi; x_diabetes_duration_years; cgm_mean_glucose_mg_dl; cgm_time_in_range_70_180_pct; cgm_time_below_70_pct; cgm_time_below_54_pct; cgm_time_above_180_pct; cgm_time_above_250_pct; cgm_cv_pct; glycemic_burden_score; hypoglycemic_susceptibility_score; dynamic_instability_score; circadian_disruption_score; resilience_proxy_score study_id; x_randomized_arm; x_sex; x_race; x_ethnicity; phase_label

## Subgroup Audit Highlights

The subgroup audit uses out-of-fold predictions from the original JAEB development package. It reports calibration and performance by age, sex, race/ethnicity, study, baseline HbA1c and phase label.

Largest evaluable AUROC deviations:

                 target  feature_set          model    subgroup_variable                   subgroup   n    auroc  delta_auroc_vs_overall    brier
y_hba1c_improved_ge_0_5  C1_clinical logistic_ridge               x_race                      asian  29 0.361111               -0.437771 0.301007
y_hba1c_improved_ge_0_5  C1_clinical       lightgbm               x_race                      asian  29 0.444444               -0.355927 0.268726
y_hba1c_improved_ge_0_5  C1_clinical        xgboost               x_race                      asian  29 0.461111               -0.338434 0.256866
y_hba1c_improved_ge_0_5 C4_phase_map        xgboost               x_race                      asian  29 0.472222               -0.326615 0.253761
y_hba1c_improved_ge_0_5  C1_clinical        xgboost             study_id              METFORMIN_T1D 137 0.531041               -0.268504 0.182065
y_hba1c_improved_ge_0_5  C1_clinical       lightgbm             study_id              METFORMIN_T1D 137 0.540627               -0.259744 0.200233
y_hba1c_improved_ge_0_5 C4_phase_map        xgboost             study_id              METFORMIN_T1D 137 0.540475               -0.258362 0.179906
y_hba1c_improved_ge_0_5 C4_phase_map        xgboost baseline_hba1c_group                         <7 466 0.577644               -0.221193 0.094032
y_hba1c_improved_ge_0_5 C4_phase_map        xgboost          phase_label Circadian-disruption phase  91 0.583157               -0.215680 0.236289
y_hba1c_improved_ge_0_5  C1_clinical       lightgbm baseline_hba1c_group                         <7 466 0.589585               -0.210786 0.100294

## Interpretation

The Loop frozen validation is a transportability test, not a new tuning exercise. Because Loop lacks some demographic covariates used in the development models, external prediction metrics should be interpreted alongside calibration and phase-distribution shift. The strongest npj Digital Medicine framing remains the computable CGM digital phenotype and phase-guided workflow, with model performance as validation rather than the central claim.
