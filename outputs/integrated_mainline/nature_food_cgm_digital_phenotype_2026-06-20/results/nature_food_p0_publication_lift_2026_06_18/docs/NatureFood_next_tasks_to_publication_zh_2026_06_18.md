# Nature Food 下一阶段任务设计

Date: 2026-06-18

## Strategic Decision

当前最强路线不是继续无限增加数据库，而是把现有证据组织成一篇 Nature Food **Analysis**：食品系统暴露背景、真实餐食基质、CGM 数字表型在三个层面形成 triangulated evidence。Nature Food 的范围覆盖 Food Chemistry、Food Processing、Food Systems、Human Nutrition、Information Technology 和 Public Health Nutrition；Analysis 栏目允许对既有数据或比较数据进行新分析，并要求 broad audience 重要性、100-150 word abstract、最多 6 个 display items。

Article 路线暂不作为立即投稿形态。Article 需要更强的新研究闭环，目前缺口是同一批人中同时测量尿/食物接触 plasticizer panel、标准餐 PPGR、14-28 天 CGM 和胰岛素/HOMA。这个缺口由 Aim 4 bridge cohort 解决。

## Locked Submission Route

**Route A: Nature Food Analysis presubmission now**

Use when the claim is: food-system exposure context, meal matrix and CGM dynamics jointly define a digital metabolic vulnerability phenotype.

Allowed claims:

- NHANES anchors population-level DEHP oxidative profile and metabolic susceptibility.
- CGMacros shows meal matrix and MSI-core express susceptibility as PPGR vulnerability.
- JAEB/Loop/PSO phase-map provides a transportable CGM digital phenotype and response-ranking language.
- CGMacros phase/order-parameter bridge supports compatibility between meal-response and dynamic CGM language.

Forbidden claims:

- Plasticizer exposure directly causes PPGR or phase membership in the same individuals.
- Counterfactual meal redesign is proven intervention efficacy.
- Phase-map output is autonomous clinical decision support.

**Route B: Nature Food Article after Aim 4**

Use only after same-person bridge data establish the exposure -> MSI -> PPGR -> CGM order-parameter chain.

## P0: 7-Day Presubmission Sprint

Goal: make the editor understand the paper in one page and decide whether Nature Food wants the Analysis.

1. Freeze the presubmission package.
   Deliverables: one-page enquiry, 100-150 word abstract, 6-figure spine, title, claim hierarchy.
   Success criterion: a senior reader can state the food-system contribution in one sentence without hearing an oral explanation.

2. Rewrite Results around six display items.
   Deliverables: Results skeleton with real numbers only; no background filler; one paragraph per figure.
   Success criterion: every paragraph contains at least one numeric result and one claim label: direct, triangulated, model-based or bridge-needed.

3. Create main-versus-extended-data allocation.
   Deliverables: table assigning each result to main figure, extended data, supplement or exclusion.
   Success criterion: main text contains only the evidence needed for the central food-system claim.

4. Lock reproducibility.
   Deliverables: integrated package README, schema, toy data, unit tests, figure reproduction script, manifest.
   Success criterion: a clean run regenerates manuscript tables, figures and source data.

5. Tighten reviewer-risk language.
   Deliverables: response memo for causality, exposure measurement, matrix labels, calibration, fairness, external transport and counterfactual claims.
   Success criterion: no claim in the abstract or figure legends exceeds available evidence.

Decision gate: send presubmission enquiry if the package reads as a food-system Analysis rather than a diabetes ML benchmark.

## P1: 21-Day Manuscript Sprint

Goal: convert the presubmission package into a full Analysis manuscript that can survive external peer review.

### Aim 1: Food-System Exposure Anchor

Tasks:

- Convert the food plasticizer measurement panel into a structured extraction table with food category, packaging/contact condition, compound, matrix, assay method, concentration metric and uncertainty.
- Map NHANES dietary/source proxies to packaging, processing and food-contact plausibility classes.
- Add an explicit negative-control or specificity table where possible.
- Harmonize all Aim 1 claims as population exposure anchors, not direct food assay claims.

Deliverables:

- Extended Data table for food-system source proxies.
- Literature extraction table for plasticizer panel.
- Aim 1 Methods subsection with NHANES survey design, LOD handling, creatinine handling and exclusions.

### Aim 2: Meal Matrix and PPGR Expression

Tasks:

- Freeze the collapsed 3-class food matrix and keep the 6-class labels as traceable annotation.
- Add adjudication audit: coverage, ambiguity, label-change sensitivity and inter-rater plan if a second annotator is available.
- Convert leave-one-subject-out results into an influence figure or Extended Data table.
- Pre-specify the standard meal challenge for Aim 4 using the CGMacros matrix findings.

Deliverables:

- Matrix defense table.
- Main Figure 3 final source data.
- Standard meal challenge specification.

### Aim 3: CGM Digital Phenotype and Deployment Layer

Tasks:

- Reframe phase-map as a CGM digital phenotype, not a generic prediction benchmark.
- Keep calibration/fairness as guardrails and ranking limitations.
- Use CGMacros phase bridge only as order-parameter compatibility, not clinical phase validation.
- Build a clear workflow from phenotype to phase-guided digital care hypothesis.

Deliverables:

- Phase-map algorithm card.
- Calibration and fairness Extended Data.
- Integrated phenotype software release v0.2.

### Integrated Manuscript

Tasks:

- Write full Introduction in three paragraphs: food-system exposure problem, meal matrix expression, CGM digital phenotype opportunity.
- Write Results in six figure-linked sections.
- Write Discussion without subheadings, emphasizing triangulated evidence and the Aim 4 upgrade path.
- Keep the abstract inside 100-150 words.
- Keep display items to six.

Decision gate: submit full Analysis only if the manuscript has one central claim, six figure-linked result sections and no unsupported causal bridge.

## P2: 90-Day Article Upgrade Path

Goal: create the same-person data needed to turn the study from triangulated Analysis into Article-level evidence.

### Aim 4 Bridge Cohort

Design:

- N = 80-120 adults, with a 20-30 person feasibility pilot first.
- Urine plasticizer panel with creatinine/specific gravity.
- Food/contact plasticizer panel on standardized meals and selected packaged foods.
- 2x2 meal matrix challenge: high-protection vs low-protection matrix, low-contact vs high-contact preparation/contact condition.
- 14-28 day CGM.
- HbA1c, fasting glucose, insulin, HOMA-IR and covariates.

Primary tests:

- Exposure profile -> MSI/HOMA/HbA1c.
- MSI -> PPGR response under controlled meal matrix.
- Meal/contact condition -> glucose release and PPGR.
- PPGR/order parameters -> free-living CGM phase-map metrics.

Decision gate for Article route:

- Assay feasibility confirmed.
- Standard meals produce separable glucose-release and PPGR profiles.
- Same-person exposure, PPGR and CGM order parameters align in the prespecified direction.
- Safety, adherence and missingness are acceptable.

## What Not To Do Next

- Do not add another disconnected ML benchmark unless it directly strengthens the CGM phenotype claim.
- Do not present food plasticizer source proxies as measured food concentrations.
- Do not expand to broad exposomics without preserving the food-system narrative.
- Do not use intervention language for counterfactual meal redesign before prospective validation.
- Do not make the paper look like three separate papers stitched together.

## Next Concrete Step

Send the Analysis presubmission enquiry after one final visual pass of Figures 1-6 and the 150-word abstract. In parallel, begin Aim 4 feasibility work so that a positive editorial signal can be followed by either rapid Analysis submission or Article-upgrade planning.
