# 项目规则（PROJECT_RULES 索引）

本文件为总纲与索引。各功能域细则请参见 docs/ 目录：
- DATA_SPEC（数据文件规范）
- SCHEMA_AND_DB（表结构与数据库）
- ALIGNMENT_POLICY（时间与网格对齐策略）
- QUALITY_VALIDATION（数据质量与校验）
- DERIVATIONS（派生量与公式）
- FITTING_MODELS（特性曲线拟合）
- OPTIMIZATION（泵组优化）
- VIZ_SPEC（可视化规范）
- ENGINEERING_STANDARDS（工程与编码规范）
- RUNBOOK（运行手册）
- TESTING_STRATEGY（测试策略）
- GLOSSARY（术语表）

以下为总原则与成功标准摘要：

## 1. 配置与映射
- 唯一事实来源：`config/data_mapping.json` 是数据-设备-测点映射的唯一来源；代码严禁硬编码数据文件路径与设备/测点。
- 可扩展：新增站/设备/测点仅需更新映射文件，代码按模式加载。
- 标识规范：
  - `station_id` 由顶层键（如“二期供水泵房”）规范化生成。
  - `device_id` 由子键（如“二期供水泵房1#泵”）规范化生成。
  - `metric` 采用统一命名：`frequency, voltage_a, current_a, power, kwh, pressure, flow_rate, cumulative_flow, power_factor, ...`。

## 2. 文件解析与编码
- 编码自动识别：优先 UTF-8（含/不含 BOM），失败回退 GBK；失败记录审计并跳过。
- CSV 规范：自动识别分隔符（逗号优先），必须包含时间列与至少一列数值；多数值列转为 tidy 格式。
- 时间列识别：优先匹配列名（`时间/timestamp/采集时间/记录时间` 等）；不明确时尝试第一列多格式解析。
- 单位与数值处理：
  - 数值统一为浮点（或 decimal），非法值设为 NULL 并记录。
  - 单位统一：流量（m3/h）、压力（MPa 或 kPa，需确认）、电压（V）、电流（A）、功率（kW）、电度（kWh）、频率（Hz）；若源单位不同在配置中注明并换算。
- 去重与排序：按 `timestamp` 去重（device+metric 唯一），时间升序。

## 3. 时区与时间对齐
- 时区：默认 Asia/Shanghai，入库以 UTC 存储，保留本地时区视图。
- 精度：至少到秒，保留更高精度（ms/us）。
- 对齐策略：
  - 站内对齐优先，后站间对齐。
  - 统一时间网格（如 1s/5s/1min，默认根据数据自适应建议），最近邻采样+容差（≤ 半个网格步长），超容差记 NULL。
  - 插值：累计量禁插值（仅阶梯保持）；瞬时量可选线性插值，默认只最近邻不插值。
  - 支持滞后补偿（如总管流量相对泵功率滞后秒级校正）。

## 4. 入库与表结构（建议 PostgreSQL + TimescaleDB）
- 表设计：
  - `stations(id, name, meta)`
  - `devices(id, station_id, name, type, pump_type, meta)`
  - `metrics(id, name, unit, kind)` // kind: instantaneous|cumulative|state
  - `raw_timeseries(device_id, metric_id, ts_utc, ts_local, value, src_file, src_row, ingest_at)`
  - `aligned_timeseries(station_id, device_id, metric_id, ts_utc, ts_local, value, grid, version)`
  - `derived_timeseries(station_id, device_id, metric_id, ts_utc, ts_local, value, formula, version)`
  - `model_fits(scope, scope_id, model_type, input_metrics, hyperparams, train_range, valid_range, fit_artifacts, created_at)`
  - `fit_curves(scope, scope_id, curve_type, x_name, y_name, equation, params, goodness, constraints, version)`
  - `optimization_results(scope, scope_id, objective, constraints, method, result, created_at)`
- 唯一键：`raw_timeseries` 以 `(device_id, metric_id, ts_utc)` UPSERT；重复导入不产生重复。
- 版本化：对齐/派生带 `version`，参数变化 version+1，保留可追溯性。

## 5. 数据质量与校验
- 基础校验：
  - 累计量（kWh/累计流量）非递减，否则标记“归零/复位/换表”，切分周期。
  - 合理范围：为每测点设置硬/软阈值（软阈报警但保留，硬阈置 NULL）。
  - 缺失比率：统计每设备/测点缺失，超过阈值（如 30%）的区段在拟合与优化中剔除。
  - 离群：IQR/MAD 或滑窗 z-score 标记离群；保留原值，在质量标签中记录。
- 交叉校验：
  - 电功率关系：`S ≈ √3·U·I`，`P ≈ S·PF`；U/I/P/PF 交叉验证。
  - 水力功率：`P_h = ρ·g·Q·H` 与电功率（扣效率）对比。
  - 累计量增量与瞬时量积分一致性校验（ΔkWh、Δ累计流量 vs 积分）。
- 审计日志：记录每次入库/对齐/派生/拟合/优化的参数、范围、指标与异常摘要。

## 6. 派生数据
- 统一公式库（可配置）：ρ=1000 kg/m3，g=9.80665 m/s2，必要时温度修正。
- 常用派生：视在功率S、无功功率Q、效率η、扬程H（由压力换算并考虑高度差）、平滑功率、能效指标等。
- 设备/口径/延迟差异允许配置滞后补偿。

## 7. 特性曲线拟合（机理 + 统计/ML/DL）
- 相似定律：`Q ∝ n`，`H ∝ n²`，`P ∝ n³`；直径缩放：`Q ∝ D³`，`H ∝ D²`。
- 形状约束：`H(Q)` 递减、`η(Q)` 单峰、`P(Q)` 单峰或单调；约束可通过惩罚或投影实现。
- 分层拟合：
  - 单泵：`H–Q`、`η–Q`、`P–Q`；可分频率层或将 n 作为输入。
  - 泵组：并联合成特性与系统曲线；按机组状态分段。
  - 泵站：站级功耗与供水能力拟合，估系统阻力系数。
- 模型序列：
  1) 物理启发参数化曲线（多项式/有理函数/幂函数）
  2) 传统 ML（XGBoost/LightGBM/随机森林）+ 物理一致性后处理
  3) 小型 MLP + 形状/物理损失（保持可解释性）
- 评估：R²、RMSE/MAE、最大相对误差、物理一致性违约率、K 折与留站/留泵验证、置信区间（分位回归/Bootstrap）。

## 8. 泵组优化
- 目标：单位水量能耗最小或功率最小；可加约束（压力下限、流量区间、启停成本、切换频率）。
- 决策变量：开停组合、转速/频率设定、切换阈值策略。
- 方法：MILP/MIQP 或启发式；约束由拟合曲线或机理模型提供。
- 输出：推荐运行组合、预期节能量、对供水指标的影响与敏感性分析。

## 9. 可视化与交互
- 方案优先：快速原型（Streamlit/Dash），后续可迁 Web 前端。
- 视图：
  - 数据总览（完整度/缺失/离群/时间轴）
  - 对齐与派生（原值 vs 对齐值 vs 派生值）
  - 特性曲线（H–Q、η–Q、P–Q）含置信带与频率分面
  - 优化（目标/约束/推荐组合与收益）
- 可追踪性：每图带版本、参数、时间范围元数据。

## 10. 工程实践
- 幂等：导入/对齐/派生/拟合/优化均可重复执行，结果可重现。
- 任务编排：提供 CLI/任务流：`ingest → align → validate → derive → fit → optimize → viz`。
- 日志与告警：结构化日志；关键阈值触发告警。
- 测试：
  - 单元：CSV/时间解析、单位换算、对齐、派生公式。
  - 集成：小样本端到端；性能：大文件基线测试。
- 数据安全：只读 `data/`；不访问 `venv/.venv`；外部写仅限数据库与本项目输出目录。

## 11. 成功标准（DoD）
- 入库成功率 > 98%；累计量非递减异常全部识别并标注。
- 对齐完整度 > 95%，无超容差误配。
- 拟合：主要泵 `H–Q/η–Q` R² ≥ 0.95，最大相对误差 ≤ 10%。
- 优化：提供可执行的运行组合与节能评估，并与历史区段对比一致。
- 可视化：覆盖全流程，支持导出。

## 12. 需要确认的配置项
- 数据库类型与连接（建议 PostgreSQL + TimescaleDB）。
- 时区（默认 Asia/Shanghai）、压力/流量单位。
- 对齐网格（1s/5s/1min 或自适应建议）。
- 各测点阈值与容差、滞后补偿设置。
- 可视化框架（Streamlit/Dash）。



## 附录 A：指标分类与单位（建议默认）
- 指标分类（kind）：
  - instantaneous：frequency, voltage_a/b/c, current_a/b/c, power, power_factor, pressure, flow_rate
  - cumulative：kwh, cumulative_flow
- 单位（与 rules/rules.yml 保持一致）：
  - pressure：kPa（如源为 MPa 则换算 ×1000）
  - flow_rate：m3/h；energy：kWh；power：kW；voltage：V；current：A；frequency：Hz

## 附录 B：对齐网格决策规则
- 网格选择（auto）：
  1) 计算站内每个 metric 的邻近时间差中位数 dt_med
  2) 取全站 dt* = min(dt_med)；将 dt* 映射到标准网格 {1s, 5s, 1min}
  3) 最近邻容差 = 0.5 × 网格步长；超过容差记 NULL
- 阶梯保持：对 cumulative 指标按“上一个有效值”保持至下一采样点（不可插值）
- 滞后补偿：允许对指定 metric 配置固定秒级滞后以提高跨测点对齐一致性

## 附录 C：质量阈值建议（可在 rules.yml 配置）
- 缺失率阈值：30%
- 离群检测：z-score 阈值 4.0（或 MAD/IQR 备选）
- 交叉校验容忍：
  - P 与 √3UI·PF 相对误差的警戒阈值 20%（可按设备调整）
  - 水力功率与电功率（扣效率）相对误差的警戒阈值 30%

## 附录 D：派生与机理公式
- 水头 H（m）：H ≈ p/(ρg) + Δz，其中 p 为表压对应的压强（Pa），ρ=1000 kg/m3，g=9.80665 m/s²
- 水力功率 P_h（kW）：P_h = ρ·g·Q·H / 1000，其中 Q 为体积流量（m3/s）
- 效率估计：η_total ≈ P_h / P_elec（必要时进行滤波平滑）

## 附录 E：特性曲线参数化模型建议
- H–Q：二次/有理函数（递减约束），示例 H(Q)=a - bQ - cQ²
- P–Q：单峰或单调递增区段的分段多项式/样条
- η–Q：单峰函数（高斯形/二次/样条带单峰约束）
- 频率/转速 n 的作用：可分层拟合（按 n 分面）或将 n 作为自变量引入（遵循 Q∝n, H∝n², P∝n³ 的相似定律）
- 评估：R²、RMSE/MAE、最大相对误差、物理一致性违约率、K 折/留站-留泵验证、置信区间

## 附录 F：优化目标与约束示例
- 目标：单位水量能耗最小（kWh/m3）或总功率最小
- 约束：供水压力下限、总流量区间、启停成本、最大切换频率/小时
- 决策变量：泵运行组合、转速/频率设定值、切换阈值

## 附录 G：CLI 阶段与命令约定（占位）
- ingest：从 config/data_mapping.json 导入 → raw_timeseries（UPSERT）
- align：站内对齐到统一网格 → aligned_timeseries（version+1）
- validate：数据质量与交叉校验 → 质量报告
- derive：计算派生量（H、η 等）→ derived_timeseries（version+1）
- fit：特性曲线拟合（单泵/泵组/泵站）→ model_fits / fit_curves
- optimize：基于曲线与约束求解运行组合 → optimization_results
- viz：可视化交互界面展示全流程与结果


## 13. 编码规范与工程实践细则（必须遵守）

### 13.1 语言与版本
- Python ≥ 3.9，跨平台兼容，路径与文件操作优先使用 `pathlib`。
- 禁止访问或解析 `venv/.venv/env` 目录。

### 13.2 目录与模块组织（后续实现将补充 src/）
- 约定结构：`src/`（业务逻辑）`scripts/`（脚本）`tests/`（测试）`config/` `rules/` `data/` `docs/`。
- 模块划分：`ingest`、`align`、`validate`、`derive`、`fit`、`optimize`、`viz` 分层清晰，互相通过明确接口交互。

### 13.3 依赖与环境
- 依赖统一通过包管理器安装与锁定（pip/poetry），严禁手动改锁文件。
- 本地环境变量用于敏感信息（DB_URL 等），提供 `.env.sample` 示例，禁止将真实密钥提交。

### 13.4 代码风格与静态检查
- 格式化：Black；导入排序：isort；Lint：Ruff/Flake8；类型检查：mypy（允许渐进式）。
- 命名：`snake_case`（函数/变量）、`PascalCase`（类）、`UPPER_CASE`（常量）。
- 注释与 Docstring：公共函数/类必须有文档字符串（Google 或 NumPy 风格），说明 `Args/Returns/Raises`。
- 行为：无死代码、无大段注释掉的代码；不足 20 行的 lambda/列表推导可用，复杂逻辑用显式函数。

### 13.5 类型与数据模型
- 公共 API 必须完整类型标注；内部关键数据结构使用 `dataclasses`/Pydantic（用于配置/参数校验）。
- DataFrame 字段规范（最小集合）：`station_id, device_id, metric, ts_local, ts_utc, value`；索引可设置为 `ts_utc`。

### 13.6 错误处理与异常体系
- 分层自定义异常：`IngestError, AlignError, ValidationError, DeriveError, FitError, OptimizeError`。
- 只在边界（I/O/入口 CLI）捕获并记录异常，内部尽量“fail fast”；附加上下文（站/泵/metric/时间范围）。
- 对可预期异常给出可操作建议（例如编码失败、时间解析失败、单位缺失）。

### 13.7 日志规范（结构化）
- 统一使用 `logging`，禁止 `print`；日志包含 `run_id/version/station/device/metric/time_range/row_count` 等关键字段。
- 级别约定：INFO（阶段进度）、WARNING（质量告警/阈值越界）、ERROR（失败并中止）、DEBUG（调试细节）。

### 13.8 配置与参数
- 所有策略类参数来自 `rules/rules.yml`；业务只读配置，严禁硬编码数据路径与单位换算。
- 数据库连接与密钥来自环境变量/安全仓库；不得写入代码仓库。

### 13.9 I/O 与性能
- CSV 读取：显式 `encoding`（自动探测失败则回退 GBK）、`parse_dates`、`dtype`、`na_values`；必要时分块（chunksize）。
- 大文件处理：流式/分区/分站处理，避免整体读入内存；对齐前先按站/设备分组。
- 持久化：批量写入（批大小可配），失败重试与幂等（UPSERT）。

### 13.10 时间与时区
- 所有时间戳统一转为 tz-aware；本地时区默认 Asia/Shanghai，入库存 UTC；禁止混用朴素时间。
- 对齐/聚合前先完成时区转换；导出/展示时再转换为本地时区。

### 13.11 数值健壮性与单位
- 所有数值操作前先 `isfinite` 检查；分母接近 0 时进行下限钳制/提前返回并打日志。
- 单位换算集中管理；压力默认 kPa（PROJECT_RULES 与 rules.yml 一致），若源为 MPa 则 ×1000。

### 13.12 DataFrame 约定
- 函数避免就地修改传入 DataFrame（除非明确标注），返回新对象或拷贝；保留列名与 dtypes 一致性。
- 对齐输出包含 `grid` 与 `version` 元数据；累计量仅作阶梯保持，不插值。

### 13.13 测试与覆盖率
- 测试框架：pytest；为解析/对齐/派生/质量检查/曲线拟合/优化分别编写单测与集成测。
- 最小覆盖建议：关键模块 ≥ 80%；对异常/边界（空文件、乱序、单位缺失、复位）必须有用例。

### 13.14 提交与评审
- 提交信息遵循 Conventional Commits：`feat|fix|docs|test|refactor|perf|chore|build|ci`。
- PR 必填“规则合规清单”，附运行日志/质量报告摘要；大改动需要“设计说明”与“回滚方案”。

### 13.15 安全与合规
- 严禁提交敏感数据与真实生产数据；示例/脱敏后再入库测试。
- 严禁执行会修改生产状态的脚本（迁移/删除）未经审批；默认一切为只读，除非明确授权。

### 13.16 可追溯与复现
- 每次 run 生成 `run_id` 与固定的随机种子（拟合/优化）；输出记录参数、输入范围、版本、摘要指标。
- 任何阶段参数变化均引起 `version+1`，并在持久化记录与图表元数据中体现。

## 附录 H：工具链建议（可选）
- Pre-commit：集成 black、isort、ruff、mypy、pytest 快检。
- 质量闸：`python scripts/quality_gate.py`；CI 中与 `pytest -q` 一起运行。
- 文档：使用 MkDocs 或 Sphinx 生成“用户指南/开发者指南/API 参考”。
