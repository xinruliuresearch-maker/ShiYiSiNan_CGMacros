# Nature Food Aim 1: NHANES DEHP oxidative profile and metabolic susceptibility
#
# This is the final intended R survey implementation. It preserves NHANES
# complex survey design through the survey package. The current machine may not
# have R installed; run with:
#
#   Rscript "D:/ai for science/scripts/run_nature_food_aim1_nhanes_survey.R"
#
# Outputs:
#   D:/ai for science/results/nature_food_aim1_nhanes/

options(stringsAsFactors = FALSE)
options(survey.lonely.psu = "adjust")

suppressPackageStartupMessages({
  library(survey)
})

ROOT <- "D:/ai for science"
NHANES <- "D:/NHANES_MetS_Project"
OUT <- file.path(ROOT, "results", "nature_food_aim1_nhanes")
dir.create(OUT, recursive = TRUE, showWarnings = FALSE)

read_csv_base <- function(path) {
  read.csv(path, check.names = FALSE)
}

write_csv <- function(x, path) {
  write.csv(x, path, row.names = FALSE, na = "")
}

safe_log <- function(x) {
  x <- suppressWarnings(as.numeric(x))
  x[x <= 0] <- NA_real_
  log(x)
}

merge_dual_msi <- function(df) {
  dual_path <- "D:/ShiYiSiNan_CGMacros/outputs/integrated_mainline/high_impact_computational_upgrade_2026-06-11/01_nhanes_dual_msi_dataset.csv"
  if (!file.exists(dual_path)) return(df)
  dual <- read_csv_base(dual_path)
  keep <- intersect(
    c("SEQN", "msi_core_partial", "msi_core_complete", "msi_no_bmi",
      "msi_glycemia_ir", "exposure_facing_msi", "response_vulnerability_index"),
    names(dual)
  )
  dual <- dual[, keep, drop = FALSE]
  merged <- merge(df, dual, by = "SEQN", all.x = TRUE, suffixes = c("", "_dual"))
  for (nm in setdiff(keep, "SEQN")) {
    alt <- paste0(nm, "_dual")
    if (alt %in% names(merged)) {
      if (!(nm %in% names(df))) merged[[nm]] <- merged[[alt]]
      merged[[alt]] <- NULL
    }
  }
  merged
}

ensure_vars <- function(df) {
  if (!("ln_URXUCR" %in% names(df)) && "URXUCR" %in% names(df)) df$ln_URXUCR <- safe_log(df$URXUCR)
  if (!("HbA1c" %in% names(df)) && "LBXGH" %in% names(df)) df$HbA1c <- df$LBXGH
  if (!("ln_HOMA_IR" %in% names(df)) && "HOMA_IR" %in% names(df)) df$ln_HOMA_IR <- safe_log(df$HOMA_IR)
  if (!("ln_TG_HDL" %in% names(df)) && "TG_HDL" %in% names(df)) df$ln_TG_HDL <- safe_log(df$TG_HDL)
  if (!("pct_oxidative_10" %in% names(df)) && "pct_oxidative" %in% names(df)) df$pct_oxidative_10 <- df$pct_oxidative / 10
  if (!("pct_oxidative_10_comp" %in% names(df)) && "pct_oxidative_comp" %in% names(df)) df$pct_oxidative_10_comp <- df$pct_oxidative_comp / 10
  df
}

main_path <- file.path(NHANES, "output", "NHANES_2013_2018_diabetes_medication_sensitivity_dataset_with_DIQ050_DIQ070.csv")
if (!file.exists(main_path)) {
  main_path <- file.path(NHANES, "output", "NHANES_2013_2018_exposure_sensitivity_dataset.csv")
}
df <- ensure_vars(merge_dual_msi(read_csv_base(main_path)))

factor_vars <- c("RIAGENDR", "RIDRETH3", "DMDEDUC2", "ever_smoker",
                 "alcohol_ever", "any_physical_activity", "cycle")
for (v in intersect(factor_vars, names(df))) df[[v]] <- as.factor(df[[v]])

base_covars <- c(
  "RIDAGEYR", "RIAGENDR", "RIDRETH3", "DMDEDUC2", "INDFMPIR",
  "DR1TKCAL", "ever_smoker", "alcohol_ever", "any_physical_activity",
  "ln_URXUCR", "cycle"
)
base_terms <- paste(
  c("RIDAGEYR", "RIAGENDR", "RIDRETH3", "DMDEDUC2", "INDFMPIR",
    "DR1TKCAL", "ever_smoker", "alcohol_ever", "any_physical_activity",
    "ln_URXUCR", "cycle"),
  collapse = " + "
)

outcomes <- data.frame(
  outcome = c("msi_core_partial", "ln_HOMA_IR", "HbA1c", "TyG", "ln_TG_HDL"),
  label = c("MSI-core", "ln(HOMA-IR)", "HbA1c", "TyG", "ln(TG/HDL-C)"),
  log_outcome = c(FALSE, TRUE, FALSE, FALSE, TRUE)
)

exposures <- data.frame(
  exposure = c("ln_Sigma_DEHP", "pct_oxidative_10", "ln_oxidative_to_MEHP",
               "ilr_oxidative_vs_primary"),
  label = c("ln(Sigma DEHP)", "%Oxidative per 10 pp",
            "ln(Oxidative/MEHP)", "ILR oxidative-vs-primary"),
  stringsAsFactors = FALSE
)

needed_design <- c("SDMVPSU", "SDMVSTRA", "WTSB6YR_MAIN")

model_effect <- function(beta, se, log_outcome, df_resid) {
  tcrit <- ifelse(is.na(df_resid) || df_resid <= 0, 1.96, qt(0.975, df = df_resid))
  lo <- beta - tcrit * se
  hi <- beta + tcrit * se
  if (log_outcome) {
    c(effect = (exp(beta) - 1) * 100,
      effect_low = (exp(lo) - 1) * 100,
      effect_high = (exp(hi) - 1) * 100)
  } else {
    c(effect = beta, effect_low = lo, effect_high = hi)
  }
}

run_svy_linear <- function(dat, outcome, exposure, log_outcome,
                           scenario = "main", weight = "WTSB6YR_MAIN",
                           extra_terms = NULL, drop_creatinine = FALSE,
                           drop_cycle = FALSE) {
  covars <- base_covars
  terms <- base_terms
  if (drop_creatinine) {
    covars <- setdiff(covars, "ln_URXUCR")
    terms <- paste(setdiff(strsplit(base_terms, " \\+ ")[[1]], "ln_URXUCR"), collapse = " + ")
  }
  if (drop_cycle) {
    covars <- setdiff(covars, "cycle")
    terms <- paste(setdiff(strsplit(terms, " \\+ ")[[1]], "cycle"), collapse = " + ")
  }
  all_vars <- unique(c(outcome, exposure, covars, needed_design, weight, extra_terms))
  if (!all(all_vars %in% names(dat))) {
    return(data.frame(scenario = scenario, outcome = outcome, exposure = exposure,
                      n = 0, beta = NA, se = NA, p_value = NA, effect = NA,
                      effect_low = NA, effect_high = NA, status = "missing_variable"))
  }
  d <- dat[, all_vars, drop = FALSE]
  d <- d[complete.cases(d) & d[[weight]] > 0, , drop = FALSE]
  if (nrow(d) < 100 || length(unique(d[[exposure]])) < 5) {
    return(data.frame(scenario = scenario, outcome = outcome, exposure = exposure,
                      n = nrow(d), beta = NA, se = NA, p_value = NA, effect = NA,
                      effect_low = NA, effect_high = NA, status = "too_few_rows"))
  }
  des <- svydesign(
    ids = as.formula("~SDMVPSU"),
    strata = as.formula("~SDMVSTRA"),
    weights = as.formula(paste0("~", weight)),
    nest = TRUE,
    data = d
  )
  rhs <- paste(c(exposure, terms, extra_terms), collapse = " + ")
  fit <- tryCatch(svyglm(as.formula(paste(outcome, "~", rhs)), design = des),
                  error = function(e) e)
  if (inherits(fit, "error")) {
    return(data.frame(scenario = scenario, outcome = outcome, exposure = exposure,
                      n = nrow(d), beta = NA, se = NA, p_value = NA, effect = NA,
                      effect_low = NA, effect_high = NA, status = fit$message))
  }
  coefs <- summary(fit)$coefficients
  if (!(exposure %in% rownames(coefs))) {
    return(data.frame(scenario = scenario, outcome = outcome, exposure = exposure,
                      n = nrow(d), beta = NA, se = NA, p_value = NA, effect = NA,
                      effect_low = NA, effect_high = NA, status = "term_not_found"))
  }
  beta <- coefs[exposure, "Estimate"]
  se <- coefs[exposure, "Std. Error"]
  p_col <- intersect(c("Pr(>|t|)", "Pr(>|z|)"), colnames(coefs))
  p <- if (length(p_col) > 0) coefs[exposure, p_col[1]] else NA_real_
  if (is.na(p) && is.finite(beta) && is.finite(se) && se > 0) {
    df_resid_tmp <- fit$df.residual
    if (is.na(df_resid_tmp) || df_resid_tmp <= 0) {
      p <- 2 * pnorm(abs(beta / se), lower.tail = FALSE)
    } else {
      p <- 2 * pt(abs(beta / se), df = df_resid_tmp, lower.tail = FALSE)
    }
  }
  eff <- model_effect(beta, se, log_outcome, fit$df.residual)
  data.frame(scenario = scenario, outcome = outcome, exposure = exposure,
             n = nrow(d), beta = beta, se = se, p_value = p,
             effect = eff["effect"], effect_low = eff["effect_low"],
             effect_high = eff["effect_high"], status = "ok")
}

add_q <- function(res) {
  if (nrow(res) == 0) return(res)
  res$q_value <- ave(res$p_value, res$outcome, FUN = function(x) p.adjust(x, method = "BH"))
  res
}

rows <- list()
k <- 1
for (i in seq_len(nrow(outcomes))) {
  for (j in seq_len(nrow(exposures))) {
    rows[[k]] <- run_svy_linear(df, outcomes$outcome[i], exposures$exposure[j], outcomes$log_outcome[i])
    k <- k + 1
  }
}
main_results <- add_q(do.call(rbind, rows))
write_csv(main_results, file.path(OUT, "aim1_main_survey_results.csv"))

# LOD / creatinine / urine dilution sensitivity.
sens_specs <- list(
  list(name = "main", exposure = "pct_oxidative_10", restrict = NULL, drop_cr = FALSE),
  list(name = "drop_urinary_creatinine_covariate", exposure = "pct_oxidative_10", restrict = NULL, drop_cr = TRUE),
  list(name = "valid_creatinine_30_300", exposure = "pct_oxidative_10", restrict = "urinary_creatinine_valid_30_300", drop_cr = FALSE),
  list(name = "all_oxidative_detected", exposure = "pct_oxidative_10", restrict = "all_oxidative_detected", drop_cr = FALSE),
  list(name = "winsorized_pct_oxidative", exposure = "pct_oxidative_10_w", restrict = NULL, drop_cr = FALSE),
  list(name = "creatinine_standardized_total_dehp", exposure = "ln_cr_Sigma_DEHP", restrict = NULL, drop_cr = TRUE),
  list(name = "all_dehp_detected_total", exposure = "ln_Sigma_DEHP", restrict = "all_dehp_detected", drop_cr = FALSE)
)
rows <- list(); k <- 1
for (sp in sens_specs) {
  dat <- df
  if (!is.null(sp$restrict) && sp$restrict %in% names(dat)) dat <- dat[dat[[sp$restrict]] == 1, , drop = FALSE]
  for (out in c("msi_core_partial", "ln_HOMA_IR", "HbA1c")) {
    log_out <- outcomes$log_outcome[match(out, outcomes$outcome)]
    rows[[k]] <- run_svy_linear(dat, out, sp$exposure, log_out,
                                scenario = sp$name, drop_creatinine = sp$drop_cr)
    k <- k + 1
  }
}
sensitivity_results <- add_q(do.call(rbind, rows))
write_csv(sensitivity_results, file.path(OUT, "aim1_lod_creatinine_sensitivity_survey_results.csv"))

# Diabetes diagnosis / medication exclusion sensitivity.
flag_specs <- c("flag_full", "flag_no_diagnosed_diabetes", "flag_no_diabetes_medication",
                "flag_no_diagnosed_or_medication", "flag_strict_non_diabetes",
                "flag_strict_normoglycemia")
rows <- list(); k <- 1
for (flag in flag_specs[flag_specs %in% names(df)]) {
  dat <- df[df[[flag]] == 1, , drop = FALSE]
  for (out in c("ln_HOMA_IR", "HbA1c", "TyG", "ln_TG_HDL")) {
    log_out <- outcomes$log_outcome[match(out, outcomes$outcome)]
    for (exp in c("pct_oxidative_10", "ln_oxidative_to_MEHP")) {
      rows[[k]] <- run_svy_linear(dat, out, exp, log_out, scenario = flag)
      k <- k + 1
    }
  }
}
diabetes_results <- add_q(do.call(rbind, rows))
write_csv(diabetes_results, file.path(OUT, "aim1_diabetes_medication_exclusion_survey_results.csv"))

# Cycle-specific replication. Use 2-year weights where available.
rows <- list(); k <- 1
for (cy in sort(unique(as.character(df$cycle)))) {
  dat <- df[as.character(df$cycle) == cy, , drop = FALSE]
  weight <- if ("WTSB2YR_MAIN" %in% names(dat)) "WTSB2YR_MAIN" else "WTSB6YR_MAIN"
  for (out in c("msi_core_partial", "ln_HOMA_IR", "HbA1c", "TyG", "ln_TG_HDL")) {
    log_out <- outcomes$log_outcome[match(out, outcomes$outcome)]
    for (exp in c("pct_oxidative_10", "ln_oxidative_to_MEHP")) {
      rows[[k]] <- run_svy_linear(dat, out, exp, log_out,
                                  scenario = paste0("cycle_", cy),
                                  weight = weight,
                                  drop_cycle = TRUE)
      k <- k + 1
    }
  }
}
cycle_results <- add_q(do.call(rbind, rows))
write_csv(cycle_results, file.path(OUT, "aim1_cycle_replication_survey_results.csv"))

# Composition model adjusted for total DEHP.
comp_exposures <- c("ln_oxidative_MEHP_ratio", "ilr_oxidative_vs_primary")
comp_exposures <- comp_exposures[comp_exposures %in% names(df)]
if (length(comp_exposures) == 0 && "ln_oxidative_to_MEHP" %in% names(df)) {
  comp_exposures <- "ln_oxidative_to_MEHP"
}
total_term <- if ("ln_Sigma_DEHP_comp" %in% names(df)) "ln_Sigma_DEHP_comp" else "ln_Sigma_DEHP"
rows <- list(); k <- 1
for (out in c("msi_core_partial", "ln_HOMA_IR", "HbA1c", "TyG", "ln_TG_HDL")) {
  log_out <- outcomes$log_outcome[match(out, outcomes$outcome)]
  for (exp in comp_exposures) {
    rows[[k]] <- run_svy_linear(df, out, exp, log_out,
                                scenario = paste0("composition_adjusted_for_", total_term),
                                extra_terms = total_term)
    k <- k + 1
  }
}
composition_results <- add_q(do.call(rbind, rows))
write_csv(composition_results, file.path(OUT, "aim1_composition_total_adjusted_survey_results.csv"))

# Compact report.
sink(file.path(OUT, "aim1_nhanes_survey_report.md"))
cat("# Nature Food Aim 1 NHANES Survey Report\n\n")
cat("Generated by `scripts/run_nature_food_aim1_nhanes_survey.R`.\n\n")
cat("Input rows:", nrow(df), "\n\n")
cat("Fixed covariates: age, sex, race/ethnicity, education, PIR, energy intake, smoking, alcohol, physical activity, urinary creatinine, cycle.\n\n")
cat("Outputs:\n\n")
cat("- `aim1_main_survey_results.csv`\n")
cat("- `aim1_lod_creatinine_sensitivity_survey_results.csv`\n")
cat("- `aim1_diabetes_medication_exclusion_survey_results.csv`\n")
cat("- `aim1_cycle_replication_survey_results.csv`\n")
cat("- `aim1_composition_total_adjusted_survey_results.csv`\n")
sink()

cat("Done. Outputs written to:", OUT, "\n")
