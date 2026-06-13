# CGMacros/PPGR 研究外部数据库下载与整合方案

日期：2026-06-10

## 一、总体判断

本项目的核心科学问题是：在 CGMacros 餐食级连续血糖数据基础上，构建可解释、可校准、可外部验证的个体化餐后血糖反应（PPGR）预测与干预框架。仅依赖 CGMacros 本身，样本量、饮食结构、疾病状态和人群多样性都不足以支撑极高水平期刊的说服力。因此，本轮数据库补充遵循三个原则：

1. 优先下载具有 CGM 与餐食信息的数据，用于外部 PPGR 验证。
2. 补充健康人、T1D、T2D、中国人群、标准化食物挑战等不同外部场景，用于检验模型可迁移性和边界。
3. 选择能服务“干实验为主，少量体外仿生消化验证”的数据源，避免盲目堆砌无关数据库。

本轮已下载并整理 6 个新外部数据库，并将原项目已有 OhioT1DM 纳入清单。机器可读清单已保存为：

- `outputs/dataset_search/external_dataset_inventory_2026-06-10.csv`
- `outputs/dataset_search/external_dataset_inventory_2026-06-10.json`

## 二、已下载数据库与本地路径

| 优先级 | 数据库 | 本地路径 | 核心价值 |
|---|---|---|---|
| A | T1D-UOM longitudinal multimodal T1D dataset | `data/external/T1D_UOM_2025` | 餐食宏量营养素、CGM、胰岛素、活动、睡眠，多模态外部 PPGR 验证 |
| A | Stanford CGMDB | `data/external/Stanford_CGMDB` | 标准化食物/缓释干预挑战，适合机制验证和食物反应异质性分析 |
| A- | D1NAMO diabetes glucose-food-insulin subset | `data/external/D1NAMO_T1D_GlucoseFoodInsulin` | 食物图片、餐食描述、CGM、胰岛素，可补强食物图像和餐食窗口对齐 |
| A- | ShanghaiT1DM and ShanghaiT2DM | `data/external/ShanghaiT1DM_T2DM` | 中国 T1D/T2D CGM 与临床参考，可增强跨人群和疾病状态论证 |
| A- | OhioT1DM 2018/2020 | `data/external/OhioT1DM` | 项目已有，T1D 外部验证和疾病状态敏感性分析 |
| B+ | Jaeb T1D Nutrition Dataset 2015-2016 | `data/external/Jaeb_Nutrition_T1D_2015_2016` | 详细营养、可利用碳水、GI/GL 字段，可辅助特征工程 |
| B+ | Jaeb CGM in healthy nondiabetic adults | `data/external/Jaeb_CGMND_HealthyAdults_2017` | 健康成人 CGM 参考范围和伪餐时窗口 |
| C | Jaeb CGM in healthy young children | `data/external/Jaeb_CGMND_HealthyYoungChildren_2021` | 儿童健康 CGM 参考，仅建议作为补充敏感性分析 |

## 三、数据库逐项说明

### 1. T1D-UOM longitudinal multimodal T1D dataset

来源：Zenodo，DOI [10.5281/zenodo.15806142](https://doi.org/10.5281/zenodo.15806142)  
本地路径：`data/external/T1D_UOM_2025`

已下载内容包括：

- `Glucose Data/*.csv`：17 个 glucose 文件，356,146 条血糖记录。
- `Nutrition Data/*.csv`：15 个 nutrition 文件，4,351 条餐食记录。
- `Insulin Data/Bolus Data/*.csv`：16 个 bolus 文件，5,660 条 bolus 记录。
- `Activity Data/*.csv`、`Sleep Data/*.csv`、`Insulin Data/Basal Data/*.csv`。

关键字段：

- 餐食：`meal_ts`, `meal_type`, `meal_tag`, `carbs_g`, `prot_g`, `fat_g`, `fibre_g`
- 血糖：`bg_ts`, `value`
- 胰岛素：`bolus_ts`, `bolus_dose`

建议用途：

1. 作为最优先的外部 PPGR 数据库之一，构建与 CGMacros 相同的餐后 2h/3h iAUC、峰值、达峰时间指标。
2. 增加胰岛素、活动、睡眠等混杂因素控制，展示模型不仅是“碳水预测器”，而是对真实生活血糖动力学有稳健解释。
3. 进行 leave-dataset-out validation：CGMacros 训练，T1D-UOM 作为疾病状态外部测试；或相反用于迁移学习/校准实验。

主要限制：

- T1D 人群与 CGMacros 的人群和生理机制不同，必须把它定位为“跨疾病状态稳健性与迁移验证”，不应直接当作同分布验证。

### 2. Stanford CGMDB

来源：Stanford CGMDB 数据页 [https://cgmdb.stanford.edu/data/](https://cgmdb.stanford.edu/data/)  
本地路径：`data/external/Stanford_CGMDB`

已下载文件：

- `data_cgm.csv`：23,520 条标准化食物挑战 CGM 曲线。
- `data_meta.csv`：74 位受试者临床和代谢表型。
- `data_lipids.csv`
- `data_metabolomics.csv`
- `data_olink.csv`

关键字段：

- `glucose`, `subject`, `foods`, `mitigator`, `food`, `rep`, `mins_since_start`
- 临床表型包括 `HbA1c`, `fasting glucose`, `fasting insulin`, `BMI`, `Sex`, `Ethnicity`, `age`, `OGTT120` 等。

建议用途：

1. 作为“标准化食物挑战外部验证”而非普通自由饮食数据。
2. 验证不同食物和 mitigator 对餐后血糖曲线的影响，支持机制层面的因果叙事。
3. 与陈晓东教授体外消化仿生系统对接：优先选择 Stanford CGMDB 中具有代表性、曲线差异明显的食物类型或缓释干预，作为体外消化机制验证对象。
4. 利用代谢组、脂质组、Olink 数据探索高反应者/低反应者表型，为高水平论文提供机制线索。

主要限制：

- 这是标准化食物挑战，不是自由生活餐食数据库；缺乏完整餐食宏量营养素表，不能直接替代 CGMacros。

### 3. D1NAMO 糖尿病 glucose-food-insulin 子集

来源：Zenodo，DOI [10.5281/zenodo.5651217](https://doi.org/10.5281/zenodo.5651217)  
本地路径：`data/external/D1NAMO_T1D_GlucoseFoodInsulin`

本轮只下载了与本研究直接相关的子包：

- `diabetes_subset_pictures-glucose-food-insulin.zip`

规模：

- 9 位 T1D 参与者。
- glucose 记录 8,221 条。
- food 记录 115 条。
- insulin 记录 126 条。
- 食物图片 106 张。

关键字段：

- glucose：`date`, `time`, `glucose`, `type`, `comments`
- food：`picture`, `description`, `calories`, `balance`, `quality`, `datetime`
- insulin：`date`, `time`, `fast_insulin`, `slow_insulin`, `comment`

建议用途：

1. 补强 CGMacros 项目的食物图片维度，探索“图片-文本-营养估计-PPGR”的外部可行性。
2. 与 CGMacros 的 food photos 形成互补，用于评估食物图像特征是否能提高餐后血糖预测。
3. 用作小样本外部 case study：展示模型在食物图像较丰富但宏量营养素较弱的数据中如何降级运行。

主要限制：

- 样本小，T1D 人群，食物只有描述和热量，不具备完整宏量营养素。

### 4. ShanghaiT1DM and ShanghaiT2DM

来源：Figshare，DOI [10.6084/m9.figshare.21600933.v5](https://doi.org/10.6084/m9.figshare.21600933.v5)  
许可：CC BY 4.0  
本地路径：`data/external/ShanghaiT1DM_T2DM`

下载和校验：

- 下载文件：`data/external/_downloads/diabetes_datasets_shanghai_figshare_21600933_v5.zip`
- 文件 MD5 已按 Figshare API 校验通过。

规模：

- `Shanghai_T1DM`：16 个 visit 文件。
- `Shanghai_T2DM`：109 个 visit 文件。
- 含 `Shanghai_T1DM_Summary.xlsx` 和 `Shanghai_T2DM_Summary.xlsx`。

建议用途：

1. 中国 T1D/T2D CGM 外部参照，增强本研究对中国人群和疾病状态的外部可信度。
2. 建立 CGM phenotype 维度，例如 mean glucose、SD、CV、TIR、TAR、TBR、MAGE、MODD。
3. 与 CGMacros 中不同 glycemic status 或代谢风险分层进行对照，形成“从健康/一般人群到糖尿病人群”的血糖表型连续谱。

主要限制：

- 没有明确餐食宏量营养素记录，不能作为 meal-level PPGR 主验证集。

### 5. Jaeb T1D Nutrition Dataset 2015-2016

来源：Jaeb public diabetes archive [https://public.jaeb.org/datasets/diabetes](https://public.jaeb.org/datasets/diabetes)  
本地路径：`data/external/Jaeb_Nutrition_T1D_2015_2016`

规模：

- meal-level nutrition 表约 4,944 条记录。
- roster 表约 483 条记录。

关键字段：

- `MealTime`
- `CalEnergy`
- `TotalCarbs`
- `TotalProtein`
- `TotalDietFiber`
- `AvailCarb`
- `GlycIndexGlucose`
- `GlycLoadGlucose`

建议用途：

1. 用于改造 CGMacros 的营养特征工程，尤其是 available carbohydrate、GI、GL、糖类细分、脂肪酸和纤维相关特征。
2. 对 CGMacros 餐食结构进行外部营养分布比较，说明研究对象的饮食代表性。
3. 作为“营养结构知识库”，帮助设计体外仿生消化实验的餐食原型。

主要限制：

- 本下载包没有与餐食直接配对的 CGM 结局，因此不应作为 PPGR outcome 验证集。

### 6. Jaeb 健康成人非糖尿病 CGM 数据

来源：Jaeb public diabetes archive [https://public.jaeb.org/datasets/diabetes](https://public.jaeb.org/datasets/diabetes)  
本地路径：`data/external/Jaeb_CGMND_HealthyAdults_2017`

规模：

- `NonDiabDeviceCGM.csv`：385,292 条 CGM 记录。
- `NonDiabParticipantLogs.csv`：1,694 条参与者日志记录。
- `NonDiabScreening.csv`：171 条筛查记录。

建议用途：

1. 构建健康成人 CGM 正常波动参考，作为 CGMacros PPGR 幅度的参照。
2. 利用 breakfast/lunch/dinner/snack 时间构建伪餐时窗口，比较餐后波动分布。
3. 支持论文中“模型适用边界”的论证：哪些响应属于健康范围，哪些属于代谢异常或高风险响应。

主要限制：

- 有用餐时间，但缺乏宏量营养素，不适合做宏量营养素-PPGR 主模型训练。

### 7. Jaeb 健康儿童 CGM 数据

来源：Jaeb public diabetes archive [https://public.jaeb.org/datasets/diabetes](https://public.jaeb.org/datasets/diabetes)  
本地路径：`data/external/Jaeb_CGMND_HealthyYoungChildren_2021`

规模：

- `CGMNDDeviceCGM.txt`：117,130 条 CGM 记录。

建议用途：

- 仅作为儿童健康 CGM 参考或敏感性分析，不建议进入主结果。

主要限制：

- 儿童人群与 CGMacros 成人餐食 PPGR 研究不匹配。

### 8. OhioT1DM

来源：OhioT1DM 官方页 [https://smarthealth.cs.ohio.edu/OhioT1DM-dataset.html](https://smarthealth.cs.ohio.edu/OhioT1DM-dataset.html)  
本地路径：`data/external/OhioT1DM`

项目中已存在该数据。建议继续作为 T1D disease-state validation 或 pipeline sanity check，但如果目标是高水平营养学/代谢期刊，应避免把它包装成与 CGMacros 同分布的外部验证。

## 四、未能自动下载但强烈建议后续获取的数据

### HUPA-UCM Diabetes Dataset

来源：Mendeley Data，DOI [10.17632/3hbcscwz44.1](https://doi.org/10.17632/3hbcscwz44.1)  
状态：已检索，未能自动下载。

数据介绍显示其包含 25 位 T1D 受试者至少 14 天的 CGM、胰岛素剂量、餐食碳水、步数、能量消耗、心率和睡眠。它与 T1D-UOM 的价值非常接近，适合做多模态 T1D 外部验证。

未自动下载原因：

- Mendeley Data 页面显示为公开 CC BY 4.0 数据，但其文件树通过前端和公共 API 动态加载。自动脚本在无需登录的文件 API 上未能直接获得可下载根目录。

后续建议：

- 使用浏览器手动下载或登录 Mendeley 后导出。
- 获取后放入 `data/external/HUPA_UCM_Diabetes_2024`。
- 与 T1D-UOM 做双外部验证：一个用于模型调参策略探索，另一个用于完全 hold-out 报告。

## 五、建议的高水平研究整合路线

### 路线 1：CGMacros 作为主发现队列

CGMacros 仍应作为主数据集，因为它有真实自由生活餐食、CGM、营养宏量素和部分微生物/临床信息。主模型仍围绕：

- 2h/3h iAUC
- peak delta
- time-to-peak
- return-to-baseline
- curve shape clusters

外部数据库不应稀释主问题，而应服务于“模型是否稳健、机制是否可信、适用边界是否清楚”。

### 路线 2：建立统一 PPGR 数据标准层

建议新增统一中间表，而不是为每个外部库单独写分析：

| 字段组 | 推荐字段 |
|---|---|
| dataset metadata | `dataset`, `source`, `participant_id`, `visit_id`, `population`, `disease_state` |
| meal event | `meal_ts`, `meal_type`, `food_description`, `food_image_path`, `energy_kcal`, `carbs_g`, `protein_g`, `fat_g`, `fiber_g`, `available_carb_g`, `GI`, `GL` |
| CGM | `glucose_ts`, `glucose_mgdl`, `sensor_type`, `record_type` |
| medication | `bolus_ts`, `bolus_units`, `basal_rate`, `insulin_type` |
| context | `steps`, `activity_kcal`, `sleep_duration`, `sleep_quality`, `heart_rate` |
| phenotype | `age`, `sex`, `BMI`, `HbA1c`, `fasting_glucose`, `fasting_insulin`, `ethnicity`, `diabetes_type` |
| PPGR outcome | `baseline_glucose`, `iAUC_2h`, `iAUC_3h`, `peak_delta`, `time_to_peak`, `late_auc`, `recovery_time` |

### 路线 3：分层外部验证，而非简单合并训练

推荐论文主结果结构：

1. Internal validation：CGMacros temporal split 与 leave-subject-out。
2. Nutrient-distribution validation：Jaeb Nutrition 与 CGMacros 餐食营养分布比较。
3. Healthy reference validation：Jaeb healthy adults 建立正常 CGM 波动和伪餐时窗口。
4. Disease-state transfer validation：T1D-UOM、D1NAMO、OhioT1DM。
5. Chinese diabetes reference：ShanghaiT1DM/T2DM。
6. Controlled challenge and mechanism：Stanford CGMDB。
7. In vitro bionic digestion validation：从 CGMacros/Stanford/Jaeb Nutrition 中选择代表性餐食原型。

### 路线 4：与体外仿生消化系统衔接

数据库可以帮助减少体外实验数量，提高命中率。建议用干实验筛选 12 至 24 个餐食原型：

1. CGMacros 中模型预测误差大且临床重要的餐食。
2. Stanford CGMDB 中标准化食物响应差异大的食物。
3. Jaeb Nutrition 中高 GL、低 GL、高纤维、高脂延迟吸收等典型营养结构。
4. D1NAMO/CGMacros 中有食物图片且可复原餐食结构的真实案例。

体外消化系统输出建议包括：

- glucose release Cmax
- Tmax
- early release slope
- half-release time
- simulated gastric emptying effect
- viscosity/particle-size/starch structure指标

这些指标可以作为 CGMacros 模型的机制特征或事后解释变量，用于证明模型不是纯统计相关，而能部分映射食物消化释放动力学。

## 六、对论文层级提升最关键的分析

1. Leave-dataset-out generalization：每个外部数据集作为独立测试，不把所有数据混在一起做随机划分。
2. Calibration transfer：在 CGMacros 建模后，仅用少量个体餐食对 T1D-UOM/D1NAMO 做 few-shot calibration。
3. Domain shift analysis：比较健康成人、CGMacros、T1D、T2D、中国队列之间的 baseline glucose、variability、PPGR amplitude。
4. Mechanistic triangulation：用 Stanford CGMDB 和体外消化数据解释为什么同等碳水下 PPGR 不同。
5. Feature hierarchy：证明 carb-only < macro < macro+clinical < macro+clinical+context/omics/digestion 的逐层提升。
6. Counterfactual realism check：用 Jaeb Nutrition 的 GI/GL 和 Stanford controlled food response 约束 CGMacros 的餐食替换模拟。

## 七、引用与来源链接

- CGMacros Scientific Data record: [https://www.nature.com/articles/s41597-025-04640-8](https://www.nature.com/articles/s41597-025-04640-8)
- Stanford CGMDB data: [https://cgmdb.stanford.edu/data/](https://cgmdb.stanford.edu/data/)
- T1D-UOM Zenodo record: [https://doi.org/10.5281/zenodo.15806142](https://doi.org/10.5281/zenodo.15806142)
- T1D-UOM Scientific Data article: [https://www.nature.com/articles/s41597-025-05695-1](https://www.nature.com/articles/s41597-025-05695-1)
- D1NAMO Zenodo record: [https://doi.org/10.5281/zenodo.5651217](https://doi.org/10.5281/zenodo.5651217)
- ShanghaiT1DM/T2DM Figshare record: [https://doi.org/10.6084/m9.figshare.21600933.v5](https://doi.org/10.6084/m9.figshare.21600933.v5)
- ShanghaiT1DM/T2DM Scientific Data article: [https://www.nature.com/articles/s41597-023-01940-7](https://www.nature.com/articles/s41597-023-01940-7)
- Jaeb public diabetes datasets: [https://public.jaeb.org/datasets/diabetes](https://public.jaeb.org/datasets/diabetes)
- OhioT1DM official page: [https://smarthealth.cs.ohio.edu/OhioT1DM-dataset.html](https://smarthealth.cs.ohio.edu/OhioT1DM-dataset.html)
- HUPA-UCM Mendeley Data record: [https://doi.org/10.17632/3hbcscwz44.1](https://doi.org/10.17632/3hbcscwz44.1)
