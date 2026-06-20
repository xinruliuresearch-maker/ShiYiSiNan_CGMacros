# Aim 1 食品 plasticizer panel 检测说明

## 目标

建立食品系统塑化剂暴露层，而不是只依赖 NHANES 尿代谢物。检测对象是市场真实食品中的 parent plasticizer burden，并将其与包装、加工、热接触、脂肪含量和食物基质连接。

## 样本

- 96 个计划样本，12 个食品系统 strata，每个 stratum 8 个独立样本。
- 每批加入 field blank、运输 blank、实验室 blank、duplicate、matrix spike。
- 所有样本记录包装材质、加热接触、加工等级、物理形态、脂肪/碳水/纤维。

## 分析物

Primary: DEHP。

Secondary: DiNP、DiDP、DBP、DiBP、BBzP、DINCH、DEHT。

人体尿样对应：MEHP、MEHHP、MEOHP、MECPP；计算 Sigma DEHP、percent oxidative、oxidative/MEHP ratio、ILR oxidative-vs-primary。

## 实验室要求

- 使用经验证的 targeted MS 方法；食品样本报告 ng/g wet weight。
- 报告 LOD/LOQ、回收率、批次、空白校正规则。
- 对脂肪高、液体、固体基质分别提供 matrix spike recovery。
- 低于 LOD 的值保留原始标志，分析中使用 LOD/sqrt(2) 和 censored-model sensitivity。

## 主分析

log10(plasticizer concentration) ~ packaging + processing + heat contact + fat level + physical form + matrix class。

## 成功标准

至少一个食品系统维度与 plasticizer burden 有稳定梯度，并能支撑“食品接触/加工来源暴露链条”的 Figure 1。
