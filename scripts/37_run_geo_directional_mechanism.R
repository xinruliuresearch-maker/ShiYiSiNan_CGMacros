options(stringsAsFactors = FALSE)

library(GEOquery)
library(Biobase)
library(limma)
library(readr)
library(dplyr)
library(tidyr)
library(tibble)

root <- "C:/Users/liu12/OneDrive/Desktop/ShiYiSiNan_CGMacros"
nhanes_project <- "C:/Users/liu12/OneDrive/Desktop/NHANES_MetS_Project"
today <- as.character(Sys.Date())
out_dir <- file.path(root, "outputs", "integrated_mainline", paste0("evidence_chain_hardening_", today))
mirror_dir <- file.path(nhanes_project, "result", "integrated_mainline", paste0("evidence_chain_hardening_", today))
geo_dir <- file.path(out_dir, "geo_tmp")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(mirror_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(geo_dir, recursive = TRUE, showWarnings = FALSE)

panel_genes <- list(
  insulin_resistance = c("INSR", "IRS1", "IRS2", "PIK3CA", "PIK3R1", "AKT1", "AKT2", "SLC2A4", "GSK3B", "FOXO1", "SOCS3", "JUN"),
  lipid_ppar = c("PPARA", "PPARG", "PPARD", "RXRA", "CPT1A", "ACOX1", "SCD", "FASN", "SREBF1", "CD36", "FABP4", "APOE"),
  oxidative_stress = c("NFE2L2", "KEAP1", "HMOX1", "NQO1", "SOD1", "SOD2", "CAT", "GPX1", "GCLC", "TXNIP"),
  inflammation_tnf = c("TNF", "NFKB1", "RELA", "IL6", "IL1B", "CCL2", "CXCL8", "ICAM1", "VCAM1", "PTGS2"),
  mitochondrial_stress = c("PPARGC1A", "TFAM", "NDUFA1", "UQCRC1", "COX4I1", "ATP5F1A", "MFN2", "DNM1L", "PINK1")
)

message("Running GSE212641 paired MEHP vs DMSO differential expression...")
gse <- getGEO("GSE212641", GSEMatrix = TRUE, getGPL = FALSE)
eset <- gse[[1]]
pd <- pData(eset)

supp <- getGEOSuppFiles("GSE212641", baseDir = geo_dir, fetch_files = TRUE)
counts_file <- file.path(geo_dir, "GSE212641", "GSE212641_RNA-seq_MEHP_raw_readcounts.txt.gz")
if (!file.exists(counts_file)) stop("Missing GSE212641 raw counts file: ", counts_file)

counts <- read.delim(gzfile(counts_file), check.names = FALSE)
gene <- counts[[1]]
mat <- as.matrix(counts[, -1])
mode(mat) <- "numeric"
rownames(mat) <- gene

sample_design <- tibble(
  geo_accession = pd$geo_accession,
  title = pd$title,
  sample_col = colnames(mat),
  treatment = ifelse(grepl("MEHP", pd$title, ignore.case = TRUE), "MEHP", "DMSO"),
  cell_line = sub(",.*$", "", pd$title)
)
write_csv(sample_design, file.path(out_dir, "50_GEO_GSE212641_sample_design.csv"))

colnames(mat) <- sample_design$geo_accession
keep <- rowSums(mat >= 10) >= 3
mat_f <- mat[keep, , drop = FALSE]
gene_symbols_kept <- gene[keep]
rownames(mat_f) <- gene_symbols_kept
libsize <- colSums(mat_f)
log_cpm <- log2(t(t(mat_f + 0.5) / (libsize + 1)) * 1e6)
rownames(log_cpm) <- gene_symbols_kept

design <- model.matrix(~ factor(cell_line) + factor(treatment), data = sample_design)
fit <- lmFit(log_cpm, design)
fit <- eBayes(fit)
coef_name <- grep("treatment.*MEHP", colnames(design), value = TRUE)
if (length(coef_name) != 1) stop("Could not identify MEHP coefficient.")

coef_idx <- match(coef_name, colnames(fit$coefficients))
tt <- tibble(
  gene_symbol = gene_symbols_kept,
  logFC_MEHP_vs_DMSO = fit$coefficients[, coef_idx],
  AveExpr = fit$Amean,
  t = fit$t[, coef_idx],
  pvalue = fit$p.value[, coef_idx],
  padj = p.adjust(fit$p.value[, coef_idx], method = "BH"),
  B = fit$lods[, coef_idx]
) %>%
  arrange(pvalue)
write_csv(tt, file.path(out_dir, "51_GEO_GSE212641_MEHP_vs_DMSO_limma_all.csv"))
write_csv(head(tt, 200), file.path(out_dir, "52_GEO_GSE212641_MEHP_vs_DMSO_top200.csv"))

panel_rows <- list()
idx <- 1
for (panel in names(panel_genes)) {
  genes <- panel_genes[[panel]]
  x <- tt %>% filter(gene_symbol %in% genes)
  panel_rows[[idx]] <- tibble(
    dataset = "GSE212641_hiPSC_endothelial_RNAseq",
    comparison = "MEHP_vs_DMSO_72h_paired_limma_logCPM",
    panel = panel,
    n_panel_genes_available = nrow(x),
    n_fdr_0_05 = sum(x$padj < 0.05, na.rm = TRUE),
    n_up = sum(x$logFC_MEHP_vs_DMSO > 0 & x$padj < 0.05, na.rm = TRUE),
    n_down = sum(x$logFC_MEHP_vs_DMSO < 0 & x$padj < 0.05, na.rm = TRUE),
    median_logFC = median(x$logFC_MEHP_vs_DMSO, na.rm = TRUE),
    leading_genes = paste(head(x$gene_symbol[order(x$padj)], 10), collapse = "|")
  )
  idx <- idx + 1
}
write_csv(bind_rows(panel_rows), file.path(out_dir, "53_GEO_GSE212641_directional_panel_summary.csv"))

message("Parsing GSE293605 supplied MEHP DEG and KEGG files...")
gse293_dir <- file.path(geo_dir, "GSE293605")
dir.create(gse293_dir, recursive = TRUE, showWarnings = FALSE)
deg_url <- "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE293nnn/GSE293605/suppl/GSE293605_MEHPvsDMSO_deg.xls.gz"
kegg_url <- "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE293nnn/GSE293605/suppl/GSE293605_MEHPvsDMSO.all_KEGGenrich.xls.gz"
deg_file <- file.path(gse293_dir, "GSE293605_MEHPvsDMSO_deg.xls.gz")
kegg_file <- file.path(gse293_dir, "GSE293605_MEHPvsDMSO.all_KEGGenrich.xls.gz")
if (!file.exists(deg_file) || file.info(deg_file)$size < 1000) download.file(deg_url, deg_file, mode = "wb", quiet = FALSE)
if (!file.exists(kegg_file) || file.info(kegg_file)$size < 1000) download.file(kegg_url, kegg_file, mode = "wb", quiet = FALSE)

deg293 <- read.delim(gzfile(deg_file), check.names = FALSE)
kegg293 <- read.delim(gzfile(kegg_file), check.names = FALSE)
deg293_top <- deg293 %>%
  arrange(padj) %>%
  select(any_of(c("gene_id", "gene_name", "log2FoldChange", "pvalue", "padj", "gene_biotype", "gene_description", "tf_family"))) %>%
  head(300)
write_csv(deg293_top, file.path(out_dir, "54_GEO_GSE293605_MEHP_vs_DMSO_supplied_DEG_top300.csv"))

relevant_terms <- c("insulin", "glucose", "lipid", "fatty", "PPAR", "AMPK", "oxidative", "TNF", "inflamm", "adipocyt", "metabolic", "mitochond", "peroxisome")
kegg_rel <- kegg293 %>%
  mutate(relevance_hit = grepl(paste(relevant_terms, collapse = "|"), Description, ignore.case = TRUE)) %>%
  filter(relevance_hit | padj < 0.01) %>%
  arrange(padj) %>%
  select(any_of(c("KEGGID", "Description", "GeneRatio", "BgRatio", "pvalue", "padj", "Count", "Up", "Down", "geneName"))) %>%
  head(200)
write_csv(kegg_rel, file.path(out_dir, "55_GEO_GSE293605_MEHP_KEGG_relevant_terms.csv"))

panel293 <- list()
j <- 1
for (panel in names(panel_genes)) {
  genes <- panel_genes[[panel]]
  x <- deg293 %>% filter(gene_name %in% genes)
  panel293[[j]] <- tibble(
    dataset = "GSE293605_human_liver_organoid_supplied_DEG",
    comparison = "MEHP_vs_DMSO_author_supplied",
    panel = panel,
    n_panel_genes_available = nrow(x),
    n_fdr_0_05 = sum(x$padj < 0.05, na.rm = TRUE),
    n_up = sum(x$log2FoldChange > 0 & x$padj < 0.05, na.rm = TRUE),
    n_down = sum(x$log2FoldChange < 0 & x$padj < 0.05, na.rm = TRUE),
    median_logFC = median(x$log2FoldChange, na.rm = TRUE),
    leading_genes = paste(head(x$gene_name[order(x$padj)], 10), collapse = "|")
  )
  j <- j + 1
}

synthesis <- bind_rows(
  read_csv(file.path(out_dir, "53_GEO_GSE212641_directional_panel_summary.csv"), show_col_types = FALSE),
  bind_rows(panel293)
) %>%
  mutate(
    direction_interpretation = case_when(
      n_fdr_0_05 == 0 ~ "panel_detected_but_not_FDR_significant",
      n_up > n_down ~ "mostly_upregulated",
      n_down > n_up ~ "mostly_downregulated",
      TRUE ~ "mixed_direction"
    )
  )
write_csv(synthesis, file.path(out_dir, "56_GEO_directional_mechanism_synthesis.csv"))

report <- c(
  "# GEO方向性机制证据",
  "",
  paste0("生成日期: ", today),
  "",
  "## 已完成",
  "",
  "- `GSE212641`: 下载 raw read counts，构建 3 对 DMSO/MEHP 配对设计，使用 logCPM + limma 运行 MEHP vs DMSO 差异表达。",
  "- `GSE293605`: 下载作者提供的 MEHP vs DMSO DEG 与 KEGG 富集表，提取与 insulin resistance、lipid/PPAR、oxidative stress、TNF/inflammation、mitochondrial stress 相关的方向性证据。",
  "",
  "## 输出文件",
  "",
  "- `51_GEO_GSE212641_MEHP_vs_DMSO_limma_all.csv`",
  "- `52_GEO_GSE212641_MEHP_vs_DMSO_top200.csv`",
  "- `53_GEO_GSE212641_directional_panel_summary.csv`",
  "- `54_GEO_GSE293605_MEHP_vs_DMSO_supplied_DEG_top300.csv`",
  "- `55_GEO_GSE293605_MEHP_KEGG_relevant_terms.csv`",
  "- `56_GEO_directional_mechanism_synthesis.csv`",
  "",
  "## 使用边界",
  "",
  "GSE212641 是 endothelial cell MEHP 暴露，GSE293605 是 human liver organoid MEHP 暴露。二者都不能单独证明 NHANES 暴露-代谢关系的因果性，但能把机制层从数据库重叠推进为可复核的方向性转录组证据。"
)
writeLines(report, file.path(out_dir, "50_GEO_directional_mechanism_report.md"), useBytes = TRUE)

file.copy(list.files(out_dir, full.names = TRUE, recursive = TRUE), mirror_dir, overwrite = TRUE, recursive = TRUE)
message("GEO directional mechanism module completed: ", out_dir)
