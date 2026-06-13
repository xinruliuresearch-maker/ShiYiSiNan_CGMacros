options(stringsAsFactors = FALSE)
options(survey.lonely.psu = "adjust")

library(haven)
library(dplyr)
library(tidyr)
library(readr)
library(tibble)
library(survey)
library(qgcomp)
library(gWQS)
library(bkmr)
library(ggplot2)

root <- "C:/Users/liu12/OneDrive/Desktop/ShiYiSiNan_CGMacros"
nhanes_project <- "C:/Users/liu12/OneDrive/Desktop/NHANES_MetS_Project"
today <- as.character(Sys.Date())
out_dir <- file.path(root, "outputs", "integrated_mainline", paste0("evidence_chain_hardening_", today))
mirror_dir <- file.path(nhanes_project, "result", "integrated_mainline", paste0("evidence_chain_hardening_", today))
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(mirror_dir, recursive = TRUE, showWarnings = FALSE)

high_dir <- file.path(root, "outputs", "integrated_mainline", "high_impact_computational_upgrade_2026-06-11")
master_file <- file.path(nhanes_project, "output", "NHANES_2013_2018_master_analysis.rds")
msi_file <- file.path(high_dir, "01_nhanes_dual_msi_dataset.csv")

normal_p <- function(z) {
  2 * pnorm(abs(z), lower.tail = FALSE)
}

safe_z <- function(x) {
  x <- as.numeric(x)
  s <- sd(x, na.rm = TRUE)
  m <- mean(x, na.rm = TRUE)
  if (!is.finite(s) || s == 0) return(rep(NA_real_, length(x)))
  (x - m) / s
}

weighted_quantile <- function(x, w, probs) {
  ok <- !is.na(x) & !is.na(w) & w > 0
  x <- x[ok]
  w <- w[ok]
  if (length(x) == 0) return(rep(NA_real_, length(probs)))
  ord <- order(x)
  x <- x[ord]
  w <- w[ord] / sum(w[ord])
  cw <- cumsum(w)
  sapply(probs, function(p) x[which(cw >= p)[1]])
}

make_weighted_qscore <- function(x, w, q = 4) {
  out <- rep(NA_integer_, length(x))
  ok <- !is.na(x) & !is.na(w) & w > 0
  if (sum(ok) < 50) return(out)
  breaks <- weighted_quantile(x[ok], w[ok], seq(0, 1, length.out = q + 1))
  breaks[1] <- -Inf
  breaks[length(breaks)] <- Inf
  breaks <- unique(breaks)
  if (length(breaks) < 3) return(out)
  out[ok] <- as.integer(cut(x[ok], breaks = breaks, include.lowest = TRUE, labels = FALSE)) - 1L
  out
}

make_design <- function(d) {
  svydesign(
    ids = ~SDMVPSU,
    strata = ~SDMVSTRA,
    weights = ~WTSB6YR_MAIN,
    nest = TRUE,
    data = d
  )
}

read_pht_cycle <- function(suffix, cycle_label) {
  f <- file.path(nhanes_project, "raw_xpt", paste0("PHTHTE_", suffix, ".xpt"))
  if (!file.exists(f)) stop("Missing PHTHTE file: ", f)
  read_xpt(f) %>%
    mutate(cycle = cycle_label, cycle_suffix = suffix)
}

component_codebook <- tibble::tribble(
  ~raw_variable, ~log_variable, ~component, ~family, ~role,
  "URXMHP", "ln_URXMHP", "MEHP", "DEHP", "primary_parent_monoester",
  "URXMHH", "ln_URXMHH", "MEHHP", "DEHP", "primary_oxidative_metabolite",
  "URXMOH", "ln_URXMOH", "MEOHP", "DEHP", "primary_oxidative_metabolite",
  "URXECP", "ln_URXECP", "MECPP", "DEHP", "primary_oxidative_metabolite",
  "URXMEP", "ln_URXMEP", "MEP", "low_molecular_weight_phthalate", "broader_phthalate_mixture",
  "URXMBP", "ln_URXMBP", "MnBP", "low_molecular_weight_phthalate", "broader_phthalate_mixture",
  "URXMIB", "ln_URXMIB", "MiBP", "low_molecular_weight_phthalate", "broader_phthalate_mixture",
  "URXMZP", "ln_URXMZP", "MBzP", "benzyl_phthalate", "broader_phthalate_mixture",
  "URXCOP", "ln_URXCOP", "MCOP", "high_molecular_weight_phthalate", "broader_phthalate_mixture",
  "URXCNP", "ln_URXCNP", "MCNP", "high_molecular_weight_phthalate", "broader_phthalate_mixture",
  "URXMNP", "ln_URXMNP", "MiNP_or_MNP", "high_molecular_weight_phthalate", "broader_phthalate_mixture",
  "URXMONP", "ln_URXMONP", "MONP", "high_molecular_weight_phthalate", "broader_phthalate_mixture"
)

lod_map <- tibble::tribble(
  ~raw_variable, ~lod_flag_variable,
  "URXMHP", "URDMHPLC",
  "URXMHH", "URDMHHLC",
  "URXMOH", "URDMOHLC",
  "URXECP", "URDECPLC",
  "URXMEP", "URDMEPLC",
  "URXMBP", "URDMBPLC",
  "URXMIB", "URDMIBLC",
  "URXMZP", "URDMZPLC",
  "URXCOP", "URDCOPLC",
  "URXCNP", "URDCNPLC",
  "URXMNP", "URDMNPLC",
  "URXMONP", "URDMONPLC"
)

message("Reading NHANES master and MSI bridge data...")
nh <- readRDS(master_file)
msi <- read_csv(msi_file, show_col_types = FALSE) %>%
  select(
    SEQN,
    exposure_facing_msi,
    response_vulnerability_index,
    msi_core_partial,
    msi_no_bmi
  )

df <- nh %>%
  left_join(msi, by = "SEQN")

for (i in seq_len(nrow(component_codebook))) {
  raw_var <- component_codebook$raw_variable[i]
  log_var <- component_codebook$log_variable[i]
  if (raw_var %in% names(df) && !(log_var %in% names(df))) {
    df[[log_var]] <- ifelse(!is.na(df[[raw_var]]) & df[[raw_var]] > 0, log(df[[raw_var]]), NA_real_)
  }
}

available_components <- component_codebook %>%
  filter(raw_variable %in% names(df), log_variable %in% names(df))

write_csv(available_components, file.path(out_dir, "01_raw_monomer_codebook.csv"))

pht_all <- bind_rows(
  read_pht_cycle("H", "2013-2014"),
  read_pht_cycle("I", "2015-2016"),
  read_pht_cycle("J", "2017-2018")
)

lod_rows <- list()
for (i in seq_len(nrow(available_components))) {
  raw_var <- available_components$raw_variable[i]
  flag_var <- lod_map$lod_flag_variable[match(raw_var, lod_map$raw_variable)]
  if (!is.na(flag_var) && flag_var %in% names(pht_all)) {
    tmp <- pht_all %>%
      group_by(cycle) %>%
      summarise(
        raw_variable = raw_var,
        component = available_components$component[i],
        n_measured = sum(!is.na(.data[[raw_var]])),
        n_below_lod = sum(.data[[flag_var]] == 1, na.rm = TRUE),
        pct_below_lod = 100 * n_below_lod / pmax(n_measured, 1),
        median_value = median(.data[[raw_var]], na.rm = TRUE),
        p95_value = quantile(.data[[raw_var]], 0.95, na.rm = TRUE),
        .groups = "drop"
      )
    lod_rows[[length(lod_rows) + 1]] <- tmp
  }
}
if (length(lod_rows) > 0) {
  write_csv(bind_rows(lod_rows), file.path(out_dir, "02_raw_monomer_lod_summary.csv"))
}

mixture_sets <- list(
  dehp_raw_four_monomers = c("ln_URXMHP", "ln_URXMHH", "ln_URXMOH", "ln_URXECP"),
  dehp_raw_oxidative_three = c("ln_URXMHH", "ln_URXMOH", "ln_URXECP"),
  broad_raw_phthalate_monomers = available_components$log_variable
)
mixture_sets <- lapply(mixture_sets, function(x) intersect(x, available_components$log_variable))
mixture_sets <- mixture_sets[lengths(mixture_sets) >= 3]

outcomes <- c(
  "response_vulnerability_index",
  "exposure_facing_msi",
  "msi_core_partial",
  "msi_no_bmi",
  "ln_HOMA_IR",
  "HbA1c",
  "TyG",
  "ln_TG_HDL"
)
outcomes <- intersect(outcomes, names(df))

base_covars <- c(
  "RIDAGEYR",
  "RIAGENDR",
  "RIDRETH3",
  "DMDEDUC2",
  "INDFMPIR",
  "DR1TKCAL",
  "ever_smoker",
  "alcohol_ever",
  "any_physical_activity",
  "ln_URXUCR",
  "cycle"
)
base_covars <- intersect(base_covars, names(df))
factor_covars <- intersect(c("RIAGENDR", "RIDRETH3", "DMDEDUC2", "cycle"), base_covars)
numeric_covars <- setdiff(base_covars, factor_covars)
covar_terms <- c(numeric_covars, paste0("factor(", factor_covars, ")"))
design_vars <- c("SEQN", "SDMVPSU", "SDMVSTRA", "WTSB6YR_MAIN")

analysis_vars <- unique(c(
  design_vars,
  base_covars,
  outcomes,
  available_components$raw_variable,
  available_components$log_variable
))
analysis_df <- df %>%
  select(any_of(analysis_vars)) %>%
  filter(!is.na(WTSB6YR_MAIN), WTSB6YR_MAIN > 0, !is.na(SDMVPSU), !is.na(SDMVSTRA))

sample_flow <- tibble(
  step = c(
    "NHANES 2013-2018 adult analysis master rows",
    "Rows with valid phthalate subsample design weight",
    "Rows with response_vulnerability_index",
    "Rows with all four DEHP raw monomers",
    "Rows with all four DEHP raw monomers and response_vulnerability_index"
  ),
  n = c(
    nrow(df),
    nrow(analysis_df),
    sum(!is.na(analysis_df$response_vulnerability_index)),
    sum(complete.cases(analysis_df[, c("ln_URXMHP", "ln_URXMHH", "ln_URXMOH", "ln_URXECP")])),
    sum(complete.cases(analysis_df[, c("ln_URXMHP", "ln_URXMHH", "ln_URXMOH", "ln_URXECP", "response_vulnerability_index")]))
  )
)
write_csv(sample_flow, file.path(out_dir, "03_raw_monomer_sample_flow.csv"))
write_csv(analysis_df, file.path(out_dir, "04_raw_monomer_analysis_dataset.csv"))

message("Running survey-weighted single-monomer models...")
single_rows <- list()
k <- 1
for (y in outcomes) {
  for (x in available_components$log_variable) {
    needed <- c(y, x, base_covars, design_vars)
    d <- analysis_df[complete.cases(analysis_df[, needed]), needed]
    if (nrow(d) < 200) next
    d$z_y <- safe_z(d[[y]])
    d$z_x <- safe_z(d[[x]])
    des <- make_design(d)
    f <- as.formula(paste("z_y ~ z_x +", paste(covar_terms, collapse = " + ")))
    fit <- tryCatch(svyglm(f, design = des), error = function(e) e)
    if (inherits(fit, "error")) {
      single_rows[[k]] <- tibble(
        model = "survey_weighted_standardized_single_monomer",
        outcome = y,
        exposure = x,
        component = available_components$component[match(x, available_components$log_variable)],
        n = nrow(d),
        beta = NA_real_,
        se = NA_real_,
        statistic = NA_real_,
        p = NA_real_,
        error = conditionMessage(fit)
      )
    } else {
      co <- coef(summary(fit))["z_x", ]
      single_rows[[k]] <- tibble(
        model = "survey_weighted_standardized_single_monomer",
        outcome = y,
        exposure = x,
        component = available_components$component[match(x, available_components$log_variable)],
        n = nrow(d),
        beta = unname(co[["Estimate"]]),
        se = unname(co[["Std. Error"]]),
        statistic = unname(co[["t value"]]),
        p = unname(co[["Pr(>|t|)"]]),
        error = NA_character_
      )
    }
    k <- k + 1
  }
}
single_res <- bind_rows(single_rows) %>%
  mutate(q = p.adjust(p, method = "BH"))
write_csv(single_res, file.path(out_dir, "05_survey_weighted_single_monomer_glm.csv"))

message("Running survey-weighted qgcomp-like raw monomer mixture models...")
survey_mix_rows <- list()
survey_weight_rows <- list()
m <- 1
w <- 1
for (y in outcomes) {
  for (mix_name in names(mixture_sets)) {
    mix <- mixture_sets[[mix_name]]
    needed <- c(y, mix, base_covars, design_vars)
    d <- analysis_df[complete.cases(analysis_df[, needed]), needed]
    if (nrow(d) < 200) next
    d$z_y <- safe_z(d[[y]])
    q_vars <- paste0("q_", mix)
    for (i in seq_along(mix)) {
      d[[q_vars[i]]] <- make_weighted_qscore(d[[mix[i]]], d$WTSB6YR_MAIN, q = 4)
    }
    d <- d[complete.cases(d[, c("z_y", q_vars, base_covars, design_vars)]), ]
    if (nrow(d) < 200) next
    des <- make_design(d)
    f <- as.formula(paste("z_y ~", paste(c(q_vars, covar_terms), collapse = " + ")))
    fit <- tryCatch(svyglm(f, design = des), error = function(e) e)
    if (inherits(fit, "error")) {
      survey_mix_rows[[m]] <- tibble(
        model = "survey_weighted_qgcomp_like_weighted_quantiles",
        mixture_set = mix_name,
        outcome = y,
        n = nrow(d),
        psi = NA_real_,
        se = NA_real_,
        statistic = NA_real_,
        p = NA_real_,
        error = conditionMessage(fit)
      )
      m <- m + 1
      next
    }
    coefs <- coef(fit)[q_vars]
    vc <- vcov(fit)[q_vars, q_vars, drop = FALSE]
    psi <- sum(coefs)
    psi_se <- sqrt(sum(vc))
    stat <- psi / psi_se
    pval <- 2 * pt(abs(stat), df = fit$df.residual, lower.tail = FALSE)
    survey_mix_rows[[m]] <- tibble(
      model = "survey_weighted_qgcomp_like_weighted_quantiles",
      mixture_set = mix_name,
      components = paste(mix, collapse = "|"),
      outcome = y,
      n = nrow(d),
      psi = psi,
      se = psi_se,
      statistic = stat,
      p = pval,
      error = NA_character_
    )
    comp_beta <- as.numeric(coefs)
    pos_sum <- sum(comp_beta[comp_beta > 0], na.rm = TRUE)
    neg_sum <- abs(sum(comp_beta[comp_beta < 0], na.rm = TRUE))
    for (i in seq_along(q_vars)) {
      b <- comp_beta[i]
      survey_weight_rows[[w]] <- tibble(
        mixture_set = mix_name,
        outcome = y,
        exposure = mix[i],
        component = available_components$component[match(mix[i], available_components$log_variable)],
        beta = b,
        direction = ifelse(b >= 0, "positive", "negative"),
        normalized_weight = ifelse(b >= 0 && pos_sum > 0, b / pos_sum, ifelse(b < 0 && neg_sum > 0, abs(b) / neg_sum, NA_real_))
      )
      w <- w + 1
    }
    m <- m + 1
  }
}
survey_mix_res <- bind_rows(survey_mix_rows) %>%
  mutate(q = p.adjust(p, method = "BH"))
write_csv(survey_mix_res, file.path(out_dir, "06_survey_weighted_raw_monomer_mixture_qgcomp_like.csv"))
write_csv(bind_rows(survey_weight_rows), file.path(out_dir, "07_survey_weighted_qgcomp_like_component_weights.csv"))

message("Running qgcomp.glm.noboot weighted raw monomer sensitivity models...")
qg_rows <- list()
qidx <- 1
for (y in outcomes) {
  for (mix_name in names(mixture_sets)) {
    mix <- mixture_sets[[mix_name]]
    needed <- c(y, mix, base_covars, "WTSB6YR_MAIN")
    d <- analysis_df[complete.cases(analysis_df[, needed]), needed]
    if (nrow(d) < 200) next
    d$z_y <- safe_z(d[[y]])
    qf <- as.formula(paste("z_y ~", paste(c(mix, covar_terms), collapse = " + ")))
    qfit <- tryCatch(
      qgcomp.glm.noboot(qf, data = d, expnms = mix, q = 4, weights = WTSB6YR_MAIN, family = gaussian()),
      error = function(e) e
    )
    if (inherits(qfit, "error")) {
      qg_rows[[qidx]] <- tibble(
        model = "qgcomp_glm_noboot_weighted",
        mixture_set = mix_name,
        components = paste(mix, collapse = "|"),
        outcome = y,
        n = nrow(d),
        psi = NA_real_,
        se = NA_real_,
        statistic = NA_real_,
        p = NA_real_,
        error = conditionMessage(qfit)
      )
    } else {
      qsum <- tryCatch(coef(summary(qfit)), error = function(e) NULL)
      rowname <- if (!is.null(qsum)) rownames(qsum)[grepl("psi", rownames(qsum), ignore.case = TRUE)][1] else NA_character_
      if (!is.na(rowname)) {
        psi <- unname(qsum[rowname, 1])
        se <- unname(qsum[rowname, 2])
        z <- psi / se
        qg_rows[[qidx]] <- tibble(
          model = "qgcomp_glm_noboot_weighted",
          mixture_set = mix_name,
          components = paste(mix, collapse = "|"),
          outcome = y,
          n = nrow(d),
          psi = psi,
          se = se,
          statistic = z,
          p = normal_p(z),
          error = NA_character_
        )
      }
    }
    qidx <- qidx + 1
  }
}
qg_res <- bind_rows(qg_rows) %>%
  mutate(q = p.adjust(p, method = "BH"))
write_csv(qg_res, file.path(out_dir, "08_qgcomp_glm_noboot_weighted_raw_monomer_results.csv"))

message("Running fast gWQS sensitivity models...")
gwqs_outcomes <- intersect(c("response_vulnerability_index", "exposure_facing_msi", "ln_HOMA_IR", "HbA1c"), outcomes)
gwqs_sets <- mixture_sets[names(mixture_sets) %in% c("dehp_raw_four_monomers", "broad_raw_phthalate_monomers")]
gwqs_rows <- list()
gidx <- 1
for (y in gwqs_outcomes) {
  for (mix_name in names(gwqs_sets)) {
    mix <- gwqs_sets[[mix_name]]
    needed <- c(y, mix, base_covars)
    d <- analysis_df[complete.cases(analysis_df[, needed]), needed]
    if (nrow(d) < 200) next
    d$z_y <- safe_z(d[[y]])
    wf <- as.formula(paste("z_y ~ wqs +", paste(covar_terms, collapse = " + ")))
    wfit <- tryCatch(
      gwqs(
        wf,
        data = d,
        mix_name = mix,
        q = 4,
        validation = 0.6,
        b = 20,
        b1_pos = TRUE,
        family = "gaussian",
        seed = 20260611
      ),
      error = function(e) e
    )
    if (inherits(wfit, "error")) {
      gwqs_rows[[gidx]] <- tibble(
        model = "gWQS_positive_20_bootstrap_unweighted_sensitivity",
        mixture_set = mix_name,
        outcome = y,
        n = nrow(d),
        beta = NA_real_,
        se = NA_real_,
        statistic = NA_real_,
        p = NA_real_,
        error = conditionMessage(wfit)
      )
    } else {
      sm <- tryCatch(summary(wfit)$coefficients, error = function(e) NULL)
      if (!is.null(sm) && "wqs" %in% rownames(sm)) {
        gwqs_rows[[gidx]] <- tibble(
          model = "gWQS_positive_20_bootstrap_unweighted_sensitivity",
          mixture_set = mix_name,
          outcome = y,
          n = nrow(d),
          beta = unname(sm["wqs", 1]),
          se = unname(sm["wqs", 2]),
          statistic = unname(sm["wqs", 3]),
          p = unname(sm["wqs", 4]),
          error = NA_character_
        )
      }
      if (!is.null(wfit$final_weights)) {
        write_csv(
          as_tibble(wfit$final_weights),
          file.path(out_dir, paste0("09_gwqs_weights_", mix_name, "_", y, ".csv"))
        )
      }
    }
    gidx <- gidx + 1
  }
}
if (length(gwqs_rows) > 0) {
  write_csv(bind_rows(gwqs_rows) %>% mutate(q = p.adjust(p, method = "BH")), file.path(out_dir, "09_gwqs_positive_raw_monomer_results.csv"))
}

message("Running exploratory BKMR on raw monomer mixtures...")
bkmr_rows <- list()
bkmr_pip_rows <- list()
bidx <- 1
pidx <- 1
bkmr_outcomes <- intersect(c("response_vulnerability_index", "ln_HOMA_IR"), outcomes)
bkmr_mix <- mixture_sets[names(mixture_sets) %in% c("dehp_raw_four_monomers")]
for (y in bkmr_outcomes) {
  for (mix_name in names(bkmr_mix)) {
    mix <- bkmr_mix[[mix_name]]
    needed <- c(y, mix, base_covars, "WTSB6YR_MAIN")
    d <- analysis_df[complete.cases(analysis_df[, needed]), needed]
    if (nrow(d) < 200) next
    set.seed(20260611 + bidx)
    if (nrow(d) > 600) {
      probs <- d$WTSB6YR_MAIN / sum(d$WTSB6YR_MAIN)
      idx <- sample(seq_len(nrow(d)), size = 600, replace = FALSE, prob = probs)
      d <- d[idx, ]
    }
    yvec <- safe_z(d[[y]])
    zmat <- as.matrix(scale(d[, mix]))
    xmat <- model.matrix(as.formula(paste("~", paste(covar_terms, collapse = " + "))), data = d)
    if (ncol(xmat) > 1) xmat <- xmat[, -1, drop = FALSE] else xmat <- NULL
    fit <- tryCatch(
      kmbayes(y = yvec, Z = zmat, X = xmat, iter = 1000, varsel = TRUE, family = "gaussian", verbose = FALSE),
      error = function(e) e
    )
    if (inherits(fit, "error")) {
      bkmr_rows[[bidx]] <- tibble(
        model = "BKMR_weighted_subsample_exploratory_iter1000",
        mixture_set = mix_name,
        outcome = y,
        n = nrow(d),
        status = "failed",
        error = conditionMessage(fit)
      )
    } else {
      bkmr_rows[[bidx]] <- tibble(
        model = "BKMR_weighted_subsample_exploratory_iter1000",
        mixture_set = mix_name,
        outcome = y,
        n = nrow(d),
        status = "completed",
        error = NA_character_
      )
      pip <- tryCatch(ExtractPIPs(fit), error = function(e) NULL)
      if (!is.null(pip)) {
        pip_tbl <- as_tibble(pip)
        pip_tbl$exposure <- mix[seq_len(nrow(pip_tbl))]
        pip_tbl$component <- available_components$component[match(pip_tbl$exposure, available_components$log_variable)]
        pip_tbl$mixture_set <- mix_name
        pip_tbl$outcome <- y
        bkmr_pip_rows[[pidx]] <- pip_tbl
        pidx <- pidx + 1
      }
      saveRDS(fit, file.path(out_dir, paste0("10_bkmr_fit_", mix_name, "_", y, "_iter1000.rds")))
    }
    bidx <- bidx + 1
  }
}
if (length(bkmr_rows) > 0) write_csv(bind_rows(bkmr_rows), file.path(out_dir, "10_bkmr_run_status.csv"))
if (length(bkmr_pip_rows) > 0) write_csv(bind_rows(bkmr_pip_rows), file.path(out_dir, "10_bkmr_pip_summary.csv"))

message("Making summary figures...")
fig_dir <- file.path(out_dir, "figures")
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)

if (nrow(survey_mix_res) > 0) {
  fig_df <- survey_mix_res %>%
    filter(is.na(error), mixture_set %in% c("dehp_raw_four_monomers", "broad_raw_phthalate_monomers")) %>%
    mutate(outcome = factor(outcome, levels = rev(unique(outcome))))
  if (nrow(fig_df) > 0) {
    p <- ggplot(fig_df, aes(x = psi, y = outcome, color = mixture_set)) +
      geom_vline(xintercept = 0, linetype = 2, linewidth = 0.4) +
      geom_point(position = position_dodge(width = 0.5), size = 2) +
      geom_errorbar(aes(xmin = psi - 1.96 * se, xmax = psi + 1.96 * se),
                    position = position_dodge(width = 0.5), width = 0.2) +
      theme_bw(base_size = 10) +
      labs(
        x = "Joint raw-monomer mixture effect per quartile increase (standardized outcome)",
        y = NULL,
        color = "Mixture set",
        title = "NHANES raw monomer mixture: survey-weighted qgcomp-like estimates"
      )
    ggsave(file.path(fig_dir, "raw_monomer_mixture_effects.png"), p, width = 9, height = 5.5, dpi = 300)
    ggsave(file.path(fig_dir, "raw_monomer_mixture_effects.pdf"), p, width = 9, height = 5.5)
  }
}

if (file.exists(file.path(out_dir, "07_survey_weighted_qgcomp_like_component_weights.csv"))) {
  wt_df <- read_csv(file.path(out_dir, "07_survey_weighted_qgcomp_like_component_weights.csv"), show_col_types = FALSE) %>%
    filter(mixture_set == "dehp_raw_four_monomers", outcome %in% c("response_vulnerability_index", "ln_HOMA_IR")) %>%
    mutate(component = factor(component, levels = unique(component)))
  if (nrow(wt_df) > 0) {
    p2 <- ggplot(wt_df, aes(x = component, y = normalized_weight, fill = direction)) +
      geom_col(width = 0.7) +
      facet_wrap(~ outcome) +
      theme_bw(base_size = 10) +
      labs(
        x = NULL,
        y = "Directional normalized component weight",
        fill = "Direction",
        title = "Raw DEHP monomer component weights"
      )
    ggsave(file.path(fig_dir, "raw_dehp_component_weights.png"), p2, width = 7, height = 4, dpi = 300)
    ggsave(file.path(fig_dir, "raw_dehp_component_weights.pdf"), p2, width = 7, height = 4)
  }
}

report_lines <- c(
  "# NHANES原始单体代谢物混合物模型",
  "",
  paste0("生成日期: ", today),
  "",
  "## 目的",
  "",
  "本模块重建 NHANES 2013-2018 的原始邻苯二甲酸酯/DEHP 单体代谢物混合物模型，不再把 `ln_Sigma_DEHP`、`pct_oxidative_10` 或 `ln_oxidative_to_MEHP` 作为主混合物输入。",
  "",
  "## 主混合物",
  "",
  "- DEHP raw four monomers: MEHP, MEHHP, MEOHP, MECPP。",
  "- DEHP oxidative three: MEHHP, MEOHP, MECPP。",
  "- Broad raw phthalate monomers: 所有当前周期可用的原始单体。",
  "",
  "## 已输出",
  "",
  "- `01_raw_monomer_codebook.csv`: 原始单体变量说明。",
  "- `02_raw_monomer_lod_summary.csv`: LOD 标记与周期分布。",
  "- `03_raw_monomer_sample_flow.csv`: 样本流。",
  "- `04_raw_monomer_analysis_dataset.csv`: 复核分析数据集。",
  "- `05_survey_weighted_single_monomer_glm.csv`: survey-weighted 单体模型。",
  "- `06_survey_weighted_raw_monomer_mixture_qgcomp_like.csv`: 复杂抽样加权 qgcomp-like 主结果。",
  "- `07_survey_weighted_qgcomp_like_component_weights.csv`: 单体方向性权重。",
  "- `08_qgcomp_glm_noboot_weighted_raw_monomer_results.csv`: qgcomp 包敏感性结果。",
  "- `09_gwqs_positive_raw_monomer_results.csv`: gWQS 快速敏感性结果。",
  "- `10_bkmr_run_status.csv` 和 `10_bkmr_pip_summary.csv`: BKMR 探索运行状态与 PIP。",
  "",
  "## 解释原则",
  "",
  "主文应优先报告复杂抽样加权 qgcomp-like 结果；qgcomp/gWQS/BKMR 作为方法学三角验证。若 qgcomp 包结果与 survey-qgcomp-like 结果方向一致，说明信号不依赖派生比例指标。"
)
writeLines(report_lines, file.path(out_dir, "00_raw_nhanes_monomer_mixture_report.md"), useBytes = TRUE)

manifest <- tibble(
  generated = Sys.time(),
  out_dir = out_dir,
  mirror_dir = mirror_dir,
  master_file = master_file,
  msi_file = msi_file,
  n_analysis = nrow(analysis_df),
  n_components = nrow(available_components)
)
write_csv(manifest, file.path(out_dir, "00_raw_nhanes_monomer_mixture_manifest.csv"))

file.copy(list.files(out_dir, full.names = TRUE, recursive = TRUE), mirror_dir, overwrite = TRUE, recursive = TRUE)
message("Raw NHANES monomer mixture module completed: ", out_dir)
