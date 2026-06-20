# Aim 2 统计分析计划

## Primary

线性混合模型：log1p(iAUC_2h) ~ MSI + urinary oxidative DEHP profile + matrix arm + MSI x matrix + oxidative profile x matrix + premeal glucose + meal order + sex + age + BMI + (1|participant)。

## Secondary

- peak_delta_2h。
- high-response meal logistic mixed model。
- time-to-peak Cox 或 accelerated failure-time sensitivity。

## Sensitivity

1. 仅使用低 protocol deviation 餐次。
2. 排除尿肌酐极端值。
3. 用 percent oxidative、oxidative/MEHP ratio、ILR 三种暴露定义。
4. 用 CGMacros 训练得到的 MSI/food-matrix 模型预测 pilot PPGR，作为 external validation。

## 成功标准

高 MSI 或高 oxidative profile 在低保护基质餐中显示更高 PPGR；高保护基质方向性降低 PPGR。
