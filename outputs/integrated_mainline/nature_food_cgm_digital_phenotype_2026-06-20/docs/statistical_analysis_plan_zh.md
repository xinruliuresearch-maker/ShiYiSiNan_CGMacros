# 统计分析计划与投稿级实验蓝图

## 研究问题

本研究使用公开 JAEB 糖尿病 RCT/干预研究数据，构建血糖动力学相图，并评估相位表征在结局预测、治疗响应分层和个体化干预建议中的价值。

## 主要终点

主要预测终点：随访 HbA1c 较基线改善 >=0.5 个百分点。

关键次要终点：随访 CGM time-in-range 70-180 mg/dL 改善 >=5 个百分点。

连续次要终点：HbA1c 变化、TIR 变化、低血糖时间变化、体重/BMI 变化。

## 暴露与特征集

C1 临床基线特征：研究、治疗臂、年龄、性别、种族/族裔、糖尿病病程、基线 HbA1c、BMI 等。

C2 临床+CGM 特征：C1 加基线 CGM 均值、TIR、TBR、TAR、CV、佩戴时长。

C4 相图特征：C2 加血糖负担、低血糖易感、动态不稳定、昼夜节律紊乱、恢复力代理指标和相位标签。

所有预测模型只能使用基线变量；随访变量只用于结局定义。

## 模型比较

候选模型包括 logistic ridge、random forest、extra trees、hist gradient boosting、SVM、KNN、MLP、XGBoost、LightGBM、CatBoost 和 dummy baseline。

内部验证使用分层 5 折交叉验证；外部泛化使用 leave-one-study-out。模型选择以 AUROC 为主，同时报告 AUPRC、Brier、校准斜率、校准截距和 expected calibration error。

## 临床效用

对表现靠前模型进行 decision curve analysis，在 0.05-0.80 决策阈值范围内比较模型、treat-all 与 treat-none 的净获益。

## 可解释性

使用交叉验证框架内的 permutation importance，避免用训练集重要性夸大解释。重要性解释以方向无关的预测贡献为主，不作因果解释。

## 异质性治疗响应

优先在具备相位标签和明确对照/干预臂的 RCT 中估计相位分层治疗响应。主分析使用治疗臂、研究固定效应、基线 HbA1c、年龄、基线 TIR 与 treatment-by-phase 交互的 L2 正则化逻辑模型，报告调整风险差和 bootstrap CI。

## 稳健性分析

1. 相图 bootstrap 稳定性，报告 adjusted Rand index 和 silhouette。
2. Leave-one-study-out 外部验证热图。
3. C4 相图特征相对于 C1/C2 的增量 AUROC。
4. 名义最佳模型之间的 paired bootstrap AUROC 差异。
5. 相位-结局关联的协变量调整模型。

## 投稿叙事

若相图特征未显著提高 AUROC，应将相图定位为机制启发的低维表征、分层工具和解释框架，而不是单纯预测增强器。高水平期刊更看重可复现数据处理、严格外部验证、校准、临床效用、稳健性与克制解释。
