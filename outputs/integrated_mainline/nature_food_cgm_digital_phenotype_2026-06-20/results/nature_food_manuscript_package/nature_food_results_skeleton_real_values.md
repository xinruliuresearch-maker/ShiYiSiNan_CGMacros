# Nature Food Results Skeleton

## DEHP oxidative metabolism anchored a metabolic-susceptibility phenotype in NHANES

In survey-weighted NHANES 2013-2018 models, a 10 percentage-point higher oxidative DEHP metabolite fraction was associated with higher MSI-core (beta 0.168 (0.060, 0.277), q=0.008, n=1313). The same exposure contrast was associated with higher HOMA-IR (19.958 (6.300, 35.371)% difference, q=0.007, n=1292) and HbA1c (beta 0.110 (0.022, 0.197), q=0.019, n=2671).

The oxidative-vs-primary DEHP balance produced a similar pattern. The ILR oxidative-vs-primary contrast was associated with MSI-core (beta 0.206 (0.108, 0.304), q=0.001). After adjustment for total DEHP burden, this association remained for MSI-core (beta 0.199 (0.098, 0.301), q=0.001), HOMA-IR (25.998 (10.268, 43.972)% difference, q=0.003) and HbA1c (beta 0.142 (0.058, 0.226), q=0.004). Across cycle-specific models, primary oxidative-profile estimates were positive in 12/18 cycle-outcome-exposure checks.

## The NHANES-derived susceptibility score predicted PPGR vulnerability in CGMacros

In CGMacros, the analysis included 1498 free-living meals from 40 participants with complete human-adjudicated food-matrix labels. MSI-core was strongly associated with all three PPGR endpoints: log1p 2h iAUC (beta 1.141 (0.658, 1.624), q=<0.001), peak glucose delta (beta 28.896 (18.814, 38.979), q=<0.001) and high-iAUC meal risk (log-odds 1.344 (0.727, 1.961), q=<0.001).

## Collapsing food matrix labels retained a stable meal-context signal

Human final-label coverage was 100.0%; the dual-review Cohen kappa was 0.369. To reduce sensitivity to sparse six-class labels, we collapsed the food matrix into protective whole-food/low-carb, mixed/unknown, and rapid-digestible/liquid-carbohydrate classes. Compared with the protective class, mixed/unknown meals had higher PPGR across outcomes: log1p 2h iAUC (beta 0.616 (0.401, 0.831), p=<0.001), peak delta (beta 10.672 (6.261, 15.083), p=<0.001) and high-iAUC risk (log-odds 0.696 (0.425, 0.966), p=<0.001).

Leave-one-subject-out analyses supported stability rather than single-subject leverage. The MSI-core coefficient remained positive in 40/40 leave-one-subject-out models, and the mixed/unknown food-matrix coefficient remained positive in 40/40 leave-one-subject-out models.

## MSI and food matrix improved subject-held-out PPGR risk stratification

In leave-one-subject-out validation, a macro/timing model had high-iAUC AUC 0.573. Adding MSI-core increased AUC to 0.654 (delta 0.081); adding human-adjudicated food matrix increased AUC to 0.677 (delta 0.104). The full nutrition plus matrix model had the highest high-iAUC AUC (0.696) but worse continuous log1p iAUC RMSE than the more parsimonious MSI-plus-matrix model (2.973 vs 2.192), so we treat the MSI-plus-matrix model as the primary interpretable prediction model and the full model as a risk-classification sensitivity analysis.

## Counterfactual meal redesign suggested a translatable risk-reduction layer

Among high-priority high-MSI/high-response candidate meals, replacing the original lower-protection food matrix with a fiber-rich/whole-food matrix reduced predicted high-iAUC risk from a median 0.801 to 0.643. The median predicted risk difference was -0.157 (IQR -0.177 to -0.139); negative values indicate lower predicted high-iAUC risk after redesign. These estimates are model-based counterfactuals and define candidate meal prototypes for controlled validation rather than causal proof of diet substitution.

## Figure Mapping

- Figure 1: cohort overview, analysis roadmap, and readiness dashboard.
- Figure 2: NHANES oxidative DEHP profile, composition-adjusted models, and cycle consistency.
- Figure 3: CGMacros MSI-PPGR associations, human food-matrix distribution, collapsed matrix GEE, and subject leverage.
- Figure 4: LOSO model ladder, counterfactual high-iAUC deltas, redesign summary, and observed collapsed-matrix risk.
