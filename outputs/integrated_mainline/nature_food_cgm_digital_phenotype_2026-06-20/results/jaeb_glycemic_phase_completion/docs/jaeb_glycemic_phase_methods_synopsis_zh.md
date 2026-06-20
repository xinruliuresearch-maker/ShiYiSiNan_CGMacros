# 方法摘要

## 数据

使用公开 JAEB 糖尿病 RCT/干预研究数据。清洗脚本 harmonize participant-level 临床变量、HbA1c 结局、CGM 汇总、随机臂和研究标识。

## 相图构建

在具备基线 overall CGM 汇总的受试者中构建五个序参量：glycemic burden、hypoglycemic susceptibility、dynamic instability、circadian disruption 和 resilience proxy。序参量标准化后用 KMeans(k=5) 聚类。相位标签由聚类中心的 CGM 特征规则命名。

## 结局验证

结局包括 HbA1c 改善 >=0.5%、TIR 改善 >=5 个百分点、HbA1c 变化和 TIR 变化。先做未调整相位差异检验，再用调整 baseline HbA1c、年龄、baseline TIR、study fixed effects 和 randomized arm 的稳健模型估计相位主效应。

## 预测验证

比较 C1 临床、C2 临床+CGM、C4 相图特征集。模型包括 logistic ridge、树模型、boosting、SVM、KNN、MLP 等。验证策略包括 5-fold CV、leave-one-study-out、nested tuning、校准、决策曲线和 paired bootstrap。

## 治疗响应

在具备相位、结局和随机臂的研究中估计 treatment-by-phase 交互，并报告相位内调整风险差和 bootstrap CI。
