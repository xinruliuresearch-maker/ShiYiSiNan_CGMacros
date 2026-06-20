# Aim 3 INFOGEST-style 体外消化 SOP

## 目标

验证等碳水/等能量餐食重构是否通过更慢或更低的葡萄糖释放解释 PPGR 风险降低。

## 样本

- 16 对餐食原型：original vs redesigned。
- 每个版本至少 3 个实验重复。
- 餐食需记录实际可利用碳水、总能量、纤维、蛋白、脂肪、水分和粒径/均质化规则。

## 消化流程

采用 INFOGEST static in vitro digestion 框架：口腔、胃、小肠三个阶段；酶活、胆盐、pH 和空白/标准品按实验室验证方案记录。

## 时间点

0、15、30、60、90、120 min。

## 终点

1. released glucose。
2. starch hydrolysis percent。
3. early glucose release AUC 0-30 min。
4. total glucose release AUC 0-120 min。
5. viscosity 和 particle size 作为食物基质机制变量。

## 主要分析

paired model: glucose_release_AUC ~ meal_version + pair_id。

成功标准：redesigned 餐食的 early glucose release AUC 低于 original，并与 CGMacros counterfactual risk reduction 方向一致。
