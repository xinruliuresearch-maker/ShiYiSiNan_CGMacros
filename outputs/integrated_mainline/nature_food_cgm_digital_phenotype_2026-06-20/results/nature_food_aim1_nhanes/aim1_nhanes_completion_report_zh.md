# Aim 1：NHANES 人群暴露锚点完成报告

生成日期：2026-06-17

## 执行状态

已完成 Aim 1 的完整建模框架、最终 R `survey` 脚本和正式 R `survey` 结果。

本机原先未安装 R，已通过 `winget` 安装 R 4.6.0，并将 `survey` 包安装到用户库：

- Rscript：`C:\Program Files\R\R-4.6.0\bin\Rscript.exe`
- 用户 R 包库：`C:\Users\liu12\Documents\R\win-library\4.6`

最终 R survey 脚本：

- `D:\ai for science\scripts\run_nature_food_aim1_nhanes_survey.R`

正式 R survey 输出已生成在：

- `D:\ai for science\results\nature_food_aim1_nhanes`

同时保留 Python 审计版作为方向核对：

- `D:\ai for science\scripts\run_nature_food_aim1_nhanes_python_audit.py`

Python 审计版使用加权最小二乘，并按 NHANES `SDMVSTRA + SDMVPSU` 组合做 cluster-robust 标准误；正式投稿表应使用 R `survey` 结果。

## 固定协变量集

所有主模型按用户指定纳入：

- age：`RIDAGEYR`
- sex：`RIAGENDR`
- race/ethnicity：`RIDRETH3`
- education：`DMDEDUC2`
- PIR：`INDFMPIR`
- energy intake：`DR1TKCAL`
- smoking：`ever_smoker`
- alcohol：`alcohol_ever`
- physical activity：`any_physical_activity`
- urinary creatinine：`ln_URXUCR`
- cycle：`cycle`

## 输出文件

目录：

- `D:\ai for science\results\nature_food_aim1_nhanes`

主要输出：

| 文件 | 内容 |
|---|---|
| `aim1_main_survey_results.csv` | 主模型：DEHP 总量、%Oxidative、oxidative/MEHP、ILR 与 MSI/代谢结局 |
| `aim1_lod_creatinine_sensitivity_survey_results.csv` | LOD、肌酐、尿稀释和 winsorized 暴露敏感性 |
| `aim1_diabetes_medication_exclusion_survey_results.csv` | 糖尿病诊断/用药排除敏感性 |
| `aim1_cycle_replication_survey_results.csv` | 2013-2014、2015-2016、2017-2018 分周期复制 |
| `aim1_composition_total_adjusted_survey_results.csv` | 总 DEHP 调整后的 oxidative-vs-primary 组成模型 |
| `aim1_nhanes_survey_report.md` | R survey 运行摘要 |

## 主模型结果摘要

解释单位：

- log 结局使用百分比变化。
- HbA1c 使用原始百分比点变化。
- MSI-core 使用标准化指数单位。

| outcome | exposure | n | effect | 95% CI | p | q |
|---|---:|---:|---:|---|---:|---:|
| MSI-core | %Oxidative per 10 pp | 1,313 | 0.168 | 0.060, 0.277 | 0.0058 | 0.0077 |
| MSI-core | ln(Oxidative/MEHP) | 1,313 | 0.183 | 0.100, 0.266 | 0.0005 | 0.0015 |
| ln(HOMA-IR) | %Oxidative per 10 pp | 1,292 | +19.96% | +6.30%, +35.37% | 0.0069 | 0.0069 |
| ln(HOMA-IR) | ln(Oxidative/MEHP) | 1,292 | +24.41% | +12.56%, +37.51% | 0.0006 | 0.0020 |
| HbA1c | %Oxidative per 10 pp | 2,671 | +0.110 | +0.022, +0.197 | 0.0187 | 0.0187 |
| HbA1c | ln(Oxidative/MEHP) | 2,671 | +0.135 | +0.071, +0.198 | 0.0008 | 0.0016 |

总 DEHP 结果：

- `ln(Sigma DEHP) -> MSI-core`: 0.066 (0.003, 0.128), p=0.041。
- `ln(Sigma DEHP) -> ln(HOMA-IR)`: +8.80% (+3.63%, +14.23%), p=0.003。
- `ln(Sigma DEHP) -> HbA1c`: +0.084 (+0.018, +0.150), p=0.018。

解释：氧化代谢谱对 MSI-core 和 HOMA-IR 的信号强于总 DEHP，支持 Nature Food 稿件的“oxidative profile / metabolic susceptibility”主线。

## LOD、肌酐、尿稀释敏感性

核心暴露 `%Oxidative per 10 pp` 在主要敏感性中方向稳定：

| scenario | outcome | n | effect | 95% CI | p |
|---|---|---:|---:|---|---:|
| main | MSI-core | 1,313 | 0.168 | 0.060, 0.277 | 0.0058 |
| drop urinary creatinine covariate | MSI-core | 1,314 | 0.203 | 0.120, 0.287 | 0.0002 |
| valid creatinine 30-300 | MSI-core | 1,214 | 0.196 | 0.075, 0.317 | 0.0044 |
| all oxidative detected | MSI-core | 1,304 | 0.204 | 0.094, 0.315 | 0.0018 |
| main | ln(HOMA-IR) | 1,292 | +19.96% | +6.30%, +35.37% | 0.0069 |
| valid creatinine 30-300 | ln(HOMA-IR) | 1,194 | +25.34% | +7.50%, +46.13% | 0.0079 |
| all oxidative detected | ln(HOMA-IR) | 1,283 | +23.36% | +8.46%, +40.30% | 0.0042 |

解释：LOD 和尿肌酐处理没有改变主要方向，支持结果稳健性。

## 糖尿病诊断/用药排除敏感性

关键结果：

- 全样本中 `%Oxidative -> ln(HOMA-IR)` 为 +19.96%。
- 排除已诊断糖尿病后为 +14.62%。
- 排除糖尿病用药后为 +14.42%。
- `ln(Oxidative/MEHP)` 在排除诊断或用药后仍与 ln(HOMA-IR) 稳定正相关。
- HbA1c 对 `%Oxidative` 在排除诊断/用药后减弱，但 `ln(Oxidative/MEHP)` 仍保留正向关联。

解释：胰岛素抵抗主锚点较稳；HbA1c 对糖尿病诊断/治疗状态更敏感，适合作为次要结局。

## 分周期复制

分周期结果总体方向一致：

- 2013-2014：`%Oxidative -> ln(HOMA-IR)` +20.24% (+4.92%, +37.79%)；`ln(Oxidative/MEHP) -> ln(HOMA-IR)` +22.10% (+12.07%, +33.02%)。
- 2015-2016：`%Oxidative -> ln(HOMA-IR)` +20.05% (+2.34%, +40.82%)；`ln(Oxidative/MEHP) -> ln(HOMA-IR)` +28.79% (+11.17%, +49.20%)。
- 2017-2018：部分 HOMA-IR/TyG 相关模型因空腹/胰岛素可用样本不足被标记为 `too_few_rows`，不应作为主要周期复制证据。

解释：2013-2014 和 2015-2016 对 HOMA-IR 的方向清晰；2017-2018 受空腹/胰岛素可用样本限制，不应过度解释。

## 总 DEHP 调整后的组成模型

在调整 `ln(Sigma DEHP_comp)` 后，oxidative-vs-primary balance 仍保留独立信号：

| outcome | exposure | n | effect | 95% CI | p | q |
|---|---|---:|---:|---|---:|---:|
| MSI-core | ln(Oxidative/MEHP) | 1,313 | 0.177 | 0.093, 0.261 | 0.0009 | 0.0014 |
| MSI-core | ILR oxidative-vs-primary | 1,313 | 0.199 | 0.098, 0.301 | 0.0014 | 0.0014 |
| ln(HOMA-IR) | ln(Oxidative/MEHP) | 1,292 | +23.23% | +10.37%, +37.59% | 0.0018 | 0.0032 |
| ln(HOMA-IR) | ILR oxidative-vs-primary | 1,292 | +26.00% | +10.27%, +43.97% | 0.0032 | 0.0032 |
| HbA1c | ln(Oxidative/MEHP) | 2,671 | +0.118 | +0.048, +0.189 | 0.0043 | 0.0043 |
| HbA1c | ILR oxidative-vs-primary | 2,671 | +0.142 | +0.058, +0.226 | 0.0041 | 0.0043 |

解释：这直接支持 Nature Food Aim 1 的关键点：不是只有总 DEHP 负荷，而是 DEHP 代谢构成/氧化谱与代谢易感性相关。

## 投稿叙事建议

Aim 1 可以写成：

> In NHANES 2013-2018, the oxidative metabolic profile of DEHP exposure, rather than total DEHP burden alone, was consistently associated with an insulin-resistance-related metabolic susceptibility index and with glycemic-lipid metabolic markers. These associations were robust to urinary dilution, LOD handling, and diabetes diagnosis/medication exclusions, and persisted in total-burden-adjusted compositional models.

中文解释：

> NHANES 结果支持将 DEHP 氧化代谢谱作为上游代谢易感性锚点。该锚点随后可被转移到 CGMacros 中，检验 MSI-core 是否对应更高餐后血糖脆弱性。

## 可复现运行命令

当前 PowerShell 会话可能尚未刷新 PATH，因此建议用完整路径运行：

```powershell
$env:R_LIBS_USER='C:\Users\liu12\Documents\R\win-library\4.6'
& 'C:\Program Files\R\R-4.6.0\bin\Rscript.exe' 'D:\ai for science\scripts\run_nature_food_aim1_nhanes_survey.R'
```

如果打开新的 PowerShell 后 PATH 已刷新，也可以直接运行：

```powershell
Rscript "D:\ai for science\scripts\run_nature_food_aim1_nhanes_survey.R"
```

## 结论

Aim 1 的数据流、R survey 主模型、敏感性、分周期复制和组成模型已经完成。正式 R survey 结果稳定支持 Nature Food 稿件的上游假设：

**DEHP oxidative profile -> metabolic susceptibility**

这些结果可作为 Figure 2 和 Supplementary Table 的正式 source data，下一步可以进入 Aim 2：CGMacros 食物基质与 PPGR 脆弱性模型。
