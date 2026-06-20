# npj Digital Medicine P0 Extension Completion Report

## Completed items

1. External data compatibility matrix across GLAM, RacialDifferences, SevereHypo, CGMND, CGMNDYoungChildren and PSO1/3/4.
2. Additional frozen validation using eligible secondary datasets, without retraining or tuning on those datasets.
3. Loop and LOSO calibration upgrade with calibration bins, slope/intercept, ECE and Brier decomposition.
4. Prespecified TIR intercept/slope recalibration sensitivity.
5. Subgroup fairness and transportability uncertainty with bootstrap confidence intervals and minimum-n reporting rules.
6. Versioned phase-map research software release bundle with schema, toy data, tests and environment files.

## Compatibility summary

           dataset  n_with_cgm  n_baseline_hba1c  n_followup_hba1c                    followup_tir_possible                validation_decision                                                                                                                   reason
              GLAM         886                 4                 0 yes_raw_cgm_but_no_followup_visit_anchor                       not_eligible                    CGM is rich but HbA1c table has only four participants and no usable follow-up HbA1c response target.
 RacialDifferences         225               230               199                 yes_last_14_days_raw_cgm          eligible_secondary_frozen          Raw CGM, baseline HbA1c and final HbA1c are available; observational context differs from RCT training studies.
        SevereHypo         200               201                 0                no_clear_followup_outcome                       not_eligible Case-control severe hypoglycaemia dataset has baseline HbA1c/CGM but no follow-up HbA1c or intervention-response target.
             CGMND         169               174                 0              no_diabetes_response_target not_eligible_for_diabetes_response       Non-diabetic CGM reference cohort; useful for physiological contrast, not HbA1c/TIR treatment-response validation.
CGMNDYoungChildren          45                45                 0              no_diabetes_response_target not_eligible_for_diabetes_response                                         Young non-diabetic CGM reference cohort; no follow-up treatment-response target.
              PSO1          20                 0                 0              yes_raw_cgm_but_n_too_small                       not_eligible                                                                       Only 20 participants and no HbA1c response target.
              PSO3          47                29                45                 yes_last_14_days_raw_cgm         eligible_small_descriptive        Raw CGM, baseline HbA1c and final HbA1c exist, but sample size is small; pool with PSO4 for secondary validation.
              PSO4          87                82                81                 yes_last_14_days_raw_cgm          eligible_secondary_frozen            Raw CGM, baseline HbA1c and final HbA1c exist; pediatric sensor/pump context differs from development corpus.

## Additional frozen validation

       validation_dataset                  target          feature_set  test_n  positive_rate    auroc    auprc    brier  expected_calibration_error
RACIAL_DIFFERENCES_FROZEN y_hba1c_improved_ge_0_5 C2_clinical_plus_cgm     199       0.261307 0.708530 0.457073 0.305474                    0.346163
RACIAL_DIFFERENCES_FROZEN y_hba1c_improved_ge_0_5         C4_phase_map     199       0.261307 0.704082 0.430374 0.265599                    0.265738
RACIAL_DIFFERENCES_FROZEN  y_tir_improved_ge_5pct C2_clinical_plus_cgm     225       0.266667 0.701919 0.447586 0.246873                    0.226563
RACIAL_DIFFERENCES_FROZEN  y_tir_improved_ge_5pct         C4_phase_map     225       0.266667 0.698283 0.437601 0.251672                    0.231057
              PSO3_FROZEN y_hba1c_improved_ge_0_5 C2_clinical_plus_cgm      29       0.068966 0.555556 0.121429 0.124007                    0.219715
              PSO3_FROZEN y_hba1c_improved_ge_0_5         C4_phase_map      29       0.068966 0.592593 0.135965 0.079600                    0.108779
              PSO3_FROZEN  y_tir_improved_ge_5pct C2_clinical_plus_cgm      47       0.234043 0.686869 0.370864 0.177400                    0.100691
              PSO3_FROZEN  y_tir_improved_ge_5pct         C4_phase_map      47       0.234043 0.686869 0.384239 0.179064                    0.108112
              PSO4_FROZEN y_hba1c_improved_ge_0_5 C2_clinical_plus_cgm      81       0.185185 0.804040 0.398829 0.197235                    0.259471
              PSO4_FROZEN y_hba1c_improved_ge_0_5         C4_phase_map      81       0.185185 0.782828 0.387202 0.153317                    0.141415
              PSO4_FROZEN  y_tir_improved_ge_5pct C2_clinical_plus_cgm      87       0.298851 0.763556 0.681220 0.163948                    0.119444
              PSO4_FROZEN  y_tir_improved_ge_5pct         C4_phase_map      87       0.298851 0.762295 0.681664 0.162137                    0.112806
  PSO3_PSO4_POOLED_FROZEN y_hba1c_improved_ge_0_5 C2_clinical_plus_cgm     110       0.154545 0.784946 0.369551 0.177930                    0.248990
  PSO3_PSO4_POOLED_FROZEN y_hba1c_improved_ge_0_5         C4_phase_map     110       0.154545 0.778621 0.363120 0.133882                    0.132811
  PSO3_PSO4_POOLED_FROZEN  y_tir_improved_ge_5pct C2_clinical_plus_cgm     134       0.276119 0.730287 0.588217 0.168666                    0.077521
  PSO3_PSO4_POOLED_FROZEN  y_tir_improved_ge_5pct         C4_phase_map     134       0.276119 0.728615 0.590173 0.168074                    0.091022

Interpretation: RacialDifferences and PSO3/4 are transportability/sensitivity validations. They are not used for tuning. RacialDifferences is observational and PSO datasets have smaller sample sizes than Loop, so these are secondary evidence rather than a replacement for Loop.

## Calibration upgrade

   prediction_source                  target          feature_set                       model    n    auroc    brier  calibration_slope  calibration_intercept  expected_calibration_error  brier_reliability  brier_resolution  brier_uncertainty
         LOOP_FROZEN y_hba1c_improved_ge_0_5 C2_clinical_plus_cgm logistic_ridge_locked_train  521 0.764477 0.163286           1.214209               0.403385                    0.044148           0.004044          0.032715           0.192896
         LOOP_FROZEN y_hba1c_improved_ge_0_5         C4_phase_map logistic_ridge_locked_train  521 0.757945 0.177336           1.115584               0.902284                    0.103350           0.017377          0.033248           0.192896
         LOOP_FROZEN  y_tir_improved_ge_5pct C2_clinical_plus_cgm logistic_ridge_locked_train  633 0.828609 0.244505           1.199412               1.821905                    0.234858           0.078595          0.076394           0.244604
         LOOP_FROZEN  y_tir_improved_ge_5pct         C4_phase_map logistic_ridge_locked_train  633 0.826946 0.241566           1.134418               1.700129                    0.230581           0.074804          0.076316           0.244604
LOSO_LOCKED_LOGISTIC y_hba1c_improved_ge_0_5 C2_clinical_plus_cgm         logistic_ridge_loso 1955 0.748788 0.207416           0.717405              -0.595406                    0.112536           0.015969          0.040569           0.232381
LOSO_LOCKED_LOGISTIC y_hba1c_improved_ge_0_5         C4_phase_map         logistic_ridge_loso 1955 0.742121 0.210767           0.651660              -0.596161                    0.113778           0.017700          0.037910           0.232381
LOSO_LOCKED_LOGISTIC  y_tir_improved_ge_5pct C2_clinical_plus_cgm         logistic_ridge_loso  641 0.691872 0.232623           0.503495              -0.272720                    0.130320           0.021993          0.033292           0.244037
LOSO_LOCKED_LOGISTIC  y_tir_improved_ge_5pct         C4_phase_map         logistic_ridge_loso  641 0.682268 0.235287           0.469506              -0.231522                    0.135722           0.022906          0.032304           0.244037

## TIR recalibration sensitivity

   prediction_source                 target          feature_set                       model                                             method  calibration_intercept_used  calibration_slope_used  raw_brier  recalibrated_brier  raw_ece  recalibrated_ece  raw_mean_predicted_risk  recalibrated_mean_predicted_risk  observed_rate                          interpretation
         LOOP_FROZEN y_tir_improved_ge_5pct C2_clinical_plus_cgm logistic_ridge_locked_train apparent_intercept_slope_recalibration_sensitivity                    1.821905                1.199412   0.244505            0.169405 0.234858          0.063161                 0.194044                          0.426592       0.426540 sensitivity_only_not_a_new_frozen_model
         LOOP_FROZEN y_tir_improved_ge_5pct         C4_phase_map logistic_ridge_locked_train apparent_intercept_slope_recalibration_sensitivity                    1.700129                1.134418   0.241566            0.169619 0.230581          0.052256                 0.197909                          0.426597       0.426540 sensitivity_only_not_a_new_frozen_model
LOSO_LOCKED_LOGISTIC y_tir_improved_ge_5pct C2_clinical_plus_cgm         logistic_ridge_loso apparent_intercept_slope_recalibration_sensitivity                   -0.272720                0.503495   0.232623            0.215527 0.130320          0.058449                 0.469663                          0.422798       0.422777 sensitivity_only_not_a_new_frozen_model
LOSO_LOCKED_LOGISTIC y_tir_improved_ge_5pct         C4_phase_map         logistic_ridge_loso apparent_intercept_slope_recalibration_sensitivity                   -0.231522                0.469506   0.235287            0.217727 0.135722          0.061892                 0.453923                          0.422778       0.422777 sensitivity_only_not_a_new_frozen_model

Interpretation: recalibration rows are apparent sensitivity analyses, not new frozen models. If recalibrated ECE improves materially but raw ECE remains high, the manuscript should present absolute-risk displays cautiously and emphasize phenotype/ranking use.

## Fairness uncertainty highlights

                 target  feature_set          model    subgroup_variable           subgroup_display   n    auroc  auroc_ci_low  auroc_ci_high  expected_calibration_error  ece_ci_low  ece_ci_high               minimum_n_rule
y_hba1c_improved_ge_0_5  C1_clinical logistic_ridge               x_race                      asian  29 0.361111      0.150626       0.637283                    0.297055    0.194871     0.513498 small_n_no_strong_conclusion
y_hba1c_improved_ge_0_5  C1_clinical       lightgbm               x_race                      asian  29 0.444444      0.220588       0.698630                    0.225873    0.163439     0.450482 small_n_no_strong_conclusion
y_hba1c_improved_ge_0_5  C1_clinical        xgboost               x_race                      asian  29 0.461111      0.228934       0.714028                    0.173292    0.123898     0.441779 small_n_no_strong_conclusion
y_hba1c_improved_ge_0_5 C4_phase_map        xgboost               x_race                      asian  29 0.472222      0.243231       0.719911                    0.169840    0.139760     0.446951 small_n_no_strong_conclusion
y_hba1c_improved_ge_0_5  C1_clinical        xgboost             study_id              METFORMIN_T1D 137 0.531041      0.417176       0.643988                    0.055536    0.053968     0.194491       primary_interpretation
y_hba1c_improved_ge_0_5  C1_clinical       lightgbm             study_id              METFORMIN_T1D 137 0.540627      0.418625       0.651136                    0.160702    0.088715     0.265754       primary_interpretation
y_hba1c_improved_ge_0_5 C4_phase_map        xgboost             study_id              METFORMIN_T1D 137 0.540475      0.427284       0.653182                    0.050782    0.054410     0.190631       primary_interpretation
y_hba1c_improved_ge_0_5 C4_phase_map        xgboost baseline_hba1c_group                         <7 466 0.577644      0.480540       0.664749                    0.046625    0.019663     0.090142       primary_interpretation
y_hba1c_improved_ge_0_5 C4_phase_map        xgboost          phase_label Circadian-disruption phase  91 0.583157      0.450694       0.696193                    0.110301    0.103007     0.290593             descriptive_only
y_hba1c_improved_ge_0_5  C1_clinical       lightgbm baseline_hba1c_group                         <7 466 0.589585      0.500209       0.671717                    0.073936    0.054925     0.119577       primary_interpretation

Minimum-n rule:

- primary_interpretation: n >= 100 and at least 20 events/non-events.
- descriptive_only: n >= 50 and at least 10 events/non-events.
- small_n_no_strong_conclusion: otherwise.

## Software release

Software bundle: `D:\ai for science\results\npj_digital_medicine_phase_strategy\p0_extensions_2026_06_18\software_release\phase_map_jaeb_v0_1`

Files: 14 release files. Test command:

`python -m unittest discover -s tests`
