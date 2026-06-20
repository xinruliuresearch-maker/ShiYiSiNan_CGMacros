# Bridge cohort protocol and SAP skeleton

## 目的

Bridge cohort 不是锦上添花，而是整合研究缺失的核心层。它要在同一批人中直接测试：食品系统暴露 -> 代谢易感性 -> PPGR 脆弱性 -> CGM 数字表型。

## 设计

入组 80-120 名成年人，覆盖正常血糖、糖尿病前期和已治疗但非胰岛素依赖的 2 型糖尿病人群。研究包含重复尿样、目标食品/包装接触塑化剂检测、标准餐挑战和 14-28 天 CGM。不能主动给受试者“投加”塑化剂；暴露对比应来自真实生活中可遇到的食品接触和加工情境，并在人体试验前完成预检测。

## 流程

Baseline：人口学、病史、用药、饮食记录、体格测量、HbA1c、空腹血糖、空腹胰岛素、血脂、晨尿 plasticizer panel 和 CGM 佩戴。

Free-living phase：7-14 天 CGM，配合餐食日志、可获得的活动/睡眠协变量，并重复晨尿。

Challenge phase：随机化标准餐访问，采用 2x2 结构：高/低 matrix protection 交叉高/低 measured food-contact burden，并匹配能量和碳水。如果四次访问不可行，用紧凑 Latin-square 或优先保留最关键对比。

Follow-up phase：继续 CGM 至总计 14-28 天，至少在一个 challenge day 重复尿样，并记录依从性和耐受性。

## 主要终点

Primary endpoint 1：尿 DEHP oxidative fraction 与 measured food-contact burden 是否关联 MSI-core 和 CGM phase/order parameters。

Primary endpoint 2：matrix protection 是否降低标准餐 2h iAUC、peak glucose delta 和 high-iAUC probability，并检验 MSI-core 与 exposure burden 的预设效应修饰。

Primary endpoint 3：locked CGM phase-map 能否在 nutrition/food-exposure cohort 中稳定赋值，并通过 wear-quality pass rate、phase distribution、phase stability 和 phase-wise PPGR gradients 评估有效性。

## 统计分析计划

暴露锚点沿用 NHANES 的协变量逻辑，餐食反应沿用 CGMacros 的 GEE/mixed model 逻辑。暴露组成继续保留 total-burden-adjusted oxidative-vs-primary contrast。标准餐 outcome 使用 repeated-meal models，并按 participant 聚类；预设协变量包括 age、sex、race/ethnicity、BMI、diabetes status/medication、energy intake、smoking/alcohol、physical activity、urinary creatinine、CGM wear quality 和 visit order。Phase membership 先应用 locked JAEB phase-map，不重新训练 phase algorithm，再检验 exposure 和 PPGR 与 phase/order parameters 的关系。

## 决策规则

如果校准较弱，所有输出定位为 phenotype/ranking，而不是 absolute clinical risk。如果亚组样本量偏小，只报告 bootstrap intervals，不做强亚组结论。如果 food-contact assay 不能产生清晰暴露对比，则将 bridge cohort 定位为 susceptibility/meal-matrix validation，并把化学暴露主张保留在 NHANES anchor。

## 最低发表价值

即使作为 pilot，这个 cohort 也必须产出三件事：同人群 construct crosswalk、CGMacros matrix result 的标准餐验证，以及可对每个受试者输出 MSI、meal-risk 和 CGM phase-map phenotype 的整合软件报告。
