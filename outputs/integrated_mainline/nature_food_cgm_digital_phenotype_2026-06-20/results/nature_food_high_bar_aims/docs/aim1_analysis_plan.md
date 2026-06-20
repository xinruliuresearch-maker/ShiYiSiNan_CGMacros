# Aim 1 分析计划：食品系统塑化剂暴露与人群代谢易感性

## 已锁定的 NHANES 分析

使用 NHANES 2013-2018，保留复杂抽样设计。核心暴露为 ln(Sigma DEHP)、percent oxidative、ln(oxidative/MEHP)、ILR oxidative-vs-primary。固定协变量：age、sex、race/ethnicity、education、PIR、energy intake、smoking、alcohol、physical activity、urinary creatinine、cycle。

## 新增食品 panel 分析

1. 描述每个食品系统 stratum 的 plasticizer concentration 分布。
2. 以 DEHP 为 primary；以 sum parent plasticizer 和 alternatives 为 secondary。
3. 左删失处理：primary 使用 LOD/sqrt(2)，敏感性使用 Tobit 或 rank-based model。
4. 多重比较：同一 family 内 FDR。
5. 输出食品系统暴露链条图：source -> food burden -> urine metabolites -> metabolic susceptibility。

## 桥接模型

NHANES 层面证明尿 DEHP oxidative profile 与 MSI/HOMA-IR/HbA1c 相关；食品 panel 层面证明某些食品系统场景具有更高 plasticizer burden。两者只作为三角证据，不声称同一人群的直接因果链。
