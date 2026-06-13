from __future__ import annotations

import csv
import json
import shutil
from datetime import date, datetime
from pathlib import Path

import pandas as pd


TODAY = date.today().isoformat()
ROOT = Path(r"C:\Users\liu12\OneDrive\Desktop\ShiYiSiNan_CGMacros")
OUT = ROOT / "outputs" / "integrated_mainline" / f"next_level_evidence_strategy_{TODAY}"
MIRROR = (
    Path(r"C:\Users\liu12\OneDrive\Desktop\NHANES_MetS_Project")
    / "result"
    / "integrated_mainline"
    / f"next_level_evidence_strategy_{TODAY}"
)
FORMAL = ROOT / "outputs" / "integrated_mainline" / f"formal_drylab_strengthening_{TODAY}"
HIGH = ROOT / "outputs" / "integrated_mainline" / "high_impact_computational_upgrade_2026-06-11"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\n", "\r\n"), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def current_findings() -> dict[str, str]:
    qg = read_csv_safe(FORMAL / "02_R_qgcomp_weighted_results.csv")
    survey = read_csv_safe(FORMAL / "01_R_survey_weighted_standardized_glm.csv")
    perf = read_csv_safe(FORMAL / "11_cgmacros_non_glycemic_subject_disjoint_performance.csv")
    hier = read_csv_safe(FORMAL / "12_cgmacros_non_glycemic_cluster_hierarchical_coefficients.csv")
    fdc = read_csv_safe(FORMAL / "21_fdc_item_level_proxy_match_summary.csv")
    d1 = read_csv_safe(FORMAL / "30_d1namo_external_validation_performance.csv")
    jaeb = read_csv_safe(FORMAL / "31_jaeb_day_level_external_validation_correlations.csv")
    food = read_csv_safe(FORMAL / "20_food_matrix_dual_rater_prelabeled_reliability.csv")

    out: dict[str, str] = {}
    if len(qg):
        ok = qg[qg["error"].isna()].copy()
        if len(ok):
            ok["p"] = pd.to_numeric(ok["p"], errors="coerce")
            top = ok.sort_values("p").head(3)
            out["qgcomp_top"] = "; ".join(
                f"{r.outcome}/{r.mixture_set}: psi={float(r.psi):.3f}, p={float(r.p):.2g}, q={float(r.q):.2g}"
                for r in top.itertuples()
            )
        alias_n = int(qg["error"].notna().sum())
        out["qgcomp_aliasing"] = f"{alias_n}/{len(qg)} qgcomp rows failed or were skipped because derived exposure metrics are collinear/aliased."
    if len(survey):
        survey["p"] = pd.to_numeric(survey["p"], errors="coerce")
        top = survey.sort_values("p").head(3)
        out["survey_top"] = "; ".join(
            f"{r.outcome}/{r.exposure}: beta={float(r.beta):.3f}, p={float(r.p):.2g}, q={float(r.q):.2g}"
            for r in top.itertuples()
        )
    if len(perf):
        out["nonglycemic_prediction"] = "; ".join(
            f"{r.outcome} {r.model}: R2={float(r.r2_subject_disjoint):.3f}, r={float(r.pearson_r):.3f}"
            for r in perf.itertuples()
            if r.model == "non_glycemic_msi_foodmatrix"
        )
    if len(hier):
        rapid = hier[hier["term"].eq("rapid_digestibility_score_v2")]
        out["rapid_digestibility"] = "; ".join(
            f"{r.outcome}: beta={float(r.beta_per_1sd_predictor):.3f}, p={float(r.p):.3g}, q={float(r.q):.3g}"
            for r in rapid.itertuples()
        )
    if len(food):
        r = food.iloc[0]
        out["food_dual_prelabel"] = f"kappa={float(r['cohen_kappa']):.3f}, agreement={float(r['agreement_rate']):.3f}, manual_review={int(r['needs_manual_review_n'])}"
    if len(fdc):
        r = fdc.iloc[0]
        out["fdc"] = f"assigned={int(r['n_assigned_fdc_id'])}/{int(r['n_meals'])}, manual_review={int(r['requires_manual_review_n'])}; DEMO_KEY/API limit caused 429 in latest run."
    if len(d1):
        out["d1namo"] = "; ".join(
            f"{r.outcome}: R2={float(r.r2):.3f}, r={float(r.pearson_r):.3f}, n={int(r.n_meals)}"
            for r in d1.itertuples()
        )
    if len(jaeb):
        jaeb["pearson_r_abs"] = pd.to_numeric(jaeb["pearson_r"], errors="coerce").abs()
        top = jaeb.sort_values("pearson_r_abs", ascending=False).head(2)
        out["jaeb"] = "; ".join(
            f"{r.predictor}->{r.outcome}: r={float(r.pearson_r):.3f}, n={int(r.n_subjects)}"
            for r in top.itertuples()
        )
    return out


def literature_update() -> list[dict]:
    return [
        {
            "topic": "PPGR benchmark",
            "source": "Nature Medicine 2025, standardized carbohydrate meal PPGR study",
            "url": "https://www.nature.com/articles/s41591-025-03719-2",
            "key_message": "Equivalent carbohydrate meals produce different PPGRs; individual carb-response types, mitigator effects, metabolic tests, microbiome, metabolomics and proteomics create a high-level benchmark.",
            "implication": "Our next validation should use standardized repeated meals and molecular/metabolic phenotyping, not only free-living meal prediction.",
        },
        {
            "topic": "Personalized PPGR",
            "source": "Zeevi et al., Cell 2015",
            "url": "https://www.cell.com/fulltext/S0092-8674(15)01481-6",
            "key_message": "Week-long CGM, real meals, clinical variables and microbiome predicted individualized glycemic responses and supported personalized diet intervention.",
            "implication": "Our CGMacros result needs strong subject-disjoint validation and should be positioned as bridge phenotype, not a full personalized-diet algorithm.",
        },
        {
            "topic": "Precision nutrition",
            "source": "PREDICT 1, Nature Medicine 2020",
            "url": "https://pubmed.ncbi.nlm.nih.gov/32528151/",
            "key_message": "Large-scale standardized and free-living postprandial responses showed major interindividual variability and external validation.",
            "implication": "A high-level paper needs either a PREDICT-like standardized test component or a very strong cross-dataset validation story.",
        },
        {
            "topic": "Public CGM dataset",
            "source": "CGMacros PhysioNet 2025",
            "url": "https://physionet.org/content/cgmacros/",
            "key_message": "CGMacros provides CGM, food macronutrients, food photographs, activity, blood panels and microbiome-related features.",
            "implication": "It is useful but modest in participant number; subject-disjoint validation and food image annotation are essential.",
        },
        {
            "topic": "Stanford CGMDB",
            "source": "Stanford Continuous Glucose Monitoring Database",
            "url": "https://cgmdb.stanford.edu/data/",
            "key_message": "Provides CGM, lipid, metadata, metabolomics and Olink data.",
            "implication": "Use Stanford molecular layers to create a stronger metabolic susceptibility validation, not only a CGM boundary test.",
        },
        {
            "topic": "Phthalate/MetS evidence",
            "source": "Recent review: Impact of DEHP on metabolic syndrome",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12255270/",
            "key_message": "DEHP can interfere with lipid metabolism and insulin signaling; mechanisms include endocrine disruption and metabolic pathways.",
            "implication": "Mechanism discussion should converge on insulin signaling, lipid metabolism, PPAR/AMPK and inflammatory/oxidative stress.",
        },
        {
            "topic": "Environmental mixture methods",
            "source": "qgcomp, WQS and BKMR mixture-method literature",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7228100/ ; https://academic.oup.com/biostatistics/article/16/3/493/269719 ; https://pubmed.ncbi.nlm.nih.gov/30505142/",
            "key_message": "Modern environmental epidemiology estimates joint mixture effects and component weights/nonlinearities, but interpretability depends on using real exposure components rather than mathematically nested derived ratios.",
            "implication": "The main NHANES model should use raw urinary phthalate/plasticizer metabolites; derived DEHP burden and oxidative ratios should be secondary mechanistic features.",
        },
        {
            "topic": "Phthalate metabolites",
            "source": "NHANES PHTHTE 2013-2014 documentation",
            "url": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2013/DataFiles/PHTHTE_H.htm",
            "key_message": "Provides raw phthalate/plasticizer metabolite variables including MECPP, MEHHP, MEHP, MEOHP and LOD flags.",
            "implication": "Rebuild exposure mixture from raw monomer metabolites; derived total/ratio metrics should not be the primary mixture inputs.",
        },
        {
            "topic": "CGM outcome design",
            "source": "Modern PPGR/CGM studies with repeated standardized challenges and rich molecular phenotyping",
            "url": "https://www.nature.com/articles/s41591-025-03719-2 ; https://pubmed.ncbi.nlm.nih.gov/32528151/",
            "key_message": "High-impact PPGR studies increasingly emphasize repeated standardized meals, reproducible individual response types, and molecular/clinical layers rather than a single scalar outcome.",
            "implication": "Model full postprandial curves and response types where raw CGM traces are available; keep iAUC/peak as interpretable primary endpoints but add curve-shape robustness.",
        },
        {
            "topic": "Food matrix/digestion",
            "source": "INFOGEST 2.0",
            "url": "https://pubmed.ncbi.nlm.nih.gov/30886367/",
            "key_message": "Consensus digestion protocol for standardized in vitro digestion.",
            "implication": "Optional wet validation should test 8-12 manually annotated meals for glucose release kinetics.",
        },
        {
            "topic": "FDC data infrastructure",
            "source": "USDA FoodData Central API Guide",
            "url": "https://fdc.nal.usda.gov/api-guide",
            "key_message": "FDC search/detail endpoints are available; DEMO_KEY has low limits and 429 means rate limit exceeded.",
            "implication": "Apply for a real API key or use offline FDC downloads; current DEMO_KEY result is not publishable.",
        },
        {
            "topic": "Prediction reporting",
            "source": "TRIPOD+AI 2024",
            "url": "https://www.tripod-statement.org/",
            "key_message": "TRIPOD+AI is a 27-item checklist for transparent prediction model reporting.",
            "implication": "Every CGMacros/Stanford model must report objectives, splits, missingness, predictors, calibration, uncertainty and code availability.",
        },
        {
            "topic": "Prediction bias assessment",
            "source": "PROBAST+AI 2025",
            "url": "https://www.bmj.com/content/388/bmj-2024-082505",
            "key_message": "Updated tool evaluates risk of bias and applicability for regression and AI prediction models.",
            "implication": "The manuscript must proactively handle data leakage, sample size, participants/data source applicability and analysis domains.",
        },
        {
            "topic": "Mechanism databases",
            "source": "EPA CompTox Dashboard and NCBI GEO",
            "url": "https://www.epa.gov/comptox-tools/comptox-chemicals-dashboard ; https://www.ncbi.nlm.nih.gov/geo/info/overview.html",
            "key_message": "CompTox integrates chemical toxicity/exposure/bioassay data; GEO archives high-throughput functional genomics data.",
            "implication": "Mechanism layer should become assay/omics-supported, not only CTD pathway overlap.",
        },
    ]


def evidence_audit(findings: dict[str, str]) -> list[dict]:
    return [
        {
            "evidence_layer": "NHANES exposure-metabolic anchor",
            "current_result": f"Survey: {findings.get('survey_top', 'NA')}; qgcomp: {findings.get('qgcomp_top', 'NA')}",
            "strength": "Moderate-to-strong association evidence",
            "critical_weakness": findings.get("qgcomp_aliasing", "Derived metrics cause mixture interpretability concerns."),
            "journal_risk": "A reviewer will argue this is not a true chemical mixture because inputs are derived and mathematically dependent.",
            "next_fix": "Rebuild raw metabolite mixture using MEHP, MEHHP, MEOHP, MECPP and other phthalate monomers with LOD flags and cycle-specific weights.",
        },
        {
            "evidence_layer": "Bridge phenotype/MSI",
            "current_result": findings.get("nonglycemic_prediction", "NA"),
            "strength": "Primary RVI works; conservative non-glycemic sensitivity is weaker.",
            "critical_weakness": "Non-glycemic MSI alone gives positive correlations but negative subject-disjoint R2 in CGMacros.",
            "journal_risk": "If RVI is too close to glycemic outcomes, reviewers may claim circularity; if non-glycemic MSI is primary, predictive signal is too weak.",
            "next_fix": "Use RVI as primary bridge phenotype, non-glycemic MSI as sensitivity, and add leave-one-domain-out constructs.",
        },
        {
            "evidence_layer": "Food matrix",
            "current_result": f"{findings.get('food_dual_prelabel', 'NA')}; FDC: {findings.get('fdc', 'NA')}",
            "strength": "Conceptually important but not yet publication-grade.",
            "critical_weakness": "Automated dual prelabels have only moderate agreement and FDC matching failed under DEMO_KEY rate limits.",
            "journal_risk": "Food matrix may be seen as subjective/proxy if not manually adjudicated and database-linked.",
            "next_fix": "Complete blinded human dual annotation and FDC offline/API-key item matching before main submission.",
        },
        {
            "evidence_layer": "External CGM validation",
            "current_result": f"D1NAMO: {findings.get('d1namo', 'NA')}; Jaeb: {findings.get('jaeb', 'NA')}",
            "strength": "Boundary information rather than replication.",
            "critical_weakness": "D1NAMO T1D meal-level validation is negative/unstable; Jaeb lacks meal events.",
            "journal_risk": "External validation claim will be overread unless carefully labelled as boundary/transportability testing.",
            "next_fix": "Promote Stanford CGMDB molecular/standardized challenge validation; demote D1NAMO/Jaeb to supplement.",
        },
        {
            "evidence_layer": "Mechanism",
            "current_result": "CTD/KEGG/Reactome converge on PPAR, AMPK, PI3K-Akt, insulin resistance, TNF/inflammation, oxidative stress and lipid metabolism; GEO candidates and CompTox query manifest exist.",
            "strength": "Mechanistic plausibility is coherent.",
            "critical_weakness": "Still not directional assay/omics evidence.",
            "journal_risk": "Pathway overlap alone is weak for high-level mechanism claims.",
            "next_fix": "Screen GEO candidates, rerun differential expression, extract ToxCast assay endpoints, and show direction-concordant pathway evidence.",
        },
    ]


def redesigned_chain() -> list[dict]:
    return [
        {
            "claim_level": "Claim 1: Exposure-metabolic anchor",
            "publishable_claim": "Raw urinary DEHP/phthalate metabolite mixtures are associated with metabolic susceptibility and insulin-resistance markers in NHANES.",
            "required_evidence": "Raw monomer mixture qgcomp/gWQS/BKMR; survey weights; LOD handling; urinary dilution; negative controls; quantitative bias analysis.",
            "status": "Partially complete; needs raw monomer rebuild.",
        },
        {
            "claim_level": "Claim 2: Bridge phenotype",
            "publishable_claim": "Metabolic susceptibility is a cross-dataset bridge phenotype linking exposure epidemiology to dynamic PPGR vulnerability.",
            "required_evidence": "RVI primary, non-glycemic sensitivity, leave-one-domain-out, construct validity in NHANES/CGMacros/Stanford.",
            "status": "Promising but needs Stanford molecular validation.",
        },
        {
            "claim_level": "Claim 3: Food-matrix-dependent PPGR",
            "publishable_claim": "Food matrix and rapid digestibility modify PPGR vulnerability, especially in susceptible metabolic phenotypes.",
            "required_evidence": "Manual food annotation, FDC item matching, subject-disjoint/clustered CGMacros inference, Stanford standardized meal comparison.",
            "status": "Core signal exists; food annotation and FDC need repair.",
        },
        {
            "claim_level": "Claim 4: Mechanistic plausibility",
            "publishable_claim": "DEHP/MEHP-related toxicogenomic and bioassay evidence converges on insulin/lipid/inflammatory/oxidative stress pathways.",
            "required_evidence": "CTD + CompTox/ToxCast + GEO differential expression + KEGG/Reactome concordance.",
            "status": "Database layer complete; directional omics still pending.",
        },
        {
            "claim_level": "Claim 5: High-tier causal bridge",
            "publishable_claim": "Same-participant urinary DEHP profiles stratify standardized meal PPGR and mitigation response.",
            "required_evidence": "New pilot with repeated urine, CGM, standardized meals, baseline labs, optional stool/multiomics.",
            "status": "Not yet available; required for top-tier aspirations.",
        },
    ]


def drylab_actions() -> list[dict]:
    return [
        {
            "priority": 1,
            "module": "Raw NHANES phthalate monomer mixture",
            "actions": "Download/merge NHANES PHTHTE files by cycle; construct MEHP, MEHHP, MEOHP, MECPP, MBzP, MEP, MBP, MiBP, MCPP etc.; use LOD flags and creatinine/specific gravity sensitivity; run survey qgcomp/gWQS/BKMR.",
            "why_decisive": "Fixes the current qgcomp aliasing and converts the exposure layer into a true chemical-mixture analysis.",
            "deliverables": "raw_monomer_dataset.csv; R scripts; mixture weights; BKMR PIPs; monomer-specific heatmaps.",
            "time": "3-7 days",
        },
        {
            "priority": 2,
            "module": "Food matrix human annotation and FDC repair",
            "actions": "Use manual_dual_annotation_template; two blinded raters plus adjudicator; apply for FDC key or use offline FDC downloads; link each meal to FDC candidate and confidence.",
            "why_decisive": "Moves food matrix from proxy to auditable nutrition phenotype.",
            "deliverables": "human_annotation_v1.csv; adjudicated_food_matrix.csv; fdc_item_matches_final.csv; kappa/ICC report.",
            "time": "1-2 weeks",
        },
        {
            "priority": 3,
            "module": "Stanford CGMDB molecular validation",
            "actions": "Use Stanford CGM, lipid, metadata, metabolomics and Olink files; derive PPGR subtypes and metabolic/inflammatory molecular signatures; test whether RVI-like signatures explain meal-specific spikes and mitigator response.",
            "why_decisive": "Upgrades external validation from modest boundary test to molecularly anchored PPGR validation.",
            "deliverables": "stanford_molecular_validation.csv; subtype figures; molecular pathway enrichment.",
            "time": "1-2 weeks",
        },
        {
            "priority": 4,
            "module": "GEO/CompTox directional mechanism",
            "actions": "Screen GEO candidate list; select true DEHP/MEHP exposure datasets; rerun differential expression; map genes to CTD/KEGG/Reactome; extract CompTox/ToxCast assay endpoints with key/offline files.",
            "why_decisive": "Turns mechanism from overlap plausibility into direction-concordant toxicogenomic evidence.",
            "deliverables": "geo_screening_table.csv; DEG tables; assay_endpoint_table.csv; mechanism concordance network.",
            "time": "1-3 weeks",
        },
        {
            "priority": 5,
            "module": "Functional PPGR modeling",
            "actions": "Move beyond scalar iAUC/peak; model full 0-180 min curve where available using functional features, recovery slope, and clustered curve types.",
            "why_decisive": "Aligns with modern PPGR literature emphasizing dynamic curve shape and reproducible response types.",
            "deliverables": "curve_feature_matrix.csv; response_type_clusters.csv; functional model supplement.",
            "time": "1 week",
        },
    ]


def pilot_protocol() -> list[dict]:
    return [
        {
            "section": "Objective",
            "design": "Same-participant CGM-exposome bridge pilot",
            "details": "Test whether urinary DEHP/phthalate metabolite profiles and metabolic susceptibility predict standardized meal PPGR and mitigator response.",
        },
        {
            "section": "Participants",
            "design": "N=60 feasibility or N=120 definitive bridge",
            "details": "Adults without insulin-treated diabetes; enrich across BMI/insulin-resistance strata; balance sex and major ancestry groups where feasible.",
        },
        {
            "section": "Exposure",
            "design": "Repeated urine biomarkers",
            "details": "Two or three first-morning urine samples; MEHP, MEHHP, MEOHP, MECPP, MEP, MBP, MiBP, MBzP; creatinine/specific gravity; calculate molar SigmaDEHP and oxidative fractions.",
        },
        {
            "section": "PPGR",
            "design": "10-14 day CGM with standardized meal challenges",
            "details": "Replicated rice/bread/potato/beans/pasta or local equivalents; include mitigator arms such as rice plus fiber/protein/fat; water-only washout and 3-hour spacing.",
        },
        {
            "section": "Baseline phenotype",
            "design": "Metabolic susceptibility panel",
            "details": "BMI, waist, fasting glucose, insulin, HbA1c, lipids, CRP/IL-6 if possible; optional stool microbiome and metabolomics if budget allows.",
        },
        {
            "section": "Primary analysis",
            "design": "Hierarchical target-trial-like meal model",
            "details": "Outcome: iAUC/peak/full curve; predictors: urinary raw metabolite mixture, RVI, meal type, mitigator, interactions; random participant intercept and meal replicate effects.",
        },
        {
            "section": "Decision criterion",
            "design": "Go/no-go",
            "details": "If exposure mixture or RVI modifies standardized meal PPGR/mitigator response in expected direction, paper can credibly target Nature Food/Cell Metabolism style venues.",
        },
    ]


def manuscript_claim_ladder() -> list[dict]:
    return [
        {
            "old_claim": "DEHP directly causes abnormal PPGR.",
            "new_claim": "Avoid. Current cross-dataset evidence cannot support direct DEHP-to-PPGR causality.",
            "where_in_paper": "Do not use in title, abstract or conclusion.",
        },
        {
            "old_claim": "DEHP-related mixture is associated with metabolic susceptibility.",
            "new_claim": "Supportable after raw monomer mixture rebuild; current derived metrics are supportive but not final.",
            "where_in_paper": "Results 1 and Figure 2.",
        },
        {
            "old_claim": "MSI predicts PPGR.",
            "new_claim": "Response-vulnerability MSI predicts PPGR; non-glycemic MSI is a conservative sensitivity with weaker performance.",
            "where_in_paper": "Results 2-3 and Supplement.",
        },
        {
            "old_claim": "External validation confirms the model.",
            "new_claim": "Stanford provides boundary/molecular validation; D1NAMO and Jaeb define transportability limits.",
            "where_in_paper": "Results 4 and Discussion limitations.",
        },
        {
            "old_claim": "Mechanism network proves biological mechanism.",
            "new_claim": "CTD/CompTox/GEO/Reactome/KEGG provide biological plausibility and direction-concordant toxicogenomic support.",
            "where_in_paper": "Results 5 and Discussion.",
        },
    ]


def reviewer_matrix() -> list[dict]:
    return [
        {
            "reviewer_attack": "Your mixture variables are derived from each other and cannot be interpreted as a true environmental mixture.",
            "answer": "Rebuild raw monomer metabolite mixture and move derived indices to secondary metabolic-transformation analyses.",
            "status": "Must fix before high-impact submission.",
        },
        {
            "reviewer_attack": "The PPGR model may be circular because RVI contains glycemic biomarkers.",
            "answer": "Keep RVI primary as a susceptibility phenotype, show non-glycemic and leave-one-domain-out sensitivity, and avoid calling it independent causal prediction.",
            "status": "Partly fixed; needs better framing.",
        },
        {
            "reviewer_attack": "Food matrix annotation is subjective.",
            "answer": "Use blinded dual human annotation, adjudication, kappa/ICC, FDC item matches, and optional in vitro digestion validation.",
            "status": "Not yet fixed.",
        },
        {
            "reviewer_attack": "External validation is weak or contradictory.",
            "answer": "Label D1NAMO/Jaeb as boundary tests; emphasize Stanford standardized/molecular validation; do not overclaim replication.",
            "status": "Needs manuscript reframing.",
        },
        {
            "reviewer_attack": "Mechanism is just database overlap.",
            "answer": "Add GEO differential expression and ToxCast assay endpoints; require direction concordance with CTD/Reactome/KEGG.",
            "status": "Pending.",
        },
        {
            "reviewer_attack": "The study is too broad and stitched together.",
            "answer": "Narrow to one sentence: phthalate-related metabolic susceptibility shapes food-matrix-dependent PPGR vulnerability.",
            "status": "Ready to implement in manuscript.",
        },
    ]


def journal_path() -> list[dict]:
    return [
        {
            "target_level": "AJCN / Clinical Nutrition / Environment International / EHP",
            "minimum_package": "Raw monomer NHANES mixture; subject-disjoint CGMacros RVI model; manual food annotation; Stanford molecular validation; CTD+GEO+CompTox mechanism.",
            "probability_after_minimum": "Moderate if claims are restrained.",
        },
        {
            "target_level": "Nature Food / Cell Metabolism / Nature Medicine style",
            "minimum_package": "All above plus same-participant CGM-exposome pilot with standardized meal replicates and mitigator response.",
            "probability_after_minimum": "Still competitive, but scientifically plausible.",
        },
        {
            "target_level": "Current package without further fixes",
            "minimum_package": "Present derived-metric NHANES + CGMacros + proxy food matrix + boundary validation.",
            "probability_after_minimum": "Useful for a computational/interdisciplinary manuscript, but not enough for top-tier claims.",
        },
    ]


def database_fix_plan() -> list[dict]:
    return [
        {
            "database": "NHANES",
            "current_issue": "Current exposure mixture uses derived metrics and not raw monomers.",
            "fix": "Download PHTHTE files by cycle; use URXMHP/MEHP, URXMHH/MEHHP, URXMOH/MEOHP, URXECP/MECPP and other phthalate variables; preserve LOD flags and weights.",
            "publishability_gain": "High",
        },
        {
            "database": "FoodData Central",
            "current_issue": "DEMO_KEY returned 429 and final match table assigned 0/1498 meals.",
            "fix": "Use personal data.gov API key or offline FDC downloads; cache query results; include FDC ID, food description, data type, match score and reviewer decision.",
            "publishability_gain": "High",
        },
        {
            "database": "Stanford CGMDB",
            "current_issue": "Only boundary CGM validation used; metabolomics/Olink underused.",
            "fix": "Build molecular metabolic susceptibility signatures and test standardized meal/subtype associations.",
            "publishability_gain": "High",
        },
        {
            "database": "GEO",
            "current_issue": "Candidate search complete but no differential expression rerun.",
            "fix": "Screen GSE records for true DEHP/MEHP exposure; rerun DESeq2/limma; map DEGs to CTD/KEGG/Reactome.",
            "publishability_gain": "Medium-high",
        },
        {
            "database": "CompTox/ToxCast",
            "current_issue": "Query manifest exists but assay endpoints not extracted.",
            "fix": "Obtain API key or invitroDB flat files; extract PPAR/nuclear receptor, oxidative stress, mitochondrial, inflammatory and endocrine assay results.",
            "publishability_gain": "Medium-high",
        },
    ]


def report(findings: dict[str, str]) -> str:
    return f"""# 下一轮高水平证据链优化方案

生成日期: {TODAY}

## 总体判断

你对研究水平的担心是对的。最新一轮干实验不是失败，但它把真正的短板暴露得更清楚了:

1. **NHANES暴露层需要回到原始单体代谢物。** 现在的 `ln_Sigma_DEHP`、`pct_oxidative_10`、`ln_oxidative_to_MEHP` 是派生指标，正式qgcomp提示共线/aliasing。高水平期刊会要求MEHP、MEHHP、MEOHP、MECPP等原始单体进入混合物模型。
2. **non-glycemic MSI不能替代主RVI。** 它与主MSI高度相关，但在CGMacros subject-disjoint预测中R2为负，只能作为反循环论证的保守敏感性分析。
3. **食物基质还没有达到发表级。** 规则双预标注kappa只有中等，且FDC DEMO_KEY限流导致最终匹配0/1498。必须做人工双评和正式FDC匹配。
4. **外部验证要重新分层。** Stanford仍是最有价值的外部数据；D1NAMO是T1D胰岛素边界测试且方向不稳，Jaeb没有餐食事件，只能说明CGM波动边界。
5. **机制层必须从数据库重叠升级为方向性证据。** 需要CompTox/ToxCast assay endpoints和GEO差异表达。

## 当前最能支撑的主线

**Raw phthalate/DEHP metabolite mixture -> metabolic susceptibility -> food-matrix-dependent PPGR vulnerability.**

中文表述为:

**邻苯二甲酸酯/DEHP原始代谢物混合暴露与代谢易感性相关，而代谢易感性可能塑造个体面对不同食物基质时的餐后血糖反应脆弱性。**

这条主线比“DEHP直接导致PPGR异常”更窄，但更能防守。

## 本轮结果带来的重新定位

- NHANES仍是强人群锚点: {findings.get("survey_top", "NA")}
- R qgcomp可识别派生组合仍有强信号: {findings.get("qgcomp_top", "NA")}
- 但qgcomp共线问题必须处理: {findings.get("qgcomp_aliasing", "NA")}
- non-glycemic MSI用于敏感性，而非主模型: {findings.get("nonglycemic_prediction", "NA")}
- 食物快速消化性仍有独立价值: {findings.get("rapid_digestibility", "NA")}
- 食物/FDC层目前不能过度声称: {findings.get("food_dual_prelabel", "NA")}; {findings.get("fdc", "NA")}

## 下一步优先级

### Priority 1: 重建NHANES原始单体暴露混合物

这是最值得马上做的干实验。不要再把派生比例当主混合物。应下载各周期PHTHTE原始文件，保留MEHP、MEHHP、MEOHP、MECPP、MEP、MBP、MiBP、MBzP、MCPP等变量、LOD标记、尿肌酐和复杂抽样权重。主模型用survey-weighted qgcomp/gWQS/BKMR，派生指标只作为“DEHP代谢转化/氧化比例”的二级分析。

### Priority 2: Stanford分子层外部验证

Stanford CGMDB有CGM、metadata、lipid、metabolomics、Olink。下一步应构建PPGR response type、mitigator response、炎症/脂质/胰岛素相关分子签名，而不是只做一个R2边界验证。这样才能接近2025年Nature Medicine标准化餐食多组学PPGR研究的证据形态。

### Priority 3: 食物基质从proxy升级到人工审定

当前规则双评只能做预标注。需要两名人工独立评估餐食图像/描述，再由第三方裁决；FDC必须使用正式API key或离线数据库，保留FDC ID、候选项、匹配分、人工确认。否则食物基质创新点会被审稿人打穿。

### Priority 4: GEO/CompTox方向性机制

已有CTD/KEGG/Reactome说明机制“合理”，但还不够。应筛出真正DEHP/MEHP暴露的GEO数据，跑差异表达，再与PPAR、AMPK、PI3K-Akt、insulin signaling、TNF/炎症、oxidative stress、lipid metabolism做方向一致性验证。CompTox/ToxCast则用于补受体/线粒体/氧化应激/内分泌相关assay endpoint。

### Priority 5: 同受试者CGM-exposome pilot

如果目标是最高水平期刊，这一步几乎不可替代。设计为N=60可行性或N=120正式桥接: 重复晨尿DEHP代谢物 + 10-14天CGM + 标准化餐食重复挑战 + mitigator测试 + 基础代谢表型。它能补上当前最大断点: 同一人内的环境暴露、代谢易感性和餐后血糖反应。

## 投稿策略

只靠当前计算结果，适合较强但不是顶级的计算型营养/环境健康论文。若完成原始单体NHANES、人工食物基质、Stanford分子验证和GEO/CompTox机制，才适合冲击AJCN、Clinical Nutrition、Environment International、EHP。若再加同受试者CGM-exposome pilot，才有现实机会向Nature Food、Cell Metabolism或Nature Medicine风格靠近。

## 最重要的取舍

不要继续横向堆更多弱外部数据集。下一步要做的是把最关键的三处证据做实:

1. **真实原始暴露混合物。**
2. **真实人工审定食物基质。**
3. **同受试者或分子层桥接验证。**

这三处补上后，论文才会从“聪明的跨数据库整合”变成“证据链闭合的高水平研究”。
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    findings = current_findings()
    tables = {
        "01_literature_and_guideline_update.csv": literature_update(),
        "02_current_evidence_audit.csv": evidence_audit(findings),
        "03_redesigned_evidence_chain.csv": redesigned_chain(),
        "04_priority_drylab_actions.csv": drylab_actions(),
        "05_same_participant_pilot_protocol.csv": pilot_protocol(),
        "06_manuscript_claim_ladder.csv": manuscript_claim_ladder(),
        "07_reviewer_attack_prebuttal_matrix.csv": reviewer_matrix(),
        "08_journal_path_decision_matrix.csv": journal_path(),
        "09_database_remediation_plan.csv": database_fix_plan(),
    }
    for name, rows in tables.items():
        write_csv(OUT / name, rows)
    write_text(OUT / "00_next_level_evidence_strategy_report.md", report(findings))
    write_text(
        OUT / "README.md",
        f"""# Next-Level Evidence Strategy

生成日期: {TODAY}

本文件夹回应“研究水平还不够充分、证据链还不够完整、论证还不够有力”的问题。它基于最新干实验输出和补充文献检索，重新定义下一轮真正能提升期刊层级的工作。

最重要结论: 下一步不要继续横向堆弱模块，而要补三处硬断点: 原始单体NHANES混合物、人工审定食物基质、同受试者或Stanford分子层桥接验证。
""",
    )
    manifest = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "output_dir": str(OUT),
        "mirror_dir": str(MIRROR),
        "central_claim": "Raw phthalate/DEHP metabolite mixture -> metabolic susceptibility -> food-matrix-dependent PPGR vulnerability",
        "source_packages": [str(FORMAL), str(HIGH)],
        "files": ["README.md", "00_next_level_evidence_strategy_report.md"] + list(tables.keys()),
    }
    (OUT / "00_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if MIRROR.exists():
        shutil.rmtree(MIRROR)
    shutil.copytree(OUT, MIRROR)
    print(f"Built next-level strategy package: {OUT}")
    print(f"Mirrored to: {MIRROR}")


if __name__ == "__main__":
    main()
