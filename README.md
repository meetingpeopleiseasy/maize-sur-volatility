# 玉米库存使用比与价格波动：一项探索性实证研究

本项目以 Storage Theory 的库存缓冲机制为出发点，使用 USDA 玉米供需数据与 CME 期货价格数据，考察玉米库存使用比（stocks-to-use ratio，SUR）与价格波动之间的关系。这是一项个人开展的探索性实证研究，重点展示真实的数据整理、计量分析与模型诊断过程，而不是宣称已经得到稳定的因果结论。

## 项目概览

研究问题：库存趋紧（SUR 较低）是否伴随更高的玉米价格波动？理论动机来自 Storage Theory——库存是吸收供需冲击的缓冲，库存充裕时波动相对温和，库存趋紧时缓冲能力下降、冲击只能通过更大的价格调整出清，从而推高波动率。

这是一个有明确理论出处、但识别上很困难的问题：库存本身由供需共同决定，存在共同趋势与前视（look-ahead）偏差。选择它，是为了经历一次从数据整理到研究判断的完整实证流程。

主要数据：USDA《Feed Grains Yearbook》表 4 的季度库存与使用数据；CME 玉米连续合约日度结算价（用于构造季度已实现波动率 RV）；1877 年起的历史日度价格区间数据（作为长样本替代口径）。

主要工作：营销年度（9 月起）与季度的时间匹配、SUR 构造、日度收益率与季度波动率构造、换月异常处理，以及 OLS/HAC 回归、季节与趋势控制、非线性与阈值检验、结构断点与时序诊断、反向关系检查。

目前判断：初步负相关在控制季节性、趋势与波动持续性后不再稳健，现有数据尚不足以支持对库存缓冲效应的因果解释。

## 我实际完成的工作

| 工作模块 | 实际工作 |
| --- | --- |
| 数据整理 | 多源数据整理、营销年度与季度匹配、SUR 构造、缺失与异常处理 |
| 变量构造 | 日度对数收益率、季度已实现波动率、日度价格区间季度均值、换月异常识别与置零 |
| 计量分析 | 基准 OLS、HAC 推断、季度固定效应、线性趋势与滞后波动率 |
| 模型检验 | 二次项、样条与阈值（sup-F bootstrap）、扩张窗口样本外比较、结构断点检验 |
| 时序诊断 | 季节性与持续性、单位根与平稳性、反向回归、一阶差分短期模型 |

## 主要研究判断

- 只控制季度固定效应时，SUR 系数显著为负（第一、第二近月价格区间约为 −0.011，p < 0.05）。
- 加入线性趋势后系数转为正且不显著，再加入滞后波动率后趋近于零。原始负相关主要来自共同趋势，而不是独立的库存缓冲机制。
- 阈值效应不显著（bootstrap p ≈ 0.24–0.28）；非线性模型相对线性模型的样本外改善不超过约 1%。
- SUR 高度持续（去季节后 AR(1) ≈ 0.91），且存在反向关系：在含趋势设定下，滞后价格区间仍可预测 SUR（第二近月口径 p ≈ 0.02），这更像共同趋势或反馈，而非独立的库存缓冲机制。
- 因此本研究的意义不在于“发现了一个稳健结果”，而在于根据诊断结果逐步修正判断、明确识别边界的过程。

## 从哪里开始阅读

| 阅读顺序 | 材料 | 为什么值得看 |
| --- | --- | --- |
| 1 | [研究经历展示 PDF](docs/demonstration_of_research_abilities_v2.pdf) | 两页快速了解研究问题、工作流程与主要判断 |
| 2 | [研究流程图](results/figures/workflow_diagram.pdf) | 看清库存与价格两条数据支线如何汇合、分析如何分层 |
| 3 | [SUR 系数图](results/figures/sur_coef_final.pdf) | 一张图看懂系数符号随模型设定翻转 |
| 4 | [季度主分析脚本](scripts/analysis/ppj_4.py) | 基准回归、阈值、结构断点与样本外比较的实现 |
| 5 | [实验与诊断记录](docs/process_outcome.md) | 看到结果不稳健后如何调整研究判断、并设定停止标准 |

## 目录结构

```
.
├── data/                # 输入数据
├── scripts/
│   ├── data/            # 数据构造
│   ├── analysis/        # 主分析
│   ├── diagnostics/     # 研究诊断
│   └── figures/         # 绘图脚本
├── results/
│   ├── figures/         # 图
│   └── tables/          # 结果表
└── docs/                # 展示材料与过程记录
```

## 项目状态与研究边界

已完成且可在仓库中查阅：

- USDA 库存数据整理与 SUR 构造，日度价格区间季度聚合。
- 以日度价格区间为因变量的完整探索性分析（OLS/HAC、季节与趋势、非线性、阈值、结构断点、时序诊断），结果见 [sur_coef_final_results.csv](results/tables/sur_coef_final_results.csv)。
- CHRIS-CME 连续合约的季度已实现波动率（RV）管道已构造，原始价格文件 `CHRIS-CME_C1.csv` 已在 `data/` 中；RV 主口径回归已运行，各设定均不显著（[sur_coef_final_rv_results.csv](results/tables/sur_coef_final_rv_results.csv)，n = 167）。该口径未纳入最终展示图，结论同样不支持库存缓冲效应的因果解释。

仅属探索性、不作因果解释：

- 阈值检验、非线性样本外比较、反向回归与断点检验均为诊断性分析；样本量约 168 个季度，统计功效有限。

尚未完成：

- 带发布时点（vintage）的库存数据尚未取得，SUR 分母存在前视偏差的问题尚未解决。
- 使用外生供给冲击或 WASDE 事件研究进行因果识别的计划尚未实施。

研究结论边界：现有证据仅支持历史样本中的条件相关，不能识别库存缓冲效应的因果机制；未完成的工作不会在本仓库中表述为已完成。

## 代码与复现说明

- 语言与依赖：Python。核心季度分析（`scripts/analysis/ppj_4.py`、`scripts/diagnostics/ppj_5_data_audit.py`、`scripts/diagnostics/ppj_6_ts_diagnostics.py`、`scripts/figures/plot_sur_coef_final.py`）只依赖 numpy、scipy、matplotlib；`scripts/analysis/ppj_1.py`、`scripts/data/pj_3test.py`、`scripts/figures/plot_sur_coef_final_rv.py` 等还需 pandas、statsmodels、pyfixest。
- 数据来源：`data/feed-grains-yearbook-all-years.xlsx`（USDA Feed Grains Yearbook 表 4）；`data/rangedata_commodities_since1877.csv`（Zenodo 公开数据集 “Daily historical price ranges of Wheat, Corn and Oats futures”）；`data/CHRIS-CME_C1.csv`（Nasdaq Data Link 玉米连续合约日度结算价）；`data/Grain_Basis_20261020.csv`（USDA AMS 基差数据）。
- 复现注意：脚本原本以平铺方式运行，相互 `import ppj_4`，并从当前工作目录读取数据文件。本仓库为了便于阅读按 `data/`、`scripts/`、`results/`、`docs/` 归档，因此不能直接在各子目录内运行脚本；要复现需把脚本与它们依赖的数据文件放到同一工作目录（或按脚本内的相对路径约定调整），再按 `ppj_4.py` → `ppj_5_data_audit.py` / `ppj_6_ts_diagnostics.py` → `plot_sur_coef_final.py` 的顺序执行。绘图脚本还需要 Noto Sans CJK SC 字体文件（未随仓库附带）。
- 可复现范围：以日度价格区间为因变量的核心分析，所需数据文件均在 `data/` 中，脚本为 numpy/scipy 自包含实现；但本仓库尚未进行过端到端重新运行验证，因此不声称“开箱即用”。
- 不能保证从头复现：早期月度/日度分析（依赖未在仓库中留存的中间数据或未装齐的第三方包）。

## 数据与授权

`feed-grains-yearbook-all-years.xlsx`、`Grain_Basis_20261020.csv` 来自 USDA，`rangedata_commodities_since1877.csv` 来自 Zenodo 公开数据集，属公开来源。`CHRIS-CME_C1.csv` 来自 Nasdaq Data Link 的免费 API，下载数据是否允许再分发需以该平台当前条款为准，公开此文件前建议先确认授权。
